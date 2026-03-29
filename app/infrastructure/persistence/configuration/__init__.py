"""
Configuration Persistence Services - T11.1

Database layer for saving/loading configurations, results, and decisions.

Provides two complementary services:
- ConfigurationRepository: Type-based storage for various artifact types
- ConfigurationPersistence: Comprehensive strategy configuration storage with versioning
"""

from app.infrastructure.persistence.configuration.configuration_persistence import (
    ConfigurationPersistence,
    get_configuration_persistence,
)
from app.infrastructure.persistence.configuration.configuration_repository import (
    ConfigurationRepository,
    StoredConfiguration,
)
from app.infrastructure.persistence.configuration.models import (
    ConfigurationListResponse,
    ConfigurationLoadRequest,
    ConfigurationLoadResponse,
    ConfigurationSaveRequest,
    StrategyConfiguration,
    VersionedConfiguration,
)

# Repository (type-based)
__all__ = [
    "ConfigurationListResponse",
    "ConfigurationLoadRequest",
    "ConfigurationLoadResponse",
    # Persistence (strategy-centric)
    "ConfigurationPersistence",
    "ConfigurationRepository",
    "ConfigurationSaveRequest",
    "StoredConfiguration",
    # Models
    "StrategyConfiguration",
    "VersionedConfiguration",
    "get_configuration_persistence",
]
