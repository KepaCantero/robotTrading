"""
T18.1.1: AllocationManager - Portfolio allocation tracking and management

Manages current portfolio allocations, tracks deviations, and maintains allocation history.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AllocationSnapshot:
    """Snapshot of portfolio allocation at a point in time."""
    timestamp: datetime
    allocations: Dict[str, Decimal]  # {asset: weight}
    total_value: Decimal
    drift_from_target: Dict[str, Decimal]  # {asset: deviation%}


@dataclass
class AllocationMetrics:
    """Metrics for current allocation."""
    concentration_ratio: Decimal  # Largest position / total
    herfindahl_index: Decimal  # Sum of squared weights (0-1)
    num_positions: int
    largest_position: str
    largest_position_weight: Decimal
    smallest_position: str
    smallest_position_weight: Decimal


class AllocationManager:
    """
    Manages portfolio allocations with tracking and drift detection.

    Features:
    - Current allocation tracking
    - Target allocation comparison
    - Drift and rebalancing threshold detection
    - Allocation history snapshots
    - Concentration metrics
    """

    def __init__(self, rebalancing_threshold: Decimal = Decimal("0.05")):
        """
        Initialize allocation manager.

        Args:
            rebalancing_threshold: Drift threshold for rebalancing (default 5%)
        """
        self.rebalancing_threshold = rebalancing_threshold
        self.current_allocation: Dict[str, Decimal] = {}
        self.target_allocation: Dict[str, Decimal] = {}
        self.allocation_history: List[AllocationSnapshot] = []
        self.total_value: Decimal = Decimal("0")
        logger.info("✅ AllocationManager initialized")

    async def set_target_allocation(self, allocation: Dict[str, Decimal]) -> bool:
        """
        Set target portfolio allocation.

        Args:
            allocation: Target allocation {asset: weight}

        Returns:
            True if valid allocation (sums to ~1.0)
        """
        try:
            total = sum(allocation.values())
            if not (Decimal("0.99") <= total <= Decimal("1.01")):
                logger.error(f"❌ Invalid allocation, sum={total}")
                return False

            self.target_allocation = allocation
            logger.info(f"✅ Target allocation set: {len(allocation)} assets")
            return True
        except Exception as e:
            logger.error(f"❌ Error setting target allocation: {e}")
            return False

    async def set_current_allocation(
        self,
        allocation: Dict[str, Decimal],
        total_value: Decimal,
    ) -> bool:
        """
        Set current portfolio allocation.

        Args:
            allocation: Current allocation {asset: weight}
            total_value: Total portfolio value

        Returns:
            True if valid
        """
        try:
            total = sum(allocation.values())
            if not (Decimal("0.99") <= total <= Decimal("1.01")):
                logger.error(f"❌ Invalid allocation, sum={total}")
                return False

            self.current_allocation = allocation
            self.total_value = total_value

            # Record snapshot
            drift = await self._calculate_drift()
            snapshot = AllocationSnapshot(
                timestamp=datetime.now(),
                allocations=allocation.copy(),
                total_value=total_value,
                drift_from_target=drift,
            )
            self.allocation_history.append(snapshot)

            logger.debug(f"✅ Current allocation updated: {len(allocation)} assets")
            return True
        except Exception as e:
            logger.error(f"❌ Error setting current allocation: {e}")
            return False

    async def get_drift(self) -> Dict[str, Decimal]:
        """Get current drift from target allocation."""
        return await self._calculate_drift()

    async def _calculate_drift(self) -> Dict[str, Decimal]:
        """Calculate deviation from target for each asset."""
        drift = {}
        all_assets = set(self.current_allocation.keys()) | set(self.target_allocation.keys())

        for asset in all_assets:
            current = self.current_allocation.get(asset, Decimal("0"))
            target = self.target_allocation.get(asset, Decimal("0"))
            drift[asset] = current - target

        return drift

    async def needs_rebalancing(self) -> bool:
        """
        Check if portfolio drift exceeds rebalancing threshold.

        Returns:
            True if any asset has drift > threshold
        """
        drift = await self._calculate_drift()
        max_drift = max(abs(d) for d in drift.values()) if drift else Decimal("0")
        return max_drift > self.rebalancing_threshold

    async def get_rebalancing_trades(
        self,
        current_values: Dict[str, Decimal],
    ) -> Dict[str, Decimal]:
        """
        Calculate trades needed to rebalance to target.

        Args:
            current_values: Current position values {asset: value}

        Returns:
            Rebalancing trades {asset: delta_value}
        """
        total = sum(current_values.values())
        if total == 0:
            return {}

        trades = {}
        for asset, target_weight in self.target_allocation.items():
            current_value = current_values.get(asset, Decimal("0"))
            target_value = total * target_weight
            delta = target_value - current_value
            if abs(delta) > Decimal("0.01"):  # Only trades > 0.01 in value
                trades[asset] = delta

        return trades

    async def get_allocation_metrics(self) -> AllocationMetrics:
        """Calculate concentration and diversity metrics."""
        if not self.current_allocation:
            return AllocationMetrics(
                concentration_ratio=Decimal("0"),
                herfindahl_index=Decimal("0"),
                num_positions=0,
                largest_position="",
                largest_position_weight=Decimal("0"),
                smallest_position="",
                smallest_position_weight=Decimal("0"),
            )

        weights = list(self.current_allocation.values())
        largest = max(weights)
        smallest = min(weights)

        # Herfindahl index: sum of squared weights
        herfindahl = sum(w * w for w in weights)

        largest_asset = [a for a, w in self.current_allocation.items() if w == largest][0]
        smallest_asset = [a for a, w in self.current_allocation.items() if w == smallest][0]

        return AllocationMetrics(
            concentration_ratio=largest,
            herfindahl_index=herfindahl,
            num_positions=len(self.current_allocation),
            largest_position=largest_asset,
            largest_position_weight=largest,
            smallest_position=smallest_asset,
            smallest_position_weight=smallest,
        )

    async def get_allocation_history(
        self,
        limit: Optional[int] = None,
    ) -> List[AllocationSnapshot]:
        """
        Get allocation history snapshots.

        Args:
            limit: Maximum number of snapshots to return

        Returns:
            Allocation history
        """
        if limit is None:
            return self.allocation_history
        return self.allocation_history[-limit:]

    def get_management_status(self) -> Dict:
        """Get allocation management status."""
        return {
            "current_allocation": len(self.current_allocation),
            "target_allocation": len(self.target_allocation),
            "total_value": float(self.total_value),
            "history_snapshots": len(self.allocation_history),
            "rebalancing_threshold": float(self.rebalancing_threshold),
        }


# Singleton
_manager: Optional[AllocationManager] = None


def get_allocation_manager(
    rebalancing_threshold: Decimal = Decimal("0.05"),
) -> AllocationManager:
    """Get or create singleton AllocationManager."""
    global _manager
    if _manager is None:
        _manager = AllocationManager(rebalancing_threshold)
    return _manager
