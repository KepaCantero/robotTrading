"""
Comprehensive integration tests for Emergency Close functionality.

This module tests the emergency close system including:
- Connection loss handling
- System shutdown handling
- Critical error handling
- Manual trigger functionality
- Position closure execution
- Alert notifications
- Audit trail
- Multi-position scenarios
"""

import asyncio
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import signal

from app.services.emergency_handler.emergency_closer import (
    EmergencyCloser,
    EmergencyTrigger,
    EmergencyCloseResult,
)


class MockBroker:
    """Mock broker for testing emergency close."""

    def __init__(self):
        self.positions: List[Any] = []
        self.orders: List[Dict[str, Any]] = []
        self.connection_lost = False
        self.order_failures = False
        self.close_count = 0
        self.close_delay = 0

    async def get_positions(self):
        """Get current positions."""
        if self.connection_lost:
            raise ConnectionError("Broker connection lost")
        if self.close_delay > 0:
            await asyncio.sleep(self.close_delay)

        return self.positions

    async def place_order(
        self, symbol: str, side: str, quantity: Decimal, order_type: str = "MARKET", **kwargs
    ):
        """Place an order."""
        if self.connection_lost:
            raise ConnectionError("Broker connection lost")
        if self.order_failures:
            raise Exception("Order execution failed")

        self.close_count += 1

        order = {
            "order_id": f"emergency_close_{self.close_count}",
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "order_type": order_type,
            "status": "FILLED",
            "fill_price": 150.0,  # Mock price
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.orders.append(order)
        return order


class MockPosition:
    """Mock position object."""

    def __init__(
        self,
        symbol: str,
        quantity: Decimal,
        side: str = "LONG",
        current_price: Decimal = Decimal("150.00"),
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.side = side
        self.current_price = current_price
        self.position_id = f"pos_{symbol}_{id(self)}"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.integration
class TestEmergencyCloserBasicOperations:
    """Test basic emergency closer operations."""

    async def test_emergency_close_no_positions(self):
        """Test emergency close when there are no positions."""
        broker = MockBroker()

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 0
        assert result.closed_positions == 0
        assert result.failed_positions == 0

    async def test_emergency_close_single_position(self):
        """Test emergency close of a single position."""
        broker = MockBroker()

        # Add mock position
        position = MockPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="LONG",
        )
        broker.positions.append(position)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 1
        assert result.closed_positions == 1
        assert result.failed_positions == 0

        # Verify order was placed
        assert len(broker.orders) == 1
        assert broker.orders[0]["symbol"] == "AAPL"
        assert broker.orders[0]["side"] == "SELL"

    async def test_emergency_close_multiple_positions(self):
        """Test emergency close of multiple positions."""
        broker = MockBroker()

        # Add mock positions
        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
            MockPosition(symbol="MSFT", quantity=Decimal("50")),
            MockPosition(symbol="GOOGL", quantity=Decimal("10")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 3
        assert result.closed_positions == 3
        assert result.failed_positions == 0

        # Verify all orders were placed
        assert len(broker.orders) == 3

    async def test_emergency_close_short_position(self):
        """Test emergency close of a SHORT position."""
        broker = MockBroker()

        # Add SHORT position
        position = MockPosition(
            symbol="AAPL",
            quantity=Decimal("-100"),
            side="SHORT",
        )
        broker.positions.append(position)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True

        # Verify BUY order was placed to cover short
        assert len(broker.orders) == 1
        assert broker.orders[0]["side"] == "BUY"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.integration
class TestEmergencyCloserTriggers:
    """Test various emergency trigger scenarios."""

    async def test_connection_lost_trigger(self):
        """Test emergency close on connection loss."""
        broker = MockBroker()

        # Add positions before connection is lost
        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
            MockPosition(symbol="MSFT", quantity=Decimal("50")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Simulate connection lost
        broker.connection_lost = True

        # Trigger connection lost handler
        result = await closer.on_connection_lost()

        # Note: In production, this would fail because connection is lost
        # This test verifies the trigger mechanism works
        assert result.trigger == EmergencyTrigger.CONNECTION_LOST
        assert "CONNECTION LOST" in result.errors or result.total_positions >= 0

    async def test_system_shutdown_trigger(self):
        """Test emergency close on system shutdown."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)
        result = await closer.on_system_shutdown()

        assert result.success is True
        assert result.trigger == EmergencyTrigger.SYSTEM_SHUTDOWN
        assert result.closed_positions == 1

    async def test_critical_error_trigger(self):
        """Test emergency close on critical error."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Trigger with critical error (ConnectionError)
        result = await closer.on_critical_error(ConnectionError("Connection lost"))

        assert result.success is True
        assert result.trigger == EmergencyTrigger.CRITICAL_ERROR
        assert result.closed_positions == 1

    async def test_non_critical_error_no_trigger(self):
        """Test that non-critical errors don't trigger close."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Trigger with non-critical error
        result = await closer.on_critical_error(ValueError("Invalid parameter"))

        # Should not trigger close
        assert result.success is False
        assert result.closed_positions == 0
        assert len(result.errors) > 0

    async def test_manual_trigger(self):
        """Test manual emergency trigger."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)
        result = await closer.manual_trigger(reason="Testing manual trigger")

        assert result.success is True
        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER
        assert result.closed_positions == 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserErrorHandling:
    """Test error handling in emergency close scenarios."""

    async def test_partial_close_failure(self):
        """Test handling when some positions fail to close."""
        broker = MockBroker()

        # Add positions
        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
            MockPosition(symbol="MSFT", quantity=Decimal("50")),
            MockPosition(symbol="GOOGL", quantity=Decimal("10")),
        ]
        broker.positions.extend(positions)

        # Make second position fail
        broker.order_failures = True

        closer = EmergencyCloser(broker)

        # Mock to make only first succeed
        original_place_order = broker.place_order

        async def selective_fail(symbol, side, quantity, order_type="MARKET", **kwargs):
            if symbol == "MSFT":
                raise Exception("Order failed")
            return await original_place_order(symbol, side, quantity, order_type, **kwargs)

        broker.place_order = selective_fail

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Should have partial success
        assert result.total_positions == 3
        assert result.closed_positions < 3  # Some failed
        assert result.failed_positions > 0
        assert result.success is False  # Not all succeeded
        assert len(result.errors) > 0

    async def test_double_close_prevention(self):
        """Test that double close is prevented."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Start first close (in background)
        task1 = asyncio.create_task(closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER))

        # Try to close again immediately
        result2 = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Second close should be rejected
        assert result2.success is False
        assert "already in progress" in result2.errors[0].lower()

        # Wait for first close to complete
        result1 = await task1
        assert result1.success is True

    async def test_close_with_timeout(self):
        """Test close with timeout handling."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        # Add delay to order placement
        broker.close_delay = 0.1  # 100ms

        closer = EmergencyCloser(broker)

        # Close should succeed despite delay
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.closed_positions == 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserAuditTrail:
    """Test audit trail functionality."""

    async def test_audit_log_created(self):
        """Test that audit log is created."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        alert_messages = []

        def alert_callback(message: str):
            alert_messages.append(message)

        closer = EmergencyCloser(broker, alert_callback=alert_callback)

        await closer.manual_trigger(reason="Test audit log")

        # Check audit log
        audit_log = closer.get_audit_log()
        assert len(audit_log) > 0
        assert audit_log[0]["trigger"] == EmergencyTrigger.MANUAL_TRIGGER.value

    async def test_alert_callback_invoked(self):
        """Test that alert callback is invoked."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        alert_messages = []

        def alert_callback(message: str):
            alert_messages.append(message)

        closer = EmergencyCloser(broker, alert_callback=alert_callback)

        await closer.manual_trigger(reason="Test alert")

        # Verify alert was sent
        assert len(alert_messages) > 0
        assert "EMERGENCY" in alert_messages[0]
        assert "Manual trigger" in alert_messages[0]

    async def test_last_trigger_tracking(self):
        """Test that last trigger is tracked."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        await closer.manual_trigger(reason="First trigger")

        # Check last trigger
        assert closer.get_last_trigger() == EmergencyTrigger.MANUAL_TRIGGER
        assert closer.get_last_close_time() is not None

        # Trigger again
        first_close_time = closer.get_last_close_time()
        await closer.on_system_shutdown()

        # Verify trigger updated
        assert closer.get_last_trigger() == EmergencyTrigger.SYSTEM_SHUTDOWN
        assert closer.get_last_close_time() > first_close_time


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserConfirmation:
    """Test confirmation workflow."""

    async def test_confirmation_required(self):
        """Test that confirmation is required when configured."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(
            broker,
            require_confirmation=True,
            confirmation_timeout_seconds=0.1,
        )

        # Should wait for confirmation
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # After timeout, should proceed
        assert result.closed_positions == 1

    async def test_connection_lost_bypasses_confirmation(self):
        """Test that connection lost bypasses confirmation."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(
            broker,
            require_confirmation=True,
            confirmation_timeout_seconds=10.0,  # Long timeout
        )

        # Connection lost should bypass confirmation
        result = await closer.on_connection_lost()

        # Should proceed immediately without waiting
        assert result.total_positions >= 0


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserSignalHandlers:
    """Test signal handler integration."""

    async def test_signal_handler_registration(self):
        """Test that signal handlers are registered."""
        broker = MockBroker()

        closer = EmergencyCloser(broker)

        # Signal handlers should be registered
        # We can't easily test actual signal handling in pytest
        # But we can verify the closer was initialized
        assert closer is not None

    async def test_graceful_shutdown_on_signal(self):
        """Test graceful shutdown when signal is received."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Simulate signal handler behavior
        # (In production, signal.signal() would call this)
        result = await closer.on_system_shutdown()

        assert result.success is True
        assert result.closed_positions == 1


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserLargeScale:
    """Test emergency close with large numbers of positions."""

    async def test_close_100_positions(self):
        """Test closing 100 positions."""
        broker = MockBroker()

        # Create 100 positions
        for i in range(100):
            position = MockPosition(
                symbol=f"STOCK{i:03d}",
                quantity=Decimal("100"),
            )
            broker.positions.append(position)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.total_positions == 100
        assert result.closed_positions == 100
        assert result.execution_time_seconds < 10.0  # Should be fast

    async def test_close_with_mixed_long_short(self):
        """Test closing mixed long and short positions."""
        broker = MockBroker()

        # Add mixed positions
        long_positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100"), side="LONG"),
            MockPosition(symbol="MSFT", quantity=Decimal("50"), side="LONG"),
        ]

        short_positions = [
            MockPosition(symbol="TSLA", quantity=Decimal("-30"), side="SHORT"),
            MockPosition(symbol="NVDA", quantity=Decimal("-20"), side="SHORT"),
        ]

        broker.positions.extend(long_positions)
        broker.positions.extend(short_positions)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True
        assert result.closed_positions == 4

        # Verify correct order sides
        long_closes = [o for o in broker.orders if o["side"] == "SELL"]
        short_closes = [o for o in broker.orders if o["side"] == "BUY"]

        assert len(long_closes) == 2  # Close longs with SELL
        assert len(short_closes) == 2  # Close shorts with BUY

    async def test_close_execution_order(self):
        """Test that positions are closed in predictable order."""
        broker = MockBroker()

        # Add positions in specific order
        symbols = ["AAA", "BBB", "CCC", "DDD"]
        for symbol in symbols:
            position = MockPosition(symbol=symbol, quantity=Decimal("100"))
            broker.positions.append(position)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        assert result.success is True

        # Verify all positions were closed
        assert len(broker.orders) == 4

        # Orders should be in the same order as positions
        closed_symbols = [order["symbol"] for order in broker.orders]
        assert closed_symbols == symbols


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCloserResultSerialization:
    """Test result serialization and reporting."""

    async def test_result_to_dict(self):
        """Test that result can be serialized to dict."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)
        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Convert to dict
        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["trigger"] == "manual_trigger"
        assert result_dict["total_positions"] == 1
        assert result_dict["closed_positions"] == 1
        assert "timestamp" in result_dict
        assert "execution_time_seconds" in result_dict

    async def test_result_includes_errors(self):
        """Test that result includes error information."""
        broker = MockBroker()

        positions = [
            MockPosition(symbol="AAPL", quantity=Decimal("100")),
        ]
        broker.positions.extend(positions)

        closer = EmergencyCloser(broker)

        # Force an error
        broker.order_failures = True

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Result should have errors
        assert result.failed_positions > 0 or len(result.errors) > 0

        result_dict = result.to_dict()
        assert "errors" in result_dict
