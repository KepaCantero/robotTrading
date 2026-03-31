"""
Protocols for Strategy Registry and Logger - Dependency Inversion.

These Protocols enable SOL-005 (Dependency Inversion Principle) and DP-004
(Dependency Injection) by allowing ExecutionEngine to depend on abstractions
rather than concrete classes. This improves testability and maintainability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from decimal import Decimal

    from app.domain.models.signal import Signal
    from app.domain.strategies.strategy_registry import BaseStrategy


class StrategyRegistryProto(Protocol):
    """Protocol for strategy registry - allows mocking in tests."""

    @property
    def active_strategy(self) -> str | None:
        """Name of active strategy."""
        ...

    def get_active_strategy(self) -> BaseStrategy | None:
        """Get currently active strategy."""
        ...

    def get_all_strategies_status(self) -> dict[str, object]:
        """Get status summary for all strategies."""
        ...

    def list_available_strategies(self) -> list[str]:
        """List names of all available (registered) strategies."""
        ...

    def list_loaded_strategies(self) -> list[str]:
        """List names of all loaded (instantiated) strategies."""
        ...

    def load_strategy(self, name: str, config: dict[str, object]) -> BaseStrategy:
        """Load (create) a strategy instance by name with config."""
        ...

    def set_active_strategy(self, name: str) -> None:
        """Set the currently active strategy by name."""
        ...

    def unload_strategy(self, name: str) -> None:
        """Unload (remove) a loaded strategy."""
        ...

    def get_strategy_status(self, name: str) -> dict[str, object]:
        """Get status information for a specific strategy."""
        ...

    def get_strategy(self, name: str) -> BaseStrategy | None:
        """Get a strategy instance by name."""
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
        execution_price: Decimal | None = None,
    ) -> None:
        """Log signal execution event."""
        ...

    def log_strategy_error(
        self,
        strategy_name: str,
        error: str,
        error_type: str | None = None,
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

    def log_strategy_loaded(
        self,
        strategy_name: str,
        config: dict[str, object],
    ) -> None:
        """Log strategy loaded event."""
        ...

    def log_strategy_unloaded(self, strategy_name: str) -> None:
        """Log strategy unloaded event."""
        ...

    def log_strategy_activated(self, strategy_name: str) -> None:
        """Log strategy activated event."""
        ...

    def log_strategy_deactivated(self, strategy_name: str) -> None:
        """Log strategy deactivated event."""
        ...

    def get_strategy_metrics(self, strategy_name: str) -> dict[str, object]:
        """Get metrics for a specific strategy."""
        ...

    def get_all_metrics(self) -> dict[str, object]:
        """Get metrics for all strategies."""
        ...
