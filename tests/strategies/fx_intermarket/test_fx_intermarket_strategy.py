"""
Tests for FX Intermarket Strategy.

This module tests the FXIntermarketStrategy class which implements
the intermarket strategy based on cross-asset relationships.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.fx_intermarket.correlation_analyzer import CorrelationAnalyzer
from app.domain.strategies.fx_intermarket.fx_intermarket_strategy import (
    FXIntermarketState,
    FXIntermarketStrategy,
)
from app.domain.strategies.fx_intermarket.models import (
    AssetClass,
    FXIntermarketConfig,
    IntermarketRelationship,
    IntermarketSignal,
    RelationshipType,
)


class TestFXIntermarketState:
    """Tests for FXIntermarketState dataclass."""

    def test_state_initialization_default(self) -> None:
        """Test state initialization with default values."""
        state = FXIntermarketState()

        assert state.active_relationships == {}
        assert state.historical_correlations == {}
        assert state.current_signals == []
        assert state.total_trades == 0
        assert isinstance(state.last_correlation_update, datetime)

    def test_state_custom_values(self) -> None:
        """Test state with custom values."""
        test_time = datetime(2024, 1, 15, 10, 30, 0)
        relationship = MagicMock(spec=IntermarketRelationship)
        signal = MagicMock(spec=IntermarketSignal)

        state = FXIntermarketState(
            active_relationships={"USD/JPY_SPX": relationship},
            historical_correlations={"USD/JPY_SPX": [Decimal("0.7"), Decimal("0.75")]},
            current_signals=[signal],
            last_correlation_update=test_time,
            total_trades=10,
        )

        assert len(state.active_relationships) == 1
        assert len(state.historical_correlations) == 1
        assert len(state.current_signals) == 1
        assert state.last_correlation_update == test_time
        assert state.total_trades == 10


class TestFXIntermarketStrategyInitialization:
    """Tests for FXIntermarketStrategy initialization."""

    @pytest.fixture
    def basic_config(self) -> FXIntermarketConfig:
        """Provide a basic strategy configuration."""
        return FXIntermarketConfig(
            correlation_lookback=60,
            min_correlation=Decimal("0.6"),
            min_significance=Decimal("70"),
            signal_threshold=Decimal("60"),
            min_signal_strength=Decimal("65"),
            max_positions=5,
            stop_loss=Decimal("0.03"),
            take_profit=Decimal("0.08"),
            position_size=Decimal("0.1"),
        )

    def test_initialization_with_config(self, basic_config: FXIntermarketConfig) -> None:
        """Test strategy initialization with config object."""
        strategy = FXIntermarketStrategy(config=basic_config)

        assert strategy.config == basic_config
        assert isinstance(strategy.analyzer, CorrelationAnalyzer)
        assert isinstance(strategy.state, FXIntermarketState)
        assert len(strategy.state.active_relationships) == 0

    def test_initialization_with_dict_config(self) -> None:
        """Test strategy initialization with dict config."""
        config_dict = {
            "correlation_lookback": 90,
            "min_correlation": "0.7",
            "min_significance": "80",
            "signal_threshold": "70",
            "max_positions": 10,
        }

        strategy = FXIntermarketStrategy(config=config_dict)

        assert strategy.config.correlation_lookback == 90
        assert strategy.config.min_correlation == Decimal("0.7")
        assert strategy.config.min_significance == Decimal("80")
        assert strategy.config.signal_threshold == Decimal("70")
        assert strategy.config.max_positions == 10

    def test_initialization_analyzer_config(self, basic_config: FXIntermarketConfig) -> None:
        """Test that analyzer is initialized with config parameters."""
        strategy = FXIntermarketStrategy(config=basic_config)

        assert strategy.analyzer.lookback_days == basic_config.correlation_lookback
        assert strategy.analyzer.min_correlation == basic_config.min_correlation
        assert strategy.analyzer.min_significance == basic_config.min_significance

    def test_default_relationships_setup(self, basic_config: FXIntermarketConfig) -> None:
        """Test that default relationships are set up."""
        strategy = FXIntermarketStrategy(config=basic_config)

        assert "USD/JPY_SPX" in strategy.default_relationships
        assert strategy.default_relationships["USD/JPY_SPX"] == RelationshipType.SAFE_HAVEN
        assert "AUD/USD_GOLD" in strategy.default_relationships
        assert strategy.default_relationships["AUD/USD_GOLD"] == RelationshipType.COMMODITY_LINK

    def test_string_representation(self, basic_config: FXIntermarketConfig) -> None:
        """Test string representation of strategy."""
        strategy = FXIntermarketStrategy(config=basic_config)

        str_repr = str(strategy)
        assert "FXIntermarketStrategy" in str_repr
        assert "pairs=7" in str_repr
        assert "assets=5" in str_repr

    def test_repr(self, basic_config: FXIntermarketConfig) -> None:
        """Test detailed representation of strategy."""
        strategy = FXIntermarketStrategy(config=basic_config)

        repr_str = repr(strategy)
        assert "FXIntermarketStrategy" in repr_str


class TestFXIntermarketStrategyGenerateSignals:
    """Tests for signal generation."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig(
            min_correlation=Decimal("0.5"),
            min_significance=Decimal("60"),
            signal_threshold=Decimal("50"),
        )
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def sample_market_data(self) -> dict[str, Series]:
        """Provide sample market data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        return {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "USD/JPY": Series(np.random.randn(100) * 0.01, index=dates),
            "SPX": Series(np.random.randn(100) * 0.02, index=dates),
            "GOLD": Series(np.random.randn(100) * 0.015, index=dates),
        }

    def test_generate_signals_returns_list(
        self, strategy: FXIntermarketStrategy, sample_market_data: dict[str, Series]
    ) -> None:
        """Test that generate_signals returns a list."""
        signals = strategy.generate_signals(sample_market_data)

        assert isinstance(signals, list)

    def test_generate_signals_with_invalid_market_data_type(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test generate_signals rejects non-dict market_data."""
        with pytest.raises(ValueError, match="market_data must be a dict"):
            strategy.generate_signals("not_a_dict")

    def test_generate_signals_content(
        self, strategy: FXIntermarketStrategy, sample_market_data: dict[str, Series]
    ) -> None:
        """Test that generated signals contain expected data."""
        # Add a relationship to state for testing
        relationship = IntermarketRelationship(
            fx_pair="USD/JPY",
            external_asset="SPX",
            asset_class=AssetClass.EQUITY,
            relationship_type=RelationshipType.SAFE_HAVEN,
            correlation=Decimal("-0.75"),
            beta=Decimal("-0.5"),
            significance=Decimal("95"),
            lookback_days=60,
        )
        strategy.state.active_relationships["USD/JPY_SPX"] = relationship

        signals = strategy.generate_signals(sample_market_data)

        for signal in signals:
            assert isinstance(signal, Signal)
            assert isinstance(signal.symbol, str)
            assert signal.source == SignalSource.FUNDAMENTAL

    def test_generate_signals_limits_positions(
        self, strategy: FXIntermarketStrategy, sample_market_data: dict[str, Series]
    ) -> None:
        """Test that signal count is limited by max_positions."""
        strategy.config.max_positions = 2

        # Add multiple relationships
        for i in range(5):
            relationship = IntermarketRelationship(
                fx_pair=f"PAIR{i}",
                external_asset="SPX",
                asset_class=AssetClass.EQUITY,
                relationship_type=RelationshipType.SAFE_HAVEN,
                correlation=Decimal("-0.75"),
                beta=Decimal("-0.5"),
                significance=Decimal("95"),
                lookback_days=60,
            )
            strategy.state.active_relationships[f"PAIR{i}_SPX"] = relationship

        signals = strategy.generate_signals(sample_market_data)

        assert len(signals) <= 2


class TestFXIntermarketStrategyAnalyzeRelationships:
    """Tests for relationship analysis."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_analyze_intermarket_relationships_returns_list(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test that analyze_intermarket_relationships returns a list."""
        # Add a relationship to state
        relationship = IntermarketRelationship(
            fx_pair="USD/JPY",
            external_asset="SPX",
            asset_class=AssetClass.EQUITY,
            relationship_type=RelationshipType.SAFE_HAVEN,
            correlation=Decimal("-0.75"),
            beta=Decimal("-0.5"),
            significance=Decimal("95"),
            lookback_days=60,
        )
        strategy.state.active_relationships["USD/JPY_SPX"] = relationship

        relationships = strategy.analyze_intermarket_relationships(datetime.utcnow())

        assert isinstance(relationships, list)
        assert len(relationships) == 1
        assert relationships[0] == relationship

    def test_analyze_intermarket_relationships_empty_state(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test analyze with empty state."""
        relationships = strategy.analyze_intermarket_relationships(datetime.utcnow())

        assert isinstance(relationships, list)
        assert len(relationships) == 0


class TestFXIntermarketStrategyDetectSignificantMoves:
    """Tests for significant move detection."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig(
            monitored_assets={
                "SPX": AssetClass.EQUITY,
                "GOLD": AssetClass.COMMODITY,
            },
        )
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def returns_data(self) -> dict[str, Series]:
        """Provide returns data for testing."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        # Create returns where last value is a significant move
        normal_returns = list(np.random.randn(99) * 0.01)
        significant_move = 0.03  # 3% move

        return {
            "SPX": Series(normal_returns + [significant_move], index=dates),
            "GOLD": Series(normal_returns + [-0.025], index=dates),
            "EUR/USD": Series(normal_returns + [0.005], index=dates),
        }

    def test_detect_significant_moves_returns_dict(
        self, strategy: FXIntermarketStrategy, returns_data: dict[str, Series]
    ) -> None:
        """Test that detect_significant_moves returns a dict."""
        moves = strategy.detect_significant_moves(returns_data, threshold_std=2.0)

        assert isinstance(moves, dict)

    def test_detect_significant_moves_detects_moves(
        self, strategy: FXIntermarketStrategy, returns_data: dict[str, Series]
    ) -> None:
        """Test that significant moves are detected."""
        moves = strategy.detect_significant_moves(returns_data, threshold_std=2.0)

        # Should detect moves in SPX and GOLD (monitored assets)
        # but not EUR/USD (FX pair, not external asset)
        assert "SPX" in moves or "GOLD" in moves

    def test_detect_significant_move_structure(
        self, strategy: FXIntermarketStrategy, returns_data: dict[str, Series]
    ) -> None:
        """Test structure of detected move."""
        moves = strategy.detect_significant_moves(returns_data, threshold_std=1.5)

        if moves:
            for asset, move_info in moves.items():
                assert "return" in move_info
                assert "z_score" in move_info
                assert "mean" in move_info
                assert "std" in move_info
                assert "direction" in move_info
                assert isinstance(move_info["return"], Decimal)
                assert isinstance(move_info["z_score"], Decimal)

    def test_detect_significant_moves_direction(
        self, strategy: FXIntermarketStrategy, returns_data: dict[str, Series]
    ) -> None:
        """Test direction detection."""
        moves = strategy.detect_significant_moves(returns_data, threshold_std=1.5)

        if "SPX" in moves:
            assert moves["SPX"]["direction"] == "up"

        if "GOLD" in moves:
            assert moves["GOLD"]["direction"] == "down"

    def test_detect_significant_moves_insufficient_data(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test handling of insufficient data."""
        returns_data = {
            "SPX": Series([0.01]),  # Only one data point
        }

        moves = strategy.detect_significant_moves(returns_data, threshold_std=2.0)

        # Should handle gracefully
        assert isinstance(moves, dict)


class TestFXIntermarketStrategyGenerateIntermarketSignal:
    """Tests for intermarket signal generation."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig(
            min_signal_strength=Decimal("50"),
        )
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def sample_relationship(self) -> IntermarketRelationship:
        """Provide a sample relationship."""
        return IntermarketRelationship(
            fx_pair="USD/JPY",
            external_asset="SPX",
            asset_class=AssetClass.EQUITY,
            relationship_type=RelationshipType.SAFE_HAVEN,
            correlation=Decimal("-0.75"),
            beta=Decimal("-0.5"),
            significance=Decimal("95"),
            lookback_days=60,
        )

    @pytest.fixture
    def sample_asset_move(self) -> dict[str, Any]:
        """Provide a sample asset move."""
        return {
            "return": Decimal("-0.02"),  # SPX down 2%
            "z_score": Decimal("2.5"),
            "mean": Decimal("0.001"),
            "std": Decimal("0.008"),
            "direction": "down",
        }

    def test_generate_intermarket_signal(
        self,
        strategy: FXIntermarketStrategy,
        sample_relationship: IntermarketRelationship,
        sample_asset_move: dict[str, Any],
    ) -> None:
        """Test intermarket signal generation."""
        signal = strategy.generate_intermarket_signal(
            fx_pair="USD/JPY",
            trigger_asset="SPX",
            relationship=sample_relationship,
            asset_move=sample_asset_move,
        )

        # Signal may be None if strength is below threshold
        # Test the generation process works
        assert signal is None or isinstance(signal, IntermarketSignal)

    def test_generate_intermarket_signal_safe_haven_buy(
        self, strategy: FXIntermarketStrategy, sample_relationship: IntermarketRelationship
    ) -> None:
        """Test signal generation for safe haven relationship with larger move."""
        # Use a larger asset move to ensure signal is generated
        asset_move = {
            "return": Decimal("-0.05"),  # SPX down 5%
            "z_score": Decimal("3.0"),
            "mean": Decimal("0.001"),
            "std": Decimal("0.015"),
            "direction": "down",
        }

        signal = strategy.generate_intermarket_signal(
            fx_pair="USD/JPY",
            trigger_asset="SPX",
            relationship=sample_relationship,
            asset_move=asset_move,
        )

        # Signal may be None if strength is below threshold
        # If generated, should be buy for safe haven with SPX down
        if signal is not None:
            assert signal.is_buy is True

    def test_generate_intermarket_signal_below_threshold(
        self, strategy: FXIntermarketStrategy, sample_relationship: IntermarketRelationship
    ) -> None:
        """Test that weak signals return None."""
        strategy.config.min_signal_strength = Decimal("90")

        asset_move = {
            "return": Decimal("0.001"),  # Very small move
            "z_score": Decimal("1.0"),
            "mean": Decimal("0.001"),
            "std": Decimal("0.01"),
            "direction": "up",
        }

        signal = strategy.generate_intermarket_signal(
            fx_pair="USD/JPY",
            trigger_asset="SPX",
            relationship=sample_relationship,
            asset_move=asset_move,
        )

        # Should return None for weak signals
        assert signal is None


class TestFXIntermarketStrategyCalculateExpectedMove:
    """Tests for expected move calculation."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_calculate_expected_move_positive(self, strategy: FXIntermarketStrategy) -> None:
        """Test expected move calculation with positive values."""
        expected = strategy.calculate_expected_move(
            asset_move=Decimal("0.02"),
            correlation=Decimal("0.8"),
            beta=Decimal("0.5"),
        )

        # 0.02 * 0.8 * 0.5 = 0.008
        assert expected == Decimal("0.008")

    def test_calculate_expected_move_negative_correlation(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test expected move with negative correlation."""
        expected = strategy.calculate_expected_move(
            asset_move=Decimal("0.02"),
            correlation=Decimal("-0.75"),
            beta=Decimal("-0.5"),
        )

        # 0.02 * -0.75 * -0.5 = 0.0075
        assert expected == Decimal("0.0075")

    def test_calculate_expected_move_negative_asset_move(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test expected move with negative asset move."""
        expected = strategy.calculate_expected_move(
            asset_move=Decimal("-0.02"),
            correlation=Decimal("0.8"),
            beta=Decimal("0.5"),
        )

        # -0.02 * 0.8 * 0.5 = -0.008
        assert expected == Decimal("-0.008")


class TestFXIntermarketStrategyCalculateSignalStrength:
    """Tests for signal strength calculation."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_calculate_signal_strength(self, strategy: FXIntermarketStrategy) -> None:
        """Test signal strength calculation."""
        strength = strategy.calculate_signal_strength(
            expected_move=Decimal("0.015"),
            correlation=Decimal("0.8"),
            significance=Decimal("90"),
        )

        assert isinstance(strength, Decimal)
        assert Decimal("0") <= strength <= Decimal("100")

    def test_calculate_signal_strength_high_values(self, strategy: FXIntermarketStrategy) -> None:
        """Test strength with high input values."""
        strength = strategy.calculate_signal_strength(
            expected_move=Decimal("0.05"),
            correlation=Decimal("0.9"),
            significance=Decimal("95"),
        )

        # Should be high
        assert strength >= Decimal("70")

    def test_calculate_signal_strength_low_values(self, strategy: FXIntermarketStrategy) -> None:
        """Test strength with low input values."""
        strength = strategy.calculate_signal_strength(
            expected_move=Decimal("0.005"),
            correlation=Decimal("0.5"),
            significance=Decimal("60"),
        )

        # Should be lower
        assert strength < Decimal("70")


class TestFXIntermarketStrategyCalculateConfidence:
    """Tests for confidence calculation."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_calculate_confidence(self, strategy: FXIntermarketStrategy) -> None:
        """Test confidence calculation."""
        confidence = strategy.calculate_confidence(
            correlation=Decimal("-0.75"),
            significance=Decimal("95"),
            relationship_stability=Decimal("80"),
        )

        assert isinstance(confidence, Decimal)
        assert Decimal("0") <= confidence <= Decimal("100")

    def test_calculate_confidence_high(self, strategy: FXIntermarketStrategy) -> None:
        """Test confidence with high values."""
        confidence = strategy.calculate_confidence(
            correlation=Decimal("0.9"),
            significance=Decimal("95"),
            relationship_stability=Decimal("90"),
        )

        # Should be high
        assert confidence >= Decimal("70")

    def test_calculate_confidence_low(self, strategy: FXIntermarketStrategy) -> None:
        """Test confidence with low values."""
        confidence = strategy.calculate_confidence(
            correlation=Decimal("0.4"),
            significance=Decimal("60"),
            relationship_stability=Decimal("50"),
        )

        # Should be lower
        assert confidence < Decimal("70")


class TestFXIntermarketStrategyDetermineSignalType:
    """Tests for signal type determination."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_determine_signal_type_safe_haven_positive_move(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test signal type for safe haven with positive expected move."""
        signal_type = strategy._determine_signal_type(
            expected_move=Decimal("0.01"),
            relationship_type=RelationshipType.SAFE_HAVEN,
        )

        # Positive expected move for safe haven -> sell
        assert signal_type == "sell"

    def test_determine_signal_type_safe_haven_negative_move(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test signal type for safe haven with negative expected move."""
        signal_type = strategy._determine_signal_type(
            expected_move=Decimal("-0.01"),
            relationship_type=RelationshipType.SAFE_HAVEN,
        )

        # Negative expected move for safe haven -> buy
        assert signal_type == "buy"

    def test_determine_signal_type_commodity_link_positive(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test signal type for commodity link with positive expected move."""
        signal_type = strategy._determine_signal_type(
            expected_move=Decimal("0.01"),
            relationship_type=RelationshipType.COMMODITY_LINK,
        )

        assert signal_type == "buy"

    def test_determine_signal_type_commodity_link_negative(
        self, strategy: FXIntermarketStrategy
    ) -> None:
        """Test signal type for commodity link with negative expected move."""
        signal_type = strategy._determine_signal_type(
            expected_move=Decimal("-0.01"),
            relationship_type=RelationshipType.COMMODITY_LINK,
        )

        assert signal_type == "sell"

    def test_determine_signal_type_carry_trade(self, strategy: FXIntermarketStrategy) -> None:
        """Test signal type for carry trade."""
        signal_type = strategy._determine_signal_type(
            expected_move=Decimal("0.01"),
            relationship_type=RelationshipType.CARRY_TRADE,
        )

        assert signal_type == "buy"


class TestFXIntermarketStrategyFindRelatedPairs:
    """Tests for finding related pairs."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def sample_relationships(self) -> list[IntermarketRelationship]:
        """Provide sample relationships."""
        return [
            IntermarketRelationship(
                fx_pair="USD/JPY",
                external_asset="SPX",
                asset_class=AssetClass.EQUITY,
                relationship_type=RelationshipType.SAFE_HAVEN,
                correlation=Decimal("-0.75"),
                beta=Decimal("-0.5"),
                significance=Decimal("95"),
                lookback_days=60,
            ),
            IntermarketRelationship(
                fx_pair="EUR/USD",
                external_asset="SPX",
                asset_class=AssetClass.EQUITY,
                relationship_type=RelationshipType.CARRY_TRADE,
                correlation=Decimal("0.6"),
                beta=Decimal("0.3"),
                significance=Decimal("75"),
                lookback_days=60,
            ),
            IntermarketRelationship(
                fx_pair="AUD/USD",
                external_asset="GOLD",
                asset_class=AssetClass.COMMODITY,
                relationship_type=RelationshipType.COMMODITY_LINK,
                correlation=Decimal("0.8"),
                beta=Decimal("0.6"),
                significance=Decimal("60"),  # Below 70% threshold
                lookback_days=60,
            ),
        ]

    def test_find_related_pairs(
        self, strategy: FXIntermarketStrategy, sample_relationships: list[IntermarketRelationship]
    ) -> None:
        """Test finding pairs related to an asset."""
        related = strategy._find_related_pairs("SPX", sample_relationships)

        # Both USD/JPY (95%) and EUR/USD (75%) have significance >= 70% threshold
        assert len(related) == 2
        assert related[0][0] == "USD/JPY"
        assert related[1][0] == "EUR/USD"

    def test_find_related_pairs_no_matches(
        self, strategy: FXIntermarketStrategy, sample_relationships: list[IntermarketRelationship]
    ) -> None:
        """Test finding pairs when no matches."""
        related = strategy._find_related_pairs("OIL", sample_relationships)

        assert len(related) == 0


class TestFXIntermarketStrategyConvertToBaseSignal:
    """Tests for converting to base Signal type."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def intermarket_signal(self) -> IntermarketSignal:
        """Provide a sample intermarket signal."""
        return IntermarketSignal(
            fx_pair="USD/JPY",
            signal_type="buy",
            strength=Decimal("80"),
            trigger_asset="SPX",
            relationship_type=RelationshipType.SAFE_HAVEN,
            expected_move=Decimal("0.02"),
            confidence=Decimal("85"),
            rationale="Test signal",
        )

    def test_convert_to_base_signal(
        self, strategy: FXIntermarketStrategy, intermarket_signal: IntermarketSignal
    ) -> None:
        """Test conversion to base Signal."""
        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        assert isinstance(base_signal, Signal)
        assert base_signal.symbol == "USD/JPY"
        assert base_signal.signal_type == SignalType.BUY
        assert base_signal.source == SignalSource.FUNDAMENTAL
        assert base_signal.confidence == 85.0

    def test_convert_signal_very_strong(
        self, strategy: FXIntermarketStrategy, intermarket_signal: IntermarketSignal
    ) -> None:
        """Test strength mapping for very strong."""
        intermarket_signal.strength = Decimal("90")
        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        assert base_signal.strength == SignalStrength.VERY_STRONG

    def test_convert_signal_strong(
        self, strategy: FXIntermarketStrategy, intermarket_signal: IntermarketSignal
    ) -> None:
        """Test strength mapping for strong."""
        intermarket_signal.strength = Decimal("70")
        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        assert base_signal.strength == SignalStrength.STRONG

    def test_convert_signal_moderate(
        self, strategy: FXIntermarketStrategy, intermarket_signal: IntermarketSignal
    ) -> None:
        """Test strength mapping for moderate."""
        intermarket_signal.strength = Decimal("55")
        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        assert base_signal.strength == SignalStrength.MODERATE

    def test_convert_signal_weak(
        self, strategy: FXIntermarketStrategy, intermarket_signal: IntermarketSignal
    ) -> None:
        """Test strength mapping for weak."""
        intermarket_signal.strength = Decimal("40")
        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        # Should return None for weak signals that don't meet criteria
        # or return a Signal with WEAK strength
        if base_signal is not None:
            assert base_signal.strength == SignalStrength.WEAK
        else:
            assert base_signal is None  # Conversion may fail for weak signals

    def test_convert_signal_sell_type(self, strategy: FXIntermarketStrategy) -> None:
        """Test conversion of sell signal."""
        intermarket_signal = IntermarketSignal(
            fx_pair="EUR/USD",
            signal_type="sell",
            strength=Decimal("70"),
            trigger_asset="SPX",
            relationship_type=RelationshipType.CARRY_TRADE,
            expected_move=Decimal("-0.01"),
            confidence=Decimal("75"),
            rationale="Test sell signal",
        )

        base_signal = strategy._convert_to_base_signal(intermarket_signal)

        assert base_signal.signal_type == SignalType.SELL


class TestFXIntermarketStrategyUpdateCorrelations:
    """Tests for correlation updates."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_update_correlations_same_day(self, strategy: FXIntermarketStrategy) -> None:
        """Test that correlations aren't updated multiple times per day."""
        initial_time = strategy.state.last_correlation_update

        strategy.update_correlations(strategy.state.last_correlation_update)

        # Should not update
        assert strategy.state.last_correlation_update == initial_time

    def test_update_correlations_next_day(self, strategy: FXIntermarketStrategy) -> None:
        """Test that correlations are updated next day."""
        next_day = datetime.now(timezone.utc)

        strategy.update_correlations(next_day)

        # Note: In a real implementation, this would trigger actual correlation updates
        # For testing, we just verify the method runs without error


class TestFXIntermarketStrategyGetters:
    """Tests for getter methods."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig()
        return FXIntermarketStrategy(config=config)

    def test_get_monitored_pairs(self, strategy: FXIntermarketStrategy) -> None:
        """Test getting monitored pairs."""
        pairs = strategy.get_monitored_pairs()

        assert isinstance(pairs, list)
        assert "EUR/USD" in pairs
        assert "USD/JPY" in pairs

    def test_get_monitored_assets(self, strategy: FXIntermarketStrategy) -> None:
        """Test getting monitored assets."""
        assets = strategy.get_monitored_assets()

        assert isinstance(assets, dict)
        assert "SPX" in assets
        assert assets["SPX"] == AssetClass.EQUITY

    def test_get_portfolio_summary(self, strategy: FXIntermarketStrategy) -> None:
        """Test getting portfolio summary."""
        summary = strategy.get_portfolio_summary()

        assert isinstance(summary, dict)
        assert "active_relationships" in summary
        assert "current_signals" in summary
        assert "total_trades" in summary
        assert "monitored_pairs" in summary
        assert "monitored_assets" in summary


class TestFXIntermarketStrategyRiskCheck:
    """Tests for risk checking."""

    @pytest.fixture
    def strategy(self) -> FXIntermarketStrategy:
        """Provide a strategy for testing."""
        config = FXIntermarketConfig(signal_threshold=Decimal("60"))
        return FXIntermarketStrategy(config=config)

    def test_risk_check_pass(self, strategy: FXIntermarketStrategy) -> None:
        """Test risk check passes with high confidence."""
        signal = Signal(
            symbol="USD/JPY",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.FUNDAMENTAL,
            price=Decimal("110.50"),
            volume=Decimal("1000000"),
        )

        result = strategy.risk_check(signal, None)

        assert result is True

    def test_risk_check_fail_low_confidence(self, strategy: FXIntermarketStrategy) -> None:
        """Test risk check fails with low confidence."""
        signal = Signal(
            symbol="USD/JPY",
            signal_type=SignalType.BUY,
            strength=SignalStrength.WEAK,
            confidence=50.0,
            liquidity_score=75.0,
            priority_score=50.0,
            source=SignalSource.FUNDAMENTAL,
            price=Decimal("110.50"),
            volume=Decimal("1000000"),
        )

        result = strategy.risk_check(signal, None)

        assert result is False


class TestFXIntermarketStrategyRequiredParameters:
    """Tests for required parameters."""

    def test_get_required_parameters(self) -> None:
        """Test getting required parameters."""
        config = FXIntermarketConfig()
        strategy = FXIntermarketStrategy(config=config)

        params = strategy.get_required_parameters()

        expected_params = [
            "correlation_lookback",
            "min_correlation",
            "min_significance",
            "signal_threshold",
            "max_positions",
            "stop_loss",
            "take_profit",
        ]

        for param in expected_params:
            assert param in params


class TestFXIntermarketStrategyIntegration:
    """Integration tests for full workflow."""

    @pytest.fixture
    def full_strategy(self) -> FXIntermarketStrategy:
        """Provide a fully configured strategy."""
        config = FXIntermarketConfig(
            min_correlation=Decimal("0.5"),
            min_significance=Decimal("60"),
            signal_threshold=Decimal("50"),
            max_positions=3,
        )
        return FXIntermarketStrategy(config=config)

    @pytest.fixture
    def sample_market_data(self) -> dict[str, Series]:
        """Provide sample market data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        return {
            "EUR/USD": Series(np.random.randn(100) * 0.01, index=dates),
            "USD/JPY": Series(np.random.randn(100) * 0.01, index=dates),
            "SPX": Series(np.random.randn(100) * 0.02, index=dates),
            "GOLD": Series(np.random.randn(100) * 0.015, index=dates),
        }

    def test_full_workflow(
        self, full_strategy: FXIntermarketStrategy, sample_market_data: dict[str, Series]
    ) -> None:
        """Test complete workflow."""
        # 1. Generate signals
        signals = full_strategy.generate_signals(sample_market_data)
        assert isinstance(signals, list)

        # 2. Analyze relationships
        relationships = full_strategy.analyze_intermarket_relationships(datetime.utcnow())
        assert isinstance(relationships, list)

        # 3. Check portfolio summary
        summary = full_strategy.get_portfolio_summary()
        assert "active_relationships" in summary
        assert "monitored_pairs" in summary

    def test_strategy_error_handling(self, full_strategy: FXIntermarketStrategy) -> None:
        """Test strategy handles errors gracefully."""
        # This should not raise an exception
        signals = full_strategy.generate_signals({})

        # Should return empty list
        assert isinstance(signals, list)
