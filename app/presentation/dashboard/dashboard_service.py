"""
Dashboard service for collecting and aggregating trading data.

Provides methods to fetch current positions, performance metrics,
and system status for dashboard display.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)

from app.domain.services.compliance.compliance_engine import get_compliance_engine
from app.presentation.dashboard.dashboard_data import (
    DashboardPerformanceMetrics,
    DashboardSnapshot,
    PositionSummary,
    SystemStatus,
)


class DashboardService:
    """Service for fetching dashboard data."""

    def __init__(self):
        logger.info("Initializing DashboardService")
        self._compliance_engine = get_compliance_engine(enable_logging=False)
        self._broker = None
        self._bridge = None

    async def get_snapshot(self) -> DashboardSnapshot:
        """Get complete dashboard snapshot."""
        logger.debug("Fetching dashboard snapshot")
        timestamp = datetime.now(timezone.utc)

        # Fetch all data concurrently
        performance, positions, system_status, recent_alerts = await asyncio.gather(
            self._get_performance_metrics(),
            self._get_positions(),
            self._get_system_status(),
            self._get_recent_alerts(),
            return_exceptions=True,
        )

        # Handle any exceptions
        if isinstance(performance, Exception):
            logger.warning(
                "Failed to fetch performance metrics",
                extra={"error": str(performance)},
            )
            performance = self._empty_performance()
        if isinstance(positions, Exception):
            logger.warning(
                "Failed to fetch positions",
                extra={"error": str(positions)},
            )
            positions = []
        if isinstance(system_status, Exception):
            logger.warning(
                "Failed to fetch system status",
                extra={"error": str(system_status)},
            )
            system_status = self._empty_system_status()
        if isinstance(recent_alerts, Exception):
            logger.warning(
                "Failed to fetch recent alerts",
                extra={"error": str(recent_alerts)},
            )
            recent_alerts = []

        logger.info(
            "Dashboard snapshot created",
            extra={
                "positions_count": len(positions) if positions else 0,
                "alerts_count": len(recent_alerts) if recent_alerts else 0,
            },
        )
        return DashboardSnapshot(
            timestamp=timestamp,
            performance=performance,
            positions=positions,
            system_status=system_status,
            recent_alerts=recent_alerts,
        )

    async def _get_performance_metrics(self) -> DashboardPerformanceMetrics:
        """Get performance metrics from ComplianceEngine."""
        try:
            logger.debug("Fetching performance metrics from compliance engine")
            daily_summary = self._compliance_engine.get_daily_pnl_summary()
            slo_metrics = self._compliance_engine.get_slo_metrics()

            # Get portfolio value
            portfolio_value = await self._get_portfolio_value()
            starting_capital = Decimal(str(self._compliance_engine._starting_capital))

            # Calculate drawdown
            current_drawdown = self._calculate_drawdown(portfolio_value, starting_capital)
            max_drawdown = self._compliance_engine._max_drawdown_ratio

            metrics = DashboardPerformanceMetrics(
                total_pnl=Decimal(str(daily_summary.get("total_pnl", 0))),
                daily_pnl=Decimal(str(daily_summary.get("daily_pnl", 0))),
                daily_return_pct=daily_summary.get("daily_return_pct", 0.0),
                total_trades=daily_summary.get("total_trades", 0),
                winning_trades=daily_summary.get("winning_trades", 0),
                losing_trades=daily_summary.get("losing_trades", 0),
                win_rate=daily_summary.get("win_rate", 0.0),
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                sharpe_ratio=slo_metrics.get("sharpe_ratio"),
                portfolio_value=portfolio_value,
                starting_capital=starting_capital,
            )
            logger.debug(
                "Performance metrics fetched successfully",
                extra={
                    "daily_pnl": float(metrics.daily_pnl),
                    "total_trades": metrics.total_trades,
                    "win_rate": metrics.win_rate,
                },
            )
            return metrics
        except Exception as e:
            logger.error(
                "Failed to fetch performance metrics",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            # Return empty metrics on error
            return self._empty_performance()

    async def _get_positions(self) -> list[PositionSummary]:
        """Get current positions."""
        try:
            logger.debug("Fetching positions from broker")
            broker = await self._get_broker()
            if not broker:
                logger.warning("No broker available for fetching positions")
                return []

            positions_data = await broker.get_positions()

            positions = []
            for pos in positions_data:
                symbol = pos.get("symbol", "")
                quantity = pos.get("quantity", 0)
                if quantity == 0:
                    continue

                avg_price = Decimal(str(pos.get("avg_price", 0)))
                current_price = Decimal(str(pos.get("current_price", avg_price)))
                market_value = Decimal(
                    str(pos.get("market_value", quantity * float(current_price)))
                )
                unrealized_pnl = Decimal(str(pos.get("unrealized_pnl", 0)))

                # Calculate P&L percentage
                if avg_price > 0:
                    pnl_pct = float((current_price - avg_price) / avg_price * 100)
                else:
                    pnl_pct = 0.0

                side = "long" if quantity > 0 else "short"

                positions.append(
                    PositionSummary(
                        symbol=symbol,
                        quantity=abs(quantity),
                        avg_price=avg_price,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_pct=pnl_pct,
                        side=side,
                    )
                )

            logger.debug(
                "Positions fetched successfully",
                extra={"positions_count": len(positions)},
            )
            return positions
        except Exception as e:
            logger.error(
                "Failed to fetch positions",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return []

    async def _get_system_status(self) -> SystemStatus:
        """Get system health status."""
        try:
            logger.debug("Fetching system status")
            status_data = self._compliance_engine.get_system_status()
            slo_metrics = self._compliance_engine.get_slo_metrics()

            # Get bridge status
            bridge = await self._get_bridge()
            bridge_status = "unknown"
            if bridge:
                bridge_status = bridge.status.value

            # Get active orders
            broker = await self._get_broker()
            active_orders = 0
            if broker:
                open_orders = await broker.get_open_orders()
                active_orders = len(open_orders)

            availability = status_data.get("availability", {})
            systems_available = availability.get("available_systems", 0)
            systems_total = availability.get("total_systems", 0)

            status = SystemStatus(
                kill_switch_active=self._compliance_engine.check_kill_switch(),
                systems_available=systems_available,
                systems_total=systems_total,
                slo_compliance_rate=slo_metrics.get("slo_compliance_rate", 0.0),
                last_update=datetime.now(timezone.utc),
                bridge_status=bridge_status,
                active_orders=active_orders,
            )
            logger.debug(
                "System status fetched successfully",
                extra={
                    "kill_switch_active": status.kill_switch_active,
                    "systems_available": status.systems_available,
                    "active_orders": status.active_orders,
                },
            )
            return status
        except Exception as e:
            logger.error(
                "Failed to fetch system status",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return self._empty_system_status()

    async def _get_recent_alerts(self) -> list[dict[str, Any]]:
        """Get recent alerts."""
        try:
            logger.debug("Fetching recent alerts")
            # Get recent alerts from alerting system
            from app.services.alerting_system import NotificationDispatcher

            NotificationDispatcher.instance()
            # Return recent alerts from dispatcher history
            # For now, return empty list as dispatcher doesn't expose history
            logger.debug("Recent alerts fetched (currently empty)")
            return []
        except Exception as e:
            logger.error(
                "Failed to fetch recent alerts",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return []

    async def _get_portfolio_value(self) -> Decimal:
        """Get current portfolio value."""
        try:
            logger.debug("Fetching portfolio value")
            broker = await self._get_broker()
            if broker:
                value = await broker.calculate_portfolio_value()
                logger.debug(
                    "Portfolio value fetched",
                    extra={"portfolio_value": float(value)},
                )
                return Decimal(str(value))
        except Exception as e:
            logger.warning(
                "Failed to fetch portfolio value from broker",
                extra={"error": str(e)},
            )
        return Decimal(str(self._compliance_engine._starting_capital))

    async def _get_broker(self):
        """Get broker connector instance."""
        if self._broker is None:
            try:
                logger.debug("Getting broker connector instance")
                from app.services.live_trading.broker_connector import get_broker_connector

                self._broker = get_broker_connector()
                logger.info("Broker connector initialized")
            except Exception as e:
                logger.warning(
                    "Failed to get broker connector",
                    extra={"error": str(e)},
                )
        return self._broker

    async def _get_bridge(self):
        """Get trading bridge instance."""
        if self._bridge is None:
            try:
                logger.debug("Getting trading bridge instance")
                from app.services.live_trading.trading_bridge_orchestrator import (
                    get_trading_bridge_orchestrator,
                )

                self._bridge = get_trading_bridge_orchestrator()
                logger.info("Trading bridge initialized")
            except Exception as e:
                logger.warning(
                    "Failed to get trading bridge",
                    extra={"error": str(e)},
                )
        return self._bridge

    def _calculate_drawdown(self, current: Decimal, peak: Decimal) -> float:
        """Calculate drawdown percentage."""
        if peak <= 0:
            return 0.0
        return float((peak - current) / peak)

    def _empty_performance(self) -> DashboardPerformanceMetrics:
        """Return empty performance metrics."""
        return DashboardPerformanceMetrics(
            total_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
            daily_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            portfolio_value=Decimal("0"),
            starting_capital=Decimal("0"),
        )

    def _empty_system_status(self) -> SystemStatus:
        """Return empty system status."""
        return SystemStatus(
            kill_switch_active=False,
            systems_available=0,
            systems_total=0,
            slo_compliance_rate=0.0,
            last_update=datetime.now(timezone.utc),
            bridge_status="unknown",
            active_orders=0,
        )


# Singleton instance
_dashboard_service: Optional[DashboardService] = None


def get_dashboard_service() -> DashboardService:
    """Get singleton dashboard service instance."""
    global _dashboard_service
    if _dashboard_service is None:
        logger.info("Creating singleton DashboardService instance")
        _dashboard_service = DashboardService()
    return _dashboard_service
