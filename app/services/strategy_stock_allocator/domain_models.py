"""
Domain Models for Strategy Stock Allocation

This module contains pure domain models for stock allocation,
following Clean Architecture principles with no infrastructure dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Types of trading strategies."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"


class StockCategory(Enum):
    """Stock classification categories."""

    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    RANDOM_WALK = "random_walk"


@dataclass(frozen=True)
class StockMetrics:
    """
    Metrics for a single stock.

    This is a pure domain value object with no external dependencies.
    """

    ticker: str
    strategy: StrategyType | None = None
    weight: Decimal = Decimal("0")
    capital: Decimal = Decimal("0")
    sps_score: Decimal = Decimal("0")  # Strategy Preference Score
    sortino_ratio: Decimal | None = None
    h_long: Decimal | None = None  # Long memory Hurst exponent
    h_short: Decimal | None = None  # Short memory Hurst exponent
    half_life_tau: Decimal | None = None  # Mean reversion half-life
    garch_volatility: Decimal | None = None
    category: StockCategory | None = None
    decision_log: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        logger.debug(
            "Converting StockMetrics to dict",
            extra={
                "ticker": self.ticker,
                "strategy": self.strategy.value if self.strategy else None,
            },
        )
        return {
            "ticker": self.ticker,
            "strategy": self.strategy.value if self.strategy else None,
            "weight": float(self.weight),
            "capital": float(self.capital),
            "sps_score": float(self.sps_score),
            "sortino_ratio": float(self.sortino_ratio) if self.sortino_ratio else None,
            "h_long": float(self.h_long) if self.h_long else None,
            "h_short": float(self.h_short) if self.h_short else None,
            "half_life_tau": float(self.half_life_tau) if self.half_life_tau else None,
            "garch_volatility": float(self.garch_volatility) if self.garch_volatility else None,
            "category": self.category.value if self.category else None,
            "decision_log": self.decision_log,
        }


@dataclass(frozen=True)
class PairMetrics:
    """
    Metrics for a trading pair.

    Pure domain value object for pairs trading.
    """

    ticker1: str
    ticker2: str
    cointegration_score: Decimal
    correlation: Decimal
    half_life_tau: Decimal | None = None
    hedge_ratio: Decimal | None = None
    decision_log: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        logger.debug(
            "Converting PairMetrics to dict",
            extra={"ticker1": self.ticker1, "ticker2": self.ticker2},
        )
        return {
            "ticker1": self.ticker1,
            "ticker2": self.ticker2,
            "cointegration_score": float(self.cointegration_score),
            "correlation": float(self.correlation),
            "half_life_tau": float(self.half_life_tau) if self.half_life_tau else None,
            "hedge_ratio": float(self.hedge_ratio) if self.hedge_ratio else None,
            "decision_log": self.decision_log,
        }


@dataclass(frozen=True)
class AllocationResult:
    """
    Result of stock allocation operation.

    Pure domain entity representing allocation outcomes.
    """

    allocations: dict[str, StockMetrics] = field(default_factory=dict)
    pairs: list[PairMetrics] = field(default_factory=list)
    residual_capital: Decimal | None = None
    decision_logs: list[str] = field(default_factory=list)
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def get_total_allocated_capital(self) -> Decimal:
        """Calculate total allocated capital."""
        total = sum(m.capital for m in self.allocations.values())
        logger.debug(
            "Calculated total allocated capital",
            extra={"total_capital": float(total), "allocations_count": len(self.allocations)},
        )
        return total

    def get_allocation_count(self) -> int:
        """Get number of allocated stocks."""
        count = len(self.allocations)
        logger.debug("Retrieved allocation count", extra={"count": count})
        return count

    def get_pairs_count(self) -> int:
        """Get number of trading pairs."""
        count = len(self.pairs)
        logger.debug("Retrieved pairs count", extra={"count": count})
        return count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        logger.debug(
            "Converting AllocationResult to dict",
            extra={
                "allocations_count": len(self.allocations),
                "pairs_count": len(self.pairs),
                "validation_passed": self.validation_passed,
            },
        )
        return {
            "allocations": {
                ticker: metrics.to_dict() for ticker, metrics in self.allocations.items()
            },
            "pairs": [pair.to_dict() for pair in self.pairs],
            "residual_capital": float(self.residual_capital),
            "decision_logs": self.decision_logs,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "total_allocated_capital": float(self.get_total_allocated_capital()),
            "allocation_count": self.get_allocation_count(),
            "pairs_count": self.get_pairs_count(),
        }


class AllocationConfig:
    """
    Configuration for stock allocation.

    Pure domain value object for allocation parameters.
    """

    def __init__(
        self,
        initial_capital: Decimal,
        max_positions: int = 10,
        max_position_size: Decimal | None = None,
        min_position_size: Decimal | None = None,
        reserve_ratio: Decimal | None = None,
    ):
        """
        Initialize allocation configuration.

        Args:
            initial_capital: Total capital to allocate
            max_positions: Maximum number of positions
            max_position_size: Maximum size of any position (as decimal)
            min_position_size: Minimum size of any position (as decimal)
            reserve_ratio: Ratio of capital to keep in reserve
        """
        if max_position_size is None:
            max_position_size = Decimal("0.10")
        if min_position_size is None:
            min_position_size = Decimal("0.05")
        if reserve_ratio is None:
            reserve_ratio = Decimal("0.10")
        logger.debug(
            "Initializing AllocationConfig",
            extra={
                "initial_capital": float(initial_capital),
                "max_positions": max_positions,
                "max_position_size": float(max_position_size),
                "min_position_size": float(min_position_size),
                "reserve_ratio": float(reserve_ratio),
            },
        )
        if initial_capital <= 0:
            logger.error(
                "AllocationConfig validation failed - invalid initial_capital",
                extra={"initial_capital": float(initial_capital)},
            )
            raise ValueError("Initial capital must be positive")
        if max_positions <= 0:
            logger.error(
                "AllocationConfig validation failed - invalid max_positions",
                extra={"max_positions": max_positions},
            )
            raise ValueError("Max positions must be positive")
        if max_position_size <= 0 or max_position_size > 1:
            logger.error(
                "AllocationConfig validation failed - invalid max_position_size",
                extra={"max_position_size": float(max_position_size)},
            )
            raise ValueError("Max position size must be between 0 and 1")
        if min_position_size <= 0 or min_position_size > max_position_size:
            logger.error(
                "AllocationConfig validation failed - invalid min_position_size",
                extra={
                    "min_position_size": float(min_position_size),
                    "max_position_size": float(max_position_size),
                },
            )
            raise ValueError("Min position size must be positive and <= max position size")
        if reserve_ratio < 0 or reserve_ratio >= 1:
            logger.error(
                "AllocationConfig validation failed - invalid reserve_ratio",
                extra={"reserve_ratio": float(reserve_ratio)},
            )
            raise ValueError("Reserve ratio must be between 0 and 1")

        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.reserve_ratio = reserve_ratio
        logger.info(
            "AllocationConfig initialized successfully",
            extra={
                "initial_capital": float(initial_capital),
                "allocatable_capital": float(self.get_allocatable_capital()),
            },
        )

    def get_reservable_capital(self) -> Decimal:
        """Calculate capital to keep in reserve."""
        reserve = self.initial_capital * self.reserve_ratio
        logger.debug("Calculated reservable capital", extra={"reservable_capital": float(reserve)})
        return reserve

    def get_allocatable_capital(self) -> Decimal:
        """Calculate capital available for allocation."""
        allocatable = self.initial_capital - self.get_reservable_capital()
        logger.debug(
            "Calculated allocatable capital", extra={"allocatable_capital": float(allocatable)}
        )
        return allocatable

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        logger.debug("Converting AllocationConfig to dict")
        return {
            "initial_capital": float(self.initial_capital),
            "max_positions": self.max_positions,
            "max_position_size": float(self.max_position_size),
            "min_position_size": float(self.min_position_size),
            "reserve_ratio": float(self.reserve_ratio),
            "allocatable_capital": float(self.get_allocatable_capital()),
            "reservable_capital": float(self.get_reservable_capital()),
        }
