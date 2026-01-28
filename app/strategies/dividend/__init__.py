"""
Dividend Investing Strategy - Maximizar Dividendos

Este módulo implementa una estrategia completa de inversión en dividendos siguiendo
los principios de factor investing de Berkin & Swedroe y las mejores prácticas
de análisis de acciones de dividendos.

Objetivo: MAXIMIZAR_DIVIDENDOS
- Foco en alto dividend yield
- Consideración de dividend growth rate (sostenibilidad)
- Análisis de payout ratio (evitar dividend traps)
- Seguimiento de fechas ex-dividend

Estructura del módulo:
- DividendStrategy: Estrategia principal que hereda de BaseStrategy
- DividendScreener: Filtrado de acciones por métricas de dividendos
- DividendAnalyzer: Análisis de sostenibilidad y calidad
- DividendPortfolioConstructor: Construcción de portafolio optimizado
"""

from .dividend_analyzer import (
    DividendAnalyzer,
    DividendQualityScore,
    DividendSustainabilityMetrics,
)
from .dividend_portfolio_constructor import (
    DividendPortfolioConfig,
    DividendPortfolioConstructor,
)
from .dividend_screener import (
    DividendScreener,
    DividendScreeningCriteria,
    ScreeningResult,
)
from .dividend_strategy import DividendStrategy
from .models import (
    DividendData,
    DividendProfile,
    DividendStock,
    DividendStrategyConfig,
    ExDividendDate,
)

__all__ = [
    # Main strategy
    "DividendStrategy",
    # Screener
    "DividendScreener",
    "DividendScreeningCriteria",
    "ScreeningResult",
    # Analyzer
    "DividendAnalyzer",
    "DividendQualityScore",
    "DividendSustainabilityMetrics",
    # Portfolio constructor
    "DividendPortfolioConstructor",
    "DividendPortfolioConfig",
    # Models
    "DividendStrategyConfig",
    "DividendStock",
    "DividendData",
    "DividendProfile",
    "ExDividendDate",
]

# Strategy metadata for registry
STRATEGY_METADATA = {
    "name": "dividend",
    "description": "Dividend investing strategy - Maximizar dividendos con enfoque en yield sostenible y crecimiento",
    "category": "income",
    "tags": ["dividend", "income", "value", "yield", "passive"],
    "version": "1.0.0",
    "objetivo_inversion": "MAXIMIZAR_DIVIDENDOS",
    "risk_profile": "moderate",
    "horizon_recomendado": "long_term",
}
