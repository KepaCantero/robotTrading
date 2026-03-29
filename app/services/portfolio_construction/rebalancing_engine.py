"""
T18.1.2: RebalancingEngine - Dynamic portfolio rebalancing

Executes periodic and threshold-based portfolio rebalancing with cost tracking.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RebalancingFrequency(str, Enum):
    """Rebalancing frequency options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass
class RebalancingTrade:
    """Single trade in a rebalancing event."""

    asset: str
    current_weight: Decimal
    target_weight: Decimal
    delta_weight: Decimal
    estimated_cost: Decimal


@dataclass
class RebalancingEvent:
    """Complete rebalancing event with all trades and metrics."""

    event_id: str
    timestamp: datetime
    reason: str  # "threshold" or "scheduled"
    trades: list[RebalancingTrade] = field(default_factory=list)
    total_trade_value: Decimal = Decimal("0")
    total_transaction_cost: Decimal = Decimal("0")
    estimated_cost_basis_adjustment: Decimal = Decimal("0")
    num_trades: int = 0
    status: str = "pending"  # pending, executed, failed


class RebalancingEngine:
    """
    Rebalances portfolio based on frequency and drift thresholds.

    Features:
    - Periodic rebalancing (daily, weekly, monthly, etc.)
    - Threshold-based rebalancing (drift > X%)
    - Cost tracking and estimation
    - Rebalancing history
    - Minimum trade size filtering
    """

    def __init__(
        self,
        frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
        drift_threshold: Optional[Decimal] = None,
        min_trade_value: Optional[Decimal] = None,
        transaction_cost_rate: Optional[Decimal] = None,  # 0.1%
    ):
        """
        Initialize rebalancing engine.

        Args:
            frequency: Rebalancing frequency
            drift_threshold: Threshold for drift-based rebalancing
            min_trade_value: Minimum trade value to execute
            transaction_cost_rate: Transaction cost as % of trade value
        """
        if drift_threshold is None:
            drift_threshold = Decimal("0.05")
        if min_trade_value is None:
            min_trade_value = Decimal("100")
        if transaction_cost_rate is None:
            transaction_cost_rate = Decimal("0.001")
        self.frequency = frequency
        self.drift_threshold = drift_threshold
        self.min_trade_value = min_trade_value
        self.transaction_cost_rate = transaction_cost_rate
        self.last_rebalance: Optional[datetime] = None
        self.rebalancing_events: list[RebalancingEvent] = []
        self.event_counter = 0
        logger.info(f"✅ RebalancingEngine initialized ({frequency.value} rebalancing)")

    async def should_rebalance_by_schedule(self) -> bool:
        """
        Check if scheduled rebalancing is due.

        Returns:
            True if rebalancing interval has passed
        """
        if self.last_rebalance is None:
            return True

        now = datetime.now()
        interval = self._get_interval_days()

        return (now - self.last_rebalance).days >= interval

    def _get_interval_days(self) -> int:
        """Get rebalancing interval in days."""
        intervals = {
            RebalancingFrequency.DAILY: 1,
            RebalancingFrequency.WEEKLY: 7,
            RebalancingFrequency.MONTHLY: 30,
            RebalancingFrequency.QUARTERLY: 90,
            RebalancingFrequency.ANNUALLY: 365,
        }
        return intervals.get(self.frequency, 30)

    async def plan_rebalancing(
        self,
        current_allocation: dict[str, Decimal],
        target_allocation: dict[str, Decimal],
        portfolio_value: Decimal,
        reason: str = "drift_threshold",
    ) -> RebalancingEvent:
        """
        Plan rebalancing trades.

        Args:
            current_allocation: Current allocation {asset: weight}
            target_allocation: Target allocation {asset: weight}
            portfolio_value: Current portfolio value
            reason: Reason for rebalancing ("threshold" or "scheduled")

        Returns:
            RebalancingEvent with planned trades
        """
        self.event_counter += 1
        event = RebalancingEvent(
            event_id=f"rebalance_{self.event_counter}",
            timestamp=datetime.now(),
            reason=reason,
        )

        all_assets = set(current_allocation.keys()) | set(target_allocation.keys())
        total_cost = Decimal("0")

        for asset in sorted(all_assets):
            current_weight = current_allocation.get(asset, Decimal("0"))
            target_weight = target_allocation.get(asset, Decimal("0"))
            delta_weight = target_weight - current_weight

            # Calculate trade value
            trade_value = abs(delta_weight * portfolio_value)

            # Skip small trades
            if trade_value < self.min_trade_value:
                continue

            # Estimate transaction cost
            trade_cost = trade_value * self.transaction_cost_rate
            total_cost += trade_cost

            trade = RebalancingTrade(
                asset=asset,
                current_weight=current_weight,
                target_weight=target_weight,
                delta_weight=delta_weight,
                estimated_cost=trade_cost,
            )
            event.trades.append(trade)

        event.num_trades = len(event.trades)
        event.total_transaction_cost = total_cost
        event.total_trade_value = sum(abs(t.delta_weight * portfolio_value) for t in event.trades)
        event.status = "pending"

        logger.info(f"✅ Rebalancing plan created: {event.num_trades} trades, cost=${total_cost}")
        return event

    async def execute_rebalancing(self, event: RebalancingEvent) -> bool:
        """
        Execute rebalancing event.

        Args:
            event: RebalancingEvent to execute

        Returns:
            True if execution successful
        """
        try:
            event.status = "executed"
            self.last_rebalance = datetime.now()
            self.rebalancing_events.append(event)
            logger.info(f"✅ Rebalancing executed: {event.event_id} ({event.num_trades} trades)")
            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            event.status = "failed"
            logger.error(f"❌ Rebalancing failed: {e}")
            return False

    async def should_rebalance_by_drift(
        self,
        current_allocation: dict[str, Decimal],
        target_allocation: dict[str, Decimal],
    ) -> bool:
        """
        Check if drift exceeds threshold.

        Args:
            current_allocation: Current allocation
            target_allocation: Target allocation

        Returns:
            True if any asset exceeds drift threshold
        """
        all_assets = set(current_allocation.keys()) | set(target_allocation.keys())

        for asset in all_assets:
            current = current_allocation.get(asset, Decimal("0"))
            target = target_allocation.get(asset, Decimal("0"))
            drift = abs(current - target)

            if drift > self.drift_threshold:
                return True

        return False

    async def estimate_rebalancing_cost(
        self,
        trades: list[RebalancingTrade],
    ) -> Decimal:
        """
        Estimate total cost of rebalancing.

        Args:
            trades: List of planned trades

        Returns:
            Total estimated cost (transaction + slippage)
        """
        return sum(t.estimated_cost for t in trades)

    async def get_rebalancing_statistics(self) -> dict:
        """Get rebalancing statistics."""
        if not self.rebalancing_events:
            return {
                "total_events": 0,
                "total_trades": 0,
                "total_cost": Decimal("0"),
                "avg_cost_per_event": Decimal("0"),
            }

        total_trades = sum(e.num_trades for e in self.rebalancing_events)
        total_cost = sum(e.total_transaction_cost for e in self.rebalancing_events)
        avg_cost = (
            total_cost / len(self.rebalancing_events) if self.rebalancing_events else Decimal("0")
        )

        return {
            "total_events": len(self.rebalancing_events),
            "total_trades": total_trades,
            "total_cost": float(total_cost),
            "avg_cost_per_event": float(avg_cost),
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
        }

    async def get_rebalancing_history(
        self,
        limit: Optional[int] = None,
    ) -> list[RebalancingEvent]:
        """
        Get rebalancing event history.

        Args:
            limit: Maximum events to return

        Returns:
            Rebalancing history
        """
        if limit is None:
            return self.rebalancing_events
        return self.rebalancing_events[-limit:]

    def get_engine_status(self) -> dict:
        """Get rebalancing engine status."""
        return {
            "frequency": self.frequency.value,
            "drift_threshold": float(self.drift_threshold),
            "min_trade_value": float(self.min_trade_value),
            "transaction_cost_rate": float(self.transaction_cost_rate),
            "total_events": len(self.rebalancing_events),
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
        }


# Singleton
_engine: Optional[RebalancingEngine] = None


def get_rebalancing_engine(
    frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
    drift_threshold: Optional[Decimal] = None,
) -> RebalancingEngine:
    """Get or create singleton RebalancingEngine."""
    if drift_threshold is None:
        drift_threshold = Decimal("0.05")
    global _engine
    if _engine is None:
        _engine = RebalancingEngine()

    return _engine
