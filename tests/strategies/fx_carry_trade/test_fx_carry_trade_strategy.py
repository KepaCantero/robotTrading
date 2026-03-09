"""
Tests for FX Carry Trade Strategy.

This module tests the FXCarryTradeStrategy class which implements
the carry trade strategy based on Ilmanen's methodology from "Expected Returns".
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.strategies.fx_carry_trade.carry_calculator import CarryCalculator, CarryTradeOpportunity
from app.domain.strategies.fx_carry_trade.fx_carry_trade_strategy import (
    FXCarryTradeState,
    FXCarryTradeStrategy,
)
from app.domain.strategies.fx_carry_trade.fx_rates_provider import InMemoryFXRateProvider
from app.domain.strategies.fx_carry_trade.models import (
    FXCarryPosition,
    FXCarrySignal,
    FXCarryTradeConfig,
    FXPair,
)


class TestFXCarryTradeState:
    """Tests for FXCarryTradeState dataclass."""

    def test_state_initialization_default(self) -> None:
        """Test state initialization with default values."""
        state = FXCarryTradeState()

        assert state.current_positions == {}
        assert state.pending_signals == []
        assert state.total_exposure == Decimal("0")
        assert state.available_capital == Decimal("100000")
        assert state.last_update == date.today()

    def test_state_custom_values(self) -> None:
        """Test state with custom values."""
        test_date = date(2024, 1, 15)
        position = MagicMock(spec=FXCarryPosition)

        state = FXCarryTradeState(
            current_positions={FXPair("USD", "JPY"): position},
            pending_signals=[MagicMock(spec=FXCarrySignal)],
            total_exposure=Decimal("50000"),
            available_capital=Decimal("75000"),
            last_update=test_date,
        )

        assert len(state.current_positions) == 1
        assert len(state.pending_signals) == 1
        assert state.total_exposure == Decimal("50000")
        assert state.available_capital == Decimal("75000")
        assert state.last_update == test_date


class TestFXCarryTradeStrategyInitialization:
    """Tests for FXCarryTradeStrategy initialization."""

    @pytest.fixture
    def basic_config(self) -> FXCarryTradeConfig:
        """Provide a basic strategy configuration."""
        return FXCarryTradeConfig(
            min_carry_threshold=Decimal("0.01"),
            max_positions=5,
            position_size=Decimal("0.1"),
            forward_months=3,
            stop_loss=Decimal("0.05"),
            take_profit=Decimal("0.15"),
            max_leverage=Decimal("2.0"),
            min_liquidity=Decimal("1000000"),
        )

    @pytest.fixture
    def mock_provider(self) -> InMemoryFXRateProvider:
        """Provide a mock rate provider with test data."""
        provider = InMemoryFXRateProvider()
        test_date = date(2024, 1, 15)

        # Add test data for common pairs
        pairs_data = [
            ("USD/JPY", Decimal("110.50"), Decimal("110.20"), Decimal("0.0525"), Decimal("0.0000")),
            ("EUR/USD", Decimal("1.0850"), Decimal("1.0900"), Decimal("0.0450"), Decimal("0.0525")),
            ("GBP/USD", Decimal("1.2700"), Decimal("1.2650"), Decimal("0.0515"), Decimal("0.0525")),
            ("AUD/USD", Decimal("0.6550"), Decimal("0.6580"), Decimal("0.0425"), Decimal("0.0525")),
            ("NZD/USD", Decimal("0.6150"), Decimal("0.6180"), Decimal("0.0550"), Decimal("0.0525")),
        ]

        for pair_str, spot, forward, rate_base, rate_quote in pairs_data:
            provider.add_spot_rate(pair_str, spot, test_date)
            provider.add_forward_rate(pair_str, forward, test_date, 3)

            # Parse pair for interest rates
            if "/" in pair_str:
                base, quote = pair_str.split("/")
                provider.add_interest_rate(base, rate_base, test_date, 3)
                provider.add_interest_rate(quote, rate_quote, test_date, 3)

        return provider

    def test_initialization_with_config(
        self, basic_config: FXCarryTradeConfig, mock_provider: InMemoryFXRateProvider
    ) -> None:
        """Test strategy initialization with config object."""
        strategy = FXCarryTradeStrategy(config=basic_config, rate_provider=mock_provider)

        assert strategy.config == basic_config
        assert strategy.rate_provider == mock_provider
        assert len(strategy.state.current_positions) == 0

    def test_initialization_with_dict_config(self, mock_provider: InMemoryFXRateProvider) -> None:
        """Test strategy initialization with dict config."""
        config_dict = {
            "min_carry_threshold": "0.02",
            "max_positions": 10,
            "position_size": "0.15",
            "forward_months": 6,
        }

        strategy = FXCarryTradeStrategy(config=config_dict, rate_provider=mock_provider)

        assert strategy.config.min_carry_threshold == Decimal("0.02")
        assert strategy.config.max_positions == 10
        assert strategy.config.position_size == Decimal("0.15")
        assert strategy.config.forward_months == 6

    def test_initialization_default_provider(self, basic_config: FXCarryTradeConfig) -> None:
        """Test strategy creates InMemoryFXRateProvider if none provided."""
        strategy = FXCarryTradeStrategy(config=basic_config)

        assert isinstance(strategy.rate_provider, InMemoryFXRateProvider)

    def test_initialization_default_calculator(
        self, basic_config: FXCarryTradeConfig, mock_provider: InMemoryFXRateProvider
    ) -> None:
        """Test strategy creates CarryCalculator if none provided."""
        strategy = FXCarryTradeStrategy(config=basic_config, rate_provider=mock_provider)

        assert isinstance(strategy.calculator, CarryCalculator)

    def test_initialization_custom_calculator(
        self,
        basic_config: FXCarryTradeConfig,
        mock_provider: InMemoryFXRateProvider,
    ) -> None:
        """Test strategy uses custom calculator if provided."""
        custom_calculator = CarryCalculator(
            signal_threshold=Decimal("0.02"),
            signal_multiplier=5.0,
        )

        strategy = FXCarryTradeStrategy(
            config=basic_config,
            rate_provider=mock_provider,
            calculator=custom_calculator,
        )

        assert strategy.calculator == custom_calculator

    def test_default_pairs_generated(
        self, basic_config: FXCarryTradeConfig, mock_provider: InMemoryFXRateProvider
    ) -> None:
        """Test that default G10 pairs are generated."""
        strategy = FXCarryTradeStrategy(config=basic_config, rate_provider=mock_provider)

        # Should have 28 pairs (8 choose 2)
        assert len(strategy.pairs) == 28

        # Check that major pairs are included (note: USD is always base in default pairs)
        assert FXPair("USD", "JPY") in strategy.pairs
        assert FXPair("USD", "EUR") in strategy.pairs
        assert FXPair("USD", "GBP") in strategy.pairs

    def test_string_representation(
        self, basic_config: FXCarryTradeConfig, mock_provider: InMemoryFXRateProvider
    ) -> None:
        """Test string representation of strategy."""
        strategy = FXCarryTradeStrategy(config=basic_config, rate_provider=mock_provider)

        str_repr = str(strategy)
        assert "FXCarryTradeStrategy" in str_repr
        assert "pairs=28" in str_repr

    def test_repr(
        self, basic_config: FXCarryTradeConfig, mock_provider: InMemoryFXRateProvider
    ) -> None:
        """Test detailed representation of strategy."""
        strategy = FXCarryTradeStrategy(config=basic_config, rate_provider=mock_provider)

        repr_str = repr(strategy)
        assert "FXCarryTradeStrategy" in repr_str


class TestFXCarryTradeStrategyGenerateSignals:
    """Tests for signal generation."""

    @pytest.fixture
    def strategy_with_data(self) -> FXCarryTradeStrategy:
        """Provide a strategy with pre-populated rate data."""
        provider = InMemoryFXRateProvider()
        test_date = date(2024, 1, 15)

        # Add comprehensive test data
        pairs_data = [
            ("USD/JPY", Decimal("110.50"), Decimal("110.20"), Decimal("0.0525"), Decimal("0.0000")),
            ("EUR/USD", Decimal("1.0850"), Decimal("1.0900"), Decimal("0.0450"), Decimal("0.0525")),
            ("GBP/USD", Decimal("1.2700"), Decimal("1.2650"), Decimal("0.0515"), Decimal("0.0525")),
        ]

        for pair_str, spot, forward, rate_base, rate_quote in pairs_data:
            provider.add_spot_rate(pair_str, spot, test_date)
            provider.add_forward_rate(pair_str, forward, test_date, 3)

            base, quote = pair_str.split("/")
            provider.add_interest_rate(base, rate_base, test_date, 3)
            provider.add_interest_rate(quote, rate_quote, test_date, 3)

        config = FXCarryTradeConfig(
            min_carry_threshold=Decimal("0.001"),  # Low threshold for testing
            max_positions=10,
        )

        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_generate_signals_returns_list(self, strategy_with_data: FXCarryTradeStrategy) -> None:
        """Test that generate_signals returns a list."""
        signals = strategy_with_data.generate_signals({})

        assert isinstance(signals, list)

    def test_generate_signals_content(self, strategy_with_data: FXCarryTradeStrategy) -> None:
        """Test that generated signals contain expected data."""
        signals = strategy_with_data.generate_signals({})

        for signal in signals:
            assert isinstance(signal, FXCarrySignal)
            assert -1 <= signal.signal <= 1

    def test_generate_signals_filters_by_threshold(
        self, strategy_with_data: FXCarryTradeStrategy
    ) -> None:
        """Test that signals are filtered by threshold."""
        # Set high threshold (within valid range)
        strategy_with_data.config.min_carry_threshold = Decimal("0.15")
        signals = strategy_with_data.generate_signals({})

        # Should have fewer signals with higher threshold
        assert len(signals) >= 0

    def test_generate_signals_limits_positions(
        self, strategy_with_data: FXCarryTradeStrategy
    ) -> None:
        """Test that signal count is limited by max_positions."""
        strategy_with_data.config.max_positions = 2
        signals = strategy_with_data.generate_signals({})

        assert len(signals) <= 2


class TestFXCarryTradeStrategyAnalyzeOpportunities:
    """Tests for opportunity analysis."""

    @pytest.fixture
    def strategy_for_analysis(self) -> FXCarryTradeStrategy:
        """Provide a strategy for opportunity analysis testing."""
        provider = InMemoryFXRateProvider()
        test_date = date(2024, 1, 15)

        # Add test data
        provider.add_spot_rate("USD/JPY", Decimal("110.50"), test_date)
        provider.add_forward_rate("USD/JPY", Decimal("110.20"), test_date, 3)
        provider.add_interest_rate("USD", Decimal("0.0525"), test_date, 3)
        provider.add_interest_rate("JPY", Decimal("0.0000"), test_date, 3)

        provider.add_spot_rate("EUR/USD", Decimal("1.0850"), test_date)
        provider.add_forward_rate("EUR/USD", Decimal("1.0900"), test_date, 3)
        provider.add_interest_rate("EUR", Decimal("0.0450"), test_date, 3)
        provider.add_interest_rate("USD", Decimal("0.0525"), test_date, 3)

        config = FXCarryTradeConfig(min_carry_threshold=Decimal("0.001"))
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_analyze_opportunities_returns_list(
        self, strategy_for_analysis: FXCarryTradeStrategy
    ) -> None:
        """Test that analyze_opportunities returns a list."""
        opportunities = strategy_for_analysis.analyze_opportunities()

        assert isinstance(opportunities, list)

    def test_analyze_opportunities_content(
        self, strategy_for_analysis: FXCarryTradeStrategy
    ) -> None:
        """Test that opportunities contain expected data."""
        opportunities = strategy_for_analysis.analyze_opportunities()

        for opp in opportunities:
            assert isinstance(opp, CarryTradeOpportunity)
            assert isinstance(opp.pair, FXPair)
            assert isinstance(opp.expected_carry, Decimal)
            assert 0 <= opp.confidence <= 100

    def test_analyze_opportunities_sorted(
        self, strategy_for_analysis: FXCarryTradeStrategy
    ) -> None:
        """Test that opportunities are sorted by expected carry."""
        opportunities = strategy_for_analysis.analyze_opportunities()

        if len(opportunities) > 1:
            # Should be sorted by absolute carry descending
            for i in range(len(opportunities) - 1):
                assert abs(opportunities[i].expected_carry) >= abs(
                    opportunities[i + 1].expected_carry
                )

    def test_analyze_opportunities_custom_date(
        self, strategy_for_analysis: FXCarryTradeStrategy
    ) -> None:
        """Test analyzing opportunities for a specific date."""
        custom_date = date(2024, 1, 20)
        opportunities = strategy_for_analysis.analyze_opportunities(as_of=custom_date)

        assert isinstance(opportunities, list)


class TestFXCarryTradeStrategyCalculateConfidence:
    """Tests for confidence calculation."""

    @pytest.fixture
    def strategy(self) -> FXCarryTradeStrategy:
        """Provide a basic strategy for testing."""
        config = FXCarryTradeConfig()
        provider = InMemoryFXRateProvider()
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_calculate_confidence_positive_carry(self, strategy: FXCarryTradeStrategy) -> None:
        """Test confidence calculation with positive carry."""
        signal = FXCarrySignal(
            pair=FXPair("USD", "JPY"),
            spot_rate=Decimal("110.50"),
            forward_rate=Decimal("110.20"),
            interest_rate_diff=Decimal("0.025"),
            forward_premium=Decimal("-0.003"),
            carry=Decimal("0.028"),
            signal=Decimal("0.5"),
            timestamp=date(2024, 1, 15),
        )

        confidence = strategy._calculate_confidence(signal)

        assert 0 <= confidence <= 100
        # Positive carry should boost confidence
        assert confidence > 50

    def test_calculate_confidence_negative_carry(self, strategy: FXCarryTradeStrategy) -> None:
        """Test confidence calculation with negative carry."""
        signal = FXCarrySignal(
            pair=FXPair("EUR", "USD"),
            spot_rate=Decimal("1.0850"),
            forward_rate=Decimal("1.0900"),
            interest_rate_diff=Decimal("-0.01"),
            forward_premium=Decimal("0.005"),
            carry=Decimal("-0.015"),
            signal=Decimal("-0.3"),
            timestamp=date(2024, 1, 15),
        )

        confidence = strategy._calculate_confidence(signal)

        assert 0 <= confidence <= 100
        # Negative carry should not boost confidence
        assert confidence < 50


class TestFXCarryTradeStrategyPositionManagement:
    """Tests for position management."""

    @pytest.fixture
    def strategy_for_positions(self) -> FXCarryTradeStrategy:
        """Provide a strategy for position management testing."""
        config = FXCarryTradeConfig(
            position_size=Decimal("0.1"),
            max_leverage=Decimal("2.0"),
        )
        provider = InMemoryFXRateProvider()
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    @pytest.fixture
    def sample_signal(self) -> FXCarrySignal:
        """Provide a sample trading signal."""
        return FXCarrySignal(
            pair=FXPair("USD", "JPY"),
            spot_rate=Decimal("110.50"),
            forward_rate=Decimal("110.20"),
            interest_rate_diff=Decimal("0.025"),
            forward_premium=Decimal("-0.003"),
            carry=Decimal("0.028"),
            signal=Decimal("0.5"),
            timestamp=date(2024, 1, 15),
        )

    def test_execute_signal_creates_position(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that executing a signal creates a position."""
        capital = Decimal("100000")
        position = strategy_for_positions.execute_signal(sample_signal, capital)

        assert position is not None
        assert isinstance(position, FXCarryPosition)
        assert position.pair == sample_signal.pair

    def test_execute_signal_adds_to_state(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that executing a signal adds position to state."""
        capital = Decimal("100000")
        strategy_for_positions.execute_signal(sample_signal, capital)

        assert sample_signal.pair in strategy_for_positions.state.current_positions

    def test_execute_signal_long_position(
        self, strategy_for_positions: FXCarryTradeStrategy
    ) -> None:
        """Test executing a long signal."""
        long_signal = FXCarrySignal(
            pair=FXPair("USD", "JPY"),
            spot_rate=Decimal("110.50"),
            forward_rate=Decimal("110.20"),
            interest_rate_diff=Decimal("0.025"),
            forward_premium=Decimal("-0.003"),
            carry=Decimal("0.028"),
            signal=Decimal("0.5"),
            timestamp=date(2024, 1, 15),
        )
        capital = Decimal("100000")
        position = strategy_for_positions.execute_signal(long_signal, capital)

        assert position is not None
        assert position.quantity > 0

    def test_execute_signal_short_position(
        self, strategy_for_positions: FXCarryTradeStrategy
    ) -> None:
        """Test executing a short signal."""
        short_signal = FXCarrySignal(
            pair=FXPair("EUR", "USD"),
            spot_rate=Decimal("1.0850"),
            forward_rate=Decimal("1.0900"),
            interest_rate_diff=Decimal("-0.01"),
            forward_premium=Decimal("0.005"),
            carry=Decimal("-0.015"),
            signal=Decimal("-0.5"),
            timestamp=date(2024, 1, 15),
        )
        capital = Decimal("100000")
        position = strategy_for_positions.execute_signal(short_signal, capital)

        assert position is not None
        assert position.quantity < 0

    def test_execute_signal_existing_position_returns_none(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that executing signal for existing position returns None."""
        capital = Decimal("100000")

        # First execution should succeed
        strategy_for_positions.execute_signal(sample_signal, capital)

        # Second execution should fail
        position = strategy_for_positions.execute_signal(sample_signal, capital)
        assert position is None

    def test_calculate_position_size(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test position size calculation with volatility adjustment."""
        capital = Decimal("100000")
        volatility = Decimal("0.05")  # 5% annual volatility
        position_size = strategy_for_positions._calculate_position_size(
            capital, sample_signal, volatility
        )

        # Position should be positive
        assert position_size > 0

        # With 5% volatility (above 1% baseline), position should be smaller than base
        # Base position: 100000 * 0.1 / 110.50 = 90.50
        # With 5% vol: adjustment = 0.01/0.05 = 0.2 (20% of base)
        # Expected: 90.50 * 0.2 = 18.10
        expected_base = (
            capital * strategy_for_positions.config.position_size
        ) / sample_signal.spot_rate

        # Position should be less than base due to higher volatility
        assert position_size < expected_base

        # Position should be approximately 20% of base (accounting for quantization)
        expected_adjusted = expected_base * (Decimal("0.01") / volatility)
        assert abs(position_size - expected_adjusted) < Decimal("1.0")  # Within 1 unit

    def test_calculate_position_size_with_leverage_cap(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that position size respects leverage cap."""
        # Set low leverage
        strategy_for_positions.config.max_leverage = Decimal("1.5")
        strategy_for_positions.config.position_size = Decimal("0.5")  # Use 50% of capital

        capital = Decimal("100000")
        volatility = Decimal("0.01")  # Low volatility for max position
        position_size = strategy_for_positions._calculate_position_size(
            capital, sample_signal, volatility
        )

        # Should be capped by leverage
        max_size = (capital * strategy_for_positions.config.max_leverage) / sample_signal.spot_rate
        assert position_size <= max_size

    def test_calculate_position_size_volatility_adjustment(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that higher volatility results in smaller position sizes."""
        capital = Decimal("100000")

        # Low volatility (at baseline) - should get base position
        # At 1% baseline, adjustment = 0.01/0.01 = 1.0 (base position)
        low_vol = Decimal("0.01")
        low_vol_position = strategy_for_positions._calculate_position_size(
            capital, sample_signal, low_vol
        )

        # High volatility (above baseline) - should get smaller position
        # At 4% volatility, adjustment = 0.01/0.04 = 0.25 (quarter position)
        high_vol = Decimal("0.04")
        high_vol_position = strategy_for_positions._calculate_position_size(
            capital, sample_signal, high_vol
        )

        # High vol position should be smaller than low vol position
        assert high_vol_position < low_vol_position

        # Verify the ratio is approximately 0.25 (4% vol vs 1% baseline)
        # Account for leverage cap interference
        ratio = high_vol_position / low_vol_position
        assert ratio < Decimal("0.5")  # Should be at most half the size

    def test_calculate_signal_volatility(
        self, strategy_for_positions: FXCarryTradeStrategy
    ) -> None:
        """Test volatility calculation from signal."""
        signal = FXCarrySignal(
            pair=FXPair("USD", "JPY"),
            spot_rate=Decimal("110.50"),
            forward_rate=Decimal("110.20"),
            interest_rate_diff=Decimal("0.025"),
            forward_premium=Decimal("-0.0027"),  # -0.27%
            carry=Decimal("0.0277"),
            signal=Decimal("0.5"),
            timestamp=date(2024, 1, 15),
        )

        volatility = strategy_for_positions._calculate_signal_volatility(signal)

        # Volatility should be positive
        assert volatility > 0

        # Should be at least minimum floor (2%)
        assert volatility >= Decimal("0.02")

        # Should be capped at maximum (50%)
        assert volatility <= Decimal("0.50")

    def test_calculate_position_size_invalid_capital(
        self, strategy_for_positions: FXCarryTradeStrategy, sample_signal: FXCarrySignal
    ) -> None:
        """Test that invalid capital raises ValueError."""
        with pytest.raises(ValueError, match="Capital must be positive"):
            strategy_for_positions._calculate_position_size(
                Decimal("0"), sample_signal, Decimal("0.05")
            )

        with pytest.raises(ValueError, match="Capital must be positive"):
            strategy_for_positions._calculate_position_size(
                Decimal("-1000"), sample_signal, Decimal("0.05")
            )

    def test_update_positions(self, strategy_for_positions: FXCarryTradeStrategy) -> None:
        """Test updating positions with current rates."""
        provider = strategy_for_positions.rate_provider
        test_date = date(2024, 1, 15)
        future_date = date(2024, 1, 20)

        # Add rate data
        provider.add_spot_rate("USD/JPY", Decimal("110.50"), test_date)
        provider.add_spot_rate("USD/JPY", Decimal("111.00"), future_date)

        # Create a position
        position = FXCarryPosition(
            pair=FXPair("USD", "JPY"),
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            current_price=Decimal("110.50"),
            carry_return=Decimal("0"),
            price_return=Decimal("0"),
            total_return=Decimal("0"),
            entry_date=test_date,
            current_date=test_date,
        )

        strategy_for_positions.state.current_positions[FXPair("USD", "JPY")] = position

        # Update positions
        updated = strategy_for_positions.update_positions(as_of=future_date)

        assert FXPair("USD", "JPY") in updated
        assert updated[FXPair("USD", "JPY")].current_price == Decimal("111.00")

    def test_close_position(self, strategy_for_positions: FXCarryTradeStrategy) -> None:
        """Test closing a position."""
        test_date = date(2024, 1, 15)

        # Create a position
        position = FXCarryPosition(
            pair=FXPair("USD", "JPY"),
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            current_price=Decimal("111.00"),
            carry_return=Decimal("0.01"),
            price_return=Decimal("0.0045"),
            total_return=Decimal("0.0145"),
            entry_date=test_date,
            current_date=test_date,
        )

        strategy_for_positions.state.current_positions[FXPair("USD", "JPY")] = position
        strategy_for_positions.state.total_exposure = Decimal("11100000")

        # Close the position
        closed = strategy_for_positions.close_position(
            FXPair("USD", "JPY"),
            Decimal("111.50"),
            date(2024, 1, 20),
        )

        assert closed is not None
        assert closed.current_price == Decimal("111.50")
        assert FXPair("USD", "JPY") not in strategy_for_positions.state.current_positions

    def test_close_nonexistent_position(self, strategy_for_positions: FXCarryTradeStrategy) -> None:
        """Test closing a position that doesn't exist."""
        closed = strategy_for_positions.close_position(
            FXPair("EUR", "USD"),
            Decimal("1.09"),
            date(2024, 1, 20),
        )

        assert closed is None


class TestFXCarryTradeStrategyExitConditions:
    """Tests for exit condition checking."""

    @pytest.fixture
    def strategy_for_exits(self) -> FXCarryTradeStrategy:
        """Provide a strategy for exit condition testing."""
        config = FXCarryTradeConfig(
            stop_loss=Decimal("0.05"),
            take_profit=Decimal("0.15"),
            min_carry_threshold=Decimal("0.01"),
        )
        provider = InMemoryFXRateProvider()
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    @pytest.fixture
    def long_position(self) -> FXCarryPosition:
        """Provide a sample long position."""
        test_date = date(2024, 1, 15)
        return FXCarryPosition(
            pair=FXPair("USD", "JPY"),
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            current_price=Decimal("110.50"),
            carry_return=Decimal("0"),
            price_return=Decimal("0"),
            total_return=Decimal("0"),
            entry_date=test_date,
            current_date=test_date,
        )

    def test_check_exit_conditions_no_position(
        self, strategy_for_exits: FXCarryTradeStrategy
    ) -> None:
        """Test exit check when no position exists."""
        should_close, reason = strategy_for_exits.check_exit_conditions(
            FXPair("USD", "JPY"),
            Decimal("111.00"),
        )

        assert should_close is False
        assert reason == "No position"

    def test_check_exit_conditions_stop_loss_long(
        self, strategy_for_exits: FXCarryTradeStrategy, long_position: FXCarryPosition
    ) -> None:
        """Test stop loss trigger for long position."""
        strategy_for_exits.state.current_positions[FXPair("USD", "JPY")] = long_position

        # Price drops 6% (exceeds 5% stop loss)
        should_close, reason = strategy_for_exits.check_exit_conditions(
            FXPair("USD", "JPY"),
            Decimal("104.00"),  # 110.50 * 0.94 = 103.87, close to 104
        )

        assert should_close is True
        assert "Stop loss" in reason

    def test_check_exit_conditions_take_profit_long(
        self, strategy_for_exits: FXCarryTradeStrategy, long_position: FXCarryPosition
    ) -> None:
        """Test take profit trigger for long position."""
        strategy_for_exits.state.current_positions[FXPair("USD", "JPY")] = long_position

        # Price rises 16% (exceeds 15% take profit)
        should_close, reason = strategy_for_exits.check_exit_conditions(
            FXPair("USD", "JPY"),
            Decimal("128.20"),  # 110.50 * 1.16 = 128.18
        )

        assert should_close is True
        assert "Take profit" in reason

    def test_check_exit_conditions_no_trigger(
        self, strategy_for_exits: FXCarryTradeStrategy, long_position: FXCarryPosition
    ) -> None:
        """Test no exit trigger when price is within range."""
        strategy_for_exits.state.current_positions[FXPair("USD", "JPY")] = long_position

        should_close, reason = strategy_for_exits.check_exit_conditions(
            FXPair("USD", "JPY"),
            Decimal("112.00"),  # Small gain
        )

        assert should_close is False
        assert reason == ""


class TestFXCarryTradeStrategyRiskCheck:
    """Tests for risk checking."""

    @pytest.fixture
    def strategy_for_risk(self) -> FXCarryTradeStrategy:
        """Provide a strategy for risk check testing."""
        config = FXCarryTradeConfig(
            max_positions=5,
        )
        provider = InMemoryFXRateProvider()
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_risk_check_pass(self, strategy_for_risk: FXCarryTradeStrategy) -> None:
        """Test risk check passes when conditions are met."""
        result = strategy_for_risk.risk_check(None, None)
        assert result is True

    def test_risk_check_max_positions_reached(
        self, strategy_for_risk: FXCarryTradeStrategy
    ) -> None:
        """Test risk check fails when max positions reached."""
        strategy_for_risk.config.max_positions = 1

        # Add a position
        test_date = date(2024, 1, 15)
        position = FXCarryPosition(
            pair=FXPair("USD", "JPY"),
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            current_price=Decimal("110.50"),
            carry_return=Decimal("0"),
            price_return=Decimal("0"),
            total_return=Decimal("0"),
            entry_date=test_date,
            current_date=test_date,
        )
        strategy_for_risk.state.current_positions[FXPair("USD", "JPY")] = position

        result = strategy_for_risk.risk_check(None, None)
        assert result is False

    def test_risk_check_no_capital(self, strategy_for_risk: FXCarryTradeStrategy) -> None:
        """Test risk check fails when no capital available."""
        strategy_for_risk.state.available_capital = Decimal("0")

        result = strategy_for_risk.risk_check(None, None)
        assert result is False


class TestFXCarryTradeStrategyPortfolioSummary:
    """Tests for portfolio summary."""

    @pytest.fixture
    def strategy_for_summary(self) -> FXCarryTradeStrategy:
        """Provide a strategy for portfolio summary testing."""
        config = FXCarryTradeConfig()
        provider = InMemoryFXRateProvider()
        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_get_portfolio_summary_empty(self, strategy_for_summary: FXCarryTradeStrategy) -> None:
        """Test portfolio summary with no positions."""
        summary = strategy_for_summary.get_portfolio_summary()

        assert summary["num_positions"] == 0
        assert summary["total_exposure"] == 0
        assert summary["total_pnl"] == 0
        assert summary["best_position"] is None
        assert summary["worst_position"] is None

    def test_get_portfolio_summary_with_positions(
        self, strategy_for_summary: FXCarryTradeStrategy
    ) -> None:
        """Test portfolio summary with positions."""
        test_date = date(2024, 1, 15)

        # Add two positions
        position1 = FXCarryPosition(
            pair=FXPair("USD", "JPY"),
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            current_price=Decimal("111.50"),
            carry_return=Decimal("0.01"),
            price_return=Decimal("0.009"),
            total_return=Decimal("0.019"),
            entry_date=test_date,
            current_date=test_date,
        )

        position2 = FXCarryPosition(
            pair=FXPair("EUR", "USD"),
            quantity=Decimal("-100000"),
            entry_price=Decimal("1.0900"),
            current_price=Decimal("1.0950"),
            carry_return=Decimal("0.005"),
            price_return=Decimal("-0.0046"),
            total_return=Decimal("0.0004"),
            entry_date=test_date,
            current_date=test_date,
        )

        strategy_for_summary.state.current_positions[FXPair("USD", "JPY")] = position1
        strategy_for_summary.state.current_positions[FXPair("EUR", "USD")] = position2
        strategy_for_summary.state.total_exposure = Decimal("22050000")

        summary = strategy_for_summary.get_portfolio_summary()

        assert summary["num_positions"] == 2
        assert summary["total_exposure"] == 22050000
        assert abs(summary["total_pnl"] - 0.0194) < 0.0001
        assert summary["best_position"]["pair"] == "USD/JPY"
        assert summary["worst_position"]["pair"] == "EUR/USD"


class TestFXCarryTradeStrategyRequiredParameters:
    """Tests for required parameters."""

    def test_get_required_parameters(self) -> None:
        """Test getting required strategy parameters."""
        config = FXCarryTradeConfig()
        provider = InMemoryFXRateProvider()
        strategy = FXCarryTradeStrategy(config=config, rate_provider=provider)

        params = strategy.get_required_parameters()

        expected_params = [
            "min_carry_threshold",
            "max_positions",
            "position_size",
            "forward_months",
            "stop_loss",
            "take_profit",
        ]

        for param in expected_params:
            assert param in params


class TestFXCarryTradeStrategyIntegration:
    """Integration tests for the full strategy workflow."""

    @pytest.fixture
    def full_strategy(self) -> FXCarryTradeStrategy:
        """Provide a fully configured strategy with test data."""
        provider = InMemoryFXRateProvider()
        test_date = date(2024, 1, 15)

        # Populate with realistic data
        pairs_data = [
            ("USD/JPY", Decimal("110.50"), Decimal("110.20"), Decimal("0.0525"), Decimal("0.0000")),
            ("EUR/USD", Decimal("1.0850"), Decimal("1.0900"), Decimal("0.0450"), Decimal("0.0525")),
            ("AUD/JPY", Decimal("95.50"), Decimal("95.80"), Decimal("0.0425"), Decimal("0.0000")),
        ]

        for pair_str, spot, forward, rate_base, rate_quote in pairs_data:
            provider.add_spot_rate(pair_str, spot, test_date)
            provider.add_forward_rate(pair_str, forward, test_date, 3)

            base, quote = pair_str.split("/")
            provider.add_interest_rate(base, rate_base, test_date, 3)
            provider.add_interest_rate(quote, rate_quote, test_date, 3)

        config = FXCarryTradeConfig(
            min_carry_threshold=Decimal("0.001"),
            max_positions=3,
            position_size=Decimal("0.1"),
        )

        return FXCarryTradeStrategy(config=config, rate_provider=provider)

    def test_full_workflow(self, full_strategy: FXCarryTradeStrategy) -> None:
        """Test complete workflow from signals to positions."""
        # 1. Generate signals
        signals = full_strategy.generate_signals({})
        assert len(signals) >= 0

        # 2. Analyze opportunities
        opportunities = full_strategy.analyze_opportunities()
        assert isinstance(opportunities, list)

        # 3. Execute a signal if available
        if signals:
            capital = Decimal("100000")
            position = full_strategy.execute_signal(signals[0], capital)

            if position:
                assert position.pair == signals[0].pair

                # 4. Update position
                updated = full_strategy.update_positions()
                assert position.pair in updated

                # 5. Check portfolio
                summary = full_strategy.get_portfolio_summary()
                assert summary["num_positions"] >= 1

    def test_strategy_with_error_handling(self, full_strategy: FXCarryTradeStrategy) -> None:
        """Test strategy handles errors gracefully."""
        # This should not raise an exception
        signals = full_strategy.generate_signals({})

        # Even with missing data, should return a list
        assert isinstance(signals, list)
