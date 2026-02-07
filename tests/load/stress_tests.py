"""
Load and stress tests for algoTrading system.

These tests validate system performance under high load conditions:
- 1000+ positions
- High order volume
- Memory stability
- Continuous operation
- Concurrent operations
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import MagicMock

import psutil
import pytest

from app.services.emergency_handler.emergency_closer import (
    EmergencyCloser,
    EmergencyCloseResult,
    EmergencyTrigger,
)
from app.services.position_monitor import MonitoredPosition, PositionMonitor, PositionMonitorConfig


class MockBroker:
    """Mock broker for load testing."""

    def __init__(self, latency_ms: float = 0):
        self.positions: List[Any] = []
        self.orders: List[Dict[str, Any]] = []
        self.current_prices: Dict[str, float] = {}
        self.latency_ms = latency_ms
        self.order_count = 0

    async def get_positions(self):
        """Get current positions."""
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
        return self.positions

    async def get_quote(self, symbol: str):
        """Get current quote."""
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

        quote = MagicMock()
        quote.last_price = self.current_prices.get(symbol, 100.0)
        return quote

    async def place_order(
        self, symbol: str, side: str, quantity: Decimal, order_type: str = "MARKET", **kwargs
    ):
        """Place an order."""
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


class MockPosition:
    """Mock position for load testing."""

    def __init__(
        self,
        symbol: str,
        quantity: Decimal,
        side: str = "LONG",
        current_price: Decimal = Decimal("100.00"),
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.side = side
        self.current_price = current_price


@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestPositionMonitorLoad:
    """Load tests for position monitor."""

    async def test_monitor_1000_positions(self):
        """Test monitoring 1000 positions simultaneously."""
        broker = MockBroker()

        # Create prices for 1000 symbols
        symbols = [f"STOCK{i:04d}" for i in range(1000)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=1.0,
            execute_stops_automatically=False,  # Don't actually execute
            log_all_checks=False,  # Disable verbose logging
        )

        monitor = PositionMonitor(broker, config=config)

        # Measure start time
        start_time = time.time()
        start_memory = get_memory_usage()

        # Start monitor
        await monitor.start()

        # Add 1000 positions
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
        assert len(monitor.get_monitored_positions()) == 1000

        # Let monitor run for 5 cycles
        await asyncio.sleep(5.0)

        # Check statistics
        stats = monitor.get_statistics()
        assert stats["total_positions"] == 1000
        assert stats["total_checks"] >= 5

        # Stop monitor
        await monitor.stop()

        # Measure end time and memory
        end_time = time.time()
        end_memory = get_memory_usage()

        execution_time = end_time - start_time
        memory_increase = end_memory - start_memory

        # Log performance metrics
        print("\n=== 1000 Position Load Test Results ===")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Memory increase: {memory_increase:.2f} MB")
        print(f"Average check time: {stats['total_checks'] / execution_time:.2f} checks/second")
        print(f"Final memory: {end_memory:.2f} MB")

        # Performance assertions
        assert execution_time < 30.0  # Should complete in 30 seconds
        assert memory_increase < 500  # Memory increase should be reasonable (< 500MB)

    async def test_monitor_24_hours_stability(self):
        """Test monitor stability over simulated 24 hours."""
        broker = MockBroker()

        # Create 100 positions
        symbols = [f"STOCK{i:03d}" for i in range(100)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,  # Fast check for simulation
            execute_stops_automatically=False,
            log_all_checks=False,
        )

        monitor = PositionMonitor(broker, config=config)

        # Start monitor
        await monitor.start()

        # Add positions
        for i, symbol in enumerate(symbols):
            position = MonitoredPosition(
                position_id=f"pos_{i}",
                symbol=symbol,
                side="LONG",
                entry_price=Decimal("100"),
                quantity=Decimal("10"),
                current_price=Decimal("100"),
            )
            await monitor.add_position(position)

        # Simulate 24 hours of operation (accelerated)
        # With 0.1s check interval, 1 hour = 600 seconds of real time
        # We'll simulate 1 hour for testing (3600 seconds / 0.1 = 36000 checks)
        print("\n=== Starting 1-hour stability test (simulating 24h) ===")

        start_time = time.time()
        start_memory = get_memory_usage()
        checks_target = 3600  # 6 minutes at 0.1s interval

        while monitor.get_statistics()["total_checks"] < checks_target:
            await asyncio.sleep(1.0)

            # Check memory every minute
            current_memory = get_memory_usage()
            memory_increase = current_memory - start_memory

            if memory_increase > 1000:  # More than 1GB increase
                pytest.fail(f"Memory leak detected: {memory_increase:.2f} MB increase")

        end_time = time.time()
        end_memory = get_memory_usage()

        # Get final stats
        stats = monitor.get_statistics()

        await monitor.stop()

        execution_time = end_time - start_time
        memory_increase = end_memory - start_memory

        print("\n=== Stability Test Results ===")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Total checks: {stats['total_checks']}")
        print(f"Checks per second: {stats['total_checks'] / execution_time:.2f}")
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Assertions
        assert memory_increase < 500  # Memory increase should be minimal
        assert stats["total_checks"] >= checks_target

    async def test_high_frequency_price_updates(self):
        """Test monitor with high-frequency price updates."""
        broker = MockBroker()

        # Create 100 positions
        symbols = [f"STOCK{i:03d}" for i in range(100)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=0.01,  # Very fast check (100 checks/sec)
            execute_stops_automatically=False,
            log_all_checks=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions
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

        # Simulate rapid price changes
        start_time = time.time()

        for _ in range(100):  # 100 price update cycles
            # Update all prices
            for symbol in symbols:
                # Random price between 95 and 105
                import random

                broker.current_prices[symbol] = 95.0 + random.random() * 10.0

            # Wait for monitor to check
            await asyncio.sleep(0.05)

        end_time = time.time()

        stats = monitor.get_statistics()

        await monitor.stop()

        execution_time = end_time - start_time

        print("\n=== High-Frequency Update Test Results ===")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Total checks: {stats['total_checks']}")
        print(f"Checks per second: {stats['total_checks'] / execution_time:.2f}")

        # Should handle high frequency without issues
        assert stats["total_checks"] > 100


@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestEmergencyCloseLoad:
    """Load tests for emergency close."""

    async def test_emergency_close_1000_positions(self):
        """Test emergency close with 1000 positions."""
        broker = MockBroker()

        # Create 1000 positions
        for i in range(1000):
            position = MockPosition(
                symbol=f"STOCK{i:04d}",
                quantity=Decimal("100"),
            )
            broker.positions.append(position)

        closer = EmergencyCloser(broker)

        start_time = time.time()

        result = await closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        end_time = time.time()

        execution_time = end_time - start_time

        print("\n=== Emergency Close 1000 Positions ===")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Closed positions: {result.closed_positions}")
        print(f"Time per position: {execution_time / result.closed_positions * 1000:.2f} ms")

        # Assertions
        assert result.success is True
        assert result.closed_positions == 1000
        assert execution_time < 60.0  # Should complete in under 1 minute
        assert execution_time / result.closed_positions < 0.1  # < 100ms per position

    async def test_emergency_close_concurrent(self):
        """Test concurrent emergency close operations."""
        broker = MockBroker()

        # Create 500 positions
        for i in range(500):
            position = MockPosition(
                symbol=f"STOCK{i:03d}",
                quantity=Decimal("100"),
            )
            broker.positions.append(position)

        closer = EmergencyCloser(broker)

        # Try to trigger multiple concurrent closes
        # Only one should succeed
        tasks = [closer.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER) for _ in range(5)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful closes
        successful = sum(1 for r in results if isinstance(r, EmergencyCloseResult) and r.success)
        failed = sum(1 for r in results if isinstance(r, EmergencyCloseResult) and not r.success)

        print("\n=== Concurrent Emergency Close ===")
        print(f"Successful: {successful}")
        print(f"Failed (expected): {failed}")

        # Only one should succeed
        assert successful == 1
        assert failed == 4


@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestSystemMemoryStability:
    """Test system memory stability under load."""

    async def test_memory_stability_continuous_operation(self):
        """Test memory stability over continuous operation."""
        broker = MockBroker()

        # Create 500 positions
        symbols = [f"STOCK{i:03d}" for i in range(500)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=False,
            log_all_checks=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions
        for i, symbol in enumerate(symbols):
            position = MonitoredPosition(
                position_id=f"pos_{i}",
                symbol=symbol,
                side="LONG",
                entry_price=Decimal("100"),
                quantity=Decimal("10"),
                current_price=Decimal("100"),
            )
            await monitor.add_position(position)

        # Track memory over time
        memory_samples = []
        sample_interval = 10  # Sample every 10 seconds
        duration = 60  # Run for 1 minute

        start_time = time.time()

        while (time.time() - start_time) < duration:
            await asyncio.sleep(sample_interval)

            current_memory = get_memory_usage()
            memory_samples.append(current_memory)

            print(f"Memory at {time.time() - start_time:.0f}s: {current_memory:.2f} MB")

        await monitor.stop()

        # Analyze memory trend
        initial_memory = memory_samples[0]
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        memory_increase = final_memory - initial_memory

        print("\n=== Memory Stability Test Results ===")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Max memory: {max_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        print(f"Memory samples: {len(memory_samples)}")

        # Check for memory leaks
        # Memory increase should be minimal (less than 200MB over 1 minute)
        assert (
            memory_increase < 200
        ), f"Potential memory leak detected: {memory_increase:.2f} MB increase"

    async def test_memory_with_position_add_remove(self):
        """Test memory when adding and removing positions."""
        broker = MockBroker()

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=False,
            log_all_checks=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        start_memory = get_memory_usage()

        # Add and remove positions 100 times
        for cycle in range(100):
            # Add 10 positions
            for i in range(10):
                position = MonitoredPosition(
                    position_id=f"cycle{cycle}_pos{i}",
                    symbol=f"STOCK{i}",
                    side="LONG",
                    entry_price=Decimal("100"),
                    quantity=Decimal("10"),
                    current_price=Decimal("100"),
                )
                await monitor.add_position(position)

            # Remove all positions
            for i in range(10):
                await monitor.remove_position(f"cycle{cycle}_pos{i}")

            # Check memory every 10 cycles
            if cycle % 10 == 0:
                current_memory = get_memory_usage()
                memory_increase = current_memory - start_memory
                print(
                    f"Cycle {cycle}: Memory = {current_memory:.2f} MB (+{memory_increase:.2f} MB)"
                )

        end_memory = get_memory_usage()
        memory_increase = end_memory - start_memory

        print("\n=== Add/Remove Memory Test Results ===")
        print(f"Start memory: {start_memory:.2f} MB")
        print(f"End memory: {end_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

        await monitor.stop()

        # Memory should be stable (minimal increase)
        assert memory_increase < 100, f"Memory leak detected: {memory_increase:.2f} MB increase"


def get_memory_usage() -> float:
    """
    Get current process memory usage in MB.

    Returns:
        Memory usage in megabytes
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # Convert to MB


@pytest.mark.asyncio
@pytest.mark.load
class TestConcurrencyPerformance:
    """Test concurrent operation performance."""

    async def test_concurrent_price_fetches(self):
        """Test concurrent price fetching performance."""
        broker = MockBroker(latency_ms=10)  # Simulate 10ms latency

        # Create 100 positions
        symbols = [f"STOCK{i:03d}" for i in range(100)]
        for symbol in symbols:
            broker.current_prices[symbol] = 100.0

        config = PositionMonitorConfig(
            check_interval_seconds=0.1,
            execute_stops_automatically=False,
            log_all_checks=False,
        )

        monitor = PositionMonitor(broker, config=config)
        await monitor.start()

        # Add positions
        for i, symbol in enumerate(symbols):
            position = MonitoredPosition(
                position_id=f"pos_{i}",
                symbol=symbol,
                side="LONG",
                entry_price=Decimal("100"),
                quantity=Decimal("10"),
                current_price=Decimal("100"),
            )
            await monitor.add_position(position)

        # Measure check performance
        start_time = time.time()

        # Run 10 checks
        for _ in range(10):
            await asyncio.sleep(0.15)  # Wait for check cycle

        end_time = time.time()

        stats = monitor.get_statistics()

        await monitor.stop()

        execution_time = end_time - start_time
        avg_check_time = execution_time / stats["total_checks"]

        print("\n=== Concurrent Price Fetch Performance ===")
        print(f"Total checks: {stats['total_checks']}")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Average check time: {avg_check_time * 1000:.2f} ms")

        # With 10ms latency per symbol, 100 symbols would take 1000ms serial
        # Concurrent should be much faster
        assert avg_check_time < 0.5  # Should be under 500ms per check


if __name__ == "__main__":
    # Run a quick load test
    pytest.main([__file__, "-v", "-s", "-m", "load"])
