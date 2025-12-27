"""
TASK-REB-1 and REB-2: Portfolio Rebalancing System.

Implements:
- Monthly rebalancing to maintain target allocations (TASK-REB-1)
- Dynamic capital adjustments for strategies with negative streaks (TASK-REB-2)
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RebalancingTarget:
    """
    TASK-REB-1: Rebalancing target configuration.

    Defines target allocations for strategies.
    """

    def __init__(self, strategy_name: str, target_weight: Decimal):
        """
        Initialize rebalancing target.

        Args:
            strategy_name: Name of the strategy
            target_weight: Target weight (0-1)
        """
        self.strategy_name = strategy_name
        self.target_weight = target_weight
        self.last_rebalance: Optional[datetime] = None

    def needs_rebalance(self, rebalance_frequency_days: int = 30) -> bool:
        """
        Check if rebalancing is needed based on frequency.

        Args:
            rebalance_frequency_days: Days between rebalances (default 30)

        Returns:
            True if rebalancing is needed
        """
        if self.last_rebalance is None:
            return True

        days_since_rebalance = (datetime.utcnow() - self.last_rebalance).days
        return days_since_rebalance >= rebalance_frequency_days

    def update_last_rebalance(self) -> None:
        """Update last rebalance timestamp."""
        self.last_rebalance = datetime.utcnow()


class DynamicCapitalAdjuster:
    """
    TASK-REB-2: Dynamic Capital Adjuster.

    Reduces capital allocation to strategies with negative performance streaks.
    """

    def __init__(
        self,
        min_allocation: Decimal = Decimal("0.10"),  # 10% minimum
        max_allocation: Decimal = Decimal("0.70"),  # 70% maximum
        adjustment_factor: Decimal = Decimal("0.20"),  # 20% reduction per streak
    ):
        """
        Initialize capital adjuster.

        Args:
            min_allocation: Minimum allocation ratio (0-1)
            max_allocation: Maximum allocation ratio (0-1)
            adjustment_factor: Reduction factor per negative streak (0-1)
        """
        self.min_allocation = min_allocation
        self.max_allocation = max_allocation
        self.adjustment_factor = adjustment_factor

    def calculate_adjusted_weight(
        self,
        target_weight: Decimal,
        consecutive_losses: int,
        recent_performance: Decimal,  # Negative for losses, positive for gains
    ) -> Decimal:
        """
        Calculate adjusted weight based on performance.

        Args:
            target_weight: Target weight
            consecutive_losses: Number of consecutive losses
            recent_performance: Recent performance metric

        Returns:
            Adjusted weight
        """
        adjusted = target_weight

        # Reduce weight based on consecutive losses
        if consecutive_losses > 0:
            reduction = min(
                self.adjustment_factor * consecutive_losses, Decimal("0.50")  # Max 50% reduction
            )
            adjusted = adjusted * (Decimal("1") - reduction)

        # Further reduce based on poor recent performance
        if recent_performance < Decimal("-0.10"):  # Worse than -10%
            adjusted = adjusted * Decimal("0.80")  # Reduce by 20%
        elif recent_performance < Decimal("-0.05"):  # Worse than -5%
            adjusted = adjusted * Decimal("0.90")  # Reduce by 10%

        # Enforce bounds
        adjusted = max(self.min_allocation, min(self.max_allocation, adjusted))

        return adjusted

    def should_reduce_allocation(
        self,
        consecutive_losses: int,
        recent_performance: Decimal,
        threshold_losses: int = 3,
    ) -> bool:
        """
        Determine if allocation should be reduced.

        Args:
            consecutive_losses: Number of consecutive losses
            recent_performance: Recent performance metric
            threshold_losses: Threshold for consecutive losses

        Returns:
            True if allocation should be reduced
        """
        # Reduce if too many consecutive losses
        if consecutive_losses >= threshold_losses:
            return True

        # Reduce if very poor recent performance
        if recent_performance < Decimal("-0.15"):  # Worse than -15%
            return True

        return False


class PortfolioRebalancer:
    """
    TASK-REB-1: Monthly Rebalancer.

    Maintains target allocations through periodic rebalancing.
    """

    def __init__(
        self,
        rebalance_frequency_days: int = 30,
        drift_threshold: Decimal = Decimal("0.05"),  # 5% drift
    ):
        """
        Initialize rebalancer.

        Args:
            rebalance_frequency_days: Days between rebalances (default 30)
            drift_threshold: Allowed drift from target (default 5%)
        """
        self.rebalance_frequency_days = rebalance_frequency_days
        self.drift_threshold = drift_threshold
        self.rebalancing_targets: Dict[str, RebalancingTarget] = {}
        self.capital_adjuster = DynamicCapitalAdjuster()

    def set_target_allocation(self, strategy_name: str, target_weight: Decimal) -> None:
        """
        Set target allocation for a strategy.

        Args:
            strategy_name: Name of the strategy
            target_weight: Target weight (0-1)
        """
        self.rebalancing_targets[strategy_name] = RebalancingTarget(strategy_name, target_weight)
        logger.info(f"Set target allocation for {strategy_name}: {target_weight:.1%}")

    def calculate_rebalance_needs(
        self,
        current_allocations: Dict[str, Decimal],
        portfolio_value: Decimal,
    ) -> Dict[str, Decimal]:
        """
        Calculate rebalancing needs.

        Args:
            current_allocations: Current allocation per strategy
            portfolio_value: Total portfolio value

        Returns:
            Dictionary of rebalancing adjustments needed
        """
        rebalance_needs = {}
        total_current = sum(current_allocations.values())

        for strategy_name, target in self.rebalancing_targets.items():
            current = current_allocations.get(strategy_name, Decimal("0"))

            # Calculate target value
            target_value = portfolio_value * target.target_weight

            # Check drift
            if total_current > 0:
                current_weight = current / total_current
                drift = abs(current_weight - target.target_weight)

                if drift > self.drift_threshold or target.needs_rebalance():
                    rebalance_needs[strategy_name] = target_value - current

        return rebalance_needs

    def apply_rebalancing(
        self,
        current_allocations: Dict[str, Decimal],
        portfolio_value: Decimal,
        strategy_performance: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Decimal]:
        """
        Apply rebalancing with dynamic capital adjustments.

        Args:
            current_allocations: Current allocation per strategy
            portfolio_value: Total portfolio value
            strategy_performance: Performance data per strategy

        Returns:
            New target allocations
        """
        adjusted_allocations = {}

        logger.info("Applying rebalancing with dynamic capital adjustments...")

        for strategy_name, target in self.rebalancing_targets.items():
            # Get strategy performance
            perf_data = strategy_performance.get(strategy_name, {})
            consecutive_losses = perf_data.get("consecutive_losses", 0)
            recent_perf = perf_data.get("recent_performance", Decimal("0"))

            # Calculate adjusted weight based on performance
            adjusted_weight = self.capital_adjuster.calculate_adjusted_weight(
                target.target_weight, consecutive_losses, recent_perf
            )

            # Calculate target allocation
            target_allocation = portfolio_value * adjusted_weight
            adjusted_allocations[strategy_name] = target_allocation

            # Check if rebalancing needed
            current_allocation = current_allocations.get(strategy_name, Decimal("0"))
            drift = (
                abs(current_allocation - target_allocation) / portfolio_value
                if portfolio_value > 0
                else Decimal("0")
            )

            if drift > self.drift_threshold or target.needs_rebalance():
                logger.info(
                    f"{strategy_name}: rebalancing {current_allocation:.2f} -> {target_allocation:.2f} "
                    f"(weight: {target.target_weight:.1%} -> {adjusted_weight:.1%})"
                )
                target.update_last_rebalance()

        return adjusted_allocations

    def get_rebalance_status(self) -> Dict[str, Any]:
        """
        Get current rebalancing status.

        Returns:
            Status information
        """
        status = {}
        for name, target in self.rebalancing_targets.items():
            status[name] = {
                "target_weight": float(target.target_weight),
                "days_since_rebalance": (
                    (datetime.utcnow() - target.last_rebalance).days
                    if target.last_rebalance
                    else None
                ),
                "needs_rebalance": target.needs_rebalance(),
            }
        return status


# Global rebalancer instance
_portfolio_rebalancer: Optional[PortfolioRebalancer] = None


def get_portfolio_rebalancer() -> PortfolioRebalancer:
    """Get global portfolio rebalancer instance."""
    global _portfolio_rebalancer
    if _portfolio_rebalancer is None:
        _portfolio_rebalancer = PortfolioRebalancer()

    return _portfolio_rebalancer
