"""
Dashboard service for collecting and aggregating trading data.

Provides methods to fetch current positions, performance metrics,
and system status for dashboard display.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from app.presentation.dashboard.dashboard_data import (
    DashboardSnapshot,
    PositionSummary,
    PerformanceMetrics,
    SystemStatus,
)
from app.core.compliance_engine import get_compliance_engine


class DashboardService:
    """Service for fetching dashboard data."""

    def __init__(self):
        self._compliance_engine = get_compliance_engine(enable_logging=False)
        self._broker = None
        self._bridge = None

    async def get_snapshot(self) -> DashboardSnapshot:
        """Get complete dashboard snapshot."""
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
            performance = self._empty_performance()
        if isinstance(positions, Exception):
            positions = []
        if isinstance(system_status, Exception):
            system_status = self._empty_system_status()
        if isinstance(recent_alerts, Exception):
            recent_alerts = []

        return DashboardSnapshot(
            timestamp=timestamp,
            performance=performance,
            positions=positions,
            system_status=system_status,
            recent_alerts=recent_alerts,
        )

    async def _get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics from ComplianceEngine."""
        try:
            daily_summary = self._compliance_engine.get_daily_pnl_summary()
            slo_metrics = self._compliance_engine.get_slo_metrics()

            # Get portfolio value
            portfolio_value = await self._get_portfolio_value()
            starting_capital = Decimal(
                str(self._compliance_engine._starting_capital)
            )

            # Calculate drawdown
            current_drawdown = self._calculate_drawdown(
                portfolio_value, starting_capital
            )
            max_drawdown = self._compliance_engine._max_drawdown_ratio

            return PerformanceMetrics(
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
        except Exception as e:
            # Return empty metrics on error
            return self._empty_performance()

    async def _get_positions(self) -> List[PositionSummary]:
        """Get current positions."""
        try:
            broker = await self._get_broker()
            if not broker:
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
                market_value = Decimal(str(pos.get("market_value", quantity * float(current_price))))
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

            return positions
        except Exception as e:
            return []

    async def _get_system_status(self) -> SystemStatus:
        """Get system health status."""
        try:
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

            return SystemStatus(
                kill_switch_active=self._compliance_engine.check_kill_switch(),
                systems_available=systems_available,
                systems_total=systems_total,
                slo_compliance_rate=slo_metrics.get("slo_compliance_rate", 0.0),
                last_update=datetime.now(timezone.utc),
                bridge_status=bridge_status,
                active_orders=active_orders,
            )
        except Exception as e:
            return self._empty_system_status()

    async def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        try:
            # Get recent alerts from alerting system
            from app.application.alerting import NotificationDispatcher

            dispatcher = NotificationDispatcher.instance()
            # Return recent alerts from dispatcher history
            # For now, return empty list as dispatcher doesn't expose history
            return []
        except Exception:
            return []

    async def _get_portfolio_value(self) -> Decimal:
        """Get current portfolio value."""
        try:
            broker = await self._get_broker()
            if broker:
                value = await broker.calculate_portfolio_value()
                return Decimal(str(value))
        except Exception:
            pass
        return Decimal(str(self._compliance_engine._starting_capital))

    async def _get_broker(self):
        """Get broker connector instance."""
        if self._broker is None:
            try:
                from app.application.orchestration.live_trading.broker_connector import (
                    get_broker_connector,
                )

                self._broker = get_broker_connector()
            except Exception:
                pass
        return self._broker

    async def _get_bridge(self):
        """Get trading bridge instance."""
        if self._bridge is None:
            try:
                from app.application.orchestration.live_trading.trading_bridge_orchestrator import (
                    get_trading_bridge_orchestrator,
                )

                self._bridge = get_trading_bridge_orchestrator()
            except Exception:
                pass
        return self._bridge

    def _calculate_drawdown(self, current: Decimal, peak: Decimal) -> float:
        """Calculate drawdown percentage."""
        if peak <= 0:
            return 0.0
        return float((peak - current) / peak)

    def _empty_performance(self) -> PerformanceMetrics:
        """Return empty performance metrics."""
        return PerformanceMetrics(
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
        _dashboard_service = DashboardService()
    return _dashboard_service
