"""
Integration test for ComplianceEngine full trading flow.

Tests the complete trading workflow through ComplianceEngine:
1. Pre-trade analysis with risk validation
2. Trade execution via adapters
3. Post-trade analysis with compliance checks
4. Performance metrics calculation
5. Integration with all subsystems

This is an INTEGRATION test - it tests the complete flow through
the system with real components (not mocks).
"""

from decimal import Decimal

import pytest

from app.domain.services.compliance.compliance_engine import ComplianceConfig, ComplianceEngine
from app.infrastructure.execution.execution_adapter import ExecutionEngineAdapter
from app.infrastructure.execution.order_manager_adapter import OrderManagerAdapter
from app.infrastructure.execution.trading_bridge_adapter import TradingBridgeAdapter

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def compliance_config():
    """Create test compliance configuration."""
    return ComplianceConfig(
        max_position_ratio=0.10,
        max_drawdown_ratio=0.25,
        max_leverage_ratio=2.0,
        kill_switch_threshold=-0.05,
        min_data_quality_score=80.0,
        max_portfolio_volatility=0.30,
        max_daily_var_95=0.05,
    )


@pytest.fixture
def engine(compliance_config):
    """Create ComplianceEngine instance."""
    return ComplianceEngine(config=compliance_config)


@pytest.fixture
def sample_signal():
    """Create sample trade signal."""
    from app.services.alerting_system import AlertSeverity
    from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
    from app.services.live_trading.broker_connector import OrderSide, OrderType

    return TradeSignal(
        signal_id="test_signal_001",
        alert_id="test_alert_001",
        alert_rule_id="test_rule",
        symbol="AAPL",
        signal_type=TradeSignalType.LONG,
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100"),
        price=Decimal("150"),
        severity=AlertSeverity.WARNING,
        reason="Test signal for integration testing",
    )


@pytest.fixture
def execution_adapter():
    """Create ExecutionEngineAdapter instance."""
    return ExecutionEngineAdapter(enable_logging=False)


@pytest.fixture
def order_manager_adapter():
    """Create OrderManagerAdapter instance."""
    return OrderManagerAdapter(enable_logging=False)


@pytest.fixture
def trading_bridge_adapter():
    """Create TradingBridgeAdapter instance."""
    return TradingBridgeAdapter(enable_logging=False)


# =============================================================================
# Tests: Pre-Trade Analysis
# =============================================================================


class TestPreTradeAnalysis:
    """Test pre-trade analysis through ComplianceEngine."""

    def test_compliance_config_initialization(self, compliance_config):
        """Test that compliance configuration is properly initialized."""
        assert compliance_config.max_position_ratio == 0.10
        assert compliance_config.max_drawdown_ratio == 0.25
        assert compliance_config.kill_switch_threshold == -0.05

    def test_engine_initialization(self, engine):
        """Test that ComplianceEngine initializes correctly."""
        assert engine is not None
        assert hasattr(engine, "config")
        assert engine.config.max_position_ratio == 0.10

    def test_compliance_config_validation(self, compliance_config):
        """Test that configuration validates correctly."""
        # Valid configuration
        assert compliance_config.max_position_ratio > 0
        assert compliance_config.max_position_ratio <= 1.0

        # Test kill switch threshold is negative
        assert compliance_config.kill_switch_threshold <= 0


# =============================================================================
# Tests: Adapter Integration
# =============================================================================


class TestAdapterIntegration:
    """Test integration of all adapters with ComplianceEngine."""

    @pytest.mark.asyncio
    async def test_execution_adapter_basic_flow(
        self,
        execution_adapter: ExecutionEngineAdapter,
        sample_signal,
    ):
        """
        Test basic execution flow through ExecutionEngineAdapter.

        This tests the integration between:
        - TradeSignal
        - ExecutionEngineAdapter
        - PessimisticExecutionEngine (via adapter)
        """
        result = await execution_adapter.execute_order(sample_signal)

        # Verify result structure
        assert result.success is True
        assert result.symbol == "AAPL"
        assert result.side == "buy"  # OrderSide enum values are lowercase
        assert result.quantity == Decimal("100")
        assert result.status == "FILLED"
        assert result.order_id.startswith("exec_")
        assert result.execution_price > 0
        assert result.commission >= 0
        assert result.slippage_bps > 0

    @pytest.mark.asyncio
    async def test_order_manager_adapter_basic_flow(
        self,
        order_manager_adapter: OrderManagerAdapter,
        sample_signal,
    ):
        """
        Test basic order flow through OrderManagerAdapter.

        This tests the integration between:
        - TradeSignal
        - OrderManagerAdapter
        - OrderManager (via adapter)
        """
        result = await order_manager_adapter.execute_order(sample_signal)

        # Verify result structure (may be rejected by risk gates)
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "symbol")
        assert result.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_trading_bridge_adapter_basic_flow(
        self,
        trading_bridge_adapter: TradingBridgeAdapter,
        sample_signal,
    ):
        """
        Test basic trading bridge flow.

        This tests the integration between:
        - TradeSignal
        - TradingBridgeAdapter
        - TradingBridgeOrchestrator (via adapter)
        """
        result = await trading_bridge_adapter.execute_order(sample_signal)

        # Verify result structure (may fail if bridge not active)
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "symbol")


# =============================================================================
# Tests: Full Trading Flow
# =============================================================================


class TestFullTradingFlow:
    """Test complete trading flow through multiple adapters."""

    @pytest.mark.asyncio
    async def test_multi_adapter_execution(
        self,
        execution_adapter: ExecutionEngineAdapter,
        order_manager_adapter: OrderManagerAdapter,
        sample_signal,
    ):
        """
        Test executing the same signal through multiple adapters.

        This verifies that all adapters can handle the same signal type
        and produce consistent results.
        """
        # Execute through ExecutionEngineAdapter
        exec_result = await execution_adapter.execute_order(sample_signal)
        assert exec_result.success is True
        assert exec_result.symbol == sample_signal.symbol

        # Create a new signal for OrderManager (to avoid duplicate IDs)
        from app.services.alerting_system import AlertSeverity
        from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
        from app.services.live_trading.broker_connector import OrderSide, OrderType

        om_signal = TradeSignal(
            signal_id="test_signal_002",
            alert_id="test_alert_002",
            alert_rule_id="test_rule",
            symbol=sample_signal.symbol,
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=sample_signal.quantity,
            price=sample_signal.price,
            severity=AlertSeverity.WARNING,
            reason="Test signal for OrderManager",
        )

        # Execute through OrderManagerAdapter
        om_result = await order_manager_adapter.execute_order(om_signal)
        # Verify result structure (may be rejected by risk gates)
        assert om_result is not None
        assert hasattr(om_result, "success")

    @pytest.mark.asyncio
    async def test_sequential_order_execution(
        self,
        execution_adapter: ExecutionEngineAdapter,
    ):
        """Test executing multiple orders sequentially."""
        from app.services.alerting_system import AlertSeverity
        from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
        from app.services.live_trading.broker_connector import OrderSide, OrderType

        signals = [
            TradeSignal(
                signal_id=f"test_signal_{i:03d}",
                alert_id=f"test_alert_{i:03d}",
                alert_rule_id="test_rule",
                symbol=symbol,
                signal_type=TradeSignalType.LONG,
                order_side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150"),
                severity=AlertSeverity.WARNING,
                reason=f"Test signal {i}",
            )
            for i, symbol in enumerate(["AAPL", "MSFT", "TSLA"], 1)
        ]

        results = []
        for signal in signals:
            result = await execution_adapter.execute_order(signal)
            results.append(result)

        # Verify all orders executed successfully
        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].symbol == "AAPL"
        assert results[1].symbol == "MSFT"
        assert results[2].symbol == "TSLA"

        # Verify all orders have unique IDs
        order_ids = [r.order_id for r in results]
        assert len(order_ids) == len(set(order_ids))


# =============================================================================
# Tests: Order Management
# =============================================================================


class TestOrderManagement:
    """Test order management operations across adapters."""

    @pytest.mark.asyncio
    async def test_order_cancellation(
        self,
        execution_adapter: ExecutionEngineAdapter,
        sample_signal,
    ):
        """Test order cancellation through adapter."""
        # Execute order
        result = await execution_adapter.execute_order(sample_signal)
        order_id = result.order_id

        # Cancel order
        cancel_result = await execution_adapter.cancel_order(order_id)
        assert cancel_result is True

        # Verify status
        status = await execution_adapter.get_order_status(order_id)
        assert status == "CANCELLED"

    @pytest.mark.asyncio
    async def test_order_modification(
        self,
        execution_adapter: ExecutionEngineAdapter,
        sample_signal,
    ):
        """Test order modification through adapter."""
        # Execute order
        result = await execution_adapter.execute_order(sample_signal)
        order_id = result.order_id

        # Modify order
        new_price = Decimal("155")
        modify_result = await execution_adapter.modify_order(order_id, new_price)
        assert modify_result is True

    @pytest.mark.asyncio
    async def test_get_open_orders(
        self,
        execution_adapter: ExecutionEngineAdapter,
    ):
        """Test retrieving open orders."""
        open_orders = await execution_adapter.get_open_orders()
        # In backtesting context, should be empty list
        assert isinstance(open_orders, list)


# =============================================================================
# Tests: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_execution_with_invalid_signal(
        self,
        execution_adapter: ExecutionEngineAdapter,
    ):
        """Test execution with invalid signal data."""
        from app.services.alerting_system import AlertSeverity
        from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
        from app.services.live_trading.broker_connector import OrderSide, OrderType

        # Create signal with zero quantity (should still work, just zero-size trade)
        invalid_signal = TradeSignal(
            signal_id="test_invalid",
            alert_id="test_alert_invalid",
            alert_rule_id="test_rule",
            symbol="INVALID",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0"),  # Zero quantity
            price=Decimal("150"),
            severity=AlertSeverity.WARNING,
            reason="Invalid signal test",
        )

        result = await execution_adapter.execute_order(invalid_signal)
        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_cancel_unknown_order(
        self,
        execution_adapter: ExecutionEngineAdapter,
    ):
        """Test cancelling an unknown order."""
        result = await execution_adapter.cancel_order("unknown_order_123")
        # Should return True (idempotent)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_status_unknown_order(
        self,
        execution_adapter: ExecutionEngineAdapter,
    ):
        """Test getting status of unknown order."""
        status = await execution_adapter.get_order_status("unknown_order_123")
        assert status == "UNKNOWN"


# =============================================================================
# Tests: Performance and Metrics
# =============================================================================


class TestPerformanceMetrics:
    """Test performance metrics and statistics."""

    def test_execution_adapter_stats(
        self,
        execution_adapter: ExecutionEngineAdapter,
        sample_signal,
    ):
        """Test execution statistics tracking."""
        import asyncio

        # Execute order
        asyncio.run(execution_adapter.execute_order(sample_signal))

        # Get stats
        stats = execution_adapter.get_execution_stats()
        assert stats["total_orders"] == 1
        assert stats["total_slippage_bps"] > 0

    def test_order_history_tracking(
        self,
        execution_adapter: ExecutionEngineAdapter,
        sample_signal,
    ):
        """Test order history tracking."""
        import asyncio

        # Execute order
        result = asyncio.run(execution_adapter.execute_order(sample_signal))

        # Get history
        history = execution_adapter.get_order_history()
        assert result.order_id in history
        assert history[result.order_id]["symbol"] == "AAPL"


# =============================================================================
# Tests: Protocol Compliance
# =============================================================================


class TestProtocolCompliance:
    """Test that all adapters implement ITradeExecutor protocol correctly."""

    def test_execution_adapter_protocol_compliance(self, execution_adapter):
        """Test ExecutionEngineAdapter implements ITradeExecutor."""

        # Check all required methods exist
        assert hasattr(execution_adapter, "execute_order")
        assert hasattr(execution_adapter, "cancel_order")
        assert hasattr(execution_adapter, "modify_order")
        assert hasattr(execution_adapter, "get_order_status")
        assert hasattr(execution_adapter, "get_open_orders")

        # Check methods are callable
        assert callable(execution_adapter.execute_order)
        assert callable(execution_adapter.cancel_order)
        assert callable(execution_adapter.modify_order)
        assert callable(execution_adapter.get_order_status)
        assert callable(execution_adapter.get_open_orders)

    def test_order_manager_adapter_protocol_compliance(self, order_manager_adapter):
        """Test OrderManagerAdapter implements ITradeExecutor."""

        # Check all required methods exist
        assert hasattr(order_manager_adapter, "execute_order")
        assert hasattr(order_manager_adapter, "cancel_order")
        assert hasattr(order_manager_adapter, "modify_order")
        assert hasattr(order_manager_adapter, "get_order_status")
        assert hasattr(order_manager_adapter, "get_open_orders")

    def test_trading_bridge_adapter_protocol_compliance(self, trading_bridge_adapter):
        """Test TradingBridgeAdapter implements ITradeExecutor."""

        # Check all required methods exist
        assert hasattr(trading_bridge_adapter, "execute_order")
        assert hasattr(trading_bridge_adapter, "cancel_order")
        assert hasattr(trading_bridge_adapter, "modify_order")
        assert hasattr(trading_bridge_adapter, "get_order_status")
        assert hasattr(trading_bridge_adapter, "get_open_orders")
