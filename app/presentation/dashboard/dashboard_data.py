"""
Dashboard data models.

Defines the data structures used by the dashboard to display
trading information.

NOTE: For canonical PerformanceMetrics, use app.backtesting.models.PerformanceMetrics
This module contains DashboardPerformanceMetrics which is dashboard-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class PositionSummary:
    """Summary of a single position."""

    symbol: str
    quantity: int
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float
    side: str  # "long" or "short"

    def to_display_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_price": float(self.avg_price),
            "current_price": float(self.current_price),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "side": self.side,
        }


@dataclass
class DashboardPerformanceMetrics:
    """
    Dashboard-specific performance metrics.

    This is a simplified dataclass for dashboard display purposes.
    For comprehensive backtesting metrics, use the canonical
    app.backtesting.models.PerformanceMetrics instead.
    """

    total_pnl: Decimal
    daily_pnl: Decimal
    daily_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float | None = None
    portfolio_value: Decimal = Decimal("0")
    starting_capital: Decimal = Decimal("0")

    def to_display_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "total_pnl": float(self.total_pnl),
            "daily_pnl": float(self.daily_pnl),
            "daily_return_pct": self.daily_return_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "portfolio_value": float(self.portfolio_value),
            "starting_capital": float(self.starting_capital),
        }


# Backward compatibility alias - use DashboardPerformanceMetrics instead
PerformanceMetrics = DashboardPerformanceMetrics


@dataclass
class SystemStatus:
    """System health status."""

    kill_switch_active: bool
    systems_available: int
    systems_total: int
    slo_compliance_rate: float
    last_update: datetime
    bridge_status: str
    active_orders: int

    def to_display_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "kill_switch_active": self.kill_switch_active,
            "systems_available": self.systems_available,
            "systems_total": self.systems_total,
            "slo_compliance_rate": self.slo_compliance_rate,
            "last_update": self.last_update.isoformat(),
            "bridge_status": self.bridge_status,
            "active_orders": self.active_orders,
        }


@dataclass
class DashboardSnapshot:
    """Complete dashboard snapshot."""

    timestamp: datetime
    performance: PerformanceMetrics
    positions: list[PositionSummary]
    system_status: SystemStatus
    recent_alerts: list[dict[str, Any]] = field(default_factory=list)

    def to_display_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "performance": self.performance.to_display_dict(),
            "positions": [p.to_display_dict() for p in self.positions],
            "system_status": self.system_status.to_display_dict(),
            "recent_alerts": self.recent_alerts,
        }
