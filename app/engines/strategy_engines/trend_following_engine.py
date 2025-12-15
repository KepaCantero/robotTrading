"""
TrendFollowingStrategyEngine - Engine de estrategia de seguimiento de tendencia.

Detecta y sigue tendencias usando ADX (fuerza de tendencia) y MACD (dirección de tendencia).

Características principales:
- Usa ADX para detectar fuerza de tendencia (>25 = tendencia fuerte).
- Usa MACD para confirmar dirección (cruce de líneas, histograma positivo/negativo).
- Requiere confirmación por volumen (ratio vs volumen medio reciente).
- Integra métricas básicas (confidence, liquidity_score, priority_score).
- Extiende BaseStrategyEngine para futura integración con Learning Engines.
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.core.centralized_config import get_strategy_config, get_trading_threshold
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.momentum_analysis import TechnicalIndicatorCalculator
from app.services.signal_scoring_engine import get_signal_scoring_engine

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class TrendFollowingStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de seguimiento de tendencia basada en ADX y MACD.

    Lógica básica:
    - ADX > threshold (default 25) indica tendencia fuerte.
    - MACD cruce alcista (MACD > Signal y histograma positivo) = señal BUY.
    - MACD cruce bajista (MACD < Signal y histograma negativo) = señal SELL.
    - Requiere confirmación por volumen (volume_ratio >= min_volume_ratio).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar TrendFollowingStrategyEngine.

        Args:
            config: Configuración de la estrategia.
        """
        super().__init__(config)

        # Initialize all parameters with defaults FIRST
        self.adx_period = config.get("adx_period", 14)
        self.macd_fast_period = config.get("macd_fast_period", 12)
        self.macd_slow_period = config.get("macd_slow_period", 26)
        self.macd_signal_period = config.get("macd_signal_period", 9)
        self.volume_lookback = config.get("volume_lookback", 20)

        # Load strategy-specific configuration
        strategy_config = get_strategy_config("trend_following")
        if strategy_config:
            params = strategy_config.parameters
            if isinstance(params, dict):
                try:
                    self.config.update({k: v for k, v in params.items() if v is not None})
                    config.update({k: v for k, v in params.items() if v is not None})
                except Exception:
                    pass

            # Core thresholds
            self.adx_threshold = Decimal(
                str(params.get("adx_threshold", 25.0))
            )  # ADX > 25 = tendencia fuerte
            self.min_volume_ratio = Decimal(
                str(params.get("min_volume_ratio", 1.2))
            )  # Volumen >= 1.2x promedio
            self.macd_histogram_threshold = Decimal(
                str(params.get("macd_histogram_threshold", 0.0))
            )  # Histograma debe ser positivo/negativo según dirección

            # Risk parameters
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct"))
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or get_trading_threshold("take_profit_pct"))
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or get_trading_threshold("max_position_size"))
            )
            self.max_exposure = Decimal(str(params.get("max_exposure", 0.60)))

            # Technical indicator periods
            if "adx_period" in params:
                self.adx_period = params.get("adx_period", self.adx_period)
            if "macd_fast_period" in params:
                self.macd_fast_period = params.get("macd_fast_period", self.macd_fast_period)
            if "macd_slow_period" in params:
                self.macd_slow_period = params.get("macd_slow_period", self.macd_slow_period)
            if "macd_signal_period" in params:
                self.macd_signal_period = params.get("macd_signal_period", self.macd_signal_period)
            if "volume_lookback" in params:
                self.volume_lookback = params.get("volume_lookback", self.volume_lookback)
        else:
            # Defaults si no hay configuración
            self.adx_threshold = Decimal(str(config.get("adx_threshold", 25.0)))
            self.min_volume_ratio = Decimal(str(config.get("min_volume_ratio", 1.2)))
            self.macd_histogram_threshold = Decimal(str(config.get("macd_histogram_threshold", 0.0)))
            self.stop_loss = Decimal(str(get_trading_threshold("stop_loss_pct")))
            self.take_profit = Decimal(str(get_trading_threshold("take_profit_pct")))
            self.max_position_size = Decimal(str(get_trading_threshold("max_position_size")))
            self.max_exposure = Decimal(str(config.get("max_exposure", 0.60)))

        # Históricos
        self.price_history: deque[float] = deque(maxlen=200)
        self.high_history: deque[float] = deque(maxlen=200)
        self.low_history: deque[float] = deque(maxlen=200)
        self.volume_history: deque[float] = deque(maxlen=200)

        # Technical indicator calculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Signal scoring engine
        self.signal_scorer = get_signal_scoring_engine()

        logger.info(f"TrendFollowingStrategyEngine initialized: {self.name}")

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "trend_following"

    def extract_features(
        self,
        market_data: Quote,
        historical_data: Optional[Sequence[Quote]] = None,
    ) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Features principales:
        - adx (fuerza de tendencia)
        - macd_line, macd_signal, macd_histogram
        - macd_cross_up / macd_cross_down
        - volume_ratio
        - price_position (precio relativo a EMA opcional)
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

        # Calcular indicadores si hay suficiente histórico
        min_history = max(self.adx_period, self.macd_slow_period)
        if len(prices) >= min_history:
            # ADX
            adx = self.indicator_calculator.calculate_adx(
                highs, lows, prices, period=self.adx_period
            )
            features["adx"] = float(adx) if adx is not None else 0.0

            # MACD
            macd_line, macd_signal, macd_histogram = self.indicator_calculator.calculate_macd(
                prices,
                fast_period=self.macd_fast_period,
                slow_period=self.macd_slow_period,
                signal_period=self.macd_signal_period,
            )
            features["macd_line"] = float(macd_line) if macd_line is not None else 0.0
            features["macd_signal"] = float(macd_signal) if macd_signal is not None else 0.0
            features["macd_histogram"] = float(macd_histogram) if macd_histogram is not None else 0.0

            # Detectar cruces
            if len(prices) >= 2 and macd_line is not None and macd_signal is not None:
                # Para detectar cruces necesitamos valores previos
                # Por simplicidad, usamos el histograma: positivo = MACD > Signal
                features["macd_cross_up"] = features["macd_histogram"] > 0
                features["macd_cross_down"] = features["macd_histogram"] < 0
            else:
                features["macd_cross_up"] = False
                features["macd_cross_down"] = False

            # Volume ratio
            if len(volumes) >= self.volume_lookback:
                avg_volume = sum(volumes[-self.volume_lookback :]) / self.volume_lookback
                current_volume = volumes[-1] if volumes else 0
                features["volume_ratio"] = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                features["volume_ratio"] = 1.0
        else:
            # Defaults cuando no hay suficiente histórico
            features["adx"] = 0.0
            features["macd_line"] = 0.0
            features["macd_signal"] = 0.0
            features["macd_histogram"] = 0.0
            features["macd_cross_up"] = False
            features["macd_cross_down"] = False
            features["volume_ratio"] = 1.0

        return features

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementación específica de generación de señales para trend following.

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
            min_history = max(self.adx_period, self.macd_slow_period)
            if len(self.price_history) < min_history:
                return []

            # Calcular indicadores
            prices = list(self.price_history)
            highs = list(self.high_history)
            lows = list(self.low_history)
            volumes = list(self.volume_history)

            # ADX (fuerza de tendencia)
            adx = self.indicator_calculator.calculate_adx(
                highs, lows, prices, period=self.adx_period
            )

            # MACD (dirección de tendencia)
            macd_line, macd_signal, macd_histogram = self.indicator_calculator.calculate_macd(
                prices,
                fast_period=self.macd_fast_period,
                slow_period=self.macd_slow_period,
                signal_period=self.macd_signal_period,
            )

            if adx is None or macd_line is None or macd_signal is None or macd_histogram is None:
                return []

            # Calcular ratio de volumen
            if len(volumes) >= self.volume_lookback:
                avg_volume = sum(volumes[-self.volume_lookback :]) / self.volume_lookback
                current_volume = volumes[-1] if volumes else 0
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0

            # Condiciones para señal BUY (tendencia alcista)
            adx_strong = adx > float(self.adx_threshold)  # Tendencia fuerte
            macd_bullish = (
                macd_line > macd_signal and macd_histogram > float(self.macd_histogram_threshold)
            )  # MACD cruce alcista
            volume_confirmed = volume_ratio >= float(self.min_volume_ratio)  # Confirmación volumen

            if adx_strong and macd_bullish and volume_confirmed:
                # Calcular confidence
                confidence = self._calculate_confidence(adx, macd_histogram, volume_ratio)

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
                    timestamp=getattr(market_data, "timestamp", None),
                    confidence=confidence,
                    liquidity_score=min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)),
                    priority_score=confidence * 0.7
                    + min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)) * 0.3,
                    source=SignalSource.TREND_FOLLOWING,
                    volume=Decimal("1"),  # Placeholder
                    metadata={
                        "strategy": self.name,
                        "adx": adx,
                        "macd_line": macd_line,
                        "macd_signal": macd_signal,
                        "macd_histogram": macd_histogram,
                        "volume_ratio": volume_ratio,
                    },
                )

                signals.append(signal)

            # Condiciones para señal SELL (tendencia bajista)
            macd_bearish = (
                macd_line < macd_signal and macd_histogram < -float(self.macd_histogram_threshold)
            )  # MACD cruce bajista

            if adx_strong and macd_bearish and volume_confirmed:
                # Calcular confidence
                confidence = self._calculate_confidence(adx, abs(macd_histogram), volume_ratio)

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
                    signal_type=SignalType.SELL,
                    strength=strength,
                    price=Decimal(str(current_price)),
                    timestamp=getattr(market_data, "timestamp", None),
                    confidence=confidence,
                    liquidity_score=min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)),
                    priority_score=confidence * 0.7
                    + min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0)) * 0.3,
                    source=SignalSource.TREND_FOLLOWING,
                    volume=Decimal("1"),  # Placeholder
                    metadata={
                        "strategy": self.name,
                        "adx": adx,
                        "macd_line": macd_line,
                        "macd_signal": macd_signal,
                        "macd_histogram": macd_histogram,
                        "volume_ratio": volume_ratio,
                    },
                )

                signals.append(signal)

        except Exception as e:
            logger.error(f"Error generando señal en TrendFollowingStrategyEngine: {e}", exc_info=True)

        return signals

    def _calculate_confidence(
        self, adx: float, macd_histogram: float, volume_ratio: float
    ) -> float:
        """
        Calcular confidence basado en ADX, MACD histogram y volumen.

        Args:
            adx: Valor ADX (fuerza de tendencia)
            macd_histogram: Valor del histograma MACD
            volume_ratio: Ratio de volumen vs promedio

        Returns:
            Confidence score (0-100)
        """
        # ADX contribuye hasta 40 puntos (normalizado a 0-100)
        adx_score = min(40.0, (adx / 50.0) * 40.0)  # ADX máximo típico ~50

        # MACD histogram contribuye hasta 30 puntos (normalizado)
        macd_score = min(30.0, abs(macd_histogram) * 10.0)  # Ajustar según escala

        # Volume ratio contribuye hasta 30 puntos
        volume_score = min(30.0, (volume_ratio - 1.0) * 15.0)  # 1.0 = 0, 3.0 = 30

        confidence = adx_score + macd_score + volume_score
        return min(100.0, max(0.0, confidence))

    def get_required_parameters(self) -> List[str]:
        """
        Obtener lista de parámetros requeridos.

        Returns:
            Lista de nombres de parámetros requeridos
        """
        return [
            "adx_period",
            "adx_threshold",
            "macd_fast_period",
            "macd_slow_period",
            "macd_signal_period",
            "macd_histogram_threshold",
            "min_volume_ratio",
            "volume_lookback",
        ]

    def risk_check(self, signal: Signal, portfolio: Optional[Portfolio] = None) -> bool:
        """
        Verificar si la señal pasa los checks de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Portfolio actual (opcional)

        Returns:
            True si pasa los checks, False en caso contrario
        """
        if portfolio is None:
            return True

        try:
            # Check exposición máxima
            total_exposure = portfolio.get_total_exposure() if hasattr(portfolio, "get_total_exposure") else 0.0
            if total_exposure >= float(self.max_exposure):
                logger.debug(f"Risk check failed: total exposure {total_exposure} >= {self.max_exposure}")
                return False

            # Check confidence mínima
            if signal.confidence < 50.0:  # Threshold mínimo razonable
                logger.debug(f"Risk check failed: confidence {signal.confidence} < 50.0")
                return False

            return True

        except Exception as e:
            logger.error(f"Error en risk_check: {e}", exc_info=True)
            return False

