"""
VolatilityRegimeDetector - Detección de regímenes de volatilidad.

Clasifica volatilidad en high/normal/low usando percentiles.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class VolatilityRegimeDetector:
    """
    Detector de régimen de volatilidad.

    Clasifica volatilidad en high/normal/low basado en percentiles históricos.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar detector.

        Args:
            config: Configuración
        """
        config = config or {}
        self.high_threshold = config.get('high_threshold', 75)  # Percentil 75
        self.low_threshold = config.get('low_threshold', 25)  # Percentil 25
        self.window_size = config.get('window_size', 100)
        self.min_samples = config.get('min_samples', 50)

        self.historical_volatility = []

    def _calculate_volatility(self, prices: List[float], window: int = 20) -> float:
        """Calcular volatilidad usando rolling std de returns."""
        if len(prices) < window + 1:
            return 0.0

        returns = np.diff(prices[-window - 1:]) / prices[-window - 1: -1]
        return float(np.std(returns))

    def detect(
        self, prices: List[float], volatility_history: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Detectar régimen de volatilidad.

        Args:
            prices: Lista de precios
            volatility_history: Historial de volatilidad (opcional)

        Returns:
            Dict con régimen detectado
        """
        if len(prices) < self.min_samples:
            return {'regime': 'unknown', 'volatility': 0.0, 'percentile': 50, 'confidence': 0.0}

        try:
            # Calcular volatilidad actual
            current_vol = self._calculate_volatility(prices)

            # Construir historial de volatilidad
            if volatility_history:
                vol_history = volatility_history[-self.window_size:]
            else:
                # Calcular historial de volatilidad
                vol_history = []
                for i in range(20, len(prices)):
                    window_prices = prices[max(0, i - self.window_size): i + 1]
                    vol = self._calculate_volatility(window_prices)
                    vol_history.append(vol)

            # Agregar volatilidad actual
            vol_history.append(current_vol)

            # Actualizar histórico
            self.historical_volatility.extend(vol_history[-self.window_size:])
            self.historical_volatility = self.historical_volatility[-self.window_size:]

            if len(self.historical_volatility) < self.min_samples:
                return {
                    'regime': 'unknown',
                    'volatility': current_vol,
                    'percentile': 50,
                    'confidence': 0.0,
                }

            # Calcular percentil
            percentile = float(stats.percentileofscore(self.historical_volatility, current_vol))

            # Determinar régimen
            if percentile >= self.high_threshold:
                regime = 'high'
            elif percentile <= self.low_threshold:
                regime = 'low'
            else:
                regime = 'normal'

            # Calcular confianza (distancia al threshold más cercano)
            if regime == 'high':
                confidence = min(1.0, (percentile - self.high_threshold) / 25)
            elif regime == 'low':
                confidence = min(1.0, (self.low_threshold - percentile) / 25)
            else:
                # Normal: confianza basada en distancia al centro
                distance_from_center = abs(percentile - 50)
                confidence = max(0.0, 1.0 - distance_from_center / 25)

            return {
                'regime': regime,
                'volatility': current_vol,
                'percentile': percentile,
                'confidence': confidence,
                'historical_mean': float(np.mean(self.historical_volatility)),
                'historical_std': float(np.std(self.historical_volatility)),
            }

        except Exception as e:
            logger.error(f"Error detectando régimen de volatilidad: {e}")
            return {'regime': 'unknown', 'volatility': 0.0, 'percentile': 50, 'confidence': 0.0}
