"""
Unit Tests for Market Mechanics - Harris Trading and Exchanges

Tests for auction mechanisms, continuous trading, and trading session
management as described by Harris.
"""

from datetime import time
from decimal import Decimal

import pytest

from app.simulation.market_mechanics import (
    AuctionMechanism,
    AuctionType,
    ContinuousTrading,
    MarketMechanicsEngine,
    MarketPhase,
    TradingSession,
    create_market_mechanics_engine,
)
from app.simulation.order_book import LimitOrderBook, Order, OrderSide, OrderType


class TestAuctionMechanism:
    """Test AuctionMechanism class."""

    def test_create_auction(self):
        """Test auction creation."""
        auction = AuctionMechanism(
            symbol="AAPL",
            auction_type=AuctionType.OPENING,
        )

        assert auction.symbol == "AAPL"
        assert auction.auction_type == AuctionType.OPENING
        assert auction.get_auction_indicative_price() is None

    def test_submit_auction_orders(self):
        """Test submitting orders to auction."""
        auction = AuctionMechanism(
            symbol="AAPL",
            auction_type=AuctionType.OPENING,
        )

        buy_order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        sell_order = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("149.00"),
        )

        auction.submit_order(buy_order)
        auction.submit_order(sell_order)

        # Should have indicative price since orders overlap
        indicative_price = auction.get_auction_indicative_price()
        assert indicative_price is not None
        assert indicative_price >= Decimal("149.00")
        assert indicative_price <= Decimal("150.00")

    def test_execute_auction(self):
        """Test auction execution."""
        auction = AuctionMechanism(
            symbol="AAPL",
            auction_type=AuctionType.OPENING,
        )

        # Submit overlapping orders
        for i in range(5):
            buy = Order(
                order_id=f"buy_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{i:02d}"),
            )
            auction.submit_order(buy)

            sell = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"149.{i:02d}"),
            )
            auction.submit_order(sell)

        result = auction.execute_auction()

        assert result.auction_type == AuctionType.OPENING
        assert result.symbol == "AAPL"
        assert result.is_matched
        assert result.auction_price is not None
        assert result.total_volume > 0

    def test_auction_no_match(self):
        """Test auction with no matching orders."""
        auction = AuctionMechanism(
            symbol="AAPL",
            auction_type=AuctionType.OPENING,
        )

        # Submit non-overlapping orders
        buy = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("145.00"),  # Too low
        )
        auction.submit_order(buy)

        sell = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("155.00"),  # Too high
        )
        auction.submit_order(sell)

        result = auction.execute_auction()

        assert not result.is_matched
        assert result.auction_price is None
        assert result.total_volume == 0

    def test_get_order_imbalance(self):
        """Test order imbalance calculation."""
        auction = AuctionMechanism(
            symbol="AAPL",
            auction_type=AuctionType.OPENING,
        )

        # More buying pressure
        for _ in range(3):
            buy = Order(
                order_id=f"buy_{_}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("200"),
                price=Decimal("150.00"),
            )
            auction.submit_order(buy)

        sell = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("149.00"),
        )
        auction.submit_order(sell)

        imbalance = auction.get_order_imbalance()

        # Buy volume should exceed sell volume
        assert imbalance > 0


class TestContinuousTrading:
    """Test ContinuousTrading class."""

    def test_start_stop_continuous_trading(self):
        """Test starting and stopping continuous trading."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        ct = ContinuousTrading(order_book=book)

        assert not ct.is_active

        ct.start()
        assert ct.is_active

        ct.stop()
        assert not ct.is_active

    def test_submit_order_continuous_trading(self):
        """Test submitting orders during continuous trading."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        ct = ContinuousTrading(order_book=book)
        ct.start()

        # Add resting sell order
        sell = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )
        ct.submit_order(sell)

        # Submit marketable buy order
        buy = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
        )

        trades = ct.submit_order(buy)

        assert len(trades) == 1
        assert trades[0].price == Decimal("150.00")
        assert trades[0].quantity == Decimal("100")

    def test_submit_when_not_active(self):
        """Test submitting order when continuous trading is not active."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        ct = ContinuousTrading(order_book=book)

        order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        with pytest.raises(RuntimeError, match="Continuous trading is not active"):
            ct.submit_order(order)

    def test_calculate_vwap(self):
        """Test VWAP calculation."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        ct = ContinuousTrading(order_book=book)
        ct.start()

        # Generate trades through order book
        for _ in range(3):
            sell = Order(
                order_id=f"sell_{_}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{_}0"),
            )
            ct.submit_order(sell)

            buy = Order(
                order_id=f"buy_{_}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
            )
            ct.submit_order(buy)

        vwap = ct.calculate_vwap()
        assert vwap is not None
        assert vwap >= Decimal("150.00")
        assert vwap <= Decimal("150.20")


class TestTradingSession:
    """Test TradingSession class."""

    def test_create_session(self):
        """Test creating a trading session."""
        session = TradingSession(
            name="Regular",
            start_time=time(9, 30),
            end_time=time(16, 0),
            opening_auction=True,
            closing_auction=True,
            is_continuous=True,
        )

        assert session.name == "Regular"
        assert session.start_time == time(9, 30)
        assert session.end_time == time(16, 0)
        assert session.opening_auction
        assert session.closing_auction
        assert session.is_continuous


class TestMarketMechanicsEngine:
    """Test MarketMechanicsEngine class."""

    def test_create_engine(self):
        """Test engine creation."""
        engine = MarketMechanicsEngine(
            symbol="AAPL",
            tick_size=0.01,
        )

        assert engine.symbol == "AAPL"
        assert engine.current_phase == MarketPhase.CLOSED
        assert len(engine.phase_history) == 0

    def test_phase_transitions(self):
        """Test market phase transitions."""
        engine = MarketMechanicsEngine(
            symbol="AAPL",
            tick_size=0.01,
        )

        # Transition to opening auction
        engine.transition_to(MarketPhase.OPENING_AUCTION, "TEST")
        assert engine.current_phase == MarketPhase.OPENING_AUCTION
        assert len(engine.phase_history) == 1

        # Transition to continuous
        engine.transition_to(MarketPhase.CONTINUOUS_TRADING, "TEST")
        assert engine.current_phase == MarketPhase.CONTINUOUS_TRADING

        # Check history
        assert len(engine.phase_history) == 2
        assert engine.phase_history[0].to_phase == MarketPhase.OPENING_AUCTION

    def test_submit_order_in_phase(self):
        """Test submitting orders in different phases."""
        engine = MarketMechanicsEngine(
            symbol="AAPL",
            tick_size=0.01,
        )

        # Try to submit in closed phase
        order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        with pytest.raises(RuntimeError, match="Market is closed"):
            engine.submit_order(order)

        # Transition to continuous
        engine.transition_to(MarketPhase.CONTINUOUS_TRADING)

        # Should work now
        trades = engine.submit_order(order)
        assert isinstance(trades, list)

    def test_get_market_snapshot(self):
        """Test getting market snapshot."""
        engine = MarketMechanicsEngine(
            symbol="AAPL",
            tick_size=0.01,
        )

        engine.transition_to(MarketPhase.CONTINUOUS_TRADING)

        # Add some orders
        buy = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("149.50"),
        )
        engine.submit_order(buy)

        sell = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.50"),
        )
        engine.submit_order(sell)

        snapshot = engine.get_market_snapshot()

        assert snapshot["symbol"] == "AAPL"
        assert snapshot["phase"] == "CONTINUOUS_TRADING"
        assert snapshot["order_book"]["best_bid"] == Decimal("149.50")
        assert snapshot["order_book"]["best_ask"] == Decimal("150.50")
        assert snapshot["order_book"]["spread"] == Decimal("1.00")


class TestCreateMarketMechanicsEngine:
    """Test factory function."""

    def test_factory_function(self):
        """Test create_market_mechanics_engine factory."""
        engine = create_market_mechanics_engine(
            symbol="AAPL",
            tick_size=0.01,
            open_time=(9, 30),
            close_time=(16, 0),
        )

        assert engine.symbol == "AAPL"
        assert engine.regular_session.start_time == time(9, 30)
        assert engine.regular_session.end_time == time(16, 0)


@pytest.mark.parametrize(
    "phase",
    [
        MarketPhase.PRE_MARKET,
        MarketPhase.OPENING_AUCTION,
        MarketPhase.CONTINUOUS_TRADING,
        MarketPhase.CLOSING_AUCTION,
        MarketPhase.POST_MARKET,
        MarketPhase.CLOSED,
    ],
)
def test_all_market_phases(phase):
    """Test that all market phases can be set."""
    engine = MarketMechanicsEngine(symbol="AAPL")
    engine.transition_to(phase)
    assert engine.current_phase == phase
