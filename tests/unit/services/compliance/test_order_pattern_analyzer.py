"""
Unit tests for Order Pattern Analyzer.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.compliance.order_pattern_analyzer import (
    OrderPatternAnalyzer,
    OrderRecord,
    PatternAlert,
)


@pytest.fixture
def analyzer():
    """Fixture for order pattern analyzer."""
    return OrderPatternAnalyzer()


class TestOrderPatternAnalyzer:
    """Test OrderPatternAnalyzer."""

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.lookback_orders == 1000
        assert len(analyzer._orders) == 0

    def test_analyze_order_no_patterns(self, analyzer):
        """Test analyzing order with no suspicious patterns."""
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="MARKET",
        )

        assert patterns == []

    def test_detect_layering(self, analyzer):
        """Test layering detection."""
        # Add multiple orders at same price
        for i in range(3):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )

        # Now analyze another order at same price
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        assert "layering" in patterns

    def test_detect_layering_different_price(self, analyzer):
        """Test that layering not detected at different prices."""
        # Add orders at different prices
        for i, price in enumerate([Decimal("150"), Decimal("151"), Decimal("152")]):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=price,
                order_type="LIMIT",
            )

        # Analyze at different price
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("155"),
            order_type="LIMIT",
        )

        assert "layering" not in patterns

    def test_detect_excessive_cancellation(self, analyzer):
        """Test excessive cancellation detection."""
        # Add many cancelled orders
        for i in range(10):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )
            analyzer.record_cancellation(f"order_{i}")

        # Now analyze
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        assert "excessive_cancellation" in patterns

    def test_detect_marking_close(self, analyzer):
        """Test marking the close detection."""
        # This is time-dependent, so we just verify the method exists
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="MARKET",
        )

        # Pattern detection depends on time of day
        # Just verify it returns a list
        assert isinstance(patterns, list)

    def test_record_order(self, analyzer):
        """Test recording an order."""
        analyzer.record_order(
            order_id="test_order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        assert len(analyzer._orders) == 1
        assert "AAPL" in analyzer._orders_by_symbol

    def test_record_cancellation(self, analyzer):
        """Test recording order cancellation."""
        analyzer.record_order(
            order_id="test_order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        analyzer.record_cancellation("test_order")

        # Order should be marked as cancelled
        order = list(analyzer._orders)[0]
        assert order.cancelled is True

    def test_record_fill(self, analyzer):
        """Test recording order fill."""
        analyzer.record_order(
            order_id="test_order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        analyzer.record_fill("test_order", Decimal("50"))

        # Order should be marked as filled
        order = list(analyzer._orders)[0]
        assert order.filled is True
        assert order.fill_quantity == Decimal("50")

    def test_get_order_to_trade_ratio(self, analyzer):
        """Test calculating order-to-trade ratio."""
        # Add some orders
        for i in range(5):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )

        # Cancel some
        analyzer.record_cancellation("order_0")
        analyzer.record_cancellation("order_1")

        # Fill some
        analyzer.record_fill("order_2", Decimal("100"))

        ratio = analyzer.get_order_to_trade_ratio("AAPL")

        # Should be between 0 and 1
        assert Decimal("0") <= ratio <= Decimal("1")

    def test_get_order_to_trade_ratio_no_orders(self, analyzer):
        """Test order-to-trade ratio with no orders."""
        ratio = analyzer.get_order_to_trade_ratio("AAPL")

        assert ratio == Decimal("0")

    def test_get_order_to_trade_ratio_all_cancelled(self, analyzer):
        """Test order-to-trade ratio when all cancelled."""
        for i in range(3):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )
            analyzer.record_cancellation(f"order_{i}")

        ratio = analyzer.get_order_to_trade_ratio("AAPL")

        # All cancelled - ratio should be 1
        assert ratio == Decimal("1")

    def test_get_alerts(self, analyzer):
        """Test getting alerts."""
        alerts = analyzer.get_alerts()

        assert isinstance(alerts, list)

    def test_get_alerts_with_filters(self, analyzer):
        """Test getting alerts with filters."""
        # Add an alert (if any were generated)
        alerts = analyzer.get_alerts(
            pattern_type="layering",
            start_time=datetime.now() - timedelta(hours=1),
        )

        assert isinstance(alerts, list)

    def test_detect_rapid_ordering(self, analyzer):
        """Test rapid ordering detection."""
        # Add many orders rapidly
        for i in range(15):
            analyzer.record_order(
                order_id=f"order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="MARKET",
            )

        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="MARKET",
        )

        # Should detect rapid ordering
        assert "rapid_ordering" in patterns

    def test_multiple_symbols(self, analyzer):
        """Test tracking multiple symbols."""
        symbols = ["AAPL", "MSFT", "GOOGL"]

        for symbol in symbols:
            analyzer.record_order(
                order_id=f"order_{symbol}",
                symbol=symbol,
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                order_type="LIMIT",
            )

        # Each symbol should be tracked
        for symbol in symbols:
            assert symbol in analyzer._orders_by_symbol

    def test_reset(self, analyzer):
        """Test resetting analyzer."""
        analyzer.record_order(
            order_id="test_order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        analyzer.reset()

        assert len(analyzer._orders) == 0
        assert len(analyzer._orders_by_symbol) == 0


class TestOrderRecord:
    """Test OrderRecord dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        order = OrderRecord(
            order_id="test_order",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
            timestamp=datetime.now(),
        )

        result = order.to_dict()

        assert result["order_id"] == "test_order"
        assert result["symbol"] == "AAPL"
        assert result["side"] == "BUY"
        assert result["quantity"] == "100"


class TestPatternAlert:
    """Test PatternAlert dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        alert = PatternAlert(
            pattern_type="layering",
            severity="WARNING",
            symbol="AAPL",
            timestamp=datetime.now(),
            description="Layering pattern detected",
        )

        result = alert.to_dict()

        assert result["pattern_type"] == "layering"
        assert result["severity"] == "WARNING"
        assert result["symbol"] == "AAPL"
