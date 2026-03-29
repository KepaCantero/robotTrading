"""
Unified Backtest Engines Package.

This package provides a unified hierarchy of backtest engines:
- BaseBacktestEngine: Abstract base class (in parent directory)
- StandardBacktestEngine: Standard single-strategy backtest
- ExecutionBacktestEngine: Pessimistic execution engine
- MultiStrategyBacktestEngine: Multi-strategy with capital allocation
- RobustBacktestEngine: Long-term robust backtest with checkpointing

Usage:
    from app.backtesting.engines import (
        StandardBacktestEngine,
        ExecutionBacktestEngine,
        MultiStrategyBacktestEngine,
        RobustBacktestEngine,
        EngineFactory,
    )

    # Using factory
    engine = EngineFactory.create(
        engine_type=EngineType.STANDARD,
        config=my_config,
    )
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
from app.backtesting.engines.factory import EngineFactory
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine
from app.backtesting.engines.robust_engine import RobustBacktestEngine
from app.backtesting.engines.standard_engine import StandardBacktestEngine

__all__ = [
    "BacktestState",
    # Base classes and types
    "BaseBacktestEngine",
    # Factory
    "EngineFactory",
    "EngineType",
    "ExecutionBacktestEngine",
    "ExecutionResult",
    "ExecutionType",
    "MultiStrategyBacktestEngine",
    "Position",
    "RobustBacktestEngine",
    # Concrete engines
    "StandardBacktestEngine",
]
