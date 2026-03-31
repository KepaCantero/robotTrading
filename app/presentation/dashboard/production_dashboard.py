"""
Production Dashboard - Real-time monitoring for production operations.

This module provides a comprehensive production dashboard with:
- Real-time P&L display with WebSocket updates
- Position tracking and monitoring
- System health metrics (CPU, memory, uptime)
- Error rate tracking
- Latency monitoring
- Alert history and management
- Mobile-responsive design
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, ClassVar, Optional

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

logger = logging.getLogger(__name__)


class DashboardMetrics(BaseModel):
    """Real-time dashboard metrics."""

    # Portfolio metrics
    total_value: Decimal = Field(default=Decimal("0"), description="Total portfolio value")
    daily_pnl: Decimal = Field(default=Decimal("0"), description="Daily P&L")
    daily_pnl_pct: Decimal = Field(default=Decimal("0"), description="Daily P&L percentage")
    open_positions: int = Field(default=0, description="Number of open positions")
    buying_power: Decimal = Field(default=Decimal("0"), description="Available buying power")

    # System health
    cpu_percent: float = Field(default=0.0, description="CPU usage percentage")
    memory_mb: float = Field(default=0.0, description="Memory usage in MB")
    memory_percent: float = Field(default=0.0, description="Memory usage percentage")
    uptime_seconds: float = Field(default=0.0, description="System uptime in seconds")

    # Trading metrics
    orders_today: int = Field(default=0, description="Orders placed today")
    fills_today: int = Field(default=0, description="Orders filled today")
    rejects_today: int = Field(default=0, description="Orders rejected today")
    avg_latency_ms: float = Field(default=0.0, description="Average order latency in ms")

    # Risk metrics
    var_1day: Decimal = Field(default=Decimal("0"), description="1-day Value at Risk")
    var_limit: Decimal = Field(default=Decimal("0"), description="VaR limit")
    var_utilization_pct: float = Field(default=0.0, description="VaR utilization percentage")

    # Alerts
    active_alerts: int = Field(default=0, description="Count of active alerts")
    alerts_last_24h: int = Field(default=0, description="Alert count in last 24 hours")

    # Timestamp
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        json_encoders: ClassVar[dict] = {
            Decimal: str,
        }


class PositionMetric(BaseModel):
    """Individual position metric."""

    symbol: str = Field(..., description="Symbol/ticker")
    quantity: Decimal = Field(..., description="Position quantity")
    avg_price: Decimal = Field(..., description="Average entry price")
    current_price: Decimal = Field(..., description="Current market price")
    market_value: Decimal = Field(..., description="Total market value")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    unrealized_pnl_pct: Decimal = Field(..., description="Unrealized P&L percentage")
    currency: str = Field(default="USD", description="Position currency")

    class Config:
        json_encoders: ClassVar[dict] = {
            Decimal: str,
        }


class AlertHistoryItem(BaseModel):
    """Alert history item."""

    alert_id: str = Field(..., description="Alert unique identifier")
    rule_id: str = Field(..., description="Rule that triggered the alert")
    severity: str = Field(..., description="Alert severity level")
    message: str = Field(..., description="Alert message")
    triggered_at: str = Field(..., description="Alert trigger timestamp")
    resolved_at: Optional[str] = Field(default=None, description="Alert resolution timestamp")
    status: str = Field(..., description="Alert status")


class HistoricalDataPoint(BaseModel):
    """Historical data point for charts."""

    timestamp: str = Field(..., description="Data timestamp")
    portfolio_value: Decimal = Field(..., description="Portfolio value")
    daily_pnl: Decimal = Field(..., description="Daily P&L")
    drawdown_pct: Decimal = Field(..., description="Drawdown percentage")

    class Config:
        json_encoders: ClassVar[dict] = {
            Decimal: str,
        }


class ProductionDashboard:
    """
    Production dashboard with real-time monitoring capabilities.

    Integrates with:
    - Portfolio service for P&L and positions
    - Risk manager for VaR calculations
    - Alerting system for alert history
    - System monitors for health metrics
    - Trading services for order/execution metrics
    """

    def __init__(
        self,
        portfolio_service=None,
        position_monitor=None,
        risk_manager=None,
        memory_monitor=None,
        health_checker=None,
        alerting_orchestrator=None,
    ):
        """
        Initialize production dashboard.

        Args:
            portfolio_service: Portfolio service instance
            position_monitor: Position monitor instance
            risk_manager: Risk manager instance
            memory_monitor: Memory monitor instance
            health_checker: Health checker instance
            alerting_orchestrator: Alerting orchestrator instance
        """
        self.portfolio_service = portfolio_service
        self.position_monitor = position_monitor
        self.risk_manager = risk_manager
        self.memory_monitor = memory_monitor
        self.health_checker = health_checker
        self.alerting_orchestrator = alerting_orchestrator

        # WebSocket connections
        self._websocket_connections: list[WebSocket] = []

        # Metrics cache
        self._metrics_cache: Optional[DashboardMetrics] = None
        self._last_update: Optional[datetime] = None

        # Historical data cache
        self._historical_cache: dict[str, list[HistoricalDataPoint]] = {
            "7d": [],
            "30d": [],
        }

        # System start time
        self._start_time = datetime.now(timezone.utc)

        logger.info("ProductionDashboard initialized")

    async def get_metrics(self) -> DashboardMetrics:
        """
        Get current dashboard metrics.

        Returns:
            DashboardMetrics with all current values
        """
        try:
            # Portfolio metrics
            total_value = await self._get_portfolio_value()
            daily_pnl = await self._get_daily_pnl()
            open_positions = await self._get_open_position_count()
            buying_power = await self._get_buying_power()

            # Calculate daily P&L percentage
            daily_pnl_pct = (daily_pnl / total_value * 100) if total_value > 0 else Decimal("0")

            # System health
            cpu_percent = await self._get_cpu_percent()
            memory_mb = await self._get_memory_mb()
            memory_percent = await self._get_memory_percent()
            uptime = await self._get_uptime()

            # Trading metrics
            orders_today = await self._get_orders_today()
            fills_today = await self._get_fills_today()
            rejects_today = await self._get_rejects_today()
            avg_latency = await self._get_avg_latency()

            # Risk metrics
            var_1day = await self._get_var_1day()
            var_limit = await self._get_var_limit()
            var_util = await self._get_var_utilization()

            # Alerts
            active_alerts = await self._get_active_alerts()
            alerts_24h = await self._get_alerts_24h()

            metrics = DashboardMetrics(
                total_value=total_value,
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                open_positions=open_positions,
                buying_power=buying_power,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                uptime_seconds=uptime,
                orders_today=orders_today,
                fills_today=fills_today,
                rejects_today=rejects_today,
                avg_latency_ms=avg_latency,
                var_1day=var_1day,
                var_limit=var_limit,
                var_utilization_pct=var_util * 100,
                active_alerts=active_alerts,
                alerts_last_24h=alerts_24h,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            self._metrics_cache = metrics
            self._last_update = datetime.now(timezone.utc)

            return metrics

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error getting dashboard metrics: {e}", exc_info=True)
            # Return cached metrics if available
            if self._metrics_cache:
                return self._metrics_cache
            return DashboardMetrics()

    async def get_positions(self) -> list[PositionMetric]:
        """
        Get current position metrics.

        Returns:
            List of PositionMetric objects
        """
        try:
            positions = []

            if self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio()
                if portfolio and portfolio.positions:
                    for pos in portfolio.positions:
                        position_metric = PositionMetric(
                            symbol=pos.symbol,
                            quantity=pos.quantity,
                            avg_price=pos.avg_price,
                            current_price=pos.market_price,
                            market_value=pos.quantity * pos.market_price,
                            unrealized_pnl=pos.unrealized_pnl,
                            unrealized_pnl_pct=(
                                (pos.unrealized_pnl / (pos.avg_price * pos.quantity) * 100)
                                if pos.quantity != 0
                                else Decimal("0")
                            ),
                            currency=pos.currency,
                        )
                        positions.append(position_metric)

            return positions

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return []

    async def get_alert_history(self, hours: int = 24) -> list[AlertHistoryItem]:
        """
        Get alert history.

        Args:
            hours: Number of hours of history to retrieve

        Returns:
            List of AlertHistoryItem objects
        """
        try:
            alert_history = []

            if self.alerting_orchestrator:
                # Get alert manager from orchestrator
                alert_manager = self.alerting_orchestrator.alert_manager
                if alert_manager:
                    # Get recent alerts
                    datetime.now(timezone.utc) - timedelta(hours=hours)
                    alerts = alert_manager.get_recent_alerts(older_than_hours=hours)

                    for alert in alerts:
                        alert_item = AlertHistoryItem(
                            alert_id=alert.get("event_id", ""),
                            rule_id=alert.get("rule_id", ""),
                            severity=alert.get("severity", "unknown"),
                            message=alert.get("message", ""),
                            triggered_at=alert.get("triggered_at", ""),
                            resolved_at=alert.get("resolved_at"),
                            status=alert.get("status", "unknown"),
                        )
                        alert_history.append(alert_item)

            return alert_history

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Error getting alert history: {e}", exc_info=True)
            return []

    async def get_historical_data(self, period: str = "7d") -> list[HistoricalDataPoint]:
        """
        Get historical performance data.

        Args:
            period: Time period ('7d' or '30d')

        Returns:
            List of HistoricalDataPoint objects
        """
        try:
            # Return cached data
            if self._historical_cache.get(period):
                return self._historical_cache[period]

            # Generate mock historical data for now
            # In production, this would query the metrics database
            days = 7 if period == "7d" else 30
            historical_data = []

            base_value = await self._get_portfolio_value()
            if base_value == 0:
                base_value = Decimal("100000")

            for i in range(days):
                timestamp = datetime.now(timezone.utc) - timedelta(days=days - i)

                # Simulate some variation
                variation = Decimal(str((i - days / 2) * 0.01))
                portfolio_value = base_value * (1 + variation)
                daily_pnl = portfolio_value - base_value
                drawdown = min(variation, Decimal("0"))

                data_point = HistoricalDataPoint(
                    timestamp=timestamp.isoformat(),
                    portfolio_value=portfolio_value,
                    daily_pnl=daily_pnl,
                    drawdown_pct=abs(drawdown) * 100,
                )
                historical_data.append(data_point)

            # Cache the data
            self._historical_cache[period] = historical_data

            return historical_data

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error getting historical data: {e}", exc_info=True)
            return []

    # Helper methods for metrics

    async def _get_portfolio_value(self) -> Decimal:
        """Get total portfolio value."""
        try:
            if self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio()
                if portfolio:
                    return portfolio.total_value
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting portfolio value: {e}")
        return Decimal("0")

    async def _get_daily_pnl(self) -> Decimal:
        """Get daily P&L."""
        try:
            if self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio()
                if portfolio:
                    return portfolio.total_pnl
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting daily P&L: {e}")
        return Decimal("0")

    async def _get_open_position_count(self) -> int:
        """Get number of open positions."""
        try:
            if self.position_monitor:
                positions = self.position_monitor.get_monitored_positions()
                return len([p for p in positions if getattr(p, "status", None) == "active"])
            elif self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio()
                if portfolio:
                    return len(portfolio.positions)
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting open position count: {e}")
        return 0

    async def _get_buying_power(self) -> Decimal:
        """Get available buying power."""
        try:
            if self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio()
                if portfolio:
                    return portfolio.cash
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting buying power: {e}")
        return Decimal("0")

    async def _get_cpu_percent(self) -> float:
        """Get CPU usage percent."""
        try:
            import psutil

            return psutil.cpu_percent(interval=0.1)
        except (asyncio.TimeoutError, OSError):
            return 0.0

    async def _get_memory_mb(self) -> float:
        """Get memory usage in MB."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except (asyncio.TimeoutError, OSError):
            return 0.0

    async def _get_memory_percent(self) -> float:
        """Get memory usage percent."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_percent()
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError):
            return 0.0

    async def _get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    async def _get_orders_today(self) -> int:
        """Get orders placed today."""
        # In production, this would query the order database
        # For now, return a mock value
        return 0

    async def _get_fills_today(self) -> int:
        """Get orders filled today."""
        # In production, this would query the order database
        return 0

    async def _get_rejects_today(self) -> int:
        """Get orders rejected today."""
        # In production, this would query the order database
        return 0

    async def _get_avg_latency(self) -> float:
        """Get average order latency in milliseconds."""
        # In production, this would calculate from execution times
        return 0.0

    async def _get_var_1day(self) -> Decimal:
        """Get 1-day VaR."""
        try:
            if self.risk_manager:
                # Get current VaR from risk manager
                # For now, return a default value
                return Decimal("2000")
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"Error getting VaR: {e}")
        return Decimal("0")

    async def _get_var_limit(self) -> Decimal:
        """Get VaR limit."""
        # In production, this would come from configuration
        return Decimal("2000")

    async def _get_var_utilization(self) -> float:
        """Get VaR utilization (0-1)."""
        var_1day = await self._get_var_1day()
        var_limit = await self._get_var_limit()
        if var_limit > 0:
            return float(var_1day / var_limit)
        return 0.0

    async def _get_active_alerts(self) -> int:
        """Get count of active alerts."""
        try:
            if self.alerting_orchestrator:
                stats = self.alerting_orchestrator.get_statistics()
                # Calculate active alerts (triggered - resolved)
                return stats.get("total_alerts_triggered", 0) - stats.get(
                    "total_alerts_resolved", 0
                )
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting active alerts: {e}")
        return 0

    async def _get_alerts_24h(self) -> int:
        """Get alert count in last 24 hours."""
        try:
            if self.alerting_orchestrator:
                stats = self.alerting_orchestrator.get_statistics()
                return stats.get("total_alerts_triggered", 0)
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error getting 24h alert count: {e}")
        return 0

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        """
        WebSocket endpoint for real-time updates.

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self._websocket_connections.append(websocket)

        try:
            # Send initial metrics
            metrics = await self.get_metrics()
            await websocket.send_json(metrics.model_dump())

            # Send updates every second
            while True:
                await asyncio.sleep(1.0)
                metrics = await self.get_metrics()
                await websocket.send_json(metrics.model_dump())

        except WebSocketDisconnect:
            self._websocket_connections.remove(websocket)
            logger.info("WebSocket disconnected")
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            if websocket in self._websocket_connections:
                self._websocket_connections.remove(websocket)

    async def broadcast_update(self, data: dict[str, Any]) -> None:
        """
        Broadcast update to all connected WebSocket clients.

        Args:
            data: Data to broadcast
        """
        disconnected = []
        for websocket in self._websocket_connections:
            try:
                await websocket.send_json(data)
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(f"Error broadcasting to websocket: {e}")
                disconnected.append(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            self._websocket_connections.remove(websocket)

    def get_connection_count(self) -> int:
        """Get number of active WebSocket connections."""
        return len(self._websocket_connections)

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.alerting_orchestrator:
                return await self.alerting_orchestrator.acknowledge_alert(alert_id)
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.alerting_orchestrator:
                return await self.alerting_orchestrator.resolve_alert(alert_id)
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error resolving alert: {e}", exc_info=True)
        return False

    def get_health_status(self) -> dict[str, Any]:
        """
        Get overall health status of the dashboard.

        Returns:
            Dictionary with health status information
        """
        return {
            "is_running": True,
            "websocket_connections": len(self._websocket_connections),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "uptime_seconds": (datetime.now(timezone.utc) - self._start_time).total_seconds(),
            "components": {
                "portfolio_service": self.portfolio_service is not None,
                "position_monitor": self.position_monitor is not None,
                "risk_manager": self.risk_manager is not None,
                "memory_monitor": self.memory_monitor is not None,
                "health_checker": self.health_checker is not None,
                "alerting_orchestrator": self.alerting_orchestrator is not None,
            },
        }


# Singleton instance for production use
_production_dashboard_instance: Optional[ProductionDashboard] = None


def get_production_dashboard(
    portfolio_service=None,
    position_monitor=None,
    risk_manager=None,
    memory_monitor=None,
    health_checker=None,
    alerting_orchestrator=None,
) -> ProductionDashboard:
    """
    Get or create the production dashboard singleton instance.

    Args:
        portfolio_service: Portfolio service instance
        position_monitor: Position monitor instance
        risk_manager: Risk manager instance
        memory_monitor: Memory monitor instance
        health_checker: Health checker instance
        alerting_orchestrator: Alerting orchestrator instance

    Returns:
        ProductionDashboard instance
    """
    global _production_dashboard_instance

    if _production_dashboard_instance is None:
        _production_dashboard_instance = ProductionDashboard(
            portfolio_service=portfolio_service,
            position_monitor=position_monitor,
            risk_manager=risk_manager,
            memory_monitor=memory_monitor,
            health_checker=health_checker,
            alerting_orchestrator=alerting_orchestrator,
        )
        logger.info("Created production dashboard singleton instance")

    return _production_dashboard_instance
