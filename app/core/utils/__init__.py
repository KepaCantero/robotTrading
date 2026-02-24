"""
Core utilities for the algoTrading application.

This package provides common utilities used across the application.
DEPRECATED: Import directly from app.shared.utils instead.
"""

# Re-export from shared/utils for backward compatibility
from app.shared.utils.subsystem_config_factory import (
    SubsystemConfigFactory,
    get_subsystem_config_factory,
)

__all__ = [
    "SubsystemConfigFactory",
    "get_subsystem_config_factory",
]
