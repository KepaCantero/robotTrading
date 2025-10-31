"""
Módulos detectores de régimen de mercado.
Cada tipo de detección es un módulo independiente.
"""

from .base_detector import BaseMarketDetector
from .trend_detector import TrendDetector
from .volatility_detector import VolatilityDetector
from .range_detector import RangeDetector

__all__ = [
    "BaseMarketDetector",
    "TrendDetector",
    "VolatilityDetector",
    "RangeDetector",
]

