"""
Integration tests for BrokerFailoverManager.

Tests end-to-end failover scenarios with real broker adapters.
"""

import asyncio
from decimal import Decimal
from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from app.services.broker_failover import (
    BrokerConfig,
    BrokerFailoverManager,
    BrokerHealth,
)
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerPosition,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)

# Import PaperAdapter directly to avoid import errors from other adapters
from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter


class TestBrokerFailoverIntegration:
    """Integration tests for broker failover manager."""

    @pytest.fixture
    def paper_adapter_1(self):
        """Create first paper adapter."""
        adapter = PaperAdapter(initial_cash=Decimal("100000"))
        adapter.auto_fill_orders = True
        return adapter

    @pytest.fixture
    def paper_adapter_2(self):
        """Create second paper adapter."""
        adapter = PaperAdapter(initial_cash=Decimal("100000"))
        adapter.auto_fill_orders = True
        return adapter

    @pytest.fixture
    def broker_configs(self, paper_adapter_1, paper_adapter_2):
        """Create broker configurations."""
        return [
            BrokerConfig(
                name="paper_primary",
                broker=paper_adapter_1,
                priority=1,
                enabled=True,
            ),
            BrokerConfig(
                name="paper_secondary",
                broker=paper_adapter_2,
                priority=2,
                enabled=True,
            ),
        ]

    @pytest.fixture
    def failover_tracker(self):
        """Create failover event tracker."""
        tracker = {
            "failovers": [],
        }

        def _callback(from_broker: str, to_broker: str):
            tracker["failovers"].append(
                {
                    "from": from_broker,
                    "to": to_broker,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )

        return _callback, tracker

    @pytest.mark.asyncio
    async def test_full_failover_lifecycle(
        self, broker_configs, paper_adapter_1, paper_adapter_2
    ):
        """Test complete failover lifecycle: start, fail, recover."""
        failover_events = []

        def on_failover(from_broker: str, to_broker: str):
            failover_events.append({"from": from_broker, "to": to_broker})

        manager = BrokerFailoverManager(
            brokers=broker_configs,
            on_failover=on_failover,
            health_check_interval=1.0,  # Fast checks for testing
        )

        # Start monitoring
        await manager.start()

        # Verify primary is active
        assert manager.get_active_broker_name() == "paper_primary"

        # Execute order on primary
        result = await manager.execute_order_with_failover(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
        )
        assert result is not None

        # Simulate primary failure by making it disconnect
        await paper_adapter_1.disconnect()

        # Health check should detect failure and failover
        await asyncio.sleep(2.0)  # Wait for health check

        # Verify failover occurred
        assert manager.get_active_broker_name() == "paper_secondary"
        assert len(failover_events) > 0
        assert failover_events[-1]["from"] == "paper_primary"
        assert failover_events[-1]["to"] == "paper_secondary"

        # Execute order on secondary
        result = await manager.execute_order_with_failover(
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("50"),
        )
        assert result is not None

        # Cleanup
        await manager.stop()

    @pytest.mark.asyncio
    async def test_position_sync_across_brokers(
        self, broker_configs, paper_adapter_1, paper_adapter_2
    ):
        """Test syncing positions across multiple brokers."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Connect both brokers
        await paper_adapter_1.connect()
        await paper_adapter_2.connect()

        # Create positions on both brokers
        await paper_adapter_1.place_order(
            symbol="AAPL", side=OrderSide.BUY, quantity=Decimal("100")
        )

        await paper_adapter_2.place_order(
            symbol="MSFT", side=OrderSide.BUY, quantity=Decimal("50")
        )

        # Sync positions
        positions = await manager.sync_positions()

        assert "paper_primary" in positions
        assert "paper_secondary" in positions
        assert "AAPL" in positions["paper_primary"]
        assert "MSFT" in positions["paper_secondary"]

    @pytest.mark.asyncio
    async def test_account_info_failover(self, broker_configs, paper_adapter_1):
        """Test getting account info with failover."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        # Get account info from active broker
        account = await manager.get_account_info()
        assert account is not None
        assert account.cash_available == Decimal("100000")

    @pytest.mark.asyncio
    async def test_concurrent_order_execution(self, broker_configs):
        """Test concurrent order execution with failover."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Execute multiple orders concurrently
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

        tasks = [
            manager.execute_order_with_failover(
                symbol=symbol,
                side="BUY",
                quantity=Decimal("10"),
            )
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks)

        # All orders should succeed
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_manual_failover(self, broker_configs):
        """Test manual failover between brokers."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Set primary as active
        manager._active_broker = broker_configs[0]

        # Manually failover to secondary
        result = await manager.force_failover("paper_secondary")

        assert result is True
        assert manager.get_active_broker_name() == "paper_secondary"

    @pytest.mark.asyncio
    async def test_enable_disable_brokers(self, broker_configs):
        """Test enabling and disabling brokers."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Disable secondary broker
        result = manager.disable_broker("paper_secondary")
        assert result is True
        assert broker_configs[1].enabled is False

        # Enable it back
        result = manager.enable_broker("paper_secondary")
        assert result is True
        assert broker_configs[1].enabled is True

    @pytest.mark.asyncio
    async def test_health_report_generation(self, broker_configs):
        """Test generating comprehensive health report."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        report = manager.get_health_report()

        assert "timestamp" in report
        assert report["active_broker"] == "paper_primary"
        assert "brokers" in report
        assert "paper_primary" in report["brokers"]
        assert "paper_secondary" in report["brokers"]

        # Check broker state details
        primary_state = report["brokers"]["paper_primary"]
        assert primary_state["name"] == "paper_primary"
        assert primary_state["is_primary"] is True
        assert "health" in primary_state

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, broker_configs):
        """Test failover statistics tracking."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        stats = manager.get_statistics()

        assert stats["active_broker"] == "paper_primary"
        assert stats["total_brokers"] == 2
        assert "healthy_brokers" in stats
        assert "unhealthy_brokers" in stats

    @pytest.mark.asyncio
    async def test_order_execution_with_different_types(self, broker_configs):
        """Test order execution with different order types."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        # Test MARKET order
        result = await manager.execute_order_with_failover(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        assert result is not None

        # Test LIMIT order
        result = await manager.execute_order_with_failover(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="LIMIT",
            price=Decimal("150.00"),
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_broker_state_persistence(self, broker_configs):
        """Test that broker states persist through operations."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        initial_states = manager.get_broker_states()

        # Perform some operations
        await manager.sync_positions()
        await manager.get_account_info()

        # States should still be accessible
        final_states = manager.get_broker_states()
        assert len(initial_states) == len(final_states)

    @pytest.mark.asyncio
    async def test_multiple_failover_cycles(self, broker_configs):
        """Test multiple failover cycles."""
        failover_count = {"count": 0}

        def on_failover(from_broker: str, to_broker: str):
            failover_count["count"] += 1

        manager = BrokerFailoverManager(
            brokers=broker_configs,
            on_failover=on_failover,
            health_check_interval=1.0,
        )

        await manager.start()

        # Trigger first failover
        await manager.force_failover("paper_secondary")
        assert failover_count["count"] == 1

        # Trigger second failover
        await manager.force_failover("paper_primary")
        assert failover_count["count"] == 2

        # Cleanup
        await manager.stop()

    @pytest.mark.asyncio
    async def test_get_active_broker_methods(self, broker_configs):
        """Test different methods to get active broker."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        # Test get_active_broker
        active_broker = manager.get_active_broker()
        assert active_broker is not None
        assert hasattr(active_broker, "place_order")

        # Test get_active_broker_name
        active_name = manager.get_active_broker_name()
        assert active_name == "paper_primary"

    @pytest.mark.asyncio
    async def test_sell_order_execution(self, broker_configs):
        """Test sell order execution with failover."""
        manager = BrokerFailoverManager(brokers=broker_configs)
        manager._active_broker = broker_configs[0]

        # First buy to establish position
        await manager.execute_order_with_failover(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
        )

        # Then sell
        result = await manager.execute_order_with_failover(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("50"),
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_disabled_broker_not_used(self, broker_configs, paper_adapter_2):
        """Test that disabled brokers are not used for failover."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Disable secondary broker
        broker_configs[1].enabled = False

        # Try to failover to disabled broker
        result = await manager.force_failover("paper_secondary")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_broker_states_consistency(self, broker_configs):
        """Test that broker states remain consistent."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        states1 = manager.get_broker_states()
        states2 = manager.get_broker_states()

        # Should get same states (copied)
        assert len(states1) == len(states2)
        for name in states1:
            assert name in states2
            assert states1[name].name == states2[name].name

    @pytest.mark.asyncio
    async def test_health_check_interval_configurable(self, broker_configs):
        """Test that health check interval is configurable."""
        manager = BrokerFailoverManager(
            brokers=broker_configs,
            health_check_interval=5.0,
        )

        assert manager.health_check_interval == 5.0

        # Start and stop to verify interval is used
        await manager.start()
        await manager.stop()

    @pytest.mark.asyncio
    async def test_broker_priority_ordering(self, paper_adapter_1, paper_adapter_2):
        """Test that brokers are ordered by priority."""
        # Create configs with reversed priority
        broker_configs = [
            BrokerConfig(
                name="secondary_first",
                broker=paper_adapter_2,
                priority=2,
            ),
            BrokerConfig(
                name="primary_first",
                broker=paper_adapter_1,
                priority=1,
            ),
        ]

        manager = BrokerFailoverManager(brokers=broker_configs)

        # Should be sorted by priority (1 first)
        assert manager.brokers[0].name == "primary_first"
        assert manager.brokers[1].name == "secondary_first"

    @pytest.mark.asyncio
    async def test_consecutive_failure_tracking(self, broker_configs):
        """Test tracking of consecutive failures."""
        manager = BrokerFailoverManager(brokers=broker_configs)

        # Mark broker as unhealthy multiple times
        await manager._mark_broker_unhealthy("paper_primary", "Error 1")
        await manager._mark_broker_unhealthy("paper_primary", "Error 2")
        await manager._mark_broker_unhealthy("paper_primary", "Error 3")

        state = manager._broker_states["paper_primary"]
        assert state.consecutive_failures == 3
        assert state.total_failures == 3
        assert state.health == BrokerHealth.UNHEALTHY
