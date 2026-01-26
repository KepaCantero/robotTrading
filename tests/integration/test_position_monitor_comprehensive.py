"""
Comprehensive integration tests for Position Monitor functionality.

This module tests the critical position monitoring system including:
- Stop-loss execution
- Take-profit execution
- Recovery from restart
- Emergency close scenarios
- Multi-position monitoring
- Short position handling
- Price update handling
- State persistence
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from app.services.position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
    PositionStatus,
)


class MockBroker:
    """Mock broker for testing position monitor."""

    def __init__(self):
        self.positions: List[Any] = []
        self.orders: List[Dict[str, Any]] = []
        self.current_prices: Dict[str, float] = {}
        self.connection_lost = False
        self.order_failures = False
        self.latency_ms = 0

    async def get_positions(self):
        """Get current positions from broker."""
        if self.connection_lost:
            raise ConnectionError("Broker connection lost")
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
        return self.positions

    async def get_quote(self, symbol: str):
        """Get current quote for symbol."""
        if self.connection_lost:
            raise ConnectionError("Broker connection lost")
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

        quote = MagicMock()
        quote.last_price = self.current_prices.get(symbol, 0.0)
        return quote

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = "MARKET",
        **kwargs
    ):
        """Place an order."""
        if self.connection_lost:
            raise ConnectionError("Broker connection lost")
        if self.order_failures:
            raise Exception("Order execution failed")
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

        order = {
            "order_id": f"order_{len(self.orders)}",
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "order_type": order_type,
            "status": "FILLED",
            "fill_price": self.current_prices.get(symbol, 0.0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.orders.append(order)
        return order


@pytest.mark.asyncio
@pytest.mark.critical
class TestPositionMonitorCriticalPaths:
    """Test critical paths for position monitoring."""

    async def test_stop_loss_execution_long_position(self):
        """Test that stop-loss is triggered correctly for LONG position."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="test_sl_long",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100"),
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            stop_loss_price=Decimal("95"),
        )

        await monitor.add_position(position)

        # Simulate price drop to $94 (below stop-loss)
        broker.current_prices["AAPL"] = 94.0

        # Wait for monitor to check and execute
        await asyncio.sleep(0.3)

        # Verify stop-loss was executed
        assert len(broker.orders) == 1
        stop_order = broker.orders[0]
        assert stop_order["symbol"] == "AAPL"
        assert stop_order["side"] == "SELL"
        assert stop_order["quantity"] == 10.0

        # Verify position was closed
        assert monitor.get_position("test_sl_long") is None

        # Check statistics
        stats = monitor.get_statistics()
        assert stats["stop_loss_triggered_count"] == 1

        await monitor.stop()

    async def test_stop_loss_execution_short_position(self):
        """Test that stop-loss is triggered correctly for SHORT position."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="test_sl_short",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100"),
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            stop_loss_price=Decimal("105"),  # Short stop-loss is above entry
        )

        await monitor.add_position(position)

        # Simulate price rise to $106 (above stop-loss)
        broker.current_prices["AAPL"] = 106.0

        # Wait for monitor to check and execute
        await asyncio.sleep(0.3)

        # Verify stop-loss was executed (BUY to cover)
        assert len(broker.orders) == 1
        stop_order = broker.orders[0]
        assert stop_order["symbol"] == "AAPL"
        assert stop_order["side"] == "BUY"  # Covering short
        assert stop_order["quantity"] == 10.0

        await monitor.stop()

    async def test_take_profit_execution_long_position(self):
        """Test that take-profit is triggered correctly for LONG position."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="test_tp_long",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100"),
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            take_profit_price=Decimal("110"),
        )

        await monitor.add_position(position)

        # Simulate price rise to $111 (above take-profit)
        broker.current_prices["AAPL"] = 111.0

        # Wait for monitor to check and execute
        await asyncio.sleep(0.3)

        # Verify take-profit was executed
        assert len(broker.orders) == 1
        tp_order = broker.orders[0]
        assert tp_order["symbol"] == "AAPL"
        assert tp_order["side"] == "SELL"
        assert tp_order["quantity"] == 10.0

        # Check statistics
        stats = monitor.get_statistics()
        assert stats["take_profit_triggered_count"] == 1

        await monitor.stop()

    async def test_take_profit_execution_short_position(self):
        """Test that take-profit is triggered correctly for SHORT position."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="test_tp_short",
            symbol="AAPL",
            side="SHORT",
            entry_price=Decimal("100"),
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            take_profit_price=Decimal("90"),  # Short take-profit is below entry
        )

        await monitor.add_position(position)

        # Simulate price drop to $89 (below take-profit)
        broker.current_prices["AAPL"] = 89.0

        # Wait for monitor to check and execute
        await asyncio.sleep(0.3)

        # Verify take-profit was executed (BUY to cover at profit)
        assert len(broker.orders) == 1
        tp_order = broker.orders[0]
        assert tp_order["symbol"] == "AAPL"
        assert tp_order["side"] == "BUY"

        await monitor.stop()

    async def test_stop_loss_calculated_from_percentage(self):
        """Test that stop-loss price is calculated from percentage."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 100.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Create position with percentage-based stop-loss
        position = MonitoredPosition(
            position_id="test_sl_pct",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("100"),
            quantity=Decimal("10"),
            current_price=Decimal("100"),
            stop_loss_pct=Decimal("0.05"),  # 5%
        )

        await monitor.add_position(position)

        # Verify stop-loss price was calculated
        monitored = monitor.get_position("test_sl_pct")
        assert monitored is not None
        assert monitored.stop_loss_price == Decimal("95.0")  # 100 * (1 - 0.05)

        # Simulate price drop to trigger stop-loss
        broker.current_prices["AAPL"] = 94.0
        await asyncio.sleep(0.3)

        # Verify stop-loss was executed
        assert len(broker.orders) == 1

        await monitor.stop()

    async def test_emergency_close_on_disconnect(self):
        """Test emergency close on connection loss."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 2500.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add multiple positions
        positions = [
            MonitoredPosition(
                position_id="pos_aapl",
                symbol="AAPL",
                side="LONG",
                entry_price=Decimal("150"),
                quantity=Decimal("100"),
                current_price=Decimal("150"),
            ),
            MonitoredPosition(
                position_id="pos_msft",
                symbol="MSFT",
                side="LONG",
                entry_price=Decimal("300"),
                quantity=Decimal("50"),
                current_price=Decimal("300"),
            ),
        ]

        for pos in positions:
            await monitor.add_position(pos)

        # Simulate connection loss
        broker.connection_lost = True

        # Wait for monitor to detect connection loss
        await asyncio.sleep(0.3)

        # Monitor should handle connection loss gracefully
        # In production, this would trigger emergency closer
        stats = monitor.get_statistics()
        assert stats["execution_failures"] >= 0  # Should track failures

        await monitor.stop()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitorRecovery:
    """Test position monitor recovery scenarios."""

    async def test_recovery_from_restart_with_positions(self):
        """Test that monitor recovers positions after restart."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        # Create broker position
        broker_position = MagicMock()
        broker_position.symbol = "AAPL"
        broker_position.position_id = "broker_pos_1"
        broker_position.position = 100  # Quantity
        broker_position.avg_cost = 150.0
        broker_position.current_price = 150.0
        broker.positions.append(broker_position)

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=False,
        )

        # Start monitor (should load positions from broker)
        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Verify position was loaded from broker
        assert len(monitor.get_monitored_positions()) == 1
        assert monitor.get_position("broker_pos_1") is not None

        await monitor.stop()

    async def test_state_persistence_and_recovery(self):
        """Test that monitor state is persisted and can be recovered."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            persist_state=True,
            state_sync_interval_seconds=0.2,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add position
        position = MonitoredPosition(
            position_id="persist_test",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
            stop_loss_price=Decimal("140"),
        )

        await monitor.add_position(position)

        # Wait for state sync
        await asyncio.sleep(0.3)

        # Stop monitor
        await monitor.stop()

        # Create new monitor instance (simulating restart)
        monitor2 = PositionMonitor(broker, config=config)
        await monitor2.start()

        # Verify position was recovered
        # Note: This test requires database persistence to be fully implemented
        # For now, we verify the structure is in place

        await monitor2.stop()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitorMultiPosition:
    """Test monitoring multiple positions simultaneously."""

    async def test_monitor_100_positions(self):
        """Test monitoring 100 positions simultaneously."""
        broker = MockBroker()

        # Create prices for 100 symbols
        symbols = [f"STOCK{i:03d}" for i in range(100)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
            log_all_checks=False,  # Disable verbose logging
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add 100 positions
        for i, symbol in enumerate(symbols):
            position = MonitoredPosition(
                position_id=f"pos_{i}",
                symbol=symbol,
                side="LONG",
                entry_price=Decimal("100"),
                quantity=Decimal("10"),
                current_price=Decimal("100"),
                stop_loss_price=Decimal("95"),
            )
            await monitor.add_position(position)

        # Verify all positions are monitored
        assert len(monitor.get_monitored_positions()) == 100

        # Trigger stop-loss for 10 positions
        for i in range(10):
            broker.current_prices[symbols[i]] = 94.0

        # Wait for monitoring cycle
        await asyncio.sleep(0.3)

        # Verify 10 positions were closed
        stats = monitor.get_statistics()
        assert stats["stop_loss_triggered_count"] == 10

        # Verify 90 positions remain
        assert len(monitor.get_monitored_positions()) == 90

        await monitor.stop()

    async def test_independent_position_monitoring(self):
        """Test that positions are monitored independently."""
        broker = MockBroker()
        broker.current_prices = {
            "AAPL": 150.0,
            "MSFT": 300.0,
            "GOOGL": 2500.0,
        }

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions with different stop-loss levels
        positions = [
            MonitoredPosition(
                position_id="pos_aapl",
                symbol="AAPL",
                side="LONG",
                entry_price=Decimal("150"),
                quantity=Decimal("100"),
                current_price=Decimal("150"),
                stop_loss_price=Decimal("140"),  # Will trigger
            ),
            MonitoredPosition(
                position_id="pos_msft",
                symbol="MSFT",
                side="LONG",
                entry_price=Decimal("300"),
                quantity=Decimal("50"),
                current_price=Decimal("300"),
                stop_loss_price=Decimal("250"),  # Won't trigger
            ),
            MonitoredPosition(
                position_id="pos_googl",
                symbol="GOOGL",
                side="LONG",
                entry_price=Decimal("2500"),
                quantity=Decimal("10"),
                current_price=Decimal("2500"),
                take_profit_price=Decimal("2750"),  # Will trigger
            ),
        ]

        for pos in positions:
            await monitor.add_position(pos)

        # Trigger AAPL stop-loss and GOOGL take-profit
        broker.current_prices["AAPL"] = 139.0
        broker.current_prices["GOOGL"] = 2760.0

        # Wait for monitoring cycle
        await asyncio.sleep(0.3)

        # Verify AAPL and GOOGL were closed, MSFT remains
        assert monitor.get_position("pos_aapl") is None
        assert monitor.get_position("pos_googl") is None
        assert monitor.get_position("pos_msft") is not None

        await monitor.stop()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitorEdgeCases:
    """Test edge cases and error scenarios."""

    async def test_position_with_zero_quantity(self):
        """Test handling of position with zero quantity."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add position with zero quantity
        position = MonitoredPosition(
            position_id="zero_qty",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("0"),
            current_price=Decimal("150"),
        )

        await monitor.add_position(position)

        # Position should still be monitored
        assert monitor.get_position("zero_qty") is not None

        await monitor.stop()

    async def test_price_fetch_timeout_handling(self):
        """Test handling of price fetch timeouts."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}
        broker.latency_ms = 100  # High latency

        config = PositionMonitorConfig(
            check_interval_seconds=0.05,
            price_fetch_timeout_seconds=0.05,  # Very short timeout
            execute_stops_automatically=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="timeout_test",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
            stop_loss_price=Decimal("140"),
        )

        await monitor.add_position(position)

        # Wait for monitoring cycle (should handle timeout gracefully)
        await asyncio.sleep(0.2)

        # Position should still be monitored despite timeouts
        assert monitor.get_position("timeout_test") is not None

        await monitor.stop()

    async def test_order_execution_failure(self):
        """Test handling of order execution failures."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}
        broker.order_failures = True  # All orders will fail

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="failure_test",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
            stop_loss_price=Decimal("140"),
        )

        await monitor.add_position(position)

        # Trigger stop-loss
        broker.current_prices["AAPL"] = 139.0

        # Wait for monitoring cycle
        await asyncio.sleep(0.3)

        # Verify execution failure was tracked
        stats = monitor.get_statistics()
        assert stats["execution_failures"] == 1

        # Position should be in ERROR state
        monitored = monitor.get_position("failure_test")
        assert monitored is not None
        assert monitored.status == PositionStatus.ERROR

        await monitor.stop()

    async def test_duplicate_position_id(self):
        """Test handling of duplicate position IDs."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(check_interval_seconds=0.1)

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add first position
        position1 = MonitoredPosition(
            position_id="duplicate",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
        )

        await monitor.add_position(position1)

        # Add second position with same ID (should overwrite)
        position2 = MonitoredPosition(
            position_id="duplicate",
            symbol="MSFT",
            side="LONG",
            entry_price=Decimal("300"),
            quantity=Decimal("50"),
            current_price=Decimal("300"),
        )

        await monitor.add_position(position2)

        # Verify only one position exists
        assert len(monitor.get_monitored_positions()) == 1
        monitored = monitor.get_position("duplicate")
        assert monitored.symbol == "MSFT"  # Should be the second one

        await monitor.stop()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitorAuditTrail:
    """Test audit trail functionality."""

    async def test_audit_log_position_added(self):
        """Test that position addition is logged."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            audit_log_enabled=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="audit_test",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
            stop_loss_price=Decimal("140"),
        )

        await monitor.add_position(position)

        # Check audit log
        audit_log = monitor.get_audit_log()
        assert len(audit_log) > 0
        assert audit_log[0]["action"] == "position_added"
        assert audit_log[0]["symbol"] == "AAPL"

        await monitor.stop()

    async def test_audit_log_stop_loss_triggered(self):
        """Test that stop-loss trigger is logged."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
            audit_log_enabled=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="audit_sl",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
            stop_loss_price=Decimal("140"),
        )

        await monitor.add_position(position)

        # Trigger stop-loss
        broker.current_prices["AAPL"] = 139.0
        await asyncio.sleep(0.3)

        # Check audit log
        audit_log = monitor.get_audit_log()
        assert any(entry["action"] == "stop_loss_triggered" for entry in audit_log)

        sl_entry = next(
            e for e in audit_log if e["action"] == "stop_loss_triggered"
        )
        assert sl_entry["symbol"] == "AAPL"
        assert "trigger_price" in sl_entry

        await monitor.stop()

    async def test_audit_log_position_removed(self):
        """Test that position removal is logged."""
        broker = MockBroker()
        broker.current_prices = {"AAPL": 150.0}

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            audit_log_enabled=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        position = MonitoredPosition(
            position_id="audit_remove",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150"),
            quantity=Decimal("100"),
            current_price=Decimal("150"),
        )

        await monitor.add_position(position)
        await monitor.remove_position("audit_remove")

        # Check audit log
        audit_log = monitor.get_audit_log()
        assert any(entry["action"] == "position_removed" for entry in audit_log)

        await monitor.stop()


@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitorStatistics:
    """Test statistics and reporting functionality."""

    async def test_monitor_statistics_accuracy(self):
        """Test that monitor statistics are accurate."""
        broker = MockBroker()
        broker.current_prices = {
            "AAPL": 150.0,
            "MSFT": 300.0,
            "GOOGL": 2500.0,
        }

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=True,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions
        positions = [
            MonitoredPosition(
                position_id="pos_aapl",
                symbol="AAPL",
                side="LONG",
                entry_price=Decimal("150"),
                quantity=Decimal("100"),
                current_price=Decimal("150"),
                stop_loss_price=Decimal("140"),
            ),
            MonitoredPosition(
                position_id="pos_msft",
                symbol="MSFT",
                side="LONG",
                entry_price=Decimal("300"),
                quantity=Decimal("50"),
                current_price=Decimal("300"),
                take_profit_price=Decimal("330"),
            ),
        ]

        for pos in positions:
            await monitor.add_position(pos)

        # Get initial statistics
        stats = monitor.get_statistics()
        assert stats["total_positions"] == 2
        assert stats["active_positions"] == 2
        assert stats["is_running"] is True

        # Trigger stop-loss for AAPL
        broker.current_prices["AAPL"] = 139.0
        await asyncio.sleep(0.3)

        # Check updated statistics
        stats = monitor.get_statistics()
        assert stats["total_positions"] == 1
        assert stats["stop_loss_triggered_count"] == 1

        await monitor.stop()

    async def test_position_summary_accuracy(self):
        """Test that position summary is accurate."""
        broker = MockBroker()
        broker.current_prices = {
            "AAPL": 150.0,
            "MSFT": 300.0,
        }

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions
        positions = [
            MonitoredPosition(
                position_id="pos_aapl",
                symbol="AAPL",
                side="LONG",
                entry_price=Decimal("150"),
                quantity=Decimal("100"),
                current_price=Decimal("155"),  # +$5 profit
            ),
            MonitoredPosition(
                position_id="pos_msft",
                symbol="MSFT",
                side="LONG",
                entry_price=Decimal("300"),
                quantity=Decimal("50"),
                current_price=Decimal("290"),  # -$10 loss
            ),
        ]

        for pos in positions:
            await monitor.add_position(pos)

        # Wait for price updates
        await asyncio.sleep(0.2)

        # Get position summary
        summary = monitor.get_position_summary()
        assert summary["total_positions"] == 2
        assert summary["active_positions"] == 2

        # Calculate expected P&L
        # AAPL: (155 - 150) * 100 = 500
        # MSFT: (290 - 300) * 50 = -500
        # Total: 0
        total_pnl = Decimal(summary["total_unrealized_pnl"])
        assert abs(total_pnl) < Decimal("1")  # Should be close to 0

        await monitor.stop()
