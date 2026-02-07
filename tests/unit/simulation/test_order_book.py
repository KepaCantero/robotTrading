"""
Unit Tests for Order Book Simulation - Harris Trading and Exchanges

Tests for the LimitOrderBook implementation following Harris's model of
order book dynamics and price formation.
"""

from decimal import Decimal


from app.simulation.order_book import (
    LimitOrderBook,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PriceLevel,
    Trade,
    create_limit_order_book,
)


class TestOrder:
    """Test Order class."""

    def test_create_order(self):
        """Test order creation."""
        order = Order(
            order_id="test_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        assert order.order_id == "test_001"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("100")
        assert order.price == Decimal("150.00")
        assert order.status == OrderStatus.PENDING
        assert order.remaining_quantity == Decimal("100")

    def test_fill_order(self):
        """Test order filling."""
        order = Order(
            order_id="test_002",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        order.fill(Decimal("50"), Decimal("149.50"))

        assert order.filled_quantity == Decimal("50")
        assert order.remaining_quantity == Decimal("50")
        assert order.avg_fill_price == Decimal("149.50")
        assert order.status == OrderStatus.PARTIALLY_FILLED

    def test_fill_complete_order(self):
        """Test complete order fill."""
        order = Order(
            order_id="test_003",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        order.fill(Decimal("100"), Decimal("150.25"))

        assert order.filled_quantity == Decimal("100")
        assert order.remaining_quantity == Decimal("0")
        assert order.status == OrderStatus.FILLED

    def test_fill_with_avg_price(self):
        """Test order fill with average price calculation."""
        order = Order(
            order_id="test_004",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("300"),
            price=Decimal("150.00"),
        )

        order.fill(Decimal("100"), Decimal("149.50"))
        order.fill(Decimal("100"), Decimal("150.00"))
        order.fill(Decimal("100"), Decimal("150.50"))

        assert order.filled_quantity == Decimal("300")
        assert order.avg_fill_price == Decimal("150.00")

    def test_cancel_order(self):
        """Test order cancellation."""
        order = Order(
            order_id="test_005",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        order.cancel()

        assert order.status == OrderStatus.CANCELLED

    def test_is_marketable(self):
        """Test marketable order detection."""
        market_order = Order(
            order_id="test_006",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
        )

        limit_order = Order(
            order_id="test_007",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        assert market_order.is_marketable
        assert not limit_order.is_marketable


class TestPriceLevel:
    """Test PriceLevel class."""

    def test_add_order_to_level(self):
        """Test adding orders to a price level."""
        level = PriceLevel(price=Decimal("150.00"))

        order1 = Order(
            order_id="test_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        order2 = Order(
            order_id="test_002",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("200"),
            price=Decimal("150.00"),
        )

        level.add_order(order1)
        level.add_order(order2)

        assert level.get_quantity() == Decimal("300")
        assert level.get_order_count() == 2

    def test_remove_order_from_level(self):
        """Test removing order from price level."""
        level = PriceLevel(price=Decimal("150.00"))

        order = Order(
            order_id="test_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        level.add_order(order)
        assert level.get_quantity() == Decimal("100")

        removed = level.remove_order("test_001")
        assert removed is not None
        assert removed.order_id == "test_001"
        assert level.get_quantity() == Decimal("0")
        assert level.is_empty()


class TestLimitOrderBook:
    """Test LimitOrderBook class."""

    def test_create_order_book(self):
        """Test order book creation."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
            max_depth=100,
        )

        assert book.symbol == "AAPL"
        assert book.tick_size == Decimal("0.01")
        assert book.best_bid is None
        assert book.best_ask is None

    def test_add_limit_order(self):
        """Test adding limit order to book."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        buy_order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("149.50"),
        )

        sell_order = Order(
            order_id="sell_001",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.50"),
        )

        book.submit_order(buy_order)
        book.submit_order(sell_order)

        assert book.best_bid == Decimal("149.50")
        assert book.best_ask == Decimal("150.50")
        assert book.spread == Decimal("1.00")
        assert book.mid_price == Decimal("150.00")

    def test_market_order_execution(self):
        """Test market order execution."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        # Add resting sell orders
        for i in range(5):
            order = Order(
                order_id=f"sell_{i:03d}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{i:02d}"),
            )
            book.submit_order(order)

        # Submit market buy order
        market_buy = Order(
            order_id="market_buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("300"),
        )

        trades = book.submit_order(market_buy)

        # Should execute against 3 price levels (100 each)
        assert len(trades) == 3
        assert sum(t.quantity for t in trades) == Decimal("300")
        assert trades[0].price == Decimal("150.00")  # Best ask
        assert trades[2].price == Decimal("150.02")  # Third level

    def test_price_time_priority(self):
        """Test FIFO execution at price level."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        # Add multiple sell orders at same price
        for i in range(3):
            order = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
            )
            book.submit_order(order)

        # Market buy for 150 shares
        market_buy = Order(
            order_id="market_buy",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("150"),
        )

        trades = book.submit_order(market_buy)

        # Should fill first two orders (FIFO)
        assert len(trades) == 2
        assert trades[0].sell_order_id == "sell_0"
        assert trades[1].sell_order_id == "sell_1"

        # Third order should be untouched (100 remaining)
        remaining_order = book.get_order("sell_2")
        assert remaining_order is not None
        assert remaining_order.remaining_quantity == Decimal("100")
        assert remaining_order.filled_quantity == Decimal("0")

    def test_order_cancellation(self):
        """Test order cancellation."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("149.50"),
        )

        book.submit_order(order)
        assert book.best_bid == Decimal("149.50")

        cancelled = book.cancel_order("buy_001")
        assert cancelled is True
        assert book.best_bid is None

    def test_get_snapshot(self):
        """Test order book snapshot."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        # Add some orders
        # Bids: 149.50, 149.40, 149.30, 149.20, 149.10 (descending)
        for i, price in enumerate([50, 40, 30, 20, 10]):
            buy = Order(
                order_id=f"buy_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"149.{price:d}"),
            )
            book.submit_order(buy)

        # Asks: 150.00, 150.10, 150.20, 150.30, 150.40 (ascending)
        for i, price in enumerate([0, 10, 20, 30, 40]):
            sell = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{price:02d}"),
            )
            book.submit_order(sell)

        snapshot = book.get_snapshot(depth=3)

        assert snapshot.symbol == "AAPL"
        assert len(snapshot.bids) == 3
        assert len(snapshot.asks) == 3
        assert snapshot.bid_depth == 5
        assert snapshot.ask_depth == 5
        assert snapshot.best_bid == Decimal("149.50")
        assert snapshot.best_ask == Decimal("150.00")

    def test_get_liquidity_metrics(self):
        """Test liquidity metrics calculation."""
        book = LimitOrderBook(
            symbol="AAPL",
            tick_size=Decimal("0.01"),
        )

        # Add orders to create spread
        book.submit_order(
            Order(
                order_id="buy_001",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("500"),
                price=Decimal("149.50"),
            )
        )

        book.submit_order(
            Order(
                order_id="sell_001",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("500"),
                price=Decimal("150.50"),
            )
        )

        metrics = book.get_liquidity_metrics()

        assert metrics["best_bid"] == Decimal("149.50")
        assert metrics["best_ask"] == Decimal("150.50")
        assert metrics["spread"] == Decimal("1.00")
        assert metrics["mid_price"] == Decimal("150.00")
        assert metrics["total_bid_quantity"] == Decimal("500")
        assert metrics["total_ask_quantity"] == Decimal("500")
        assert metrics["bid_ask_ratio"] == Decimal("1.0")


class TestCreateLimitOrderBook:
    """Test factory function."""

    def test_factory_function(self):
        """Test create_limit_order_book factory."""
        book = create_limit_order_book(
            symbol="AAPL",
            tick_size=0.01,
            max_depth=50,
        )

        assert book.symbol == "AAPL"
        assert book.tick_size == Decimal("0.01")
        assert isinstance(book, LimitOrderBook)


class TestTrade:
    """Test Trade class."""

    def test_trade_creation(self):
        """Test trade object creation."""
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            buy_order_id="buy_001",
            sell_order_id="sell_001",
            price=Decimal("150.00"),
            quantity=Decimal("100"),
            is_buy_aggressor=True,
        )

        assert trade.trade_id == "trade_001"
        assert trade.symbol == "AAPL"
        assert trade.price == Decimal("150.00")
        assert trade.quantity == Decimal("100")
        assert trade.is_buy_aggressor
