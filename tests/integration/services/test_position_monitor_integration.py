"""
Integration test for Position Monitor Service.

This test demonstrates how the PositionMonitor works with a broker adapter
to monitor positions and execute stop-loss/take-profit orders.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
    PositionStatus,
)


class MockBroker:
    """Mock broker for testing."""

    def __init__(self):
        self.positions = []
        self.orders = []
        self.current_prices = {}

    async def get_positions(self):
        """Get current positions."""
        return self.positions

    async def get_quote(self, symbol):
        """Get current quote for symbol."""
        quote = MagicMock()
        quote.last_price = self.current_prices.get(symbol, 0.0)
        return quote

    async def place_order(self, symbol, side, quantity, order_type="MARKET", **kwargs):
        """Place an order."""
        order = {
            "order_id": f"order_{len(self.orders)}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "status": "FILLED",
            "fill_price": self.current_prices.get(symbol, 0.0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.orders.append(order)
        return order


@pytest.mark.asyncio
async def test_position_monitor_end_to_end():
    """
    End-to-end test of position monitoring with stop-loss execution.

    This test demonstrates:
    1. Starting the monitor
    2. Adding a position to monitor
    3. Simulating price movement that triggers stop-loss
    4. Verifying stop-loss was executed
    5. Stopping the monitor
    """
    # Create mock broker
    broker = MockBroker()
    broker.current_prices = {"AAPL": 150.0}

    # Create monitor with fast check interval
    config = PositionMonitorConfig(
        check_interval_seconds=0.1,  # Fast for testing
        execute_stops_automatically=True,
        audit_log_enabled=True,
    )

    monitor = PositionMonitor(broker, config=config)

    # Start monitoring
    await monitor.start()
    assert monitor.is_running is True

    # Add a LONG position with 5% stop-loss
    position = MonitoredPosition(
        position_id="test_e2e",
        symbol="AAPL",
        side="LONG",
        entry_price=Decimal("150.0"),
        quantity=Decimal("100"),
        current_price=Decimal("150.0"),
        stop_loss_pct=Decimal("0.05"),  # 5% stop-loss = $142.50
    )

    await monitor.add_position(position)

    # Verify position was added
    monitored = monitor.get_position("test_e2e")
    assert monitored is not None
    assert monitored.symbol == "AAPL"
    assert monitored.stop_loss_price == Decimal("142.5")

    # Simulate price dropping to stop-loss level
    broker.current_prices["AAPL"] = 142.0

    # Wait for monitor to check and execute stop
    await asyncio.sleep(0.3)

    # Verify stop-loss was executed
    assert len(broker.orders) > 0
    stop_order = broker.orders[0]
    assert stop_order["symbol"] == "AAPL"
    assert stop_order["side"] == "SELL"
    assert stop_order["quantity"] == 100.0

    # Verify position was closed
    monitored = monitor.get_position("test_e2e")
    assert monitored is None  # Position was removed after execution

    # Check audit log
    audit_log = monitor.get_audit_log()
    assert len(audit_log) > 0
    assert audit_log[0]["action"] == "position_added"
    assert any(entry["action"] == "stop_loss_triggered" for entry in audit_log)

    # Get statistics
    stats = monitor.get_statistics()
    assert stats["stop_loss_triggered_count"] == 1
    assert stats["total_checks"] > 0

    # Stop monitoring
    await monitor.stop()
    assert monitor.is_running is False


@pytest.mark.asyncio
async def test_position_monitor_take_profit():
    """
    Test take-profit execution.

    This test demonstrates:
    1. Adding a position with take-profit
    2. Simulating price increase to take-profit level
    3. Verifying take-profit was executed
    """
    # Create mock broker
    broker = MockBroker()
    broker.current_prices = {"AAPL": 150.0}

    # Create monitor
    config = PositionMonitorConfig(
        check_interval_seconds=0.1,
        execute_stops_automatically=True,
    )

    monitor = PositionMonitor(broker, config=config)
    await monitor.start()

    # Add a LONG position with 10% take-profit
    position = MonitoredPosition(
        position_id="test_tp",
        symbol="AAPL",
        side="LONG",
        entry_price=Decimal("150.0"),
        quantity=Decimal("100"),
        current_price=Decimal("150.0"),
        take_profit_pct=Decimal("0.10"),  # 10% take-profit = $165.00
    )

    await monitor.add_position(position)

    # Simulate price rising to take-profit level
    broker.current_prices["AAPL"] = 166.0

    # Wait for monitor to check and execute
    await asyncio.sleep(0.3)

    # Verify take-profit was executed
    assert len(broker.orders) > 0
    tp_order = broker.orders[0]
    assert tp_order["symbol"] == "AAPL"
    assert tp_order["side"] == "SELL"

    # Verify position was closed
    monitored = monitor.get_position("test_tp")
    assert monitored is None

    # Check statistics
    stats = monitor.get_statistics()
    assert stats["take_profit_triggered_count"] == 1

    await monitor.stop()


@pytest.mark.asyncio
async def test_position_monitor_multiple_positions():
    """
    Test monitoring multiple positions simultaneously.

    This test demonstrates:
    1. Adding multiple positions for different symbols
    2. Independent monitoring of each position
    3. Selective stop execution based on price triggers
    """
    # Create mock broker
    broker = MockBroker()
    broker.current_prices = {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 2500.0,
    }

    # Create monitor
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
            entry_price=Decimal("150.0"),
            quantity=Decimal("100"),
            current_price=Decimal("150.0"),
            stop_loss_pct=Decimal("0.05"),
        ),
        MonitoredPosition(
            position_id="pos_msft",
            symbol="MSFT",
            side="LONG",
            entry_price=Decimal("300.0"),
            quantity=Decimal("50"),
            current_price=Decimal("300.0"),
            stop_loss_pct=Decimal("0.05"),
        ),
        MonitoredPosition(
            position_id="pos_googl",
            symbol="GOOGL",
            side="LONG",
            entry_price=Decimal("2500.0"),
            quantity=Decimal("10"),
            current_price=Decimal("2500.0"),
            take_profit_pct=Decimal("0.10"),
        ),
    ]

    for pos in positions:
        await monitor.add_position(pos)

    # Verify all positions are monitored
    assert len(monitor.get_monitored_positions()) == 3

    # Simulate AAPL hitting stop-loss
    broker.current_prices["AAPL"] = 142.0
    await asyncio.sleep(0.2)

    # Verify only AAPL was closed
    assert monitor.get_position("pos_aapl") is None
    assert monitor.get_position("pos_msft") is not None
    assert monitor.get_position("pos_googl") is not None

    # Simulate GOOGL hitting take-profit
    broker.current_prices["GOOGL"] = 2760.0
    await asyncio.sleep(0.2)

    # Verify GOOGL was closed
    assert monitor.get_position("pos_googl") is None
    assert monitor.get_position("pos_msft") is not None  # Still active

    # Get summary
    summary = monitor.get_position_summary()
    assert summary["total_positions"] == 1  # Only MSFT left
    assert summary["active_positions"] == 1

    await monitor.stop()


@pytest.mark.asyncio
async def test_position_monitor_short_position():
    """
    Test monitoring a SHORT position.

    For SHORT positions:
    - Stop-loss triggers when price goes UP
    - Take-profit triggers when price goes DOWN
    """
    # Create mock broker
    broker = MockBroker()
    broker.current_prices = {"AAPL": 150.0}

    # Create monitor
    config = PositionMonitorConfig(
        check_interval_seconds=0.1,
        execute_stops_automatically=True,
    )

    monitor = PositionMonitor(broker, config=config)
    await monitor.start()

    # Add a SHORT position
    position = MonitoredPosition(
        position_id="short_aapl",
        symbol="AAPL",
        side="SHORT",
        entry_price=Decimal("150.0"),
        quantity=Decimal("100"),
        current_price=Decimal("150.0"),
        stop_loss_pct=Decimal("0.05"),  # 5% stop-loss = $157.50
        take_profit_pct=Decimal("0.10"),  # 10% take-profit = $135.00
    )

    await monitor.add_position(position)

    # Verify stop-loss and take-profit prices
    assert position.stop_loss_price == Decimal("157.5")
    assert position.take_profit_price == Decimal("135.0")

    # Simulate price going up (stop-loss for SHORT)
    broker.current_prices["AAPL"] = 158.0
    await asyncio.sleep(0.3)

    # Verify stop-loss was executed (BUY to cover)
    assert len(broker.orders) > 0
    stop_order = broker.orders[0]
    assert stop_order["side"] == "BUY"  # Covering short
    assert stop_order["symbol"] == "AAPL"

    await monitor.stop()


@pytest.mark.asyncio
async def test_position_monitor_pnl_tracking():
    """
    Test P&L tracking for monitored positions.

    This test demonstrates:
    1. Tracking unrealized P&L as prices change
    2. Calculating P&L percentage
    3. P&L reporting in position summary
    """
    # Create mock broker
    broker = MockBroker()
    broker.current_prices = {"AAPL": 150.0}

    # Create monitor with auto-execute disabled
    config = PositionMonitorConfig(
        check_interval_seconds=0.1,
        execute_stops_automatically=False,  # Don't execute, just track
    )

    monitor = PositionMonitor(broker, config=config)
    await monitor.start()

    # Add position
    position = MonitoredPosition(
        position_id="pnl_test",
        symbol="AAPL",
        side="LONG",
        entry_price=Decimal("150.0"),
        quantity=Decimal("100"),
        current_price=Decimal("150.0"),
    )

    await monitor.add_position(position)

    # Initial P&L should be 0
    initial_pnl = position.calculate_pnl()
    assert initial_pnl == Decimal("0")

    # Simulate price increase
    broker.current_prices["AAPL"] = 155.0
    await asyncio.sleep(0.2)

    # Check updated P&L
    monitored = monitor.get_position("pnl_test")
    assert monitored is not None
    pnl = monitored.calculate_pnl()
    assert pnl == Decimal("500.0")  # (155 - 150) * 100

    pnl_pct = monitored.calculate_pnl_percentage()
    assert pnl_pct == Decimal("3.333333333333333333333333333")  # 500/15000 = 3.33%

    # Get position summary
    summary = monitor.get_position_summary()
    assert summary["total_unrealized_pnl"] == "500.0"

    await monitor.stop()
