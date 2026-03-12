"""
Signal and Risk Configuration Module

Contains configuration for signal thresholds, risk management,
circuit breakers, and related parameters.
"""

import logging
from decimal import Decimal
from typing import Dict

logger = logging.getLogger(__name__)

from pydantic import Field, field_validator

from app.shared.config.base import ConfigBase


class SignalThresholds(ConfigBase):
    """Configuration for signal-related thresholds."""

    # Signal strength and confidence
    min_signal_strength: float = Field(default=60.0, description="Minimum signal strength (0-100)")
    min_signal_confidence: float = Field(
        default=70.0, description="Minimum signal confidence (0-100)"
    )
    min_liquidity_score: float = Field(default=50.0, description="Minimum liquidity score (0-100)")

    # Additional thresholds for momentum analysis
    min_strength: float = Field(
        default=60.0, description="Minimum strength threshold for momentum analysis"
    )

    # Signal Scoring Engine (TASK-SC-1 to SC-5)
    signal_cooldown_minutes: int = Field(
        default=10, description="Signal cooldown period in minutes"
    )
    signal_compound_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "confidence": 0.30,
            "volume_ratio": 0.25,
            "volatility": 0.20,
            "liquidity": 0.15,
            "timing": 0.10,
        },
        description="Weights for compound signal scoring",
    )
    signal_high_priority_threshold: float = Field(
        default=80.0, description="High priority threshold (0-100)"
    )
    signal_medium_priority_threshold: float = Field(
        default=50.0, description="Medium priority threshold (0-100)"
    )

    @field_validator(
        "min_signal_strength", "min_signal_confidence", "min_liquidity_score", "min_strength"
    )
    @classmethod
    def validate_0_100_range(cls, v):
        if not 0 <= v <= 100:
            logger.warning(
                "Signal threshold validation failed",
                extra={"value": v, "valid_range": "0-100"},
            )
            raise ValueError("Value must be between 0 and 100")
        logger.debug(
            "Signal threshold validated",
            extra={"value": v},
        )
        return v


class RiskManagementThresholds(ConfigBase):
    """Configuration for risk management parameters."""

    # Position-level risk
    stop_loss_pct: float = Field(default=0.05, description="Stop loss percentage (0-1)")
    take_profit_pct: float = Field(default=0.15, description="Take profit percentage (0-1)")
    max_risk_per_trade: float = Field(default=0.02, description="Maximum risk per trade (0-1)")
    min_risk_reward_ratio: float = Field(default=3.0, description="Minimum risk/reward ratio")

    # Portfolio-level risk
    daily_loss_limit: float = Field(default=0.05, description="Daily loss limit (0-1)")
    max_drawdown_limit: float = Field(default=0.15, description="Maximum drawdown limit (0-1)")
    max_total_exposure: float = Field(default=0.8, description="Maximum total exposure (0-1)")
    max_sector_exposure: float = Field(default=0.3, description="Maximum sector exposure (0-1)")
    max_correlation: float = Field(default=0.7, description="Maximum correlation between positions")

    # Strategy-specific exposure limits
    max_momentum_exposure: float = Field(default=0.50, description="Max momentum exposure (0-1)")
    max_mean_reversion_exposure: float = Field(
        default=0.30, description="Max mean reversion exposure (0-1)"
    )
    max_pairs_trading_exposure: float = Field(
        default=0.30, description="Max pairs trading exposure (0-1)"
    )

    # Trading controls
    max_consecutive_stops: int = Field(default=5, description="Max consecutive stops before pause")

    # Capital adjustment
    capital_adjustment_factor: float = Field(
        default=0.20, description="Capital adjustment factor per negative streak (0-1)"
    )

    @field_validator("stop_loss_pct")
    @classmethod
    def validate_stop_loss(cls, v):
        if not 0 <= v <= 0.5:
            logger.warning(
                "Stop loss validation failed",
                extra={"value": v, "valid_range": "0-0.5"},
            )
            raise ValueError("Stop loss percentage must be between 0 and 0.5")
        logger.debug(
            "Stop loss validated",
            extra={"value": v},
        )
        return v

    @field_validator(
        "take_profit_pct",
        "max_risk_per_trade",
        "daily_loss_limit",
        "max_drawdown_limit",
        "max_total_exposure",
        "max_sector_exposure",
        "max_correlation",
        "max_momentum_exposure",
        "max_mean_reversion_exposure",
        "max_pairs_trading_exposure",
        "capital_adjustment_factor",
    )
    @classmethod
    def validate_percentage_0_1(cls, v):
        if not 0 <= v <= 1:
            logger.warning(
                "Risk management threshold validation failed",
                extra={"value": v, "valid_range": "0-1"},
            )
            raise ValueError("Percentage values must be between 0 and 1")
        logger.debug(
            "Risk management threshold validated",
            extra={"value": v},
        )
        return v


class CircuitBreakerThresholds(ConfigBase):
    """Configuration for circuit breaker parameters."""

    circuit_breaker_daily_loss: float = Field(
        default=0.05, description="Circuit breaker daily loss threshold (Chan #15: 5%)"
    )
    circuit_breaker_drawdown: float = Field(
        default=0.1, description="Circuit breaker drawdown threshold"
    )
    circuit_breaker_volatility: float = Field(
        default=0.05, description="Circuit breaker volatility threshold"
    )
    circuit_breaker_error_rate: float = Field(
        default=0.05, description="Circuit breaker error rate threshold"
    )

    @field_validator(
        "circuit_breaker_daily_loss",
        "circuit_breaker_drawdown",
        "circuit_breaker_volatility",
        "circuit_breaker_error_rate",
    )
    @classmethod
    def validate_percentage_0_1(cls, v):
        if not 0 <= v <= 1:
            logger.warning(
                "Circuit breaker threshold validation failed",
                extra={"value": v, "valid_range": "0-1"},
            )
            raise ValueError("Percentage values must be between 0 and 1")
        logger.debug(
            "Circuit breaker threshold validated",
            extra={"value": v},
        )
        return v


class SlippageThresholds(ConfigBase):
    """Configuration for slippage analysis parameters."""

    volatility_threshold_high: Decimal = Field(
        default=Decimal("30.0"), description="High volatility threshold (%)"
    )
    volatility_threshold_extreme: Decimal = Field(
        default=Decimal("50.0"), description="Extreme volatility threshold (%)"
    )
    max_spread_threshold: Decimal = Field(
        default=Decimal("2.0"), description="Maximum spread threshold (%)"
    )
    base_slippage: Decimal = Field(default=Decimal("0.1"), description="Base slippage rate (%)")

    @field_validator(
        "volatility_threshold_high",
        "volatility_threshold_extreme",
        "max_spread_threshold",
        "base_slippage",
    )
    @classmethod
    def validate_decimal_percentage(cls, v):
        if not Decimal("0") <= v <= Decimal("100"):
            logger.warning(
                "Slippage threshold validation failed",
                extra={"value": str(v), "valid_range": "0-100"},
            )
            raise ValueError("Percentage values must be between 0 and 100")
        logger.debug(
            "Slippage threshold validated",
            extra={"value": str(v)},
        )
        return v


class TradingCostThresholds(ConfigBase):
    """Configuration for trading cost estimation in profitability validation."""

    # Commission rates (as decimals, e.g., 0.001 = 0.1%)
    commission_rate: Decimal = Field(
        default=Decimal("0.001"),
        ge=Decimal("0"),
        le=Decimal("0.1"),
        description="Commission rate as decimal (0.001 = 0.1%)",
    )

    # Slippage rates (as decimals, e.g., 0.0005 = 0.05%)
    slippage_rate: Decimal = Field(
        default=Decimal("0.0005"),
        ge=Decimal("0"),
        le=Decimal("0.01"),
        description="Expected slippage rate as decimal (0.0005 = 0.05%)",
    )

    # Market impact rates (as decimals, e.g., 0.0002 = 0.02%)
    market_impact_rate: Decimal = Field(
        default=Decimal("0.0002"),
        ge=Decimal("0"),
        le=Decimal("0.01"),
        description="Expected market impact rate as decimal (0.0002 = 0.02%)",
    )

    # Fixed costs per trade (in USD)
    infrastructure_cost_per_trade: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("0"),
        description="Fixed infrastructure cost per trade in USD",
    )

    data_fee_per_trade: Decimal = Field(
        default=Decimal("0.5"), ge=Decimal("0"), description="Fixed data fee per trade in USD"
    )

    # Trade value estimation multiplier
    trade_value_multiplier: Decimal = Field(
        default=Decimal("10"),
        ge=Decimal("1"),
        description="Multiplier to estimate trade value from PnL",
    )

    # Assumptions for calculations
    assumed_base_capital: Decimal = Field(
        default=Decimal("1000"),
        ge=Decimal("100"),
        description="Assumed base capital for return calculations",
    )


class PerformanceThresholds(ConfigBase):
    """Configuration for performance and latency thresholds."""

    max_latency_ms: int = Field(
        default=1000, description="Maximum acceptable latency in milliseconds"
    )
    max_execution_time_ms: int = Field(
        default=500, description="Maximum execution time in milliseconds"
    )


class MarketMicrostructureThresholds(ConfigBase):
    """Configuration for market microstructure and liquidity analysis."""

    # Default volatility for fallback calculations
    default_volatility: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Default volatility assumption when historical data unavailable",
    )

    # Liquidity score thresholds
    liquidity_high_threshold: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Liquidity score threshold for HIGH regime"
    )
    liquidity_normal_threshold: float = Field(
        default=60.0, ge=0.0, le=100.0, description="Liquidity score threshold for NORMAL regime"
    )
    liquidity_low_threshold: float = Field(
        default=40.0, ge=0.0, le=100.0, description="Liquidity score threshold for LOW regime"
    )

    # Market impact thresholds
    high_market_impact_bps: float = Field(
        default=50.0, ge=0.0, description="Market impact threshold (in bps) for high impact alert"
    )
    wide_spread_bps: float = Field(
        default=10.0, ge=0.0, description="Spread threshold (in bps) for wide spread alert"
    )
