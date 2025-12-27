"""
Strategy Engines - Motores de estrategias refactorizados.

Este módulo contiene los engines de estrategias que extienden BaseStrategy
con funcionalidades adicionales para integración con Learning Engines,
composición de estrategias, y feature extraction estandarizado.
"""

from .arbitrage_engine import ArbitrageStrategyEngine
from .base import BaseStrategyEngine
from .breakout_engine import BreakoutStrategyEngine
from .ensemble import BaseStrategyEnsemble, RegimeBasedSelector, VotingEnsemble, WeightedEnsemble
from .mean_reversion_engine import MeanReversionStrategyEngine
from .modular_momentum_engine import ModularMomentumStrategyEngine
from .momentum_engine import MomentumStrategyEngine
from .pairs_engine import PairsTradingStrategyEngine
from .trend_following_engine import TrendFollowingStrategyEngine

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
