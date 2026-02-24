"""
Base Configuration Module

Contains base classes, enums, and common utilities for the configuration system.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigBase(BaseModel):
    """Base class for all configuration models."""

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        arbitrary_types_allowed = True
        use_enum_values = True


class SettingsBase(BaseSettings):
    """Base class for settings that load from environment variables."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields from .env not defined in model
    }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "fields": list(self.model_fields.keys()),
            "json": self.model_dump(mode="json"),
        }
