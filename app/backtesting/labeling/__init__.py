"""
Financial ML Labeling module for AlgoTrading system.

This module provides advanced labeling techniques for machine learning in finance,
following the methodologies from Marcos López de Prado's "Advances in Financial Machine Learning".

Key components:
- Triple Barrier Method: Dynamic labeling based on price barriers
- Meta-labeling: Secondary labeling for position sizing
- Volatility-adjusted barriers: Dynamic barrier adjustment based on market conditions
"""

from .triple_barrier import (
    TripleBarrierLabeler,
    TripleBarrierConfig,
    calculate_dynamic_barriers,
    get_vertical_barriers,
    plot_triple_barrier,
)

__all__ = [
    "TripleBarrierLabeler",
    "TripleBarrierConfig",
    "calculate_dynamic_barriers",
    "get_vertical_barriers",
    "plot_triple_barrier",
]
