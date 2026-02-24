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
    BaseBacktestEngine,
    BacktestState,
    EngineType,
    ExecutionType,
    ExecutionResult,
    Position,
)

from app.backtesting.engines.standard_engine import StandardBacktestEngine
from app.backtesting.engines.execution_engine import ExecutionBacktestEngine
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine
from app.backtesting.engines.robust_engine import RobustBacktestEngine
from app.backtesting.engines.factory import EngineFactory

__all__ = [
    # Base classes and types
    "BaseBacktestEngine",
    "BacktestState",
    "EngineType",
    "ExecutionType",
    "ExecutionResult",
    "Position",
    # Concrete engines
    "StandardBacktestEngine",
    "ExecutionBacktestEngine",
    "MultiStrategyBacktestEngine",
    "RobustBacktestEngine",
    # Factory
    "EngineFactory",
]
