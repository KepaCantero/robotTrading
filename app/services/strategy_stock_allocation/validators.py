"""
Validation modules for stock allocation.

Provides validation for allocation results ensuring
capital totals, limits, and constraints are satisfied.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.core.centralized_config import StockAllocationSettings

logger = logging.getLogger(__name__)


# Data model for type checking
class StockMetrics(BaseModel):
    """Metrics for a single stock."""

    ticker: str
    strategy: str | None = None
    weight: float = 0.0
    capital: float = 0.0
    sps_score: float = 0.0
    sortino_ratio: float | None = None
    h_long: float | None = None
    h_short: float | None = None
    half_life_tau: float | None = None
    garch_volatility: float | None = None
    decision_log: str = ""


class AllocationValidator:
    """
    Validates final allocation results.

    Checks:
    - Capital total assigned = capital initial
    - No limits exceeded
    - Cointegration and half-life validated
    - No strategy overlap
    """

    def __init__(self, config: StockAllocationSettings) -> None:
        """
        Initialize allocation validator.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def validate(
        self,
        allocations: dict[str, StockMetrics],
        total_capital: float,
        strategy_allocations: dict[str, float],
    ) -> tuple[bool, list[str]]:
        """
        Validate final allocation.

        Args:
            allocations: Dictionary of allocations
            total_capital: Total capital
            strategy_allocations: Strategy-level allocations

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        try:
            # Check total capital
            allocated_total = sum(alloc.capital for alloc in allocations.values())
            capital_diff = abs(allocated_total - total_capital)

            if capital_diff > 0.01:
                errors.append(
                    f"Capital mismatch: allocated ${allocated_total:,.2f} != total ${total_capital:,.2f}"
                )

            # Check individual limits
            for ticker, alloc in allocations.items():
                if alloc.weight > self.config.MAX_STRATEGY_EXPOSURE:
                    errors.append(
                        f"{ticker}: Weight {alloc.weight:.4f} > max {self.config.MAX_STRATEGY_EXPOSURE}"
                    )

                # Check half-life if mean reversion
                if alloc.strategy == "mean_reversion" and alloc.half_life_tau is not None:
                    if alloc.half_life_tau > self.config.MAX_HALF_LIFE_DAYS:
                        errors.append(
                            f"{ticker}: Half-life {alloc.half_life_tau:.2f} > max {self.config.MAX_HALF_LIFE_DAYS}"
                        )

            # Check strategy exposure limits
            strategy_totals = defaultdict(float)
            for alloc in allocations.values():
                if alloc.strategy:
                    strategy_totals[alloc.strategy] += alloc.weight

            tolerance = 0.0001
            for strategy, total_weight in strategy_totals.items():
                if total_weight > self.config.MAX_STRATEGY_EXPOSURE + tolerance:
                    errors.append(
                        f"{strategy}: Total exposure {total_weight:.4f} > max {self.config.MAX_STRATEGY_EXPOSURE}"
                    )

            # Check for strategy overlap
            ticker_strategies = defaultdict(set)
            for alloc in allocations.values():
                if alloc.strategy:
                    ticker_strategies[alloc.ticker].add(alloc.strategy)

            for ticker, strategies in ticker_strategies.items():
                if len(strategies) > 1:
                    errors.append(f"{ticker}: Assigned to multiple strategies: {strategies}")

            is_valid = len(errors) == 0

            if is_valid:
                logger.info("✅ Allocation validation passed")
            else:
                logger.warning(f"❌ Allocation validation failed: {len(errors)} errors")
                for error in errors[:10]:
                    logger.warning(f"  - {error}")

            return is_valid, errors

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error validating allocation: {e}", exc_info=True)
            return False, [f"Validation error: {str(e)}"]
