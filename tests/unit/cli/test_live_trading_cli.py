"""
Unit tests for Live Trading CLI.

Tests the CLI commands and validation functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add scripts to path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))


@pytest.fixture
def mock_broker():
    """Mock broker connector."""
    broker = MagicMock()
    broker.get_account_info = AsyncMock(return_value={
        "account_id": "test_account",
        "buying_power": 100000,
        "cash_balance": 50000,
    })
    broker.calculate_portfolio_value = AsyncMock(return_value=100000)
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    return broker


@pytest.fixture
def mock_bridge():
    """Mock trading bridge."""
    bridge = MagicMock()
    bridge.start = AsyncMock(return_value=True)
    bridge.stop = AsyncMock(return_value=True)
    bridge.status = MagicMock(value="idle")
    return bridge


@pytest.mark.asyncio
async def test_validate_config():
    """Test configuration validation."""
    from validate_config import validate_config

    with patch('validate_config.get_broker_connector') as mock_get_broker:
        mock_broker = MagicMock()
        mock_broker.get_account_info = AsyncMock(return_value={"account_id": "test"})
        mock_get_broker.return_value = mock_broker

        success = await validate_config()
        assert success is True


@pytest.mark.asyncio
async def test_validate_broker_connection():
    """Test broker connection validation."""
    from validate_broker_connection import validate_broker_connection

    with patch('validate_broker_connection.get_broker_connector') as mock_get_broker:
        mock_broker = MagicMock()
        mock_broker.get_account_info = AsyncMock(return_value={"account_id": "test"})
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=100000)
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.get_open_orders = AsyncMock(return_value=[])
        mock_get_broker.return_value = mock_broker

        success = await validate_broker_connection()
        assert success is True


@pytest.mark.asyncio
async def test_live_trading_cli_validate_config(mock_broker):
    """Test LiveTradingCLI validate_config method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker):
        cli = LiveTradingCLI()
        success = await cli.validate_config()
        assert success is True


@pytest.mark.asyncio
async def test_live_trading_cli_validate_broker_connection(mock_broker):
    """Test LiveTradingCLI validate_broker_connection method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker):
        cli = LiveTradingCLI()
        success = await cli.validate_broker_connection()
        assert success is True


@pytest.mark.asyncio
async def test_live_trading_cli_start_trading(mock_broker, mock_bridge):
    """Test LiveTradingCLI start_trading method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker), \
         patch('start_live_trading.get_trading_bridge_orchestrator', return_value=mock_bridge), \
         patch('start_live_trading.get_compliance_engine') as mock_get_engine:
        # Mock compliance engine
        mock_engine = MagicMock()
        mock_engine.check_kill_switch = MagicMock(return_value=False)
        mock_engine._starting_capital = 100000
        mock_get_engine.return_value = mock_engine

        cli = LiveTradingCLI()
        success = await cli.start_trading()
        assert success is True
        assert cli.is_running is True


@pytest.mark.asyncio
async def test_live_trading_cli_stop_trading(mock_bridge):
    """Test LiveTradingCLI stop_trading method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_trading_bridge_orchestrator', return_value=mock_bridge):
        cli = LiveTradingCLI()
        cli.is_running = True
        success = await cli.stop_trading()
        assert success is True
        assert cli.is_running is False


@pytest.mark.asyncio
async def test_live_trading_cli_check_risk_status():
    """Test LiveTradingCLI check_risk_status method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_compliance_engine') as mock_get_engine:
        # Mock compliance engine
        mock_engine = MagicMock()
        mock_engine.get_daily_pnl_summary = MagicMock(return_value={
            "total_pnl": 1000,
            "daily_return_pct": 0.01,
            "total_trades": 5,
            "win_rate": 0.6,
        })
        mock_engine.get_slo_metrics = MagicMock(return_value={
            "slo_compliance_rate": 0.95,
        })
        mock_engine.get_system_status = MagicMock(return_value={
            "availability": {
                "available_systems": 17,
                "total_systems": 17,
            }
        })
        mock_engine.check_kill_switch = MagicMock(return_value=False)
        mock_get_engine.return_value = mock_engine

        cli = LiveTradingCLI()
        status = await cli.check_risk_status()
        assert status is not None
        assert "kill_switch_active" in status


@pytest.mark.asyncio
async def test_live_trading_cli_show_positions(mock_broker):
    """Test LiveTradingCLI show_positions method."""
    from start_live_trading import LiveTradingCLI

    mock_positions = [
        {"symbol": "AAPL", "quantity": 100, "avg_price": 150},
        {"symbol": "MSFT", "quantity": 50, "avg_price": 300},
    ]
    mock_broker.get_positions = AsyncMock(return_value=mock_positions)

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker):
        cli = LiveTradingCLI()
        positions = await cli.show_positions()
        assert positions == mock_positions


@pytest.mark.asyncio
async def test_live_trading_cli_place_order(mock_broker):
    """Test LiveTradingCLI place_order method."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker), \
         patch('start_live_trading.get_compliance_engine') as mock_get_engine:
        # Mock compliance engine
        mock_engine = MagicMock()
        mock_engine.execute_trade = AsyncMock(return_value=MagicMock(
            success=True,
            order_id="test_order_123",
        ))
        mock_engine._starting_capital = 100000
        mock_get_engine.return_value = mock_engine

        cli = LiveTradingCLI()
        success = await cli.place_order("AAPL", "buy", 10, 150.0)
        assert success is True


@pytest.mark.asyncio
async def test_live_trading_cli_place_order_failure(mock_broker):
    """Test LiveTradingCLI place_order method with failure."""
    from start_live_trading import LiveTradingCLI

    with patch('start_live_trading.get_broker_connector', return_value=mock_broker), \
         patch('start_live_trading.get_compliance_engine') as mock_get_engine:
        # Mock compliance engine with failure
        mock_engine = MagicMock()
        mock_engine.execute_trade = AsyncMock(return_value=MagicMock(
            success=False,
            error="Risk validation failed",
        ))
        mock_engine._starting_capital = 100000
        mock_get_engine.return_value = mock_engine

        cli = LiveTradingCLI()
        success = await cli.place_order("AAPL", "buy", 10, 150.0)
        assert success is False
