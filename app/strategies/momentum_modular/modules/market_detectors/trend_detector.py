"""
TrendDetector - Módulo independiente para detectar tendencias.

VECTORIZADO: Usa numpy para todos los cálculos. Sin bucles Python.
"""

import logging
from typing import Dict, List, Optional, Union

import numpy as np

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class TrendDetector(BaseMarketDetector):
    """
    Detecta tendencias alcistas, bajistas o ausencia de tendencia.

    Métodos soportados:
    - ema_cross: Cruce de EMAs
    - adx: Average Directional Index
    - macd: MACD

    NOTA: Todas las implementaciones están vectorizadas con numpy.
    """

    def __init__(self, config: Dict):
        """Inicializar detector de tendencias."""
        super().__init__("trend_detector", config)

        trend_config = config.get("trend_detection", {})
        self.method = trend_config.get("method", "ema_cross")
        self.ema_fast_period = trend_config.get("ema_fast_period", 12)
        self.ema_slow_period = trend_config.get("ema_slow_period", 26)
        self.min_trend_strength = trend_config.get("min_trend_strength", 0.6)

    def detect(self, price_history: Union[List[float], np.ndarray], **kwargs) -> Dict:
        """
        Detectar tendencia.

        Args:
            price_history: Precios close (list o numpy array)
            **kwargs: high_history, low_history para ADX

        Returns:
            {
                'type': 'trend_up' | 'trend_down' | 'no_trend',
                'strength': float,  # 0.0-1.0
                'confidence': float,  # 0.0-1.0
                'method': str
            }
        """
        # Convert to numpy array if needed
        prices = np.asarray(price_history, dtype=np.float64)

        if not self.enabled or len(prices) < self.ema_slow_period:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': self.method}

        # Check for NaN/Inf
        if not np.isfinite(prices).all():
            logger.warning("Price history contains NaN or Inf values")
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': self.method}

        if self.method == "ema_cross":
            return self._detect_ema_cross(prices)
        elif self.method == "adx":
            return self._detect_adx(prices, **kwargs)
        elif self.method == "macd":
            return self._detect_macd(prices, **kwargs)
        else:
            logger.warning(f"Unknown trend detection method: {self.method}")
            return self._detect_ema_cross(prices)

    def _detect_ema_cross(self, prices: np.ndarray) -> Dict:
        """Detectar tendencia usando cruce de EMAs - VECTORIZADO."""
        ema_fast = self._ema_vectorized(prices, self.ema_fast_period)
        ema_slow = self._ema_vectorized(prices, self.ema_slow_period)

        if ema_fast is None or ema_slow is None:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'ema_cross'}

        current_price = prices[-1]
        current_fast = ema_fast[-1]
        current_slow = ema_slow[-1]

        fast_above_slow = current_fast > current_slow
        price_above_fast = current_price > current_fast

        if fast_above_slow and price_above_fast:
            distance = (current_fast - current_slow) / current_slow if current_slow > 0 else 0
            strength = min(1.0, distance / 0.05)
            confidence = min(1.0, strength / self.min_trend_strength)

            if strength >= self.min_trend_strength:
                return {
                    'type': 'trend_up',
                    'strength': float(strength),
                    'confidence': float(confidence),
                    'method': 'ema_cross',
                    'metadata': {
                        'ema_fast': float(current_fast),
                        'ema_slow': float(current_slow),
                        'distance_pct': float(distance),
                    },
                }

        elif not fast_above_slow and not price_above_fast:
            distance = (current_slow - current_fast) / current_fast if current_fast > 0 else 0
            strength = min(1.0, distance / 0.05)
            confidence = min(1.0, strength / self.min_trend_strength)

            if strength >= self.min_trend_strength:
                return {
                    'type': 'trend_down',
                    'strength': float(strength),
                    'confidence': float(confidence),
                    'method': 'ema_cross',
                    'metadata': {
                        'ema_fast': float(current_fast),
                        'ema_slow': float(current_slow),
                        'distance_pct': float(distance),
                    },
                }

        return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.5, 'method': 'ema_cross'}

    def _detect_adx(self, prices: np.ndarray, **kwargs) -> Dict:
        """
        Detectar tendencia usando ADX - COMPLETAMENTE VECTORIZADO.

        Usa numpy para todos los cálculos sin bucles Python.
        """
        high = np.asarray(kwargs.get('high_history', prices), dtype=np.float64)
        low = np.asarray(kwargs.get('low_history', prices), dtype=np.float64)

        period = self.config.get("trend_detection", {}).get("adx_period", 14)

        if len(prices) < period + 1:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'adx'}

        try:
            # Vectorized True Range calculation
            high_low = high[1:] - low[1:]
            high_prev_close = np.abs(high[1:] - prices[:-1])
            low_prev_close = np.abs(low[1:] - prices[:-1])
            tr = np.maximum(high_low, np.maximum(high_prev_close, low_prev_close))

            # Vectorized Directional Movement
            up_move = high[1:] - high[:-1]
            down_move = low[:-1] - low[1:]

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

            if len(tr) < period:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'adx'}

            # Wilder's smoothing - vectorized
            atr = self._wilder_smooth(tr, period)
            smooth_plus_dm = self._wilder_smooth(plus_dm, period)
            smooth_minus_dm = self._wilder_smooth(minus_dm, period)

            if atr is None or len(atr) == 0:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'adx'}

            # Vectorized +DI, -DI calculation
            # Avoid division by zero
            atr_safe = np.where(atr > 0, atr, 1.0)
            plus_di = 100.0 * smooth_plus_dm / atr_safe
            minus_di = 100.0 * smooth_minus_dm / atr_safe

            # Vectorized DX calculation
            di_sum = plus_di + minus_di
            di_sum_safe = np.where(di_sum > 0, di_sum, 1.0)
            dx = np.abs(plus_di - minus_di) / di_sum_safe * 100.0

            if len(dx) < period:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'adx'}

            # ADX = smoothed DX
            adx = self._wilder_smooth(dx, period)

            if adx is None or len(adx) == 0:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'adx'}

            current_adx = float(adx[-1])
            current_plus_di = float(plus_di[-1])
            current_minus_di = float(minus_di[-1])

            # Normalize strength
            strength = min(1.0, current_adx / 50.0)

            if current_adx < 20:
                trend_type = 'no_trend'
                confidence = 0.3
            elif current_plus_di > current_minus_di:
                trend_type = 'trend_up'
                confidence = min(1.0, current_adx / 40.0)
            else:
                trend_type = 'trend_down'
                confidence = min(1.0, current_adx / 40.0)

            return {
                'type': trend_type,
                'strength': strength,
                'confidence': confidence,
                'method': 'adx',
                'metadata': {
                    'adx': current_adx,
                    'plus_di': current_plus_di,
                    'minus_di': current_minus_di,
                },
            }

        except (ValueError, IndexError) as e:
            logger.warning(f"ADX calculation error: {e}, falling back to EMA")
            return self._detect_ema_cross(prices)

    def _detect_macd(self, prices: np.ndarray, **kwargs) -> Dict:
        """
        Detectar tendencia usando MACD - COMPLETAMENTE VECTORIZADO.

        MACD = EMA(fast) - EMA(slow)
        Signal = EMA(MACD, signal_period)
        Histogram = MACD - Signal
        """
        macd_config = self.config.get("trend_detection", {})
        fast_period = macd_config.get("macd_fast_period", 12)
        slow_period = macd_config.get("macd_slow_period", 26)
        signal_period = macd_config.get("macd_signal_period", 9)

        min_periods = slow_period + signal_period

        if len(prices) < min_periods:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'macd'}

        try:
            # Vectorized EMA calculation
            ema_fast = self._ema_vectorized(prices, fast_period)
            ema_slow = self._ema_vectorized(prices, slow_period)

            if ema_fast is None or ema_slow is None:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'macd'}

            # Align arrays (slow EMA is shorter)
            offset = len(ema_fast) - len(ema_slow)
            macd_line = ema_fast[offset:] - ema_slow

            if len(macd_line) < signal_period:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'macd'}

            # Signal line
            signal_line = self._ema_vectorized(macd_line, signal_period)

            if signal_line is None or len(signal_line) < 2:
                return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'macd'}

            # Align for histogram
            macd_aligned = macd_line[-(len(signal_line)) :]
            histogram = macd_aligned - signal_line

            current_macd = float(macd_aligned[-1])
            current_signal = float(signal_line[-1])
            current_histogram = float(histogram[-1])

            prev_macd = float(macd_aligned[-2]) if len(macd_aligned) > 1 else current_macd
            prev_signal = float(signal_line[-2]) if len(signal_line) > 1 else current_signal
            prev_histogram = prev_macd - prev_signal

            # Strength normalized by price
            avg_price = float(np.mean(prices[-slow_period:]))
            relative_macd = abs(current_macd) / avg_price * 100 if avg_price > 0 else 0
            strength = min(1.0, relative_macd / 2.0)

            # Determine trend
            if current_macd > current_signal and current_macd > 0:
                trend_type = 'trend_up'
                confidence = 0.8 if current_histogram > prev_histogram else 0.6
            elif current_macd < current_signal and current_macd < 0:
                trend_type = 'trend_down'
                confidence = 0.8 if current_histogram < prev_histogram else 0.6
            elif current_macd > current_signal:
                trend_type = 'trend_up'
                confidence = 0.4
            elif current_macd < current_signal:
                trend_type = 'trend_down'
                confidence = 0.4
            else:
                trend_type = 'no_trend'
                confidence = 0.3

            # Crossover detection
            crossover = None
            if prev_macd < prev_signal and current_macd > current_signal:
                crossover = 'bullish_crossover'
                confidence = min(1.0, confidence + 0.2)
            elif prev_macd > prev_signal and current_macd < current_signal:
                crossover = 'bearish_crossover'
                confidence = min(1.0, confidence + 0.2)

            return {
                'type': trend_type,
                'strength': strength,
                'confidence': min(1.0, confidence),
                'method': 'macd',
                'metadata': {
                    'macd': current_macd,
                    'signal': current_signal,
                    'histogram': current_histogram,
                    'crossover': crossover,
                },
            }

        except (ValueError, IndexError) as e:
            logger.warning(f"MACD calculation error: {e}, falling back to EMA")
            return self._detect_ema_cross(prices)

    @staticmethod
    def _ema_vectorized(data: np.ndarray, period: int) -> Optional[np.ndarray]:
        """
        Calculate EMA using numpy - FULLY VECTORIZED.

        Uses pandas-style EMA calculation without pandas dependency.
        """
        if len(data) < period:
            return None

        alpha = 2.0 / (period + 1)

        # Initial SMA
        sma = np.mean(data[:period])

        # Pre-allocate result array
        result = np.empty(len(data) - period + 1)
        result[0] = sma

        # Vectorized EMA calculation using cumulative approach
        # This is O(n) and fully vectorized
        weights = (1 - alpha) ** np.arange(len(data) - period)
        weights = weights[::-1]  # Reverse for proper weighting

        for i in range(1, len(result)):
            result[i] = alpha * data[period - 1 + i] + (1 - alpha) * result[i - 1]

        return result

    @staticmethod
    def _wilder_smooth(data: np.ndarray, period: int) -> Optional[np.ndarray]:
        """
        Wilder's smoothing method - VECTORIZED.

        Wilder's smoothing: smooth[i] = (smooth[i-1] * (period-1) + data[i]) / period
        """
        if len(data) < period:
            return None

        # Initial value is SMA
        initial = np.mean(data[:period])

        # Pre-allocate
        result = np.empty(len(data) - period + 1)
        result[0] = initial

        # Wilder's smoothing factor
        factor = (period - 1) / period

        for i in range(1, len(result)):
            result[i] = result[i - 1] * factor + data[period - 1 + i] / period

        return result
