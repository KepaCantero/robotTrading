"""
Protocols for Strategy Registry and Logger - Dependency Inversion.

These Protocols enable SOL-005 (Dependency Inversion Principle) and DP-004
(Dependency Injection) by allowing ExecutionEngine to depend on abstractions
rather than concrete classes. This improves testability and maintainability.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from app.models.signal import Signal


class StrategyRegistryProto(Protocol):
    """Protocol for strategy registry - allows mocking in tests."""

    @property
    def active_strategy(self) -> Optional[str]:
        """Name of active strategy."""
        ...

    def get_active_strategy(self) -> Optional[Any]:
        """Get currently active strategy."""
        ...


class StrategyLoggerProto(Protocol):
    """Protocol for strategy logger - allows mocking in tests."""

    def log_signal_generated(
        self,
        strategy_name: str,
        signal: Signal,
    ) -> None:
        """Log signal generation event."""
        ...

    def log_signal_rejected(
        self,
        strategy_name: str,
        signal: Signal,
        reason: str,
    ) -> None:
        """Log signal rejection event."""
        ...

    def log_signal_executed(
        self,
        strategy_name: str,
        signal: Signal,
        execution_price: Optional[Decimal] = None,
    ) -> None:
        """Log signal execution event."""
        ...

    def log_strategy_error(
        self,
        strategy_name: str,
        error: str,
        error_type: Optional[str] = None,
    ) -> None:
        """Log strategy error event."""
        ...

    def log_execution_error(
        self,
        strategy_name: str,
        signal: Signal,
        error: str,
    ) -> None:
        """Log signal execution error event."""
        ...
