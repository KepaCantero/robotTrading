"""
Response DTOs for Presentation Layer
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class PortfolioResponse(BaseModel):
    """Portfolio response."""

    portfolio_id: str = Field(..., description="Portfolio ID")
    total_value: Decimal = Field(..., description="Total portfolio value")
    currency: str = Field(..., description="Currency code")
    positions: list[dict] = Field(default_factory=list, description="Portfolio positions")


class StrategyResponse(BaseModel):
    """Strategy response."""

    strategy_id: str = Field(..., description="Strategy ID")
    strategy_type: str = Field(..., description="Strategy type")
    status: str = Field(..., description="Execution status")
    signals: list[dict] = Field(default_factory=list, description="Trading signals")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="System status")
    version: str = Field(default="1.0.0", description="API version")
