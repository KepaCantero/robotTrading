"""
Tests for dashboard service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.dashboard.dashboard_service import DashboardService
from app.dashboard.dashboard_data import (
    DashboardSnapshot,
    PerformanceMetrics,
    SystemStatus,
)


@pytest.fixture
def mock_compliance_engine():
    """Mock compliance engine."""
    engine = MagicMock()
    engine.get_daily_pnl_summary.return_value = {
        "total_pnl": 1500.50,
        "daily_pnl": 250.25,
        "daily_return_pct": 0.025,
        "total_trades": 10,
        "winning_trades": 6,
        "losing_trades": 4,
        "win_rate": 0.6,
    }
    engine.get_slo_metrics.return_value = {
        "slo_compliance_rate": 0.95,
        "sharpe_ratio": 1.5,
    }
    engine.get_system_status.return_value = {
        "availability": {
            "available_systems": 5,
            "total_systems": 5,
        }
    }
    engine.check_kill_switch.return_value = False
    engine._starting_capital = 10000
    engine._max_drawdown_ratio = 0.10
    return engine


@pytest.fixture
def mock_broker():
    """Mock broker connector."""
    broker = MagicMock()
    broker.get_positions = AsyncMock(
        return_value=[
            {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 15500.0,
                "unrealized_pnl": 500.0,
            },
            {
                "symbol": "MSFT",
                "quantity": 50,
                "avg_price": 300.0,
                "current_price": 295.0,
                "market_value": 14750.0,
                "unrealized_pnl": -250.0,
            },
        ]
    )
    broker.calculate_portfolio_value = AsyncMock(return_value=100000.0)
    broker.get_open_orders = AsyncMock(return_value=[])
    return broker


@pytest.fixture
def dashboard_service(mock_compliance_engine):
    """Create dashboard service with mocked dependencies."""
    with patch(
        "app.dashboard.dashboard_service.get_compliance_engine",
        return_value=mock_compliance_engine,
    ):
        service = DashboardService()
        return service


@pytest.mark.asyncio
async def test_get_snapshot(dashboard_service, mock_broker):
    """Test getting complete dashboard snapshot."""
    with patch.object(
        dashboard_service, "_get_broker", return_value=mock_broker
    ):
        snapshot = await dashboard_service.get_snapshot()

        assert isinstance(snapshot, DashboardSnapshot)
        assert isinstance(snapshot.performance, PerformanceMetrics)
        assert isinstance(snapshot.system_status, SystemStatus)
        assert len(snapshot.positions) == 2


@pytest.mark.asyncio
async def test_get_performance_metrics(dashboard_service):
    """Test getting performance metrics."""
    metrics = await dashboard_service._get_performance_metrics()

    assert metrics.total_pnl == Decimal("1500.50")
    assert metrics.daily_pnl == Decimal("250.25")
    assert metrics.daily_return_pct == 0.025
    assert metrics.total_trades == 10
    assert metrics.win_rate == 0.6
    assert metrics.sharpe_ratio == 1.5


@pytest.mark.asyncio
async def test_get_positions(dashboard_service, mock_broker):
    """Test getting positions."""
    with patch.object(
        dashboard_service, "_get_broker", return_value=mock_broker
    ):
        positions = await dashboard_service._get_positions()

        assert len(positions) == 2
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 100
        assert positions[0].side == "long"
        assert positions[0].unrealized_pnl == Decimal("500.0")

        assert positions[1].symbol == "MSFT"
        assert positions[1].side == "long"
        assert positions[1].unrealized_pnl == Decimal("-250.0")


@pytest.mark.asyncio
async def test_get_system_status(dashboard_service):
    """Test getting system status."""
    with patch.object(
        dashboard_service, "_get_broker", return_value=None
    ):
        status = await dashboard_service._get_system_status()

        assert status.kill_switch_active is False
        assert status.systems_available == 5
        assert status.systems_total == 5
        assert status.slo_compliance_rate == 0.95


@pytest.mark.asyncio
async def test_empty_positions(dashboard_service):
    """Test with no positions."""
    mock_broker = MagicMock()
    mock_broker.get_positions = AsyncMock(return_value=[])

    with patch.object(
        dashboard_service, "_get_broker", return_value=mock_broker
    ):
        positions = await dashboard_service._get_positions()
        assert positions == []


@pytest.mark.asyncio
async def test_broker_error_handling(dashboard_service):
    """Test handling of broker errors."""
    with patch.object(
        dashboard_service, "_get_broker", return_value=None
    ):
        positions = await dashboard_service._get_positions()
        assert positions == []


@pytest.mark.asyncio
async def test_get_dashboard_service_singleton():
    """Test that get_dashboard_service returns singleton instance."""
    from app.dashboard.dashboard_service import get_dashboard_service

    # First call creates instance
    service1 = get_dashboard_service()

    # Reset global to test singleton behavior
    import app.dashboard.dashboard_service as ds_module
    original_get_engine = ds_module.get_compliance_engine

    with patch("app.dashboard.dashboard_service.get_compliance_engine"):
        # After first call, should return same instance
        ds_module._dashboard_service = None
        service2 = get_dashboard_service()
        service3 = get_dashboard_service()

        assert service2 is service3
