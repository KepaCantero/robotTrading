"""
Unit tests for Production Dashboard.

Tests the core dashboard functionality including:
- Metrics collection
- Position tracking
- Alert history
- Historical data
- WebSocket endpoint simulation
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.dashboard.production_dashboard import (
    ProductionDashboard,
    DashboardMetrics,
    PositionMetric,
    AlertHistoryItem,
    HistoricalDataPoint,
    get_production_dashboard,
)


@pytest.fixture
def mock_portfolio_service():
    """Mock portfolio service."""
    service = Mock()
    service.get_portfolio = AsyncMock()
    return service


@pytest.fixture
def mock_position_monitor():
    """Mock position monitor."""
    monitor = Mock()
    monitor.get_monitored_positions = Mock(return_value=[])
    return monitor


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager."""
    manager = Mock()
    return manager


@pytest.fixture
def mock_alerting_orchestrator():
    """Mock alerting orchestrator."""
    orchestrator = Mock()
    orchestrator.acknowledge_alert = AsyncMock(return_value=True)
    orchestrator.resolve_alert = AsyncMock(return_value=True)
    orchestrator.get_statistics = Mock(return_value={
        "total_alerts_triggered": 10,
        "total_alerts_resolved": 7,
    })
    orchestrator.alert_manager = Mock()
    orchestrator.alert_manager.get_recent_alerts = Mock(return_value=[])
    return orchestrator


@pytest.fixture
def dashboard(mock_portfolio_service, mock_alerting_orchestrator):
    """Create dashboard instance with mocked dependencies."""
    return ProductionDashboard(
        portfolio_service=mock_portfolio_service,
        alerting_orchestrator=mock_alerting_orchestrator,
    )


class TestDashboardMetrics:
    """Test DashboardMetrics model."""

    def test_default_values(self):
        """Test dashboard metrics with default values."""
        metrics = DashboardMetrics()
        assert metrics.total_value == Decimal("0"), "Default total_value should be 0"
        assert metrics.daily_pnl == Decimal("0"), "Default daily_pnl should be 0"
        assert metrics.open_positions == 0, "Default open_positions should be 0"
        assert metrics.cpu_percent == 0.0, "Default cpu_percent should be 0.0"

    def test_metrics_with_values(self):
        """Test dashboard metrics with actual values."""
        metrics = DashboardMetrics(
            total_value=Decimal("100000"),
            daily_pnl=Decimal("1500"),
            daily_pnl_pct=Decimal("1.5"),
            open_positions=5,
            buying_power=Decimal("50000"),
            cpu_percent=25.5,
            memory_mb=512.0,
            memory_percent=12.5,
            uptime_seconds=86400.0,
            orders_today=25,
            fills_today=23,
            rejects_today=2,
            avg_latency_ms=150.0,
            var_1day=Decimal("2000"),
            var_limit=Decimal("2000"),
            var_utilization_pct=100.0,
            active_alerts=0,
            alerts_last_24h=5,
        )
        assert metrics.total_value == Decimal("100000"), "Total value should match input"
        assert metrics.daily_pnl_pct == Decimal("1.5"), "Daily P&L percentage should match input"
        assert metrics.var_utilization_pct == 100.0, "VaR utilization should match input"


class TestProductionDashboard:
    """Test ProductionDashboard class."""

    def test_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard is not None, "Dashboard should be initialized"
        assert dashboard._websocket_connections == [], "WebSocket connections should be empty initially"
        assert dashboard._metrics_cache is None, "Metrics cache should be None initially"
        assert dashboard._last_update is None, "Last update should be None initially"

    @pytest.mark.asyncio
    async def test_get_metrics_with_no_portfolio(self, dashboard):
        """Test get_metrics when portfolio service returns None."""
        dashboard.portfolio_service.get_portfolio.return_value = None

        metrics = await dashboard.get_metrics()

        assert metrics.total_value == Decimal("0"), "Total value should be 0 when no portfolio"
        assert metrics.daily_pnl == Decimal("0"), "Daily P&L should be 0 when no portfolio"
        assert metrics.open_positions == 0, "Open positions should be 0 when no portfolio"

    @pytest.mark.asyncio
    async def test_get_metrics_with_portfolio(self, dashboard, mock_portfolio_service):
        """Test get_metrics with valid portfolio."""
        from app.models.portfolio import AssetClass, Portfolio, Position

        # Create mock portfolio
        portfolio = Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("50000"),
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("100"),
                    avg_price=Decimal("150"),
                    market_price=Decimal("155"),
                    unrealized_pnl=Decimal("500"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            timestamp=datetime.now(timezone.utc),
            broker="test",
            currency="USD",
        )

        mock_portfolio_service.get_portfolio.return_value = portfolio

        metrics = await dashboard.get_metrics()

        # Portfolio total_value is a computed property: cash + positions_market_value
        # cash=50000 + (100 * 155) = 50000 + 15500 = 65500
        assert metrics.total_value == Decimal("65500"), "Total value should be cash + positions market value"
        # P&L comes from dashboard calculation, not portfolio
        assert metrics.buying_power == Decimal("50000"), "Buying power should match portfolio cash"

    @pytest.mark.asyncio
    async def test_get_positions(self, dashboard, mock_portfolio_service):
        """Test getting positions."""
        from app.models.portfolio import AssetClass, Portfolio, Position

        portfolio = Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("50000"),
            positions=[
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("100"),
                    avg_price=Decimal("150"),
                    market_price=Decimal("155"),
                    unrealized_pnl=Decimal("500"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            timestamp=datetime.now(timezone.utc),
            broker="test",
            currency="USD",
        )

        mock_portfolio_service.get_portfolio.return_value = portfolio

        positions = await dashboard.get_positions()

        assert len(positions) == 1, "Should have 1 position"
        assert positions[0].symbol == "AAPL", "Position symbol should be AAPL"
        assert positions[0].quantity == Decimal("100"), "Position quantity should be 100"
        assert positions[0].unrealized_pnl == Decimal("500"), "Position unrealized P&L should be 500"

    @pytest.mark.asyncio
    async def test_get_alert_history(self, dashboard, mock_alerting_orchestrator):
        """Test getting alert history."""
        mock_alerts = [
            {
                "event_id": "alert_1",
                "rule_id": "high_drawdown",
                "severity": "warning",
                "message": "Drawdown exceeded 10%",
                "triggered_at": "2024-01-25T12:00:00Z",
                "resolved_at": None,
                "status": "active",
            }
        ]

        mock_alerting_orchestrator.alert_manager.get_recent_alerts.return_value = mock_alerts

        alerts = await dashboard.get_alert_history(hours=24)

        assert len(alerts) == 1, "Should have 1 alert"
        assert alerts[0].alert_id == "alert_1", "Alert ID should be alert_1"
        assert alerts[0].severity == "warning", "Alert severity should be warning"
        assert alerts[0].status == "active", "Alert status should be active"

    @pytest.mark.asyncio
    async def test_get_historical_data(self, dashboard):
        """Test getting historical data."""
        data = await dashboard.get_historical_data(period="7d")

        assert len(data) == 7
        assert isinstance(data[0], HistoricalDataPoint)
        assert data[0].timestamp is not None
        assert data[0].portfolio_value > 0

    def test_get_health_status(self, dashboard):
        """Test getting health status."""
        health = dashboard.get_health_status()

        assert health["is_running"] is True, "Dashboard should be running"
        assert health["websocket_connections"] == 0, "WebSocket connections should be 0"
        assert "uptime_seconds" in health, "Health status should include uptime_seconds"
        assert "components" in health, "Health status should include components"

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, dashboard, mock_alerting_orchestrator):
        """Test acknowledging an alert."""
        result = await dashboard.acknowledge_alert("alert_1")

        assert result is True, "Acknowledging alert should succeed"
        mock_alerting_orchestrator.acknowledge_alert.assert_called_once_with("alert_1")

    @pytest.mark.asyncio
    async def test_resolve_alert(self, dashboard, mock_alerting_orchestrator):
        """Test resolving an alert."""
        result = await dashboard.resolve_alert("alert_1")

        assert result is True, "Resolving alert should succeed"
        mock_alerting_orchestrator.resolve_alert.assert_called_once_with("alert_1")

    def test_get_connection_count(self, dashboard):
        """Test getting connection count."""
        count = dashboard.get_connection_count()
        assert count == 0, "Connection count should be 0 initially"

        # Add a mock connection
        mock_ws = Mock()
        dashboard._websocket_connections.append(mock_ws)

        count = dashboard.get_connection_count()
        assert count == 1, "Connection count should be 1 after adding connection"


class TestDashboardSingleton:
    """Test dashboard singleton pattern."""

    def test_singleton_instance(self):
        """Test that get_production_dashboard returns singleton."""
        dashboard1 = get_production_dashboard()
        dashboard2 = get_production_dashboard()

        assert dashboard1 is dashboard2, "get_production_dashboard() should return same instance (singleton)"

    def test_singleton_initialization(self):
        """Test singleton initialization only happens once."""
        instance_id_1 = id(get_production_dashboard())
        instance_id_2 = id(get_production_dashboard())

        assert instance_id_1 == instance_id_2


class TestSystemMetrics:
    """Test system metrics collection."""

    @pytest.mark.asyncio
    async def test_cpu_percent(self, dashboard):
        """Test CPU percentage collection."""
        cpu = await dashboard._get_cpu_percent()
        assert isinstance(cpu, float), "CPU percent should be a float"
        assert 0 <= cpu <= 100, "CPU percent should be between 0 and 100"

    @pytest.mark.asyncio
    async def test_memory_mb(self, dashboard):
        """Test memory usage in MB."""
        memory = await dashboard._get_memory_mb()
        assert isinstance(memory, float), "Memory MB should be a float"
        assert memory >= 0, "Memory MB should be non-negative"

    @pytest.mark.asyncio
    async def test_uptime(self, dashboard):
        """Test uptime calculation."""
        uptime = await dashboard._get_uptime()
        assert isinstance(uptime, float), "Uptime should be a float"
        assert uptime >= 0, "Uptime should be non-negative"


class TestPositionMetric:
    """Test PositionMetric model."""

    def test_position_metric_creation(self):
        """Test creating a position metric."""
        position = PositionMetric(
            symbol="AAPL",
            quantity=Decimal("100"),
            avg_price=Decimal("150"),
            current_price=Decimal("155"),
            market_value=Decimal("15500"),
            unrealized_pnl=Decimal("500"),
            unrealized_pnl_pct=Decimal("3.33"),
            currency="USD",
        )

        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.unrealized_pnl_pct == Decimal("3.33")


class TestAlertHistoryItem:
    """Test AlertHistoryItem model."""

    def test_alert_history_item_creation(self):
        """Test creating an alert history item."""
        alert = AlertHistoryItem(
            alert_id="alert_1",
            rule_id="high_drawdown",
            severity="warning",
            message="Drawdown exceeded 10%",
            triggered_at="2024-01-25T12:00:00Z",
            resolved_at=None,
            status="active",
        )

        assert alert.alert_id == "alert_1"
        assert alert.severity == "warning"
        assert alert.status == "active"


class TestHistoricalDataPoint:
    """Test HistoricalDataPoint model."""

    def test_historical_data_point_creation(self):
        """Test creating a historical data point."""
        point = HistoricalDataPoint(
            timestamp="2024-01-25T12:00:00Z",
            portfolio_value=Decimal("100000"),
            daily_pnl=Decimal("1500"),
            drawdown_pct=Decimal("5.0"),
        )

        assert point.portfolio_value == Decimal("100000")
        assert point.daily_pnl == Decimal("1500")
        assert point.drawdown_pct == Decimal("5.0")
