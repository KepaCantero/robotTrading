"""
T11.1: ConfigurationPersistence - Save/load configurations, results, decisions

Database layer for persisting:
- Investment profiles and input configurations
- Backtest results with feasibility metrics
- Validation reports from PHASE 0 gates
- Deployment decisions and recommendations
- Module parameters for reproducibility
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StoredConfiguration:
    """Model for stored configuration."""

    config_id: str
    config_type: str  # backtest_config, investment_profile, deployment_decision
    created_at: str
    updated_at: str
    data: dict
    metadata: dict


class ConfigurationRepository:
    """
    T11.1: Repository for saving/loading configurations.

    Uses in-memory store for MVP; can be extended with SQLAlchemy.
    """

    def __init__(self):
        """Initialize repository with in-memory storage."""
        self.logger = logging.getLogger(__name__)
        self._storage: dict[str, StoredConfiguration] = {}
        self.logger.info("✅ ConfigurationRepository initialized")

    async def save_investment_profile(
        self,
        profile_id: str,
        profile_data: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """Save investment profile."""
        return await self._save_config(
            config_id=profile_id,
            config_type="investment_profile",
            data=profile_data,
            metadata=metadata or {},
        )

    async def save_backtest_config(
        self,
        config_id: str,
        config_data: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """Save backtest configuration."""
        return await self._save_config(
            config_id=config_id,
            config_type="backtest_config",
            data=config_data,
            metadata=metadata or {},
        )

    async def save_backtest_result(
        self,
        result_id: str,
        result_data: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """Save backtest result with feasibility metrics."""
        return await self._save_config(
            config_id=result_id,
            config_type="backtest_result",
            data=result_data,
            metadata=metadata or {},
        )

    async def save_validation_report(
        self,
        report_id: str,
        report_data: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """Save validation report from T5.1."""
        return await self._save_config(
            config_id=report_id,
            config_type="validation_report",
            data=report_data,
            metadata=metadata or {},
        )

    async def save_deployment_decision(
        self,
        decision_id: str,
        decision_data: dict,
        metadata: Optional[dict] = None,
    ) -> str:
        """Save deployment decision from T10.1."""
        return await self._save_config(
            config_id=decision_id,
            config_type="deployment_decision",
            data=decision_data,
            metadata=metadata or {},
        )

    async def load_configuration(self, config_id: str) -> Optional[StoredConfiguration]:
        """Load configuration by ID."""
        try:
            if config_id in self._storage:
                self.logger.info(f"📂 Loaded configuration {config_id}")
                return self._storage[config_id]
            else:
                self.logger.warning(f"⚠️  Configuration {config_id} not found")
                return None
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"❌ Error loading configuration: {e}")
            raise ValueError(f"Failed to load configuration: {e}") from e

    async def load_by_type(self, config_type: str) -> list[StoredConfiguration]:
        """Load all configurations of a specific type."""
        try:
            results = [
                config for config in self._storage.values() if config.config_type == config_type
            ]
            self.logger.info(f"📂 Loaded {len(results)} configurations of type {config_type}")
            return results
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"❌ Error loading configurations: {e}")
            raise ValueError(f"Failed to load configurations: {e}") from e

    async def list_all(self) -> list[StoredConfiguration]:
        """List all stored configurations."""
        return list(self._storage.values())

    async def delete_configuration(self, config_id: str) -> bool:
        """Delete configuration by ID."""
        try:
            if config_id in self._storage:
                del self._storage[config_id]
                self.logger.info(f"🗑️  Deleted configuration {config_id}")
                return True
            else:
                self.logger.warning(f"⚠️  Configuration {config_id} not found for deletion")
                return False
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"❌ Error deleting configuration: {e}")
            raise ValueError(f"Failed to delete configuration: {e}") from e

    async def _save_config(
        self,
        config_id: str,
        config_type: str,
        data: dict,
        metadata: dict,
    ) -> str:
        """Internal method to save configuration."""
        try:
            timestamp = datetime.now().isoformat()

            # Create stored configuration
            stored = StoredConfiguration(
                config_id=config_id,
                config_type=config_type,
                created_at=(
                    timestamp
                    if config_id not in self._storage
                    else self._storage[config_id].created_at
                ),
                updated_at=timestamp,
                data=data,
                metadata=metadata,
            )

            # Save to in-memory storage
            self._storage[config_id] = stored

            self.logger.info(f"💾 Saved {config_type} with ID {config_id}")
            return config_id

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"❌ Error saving configuration: {e}")
            raise ValueError(f"Failed to save configuration: {e}") from e

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        config_types = {}
        for config in self._storage.values():
            config_types[config.config_type] = config_types.get(config.config_type, 0) + 1

        return {
            "total_configs": len(self._storage),
            "by_type": config_types,
            "config_ids": list(self._storage.keys()),
        }
