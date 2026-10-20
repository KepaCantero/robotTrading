"""
Backtesting module for AlgoTrading system.

This module provides backtesting capabilities for trading strategies,
including historical data simulation, performance metrics calculation,
and strategy evaluation.

Includes:
- SimpleBacktester: Basic backtesting engine
- Walk-forward validation (WalkForwardValidator, TomasiniWalkForwardValidator)
- Monte Carlo simulation
- Stress testing
- BacktestingCompliance: Validacion de reglas R5, R6, R7, DATA-001

Engine hierarchy (app.backtesting.engines)
- BaseBacktestEngine: Abstract base class for all engines
- MultiStrategyBacktestEngine: Multi-strategy with capital allocation;
  per-strategy execution delegates to the single motor below

COMPLIANCE: Todos los backtests deben usar BacktestingCompliance para validar
las reglas de backtesting segun .ralph/rules/rules_mapping.yml:
- R5: Walk-Forward Analysis
- R6: Overfitting Prevention (ratio < 1:30)
- R7: Monte Carlo para riesgo
- DATA-001: Purged Cross-Validation
"""

from .backtesting_compliance import (
    BacktestingCompliance,
    BacktestingComplianceResult,
    ComplianceViolation,
    create_backtesting_compliance,
    validate_backtest_quick,
)
from .engine import BacktestResult, SimpleBacktester
from .models import BacktestConfig, PerformanceMetrics, Trade, TradeSide, TradeStatus
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
from .walk_forward_validator_enhanced import (
    ParameterHistory,
    ParameterStabilityMetrics,
    TomasiniWalkForwardResult,
    TomasiniWalkForwardValidator,
)

# Core backtesting
__all__ = [
    "BacktestConfig",
    "BacktestResult",
    # Backtesting Compliance (R5, R6, R7, DATA-001)
    "BacktestingCompliance",
    "BacktestingComplianceResult",
    "ComplianceViolation",
    "ComprehensiveValidator",
    "CrossValidationTemporal",
    "MonteCarloSimulator",
    "ParameterHistory",
    "ParameterStabilityMetrics",
    "PerformanceMetrics",
    # Basic backtesting
    "SimpleBacktester",
    "StressTester",
    "SyntheticDataGenerator",
    "TomasiniWalkForwardResult",
    # Tomasini Walk-Forward (Enhanced)
    "TomasiniWalkForwardValidator",
    "Trade",
    "TradeSide",
    "TradeStatus",
    "ValidationReport",
    # Validation (Task 3.5)
    "WalkForwardValidator",
    "create_backtesting_compliance",
    "load_validation_config",
    "validate_backtest_quick",
]

# NEW: Unified Engine Hierarchy
# Import the new engine hierarchy for advanced use cases
# These provide a cleaner abstraction over the original engines
from app.backtesting.base_engine import (
    BacktestState as BacktestState,
    BaseBacktestEngine as BaseBacktestEngine,
    EngineType as EngineType,
    ExecutionResult as ExecutionResult,
    ExecutionType as ExecutionType,
    Position as Position,
)

# Add new engine exports
__all__.extend(
    [
        "BacktestState",
        # Base classes and types
        "BaseBacktestEngine",
        "EngineType",
        "ExecutionResult",
        "ExecutionType",
        "Position",
    ]
)
