"""
Execution module - re-exports from domain layer for backward compatibility.
"""

from app.domain.services.execution.execution_adapter import ExecutionConfig, ExecutionEngineAdapter
from app.domain.services.execution.order_manager_adapter import OrderManagerAdapter
from app.domain.services.execution.trading_bridge_adapter import (
    TradingBridgeAdapter,
    TradingBridgeConfig,
)

__all__ = [
    "ExecutionEngineAdapter",
    "ExecutionConfig",
    "OrderManagerAdapter",
    "TradingBridgeAdapter",
    "TradingBridgeConfig",
]
