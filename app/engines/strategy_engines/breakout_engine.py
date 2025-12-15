"""
BreakoutStrategyEngine - Engine de estrategia de breakout.

Detecta rupturas de rango (soporte/resistencia) con confirmación de volumen.

Características principales:
- Usa una ventana configurable para definir el rango reciente (máximos/mínimos).
- Genera señales cuando el precio rompe el máximo/mínimo del rango por encima
  de un umbral porcentual configurable.
- Requiere confirmación por volumen (ratio vs volumen medio reciente).
- Integra métricas básicas (confidence, liquidity_score, priority_score).
- Extiende BaseStrategyEngine para futura integración con Learning Engines.
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.momentum_analysis import TechnicalIndicatorCalculator

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class BreakoutStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de breakout basada en rupturas de rango.

    Lógica básica:
    - Calcula un rango reciente usando máximos/mínimos de los últimos N periodos.
    - Detecta breakout alcista cuando el precio actual rompe por encima del máximo reciente
      más un umbral porcentual configurable.
    - Detecta breakout bajista cuando el precio rompe por debajo del mínimo reciente
      menos un umbral porcentual configurable.
    - Requiere confirmación por volumen (volume_ratio >= min_volume_ratio).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar BreakoutStrategyEngine.

        Args:
            config: Configuración de la estrategia.
        """
        super().__init__(config)

        # Parámetros principales
        self.lookback_period: int = int(config.get("lookback_period", 20))
        # Umbral de breakout expresado como fracción (0.01 = 1%)
        self.breakout_threshold_pct: Decimal = Decimal(
            str(config.get("breakout_threshold_pct", 0.01))
        )
        # Mínimo volumen relativo requerido (>= 1.0 significa al menos igual al promedio)
        self.min_volume_ratio: Decimal = Decimal(
            str(config.get("min_volume_ratio", 1.5))
        )
        # Exposición máxima global del portfolio (similar a MomentumStrategyEngine)
        self.max_exposure: Decimal = Decimal(
            str(config.get("max_exposure", 0.60))
        )
        # Confianza mínima para pasar risk_check
        self.min_signal_confidence: float = float(
            config.get("min_signal_confidence", 60.0)
        )

        # Históricos
        self.price_history: deque[float] = deque(maxlen=max(self.lookback_period, 100))
        self.high_history: deque[float] = deque(maxlen=max(self.lookback_period, 100))
        self.low_history: deque[float] = deque(maxlen=max(self.lookback_period, 100))
        self.volume_history: deque[float] = deque(maxlen=100)

        # Calculadora de indicadores técnicos (para ATR opcional)
        self.indicator_calculator = TechnicalIndicatorCalculator()

        logger.info(f"BreakoutStrategyEngine initialized: {self.name}")

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "breakout"

    def extract_features(
        self,
        market_data: Quote,
        historical_data: Optional[Sequence[Quote]] = None,
    ) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Features principales:
        - range_high / range_low / range_width
        - distance_to_range_high / distance_to_range_low
        - breakout_up_candidate / breakout_down_candidate
        - volume_ratio
        - atr / relative_atr (si hay suficiente histórico)
        """
        features: Dict[str, Any] = {
            "timestamp": getattr(market_data, "timestamp", None),
            "symbol": market_data.symbol,
            "price": float(market_data.close or market_data.bid or market_data.last or 0),
        }

        # Obtener histórico
        if historical_data is None:
            prices = list(self.price_history) if self.price_history else []
            highs = list(self.high_history) if self.high_history else []
            lows = list(self.low_history) if self.low_history else []
            volumes = list(self.volume_history) if self.volume_history else []
        else:
            prices = [
                float(q.close or q.bid or q.last or 0)
                for q in historical_data
            ]
            highs = [
                float(getattr(q, "high", q.close or 0)) for q in historical_data
            ]
            lows = [
                float(getattr(q, "low", q.close or 0)) for q in historical_data
            ]
            volumes = [float(getattr(q, "volume", 0)) for q in historical_data]

        if len(prices) >= self.lookback_period:
            window_prices = prices[-self.lookback_period :]
            window_highs = highs[-self.lookback_period :] if highs else window_prices
            window_lows = lows[-self.lookback_period :] if lows else window_prices

            range_high = max(window_highs)
            range_low = min(window_lows)
            range_width = max(range_high - range_low, 1e-8)  # evitar división por cero

            current_price = features["price"]
            distance_to_high = range_high - current_price
            distance_to_low = current_price - range_low

            features.update(
                {
                    "range_high": float(range_high),
                    "range_low": float(range_low),
                    "range_width": float(range_width),
                    "distance_to_range_high": float(distance_to_high),
                    "distance_to_range_low": float(distance_to_low),
                }
            )

            # Volume ratio
            if volumes and len(volumes) >= 20:
                avg_volume = sum(volumes[-20:]) / 20
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0

            features["volume_ratio"] = float(volume_ratio)

            # ATR y relative ATR (opcional)
            atr = self.indicator_calculator.calculate_atr(
                window_highs, window_lows, window_prices, period=min(14, self.lookback_period)
            )
            if atr is not None and current_price > 0:
                features["atr"] = float(atr)
                features["relative_atr"] = float(atr) / current_price
            else:
                features["atr"] = 0.0
                features["relative_atr"] = 0.0

            # Flags de posible breakout
            breakout_up_level = range_high * (1 + float(self.breakout_threshold_pct))
            breakout_down_level = range_low * (1 - float(self.breakout_threshold_pct))

            features["breakout_up_candidate"] = current_price >= breakout_up_level
            features["breakout_down_candidate"] = current_price <= breakout_down_level
            features["breakout_threshold_pct"] = float(self.breakout_threshold_pct)
        else:
            # Defaults cuando no hay suficiente histórico
            features.update(
                {
                    "range_high": features["price"],
                    "range_low": features["price"],
                    "range_width": 0.0,
                    "distance_to_range_high": 0.0,
                    "distance_to_range_low": 0.0,
                    "volume_ratio": 1.0,
                    "atr": 0.0,
                    "relative_atr": 0.0,
                    "breakout_up_candidate": False,
                    "breakout_down_candidate": False,
                    "breakout_threshold_pct": float(self.breakout_threshold_pct),
                }
            )

        return features

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementación específica de generación de señales para breakout.

        Args:
            market_data: Datos de mercado actuales.

        Returns:
            Lista de señales generadas.
        """
        signals: List[Signal] = []

        try:
            current_price = float(
                market_data.close or market_data.bid or market_data.last or 0
            )
            if current_price <= 0:
                return []

            # Actualizar histórico
            self.price_history.append(current_price)
            self.high_history.append(
                float(getattr(market_data, "high", current_price))
            )
            self.low_history.append(
                float(getattr(market_data, "low", current_price))
            )
            self.volume_history.append(float(getattr(market_data, "volume", 0)))

            # Necesitamos suficiente histórico
            if len(self.price_history) < self.lookback_period:
                return []

            prices = list(self.price_history)
            highs = list(self.high_history)
            lows = list(self.low_history)
            volumes = list(self.volume_history)

            window_prices = prices[-self.lookback_period :]
            window_highs = highs[-self.lookback_period :]
            window_lows = lows[-self.lookback_period :]

            range_high = max(window_highs)
            range_low = min(window_lows)
            range_width = max(range_high - range_low, 1e-8)

            # Volume ratio
            if len(volumes) >= 20:
                avg_volume = sum(volumes[-20:]) / 20
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0

            # Niveles de breakout
            breakout_up_level = range_high * (1 + float(self.breakout_threshold_pct))
            breakout_down_level = range_low * (1 - float(self.breakout_threshold_pct))

            # Flags de breakout
            breakout_up = current_price >= breakout_up_level
            breakout_down = current_price <= breakout_down_level
            volume_ok = volume_ratio >= float(self.min_volume_ratio)

            if breakout_up and volume_ok:
                confidence = self._calculate_breakout_confidence(
                    current_price=current_price,
                    range_high=range_high,
                    range_low=range_low,
                    volume_ratio=volume_ratio,
                    direction="up",
                )
                strength = self._map_confidence_to_strength(confidence)

                signal = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=strength,
                    price=Decimal(str(current_price)),
                    timestamp=getattr(market_data, "timestamp", None),
                    confidence=confidence,
                    liquidity_score=min(
                        100.0, max(0.0, (volume_ratio - 0.5) * 50.0)
                    ),
                    priority_score=confidence * 0.7
                    + min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)) * 0.3,
                    source=SignalSource.TECHNICAL,
                    volume=Decimal("1"),  # El tamaño real lo calcula get_position_size()
                    metadata={
                        "strategy": self.name,
                        "breakout_direction": "up",
                        "range_high": range_high,
                        "range_low": range_low,
                        "range_width": range_width,
                        "breakout_level": breakout_up_level,
                        "volume_ratio": volume_ratio,
                        "lookback_period": self.lookback_period,
                        "breakout_threshold_pct": float(self.breakout_threshold_pct),
                    },
                )
                signals.append(signal)

            elif breakout_down and volume_ok:
                confidence = self._calculate_breakout_confidence(
                    current_price=current_price,
                    range_high=range_high,
                    range_low=range_low,
                    volume_ratio=volume_ratio,
                    direction="down",
                )
                strength = self._map_confidence_to_strength(confidence)

                signal = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.SELL,
                    strength=strength,
                    price=Decimal(str(current_price)),
                    timestamp=getattr(market_data, "timestamp", None),
                    confidence=confidence,
                    liquidity_score=min(
                        100.0, max(0.0, (volume_ratio - 0.5) * 50.0)
                    ),
                    priority_score=confidence * 0.7
                    + min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)) * 0.3,
                    source=SignalSource.TECHNICAL,
                    volume=Decimal("1"),
                    metadata={
                        "strategy": self.name,
                        "breakout_direction": "down",
                        "range_high": range_high,
                        "range_low": range_low,
                        "range_width": range_width,
                        "breakout_level": breakout_down_level,
                        "volume_ratio": volume_ratio,
                        "lookback_period": self.lookback_period,
                        "breakout_threshold_pct": float(self.breakout_threshold_pct),
                    },
                )
                signals.append(signal)

        except Exception as e:
            logger.error(
                f"Error generando señal en BreakoutStrategyEngine: {e}", exc_info=True
            )

        return signals

    def _calculate_breakout_confidence(
        self,
        current_price: float,
        range_high: float,
        range_low: float,
        volume_ratio: float,
        direction: str,
    ) -> float:
        """
        Calcular confidence de la señal de breakout basado en:
        - Distancia relativa más allá del rango (normalizada).
        - Confirmación de volumen.
        """
        confidence = 50.0  # base

        range_width = max(range_high - range_low, 1e-8)
        if direction == "up":
            distance_beyond = max(0.0, current_price - range_high)
        else:
            distance_beyond = max(0.0, range_low - current_price)

        distance_ratio = distance_beyond / range_width

        # Contribución por distancia (hasta +25)
        if distance_ratio > 0.05:
            confidence += 25.0
        elif distance_ratio > 0.02:
            confidence += 15.0
        elif distance_ratio > 0.01:
            confidence += 10.0

        # Contribución por volumen (hasta +25)
        if volume_ratio > 3.0:
            confidence += 25.0
        elif volume_ratio > 2.0:
            confidence += 15.0
        elif volume_ratio > float(self.min_volume_ratio):
            confidence += 10.0

        return min(100.0, max(0.0, confidence))

    @staticmethod
    def _map_confidence_to_strength(confidence: float) -> SignalStrength:
        """Mapear confidence (0-100) a SignalStrength."""
        if confidence >= 80.0:
            return SignalStrength.VERY_STRONG
        if confidence >= 70.0:
            return SignalStrength.STRONG
        if confidence >= 50.0:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def get_required_parameters(self) -> List[str]:
        """Obtener parámetros requeridos."""
        return [
            "lookback_period",
            "breakout_threshold_pct",
            "min_volume_ratio",
            "max_exposure",
            "min_signal_confidence",
        ]

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar criterios de riesgo básicos para breakout.

        - Limitar exposición total del portfolio.
        - Requerir una confianza mínima en la señal.
        """
        # Exposición máxima
        try:
            current_exposure = portfolio.get_total_exposure()
        except Exception:
            # Fallback defensivo: si el método no existe o falla, no bloquear por exposición
            current_exposure = 0.0

        if current_exposure >= float(self.max_exposure):
            logger.debug(
                "Risk check fallido en BreakoutStrategyEngine: "
                f"exposición {current_exposure:.2%} >= {float(self.max_exposure):.2%}"
            )
            return False

        # Confianza mínima
        if signal.confidence < self.min_signal_confidence:
            logger.debug(
                "Risk check fallido en BreakoutStrategyEngine: "
                f"confidence {signal.confidence:.2f} < {self.min_signal_confidence:.2f}"
            )
            return False

        return True


