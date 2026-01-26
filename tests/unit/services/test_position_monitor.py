"""
Unit tests for Position Monitor Service.

Tests the core functionality of the position monitor including:
- Position status tracking
- Stop-loss/take-profit trigger detection
- Price calculations
- P&L calculations
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.services.position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
    PositionStatus,
    StopExecutor,
    StopExecutionResult,
    StopType,
)


class TestMonitoredPosition:
    """Tests for MonitoredPosition dataclass."""

    def test_create_long_position(self):
        """Test creating a LONG position."""
        position = MonitoredPosition(
            position_id="test_1",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150.0"),
            quantity=Decimal("100"),
            current_price=Decimal("150.0"),
            stop_loss_pct=Decimal("0.05"),  # 5% stop-loss
            take_profit_pct=Decimal("0.10"),  # 10% take-profit
        )

        assert position.position_id == "test_1", "Position ID should match the provided value"
        assert position.symbol == "AAPL", "Symbol should be AAPL"
        assert position.side == "LONG", "Side should be LONG"
        assert position.entry_price == Decimal("150.0"), "Entry price should be 150.0"
        assert position.quantity == Decimal("100"), "Quantity should be 100"
        assert position.status == PositionStatus.ACTIVE, "Status should be ACTIVE by default"

    def test_create_short_position(self):
        """Test creating a SHORT position."""
        position = MonitoredPosition(
            position_id="test_2",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("150.0"),
            quantity=Decimal("100"),
            current_price=Decimal("150.0"),
            stop_loss_pct=Decimal("0.05"),
            take_profit_pct=Decimal("0.10"),
        )

        assert position.side == "SHORT", "Side should be SHORT"
        assert position.status == PositionStatus.ACTIVE, "Status should be ACTIVE by default"

    def test_calculate_stop_loss_long(self):
        """Test stop-loss calculation for LONG position."""
        position = MonitoredPosition(
            position_id="test_3",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            stop_loss_pct=Decimal("0.05"),  # 5%
        )

        # For LONG: stop_loss = entry * (1 - pct) = 100 * 0.95 = 95
        stop_loss = position.calculate_stop_loss_price()
        assert stop_loss == Decimal("95.0"), "Stop loss for LONG should be entry * (1 - stop_pct) = 95.0"

    def test_calculate_stop_loss_short(self):
        """Test stop-loss calculation for SHORT position."""
        position = MonitoredPosition(
            position_id="test_4",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            stop_loss_pct=Decimal("0.05"),  # 5%
        )

        # For SHORT: stop_loss = entry * (1 + pct) = 100 * 1.05 = 105
        stop_loss = position.calculate_stop_loss_price()
        assert stop_loss == Decimal("105.0"), "Stop loss for SHORT should be entry * (1 + stop_pct) = 105.0"

    def test_calculate_take_profit_long(self):
        """Test take-profit calculation for LONG position."""
        position = MonitoredPosition(
            position_id="test_5",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            take_profit_pct=Decimal("0.10"),  # 10%
        )

        # For LONG: take_profit = entry * (1 + pct) = 100 * 1.10 = 110
        take_profit = position.calculate_take_profit_price()
        assert take_profit == Decimal("110.0"), "Take profit for LONG should be entry * (1 + tp_pct) = 110.0"

    def test_calculate_take_profit_short(self):
        """Test take-profit calculation for SHORT position."""
        position = MonitoredPosition(
            position_id="test_6",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            take_profit_pct=Decimal("0.10"),  # 10%
        )

        # For SHORT: take_profit = entry * (1 - pct) = 100 * 0.90 = 90
        take_profit = position.calculate_take_profit_price()
        assert take_profit == Decimal("90.0"), "Take profit for SHORT should be entry * (1 - tp_pct) = 90.0"

    def test_should_trigger_stop_loss_long(self):
        """Test stop-loss trigger for LONG position."""
        position = MonitoredPosition(
            position_id="test_7",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("94.0"),
            stop_loss_price=Decimal("95.0"),
        )

        # For LONG: stop triggers when price <= stop_price
        assert position.should_trigger_stop_loss() is True, "Stop loss should trigger for LONG when current_price (94) <= stop_loss_price (95)"

        # Update price above stop
        position.current_price = Decimal("96.0")
        assert position.should_trigger_stop_loss() is False, "Stop loss should NOT trigger for LONG when current_price (96) > stop_loss_price (95)"

    def test_should_trigger_stop_loss_short(self):
        """Test stop-loss trigger for SHORT position."""
        position = MonitoredPosition(
            position_id="test_8",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("106.0"),
            stop_loss_price=Decimal("105.0"),
        )

        # For SHORT: stop triggers when price >= stop_price
        assert position.should_trigger_stop_loss() is True, "Stop loss should trigger for SHORT when current_price (106) >= stop_loss_price (105)"

        # Update price below stop
        position.current_price = Decimal("104.0")
        assert position.should_trigger_stop_loss() is False, "Stop loss should NOT trigger for SHORT when current_price (104) < stop_loss_price (105)"

    def test_should_trigger_take_profit_long(self):
        """Test take-profit trigger for LONG position."""
        position = MonitoredPosition(
            position_id="test_9",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("111.0"),
            take_profit_price=Decimal("110.0"),
        )

        # For LONG: take-profit triggers when price >= take_profit_price
        assert position.should_trigger_take_profit() is True, "Take profit should trigger for LONG when current_price (111) >= take_profit_price (110)"

        # Update price below target
        position.current_price = Decimal("109.0")
        assert position.should_trigger_take_profit() is False, "Take profit should NOT trigger for LONG when current_price (109) < take_profit_price (110)"

    def test_should_trigger_take_profit_short(self):
        """Test take-profit trigger for SHORT position."""
        position = MonitoredPosition(
            position_id="test_10",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("89.0"),
            take_profit_price=Decimal("90.0"),
        )

        # For SHORT: take-profit triggers when price <= take_profit_price
        assert position.should_trigger_take_profit() is True, "Take profit should trigger for SHORT when current_price (89) <= take_profit_price (90)"

        # Update price above target
        position.current_price = Decimal("91.0")
        assert position.should_trigger_take_profit() is False, "Take profit should NOT trigger for SHORT when current_price (91) > take_profit_price (90)"

    def test_calculate_pnl_long(self):
        """Test P&L calculation for LONG position."""
        position = MonitoredPosition(
            position_id="test_11",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("110.0"),
        )

        # For LONG: pnl = (current - entry) * quantity = (110 - 100) * 100 = 1000
        pnl = position.calculate_pnl()
        assert pnl == Decimal("1000.0"), "P&L for LONG should be (current - entry) * quantity = 1000.0"

    def test_calculate_pnl_short(self):
        """Test P&L calculation for SHORT position."""
        position = MonitoredPosition(
            position_id="test_12",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("90.0"),
        )

        # For SHORT: pnl = (entry - current) * quantity = (100 - 90) * 100 = 1000
        pnl = position.calculate_pnl()
        assert pnl == Decimal("1000.0"), "P&L for SHORT should be (entry - current) * quantity = 1000.0"

    def test_calculate_pnl_percentage(self):
        """Test P&L percentage calculation."""
        position = MonitoredPosition(
            position_id="test_13",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("110.0"),
        )

        pnl_pct = position.calculate_pnl_percentage()
        assert pnl_pct == Decimal("10.0"), "P&L percentage should be (110-100)/100 * 100 = 10.0%"

    def test_update_current_price(self):
        """Test updating current price."""
        position = MonitoredPosition(
            position_id="test_14",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
        )

        initial_count = position.check_count
        initial_time = position.last_checked

        # Wait a bit
        asyncio.run(asyncio.sleep(0.01))

        # Update price
        position.update_current_price(Decimal("105.0"))

        assert position.current_price == Decimal("105.0")
        assert position.check_count == initial_count + 1
        assert position.last_checked > initial_time

    def test_to_dict(self):
        """Test converting position to dictionary."""
        position = MonitoredPosition(
            position_id="test_15",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("110.0"),
            stop_loss_price=Decimal("95.0"),
            take_profit_price=Decimal("110.0"),
        )

        data = position.to_dict()

        assert data["position_id"] == "test_15"
        assert data["symbol"] == "AAPL"
        assert data["side"] == "LONG"
        assert data["entry_price"] == "100.0"
        assert data["quantity"] == "100"
        assert data["current_price"] == "110.0"
        assert data["stop_loss_price"] == "95.0"
        assert data["take_profit_price"] == "110.0"
        assert data["status"] == "active"
        assert "unrealized_pnl" in data

    def test_from_dict(self):
        """Test creating position from dictionary."""
        data = {
            "position_id": "test_16",
            "symbol": "AAPL",
            "side": "LONG",
            "entry_price": "100.0",
            "quantity": "100.0",
            "current_price": "110.0",
            "stop_loss_price": "95.0",
            "take_profit_price": "110.0",
            "status": "active",
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "check_count": 5,
        }

        position = MonitoredPosition.from_dict(data)

        assert position.position_id == "test_16"
        assert position.symbol == "AAPL"
        assert position.side == "LONG"
        assert position.entry_price == Decimal("100.0")
        assert position.quantity == Decimal("100.0")
        assert position.current_price == Decimal("110.0")
        assert position.check_count == 5


class TestStopExecutor:
    """Tests for StopExecutor."""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker."""
        broker = AsyncMock()
        broker.place_order = AsyncMock()
        return broker

    @pytest.fixture
    def executor(self, mock_broker):
        """Create a StopExecutor instance."""
        return StopExecutor(mock_broker)

    @pytest.fixture
    def long_position(self):
        """Create a test LONG position."""
        return MonitoredPosition(
            position_id="test_long",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("95.0"),  # Hit stop-loss
            stop_loss_price=Decimal("95.0"),
        )

    @pytest.mark.asyncio
    async def test_execute_stop_loss_success(self, executor, mock_broker, long_position):
        """Test successful stop-loss execution."""
        # Mock broker response
        mock_broker.place_order.return_value = {
            "order_id": "order_123",
            "status": "FILLED",
            "fill_price": 95.0,
        }

        result = await executor.execute_stop_loss(long_position)

        assert result.success is True, "Stop-loss execution should succeed"
        assert result.stop_type == StopType.STOP_LOSS, "Stop type should be STOP_LOSS"
        assert result.symbol == "AAPL", "Symbol should match position symbol"
        assert result.order_id == "order_123", "Order ID should match broker response"
        assert result.executed_price == Decimal("95.0"), "Executed price should match fill price"
        assert result.execution_time_ms is not None, "Execution time should be recorded"

        # Verify broker was called correctly
        mock_broker.place_order.assert_called_once_with(
            symbol="AAPL",
            side="SELL",
            quantity=100.0,
            order_type="MARKET",
        )

    @pytest.mark.asyncio
    async def test_execute_stop_loss_failure(self, executor, mock_broker, long_position):
        """Test failed stop-loss execution."""
        # Mock broker error
        mock_broker.place_order.return_value = {"error": "Insufficient funds"}

        result = await executor.execute_stop_loss(long_position)

        assert result.success is False, "Stop-loss execution should fail when broker returns error"
        assert result.stop_type == StopType.STOP_LOSS, "Stop type should still be STOP_LOSS on failure"
        assert result.error_message == "Insufficient funds", "Error message should match broker error"
        assert result.order_id is None, "Order ID should be None on failed execution"

    @pytest.mark.asyncio
    async def test_execute_take_profit_success(self, executor, mock_broker):
        """Test successful take-profit execution."""
        position = MonitoredPosition(
            position_id="test_tp",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("110.0"),  # Hit take-profit
            take_profit_price=Decimal("110.0"),
        )

        # Mock broker response
        mock_broker.place_order.return_value = {
            "order_id": "order_456",
            "status": "FILLED",
            "fill_price": 110.0,
        }

        result = await executor.execute_take_profit(position)

        assert result.success is True
        assert result.stop_type == StopType.TAKE_PROFIT
        assert result.symbol == "AAPL"
        assert result.order_id == "order_456"
        assert result.executed_price == Decimal("110.0")

    @pytest.mark.asyncio
    async def test_execute_stop_loss_short(self, executor, mock_broker):
        """Test stop-loss execution for SHORT position."""
        position = MonitoredPosition(
            position_id="test_short",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("105.0"),  # Hit stop-loss
            stop_loss_price=Decimal("105.0"),
        )

        # Mock broker response
        mock_broker.place_order.return_value = {
            "order_id": "order_789",
            "status": "FILLED",
            "fill_price": 105.0,
        }

        result = await executor.execute_stop_loss(position)

        assert result.success is True

        # For SHORT, we should BUY to close
        mock_broker.place_order.assert_called_once_with(
            symbol="AAPL",
            side="BUY",
            quantity=100.0,
            order_type="MARKET",
        )


class TestPositionMonitor:
    """Tests for PositionMonitor."""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker."""
        broker = MagicMock()
        broker.get_positions = AsyncMock(return_value=[])
        broker.get_quote = AsyncMock()
        return broker

    @pytest.fixture
    def monitor(self, mock_broker):
        """Create a PositionMonitor instance."""
        config = PositionMonitorConfig(
            check_interval_seconds=0.1,  # Fast for testing
            execute_stops_automatically=False,  # Don't actually execute in tests
        )
        return PositionMonitor(mock_broker, config=config)

    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """Test starting and stopping the monitor."""
        assert monitor.is_running is False, "Monitor should not be running initially"

        await monitor.start()
        assert monitor.is_running is True, "Monitor should be running after start()"

        await monitor.stop()
        assert monitor.is_running is False, "Monitor should not be running after stop()"

    @pytest.mark.asyncio
    async def test_add_position(self, monitor):
        """Test adding a position to monitor."""
        position = MonitoredPosition(
            position_id="test_add",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            stop_loss_pct=Decimal("0.05"),
        )

        await monitor.add_position(position)

        positions = monitor.get_monitored_positions()
        assert len(positions) == 1, "Should have 1 position after adding"
        assert positions[0].position_id == "test_add", "Position ID should match the added position"

    @pytest.mark.asyncio
    async def test_remove_position(self, monitor):
        """Test removing a position from monitor."""
        position = MonitoredPosition(
            position_id="test_remove",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
        )

        await monitor.add_position(position)
        assert len(monitor.get_monitored_positions()) == 1, "Should have 1 position after adding"

        await monitor.remove_position("test_remove")
        assert len(monitor.get_monitored_positions()) == 0, "Should have 0 positions after removal"

    def test_get_position(self, monitor):
        """Test getting a specific position."""
        position = MonitoredPosition(
            position_id="test_get",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
        )

        # Add directly to internal dict (synchronous)
        monitor._positions["test_get"] = position

        retrieved = monitor.get_position("test_get")
        assert retrieved is not None, "Should retrieve existing position"
        assert retrieved.position_id == "test_get", "Retrieved position ID should match"

        not_found = monitor.get_position("not_found")
        assert not_found is None, "Should return None for non-existent position"

    def test_get_statistics(self, monitor):
        """Test getting monitor statistics."""
        stats = monitor.get_statistics()

        assert "is_running" in stats
        assert "total_positions" in stats
        assert "active_positions" in stats
        assert "check_interval_seconds" in stats
        assert stats["total_positions"] == 0

    def test_get_position_summary(self, monitor):
        """Test getting position summary."""
        summary = monitor.get_position_summary()

        assert "total_positions" in summary
        assert "active_positions" in summary
        assert "total_unrealized_pnl" in summary
        assert "positions_by_symbol" in summary
        assert "positions_by_status" in summary

    @pytest.mark.asyncio
    async def test_monitor_loop_checks_positions(self, monitor):
        """Test that monitor loop checks positions."""
        # Create a position
        position = MonitoredPosition(
            position_id="test_loop",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100.0"),
            quantity=Decimal("100"),
            current_price=Decimal("100.0"),
            stop_loss_price=Decimal("95.0"),
            take_profit_price=Decimal("110.0"),
        )

        await monitor.add_position(position)

        # Mock quote
        mock_quote = MagicMock()
        mock_quote.last_price = 105.0
        monitor.broker.get_quote.return_value = mock_quote

        # Start monitor
        await monitor.start()

        # Wait for a few checks
        await asyncio.sleep(0.3)

        # Stop monitor
        await monitor.stop()

        # Verify position was checked
        stats = monitor.get_statistics()
        assert stats["total_checks"] > 0

        # Verify price was updated
        retrieved_position = monitor.get_position("test_loop")
        assert retrieved_position is not None
        assert retrieved_position.current_price == Decimal("105.0")
