"""
Input Profile Model

Defines the input profile for investment strategy configuration.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ObjectivoInversion(str, Enum):
    """Investment objective enumeration."""

    MAXIMIZAR_CAPITAL = "maximizar_capital"
    MAXIMIZAR_DIVIDENDOS = "maximize_dividends"
    PRESERVAR_CAPITAL = "preserve_capital"
    BALANCED_GROWTH = "balanced_growth"


class RiskTolerance(str, Enum):
    """Risk tolerance enumeration."""

    BAJO = "low"
    MEDIO = "medium"
    ALTO = "high"


class InputProfile(BaseModel):
    """Input profile for investment configuration."""

    capital_initial: Decimal = Field(..., ge=0, description="Initial capital amount")
    objetivo_inversion: ObjectivoInversion = Field(..., description="Investment objective")
    risk_tolerance: RiskTolerance = Field(..., description="Risk tolerance level")
    investment_horizon: int = Field(..., ge=0, description="Investment horizon in months")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Optional constraints")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Profile creation timestamp"
    )

    @field_validator("capital_initial")
    @classmethod
    def validate_capital(cls, v: Decimal) -> Decimal:
        """Validate that capital is positive."""
        logger.debug("Validating capital value", extra={"capital": float(v)})
        if v <= 0:
            logger.error("Capital validation failed: must be positive", extra={"capital": float(v)})
            raise ValueError("Capital must be positive")
        logger.debug("Capital validation passed", extra={"capital": float(v)})
        return v

    @field_validator("investment_horizon")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        """Validate that investment horizon is within acceptable range."""
        logger.debug("Validating investment horizon", extra={"horizon_months": v})
        if v < 1 or v > 600:
            logger.error(
                "Horizon validation failed: must be between 1 and 600 months",
                extra={"horizon_months": v},
            )
            raise ValueError("Investment horizon must be between 1 and 600 months")
        logger.debug("Horizon validation passed", extra={"horizon_months": v})
        return v
