"""
MomentumStrategyEngine - Engine de estrategia de momentum.

Refactorización de MomentumStrategy como Strategy Engine con:
- Integración con Learning Engines
- Feature extraction estandarizado
- Soporte para callbacks
- Métricas mejoradas
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator
from app.domain.services.signals.scoring import get_signal_scoring_engine
from app.shared.config.centralized_config import get_config

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class MomentumStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de momentum basada en RSI, EMA y volumen.

    Extiende BaseStrategyEngine con:
    - Feature extraction para Learning Engines
    - Integración con predicciones de ML
    - Callbacks para aprendizaje continuo
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar momentum strategy engine.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Initialize all parameters with defaults FIRST
        self.rsi_period = config.get("rsi_period", 14)
        self.ema_period = config.get("ema_period", 20)
        self.lookback_period = config.get("lookback_period", 5)

        # ATR volatility filter settings
        self.min_atr_threshold = Decimal(str(config.get("min_atr_threshold", 0.015)))
        self.atr_filter_enabled = config.get("atr_filter_enabled", True)
        self.use_relative_atr = config.get("use_relative_atr", True)

        # Load strategy-specific configuration from centralized config
        centralized_config = get_config()
        strategy_cfg = centralized_config.get_strategy_config("momentum")

        if strategy_cfg:
            params = strategy_cfg.parameters
            if isinstance(params, dict):
                try:
                    self.config.update({k: v for k, v in params.items() if v is not None})
                    config.update({k: v for k, v in params.items() if v is not None})
                except (FileNotFoundError, ValueError, KeyError, TypeError):
                    pass

            # Core thresholds
            self.rsi_threshold = Decimal(
                str(params.get("rsi_threshold_buy") or params.get("rsi_threshold"))
            )
            self.momentum_threshold = Decimal(str(params.get("momentum_threshold")))
            self.volume_threshold = Decimal(str(params.get("volume_threshold")))

            # Risk parameters - use centralized config with fallback to strategy config
            self.stop_loss = Decimal(
                str(strategy_cfg.stop_loss_pct or centralized_config.trading.stop_loss_pct)
            )
            self.take_profit = Decimal(
                str(strategy_cfg.take_profit_pct or centralized_config.trading.take_profit_pct)
            )
            self.max_position_size = Decimal(
                str(strategy_cfg.max_position_size or centralized_config.trading.max_position_size)
            )
            self.max_exposure = Decimal(str(params.get("max_exposure", 0.60)))

            # Technical indicator periods
            if "ema_period" in params:
                self.ema_period = params.get("ema_period", self.ema_period)
            if "lookback_period" in params:
                self.lookback_period = params.get("lookback_period", self.lookback_period)
            if "rsi_period" in params:
                self.rsi_period = params.get("rsi_period", self.rsi_period)

            # ATR/Stochastic RSI filters
            if "atr_filter_enabled" in params:
                self.atr_filter_enabled = params.get("atr_filter_enabled", self.atr_filter_enabled)
            if "use_relative_atr" in params:
                self.use_relative_atr = params.get("use_relative_atr", self.use_relative_atr)
            if "min_atr_threshold" in params:
                self.min_atr_threshold = Decimal(
                    str(params.get("min_atr_threshold", self.min_atr_threshold))
                )

        # Price history
        self.price_history = deque(maxlen=200)
        self.high_history = deque(maxlen=200)
        self.low_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)

        # Technical indicator calculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Signal scoring engine
        self.signal_scorer = get_signal_scoring_engine()

        logger.info(
            "MomentumStrategyEngine initialized",
            extra={
                "strategy_name": self.name,
                "strategy_type": "momentum",
                "rsi_period": self.rsi_period,
                "ema_period": self.ema_period,
                "rsi_threshold": float(self.rsi_threshold),
                "momentum_threshold": float(self.momentum_threshold),
                "volume_threshold": float(self.volume_threshold),
                "atr_filter_enabled": self.atr_filter_enabled,
            },
        )

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "momentum"

    def extract_features(
        self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None
    ) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional (si no se provee, usa self.price_history)

        Returns:
            Diccionario con features estandarizados
        """
        features = {
            "timestamp": market_data.timestamp if hasattr(market_data, 'timestamp') else None,
            "symbol": market_data.symbol,
            "price": float(market_data.close or market_data.bid or market_data.last or 0),
        }

        # Usar histórico interno si no se provee
        if historical_data is None:
            prices = list(self.price_history) if self.price_history else []
            highs = list(self.high_history) if self.high_history else []
            lows = list(self.low_history) if self.low_history else []
            volumes = list(self.volume_history) if self.volume_history else []
        else:
            prices = [float(q.close or q.bid or q.last or 0) for q in historical_data]
            highs = [float(getattr(q, 'high', q.close or 0)) for q in historical_data]
            lows = [float(getattr(q, 'low', q.close or 0)) for q in historical_data]
            volumes = [float(getattr(q, 'volume', 0)) for q in historical_data]

        # Calcular indicadores técnicos si hay suficiente histórico
        if len(prices) >= max(self.rsi_period, self.ema_period):
            # RSI
            rsi = self.indicator_calculator.calculate_rsi(prices, period=self.rsi_period)
            features["rsi"] = float(rsi) if rsi is not None else 50.0

            # EMA
            ema = self.indicator_calculator.calculate_ema(prices, period=self.ema_period)
            features["ema"] = float(ema) if ema is not None else features["price"]

            # Momentum/ROC
            momentum = self.indicator_calculator.calculate_roc(prices, period=self.lookback_period)
            features["momentum"] = float(momentum) if momentum is not None else 0.0

            # Volume
            if len(volumes) >= 20:
                avg_volume = sum(volumes[-20:]) / 20
                current_volume = volumes[-1] if volumes else 0
                features["volume_ratio"] = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                features["volume_ratio"] = 1.0

            # ATR
            if len(highs) > 0 and len(lows) > 0:
                atr = self.indicator_calculator.calculate_atr(highs, lows, prices, period=14)
                features["atr"] = float(atr) if atr is not None else 0.0
                if features["price"] > 0:
                    features["relative_atr"] = features["atr"] / features["price"]

            # Price position relative to EMA
            if features["ema"] > 0:
                features["price_ema_ratio"] = features["price"] / features["ema"]
                features["price_above_ema"] = features["price"] > features["ema"]
        else:
            # Defaults cuando no hay suficiente histórico
            features["rsi"] = 50.0
            features["ema"] = features["price"]
            features["momentum"] = 0.0
            features["volume_ratio"] = 1.0
            features["atr"] = 0.0
            features["relative_atr"] = 0.0
            features["price_ema_ratio"] = 1.0
            features["price_above_ema"] = True

        return features

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementación específica de generación de señales para momentum.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price <= 0:
                return []

            # Actualizar histórico
            self.price_history.append(current_price)
            self.high_history.append(float(market_data.high or current_price))
            self.low_history.append(float(market_data.low or current_price))
            self.volume_history.append(float(market_data.volume or 0))

            # Necesitamos suficiente histórico
            min_history = max(self.rsi_period, self.ema_period)
            if len(self.price_history) < min_history:
                return []

            # Calcular indicadores
            prices = list(self.price_history)
            highs = list(self.high_history)
            lows = list(self.low_history)
            volumes = list(self.volume_history)

            rsi = self.indicator_calculator.calculate_rsi(prices, period=self.rsi_period)
            ema = self.indicator_calculator.calculate_ema(prices, period=self.ema_period)
            momentum = self.indicator_calculator.calculate_roc(prices, period=self.lookback_period)

            if rsi is None or ema is None or momentum is None:
                return []

            # Calcular ratio de volumen
            if len(volumes) >= 20:
                avg_volume = sum(volumes[-20:]) / 20
                current_volume = volumes[-1] if volumes else 0
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0

            # ATR filter (si está habilitado)
            if self.atr_filter_enabled:
                atr = self.indicator_calculator.calculate_atr(highs, lows, prices, period=14)
                if atr is not None and self.use_relative_atr:
                    relative_atr = (atr / current_price) * 100 if current_price > 0 else 0
                    if relative_atr < float(self.min_atr_threshold * 100):
                        logger.debug(
                            "Señal filtrada por ATR bajo",
                            extra={
                                "strategy": "momentum",
                                "symbol": market_data.symbol,
                                "relative_atr_pct": relative_atr,
                                "min_atr_threshold_pct": float(self.min_atr_threshold * 100),
                                "filter_reason": "low_atr",
                            },
                        )
                        return []

            # Condiciones para señal BUY
            price_above_ema = current_price > ema
            rsi_buy_condition = rsi < float(self.rsi_threshold)  # RSI bajo = momentum alcista
            momentum_positive = momentum > float(self.momentum_threshold)
            volume_above_threshold = volume_ratio > float(self.volume_threshold)

            if (
                price_above_ema
                and rsi_buy_condition
                and momentum_positive
                and volume_above_threshold
            ):
                # Calcular confidence
                confidence = self._calculate_confidence(
                    rsi, momentum, volume_ratio, price_above_ema
                )

                # Calcular strength
                if confidence >= 80.0:
                    strength = SignalStrength.VERY_STRONG
                elif confidence >= 70.0:
                    strength = SignalStrength.STRONG
                elif confidence >= 50.0:
                    strength = SignalStrength.MODERATE
                else:
                    strength = SignalStrength.WEAK

                signal = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=strength,
                    price=Decimal(str(current_price)),
                    timestamp=market_data.timestamp if hasattr(market_data, 'timestamp') else None,
                    confidence=confidence,
                    liquidity_score=min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)),
                    priority_score=confidence * 0.7
                    + min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)) * 0.3,
                    source=SignalSource.MOMENTUM,
                    volume=Decimal("1"),  # Placeholder
                    metadata={
                        'strategy': self.name,
                        'rsi': rsi,
                        'ema': ema,
                        'momentum': momentum,
                        'volume_ratio': volume_ratio,
                    },
                )

                signals.append(signal)
                logger.info(
                    "Signal generated",
                    extra={
                        "strategy": "momentum",
                        "signal_type": "BUY",
                        "symbol": market_data.symbol,
                        "price": float(current_price),
                        "confidence": float(confidence),
                        "rsi": float(rsi),
                        "momentum": float(momentum),
                        "volume_ratio": float(volume_ratio),
                    },
                )

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(
                "Error generando señal en MomentumStrategyEngine",
                extra={
                    "strategy": "momentum",
                    "symbol": getattr(market_data, 'symbol', None),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        return signals

    def _calculate_confidence(
        self, rsi: float, momentum: float, volume_ratio: float, price_above_ema: bool
    ) -> float:
        """
        Calcular confidence de la señal basado en múltiples factores.

        Args:
            rsi: Valor de RSI
            momentum: Valor de momentum/ROC
            volume_ratio: Ratio de volumen
            price_above_ema: Si el precio está arriba de la EMA

        Returns:
            Confidence entre 0 y 100
        """
        try:
            config = get_config()

            # Base confidence
            confidence = 50.0

            # RSI contribution (RSI bajo = más momentum alcista)
            rsi_very_oversold = float(getattr(config.trading, 'momentum_rsi_very_oversold', 30.0))
            rsi_oversold = float(getattr(config.trading, 'momentum_rsi_oversold', 40.0))
            rsi_neutral_low = float(getattr(config.trading, 'momentum_rsi_neutral_low', 50.0))

            if rsi < rsi_very_oversold:
                confidence += 20.0
            elif rsi < rsi_oversold:
                confidence += 15.0
            elif rsi < rsi_neutral_low:
                confidence += 10.0

            # Momentum contribution
            momentum_high_threshold = float(
                getattr(config.trading, 'momentum_confidence_high_threshold', 0.05)
            )
            momentum_medium_threshold = float(
                getattr(config.trading, 'momentum_confidence_medium_threshold', 0.02)
            )

            if momentum > momentum_high_threshold:
                confidence += 15.0
            elif momentum > momentum_medium_threshold:
                confidence += 10.0

            # Volume contribution
            volume_high_threshold = float(
                getattr(config.trading, 'momentum_volume_ratio_high_threshold', 2.0)
            )
            volume_medium_threshold = float(
                getattr(config.trading, 'momentum_volume_ratio_medium_threshold', 1.5)
            )

            if volume_ratio > volume_high_threshold:
                confidence += 10.0
            elif volume_ratio > volume_medium_threshold:
                confidence += 5.0

            # EMA contribution
            if price_above_ema:
                confidence += 5.0

            return min(100.0, max(0.0, confidence))

        except (ValueError, AttributeError, KeyError) as e:
            logger.error(f"Error calculating confidence in MomentumStrategyEngine: {e}")
            # Fallback to original hardcoded values
            confidence = 50.0
            if rsi < 30:
                confidence += 20.0
            elif rsi < 40:
                confidence += 15.0
            elif rsi < 50:
                confidence += 10.0
            if momentum > 0.05:
                confidence += 15.0
            elif momentum > 0.02:
                confidence += 10.0
            if volume_ratio > 2.0:
                confidence += 10.0
            elif volume_ratio > 1.5:
                confidence += 5.0
            if price_above_ema:
                confidence += 5.0
            return min(100.0, max(0.0, confidence))

    def get_required_parameters(self) -> List[str]:
        """Obtener parámetros requeridos."""
        return [
            "rsi_threshold",
            "momentum_threshold",
            "volume_threshold",
            "rsi_period",
            "ema_period",
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
        # Verificar exposición máxima
        current_exposure = portfolio.get_total_exposure()
        if current_exposure >= float(self.max_exposure):
            logger.debug(
                "Risk check fallido: exposición excedida",
                extra={
                    "strategy": "momentum",
                    "symbol": signal.symbol,
                    "current_exposure": current_exposure,
                    "max_exposure": float(self.max_exposure),
                    "check_type": "exposure",
                },
            )
            return False

        # Verificar confidence mínima
        min_confidence = self.config.get("min_signal_confidence", 50.0)
        if signal.confidence < min_confidence:
            logger.debug(
                "Risk check fallido: confidence insuficiente",
                extra={
                    "strategy": "momentum",
                    "symbol": signal.symbol,
                    "signal_confidence": signal.confidence,
                    "min_confidence": min_confidence,
                    "check_type": "confidence",
                },
            )
            return False

        return True
