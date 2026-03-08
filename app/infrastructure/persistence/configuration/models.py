"""
Configuration Persistence Models - T11.1

Data models for configuration storage and retrieval.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyConfiguration(BaseModel):
    """Strategy configuration with parameters."""

    strategy_name: str
    parameters: Dict[str, Any]
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VersionedConfiguration(BaseModel):
    """Versioned configuration entry."""

    config_id: str
    version: int
    strategy_name: str
    parameters: Dict[str, Any]
    created_at: datetime
    is_active: bool = True


class ConfigurationSaveRequest(BaseModel):
    """Request to save a configuration."""

    strategy_name: str
    parameters: Dict[str, Any]
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConfigurationLoadRequest(BaseModel):
    """Request to load a configuration."""

    strategy_name: str
    version: Optional[str] = None


class ConfigurationLoadResponse(BaseModel):
    """Response from loading a configuration."""

    success: bool
    configuration: Optional[StrategyConfiguration] = None
    message: Optional[str] = None


class ConfigurationListResponse(BaseModel):
    """Response from listing configurations."""

    configurations: List[StrategyConfiguration]
    total_count: int
