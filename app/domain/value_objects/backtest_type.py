"""
BacktestType Enum - Types of backtesting operations

Defines the different types of backtests supported by the system.
"""

from enum import Enum


class BacktestType(Enum):
    """Types of backtests supported by the system."""

    BASELINE = "baseline"
    LEARNING_ENGINES = "learning_engines"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    TRANSFORMER_OPTIMIZATION = "transformer_optimization"
    ABLATION = "ablation"
    GRID_SEARCH = "grid_search"
    OUT_OF_SAMPLE = "out_of_sample"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_TEST = "regime_test"
