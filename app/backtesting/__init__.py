"""
Backtesting module for AlgoTrading system.

This module provides backtesting capabilities for trading strategies,
including historical data simulation, performance metrics calculation,
and strategy evaluation.

Includes:
- SimpleBacktester: Basic backtesting engine
- RobustBacktester: Advanced engine for 25+ year backtests with bias correction
- Walk-forward validation (WalkForwardValidator, TomasiniWalkForwardValidator)
- Monte Carlo simulation
- Stress testing
- BacktestingCompliance: Validación de reglas R5, R6, R7, DATA-001

COMPLIANCE: Todos los backtests deben usar BacktestingCompliance para validar
las reglas de backtesting según .ralph/rules/rules_mapping.yml:
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
from .walk_forward_validator_enhanced import (
    ParameterHistory,
    ParameterStabilityMetrics,
    TomasiniWalkForwardResult,
    TomasiniWalkForwardValidator,
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
    # Tomasini Walk-Forward (Enhanced)
    "TomasiniWalkForwardValidator",
    "TomasiniWalkForwardResult",
    "ParameterHistory",
    "ParameterStabilityMetrics",
    # Backtesting Compliance (R5, R6, R7, DATA-001)
    "BacktestingCompliance",
    "BacktestingComplianceResult",
    "ComplianceViolation",
    "create_backtesting_compliance",
    "validate_backtest_quick",
]
