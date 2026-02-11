"""
MeanReversionStrategyEngine - Engine de estrategia de reversión a la media.

Refactorización de MeanReversionStrategy como Strategy Engine con:
- Integración con Learning Engines
- Feature extraction estandarizado (Z-score adaptativo)
- Soporte para callbacks
- Métricas mejoradas
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.core.config.base import get_config
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.momentum_analysis import TechnicalIndicatorCalculator

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class MeanReversionStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de reversión a la media basada en Z-score.

    Extiende BaseStrategyEngine con:
    - Feature extraction para Learning Engines (Z-score adaptativo)
    - Integración con predicciones de ML
    - Callbacks para aprendizaje continuo
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar mean reversion strategy engine.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Load strategy-specific configuration from centralized config
        centralized_config = get_config()
        strategy_config = centralized_config.get_strategy_config("mean_reversion")
        if strategy_config:
            params = strategy_config.parameters
            self.z_score_threshold = Decimal(str(params.get("z_score_threshold")))
            self.lookback_period = params.get("lookback_period")
            self.volatility_threshold = Decimal(str(params.get("volatility_threshold")))
            self.mean_reversion_speed = Decimal(str(params.get("mean_reversion_speed")))
            self.atr_floor = Decimal(str(params.get("atr_floor")))
            self.price_range_multiplier = Decimal(str(params.get("price_range_multiplier")))

            # Risk parameters from centralized config with fallback to strategy config
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or centralized_config.trading.stop_loss_pct)
            )
            self.take_profit = Decimal(
                str(strategy_config.stop_loss_pct or centralized_config.trading.take_profit_pct)
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or centralized_config.trading.max_position_size)
            )
        else:
            # Fallback to config or defaults
            self.z_score_threshold = Decimal(str(config.get("z_score_threshold", 2.0)))
            self.lookback_period = config.get("lookback_period", 20)
            self.stop_loss = Decimal(
                str(config.get("stop_loss", centralized_config.trading.stop_loss_pct))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", centralized_config.trading.take_profit_pct))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", centralized_config.trading.max_position_size))
            )
            self.volatility_threshold = Decimal(str(config.get("volatility_threshold", 0.02)))
            self.mean_reversion_speed = Decimal(str(config.get("mean_reversion_speed", 0.1)))
            self.atr_floor = Decimal(str(config.get("atr_floor", 0.01)))
            self.price_range_multiplier = Decimal(str(config.get("price_range_multiplier", 2.0)))

        # Additional parameters
        min_z_score_value = config.get("min_z_score")
        if min_z_score_value is None and strategy_config:
            min_z_score_value = strategy_config.parameters.get("min_z_score", 1.5)
        elif min_z_score_value is None:
            min_z_score_value = 1.5
        self.min_z_score = Decimal(str(min_z_score_value))

        # Price history
        self.price_history = deque(maxlen=200)

        # Technical indicator calculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        logger.info(f"MeanReversionStrategyEngine initialized: {self.name}")
        config_value = (
            strategy_config.parameters.get('z_score_threshold') if strategy_config else 'NO_CONFIG'
        )
        logger.info(
            f"⚠️ CRITICAL: z_score_threshold={self.z_score_threshold} (target: 1.0, config loaded: {config_value})"
        )

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "mean_reversion"

    def extract_features(
        self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None
    ) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Incluye Z-score adaptativo y métricas de volatilidad.

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
        else:
            prices = [float(q.close or q.bid or q.last or 0) for q in historical_data]

        # Calcular indicadores si hay suficiente histórico
        if len(prices) >= self.lookback_period:
            current_price = features["price"]

            # Z-score (reversión a la media)
            # Usar pandas-ta para calcular mean y std
            import pandas as pd

            df = pd.DataFrame({'close': prices})
            mean = df['close'].rolling(window=self.lookback_period).mean().iloc[-1]
            std = df['close'].rolling(window=self.lookback_period).std().iloc[-1]

            if std is not None and std > 0 and not pd.isna(std):
                z_score = (current_price - mean) / std
                features["z_score"] = float(z_score)
                features["mean"] = float(mean)
                features["std"] = float(std)
                features["price_mean_distance"] = (
                    float((current_price - mean) / mean) if mean > 0 else 0.0
                )
            else:
                features["z_score"] = 0.0
                features["mean"] = current_price
                features["std"] = 0.0
                features["price_mean_distance"] = 0.0

            # Volatilidad (ATR relativo)
            if len(prices) >= 20:
                # Calcular ATR simplificado
                highs = [p * 1.02 for p in prices[-20:]]  # Approximation
                lows = [p * 0.98 for p in prices[-20:]]  # Approximation
                atr = self.indicator_calculator.calculate_atr(highs, lows, prices[-20:], period=14)
                if atr is not None and current_price > 0:
                    features["atr"] = float(atr)
                    features["relative_atr"] = float(atr / current_price)
                    features["volatility"] = features["relative_atr"]
                else:
                    features["atr"] = 0.0
                    features["relative_atr"] = 0.0
                    features["volatility"] = 0.0

            # Price range metrics
            if len(prices) >= self.lookback_period:
                period_high = max(prices[-self.lookback_period :])
                period_low = min(prices[-self.lookback_period :])
                price_range = period_high - period_low

                features["period_high"] = float(period_high)
                features["period_low"] = float(period_low)
                features["price_range"] = float(price_range)
                if period_high > period_low:
                    features["price_position_in_range"] = float(
                        (current_price - period_low) / (period_high - period_low)
                    )
                else:
                    features["price_position_in_range"] = 0.5
        else:
            # Defaults cuando no hay suficiente histórico
            features["z_score"] = 0.0
            features["mean"] = features["price"]
            features["std"] = 0.0
            features["price_mean_distance"] = 0.0
            features["atr"] = 0.0
            features["relative_atr"] = 0.0
            features["volatility"] = 0.0
            features["period_high"] = features["price"]
            features["period_low"] = features["price"]
            features["price_range"] = 0.0
            features["price_position_in_range"] = 0.5

        return features

    def _get_signal_strength(self, confidence: float) -> SignalStrength:
        """Convert confidence to signal strength."""
        if confidence >= 80.0:
            return SignalStrength.VERY_STRONG
        elif confidence >= 70.0:
            return SignalStrength.STRONG
        elif confidence >= 50.0:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def _create_signal(
        self,
        market_data: Quote,
        signal_type: SignalType,
        confidence: float,
        current_price: float,
        z_score: float,
        mean: float,
        std: float,
        volatility: float,
    ) -> Signal:
        """Create a signal with metadata."""
        strength = self._get_signal_strength(confidence)
        return Signal(
            symbol=market_data.symbol,
            signal_type=signal_type,
            strength=strength,
            price=Decimal(str(current_price)),
            timestamp=market_data.timestamp if hasattr(market_data, 'timestamp') else None,
            confidence=confidence,
            liquidity_score=70.0,
            priority_score=confidence * 0.8,
            source=SignalSource.MEAN_REVERSION,
            volume=Decimal("1"),
            metadata={
                'strategy': self.name,
                'z_score': float(z_score),
                'mean': float(mean),
                'std': float(std),
                'volatility': volatility,
                'price_mean_distance': (float((current_price - mean) / mean) if mean > 0 else 0.0),
            },
        )

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementación específica de generación de señales para mean reversion.

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

            self.price_history.append(current_price)

            if len(self.price_history) < self.lookback_period:
                return []

            import pandas as pd

            df = pd.DataFrame({'close': list(self.price_history)})
            mean = df['close'].rolling(window=self.lookback_period).mean().iloc[-1]
            std = df['close'].rolling(window=self.lookback_period).std().iloc[-1]

            if std is None or std <= 0 or pd.isna(std):
                return []

            z_score = (current_price - mean) / std
            z_score_decimal = Decimal(str(z_score))
            volatility = float(std / mean) if mean > 0 else 0.0

            buy_condition = (
                z_score_decimal <= -self.z_score_threshold
                and z_score_decimal <= -self.min_z_score
                and volatility <= float(self.volatility_threshold)
            )

            sell_condition = z_score_decimal >= self.z_score_threshold and volatility <= float(
                self.volatility_threshold
            )

            if buy_condition:
                confidence = self._calculate_confidence(
                    abs(float(z_score_decimal)), volatility, is_oversold=True
                )
                signal = self._create_signal(
                    market_data,
                    SignalType.BUY,
                    confidence,
                    current_price,
                    z_score,
                    mean,
                    std,
                    volatility,
                )
                signals.append(signal)
            elif sell_condition:
                confidence = self._calculate_confidence(
                    abs(float(z_score_decimal)), volatility, is_oversold=False
                )
                signal = self._create_signal(
                    market_data,
                    SignalType.SELL,
                    confidence,
                    current_price,
                    z_score,
                    mean,
                    std,
                    volatility,
                )
                signals.append(signal)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(
                f"Error generando señal en MeanReversionStrategyEngine: {e}", exc_info=True
            )

        return signals

    def _calculate_confidence(
        self, abs_z_score: float, volatility: float, is_oversold: bool
    ) -> float:
        """
        Calcular confidence de la señal basado en Z-score y volatilidad.

        Args:
            abs_z_score: Valor absoluto del Z-score
            volatility: Volatilidad relativa
            is_oversold: Si es condición de oversold (BUY) o overbought (SELL)

        Returns:
            Confidence entre 0 y 100
        """
        confidence = 50.0

        if abs_z_score >= 3.0:
            confidence += 30.0
        elif abs_z_score >= 2.5:
            confidence += 25.0
        elif abs_z_score >= 2.0:
            confidence += 20.0
        elif abs_z_score >= 1.5:
            confidence += 15.0

        # Volatility thresholds from config (very low and low volatility for confidence bonus)
        centralized_config = get_config()
        vol_very_low = centralized_config.trading.get("volatility_confidence_very_low", 0.01)
        vol_low = centralized_config.trading.get("volatility_confidence_low", 0.02)

        if volatility < vol_very_low:
            confidence += 10.0
        elif volatility < vol_low:
            confidence += 5.0

        return min(100.0, max(0.0, confidence))

    def get_required_parameters(self) -> List[str]:
        """Obtener parámetros requeridos."""
        return [
            "z_score_threshold",
            "lookback_period",
            "volatility_threshold",
            "stop_loss",
            "take_profit",
            "max_position_size",
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
        min_confidence = self.config.get("min_signal_confidence", 50.0)
        if signal.confidence < min_confidence:
            logger.debug(
                f"Risk check fallido: confidence {signal.confidence:.2f} < {min_confidence:.2f}"
            )
            return False

        # Verificar volatilidad (mean reversion requiere volatilidad controlada)
        volatility = signal.metadata.get('volatility', 0.0)
        if volatility > float(self.volatility_threshold * 2):  # Permitir hasta 2x el threshold
            logger.debug(f"Risk check fallido: volatilidad {volatility:.4f} muy alta")
            return False

        return True
