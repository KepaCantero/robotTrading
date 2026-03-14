"""
T11.1: ConfigurationPersistence - Models for configuration storage and retrieval

Persists strategy configurations to in-memory store with optional persistence.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StrategyConfiguration(BaseModel):
    """Complete strategy configuration for persistence."""

    config_id: str = Field(..., description="Unique configuration ID")
    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Strategy name")

    # Input parameters
    capital_eur: Decimal = Field(..., description="Initial capital in EUR")
    risk_profile: str = Field(..., description="Risk profile: aggressive/balanced/conservative")
    objective: str = Field(..., description="Investment objective")
    target_annual_return_pct: Decimal = Field(..., description="Target annual return %")
    max_acceptable_drawdown_pct: Decimal = Field(..., description="Max acceptable drawdown %")

    # Module configuration
    enabled_modules: List[str] = Field(..., description="List of enabled modules")
    module_parameters: Dict[str, Any] = Field(default={}, description="Module-specific parameters")

    # Backtest results
    feasibility_ratio: Optional[Decimal] = Field(None, description="Feasibility ratio")
    annual_return_pct: Optional[Decimal] = Field(None, description="Annual return %")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    max_drawdown_pct: Optional[Decimal] = Field(None, description="Max drawdown %")

    # Portfolio allocation
    portfolio_allocations: Dict[str, Decimal] = Field(default={}, description="Module allocations")

    # Validation & Recommendation
    validation_passed: Optional[bool] = Field(None, description="Validation gate status")
    recommendation_score: Optional[Decimal] = Field(None, description="Recommendation score")
    recommendation_status: Optional[str] = Field(None, description="Recommendation status")

    # Deployment decision
    deployment_status: Optional[str] = Field(
        None, description="Deployment decision: APPROVED/CONDITIONAL/REJECTED"
    )
    deployment_confidence: Optional[str] = Field(
        None, description="Decision confidence: high/medium/low"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    is_active: bool = Field(default=True, description="Whether configuration is active")
    notes: str = Field(default="", description="Optional notes about configuration")


class ConfigurationSaveRequest(BaseModel):
    """Request to save configuration."""

    config_id: str = Field(..., description="Configuration ID")
    profile_id: str = Field(..., description="Profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Strategy name")

    # Configuration data
    configuration: StrategyConfiguration = Field(..., description="Configuration to save")


class ConfigurationLoadRequest(BaseModel):
    """Request to load configuration."""

    config_id: str = Field(..., description="Configuration ID to load")


class ConfigurationLoadResponse(BaseModel):
    """Response from loading configuration."""

    success: bool = Field(default=True, description="Load success")
    config_id: str = Field(..., description="Configuration ID")
    configuration: Optional[StrategyConfiguration] = Field(None, description="Loaded configuration")
    error_message: Optional[str] = Field(None, description="Error if loading failed")


class ConfigurationListResponse(BaseModel):
    """Response with list of configurations."""

    success: bool = Field(default=True, description="Query success")
    total_count: int = Field(..., description="Total configurations stored")
    active_count: int = Field(..., description="Active configurations")
    configurations: List[StrategyConfiguration] = Field(..., description="List of configurations")
    error_message: Optional[str] = Field(None, description="Error if query failed")


class VersionedConfiguration(BaseModel):
    """Configuration with version tracking."""

    config_id: str = Field(..., description="Configuration ID")
    version: int = Field(..., description="Configuration version")
    created_at: datetime = Field(..., description="Version creation time")
    configuration: StrategyConfiguration = Field(..., description="Configuration at this version")
    change_description: str = Field(default="", description="Description of changes")


logger.debug(
    "ConfigurationPersistence models loaded",
    extra={
        "component": "configuration_persistence_models",
        "operation": "module_init",
        "models": [
            "StrategyConfiguration",
            "ConfigurationSaveRequest",
            "ConfigurationLoadRequest",
            "ConfigurationLoadResponse",
            "ConfigurationListResponse",
            "VersionedConfiguration",
        ],
    },
)
