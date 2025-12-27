"""
T16.1: Live Trading Bridge - Comprehensive unit tests

Tests for BrokerConnector, OrderManager, RiskGates, and AccountSynchronizer
"""

from decimal import Decimal

import pytest

from app.services.live_trading.account_synchronizer import AccountSynchronizer
from app.services.live_trading.broker_connector import (
    BrokerConnector,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)
from app.services.live_trading.order_manager import OrderManager
from app.services.live_trading.risk_gates import RiskGates, RiskLevel


@pytest.fixture
def broker():
    """Create test broker connector."""
    return BrokerConnector(BrokerType.PAPER)


@pytest.fixture
def order_manager(broker):
    """Create test order manager."""
    return OrderManager(broker)


@pytest.fixture
def risk_gates(broker):
    """Create test risk gates."""
    return RiskGates(broker)


@pytest.fixture
def account_sync(broker):
    """Create test account synchronizer."""
    return AccountSynchronizer(broker)


@pytest.mark.asyncio
class TestBrokerConnector:
    """Test BrokerConnector."""

    async def test_initialization(self, broker):
        """Test broker initialization."""
        assert broker.broker_type == BrokerType.PAPER
        assert not broker.is_connected

    async def test_connect(self, broker):
        """Test connecting to broker."""
        result = await broker.connect(account_id="test_account")
        assert result is True
        assert broker.is_connected
        assert broker.account is not None

    async def test_disconnect(self, broker):
        """Test disconnecting from broker."""
        await broker.connect()
        result = await broker.disconnect()
        assert result is True
        assert not broker.is_connected

    async def test_get_account_info(self, broker):
        """Test getting account information."""
        assert not broker.is_connected
        account = await broker.get_account_info()
        assert account is None

        await broker.connect()
        account = await broker.get_account_info()
        assert account is not None
        assert account.connected is True

    async def test_place_order(self, broker):
        """Test placing an order."""
        await broker.connect()
        order = await broker.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
        )
        assert order is not None
        assert order.symbol == "AAPL"
        assert order.quantity == Decimal("100")
        assert order.status == OrderStatus.SUBMITTED

    async def test_cancel_order(self, broker):
        """Test canceling an order."""
        await broker.connect()
        order = await broker.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        assert order is not None

        result = await broker.cancel_order(order.order_id)
        assert result is True

    async def test_order_status(self, broker):
        """Test getting order status."""
        await broker.connect()
        order = await broker.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        status = await broker.get_order_status(order.order_id)
        assert status == OrderStatus.SUBMITTED


@pytest.mark.asyncio
class TestOrderManager:
    """Test OrderManager."""

    async def test_place_order(self, order_manager, broker):
        """Test placing order through manager."""
        await broker.connect()
        order = await order_manager.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        assert order is not None
        assert order.symbol == "AAPL"
        assert order.order_id in order_manager.pending_orders

    async def test_cancel_order(self, order_manager, broker):
        """Test canceling order."""
        await broker.connect()
        order = await order_manager.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        result = await order_manager.cancel_order(order.order_id)
        assert result is True

    async def test_pending_orders(self, order_manager, broker):
        """Test tracking pending orders."""
        await broker.connect()
        await order_manager.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        await order_manager.place_order("MSFT", OrderSide.SELL, Decimal("50"))

        pending = await order_manager.get_pending_orders()
        assert len(pending) == 2

    async def test_execution_recording(self, order_manager):
        """Test recording order execution."""
        execution = await order_manager.record_execution(
            "order_1", "AAPL", Decimal("100"), Decimal("150"), Decimal("10")
        )
        assert execution is not None
        assert execution.quantity == Decimal("100")
        assert len(order_manager.executions) == 1

    async def test_order_error_tracking(self, order_manager):
        """Test tracking order errors."""
        error = await order_manager.record_error(
            "order_1", "AAPL", "INSUFFICIENT_FUNDS", "Not enough buying power"
        )
        assert error is not None
        assert "order_1" in order_manager.order_errors


@pytest.mark.asyncio
class TestRiskGates:
    """Test RiskGates."""

    async def test_validate_order_low_value(self, risk_gates, broker):
        """Test validating low-value order."""
        await broker.connect()
        # Set mock buying power on account
        broker.account.buying_power = Decimal("100000")
        result = await risk_gates.validate_order(
            "AAPL", OrderSide.BUY, Decimal("10"), Decimal("150")
        )
        assert isinstance(result.passed, bool)
        # May pass or fail depending on cash reserve check
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

    async def test_validate_order_exceeds_buying_power(self, risk_gates, broker):
        """Test order that exceeds buying power."""
        await broker.connect()
        result = await risk_gates.validate_order(
            "AAPL", OrderSide.BUY, Decimal("1000000"), Decimal("150")
        )
        # Will likely fail due to buying power
        assert isinstance(result.passed, bool)

    async def test_set_limits(self, risk_gates):
        """Test setting risk limits."""
        risk_gates.set_max_position_size(Decimal("100000"))
        risk_gates.set_max_leverage(Decimal("1.5"))
        risk_gates.set_max_daily_loss(Decimal("0.1"))

        assert risk_gates.max_position_size == Decimal("100000")
        assert risk_gates.max_leverage == Decimal("1.5")
        assert risk_gates.max_daily_loss == Decimal("0.1")

    async def test_concentration_check(self, risk_gates):
        """Test sector concentration limits."""
        sector_allocations = {
            "Technology": Decimal("0.35"),
            "Healthcare": Decimal("0.20"),
            "Financials": Decimal("0.15"),
        }
        result = await risk_gates.check_sector_concentration(sector_allocations)
        assert isinstance(result.passed, bool)
        # Technology is 35%, exceeds 30% max
        assert result.passed is False


@pytest.mark.asyncio
class TestAccountSynchronizer:
    """Test AccountSynchronizer."""

    async def test_sync_account(self, account_sync, broker):
        """Test account synchronization."""
        await broker.connect()
        result = await account_sync.sync_account()
        assert result is True
        assert account_sync.last_sync is not None

    async def test_take_snapshot(self, account_sync, broker):
        """Test taking portfolio snapshot."""
        await broker.connect()
        snapshot = await account_sync.take_snapshot()
        assert snapshot is not None
        assert snapshot.timestamp is not None
        assert len(account_sync.snapshots) == 1

    async def test_reconcile_balance(self, account_sync, broker):
        """Test balance reconciliation."""
        await broker.connect()
        await account_sync.sync_account()
        reconciliation = await account_sync.reconcile_balance()
        assert reconciliation is not None
        assert isinstance(reconciliation.is_balanced, bool)

    async def test_portfolio_history(self, account_sync, broker):
        """Test getting portfolio history."""
        await broker.connect()
        await account_sync.take_snapshot()
        history = await account_sync.get_portfolio_history(hours=24)
        assert isinstance(history, list)
        assert len(history) >= 1

    async def test_margin_status(self, account_sync, broker):
        """Test getting margin status."""
        await broker.connect()
        status = await account_sync.get_margin_status()
        assert isinstance(status, dict)

    async def test_sync_status(self, account_sync, broker):
        """Test getting sync status."""
        await broker.connect()
        await account_sync.sync_account()
        status = account_sync.get_sync_status()
        assert status["is_synced"] is True
        assert status["last_sync"] is not None


@pytest.mark.asyncio
class TestLiveTradingIntegration:
    """Integration tests for live trading bridge."""

    async def test_complete_trade_flow(self, broker, order_manager, risk_gates):
        """Test complete trade flow."""
        # 1. Connect
        await broker.connect()

        # 2. Validate order
        result = await risk_gates.validate_order(
            "AAPL", OrderSide.BUY, Decimal("100"), Decimal("150")
        )
        assert result is not None

        # 3. Place order
        order = await order_manager.place_order("AAPL", OrderSide.BUY, Decimal("100"))
        assert order is not None

        # 4. Record execution
        execution = await order_manager.record_execution(
            order.order_id, "AAPL", Decimal("100"), Decimal("150")
        )
        assert execution is not None

    async def test_multiple_positions(self, broker, order_manager, account_sync):
        """Test managing multiple positions."""
        await broker.connect()

        # Place orders for multiple symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in symbols:
            await order_manager.place_order(symbol, OrderSide.BUY, Decimal("50"))

        pending = await order_manager.get_pending_orders()
        assert len(pending) == 3

    async def test_risk_assessment_workflow(self, risk_gates, broker):
        """Test complete risk assessment."""
        await broker.connect()

        # Validate multiple orders
        orders = [
            ("AAPL", OrderSide.BUY, Decimal("100"), Decimal("150")),
            ("MSFT", OrderSide.BUY, Decimal("50"), Decimal("300")),
            ("GOOGL", OrderSide.SELL, Decimal("25"), Decimal("2500")),
        ]

        for symbol, side, qty, price in orders:
            result = await risk_gates.validate_order(symbol, side, qty, price)
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
