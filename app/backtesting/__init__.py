"""
Backtesting module for AlgoTrading system.

This module provides backtesting capabilities for trading strategies,
including historical data simulation, performance metrics calculation,
and strategy evaluation.

Includes:
- SimpleBacktester: Basic backtesting engine
- RobustBacktester: Advanced engine for 25+ year backtests with bias correction
- Walk-forward validation
- Monte Carlo simulation
- Stress testing
"""

from .engine import BacktestResult, SimpleBacktester
from .models import BacktestConfig, PerformanceMetrics, Trade
from .robust_engine import (
    CorporateActionHandler,
    CorporateActionType,
    DividendHandler,
    DripConfig,
    PerformanceTracker,
    RobustBacktestConfig,
    RobustBacktester,
    RobustBacktestResult,
    SurvivorshipAdjuster,
)
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

# Core backtesting
__all__ = [
    # Basic backtesting
    "SimpleBacktester",
    "BacktestResult",
    "BacktestConfig",
    "Trade",
    "PerformanceMetrics",
    # Robust backtesting (FASE 5.1)
    "RobustBacktester",
    "RobustBacktestConfig",
    "RobustBacktestResult",
    "CorporateActionHandler",
    "CorporateActionType",
    "DividendHandler",
    "DripConfig",
    "PerformanceTracker",
    "SurvivorshipAdjuster",
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
