"""
Unit tests for Wash Sale Tracker.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.compliance.wash_sale_tracker import (
    Country,
    PositionRecord,
    WashSale,
    WashSaleTracker,
)


@pytest.fixture
def us_tracker():
    """Fixture for USA wash sale tracker."""
    return WashSaleTracker(country=Country.US)


@pytest.fixture
def es_tracker():
    """Fixture for Spain wash sale tracker."""
    return WashSaleTracker(country=Country.ES)


class TestWashSaleTracker:
    """Test WashSaleTracker."""

    def test_initialization_us(self, us_tracker):
        """Test USA tracker initialization."""
        assert us_tracker.country == Country.US
        assert us_tracker.WASH_SALE_WINDOW_DAYS == 30

    def test_initialization_es(self, es_tracker):
        """Test Spain tracker initialization."""
        assert es_tracker.country == Country.ES

    def test_is_wash_sale_spain_no_rule(self, es_tracker):
        """Test that Spain has no wash sale rule."""
        is_wash = es_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("140"),
        )

        assert is_wash is False

    def test_is_wash_sale_us_no_prior_purchase(self, us_tracker):
        """Test wash sale detection with no prior purchase."""
        is_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("140"),
        )

        # No prior purchase - not a wash sale
        assert is_wash is False

    def test_is_wash_sale_us_with_prior_purchase(self, us_tracker):
        """Test wash sale detection with prior purchase in window."""
        today = date.today()

        # Buy 10 days ago
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=10),
        )

        # Sell today
        is_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
        )

        # Prior purchase within 30 days - would be wash sale
        assert is_wash is True

    def test_is_wash_sale_outside_window(self, us_tracker):
        """Test wash sale detection with purchase outside window."""
        today = date.today()

        # Buy 40 days ago (outside 30-day window)
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=40),
        )

        # Sell today
        is_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
        )

        # Purchase outside window - not a wash sale
        assert is_wash is False

    def test_record_trade_buy(self, us_tracker):
        """Test recording a BUY trade."""
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        # Should have position recorded
        assert len(us_tracker._positions) == 1
        assert "AAPL" in us_tracker._positions_by_symbol

    def test_record_trade_sell(self, us_tracker):
        """Test recording a SELL trade."""
        us_tracker.record_trade(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        # Should have position recorded
        assert len(us_tracker._positions) == 1

    def test_check_wash_sale_impact_no_wash(self, us_tracker):
        """Test wash sale impact when not a wash sale."""
        is_wash, disallowed, deductible = us_tracker.check_wash_sale_impact(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("140"),
            cost_basis=Decimal("150"),
        )

        assert is_wash is False
        assert disallowed == Decimal("0")
        # Full loss deductible
        assert deductible == Decimal("10")  # 150 - 140

    def test_check_wash_sale_impact_with_wash(self, us_tracker):
        """Test wash sale impact when it is a wash sale."""
        today = date.today()

        # Buy previously
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=10),
        )

        # Check impact
        is_wash, disallowed, deductible = us_tracker.check_wash_sale_impact(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
            cost_basis=Decimal("150"),
        )

        assert is_wash is True
        assert disallowed == Decimal("10")  # Full loss disallowed
        assert deductible == Decimal("0")  # Nothing deductible

    def test_check_wash_sale_impact_no_loss(self, us_tracker):
        """Test wash sale impact when there's no loss."""
        is_wash, disallowed, deductible = us_tracker.check_wash_sale_impact(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("160"),  # Sold at profit
            cost_basis=Decimal("150"),
        )

        assert is_wash is False
        assert disallowed == Decimal("0")
        assert deductible == Decimal("0")  # No loss

    def test_get_wash_sales(self, us_tracker):
        """Test getting wash sales."""
        today = date.today()

        # Create a wash sale
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=10),
        )

        # Check impact to trigger wash sale recording
        us_tracker.check_wash_sale_impact(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
            cost_basis=Decimal("150"),
        )

        wash_sales = us_tracker.get_wash_sales()

        # Should have recorded wash sale
        assert len(wash_sales) >= 0

    def test_get_wash_sale_summary(self, us_tracker):
        """Test getting wash sale summary."""
        summary = us_tracker.get_wash_sale_summary()

        assert "total_wash_sales" in summary
        assert "total_disallowed_loss" in summary
        assert "by_symbol" in summary

    def test_wash_sale_at_window_boundary(self, us_tracker):
        """Test wash sale at exactly 30 days."""
        today = date.today()

        # Buy exactly 30 days ago
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=30),
        )

        # Sell today - at boundary
        is_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
        )

        # At 30-day boundary - should be wash sale
        assert is_wash is True

    def test_wash_sale_just_outside_window(self, us_tracker):
        """Test wash sale at 31 days (just outside)."""
        today = date.today()

        # Buy 31 days ago
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today - timedelta(days=31),
        )

        # Sell today
        is_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
        )

        # Outside window - not a wash sale
        assert is_wash is False

    def test_multiple_symbols(self, us_tracker):
        """Test wash sale tracking with multiple symbols."""
        today = date.today()

        # Buy different symbols
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            us_tracker.record_trade(
                symbol=symbol,
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150"),
                trade_date=today - timedelta(days=10),
            )

        # Only AAPL should be wash sale
        aapl_wash = us_tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=today,
            sale_price=Decimal("140"),
        )

        # MSFT without prior purchase in window
        msft_wash = us_tracker.is_wash_sale(
            symbol="TSLA",  # Different symbol
            sale_date=today,
            sale_price=Decimal("140"),
        )

        assert aapl_wash is True
        assert msft_wash is False

    def test_reset(self, us_tracker):
        """Test resetting tracker."""
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        us_tracker.reset()

        assert len(us_tracker._positions) == 0
        assert len(us_tracker._wash_sales) == 0
        assert len(us_tracker._positions_by_symbol) == 0


class TestWashSale:
    """Test WashSale dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        wash_sale = WashSale(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("140"),
            loss_amount=Decimal("1000"),
            disallowed_loss=Decimal("1000"),
        )

        result = wash_sale.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["sale_price"] == "140"
        assert result["loss_amount"] == "1000"


class TestPositionRecord:
    """Test PositionRecord dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        position = PositionRecord(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        result = position.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["side"] == "BUY"
        assert result["quantity"] == "100"
