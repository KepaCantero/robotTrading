"""
Comprehensive unit tests for BaseStrategyEngine.

Tests cover:
- Abstract method enforcement
- Learning engine integration
- Callback registration and triggering
- Ensemble weight management
- Context/Data/Portfolio/Risk engine integration
- Metrics tracking
- Feature extraction interface
- Signal generation wrapper
"""

import pytest
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch, call

from app.engines.strategy_engines.base import BaseStrategyEngine
from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio


# ===== Concrete Implementation for Testing =====


class ConcreteStrategyEngine(BaseStrategyEngine):
    """Concrete implementation of BaseStrategyEngine for testing."""

    def get_strategy_type(self) -> str:
        return "test_strategy"

    def extract_features(self, market_data: Quote, historical_data: List = None) -> Dict[str, Any]:
        return {
            "timestamp": market_data.timestamp,
            "symbol": market_data.symbol,
            "price": float(market_data.close),
        }

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        # Simple implementation: generate a BUY signal if price > 100
        if float(market_data.close) > 100:
            return [
                Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=60.0,
                    liquidity_score=70.0,
                    priority_score=64.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.close,
                    volume=Decimal("100"),
                    timestamp=market_data.timestamp,
                )
            ]
        return []


# ===== Initialization Tests =====


@pytest.mark.unit
class TestBaseStrategyEngineInitialization:
    """Test suite for BaseStrategyEngine initialization."""

    def test_initialization_with_minimal_config(self, sample_quote):
        """Test engine initialization with minimal configuration."""
        config = {
            "name": "test_engine",
            "enabled": True,
        }

        engine = ConcreteStrategyEngine(config)

        assert engine.name == "test_engine"
        assert engine.is_active is True
        assert engine.learning_enabled is False
        assert engine.learning_engine is None
        assert engine.data_engine is None
        assert engine.context_engine is None
        assert engine.portfolio_engine is None
        assert engine.risk_engine is None

    def test_initialization_with_learning_enabled(self, sample_quote):
        """Test engine initialization with learning enabled."""
        config = {
            "name": "test_engine",
            "learning_enabled": True,
            "learning_engine": {"type": "supervised"},
        }

        engine = ConcreteStrategyEngine(config)

        assert engine.learning_enabled is True
        assert engine.learning_config == {"type": "supervised"}

    def test_initialization_with_engines_disabled(self, sample_quote):
        """Test engine initialization with all optional engines disabled."""
        config = {
            "name": "test_engine",
            "data_engine_enabled": False,
            "context_engine_enabled": False,
            "portfolio_engine_enabled": False,
            "risk_engine_enabled": False,
        }

        engine = ConcreteStrategyEngine(config)

        assert engine.data_engine is None
        assert engine.context_engine is None
        assert engine.portfolio_engine is None
        assert engine.risk_engine is None

    def test_initialization_callbacks_empty(self, sample_quote):
        """Test that callbacks are initialized as empty lists."""
        config = {"name": "test_engine"}

        engine = ConcreteStrategyEngine(config)

        assert engine.on_signal_generated_callbacks == []
        assert engine.on_trade_executed_callbacks == []
        assert engine.on_market_data_callbacks == []

    def test_initialization_metrics(self, sample_quote):
        """Test that metrics are initialized correctly."""
        config = {"name": "test_engine"}

        engine = ConcreteStrategyEngine(config)

        assert engine.metrics["signals_generated"] == 0
        assert engine.metrics["trades_executed"] == 0
        assert engine.metrics["learning_adjustments_applied"] == 0
        assert engine.metrics["context_analysis_calls"] == 0
        assert engine.metrics["data_engine_calls"] == 0
        assert engine.metrics["last_update"] is None

    def test_ensemble_weight_initialization(self, sample_quote):
        """Test that ensemble weight is initialized correctly."""
        config = {"name": "test_engine"}

        engine = ConcreteStrategyEngine(config)

        assert engine.ensemble_weight == Decimal("1.0")
        assert engine.is_ensemble_component is False


# ===== Learning Engine Integration Tests =====


@pytest.mark.unit
class TestLearningEngineIntegration:
    """Test suite for learning engine integration."""

    def test_set_learning_engine(self, sample_quote, mock_learning_engine):
        """Test setting learning engine."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_learning_engine(mock_learning_engine)

        assert engine.learning_engine == mock_learning_engine
        assert engine.learning_enabled is True

    def test_set_learning_engine_none(self, sample_quote):
        """Test setting learning engine to None."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.learning_enabled = True

        engine.set_learning_engine(None)

        assert engine.learning_engine is None
        assert engine.learning_enabled is False

    def test_get_learning_prediction_no_engine(self, sample_quote):
        """Test getting prediction when no learning engine is set."""
        engine = ConcreteStrategyEngine({"name": "test"})

        prediction = engine.get_learning_prediction(sample_quote)

        assert prediction is None

    def test_get_learning_prediction_disabled(self, sample_quote, mock_learning_engine):
        """Test getting prediction when learning is disabled."""
        engine = ConcreteStrategyEngine({"name": "test", "learning_enabled": False})

        prediction = engine.get_learning_prediction(sample_quote)

        assert prediction is None

    def test_get_learning_prediction_success(self, sample_quote, mock_learning_engine):
        """Test successful prediction retrieval."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_learning_engine(mock_learning_engine)

        prediction = engine.get_learning_prediction(sample_quote)

        assert prediction is not None
        assert prediction["confidence"] == 0.8
        assert engine.metrics["learning_adjustments_applied"] == 1

    def test_get_learning_prediction_exception(self, sample_quote):
        """Test prediction retrieval with exception."""
        engine = ConcreteStrategyEngine({"name": "test"})
        mock_engine = Mock()
        mock_engine.predict.side_effect = Exception("Prediction error")
        engine.set_learning_engine(mock_engine)

        prediction = engine.get_learning_prediction(sample_quote)

        assert prediction is None

    def test_apply_learning_adjustments_no_prediction(self, sample_quote):
        """Test applying adjustments with no prediction."""
        engine = ConcreteStrategyEngine({"name": "test"})
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=50.0,
            liquidity_score=70.0,
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("100"),
        )

        adjusted_signal = engine.apply_learning_adjustments(None, signal)

        assert adjusted_signal == signal
        assert adjusted_signal.confidence == 50.0

    def test_apply_learning_adjustments_with_confidence(self, sample_quote):
        """Test applying adjustments with confidence."""
        engine = ConcreteStrategyEngine({"name": "test"})
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=50.0,
            liquidity_score=70.0,
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("100"),
        )
        prediction = {"confidence": 0.85}

        adjusted_signal = engine.apply_learning_adjustments(prediction, signal)

        assert adjusted_signal.confidence == 85.0

    def test_apply_learning_adjustments_confidence_bounds(self, sample_quote):
        """Test that confidence is bounded between 0 and 100."""
        engine = ConcreteStrategyEngine({"name": "test"})
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=50.0,
            liquidity_score=70.0,
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("100"),
        )

        # Test upper bound
        prediction_high = {"confidence": 1.5}
        adjusted_high = engine.apply_learning_adjustments(prediction_high, signal)
        assert adjusted_high.confidence == 100.0

        # Test lower bound
        prediction_low = {"confidence": -0.5}
        adjusted_low = engine.apply_learning_adjustments(prediction_low, signal)
        assert adjusted_low.confidence == 0.0


# ===== Callback Tests =====


@pytest.mark.unit
class TestCallbacks:
    """Test suite for callback registration and triggering."""

    def test_register_signal_callback(self, sample_quote):
        """Test registering signal callback."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback = Mock()

        engine.register_signal_callback(callback)

        assert callback in engine.on_signal_generated_callbacks

    def test_register_trade_callback(self, sample_quote):
        """Test registering trade callback."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback = Mock()

        engine.register_trade_callback(callback)

        assert callback in engine.on_trade_executed_callbacks

    def test_register_market_data_callback(self, sample_quote):
        """Test registering market data callback."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback = Mock()

        engine.register_market_data_callback(callback)

        assert callback in engine.on_market_data_callbacks

    def test_trigger_signal_callbacks(self, sample_quote, sample_buy_signal):
        """Test triggering signal callbacks."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback1 = Mock()
        callback2 = Mock()
        engine.register_signal_callback(callback1)
        engine.register_signal_callback(callback2)

        engine._trigger_signal_callbacks(sample_buy_signal, sample_quote)

        callback1.assert_called_once_with(sample_buy_signal, sample_quote)
        callback2.assert_called_once_with(sample_buy_signal, sample_quote)

    def test_trigger_trade_callbacks(self, sample_quote):
        """Test triggering trade callbacks."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback = Mock()
        execution_result = {"status": "filled"}
        engine.register_trade_callback(callback)
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=50.0,
            liquidity_score=70.0,
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("100"),
        )

        engine._trigger_trade_callbacks(signal, execution_result)

        callback.assert_called_once_with(signal, execution_result)

    def test_trigger_market_data_callbacks(self, sample_quote):
        """Test triggering market data callbacks."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback = Mock()
        engine.register_market_data_callback(callback)

        engine._trigger_market_data_callbacks(sample_quote)

        callback.assert_called_once_with(sample_quote)

    def test_callback_exception_handling(self, sample_quote):
        """Test that callback exceptions are handled gracefully."""
        engine = ConcreteStrategyEngine({"name": "test"})
        callback_error = Mock(side_effect=Exception("Callback error"))
        callback_ok = Mock()
        engine.register_signal_callback(callback_error)
        engine.register_signal_callback(callback_ok)

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=50.0,
            liquidity_score=70.0,
            priority_score=60.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150"),
            volume=Decimal("100"),
        )

        # Should not raise exception
        engine._trigger_signal_callbacks(signal, sample_quote)

        callback_ok.assert_called_once()


# ===== Ensemble Weight Tests =====


@pytest.mark.unit
class TestEnsembleWeights:
    """Test suite for ensemble weight management."""

    def test_set_ensemble_weight_decimal(self, sample_quote):
        """Test setting ensemble weight with Decimal."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_ensemble_weight(Decimal("0.5"))

        assert engine.ensemble_weight == Decimal("0.5")
        assert engine.is_ensemble_component is True

    def test_set_ensemble_weight_float(self, sample_quote):
        """Test setting ensemble weight with float."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_ensemble_weight(0.75)

        assert engine.ensemble_weight == Decimal("0.75")
        assert engine.is_ensemble_component is True

    def test_set_ensemble_weight_string(self, sample_quote):
        """Test setting ensemble weight with string."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_ensemble_weight("0.33")

        assert engine.ensemble_weight == Decimal("0.33")
        assert engine.is_ensemble_component is True

    def test_set_ensemble_weight_full(self, sample_quote):
        """Test setting ensemble weight to 1.0 (full weight)."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_ensemble_weight(1.0)

        assert engine.ensemble_weight == Decimal("1.0")
        assert engine.is_ensemble_component is False

    def test_get_ensemble_weight(self, sample_quote):
        """Test getting ensemble weight."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_ensemble_weight(0.6)

        weight = engine.get_ensemble_weight()

        assert weight == Decimal("0.6")


# ===== Context/Data Engine Integration Tests =====


@pytest.mark.unit
class TestContextDataEngineIntegration:
    """Test suite for Context and Data engine integration."""

    def test_set_context_engine(self, sample_quote, mock_context_engine):
        """Test setting context engine."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_context_engine(mock_context_engine)

        assert engine.context_engine == mock_context_engine
        assert engine.context_engine_enabled is True

    def test_set_data_engine(self, sample_quote, mock_data_engine):
        """Test setting data engine."""
        engine = ConcreteStrategyEngine({"name": "test"})

        engine.set_data_engine(mock_data_engine)

        assert engine.data_engine == mock_data_engine
        assert engine.data_engine_enabled is True

    def test_get_context_analysis_no_engine(self, sample_quote):
        """Test context analysis when no engine is set."""
        engine = ConcreteStrategyEngine({"name": "test"})

        result = engine.get_context_analysis([150, 151, 152])

        assert result is None

    def test_get_context_analysis_disabled(self, sample_quote):
        """Test context analysis when engine is disabled."""
        engine = ConcreteStrategyEngine({"name": "test", "context_engine_enabled": False})
        engine.context_engine = mock_context_engine = Mock()

        result = engine.get_context_analysis([150, 151, 152])

        assert result is None

    def test_get_context_analysis_success(self, sample_quote, mock_context_engine):
        """Test successful context analysis."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_context_engine(mock_context_engine)

        result = engine.get_context_analysis([150, 151, 152])

        assert result is not None
        assert result["regime"] == "bull"
        assert engine.metrics["context_analysis_calls"] == 1

    def test_get_volatility_regime_no_engine(self, sample_quote):
        """Test volatility regime when no engine is set."""
        engine = ConcreteStrategyEngine({"name": "test"})

        result = engine.get_volatility_regime([150, 151, 152])

        assert result is None

    def test_get_volatility_regime_success(self, sample_quote, mock_context_engine):
        """Test successful volatility regime retrieval."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_context_engine(mock_context_engine)

        result = engine.get_volatility_regime([150, 151, 152])

        assert result is not None
        assert result["regime"] == "normal"


# ===== Signal Generation Tests =====


@pytest.mark.unit
class TestSignalGeneration:
    """Test suite for signal generation."""

    def test_generate_signals_triggers_callbacks(self, sample_quote):
        """Test that signal generation triggers callbacks."""
        engine = ConcreteStrategyEngine({"name": "test"})
        market_callback = Mock()
        signal_callback = Mock()
        engine.register_market_data_callback(market_callback)
        engine.register_signal_callback(signal_callback)

        # Use price > 100 to trigger signal
        quote_with_high_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("150"),
            ask=Decimal("150.05"),
            last=Decimal("150"),
            volume=Decimal("1000"),
        )

        signals = engine.generate_signals(quote_with_high_price)

        market_callback.assert_called_once()
        signal_callback.assert_called_once()
        assert len(signals) == 1
        assert engine.metrics["signals_generated"] == 1

    def test_generate_signals_no_signals(self, sample_quote):
        """Test signal generation when no signals are generated."""
        engine = ConcreteStrategyEngine({"name": "test"})

        # Use price < 100 to not trigger signal
        quote_with_low_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("50"),
            ask=Decimal("50.05"),
            last=Decimal("50"),
            volume=Decimal("1000"),
        )

        signals = engine.generate_signals(quote_with_low_price)

        assert len(signals) == 0
        assert engine.metrics["signals_generated"] == 0

    def test_generate_signals_with_learning(self, sample_quote, mock_learning_engine):
        """Test signal generation with learning adjustments."""
        engine = ConcreteStrategyEngine({"name": "test", "learning_enabled": True})
        engine.set_learning_engine(mock_learning_engine)

        quote_with_high_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("150"),
            ask=Decimal("150.05"),
            last=Decimal("150"),
            volume=Decimal("1000"),
        )

        signals = engine.generate_signals(quote_with_high_price)

        assert len(signals) == 1
        # Learning engine should have adjusted confidence
        assert signals[0].confidence == 80.0

    def test_generate_signals_updates_metrics(self, sample_quote):
        """Test that signal generation updates metrics."""
        engine = ConcreteStrategyEngine({"name": "test"})

        quote_with_high_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("150"),
            ask=Decimal("150.05"),
            last=Decimal("150"),
            volume=Decimal("1000"),
        )

        signals = engine.generate_signals(quote_with_high_price)

        assert engine.metrics["last_update"] is not None
        assert engine.metrics["signals_generated"] == 1


# ===== Metrics Tests =====


@pytest.mark.unit
class TestMetrics:
    """Test suite for metrics tracking."""

    def test_get_metrics(self, sample_quote):
        """Test getting metrics."""
        engine = ConcreteStrategyEngine({"name": "test"})

        metrics = engine.get_metrics()

        assert metrics["signals_generated"] == 0
        assert metrics["trades_executed"] == 0
        assert metrics["learning_adjustments_applied"] == 0

    def test_get_metrics_returns_copy(self, sample_quote):
        """Test that get_metrics returns a copy, not reference."""
        engine = ConcreteStrategyEngine({"name": "test"})
        metrics1 = engine.get_metrics()
        metrics1["signals_generated"] = 999

        metrics2 = engine.get_metrics()

        assert metrics2["signals_generated"] == 0

    def test_reset_metrics(self, sample_quote):
        """Test resetting metrics."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.metrics["signals_generated"] = 100
        engine.metrics["trades_executed"] = 50

        engine.reset_metrics()

        assert engine.metrics["signals_generated"] == 0
        assert engine.metrics["trades_executed"] == 0
        assert engine.metrics["learning_adjustments_applied"] == 0


# ===== Status Tests =====


@pytest.mark.unit
class TestStatus:
    """Test suite for engine status reporting."""

    def test_get_status_basic(self, sample_quote):
        """Test getting basic engine status."""
        engine = ConcreteStrategyEngine({"name": "test_engine"})

        status = engine.get_status()

        assert status["name"] == "test_engine"
        assert status["type"] == "test_strategy"
        assert status["is_active"] is True
        assert status["learning_enabled"] is False
        assert status["is_ensemble_component"] is False
        assert status["ensemble_weight"] == 1.0

    def test_get_status_with_learning(self, sample_quote, mock_learning_engine):
        """Test status with learning engine enabled."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_learning_engine(mock_learning_engine)

        status = engine.get_status()

        assert status["learning_enabled"] is True

    def test_get_status_with_ensemble(self, sample_quote):
        """Test status with ensemble component."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_ensemble_weight(0.5)

        status = engine.get_status()

        assert status["is_ensemble_component"] is True
        assert status["ensemble_weight"] == 0.5

    def test_get_status_includes_metrics(self, sample_quote):
        """Test that status includes metrics."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.metrics["signals_generated"] = 100

        status = engine.get_status()

        assert status["metrics"]["signals_generated"] == 100


# ===== Abstract Method Enforcement Tests =====


@pytest.mark.unit
class TestAbstractMethods:
    """Test suite for abstract method enforcement."""

    def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class directly
            BaseStrategyEngine({"name": "test"})


# ===== Repr Tests =====


@pytest.mark.unit
class TestRepr:
    """Test suite for string representation."""

    def test_repr_basic(self, sample_quote):
        """Test basic string representation."""
        engine = ConcreteStrategyEngine({"name": "test_engine"})

        repr_str = repr(engine)

        assert "ConcreteStrategyEngine" in repr_str
        assert "test_engine" in repr_str
        assert "test_strategy" in repr_str

    def test_repr_with_learning(self, sample_quote, mock_learning_engine):
        """Test repr with learning enabled."""
        engine = ConcreteStrategyEngine({"name": "test"})
        engine.set_learning_engine(mock_learning_engine)

        repr_str = repr(engine)

        assert "enabled" in repr_str


# ===== Edge Case Tests =====


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases."""

    def test_empty_config(self, sample_quote):
        """Test engine with empty configuration."""
        engine = ConcreteStrategyEngine({})

        assert engine is not None
        assert engine.name is not None

    def test_signal_callback_with_exception_in_generate_signals(self, sample_quote):
        """Test signal generation with callback exception."""
        engine = ConcreteStrategyEngine({"name": "test"})
        error_callback = Mock(side_effect=Exception("Error"))
        ok_callback = Mock()
        engine.register_signal_callback(error_callback)
        engine.register_signal_callback(ok_callback)

        quote_with_high_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("150"),
            ask=Decimal("150.05"),
            last=Decimal("150"),
            volume=Decimal("1000"),
        )

        # Should not raise exception
        signals = engine.generate_signals(quote_with_high_price)

        assert len(signals) == 1
        ok_callback.assert_called_once()

    def test_multiple_callbacks_execution_order(self, sample_quote):
        """Test that callbacks are executed in registration order."""
        engine = ConcreteStrategyEngine({"name": "test"})
        results = []

        def callback1(signal, quote):
            results.append("callback1")

        def callback2(signal, quote):
            results.append("callback2")

        def callback3(signal, quote):
            results.append("callback3")

        engine.register_signal_callback(callback1)
        engine.register_signal_callback(callback2)
        engine.register_signal_callback(callback3)

        quote_with_high_price = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            bid=Decimal("150"),
            ask=Decimal("150.05"),
            last=Decimal("150"),
            volume=Decimal("1000"),
        )

        engine.generate_signals(quote_with_high_price)

        assert results == ["callback1", "callback2", "callback3"]
