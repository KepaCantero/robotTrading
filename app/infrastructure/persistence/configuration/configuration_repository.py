"""
Configuration Repository - T11.1

Type-based storage for various artifact types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class StoredConfiguration:
    """Stored configuration entry."""

    config_id: str
    config_type: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigurationRepository:
    """
    Type-based configuration repository.

    Provides storage for various configuration types:
    - Strategy configurations
    - Backtest results
    - Deployment decisions
    """

    def __init__(self):
        self._store: Dict[str, StoredConfiguration] = {}

    def save(
        self, config_type: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
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
        return config_id

    def load(self, config_id: str) -> Optional[StoredConfiguration]:
        """Load a configuration by ID."""
        return self._store.get(config_id)

    def list_by_type(self, config_type: str) -> List[StoredConfiguration]:
        """List all configurations of a specific type."""
        return [c for c in self._store.values() if c.config_type == config_type]

    def delete(self, config_id: str) -> bool:
        """Delete a configuration by ID."""
        if config_id in self._store:
            del self._store[config_id]
            return True
        return False

    def update(self, config_id: str, data: Dict[str, Any]) -> Optional[StoredConfiguration]:
        """Update a configuration's data."""
        if config_id not in self._store:
            return None

        config = self._store[config_id]
        config.data = data
        config.updated_at = datetime.utcnow()
        return config
