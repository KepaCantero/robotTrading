"""
Strategy Ensemble System - Sistema de composición de estrategias.

Implementa ensembles de estrategias para combinar señales de múltiples engines:
- WeightedEnsemble: Combina señales con pesos dinámicos
- RegimeBasedSelector: Selecciona estrategia según régimen de mercado
- VotingEnsemble: Combina señales por votación mayoritaria

Características principales:
- Pesos dinámicos basados en performance histórica
- Adaptación automática a régimen de mercado
- Combinación inteligente de señales
- Gestión de conflictos entre estrategias
"""

from __future__ import annotations

import contextlib
import logging
from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np

from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType

from .base import BaseStrategyEngine

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


class BaseStrategyEnsemble(BaseStrategyEngine):
    """
    Clase base para ensembles de estrategias.

    Un ensemble combina múltiples strategy engines para generar
    señales más robustas y diversificadas.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar ensemble base.

        Args:
            config: Configuración del ensemble
        """
        super().__init__(config)

        self.strategies: dict[str, BaseStrategyEngine] = {}
        self.strategy_weights: dict[str, float] = {}
        self.performance_history: dict[str, list[dict[str, float]]] = defaultdict(list)

        # Configuración de ensemble
        self.min_strategies_for_signal = config.get("min_strategies_for_signal", 1)
        self.conflict_resolution = config.get(
            "conflict_resolution", "weighted"
        )  # weighted, majority, strongest
        self.weight_update_frequency = config.get("weight_update_frequency", 100)  # cada N señales
        self.signal_count = 0

        logger.info(f"BaseStrategyEnsemble initialized: {self.name}")

    def add_strategy(self, name: str, strategy: BaseStrategyEngine, weight: float = 1.0) -> None:
        """
        Añadir estrategia al ensemble.

        Args:
            name: Nombre identificador de la estrategia
            strategy: Instancia del strategy engine
            weight: Peso inicial de la estrategia (default 1.0)
        """
        self.strategies[name] = strategy
        self.strategy_weights[name] = weight
        logger.info(f"Added strategy '{name}' to ensemble with weight {weight}")

    def remove_strategy(self, name: str) -> bool:
        """
        Eliminar estrategia del ensemble.

        Args:
            name: Nombre de la estrategia a eliminar

        Returns:
            True si se eliminó correctamente
        """
        if name in self.strategies:
            del self.strategies[name]
            del self.strategy_weights[name]
            if name in self.performance_history:
                del self.performance_history[name]
            logger.info(f"Removed strategy '{name}' from ensemble")
            return True
        return False

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "ensemble"

    def extract_features(
        self,
        market_data: Quote,
        historical_data: Sequence[Quote] | None = None,
    ) -> dict[str, Any]:
        """
        Extraer features combinados de todas las estrategias.

        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional

        Returns:
            Features combinados de todas las estrategias
        """
        features: dict[str, Any] = {
            "timestamp": getattr(market_data, "timestamp", None),
            "symbol": market_data.symbol,
            "ensemble_type": self.get_strategy_type(),
            "num_strategies": len(self.strategies),
            "strategy_weights": self.strategy_weights.copy(),
        }

        # Extraer features de cada estrategia
        for name, strategy in self.strategies.items():
            try:
                strategy_features = strategy.extract_features(market_data, historical_data)
                features[f"{name}_features"] = strategy_features
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Error extracting features from {name}: {e}")
                features[f"{name}_features"] = {}

        return features

    def get_required_parameters(self) -> list[str]:
        """
        Obtener parámetros requeridos.

        Todos los parámetros tienen defaults sensibles, por lo que
        ninguno es estrictamente requerido.
        """
        return []  # All parameters have sensible defaults

    def risk_check(self, signal: Signal, portfolio: object) -> bool:
        """
        Verificar criterios de riesgo para el ensemble.

        Para ensembles, delegamos al risk_check de las estrategias individuales
        o aplicamos un check básico por defecto.

        Args:
            signal: Señal a verificar
            portfolio: Estado del portfolio

        Returns:
            True si pasa el risk check
        """
        # Check básico de confianza - lowered from 50.0 to 30.0 for ensemble flexibility
        min_confidence = 30.0
        if signal.confidence < min_confidence:
            return False

        # Verificar con estrategias individuales si tienen el check
        strategy_name = signal.metadata.get("selected_strategy")
        if strategy_name and strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            with contextlib.suppress(ValueError, TypeError, KeyError, AttributeError, IndexError):
                result = strategy.risk_check(signal, portfolio)
                if isinstance(result, bool):
                    return result

        return True

    def update_strategy_performance(self, strategy_name: str, metrics: dict[str, float]) -> None:
        """
        Actualizar historial de performance de una estrategia.

        Args:
            strategy_name: Nombre de la estrategia
            metrics: Métricas de performance (sharpe, return, drawdown, etc.)
        """
        metrics["timestamp"] = float(datetime.utcnow().timestamp())
        self.performance_history[strategy_name].append(metrics)

        # Mantener solo últimos N registros
        max_history = 100
        if len(self.performance_history[strategy_name]) > max_history:
            self.performance_history[strategy_name] = self.performance_history[strategy_name][
                -max_history:
            ]

    @abstractmethod
    def _combine_signals(
        self, strategy_signals: dict[str, list[Signal]], market_data: Quote
    ) -> list[Signal]:
        """
        Combinar señales de múltiples estrategias.

        Args:
            strategy_signals: Dict con señales por estrategia
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales combinadas
        """


class WeightedEnsemble(BaseStrategyEnsemble):
    """
    Ensemble con pesos dinámicos.

    Combina señales de múltiples estrategias usando pesos que se
    ajustan automáticamente basándose en performance histórica.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar WeightedEnsemble.

        Args:
            config: Configuración del ensemble
        """
        super().__init__(config)

        # Parámetros de ajuste de pesos
        self.weight_decay = Decimal(str(config.get("weight_decay", 0.95)))
        self.min_weight = Decimal(str(config.get("min_weight", 0.1)))
        self.max_weight = Decimal(str(config.get("max_weight", 3.0)))
        self.performance_lookback = config.get("performance_lookback", 20)

        # Método de cálculo de pesos
        self.weight_method = config.get("weight_method", "sharpe")  # sharpe, return, inverse_dd

        logger.info(f"WeightedEnsemble initialized with method: {self.weight_method}")

    def _generate_signals_impl(self, market_data: Quote) -> list[Signal]:
        """
        Generar señales combinadas del ensemble.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales combinadas
        """
        if not self.strategies:
            return []

        # Recopilar señales de todas las estrategias
        strategy_signals: dict[str, list[Signal]] = {}

        for name, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(market_data)
                strategy_signals[name] = signals
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Error generating signals from {name}: {e}")
                strategy_signals[name] = []

        # Actualizar contador y pesos si es necesario
        self.signal_count += 1
        if self.signal_count % self.weight_update_frequency == 0:
            self._update_weights()

        # Combinar señales
        return self._combine_signals(strategy_signals, market_data)

    def _combine_signals(
        self, strategy_signals: dict[str, list[Signal]], market_data: Quote
    ) -> list[Signal]:
        """
        Combinar señales usando pesos ponderados.

        Args:
            strategy_signals: Dict con señales por estrategia
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales combinadas
        """
        # Agrupar señales por símbolo y tipo
        signal_groups: dict[str, dict[SignalType, list[tuple[str, Signal, float]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for strategy_name, signals in strategy_signals.items():
            weight = self.strategy_weights.get(strategy_name, 1.0)
            for signal in signals:
                signal_groups[signal.symbol][signal.signal_type].append(
                    (strategy_name, signal, weight)
                )

        combined_signals: list[Signal] = []

        for symbol, type_groups in signal_groups.items():
            for signal_type, weighted_signals in type_groups.items():
                if len(weighted_signals) < self.min_strategies_for_signal:
                    continue

                # Calcular confianza ponderada
                total_weight = sum(w for _, _, w in weighted_signals)
                if total_weight == 0:
                    continue

                weighted_confidence = (
                    sum(s.confidence * w for _, s, w in weighted_signals) / total_weight
                )

                # Usar el mejor precio disponible
                best_signal = max(weighted_signals, key=lambda x: x[1].confidence * x[2])
                _, base_signal, _ = best_signal

                # Crear señal combinada
                # Asegurar que signal_type es un SignalType enum
                signal_type_enum = (
                    signal_type if isinstance(signal_type, SignalType) else SignalType(signal_type)
                )
                priority = min(100.0, weighted_confidence * 0.8 + 20.0)  # Cap at 100

                combined_signal = Signal(
                    symbol=symbol,
                    signal_type=signal_type_enum,
                    strength=self._map_confidence_to_strength(weighted_confidence),
                    price=base_signal.price,
                    timestamp=base_signal.timestamp,
                    confidence=weighted_confidence,
                    liquidity_score=base_signal.liquidity_score,
                    priority_score=priority,
                    source=SignalSource.TECHNICAL,
                    volume=base_signal.volume,
                    metadata={
                        "ensemble_type": "weighted",
                        "contributing_strategies": [name for name, _, _ in weighted_signals],
                        "strategy_weights": {name: w for name, _, w in weighted_signals},
                        "num_strategies": len(weighted_signals),
                        "total_weight": total_weight,
                    },
                )
                combined_signals.append(combined_signal)

        return combined_signals

    def _update_weights(self) -> None:
        """Actualizar pesos basándose en performance histórica."""
        if not self.performance_history:
            return

        for strategy_name in self.strategies:
            history = self.performance_history.get(strategy_name, [])
            if len(history) < 5:  # Mínimo 5 registros para actualizar
                continue

            recent = history[-self.performance_lookback :]

            new_weight: float
            if self.weight_method == "sharpe":
                avg_sharpe = np.mean([h.get("sharpe", 0) for h in recent])
                new_weight = float(max(0.5 + float(avg_sharpe) * 0.5, float(self.min_weight)))
            elif self.weight_method == "return":
                avg_return = np.mean([h.get("return", 0) for h in recent])
                new_weight = float(max(1.0 + float(avg_return) * 10, float(self.min_weight)))
            elif self.weight_method == "inverse_dd":
                avg_dd = np.mean([h.get("max_drawdown", 0.1) for h in recent])
                new_weight = float(max(1.0 / (float(avg_dd) + 0.01), float(self.min_weight)))
            else:
                new_weight = 1.0

            # Aplicar decay y límites
            current_weight = float(self.strategy_weights.get(strategy_name, 1.0))
            smoothed_weight = current_weight * float(self.weight_decay) + new_weight * (
                1 - float(self.weight_decay)
            )
            self.strategy_weights[strategy_name] = min(
                float(self.max_weight), max(float(self.min_weight), smoothed_weight)
            )

        logger.debug(f"Updated weights: {self.strategy_weights}")

    @staticmethod
    def _map_confidence_to_strength(confidence: float) -> SignalStrength:
        """Mapear confianza a strength."""
        if confidence >= 80.0:
            return SignalStrength.VERY_STRONG
        if confidence >= 70.0:
            return SignalStrength.STRONG
        if confidence >= 50.0:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK


class RegimeBasedSelector(BaseStrategyEnsemble):
    """
    Selector de estrategia basado en régimen de mercado.

    Selecciona la estrategia más apropiada según el régimen
    actual del mercado (trending, mean-reverting, volatile, etc.).
    """

    # Regímenes de mercado soportados
    REGIME_TRENDING_UP = "trending_up"
    REGIME_TRENDING_DOWN = "trending_down"
    REGIME_MEAN_REVERTING = "mean_reverting"
    REGIME_HIGH_VOLATILITY = "high_volatility"
    REGIME_LOW_VOLATILITY = "low_volatility"
    REGIME_UNKNOWN = "unknown"

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar RegimeBasedSelector.

        Args:
            config: Configuración del selector
        """
        super().__init__(config)

        # Mapeo de régimen a estrategias preferidas (using correct engine names)
        self.regime_strategy_map: dict[str, list[str]] = config.get(
            "regime_strategy_map",
            {
                self.REGIME_TRENDING_UP: ["trend_following", "momentum_engine", "breakout"],
                self.REGIME_TRENDING_DOWN: ["trend_following", "momentum_engine"],
                self.REGIME_MEAN_REVERTING: ["mean_reversion_engine"],
                self.REGIME_HIGH_VOLATILITY: ["breakout", "momentum_engine"],
                self.REGIME_LOW_VOLATILITY: ["mean_reversion_engine"],
                self.REGIME_UNKNOWN: [],  # Usar todas
            },
        )

        # Estado del régimen actual
        self.current_regime: str = self.REGIME_UNKNOWN
        self.regime_confidence: float = 0.0

        # Historial de precios para detección de régimen
        self.price_history: list[float] = []
        self.regime_lookback = config.get("regime_lookback", 100)  # Increased from 50 to 100

        # Umbrales para detección de régimen (improved defaults)
        self.trend_threshold = config.get("trend_threshold", 0.02)  # 2% para tendencia
        self.volatility_threshold = config.get(
            "volatility_threshold",
            0.30,  # Increased from 0.025 to 0.30 (30% annualized)
        )

        # Hysteresis for regime changes - require N consecutive detections
        self.regime_history: list[str] = []
        self.hysteresis_count = config.get(
            "hysteresis_count", 3
        )  # Require 3 consecutive detections

        logger.info("RegimeBasedSelector initialized")

    def _generate_signals_impl(self, market_data: Quote) -> list[Signal]:
        """
        Generar señales seleccionando estrategia por régimen.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales de la estrategia seleccionada
        """
        if not self.strategies:
            return []

        # Actualizar historial de precios
        current_price = float(market_data.close or market_data.bid or market_data.last or 0)
        if current_price > 0:
            self.price_history.append(current_price)
            if len(self.price_history) > self.regime_lookback * 2:
                self.price_history = self.price_history[-self.regime_lookback * 2 :]

        # Detectar régimen actual
        self._detect_regime()

        # Seleccionar estrategias según régimen
        selected_strategies = self._select_strategies_for_regime()

        # Generar señales de estrategias seleccionadas
        strategy_signals: dict[str, list[Signal]] = {}
        for name in selected_strategies:
            if name in self.strategies:
                try:
                    signals = self.strategies[name].generate_signals(market_data)
                    strategy_signals[name] = signals
                except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                    logger.warning(f"Error generating signals from {name}: {e}")

        return self._combine_signals(strategy_signals, market_data)

    def _detect_regime(self) -> None:
        """Detectar régimen de mercado actual with hysteresis."""
        if len(self.price_history) < self.regime_lookback:
            self.current_regime = self.REGIME_UNKNOWN
            self.regime_confidence = 0.0
            return

        prices = np.array(self.price_history[-self.regime_lookback :])

        # Calcular retorno y volatilidad
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Anualizada

        # Calcular tendencia (pendiente de regresión lineal)
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        normalized_slope = slope / np.mean(prices)

        # Detect raw regime (before hysteresis)
        detected_regime = self.REGIME_UNKNOWN
        detected_confidence = 0.0

        # IMPORTANT: Check trend FIRST, then volatility
        # This ensures trending markets are identified correctly
        if normalized_slope > self.trend_threshold:
            detected_regime = self.REGIME_TRENDING_UP
            detected_confidence = min(abs(normalized_slope) / self.trend_threshold, 2.0) * 50
        elif normalized_slope < -self.trend_threshold:
            detected_regime = self.REGIME_TRENDING_DOWN
            detected_confidence = min(abs(normalized_slope) / self.trend_threshold, 2.0) * 50
        elif volatility > self.volatility_threshold:
            detected_regime = self.REGIME_HIGH_VOLATILITY
            detected_confidence = min(volatility / self.volatility_threshold, 2.0) * 50
        elif volatility < self.volatility_threshold * 0.4:
            detected_regime = self.REGIME_LOW_VOLATILITY
            detected_confidence = 70.0
        else:
            detected_regime = self.REGIME_MEAN_REVERTING
            detected_confidence = 60.0

        # Apply hysteresis - only change regime if detected N consecutive times
        self.regime_history.append(detected_regime)
        if len(self.regime_history) > self.hysteresis_count * 2:
            self.regime_history = self.regime_history[-self.hysteresis_count * 2 :]

        # Check if we have enough history and if the detected regime is consistent
        if len(self.regime_history) >= self.hysteresis_count:
            recent_regimes = self.regime_history[-self.hysteresis_count :]
            if all(r == detected_regime for r in recent_regimes):
                # Regime is stable, update current regime
                self.current_regime = detected_regime
                self.regime_confidence = detected_confidence
            # else: keep current regime (hysteresis in action)
        else:
            # Not enough history yet, use detected regime
            self.current_regime = detected_regime
            self.regime_confidence = detected_confidence

    def _select_strategies_for_regime(self) -> list[str]:
        """Seleccionar estrategias apropiadas para el régimen actual."""
        preferred = self.regime_strategy_map.get(self.current_regime, [])

        if not preferred:
            # Si no hay preferencia, usar todas
            return list(self.strategies.keys())

        # Filtrar solo estrategias disponibles
        available = [s for s in preferred if s in self.strategies]

        if not available:
            # Si ninguna preferida está disponible, usar todas
            return list(self.strategies.keys())

        return available

    def _combine_signals(
        self, strategy_signals: dict[str, list[Signal]], market_data: Quote
    ) -> list[Signal]:
        """
        Combinar señales de estrategias seleccionadas.

        Args:
            strategy_signals: Dict con señales por estrategia
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales combinadas
        """
        combined_signals: list[Signal] = []

        for strategy_name, signals in strategy_signals.items():
            for signal in signals:
                # Añadir información de régimen al metadata
                enhanced_metadata = signal.metadata.copy() if signal.metadata else {}
                enhanced_metadata.update(
                    {
                        "regime": self.current_regime,
                        "regime_confidence": self.regime_confidence,
                        "selected_strategy": strategy_name,
                        "selector_type": "regime_based",
                    }
                )

                # Asegurar tipos correctos para Pydantic
                signal_type_enum = (
                    signal.signal_type
                    if isinstance(signal.signal_type, SignalType)
                    else SignalType(signal.signal_type)
                )
                strength_enum = (
                    signal.strength
                    if isinstance(signal.strength, SignalStrength)
                    else SignalStrength(signal.strength)
                )
                source_enum = (
                    signal.source
                    if isinstance(signal.source, SignalSource)
                    else SignalSource(signal.source)
                )

                enhanced_signal = Signal(
                    symbol=signal.symbol,
                    signal_type=signal_type_enum,
                    strength=strength_enum,
                    price=signal.price,
                    timestamp=signal.timestamp,
                    confidence=signal.confidence,
                    liquidity_score=signal.liquidity_score,
                    priority_score=min(100.0, signal.priority_score),
                    source=source_enum,
                    volume=signal.volume,
                    metadata=enhanced_metadata,
                )
                combined_signals.append(enhanced_signal)

        return combined_signals

    def get_current_regime(self) -> tuple[str, float]:
        """
        Obtener régimen actual y confianza.

        Returns:
            Tupla (régimen, confianza)
        """
        return self.current_regime, self.regime_confidence


class VotingEnsemble(BaseStrategyEnsemble):
    """
    Ensemble por votación mayoritaria.

    Genera señales solo cuando múltiples estrategias coinciden
    en la dirección (compra/venta).
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar VotingEnsemble.

        Args:
            config: Configuración del ensemble
        """
        super().__init__(config)

        # Configuración de votación
        self.min_votes = config.get("min_votes", 2)  # Mínimo de estrategias que deben coincidir
        self.require_majority = config.get("require_majority", True)  # Requiere >50%
        self.unanimous_boost = config.get("unanimous_boost", 1.2)  # Boost si es unánime

        logger.info(f"VotingEnsemble initialized: min_votes={self.min_votes}")

    def _generate_signals_impl(self, market_data: Quote) -> list[Signal]:
        """
        Generar señales por votación.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales votadas
        """
        if not self.strategies:
            return []

        # Recopilar señales de todas las estrategias
        strategy_signals: dict[str, list[Signal]] = {}

        for name, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(market_data)
                strategy_signals[name] = signals
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.warning(f"Error generating signals from {name}: {e}")
                strategy_signals[name] = []

        return self._combine_signals(strategy_signals, market_data)

    def _combine_signals(
        self, strategy_signals: dict[str, list[Signal]], market_data: Quote
    ) -> list[Signal]:
        """
        Combinar señales por votación mayoritaria.

        Args:
            strategy_signals: Dict con señales por estrategia
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales votadas
        """
        # Contar votos por símbolo y tipo
        votes: dict[str, dict[SignalType, list[tuple[str, Signal]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for strategy_name, signals in strategy_signals.items():
            for signal in signals:
                votes[signal.symbol][signal.signal_type].append((strategy_name, signal))

        combined_signals: list[Signal] = []
        total_strategies = len(self.strategies)

        for symbol, type_votes in votes.items():
            for signal_type, voted_signals in type_votes.items():
                num_votes = len(voted_signals)

                # Verificar criterios de votación
                if num_votes < self.min_votes:
                    continue

                if self.require_majority and num_votes <= total_strategies / 2:
                    continue

                # Calcular confianza promedio
                avg_confidence: float = float(np.mean([s.confidence for _, s in voted_signals]))

                # Boost si es unánime
                is_unanimous = num_votes == total_strategies
                if is_unanimous:
                    avg_confidence = min(avg_confidence * self.unanimous_boost, 100.0)

                # Usar señal con mayor confianza como base
                best_signal = max(voted_signals, key=lambda x: x[1].confidence)
                _, base_signal = best_signal

                # Convertir signal_type a enum si es string
                signal_type_enum = (
                    signal_type if isinstance(signal_type, SignalType) else SignalType(signal_type)
                )

                # Calcular priority_score con cap en 100
                priority = min(100.0, float(avg_confidence) * (num_votes / total_strategies))

                # Crear señal combinada
                combined_signal = Signal(
                    symbol=symbol,
                    signal_type=signal_type_enum,
                    strength=self._map_confidence_to_strength(float(avg_confidence)),
                    price=base_signal.price,
                    timestamp=base_signal.timestamp,
                    confidence=float(avg_confidence),
                    liquidity_score=base_signal.liquidity_score,
                    priority_score=priority,
                    source=SignalSource.TECHNICAL,
                    volume=base_signal.volume,
                    metadata={
                        "ensemble_type": "voting",
                        "votes": num_votes,
                        "total_strategies": total_strategies,
                        "vote_ratio": num_votes / total_strategies,
                        "is_unanimous": is_unanimous,
                        "voting_strategies": [name for name, _ in voted_signals],
                    },
                )
                combined_signals.append(combined_signal)

        return combined_signals

    @staticmethod
    def _map_confidence_to_strength(confidence: float) -> SignalStrength:
        """Mapear confianza a strength."""
        if confidence >= 80.0:
            return SignalStrength.VERY_STRONG
        if confidence >= 70.0:
            return SignalStrength.STRONG
        if confidence >= 50.0:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK
