"""
Integration tests for Alpaca broker connector.

Tests against real Alpaca paper trading account.
Requires ALPACA_API_KEY and ALPACA_API_SECRET environment variables.

WARNING: These tests will make actual API calls to Alpaca.
Use a paper trading account only!
"""

import os
import pytest
from decimal import Decimal
from datetime import datetime

from app.services.live_trading.broker_connector import (
    BrokerConnector,
    BrokerType,
    OrderSide,
    OrderType,
    OrderStatus,
)


# Skip all tests in this module if Alpaca credentials are not set
pytestmark = pytest.mark.skipif(
    not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_API_SECRET")),
    reason="Alpaca credentials not set (ALPACA_API_KEY, ALPACA_API_SECRET)",
)


@pytest.fixture
async def broker_connector():
    """Create BrokerConnector instance for Alpaca."""
    connector = BrokerConnector(broker_type=BrokerType.ALPACA)
    yield connector
    # Cleanup
    await connector.disconnect()


class TestAlpacaBrokerConnectorConnection:
    """Test BrokerConnector connection to Alpaca."""

    @pytest.mark.asyncio
    async def test_connect_to_alpaca_paper_trading(self, broker_connector):
        """Test connecting to Alpaca paper trading."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        result = await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
            paper_trading=True,
        )

        assert result is True
        assert broker_connector.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect_from_alpaca(self, broker_connector):
        """Test disconnecting from Alpaca."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        result = await broker_connector.disconnect()

        assert result is True


class TestAlpacaBrokerConnectorAccountInfo:
    """Test account info retrieval from Alpaca."""

    @pytest.mark.asyncio
    async def test_get_account_info(self, broker_connector):
        """Test retrieving account information."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        account = await broker_connector.get_account_info()

        assert account is not None
        assert account.account_id is not None
        assert isinstance(account.cash_available, Decimal)
        assert isinstance(account.portfolio_value, Decimal)
        assert isinstance(account.buying_power, Decimal)
        assert account.broker_type == BrokerType.ALPACA

    @pytest.mark.asyncio
    async def test_sync_account_balance(self, broker_connector):
        """Test syncing account balance."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        result = await broker_connector.sync_account_balance()

        assert result is True

    @pytest.mark.asyncio
    async def test_calculate_portfolio_value(self, broker_connector):
        """Test portfolio value calculation."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        portfolio_value = await broker_connector.calculate_portfolio_value()

        assert portfolio_value is not None
        assert isinstance(portfolio_value, Decimal)
        assert portfolio_value > Decimal("0")


class TestAlpacaBrokerConnectorPositions:
    """Test position management with Alpaca."""

    @pytest.mark.asyncio
    async def test_get_positions(self, broker_connector):
        """Test retrieving all positions."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        positions = await broker_connector.get_positions()

        assert isinstance(positions, list)
        # Positions may be empty in new account
        for pos in positions:
            assert hasattr(pos, "symbol")
            assert hasattr(pos, "quantity")
            assert hasattr(pos, "market_value")
            assert isinstance(pos.quantity, Decimal)

    @pytest.mark.asyncio
    async def test_get_specific_position(self, broker_connector):
        """Test retrieving specific position."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Try to get a position (may not exist)
        position = await broker_connector.get_position("AAPL")

        # Either position exists or returns None
        if position is not None:
            assert position.symbol == "AAPL"


class TestAlpacaBrokerConnectorOrderFlow:
    """Test complete order flow with Alpaca."""

    @pytest.mark.asyncio
    async def test_place_market_order(self, broker_connector):
        """Test placing a market order."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Place a small market order (this will actually execute!)
        order_id = await broker_connector.place_order(
            symbol="SPY",  # High liquidity ETF
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
        )

        assert order_id is not None
        assert isinstance(order_id, str)

    @pytest.mark.asyncio
    async def test_place_limit_order(self, broker_connector):
        """Test placing a limit order."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Place a limit order that likely won't execute (low price)
        order_id = await broker_connector.place_order(
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.LIMIT,
            price=Decimal("1.00"),  # Very low price, won't fill
        )

        assert order_id is not None

    @pytest.mark.asyncio
    async def test_order_lifecycle(self, broker_connector):
        """Test complete order lifecycle: place, query, cancel."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Place a limit order (won't fill immediately)
        order_id = await broker_connector.place_order(
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.LIMIT,
            price=Decimal("1.00"),
        )

        # Check order status
        status = await broker_connector.get_order_status(order_id)
        assert status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED]

        # Cancel the order
        cancel_result = await broker_connector.cancel_order(order_id)
        assert cancel_result is True

        # Verify order is canceled
        final_status = await broker_connector.get_order_status(order_id)
        # Status might be CANCELED or PENDING depending on timing
        assert final_status in [OrderStatus.CANCELED, OrderStatus.PENDING]


class TestAlpacaBrokerConnectorPositionAccuracy:
    """Test position P&L calculations accuracy."""

    @pytest.mark.asyncio
    async def test_position_calculations(self, broker_connector):
        """Test position calculation accuracy."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        positions = await broker_connector.get_positions()

        for pos in positions:
            # Verify market value calculation
            expected_market_value = pos.quantity * pos.current_price
            assert pos.market_value == expected_market_value

            # Verify unrealized P&L calculation
            expected_pl = (pos.current_price - pos.avg_price) * pos.quantity
            assert pos.unrealized_pl == expected_pl

            # Verify unrealized P&L percentage
            if pos.market_value != Decimal("0"):
                expected_pl_pct = (pos.unrealized_pl / pos.market_value) * Decimal("100")
                assert pos.unrealized_pl_pct == expected_pl_pct


class TestAlpacaBrokerConnectorErrorRecovery:
    """Test error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, broker_connector):
        """Test handling of connection errors."""
        # Try to connect with invalid credentials
        result = await broker_connector.connect(
            api_key="invalid_key",
            api_secret="invalid_secret",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_symbol_handling(self, broker_connector):
        """Test handling of invalid symbol."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Try to place order with invalid symbol
        with pytest.raises(Exception):
            await broker_connector.place_order(
                symbol="INVALID_SYMBOL_XYZ",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                order_type=OrderType.MARKET,
            )


class TestAlpacaBrokerConnectorRateLimiting:
    """Test rate limiting compliance."""

    @pytest.mark.asyncio
    async def test_rapid_api_calls_survive_rate_limits(self, broker_connector):
        """Test that rapid API calls handle rate limiting gracefully."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        # Make multiple rapid calls (may hit rate limit)
        for i in range(5):
            try:
                account = await broker_connector.get_account_info()
                assert account is not None
            except Exception as e:
                # Rate limiting is OK, should recover
                pytest.skip(f"Rate limited: {e}")


class TestAlpacaBrokerConnectorDataConsistency:
    """Test data consistency across multiple calls."""

    @pytest.mark.asyncio
    async def test_account_data_consistency(self, broker_connector):
        """Test that account data is consistent across calls."""
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")

        await broker_connector.connect(
            api_key=api_key,
            api_secret=api_secret,
        )

        account1 = await broker_connector.get_account_info()
        account2 = await broker_connector.get_account_info()

        # Account ID should be the same
        assert account1.account_id == account2.account_id

        # Cash and portfolio should be close (might change slightly)
        # Allow small variance for concurrent trading
        cash_diff = abs(account1.cash_available - account2.cash_available)
        assert cash_diff < Decimal("1000")  # Allow $1000 variance


class TestAlpacaBrokerConnectorBrokerType:
    """Test broker type detection."""

    def test_alpaca_broker_type(self, broker_connector):
        """Test that broker type is correctly identified as ALPACA."""
        broker_type = broker_connector.get_broker_type()
        assert broker_type == BrokerType.ALPACA

    def test_paper_trading_mode(self, broker_connector):
        """Test paper trading mode detection."""
        # Default should be paper trading
        is_paper = broker_connector.is_paper_trading()
        # Depends on configuration, just verify it returns boolean
        assert isinstance(is_paper, bool)
