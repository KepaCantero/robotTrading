"""
Strategy Engines - Motores de estrategias refactorizados.

Este módulo contiene los engines de estrategias que extienden BaseStrategy
con funcionalidades adicionales para integración con Learning Engines,
composición de estrategias, y feature extraction estandarizado.
"""

from .base import BaseStrategyEngine
from .momentum_engine import MomentumStrategyEngine
from .mean_reversion_engine import MeanReversionStrategyEngine
from .pairs_engine import PairsTradingStrategyEngine
from .modular_momentum_engine import ModularMomentumStrategyEngine

__all__ = [
    'BaseStrategyEngine',
    'MomentumStrategyEngine',
    'MeanReversionStrategyEngine',
    'PairsTradingStrategyEngine',
    'ModularMomentumStrategyEngine',
]

