"""
Covered Calls Strategy - Generación de Ingreso a través de Opciones

Este módulo implementa una estrategia completa de covered calls (llamadas cubiertas)
siguiendo los principios de factor investing y las mejores prácticas de gestión de
opciones para generación de ingresos.

Objetivo: INCOME_GENERATION
- Generar ingreso adicional vendiendo opciones de compra
- Mantener posición larga en el activo subyacente
- Ingreso por primas mientras se limita el potencial alcista
- Protección a la baja desde la prima recibida

Estructura del módulo:
- CoveredCallStrategy: Estrategia principal que hereda de BaseStrategy
- OptionScreener: Filtrado de opciones óptimas para vender
- GreeksCalculator: Cálculo de Delta, Theta, Vega, Gamma
- PositionManager: Gestión de posiciones covered call
- RollAnalyzer: Análisis de oportunidades de rolling
"""

from .covered_call_strategy import CoveredCallStrategy, RollDecision
from .greeks_calculator import BlackScholesGreeks, GreeksCalculator, OptionGreeks
from .models import (
    CallOption,
    CoveredCallConfig,
    CoveredCallPosition,
    OptionScreenerResult,
    OptionScreeningCriteria,
    OptionType,
    RollOpportunity,
    RollType,
)
from .option_screener import OptionScreener
from .position_manager import PositionManager
from .roll_analyzer import RollAnalyzer

__all__ = [
    # Main strategy
    "CoveredCallStrategy",
    "RollDecision",
    "RollType",
    # Models
    "CoveredCallConfig",
    "CallOption",
    "CoveredCallPosition",
    "RollOpportunity",
    "OptionType",
    "OptionScreeningCriteria",
    "OptionScreenerResult",
    # Greeks calculator
    "GreeksCalculator",
    "BlackScholesGreeks",
    "OptionGreeks",
    # Screener
    "OptionScreener",
    # Position manager
    "PositionManager",
    # Roll analyzer
    "RollAnalyzer",
]

# Strategy metadata for registry
STRATEGY_METADATA = {
    "name": "covered_calls",
    "description": "Covered calls strategy - Generacion de ingresos vendiendo opciones de compra sobre posiciones largas",
    "category": "income",
    "tags": ["covered_calls", "income", "options", "theta", "generation"],
    "version": "1.0.0",
    "objetivo_inversion": "INCOME_GENERATION",
    "risk_profile": "moderate",
    "horizon_recomendado": "short_to_medium_term",
}
