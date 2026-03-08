"""
Configuration Persistence - T11.1

Comprehensive strategy configuration storage with versioning.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app.infrastructure.persistence.configuration.models import (
    ConfigurationListResponse,
    ConfigurationLoadRequest,
    ConfigurationLoadResponse,
    ConfigurationSaveRequest,
    StrategyConfiguration,
    VersionedConfiguration,
)


class ConfigurationPersistence:
    """
    Comprehensive configuration persistence service.

    Provides versioned storage for strategy configurations with:
    - Save/load operations
    - Version management
    - Configuration listing
    """

    def __init__(self):
        self._configurations: Dict[str, StrategyConfiguration] = {}
        self._versioned: Dict[str, List[VersionedConfiguration]] = {}

    def save_configuration(self, request: ConfigurationSaveRequest) -> StrategyConfiguration:
        """Save a strategy configuration."""
        config_id = f"config_{uuid4().hex[:8]}"

        config = StrategyConfiguration(
            strategy_name=request.strategy_name,
            parameters=request.parameters,
            version=request.version or "1.0",
            created_at=datetime.utcnow(),
            metadata=request.metadata or {},
        )

        self._configurations[config_id] = config
        return config

    def load_configuration(self, request: ConfigurationLoadRequest) -> ConfigurationLoadResponse:
        """Load a strategy configuration."""
        # Find configuration by strategy name
        for config in self._configurations.values():
            if config.strategy_name == request.strategy_name:
                if request.version is None or config.version == request.version:
                    return ConfigurationLoadResponse(
                        success=True,
                        configuration=config,
                        message="Configuration loaded successfully",
                    )

        return ConfigurationLoadResponse(
            success=False,
            configuration=None,
            message=f"Configuration not found for strategy: {request.strategy_name}",
        )

    def list_configurations(self, strategy_name: Optional[str] = None) -> ConfigurationListResponse:
        """List all configurations, optionally filtered by strategy."""
        configs = list(self._configurations.values())

        if strategy_name:
            configs = [c for c in configs if c.strategy_name == strategy_name]

        return ConfigurationListResponse(
            configurations=configs,
            total_count=len(configs),
        )

    def delete_configuration(self, strategy_name: str) -> bool:
        """Delete a configuration by strategy name."""
        to_delete = [
            config_id
            for config_id, config in self._configurations.items()
            if config.strategy_name == strategy_name
        ]

        for config_id in to_delete:
            del self._configurations[config_id]

        return len(to_delete) > 0


# Singleton instance
_configuration_persistence: Optional[ConfigurationPersistence] = None


def get_configuration_persistence() -> ConfigurationPersistence:
    """Get the singleton ConfigurationPersistence instance."""
    global _configuration_persistence
    if _configuration_persistence is None:
        _configuration_persistence = ConfigurationPersistence()
    return _configuration_persistence
