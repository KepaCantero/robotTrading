"""
Request DTOs for Presentation Layer
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from decimal import Decimal


class CreatePortfolioRequest(BaseModel):
    """Request to create a portfolio."""

    portfolio_id: str = Field(..., description="Portfolio ID")
    initial_capital: Decimal = Field(..., gt=0, description="Initial capital")
    currency: str = Field(default="USD", description="Currency code")


class ExecuteStrategyRequest(BaseModel):
    """Request to execute a strategy."""

    strategy_type: str = Field(..., description="Strategy type")
    symbol: str = Field(..., description="Trading symbol")
    parameters: dict = Field(default_factory=dict, description="Strategy parameters")
