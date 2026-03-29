"""
Backtest Entity - Core business object for backtesting operations

This entity represents a backtest with its configuration, execution state,
and results. It contains pure business logic without infrastructure concerns.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from ..value_objects.backtest_config import BacktestConfigValue
    from ..value_objects.backtest_result import BacktestResultValue

logger = logging.getLogger(__name__)


class BacktestStatus(Enum):
    """Backtest execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BacktestType(Enum):
    """Types of backtests supported."""

    BASELINE = "baseline"
    LEARNING_ENGINES = "learning_engines"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    TRANSFORMER_OPTIMIZATION = "transformer_optimization"
    ABLATION = "ablation"
    GRID_SEARCH = "grid_search"
    OUT_OF_SAMPLE = "out_of_sample"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_TEST = "regime_test"


@dataclass(frozen=True)
class Backtest:
    """
    Backtest entity representing a backtesting operation.

    This is a pure domain entity that maintains business rules
    and invariants for backtesting operations.

    State transitions are managed through factory methods that return new instances.
    """

    backtest_id: str
    config: BacktestConfigValue
    status: BacktestStatus = BacktestStatus.PENDING
    result: BacktestResultValue | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        """Validate backtest invariants."""
        if not self.backtest_id:
            raise ValueError("Backtest ID cannot be empty")
        if not self.config:
            raise ValueError("Backtest configuration is required")

    def start(self) -> Backtest:
        """
        Mark backtest as started.

        Returns:
            New Backtest instance with RUNNING status

        Raises:
            ValueError: If backtest is not in PENDING status
        """
        if self.status != BacktestStatus.PENDING:
            raise ValueError(f"Cannot start backtest with status {self.status}")

        logger.info(
            "Starting backtest",
            extra={
                "backtest_id": self.backtest_id,
                "previous_status": self.status.value,
                "new_status": BacktestStatus.RUNNING.value,
            },
        )

        return dataclasses.replace(
            self,
            status=BacktestStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

    def complete(self, result: BacktestResultValue) -> Backtest:
        """
        Mark backtest as completed with results.

        Args:
            result: Backtest results

        Returns:
            New Backtest instance with COMPLETED status and results

        Raises:
            ValueError: If backtest is not in RUNNING status
        """
        if self.status != BacktestStatus.RUNNING:
            raise ValueError(f"Cannot complete backtest with status {self.status}")

        logger.info(
            "Completing backtest",
            extra={
                "backtest_id": self.backtest_id,
                "previous_status": self.status.value,
                "new_status": BacktestStatus.COMPLETED.value,
                "sharpe_ratio": str(result.sharpe_ratio) if result.sharpe_ratio else None,
            },
        )

        return dataclasses.replace(
            self,
            status=BacktestStatus.COMPLETED,
            result=result,
            completed_at=datetime.now(timezone.utc),
        )

    def fail(self, error_message: str) -> Backtest:
        """
        Mark backtest as failed.

        Args:
            error_message: Error description

        Returns:
            New Backtest instance with FAILED status

        Raises:
            ValueError: If backtest is already COMPLETED
        """
        if self.status == BacktestStatus.COMPLETED:
            raise ValueError("Cannot fail a completed backtest")

        logger.warning(
            "Backtest failed",
            extra={
                "backtest_id": self.backtest_id,
                "previous_status": self.status.value,
                "new_status": BacktestStatus.FAILED.value,
                "error_message": error_message,
            },
        )

        return dataclasses.replace(
            self,
            status=BacktestStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> Backtest:
        """
        Cancel backtest.

        Returns:
            New Backtest instance with CANCELLED status

        Raises:
            ValueError: If backtest is already COMPLETED or FAILED
        """
        if self.status in (BacktestStatus.COMPLETED, BacktestStatus.FAILED):
            raise ValueError(f"Cannot cancel backtest with status {self.status}")

        logger.info(
            "Cancelling backtest",
            extra={
                "backtest_id": self.backtest_id,
                "previous_status": self.status.value,
                "new_status": BacktestStatus.CANCELLED.value,
            },
        )

        return dataclasses.replace(
            self,
            status=BacktestStatus.CANCELLED,
            completed_at=datetime.now(timezone.utc),
        )

    def get_duration(self) -> float | None:
        """
        Get backtest execution duration in seconds.

        Returns:
            Duration in seconds or None if not completed
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def is_running(self) -> bool:
        """Check if backtest is currently running."""
        return self.status == BacktestStatus.RUNNING

    def is_completed(self) -> bool:
        """Check if backtest is completed."""
        return self.status == BacktestStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if backtest failed."""
        return self.status == BacktestStatus.FAILED

    def get_roi(self) -> Decimal | None:
        """
        Get return on investment.

        Returns:
            ROI as decimal or None if no results or initial_capital is zero

        Raises:
            ValueError: If initial_capital is zero or negative
        """
        if self.result and self.result.initial_capital and self.result.final_capital:
            if self.result.initial_capital <= 0:
                raise ValueError(
                    f"initial_capital must be positive, got {self.result.initial_capital}"
                )
            return (
                self.result.final_capital - self.result.initial_capital
            ) / self.result.initial_capital
        return None

    def get_sharpe_ratio(self) -> Decimal | None:
        """
        Get Sharpe ratio from results.

        Returns:
            Sharpe ratio or None if no results
        """
        if self.result:
            return self.result.sharpe_ratio
        return None
