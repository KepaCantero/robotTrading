"""
Configuration Protocols

Defines Protocol interfaces for configuration providers following OCP.
Allows dependency injection and makes configuration system extensible.

TASK-24: OCP Compliance - Protocol interfaces for configuration
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: Optional[object] = None) -> Optional[object]:
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

    def load(self, config_path: Path) -> Dict[str, object]:
        """Load configuration from file."""
        ...

    def supports(self, file_extension: str) -> bool:
        """Check if loader supports given file extension."""
        ...


@runtime_checkable
class ConfigValidator(Protocol):
    """Protocol for configuration validators."""

    def validate(self, config: Dict[str, object]) -> bool:
        """Validate configuration dictionary."""
        ...

    def get_errors(self) -> List[str]:
        """Get validation errors."""
        ...


@runtime_checkable
class ConfigMerger(Protocol):
    """Protocol for configuration mergers."""

    def merge(self, base: Dict[str, object], override: Dict[str, object]) -> Dict[str, object]:
        """Merge two configurations."""
        ...


@runtime_checkable
class ConfigCache(Protocol):
    """Protocol for configuration caching."""

    def get_cached(self, config_path: Path) -> Optional[Dict[str, object]]:
        """Get cached configuration if available and valid."""
        ...

    def set_cached(self, config_path: Path, config: Dict[str, object]) -> None:
        """Cache configuration."""
        ...

    def invalidate(self, config_path: Path) -> None:
        """Invalidate cached configuration."""
        ...
