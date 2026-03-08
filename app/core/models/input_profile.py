"""
Input Profile Model

Defines the input profile for investment strategy configuration.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field, validator


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

    @validator("capital_must_be_positive")
    def validate_capital(cls, v: Decimal) -> bool:
        if v <= 0:
            raise ValueError("Capital must be positive")
        return v

    @validator("horizon_must_be_valid")
    def validate_horizon(cls, v: int) -> bool:
        if v < 1 or v > 600:
            raise ValueError("Investment horizon must be between 1 and 600 months")
        return v
