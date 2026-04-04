"""
Tests for FX Carry Trade Calculator.

This module tests the carry trade signal calculation based on Ilmanen's
methodology from "Expected Returns" - Rule 12.9.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.strategies.fx_carry_trade.carry_calculator import (
    CarryCalculator,
    CarryTradeOpportunity,
)
from app.domain.strategies.fx_carry_trade.models import FXCarrySignal, FXPair


class TestCarryCalculator:
    """Tests for CarryCalculator class."""

    def test_calculator_initialization_default(self) -> None:
        """Test calculator initialization with default parameters."""
        calculator = CarryCalculator()

        assert calculator.signal_threshold == Decimal("0.01")
        assert calculator.signal_multiplier == 10.0

    def test_calculator_initialization_custom(self) -> None:
        """Test calculator initialization with custom parameters."""
        calculator = CarryCalculator(
            signal_threshold=Decimal("0.02"),
            signal_multiplier=5.0,
        )

        assert calculator.signal_threshold == Decimal("0.02")
        assert calculator.signal_multiplier == 5.0

    def test_calculator_invalid_negative_threshold(self) -> None:
        """Test validation rejects negative signal threshold."""
        with pytest.raises(ValueError, match="signal_threshold must be non-negative"):
            CarryCalculator(signal_threshold=Decimal("-0.01"))

    def test_calculator_invalid_zero_multiplier(self) -> None:
        """Test validation rejects zero signal multiplier."""
        with pytest.raises(ValueError, match="signal_multiplier must be positive"):
            CarryCalculator(signal_multiplier=0.0)

    def test_calculator_invalid_negative_multiplier(self) -> None:
        """Test validation rejects negative signal multiplier."""
        with pytest.raises(ValueError, match="signal_multiplier must be positive"):
            CarryCalculator(signal_multiplier=-5.0)


class TestCarryCalculatorForwardPremium:
    """Tests for forward premium calculation."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator()

    def test_calculate_forward_premium_basic(self, calculator: CarryCalculator) -> None:
        """Test basic forward premium calculation."""
        spot = Decimal("110.50")
        forward = Decimal("110.20")
        # (110.20 - 110.50) / 110.50 = -0.30 / 110.50 = -0.0027149...
        premium = calculator.calculate_forward_premium(spot, forward)

        # Just check the value is negative and in reasonable range
        assert premium < 0
        assert abs(float(premium)) < 0.01

    def test_calculate_forward_premium_positive(self, calculator: CarryCalculator) -> None:
        """Test forward premium with forward higher than spot."""
        spot = Decimal("1.0850")
        forward = Decimal("1.0900")
        # (1.0900 - 1.0850) / 1.0850 = 0.0050 / 1.0850 = 0.004608...
        premium = calculator.calculate_forward_premium(spot, forward)

        assert premium > 0
        assert abs(float(premium - Decimal("0.004608"))) < 0.0001

    def test_calculate_forward_premium_equal_rates(self, calculator: CarryCalculator) -> None:
        """Test forward premium when spot equals forward."""
        spot = Decimal("110.00")
        forward = Decimal("110.00")
        premium = calculator.calculate_forward_premium(spot, forward)

        assert premium == Decimal("0")

    def test_calculate_forward_premium_invalid_spot(self, calculator: CarryCalculator) -> None:
        """Test validation rejects non-positive spot rate."""
        with pytest.raises(ValueError, match="spot_rate must be positive"):
            calculator.calculate_forward_premium(Decimal("0"), Decimal("110"))

        with pytest.raises(ValueError, match="spot_rate must be positive"):
            calculator.calculate_forward_premium(Decimal("-110.50"), Decimal("110"))

    def test_calculate_forward_premium_invalid_forward(self, calculator: CarryCalculator) -> None:
        """Test validation rejects non-positive forward rate."""
        with pytest.raises(ValueError, match="forward_rate must be positive"):
            calculator.calculate_forward_premium(Decimal("110.50"), Decimal("0"))

        with pytest.raises(ValueError, match="forward_rate must be positive"):
            calculator.calculate_forward_premium(Decimal("110.50"), Decimal("-110"))


class TestCarryCalculatorCarry:
    """Tests for carry calculation."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator()

    def test_calculate_carry_basic(self, calculator: CarryCalculator) -> None:
        """Test basic carry calculation."""
        rate_diff = Decimal("0.025")  # 2.5% interest rate differential
        forward_premium = Decimal("-0.003")
        # carry = 0.025 - (-0.003) = 0.028
        carry = calculator.calculate_carry(rate_diff, forward_premium)

        assert carry == Decimal("0.028")

    def test_calculate_carry_positive_differential(self, calculator: CarryCalculator) -> None:
        """Test carry with positive interest rate differential."""
        rate_diff = Decimal("0.05")
        forward_premium = Decimal("0.01")
        carry = calculator.calculate_carry(rate_diff, forward_premium)

        assert carry == Decimal("0.04")

    def test_calculate_carry_negative_differential(self, calculator: CarryCalculator) -> None:
        """Test carry with negative interest rate differential."""
        rate_diff = Decimal("-0.02")
        forward_premium = Decimal("0.005")
        carry = calculator.calculate_carry(rate_diff, forward_premium)

        assert carry == Decimal("-0.025")

    def test_calculate_carry_zero_differential(self, calculator: CarryCalculator) -> None:
        """Test carry with zero interest rate differential."""
        rate_diff = Decimal("0")
        forward_premium = Decimal("0.01")
        carry = calculator.calculate_carry(rate_diff, forward_premium)

        assert carry == Decimal("-0.01")

    def test_calculate_carry_negative_premium(self, calculator: CarryCalculator) -> None:
        """Test carry with negative forward premium."""
        rate_diff = Decimal("0.03")
        forward_premium = Decimal("-0.01")
        carry = calculator.calculate_carry(rate_diff, forward_premium)

        assert carry == Decimal("0.04")


class TestCarryCalculatorSignal:
    """Tests for signal calculation."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator(signal_threshold=Decimal("0.01"), signal_multiplier=10.0)

    def test_calculate_signal_above_threshold(self, calculator: CarryCalculator) -> None:
        """Test signal generation with carry above threshold."""
        carry = Decimal("0.02")
        signal = calculator.calculate_signal(carry)

        assert signal > 0
        assert signal <= 1.0

    def test_calculate_signal_below_threshold(self, calculator: CarryCalculator) -> None:
        """Test signal generation with carry below threshold."""
        carry = Decimal("0.005")
        signal = calculator.calculate_signal(carry)

        assert signal == 0.0

    def test_calculate_signal_negative_carry(self, calculator: CarryCalculator) -> None:
        """Test signal generation with negative carry."""
        carry = Decimal("-0.02")
        signal = calculator.calculate_signal(carry)

        assert signal < 0
        assert signal >= -1.0

    def test_calculate_signal_at_threshold(self, calculator: CarryCalculator) -> None:
        """Test signal generation at exactly threshold."""
        carry = Decimal("0.01")
        signal = calculator.calculate_signal(carry)

        # At threshold, should generate no signal
        assert signal == 0.0

    def test_calculate_signal_negative_at_threshold(self, calculator: CarryCalculator) -> None:
        """Test signal generation at negative threshold."""
        carry = Decimal("-0.01")
        signal = calculator.calculate_signal(carry)

        # At threshold, should generate no signal
        assert signal == 0.0

    def test_calculate_signal_very_large_carry(self, calculator: CarryCalculator) -> None:
        """Test signal with very large carry value."""
        carry = Decimal("0.10")
        signal = calculator.calculate_signal(carry)

        # Should be close to 1.0 due to tanh saturation
        # tanh(0.10 * 10) = tanh(1.0) = 0.761594...
        assert signal > 0.7
        assert signal <= 1.0

    def test_calculate_signal_very_negative_carry(self, calculator: CarryCalculator) -> None:
        """Test signal with very negative carry value."""
        carry = Decimal("-0.10")
        signal = calculator.calculate_signal(carry)

        # Should be close to -1.0 due to tanh saturation
        # tanh(-0.10 * 10) = tanh(-1.0) = -0.761594...
        assert signal < -0.7
        assert signal >= -1.0

    def test_calculate_signal_custom_multiplier(self) -> None:
        """Test signal with custom multiplier."""
        calculator = CarryCalculator(signal_multiplier=5.0)
        carry = Decimal("0.05")
        signal = calculator.calculate_signal(carry)

        # Lower multiplier should give less aggressive signal
        assert 0 < signal < 1.0

    def test_calculate_signal_zero_carry(self, calculator: CarryCalculator) -> None:
        """Test signal with zero carry."""
        carry = Decimal("0")
        signal = calculator.calculate_signal(carry)

        assert signal == 0.0


class TestCarryCalculatorSignalFull:
    """Tests for full signal calculation."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator()

    @pytest.fixture
    def valid_signal_params(self) -> dict:
        """Provide valid parameters for signal calculation."""
        return {
            "pair": FXPair(base_currency="USD", quote_currency="JPY"),
            "spot_rate": Decimal("110.50"),
            "forward_rate": Decimal("110.20"),
            "interest_rate_diff": Decimal("0.025"),
            "timestamp": date(2024, 1, 15),
            "months": 3,
        }

    def test_calculate_signal_full_basic(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test full signal calculation."""
        signal = calculator.calculate_signal_full(**valid_signal_params)

        assert isinstance(signal, FXCarrySignal)
        assert signal.pair == valid_signal_params["pair"]
        assert signal.spot_rate == valid_signal_params["spot_rate"]
        assert signal.forward_rate == valid_signal_params["forward_rate"]
        assert signal.interest_rate_diff == valid_signal_params["interest_rate_diff"]
        assert signal.timestamp == valid_signal_params["timestamp"]
        assert signal.months == 3

    def test_calculate_signal_full_forward_premium_calculated(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test that forward premium is calculated correctly."""
        signal = calculator.calculate_signal_full(**valid_signal_params)

        expected_premium = calculator.calculate_forward_premium(
            valid_signal_params["spot_rate"],
            valid_signal_params["forward_rate"],
        )
        assert signal.forward_premium == expected_premium

    def test_calculate_signal_full_carry_calculated(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test that carry is calculated correctly."""
        signal = calculator.calculate_signal_full(**valid_signal_params)

        expected_carry = calculator.calculate_carry(
            valid_signal_params["interest_rate_diff"],
            signal.forward_premium,
        )
        assert signal.carry == expected_carry

    def test_calculate_signal_full_signal_in_range(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test that signal value is in valid range."""
        signal = calculator.calculate_signal_full(**valid_signal_params)

        assert Decimal("-1") <= signal.signal <= Decimal("1")

    def test_calculate_signal_full_invalid_spot(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test validation rejects non-positive spot rate."""
        valid_signal_params["spot_rate"] = Decimal("0")
        with pytest.raises(ValueError, match="spot_rate must be positive"):
            calculator.calculate_signal_full(**valid_signal_params)

    def test_calculate_signal_full_invalid_forward(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test validation rejects non-positive forward rate."""
        valid_signal_params["forward_rate"] = Decimal("0")
        with pytest.raises(ValueError, match="forward_rate must be positive"):
            calculator.calculate_signal_full(**valid_signal_params)

    def test_calculate_signal_full_invalid_months(
        self, calculator: CarryCalculator, valid_signal_params: dict
    ) -> None:
        """Test validation rejects invalid months."""
        valid_signal_params["months"] = 2
        with pytest.raises(ValueError, match="months must be 1, 3, 6, or 12"):
            calculator.calculate_signal_full(**valid_signal_params)

    def test_calculate_signal_full_valid_months(self, calculator: CarryCalculator) -> None:
        """Test all valid month values."""
        params = {
            "pair": FXPair(base_currency="EUR", quote_currency="USD"),
            "spot_rate": Decimal("1.0850"),
            "forward_rate": Decimal("1.0900"),
            "interest_rate_diff": Decimal("0.01"),
            "timestamp": date(2024, 1, 15),
        }

        for months in [1, 3, 6, 12]:
            signal = calculator.calculate_signal_full(**params, months=months)
            assert signal.months == months


class TestCarryCalculatorFilterRank:
    """Tests for signal filtering and ranking."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator()

    @pytest.fixture
    def sample_signals(self) -> dict[FXPair, FXCarrySignal]:
        """Provide sample signals for testing."""
        usdjpy = FXPair(base_currency="USD", quote_currency="JPY")
        eurusd = FXPair(base_currency="EUR", quote_currency="USD")
        gbpusd = FXPair(base_currency="GBP", quote_currency="USD")

        return {
            usdjpy: FXCarrySignal(
                pair=usdjpy,
                spot_rate=Decimal("110.50"),
                forward_rate=Decimal("110.20"),
                interest_rate_diff=Decimal("0.025"),
                forward_premium=Decimal("-0.003"),
                carry=Decimal("0.028"),
                signal=Decimal("0.8"),
                timestamp=date(2024, 1, 15),
            ),
            eurusd: FXCarrySignal(
                pair=eurusd,
                spot_rate=Decimal("1.0850"),
                forward_rate=Decimal("1.0900"),
                interest_rate_diff=Decimal("0.01"),
                forward_premium=Decimal("0.005"),
                carry=Decimal("0.005"),
                signal=Decimal("0.2"),
                timestamp=date(2024, 1, 15),
            ),
            gbpusd: FXCarrySignal(
                pair=gbpusd,
                spot_rate=Decimal("1.2700"),
                forward_rate=Decimal("1.2650"),
                interest_rate_diff=Decimal("-0.01"),
                forward_premium=Decimal("-0.004"),
                carry=Decimal("-0.006"),
                signal=Decimal("-0.3"),
                timestamp=date(2024, 1, 15),
            ),
        }

    def test_filter_signals_none_filtered(
        self, calculator: CarryCalculator, sample_signals: dict
    ) -> None:
        """Test filtering with minimum threshold that keeps all signals."""
        filtered = calculator.filter_signals(sample_signals, Decimal("0.1"))

        assert len(filtered) == 3

    def test_filter_signals_some_filtered(
        self, calculator: CarryCalculator, sample_signals: dict
    ) -> None:
        """Test filtering that removes some signals."""
        filtered = calculator.filter_signals(sample_signals, Decimal("0.3"))

        # Should only keep USD/JPY (0.8) and GBP/USD (-0.3)
        assert len(filtered) == 2
        assert abs(float(filtered[FXPair("USD", "JPY")].signal)) >= 0.3
        assert abs(float(filtered[FXPair("GBP", "USD")].signal)) >= 0.3

    def test_filter_signals_all_filtered(
        self, calculator: CarryCalculator, sample_signals: dict
    ) -> None:
        """Test filtering that removes all signals."""
        filtered = calculator.filter_signals(sample_signals, Decimal("0.9"))

        assert len(filtered) == 0

    def test_rank_signals_basic(self, calculator: CarryCalculator, sample_signals: dict) -> None:
        """Test basic signal ranking."""
        ranked = calculator.rank_signals(sample_signals)

        assert len(ranked) == 3
        # Should be sorted by absolute signal descending
        assert abs(float(ranked[0][1].signal)) >= abs(float(ranked[1][1].signal))
        assert abs(float(ranked[1][1].signal)) >= abs(float(ranked[2][1].signal))

    def test_rank_signals_order(self, calculator: CarryCalculator, sample_signals: dict) -> None:
        """Test that ranking produces correct order."""
        ranked = calculator.rank_signals(sample_signals)

        # First should be USD/JPY with signal 0.8
        assert ranked[0][0] == FXPair("USD", "JPY")
        assert ranked[0][1].signal == Decimal("0.8")

        # Last should be EUR/USD with signal 0.2
        assert ranked[2][0] == FXPair("EUR", "USD")
        assert ranked[2][1].signal == Decimal("0.2")

    def test_rank_signals_empty(self, calculator: CarryCalculator) -> None:
        """Test ranking with no signals."""
        ranked = calculator.rank_signals({})

        assert ranked == []


class TestCarryCalculatorProvider:
    """Tests for provider-based signal calculation."""

    @pytest.fixture
    def calculator(self) -> CarryCalculator:
        """Provide a calculator instance for testing."""
        return CarryCalculator()

    @pytest.fixture
    def mock_provider(self) -> type:
        """Create a mock FX rate provider for testing."""
        from typing import Protocol, runtime_checkable

        @runtime_checkable
        class MockProvider(Protocol):
            def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal: ...

            def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal: ...

            def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal: ...

        class ConcreteMockProvider:
            def __init__(self) -> None:
                self._spots = {
                    (FXPair("USD", "JPY"), date(2024, 1, 15)): Decimal("110.50"),
                    (FXPair("EUR", "USD"), date(2024, 1, 15)): Decimal("1.0850"),
                }
                self._forwards = {
                    (FXPair("USD", "JPY"), date(2024, 1, 15), 3): Decimal("110.20"),
                    (FXPair("EUR", "USD"), date(2024, 1, 15), 3): Decimal("1.0900"),
                }
                self._rates = {
                    ("USD", date(2024, 1, 15), 3): Decimal("0.0525"),
                    ("JPY", date(2024, 1, 15), 3): Decimal("0.0000"),
                    ("EUR", date(2024, 1, 15), 3): Decimal("0.0450"),
                }

            def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
                return self._spots[(pair, as_of)]

            def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
                return self._forwards[(pair, as_of, months)]

            def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
                return self._rates[(currency, as_of, months)]

        return ConcreteMockProvider

    def test_calculate_signals_from_provider_single(
        self, calculator: CarryCalculator, mock_provider: type
    ) -> None:
        """Test calculating signal for a single pair using provider."""
        provider = mock_provider()
        pairs = [FXPair("USD", "JPY")]
        as_of = date(2024, 1, 15)

        signals = calculator.calculate_signals_from_provider(pairs, provider, as_of, 3)

        assert len(signals) == 1
        assert FXPair("USD", "JPY") in signals
        assert isinstance(signals[FXPair("USD", "JPY")], FXCarrySignal)

    def test_calculate_signals_from_provider_multiple(
        self, calculator: CarryCalculator, mock_provider: type
    ) -> None:
        """Test calculating signals for multiple pairs using provider."""
        provider = mock_provider()
        pairs = [FXPair("USD", "JPY"), FXPair("EUR", "USD")]
        as_of = date(2024, 1, 15)

        signals = calculator.calculate_signals_from_provider(pairs, provider, as_of, 3)

        assert len(signals) == 2

    def test_calculate_signals_from_provider_missing_data(
        self, calculator: CarryCalculator, mock_provider: type
    ) -> None:
        """Test handling of missing data from provider."""
        provider = mock_provider()
        # The mock provider only has data for USD/JPY and EUR/USD
        pairs = [FXPair("USD", "JPY"), FXPair("EUR", "USD")]
        as_of = date(2024, 1, 15)

        signals = calculator.calculate_signals_from_provider(pairs, provider, as_of, 3)

        # Should return signals for available pairs
        assert len(signals) == 2
        assert FXPair("USD", "JPY") in signals
        assert FXPair("EUR", "USD") in signals

    def test_calculate_signals_from_provider_empty_list(
        self, calculator: CarryCalculator, mock_provider: type
    ) -> None:
        """Test calculating signals with empty pair list."""
        provider = mock_provider()
        signals = calculator.calculate_signals_from_provider([], provider, date(2024, 1, 15))

        assert len(signals) == 0


class TestCarryTradeOpportunity:
    """Tests for CarryTradeOpportunity dataclass."""

    def test_opportunity_creation(self) -> None:
        """Test creating a carry trade opportunity."""
        opportunity = CarryTradeOpportunity(
            pair=FXPair("USD", "JPY"),
            expected_carry=Decimal("0.028"),
            forward_premium=Decimal("-0.003"),
            signal=Decimal("0.8"),
            confidence=75.0,
        )

        assert opportunity.pair == FXPair("USD", "JPY")
        assert opportunity.expected_carry == Decimal("0.028")
        assert opportunity.forward_premium == Decimal("-0.003")
        assert opportunity.signal == Decimal("0.8")
        assert opportunity.confidence == 75.0

    def test_opportunity_is_actionable_true(self) -> None:
        """Test is_actionable when confidence > 60."""
        opportunity = CarryTradeOpportunity(
            pair=FXPair("EUR", "USD"),
            expected_carry=Decimal("0.02"),
            forward_premium=Decimal("0.005"),
            signal=Decimal("0.6"),
            confidence=75.0,
        )

        assert opportunity.is_actionable is True

    def test_opportunity_is_actionable_false(self) -> None:
        """Test is_actionable when confidence <= 60."""
        opportunity = CarryTradeOpportunity(
            pair=FXPair("GBP", "USD"),
            expected_carry=Decimal("0.01"),
            forward_premium=Decimal("0.002"),
            signal=Decimal("0.3"),
            confidence=50.0,
        )

        assert opportunity.is_actionable is False

    def test_opportunity_is_actionable_boundary(self) -> None:
        """Test is_actionable at boundary value."""
        # At exactly 60, should not be actionable
        opportunity = CarryTradeOpportunity(
            pair=FXPair("AUD", "USD"),
            expected_carry=Decimal("0.015"),
            forward_premium=Decimal("0.003"),
            signal=Decimal("0.5"),
            confidence=60.0,
        )

        assert opportunity.is_actionable is False

    def test_opportunity_is_actionable_just_above(self) -> None:
        """Test is_actionable just above boundary."""
        opportunity = CarryTradeOpportunity(
            pair=FXPair("NZD", "USD"),
            expected_carry=Decimal("0.02"),
            forward_premium=Decimal("0.004"),
            signal=Decimal("0.55"),
            confidence=60.1,
        )

        assert opportunity.is_actionable is True

    def test_opportunity_negative_carry(self) -> None:
        """Test opportunity with negative carry."""
        opportunity = CarryTradeOpportunity(
            pair=FXPair("CHF", "JPY"),
            expected_carry=Decimal("-0.01"),
            forward_premium=Decimal("0.005"),
            signal=Decimal("-0.5"),
            confidence=40.0,
        )

        assert opportunity.expected_carry < 0
        assert opportunity.signal < 0
        assert opportunity.is_actionable is False
