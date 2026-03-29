"""
RangeDetector - Módulo independiente para detectar mercados en rango.

VECTORIZADO: Usa numpy para todos los cálculos. Sin bucles Python.
"""

import logging
from typing import Union

import numpy as np

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class RangeDetector(BaseMarketDetector):
    """
    Detecta si el mercado está en rango lateral.

    Métodos soportados:
    - bollinger_squeeze: Bandas de Bollinger estrechas
    - price_range: Rango de precios limitado

    NOTA: Todas las implementaciones están vectorizadas con numpy.
    """

    def __init__(self, config: dict):
        """Inicializar detector de rangos."""
        super().__init__("range_detector", config)

        range_config = config.get("range_detection", {})
        self.method = range_config.get("method", "bollinger_squeeze")
        self.lookback_period = range_config.get("lookback_period", 20)
        self.squeeze_threshold = range_config.get("squeeze_threshold", 0.1)
        self.max_range_pct = range_config.get("max_range_pct", 0.03)  # 3%

    def detect(self, price_history: Union[list[float], np.ndarray], **kwargs) -> dict:
        """
        Detectar si el mercado está en rango.

        Args:
            price_history: Precios close (list o numpy array)

        Returns:
            {
                'in_range': bool,
                'range_size_pct': float,
                'confidence': float,
                'method': str
            }
        """
        # Convert to numpy
        prices = np.asarray(price_history, dtype=np.float64)

        if not self.enabled or len(prices) < self.lookback_period:
            return {
                "in_range": False,
                "range_size_pct": 1.0,
                "confidence": 0.5,
                "method": self.method,
            }

        # Check for NaN/Inf
        if not np.isfinite(prices).all():
            logger.warning("Price history contains NaN or Inf values")
            return {
                "in_range": False,
                "range_size_pct": 1.0,
                "confidence": 0.0,
                "method": self.method,
            }

        # Si hay tendencia clara (pasado como parámetro), no está en rango
        trend_info = kwargs.get("trend_info", {})
        if trend_info.get("strength", 0) > 0.5:
            return {
                "in_range": False,
                "range_size_pct": 0.0,
                "confidence": 1.0,
                "method": self.method,
                "reason": "Strong trend detected",
            }

        if self.method == "bollinger_squeeze":
            return self._detect_bollinger_squeeze(prices, **kwargs)
        elif self.method == "price_range":
            return self._detect_price_range(prices)
        else:
            logger.warning(f"Unknown range detection method: {self.method}")
            return self._detect_price_range(prices)

    def _detect_price_range(self, prices: np.ndarray) -> dict:
        """Detectar rango basado en tamaño de movimiento de precios - VECTORIZADO."""
        recent_prices = prices[-self.lookback_period :]

        # Vectorized min/max/mean
        price_range = float(np.ptp(recent_prices))  # ptp = peak to peak = max - min
        avg_price = float(np.mean(recent_prices))

        # Avoid division by zero
        range_pct = price_range / avg_price if avg_price > 0 else 1.0

        in_range = range_pct < self.max_range_pct

        # Calcular confianza basada en qué tan pequeño es el rango
        if in_range:
            confidence = min(1.0, (self.max_range_pct - range_pct) / self.max_range_pct * 2)
        else:
            confidence = 0.0

        return {
            "in_range": in_range,
            "range_size_pct": float(range_pct),
            "confidence": float(confidence),
            "method": "price_range",
            "metadata": {"price_range": price_range, "avg_price": avg_price},
        }

    def _detect_bollinger_squeeze(self, prices: np.ndarray, **kwargs) -> dict:
        """
        Detectar rango usando Bollinger Squeeze - COMPLETAMENTE VECTORIZADO.

        El "squeeze" ocurre cuando las Bandas de Bollinger se estrechan,
        indicando baja volatilidad y posible movimiento fuerte inminente.
        """
        bb_config = self.config.get("range_detection", {})
        period = bb_config.get("bollinger_period", 20)
        std_mult = bb_config.get("bollinger_std", 2.0)
        squeeze_percentile = bb_config.get("squeeze_percentile", 20)

        if len(prices) < period:
            return {
                "in_range": False,
                "range_size_pct": 1.0,
                "confidence": 0.5,
                "method": "bollinger_squeeze",
            }

        try:
            # Rolling statistics using numpy stride tricks for efficiency
            # Calculate rolling SMA
            sma = self._rolling_mean(prices, period)

            # Calculate rolling std
            rolling_std = self._rolling_std(prices, period)

            if sma is None or rolling_std is None:
                return self._detect_price_range(prices)

            # Current values
            current_sma = float(sma[-1])
            current_std = float(rolling_std[-1])

            # Bollinger Bands
            upper_band = current_sma + (std_mult * current_std)
            lower_band = current_sma - (std_mult * current_std)

            # Band width (normalized by SMA)
            band_width = (upper_band - lower_band) / current_sma if current_sma > 0 else 0

            # Calculate all historical band widths VECTORIZED
            # band_width = 2 * std_mult * rolling_std / sma
            band_widths = 2 * std_mult * rolling_std / np.where(sma > 0, sma, 1.0)

            # Find squeeze threshold using percentile
            squeeze_threshold = float(np.percentile(band_widths, squeeze_percentile))

            # Determine if in squeeze
            in_squeeze = band_width <= squeeze_threshold

            # Position within bands
            current_price = float(prices[-1])
            band_range = upper_band - lower_band
            position_in_bands = (current_price - lower_band) / band_range if band_range > 0 else 0.5

            # Confidence
            if in_squeeze:
                width_ratio = band_width / squeeze_threshold if squeeze_threshold > 0 else 1
                confidence = min(1.0, (2.0 - width_ratio))
            else:
                confidence = 0.3

            return {
                "in_range": in_squeeze,
                "range_size_pct": float(band_width),
                "confidence": float(confidence),
                "method": "bollinger_squeeze",
                "metadata": {
                    "upper_band": float(upper_band),
                    "lower_band": float(lower_band),
                    "sma": float(current_sma),
                    "band_width": float(band_width),
                    "squeeze_threshold": float(squeeze_threshold),
                    "position_in_bands": float(position_in_bands),
                    "is_near_upper": position_in_bands > 0.8,
                    "is_near_lower": position_in_bands < 0.2,
                },
            }

        except (ValueError, IndexError) as e:
            logger.warning(f"Bollinger Squeeze calculation error: {e}, falling back to price_range")
            return self._detect_price_range(prices)

    @staticmethod
    def _rolling_mean(data: np.ndarray, window: int) -> np.ndarray:
        """
        Calculate rolling mean - VECTORIZED with cumsum trick.

        O(n) complexity, no Python loops.
        """
        if len(data) < window:
            return None

        # Cumulative sum approach - O(n) and fully vectorized
        cumsum = np.cumsum(np.insert(data, 0, 0))
        return (cumsum[window:] - cumsum[:-window]) / window

    @staticmethod
    def _rolling_std(data: np.ndarray, window: int) -> np.ndarray:
        """
        Calculate rolling standard deviation - VECTORIZED.

        Uses the formula: std = sqrt(E[X^2] - E[X]^2)
        """
        if len(data) < window:
            return None

        # Rolling mean of data
        rolling_mean = RangeDetector._rolling_mean(data, window)
        if rolling_mean is None:
            return None

        # Rolling mean of data^2
        rolling_mean_sq = RangeDetector._rolling_mean(data**2, window)
        if rolling_mean_sq is None:
            return None

        # Variance = E[X^2] - E[X]^2
        variance = rolling_mean_sq - rolling_mean**2

        # Handle numerical precision issues (variance can be slightly negative)
        variance = np.maximum(variance, 0.0)

        return np.sqrt(variance)
