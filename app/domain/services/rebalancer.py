"""
Rebalancer Domain Service - Portfolio rebalancing logic

Rebalancer provides domain logic for rebalancing portfolios
to target weights and managing drift.

Reference: Rule 05-architecture.md, Rule 03-solid-principles.md
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from app.domain.entities.portfolio import Portfolio
from app.domain.entities.position import Position
from app.domain.value_objects.percentage import Percentage


@dataclass
class RebalanceTrade:
    """Trade required for rebalancing."""

    symbol: str
    target_quantity: Decimal
    current_quantity: Decimal
    trade_quantity: Decimal  # Positive = buy, Negative = sell
    target_value: Decimal
    current_value: Decimal
    drift_pct: Decimal  # How far from target (percentage points)
    average_price: Decimal  # Average price per unit (used for validation)


@dataclass
class RebalancePlan:
    """Complete rebalancing plan."""

    total_value: Decimal
    cash_available: Decimal
    trades: List[RebalanceTrade]
    total_drift: Decimal  # Overall portfolio drift
    estimated_cost: Decimal  # Estimated transaction costs

    def has_trades(self) -> bool:
        """Check if rebalancing requires trades."""
        return len(self.trades) > 0


@dataclass
class RebalanceConfig:
    """Configuration for rebalancing."""

    drift_threshold: Percentage = Percentage.from_percent(5)  # 5% drift threshold
    min_trade_size: Decimal = Decimal("100")  # Minimum trade size
    max_trade_size_pct: Percentage = Percentage.from_percent(20)  # Max single trade
    allow_fractional: bool = False  # Allow fractional shares
    cost_per_trade: Decimal = Decimal("1")  # Estimated cost per trade


class Rebalancer:
    """
    Domain service for portfolio rebalancing.

    Provides pure domain logic for:
    - Detecting target weight drift
    - Generating rebalancing trades
    - Minimizing transaction costs
    """

    def __init__(self, config: Optional[RebalanceConfig] = None):
        """
        Initialize rebalancer.

        Args:
            config: Rebalancing configuration
        """
        self._config = config or RebalanceConfig()

    def calculate_drift(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, Decimal],
    ) -> Dict[str, Decimal]:
        """
        Calculate current drift from target weights.

        Args:
            portfolio: Current portfolio
            target_weights: Target weights (symbol -> weight 0-1)

        Returns:
            Dictionary of symbol -> drift (positive = overweight, negative = underweight)
        """
        drift = {}
        total_value = portfolio.get_total_value().amount

        if total_value == 0:
            return drift

        for symbol, target_weight in target_weights.items():
            position = portfolio.get_position(symbol)
            if position:
                current_weight = position.get_value().amount / total_value
            else:
                current_weight = Decimal("0")

            # Drift = current - target (in percentage points)
            drift[symbol] = (current_weight - target_weight) * Decimal("100")

        return drift

    def create_rebalance_plan(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, Decimal],
    ) -> RebalancePlan:
        """
        Create rebalancing plan to achieve target weights.

        Args:
            portfolio: Current portfolio
            target_weights: Target weights (symbol -> weight 0-1)

        Returns:
            RebalancePlan with required trades
        """
        total_value = portfolio.get_total_value().amount
        cash = portfolio.get_cash()

        if total_value == 0:
            return RebalancePlan(
                total_value=Decimal("0"),
                cash_available=Decimal("0"),
                trades=[],
                total_drift=Decimal("0"),
                estimated_cost=Decimal("0"),
            )

        # Calculate trades needed
        trades = []
        total_drift = Decimal("0")

        for symbol, target_weight in target_weights.items():
            target_value = total_value * target_weight
            position = portfolio.get_position(symbol)

            if position:
                current_value = position.get_value().amount
                current_qty = position.quantity
                current_price = position.current_price
            else:
                current_value = Decimal("0")
                current_qty = Decimal("0")
                # Need to get price from elsewhere - placeholder
                current_price = Decimal("100")  # Placeholder

            # Calculate drift
            value_diff = target_value - current_value
            drift_pct = (
                (value_diff / total_value * Decimal("100")) if total_value > 0 else Decimal("0")
            )
            total_drift += abs(drift_pct)

            # Skip if within threshold
            if abs(drift_pct) <= self._config.drift_threshold.value:
                continue

            # Calculate trade quantity
            if current_price > 0:
                target_qty = target_value / current_price
                trade_qty = target_qty - current_qty

                # Check minimum trade size
                trade_value = abs(trade_qty * current_price)
                if trade_value < self._config.min_trade_size:
                    continue

                # Calculate average price for validation (handle zero quantity case)
                if current_qty > 0:
                    avg_price = current_value / current_qty
                else:
                    # For new positions, use current market price
                    avg_price = current_price

                trades.append(
                    RebalanceTrade(
                        symbol=symbol,
                        target_quantity=target_qty,
                        current_quantity=current_qty,
                        trade_quantity=trade_qty,
                        target_value=target_value,
                        current_value=current_value,
                        drift_pct=drift_pct,
                        average_price=avg_price,
                    )
                )

        # Estimate costs
        estimated_cost = Decimal(str(len(trades))) * self._config.cost_per_trade

        return RebalancePlan(
            total_value=total_value,
            cash_available=cash,
            trades=trades,
            total_drift=total_drift,
            estimated_cost=estimated_cost,
        )

    def optimize_rebalance_order(
        self,
        trades: List[RebalanceTrade],
    ) -> List[RebalanceTrade]:
        """
        Optimize order of trades for rebalancing.

        Strategy: Sell overweight positions first to raise cash,
        then buy underweight positions.

        Args:
            trades: List of trades to execute

        Returns:
            Optimized trade list
        """
        # Separate sells and buys
        sells = [t for t in trades if t.trade_quantity < 0]
        buys = [t for t in trades if t.trade_quantity > 0]

        # Sort sells by drift (largest drift first - most overweight)
        sells.sort(key=lambda t: t.drift_pct, reverse=True)

        # Sort buys by drift (largest drift first - most underweight)
        buys.sort(key=lambda t: t.drift_pct, reverse=True)

        # Execute sells first, then buys
        return sells + buys

    def validate_rebalance_plan(
        self,
        plan: RebalancePlan,
        portfolio: Portfolio,
    ) -> tuple[bool, List[str]]:
        """
        Validate rebalancing plan.

        Args:
            plan: Rebalancing plan
            portfolio: Current portfolio

        Returns:
            Tuple of (is_valid, warnings/errors)
        """
        issues = []

        # Check cash sufficiency for buys
        buy_value = Decimal("0")
        sell_value = Decimal("0")

        for trade in plan.trades:
            # Use average_price stored during plan creation (handles zero quantity case)
            trade_price = trade.average_price
            if trade.trade_quantity > 0:  # Buy
                buy_value += abs(trade.trade_quantity) * trade_price
            else:  # Sell
                sell_value += abs(trade.trade_quantity) * trade_price

        net_cash_needed = buy_value - sell_value

        if net_cash_needed > plan.cash_available:
            issues.append(
                f"Insufficient cash: need ${net_cash_needed:.2f}, have ${plan.cash_available:.2f}"
            )

        # Check for excessive position sizes
        max_trade_value_pct = self._config.max_trade_size_pct.as_decimal
        max_trade_value = plan.total_value * max_trade_value_pct

        for trade in plan.trades:
            # Use average_price stored during plan creation (handles zero quantity case)
            trade_value = abs(trade.trade_quantity * trade.average_price)
            if trade_value > max_trade_value:
                issues.append(
                    f"Trade for {trade.symbol} exceeds max size: "
                    f"${trade_value:.2f} > ${max_trade_value:.2f}"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_rebalance_summary(self, plan: RebalancePlan) -> Dict[str, str]:
        """
        Get human-readable rebalancing summary.

        Args:
            plan: Rebalancing plan

        Returns:
            Summary dictionary
        """
        num_sells = len([t for t in plan.trades if t.trade_quantity < 0])
        num_buys = len([t for t in plan.trades if t.trade_quantity > 0])

        if plan.total_drift < Decimal("5"):
            action = "No rebalancing needed"
        elif plan.total_drift < Decimal("15"):
            action = "Minor rebalancing recommended"
        elif plan.total_drift < Decimal("30"):
            action = "Moderate rebalancing needed"
        else:
            action = "Significant rebalancing required"

        return {
            "action": action,
            "total_trades": str(len(plan.trades)),
            "sells": str(num_sells),
            "buys": str(num_buys),
            "total_drift": f"{plan.total_drift:.2f}%",
            "estimated_cost": f"${plan.estimated_cost:.2f}",
            "cash_available": f"${plan.cash_available:.2f}",
        }
