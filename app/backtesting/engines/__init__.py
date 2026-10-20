"""
Backtest Engines Package.

Concrete engines on top of BaseBacktestEngine:
- MultiStrategyBacktestEngine: multi-strategy with capital allocation
  (used by ComprehensiveBacktestRunner). Per-strategy EXECUTION delegates
  to app.backtesting.engine.BacktestEngine — the single, golden-tested
  motor (t+1, IBKR costs, cash reconciliation).

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
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine

__all__ = [
    "BacktestState",
    "BaseBacktestEngine",
    "EngineType",
    "ExecutionResult",
    "ExecutionType",
    "MultiStrategyBacktestEngine",
    "Position",
]
