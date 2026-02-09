"""
Execution services for integrating execution engines with ITradeExecutor.

This module provides adapters that connect different execution engines with
the coordinator layer (ComplianceEngine).

Available adapters:
- ExecutionEngineAdapter: For backtesting with PessimisticExecutionEngine
- OrderManagerAdapter: For live trading with OrderManager
"""

from app.services.execution.execution_adapter import ExecutionEngineAdapter
from app.services.execution.order_manager_adapter import OrderManagerAdapter

__all__ = [
    "ExecutionEngineAdapter",
    "OrderManagerAdapter",
]
