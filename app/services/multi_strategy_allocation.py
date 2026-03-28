"""
TASK-PA-1, PA-2, PORT-SEL-1: Multi-Strategy Portfolio Allocation System.

Implements dynamic capital allocation across multiple strategies:
- Momentum (50%)
- Mean Reversion (25%)
- Pairs Trading (25%)

With dynamic rebalancing based on rolling 30-day performance.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class StrategyCapitalAllocation:
    """
    TASK-PA-1: Capital allocation configuration for each strategy.

    Manages target allocations and current allocations per strategy.
    """

    def __init__(
        self,
        strategy_name: str,
        target_weight: Decimal,
        min_weight: Decimal,
        max_weight: Decimal,
    ):
        """
        Initialize strategy allocation.

        Args:
            strategy_name: Name of the strategy
            target_weight: Target weight (0-1)
            min_weight: Minimum allowed weight (0-1)
            max_weight: Maximum allowed weight (0-1)
        """
        self.strategy_name = strategy_name
        self.target_weight = target_weight
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.current_weight = target_weight
        self.allocated_capital = Decimal("0")
        self.performance_data: List[Dict[str, Any]] = []

    def allocate(self, total_capital: Decimal) -> Decimal:
        """
        Calculate allocated capital for this strategy.

        Args:
            total_capital: Total portfolio capital

        Returns:
            Capital allocated to this strategy
        """
        self.allocated_capital = total_capital * self.current_weight
        return self.allocated_capital

    def update_weight(self, new_weight: Decimal) -> None:
        """
        Update current weight, respecting min/max constraints.

        Args:
            new_weight: New weight (0-1)
        """
        # Clamp to min/max bounds
        self.current_weight = max(self.min_weight, min(self.max_weight, new_weight))
        logger.debug(f"{self.strategy_name}: weight updated to {self.current_weight:.2%}")

    def add_performance_data(self, timestamp: datetime, pnl: Decimal, returns: Decimal) -> None:
        """
        Add performance data point.

        Args:
            timestamp: Timestamp of the data point
            pnl: Profit/loss
            returns: Return percentage
        """
        self.performance_data.append(
            {
                "timestamp": timestamp,
                "pnl": pnl,
                "returns": returns,
            }
        )

        # Keep only last 90 days of data
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        self.performance_data = [d for d in self.performance_data if d["timestamp"] >= cutoff_date]

    def calculate_rolling_returns(self, days: int = 30) -> Decimal:
        """
        Calculate rolling returns over specified period.

        Args:
            days: Number of days to look back

        Returns:
            Rolling returns (as decimal)
        """
        if not self.performance_data:
            return Decimal("0")

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_data = [d for d in self.performance_data if d["timestamp"] >= cutoff_date]

        if not recent_data:
            return Decimal("0")

        total_return = sum(d["returns"] for d in recent_data)
        return Decimal(str(total_return))


class MultiStrategyAllocationManager:
    """
    TASK-PA-2: Multi-strategy capital allocation manager.

    Manages capital distribution across multiple strategies based on target allocations.
    """

    def __init__(self, total_capital: Decimal):
        """
        Initialize allocation manager.

        Args:
            total_capital: Total portfolio capital
        """
        self.total_capital = total_capital
        self.strategy_allocations: Dict[str, StrategyCapitalAllocation] = {}

        # TASK-PA-1: Default allocations
        # 50% Momentum, 25% Mean Reversion, 25% Pairs Trading
        self._initialize_default_allocations()

    def _initialize_default_allocations(self) -> None:
        """Initialize default strategy allocations from centralized config."""
        # Get centralized configuration
        config = get_config()
        trading = config.trading

        self.strategy_allocations = {
            "momentum": StrategyCapitalAllocation(
                strategy_name="momentum",
                target_weight=Decimal(str(trading.momentum_target_weight)),
                min_weight=Decimal(str(config.trading.min_allocation_weight)),
                max_weight=Decimal(str(trading.max_momentum_exposure)),
            ),
            "mean_reversion": StrategyCapitalAllocation(
                strategy_name="mean_reversion",
                target_weight=Decimal(str(trading.mean_reversion_target_weight)),
                min_weight=Decimal(str(config.trading.min_allocation_weight)),
                max_weight=Decimal(str(trading.max_mean_reversion_exposure)),
            ),
            "pairs_trading": StrategyCapitalAllocation(
                strategy_name="pairs_trading",
                target_weight=Decimal(str(trading.pairs_trading_target_weight)),
                min_weight=Decimal(str(config.trading.min_allocation_weight)),
                max_weight=Decimal(str(trading.max_pairs_trading_exposure)),
            ),
        }

        logger.info("Initialized default strategy allocations")
        for name, allocation in self.strategy_allocations.items():
            logger.info(
                f"  {name}: {allocation.target_weight:.1%} (range: {allocation.min_weight:.1%} - {allocation.max_weight:.1%})"
            )

    def allocate_capital(self) -> Dict[str, Decimal]:
        """
        Allocate capital to each strategy based on current weights.

        Returns:
            Dictionary mapping strategy names to allocated capital
        """
        allocations = {}

        for name, allocation in self.strategy_allocations.items():
            allocated = allocation.allocate(self.total_capital)
            allocations[name] = allocated
            logger.debug(f"{name}: allocated ${allocated:,.2f} ({allocation.current_weight:.1%})")

        # Normalize allocations to ensure total exactly matches total capital
        # This handles floating-point precision issues
        total_allocated = sum(allocations.values())
        if total_allocated != self.total_capital:
            difference = self.total_capital - total_allocated
            if abs(difference) > Decimal("0"):
                # Add the difference to the largest allocation to minimize relative impact
                if allocations:
                    largest_strategy = max(allocations.keys(), key=lambda k: allocations[k])
                    allocations[largest_strategy] += difference
                    logger.debug(
                        f"Adjusted {largest_strategy} by ${difference:,.2f} "
                        f"to match total capital"
                    )

        return allocations

    def get_allocation_for_strategy(self, strategy_name: str) -> Decimal:
        """
        Get allocated capital for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Allocated capital
        """
        if strategy_name not in self.strategy_allocations:
            logger.warning(f"Strategy '{strategy_name}' not found in allocations")
            return Decimal("0")

        return self.strategy_allocations[strategy_name].allocated_capital

    def update_total_capital(self, new_capital: Decimal) -> None:
        """
        Update total capital and reallocate.

        Args:
            new_capital: New total capital
        """
        self.total_capital = new_capital
        logger.info(f"Total capital updated to ${new_capital:,.2f}")


class DynamicPortfolioSelector:
    """
    TASK-PORT-SEL-1: Dynamic Portfolio Selector.

    Adjusts strategy weights based on rolling 30-day performance.
    """

    def __init__(self, allocation_manager: MultiStrategyAllocationManager):
        """
        Initialize dynamic selector.

        Args:
            allocation_manager: Multi-strategy allocation manager
        """
        self.allocation_manager = allocation_manager
        self.rebalance_threshold = Decimal("0.05")  # 5% drift threshold

    def update_strategy_performance(
        self,
        strategy_name: str,
        timestamp: datetime,
        pnl: Decimal,
        returns: Decimal,
    ) -> None:
        """
        Update performance data for a strategy.

        Args:
            strategy_name: Name of the strategy
            timestamp: Timestamp of the performance data
            pnl: Profit/loss
            returns: Return percentage
        """
        if strategy_name not in self.allocation_manager.strategy_allocations:
            logger.warning(f"Strategy '{strategy_name}' not found")
            return

        allocation = self.allocation_manager.strategy_allocations[strategy_name]
        allocation.add_performance_data(timestamp, pnl, returns)

    def rebalance_allocations(self) -> Dict[str, Decimal]:
        """
        Rebalance allocations based on rolling 30-day performance.

        Returns:
            Dictionary of adjusted allocations
        """
        logger.info("Rebalancing allocations based on performance...")

        # Calculate rolling 30-day returns for each strategy
        rolling_returns = {}
        total_return = Decimal("0")

        for name, allocation in self.allocation_manager.strategy_allocations.items():
            rolling_return = allocation.calculate_rolling_returns(days=30)
            rolling_returns[name] = rolling_return
            total_return += rolling_return

        # If no returns, use target weights
        if total_return == 0 or not rolling_returns:
            logger.info("No performance data available, using target weights")
            return self.allocation_manager.allocate_capital()

        # Calculate adjusted weights based on performance
        new_allocations = {}

        for name, allocation in self.allocation_manager.strategy_allocations.items():
            performance_factor = rolling_returns.get(name, Decimal("0"))

            # Better performers get higher weight (normalize to avoid negative)
            if performance_factor > Decimal("0"):
                # Scale performance factor (0 to 1.5x target weight)
                adjustment = (performance_factor / total_return) * Decimal("1.5")
                new_weight = allocation.target_weight * adjustment
            else:
                # Underperformers get lower weight
                adjustment = (
                    max(Decimal("0.5"), total_return / Decimal("0.01"))
                    if total_return > 0
                    else Decimal("0.5")
                )
                new_weight = allocation.target_weight * adjustment

            # Update weight
            allocation.update_weight(new_weight)
            new_allocations[name] = allocation.allocated_capital

        # Normalize allocations to ensure total = 1.0
        total_weight = sum(
            a.current_weight for a in self.allocation_manager.strategy_allocations.values()
        )
        if total_weight > 0:
            normalization_factor = Decimal("1") / total_weight
            for allocation in self.allocation_manager.strategy_allocations.values():
                allocation.current_weight *= normalization_factor

        # Reallocate with normalized weights
        final_allocations = self.allocation_manager.allocate_capital()

        # Fix precision errors: ensure total exactly matches total capital
        allocated_total = sum(final_allocations.values())
        total_capital = self.allocation_manager.total_capital
        difference = total_capital - allocated_total

        # Distribute any difference to the largest allocation (rounding fix)
        if abs(difference) > Decimal("0.01"):
            # Find strategy with largest allocation
            largest_strategy = max(final_allocations.keys(), key=lambda k: final_allocations[k])
            final_allocations[largest_strategy] += difference
        elif abs(difference) > Decimal("0") and abs(difference) <= Decimal("0.01"):
            # Small rounding error: round each allocation to nearest cent
            rounded_allocations = {}
            running_total = Decimal("0")
            strategies = list(final_allocations.keys())
            for _i, strategy in enumerate(strategies[:-1]):
                rounded_value = final_allocations[strategy].quantize(Decimal("0.01"))
                rounded_allocations[strategy] = rounded_value
                running_total += rounded_value
            # Last strategy gets the remainder to ensure exact total
            rounded_allocations[strategies[-1]] = total_capital - running_total
            final_allocations = rounded_allocations

        logger.info("Rebalancing complete:")
        for name, allocated in final_allocations.items():
            logger.info(f"  {name}: ${allocated:,.2f}")

        return final_allocations

    def should_rebalance(self) -> bool:
        """
        Check if rebalancing is needed based on drift threshold.

        Returns:
            True if rebalancing should occur
        """
        current_weights = {
            name: alloc.current_weight
            for name, alloc in self.allocation_manager.strategy_allocations.items()
        }

        target_weights = {
            name: alloc.target_weight
            for name, alloc in self.allocation_manager.strategy_allocations.items()
        }

        # Check if any strategy has drifted significantly from target
        for name in current_weights:
            drift = abs(current_weights[name] - target_weights[name])
            if drift > self.rebalance_threshold:
                logger.debug(
                    f"{name}: drift of {drift:.2%} exceeds threshold {self.rebalance_threshold:.2%}"
                )
                return True

        return False


# Global manager instance
_multi_strategy_manager: Optional[MultiStrategyAllocationManager] = None
_dynamic_selector: Optional[DynamicPortfolioSelector] = None


def get_multi_strategy_manager(
    total_capital: Optional[Decimal] = None,
) -> MultiStrategyAllocationManager:
    """Get global multi-strategy allocation manager."""
    if total_capital is None:
        total_capital = Decimal("100000")
    global _multi_strategy_manager
    if _multi_strategy_manager is None:
        # Pass the required total_capital argument to constructor
        _multi_strategy_manager = MultiStrategyAllocationManager(total_capital)

    return _multi_strategy_manager


def get_dynamic_selector() -> DynamicPortfolioSelector:
    """Get global dynamic portfolio selector."""
    global _dynamic_selector
    if _dynamic_selector is None:
        manager = get_multi_strategy_manager()
        _dynamic_selector = DynamicPortfolioSelector(manager)

    return _dynamic_selector
