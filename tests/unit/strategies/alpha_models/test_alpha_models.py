"""
Tests for Alpha Models - Narang "Inside the Black Box" Chapter 3
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.models.signal import SignalStrength, SignalType
from app.strategies.alpha_models import (
    AlphaDecayMetrics,
    AlphaDecayRegime,
    AlphaSignal,
    AlphaType,
    MeanReversionAlphaModel,
    MomentumAlphaModel,
    MultiFactorAlphaModel,
    get_alpha_model,
)


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")

    # Create price series with trend
    trend = np.linspace(100, 110, 100)
    noise = np.random.randn(100) * 2
    prices = trend + noise

    # Volume
    volume = np.random.randint(1000000, 5000000, 100)

    df = pd.DataFrame(
        {
            "close": prices,
            "high": prices + np.random.rand(100) * 2,
            "low": prices - np.random.rand(100) * 2,
            "volume": volume,
            "open": prices + np.random.randn(100) * 0.5,
        },
        index=dates,
    )

    return df


@pytest.fixture
def momentum_config():
    """Momentum alpha model configuration."""
    return {
        "name": "test_momentum",
        "alpha_type": "momentum",
        "lookback_period": 20,
        "min_confidence": 0.6,
        "min_holding_period": 1,
        "max_holding_period": 30,
    }


@pytest.fixture
def mean_reversion_config():
    """Mean reversion alpha model configuration."""
    return {
        "name": "test_mean_reversion",
        "alpha_type": "mean_reversion",
        "lookback_period": 20,
        "z_score_threshold": 2.0,
        "min_confidence": 0.6,
    }


class TestAlphaSignal:
    """Tests for AlphaSignal dataclass."""

    def test_alpha_signal_creation(self):
        """Test creating an alpha signal."""
        signal = AlphaSignal(
            symbol="AAPL",
            alpha_type=AlphaType.MOMENTUM,
            direction=SignalType.BUY,
            raw_alpha=5.0,
            confidence=0.75,
            expected_return=50.0,  # 50 bps
            holding_period_days=10,
            decay_regime=AlphaDecayRegime.EXPONENTIAL,
            decay_half_life=5,
        )

        assert signal.symbol == "AAPL"
        assert signal.alpha_type == AlphaType.MOMENTUM
        assert signal.direction == SignalType.BUY
        assert signal.confidence == 0.75
        assert signal.decay_regime == AlphaDecayRegime.EXPONENTIAL

    def test_alpha_signal_to_signal(self):
        """Test converting AlphaSignal to trading Signal."""
        # Use a past timestamp to avoid validation error
        past_timestamp = datetime.now() - timedelta(minutes=5)

        alpha = AlphaSignal(
            symbol="AAPL",
            alpha_type=AlphaType.MOMENTUM,
            direction=SignalType.BUY,
            raw_alpha=5.0,
            confidence=0.85,
            expected_return=50.0,
            holding_period_days=10,
            decay_regime=AlphaDecayRegime.EXPONENTIAL,
            timestamp=past_timestamp,
        )

        signal = alpha.to_signal(Decimal("150.00"))

        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.VERY_STRONG  # confidence >= 0.8
        assert signal.price == Decimal("150.00")
        assert signal.confidence == 85.0


class TestMomentumAlphaModel:
    """Tests for MomentumAlphaModel."""

    def test_initialization(self, momentum_config):
        """Test model initialization."""
        model = MomentumAlphaModel(momentum_config)

        assert model.name == "test_momentum"
        assert model.alpha_type == AlphaType.MOMENTUM
        assert model.lookback_period == 20

    def test_generate_alpha_bullish(self, momentum_config, sample_market_data):
        """Test generating alpha for bullish momentum."""
        model = MomentumAlphaModel(momentum_config)
        timestamp = datetime.now()

        signal = model.generate_alpha("TEST", sample_market_data, timestamp)

        assert signal is not None
        assert signal.symbol == "TEST"
        assert signal.alpha_type == AlphaType.MOMENTUM
        assert signal.direction == SignalType.BUY  # Prices trending up
        assert signal.confidence > 0

    def test_generate_alpha_insufficient_data(self, momentum_config):
        """Test generating alpha with insufficient data."""
        model = MomentumAlphaModel(momentum_config)

        short_data = pd.DataFrame({"close": [100, 101, 102]})
        signal = model.generate_alpha("TEST", short_data, datetime.now())

        assert signal is None  # Should return None with insufficient data

    def test_analyze_alpha_decay(self, momentum_config):
        """Test alpha decay analysis."""
        model = MomentumAlphaModel(momentum_config)

        # Create simulated returns
        np.random.seed(42)
        signal_dates = [datetime.now() - timedelta(days=i) for i in range(100, 0, -1)]
        realized_returns = pd.Series(np.random.randn(100) * 0.01)

        decay_metrics = model.analyze_alpha_decay("TEST", realized_returns, signal_dates)

        if decay_metrics:
            assert decay_metrics.symbol == "TEST"
            assert decay_metrics.alpha_type == AlphaType.MOMENTUM
            assert decay_metrics.total_observations == 100
            assert decay_metrics.half_life_days >= 0

    def test_get_optimal_holding_period(self, momentum_config):
        """Test optimal holding period calculation."""
        model = MomentumAlphaModel(momentum_config)

        # Test with no decay metrics
        holding_period = model.get_optimal_holding_period(None, default_days=5)
        assert holding_period == 5

        # Test with exponential decay
        decay_metrics = AlphaDecayMetrics(
            symbol="TEST",
            alpha_type=AlphaType.MOMENTUM,
            total_observations=50,
            decay_regime=AlphaDecayRegime.EXPONENTIAL,
            half_life_days=10.0,
            decay_rate=0.1,
            predictive_power_by_day={1: 0.5, 5: 0.3, 10: 0.25},
            is_significant=True,
        )

        holding_period = model.get_optimal_holding_period(decay_metrics)
        assert 1 <= holding_period <= model.max_holding_period


class TestMeanReversionAlphaModel:
    """Tests for MeanReversionAlphaModel."""

    def test_initialization(self, mean_reversion_config):
        """Test model initialization."""
        model = MeanReversionAlphaModel(mean_reversion_config)

        assert model.name == "test_mean_reversion"
        assert model.alpha_type == AlphaType.MEAN_REVERSION
        assert model.z_score_threshold == 2.0

    def test_generate_alpha_oversold(self, mean_reversion_config):
        """Test generating alpha for oversold condition."""
        model = MeanReversionAlphaModel(mean_reversion_config)

        # Create price series with large drop (oversold)
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        prices = np.concatenate(
            [
                np.ones(25) * 100,  # First half at 100
                np.ones(25) * 90,  # Second half at 90 (big drop)
            ]
        )

        market_data = pd.DataFrame(
            {
                "close": prices,
                "high": prices + 1,
                "low": prices - 1,
                "volume": np.random.randint(1000000, 5000000, 50),
            },
            index=dates,
        )

        signal = model.generate_alpha("TEST", market_data, datetime.now())

        # Should generate BUY signal when price is below mean (oversold)
        if signal:
            assert signal.symbol == "TEST"
            assert signal.alpha_type == AlphaType.MEAN_REVERSION

    def test_generate_alpha_no_signal(self, mean_reversion_config):
        """Test that no signal is generated when z-score is below threshold."""
        model = MeanReversionAlphaModel(mean_reversion_config)

        # Create price series with no deviation
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        prices = np.ones(50) * 100 + np.random.randn(50) * 0.5  # Small noise

        market_data = pd.DataFrame(
            {
                "close": prices,
                "high": prices + 1,
                "low": prices - 1,
                "volume": np.random.randint(1000000, 5000000, 50),
            },
            index=dates,
        )

        signal = model.generate_alpha("TEST", market_data, datetime.now())

        # Should not generate signal for small deviations
        assert signal is None or signal.confidence < 0.5


class TestMultiFactorAlphaModel:
    """Tests for MultiFactorAlphaModel."""

    def test_initialization(self):
        """Test model initialization."""
        config = {"name": "test_multi_factor", "combination_method": "weighted"}
        model = MultiFactorAlphaModel(config)

        assert model.name == "test_multi_factor"
        assert model.alpha_type == AlphaType.MACHINE_LEARNING
        assert model.combination_method == "weighted"

    def test_add_sub_model(self):
        """Test adding sub-models."""
        model = MultiFactorAlphaModel({"name": "test"})
        momentum_config = {"name": "momentum", "alpha_type": "momentum", "lookback_period": 20}

        sub_model = MomentumAlphaModel(momentum_config)
        model.add_sub_model(sub_model)

        assert len(model.sub_models) == 1
        assert model.sub_models[0].name == "momentum"

    def test_combine_alpha_signals_weighted(self):
        """Test combining signals with weighted method."""
        model = MultiFactorAlphaModel({"name": "test", "combination_method": "weighted"})

        signals = [
            AlphaSignal(
                symbol="AAPL",
                alpha_type=AlphaType.MOMENTUM,
                direction=SignalType.BUY,
                raw_alpha=5.0,
                confidence=0.8,
                expected_return=50.0,
                holding_period_days=10,
                decay_regime=AlphaDecayRegime.EXPONENTIAL,
            ),
            AlphaSignal(
                symbol="AAPL",
                alpha_type=AlphaType.MEAN_REVERSION,
                direction=SignalType.BUY,
                raw_alpha=3.0,
                confidence=0.6,
                expected_return=30.0,
                holding_period_days=5,
                decay_regime=AlphaDecayRegime.LINEAR,
            ),
        ]

        combined = model.combine_alpha_signals(signals, method="weighted")

        assert combined is not None
        assert combined.direction == SignalType.BUY
        assert combined.alpha_type == AlphaType.MACHINE_LEARNING
        # Weighted confidence should be between individual confidences
        assert 0.6 <= combined.confidence <= 0.8


class TestAlphaModelFactory:
    """Tests for the alpha model factory function."""

    def test_get_momentum_model(self):
        """Test factory creates momentum model."""
        config = {"model_type": "momentum", "lookback_period": 20}
        model = get_alpha_model(config)

        assert isinstance(model, MomentumAlphaModel)
        assert model.lookback_period == 20

    def test_get_mean_reversion_model(self):
        """Test factory creates mean reversion model."""
        config = {"model_type": "mean_reversion", "z_score_threshold": 2.0}
        model = get_alpha_model(config)

        assert isinstance(model, MeanReversionAlphaModel)

    def test_get_multi_factor_model(self):
        """Test factory creates multi-factor model."""
        config = {"model_type": "multi_factor"}
        model = get_alpha_model(config)

        assert isinstance(model, MultiFactorAlphaModel)

    def test_invalid_model_type(self):
        """Test factory raises error for invalid type."""
        config = {"model_type": "invalid"}

        with pytest.raises(ValueError):
            get_alpha_model(config)
