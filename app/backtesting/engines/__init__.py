"""
Backtest Engines Package.

Concrete engines on top of BaseBacktestEngine:
- StandardBacktestEngine: per-strategy execution (used internally by the
  multi-strategy engine)
- ExecutionBacktestEngine: pessimistic execution engine
- MultiStrategyBacktestEngine: multi-strategy with capital allocation
  (used by ComprehensiveBacktestRunner)

Usage:
    from app.backtesting.engines import MultiStrategyBacktestEngine

    engine = MultiStrategyBacktestEngine(config)
    result = engine.run_backtest(market_data, signals)
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
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine
from app.backtesting.engines.standard_engine import StandardBacktestEngine

__all__ = [
    "BacktestState",
    "BaseBacktestEngine",
    "EngineType",
    "ExecutionBacktestEngine",
    "ExecutionResult",
    "ExecutionType",
    "MultiStrategyBacktestEngine",
    "Position",
    "StandardBacktestEngine",
]
