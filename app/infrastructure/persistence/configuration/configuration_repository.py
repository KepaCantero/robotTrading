"""
Configuration Repository - T11.1

Type-based storage for various artifact types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class StoredConfiguration:
    """Stored configuration entry."""

    config_id: str
    config_type: str
    data: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigurationRepository:
    """
    Type-based configuration repository.

    Provides storage for various configuration types:
    - Strategy configurations
    - Backtest results
    - Deployment decisions
    """

    def __init__(self):
        self._store: dict[str, StoredConfiguration] = {}
        logger.debug(
            "ConfigurationRepository initialized",
            extra={"component": "ConfigurationRepository", "store_size": 0},
        )

    def save(
        self, config_type: str, data: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> str:
        """Save a configuration and return its ID."""
        config_id = f"config_{uuid4().hex[:8]}"

        config = StoredConfiguration(
            config_id=config_id,
            config_type=config_type,
            data=data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        self._store[config_id] = config
        logger.info(
            "Configuration saved",
            extra={
                "component": "ConfigurationRepository",
                "config_id": config_id,
                "config_type": config_type,
                "store_size": len(self._store),
                "has_metadata": bool(metadata),
            },
        )
        return config_id

    def load(self, config_id: str) -> StoredConfiguration | None:
        """Load a configuration by ID."""
        config = self._store.get(config_id)
        logger.debug(
            "Configuration loaded",
            extra={
                "component": "ConfigurationRepository",
                "config_id": config_id,
                "found": config is not None,
            },
        )
        return config

    def list_by_type(self, config_type: str) -> list[StoredConfiguration]:
        """List all configurations of a specific type."""
        configs = [c for c in self._store.values() if c.config_type == config_type]
        logger.debug(
            "Configurations listed by type",
            extra={
                "component": "ConfigurationRepository",
                "config_type": config_type,
                "count": len(configs),
            },
        )
        return configs

    def delete(self, config_id: str) -> bool:
        """Delete a configuration by ID."""
        if config_id in self._store:
            del self._store[config_id]
            logger.info(
                "Configuration deleted",
                extra={
                    "component": "ConfigurationRepository",
                    "config_id": config_id,
                    "store_size": len(self._store),
                },
            )
            return True
        logger.warning(
            "Configuration not found for deletion",
            extra={
                "component": "ConfigurationRepository",
                "config_id": config_id,
            },
        )
        return False

    def update(self, config_id: str, data: dict[str, Any]) -> StoredConfiguration | None:
        """Update a configuration's data."""
        if config_id not in self._store:
            logger.warning(
                "Configuration not found for update",
                extra={
                    "component": "ConfigurationRepository",
                    "config_id": config_id,
                },
            )
            return None

        config = self._store[config_id]
        config.data = data
        config.updated_at = datetime.utcnow()
        logger.info(
            "Configuration updated",
            extra={
                "component": "ConfigurationRepository",
                "config_id": config_id,
                "config_type": config.config_type,
            },
        )
        return config
