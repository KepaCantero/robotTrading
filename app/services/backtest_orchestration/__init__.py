"""T4.1: BacktestOrchestrator - Backtesting orchestration and execution

Orchestrates backtesting for parametrized trading strategies.
Calculates feasibility_ratio for deployment decisions.
Integrates with existing backtesting infrastructure.
"""

from .backtest_orchestrator import (
    BacktestOrchestrator,
    get_backtest_orchestrator,
)
from .models import (
    BacktestConfig,
    BacktestResult,
    BacktestMetrics,
    BacktestStatus,
    BacktestOrchestrationRequest,
    BacktestOrchestrationResult,
)

__all__ = [
    "BacktestOrchestrator",
    "get_backtest_orchestrator",
    "BacktestConfig",
    "BacktestResult",
    "BacktestMetrics",
    "BacktestStatus",
    "BacktestOrchestrationRequest",
    "BacktestOrchestrationResult",
]
