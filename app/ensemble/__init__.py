"""
Ensemble Methods Module for Algorithmic Trading

This module provides ensemble methods for combining multiple trading strategies,
including:
- Multi-objective optimization with Pareto fronts
- Ensemble voting mechanisms
- Strategy combination and allocation
- Correlation analysis and redundancy detection
- Risk parity and mean-variance optimization
"""

from .correlation_analyzer import CorrelationAnalyzer
from .ensemble import EnsembleVoting
from .models import (
    CombinedPortfolio,
    CorrelationMetrics,
    EnsembleConfig,
    EnsembleSignal,
    ObjectiveConfig,
    ParetoSolution,
    StrategyAllocation,
)
from .pareto import ParetoFrontOptimizer
from .strategy_combiner import StrategyCombiner

__all__ = [
    # Models
    "ObjectiveConfig",
    "ParetoSolution",
    "EnsembleConfig",
    "EnsembleSignal",
    "StrategyAllocation",
    "CombinedPortfolio",
    "CorrelationMetrics",
    # Classes
    "ParetoFrontOptimizer",
    "EnsembleVoting",
    "StrategyCombiner",
    "CorrelationAnalyzer",
]
