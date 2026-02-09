"""
Execution services for integrating PessimisticExecutionEngine with ITradeExecutor.

This module provides adapters that connect the backtesting execution engine
with the coordinator layer (ComplianceEngine).
"""

from app.services.execution.execution_adapter import ExecutionEngineAdapter

__all__ = ["ExecutionEngineAdapter"]
