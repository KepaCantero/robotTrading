"""
RangeDetector - Módulo independiente para detectar mercados en rango.
"""

import logging
from typing import Dict, List

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class RangeDetector(BaseMarketDetector):
    """
    Detecta si el mercado está en rango lateral.

    Métodos soportados:
    - bollinger_squeeze: Bandas de Bollinger estrechas
    - price_range: Rango de precios limitado
    """

    def __init__(self, config: Dict):
        """Inicializar detector de rangos."""
        super().__init__("range_detector", config)

        range_config = config.get("range_detection", {})
        self.method = range_config.get("method", "bollinger_squeeze")
        self.lookback_period = range_config.get("lookback_period", 20)
        self.squeeze_threshold = range_config.get("squeeze_threshold", 0.1)
        self.max_range_pct = range_config.get("max_range_pct", 0.03)  # 3%

    def detect(self, price_history: List[float], **kwargs) -> Dict:
        """
        Detectar si el mercado está en rango.

        Returns:
            {
                'in_range': bool,
                'range_size_pct': float,
                'confidence': float,
                'method': str
            }
        """
        if not self.enabled or len(price_history) < self.lookback_period:
            return {
                'in_range': False,
                'range_size_pct': 1.0,
                'confidence': 0.5,
                'method': self.method,
            }

        # Si hay tendencia clara (pasado como parámetro), no está en rango
        trend_info = kwargs.get("trend_info", {})
        if trend_info.get('strength', 0) > 0.5:
            return {
                'in_range': False,
                'range_size_pct': 0.0,
                'confidence': 1.0,
                'method': self.method,
                'reason': 'Strong trend detected',
            }

        if self.method == "bollinger_squeeze":
            return self._detect_bollinger_squeeze(price_history, **kwargs)
        elif self.method == "price_range":
            return self._detect_price_range(price_history)
        else:
            logger.warning(f"Unknown range detection method: {self.method}")
            return self._detect_price_range(price_history)

    def _detect_price_range(self, price_history: List[float]) -> Dict:
        """Detectar rango basado en tamaño de movimiento de precios."""
        recent_prices = price_history[-self.lookback_period :]
        price_range = max(recent_prices) - min(recent_prices)
        avg_price = sum(recent_prices) / len(recent_prices)

        # Si el rango es < umbral del precio promedio, considerar que está en rango
        range_pct = price_range / avg_price if avg_price > 0 else 1.0

        in_range = range_pct < self.max_range_pct

        # Calcular confianza basada en qué tan pequeño es el rango
        confidence = (
            min(1.0, (self.max_range_pct - range_pct) / self.max_range_pct * 2) if in_range else 0.0
        )

        return {
            'in_range': in_range,
            'range_size_pct': range_pct,
            'confidence': confidence,
            'method': 'price_range',
            'metadata': {'price_range': price_range, 'avg_price': avg_price},
        }

    def _detect_bollinger_squeeze(self, price_history: List[float], **kwargs) -> Dict:
        """Detectar rango usando Bollinger Squeeze (futuro)."""
        # TODO: Implementar Bollinger Squeeze detection
        logger.debug("Bollinger Squeeze detection not yet implemented, falling back to price_range")
        return self._detect_price_range(price_history)
