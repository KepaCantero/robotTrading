"""
Tests for Trading Metrics Monitoring Module.

Tests the implementation of trading-specific SRE metrics:
- Order execution latency tracking
- Fill rate monitoring
- Slippage analysis
- Position synchronization health
- Market data freshness
- Strategy health scoring
- Risk limit compliance
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from app.sre.monitoring.trading_metrics import (
    OrderRecord,
    TradingHealthStatus,
    TradingMetrics,
    TradingMetricsConfig,
    TradingMetricsMonitor,
    get_trading_metrics_monitor,
)


class TestOrderRecord:
    """Test order record functionality."""

    def test_order_creation(self):
        """Test creating an order record."""
        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )

        assert order.order_id == "test_order"
        assert order.symbol == "AAPL"
        assert order.status == "pending"
        assert order.fill_price is None

    def test_latency_calculation(self):
        """Test order latency calculation."""
        submitted = datetime.utcnow()
        filled = submitted + timedelta(milliseconds=250)

        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=submitted,
            filled_at=filled,
        )

        latency = order.get_latency_ms()
        assert latency is not None
        assert 240 <= latency <= 260  # Allow some tolerance

    def test_latency_no_fill(self):
        """Test latency calculation when order not filled."""
        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )

        assert order.get_latency_ms() is None

    def test_slippage_calculation(self):
        """Test slippage calculation in basis points."""
        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
            fill_price=150.05,
        )

        slippage = order.get_slippage_bps()
        assert slippage is not None
        # 0.05 / 150.0 * 10000 = 3.33 bps
        assert 3.0 <= slippage <= 4.0

    def test_negative_slippage(self):
        """Test negative (favorable) slippage."""
        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
            fill_price=149.95,
        )

        slippage = order.get_slippage_bps()
        assert slippage is not None
        assert slippage < 0  # Negative slippage (favorable)


class TestTradingMetricsConfig:
    """Test trading metrics configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TradingMetricsConfig()

        assert config.fill_rate_warning_pct == 95.0
        assert config.slippage_warning_bps == 5.0
        assert config.order_latency_warning_ms == 500.0
        assert config.collection_interval_seconds == 60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TradingMetricsConfig(
            fill_rate_warning_pct=98.0,
            slippage_warning_bps=2.0,
        )

        assert config.fill_rate_warning_pct == 98.0
        assert config.slippage_warning_bps == 2.0


@pytest.mark.asyncio
class TestTradingMetricsMonitor:
    """Test trading metrics monitor functionality."""

    @pytest.fixture
    async def monitor(self):
        """Create a monitor instance."""
        config = TradingMetricsConfig(
            collection_interval_seconds=1,
        )
        monitor = TradingMetricsMonitor(config=config)
        await monitor.initialize()
        yield monitor
        await monitor.stop_collection()

    async def test_initialize(self, monitor):
        """Test monitor initialization."""
        assert monitor._current_health == TradingHealthStatus.HEALTHY
        assert len(monitor._orders) == 0

    async def test_record_order(self, monitor):
        """Test recording an order."""
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )

        assert order_id in monitor._orders
        assert monitor._orders[order_id].symbol == "AAPL"

    async def test_update_order_fill(self, monitor):
        """Test updating order with fill information."""
        submitted = datetime.utcnow()
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=submitted,
        )

        filled = submitted + timedelta(milliseconds=200)
        monitor.update_order_fill(
            order_id=order_id,
            fill_price=150.05,
            filled_at=filled,
        )

        order = monitor._orders[order_id]
        assert order.status == "filled"
        assert order.fill_price == 150.05
        assert len(monitor._order_latencies) == 1
        assert len(monitor._slippages) == 1

    async def test_update_order_rejection(self, monitor):
        """Test updating order as rejected."""
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )

        monitor.update_order_rejection(order_id, "Insufficient funds")

        order = monitor._orders[order_id]
        assert order.status == "rejected"
        assert order.rejection_reason == "Insufficient funds"

    async def test_update_position_sync(self, monitor):
        """Test updating position synchronization."""
        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_broker_position("AAPL", 100.0)

        assert monitor._internal_positions["AAPL"] == 100.0
        assert monitor._broker_positions["AAPL"] == 100.0

    async def test_position_mismatch(self, monitor):
        """Test position mismatch detection."""
        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_broker_position("AAPL", 95.0)

        sync_health = monitor.check_position_sync()
        assert sync_health < 100.0

    async def test_update_market_data(self, monitor):
        """Test updating market data timestamps."""
        monitor.update_market_data_timestamp(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            latency_ms=50.0,
        )

        assert "AAPL" in monitor._market_data_timestamps
        assert len(monitor._market_data_latencies) == 1

    async def test_update_strategy_health(self, monitor):
        """Test updating strategy health scores."""
        monitor.update_strategy_health("momentum", 85.0)
        monitor.update_strategy_health("mean_reversion", 72.0)

        assert monitor._strategy_health["momentum"] == 85.0
        assert monitor._strategy_health["mean_reversion"] == 72.0

    async def test_update_risk_limit(self, monitor):
        """Test updating risk limit utilization."""
        monitor.update_risk_limit("max_exposure", utilization_pct=75.0, critical=False)
        monitor.update_risk_limit("leverage", utilization_pct=95.0, critical=True)

        assert monitor._risk_limits["max_exposure"]["utilization_pct"] == 75.0
        assert monitor._risk_limits["leverage"]["critical"] is True

    async def test_calculate_fill_rate(self, monitor):
        """Test fill rate calculation."""
        # Record 10 orders
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )

            # Fill 8 of them
            if i < 8:
                monitor.update_order_fill(
                    order_id=order_id,
                    fill_price=150.0,
                    filled_at=datetime.utcnow(),
                )

        fill_rate = monitor.calculate_fill_rate()
        assert fill_rate == 80.0

    async def test_calculate_slippage(self, monitor):
        """Test slippage calculation."""
        for i in range(5):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )

            monitor.update_order_fill(
                order_id=order_id,
                fill_price=150.05 + (i * 0.01),
                filled_at=datetime.utcnow(),
            )

        avg_slippage = monitor.calculate_slippage()
        assert avg_slippage > 0

    async def test_collect_order_execution_metrics(self, monitor):
        """Test collecting order execution metrics."""
        # Record some orders
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )
            if i < 8:
                monitor.update_order_fill(
                    order_id=order_id,
                    fill_price=150.0,
                    filled_at=datetime.utcnow(),
                )

        metrics = await monitor._collect_order_execution_metrics()

        assert metrics.total_orders == 10
        assert metrics.filled_orders == 8
        assert metrics.fill_rate_pct == 80.0

    async def test_collect_slippage_metrics(self, monitor):
        """Test collecting slippage metrics."""
        # Record orders with different slippages
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )
            monitor.update_order_fill(
                order_id=order_id,
                fill_price=150.02,
                filled_at=datetime.utcnow(),
            )

        metrics = await monitor._collect_slippage_metrics()

        assert metrics.avg_slippage_bps > 0
        assert metrics.total_quotes == 0  # No market data yet

    async def test_collect_position_sync_metrics(self, monitor):
        """Test collecting position sync metrics."""
        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_internal_position("MSFT", 50.0)
        monitor.update_broker_position("AAPL", 100.0)
        monitor.update_broker_position("MSFT", 50.0)

        metrics = await monitor._collect_position_sync_metrics()

        assert metrics.total_positions == 2
        assert metrics.synced_positions == 2
        assert metrics.sync_health_pct == 100.0

    async def test_collect_position_sync_mismatch(self, monitor):
        """Test position sync with mismatches."""
        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_internal_position("MSFT", 50.0)
        monitor.update_broker_position("AAPL", 95.0)  # Mismatch
        monitor.update_broker_position("TSLA", 25.0)  # Ghost position

        metrics = await monitor._collect_position_sync_metrics()

        assert metrics.mismatched_positions == 1
        assert metrics.ghost_positions == 1
        assert metrics.sync_health_pct < 100.0

    async def test_collect_market_data_metrics(self, monitor):
        """Test collecting market data metrics."""
        now = datetime.utcnow()
        monitor.update_market_data_timestamp("AAPL", now, latency_ms=50.0)
        monitor.update_market_data_timestamp("MSFT", now, latency_ms=75.0)

        metrics = await monitor._collect_market_data_metrics()

        assert metrics.total_quotes == 2
        assert metrics.data_freshness_pct == 100.0

    async def test_collect_stale_market_data(self, monitor):
        """Test collecting stale market data metrics."""
        now = datetime.utcnow()
        old = now - timedelta(seconds=10)

        monitor.update_market_data_timestamp("AAPL", now, latency_ms=50.0)
        monitor.update_market_data_timestamp("MSFT", old, latency_ms=75.0)

        metrics = await monitor._collect_market_data_metrics()

        assert metrics.stale_data_count == 1
        assert metrics.data_freshness_pct < 100.0

    async def test_collect_strategy_health_metrics(self, monitor):
        """Test collecting strategy health metrics."""
        monitor.update_strategy_health("momentum", 85.0)
        monitor.update_strategy_health("mean_reversion", 72.0)
        monitor.update_strategy_health("arbitrage", 45.0)

        metrics = await monitor._collect_strategy_health_metrics()

        assert metrics.active_strategies == 3
        assert metrics.healthy_strategies == 1
        assert metrics.degraded_strategies == 1
        assert metrics.critical_strategies == 1

    async def test_collect_risk_limit_metrics(self, monitor):
        """Test collecting risk limit metrics."""
        monitor.update_risk_limit("exposure", utilization_pct=80.0, critical=False)
        monitor.update_risk_limit("leverage", utilization_pct=95.0, critical=False)
        monitor.update_risk_limit("var", utilization_pct=105.0, critical=True)

        metrics = await monitor._collect_risk_limit_metrics()

        assert metrics.total_limits == 3
        assert metrics.limits_compliant == 1
        assert metrics.limits_warning == 1
        assert metrics.limits_violated == 1
        assert metrics.critical_violations == 1

    async def test_evaluate_overall_health_optimal(self, monitor):
        """Test health evaluation when everything is optimal."""
        # Set up good metrics
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )
            monitor.update_order_fill(
                order_id=order_id,
                fill_price=150.0,
                filled_at=datetime.utcnow(),
            )

        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_broker_position("AAPL", 100.0)
        monitor.update_strategy_health("momentum", 90.0)

        metrics = await monitor.collect_metrics()

        assert metrics.overall_health in [
            TradingHealthStatus.OPTIMAL,
            TradingHealthStatus.HEALTHY,
        ]

    async def test_evaluate_overall_health_critical(self, monitor):
        """Test health evaluation when system is critical."""
        # Set up bad metrics
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )
            # Only fill 50% (below critical threshold)
            if i < 5:
                monitor.update_order_fill(
                    order_id=order_id,
                    fill_price=152.0,  # High slippage
                    filled_at=datetime.utcnow(),
                )

        metrics = await monitor.collect_metrics()

        # Should be critical or degraded due to low fill rate
        assert metrics.overall_health in [
            TradingHealthStatus.CRITICAL,
            TradingHealthStatus.DEGRADED,
        ]

    async def test_collect_metrics(self, monitor):
        """Test collecting all metrics."""
        # Set up some data
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )
        monitor.update_order_fill(
            order_id=order_id,
            fill_price=150.0,
            filled_at=datetime.utcnow(),
        )

        monitor.update_internal_position("AAPL", 100.0)
        monitor.update_broker_position("AAPL", 100.0)
        monitor.update_strategy_health("momentum", 85.0)

        metrics = await monitor.collect_metrics()

        assert isinstance(metrics, TradingMetrics)
        assert metrics.overall_health in TradingHealthStatus

    async def test_get_current_metrics(self, monitor):
        """Test getting current metrics."""
        await monitor.collect_metrics()

        current = await monitor.get_current_metrics()

        assert current is not None
        assert isinstance(current, TradingMetrics)

    async def test_get_metrics_summary(self, monitor):
        """Test getting metrics summary."""
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )
        monitor.update_order_fill(
            order_id=order_id,
            fill_price=150.0,
            filled_at=datetime.utcnow(),
        )

        await monitor.collect_metrics()

        summary = await monitor.get_metrics_summary()

        assert "overall_health" in summary
        assert "order_execution" in summary
        assert "slippage" in summary
        assert "position_sync" in summary
        assert "market_data" in summary
        assert "strategy_health" in summary
        assert "risk_limits" in summary

    async def test_health_status_change(self, monitor):
        """Test health status change detection."""
        changes = []

        def on_health_change(old_health, new_health):
            changes.append((old_health, new_health))

        monitor.config.on_health_change = on_health_change

        # Start healthy
        await monitor.collect_metrics()

        # Create critical condition
        for i in range(10):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )
            if i < 4:  # Only 40% fill rate
                monitor.update_order_fill(
                    order_id=order_id,
                    fill_price=150.0,
                    filled_at=datetime.utcnow(),
                )

        await monitor.collect_metrics()

        # Should have detected health change
        assert len(changes) > 0

    async def test_start_stop_collection(self, monitor):
        """Test starting and stopping collection."""
        await monitor.start_collection()
        assert monitor._is_running is True

        await asyncio.sleep(0.1)  # Let collection run

        await monitor.stop_collection()
        assert monitor._is_running is False


class TestTradingMetricsSingleton:
    """Test trading metrics monitor singleton pattern."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        monitor1 = get_trading_metrics_monitor()
        monitor2 = get_trading_metrics_monitor()

        # Should return same instance
        assert monitor1 is monitor2

    def test_custom_config_singleton(self):
        """Test that custom config is only used on first call."""
        config1 = TradingMetricsConfig(fill_rate_warning_pct=98.0)
        config2 = TradingMetricsConfig(fill_rate_warning_pct=95.0)

        monitor1 = get_trading_metrics_monitor(config=config1)
        monitor2 = get_trading_metrics_monitor(config=config2)

        # Same instance
        assert monitor1 is monitor2
        # First config is used
        assert monitor1.config.fill_rate_warning_pct == 98.0


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for trading metrics monitoring."""

    async def test_full_trading_workflow(self):
        """Test complete trading monitoring workflow."""
        # Create monitor
        config = TradingMetricsConfig(collection_interval_seconds=1)
        monitor = get_trading_metrics_monitor(config=config)
        await monitor.initialize()

        # Start collection
        await monitor.start_collection()

        # Simulate trading activity
        for i in range(20):
            order_id = monitor.record_order(
                symbol="AAPL",
                side="buy" if i % 2 == 0 else "sell",
                quantity=100.0,
                expected_price=150.0,
                submitted_at=datetime.utcnow(),
            )

            # Fill most orders
            if i % 5 != 0:  # 80% fill rate
                monitor.update_order_fill(
                    order_id=order_id,
                    fill_price=150.02 + (i * 0.001),
                    filled_at=datetime.utcnow(),
                )

        # Update positions
        monitor.update_internal_position("AAPL", 1000.0)
        monitor.update_broker_position("AAPL", 995.0)

        # Update market data
        monitor.update_market_data_timestamp(
            "AAPL",
            datetime.utcnow(),
            latency_ms=50.0,
        )

        # Update strategy health
        monitor.update_strategy_health("momentum", 78.0)

        # Update risk limits
        monitor.update_risk_limit("exposure", utilization_pct=82.0, critical=False)

        # Wait for collection
        await asyncio.sleep(2)

        # Get metrics
        metrics = await monitor.get_current_metrics()
        assert metrics is not None

        # Get summary
        summary = await monitor.get_metrics_summary()
        assert "overall_health" in summary

        # Check calculated metrics
        fill_rate = monitor.calculate_fill_rate()
        assert 75.0 <= fill_rate <= 85.0

        slippage = monitor.calculate_slippage()
        assert isinstance(slippage, float)

        sync_health = monitor.check_position_sync()
        assert 0.0 <= sync_health <= 100.0

        # Stop collection
        await monitor.stop_collection()

    async def test_error_handling(self):
        """Test error handling in monitor."""
        monitor = TradingMetricsMonitor()

        # Update unknown order
        monitor.update_order_fill("unknown", 150.0, datetime.utcnow())
        # Should not raise, just log warning

        # Update with invalid data
        monitor.update_strategy_health("test", 150.0)  # Above 100
        # Should clamp to 100
        assert monitor._strategy_health["test"] == 100.0

        monitor.update_strategy_health("test2", -10.0)  # Below 0
        # Should clamp to 0
        assert monitor._strategy_health["test2"] == 0.0

    async def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        monitor = TradingMetricsMonitor()

        # Add some data
        order_id = monitor.record_order(
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_price=150.0,
            submitted_at=datetime.utcnow(),
        )
        monitor.update_order_fill(
            order_id=order_id,
            fill_price=150.02,
            filled_at=datetime.utcnow(),
        )

        metrics = await monitor.collect_metrics()
        metrics_dict = metrics.to_dict()

        assert "order_execution" in metrics_dict
        assert "slippage" in metrics_dict
        assert "position_sync" in metrics_dict
        assert "market_data" in metrics_dict
        assert "strategy_health" in metrics_dict
        assert "risk_limits" in metrics_dict
        assert "overall_health" in metrics_dict
        assert "collected_at" in metrics_dict

    async def test_empty_metrics(self):
        """Test metrics with no data."""
        monitor = TradingMetricsMonitor()
        await monitor.initialize()

        metrics = await monitor.collect_metrics()

        # Should return zeros/defaults for empty data
        assert metrics.order_execution.total_orders == 0
        assert metrics.order_execution.fill_rate_pct == 100.0  # Default
        assert metrics.slippage.avg_slippage_bps == 0.0
