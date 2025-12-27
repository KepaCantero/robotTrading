"""
Módulos detectores de régimen de mercado.
Cada tipo de detección es un módulo independiente.
"""

from .base_detector import BaseMarketDetector
from .range_detector import RangeDetector
from .trend_detector import TrendDetector
from .volatility_detector import VolatilityDetector

    "BaseMarketDetector",
    "TrendDetector",
    "VolatilityDetector",
    "RangeDetector",
]
