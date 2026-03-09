"""
Integration test for ExecutionEngineAdapter.

Tests the backtesting execution flow through ExecutionEngineAdapter:
1. Order placement via adapter
2. Integration with PessimisticExecutionEngine
3. Trade result handling
4. Position tracking
5. Commission calculation
6. Slippage application

This is an INTEGRATION test - it tests the complete execution flow
with real PessimisticExecutionEngine (not mocked).
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.services.execution.execution_adapter import ExecutionEngineAdapter


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_adapter():
    """Create ExecutionEngineAdapter instance."""
    return ExecutionEngineAdapter(enable_logging=False)


@pytest.fixture
def sample_signal():
    """Create sample trade signal."""
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.alerting_system import AlertSeverity

    return TradeSignal(
        signal_id="test_exec_001",
        alert_id="test_alert_exec_001",
        alert_rule_id="test_rule",
        symbol="AAPL",
        signal_type=TradeSignalType.LONG,
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100"),
        price=Decimal("150"),
        severity=AlertSeverity.WARNING,
        reason="Test signal for execution adapter integration",
    )


@pytest.fixture
def sell_signal():
    """Create sample SELL signal."""
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.alerting_system import AlertSeverity

    return TradeSignal(
        signal_id="test_exec_002",
        alert_id="test_alert_exec_002",
        alert_rule_id="test_rule",
        symbol="AAPL",
        signal_type=TradeSignalType.SHORT,
        order_side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("50"),
        price=Decimal("150"),
        severity=AlertSeverity.WARNING,
        reason="Test SELL signal",
    )


# =============================================================================
# Tests: Order Execution
# =============================================================================


class TestOrderExecution:
    """Test order execution through ExecutionEngineAdapter."""

    @pytest.mark.asyncio
    async def test_execute_order_basic(self, execution_adapter, sample_signal):
        """Test basic order execution."""
        result = await execution_adapter.execute_order(sample_signal)

        assert result.success is True
        assert result.order_id is not None
        assert result.order_id.startswith("exec_")
        assert result.symbol == sample_signal.symbol
        assert result.side == "buy"  # OrderSide enum values are lowercase
        assert result.quantity == sample_signal.quantity
        assert result.status == "FILLED"
        assert result.execution_price > 0

    @pytest.mark.asyncio
    async def test_execute_order_with_limit_price(self, execution_adapter):
        """Test execution with limit order type."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signal = TradeSignal(
            signal_id="test_limit",
            alert_id="test_alert_limit",
            alert_rule_id="test_rule",
            symbol="AAPL",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150"),
            severity=AlertSeverity.WARNING,
            reason="Limit order test",
        )

        result = await execution_adapter.execute_order(signal)

        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_execute_sell_order(self, execution_adapter, sell_signal):
        """Test SELL order execution."""
        result = await execution_adapter.execute_order(sell_signal)

        assert result.success is True
        assert result.side == "sell"
        assert result.quantity == Decimal("50")

    @pytest.mark.asyncio
    async def test_execute_order_without_price(self, execution_adapter):
        """Test execution when price is not provided."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signal = TradeSignal(
            signal_id="test_no_price",
            alert_id="test_alert_no_price",
            alert_rule_id="test_rule",
            symbol="TSLA",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10"),
            price=None,  # No price provided
            severity=AlertSeverity.WARNING,
            reason="No price test",
        )

        result = await execution_adapter.execute_order(signal)

        # Should use default price
        assert result.success is True
        assert result.signal_price > 0


# =============================================================================
# Tests: Slippage Calculation
# =============================================================================


class TestSlippageCalculation:
    """Test slippage calculation in execution."""

    @pytest.mark.asyncio
    async def test_slippage_applied_buy_order(self, execution_adapter, sample_signal):
        """Test that slippage is applied correctly for BUY orders."""
        result = await execution_adapter.execute_order(sample_signal)

        # For BUY orders, execution price should be higher (worse for trader)
        # Default slippage is 5 bps (0.05%)
        expected_min_price = sample_signal.price * Decimal("1.0005")
        assert result.execution_price >= expected_min_price.quantize(Decimal("0.01"))

    @pytest.mark.asyncio
    async def test_slippage_applied_sell_order(self, execution_adapter, sell_signal):
        """Test that slippage is applied correctly for SELL orders."""
        result = await execution_adapter.execute_order(sell_signal)

        # For SELL orders, execution price should be lower (worse for trader)
        assert result.execution_price < sell_signal.price

    @pytest.mark.asyncio
    async def test_slippage_bps_value(self, execution_adapter):
        """Test that slippage bps is recorded correctly."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signal = TradeSignal(
            signal_id="test_slippage",
            alert_id="test_alert_slippage",
            alert_rule_id="test_rule",
            symbol="AAPL",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("100"),  # Round number for easier calculation
            severity=AlertSeverity.WARNING,
            reason="Slippage test",
        )

        result = await execution_adapter.execute_order(signal)

        # Default slippage is 5 bps
        assert result.slippage_bps == Decimal("5")

    @pytest.mark.asyncio
    async def test_slippage_calculation_accuracy(self, execution_adapter):
        """Test that slippage calculation is mathematically accurate."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signal = TradeSignal(
            signal_id="test_accuracy",
            alert_id="test_alert_accuracy",
            alert_rule_id="test_rule",
            symbol="AAPL",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("100"),
            severity=AlertSeverity.WARNING,
            reason="Accuracy test",
        )

        result = await execution_adapter.execute_order(signal)

        # Execution price = signal price * (1 + slippage_bps/10000)
        # = 100 * (1 + 5/10000) = 100 * 1.0005 = 100.05
        expected_price = Decimal("100") * (Decimal("1") + Decimal("5") / Decimal("10000"))
        assert result.execution_price == expected_price.quantize(Decimal("0.01"))


# =============================================================================
# Tests: Commission Calculation
# =============================================================================


class TestCommissionCalculation:
    """Test commission calculation in execution."""

    @pytest.mark.asyncio
    async def test_commission_charged(self, execution_adapter, sample_signal):
        """Test that commission is charged on execution."""
        result = await execution_adapter.execute_order(sample_signal)

        # Commission should be >= 0
        assert result.commission >= 0

    @pytest.mark.asyncio
    async def test_commission_consistency(self, execution_adapter):
        """Test that commission is consistent across similar orders."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signals = [
            TradeSignal(
                signal_id=f"test_comm_{i}",
                alert_id=f"test_alert_comm_{i}",
                alert_rule_id="test_rule",
                symbol="AAPL",
                signal_type=TradeSignalType.LONG,
                order_side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150"),
                severity=AlertSeverity.WARNING,
                reason="Commission test",
            )
            for i in range(3)
        ]

        results = []
        for signal in signals:
            result = await execution_adapter.execute_order(signal)
            results.append(result)

        # All commissions should be the same for identical orders
        commissions = [r.commission for r in results]
        assert len(set(commissions)) == 1


# =============================================================================
# Tests: Order Management
# =============================================================================


class TestOrderManagement:
    """Test order management operations."""

    @pytest.mark.asyncio
    async def test_cancel_order(self, execution_adapter, sample_signal):
        """Test order cancellation."""
        result = await execution_adapter.execute_order(sample_signal)
        order_id = result.order_id

        cancelled = await execution_adapter.cancel_order(order_id)
        assert cancelled is True

        # Verify status changed
        status = await execution_adapter.get_order_status(order_id)
        assert status == "CANCELLED"

    @pytest.mark.asyncio
    async def test_cancel_unknown_order(self, execution_adapter):
        """Test cancelling an unknown order."""
        result = await execution_adapter.cancel_order("unknown_order_123")
        assert result is True  # Idempotent

    @pytest.mark.asyncio
    async def test_modify_order(self, execution_adapter, sample_signal):
        """Test order modification."""
        result = await execution_adapter.execute_order(sample_signal)
        order_id = result.order_id

        new_price = Decimal("155")
        modified = await execution_adapter.modify_order(order_id, new_price)
        assert modified is True

    @pytest.mark.asyncio
    async def test_get_order_status(self, execution_adapter, sample_signal):
        """Test getting order status."""
        result = await execution_adapter.execute_order(sample_signal)
        order_id = result.order_id

        status = await execution_adapter.get_order_status(order_id)
        assert status == "FILLED"

    @pytest.mark.asyncio
    async def test_get_order_status_unknown(self, execution_adapter):
        """Test getting status of unknown order."""
        status = await execution_adapter.get_order_status("unknown_order_123")
        assert status == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_get_open_orders(self, execution_adapter):
        """Test retrieving open orders."""
        open_orders = await execution_adapter.get_open_orders()
        # In backtesting context, should be empty list
        assert open_orders == []


# =============================================================================
# Tests: Order History and Tracking
# =============================================================================


class TestOrderHistory:
    """Test order history tracking."""

    @pytest.mark.asyncio
    async def test_order_tracked_in_history(self, execution_adapter, sample_signal):
        """Test that executed orders are tracked in history."""
        result = await execution_adapter.execute_order(sample_signal)

        history = execution_adapter.get_order_history()
        assert result.order_id in history
        assert history[result.order_id]["symbol"] == "AAPL"
        assert history[result.order_id]["side"] == "buy"

    @pytest.mark.asyncio
    async def test_multiple_orders_in_history(self, execution_adapter):
        """Test that multiple orders are tracked."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signals = [
            TradeSignal(
                signal_id=f"test_hist_{i}",
                alert_id=f"test_alert_hist_{i}",
                alert_rule_id="test_rule",
                symbol=symbol,
                signal_type=TradeSignalType.LONG,
                order_side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150"),
                severity=AlertSeverity.WARNING,
                reason=f"History test {i}",
            )
            for i, symbol in enumerate(["AAPL", "MSFT", "TSLA"], 1)
        ]

        for signal in signals:
            await execution_adapter.execute_order(signal)

        history = execution_adapter.get_order_history()
        assert len(history) == 3


# =============================================================================
# Tests: Statistics
# =============================================================================


class TestExecutionStatistics:
    """Test execution statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_single_order(self, execution_adapter, sample_signal):
        """Test stats after single order."""
        await execution_adapter.execute_order(sample_signal)

        stats = execution_adapter.get_execution_stats()
        assert stats["total_orders"] == 1
        assert stats["total_slippage_bps"] > 0
        assert stats["avg_slippage_bps"] > 0

    @pytest.mark.asyncio
    async def test_stats_multiple_orders(self, execution_adapter):
        """Test stats after multiple orders."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signals = [
            TradeSignal(
                signal_id=f"test_stats_{i}",
                alert_id=f"test_alert_stats_{i}",
                alert_rule_id="test_rule",
                symbol="AAPL",
                signal_type=TradeSignalType.LONG,
                order_side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150"),
                severity=AlertSeverity.WARNING,
                reason=f"Stats test {i}",
            )
            for i in range(1, 4)
        ]

        for signal in signals:
            await execution_adapter.execute_order(signal)

        stats = execution_adapter.get_execution_stats()
        assert stats["total_orders"] == 3
        assert stats["total_slippage_bps"] == Decimal("15")  # 5 bps * 3
        assert stats["avg_slippage_bps"] == Decimal("5")


# =============================================================================
# Tests: Adapter Reset
# =============================================================================


class TestAdapterReset:
    """Test adapter reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_history(self, execution_adapter, sample_signal):
        """Test that reset clears order history."""
        await execution_adapter.execute_order(sample_signal)
        assert len(execution_adapter.get_order_history()) > 0

        execution_adapter.reset()
        assert len(execution_adapter.get_order_history()) == 0

    @pytest.mark.asyncio
    async def test_reset_clears_stats(self, execution_adapter, sample_signal):
        """Test that reset clears statistics."""
        await execution_adapter.execute_order(sample_signal)
        assert execution_adapter.get_execution_stats()["total_orders"] > 0

        execution_adapter.reset()
        stats = execution_adapter.get_execution_stats()
        assert stats["total_orders"] == 0
        assert stats["total_slippage_bps"] == Decimal("0")


# =============================================================================
# Tests: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in execution scenarios."""

    @pytest.mark.asyncio
    async def test_execution_with_zero_quantity(self, execution_adapter):
        """Test execution with zero quantity."""
        from app.services.live_trading.alert_to_trade_mapper import (
            TradeSignal,
            TradeSignalType,
        )
        from app.services.live_trading.broker_connector import OrderSide, OrderType
        from app.services.alerting_system import AlertSeverity

        signal = TradeSignal(
            signal_id="test_zero",
            alert_id="test_alert_zero",
            alert_rule_id="test_rule",
            symbol="AAPL",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0"),
            price=Decimal("150"),
            severity=AlertSeverity.WARNING,
            reason="Zero quantity test",
        )

        result = await execution_adapter.execute_order(signal)
        # Should handle gracefully
        assert result is not None


# =============================================================================
# Tests: PessimisticExecutionEngine Integration
# =============================================================================


class TestExecutionEngineIntegration:
    """Test integration with PessimisticExecutionEngine."""

    def test_adapter_has_execution_engine(self, execution_adapter):
        """Test that adapter has execution engine instance."""
        assert execution_adapter.execution_engine is not None
        from app.backtesting.engines.execution_engine import PessimisticExecutionEngine
        assert isinstance(execution_adapter.execution_engine, PessimisticExecutionEngine)

    def test_adapter_uses_custom_engine(self):
        """Test that adapter can use custom execution engine."""
        from app.backtesting.engines.execution_engine import PessimisticExecutionEngine

        custom_engine = PessimisticExecutionEngine()
        adapter = ExecutionEngineAdapter(execution_engine=custom_engine)

        assert adapter.execution_engine is custom_engine
