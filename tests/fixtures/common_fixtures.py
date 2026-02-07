"""
Shared test fixtures for algoTrading testing suite.

This module provides common fixtures used across multiple test modules.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.emergency_handler.emergency_closer import EmergencyCloser
from app.services.fifo.fifo_integrator import FIFOIntegrator, Trade
from app.services.position_monitor import (
    MonitoredPosition,
    PositionMonitor,
    PositionMonitorConfig,
    PositionStatus,
)


@pytest.fixture
def event_loop():
    """
    Create event loop for async tests.

    This fixture ensures a fresh event loop for each test module.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_broker():
    """
    Mock broker for testing.

    Provides a mock broker implementation with:
    - Position tracking
    - Order placement
    - Price quotes
    - Connection state simulation
    """

    class MockBroker:
        def __init__(self):
            self.positions: List[Any] = []
            self.orders: List[Dict[str, Any]] = []
            self.current_prices: Dict[str, float] = {}
            self.connection_lost = False
            self.order_failures = False
            self.latency_ms = 0
            self.order_count = 0

        async def get_positions(self):
            if self.connection_lost:
                raise ConnectionError("Broker connection lost")
            if self.latency_ms > 0:
                await asyncio.sleep(self.latency_ms / 1000)
            return self.positions

        async def get_quote(self, symbol: str):
            if self.connection_lost:
                raise ConnectionError("Broker connection lost")
            if self.latency_ms > 0:
                await asyncio.sleep(self.latency_ms / 1000)

            quote = MagicMock()
            quote.last_price = self.current_prices.get(symbol, 100.0)
            return quote

        async def get_market_data(self, symbol: str):
            if self.connection_lost:
                raise ConnectionError("Broker connection lost")

            return {
                "symbol": symbol,
                "last": self.current_prices.get(symbol, 100.0),
                "bid": self.current_prices.get(symbol, 100.0) - 0.01,
                "ask": self.current_prices.get(symbol, 100.0) + 0.01,
            }

        async def place_order(
            self, symbol: str, side: str, quantity: Decimal, order_type: str = "MARKET", **kwargs
        ):
            if self.connection_lost:
                raise ConnectionError("Broker connection lost")
            if self.order_failures:
                raise Exception("Order execution failed")
            if self.latency_ms > 0:
                await asyncio.sleep(self.latency_ms / 1000)

            self.order_count += 1

            order = {
                "order_id": f"order_{self.order_count}",
                "symbol": symbol,
                "side": side,
                "quantity": float(quantity),
                "order_type": order_type,
                "status": "FILLED",
                "fill_price": self.current_prices.get(symbol, 100.0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.orders.append(order)
            return order

        def reset(self):
            """Reset broker state."""
            self.positions.clear()
            self.orders.clear()
            self.current_prices.clear()
            self.connection_lost = False
            self.order_failures = False
            self.order_count = 0

    broker = MockBroker()
    yield broker
    broker.reset()


@pytest.fixture
def mock_position():
    """
    Mock position factory.

    Returns a function that creates mock positions.
    """

    def _create_position(
        symbol: str = "AAPL",
        quantity: Decimal = Decimal("100"),
        side: str = "LONG",
        entry_price: Decimal = Decimal("150.00"),
        current_price: Decimal = Decimal("150.00"),
    ) -> Any:
        position = MagicMock()
        position.symbol = symbol
        position.quantity = quantity
        position.side = side
        position.entry_price = entry_price
        position.avg_cost = entry_price
        position.current_price = current_price
        position.position_id = f"pos_{symbol}_{id(position)}"
        return position

    return _create_position


@pytest.fixture
def sample_symbols():
    """
    List of sample symbols for testing.
    """
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]


@pytest.fixture
def sample_prices():
    """
    Dictionary of sample prices for testing.
    """
    return {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 2500.0,
        "AMZN": 3000.0,
        "TSLA": 800.0,
        "NVDA": 400.0,
        "META": 250.0,
        "NFLX": 350.0,
    }


@pytest.fixture
def monitored_position_factory():
    """
    Factory for creating MonitoredPosition instances.
    """

    def _create_position(
        position_id: str = "test_position",
        symbol: str = "AAPL",
        side: str = "LONG",
        entry_price: Decimal = Decimal("150.00"),
        quantity: Decimal = Decimal("100"),
        current_price: Decimal = Decimal("150.00"),
        stop_loss_price: Optional[Decimal] = None,
        stop_loss_pct: Optional[Decimal] = None,
        take_profit_price: Optional[Decimal] = None,
        take_profit_pct: Optional[Decimal] = None,
    ) -> MonitoredPosition:
        return MonitoredPosition(
            position_id=position_id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            current_price=current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_pct=stop_loss_pct,
            take_profit_price=take_profit_price,
            take_profit_pct=take_profit_pct,
        )

    return _create_position


@pytest.fixture
def trade_factory():
    """
    Factory for creating Trade instances for FIFO.
    """

    def _create_trade(
        trade_id: str = "test_trade",
        symbol: str = "AAPL",
        side: str = "BUY",
        quantity: Decimal = Decimal("100"),
        execution_price: Decimal = Decimal("150.00"),
        execution_time: Optional[datetime] = None,
        commission: Decimal = Decimal("1.00"),
        broker_name: str = "alpaca",
        broker_trade_id: Optional[str] = None,
    ) -> Trade:
        if execution_time is None:
            execution_time = datetime.now(timezone.utc)

        return Trade(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
            execution_time=execution_time,
            commission=commission,
            broker_name=broker_name,
            broker_trade_id=broker_trade_id,
        )

    return _create_trade


@pytest.fixture
async def position_monitor(mock_broker):
    """
    Position monitor instance for testing.

    Creates a monitor with fast check interval for testing.
    """
    config = PositionMonitorConfig(
        check_interval_seconds=0.1,
        execute_stops_automatically=False,  # Don't execute by default
        audit_log_enabled=True,
    )

    monitor = PositionMonitor(mock_broker, config=config)
    await monitor.start()

    yield monitor

    # Cleanup
    await monitor.stop()


@pytest.fixture
async def emergency_closer(mock_broker):
    """
    Emergency closer instance for testing.
    """
    closer = EmergencyCloser(mock_broker)
    yield closer


@pytest.fixture
async def fifo_integrator():
    """
    FIFO integrator instance for testing.
    """
    integrator = FIFOIntegrator(user_id=uuid4())
    await integrator.initialize()

    yield integrator


@pytest.fixture
def fast_monitor_config():
    """
    Fast monitor config for testing.
    """
    return PositionMonitorConfig(
        check_interval_seconds=0.05,
        execute_stops_automatically=False,
        audit_log_enabled=False,
        log_all_checks=False,
    )


@pytest.fixture
def slow_monitor_config():
    """
    Slow monitor config for testing.
    """
    return PositionMonitorConfig(
        check_interval_seconds=1.0,
        execute_stops_automatically=False,
        audit_log_enabled=True,
        log_all_checks=True,
    )


@pytest.fixture
def price_update_sequence():
    """
    Sequence of price updates for testing.

    Returns a function that generates price sequences.
    """

    def _generate_sequence(
        start_price: float,
        steps: int,
        change_pct: float,
    ) -> List[float]:
        """Generate price sequence."""
        prices = []
        price = start_price

        for _ in range(steps):
            prices.append(price)
            price *= 1 + change_pct

        return prices

    return _generate_sequence


@pytest.fixture
def assert_position_state():
    """
    Helper for asserting position state.
    """

    def _assert_state(
        position: MonitoredPosition,
        status: PositionStatus,
        expected_pnl: Optional[Decimal] = None,
        expected_check_count: Optional[int] = None,
    ):
        """Assert position is in expected state."""
        assert position.status == status

        if expected_pnl is not None:
            actual_pnl = position.calculate_pnl()
            assert abs(actual_pnl - expected_pnl) < Decimal("0.01")

        if expected_check_count is not None:
            assert position.check_count >= expected_check_count

    return _assert_state


@pytest.fixture
def wait_for_condition():
    """
    Wait for a condition to become true.

    Useful for async tests that need to wait for state changes.
    """

    async def _wait(
        condition: callable,
        timeout: float = 5.0,
        interval: float = 0.1,
    ) -> bool:
        """Wait for condition to be true."""
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)

        return False

    return _wait


@pytest.fixture
def memory_monitor():
    """
    Monitor memory usage during tests.

    Useful for detecting memory leaks in load tests.
    """
    import os

    import psutil

    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_memory = self.get_memory_mb()
            self.samples = []

        def get_memory_mb(self) -> float:
            """Get current memory usage in MB."""
            info = self.process.memory_info()
            return info.rss / 1024 / 1024

        def sample(self):
            """Take a memory sample."""
            current = self.get_memory_mb()
            self.samples.append(current)
            return current

        def get_increase(self) -> float:
            """Get memory increase since start."""
            return self.get_memory_mb() - self.start_memory

        def get_max_increase(self) -> float:
            """Get maximum memory increase."""
            return max(self.samples) - self.start_memory if self.samples else 0

        def assert_no_leak(self, max_increase_mb: float = 100):
            """Assert memory increase is within limits."""
            increase = self.get_increase()
            if increase > max_increase_mb:
                raise AssertionError(
                    f"Memory leak detected: {increase:.2f} MB increase "
                    f"(max allowed: {max_increase_mb} MB)"
                )

    monitor = MemoryMonitor()
    yield monitor
    monitor.assert_no_leak()


@pytest.fixture(scope="session")
def test_data_dir():
    """
    Directory for test data files.
    """
    from pathlib import Path

    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "tests" / "data"

    data_dir.mkdir(exist_ok=True)

    return data_dir


@pytest.fixture
def temp_db_path(test_data_dir):
    """
    Path for temporary database file.
    """

    db_path = test_data_dir / f"test_{uuid4()}.db"

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def assert_executed_orders():
    """
    Helper for asserting orders were executed correctly.
    """

    def _assert_orders(
        orders: List[Dict[str, Any]],
        expected_symbols: List[str],
        expected_sides: List[str],
        expected_quantities: List[float],
    ):
        """Assert orders match expectations."""
        assert len(orders) == len(expected_symbols)

        for i, order in enumerate(orders):
            assert order["symbol"] == expected_symbols[i]
            assert order["side"] == expected_sides[i]
            assert order["quantity"] == expected_quantities[i]

    return _assert_orders
