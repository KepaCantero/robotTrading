"""
Backtesting module for AlgoTrading system.

This module provides backtesting capabilities for trading strategies,
including historical data simulation, performance metrics calculation,
and strategy evaluation.
"""

from .engine import BacktestResult, SimpleBacktester
from .models import BacktestConfig, PerformanceMetrics, Trade

__all__ = [
    "SimpleBacktester",
    "BacktestResult",
    "BacktestConfig",
    "Trade",
    "PerformanceMetrics",
]
