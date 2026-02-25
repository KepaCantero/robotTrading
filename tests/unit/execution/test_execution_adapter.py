"""
Unit tests for ExecutionEngineAdapter (Task 10 - Execution Engine Integration)

Tests verify that the adapter correctly implements ITradeExecutor protocol
and bridges PessimisticExecutionEngine with ComplianceEngine.
"""

import pytest
from decimal import Decimal

from app.domain.services.execution.execution_adapter import (
    ExecutionEngineAdapter,
    get_execution_adapter,
)


# Fixtures
@pytest.fixture
def adapter():
    """Provide a fresh ExecutionEngineAdapter for each test."""
    return ExecutionEngineAdapter(enable_logging=False)


@pytest.fixture
def sample_signal():
    """Provide a sample TradeSignal for testing."""
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.alerting_system import AlertSeverity

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
        reason="Test signal",
    )


# Tests for execute_order
@pytest.mark.asyncio
async def test_execute_order_success(adapter, sample_signal):
    """Test successful order execution."""
    result = await adapter.execute_order(sample_signal)

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
async def test_execute_order_with_slippage(adapter, sample_signal):
    """Test that slippage is applied correctly."""
    result = await adapter.execute_order(sample_signal)

    # For BUY orders, execution price should be higher (worse for trader)
    # Default slippage is 5 bps (0.05%)
    expected_min_price = sample_signal.price * Decimal("1.0005")
    assert result.execution_price >= expected_min_price.quantize(Decimal("0.01"))


@pytest.mark.asyncio
async def test_execute_order_sell_side(adapter):
    """Test order execution for SELL side."""
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.alerting_system import AlertSeverity

    signal = TradeSignal(
        signal_id="test_signal_002",
        alert_id="test_alert_002",
        alert_rule_id="test_rule",
        symbol="AAPL",
        signal_type=TradeSignalType.SHORT,
        order_side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("50"),
        price=Decimal("150"),
        severity=AlertSeverity.INFO,
    )

    result = await adapter.execute_order(signal)

    assert result.success is True
    assert result.side == "sell"  # OrderSide enum values are lowercase
    # For SELL orders, execution price should be lower (worse for trader)
    assert result.execution_price < signal.price


@pytest.mark.asyncio
async def test_execute_order_without_price(adapter):
    """Test order execution when price is not provided."""
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.alerting_system import AlertSeverity

    signal = TradeSignal(
        signal_id="test_signal_003",
        alert_id="test_alert_003",
        alert_rule_id="test_rule",
        symbol="TSLA",
        signal_type=TradeSignalType.LONG,
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10"),
        price=None,  # No price provided
        severity=AlertSeverity.WARNING,
    )

    result = await adapter.execute_order(signal)

    # Should use default price (100)
    assert result.success is True
    assert result.signal_price > 0


@pytest.mark.asyncio
async def test_execute_order_tracking(adapter, sample_signal):
    """Test that executed orders are tracked in history."""
    result = await adapter.execute_order(sample_signal)

    history = adapter.get_order_history()
    assert result.order_id in history
    assert history[result.order_id]["symbol"] == "AAPL"
    assert history[result.order_id]["side"] == "buy"  # OrderSide enum values are lowercase


# Tests for cancel_order
@pytest.mark.asyncio
async def test_cancel_order(adapter, sample_signal):
    """Test order cancellation."""
    result = await adapter.execute_order(sample_signal)
    order_id = result.order_id

    cancel_result = await adapter.cancel_order(order_id)

    assert cancel_result is True
    # get_order_status is async - need to await it
    status = await adapter.get_order_status(order_id)
    assert status == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_unknown_order(adapter):
    """Test cancelling an unknown order."""
    result = await adapter.cancel_order("unknown_order_123")
    assert result is True  # Returns True even for unknown orders


# Tests for modify_order
@pytest.mark.asyncio
async def test_modify_order(adapter, sample_signal):
    """Test order modification."""
    result = await adapter.execute_order(sample_signal)
    order_id = result.order_id
    new_price = Decimal("155")

    modify_result = await adapter.modify_order(order_id, new_price)

    assert modify_result is True


# Tests for get_order_status
@pytest.mark.asyncio
async def test_get_order_status_filled(adapter, sample_signal):
    """Test getting status of a filled order."""
    result = await adapter.execute_order(sample_signal)
    order_id = result.order_id

    status = await adapter.get_order_status(order_id)
    assert status == "FILLED"


@pytest.mark.asyncio
async def test_get_order_status_unknown(adapter):
    """Test getting status of an unknown order."""
    status = await adapter.get_order_status("unknown_order_123")
    assert status == "UNKNOWN"


# Tests for get_open_orders
@pytest.mark.asyncio
async def test_get_open_orders(adapter):
    """Test that open orders list is empty (backtesting context)."""
    open_orders = await adapter.get_open_orders()
    assert open_orders == []


# Tests for statistics and history
def test_get_order_history_empty(adapter):
    """Test getting order history when no orders."""
    history = adapter.get_order_history()
    assert history == {}


def test_get_execution_stats_empty(adapter):
    """Test getting execution stats when no orders."""
    stats = adapter.get_execution_stats()
    assert stats["total_orders"] == 0
    assert stats["total_slippage_bps"] == Decimal("0")


def test_get_execution_stats_with_orders(adapter, sample_signal):
    """Test getting execution stats after executing orders."""
    import asyncio

    asyncio.run(adapter.execute_order(sample_signal))

    stats = adapter.get_execution_stats()
    assert stats["total_orders"] == 1
    assert stats["total_slippage_bps"] > 0
    assert stats["avg_slippage_bps"] > 0


# Tests for reset
def test_reset_clears_history(adapter, sample_signal):
    """Test that reset clears order history."""
    import asyncio

    asyncio.run(adapter.execute_order(sample_signal))
    assert len(adapter.get_order_history()) > 0

    adapter.reset()
    assert len(adapter.get_order_history()) == 0


# Tests for factory function
def test_get_execution_adapter():
    """Test factory function for creating adapter."""
    adapter = get_execution_adapter(enable_logging=False)
    assert isinstance(adapter, ExecutionEngineAdapter)


# Integration-style tests
@pytest.mark.asyncio
async def test_execute_multiple_orders(adapter):
    """Test executing multiple orders sequentially."""
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.alerting_system import AlertSeverity

    signals = [
        TradeSignal(
            signal_id="test_signal_004",
            alert_id="test_alert_004",
            alert_rule_id="test_rule",
            symbol="AAPL",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150"),
            severity=AlertSeverity.WARNING,
        ),
        TradeSignal(
            signal_id="test_signal_005",
            alert_id="test_alert_005",
            alert_rule_id="test_rule",
            symbol="MSFT",
            signal_type=TradeSignalType.LONG,
            order_side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=Decimal("300"),
            severity=AlertSeverity.WARNING,
        ),
    ]

    results = []
    for signal in signals:
        result = await adapter.execute_order(signal)
        results.append(result)

    assert len(results) == 2
    assert all(r.success for r in results)
    assert results[0].symbol == "AAPL"
    assert results[1].symbol == "MSFT"

    # Verify both orders are in history
    history = adapter.get_order_history()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_slippage_calculation_accuracy(adapter):
    """Test that slippage calculation is accurate."""
    from app.services.live_trading.broker_connector import OrderSide, OrderType
    from app.services.live_trading.alert_to_trade_mapper import (
        TradeSignal,
        TradeSignalType,
    )
    from app.services.alerting_system import AlertSeverity

    signal = TradeSignal(
        signal_id="test_signal_006",
        alert_id="test_alert_006",
        alert_rule_id="test_rule",
        symbol="AAPL",
        signal_type=TradeSignalType.LONG,
        order_side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100"),
        price=Decimal("100"),  # Round number for easier calculation
        severity=AlertSeverity.WARNING,
    )

    result = await adapter.execute_order(signal)

    # Default slippage is 5 bps = 0.05%
    # For BUY: 100 * 1.0005 = 100.05
    expected_slippage_bps = Decimal("5")
    assert result.slippage_bps == expected_slippage_bps

    # Execution price should be signal price * (1 + slippage/10000)
    expected_price = Decimal("100") * (Decimal("1") + Decimal("5") / Decimal("10000"))
    assert result.execution_price == expected_price.quantize(Decimal("0.01"))


# Tests for ITradeExecutor protocol compliance
def test_adapter_implements_itradeexecutor():
    """Test that ExecutionEngineAdapter implements ITradeExecutor protocol."""
    from app.core.protocols import ITradeExecutor

    adapter = ExecutionEngineAdapter()

    # Check that all required methods exist
    assert hasattr(adapter, "execute_order")
    assert hasattr(adapter, "cancel_order")
    assert hasattr(adapter, "modify_order")
    assert hasattr(adapter, "get_order_status")
    assert hasattr(adapter, "get_open_orders")

    # Check that methods are callable
    assert callable(adapter.execute_order)
    assert callable(adapter.cancel_order)
    assert callable(adapter.modify_order)
    assert callable(adapter.get_order_status)
    assert callable(adapter.get_open_orders)
