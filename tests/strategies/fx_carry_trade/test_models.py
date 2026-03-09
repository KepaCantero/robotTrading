"""
Tests for FX Carry Trade Strategy data models.

This module tests the data models used in the FX Carry Trade strategy,
including currency pairs, signals, positions, rate quotes, and configuration.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.strategies.fx_carry_trade.models import (
    CurrencyCode,
    FXCarryPosition,
    FXCarrySignal,
    FXCarryTradeConfig,
    FXPair,
    FXRateQuote,
    InterestRateQuote,
)


class TestCurrencyCode:
    """Tests for CurrencyCode enum."""

    def test_all_currency_codes_defined(self) -> None:
        """Test that all expected currency codes are defined."""
        expected_codes = [
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CHF",
            "CAD",
            "AUD",
            "NZD",
            "SEK",
            "NOK",
        ]

        for code in expected_codes:
            assert hasattr(CurrencyCode, code)
            assert getattr(CurrencyCode, code).value == code

    def test_currency_code_is_string(self) -> None:
        """Test that CurrencyCode values are strings."""
        assert isinstance(CurrencyCode.USD, str)
        assert CurrencyCode.EUR.value == "EUR"


class TestFXPair:
    """Tests for FXPair dataclass."""

    def test_pair_creation(self) -> None:
        """Test creating a valid FX pair."""
        pair = FXPair(base_currency="USD", quote_currency="JPY")

        assert pair.base_currency == "USD"
        assert pair.quote_currency == "JPY"

    def test_pair_string_representation(self) -> None:
        """Test string representation of FX pair."""
        pair = FXPair(base_currency="EUR", quote_currency="USD")
        assert str(pair) == "EUR/USD"

    def test_pair_inverse(self) -> None:
        """Test getting inverse pair."""
        pair = FXPair(base_currency="USD", quote_currency="JPY")
        inverse = pair.inverse

        assert inverse.base_currency == "JPY"
        assert inverse.quote_currency == "USD"

    def test_pair_inverse_double(self) -> None:
        """Test that double inverse returns original pair."""
        pair = FXPair(base_currency="EUR", quote_currency="GBP")
        double_inverse = pair.inverse.inverse

        assert double_inverse.base_currency == pair.base_currency
        assert double_inverse.quote_currency == pair.quote_currency

    def test_pair_invalid_base_currency(self) -> None:
        """Test validation rejects invalid base currency."""
        with pytest.raises(ValueError, match="Invalid base currency code"):
            FXPair(base_currency="US", quote_currency="JPY")

        with pytest.raises(ValueError, match="Invalid base currency code"):
            FXPair(base_currency="", quote_currency="JPY")

    def test_pair_invalid_quote_currency(self) -> None:
        """Test validation rejects invalid quote currency."""
        with pytest.raises(ValueError, match="Invalid quote currency code"):
            FXPair(base_currency="USD", quote_currency="JP")

        with pytest.raises(ValueError, match="Invalid quote currency code"):
            FXPair(base_currency="USD", quote_currency="")

    def test_pair_same_currencies(self) -> None:
        """Test validation rejects same base and quote currency."""
        with pytest.raises(ValueError, match="cannot be the same"):
            FXPair(base_currency="USD", quote_currency="USD")

    def test_pair_immutability(self) -> None:
        """Test that FXPair is immutable (frozen dataclass)."""
        pair = FXPair(base_currency="USD", quote_currency="JPY")

        with pytest.raises(AttributeError):
            pair.base_currency = "EUR"  # type: ignore


class TestFXCarrySignal:
    """Tests for FXCarrySignal dataclass."""

    @pytest.fixture
    def valid_signal_data(self) -> dict:
        """Provide valid signal data for testing."""
        return {
            "pair": FXPair(base_currency="USD", quote_currency="JPY"),
            "spot_rate": Decimal("110.50"),
            "forward_rate": Decimal("110.20"),
            "interest_rate_diff": Decimal("0.025"),
            "forward_premium": Decimal("-0.0027"),
            "carry": Decimal("0.0277"),
            "signal": Decimal("0.5"),
            "timestamp": date(2024, 1, 15),
            "months": 3,
        }

    def test_signal_creation(self, valid_signal_data: dict) -> None:
        """Test creating a valid carry trade signal."""
        signal = FXCarrySignal(**valid_signal_data)

        assert signal.pair == valid_signal_data["pair"]
        assert signal.spot_rate == Decimal("110.50")
        assert signal.forward_rate == Decimal("110.20")
        assert signal.interest_rate_diff == Decimal("0.025")
        assert signal.forward_premium == Decimal("-0.0027")
        assert signal.carry == Decimal("0.0277")
        assert signal.signal == Decimal("0.5")
        assert signal.timestamp == date(2024, 1, 15)
        assert signal.months == 3

    def test_signal_invalid_spot_rate(self, valid_signal_data: dict) -> None:
        """Test validation rejects non-positive spot rate."""
        valid_signal_data["spot_rate"] = Decimal("0")
        with pytest.raises(ValueError, match="Spot rate must be positive"):
            FXCarrySignal(**valid_signal_data)

        valid_signal_data["spot_rate"] = Decimal("-110.50")
        with pytest.raises(ValueError, match="Spot rate must be positive"):
            FXCarrySignal(**valid_signal_data)

    def test_signal_invalid_forward_rate(self, valid_signal_data: dict) -> None:
        """Test validation rejects non-positive forward rate."""
        valid_signal_data["forward_rate"] = Decimal("0")
        with pytest.raises(ValueError, match="Forward rate must be positive"):
            FXCarrySignal(**valid_signal_data)

    def test_signal_invalid_signal_range(self, valid_signal_data: dict) -> None:
        """Test validation rejects signal outside [-1, 1]."""
        valid_signal_data["signal"] = Decimal("1.5")
        with pytest.raises(ValueError, match="Signal must be between -1 and 1"):
            FXCarrySignal(**valid_signal_data)

        valid_signal_data["signal"] = Decimal("-1.5")
        with pytest.raises(ValueError, match="Signal must be between -1 and 1"):
            FXCarrySignal(**valid_signal_data)

    def test_signal_boundary_values(self, valid_signal_data: dict) -> None:
        """Test signal creation with boundary values."""
        valid_signal_data["signal"] = Decimal("1")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal == Decimal("1")

        valid_signal_data["signal"] = Decimal("-1")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal == Decimal("-1")

        valid_signal_data["signal"] = Decimal("0")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal == Decimal("0")

    def test_signal_is_long(self, valid_signal_data: dict) -> None:
        """Test is_long property."""
        valid_signal_data["signal"] = Decimal("0.5")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.is_long is True
        assert signal.is_short is False

        valid_signal_data["signal"] = Decimal("0")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.is_long is False

    def test_signal_is_short(self, valid_signal_data: dict) -> None:
        """Test is_short property."""
        valid_signal_data["signal"] = Decimal("-0.5")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.is_short is True
        assert signal.is_long is False

    def test_signal_is_neutral(self, valid_signal_data: dict) -> None:
        """Test is_neutral property."""
        valid_signal_data["signal"] = Decimal("0")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.is_neutral is True

        valid_signal_data["signal"] = Decimal("0.1")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.is_neutral is False

    def test_signal_strength_weak(self, valid_signal_data: dict) -> None:
        """Test signal strength classification - weak."""
        valid_signal_data["signal"] = Decimal("0.1")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "WEAK"

        valid_signal_data["signal"] = Decimal("-0.15")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "WEAK"

    def test_signal_strength_moderate(self, valid_signal_data: dict) -> None:
        """Test signal strength classification - moderate."""
        valid_signal_data["signal"] = Decimal("0.3")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "MODERATE"

        valid_signal_data["signal"] = Decimal("-0.4")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "MODERATE"

    def test_signal_strength_strong(self, valid_signal_data: dict) -> None:
        """Test signal strength classification - strong."""
        valid_signal_data["signal"] = Decimal("0.6")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "STRONG"

        valid_signal_data["signal"] = Decimal("-0.7")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "STRONG"

    def test_signal_strength_very_strong(self, valid_signal_data: dict) -> None:
        """Test signal strength classification - very strong."""
        valid_signal_data["signal"] = Decimal("0.85")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "VERY_STRONG"

        valid_signal_data["signal"] = Decimal("1.0")
        signal = FXCarrySignal(**valid_signal_data)
        assert signal.signal_strength == "VERY_STRONG"


class TestFXCarryPosition:
    """Tests for FXCarryPosition dataclass."""

    @pytest.fixture
    def valid_position_data(self) -> dict:
        """Provide valid position data for testing."""
        return {
            "pair": FXPair(base_currency="USD", quote_currency="JPY"),
            "quantity": Decimal("100000"),
            "entry_price": Decimal("110.50"),
            "current_price": Decimal("111.00"),
            "carry_return": Decimal("0.01"),
            "price_return": Decimal("0.0045"),
            "total_return": Decimal("0.0145"),
            "entry_date": date(2024, 1, 10),
            "current_date": date(2024, 1, 15),
        }

    def test_position_creation(self, valid_position_data: dict) -> None:
        """Test creating a valid carry trade position."""
        position = FXCarryPosition(**valid_position_data)

        assert position.pair == valid_position_data["pair"]
        assert position.quantity == Decimal("100000")
        assert position.entry_price == Decimal("110.50")
        assert position.current_price == Decimal("111.00")
        assert position.carry_return == Decimal("0.01")
        assert position.price_return == Decimal("0.0045")
        assert position.total_return == Decimal("0.0145")
        assert position.entry_date == date(2024, 1, 10)
        assert position.current_date == date(2024, 1, 15)

    def test_position_invalid_entry_price(self, valid_position_data: dict) -> None:
        """Test validation rejects non-positive entry price."""
        valid_position_data["entry_price"] = Decimal("0")
        with pytest.raises(ValueError, match="Entry price must be positive"):
            FXCarryPosition(**valid_position_data)

    def test_position_invalid_current_price(self, valid_position_data: dict) -> None:
        """Test validation rejects non-positive current price."""
        valid_position_data["current_price"] = Decimal("0")
        with pytest.raises(ValueError, match="Current price must be positive"):
            FXCarryPosition(**valid_position_data)

    def test_position_invalid_date_order(self, valid_position_data: dict) -> None:
        """Test validation rejects entry date after current date."""
        valid_position_data["entry_date"] = date(2024, 1, 20)
        valid_position_data["current_date"] = date(2024, 1, 15)
        with pytest.raises(ValueError, match="Entry date cannot be after current date"):
            FXCarryPosition(**valid_position_data)

    def test_position_same_dates(self, valid_position_data: dict) -> None:
        """Test position with same entry and current date."""
        valid_position_data["entry_date"] = date(2024, 1, 15)
        valid_position_data["current_date"] = date(2024, 1, 15)
        position = FXCarryPosition(**valid_position_data)
        assert position.days_held == 0

    def test_position_is_long(self, valid_position_data: dict) -> None:
        """Test is_long property."""
        valid_position_data["quantity"] = Decimal("100000")
        position = FXCarryPosition(**valid_position_data)
        assert position.is_long is True
        assert position.is_short is False

    def test_position_is_short(self, valid_position_data: dict) -> None:
        """Test is_short property."""
        valid_position_data["quantity"] = Decimal("-100000")
        position = FXCarryPosition(**valid_position_data)
        assert position.is_short is True
        assert position.is_long is False

    def test_position_neutral_quantity(self, valid_position_data: dict) -> None:
        """Test position with zero quantity."""
        valid_position_data["quantity"] = Decimal("0")
        position = FXCarryPosition(**valid_position_data)
        assert position.is_long is False
        assert position.is_short is False

    def test_unrealized_pnl_long_position(self, valid_position_data: dict) -> None:
        """Test unrealized P&L calculation for long position."""
        # (111.00 - 110.50) * 100000 = 0.50 * 100000 = 50000
        position = FXCarryPosition(**valid_position_data)
        assert position.unrealized_pnl == Decimal("50000")

    def test_unrealized_pnl_short_position(self, valid_position_data: dict) -> None:
        """Test unrealized P&L calculation for short position."""
        valid_position_data["quantity"] = Decimal("-100000")
        valid_position_data["current_price"] = Decimal("109.50")
        # (109.50 - 110.50) * -100000 = -1.00 * -100000 = 100000
        position = FXCarryPosition(**valid_position_data)
        assert position.unrealized_pnl == Decimal("100000")

    def test_unrealized_pnl_loss_long(self, valid_position_data: dict) -> None:
        """Test unrealized P&L with loss on long position."""
        valid_position_data["current_price"] = Decimal("109.50")
        # (109.50 - 110.50) * 100000 = -1.00 * 100000 = -100000
        position = FXCarryPosition(**valid_position_data)
        assert position.unrealized_pnl == Decimal("-100000")

    def test_days_held(self, valid_position_data: dict) -> None:
        """Test days_held calculation."""
        position = FXCarryPosition(**valid_position_data)
        # Jan 10 to Jan 15 = 5 days
        assert position.days_held == 5

    def test_days_held_longer_period(self, valid_position_data: dict) -> None:
        """Test days_held for longer holding period."""
        valid_position_data["entry_date"] = date(2023, 12, 1)
        valid_position_data["current_date"] = date(2024, 1, 15)
        position = FXCarryPosition(**valid_position_data)
        # Dec 1 to Jan 15 = 45 days
        assert position.days_held == 45

    def test_unrealized_pnl_fractional_prices(self, valid_position_data: dict) -> None:
        """Test unrealized P&L with fractional price changes."""
        valid_position_data["entry_price"] = Decimal("1.1050")
        valid_position_data["current_price"] = Decimal("1.1075")
        valid_position_data["quantity"] = Decimal("1000000")
        # (1.1075 - 1.1050) * 1000000 = 0.0025 * 1000000 = 2500
        position = FXCarryPosition(**valid_position_data)
        assert position.unrealized_pnl == Decimal("2500")


class TestFXRateQuote:
    """Tests for FXRateQuote dataclass."""

    @pytest.fixture
    def valid_quote_data(self) -> dict:
        """Provide valid quote data for testing."""
        return {
            "pair": FXPair(base_currency="USD", quote_currency="JPY"),
            "spot_rate": Decimal("110.50"),
            "forward_1m": Decimal("110.35"),
            "forward_3m": Decimal("110.10"),
            "forward_6m": Decimal("109.80"),
            "forward_12m": Decimal("109.20"),
            "timestamp": date(2024, 1, 15),
        }

    def test_quote_creation_all_forwards(self, valid_quote_data: dict) -> None:
        """Test creating quote with all forward rates."""
        quote = FXRateQuote(**valid_quote_data)

        assert quote.pair == valid_quote_data["pair"]
        assert quote.spot_rate == Decimal("110.50")
        assert quote.forward_1m == Decimal("110.35")
        assert quote.forward_3m == Decimal("110.10")
        assert quote.forward_6m == Decimal("109.80")
        assert quote.forward_12m == Decimal("109.20")
        assert quote.timestamp == date(2024, 1, 15)

    def test_quote_creation_spot_only(self) -> None:
        """Test creating quote with only spot rate."""
        quote = FXRateQuote(
            pair=FXPair(base_currency="EUR", quote_currency="USD"),
            spot_rate=Decimal("1.0850"),
        )

        assert quote.spot_rate == Decimal("1.0850")
        assert quote.forward_1m is None
        assert quote.forward_3m is None
        assert quote.forward_6m is None
        assert quote.forward_12m is None
        assert quote.timestamp is None

    def test_get_forward_rate_1m(self, valid_quote_data: dict) -> None:
        """Test getting 1-month forward rate."""
        quote = FXRateQuote(**valid_quote_data)
        assert quote.get_forward_rate(1) == Decimal("110.35")

    def test_get_forward_rate_3m(self, valid_quote_data: dict) -> None:
        """Test getting 3-month forward rate."""
        quote = FXRateQuote(**valid_quote_data)
        assert quote.get_forward_rate(3) == Decimal("110.10")

    def test_get_forward_rate_6m(self, valid_quote_data: dict) -> None:
        """Test getting 6-month forward rate."""
        quote = FXRateQuote(**valid_quote_data)
        assert quote.get_forward_rate(6) == Decimal("109.80")

    def test_get_forward_rate_12m(self, valid_quote_data: dict) -> None:
        """Test getting 12-month forward rate."""
        quote = FXRateQuote(**valid_quote_data)
        assert quote.get_forward_rate(12) == Decimal("109.20")

    def test_get_forward_rate_none(self) -> None:
        """Test getting non-existent forward rate."""
        quote = FXRateQuote(
            pair=FXPair(base_currency="EUR", quote_currency="USD"),
            spot_rate=Decimal("1.0850"),
        )
        assert quote.get_forward_rate(3) is None

    def test_get_forward_rate_invalid_period(self, valid_quote_data: dict) -> None:
        """Test getting forward rate with invalid period."""
        quote = FXRateQuote(**valid_quote_data)

        with pytest.raises(ValueError, match="Invalid forward period"):
            quote.get_forward_rate(2)

        with pytest.raises(ValueError, match="Invalid forward period"):
            quote.get_forward_rate(0)

        with pytest.raises(ValueError, match="Invalid forward period"):
            quote.get_forward_rate(24)


class TestInterestRateQuote:
    """Tests for InterestRateQuote dataclass."""

    @pytest.fixture
    def valid_rate_data(self) -> dict:
        """Provide valid rate data for testing."""
        return {
            "currency": "USD",
            "rate_1m": Decimal("0.0525"),
            "rate_3m": Decimal("0.0530"),
            "rate_6m": Decimal("0.0540"),
            "rate_12m": Decimal("0.0550"),
            "timestamp": date(2024, 1, 15),
        }

    def test_rate_quote_all_periods(self, valid_rate_data: dict) -> None:
        """Test creating quote with all rate periods."""
        quote = InterestRateQuote(**valid_rate_data)

        assert quote.currency == "USD"
        assert quote.rate_1m == Decimal("0.0525")
        assert quote.rate_3m == Decimal("0.0530")
        assert quote.rate_6m == Decimal("0.0540")
        assert quote.rate_12m == Decimal("0.0550")
        assert quote.timestamp == date(2024, 1, 15)

    def test_rate_quote_single_period(self) -> None:
        """Test creating quote with single rate period."""
        quote = InterestRateQuote(
            currency="EUR",
            rate_3m=Decimal("0.0450"),
        )

        assert quote.currency == "EUR"
        assert quote.rate_3m == Decimal("0.0450")
        assert quote.rate_1m is None
        assert quote.rate_6m is None
        assert quote.rate_12m is None

    def test_get_rate_1m(self, valid_rate_data: dict) -> None:
        """Test getting 1-month interest rate."""
        quote = InterestRateQuote(**valid_rate_data)
        assert quote.get_rate(1) == Decimal("0.0525")

    def test_get_rate_3m(self, valid_rate_data: dict) -> None:
        """Test getting 3-month interest rate."""
        quote = InterestRateQuote(**valid_rate_data)
        assert quote.get_rate(3) == Decimal("0.0530")

    def test_get_rate_6m(self, valid_rate_data: dict) -> None:
        """Test getting 6-month interest rate."""
        quote = InterestRateQuote(**valid_rate_data)
        assert quote.get_rate(6) == Decimal("0.0540")

    def test_get_rate_12m(self, valid_rate_data: dict) -> None:
        """Test getting 12-month interest rate."""
        quote = InterestRateQuote(**valid_rate_data)
        assert quote.get_rate(12) == Decimal("0.0550")

    def test_get_rate_none(self) -> None:
        """Test getting non-existent rate."""
        quote = InterestRateQuote(currency="JPY", rate_1m=Decimal("0.001"))
        assert quote.get_rate(3) is None

    def test_get_rate_invalid_period(self, valid_rate_data: dict) -> None:
        """Test getting rate with invalid period."""
        quote = InterestRateQuote(**valid_rate_data)

        with pytest.raises(ValueError, match="Invalid period"):
            quote.get_rate(2)

        with pytest.raises(ValueError, match="Invalid period"):
            quote.get_rate(24)


class TestFXCarryTradeConfig:
    """Tests for FXCarryTradeConfig dataclass."""

    def test_default_config(self) -> None:
        """Test creating config with default values."""
        config = FXCarryTradeConfig()

        assert config.min_carry_threshold == Decimal("0.01")
        assert config.max_positions == 10
        assert config.position_size == Decimal("0.1")
        assert config.forward_months == 3
        assert config.stop_loss == Decimal("0.05")
        assert config.take_profit == Decimal("0.15")
        assert config.max_leverage == Decimal("2.0")
        assert config.min_liquidity == Decimal("1000000")

    def test_custom_config(self) -> None:
        """Test creating config with custom values."""
        config = FXCarryTradeConfig(
            min_carry_threshold=Decimal("0.02"),
            max_positions=5,
            position_size=Decimal("0.2"),
            forward_months=6,
            stop_loss=Decimal("0.03"),
            take_profit=Decimal("0.10"),
            max_leverage=Decimal("3.0"),
            min_liquidity=Decimal("5000000"),
        )

        assert config.min_carry_threshold == Decimal("0.02")
        assert config.max_positions == 5
        assert config.position_size == Decimal("0.2")
        assert config.forward_months == 6
        assert config.stop_loss == Decimal("0.03")
        assert config.take_profit == Decimal("0.10")
        assert config.max_leverage == Decimal("3.0")
        assert config.min_liquidity == Decimal("5000000")

    def test_config_invalid_negative_carry_threshold(self) -> None:
        """Test validation rejects negative carry threshold."""
        with pytest.raises(ValueError, match="min_carry_threshold must be non-negative"):
            FXCarryTradeConfig(min_carry_threshold=Decimal("-0.01"))

    def test_config_invalid_zero_max_positions(self) -> None:
        """Test validation rejects zero max positions."""
        with pytest.raises(ValueError, match="max_positions must be positive"):
            FXCarryTradeConfig(max_positions=0)

    def test_config_invalid_negative_max_positions(self) -> None:
        """Test validation rejects negative max positions."""
        with pytest.raises(ValueError, match="max_positions must be positive"):
            FXCarryTradeConfig(max_positions=-5)

    def test_config_invalid_position_size_zero(self) -> None:
        """Test validation rejects zero position size."""
        with pytest.raises(ValueError, match="position_size must be between 0 and 1"):
            FXCarryTradeConfig(position_size=Decimal("0"))

    def test_config_invalid_position_size_negative(self) -> None:
        """Test validation rejects negative position size."""
        with pytest.raises(ValueError, match="position_size must be between 0 and 1"):
            FXCarryTradeConfig(position_size=Decimal("-0.1"))

    def test_config_invalid_position_size_gt_one(self) -> None:
        """Test validation rejects position size greater than 1."""
        with pytest.raises(ValueError, match="position_size must be between 0 and 1"):
            FXCarryTradeConfig(position_size=Decimal("1.5"))

    def test_config_invalid_position_size_one(self) -> None:
        """Test validation accepts position size equal to 1."""
        # The validation allows position_size up to and including 1
        config = FXCarryTradeConfig(position_size=Decimal("1"))
        assert config.position_size == Decimal("1")

    def test_config_invalid_forward_months(self) -> None:
        """Test validation rejects invalid forward months."""
        with pytest.raises(ValueError, match="forward_months must be 1, 3, 6, or 12"):
            FXCarryTradeConfig(forward_months=2)

        with pytest.raises(ValueError, match="forward_months must be 1, 3, 6, or 12"):
            FXCarryTradeConfig(forward_months=0)

        with pytest.raises(ValueError, match="forward_months must be 1, 3, 6, or 12"):
            FXCarryTradeConfig(forward_months=24)

    def test_config_valid_forward_months(self) -> None:
        """Test all valid forward months values."""
        for months in [1, 3, 6, 12]:
            config = FXCarryTradeConfig(forward_months=months)
            assert config.forward_months == months

    def test_config_invalid_stop_loss_zero(self) -> None:
        """Test validation rejects zero stop loss."""
        with pytest.raises(ValueError, match="stop_loss must be between 0 and 1"):
            FXCarryTradeConfig(stop_loss=Decimal("0"))

    def test_config_invalid_stop_loss_negative(self) -> None:
        """Test validation rejects negative stop loss."""
        with pytest.raises(ValueError, match="stop_loss must be between 0 and 1"):
            FXCarryTradeConfig(stop_loss=Decimal("-0.05"))

    def test_config_invalid_stop_loss_one(self) -> None:
        """Test validation rejects stop loss equal to 1."""
        with pytest.raises(ValueError, match="stop_loss must be between 0 and 1"):
            FXCarryTradeConfig(stop_loss=Decimal("1"))

    def test_config_invalid_take_profit_zero(self) -> None:
        """Test validation rejects zero take profit."""
        with pytest.raises(ValueError, match="take_profit must be between 0 and 1"):
            FXCarryTradeConfig(take_profit=Decimal("0"))

    def test_config_invalid_take_profit_one(self) -> None:
        """Test validation rejects take profit equal to 1."""
        with pytest.raises(ValueError, match="take_profit must be between 0 and 1"):
            FXCarryTradeConfig(take_profit=Decimal("1"))

    def test_config_invalid_max_leverage(self) -> None:
        """Test validation rejects max leverage less than 1."""
        with pytest.raises(ValueError, match="max_leverage must be at least 1"):
            FXCarryTradeConfig(max_leverage=Decimal("0.5"))

    def test_config_max_leverage_one(self) -> None:
        """Test max leverage equal to 1 is valid."""
        config = FXCarryTradeConfig(max_leverage=Decimal("1"))
        assert config.max_leverage == Decimal("1")

    def test_config_invalid_min_liquidity(self) -> None:
        """Test validation rejects negative min liquidity."""
        with pytest.raises(ValueError, match="min_liquidity must be non-negative"):
            FXCarryTradeConfig(min_liquidity=Decimal("-1000000"))

    def test_config_zero_min_liquidity(self) -> None:
        """Test zero min liquidity is valid."""
        config = FXCarryTradeConfig(min_liquidity=Decimal("0"))
        assert config.min_liquidity == Decimal("0")

    def test_config_mutability(self) -> None:
        """Test that config is mutable (non-frozen dataclass)."""
        config = FXCarryTradeConfig()
        config.min_carry_threshold = Decimal("0.02")  # type: ignore
        assert config.min_carry_threshold == Decimal("0.02")
