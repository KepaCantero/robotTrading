"""
Integration tests for EmergencyCloser.

Tests the emergency position closing functionality with realistic
broker adapter integration.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.emergency_handler.emergency_closer import (
    EmergencyCloser,
    EmergencyCloseResult,
    EmergencyTrigger,
)


@pytest.fixture
def realistic_broker():
    """Create a realistic broker adapter mock."""
    broker = Mock()

    # Simulate realistic position data structure
    async def get_positions():
        return [
            Mock(
                symbol="AAPL",
                side="LONG",
                quantity=Decimal("100"),
                current_price=Decimal("150.00"),
                market_value=Decimal("15000.00"),
            ),
            Mock(
                symbol="MSFT",
                side="LONG",
                quantity=Decimal("50"),
                current_price=Decimal("300.00"),
                market_value=Decimal("15000.00"),
            ),
            Mock(
                symbol="GOOGL",
                side="SHORT",
                quantity=Decimal("20"),
                current_price=Decimal("2500.00"),
                market_value=Decimal("-50000.00"),
            ),
        ]

    async def place_order(symbol, side, quantity, order_type, **kwargs):
        # Simulate broker order placement
        await asyncio.sleep(0.1)  # Simulate network delay
        return {
            "order_id": 12345,
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "status": "FILLED",
            "fill_price": 150.00,
        }

    broker.get_positions = get_positions
    broker.place_order = place_order
    return broker


@pytest.fixture
def alert_tracker():
    """Track alerts sent during emergency close."""
    alerts = []

    def alert_callback(message):
        alerts.append(message)

    alert_callback.get_alerts = lambda: alerts
    alert_callback.clear = lambda: alerts.clear()
    return alert_callback


class TestEmergencyCloserIntegration:
    """Integration tests for EmergencyCloser."""

    @pytest.mark.asyncio
    async def test_full_emergency_close_workflow(self, realistic_broker, alert_tracker):
        """Test complete emergency close workflow from trigger to completion."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        # Trigger emergency close
        result = await closer.manual_trigger(reason="Integration test")

        # Verify result
        assert result.success is True
        assert result.total_positions == 3
        assert result.closed_positions == 3
        assert result.failed_positions == 0
        assert result.trigger == EmergencyTrigger.MANUAL_TRIGGER

        # Verify alert was sent
        alerts = alert_tracker.get_alerts()
        assert len(alerts) == 1
        assert "emergency" in alerts[0].lower()
        assert "integration test" in alerts[0].lower()

        # Verify audit log
        audit_log = closer.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["trigger"] == "manual_trigger"
        assert "reason" in audit_log[0]

    @pytest.mark.asyncio
    async def test_connection_lost_emergency_close(self, realistic_broker, alert_tracker):
        """Test emergency close triggered by connection loss."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        result = await closer.on_connection_lost()

        assert result.success is True
        assert result.trigger == EmergencyTrigger.CONNECTION_LOST
        assert result.closed_positions == 3

        # Verify alert mentions connection loss
        alerts = alert_tracker.get_alerts()
        assert "connection lost" in alerts[0].lower()

    @pytest.mark.asyncio
    async def test_critical_error_emergency_close(self, realistic_broker, alert_tracker):
        """Test emergency close triggered by critical error."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        critical_error = ConnectionError("Broker connection terminated unexpectedly")
        result = await closer.on_critical_error(critical_error)

        assert result.success is True
        assert result.trigger == EmergencyTrigger.CRITICAL_ERROR
        assert result.closed_positions == 3

        # Verify audit log includes error details
        audit_log = closer.get_audit_log()
        assert "error" in audit_log[0]
        assert "connection terminated" in audit_log[0]["error"]

    @pytest.mark.asyncio
    async def test_system_shutdown_emergency_close(self, realistic_broker, alert_tracker):
        """Test emergency close triggered by system shutdown."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        result = await closer.on_system_shutdown()

        assert result.success is True
        assert result.trigger == EmergencyTrigger.SYSTEM_SHUTDOWN
        assert result.closed_positions == 3

        # Verify alert mentions shutdown
        alerts = alert_tracker.get_alerts()
        assert "shutting down" in alerts[0].lower()

    @pytest.mark.asyncio
    async def test_multiple_emergency_triggers(self, realistic_broker, alert_tracker):
        """Test handling multiple emergency triggers in sequence."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        # First trigger
        result1 = await closer.manual_trigger(reason="First trigger")
        assert result1.success is True

        # Reset broker positions
        async def get_positions_2():
            return [
                Mock(
                    symbol="TSLA",
                    side="LONG",
                    quantity=Decimal("10"),
                    current_price=Decimal("800.00"),
                )
            ]

        realistic_broker.get_positions = get_positions_2

        # Second trigger
        result2 = await closer.on_connection_lost()
        assert result2.success is True

        # Verify audit log has both entries
        audit_log = closer.get_audit_log()
        assert len(audit_log) == 2
        assert audit_log[0]["trigger"] == "manual_trigger"
        assert audit_log[1]["trigger"] == "connection_lost"

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, realistic_broker):
        """Test that execution time is accurately tracked."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Each position takes ~0.1s to close, so total should be ~0.3s
        assert result.execution_time_seconds > 0
        assert result.execution_time_seconds < 1.0  # Should be fast

    @pytest.mark.asyncio
    async def test_position_value_calculation(self, realistic_broker):
        """Test that total position value is calculated correctly."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Expected values:
        # AAPL: 100 * 150.00 = 15000
        # MSFT: 50 * 300.00 = 15000
        # GOOGL: 20 * 2500.00 = 50000
        # Total: 80000
        expected_value = Decimal("80000.00")
        assert result.total_value == expected_value

    @pytest.mark.asyncio
    async def test_long_vs_short_position_closing(self, realistic_broker):
        """Test that LONG and SHORT positions are closed correctly."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        # Track order sides
        order_sides = []

        original_place_order = realistic_broker.place_order

        async def tracking_place_order(symbol, side, quantity, order_type, **kwargs):
            order_sides.append((symbol, side))
            return await original_place_order(symbol, side, quantity, order_type, **kwargs)

        realistic_broker.place_order = tracking_place_order

        await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Verify LONG positions closed with SELL orders
        assert ("AAPL", "SELL") in order_sides
        assert ("MSFT", "SELL") in order_sides

        # Verify SHORT position closed with BUY order
        assert ("GOOGL", "BUY") in order_sides

    @pytest.mark.asyncio
    async def test_result_serialization(self, realistic_broker):
        """Test that EmergencyCloseResult can be serialized to dict."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Convert to dict
        result_dict = result.to_dict()

        # Verify all fields are present and serializable
        assert "success" in result_dict
        assert "trigger" in result_dict
        assert "total_positions" in result_dict
        assert "closed_positions" in result_dict
        assert "failed_positions" in result_dict
        assert "total_value" in result_dict
        assert "execution_time_seconds" in result_dict
        assert "errors" in result_dict
        assert "timestamp" in result_dict

        # Verify JSON serializable
        import json

        json_str = json.dumps(result_dict)
        assert json_str  # Should not raise

    @pytest.mark.asyncio
    async def test_concurrent_close_protection(self, realistic_broker):
        """Test that concurrent close attempts are prevented."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        # Start two concurrent closes
        task1 = asyncio.create_task(closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER))
        task2 = asyncio.create_task(closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER))

        # Wait for both to complete
        result1, result2 = await asyncio.gather(task1, task2)

        # One should succeed, one should fail
        assert result1.success != result2.success or (
            result1.closed_positions == 3 and result2.closed_positions == 0
        )

    @pytest.mark.asyncio
    async def test_audit_log_limit(self, realistic_broker):
        """Test that audit log respects the limit parameter."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        # Generate multiple audit entries
        for i in range(5):
            await closer.manual_trigger(reason=f"Trigger {i}")

        # Get limited log
        limited_log = closer.get_audit_log(limit=3)

        assert len(limited_log) == 3

        # Get full log
        full_log = closer.get_audit_log()

        assert len(full_log) == 5

    @pytest.mark.asyncio
    async def test_non_critical_error_no_close(self, realistic_broker):
        """Test that non-critical errors don't trigger position close."""
        closer = EmergencyCloser(
            broker=realistic_broker,
            require_confirmation=False,
        )

        # Track if positions were closed
        positions_closed = False

        original_get_positions = realistic_broker.get_positions

        async def tracking_get_positions():
            nonlocal positions_closed
            positions_closed = True
            return await original_get_positions()

        realistic_broker.get_positions = tracking_get_positions

        # Trigger with non-critical error
        result = await closer.on_critical_error(ValueError("Invalid parameter"))

        # Should not have closed positions
        assert result.success is False
        assert positions_closed is False

    @pytest.mark.asyncio
    async def test_broker_connection_timeout_during_close(self, alert_tracker):
        """Test handling broker timeout during position close."""

        # Create broker that times out
        async def timeout_place_order(symbol, side, quantity, order_type, **kwargs):
            await asyncio.sleep(35)  # Exceed 30s timeout
            return {"order_id": 12345}

        broker = Mock()
        broker.get_positions = AsyncMock(
            return_value=[
                Mock(
                    symbol="AAPL",
                    side="LONG",
                    quantity=Decimal("100"),
                    current_price=Decimal("150.00"),
                )
            ]
        )
        broker.place_order = timeout_place_order

        closer = EmergencyCloser(
            broker=broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Should handle timeout gracefully
        assert result.success is False
        assert result.failed_positions == 1
        assert "timeout" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_empty_portfolio_emergency_close(self, realistic_broker, alert_tracker):
        """Test emergency close when portfolio is empty."""
        # Reset broker to return no positions
        realistic_broker.get_positions = AsyncMock(return_value=[])

        closer = EmergencyCloser(
            broker=realistic_broker,
            alert_callback=alert_tracker,
            require_confirmation=False,
        )

        result = await closer.manual_trigger(reason="Empty portfolio test")

        # Should succeed with no positions closed
        assert result.success is True
        assert result.total_positions == 0
        assert result.closed_positions == 0

        # Alert should still be sent
        alerts = alert_tracker.get_alerts()
        assert len(alerts) == 1
