"""
Backtest Engines Package.

The single execution motor is app.backtesting.engine.BacktestEngine
(golden-tested: t+1, IBKR costs, cash reconciliation). This package keeps
only the pessimistic execution engine (test-only library) on top of
BaseBacktestEngine.
"""

from app.backtesting.base_engine import (
    BacktestState,
    BaseBacktestEngine,
    EngineType,
    ExecutionResult,
    ExecutionType,
    Position,
)
from app.backtesting.engines.execution_engine import ExecutionBacktestEngine

__all__ = [
    "BacktestState",
    "BaseBacktestEngine",
    "EngineType",
    "ExecutionBacktestEngine",
    "ExecutionResult",
    "ExecutionType",
    "Position",
]
