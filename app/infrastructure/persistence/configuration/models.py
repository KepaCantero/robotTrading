"""
Configuration Persistence Models - T11.1

Data models for configuration storage and retrieval.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StrategyConfiguration(BaseModel):
    """Strategy configuration with parameters."""

    strategy_name: str
    parameters: dict[str, Any]
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VersionedConfiguration(BaseModel):
    """Versioned configuration entry."""

    config_id: str
    version: int
    strategy_name: str
    parameters: dict[str, Any]
    created_at: datetime
    is_active: bool = True


class ConfigurationSaveRequest(BaseModel):
    """Request to save a configuration."""

    strategy_name: str
    parameters: dict[str, Any]
    version: str | None = None
    metadata: dict[str, Any] | None = None


class ConfigurationLoadRequest(BaseModel):
    """Request to load a configuration."""

    strategy_name: str
    version: str | None = None


class ConfigurationLoadResponse(BaseModel):
    """Response from loading a configuration."""

    success: bool
    configuration: StrategyConfiguration | None = None
    message: str | None = None


class ConfigurationListResponse(BaseModel):
    """Response from listing configurations."""

    configurations: list[StrategyConfiguration]
    total_count: int
