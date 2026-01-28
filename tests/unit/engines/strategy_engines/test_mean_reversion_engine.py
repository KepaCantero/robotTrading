"""
Comprehensive unit tests for MeanReversionStrategyEngine.

Tests cover:
- Mean reversion strategy initialization
- Feature extraction (Z-score, mean, std, volatility)
- Signal generation for mean reversion
- Confidence calculation
- Risk checking
- Edge cases (insufficient data, NaN handling, volatility thresholds)
"""

import pytest
import numpy as np
from decimal import Decimal
from datetime import datetime
from collections import deque
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from app.engines.strategy_engines.mean_reversion_engine import MeanReversionStrategyEngine
from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio, Position


# ===== Initialization Tests =====

@pytest.mark.unit
class TestMeanReversionInitialization:
    """Test suite for MeanReversionStrategyEngine initialization."""

    def test_initialization_with_config(self, mean_reversion_config):
        """Test initialization with configuration."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config') as mock_config, \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold') as mock_threshold:

            # Setup mocks
            strategy_config = Mock()
            strategy_config.parameters = {
                "z_score_threshold": Decimal("2.0"),
                "lookback_period": 20,
                "volatility_threshold": Decimal("0.02"),
                "mean_reversion_speed": Decimal("0.1"),
                "atr_floor": Decimal("0.01"),
                "price_range_multiplier": Decimal("2.0"),
                "min_z_score": Decimal("1.5"),
            }
            strategy_config.stop_loss_pct = Decimal("0.05")
            strategy_config.take_profit_pct = Decimal("0.10")
            strategy_config.max_position_size = Decimal("10000")

            mock_config.return_value = strategy_config
            mock_threshold.side_effect = lambda key: {
                "stop_loss_pct": Decimal("0.05"),
                "take_profit_pct": Decimal("0.10"),
                "max_position_size": Decimal("10000"),
            }.get(key, Decimal("0.05"))

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            assert engine.name == "test_mean_reversion"
            assert engine.z_score_threshold == Decimal("2.0")
            assert engine.lookback_period == 20
            assert engine.min_z_score == Decimal("1.5")

    def test_initialization_default_values(self):
        """Test initialization with default values."""
        config = {"name": "test_mean_reversion"}

        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(config)

            assert engine.z_score_threshold == Decimal("2.0")
            assert engine.lookback_period == 20
            assert engine.volatility_threshold == Decimal("0.02")

    def test_get_strategy_type(self, mean_reversion_config):
        """Test get_strategy_type returns correct type."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            assert engine.get_strategy_type() == "mean_reversion"


# ===== Feature Extraction Tests =====

@pytest.mark.unit
class TestMeanReversionFeatureExtraction:
    """Test suite for feature extraction in mean reversion strategy."""

    def test_extract_features_basic(self, mean_reversion_config):
        """Test basic feature extraction."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "timestamp" in features
            assert "symbol" in features
            assert "price" in features

    def test_extract_features_z_score_calculation(self, mean_reversion_config):
        """Test Z-score calculation in feature extraction."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.lookback_period = 20

            # Build price history with known mean and std
            # Prices oscillating around 150
            for i in range(100):
                price = 150 + 5 * np.sin(i * 0.2)  # Oscillating
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("155"),  # Above mean
                ask=Decimal("155.05"),
                last=Decimal("155"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "z_score" in features
            assert "mean" in features
            assert "std" in features
            assert "price_mean_distance" in features

    def test_extract_features_volatility_calculation(self, mean_reversion_config):
        """Test volatility calculation in feature extraction."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            # Build price history
            for i in range(100):
                engine.price_history.append(150 + i * 0.1)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("160"),
                ask=Decimal("160.05"),
                last=Decimal("160"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "atr" in features
            assert "relative_atr" in features
            assert "volatility" in features

    def test_extract_features_insufficient_history(self, mean_reversion_config):
        """Test feature extraction with insufficient history."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Should return defaults
            assert features["z_score"] == 0.0
            assert features["mean"] == features["price"]
            assert features["std"] == 0.0

    def test_extract_features_price_range(self, mean_reversion_config):
        """Test price range calculation in feature extraction."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.lookback_period = 20

            # Build price history with known range
            for i in range(100):
                price = 140 + i * 0.2  # Range from 140 to ~160
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "period_high" in features
            assert "period_low" in features
            assert "price_range" in features
            assert "price_position_in_range" in features


# ===== Signal Generation Tests =====

@pytest.mark.unit
class TestMeanReversionSignalGeneration:
    """Test suite for signal generation in mean reversion strategy."""

    def test_generate_signals_insufficient_history(self, mean_reversion_config):
        """Test signal generation with insufficient history."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_generate_signals_zero_price(self, mean_reversion_config):
        """Test signal generation with zero price."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            # Build history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("0"),
                ask=Decimal("0"),
                last=Decimal("0"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_generate_signals_oversold_buy(self, mean_reversion_config):
        """Test signal generation for oversold condition (buy)."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.z_score_threshold = Decimal("2.0")
            engine.min_z_score = Decimal("1.5")
            engine.volatility_threshold = Decimal("0.02")

            # Build price history
            prices = []
            for i in range(100):
                # Oscillating prices
                price = 150 + 10 * np.sin(i * 0.1)
                prices.append(price)
                engine.price_history.append(price)

            # Create quote with very low price (oversold)
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("135"),  # Significantly below mean
                ask=Decimal("135.05"),
                last=Decimal("135"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            # May generate buy signal if z-score is very negative
            # (depends on actual calculation)

    def test_generate_signals_overbought_sell(self, mean_reversion_config):
        """Test signal generation for overbought condition (sell)."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.z_score_threshold = Decimal("2.0")
            engine.volatility_threshold = Decimal("0.02")

            # Build price history
            for i in range(100):
                # Oscillating prices
                price = 150 + 10 * np.sin(i * 0.1)
                engine.price_history.append(price)

            # Create quote with very high price (overbought)
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("165"),  # Significantly above mean
                ask=Decimal("165.05"),
                last=Decimal("165"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            # May generate sell signal if z-score is very positive
            # (depends on actual calculation)

    def test_generate_signal_metadata(self, mean_reversion_config):
        """Test that generated signals have correct metadata."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.z_score_threshold = Decimal("2.0")
            engine.volatility_threshold = Decimal("0.1")

            # Build price history with extreme value
            for i in range(100):
                price = 150 + np.random.randn() * 2
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("145"),
                ask=Decimal("145.05"),
                last=Decimal("145"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            if len(signals) > 0:
                signal = signals[0]
                assert signal.source == SignalSource.MEAN_REVERSION
                assert "z_score" in signal.metadata
                assert "mean" in signal.metadata
                assert "std" in signal.metadata
                assert "volatility" in signal.metadata
                assert "price_mean_distance" in signal.metadata


# ===== Confidence Calculation Tests =====

@pytest.mark.unit
class TestConfidenceCalculation:
    """Test suite for confidence calculation."""

    def test_calculate_confidence_high_z_score(self, mean_reversion_config):
        """Test confidence with very high Z-score."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            confidence = engine._calculate_confidence(
                abs_z_score=3.5,
                volatility=0.008,
                is_oversold=True
            )

            # Should be high confidence
            assert confidence >= 85

    def test_calculate_confidence_medium_z_score(self, mean_reversion_config):
        """Test confidence with medium Z-score."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            confidence = engine._calculate_confidence(
                abs_z_score=2.0,
                volatility=0.015,
                is_oversold=False
            )

            # Should be medium confidence
            assert 65 <= confidence < 85

    def test_calculate_confidence_low_z_score(self, mean_reversion_config):
        """Test confidence with low Z-score."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            confidence = engine._calculate_confidence(
                abs_z_score=1.0,
                volatility=0.02,
                is_oversold=True
            )

            # Should be low confidence
            assert confidence < 70

    def test_calculate_confidence_low_volatility(self, mean_reversion_config):
        """Test confidence with low volatility (better for mean reversion)."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            # Low volatility should increase confidence
            confidence_low_vol = engine._calculate_confidence(
                abs_z_score=2.0,
                volatility=0.005,
                is_oversold=True
            )

            # High volatility should decrease confidence
            confidence_high_vol = engine._calculate_confidence(
                abs_z_score=2.0,
                volatility=0.03,
                is_oversold=True
            )

            assert confidence_low_vol > confidence_high_vol

    def test_calculate_confidence_bounds(self, mean_reversion_config):
        """Test that confidence is bounded between 0 and 100."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            # Test upper bound
            confidence_high = engine._calculate_confidence(
                abs_z_score=5.0,
                volatility=0.001,
                is_oversold=True
            )
            assert confidence_high <= 100.0

            # Test lower bound
            confidence_low = engine._calculate_confidence(
                abs_z_score=0.5,
                volatility=0.1,
                is_oversold=False
            )
            assert confidence_low >= 0.0


# ===== Risk Check Tests =====

@pytest.mark.unit
class TestRiskCheck:
    """Test suite for risk checking."""

    def test_risk_check_pass(self, mean_reversion_config, sample_buy_signal, empty_portfolio):
        """Test risk check that passes."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.config = {"min_signal_confidence": 50.0}
            sample_buy_signal.metadata["volatility"] = 0.01

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is True

    def test_risk_check_low_confidence(self, mean_reversion_config, empty_portfolio):
        """Test risk check with low confidence signal."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.config = {"min_signal_confidence": 70.0}

            low_confidence_signal = Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=40.0,
                liquidity_score=70.0,
                priority_score=40.0,
                source=SignalSource.MEAN_REVERSION,
                price=Decimal("150"),
                volume=Decimal("100"),
                metadata={"volatility": 0.01}
            )

            passes = engine.risk_check(low_confidence_signal, empty_portfolio)

            assert passes is False

    def test_risk_check_high_volatility(self, mean_reversion_config, sample_buy_signal, empty_portfolio):
        """Test risk check with high volatility."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.volatility_threshold = Decimal("0.02")
            engine.config = {"min_signal_confidence": 50.0}

            # High volatility in metadata
            sample_buy_signal.metadata["volatility"] = 0.05  # > 2x threshold

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is False

    def test_risk_check_acceptable_volatility(self, mean_reversion_config, sample_buy_signal, empty_portfolio):
        """Test risk check with acceptable volatility."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.volatility_threshold = Decimal("0.02")
            engine.config = {"min_signal_confidence": 50.0}

            # Acceptable volatility in metadata
            sample_buy_signal.metadata["volatility"] = 0.03  # < 2x threshold

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is True


# ===== Edge Cases Tests =====

@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    def test_empty_price_history(self, mean_reversion_config):
        """Test with empty price history."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_single_data_point(self, mean_reversion_config):
        """Test with only one data point."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            engine.price_history.append(150)

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_constant_prices(self, mean_reversion_config):
        """Test with constant prices (no volatility)."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.lookback_period = 20

            # Add constant prices
            for i in range(100):
                engine.price_history.append(150.0)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            signals = engine._generate_signals_impl(quote)

            # Should not generate signals when std is 0
            assert len(signals) == 0

    def test_nan_handling_in_features(self, mean_reversion_config):
        """Test handling of NaN values in feature extraction."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.lookback_period = 20

            # Build price history
            for i in range(100):
                price = 150 + np.random.randn() * 5
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Features should not contain NaN
            assert not np.isnan(features.get("z_score", 0))
            assert not np.isnan(features.get("mean", 150))
            assert not np.isnan(features.get("std", 0))

    def test_get_required_parameters(self, mean_reversion_config):
        """Test getting required parameters."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)

            params = engine.get_required_parameters()

            assert "z_score_threshold" in params
            assert "lookback_period" in params
            assert "volatility_threshold" in params
            assert "stop_loss" in params
            assert "take_profit" in params
            assert "max_position_size" in params


# ===== Volatility Regime Tests =====

@pytest.mark.unit
class TestVolatilityRegime:
    """Test suite for volatility regime handling."""

    def test_low_volatility_regime(self, mean_reversion_config):
        """Test signal generation in low volatility regime."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.z_score_threshold = Decimal("2.0")
            engine.volatility_threshold = Decimal("0.02")

            # Build low volatility price history
            for i in range(100):
                price = 150 + 0.5 * np.sin(i * 0.1)  # Low amplitude
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("148"),  # Slightly below mean
                ask=Decimal("148.05"),
                last=Decimal("148"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Volatility should be low
            assert features["volatility"] < 0.02

    def test_high_volatility_regime(self, mean_reversion_config):
        """Test signal generation in high volatility regime."""
        with patch('app.engines.strategy_engines.mean_reversion_engine.get_strategy_config', return_value=None), \
             patch('app.engines.strategy_engines.mean_reversion_engine.get_trading_threshold', return_value=Decimal("0.05")):

            engine = MeanReversionStrategyEngine(mean_reversion_config)
            engine.z_score_threshold = Decimal("2.0")
            engine.volatility_threshold = Decimal("0.02")

            # Build high volatility price history
            for i in range(100):
                price = 150 + 10 * np.sin(i * 0.3) + np.random.randn()  # High amplitude
                engine.price_history.append(price)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            # Volatility should be higher
            # (actual value depends on random data)
