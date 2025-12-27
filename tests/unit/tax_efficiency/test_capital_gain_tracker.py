"""
T15.1.3: CapitalGainTracker - Comprehensive unit tests

Tests cover:
- ST/LT classification (365 day boundary)
- FIFO/LIFO/AVERAGE_COST cost basis methods
- Realized vs unrealized gain tracking
- Tax liability projection
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.tax_efficiency.capital_gain_tracker import CapitalGainTracker


@pytest.fixture
def tracker():
    """Create CapitalGainTracker instance."""
    return CapitalGainTracker()


@pytest.fixture
def base_date():
    """Base date for test trades."""
    return datetime(2025, 6, 15)


class TestRecordPositionPurchase:
    """Test recording position purchases."""

    def test_record_single_purchase(self, tracker):
        """Record a single purchase transaction."""
        tracker.record_position_purchase(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("150"),
            purchase_date=datetime(2025, 1, 1),
        )

        assert "AAPL" in tracker.position_history
        assert len(tracker.position_history["AAPL"]) == 1
        record = tracker.position_history["AAPL"][0]
        assert record["quantity"] == Decimal("100")
        assert record["price"] == Decimal("150")
        assert record["cost_basis"] == Decimal("15000")

    def test_record_multiple_purchases_same_symbol(self, tracker):
        """Record multiple purchases of same symbol."""
        tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("150"), datetime(2025, 1, 1)
        )
        tracker.record_position_purchase(
            "AAPL", Decimal("50"), Decimal("160"), datetime(2025, 3, 1)
        )

        assert len(tracker.position_history["AAPL"]) == 2
        assert tracker.position_history["AAPL"][0]["quantity"] == Decimal("100")
        assert tracker.position_history["AAPL"][1]["quantity"] == Decimal("50")

    def test_record_purchases_different_symbols(self, tracker):
        """Record purchases for different symbols."""
        tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("150"), datetime(2025, 1, 1)
        )
        tracker.record_position_purchase(
            "MSFT", Decimal("50"), Decimal("300"), datetime(2025, 1, 5)
        )

        assert "AAPL" in tracker.position_history
        assert "MSFT" in tracker.position_history


class TestRecordPositionSalesFIFO:
    """Test recording position sales using FIFO method."""

    def test_fifo_single_lot_sale(self, tracker, base_date):
        """FIFO: Sell all shares from single purchase."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        gains = tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=400), method="FIFO"
        )

        assert len(gains) == 1
        assert gains[0].gain_loss == Decimal("2000")  # (120-100)*100
        assert gains[0].is_long_term is True  # 400 days > 365
        assert gains[0].symbol == "AAPL"

    def test_fifo_multiple_lots_partial_sale(self, tracker, base_date):
        """FIFO: Sell from multiple lots, oldest first."""
        # First purchase (oldest)
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        # Second purchase (newer)
        tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("110"), base_date + timedelta(days=100)
        )

        # Sell 150 shares - should use 100 from first lot + 50 from second lot
        gains = tracker.record_position_sale(
            "AAPL", Decimal("150"), Decimal("120"), base_date + timedelta(days=400), method="FIFO"
        )

        assert len(gains) == 2
        # First lot: 100 shares at €100, sold at €120 = €2000 gain, LT
        assert gains[0].quantity == Decimal("100")
        assert gains[0].purchase_price == Decimal("100")
        assert gains[0].gain_loss == Decimal("2000")
        assert gains[0].is_long_term is True

        # Second lot: 50 shares at €110, sold at €120 = €500 gain, LT
        assert gains[1].quantity == Decimal("50")
        assert gains[1].purchase_price == Decimal("110")
        assert gains[1].gain_loss == Decimal("500")

    def test_fifo_short_term_classification(self, tracker, base_date):
        """FIFO: Correctly classify short-term gains."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        gains = tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        assert gains[0].is_long_term is False  # 100 days < 365
        assert gains[0].tax_rate == Decimal("0.35")  # ST rate


class TestRecordPositionSalesLIFO:
    """Test recording position sales using LIFO method."""

    def test_lifo_multiple_lots(self, tracker, base_date):
        """LIFO: Sell from newest lots first."""
        # First purchase (oldest)
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        # Second purchase (newer)
        tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("110"), base_date + timedelta(days=100)
        )

        # Sell 150 shares - should use 100 from second lot + 50 from first lot (LIFO order)
        gains = tracker.record_position_sale(
            "AAPL", Decimal("150"), Decimal("120"), base_date + timedelta(days=400), method="LIFO"
        )

        assert len(gains) == 2
        # First lot used (newest): 100 shares at €110
        assert gains[0].purchase_price == Decimal("110")
        # Second lot used: 50 shares at €100
        assert gains[1].purchase_price == Decimal("100")


class TestRecordPositionSalesAverageCost:
    """Test recording position sales using AVERAGE_COST method."""

    def test_average_cost_single_lot(self, tracker, base_date):
        """AVERAGE_COST: Single lot uses actual price."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        gains = tracker.record_position_sale(
            "AAPL",
            Decimal("100"),
            Decimal("120"),
            base_date + timedelta(days=400),
            method="AVERAGE_COST",
        )

        assert len(gains) == 1
        assert gains[0].gain_loss == Decimal("2000")

    def test_average_cost_multiple_lots(self, tracker, base_date):
        """AVERAGE_COST: Multiple lots use weighted average."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("110"), base_date + timedelta(days=100)
        )

        # Average cost: (100*100 + 100*110) / 200 = €105
        gains = tracker.record_position_sale(
            "AAPL",
            Decimal("200"),
            Decimal("120"),
            base_date + timedelta(days=400),
            method="AVERAGE_COST",
        )

        assert len(gains) == 1
        assert gains[0].purchase_price == Decimal("105")
        assert gains[0].gain_loss == Decimal("3000")  # (120-105)*200


class TestCalculateUnrealizedGains:
    """Test unrealized gain/loss calculation."""

    def test_unrealized_gain_single_position(self, tracker, base_date):
        """Calculate unrealized gain on profitable position."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)

        unrealized = tracker.calculate_unrealized_gains(
            {"AAPL": Decimal("12000")},  # Current value
            {"AAPL": Decimal("120")},  # Current price
            {"AAPL": Decimal("100")},  # Quantity
        )

        assert "AAPL" in unrealized
        assert unrealized["AAPL"].unrealized_gain_loss == Decimal("2000")

    def test_unrealized_loss_single_position(self, tracker, base_date):
        """Calculate unrealized loss on underwater position."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)

        unrealized = tracker.calculate_unrealized_gains(
            {"AAPL": Decimal("9000")},
            {"AAPL": Decimal("90")},
            {"AAPL": Decimal("100")},
        )

        assert unrealized["AAPL"].unrealized_gain_loss == Decimal("-1000")

    def test_unrealized_long_term_classification(self, tracker):
        """Classify unrealized gains as LT when held >365 days."""
        old_date = datetime.now() - timedelta(days=400)
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), old_date)

        unrealized = tracker.calculate_unrealized_gains(
            {"AAPL": Decimal("12000")},
            {"AAPL": Decimal("120")},
            {"AAPL": Decimal("100")},
        )

        assert unrealized["AAPL"].is_long_term is True
        assert unrealized["AAPL"].projected_tax_if_sold == Decimal("300")  # 2000 * 0.15

    def test_unrealized_short_term_classification(self, tracker):
        """Classify unrealized gains as ST when held <365 days."""
        recent_date = datetime.now() - timedelta(days=100)
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), recent_date)

        unrealized = tracker.calculate_unrealized_gains(
            {"AAPL": Decimal("12000")},
            {"AAPL": Decimal("120")},
            {"AAPL": Decimal("100")},
        )

        assert unrealized["AAPL"].is_long_term is False
        assert unrealized["AAPL"].projected_tax_if_sold == Decimal("700")  # 2000 * 0.35


class TestGetShortTermAndLongTermGains:
    """Test ST/LT gain and loss aggregation."""

    def test_get_short_term_gains(self, tracker, base_date):
        """Calculate total short-term gains."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        st_gains = tracker.get_short_term_gains()
        assert st_gains == Decimal("2000")

    def test_get_long_term_gains(self, tracker, base_date):
        """Calculate total long-term gains."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=400), method="FIFO"
        )

        lt_gains = tracker.get_long_term_gains()
        assert lt_gains == Decimal("2000")

    def test_get_short_term_losses(self, tracker, base_date):
        """Calculate total short-term losses."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("80"), base_date + timedelta(days=100), method="FIFO"
        )

        st_losses = tracker.get_short_term_losses()
        assert st_losses == Decimal("2000")

    def test_get_long_term_losses(self, tracker, base_date):
        """Calculate total long-term losses."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("80"), base_date + timedelta(days=400), method="FIFO"
        )

        lt_losses = tracker.get_long_term_losses()
        assert lt_losses == Decimal("2000")

    def test_mixed_gains_and_losses(self, tracker, base_date):
        """Calculate mix of ST gains, ST losses, LT gains, LT losses."""
        # ST gain
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        # LT loss
        tracker.record_position_purchase("MSFT", Decimal("50"), Decimal("200"), base_date)
        tracker.record_position_sale(
            "MSFT", Decimal("50"), Decimal("150"), base_date + timedelta(days=400), method="FIFO"
        )

        assert tracker.get_short_term_gains() == Decimal("2000")
        assert tracker.get_long_term_losses() == Decimal("2500")
        assert tracker.get_short_term_losses() == Decimal("0")
        assert tracker.get_long_term_gains() == Decimal("0")


class TestProjectAnnualTax:
    """Test annual tax liability projection."""

    def test_project_tax_short_term_gain(self, tracker, base_date):
        """Project tax on short-term gains."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        tax = tracker.project_annual_tax(
            marginal_tax_rate_st=Decimal("0.35"), marginal_tax_rate_lt=Decimal("0.15")
        )

        assert tax == Decimal("700")  # 2000 * 0.35

    def test_project_tax_long_term_gain(self, tracker, base_date):
        """Project tax on long-term gains."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=400), method="FIFO"
        )

        tax = tracker.project_annual_tax(
            marginal_tax_rate_st=Decimal("0.35"), marginal_tax_rate_lt=Decimal("0.15")
        )

        assert tax == Decimal("300")  # 2000 * 0.15

    def test_project_tax_st_losses_offset_st_gains(self, tracker, base_date):
        """ST losses offset ST gains first."""
        # ST gain
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        # ST loss
        tracker.record_position_purchase("MSFT", Decimal("50"), Decimal("200"), base_date)
        tracker.record_position_sale(
            "MSFT", Decimal("50"), Decimal("150"), base_date + timedelta(days=100), method="FIFO"
        )

        tax = tracker.project_annual_tax(
            marginal_tax_rate_st=Decimal("0.35"), marginal_tax_rate_lt=Decimal("0.15")
        )

        # Net ST: 2000 - 2500 = -500
        # Remaining loss offsets LT: 0
        assert tax == Decimal("0")

    def test_project_tax_lt_losses_offset_lt_gains(self, tracker, base_date):
        """LT losses offset LT gains."""
        # LT gain
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=400), method="FIFO"
        )

        # LT loss
        tracker.record_position_purchase("MSFT", Decimal("50"), Decimal("200"), base_date)
        tracker.record_position_sale(
            "MSFT", Decimal("50"), Decimal("150"), base_date + timedelta(days=400), method="FIFO"
        )

        tax = tracker.project_annual_tax(
            marginal_tax_rate_st=Decimal("0.35"), marginal_tax_rate_lt=Decimal("0.15")
        )

        # Net LT: 2000 - 2500 = -500
        # Tax: 0
        assert tax == Decimal("0")

    def test_project_tax_no_gains_or_losses(self, tracker):
        """Project zero tax when no trades made."""
        tax = tracker.project_annual_tax()
        assert tax == Decimal("0")


class TestGenerateTaxLotReport:
    """Test comprehensive tax lot reporting."""

    def test_basic_tax_lot_report(self, tracker, base_date):
        """Generate basic tax lot report."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        report = tracker.generate_tax_lot_report()

        assert report.report_date is not None
        assert report.total_short_term_gains == Decimal("2000")
        assert report.total_long_term_gains == Decimal("0")
        assert report.net_capital_gain_loss == Decimal("2000")

    def test_tax_lot_report_with_mixed_trades(self, tracker, base_date):
        """Report with mixed ST/LT gains and losses."""
        # ST gain
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        # LT gain
        tracker.record_position_purchase("MSFT", Decimal("50"), Decimal("200"), base_date)
        tracker.record_position_sale(
            "MSFT", Decimal("50"), Decimal("220"), base_date + timedelta(days=400), method="FIFO"
        )

        # ST loss
        tracker.record_position_purchase("GOOGL", Decimal("20"), Decimal("150"), base_date)
        tracker.record_position_sale(
            "GOOGL", Decimal("20"), Decimal("130"), base_date + timedelta(days=100), method="FIFO"
        )

        report = tracker.generate_tax_lot_report()

        assert report.total_short_term_gains == Decimal("2000")
        assert report.total_long_term_gains == Decimal("1000")
        assert report.total_short_term_losses == Decimal("400")
        assert report.net_capital_gain_loss == Decimal("2600")

    def test_tax_lot_report_projected_tax(self, tracker, base_date):
        """Report includes projected annual tax."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=100), method="FIFO"
        )

        report = tracker.generate_tax_lot_report()

        # ST gain of €2000 at 35% rate = €700 tax
        assert report.projected_annual_tax == Decimal("700")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_365_day_boundary(self, tracker, base_date):
        """Position held exactly 365 days should be classified as LT."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        gains = tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=365), method="FIFO"
        )

        assert gains[0].is_long_term is True

    def test_364_day_boundary(self, tracker, base_date):
        """Position held 364 days should be classified as ST."""
        tracker.record_position_purchase("AAPL", Decimal("100"), Decimal("100"), base_date)
        gains = tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"), base_date + timedelta(days=364), method="FIFO"
        )

        assert gains[0].is_long_term is False

    def test_fractional_shares(self, tracker, base_date):
        """Handle fractional shares correctly."""
        tracker.record_position_purchase("AAPL", Decimal("100.5"), Decimal("150.25"), base_date)
        gains = tracker.record_position_sale(
            "AAPL",
            Decimal("100.5"),
            Decimal("160.75"),
            base_date + timedelta(days=400),
            method="FIFO",
        )

        expected_gain = (Decimal("160.75") - Decimal("150.25")) * Decimal("100.5")
        assert gains[0].gain_loss == expected_gain

    def test_zero_quantity_purchase(self, tracker):
        """Handle edge case of zero quantity."""
        tracker.record_position_purchase("AAPL", Decimal("0"), Decimal("100"), datetime.now())

        assert "AAPL" in tracker.position_history
        assert tracker.position_history["AAPL"][0]["quantity"] == Decimal("0")

    def test_no_purchase_history_for_sale(self, tracker):
        """Return empty list when selling position with no purchase history."""
        gains = tracker.record_position_sale(
            "UNKNOWN", Decimal("100"), Decimal("120"), datetime.now(), method="FIFO"
        )

        assert len(gains) == 0

    def test_decimal_precision_maintained(self, tracker, base_date):
        """Maintain decimal precision in calculations."""
        tracker.record_position_purchase("AAPL", Decimal("33.333"), Decimal("150.123"), base_date)
        gains = tracker.record_position_sale(
            "AAPL",
            Decimal("33.333"),
            Decimal("160.456"),
            base_date + timedelta(days=400),
            method="FIFO",
        )

        expected_gain = (Decimal("160.456") - Decimal("150.123")) * Decimal("33.333")
        assert abs(gains[0].gain_loss - expected_gain) < Decimal("0.01")
