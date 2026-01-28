"""
Backtest Entity - Core business object for backtesting operations

This entity represents a backtest with its configuration, execution state,
and results. It contains pure business logic without infrastructure concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ..value_objects.backtest_config import BacktestConfigValue
from ..value_objects.backtest_result import BacktestResultValue


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


@dataclass
class Backtest:
    """
    Backtest entity representing a backtesting operation.

    This is a pure domain entity that maintains business rules
    and invariants for backtesting operations.
    """

    backtest_id: str
    config: BacktestConfigValue
    status: BacktestStatus = BacktestStatus.PENDING
    result: Optional[BacktestResultValue] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate backtest invariants."""
        if not self.backtest_id:
            raise ValueError("Backtest ID cannot be empty")
        if not self.config:
            raise ValueError("Backtest configuration is required")

    def start(self) -> None:
        """Mark backtest as started."""
        if self.status != BacktestStatus.PENDING:
            raise ValueError(f"Cannot start backtest with status {self.status}")
        self.status = BacktestStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result: BacktestResultValue) -> None:
        """
        Mark backtest as completed with results.

        Args:
            result: Backtest results
        """
        if self.status != BacktestStatus.RUNNING:
            raise ValueError(f"Cannot complete backtest with status {self.status}")
        self.status = BacktestStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow()

    def fail(self, error_message: str) -> None:
        """
        Mark backtest as failed.

        Args:
            error_message: Error description
        """
        if self.status == BacktestStatus.COMPLETED:
            raise ValueError("Cannot fail a completed backtest")
        self.status = BacktestStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel backtest."""
        if self.status in (BacktestStatus.COMPLETED, BacktestStatus.FAILED):
            raise ValueError(f"Cannot cancel backtest with status {self.status}")
        self.status = BacktestStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def get_duration(self) -> Optional[float]:
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

    def get_roi(self) -> Optional[Decimal]:
        """
        Get return on investment.

        Returns:
            ROI as decimal or None if no results
        """
        if self.result and self.result.initial_capital and self.result.final_capital:
            return (
                self.result.final_capital - self.result.initial_capital
            ) / self.result.initial_capital
        return None

    def get_sharpe_ratio(self) -> Optional[Decimal]:
        """
        Get Sharpe ratio from results.

        Returns:
            Sharpe ratio or None if no results
        """
        if self.result:
            return self.result.sharpe_ratio
        return None
