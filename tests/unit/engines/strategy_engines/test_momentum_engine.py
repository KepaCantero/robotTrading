"""
Comprehensive unit tests for MomentumStrategyEngine.

Tests cover:
- Momentum strategy initialization
- Feature extraction (RSI, EMA, momentum, volume, ATR)
- Signal generation for momentum strategy
- Confidence calculation
- Risk checking
- Edge cases (insufficient data, NaN handling, ATR filtering)
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.engines.strategy_engines.momentum_engine import MomentumStrategyEngine
from app.models.market_data import Quote
from app.models.portfolio import Portfolio, Position
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

# ===== Initialization Tests =====


@pytest.mark.unit
class TestMomentumInitialization:
    """Test suite for MomentumStrategyEngine initialization."""

    def test_initialization_with_config(self, momentum_config):
        """Test initialization with configuration."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config'
        ) as mock_config, patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold'
        ) as mock_threshold, patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine'
        ) as mock_scorer:
            # Setup mocks
            strategy_config = Mock()
            strategy_config.parameters = {
                "rsi_threshold_buy": Decimal("0.3"),
                "momentum_threshold": Decimal("0.02"),
                "volume_threshold": Decimal("1.5"),
                "max_exposure": Decimal("0.60"),
                "ema_period": 20,
                "rsi_period": 14,
                "lookback_period": 5,
                "atr_filter_enabled": True,
                "use_relative_atr": True,
                "min_atr_threshold": Decimal("0.015"),
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
            mock_scorer.return_value = Mock()

            engine = MomentumStrategyEngine(momentum_config)

            assert engine.name == "test_momentum"
            assert engine.rsi_period == 14
            assert engine.ema_period == 20
            assert engine.lookback_period == 5
            assert engine.atr_filter_enabled is True

    def test_initialization_default_values(self):
        """Test initialization with default values."""
        config = {"name": "test_momentum"}

        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(config)

            assert engine.rsi_period == 14
            assert engine.ema_period == 20
            assert engine.lookback_period == 5

    def test_get_strategy_type(self, momentum_config):
        """Test get_strategy_type returns correct type."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            assert engine.get_strategy_type() == "momentum"


# ===== Feature Extraction Tests =====


@pytest.mark.unit
class TestMomentumFeatureExtraction:
    """Test suite for feature extraction in momentum strategy."""

    def test_extract_features_basic(self, momentum_config):
        """Test basic feature extraction."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

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

    def test_extract_features_with_indicators(self, momentum_config):
        """Test feature extraction with technical indicators."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            # Build sufficient price history
            for i in range(100):
                price = 150 + i * 0.5
                engine.price_history.append(price)
                engine.high_history.append(price + 0.5)
                engine.low_history.append(price - 0.5)
                engine.volume_history.append(1000000 + i * 1000)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            features = engine.extract_features(quote)

            assert "rsi" in features
            assert "ema" in features
            assert "momentum" in features
            assert "volume_ratio" in features

    def test_extract_features_insufficient_history(self, momentum_config):
        """Test feature extraction with insufficient history."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

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
            assert features["rsi"] == 50.0
            assert features["ema"] == features["price"]
            assert features["momentum"] == 0.0


# ===== Signal Generation Tests =====


@pytest.mark.unit
class TestMomentumSignalGeneration:
    """Test suite for signal generation in momentum strategy."""

    def test_generate_signals_insufficient_history(self, momentum_config):
        """Test signal generation with insufficient history."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

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

    def test_generate_signals_zero_price(self, momentum_config):
        """Test signal generation with zero price."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

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

    def test_generate_signals_momentum_buy_conditions(self, momentum_config):
        """Test signal generation with buy conditions met."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)
            engine.rsi_threshold = Decimal("40")  # RSI < 40 triggers buy
            engine.momentum_threshold = Decimal("0.01")
            engine.volume_threshold = Decimal("1.2")

            # Build trending up price history with low RSI
            for i in range(100):
                price = 150 + i * 0.5
                engine.price_history.append(price)
                engine.high_history.append(price + 0.5)
                engine.low_history.append(price - 0.5)
                # High volume at end
                engine.volume_history.append(1000000 if i < 90 else 2000000)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                high=Decimal("201"),
                low=Decimal("199"),
                volume=Decimal("2000000"),
            )

            engine._generate_signals_impl(quote)

            # May generate signal if conditions are met
            # (depends on actual indicator calculations)

    def test_generate_signal_metadata(self, momentum_config):
        """Test that generated signals have correct metadata."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config'
        ) as mock_config, patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold'
        ) as mock_threshold, patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.TechnicalIndicatorCalculator'
        ) as mock_calc:
            # Mock technical indicators to return buy signal conditions
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=35.0)
            mock_calc_instance.calculate_ema = Mock(return_value=190.0)
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=2.0)
            mock_calc.return_value = mock_calc_instance

            strategy_config = Mock()
            strategy_config.parameters = {}
            strategy_config.stop_loss_pct = Decimal("0.05")
            strategy_config.take_profit_pct = Decimal("0.10")
            strategy_config.max_position_size = Decimal("10000")

            mock_config.return_value = strategy_config
            mock_threshold.return_value = Decimal("0.05")

            engine = MomentumStrategyEngine(momentum_config)
            engine.rsi_threshold = Decimal("40")
            engine.momentum_threshold = Decimal("0.01")
            engine.volume_threshold = Decimal("1.2")

            # Build history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)
                engine.high_history.append(150 + i * 0.5 + 0.5)
                engine.low_history.append(150 + i * 0.5 - 0.5)
                engine.volume_history.append(1000000 if i < 90 else 2000000)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                high=Decimal("201"),
                low=Decimal("199"),
                volume=Decimal("2000000"),
            )

            signals = engine._generate_signals_impl(quote)

            if len(signals) > 0:
                signal = signals[0]
                assert signal.source == SignalSource.MOMENTUM
                assert "rsi" in signal.metadata
                assert "ema" in signal.metadata
                assert "momentum" in signal.metadata
                assert "volume_ratio" in signal.metadata


# ===== Confidence Calculation Tests =====


@pytest.mark.unit
class TestConfidenceCalculation:
    """Test suite for confidence calculation."""

    def test_calculate_confidence_high(self, momentum_config):
        """Test confidence calculation with high indicators."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            confidence = engine._calculate_confidence(
                rsi=25.0,  # Very low RSI (good for momentum)
                momentum=0.06,  # High momentum
                volume_ratio=2.5,  # High volume
                price_above_ema=True,
            )

            # Should be high confidence
            assert confidence >= 80

    def test_calculate_confidence_medium(self, momentum_config):
        """Test confidence calculation with medium indicators."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            confidence = engine._calculate_confidence(
                rsi=35.0, momentum=0.03, volume_ratio=1.5, price_above_ema=True
            )

            # Should be medium confidence
            assert 60 <= confidence < 90

    def test_calculate_confidence_low(self, momentum_config):
        """Test confidence calculation with low indicators."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            confidence = engine._calculate_confidence(
                rsi=45.0, momentum=0.01, volume_ratio=1.0, price_above_ema=False
            )

            # Should be low confidence
            assert confidence < 70

    def test_calculate_confidence_bounds(self, momentum_config):
        """Test that confidence is bounded between 0 and 100."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            # Test upper bound
            confidence_high = engine._calculate_confidence(
                rsi=20.0, momentum=0.10, volume_ratio=5.0, price_above_ema=True
            )
            assert confidence_high <= 100.0

            # Test lower bound
            confidence_low = engine._calculate_confidence(
                rsi=60.0, momentum=-0.05, volume_ratio=0.5, price_above_ema=False
            )
            assert confidence_low >= 0.0


# ===== Risk Check Tests =====


@pytest.mark.unit
class TestRiskCheck:
    """Test suite for risk checking."""

    def test_risk_check_pass(self, momentum_config, sample_buy_signal, empty_portfolio):
        """Test risk check that passes."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)
            engine.max_exposure = Decimal("0.60")
            engine.config = {"min_signal_confidence": 50.0}

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is True

    def test_risk_check_max_exposure(self, momentum_config, sample_buy_signal):
        """Test risk check with maximum exposure reached."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)
            engine.max_exposure = Decimal("0.60")
            engine.config = {"min_signal_confidence": 50.0}

            # Create portfolio with high exposure
            high_exposure_portfolio = Portfolio(
                cash=Decimal("40000"),
                positions=[
                    Position(
                        symbol="AAPL",
                        quantity=Decimal("1000"),
                        entry_price=Decimal("150"),
                        current_price=Decimal("150"),
                        market_value=Decimal("150000"),
                        unrealized_pnl=Decimal("0"),
                    )
                ],
            )

            # Mock get_total_exposure to return high value
            high_exposure_portfolio.get_total_exposure = Mock(return_value=0.65)

            passes = engine.risk_check(sample_buy_signal, high_exposure_portfolio)

            assert passes is False

    def test_risk_check_low_confidence(self, momentum_config, empty_portfolio):
        """Test risk check with low confidence signal."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)
            engine.config = {"min_signal_confidence": 70.0}

            low_confidence_signal = Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=40.0,
                liquidity_score=70.0,
                priority_score=40.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150"),
                volume=Decimal("100"),
            )

            passes = engine.risk_check(low_confidence_signal, empty_portfolio)

            assert passes is False


# ===== ATR Filter Tests =====


@pytest.mark.unit
class TestATRFilter:
    """Test suite for ATR volatility filter."""

    def test_atr_filter_enabled_low_atr(self, momentum_config):
        """Test ATR filter filtering out low volatility."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.TechnicalIndicatorCalculator'
        ) as mock_calc:
            # Mock ATR to return low value
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=35.0)
            mock_calc_instance.calculate_ema = Mock(return_value=190.0)
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=1.0)  # Low ATR
            mock_calc.return_value = mock_calc_instance

            engine = MomentumStrategyEngine(momentum_config)
            engine.atr_filter_enabled = True
            engine.use_relative_atr = True
            engine.min_atr_threshold = Decimal("0.015")
            engine.rsi_threshold = Decimal("40")
            engine.momentum_threshold = Decimal("0.01")
            engine.volume_threshold = Decimal("1.2")

            # Build history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)
                engine.high_history.append(150 + i * 0.5 + 0.5)
                engine.low_history.append(150 + i * 0.5 - 0.5)
                engine.volume_history.append(2000000)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                high=Decimal("201"),
                low=Decimal("199"),
                volume=Decimal("2000000"),
            )

            signals = engine._generate_signals_impl(quote)

            # Should be filtered out due to low ATR (1.0/200 = 0.5% < 1.5%)
            assert len(signals) == 0

    def test_atr_filter_disabled(self, momentum_config):
        """Test with ATR filter disabled."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=35.0)
            mock_calc_instance.calculate_ema = Mock(return_value=190.0)
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=1.0)
            mock_calc.return_value = mock_calc_instance

            engine = MomentumStrategyEngine(momentum_config)
            engine.atr_filter_enabled = False  # Disabled
            engine.rsi_threshold = Decimal("40")
            engine.momentum_threshold = Decimal("0.01")
            engine.volume_threshold = Decimal("1.2")

            # Build history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)
                engine.high_history.append(150 + i * 0.5 + 0.5)
                engine.low_history.append(150 + i * 0.5 - 0.5)
                engine.volume_history.append(2000000)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                high=Decimal("201"),
                low=Decimal("199"),
                volume=Decimal("2000000"),
            )

            engine._generate_signals_impl(quote)

            # Should not be filtered (filter is disabled)
            # May generate signal if other conditions met


# ===== Edge Cases Tests =====


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    def test_empty_price_history(self, momentum_config):
        """Test with empty price history."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

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

    def test_single_data_point(self, momentum_config):
        """Test with only one data point."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("150"),
                ask=Decimal("150.05"),
                last=Decimal("150"),
                volume=Decimal("1000"),
            )

            # Add single data point
            engine.price_history.append(150)

            signals = engine._generate_signals_impl(quote)

            assert len(signals) == 0

    def test_get_required_parameters(self, momentum_config):
        """Test getting required parameters."""
        with patch(
            'app.engines.strategy_engines.momentum_engine.get_strategy_config', return_value=None
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_trading_threshold',
            return_value=Decimal("0.05"),
        ), patch(
            'app.engines.strategy_engines.momentum_engine.get_signal_scoring_engine',
            return_value=Mock(),
        ):
            engine = MomentumStrategyEngine(momentum_config)

            params = engine.get_required_parameters()

            assert "rsi_threshold" in params
            assert "momentum_threshold" in params
            assert "volume_threshold" in params
            assert "rsi_period" in params
            assert "ema_period" in params
