"""
Backtesting module for AlgoTrading system.

This module provides backtesting capabilities for trading strategies,
including historical data simulation, performance metrics calculation,
and strategy evaluation.
"""

from .engine import BacktestResult, SimpleBacktester
from .models import BacktestConfig, PerformanceMetrics, Trade
from .walk_forward_validator import (
    ComprehensiveValidator,
    CrossValidationTemporal,
    MonteCarloSimulator,
    StressTester,
    SyntheticDataGenerator,
    ValidationReport,
    WalkForwardValidator,
    load_validation_config,
)

__all__ = [
    # Core backtesting
    "SimpleBacktester",
    "BacktestResult",
    "BacktestConfig",
    "Trade",
    "PerformanceMetrics",
    # Validation (Task 3.5)
    "WalkForwardValidator",
    "CrossValidationTemporal",
    "SyntheticDataGenerator",
    "StressTester",
    "MonteCarloSimulator",
    "ComprehensiveValidator",
    "ValidationReport",
    "load_validation_config",
]
