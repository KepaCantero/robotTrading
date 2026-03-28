"""
Configuration Persistence - T11.1

Comprehensive strategy configuration storage with versioning.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

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
        logger.debug("ConfigurationPersistence initialized")

    def save_configuration(self, request: ConfigurationSaveRequest) -> StrategyConfiguration:
        """Save a strategy configuration."""
        config_id = f"config_{uuid4().hex[:8]}"

        logger.info(
            "Saving configuration",
            extra={
                "config_id": config_id,
                "strategy_name": request.strategy_name,
                "version": request.version or "1.0",
            },
        )

        config = StrategyConfiguration(
            strategy_name=request.strategy_name,
            parameters=request.parameters,
            version=request.version or "1.0",
            created_at=datetime.utcnow(),
            metadata=request.metadata or {},
        )

        self._configurations[config_id] = config

        logger.debug(
            "Configuration saved",
            extra={
                "config_id": config_id,
                "strategy_name": request.strategy_name,
                "total_configurations": len(self._configurations),
            },
        )

        return config

    def load_configuration(self, request: ConfigurationLoadRequest) -> ConfigurationLoadResponse:
        """Load a strategy configuration."""
        logger.debug(
            "Loading configuration",
            extra={"strategy_name": request.strategy_name, "version": request.version},
        )

        # Find configuration by strategy name
        for config in self._configurations.values():
            if config.strategy_name == request.strategy_name and (request.version is None or config.version == request.version):
                logger.info(
                    "Configuration loaded successfully",
                    extra={
                        "strategy_name": request.strategy_name,
                        "version": config.version,
                    },
                )
                return ConfigurationLoadResponse(
                    success=True,
                    configuration=config,
                    message="Configuration loaded successfully",
                )

        logger.warning(
            "Configuration not found",
            extra={"strategy_name": request.strategy_name, "version": request.version},
        )

        return ConfigurationLoadResponse(
            success=False,
            configuration=None,
            message=f"Configuration not found for strategy: {request.strategy_name}",
        )

    def list_configurations(self, strategy_name: Optional[str] = None) -> ConfigurationListResponse:
        """List all configurations, optionally filtered by strategy."""
        logger.debug("Listing configurations", extra={"strategy_name_filter": strategy_name})

        configs = list(self._configurations.values())

        if strategy_name:
            configs = [c for c in configs if c.strategy_name == strategy_name]

        logger.info(
            "Configurations listed",
            extra={
                "total_count": len(configs),
                "strategy_name_filter": strategy_name,
            },
        )

        return ConfigurationListResponse(
            configurations=configs,
            total_count=len(configs),
        )

    def delete_configuration(self, strategy_name: str) -> bool:
        """Delete a configuration by strategy name."""
        logger.debug("Deleting configuration", extra={"strategy_name": strategy_name})

        to_delete = [
            config_id
            for config_id, config in self._configurations.items()
            if config.strategy_name == strategy_name
        ]

        for config_id in to_delete:
            del self._configurations[config_id]

        deleted = len(to_delete) > 0

        if deleted:
            logger.info(
                "Configuration deleted",
                extra={
                    "strategy_name": strategy_name,
                    "deleted_count": len(to_delete),
                },
            )
        else:
            logger.warning(
                "No configuration found to delete", extra={"strategy_name": strategy_name}
            )

        return deleted


# Singleton instance
_configuration_persistence: Optional[ConfigurationPersistence] = None


def get_configuration_persistence() -> ConfigurationPersistence:
    """Get the singleton ConfigurationPersistence instance."""
    global _configuration_persistence
    if _configuration_persistence is None:
        logger.debug("Creating singleton ConfigurationPersistence instance")
        _configuration_persistence = ConfigurationPersistence()
    return _configuration_persistence
