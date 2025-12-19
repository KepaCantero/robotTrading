"""
MarketAnalyzer - Orquesta módulos detectores de régimen de mercado.
"""

import logging
from collections import deque
from typing import Dict, List, Optional

from .market_detectors.range_detector import RangeDetector
from .market_detectors.trend_detector import TrendDetector
from .market_detectors.volatility_detector import VolatilityDetector

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """
    Orquesta módulos de detección de régimen de mercado.

    Utiliza módulos modulares:
    - TrendDetector: Detecta tendencias
    - VolatilityDetector: Detecta régimen de volatilidad
    - RangeDetector: Detecta mercados en rango
    """

    def __init__(self, config: Dict):
        """
        Inicializar analizador de mercado con módulos detectores.

        Args:
            config: Configuración desde YAML
        """
        self.config = config
        self.enabled = config.get("enabled", True)

        # Inicializar módulos detectores modulares
        self.trend_detector = (
            TrendDetector(config)
            if config.get("trend_detection", {}).get("enabled", True)
            else None
        )
        self.volatility_detector = (
            VolatilityDetector(config)
            if config.get("volatility_detection", {}).get("enabled", True)
            else None
        )
        self.range_detector = (
            RangeDetector(config)
            if config.get("range_detection", {}).get("enabled", True)
            else None
        )

        # Históricos para los detectores
        self.price_history = deque(maxlen=200)
        self.atr_history = deque(maxlen=100)

    def analyze(self, market_data, price_history: List[float], atr_history: List[float]) -> Dict:
        """
        Analiza el contexto actual del mercado.

        Args:
            market_data: Datos de mercado actuales
            price_history: Histórico de precios
            atr_history: Histórico de ATR para cálculo de percentiles

        Returns:
            {
                'type': str,  # 'trend_up' | 'trend_down' | 'range' | 'high_vol' | 'low_vol'
                'confidence': float,  # 0.0-1.0
                'volatility_regime': str,  # 'high' | 'normal' | 'low'
                'trend_strength': float,  # 0.0-1.0
                'volatility_percentile': int  # 0-100
            }
        """
        if not self.enabled or len(price_history) < 26:
            return self._default_context()

        # Actualizar histórico
        min_period = 26  # EMA slow period mínimo
        if len(price_history) >= min_period:
            self.price_history.extend(price_history[-min_period:])
        if atr_history:
            self.atr_history.extend(atr_history[-30:])

        # 1. Detectar tendencia usando módulo TrendDetector
        trend_info = {}
        if self.trend_detector:
            trend_info = self.trend_detector.detect(price_history)
        else:
            trend_info = {'type': 'no_trend', 'strength': 0.0, 'confidence': 0.5}

        # 2. Detectar volatilidad usando módulo VolatilityDetector
        vol_info = {}
        if self.volatility_detector:
            vol_info = self.volatility_detector.detect(
                price_history, atr_history=atr_history if atr_history else []
            )
        else:
            vol_info = {'regime': 'normal', 'percentile': 50, 'confidence': 0.5}

        # 3. Detectar rango usando módulo RangeDetector
        range_info = {}
        if self.range_detector:
            range_info = self.range_detector.detect(price_history, trend_info=trend_info)
        else:
            range_info = {'in_range': False, 'range_size_pct': 0.0, 'confidence': 0.5}

        # 4. Combinar información de todos los módulos
        return self._combine_context(trend_info, vol_info, range_info)

    def _combine_context(self, trend_info: Dict, vol_info: Dict, range_info: Dict) -> Dict:
        """Combinar información de tendencia, volatilidad y rango."""
        # Determinar tipo principal
        market_type = 'range'  # Default

        if trend_info.get('type') == 'trend_up':
            market_type = 'trend_up'
        elif trend_info.get('type') == 'trend_down':
            market_type = 'trend_down'
        elif range_info.get('in_range', False):
            market_type = 'range'

        # Añadir información de volatilidad al tipo si es extrema
        if vol_info.get('regime') == 'high':
            if market_type in ['trend_up', 'trend_down']:
                market_type = 'high_vol'  # Priorizar volatilidad extrema
        elif vol_info.get('regime') == 'low':
            if market_type == 'range':
                market_type = 'low_vol'

        return {
            'type': market_type,
            'confidence': trend_info.get('strength', 0.5),
            'volatility_regime': vol_info.get('regime', 'normal'),
            'trend_strength': trend_info.get('strength', 0.0),
            'volatility_percentile': vol_info.get('percentile', 50),
            'in_range': range_info.get('in_range', False),
        }

    def _default_context(self) -> Dict:
        """Retornar contexto por defecto cuando no hay suficiente data."""
        return {
            'type': 'unknown',
            'confidence': 0.5,
            'volatility_regime': 'normal',
            'trend_strength': 0.0,
            'volatility_percentile': 50,
            'in_range': False,
        }
