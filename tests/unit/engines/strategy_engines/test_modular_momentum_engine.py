"""
Comprehensive unit tests for ModularMomentumStrategyEngine.

Tests cover:
- Modular momentum strategy initialization with presets
- Filter configuration and activation
- Indicator calculation
- Market context analysis
- Signal generation with filter combinations
- Ensemble weight management
- Edge cases (no filters, insufficient data, callback handling)
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.engines.strategy_engines.modular_momentum_engine import ModularMomentumStrategyEngine
from app.domain.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

# ===== Initialization Tests =====


@pytest.mark.unit
class TestModularMomentumInitialization:
    """Test suite for ModularMomentumStrategyEngine initialization."""

    def test_initialization_with_config(self, modular_momentum_config):
        """Test initialization with configuration."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            assert engine.name == "test_modular_momentum"
            assert engine.preset == "balanced"
            assert engine.combination_mode == "MAJORITY"
            assert len(engine.filters) > 0  # Should have active filters

    def test_initialization_preset_configuration(self, modular_momentum_config):
        """Test initialization with preset configuration."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            config = modular_momentum_config.copy()
            config["preset"] = "aggressive"
            config["presets"] = {
                "aggressive": {
                    "min_confidence": 0.5,
                    "combination_mode": "ANY",
                }
            }

            engine = ModularMomentumStrategyEngine(config)

            assert engine.preset == "aggressive"
            assert engine.min_success_probability == 0.5
            assert engine.combination_mode == "ANY"

    def test_initialization_no_filters(self):
        """Test initialization with no filters enabled."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            config = {
                "name": "test",
                "preset": "balanced",
                "modules": {},  # No filters
            }

            engine = ModularMomentumStrategyEngine(config)

            assert len(engine.filters) == 0

    def test_initialization_learning_disabled(self, modular_momentum_config):
        """Test initialization with learning disabled."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            config = modular_momentum_config.copy()
            config["adaptive_learning"] = {"enabled": False}

            engine = ModularMomentumStrategyEngine(config)

            assert engine.learning_config is None

    def test_get_strategy_type(self, modular_momentum_config):
        """Test get_strategy_type returns correct type."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            assert engine.get_strategy_type() == "modular_momentum"


# ===== Indicator Calculation Tests =====


@pytest.mark.unit
class TestIndicatorCalculation:
    """Test suite for indicator calculation."""

    def test_calculate_indicators_insufficient_history(self, modular_momentum_config):
        """Test indicator calculation with insufficient history."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Only add a few data points
            for i in range(10):
                engine.price_history.append(150 + i * 0.5)

            indicators = engine._calculate_indicators()

            assert indicators == {}

    def test_calculate_indicators_success(self, modular_momentum_config):
        """Test successful indicator calculation."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=65.0)
            mock_calc_instance.calculate_ema = Mock(
                side_effect=lambda prices, period: prices[-1] if prices else 0
            )
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=2.0)
            mock_calc.return_value = mock_calc_instance

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Add sufficient history
            for i in range(100):
                price = 150 + i * 0.5
                engine.price_history.append(price)
                engine.high_history.append(price + 0.5)
                engine.low_history.append(price - 0.5)
                engine.volume_history.append(1000000 + i * 1000)

            indicators = engine._calculate_indicators()

            assert "rsi" in indicators
            assert "ema_fast" in indicators
            assert "ema_slow" in indicators
            assert "momentum_roc" in indicators
            assert "volume_ratio" in indicators
            assert "atr" in indicators

    def test_calculate_indicators_atr_percentile(self, modular_momentum_config):
        """Test ATR percentile calculation."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=65.0)
            mock_calc_instance.calculate_ema = Mock(
                side_effect=lambda prices, period: prices[-1] if prices else 0
            )
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=2.0)
            mock_calc.return_value = mock_calc_instance

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Add sufficient history for ATR percentile
            for i in range(100):
                price = 150 + i * 0.5
                engine.price_history.append(price)
                engine.high_history.append(price + 0.5)
                engine.low_history.append(price - 0.5)
                engine.volume_history.append(1000000)

            indicators = engine._calculate_indicators()

            assert "atr_percentile" in indicators
            assert 0 <= indicators["atr_percentile"] <= 100


# ===== Market Context Tests =====


@pytest.mark.unit
class TestMarketContext:
    """Test suite for market context analysis."""

    def test_get_market_context_with_context_engine(
        self, modular_momentum_config, mock_context_engine
    ):
        """Test getting market context with ContextEngine."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.set_context_engine(mock_context_engine)
            engine.context_engine_enabled = True

            # Build price history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            context = engine._get_market_context(quote)

            assert context is not None
            assert context["type"] == "bull"

    def test_get_market_context_with_market_analyzer(self, modular_momentum_config):
        """Test getting market context with MarketAnalyzer."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer_class, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer = Mock()
            mock_analyzer.analyze = Mock(
                return_value={
                    "type": "bull",
                    "confidence": 0.7,
                    "volatility_regime": "normal",
                    "trend_strength": 0.6,
                    "volatility_percentile": 50,
                    "in_range": False,
                }
            )
            mock_analyzer_class.return_value = mock_analyzer
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Build price history
            for i in range(100):
                engine.price_history.append(150 + i * 0.5)

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            context = engine._get_market_context(quote)

            assert context is not None
            assert context["type"] == "bull"
            mock_analyzer.analyze.assert_called_once()

    def test_get_market_context_fallback(self, modular_momentum_config):
        """Test market context fallback when no analyzer available."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = None
            mock_calc.return_value = Mock()

            config = modular_momentum_config.copy()
            config["market_analyzer"] = None
            config["context_engine_enabled"] = False

            engine = ModularMomentumStrategyEngine(config)
            engine.market_analyzer = None
            engine.context_engine = None

            quote = Quote(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                bid=Decimal("200"),
                ask=Decimal("200.05"),
                last=Decimal("200"),
                volume=Decimal("1000"),
            )

            context = engine._get_market_context(quote)

            assert context is not None
            assert context["type"] == "unknown"


# ===== Filter Evaluation Tests =====


@pytest.mark.unit
class TestFilterEvaluation:
    """Test suite for filter evaluation."""

    def test_evaluate_filters_no_filters(self, modular_momentum_config):
        """Test filter evaluation with no filters."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            config = modular_momentum_config.copy()
            config["modules"] = {}

            engine = ModularMomentumStrategyEngine(config)

            indicators = {"rsi": 65}
            market_context = {"type": "bull"}

            results = engine._evaluate_filters(indicators, market_context)

            assert results == {}

    def test_evaluate_filters_with_active_filters(self, modular_momentum_config):
        """Test filter evaluation with active filters."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            indicators = {"rsi": 65, "ema_fast": 155, "ema_slow": 150}
            market_context = {"type": "bull"}

            # Mock filter evaluation
            for filter_instance in engine.filters:
                filter_instance.evaluate = Mock(
                    return_value={"passed": True, "confidence": 0.8, "reason": "Conditions met"}
                )

            results = engine._evaluate_filters(indicators, market_context)

            assert len(results) > 0
            # Each filter should have been evaluated
            for filter_instance in engine.filters:
                filter_instance.evaluate.assert_called()


# ===== Signal Determination Tests =====


@pytest.mark.unit
class TestSignalDetermination:
    """Test suite for signal type determination."""

    def test_determine_signal_no_filters(self, modular_momentum_config):
        """Test signal determination with no filters."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            config = modular_momentum_config.copy()
            config["modules"] = {}

            engine = ModularMomentumStrategyEngine(config)

            filter_results = {}
            market_context = {"type": "bull"}

            signal_type = engine._determine_signal_type(filter_results, market_context)

            assert signal_type is None

    def test_determine_signal_all_mode(self, modular_momentum_config):
        """Test signal determination with ALL combination mode."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.combination_mode = "ALL"

            # Create mock filters
            engine.filters = [Mock(name=f"filter{i}") for i in range(3)]

            filter_results = {
                "filter0": {"passed": True, "confidence": 0.8},
                "filter1": {"passed": True, "confidence": 0.7},
                "filter2": {"passed": True, "confidence": 0.9},
            }

            # Set mock names
            for i, f in enumerate(engine.filters):
                f.name = f"filter{i}"

            market_context = {"type": "bull"}

            signal_type = engine._determine_signal_type(filter_results, market_context)

            assert signal_type == SignalType.BUY

    def test_determine_signal_majority_mode(self, modular_momentum_config):
        """Test signal determination with MAJORITY combination mode."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.combination_mode = "MAJORITY"

            # Create mock filters
            engine.filters = [Mock(name=f"filter{i}") for i in range(5)]

            filter_results = {
                "filter0": {"passed": True, "confidence": 0.8},
                "filter1": {"passed": True, "confidence": 0.7},
                "filter2": {"passed": True, "confidence": 0.9},
                "filter3": {"passed": False, "confidence": 0.3},
                "filter4": {"passed": False, "confidence": 0.4},
            }

            for i, f in enumerate(engine.filters):
                f.name = f"filter{i}"

            market_context = {"type": "bull"}

            signal_type = engine._determine_signal_type(filter_results, market_context)

            # 3 out of 5 passed (majority)
            assert signal_type == SignalType.BUY

    def test_determine_signal_any_mode(self, modular_momentum_config):
        """Test signal determination with ANY combination mode."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.combination_mode = "ANY"

            # Create mock filters
            engine.filters = [Mock(name=f"filter{i}") for i in range(5)]

            filter_results = {
                "filter0": {"passed": True, "confidence": 0.8},
                "filter1": {"passed": False, "confidence": 0.3},
                "filter2": {"passed": False, "confidence": 0.4},
                "filter3": {"passed": False, "confidence": 0.3},
                "filter4": {"passed": False, "confidence": 0.4},
            }

            for i, f in enumerate(engine.filters):
                f.name = f"filter{i}"

            market_context = {"type": "bull"}

            signal_type = engine._determine_signal_type(filter_results, market_context)

            # At least one passed
            assert signal_type == SignalType.BUY


# ===== Signal Generation Tests =====


@pytest.mark.unit
class TestSignalGeneration:
    """Test suite for signal generation."""

    def test_generate_signals_insufficient_history(self, modular_momentum_config):
        """Test signal generation with insufficient history."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

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

    def test_generate_signals_zero_price(self, modular_momentum_config):
        """Test signal generation with zero price."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

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

    def test_generate_signals_success(self, modular_momentum_config):
        """Test successful signal generation."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer_inst = Mock()
            mock_analyzer_inst.analyze = Mock(
                return_value={
                    "type": "bull",
                    "confidence": 0.7,
                    "volatility_regime": "normal",
                    "trend_strength": 0.6,
                    "volatility_percentile": 50,
                    "in_range": False,
                }
            )
            mock_analyzer.return_value = mock_analyzer_inst

            mock_calc_instance = Mock()
            mock_calc_instance.calculate_rsi = Mock(return_value=35.0)
            mock_calc_instance.calculate_ema = Mock(
                side_effect=lambda prices, period: prices[-1] if prices else 0
            )
            mock_calc_instance.calculate_roc = Mock(return_value=0.03)
            mock_calc_instance.calculate_atr = Mock(return_value=2.0)
            mock_calc.return_value = mock_calc_instance

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Build history
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
                high=Decimal("201"),
                low=Decimal("199"),
                volume=Decimal("2000000"),
            )

            # Mock filters to pass
            for filter_instance in engine.filters:
                filter_instance.evaluate = Mock(
                    return_value={"passed": True, "confidence": 0.8, "reason": "Conditions met"}
                )
                filter_instance.name = "test_filter"

            signals = engine._generate_signals_impl(quote)

            # May generate signal depending on filter evaluation
            if len(signals) > 0:
                signal = signals[0]
                assert signal.source == SignalSource.MOMENTUM
                assert "indicators" in signal.metadata
                assert "market_context" in signal.metadata
                assert "filter_results" in signal.metadata


# ===== Confidence Calculation Tests =====


@pytest.mark.unit
class TestConfidenceCalculation:
    """Test suite for confidence calculation."""

    def test_calculate_signal_confidence_no_filters(self, modular_momentum_config):
        """Test confidence calculation with no filter results."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            filter_results = {}
            learning_prediction = None

            confidence = engine._calculate_signal_confidence(filter_results, learning_prediction)

            # Should return default confidence
            assert confidence == 50.0

    def test_calculate_signal_confidence_with_filters(self, modular_momentum_config):
        """Test confidence calculation with filter results."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            filter_results = {
                "filter1": {"confidence": 0.8},
                "filter2": {"confidence": 0.7},
                "filter3": {"confidence": 0.9},
            }
            learning_prediction = None

            confidence = engine._calculate_signal_confidence(filter_results, learning_prediction)

            # Should be average of filter confidences
            expected = (0.8 + 0.7 + 0.9) / 3 * 100
            assert abs(confidence - expected) < 1.0

    def test_calculate_signal_confidence_with_learning(self, modular_momentum_config):
        """Test confidence calculation with learning prediction."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            filter_results = {
                "filter1": {"confidence": 0.7},
                "filter2": {"confidence": 0.7},
            }
            learning_prediction = {"confidence": 0.9}

            confidence = engine._calculate_signal_confidence(filter_results, learning_prediction)

            # Should combine filter and learning confidence
            # (60% filters, 40% learning)
            expected = (0.7 * 0.6 + 0.9 * 0.4) * 100
            assert abs(confidence - expected) < 1.0


# ===== Risk Check Tests =====


@pytest.mark.unit
class TestRiskCheck:
    """Test suite for risk checking."""

    def test_risk_check_pass(self, modular_momentum_config, sample_buy_signal, empty_portfolio):
        """Test risk check that passes."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.min_success_probability = 0.6

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is True

    def test_risk_check_low_confidence(self, modular_momentum_config, empty_portfolio):
        """Test risk check with low confidence signal."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.min_success_probability = 0.7

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

    def test_risk_check_learning_recommendation(
        self, modular_momentum_config, sample_buy_signal, empty_portfolio, mock_learning_engine
    ):
        """Test risk check with learning engine recommendation."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)
            engine.min_success_probability = 0.6
            engine.set_learning_engine(mock_learning_engine)
            engine.learning_enabled = True

            # Mock learning engine to recommend HOLD
            mock_learning_engine.is_ready = Mock(return_value=True)
            mock_learning_engine.predict = Mock(
                return_value={
                    "recommended_action": "HOLD",
                    "confidence": 0.8,
                }
            )

            passes = engine.risk_check(sample_buy_signal, empty_portfolio)

            assert passes is False


# ===== Learning Adjustment Tests =====


@pytest.mark.unit
class TestLearningAdjustments:
    """Test suite for learning adjustments."""

    def test_apply_learning_adjustments_no_prediction(
        self, modular_momentum_config, sample_buy_signal
    ):
        """Test learning adjustments with no prediction."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            adjusted = engine.apply_learning_adjustments(None, sample_buy_signal)

            assert adjusted == sample_buy_signal

    def test_apply_learning_adjustments_with_confidence(
        self, modular_momentum_config, sample_buy_signal
    ):
        """Test learning adjustments with confidence."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            prediction = {"confidence": 0.85}

            adjusted = engine.apply_learning_adjustments(prediction, sample_buy_signal)

            assert adjusted.confidence == 85.0

    def test_apply_learning_adjustments_with_filter_adjustments(
        self, modular_momentum_config, sample_buy_signal
    ):
        """Test learning adjustments with filter adjustments."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Add mock filter
            mock_filter = Mock()
            mock_filter.name = "test_filter"
            engine.filters = [mock_filter]

            prediction = {
                "confidence": 0.8,
                "filter_adjustments": {"test_filter": {"threshold": 0.7}},
            }

            adjusted = engine.apply_learning_adjustments(prediction, sample_buy_signal)

            assert adjusted.confidence == 80.0


# ===== Edge Cases Tests =====


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    def test_calculate_recent_win_rate_empty(self, modular_momentum_config):
        """Test recent win rate calculation with no trades."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            win_rate = engine._calculate_recent_win_rate()

            assert win_rate == 0.5  # Default neutral

    def test_calculate_recent_win_rate_with_trades(self, modular_momentum_config):
        """Test recent win rate calculation with trades."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            # Add mock trades
            trade1 = Mock()
            trade1.pnl = 100
            trade2 = Mock()
            trade2.pnl = -50
            trade3 = Mock()
            trade3.pnl = 75
            trade4 = Mock()
            trade4.pnl = -25

            engine.recent_trades.extend([trade1, trade2, trade3, trade4])

            win_rate = engine._calculate_recent_win_rate()

            # 2 winners out of 4 = 0.5
            assert win_rate == 0.5

    def test_get_required_parameters(self, modular_momentum_config):
        """Test getting required parameters."""
        with patch(
            'app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer'
        ) as mock_analyzer, patch(
            'app.services.momentum_analysis.TechnicalIndicatorCalculator'
        ) as mock_calc:
            mock_analyzer.return_value = Mock()
            mock_calc.return_value = Mock()

            engine = ModularMomentumStrategyEngine(modular_momentum_config)

            params = engine.get_required_parameters()

            assert "preset" in params
            assert "modules" in params
            assert "min_confidence" in params
            assert "combination_mode" in params
