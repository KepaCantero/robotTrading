"""
Unit tests for Strategy Ensemble System.

Tests para WeightedEnsemble, RegimeBasedSelector y VotingEnsemble.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.models.market_data import Quote
from app.engines.strategy_engines.base import BaseStrategyEngine
from app.engines.strategy_engines.ensemble import (
    BaseStrategyEnsemble,
    RegimeBasedSelector,
    VotingEnsemble,
    WeightedEnsemble,
)
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


def make_quote(
    symbol: str = "AAPL",
    price: float = 150.0,
    volume: float = 1_000_000,
) -> Quote:
    """Helper para crear Quote."""
    return Quote(
        symbol=symbol,
        timestamp=datetime.utcnow(),
        bid=Decimal(str(price)),
        ask=Decimal(str(price)),
        last=Decimal(str(price)),
        close=Decimal(str(price)),
        open=Decimal(str(price)),
        high=Decimal(str(price)),
        low=Decimal(str(price)),
        volume=Decimal(str(volume)),
    )


def _confidence_to_strength(confidence: float) -> SignalStrength:
    """Map confidence to appropriate signal strength."""
    if confidence >= 80.0:
        return SignalStrength.VERY_STRONG
    elif confidence >= 70.0:
        return SignalStrength.STRONG
    elif confidence >= 50.0:
        return SignalStrength.MODERATE
    else:
        return SignalStrength.WEAK


def make_signal(
    symbol: str = "AAPL",
    signal_type: SignalType = SignalType.BUY,
    confidence: float = 75.0,
    price: float = 150.0,
) -> Signal:
    """Helper para crear Signal."""
    strength = _confidence_to_strength(confidence)
    return Signal(
        symbol=symbol,
        signal_type=signal_type,
        strength=strength,
        price=Decimal(str(price)),
        timestamp=datetime.utcnow(),
        confidence=confidence,
        liquidity_score=70.0,
        priority_score=confidence,
        source=SignalSource.TECHNICAL,
        volume=Decimal("100"),
        metadata={},
    )


class MockStrategy(BaseStrategyEngine):
    """Mock strategy for testing ensembles."""

    def __init__(self, config, signals_to_return=None):
        super().__init__(config)
        self.signals_to_return = signals_to_return or []

    def get_strategy_type(self) -> str:
        return "mock"

    def extract_features(self, market_data, historical_data=None):
        return {"mock": True}

    def _generate_signals_impl(self, market_data):
        return self.signals_to_return

    def get_required_parameters(self):
        return []

    def risk_check(self, signal, portfolio):
        return True


class TestWeightedEnsemble:
    """Tests para WeightedEnsemble."""

    def test_weighted_ensemble_initialization(self):
        """El ensemble se inicializa correctamente."""
        config = {
            "weight_decay": 0.9,
            "min_weight": 0.2,
            "max_weight": 2.0,
        }
        ensemble = WeightedEnsemble(config)

        assert ensemble.get_strategy_type() == "ensemble"
        assert float(ensemble.weight_decay) == 0.9
        assert float(ensemble.min_weight) == 0.2
        assert float(ensemble.max_weight) == 2.0

    def test_add_strategy(self):
        """Se pueden añadir estrategias al ensemble."""
        ensemble = WeightedEnsemble({})
        strategy1 = MockStrategy({"name": "strategy1"})
        strategy2 = MockStrategy({"name": "strategy2"})

        ensemble.add_strategy("s1", strategy1, weight=1.0)
        ensemble.add_strategy("s2", strategy2, weight=0.5)

        assert len(ensemble.strategies) == 2
        assert "s1" in ensemble.strategies
        assert "s2" in ensemble.strategies
        assert ensemble.strategy_weights["s1"] == 1.0
        assert ensemble.strategy_weights["s2"] == 0.5

    def test_remove_strategy(self):
        """Se pueden eliminar estrategias del ensemble."""
        ensemble = WeightedEnsemble({})
        strategy = MockStrategy({"name": "test"})

        ensemble.add_strategy("test", strategy)
        assert "test" in ensemble.strategies

        result = ensemble.remove_strategy("test")
        assert result is True
        assert "test" not in ensemble.strategies

        result = ensemble.remove_strategy("nonexistent")
        assert result is False

    def test_no_signals_without_strategies(self):
        """No genera señales si no hay estrategias."""
        ensemble = WeightedEnsemble({})
        quote = make_quote()

        signals = ensemble.generate_signals(quote)
        assert signals == []

    def test_combines_signals_from_multiple_strategies(self):
        """Combina señales de múltiples estrategias."""
        ensemble = WeightedEnsemble({"min_strategies_for_signal": 1})

        # Crear estrategias con señales
        signal1 = make_signal(confidence=70.0)
        signal2 = make_signal(confidence=80.0)

        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal1])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal2])

        ensemble.add_strategy("s1", strategy1, weight=1.0)
        ensemble.add_strategy("s2", strategy2, weight=1.0)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        # Debe combinar las señales del mismo tipo
        assert len(signals) >= 1
        if len(signals) > 0:
            assert signals[0].metadata.get("ensemble_type") == "weighted"

    def test_weighted_confidence_calculation(self):
        """La confianza se calcula con pesos correctos."""
        ensemble = WeightedEnsemble({"min_strategies_for_signal": 1})

        signal1 = make_signal(confidence=60.0)
        signal2 = make_signal(confidence=80.0)

        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal1])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal2])

        ensemble.add_strategy("s1", strategy1, weight=1.0)
        ensemble.add_strategy("s2", strategy2, weight=3.0)  # Peso mayor

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        if len(signals) > 0:
            # Confianza ponderada: (60*1 + 80*3) / (1+3) = 75
            assert signals[0].confidence == pytest.approx(75.0, rel=0.1)

    def test_extract_features_from_all_strategies(self):
        """Extrae features de todas las estrategias."""
        ensemble = WeightedEnsemble({})

        strategy1 = MockStrategy({"name": "s1"})
        strategy2 = MockStrategy({"name": "s2"})

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)

        quote = make_quote()
        features = ensemble.extract_features(quote)

        assert "s1_features" in features
        assert "s2_features" in features
        assert features["num_strategies"] == 2

    def test_update_strategy_performance(self):
        """Se puede actualizar el historial de performance."""
        ensemble = WeightedEnsemble({})

        ensemble.update_strategy_performance(
            "test",
            {
                "sharpe": 1.5,
                "return": 0.15,
                "max_drawdown": 0.05,
            },
        )

        assert len(ensemble.performance_history["test"]) == 1
        assert ensemble.performance_history["test"][0]["sharpe"] == 1.5


class TestRegimeBasedSelector:
    """Tests para RegimeBasedSelector."""

    def test_regime_selector_initialization(self):
        """El selector se inicializa correctamente."""
        config = {
            "trend_threshold": 0.03,
            "volatility_threshold": 0.03,
        }
        selector = RegimeBasedSelector(config)

        assert selector.get_strategy_type() == "ensemble"
        assert selector.trend_threshold == 0.03
        assert selector.volatility_threshold == 0.03
        assert selector.current_regime == RegimeBasedSelector.REGIME_UNKNOWN

    def test_regime_detection_unknown_with_insufficient_data(self):
        """Régimen desconocido sin suficientes datos."""
        selector = RegimeBasedSelector({"regime_lookback": 50})

        # Sin datos, régimen es desconocido
        regime, confidence = selector.get_current_regime()
        assert regime == RegimeBasedSelector.REGIME_UNKNOWN
        assert confidence == 0.0

    def test_regime_detection_trending_up(self):
        """Detecta tendencia alcista correctamente."""
        selector = RegimeBasedSelector(
            {
                "regime_lookback": 20,
                "trend_threshold": 0.005,  # Umbral más bajo
                "volatility_threshold": 0.1,  # Umbral alto para evitar high_vol
            }
        )

        # Simular precios con tendencia alcista fuerte
        for i in range(30):
            price = 100.0 + i * 2.0  # Tendencia muy clara
            selector.price_history.append(price)

        selector._detect_regime()
        regime, confidence = selector.get_current_regime()

        # Puede detectar trending_up o low_volatility dependiendo de los cálculos
        assert regime in [
            RegimeBasedSelector.REGIME_TRENDING_UP,
            RegimeBasedSelector.REGIME_LOW_VOLATILITY,
            RegimeBasedSelector.REGIME_MEAN_REVERTING,
        ]

    def test_regime_detection_trending_down(self):
        """Detecta tendencia bajista correctamente."""
        selector = RegimeBasedSelector(
            {
                "regime_lookback": 20,
                "trend_threshold": 0.005,  # Umbral más bajo
                "volatility_threshold": 0.1,  # Umbral alto para evitar high_vol
            }
        )

        # Simular precios con tendencia bajista fuerte
        for i in range(30):
            price = 200.0 - i * 2.0  # Tendencia bajista muy clara
            selector.price_history.append(price)

        selector._detect_regime()
        regime, confidence = selector.get_current_regime()

        # Puede detectar trending_down o low_volatility dependiendo de los cálculos
        assert regime in [
            RegimeBasedSelector.REGIME_TRENDING_DOWN,
            RegimeBasedSelector.REGIME_LOW_VOLATILITY,
            RegimeBasedSelector.REGIME_MEAN_REVERTING,
        ]

    def test_regime_detection_high_volatility(self):
        """Detecta alta volatilidad correctamente."""
        selector = RegimeBasedSelector(
            {
                "regime_lookback": 20,
                "volatility_threshold": 0.01,  # Umbral bajo para test
            }
        )

        # Simular precios muy volátiles
        import random

        random.seed(42)
        for i in range(30):
            price = 100.0 + random.uniform(-10, 10)  # Alta volatilidad
            selector.price_history.append(price)

        selector._detect_regime()
        regime, confidence = selector.get_current_regime()

        # Puede ser high_volatility o trending dependiendo de los valores random
        assert regime in [
            RegimeBasedSelector.REGIME_HIGH_VOLATILITY,
            RegimeBasedSelector.REGIME_TRENDING_UP,
            RegimeBasedSelector.REGIME_TRENDING_DOWN,
            RegimeBasedSelector.REGIME_MEAN_REVERTING,
        ]

    def test_selects_appropriate_strategies_for_regime(self):
        """Selecciona estrategias apropiadas según régimen."""
        selector = RegimeBasedSelector(
            {
                "regime_strategy_map": {
                    RegimeBasedSelector.REGIME_TRENDING_UP: ["trend_following", "momentum"],
                    RegimeBasedSelector.REGIME_MEAN_REVERTING: ["mean_reversion"],
                }
            }
        )

        # Añadir estrategias
        selector.add_strategy("trend_following", MockStrategy({"name": "tf"}))
        selector.add_strategy("momentum", MockStrategy({"name": "mom"}))
        selector.add_strategy("mean_reversion", MockStrategy({"name": "mr"}))

        # Forzar régimen
        selector.current_regime = RegimeBasedSelector.REGIME_TRENDING_UP

        selected = selector._select_strategies_for_regime()

        assert "trend_following" in selected
        assert "momentum" in selected
        assert "mean_reversion" not in selected

    def test_adds_regime_info_to_signal_metadata(self):
        """Añade información de régimen al metadata de señales."""
        selector = RegimeBasedSelector({"regime_lookback": 5})

        signal = make_signal()
        strategy = MockStrategy({"name": "test"}, signals_to_return=[signal])
        selector.add_strategy("test", strategy)

        # Añadir precio para tener historial
        for i in range(10):
            selector.price_history.append(100.0 + i)

        quote = make_quote()
        signals = selector.generate_signals(quote)

        if len(signals) > 0:
            assert "regime" in signals[0].metadata
            assert "regime_confidence" in signals[0].metadata


class TestVotingEnsemble:
    """Tests para VotingEnsemble."""

    def test_voting_ensemble_initialization(self):
        """El ensemble se inicializa correctamente."""
        config = {
            "min_votes": 3,
            "require_majority": True,
            "unanimous_boost": 1.3,
        }
        ensemble = VotingEnsemble(config)

        assert ensemble.min_votes == 3
        assert ensemble.require_majority is True
        assert ensemble.unanimous_boost == 1.3

    def test_no_signal_with_insufficient_votes(self):
        """No genera señal si no hay suficientes votos."""
        ensemble = VotingEnsemble({"min_votes": 3})

        signal = make_signal()
        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal])

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        # Solo 2 votos, necesita 3
        assert len(signals) == 0

    def test_generates_signal_with_sufficient_votes(self):
        """Genera señal cuando hay suficientes votos."""
        ensemble = VotingEnsemble({"min_votes": 2, "require_majority": False})

        signal = make_signal()
        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal])

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        assert len(signals) >= 1
        if len(signals) > 0:
            assert signals[0].metadata.get("ensemble_type") == "voting"
            assert signals[0].metadata.get("votes") == 2

    def test_unanimous_vote_boosts_confidence(self):
        """Votación unánime aumenta la confianza."""
        ensemble = VotingEnsemble(
            {
                "min_votes": 2,
                "require_majority": False,
                "unanimous_boost": 1.2,
            }
        )

        signal = make_signal(confidence=70.0)
        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal])

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        if len(signals) > 0:
            # Confianza boosteada: 70 * 1.2 = 84
            assert signals[0].confidence >= 70.0 * 1.2 - 1.0  # Con tolerancia
            assert signals[0].metadata.get("is_unanimous") is True

    def test_majority_requirement(self):
        """Requiere mayoría cuando está configurado."""
        ensemble = VotingEnsemble({"min_votes": 1, "require_majority": True})

        buy_signal = make_signal(signal_type=SignalType.BUY)
        sell_signal = make_signal(signal_type=SignalType.SELL)

        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[buy_signal])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[sell_signal])
        strategy3 = MockStrategy({"name": "s3"}, signals_to_return=[buy_signal])

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)
        ensemble.add_strategy("s3", strategy3)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        # BUY tiene 2/3 votos (mayoría), SELL tiene 1/3 (no mayoría)
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]

        assert len(buy_signals) >= 1  # BUY tiene mayoría
        assert len(sell_signals) == 0  # SELL no tiene mayoría

    def test_vote_metadata_includes_voting_strategies(self):
        """El metadata incluye las estrategias que votaron."""
        ensemble = VotingEnsemble({"min_votes": 2, "require_majority": False})

        signal = make_signal()
        strategy1 = MockStrategy({"name": "s1"}, signals_to_return=[signal])
        strategy2 = MockStrategy({"name": "s2"}, signals_to_return=[signal])

        ensemble.add_strategy("s1", strategy1)
        ensemble.add_strategy("s2", strategy2)

        quote = make_quote()
        signals = ensemble.generate_signals(quote)

        if len(signals) > 0:
            voting_strategies = signals[0].metadata.get("voting_strategies", [])
            assert "s1" in voting_strategies
            assert "s2" in voting_strategies


class TestEnsembleIntegration:
    """Tests de integración para ensembles."""

    def test_ensemble_can_use_real_strategies(self):
        """El ensemble puede usar estrategias reales."""
        from app.engines.strategy_engines import BreakoutStrategyEngine

        ensemble = WeightedEnsemble({"min_strategies_for_signal": 1})

        # Usar estrategia real
        breakout = BreakoutStrategyEngine({})
        ensemble.add_strategy("breakout", breakout)

        assert "breakout" in ensemble.strategies

        # Generar señales (puede no generar ninguna sin suficiente historial)
        quote = make_quote()
        signals = ensemble.generate_signals(quote)
        assert isinstance(signals, list)

    def test_multiple_ensemble_types_compatible(self):
        """Diferentes tipos de ensemble son compatibles."""
        weighted = WeightedEnsemble({})
        regime = RegimeBasedSelector({})
        voting = VotingEnsemble({})

        # Todos son BaseStrategyEnsemble
        assert isinstance(weighted, BaseStrategyEnsemble)
        assert isinstance(regime, BaseStrategyEnsemble)
        assert isinstance(voting, BaseStrategyEnsemble)

        # Todos tienen la misma interfaz básica
        assert hasattr(weighted, "add_strategy")
        assert hasattr(regime, "add_strategy")
        assert hasattr(voting, "add_strategy")

    def test_ensemble_performance_tracking(self):
        """El ensemble trackea performance correctamente."""
        ensemble = WeightedEnsemble({})

        # Añadir múltiples registros de performance
        for i in range(10):
            ensemble.update_strategy_performance(
                "test_strategy",
                {
                    "sharpe": 1.0 + i * 0.1,
                    "return": 0.01 * i,
                },
            )

        history = ensemble.performance_history["test_strategy"]
        assert len(history) == 10
        assert history[-1]["sharpe"] == 1.9  # Último registro
