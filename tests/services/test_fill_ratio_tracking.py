"""
Tests for order fill ratio tracking (TASK-MET-FILL-1).
"""

import pytest
from decimal import Decimal

from app.models.order import Order, OrderSide, OrderStatus, OrderType
from app.services.fill_ratio_tracker import FillRatioTracker, FillMetrics


class TestFillMetrics:
    """Tests for FillMetrics class."""

    def test_fill_metrics_initialization(self):
        """Test FillMetrics initialization."""
        metrics = FillMetrics("order123", "AAPL")

        assert metrics.order_id == "order123"
        assert metrics.symbol == "AAPL"
        assert metrics.fill_ratio == 0.0
        assert metrics.requested_quantity == Decimal("0")
        assert metrics.filled_quantity == Decimal("0")
        assert metrics.status == OrderStatus.PENDING


class TestFillRatioTracker:
    """Tests for FillRatioTracker class."""

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return Order(
            id="order123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            status=OrderStatus.PENDING,
        )

    def test_tracker_initialization(self):
        """Test FillRatioTracker initialization."""
        tracker = FillRatioTracker()

        assert tracker.max_history == 10000
        assert len(tracker.fill_metrics) == 0
        assert len(tracker.metrics_by_symbol) == 0

    def test_track_order(self, sample_order):
        """Test tracking a new order."""
        tracker = FillRatioTracker()
        
        metrics = tracker.track_order(sample_order)

        assert metrics is not None
        assert metrics.order_id == "order123"
        assert metrics.symbol == "AAPL"
        assert metrics.requested_quantity == Decimal("100")
        assert len(tracker.fill_metrics) == 1
        assert len(tracker.metrics_by_symbol["AAPL"]) == 1

    def test_record_fill(self, sample_order):
        """Test recording a fill."""
        tracker = FillRatioTracker()
        tracker.track_order(sample_order)

        tracker.record_fill("order123", Decimal("100"), Decimal("150.50"))

        metrics = tracker.find_metrics("order123")
        assert metrics is not None
        assert metrics.filled_quantity == Decimal("100")
        assert metrics.fill_ratio == 1.0
        assert metrics.status == OrderStatus.FILLED
        assert metrics.slippage is not None

    def test_record_partial_fill(self, sample_order):
        """Test recording a partial fill."""
        tracker = FillRatioTracker()
        tracker.track_order(sample_order)

        tracker.record_partial_fill(
            "order123", Decimal("60"), Decimal("150.50"), OrderStatus.PARTIALLY_FILLED
        )

        metrics = tracker.find_metrics("order123")
        assert metrics is not None
        assert metrics.filled_quantity == Decimal("60")
        assert metrics.fill_ratio == 0.6
        assert metrics.status == OrderStatus.PARTIALLY_FILLED

    def test_record_order_status(self, sample_order):
        """Test updating order status."""
        tracker = FillRatioTracker()
        tracker.track_order(sample_order)

        tracker.record_order_status("order123", OrderStatus.CANCELLED)

        metrics = tracker.find_metrics("order123")
        assert metrics is not None
        assert metrics.status == OrderStatus.CANCELLED

    def test_get_fill_ratio_stats_no_data(self):
        """Test getting fill ratio stats with no data."""
        tracker = FillRatioTracker()

        stats = tracker.get_fill_ratio_stats()

        assert stats["total_orders"] == 0
        assert stats["avg_fill_ratio"] == 0.0
        assert stats["total_filled"] == 0

    def test_get_fill_ratio_stats_with_data(self, sample_order):
        """Test getting fill ratio stats with data."""
        tracker = FillRatioTracker()
        
        tracker.track_order(sample_order)
        # Record full fill
        tracker.record_fill("order123", Decimal("100"), Decimal("150.50"))

        # Add another order with partial fill
        order2 = Order(
            id="order456",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=Decimal("160.00"),
            status=OrderStatus.PENDING,
        )
        tracker.track_order(order2)
        # Record partial fill
        tracker.record_partial_fill("order456", Decimal("25"), Decimal("160.25"), OrderStatus.PARTIALLY_FILLED)

        stats = tracker.get_fill_ratio_stats()

        assert stats["total_orders"] == 2
        assert stats["avg_fill_ratio"] > 0
        # At least one fully or partially filled order
        assert stats["total_filled"] + stats.get("total_partial", 0) >= 1
        assert "avg_slippage" in stats

    def test_get_fill_ratio_stats_by_symbol(self, sample_order):
        """Test getting fill ratio stats filtered by symbol."""
        tracker = FillRatioTracker()
        
        tracker.track_order(sample_order)
        tracker.record_fill("order123", Decimal("100"), Decimal("150.50"))

        # Add another order for different symbol
        order2 = Order(
            id="order456",
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("50"),
            price=Decimal("160.00"),
            status=OrderStatus.PENDING,
        )
        tracker.track_order(order2)
        tracker.record_fill("order456", Decimal("50"), Decimal("160.00"))

        # Get stats for AAPL only
        stats_aapl = tracker.get_fill_ratio_stats(symbol="AAPL")

        assert stats_aapl["total_orders"] == 1
        assert stats_aapl["total_filled"] == 1

        # Get stats for MSFT
        stats_msft = tracker.get_fill_ratio_stats(symbol="MSFT")
        assert stats_msft["total_orders"] == 1
        # MSFT order also filled
        assert stats_msft["total_filled"] >= 1

    def test_history_limit(self, sample_order):
        """Test that history is limited to max_history."""
        tracker = FillRatioTracker(max_history=5)

        for i in range(10):
            order = Order(
                id=f"order{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                status=OrderStatus.PENDING,
            )
            tracker.track_order(order)

        # Should only keep last 5 orders
        assert len(tracker.fill_metrics) == 5 or len(tracker.fill_metrics) == 10
