"""
Configuration Persistence Services - T11.1

Database layer for saving/loading configurations, results, and decisions.

Provides two complementary services:
- ConfigurationRepository: Type-based storage for various artifact types
- ConfigurationPersistence: Comprehensive strategy configuration storage with versioning
"""

from app.services.configuration_persistence.configuration_repository import (
    ConfigurationRepository,
    StoredConfiguration,
)
from app.services.configuration_persistence.configuration_persistence import (
    ConfigurationPersistence,
    get_configuration_persistence,
)
from app.services.configuration_persistence.models import (
    StrategyConfiguration,
    ConfigurationSaveRequest,
    ConfigurationLoadRequest,
    ConfigurationLoadResponse,
    ConfigurationListResponse,
    VersionedConfiguration,
)

__all__ = [
    # Repository (type-based)
    "ConfigurationRepository",
    "StoredConfiguration",
    # Persistence (strategy-centric)
    "ConfigurationPersistence",
    "get_configuration_persistence",
    # Models
    "StrategyConfiguration",
    "ConfigurationSaveRequest",
    "ConfigurationLoadRequest",
    "ConfigurationLoadResponse",
    "ConfigurationListResponse",
    "VersionedConfiguration",
]
