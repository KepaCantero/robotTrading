"""
Unit Tests for Market Microstructure Analysis - Harris Trading and Exchanges

Tests for order flow analysis, market depth, and liquidity provision
following Harris's microstructure theories.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.simulation.microstructure import (
    OrderFlowAnalyzer,
    OrderFlowDirection,
    OrderImbalance,
    MarketDepthAnalyzer,
    LiquidityRegime,
    LiquidityProvider,
    PriceImpactFunction,
    MarketMicrostructureMetrics,
    MarketMicrostructureAnalyzer,
    create_market_microstructure_analyzer,
)
from app.simulation.order_book import (
    LimitOrderBook,
    Order,
    OrderSide,
    OrderType,
    Trade,
)


class TestOrderImbalance:
    """Test OrderImbalance class."""

    def test_create_order_imbalance(self):
        """Test creating order imbalance metrics."""
        imbalance = OrderImbalance(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            buy_volume=Decimal("10000"),
            sell_volume=Decimal("5000"),
            imbalance=Decimal("5000"),
            imbalance_ratio=Decimal("0.5"),  # (10000-5000)/15000
            normalized_imbalance=Decimal("1.0"),
            direction=OrderFlowDirection.BUY_PRESSURE,
        )

        assert imbalance.symbol == "AAPL"
        assert imbalance.buy_volume == Decimal("10000")
        assert imbalance.sell_volume == Decimal("5000")
        assert imbalance.direction == OrderFlowDirection.BUY_PRESSURE
        assert imbalance.is_biased

    def test_bias_strength(self):
        """Test bias strength calculation."""
        # Strong imbalance
        strong = OrderImbalance(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            buy_volume=Decimal("15000"),
            sell_volume=Decimal("5000"),
            imbalance=Decimal("10000"),
            imbalance_ratio=Decimal("0.5"),
            normalized_imbalance=Decimal("1.0"),
            direction=OrderFlowDirection.BUY_PRESSURE,
        )
        assert strong.bias_strength == "STRONG"

        # Weak imbalance
        weak = OrderImbalance(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            buy_volume=Decimal("6000"),
            sell_volume=Decimal("4000"),
            imbalance=Decimal("2000"),
            imbalance_ratio=Decimal("0.2"),
            normalized_imbalance=Decimal("0.4"),
            direction=OrderFlowDirection.BUY_PRESSURE,
        )
        assert weak.bias_strength == "WEAK"


class TestOrderFlowAnalyzer:
    """Test OrderFlowAnalyzer class."""

    def test_add_order(self):
        """Test adding orders to flow analysis."""
        analyzer = OrderFlowAnalyzer(symbol="AAPL", window_size=10)

        order = Order(
            order_id="buy_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        analyzer.add_order(order)

        assert len(analyzer._flow_history) == 1

    def test_add_trade(self):
        """Test adding trades to flow analysis."""
        analyzer = OrderFlowAnalyzer(symbol="AAPL")

        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            buy_order_id="buy_001",
            sell_order_id="sell_001",
            price=Decimal("150.00"),
            quantity=Decimal("100"),
            is_buy_aggressor=True,
        )

        analyzer.add_trade(trade)

        assert len(analyzer._flow_history) == 1

    def test_calculate_order_imbalance(self):
        """Test order imbalance calculation."""
        analyzer = OrderFlowAnalyzer(symbol="AAPL")

        # Add buy flow
        for _ in range(3):
            analyzer.add_order(
                Order(
                    order_id=f"buy_{_}",
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal("200"),
                    price=Decimal("150.00"),
                )
            )

        # Add sell flow
        analyzer.add_order(
            Order(
                order_id="sell_001",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
            )
        )

        imbalance = analyzer.calculate_order_imbalance()

        assert imbalance is not None
        assert imbalance.buy_volume == Decimal("600")
        assert imbalance.sell_volume == Decimal("100")
        assert imbalance.direction == OrderFlowDirection.BUY_PRESSURE

    def test_calculate_flow_toxicity(self):
        """Test flow toxicity calculation."""
        analyzer = OrderFlowAnalyzer(symbol="AAPL")

        # Add orders with price information
        for i in range(10):
            analyzer.add_order(
                Order(
                    order_id=f"order_{i}",
                    symbol="AAPL",
                    side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal("100"),
                    price=Decimal(f"150.{i:02d}"),
                )
            )

        toxicity = analyzer.calculate_flow_toxicity()

        assert 0 <= toxicity <= 1

    def test_detect_informed_trading(self):
        """Test informed trading detection."""
        analyzer = OrderFlowAnalyzer(symbol="AAPL")

        # Add strong buy pressure
        for _ in range(10):
            analyzer.add_order(
                Order(
                    order_id=f"buy_{_}",
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal("500"),
                    price=Decimal("150.00"),
                )
            )

        # Add small sell pressure
        analyzer.add_order(
            Order(
                order_id="sell_001",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
            )
        )

        # High toxicity scenario
        is_informed = analyzer.detect_informed_trading()
        assert isinstance(is_informed, bool)


class TestMarketDepthAnalyzer:
    """Test MarketDepthAnalyzer class."""

    def test_analyze_depth(self):
        """Test market depth analysis."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketDepthAnalyzer(order_book=book, depth_levels=5)

        # Add some depth
        for i in range(5):
            buy = Order(
                order_id=f"buy_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"149.{5-i:02d}"),
            )
            book.submit_order(buy)

            sell = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{i:02d}"),
            )
            book.submit_order(sell)

        depth = analyzer.analyze_depth()

        assert "total_bid_depth" in depth
        assert "total_ask_depth" in depth
        assert "spread_bps" in depth
        assert "depth_imbalance" in depth
        assert depth["total_bid_depth"] == 500.0
        assert depth["total_ask_depth"] == 500.0

    def test_estimate_price_impact(self):
        """Test price impact estimation."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketDepthAnalyzer(order_book=book)

        # Add depth
        for i in range(5):
            sell = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal(f"150.{i:02d}"),
            )
            book.submit_order(sell)

        # Estimate impact for 300 share buy
        impact = analyzer.estimate_price_impact(
            order_size=300,
            side=OrderSide.BUY,
        )

        assert impact > 0  # Should have some impact

    def test_classify_liquidity_regime(self):
        """Test liquidity regime classification."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketDepthAnalyzer(order_book=book)

        # Add good liquidity
        for i in range(10):
            buy = Order(
                order_id=f"buy_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("1000"),
                price=Decimal(f"149.{10-i:02d}"),
            )
            book.submit_order(buy)

            sell = Order(
                order_id=f"sell_{i}",
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("1000"),
                price=Decimal(f"150.{i:02d}"),
            )
            book.submit_order(sell)

        regime = analyzer.classify_liquidity_regime()

        assert isinstance(regime, LiquidityRegime)
        # Should be HIGH or NORMAL given the depth
        assert regime in [LiquidityRegime.HIGH, LiquidityRegime.NORMAL]


class TestLiquidityProvider:
    """Test LiquidityProvider class."""

    def test_should_provide_liquidity(self):
        """Test decision to provide liquidity."""
        lp = LiquidityProvider(
            symbol="AAPL",
            max_position=Decimal("10000"),
            adverse_selection_threshold=0.6,
        )

        # Low toxicity, good spread = should provide
        should_provide = lp.should_provide_liquidity(
            current_toxicity=0.3,
            current_spread_bps=10.0,
        )
        assert should_provide

        # High toxicity = should not provide
        should_provide = lp.should_provide_liquidity(
            current_toxicity=0.8,
            current_spread_bps=10.0,
        )
        assert not should_provide

    def test_calculate_quotes(self):
        """Test quote calculation."""
        lp = LiquidityProvider(
            symbol="AAPL",
            target_spread_bps=10.0,
        )

        bid, ask, size = lp.calculate_quotes(
            mid_price=Decimal("150.00"),
            volatility=0.2,
        )

        assert bid is not None
        assert ask is not None
        assert size > 0
        assert bid < Decimal("150.00")
        assert ask > Decimal("150.00")

    def test_on_trade_executed(self):
        """Test handling trade execution."""
        lp = LiquidityProvider(symbol="AAPL")

        initial_position = lp.position

        lp.on_trade_executed(
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        assert lp.position == initial_position + Decimal("100")

    def test_max_position_constraint(self):
        """Test max position constraint on quotes."""
        lp = LiquidityProvider(
            symbol="AAPL",
            max_position=Decimal("1000"),
        )

        # Build up to max
        for _ in range(10):
            lp.on_trade_executed(
                side=OrderSide.BUY,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
            )

        # At max position, should not quote bids
        bid, ask, size = lp.calculate_quotes(
            mid_price=Decimal("150.00"),
            volatility=0.2,
        )

        assert bid is None  # Can't buy more
        assert ask is not None  # Can still sell


class TestMarketMicrostructureAnalyzer:
    """Test MarketMicrostructureAnalyzer class."""

    def test_create_analyzer(self):
        """Test creating microstructure analyzer."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketMicrostructureAnalyzer(
            symbol="AAPL",
            order_book=book,
        )

        assert analyzer.symbol == "AAPL"
        assert isinstance(analyzer.order_flow_analyzer, OrderFlowAnalyzer)
        assert isinstance(analyzer.depth_analyzer, MarketDepthAnalyzer)

    def test_update_analyzer(self):
        """Test updating analyzer with new data."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketMicrostructureAnalyzer(
            symbol="AAPL",
            order_book=book,
        )

        order = Order(
            order_id="test_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        analyzer.update(order=order)

        assert len(analyzer.order_flow_analyzer._flow_history) == 1

    def test_get_comprehensive_metrics(self):
        """Test getting comprehensive metrics."""
        book = LimitOrderBook(symbol="AAPL", tick_size=Decimal("0.01"))
        analyzer = MarketMicrostructureAnalyzer(
            symbol="AAPL",
            order_book=book,
        )

        # Add some data
        for _ in range(5):
            analyzer.update(
                order=Order(
                    order_id=f"order_{_}",
                    symbol="AAPL",
                    side=OrderSide.BUY if _ % 2 == 0 else OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=Decimal("100"),
                    price=Decimal("150.00"),
                )
            )

        metrics = analyzer.get_comprehensive_metrics()

        assert isinstance(metrics, MarketMicrostructureMetrics)
        assert metrics.symbol == "AAPL"
        assert isinstance(metrics.order_imbalance, OrderImbalance)
        assert isinstance(metrics.liquidity_regime, LiquidityRegime)
        assert 0 <= metrics.flow_toxicity <= 1
        assert 0 <= metrics.price_discovery <= 100


class TestCreateMarketMicrostructureAnalyzer:
    """Test factory function."""

    def test_factory_function(self):
        """Test create_market_microstructure_analyzer factory."""
        book = LimitOrderBook(symbol="AAPL")
        analyzer = create_market_microstructure_analyzer(
            symbol="AAPL",
            order_book=book,
        )

        assert isinstance(analyzer, MarketMicrostructureAnalyzer)


@pytest.mark.parametrize(
    "regime",
    [
        LiquidityRegime.HIGH,
        LiquidityRegime.NORMAL,
        LiquidityRegime.LOW,
        LiquidityRegime.DRY,
    ],
)
def test_liquidity_regimes(regime):
    """Test that all liquidity regimes are valid."""
    assert isinstance(regime, LiquidityRegime)


@pytest.mark.parametrize(
    "direction",
    [
        OrderFlowDirection.BUY_PRESSURE,
        OrderFlowDirection.SELL_PRESSURE,
        OrderFlowDirection.BALANCED,
    ],
)
def test_flow_directions(direction):
    """Test that all flow directions are valid."""
    assert isinstance(direction, OrderFlowDirection)
