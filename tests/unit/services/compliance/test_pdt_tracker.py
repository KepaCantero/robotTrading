"""
Unit tests for PDT Tracker.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.compliance.pdt_tracker import Country, DayTradeRecord, PDTStatus, PDTTracker


@pytest.fixture
def us_tracker():
    """Fixture for USA PDT tracker."""
    return PDTTracker(country=Country.US)


@pytest.fixture
def es_tracker():
    """Fixture for Spain PDT tracker."""
    return PDTTracker(country=Country.ES)


class TestCountry:
    """Test Country enum."""

    def test_country_values(self):
        """Test country enum values."""
        assert Country.US.value == "US"
        assert Country.ES.value == "ES"
        assert Country.UK.value == "UK"
        assert Country.EU.value == "EU"


class TestPDTTracker:
    """Test PDTTracker."""

    def test_initialization_us(self, us_tracker):
        """Test USA tracker initialization."""
        assert us_tracker.country == Country.US
        assert Decimal("25000") == us_tracker.PDT_MIN_EQUITY
        assert us_tracker.MAX_DAY_TRADES == 3
        assert us_tracker.ROLLING_WINDOW_DAYS == 5

    def test_initialization_es(self, es_tracker):
        """Test Spain tracker initialization."""
        assert es_tracker.country == Country.ES

    def test_check_pdt_limit_spain_no_restriction(self, es_tracker):
        """Test that Spain has no PDT restriction."""
        allowed, message = es_tracker.check_pdt_limit(
            account_equity=Decimal("1000"),  # Low equity
        )

        assert allowed is True
        assert "not applicable" in message.lower()

    def test_check_pdt_limit_us_low_equity(self, us_tracker):
        """Test PDT restriction for low equity accounts."""
        allowed, message = us_tracker.check_pdt_limit(
            account_equity=Decimal("10000"),  # Below $25k
        )

        assert allowed is False
        assert "$25,000" in message
        assert "PDT restriction" in message

    def test_check_pdt_limit_us_sufficient_equity(self, us_tracker):
        """Test PDT pass with sufficient equity."""
        allowed, message = us_tracker.check_pdt_limit(
            account_equity=Decimal("30000"),  # Above $25k
        )

        assert allowed is True
        assert "passed" in message.lower()

    def test_check_pdt_limit_at_minimum(self, us_tracker):
        """Test PDT at exactly $25k."""
        allowed, message = us_tracker.check_pdt_limit(
            account_equity=Decimal("25000"),  # Exactly $25k
        )

        assert allowed is True

    def test_check_pdt_limit_below_minimum_by_one_cent(self, us_tracker):
        """Test PDT one cent below minimum."""
        allowed, message = us_tracker.check_pdt_limit(
            account_equity=Decimal("24999.99"),
        )

        assert allowed is False

    def test_record_trade_buy(self, us_tracker):
        """Test recording a BUY trade."""
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )

        # Should have open position
        assert "AAPL" in us_tracker._open_positions
        assert len(us_tracker._open_positions["AAPL"]) == 1

    def test_record_trade_sell_creates_day_trade(self, us_tracker):
        """Test that selling same day creates day trade."""
        today = date.today()

        # Buy in morning
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today,
        )

        # Sell same day - creates day trade
        us_tracker.record_trade(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("155"),
            trade_date=today,
        )

        # Should have day trade recorded
        assert len(us_tracker._day_trades) == 1
        assert us_tracker._day_trades[0].symbol == "AAPL"

    def test_record_trade_sell_different_day_no_day_trade(self, us_tracker):
        """Test that selling different day doesn't create day trade."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Buy yesterday
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=yesterday,
        )

        # Sell today - NOT a day trade
        us_tracker.record_trade(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("155"),
            trade_date=today,
        )

        # Should NOT have day trade recorded
        assert len(us_tracker._day_trades) == 0

    def test_get_status_no_restrictions(self, us_tracker):
        """Test status when no restrictions apply."""
        status = us_tracker.get_status(account_equity=Decimal("50000"))

        assert isinstance(status, PDTStatus)
        assert status.is_restricted is False
        assert status.account_equity == Decimal("50000")
        assert status.day_trades_last_5_days == 0

    def test_get_status_equity_restriction(self, us_tracker):
        """Test status with equity restriction."""
        status = us_tracker.get_status(account_equity=Decimal("10000"))

        assert status.is_restricted is True
        assert "equity" in status.restriction_reason.lower()

    def test_get_status_day_trade_limit(self, us_tracker):
        """Test status with day trade limit reached."""
        today = date.today()

        # Record 3 day trades
        for i in range(3):
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("100"),
                trade_date=today,
            )
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="SELL",
                quantity=Decimal("100"),
                price=Decimal("105"),
                trade_date=today,
            )

        status = us_tracker.get_status(account_equity=Decimal("50000"))

        assert status.is_restricted is True
        assert "day trade" in status.restriction_reason.lower()

    def test_get_day_trades(self, us_tracker):
        """Test getting day trades."""
        today = date.today()

        # Create a day trade
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today,
        )
        us_tracker.record_trade(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("155"),
            trade_date=today,
        )

        day_trades = us_tracker.get_day_trades(days=5)

        assert len(day_trades) == 1
        assert day_trades[0].symbol == "AAPL"

    def test_would_create_day_trade(self, us_tracker):
        """Test checking if trade would create day trade."""
        today = date.today()

        # Buy today
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today,
        )

        # Check if selling would create day trade
        would_create = us_tracker._would_create_day_trade("AAPL")

        assert would_create is True

    def test_check_pdt_limit_with_day_trade_count(self, us_tracker):
        """Test PDT limit considers day trade count."""
        today = date.today()

        # Create 2 day trades
        for i in range(2):
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("100"),
                trade_date=today,
            )
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="SELL",
                quantity=Decimal("100"),
                price=Decimal("105"),
                trade_date=today,
            )

        # Third day trade should be allowed
        allowed, _ = us_tracker.check_pdt_limit(
            account_equity=Decimal("50000"),
            symbol="STOCK2",
            side="SELL",
        )

        assert allowed is True

    def test_check_pdt_limit_at_max_day_trades(self, us_tracker):
        """Test PDT at maximum day trades."""
        today = date.today()

        # Create 3 day trades (max)
        for i in range(3):
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("100"),
                trade_date=today,
            )
            us_tracker.record_trade(
                symbol=f"STOCK{i}",
                side="SELL",
                quantity=Decimal("100"),
                price=Decimal("105"),
                trade_date=today,
            )

        # Fourth should be blocked
        allowed, message = us_tracker.check_pdt_limit(
            account_equity=Decimal("50000"),
            symbol="STOCK3",
            side="SELL",
        )

        assert allowed is False
        assert "3/3" in message

    def test_reset(self, us_tracker):
        """Test resetting tracker."""
        today = date.today()

        # Add some trades
        us_tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=today,
        )

        # Reset
        us_tracker.reset()

        # Should be empty
        assert len(us_tracker._all_trades) == 0
        assert len(us_tracker._day_trades) == 0
        assert len(us_tracker._open_positions) == 0


class TestDayTradeRecord:
    """Test DayTradeRecord dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = DayTradeRecord(
            symbol="AAPL",
            open_time=date.today(),
            close_time=date.today(),
            open_price=Decimal("150"),
            close_price=Decimal("155"),
            quantity=Decimal("100"),
            realized_pnl=Decimal("500"),
        )

        result = record.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["open_price"] == "150"
        assert result["realized_pnl"] == "500"


class TestPDTStatus:
    """Test PDTStatus dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        status = PDTStatus(
            day_trades_last_5_days=2,
            max_day_trades_allowed=3,
            account_equity=Decimal("50000"),
            min_equity_required=Decimal("25000"),
            is_restricted=False,
        )

        result = status.to_dict()

        assert result["day_trades_last_5_days"] == 2
        assert result["account_equity"] == "50000"
        assert result["is_restricted"] is False
