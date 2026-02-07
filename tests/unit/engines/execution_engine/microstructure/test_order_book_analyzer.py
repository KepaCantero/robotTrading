"""
Unit tests for Order Book Analyzer.
"""

from decimal import Decimal

import pandas as pd
import pytest

from app.engines.execution_engine.microstructure.order_book_analyzer import (
    BookAnalysisResult,
    OrderBookLevel,
    OrderBookSnapshot,
    get_order_book_analyzer,
)


@pytest.fixture
def sample_order_book():
    """Create sample order book snapshot."""
    timestamp = pd.Timestamp("2024-01-15 10:30:00")

    bids = [
        OrderBookLevel(price=Decimal("100.00"), size=Decimal("1000")),
        OrderBookLevel(price=Decimal("99.99"), size=Decimal("2000")),
        OrderBookLevel(price=Decimal("99.98"), size=Decimal("3000")),
        OrderBookLevel(price=Decimal("99.97"), size=Decimal("4000")),
        OrderBookLevel(price=Decimal("99.96"), size=Decimal("5000")),
    ]

    asks = [
        OrderBookLevel(price=Decimal("100.01"), size=Decimal("1000")),
        OrderBookLevel(price=Decimal("100.02"), size=Decimal("2000")),
        OrderBookLevel(price=Decimal("100.03"), size=Decimal("3000")),
        OrderBookLevel(price=Decimal("100.04"), size=Decimal("4000")),
        OrderBookLevel(price=Decimal("100.05"), size=Decimal("5000")),
    ]

    return OrderBookSnapshot(
        symbol="AAPL",
        timestamp=timestamp,
        bids=bids,
        asks=asks,
    )


@pytest.fixture
def analyzer():
    """Get order book analyzer instance."""
    return get_order_book_analyzer()


class TestOrderBookSnapshot:
    """Test OrderBookSnapshot class."""

    def test_best_bid_ask(self, sample_order_book):
        """Test best bid and ask properties."""
        assert sample_order_book.best_bid == Decimal("100.00")
        assert sample_order_book.best_ask == Decimal("100.01")

    def test_mid_price(self, sample_order_book):
        """Test mid price calculation."""
        expected = (Decimal("100.00") + Decimal("100.01")) / 2
        assert sample_order_book.mid_price == expected

    def test_spread(self, sample_order_book):
        """Test spread calculation."""
        assert sample_order_book.spread == Decimal("0.01")

    def test_spread_bps(self, sample_order_book):
        """Test spread in basis points."""
        # (0.01 / 100.005) * 10000 ≈ 1.0
        assert sample_order_book.spread_bps is not None
        assert abs(float(sample_order_book.spread_bps) - 1.0) < 0.1


class TestOrderBookAnalyzer:
    """Test OrderBookAnalyzer class."""

    def test_analyze_order_book(self, analyzer, sample_order_book):
        """Test basic order book analysis."""
        result = analyzer.analyze_order_book(sample_order_book)

        assert isinstance(result, BookAnalysisResult)
        assert result.symbol == "AAPL"
        assert result.spread_bps > 0

    def test_imbalance_calculation(self, analyzer, sample_order_book):
        """Test order book imbalance calculation."""
        result = analyzer.analyze_order_book(sample_order_book)

        # Should be balanced (equal volume on both sides)
        assert -1 <= result.imbalance <= 1

    def test_effective_spread(self, analyzer, sample_order_book):
        """Test effective spread calculation."""
        result = analyzer.analyze_order_book(sample_order_book)

        # Effective spread should be >= nominal spread
        if result.effective_spread_1000:
            assert result.effective_spread_1000 >= result.spread_bps

    def test_liquidity_score(self, analyzer, sample_order_book):
        """Test liquidity score calculation."""
        result = analyzer.analyze_order_book(sample_order_book)

        # Score should be between 0 and 100
        assert 0 <= result.liquidity_score <= 100

    def test_max_size_recommendation(self, analyzer, sample_order_book):
        """Test maximum size recommendation."""
        result = analyzer.analyze_order_book(sample_order_book)

        # Should recommend a positive max size
        assert result.recommended_max_size > 0


class TestOrderBookAnalyzerEdgeCases:
    """Test edge cases for OrderBookAnalyzer."""

    def test_empty_order_book(self, analyzer):
        """Test handling of empty order book."""
        empty_book = OrderBookSnapshot(
            symbol="TEST",
            timestamp=pd.Timestamp.now(),
            bids=[],
            asks=[],
        )

        with pytest.raises(ValueError):
            analyzer.analyze_order_book(empty_book)

    def test_shallow_order_book(self, analyzer):
        """Test handling of shallow order book."""
        shallow_book = OrderBookSnapshot(
            symbol="TEST",
            timestamp=pd.Timestamp.now(),
            bids=[OrderBookLevel(price=Decimal("100"), size=Decimal("100"))],
            asks=[OrderBookLevel(price=Decimal("101"), size=Decimal("100"))],
        )

        result = analyzer.analyze_order_book(shallow_book)
        assert result.symbol == "TEST"

    def test_imbalanced_order_book(self, analyzer):
        """Test handling of imbalanced order book."""
        imbalanced_book = OrderBookSnapshot(
            symbol="TEST",
            timestamp=pd.Timestamp.now(),
            bids=[
                OrderBookLevel(price=Decimal("100"), size=Decimal("10000")),
            ],
            asks=[
                OrderBookLevel(price=Decimal("101"), size=Decimal("100")),
            ],
        )

        result = analyzer.analyze_order_book(imbalanced_book)
        # Should show buy-side imbalance
        assert result.imbalance > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
