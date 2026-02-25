"""
Trading Thresholds Configuration

Extracted from centralized_config.py for SRP compliance.
Contains all trading-related thresholds and parameters.

TASK-10: Centralización de Configuración
TASK-24: SRP Refactoring
"""

import logging
from decimal import Decimal
from typing import Dict

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class TradingThresholds(BaseModel):
    """Centralized trading thresholds."""

    # Signal thresholds
    min_signal_strength: float = Field(default=60.0, description="Minimum signal strength (0-100)")
    min_signal_confidence: float = Field(
        default=70.0, description="Minimum signal confidence (0-100)"
    )
    min_liquidity_score: float = Field(default=50.0, description="Minimum liquidity score (0-100)")

    # Technical indicators
    rsi_oversold: float = Field(default=30.0, description="RSI oversold threshold")
    rsi_overbought: float = Field(default=70.0, description="RSI overbought threshold")

    # Position sizing
    max_position_size: float = Field(default=0.1, description="Maximum position size (0-1)")
    min_position_size: float = Field(default=0.01, description="Minimum position size (0-1)")

    # Risk management
    stop_loss_pct: float = Field(default=0.05, description="Stop loss percentage (0-1)")
    take_profit_pct: float = Field(default=0.15, description="Take profit percentage (0-1)")
    daily_loss_limit: float = Field(default=0.05, description="Daily loss limit (0-1)")
    max_drawdown_limit: float = Field(default=0.15, description="Maximum drawdown limit (0-1)")

    # Portfolio limits
    max_total_exposure: float = Field(default=0.8, description="Maximum total exposure (0-1)")
    max_sector_exposure: float = Field(default=0.3, description="Maximum sector exposure (0-1)")
    max_correlation: float = Field(default=0.7, description="Maximum correlation between positions")

    # Circuit breakers
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

    # Performance thresholds
    max_latency_ms: int = Field(
        default=1000, description="Maximum acceptable latency in milliseconds"
    )
    max_execution_time_ms: int = Field(
        default=500, description="Maximum execution time in milliseconds"
    )

    # Slippage analysis parameters
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

    # Default spreads by asset class
    default_crypto_spread: Decimal = Field(
        default=Decimal("0.0001"), description="Default spread for crypto assets (1 bps)"
    )
    default_forex_spread: Decimal = Field(
        default=Decimal("0.0001"), description="Default spread for forex pairs (1 bps)"
    )
    default_stock_spread: Decimal = Field(
        default=Decimal("0.01"), description="Default spread for stocks (1%)"
    )
    default_etf_spread: Decimal = Field(
        default=Decimal("0.01"), description="Default spread for ETFs (1%)"
    )

    # Additional thresholds for momentum analysis
    min_strength: float = Field(
        default=60.0, description="Minimum strength threshold for momentum analysis"
    )

    # ATR Volatility Filter
    min_atr_threshold: float = Field(
        default=0.015, description="Minimum ATR threshold for volatility filtering (0-1)"
    )
    atr_filter_enabled: bool = Field(
        default=True, description="Enable ATR volatility filter to avoid choppy markets"
    )
    trailing_stop_distance_pct: float = Field(
        default=0.02, description="Trailing stop distance percentage (0-1)"
    )
    trailing_stop_enabled: bool = Field(
        default=True, description="Enable trailing stop for dynamic exits"
    )

    # Signal Scoring Engine
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

    # Multi-Strategy Allocation
    momentum_target_weight: float = Field(
        default=0.50, description="Momentum strategy target weight"
    )
    mean_reversion_target_weight: float = Field(
        default=0.25, description="Mean reversion strategy target weight"
    )
    pairs_trading_target_weight: float = Field(
        default=0.25, description="Pairs trading strategy target weight"
    )

    # Risk Management
    max_risk_per_trade: float = Field(default=0.02, description="Maximum risk per trade (0-1)")
    min_risk_reward_ratio: float = Field(default=3.0, description="Minimum risk/reward ratio")
    max_momentum_exposure: float = Field(default=0.50, description="Max momentum exposure (0-1)")
    max_mean_reversion_exposure: float = Field(
        default=0.30, description="Max mean reversion exposure (0-1)"
    )
    max_pairs_trading_exposure: float = Field(
        default=0.30, description="Max pairs trading exposure (0-1)"
    )
    max_consecutive_stops: int = Field(default=5, description="Max consecutive stops before pause")

    # Portfolio Rebalancing
    rebalance_frequency_days: int = Field(default=30, description="Rebalancing frequency in days")
    rebalance_drift_threshold: float = Field(
        default=0.05, description="Rebalance drift threshold (0-1)"
    )
    min_allocation_weight: float = Field(
        default=0.10, description="Minimum allocation weight (0-1)"
    )
    max_allocation_weight: float = Field(
        default=0.70, description="Maximum allocation weight (0-1)"
    )
    capital_adjustment_factor: float = Field(
        default=0.20, description="Capital adjustment factor per negative streak (0-1)"
    )

    # Stochastic RSI thresholds
    stoch_rsi_oversold: float = Field(
        default=20.0, ge=0.0, le=100.0, description="Stochastic RSI oversold threshold"
    )
    stoch_rsi_overbought: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Stochastic RSI overbought threshold"
    )

    # MACD thresholds
    macd_signal_threshold: float = Field(
        default=0.0, description="MACD signal line crossover threshold"
    )
    macd_histogram_threshold: float = Field(
        default=0.0, description="MACD histogram threshold for divergence detection"
    )

    # Bollinger Bands
    bollinger_period: int = Field(default=20, description="Bollinger Bands period")
    bollinger_std_dev: float = Field(default=2.0, description="Bollinger Bands standard deviation")

    # Volume thresholds
    min_volume_ratio: float = Field(
        default=1.5, description="Minimum volume ratio vs average for signal confirmation"
    )
    volume_surge_threshold: float = Field(
        default=2.0, description="Volume surge threshold (2x average)"
    )

    # Trend confirmation
    trend_confirmation_periods: int = Field(
        default=3, description="Number of periods for trend confirmation"
    )
    trend_strength_threshold: float = Field(
        default=0.6, description="Trend strength threshold (0-1)"
    )

    # Volatility parameters
    volatility_min_ratio: float = Field(
        default=0.01, ge=0.001, le=0.1, description="Minimum ATR ratio to prevent scale explosion"
    )
    volatility_scale_min: float = Field(
        default=0.5, ge=0.2, le=0.9, description="Minimum volatility scale (0.5 = 50%)"
    )
    volatility_scale_max: float = Field(
        default=1.5, ge=1.1, le=3.0, description="Maximum volatility scale (1.5 = 150%)"
    )
    volatility_spike_threshold_multiplier: float = Field(
        default=2.0, ge=1.5, le=5.0, description="Multiplier for spike detection"
    )
    volatility_spike_simple_multiplier: float = Field(
        default=1.5, ge=1.2, le=3.0, description="Simple spike threshold multiplier"
    )
    volatility_regime_very_low: float = Field(
        default=0.75, ge=0.5, le=0.9, description="Very low volatility ratio threshold"
    )
    volatility_regime_low: float = Field(
        default=0.90, ge=0.8, le=0.95, description="Low volatility ratio threshold"
    )
    volatility_regime_normal_upper: float = Field(
        default=1.10, ge=1.05, le=1.20, description="Normal volatility upper ratio threshold"
    )
    volatility_regime_high: float = Field(
        default=1.50, ge=1.2, le=2.0, description="High volatility ratio threshold"
    )
    volatility_spike_lookback_minutes: int = Field(
        default=60, ge=10, le=300, description="Lookback minutes for recent spikes"
    )
    volatility_std_dev_lookback: int = Field(
        default=30, ge=10, le=100, description="Lookback periods for ATR std dev calculation"
    )

    # Trailing Stop R-Multiple Parameters
    trailing_stop_r1_threshold: float = Field(
        default=1.0, ge=0.5, le=2.0, description="R-multiple threshold for initial trailing"
    )
    trailing_stop_r2_threshold: float = Field(
        default=2.0, ge=1.0, le=3.0, description="R-multiple threshold for break-even"
    )
    trailing_stop_r3_threshold: float = Field(
        default=3.0, ge=2.0, le=5.0, description="R-multiple threshold for aggressive trailing"
    )
    trailing_stop_r3_trailing_pct: float = Field(
        default=0.5, ge=0.3, le=0.8, description="Trailing stop percentage at R3"
    )

    @field_validator(
        "momentum_target_weight",
        "mean_reversion_target_weight",
        "pairs_trading_target_weight",
        "max_momentum_exposure",
        "max_mean_reversion_exposure",
        "max_pairs_trading_exposure",
        "max_risk_per_trade",
        "rebalance_drift_threshold",
        "min_allocation_weight",
        "max_allocation_weight",
        "capital_adjustment_factor",
    )
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v

    @field_validator(
        "max_position_size",
        "min_position_size",
        "take_profit_pct",
        "daily_loss_limit",
        "max_drawdown_limit",
        "max_total_exposure",
        "max_sector_exposure",
        "max_correlation",
        "circuit_breaker_daily_loss",
        "circuit_breaker_drawdown",
        "circuit_breaker_volatility",
        "circuit_breaker_error_rate",
    )
    @classmethod
    def validate_percentage_limits(cls, v):
        """Validate percentage values for risk limits (0-1 range)."""
        if not 0 <= v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v

    @field_validator("stop_loss_pct")
    @classmethod
    def validate_stop_loss(cls, v):
        if not 0 <= v <= 0.5:
            raise ValueError("Stop loss percentage must be between 0 and 0.5")
        return v

    @field_validator(
        "volatility_threshold_high",
        "volatility_threshold_extreme",
        "max_spread_threshold",
        "base_slippage",
    )
    @classmethod
    def validate_decimal_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Decimal percentage values must be between 0 and 100")
        return v

    @field_validator(
        "min_signal_strength",
        "min_signal_confidence",
        "min_liquidity_score",
        "min_strength",
    )
    @classmethod
    def validate_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Score values must be between 0 and 100")
        return v
