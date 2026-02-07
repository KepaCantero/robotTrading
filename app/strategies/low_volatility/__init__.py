"""
Low Volatility Strategy - Minimizar Volatilidad del Portafolio

Este módulo implementa una estrategia completa de inversión de baja volatilidad siguiendo
los principios de factor investing de Berkin & Swedroe y las mejores prácticas
de gestión de riesgo de portafolio.

Objetivo: CAPITAL_PRESERVATION
- Minimizar volatilidad del portafolio
- Foco en acciones de baja beta y baja volatilidad histórica
- Sesgo hacia sectores defensivos
- Optimización de varianza mínima (MVO)
- Targeting de volatilidad

Estructura del módulo:
- LowVolatilityStrategy: Estrategia principal que hereda de BaseStrategy
- VolatilityCalculator: Cálculo de métricas de volatilidad
- LowBetaScreener: Filtrado de acciones por volatilidad
- LowVolatilityPortfolioConstructor: Construcción de portafolio optimizado
"""

from .low_beta_screener import (
    LowBetaScreener,
    LowVolatilityScreeningCriteria,
    ScreeningResult as LowVolScreeningResult,
)
from .low_volatility_strategy import LowVolatilityStrategy
from .models import (
    LowVolatilityProfile,
    LowVolatilityStock,
    LowVolatilityStrategyConfig,
    VolatilityMetrics,
)
from .portfolio_constructor import (
    LowVolatilityPortfolio,
    LowVolatilityPortfolioConfig,
    LowVolatilityPortfolioConstructor,
)
from .volatility_calculator import VolatilityCalculator, VolatilityMetrics as VolMetrics

__all__ = [
    # Main strategy
    "LowVolatilityStrategy",
    # Calculator
    "VolatilityCalculator",
    "VolMetrics",
    # Screener
    "LowBetaScreener",
    "LowVolatilityScreeningCriteria",
    "LowVolScreeningResult",
    # Portfolio constructor
    "LowVolatilityPortfolioConstructor",
    "LowVolatilityPortfolio",
    "LowVolatilityPortfolioConfig",
    # Models
    "LowVolatilityStrategyConfig",
    "VolatilityMetrics",
    "LowVolatilityProfile",
    "LowVolatilityStock",
]

# Strategy metadata for registry
STRATEGY_METADATA = {
    "name": "low_volatility",
    "description": "Low volatility strategy - Minimizar volatilidad del portafolio con acciones de baja beta y optimización de varianza mínima",
    "category": "capital_preservation",
    "tags": ["low_volatility", "low_beta", "min_variance", "defensive", "risk_management"],
    "version": "1.0.0",
    "objetivo_inversion": "CAPITAL_PRESERVATION",
    "risk_profile": "conservative",
    "horizon_recomendado": "long_term",
}
