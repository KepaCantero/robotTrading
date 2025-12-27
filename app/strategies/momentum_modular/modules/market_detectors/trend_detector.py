"""
TrendDetector - Módulo independiente para detectar tendencias.
"""

import logging
from typing import Dict, List, Optional

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class TrendDetector(BaseMarketDetector):
    """
    Detecta tendencias alcistas, bajistas o ausencia de tendencia.

    Métodos soportados:
    - ema_cross: Cruce de EMAs
    - adx: Average Directional Index
    - macd: MACD
    """

    def __init__(self, config: Dict):
        """Inicializar detector de tendencias."""
        super().__init__("trend_detector", config)

        trend_config = config.get("trend_detection", {})
        self.method = trend_config.get("method", "ema_cross")
        self.ema_fast_period = trend_config.get("ema_fast_period", 12)
        self.ema_slow_period = trend_config.get("ema_slow_period", 26)
        self.min_trend_strength = trend_config.get("min_trend_strength", 0.6)

    def detect(self, price_history: List[float], **kwargs) -> Dict:
        """
        Detectar tendencia.

        Returns:
            {
                'type': 'trend_up' | 'trend_down' | 'no_trend',
                'strength': float,  # 0.0-1.0
                'confidence': float,  # 0.0-1.0
                'method': str
            }
        """
        if not self.enabled or len(price_history) < self.ema_slow_period:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': self.method}

        if self.method == "ema_cross":
            return self._detect_ema_cross(price_history)
        elif self.method == "adx":
            return self._detect_adx(price_history, **kwargs)
        elif self.method == "macd":
            return self._detect_macd(price_history, **kwargs)
        else:
            logger.warning(f"Unknown trend detection method: {self.method}")
            return self._detect_ema_cross(price_history)

    def _detect_ema_cross(self, price_history: List[float]) -> Dict:
        """Detectar tendencia usando cruce de EMAs."""
        # Calcular EMAs
        ema_fast = self._calculate_ema(price_history[-self.ema_fast_period :])
        ema_slow = self._calculate_ema(price_history[-self.ema_slow_period :])
        current_price = price_history[-1]

        if ema_fast is None or ema_slow is None:
            return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.0, 'method': 'ema_cross'}

        # Determinar dirección y fuerza
        fast_above_slow = ema_fast > ema_slow
        price_above_fast = current_price > ema_fast

        # Calcular fuerza de tendencia
        if fast_above_slow and price_above_fast:
            # Tendencia alcista
            distance = (ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0
            strength = min(1.0, distance / 0.05)
            confidence = min(1.0, strength / self.min_trend_strength)

            if strength >= self.min_trend_strength:
                return {
                    'type': 'trend_up',
                    'strength': strength,
                    'confidence': confidence,
                    'method': 'ema_cross',
                    'metadata': {
                        'ema_fast': ema_fast,
                        'ema_slow': ema_slow,
                        'distance_pct': distance,
                    },
                }

        elif not fast_above_slow and not price_above_fast:
            # Tendencia bajista
            distance = (ema_slow - ema_fast) / ema_fast if ema_fast > 0 else 0
            strength = min(1.0, distance / 0.05)
            confidence = min(1.0, strength / self.min_trend_strength)

            if strength >= self.min_trend_strength:
                return {
                    'type': 'trend_down',
                    'strength': strength,
                    'confidence': confidence,
                    'method': 'ema_cross',
                    'metadata': {
                        'ema_fast': ema_fast,
                        'ema_slow': ema_slow,
                        'distance_pct': distance,
                    },
                }

        return {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.5, 'method': 'ema_cross'}

    def _detect_adx(self, price_history: List[float], **kwargs) -> Dict:
        """Detectar tendencia usando ADX (futuro)."""
        # TODO: Implementar ADX detection
        logger.debug("ADX detection not yet implemented, falling back to EMA")
        return self._detect_ema_cross(price_history)

    def _detect_macd(self, price_history: List[float], **kwargs) -> Dict:
        """Detectar tendencia usando MACD (futuro)."""
        # TODO: Implementar MACD detection
        logger.debug("MACD detection not yet implemented, falling back to EMA")
        return self._detect_ema_cross(price_history)

    def _calculate_ema(self, prices: List[float]) -> Optional[float]:
        """Calcular EMA simple."""
        if not prices:
            return None

        multiplier = 2.0 / (len(prices) + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema

        return ema
