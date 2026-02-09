"""
Execution services for integrating execution engines with ITradeExecutor.

This module provides adapters that connect different execution engines with
the coordinator layer (ComplianceEngine).

Available adapters:
- ExecutionEngineAdapter: For backtesting with PessimisticExecutionEngine
- OrderManagerAdapter: For live trading with OrderManager
- TradingBridgeAdapter: For live trading with TradingBridgeOrchestrator
"""

from app.services.execution.execution_adapter import (
    ExecutionEngineAdapter,
    get_execution_adapter,
)
from app.services.execution.order_manager_adapter import OrderManagerAdapter
from app.services.execution.trading_bridge_adapter import (
    TradingBridgeAdapter,
    get_trading_bridge_adapter,
)

__all__ = [
    "ExecutionEngineAdapter",
    "get_execution_adapter",
    "OrderManagerAdapter",
    "TradingBridgeAdapter",
    "get_trading_bridge_adapter",
]
