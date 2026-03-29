"""
BacktestResult Value Object - Results from backtesting operations

This value object encapsulates all results from a backtest execution.
It's immutable and contains performance metrics and statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BacktestResultValue:
    """
    Backtest result value object.

    Contains all performance metrics and statistics from a backtest.
    """

    # Basic metrics
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    total_return_pct: Decimal

    # Risk metrics
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    max_drawdown: Decimal | None = None
    volatility: Decimal | None = None
    var_95: Decimal | None = None

    # Trading metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal | None = None
    avg_win: Decimal | None = None
    avg_loss: Decimal | None = None
    profit_factor: Decimal | None = None

    # Trade level metrics
    avg_trade_duration: Decimal | None = None
    avg_hold_time: Decimal | None = None

    # Advanced metrics
    calmar_ratio: Decimal | None = None
    omega_ratio: Decimal | None = None
    tail_ratio: Decimal | None = None

    # Regression metrics
    hit_rate: Decimal | None = None
    precision: Decimal | None = None
    recall: Decimal | None = None
    f1_score: Decimal | None = None

    # Additional statistics
    additional_stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate result invariants."""
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        if self.total_trades < 0:
            raise ValueError("Total trades cannot be negative")

        if self.winning_trades < 0:
            raise ValueError("Winning trades cannot be negative")

        if self.losing_trades < 0:
            raise ValueError("Losing trades cannot be negative")

        if self.winning_trades + self.losing_trades > self.total_trades:
            raise ValueError("Sum of winning and losing trades cannot exceed total trades")

    @property
    def roi(self) -> Decimal:
        """Get return on investment."""
        return self.total_return

    @property
    def is_profitable(self) -> bool:
        """Check if backtest was profitable."""
        return self.total_return > 0

    def has_acceptable_drawdown(self, threshold: Decimal | None = None) -> bool:
        """
        Check if drawdown is within acceptable threshold.

        Args:
            threshold: Maximum acceptable drawdown (default 20%)

        Returns:
            True if drawdown is acceptable
        """
        if threshold is None:
            threshold = Decimal("0.20")
        if self.max_drawdown is None:
            return True
        return abs(self.max_drawdown) <= threshold

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary.

        Returns:
            Result dictionary
        """
        return {
            "initial_capital": str(self.initial_capital),
            "final_capital": str(self.final_capital),
            "total_return": str(self.total_return),
            "total_return_pct": str(self.total_return_pct),
            "sharpe_ratio": str(self.sharpe_ratio) if self.sharpe_ratio else None,
            "sortino_ratio": str(self.sortino_ratio) if self.sortino_ratio else None,
            "max_drawdown": str(self.max_drawdown) if self.max_drawdown else None,
            "volatility": str(self.volatility) if self.volatility else None,
            "var_95": str(self.var_95) if self.var_95 else None,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": str(self.win_rate) if self.win_rate else None,
            "avg_win": str(self.avg_win) if self.avg_win else None,
            "avg_loss": str(self.avg_loss) if self.avg_loss else None,
            "profit_factor": str(self.profit_factor) if self.profit_factor else None,
            "avg_trade_duration": str(self.avg_trade_duration) if self.avg_trade_duration else None,
            "avg_hold_time": str(self.avg_hold_time) if self.avg_hold_time else None,
            "calmar_ratio": str(self.calmar_ratio) if self.calmar_ratio else None,
            "omega_ratio": str(self.omega_ratio) if self.omega_ratio else None,
            "tail_ratio": str(self.tail_ratio) if self.tail_ratio else None,
            "hit_rate": str(self.hit_rate) if self.hit_rate else None,
            "precision": str(self.precision) if self.precision else None,
            "recall": str(self.recall) if self.recall else None,
            "f1_score": str(self.f1_score) if self.f1_score else None,
            "additional_stats": self.additional_stats,
        }
