"""
Configuration Protocols

Defines Protocol interfaces for configuration providers following OCP.
Allows dependency injection and makes configuration system extensible.

TASK-24: OCP Compliance - Protocol interfaces for configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: object | None = None) -> object | None:
        """Get configuration value by key."""
        ...

    def set(self, key: str, value: object) -> None:
        """Set configuration value."""
        ...

    def validate(self) -> bool:
        """Validate configuration."""
        ...


@runtime_checkable
class FileConfigLoader(Protocol):
    """Protocol for configuration file loaders."""

    def load(self, config_path: Path) -> dict[str, object]:
        """Load configuration from file."""
        ...

    def supports(self, file_extension: str) -> bool:
        """Check if loader supports given file extension."""
        ...


@runtime_checkable
class ConfigValidator(Protocol):
    """Protocol for configuration validators."""

    def validate(self, config: dict[str, object]) -> bool:
        """Validate configuration dictionary."""
        ...

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        ...


@runtime_checkable
class ConfigMerger(Protocol):
    """Protocol for configuration mergers."""

    def merge(self, base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
        """Merge two configurations."""
        ...


@runtime_checkable
class ConfigCache(Protocol):
    """Protocol for configuration caching."""

    def get_cached(self, config_path: Path) -> dict[str, object] | None:
        """Get cached configuration if available and valid."""
        ...

    def set_cached(self, config_path: Path, config: dict[str, object]) -> None:
        """Cache configuration."""
        ...

    def invalidate(self, config_path: Path) -> None:
        """Invalidate cached configuration."""
        ...
