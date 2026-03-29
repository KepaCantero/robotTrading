"""
ModularMomentumStrategyEngine - Engine de estrategia de momentum modular.

Refactorización de ModularMomentumStrategy como Strategy Engine con:
- Arquitectura modular de filtros
- Integración mejorada con Learning Engines (usando BaseStrategyEngine)
- Feature extraction estandarizado
- Soporte para callbacks
- Métricas mejoradas
"""

import logging
from collections import deque
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import numpy as np

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator
from app.domain.strategies.momentum_modular.modules.filters import (
    ATRFilter,
    EMAFilter,
    MomentumFilter,
    RSIFilter,
    StochRSIFilter,
    VolumeFilter,
)
from app.domain.strategies.momentum_modular.modules.market_analyzer import MarketAnalyzer

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class ModularMomentumStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de momentum completamente modular con learning engines integrado.

    Extiende BaseStrategyEngine con:
    - Arquitectura modular de filtros activables/desactivables
    - Integración mejorada con Learning Engines
    - Feature extraction usando FeatureExtractor existente
    - Análisis de contexto de mercado
    - Ajuste dinámico de thresholds basado en predicciones
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar modular momentum strategy engine.

        Args:
            config: Configuración desde YAML (momentum_modular.yaml)
        """
        super().__init__(config)

        # Configuración
        self.preset = config.get("preset", "balanced")
        self.presets_config = config.get("presets", {})
        self.current_preset = self.presets_config.get(self.preset, {})

        # Módulos de análisis
        # Usar ContextEngine si está disponible, sino usar MarketAnalyzer como fallback
        if self.context_engine_enabled and self.context_engine:
            self.market_analyzer = None  # Usar ContextEngine en su lugar
            logger.info("Usando ContextEngine para análisis de mercado")
        else:
            self.market_analyzer = MarketAnalyzer(config.get("market_analyzer", {}))
            logger.info("Usando MarketAnalyzer para análisis de mercado")

        # Filtros modulares
        modules_config = config.get("modules", {})
        self.filters = []
        filter_classes = {
            "ema_filter": EMAFilter,
            "rsi_filter": RSIFilter,
            "stoch_rsi_filter": StochRSIFilter,
            "momentum_filter": MomentumFilter,
            "volume_filter": VolumeFilter,
            "atr_filter": ATRFilter,
        }

        for filter_name, filter_class in filter_classes.items():
            if filter_name in modules_config:
                filter_config = modules_config[filter_name]
                if filter_config.get("enabled", True):
                    filter_instance = filter_class(filter_config, preset=self.preset)
                    self.filters.append(filter_instance)
                    logger.info(f"✅ Filtro activado: {filter_name}")

        # Learning engine integration (usar BaseStrategyEngine methods)
        learning_config = config.get("adaptive_learning", {})
        if learning_config.get("enabled", False):
            self.learning_config = learning_config
            self._learning_engine_type = learning_config.get("engine_type", "supervised")
            # El learning engine se inicializará lazy cuando se necesite
            # Usaremos self.set_learning_engine() de BaseStrategyEngine cuando esté listo
        else:
            self.learning_config = None
            self._learning_engine_type = None

        # Feature extractor para learning engines (import lazy)
        self._feature_extractor = None

        # Thresholds configurables
        self.min_success_probability = self.current_preset.get("min_confidence", 0.6)
        combination_mode = self.current_preset.get("combination_mode", "MAJORITY")
        self.combination_mode = combination_mode  # "ALL", "MAJORITY", "ANY"

        # Históricos para indicadores
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.price_history = deque(maxlen=200)
        self.high_history = deque(maxlen=200)
        self.low_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)
        self.atr_history = deque(maxlen=100)

        # Histórico de trades para metadata
        self.recent_trades: deque = deque(maxlen=10)

        # Histórico de features para Deep Learning / Transformer (secuencias)
        self.features_history = deque(maxlen=200)

        logger.info(
            f"✅ ModularMomentumStrategyEngine inicializada (preset: {self.preset}, "
            f"{len(self.filters)} filtros activos, "
            f"learning: {'✅ configurado' if self.learning_config else '❌'})"
        )

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "modular_momentum"

    def extract_features(
        self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None
    ) -> dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Usa el FeatureExtractor de momentum_modular para mantener compatibilidad.

        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional

        Returns:
            Diccionario con features estandarizados
        """
        # Inicializar FeatureExtractor lazy
        if self._feature_extractor is None:
            try:
                from app.domain.strategies.momentum_modular.learning.feature_extractor import (
                    FeatureExtractor,
                )

                self._feature_extractor = FeatureExtractor()
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.warning(f"No se pudo inicializar FeatureExtractor: {e}")
                return {}

        # Calcular indicadores actuales
        if len(self.price_history) < 26:
            return {}

        indicators = self._calculate_indicators()

        # Analizar contexto de mercado (usa ContextEngine si está disponible)
        market_context = self._get_market_context(market_data)

        # Evaluar filtros
        filter_results = self._evaluate_filters(indicators, market_context)

        # Preparar metadata
        metadata = {
            "timestamp": (
                market_data.timestamp if hasattr(market_data, "timestamp") else datetime.now()
            ),
            "symbol": market_data.symbol,
            "recent_trades": list(self.recent_trades),
            "recent_win_rate": self._calculate_recent_win_rate(),
        }

        # Usar FeatureExtractor para extraer features completos
        try:
            features = self._feature_extractor.extract_complete_features(
                indicators=indicators,
                filter_results=filter_results,
                market_context=market_context,
                metadata=metadata,
            )
            return features
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Error extrayendo features: {e}")
            # Fallback: features básicos
            return {
                "indicators": indicators,
                "filter_results": filter_results,
                "market_context": market_context,
                "metadata": metadata,
            }

    def _generate_signals_impl(self, market_data: Quote) -> list[Signal]:
        """
        Implementación específica de generación de señales para modular momentum.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # 1. Actualizar históricos
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price <= 0:
                return []

            self.price_history.append(current_price)
            self.high_history.append(float(market_data.high or current_price))
            self.low_history.append(float(market_data.low or current_price))
            self.volume_history.append(float(market_data.volume or 0))

            # Necesitamos suficiente histórico
            min_history = 60
            if len(self.price_history) < min_history:
                return []

            # 2. Calcular indicadores técnicos
            indicators = self._calculate_indicators()
            if not indicators:
                return []

            # 3. Analizar contexto de mercado
            price_list = list(self.price_history)
            atr_list = list(self.atr_history) if self.atr_history else []
            market_context = self.market_analyzer.analyze(market_data, price_list, atr_list)

            # 4. Evaluar todos los filtros
            filter_results = self._evaluate_filters(indicators, market_context)

            # 5. Generar señal candidata basada en filtros
            signal_type = self._determine_signal_type(filter_results, market_context)

            if signal_type is None:
                return []

            # 6. Learning prediction se obtiene automáticamente via BaseStrategyEngine.generate_signals()
            # Aquí solo necesitamos preparar la señal base

            # 7. Crear señal base (el wrapper de BaseStrategyEngine aplicará ajustes de learning)
            confidence = self._calculate_signal_confidence(
                filter_results, None
            )  # Learning se aplicará después

            # Calcular strength basado en confidence
            if confidence >= 80.0:
                strength = SignalStrength.VERY_STRONG
            elif confidence >= 70.0:
                strength = SignalStrength.STRONG
            elif confidence >= 50.0:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # Validación de seguridad
            if (
                strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]
                and confidence < 70.0
            ) or (strength == SignalStrength.WEAK and confidence > 80.0):
                strength = SignalStrength.MODERATE

            # Calcular liquidity_score
            volume_ratio = indicators.get("volume_ratio", 1.0)
            liquidity_score = min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0))

            # Calcular priority_score
            priority_score = (confidence * 0.7) + (liquidity_score * 0.3)

            # Obtener volume
            volume = Decimal(str(getattr(market_data, "volume", 0)))
            if volume == 0:
                volume = Decimal("0.01")

            signal = Signal(
                symbol=market_data.symbol,
                signal_type=signal_type,
                strength=strength,
                price=Decimal(str(current_price)),
                timestamp=(
                    market_data.timestamp if hasattr(market_data, "timestamp") else datetime.now()
                ),
                confidence=confidence,
                liquidity_score=liquidity_score,
                priority_score=priority_score,
                source=SignalSource.MOMENTUM,
                volume=volume,
                metadata={
                    "strategy": self.name,
                    "indicators": indicators,
                    "market_context": market_context,
                    "filter_results": {
                        name: {"passed": res.get("passed"), "confidence": res.get("confidence")}
                        for name, res in filter_results.items()
                    },
                    "preset": self.preset,
                },
            )

            signals.append(signal)

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(
                f"Error generando señal en ModularMomentumStrategyEngine: {e}", exc_info=True
            )

        return signals

    # ===== Métodos helper =====

    def _get_market_context(self, market_data: Quote) -> dict[str, Any]:
        """
        Obtener contexto de mercado usando ContextEngine si está disponible, sino MarketAnalyzer.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Dict con contexto de mercado
        """
        price_list = list(self.price_history)
        atr_list = list(self.atr_history) if self.atr_history else []

        # Usar ContextEngine si está disponible y hay suficientes datos
        if self.context_engine_enabled and self.context_engine and len(price_list) >= 100:
            try:
                context_result = self.get_context_analysis(price_list)
                if context_result:
                    # Convertir resultado de ContextEngine a formato compatible con MarketAnalyzer
                    regime = context_result.get("regime", "unknown")
                    volatility_result = self.get_volatility_regime(price_list)

                    market_context = {
                        "type": regime,
                        "confidence": context_result.get("confidence", 0.5),
                        "volatility_regime": (
                            volatility_result.get("regime", "normal")
                            if volatility_result
                            else "normal"
                        ),
                        "trend_strength": context_result.get("regime_probabilities", {}).get(
                            "bull", 0.0
                        ),
                        "volatility_percentile": (
                            volatility_result.get("percentile", 50) if volatility_result else 50
                        ),
                        "in_range": False,  # ContextEngine no proporciona esto directamente
                    }
                    return market_context
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.warning(
                    f"Error usando ContextEngine, usando MarketAnalyzer como fallback: {e}"
                )

        # Fallback a MarketAnalyzer
        if self.market_analyzer:
            return self.market_analyzer.analyze(market_data, price_list, atr_list)
        else:
            # Fallback mínimo si no hay ningún analyzer
            return {
                "type": "unknown",
                "confidence": 0.5,
                "volatility_regime": "normal",
                "trend_strength": 0.0,
                "volatility_percentile": 50,
                "in_range": False,
            }

    def _calculate_indicators(self) -> dict[str, Any]:
        """Calcular todos los indicadores técnicos necesarios."""
        if len(self.price_history) < 26:
            return {}

        prices = list(self.price_history)
        highs = list(self.high_history)
        lows = list(self.low_history)
        volumes = list(self.volume_history)

        indicators = {}

        # RSI
        rsi = self.indicator_calculator.calculate_rsi(prices, period=14)
        indicators["rsi"] = rsi if rsi is not None else 50.0

        # EMAs
        ema_fast = self.indicator_calculator.calculate_ema(prices, period=12)
        ema_slow = self.indicator_calculator.calculate_ema(prices, period=26)
        indicators["ema_fast"] = ema_fast if ema_fast is not None else 0.0
        indicators["ema_slow"] = ema_slow if ema_slow is not None else 0.0

        # Momentum / ROC
        momentum = self.indicator_calculator.calculate_roc(prices, period=14)
        indicators["momentum_roc"] = momentum if momentum is not None else 0.0

        # Volume
        if len(volumes) >= 20:
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1] if volumes else 0
            indicators["volume_ratio"] = current_volume / avg_volume if avg_volume > 0 else 1.0
            indicators["volume"] = current_volume
            indicators["avg_volume"] = avg_volume
        else:
            indicators["volume_ratio"] = 1.0
            indicators["volume"] = volumes[-1] if volumes else 0
            indicators["avg_volume"] = 0

        # ATR
        atr = self.indicator_calculator.calculate_atr(highs, lows, prices, period=14)
        if atr is not None:
            self.atr_history.append(atr)
            indicators["atr"] = atr
            current_price = prices[-1]
            indicators["relative_atr"] = (atr / current_price * 100) if current_price > 0 else 0

            # ATR percentile
            if len(self.atr_history) >= 30:
                recent_atr = list(self.atr_history)[-30:]
                sorted_atr = sorted(recent_atr)
                percentile = (
                    (sorted_atr.index(atr) / len(sorted_atr)) * 100 if atr in sorted_atr else 50
                )
                indicators["atr_percentile"] = percentile
            else:
                indicators["atr_percentile"] = 50
        else:
            indicators["atr"] = 0.0
            indicators["relative_atr"] = 0.0
            indicators["atr_percentile"] = 50.0

        # StochRSI (simplificado)
        indicators["stoch_rsi_k"] = 50.0
        indicators["stoch_rsi_d"] = 50.0

        # Precio actual
        indicators["price"] = prices[-1]

        return indicators

    def _evaluate_filters(
        self, indicators: dict[str, Any], market_context: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Evaluar todos los filtros activos."""
        filter_results = {}

        for filter_instance in self.filters:
            try:
                # Evaluar para compra (BUY)
                result_buy = filter_instance.evaluate(indicators, market_context, "BUY")
                filter_results[f"{filter_instance.name}_buy"] = result_buy

                # Evaluar para venta (SELL)
                result_sell = filter_instance.evaluate(indicators, market_context, "SELL")
                filter_results[f"{filter_instance.name}_sell"] = result_sell

                # Resultado general (usar BUY para simplificar)
                filter_results[filter_instance.name] = result_buy

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Error evaluando filtro {filter_instance.name}: {e}")
                filter_results[filter_instance.name] = {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"Error: {e!s}",
                }

        return filter_results

    def _determine_signal_type(
        self, filter_results: dict[str, dict[str, Any]], market_context: dict[str, Any]
    ) -> Optional[SignalType]:
        """Determinar tipo de señal basado en resultados de filtros."""

        if len(self.filters) == 0:
            logger.warning("⚠️ No hay filtros activos - no se pueden generar señales")
            return None

        # Contar solo los resultados principales de cada filtro
        filter_names = [f.name for f in self.filters]
        passed_filters = [
            filter_name
            for filter_name in filter_names
            if filter_name in filter_results and filter_results[filter_name].get("passed", False)
        ]

        total_filters = len(self.filters)

        logger.debug(
            f"🔍 Determinando señal: {len(passed_filters)}/{total_filters} filtros pasaron, modo={self.combination_mode}"
        )

        # Decidir según modo de combinación
        if self.combination_mode == "ALL":
            if len(passed_filters) == total_filters:
                logger.debug("✅ Todos los filtros pasaron - generando señal BUY")
                return SignalType.BUY
        elif self.combination_mode == "MAJORITY":
            required = max(1, (total_filters + 1) // 2)
            if len(passed_filters) >= required:
                logger.debug(
                    f"✅ Mayoría de filtros pasaron ({len(passed_filters)}/{total_filters}) - generando señal BUY"
                )
                return SignalType.BUY
        elif self.combination_mode == "ANY" and len(passed_filters) > 0:
            logger.debug(
                f"✅ Al menos un filtro pasó ({len(passed_filters)}) - generando señal BUY"
            )
            return SignalType.BUY

        logger.debug(
            f"❌ No se cumple el modo de combinación ({self.combination_mode}) - no se genera señal"
        )
        return None

    def _calculate_signal_confidence(
        self,
        filter_results: dict[str, dict[str, Any]],
        learning_prediction: Optional[dict[str, Any]],
    ) -> float:
        """Calcular confianza de la señal."""
        # Confianza base desde filtros
        confidences = [res.get("confidence", 0.0) for res in filter_results.values()]
        base_confidence = np.mean(confidences) if confidences else 0.5

        # Ajustar con predicción de learning engine (si está disponible)
        if learning_prediction:
            learning_confidence = learning_prediction.get(
                "confidence", learning_prediction.get("success_probability", 0.5)
            )
            # Combinar: 60% filtros, 40% learning
            combined = base_confidence * 0.6 + learning_confidence * 0.4
            return min(100.0, max(0.0, combined * 100))

        return min(100.0, max(0.0, base_confidence * 100))

    def _calculate_recent_win_rate(self) -> float:
        """Calcular win rate reciente de trades."""
        if not self.recent_trades:
            return 0.5  # Default neutral

        winning_trades = sum(1 for trade in self.recent_trades if getattr(trade, "pnl", 0) > 0)
        return winning_trades / len(self.recent_trades) if len(self.recent_trades) > 0 else 0.5

    def get_required_parameters(self) -> list[str]:
        """Obtener parámetros requeridos."""
        return [
            "preset",
            "modules",
            "min_confidence",
            "combination_mode",
        ]

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado del portfolio

        Returns:
            True si pasa el risk check
        """
        # Verificar confidence mínima
        if signal.confidence < (self.min_success_probability * 100):
            logger.debug(
                f"Risk check fallido: confidence {signal.confidence:.2f} < {self.min_success_probability * 100:.2f}"
            )
            return False

        # Verificar learning engine (si está disponible y entrenado)
        if (
            self.learning_enabled
            and self.learning_engine
            and hasattr(self.learning_engine, "is_ready")
            and self.learning_engine.is_ready()
        ):
            # Si el learning engine sugiere HOLD, rechazar señal
            prediction = self.get_learning_prediction(signal.metadata.get("quote"))
            if prediction and prediction.get("recommended_action") == "HOLD":
                logger.debug("Risk check fallido: learning engine recomienda HOLD")
                return False

        return True

    # ===== Override apply_learning_adjustments para ModularMomentum =====

    def apply_learning_adjustments(self, prediction: dict[str, Any], signal: Signal) -> Signal:
        """
        Aplicar ajustes sugeridos por Learning Engine a una señal.

        Override del método base para incluir lógica específica de ModularMomentum.

        Args:
            prediction: Predicción del Learning Engine
            signal: Señal a ajustar

        Returns:
            Señal ajustada
        """
        if not prediction:
            return signal

        # Aplicar ajustes base
        signal = super().apply_learning_adjustments(prediction, signal)

        # Ajustes específicos de ModularMomentum
        filter_adjustments = prediction.get("filter_adjustments", {})
        if filter_adjustments:
            # Aplicar ajustes a filtros dinámicamente
            for filter_name, adjustments in filter_adjustments.items():
                # Encontrar el filtro correspondiente
                for filter_instance in self.filters:
                    if filter_instance.name == filter_name:
                        # Aplicar ajustes (esto requeriría métodos en los filtros)
                        logger.debug(f"Aplicando ajustes a filtro {filter_name}: {adjustments}")
                        break

        return signal
