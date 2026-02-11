"""
FX Carry Trade Strategy Configuration

This module contains all configuration parameters for the FX carry trade strategy.
Centralized from fx_carry_trade/fx_carry_trade_strategy.py hardcoded values.
"""

from pydantic import BaseModel, Field


class FXCarryTradeStrategyConfig(BaseModel):
    """Configuration parameters for FX Carry Trade Strategy."""

    # Position sizing thresholds
    min_carry_threshold: float = Field(
        default=0.01, ge=0.001, le=0.10, description="Minimum carry threshold for signals (1%)"
    )
    max_positions_default: int = Field(
        default=10, ge=1, le=50, description="Default maximum number of positions (10)"
    )
    position_size_default: float = Field(
        default=0.1, ge=0.01, le=0.5, description="Default position size (10%)"
    )
    stop_loss_default: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Default stop loss percentage (5%)"
    )
    take_profit_default: float = Field(
        default=0.15, ge=0.05, le=0.50, description="Default take profit percentage (15%)"
    )
    max_leverage: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Maximum leverage for carry trades (2x)"
    )
    min_liquidity: float = Field(
        default=1_000_000.0, ge=100_000.0, le=100_000_000.0, description="Minimum liquidity requirement ($1M)"
    )

    # Volatility calculations
    baseline_volatility: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Baseline volatility for position sizing (1%)"
    )
    vol_adjustment_max: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Maximum volatility adjustment multiplier (2x)"
    )
    min_volatility: float = Field(
        default=0.02, ge=0.005, le=0.10, description="Minimum volatility floor (2%)"
    )
    max_volatility: float = Field(
        default=0.50, ge=0.10, le=1.0, description="Maximum volatility cap (50%)"
    )

    # Confidence calculation
    base_confidence_multiplier: float = Field(
        default=100.0, ge=50.0, le=200.0, description="Multiplier for base confidence (100x)"
    )
    carry_boost_max: float = Field(
        default=20.0, ge=5.0, le=50.0, description="Maximum carry boost for confidence (20%)"
    )
    carry_boost_multiplier: float = Field(
        default=500.0, ge=100.0, le=1000.0, description="Carry boost multiplier (500x)"
    )
