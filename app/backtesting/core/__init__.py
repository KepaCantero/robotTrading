"""
Core backtesting modules.

This package contains the foundational components for the backtesting system:
- Config loading and validation
- Execution orchestration
- Result management
"""

from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.executor import BacktestExecutor
from app.backtesting.core.facade import BacktestRunnerFacade, create_backtest_runner
from app.backtesting.core.orchestrator import (
    BacktestDefaults,
    BacktestOrchestrator,
    BoundedResults,
    OrchestrationResult,
)

__all__ = [
    "BacktestConfigLoader",
    "BacktestExecutor",
    "BacktestOrchestrator",
    "BacktestDefaults",
    "BoundedResults",
    "OrchestrationResult",
    "BacktestRunnerFacade",
    "create_backtest_runner",
]
