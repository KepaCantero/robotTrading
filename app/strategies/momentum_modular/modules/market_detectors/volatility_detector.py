"""
VolatilityDetector - Módulo independiente para detectar régimen de volatilidad.
"""

import logging
from typing import Dict, List, Optional

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class VolatilityDetector(BaseMarketDetector):
    """
    Detecta régimen de volatilidad: high, normal, low.
    
    Métodos soportados:
    - atr_percentile: Percentil de ATR histórico
    - std_dev: Desviación estándar de retornos
    """
    
    def __init__(self, config: Dict):
        """Inicializar detector de volatilidad."""
        super().__init__("volatility_detector", config)
        
        vol_config = config.get("volatility_detection", {})
        self.method = vol_config.get("method", "atr_percentile")
        self.percentile_window = vol_config.get("percentile_window", 30)
        self.high_vol_threshold = vol_config.get("high_vol_threshold", 75)
        self.low_vol_threshold = vol_config.get("low_vol_threshold", 25)
    
    def detect(self, price_history: List[float], **kwargs) -> Dict:
        """
        Detectar régimen de volatilidad.
        
        Args:
            atr_history: Histórico de ATR (si está disponible)
        
        Returns:
            {
                'regime': 'high' | 'normal' | 'low',
                'percentile': int,  # 0-100
                'confidence': float,
                'method': str
            }
        """
        if not self.enabled:
            return {
                'regime': 'normal',
                'percentile': 50,
                'confidence': 0.5,
                'method': self.method
            }
        
        atr_history = kwargs.get("atr_history", [])
        
        if self.method == "atr_percentile":
            return self._detect_atr_percentile(atr_history)
        elif self.method == "std_dev":
            return self._detect_std_dev(price_history)
        else:
            logger.warning(f"Unknown volatility detection method: {self.method}")
            return self._detect_atr_percentile(atr_history)
    
    def _detect_atr_percentile(self, atr_history: List[float]) -> Dict:
        """Detectar volatilidad usando percentil de ATR."""
        if len(atr_history) < self.percentile_window:
            return {
                'regime': 'normal',
                'percentile': 50,
                'confidence': 0.5,
                'method': 'atr_percentile'
            }
        
        # Calcular percentil del ATR actual
        current_atr = atr_history[-1]
        sorted_atr = sorted(atr_history[-self.percentile_window:])
        percentile = (sorted_atr.index(current_atr) / len(sorted_atr)) * 100 if current_atr in sorted_atr else 50
        
        if percentile >= self.high_vol_threshold:
            regime = 'high'
            confidence = min(1.0, (percentile - self.high_vol_threshold) / 25)
        elif percentile <= self.low_vol_threshold:
            regime = 'low'
            confidence = min(1.0, (self.low_vol_threshold - percentile) / 25)
        else:
            regime = 'normal'
            # Confianza basada en qué tan cerca del centro
            center = (self.high_vol_threshold + self.low_vol_threshold) / 2
            distance = abs(percentile - center)
            max_distance = (self.high_vol_threshold - self.low_vol_threshold) / 2
            confidence = 1.0 - (distance / max_distance) * 0.5
        
        return {
            'regime': regime,
            'percentile': int(percentile),
            'confidence': confidence,
            'method': 'atr_percentile',
            'metadata': {
                'current_atr': current_atr,
                'atr_history_length': len(atr_history)
            }
        }
    
    def _detect_std_dev(self, price_history: List[float]) -> Dict:
        """Detectar volatilidad usando desviación estándar de retornos."""
        if len(price_history) < 30:
            return {
                'regime': 'normal',
                'percentile': 50,
                'confidence': 0.5,
                'method': 'std_dev'
            }
        
        # Calcular retornos
        returns = []
        for i in range(1, len(price_history)):
            if price_history[i-1] > 0:
                ret = (price_history[i] - price_history[i-1]) / price_history[i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return {
                'regime': 'normal',
                'percentile': 50,
                'confidence': 0.5,
                'method': 'std_dev'
            }
        
        import numpy as np
        std_dev = np.std(returns)
        
        # Calcular percentil basado en ventana histórica
        # Para simplificar, usar umbrales absolutos
        # En producción, calcular percentil real
        high_threshold = 0.02  # 2% std dev
        low_threshold = 0.005  # 0.5% std dev
        
        if std_dev >= high_threshold:
            regime = 'high'
            percentile = 75 + min(25, (std_dev - high_threshold) / high_threshold * 25)
        elif std_dev <= low_threshold:
            regime = 'low'
            percentile = 25 - min(25, (low_threshold - std_dev) / low_threshold * 25)
        else:
            regime = 'normal'
            percentile = 50
        
        return {
            'regime': regime,
            'percentile': int(percentile),
            'confidence': 0.7,
            'method': 'std_dev',
            'metadata': {'std_dev': float(std_dev)}
        }

