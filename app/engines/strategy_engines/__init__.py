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
from .breakout_engine import BreakoutStrategyEngine
from .trend_following_engine import TrendFollowingStrategyEngine
from .arbitrage_engine import ArbitrageStrategyEngine
from .ensemble import (
    BaseStrategyEnsemble,
    WeightedEnsemble,
    RegimeBasedSelector,
    VotingEnsemble,
)

__all__ = [
    "BaseStrategyEngine",
    "MomentumStrategyEngine",
    "MeanReversionStrategyEngine",
    "PairsTradingStrategyEngine",
    "ModularMomentumStrategyEngine",
    "BreakoutStrategyEngine",
    "TrendFollowingStrategyEngine",
    "ArbitrageStrategyEngine",
    # Ensembles
    "BaseStrategyEnsemble",
    "WeightedEnsemble",
    "RegimeBasedSelector",
    "VotingEnsemble",
]

