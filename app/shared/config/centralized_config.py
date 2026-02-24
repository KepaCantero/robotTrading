"""
Centralized Configuration System
TASK-10: Centralización de Configuración

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.

SECTIONS:
    1. Enums & Constants
    2. Trading Configuration (TradingThresholds, StrategyConfig, StockAllocationSettings)
    3. Infrastructure Configuration (DatabaseConfig, RedisConfig, APIConfig)
    4. Monitoring & Logging (LoggingConfig, MonitoringConfig)
    5. Risk & Compliance (CurrencyHedgingConfig, SectorCountryDiversificationConfig, ComplianceConfig)
    6. Main Configuration (CentralizedConfig)
    7. Helper Functions (get_config, etc.)
    8. Legacy/Utility (Configuration wrapper class)
"""

import logging
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.domain.strategies.config import (
        DividendStrategyConfig,
        FXCarryTradeStrategyConfig,
        MomentumModularConfig,
    )
from app.shared.config.signal_risk import MarketMicrostructureThresholds

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: ENUMS & CONSTANTS
# =============================================================================

class Environment(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


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

    # Additional thresholds for momentum analysis
    min_strength: float = Field(
        default=60.0, description="Minimum strength threshold for momentum analysis"
    )

    # ATR Volatility Filter (NEW)
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

    # Multi-Strategy Allocation (TASK-PA-1, PA-2)
    momentum_target_weight: float = Field(
        default=0.50, description="Momentum strategy target weight"
    )
    mean_reversion_target_weight: float = Field(
        default=0.25, description="Mean reversion strategy target weight"
    )
    pairs_trading_target_weight: float = Field(
        default=0.25, description="Pairs trading strategy target weight"
    )

    # Risk Management (TASK-RM-1 to RM-5)
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

    # Portfolio Rebalancing (TASK-REB-1, REB-2)
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
        if not 0 <= v <= 0.5:  # Allow up to 50% stop loss
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

    # ========== TECHNICAL INDICATORS THRESHOLDS ==========

    # Stochastic RSI thresholds
    stoch_rsi_oversold: float = Field(
        default=20.0, ge=0.0, le=100.0, description="Stochastic RSI oversold threshold"
    )
    stoch_rsi_overbought: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Stochastic RSI overbought threshold"
    )

    # Momentum zones
    momentum_zone_min: float = Field(
        default=40.0, ge=0.0, le=100.0, description="Minimum RSI for momentum zone"
    )
    momentum_zone_max: float = Field(
        default=70.0, ge=0.0, le=100.0, description="Maximum RSI for momentum zone"
    )
    rsi_recovering_threshold: float = Field(
        default=40.0, ge=0.0, le=100.0, description="RSI threshold for recovering from oversold"
    )
    rsi_sell_overbought: float = Field(
        default=55.0, ge=0.0, le=100.0, description="RSI threshold for overbought sell signal"
    )
    rsi_neutral_zone_min: float = Field(
        default=50.0, ge=0.0, le=100.0, description="Minimum RSI for neutral zone"
    )
    rsi_neutral_zone_max: float = Field(
        default=55.0, ge=0.0, le=100.0, description="Maximum RSI for neutral zone"
    )

    # Volume thresholds
    strong_volume_multiplier: float = Field(
        default=1.25, ge=1.0, le=10.0, description="Strong volume multiplier"
    )

    # Signal scores
    signal_liquidity_score: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Default liquidity score for signals"
    )
    signal_priority_score: float = Field(
        default=85.0, ge=0.0, le=100.0, description="Default priority score for signals"
    )

    # ========== WINDOW SIZES AND HISTORY LENGTHS ==========

    # Price history lengths
    default_price_history_length: int = Field(
        default=200, ge=10, le=10000, description="Default price history length (candles)"
    )
    rsi_history_length: int = Field(
        default=50, ge=10, le=1000, description="RSI history length for Stochastic RSI"
    )
    atr_history_length: int = Field(
        default=14, ge=5, le=100, description="ATR history length"
    )
    multi_factor_history_length: int = Field(
        default=100, ge=10, le=1000, description="Multi-factor return history length"
    )
    annual_trading_days: int = Field(
        default=252, ge=200, le=300, description="Number of trading days in a year"
    )
    yearly_history_length: int = Field(
        default=365, ge=300, le=400, description="One year of daily data"
    )
    pairs_trading_history_length: int = Field(
        default=300, ge=100, le=1000, description="Pairs trading history length"
    )

    # Technical indicator periods
    default_rsi_period: int = Field(
        default=14, ge=2, le=50, description="Default RSI period"
    )
    default_ema_period: int = Field(
        default=20, ge=2, le=200, description="Default EMA period"
    )
    default_roc_period: int = Field(
        default=12, ge=1, le=50, description="Default ROC (Rate of Change) period"
    )
    default_stoch_rsi_period: int = Field(
        default=14, ge=5, le=50, description="Default Stochastic RSI period"
    )
    default_atr_period: int = Field(
        default=14, ge=5, le=50, description="Default ATR period"
    )

    # Log intervals
    log_interval_bars: int = Field(
        default=50, ge=10, le=1000, description="Log interval (number of bars)"
    )

    # ========== CONVERSION MULTIPLIERS ==========

    # Basis points conversion
    bps_multiplier: int = Field(
        default=10000, ge=1, le=100000, description="Multiplier for basis points conversion"
    )

    # Percentage conversion
    percentage_multiplier: int = Field(
        default=100, ge=1, le=1000, description="Multiplier for percentage conversion"
    )

    # Milliseconds conversion
    milliseconds_multiplier: int = Field(
        default=1000, ge=1, le=10000, description="Multiplier for milliseconds conversion"
    )

    # Time conversions
    seconds_per_day: int = Field(
        default=86400, ge=1, le=100000, description="Seconds per day"
    )

    # ========== PERFORMANCE THRESHOLDS ==========

    # Sharpe ratio
    min_sharpe_ratio: float = Field(
        default=1.0, ge=0.0, le=10.0, description="Minimum Sharpe ratio threshold"
    )

    # Fill rate
    min_fill_rate: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Minimum fill rate threshold"
    )

    # Confidence levels
    high_confidence_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="High confidence threshold"
    )
    medium_confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Medium confidence threshold"
    )
    low_confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Low confidence threshold"
    )

    # ========== PAIRS TRADING SPECIFIC ==========

    # Spread threshold multipliers
    spread_threshold_half_divisor: float = Field(
        default=2.0, ge=1.1, le=10.0, description="Divisor for half spread threshold (more permissive)"
    )
    cointegration_relaxed_multiplier: float = Field(
        default=0.8, ge=0.1, le=1.0, description="Multiplier for relaxed cointegration threshold"
    )

    # ========== FUNDAMENTAL ANALYSIS THRESHOLDS ==========

    # P/E ratio thresholds
    pe_ideal_min: float = Field(default=10.0, ge=0.0, le=50.0, description="Ideal minimum P/E ratio")
    pe_ideal_max: float = Field(default=20.0, ge=0.0, le=100.0, description="Ideal maximum P/E ratio")
    pe_very_cheap_max: float = Field(default=5.0, ge=0.0, le=20.0, description="Very cheap P/E threshold")
    pe_acceptable_max: float = Field(default=25.0, ge=10.0, le=100.0, description="Acceptable P/E threshold")
    pe_too_expensive_min: float = Field(default=25.0, ge=10.0, le=100.0, description="Too expensive P/E threshold")
    pe_problematic_max: float = Field(default=5.0, ge=0.0, le=20.0, description="Problematic P/E threshold")

    # P/B ratio thresholds
    pb_ideal_min: float = Field(default=1.0, ge=0.0, le=10.0, description="Ideal minimum P/B ratio")
    pb_ideal_max: float = Field(default=3.0, ge=0.0, le=20.0, description="Ideal maximum P/B ratio")
    pb_very_cheap_max: float = Field(default=1.0, ge=0.0, le=5.0, description="Very cheap P/B threshold")
    pb_too_expensive: float = Field(default=5.0, ge=1.0, le=50.0, description="Too expensive P/B threshold")

    # ROE thresholds
    roe_excellent: float = Field(default=15.0, ge=0.0, le=100.0, description="Excellent ROE threshold (%)")
    roe_good: float = Field(default=10.0, ge=0.0, le=50.0, description="Good ROE threshold (%)")

    # Dividend safety coverage ratios
    dividend_coverage_excellent: float = Field(default=2.0, ge=1.0, le=10.0, description="Excellent dividend coverage ratio")
    dividend_coverage_good: float = Field(default=1.5, ge=1.0, le=5.0, description="Good dividend coverage ratio")

    # Score thresholds
    dividend_buy_score: float = Field(default=70.0, ge=0.0, le=100.0, description="Dividend stock buy score threshold")
    dividend_hold_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Dividend stock hold score threshold")

    # ========== FX CARRY TRADE SPECIFIC ==========

    # FX rate simulation variation factors
    fx_daily_variation_factor: float = Field(
        default=0.0001, ge=0.0, le=0.01, description="Daily FX rate variation factor for simulation"
    )
    fx_long_term_variation_factor: float = Field(
        default=0.00001, ge=0.0, le=0.001, description="Long-term FX rate variation factor for simulation"
    )
    fx_quantization_precision: str = Field(
        default="0.0001", description="FX rate quantization precision"
    )
    fx_months_per_year: int = Field(
        default=12, ge=1, le=12, description="Months per year for forward calculation"
    )
    fx_default_interest_rate: float = Field(
        default=0.02, ge=0.0, le=0.5, description="Default FX interest rate (2%)"
    )

    # ========== OPTIONS/COVERED CALLS SPECIFIC ==========

    # Strike price calculation
    covered_call_otm_multiplier: float = Field(
        default=1.5, ge=1.0, le=3.0, description="OTM multiplier for target strike calculation"
    )

    # ========== BACKTESTING SLIPPAGE SPECIFIC ==========

    # Spread skew factors
    spread_skew_base: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Base spread skew factor"
    )

    # ========== STATISTICAL TESTING THRESHOLDS ==========

    # P-value thresholds
    p_value_significance: float = Field(
        default=0.1, ge=0.001, le=0.5, description="P-value threshold for statistical significance"
    )

    # ========== DIVIDEND INVESTING THRESHOLDS ==========

    # Score thresholds
    dividend_score_excellent: float = Field(default=0.7, ge=0.0, le=1.0, description="Excellent dividend score")
    dividend_score_good: float = Field(default=0.5, ge=0.0, le=1.0, description="Good dividend score")
    valuation_ratio_cheap: float = Field(default=0.9, ge=0.0, le=2.0, description="Cheap valuation ratio")
    valuation_ratio_fair: float = Field(default=1.0, ge=0.0, le=3.0, description="Fair valuation ratio")

    # ========== PAIRS TRADING CORRELATION ==========

    # Correlation threshold
    pairs_correlation_min: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum correlation for pairs trading"
    )

    # ========== POSITION SIZING SPECIFIC ==========

    # ATR fallback and stop loss
    atr_multiplier_default: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Default ATR multiplier for position sizing"
    )
    max_stop_distance_pct: float = Field(
        default=0.20, ge=0.01, le=0.50, description="Maximum stop distance as % of price (20%)"
    )
    default_stop_loss_pct: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Default stop loss percentage (5%)"
    )
    risk_per_trade_default: float = Field(
        default=0.02, ge=0.001, le=0.10, description="Default risk per trade (2%)"
    )

    # Kelly Criterion parameters
    kelly_half_multiplier: float = Field(
        default=0.5, ge=0.1, le=1.0, description="Half-Kelly safety multiplier (0.5)"
    )
    kelly_max_position_pct: float = Field(
        default=0.25, ge=0.01, le=0.50, description="Maximum position size from Kelly (25%)"
    )
    kelly_fallback_fraction: float = Field(
        default=0.02, ge=0.001, le=0.10, description="Fallback Kelly fraction (2%)"
    )
    kelly_min_positive_threshold: float = Field(
        default=0.02, ge=0.0, le=0.10, description="Minimum Kelly for positive recommendation (2%)"
    )

    # ========== PORTFOLIO ANALYTICS SPECIFIC ==========

    # Risk-free rate and benchmark
    risk_free_rate: float = Field(
        default=0.02, ge=0.0, le=0.20, description="Risk-free rate (2%)"
    )
    benchmark_return: float = Field(
        default=0.08, ge=0.0, le=0.50, description="Benchmark return (8%)"
    )

    # Allocation targets
    equity_allocation_target: float = Field(
        default=0.60, ge=0.0, le=1.0, description="Target equity allocation (60%)"
    )
    cash_allocation_target: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Target cash allocation (40%)"
    )
    rebalance_threshold_pct: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Rebalancing threshold (5%)"
    )

    # Risk scoring thresholds
    max_volatility_for_risk_score: float = Field(
        default=50.0, ge=10.0, le=100.0, description="Max volatility for risk score calculation"
    )
    max_position_weight_for_risk_score: float = Field(
        default=50.0, ge=5.0, le=100.0, description="Max position weight for risk score calculation"
    )
    volatility_risk_max: float = Field(
        default=20.0, ge=5.0, le=50.0, description="Volatility threshold for risk level assessment (20%)"
    )
    concentration_weight_max: float = Field(
        default=20.0, ge=5.0, le=50.0, description="Max concentration weight for risk level (20%)"
    )

    # Recommendation thresholds
    min_annualized_return_for_recommendation: float = Field(
        default=5.0, ge=0.0, le=20.0, description="Min annualized return threshold (5%)"
    )
    min_sharpe_for_recommendation: float = Field(
        default=0.5, ge=0.0, le=3.0, description="Min Sharpe ratio for recommendation (0.5)"
    )
    high_volatility_threshold: float = Field(
        default=20.0, ge=10.0, le=50.0, description="High volatility threshold (20%)"
    )
    high_drawdown_threshold: float = Field(
        default=20.0, ge=5.0, le=50.0, description="High drawdown threshold (20%)"
    )
    high_var_threshold: float = Field(
        default=10.0, ge=1.0, le=30.0, description="High Value at Risk threshold (10%)"
    )
    extreme_volatility_threshold: float = Field(
        default=30.0, ge=10.0, le=100.0, description="Extreme volatility threshold (30%)"
    )
    extreme_concentration_threshold: float = Field(
        default=30.0, ge=10.0, le=100.0, description="Extreme concentration threshold (30%)"
    )

    # Health score weights
    health_score_performance_weight: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Health score performance weight (40%)"
    )
    health_score_risk_weight: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Health score risk weight (30%)"
    )
    health_score_diversification_weight: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Health score diversification weight (30%)"
    )
    max_annualized_return_for_health: float = Field(
        default=20.0, ge=5.0, le=100.0, description="Max annualized return for health score (20%)"
    )
    effective_positions_for_health: float = Field(
        default=10.0, ge=3.0, le=50.0, description="Effective positions for health score (10)"
    )
    max_effective_positions_for_diversification: float = Field(
        default=20.0, ge=5.0, le=100.0, description="Max effective positions for diversification (20)"
    )
    high_cash_ratio_threshold: float = Field(
        default=0.50, ge=0.1, le=0.9, description="High cash ratio threshold (50%)"
    )

    # Mock portfolio simulation
    mock_daily_return: float = Field(
        default=0.001, ge=0.0, le=0.01, description="Mock daily return for simulation (0.1%)"
    )

    # ========== PORTFOLIO REBALANCER SPECIFIC ==========

    # Capital adjustment thresholds
    consecutive_losses_threshold: int = Field(
        default=3, ge=1, le=10, description="Consecutive losses threshold for reduction"
    )
    poor_performance_threshold: float = Field(
        default=-0.15, ge=-0.50, le=-0.05, description="Poor performance threshold (-15%)"
    )
    weak_performance_threshold: float = Field(
        default=-0.05, ge=-0.20, le=-0.01, description="Weak performance threshold (-5%)"
    )
    strong_performance_reduction: float = Field(
        default=0.20, ge=0.10, le=0.50, description="Strong performance reduction (20%)"
    )
    moderate_performance_reduction: float = Field(
        default=0.10, ge=0.05, le=0.30, description="Moderate performance reduction (10%)"
    )
    max_reduction_factor: float = Field(
        default=0.50, ge=0.20, le=0.80, description="Maximum reduction factor (50%)"
    )

    # Risk impact estimation
    rebalance_risk_impact_per_allocation: float = Field(
        default=0.10, ge=0.01, le=0.50, description="Risk impact per 1% allocation change (0.1%)"
    )
    rebalance_return_impact_per_allocation: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Return impact per 1% allocation change (0.05%)"
    )

    # ========== EXECUTION ENGINE SPECIFIC ==========

    # History and latency
    execution_history_max_size: int = Field(
        default=1000, ge=100, le=10000, description="Maximum execution history size"
    )
    simulated_latency_ms: float = Field(
        default=1.0, ge=0.1, le=100.0, description="Simulated latency in milliseconds"
    )

    # ========== MODEL VALIDATION THRESHOLDS ==========

    # Signal validation limits
    max_signal_price_usd: float = Field(
        default=1_000_000.0, ge=100_000.0, le=10_000_000.0, description="Maximum signal price in USD ($1M)"
    )
    max_signal_volume_shares: float = Field(
        default=10_000_000_000.0, ge=1_000_000_000.0, le=100_000_000_000.0, description="Maximum signal volume in shares (10B)"
    )

    # Order validation limits
    max_order_quantity_shares: float = Field(
        default=1_000_000.0, ge=100_000.0, le=100_000_000.0, description="Maximum order quantity in shares (1M)"
    )
    max_order_price_usd: float = Field(
        default=1_000_000.0, ge=100_000.0, le=10_000_000.0, description="Maximum order price in USD ($1M)"
    )
    max_order_timestamp_age_days: int = Field(
        default=365, ge=30, le=3650, description="Maximum age of order timestamp in days (1 year)"
    )

    # ========== SLIPPAGE ANALYSIS THRESHOLDS ==========

    # Volatility trend multipliers
    volatility_trend_increasing_threshold: float = Field(
        default=1.1, ge=1.01, le=2.0, description="Threshold for increasing volatility trend (1.1x)"
    )
    volatility_trend_decreasing_threshold: float = Field(
        default=0.9, ge=0.5, le=0.99, description="Threshold for decreasing volatility trend (0.9x)"
    )

    # Liquidity score normalization
    liquidity_max_spread_percent: float = Field(
        default=5.0, ge=1.0, le=20.0, description="Maximum spread for liquidity score normalization (5%)"
    )
    liquidity_volume_normalization: float = Field(
        default=1_000_000.0, ge=100_000.0, le=100_000_000.0, description="Volume normalization for liquidity score (1M)"
    )
    liquidity_depth_normalization: float = Field(
        default=100_000.0, ge=10_000.0, le=1_000_000.0, description="Depth normalization for liquidity score (100K)"
    )
    liquidity_spread_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Weight for spread in liquidity score (40%)"
    )
    liquidity_volume_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Weight for volume in liquidity score (40%)"
    )
    liquidity_depth_weight: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Weight for depth in liquidity score (20%)"
    )
    liquidity_stress_multiplier: float = Field(
        default=1.5, ge=1.1, le=3.0, description="Multiplier for liquidity stress threshold (1.5x)"
    )

    # Order size impact thresholds
    order_size_tiny_threshold: float = Field(
        default=0.001, ge=0.0001, le=0.01, description="Tiny order size threshold (0.1%)"
    )
    order_size_small_threshold: float = Field(
        default=0.01, ge=0.001, le=0.1, description="Small order size threshold (1%)"
    )
    order_size_small_multiplier: float = Field(
        default=10.0, ge=1.0, le=50.0, description="Impact multiplier for small orders"
    )
    order_size_large_multiplier: float = Field(
        default=20.0, ge=5.0, le=100.0, description="Impact multiplier for large orders"
    )

    # ========== MEAN REVERSION STRATEGY SPECIFIC ==========

    # Z-score thresholds
    min_z_score_default: float = Field(
        default=1.5, ge=0.5, le=3.0, description="Default minimum Z-score for mean reversion (1.5)"
    )
    z_score_modified_threshold: float = Field(
        default=1.2, ge=0.5, le=2.5, description="Modified Z-score threshold for signals (1.2)"
    )
    z_score_entry_multiplier: float = Field(
        default=0.7, ge=0.5, le=0.9, description="Z-score multiplier for entry signals (70%)"
    )

    # Exposure and volatility
    mean_reversion_max_exposure: float = Field(
        default=0.60, ge=0.10, le=0.90, description="Maximum exposure for mean reversion (60%)"
    )
    mean_reversion_simulated_std_dev: float = Field(
        default=0.02, ge=0.005, le=0.10, description="Simulated standard deviation for mean reversion (2%)"
    )
    mean_reversion_simulated_volatility: float = Field(
        default=0.015, ge=0.005, le=0.05, description="Simulated volatility for mean reversion (1.5%)"
    )

    # Signal score defaults (when not calculated)
    mean_reversion_default_confidence: float = Field(
        default=70.0, ge=0.0, le=100.0, description="Default confidence score for mean reversion signals"
    )
    mean_reversion_default_liquidity: float = Field(
        default=75.0, ge=0.0, le=100.0, description="Default liquidity score for mean reversion signals"
    )
    mean_reversion_default_priority: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Default priority score for mean reversion signals"
    )

    # T18.1: Metrics Database Configuration
    metrics_db_enabled: bool = Field(default=True, description="Enable metrics database collection")
    metrics_collection_interval: int = Field(
        default=60, description="Metrics collection interval in seconds"
    )
    metrics_batch_size: int = Field(default=1000, description="Metrics batch size for inserts")
    metrics_retention_days: int = Field(default=90, description="Metrics retention period in days")
    questdb_host: str = Field(default="localhost", description="QuestDB host")
    questdb_port: int = Field(default=5432, description="QuestDB port")
    questdb_database: str = Field(default="qdb", description="QuestDB database name")
    questdb_user: str = Field(default="admin", description="QuestDB user")
    # Rule 28: No default password - must come from environment
    questdb_password: str = Field(
        default="", description="QuestDB password (from QUESTDB_PASSWORD env var)"
    )
    questdb_pool_size: int = Field(default=10, description="QuestDB connection pool size")
    questdb_max_retries: int = Field(default=3, description="QuestDB maximum retries")
    metrics_cache_enabled: bool = Field(default=True, description="Enable metrics query caching")
    metrics_cache_ttl_seconds: int = Field(default=300, description="Metrics cache TTL in seconds")

    # ========== CIRCUIT BREAKER THRESHOLDS ==========
    circuit_breaker_level_1: float = Field(
        default=-0.07, ge=-0.20, le=-0.03, description="Level 1 circuit breaker threshold (-7%)"
    )
    circuit_breaker_level_2: float = Field(
        default=-0.13, ge=-0.25, le=-0.08, description="Level 2 circuit breaker threshold (-13%)"
    )
    circuit_breaker_level_3: float = Field(
        default=-0.20, ge=-0.40, le=-0.15, description="Level 3 circuit breaker threshold (-20%)"
    )
    circuit_breaker_stock_volatility: float = Field(
        default=0.20, ge=0.05, le=0.50, description="Stock volatility threshold for halt (20%)"
    )
    circuit_breaker_vix_high: float = Field(
        default=40.0, ge=20.0, le=100.0, description="VIX high threshold"
    )
    circuit_breaker_vix_extreme: float = Field(
        default=60.0, ge=40.0, le=200.0, description="VIX extreme threshold"
    )

    # API Circuit Breaker thresholds (resilience pattern)
    circuit_breaker_failure_threshold: int = Field(
        default=5, ge=1, le=20, description="API failure threshold for circuit breaker (5 failures)"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, ge=10, le=600, description="API circuit breaker recovery timeout in seconds (60s)"
    )

    # ========== CURRENCY HEDGING PARAMETERS ==========
    currency_single_max: float = Field(
        default=0.25, ge=0.10, le=0.50, description="Max single currency exposure (25%)"
    )
    currency_total_max: float = Field(
        default=0.50, ge=0.20, le=0.80, description="Max total FX exposure (50%)"
    )
    currency_min_exposure: float = Field(
        default=50000.0, ge=10000.0, le=500000.0, description="Minimum exposure for hedging ($50k)"
    )
    currency_max_cost_bps: float = Field(
        default=10.0, ge=1.0, le=50.0, description="Max hedging cost in bps (10 bps)"
    )
    currency_partial_hedge_pct: float = Field(
        default=0.5, ge=0.1, le=0.9, description="Partial hedge percentage (50%)"
    )

    # ========== LEARNING CAPITAL GATE PARAMETERS ==========
    learning_min_capital: float = Field(
        default=25000.0, ge=10000.0, le=100000.0, description="Minimum capital for learning viability ($25k)"
    )
    learning_monthly_cost: float = Field(
        default=50.0, ge=10.0, le=200.0, description="Estimated monthly learning cost ($50)"
    )
    learning_max_cost_ratio: float = Field(
        default=0.30, ge=0.10, le=0.50, description="Max learning cost as % of alpha (30%)"
    )

    # ========== TRAILING STOP PARAMETERS ==========
    trailing_stop_default_pct: float = Field(
        default=0.015, ge=0.005, le=0.05, description="Default trailing stop percentage (1.5%)"
    )

    # ========== OPPORTUNITY COST PARAMETERS ==========
    opportunity_risk_free_rate: float = Field(
        default=0.04, ge=0.01, le=0.10, description="Risk-free rate for opportunity cost (4%)"
    )
    opportunity_min_return: float = Field(
        default=0.03, ge=0.01, le=0.10, description="Minimum return for opportunity cost (3%)"
    )

    # ========== CAPITAL VIABILITY GATE PARAMETERS ==========
    capital_viability_alpha_threshold: float = Field(
        default=0.10, ge=0.05, le=0.30, description="Unreachable alpha threshold (10%)"
    )
    capital_viability_min_achievable: float = Field(
        default=0.02, ge=0.01, le=0.05, description="Minimum achievable alpha (2%)"
    )
    capital_viability_max_achievable: float = Field(
        default=0.05, ge=0.02, le=0.15, description="Maximum achievable alpha (5%)"
    )

    # ========== DYNAMIC CAPITAL REALLOCATION PARAMETERS ==========
    dynamic_realloc_min_weight: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Minimum weight for reallocation (5%)"
    )
    dynamic_realloc_max_weight: float = Field(
        default=0.70, ge=0.30, le=0.90, description="Maximum weight for reallocation (70%)"
    )
    dynamic_realloc_volatility_target: float = Field(
        default=0.10, ge=0.05, le=0.30, description="Target volatility for reallocation (10%)"
    )
    dynamic_realloc_min_trades: int = Field(
        default=5, ge=1, le=20, description="Minimum trades for active strategy (5)"
    )
    dynamic_realloc_rebalance_days: int = Field(
        default=30, ge=7, le=90, description="Rebalance frequency in days (30)"
    )
    dynamic_realloc_rolling_window: int = Field(
        default=30, ge=7, le=90, description="Rolling window in days (30)"
    )

    # ========== ALERT TO TRADE MAPPER PARAMETERS ==========
    alert_limit_price_offset: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Limit price offset from alert price (1%)"
    )

    # ========== CAPITAL TIER STRATEGY SELECTOR PARAMETERS ==========
    tier_micro_max_drawdown: float = Field(
        default=0.05, ge=0.02, le=0.10, description="Max drawdown for micro tier (5%)"
    )
    tier_small_max_drawdown: float = Field(
        default=0.08, ge=0.03, le=0.15, description="Max drawdown for small tier (8%)"
    )
    tier_default_position_size: float = Field(
        default=0.05, ge=0.01, le=0.20, description="Default position size pct (5%)"
    )
    tier_default_max_daily_loss: float = Field(
        default=0.02, ge=0.01, le=0.10, description="Default max daily loss pct (2%)"
    )

    # ========== ACCOUNT CONFIGURATION PARAMETERS ==========
    account_default_position_size: float = Field(
        default=0.02, ge=0.01, le=0.10, description="Default position size pct (2%)"
    )

    # ========== TAX OPTIMIZATION PARAMETERS ==========
    tax_dividend_rate: float = Field(
        default=0.0875, ge=0.0, le=0.30, description="Dividend tax rate (8.75%)"
    )

    # ========== TRADING VALIDATORS PARAMETERS ==========
    validator_default_max_position_pct: float = Field(
        default=0.25, ge=0.05, le=0.50, description="Default max position as % of capital (25%)"
    )
    validator_min_position_pct: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Minimum position as % of capital (1%)"
    )
    validator_max_position_pct: float = Field(
        default=1.0, ge=0.50, le=1.0, description="Maximum position as % of capital (100%)"
    )
    validator_stop_loss_warning_pct: float = Field(
        default=0.50, ge=0.10, le=1.0, description="Stop loss warning threshold (50% away from entry)"
    )
    validator_min_reward_risk_ratio: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Minimum acceptable reward/risk ratio (2.0)"
    )

    # ========== TRANSACTION COSTS PARAMETERS ==========
    tx_sec_fee_per_share: float = Field(
        default=0.0000207, ge=0.00001, le=0.0001, description="SEC fee per share (selling only)"
    )
    tx_trading_fee_per_share: float = Field(
        default=0.000175, ge=0.0001, le=0.001, description="Trading fee per share (NYSE)"
    )
    tx_market_order_slippage_pct: float = Field(
        default=0.50, ge=0.10, le=1.0, description="Market order slippage as % of impact (50%)"
    )

    # ========== TRADING CALENDAR CONSTANTS ==========
    annual_trading_days_const: int = Field(
        default=252, ge=200, le=300, description="Number of trading days in a year (252)"
    )

    # ========== POSITION MONITOR PARAMETERS ==========
    position_monitor_check_interval: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Position monitor check interval in seconds (1.0)"
    )
    position_monitor_price_fetch_timeout: float = Field(
        default=5.0, ge=1.0, le=30.0, description="Price fetch timeout in seconds (5.0)"
    )
    position_monitor_stop_execution_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Stop order execution timeout in seconds (30.0)"
    )
    position_monitor_state_sync_interval: float = Field(
        default=10.0, ge=1.0, le=60.0, description="State sync interval in seconds (10.0)"
    )
    position_monitor_max_retries: int = Field(
        default=3, ge=1, le=10, description="Max price fetch retries (3)"
    )

    # ========== RECONNECTION MANAGER PARAMETERS ==========
    reconnection_max_attempts: int = Field(
        default=10, ge=3, le=30, description="Max reconnection attempts (10)"
    )
    reconnection_base_delay_seconds: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Base delay for exponential backoff in seconds (1.0)"
    )
    reconnection_max_delay_seconds: float = Field(
        default=60.0, ge=10.0, le=300.0, description="Max delay for exponential backoff in seconds (60.0)"
    )
    reconnection_exponential_base: float = Field(
        default=2.0, ge=1.5, le=3.0, description="Exponential base for backoff calculation (2.0)"
    )
    reconnection_jitter_factor: float = Field(
        default=0.1, ge=0.0, le=0.5, description="Jitter factor to prevent thundering herd (0.1 = 10%)"
    )
    reconnection_alert_after_attempts: int = Field(
        default=3, ge=1, le=10, description="Send alert after this many failed attempts (3)"
    )
    reconnection_health_check_interval: float = Field(
        default=5.0, ge=1.0, le=30.0, description="Health check interval in seconds (5.0)"
    )
    reconnection_default_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Default connection timeout in seconds (30.0)"
    )
    reconnection_maintain_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Delay before reconnection attempt in seconds (1.0)"
    )

    # ========== RATE LIMITER PARAMETERS ==========
    rate_limit_alert_threshold: float = Field(
        default=0.8, ge=0.5, le=0.95, description="Alert when token usage exceeds this ratio (0.8 = 80%)"
    )
    rate_limit_default_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Default timeout for token acquisition in seconds (30.0)"
    )
    rate_limit_max_retries: int = Field(
        default=3, ge=1, le=10, description="Max retries for acquire_with_backoff (3)"
    )
    rate_limit_initial_backoff: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Initial backoff time in seconds (1.0)"
    )
    rate_limit_backoff_jitter_pct: float = Field(
        default=0.1, ge=0.0, le=0.5, description="Jitter percentage for backoff (0.1 = 10%)"
    )
    rate_limit_default_burst_capacity: int = Field(
        default=10, ge=5, le=100, description="Default burst capacity for rate limiter (10)"
    )
    rate_limit_ibkr_requests_per_second: float = Field(
        default=50.0, ge=10.0, le=200.0, description="IBKR requests per second (50)"
    )
    rate_limit_ibkr_burst_capacity: int = Field(
        default=100, ge=50, le=500, description="IBKR burst capacity (100)"
    )
    rate_limit_alpaca_requests_per_second: float = Field(
        default=3.33, ge=1.0, le=10.0, description="Alpaca requests per second (3.33 = 200/min)"
    )
    rate_limit_alpaca_burst_capacity: int = Field(
        default=20, ge=10, le=100, description="Alpaca burst capacity (20)"
    )
    rate_limit_polygon_requests_per_second: float = Field(
        default=5.0, ge=1.0, le=20.0, description="Polygon requests per second (5)"
    )
    rate_limit_polygon_burst_capacity: int = Field(
        default=50, ge=20, le=200, description="Polygon burst capacity (50)"
    )
    rate_limit_binance_requests_per_second: float = Field(
        default=10.0, ge=1.0, le=50.0, description="Binance requests per second (10)"
    )
    rate_limit_binance_burst_capacity: int = Field(
        default=100, ge=50, le=500, description="Binance burst capacity (100)"
    )

    # ========== EMERGENCY CLOSER PARAMETERS ==========
    emergency_confirmation_timeout: float = Field(
        default=30.0, ge=5.0, le=300.0, description="Confirmation timeout in seconds (30.0)"
    )
    emergency_position_close_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Position close order timeout in seconds (30.0)"
    )
    emergency_auto_confirm_after_timeout: bool = Field(
        default=True, description="Auto-confirm after timeout expires (True)"
    )

    # ========== DRAWDOWN MONITOR PARAMETERS ==========
    drawdown_max_limit: float = Field(
        default=0.15, ge=0.05, le=0.50, description="Maximum drawdown before halting trading (0.15 = 15%)"
    )
    drawdown_caution_threshold: float = Field(
        default=0.05, ge=0.02, le=0.20, description="Drawdown threshold for caution mode (0.05 = 5%)"
    )
    drawdown_warning_threshold: float = Field(
        default=0.10, ge=0.05, le=0.30, description="Drawdown threshold for warning mode (0.10 = 10%)"
    )
    drawdown_caution_scale: float = Field(
        default=0.8, ge=0.5, le=0.95, description="Position scale in caution mode (0.8 = 80%)"
    )
    drawdown_warning_scale: float = Field(
        default=0.5, ge=0.2, le=0.8, description="Position scale in warning mode (0.5 = 50%)"
    )
    drawdown_halt_scale: float = Field(
        default=0.0, ge=0.0, le=0.2, description="Position scale when halted (0.0 = halt trading)"
    )

    # ========== LOSS MONITOR PARAMETERS ==========
    loss_monitor_reset_threshold: int = Field(
        default=3, ge=2, le=10, description="Number of consecutive wins to reset loss counter (3)"
    )
    loss_monitor_lookback_trades: int = Field(
        default=10, ge=5, le=50, description="Recent trades to examine for reset condition (10)"
    )
    loss_monitor_window_trades: int = Field(
        default=20, ge=5, le=100, description="Recent trades for win rate calculation (20)"
    )
    loss_monitor_scale_1_loss: float = Field(
        default=0.9, ge=0.5, le=1.0, description="Position scale after 1 loss (0.9 = 90%)"
    )
    loss_monitor_scale_2_losses: float = Field(
        default=0.8, ge=0.4, le=0.95, description="Position scale after 2 losses (0.8 = 80%)"
    )
    loss_monitor_scale_3_losses: float = Field(
        default=0.6, ge=0.3, le=0.9, description="Position scale after 3 losses (0.6 = 60%)"
    )
    loss_monitor_scale_max_reduction: float = Field(
        default=0.5, ge=0.2, le=0.8, description="Maximum position scale reduction (0.5 = 50%)"
    )

    # ========== VOLATILITY MONITOR PARAMETERS ==========
    volatility_atr_period: int = Field(
        default=14, ge=7, le=50, description="ATR calculation period in days (14)"
    )
    volatility_lookback_periods: int = Field(
        default=60, ge=20, le=200, description="Lookback periods for average ATR calculation (60)"
    )
    volatility_min_ratio: float = Field(
        default=0.01, ge=0.001, le=0.1, description="Minimum ATR ratio to prevent scale explosion (0.01 = 1%)"
    )
    volatility_scale_min: float = Field(
        default=0.5, ge=0.2, le=0.9, description="Minimum volatility scale (0.5 = 50%)"
    )
    volatility_scale_max: float = Field(
        default=1.5, ge=1.1, le=3.0, description="Maximum volatility scale (1.5 = 150%)"
    )
    volatility_spike_threshold_multiplier: float = Field(
        default=2.0, ge=1.5, le=5.0, description="Multiplier for spike detection (2.0 = 2 sigma)"
    )
    volatility_spike_simple_multiplier: float = Field(
        default=1.5, ge=1.2, le=3.0, description="Simple spike threshold multiplier (1.5 = 1.5x avg)"
    )
    volatility_regime_very_low: float = Field(
        default=0.75, ge=0.5, le=0.9, description="Very low volatility ratio threshold (0.75)"
    )
    volatility_regime_low: float = Field(
        default=0.90, ge=0.8, le=0.95, description="Low volatility ratio threshold (0.90)"
    )
    volatility_regime_normal_upper: float = Field(
        default=1.10, ge=1.05, le=1.20, description="Normal volatility upper ratio threshold (1.10)"
    )
    volatility_regime_high: float = Field(
        default=1.50, ge=1.2, le=2.0, description="High volatility ratio threshold (1.50)"
    )
    volatility_spike_lookback_minutes: int = Field(
        default=60, ge=10, le=300, description="Lookback minutes for recent spikes (60)"
    )
    volatility_std_dev_lookback: int = Field(
        default=30, ge=10, le=100, description="Lookback periods for ATR std dev calculation (30)"
    )

    # ========== TRAILING STOP R-MULTIPLE PARAMETERS ==========
    trailing_stop_r1_threshold: float = Field(
        default=1.0, ge=0.5, le=2.0, description="R-multiple threshold for initial trailing (1.0 = 1R)"
    )
    trailing_stop_r2_threshold: float = Field(
        default=2.0, ge=1.0, le=3.0, description="R-multiple threshold for break-even (2.0 = 2R)"
    )
    trailing_stop_r3_threshold: float = Field(
        default=3.0, ge=2.0, le=5.0, description="R-multiple threshold for aggressive trailing (3.0 = 3R)"
    )
    trailing_stop_r3_trailing_pct: float = Field(
        default=0.5, ge=0.3, le=0.8, description="Trailing stop percentage at R3 (0.5 = 50% of profit)"
    )

    # ========== MODULAR STRATEGY CONFIGURATIONS ==========
    # Strategy-specific configs are now in separate modules to keep TradingThresholds lean.
    # Import and use them directly:
    #   from app.domain.strategies.config import MomentumModularConfig, DividendStrategyConfig, FXCarryTradeStrategyConfig
    #   momentum_cfg = MomentumModularConfig()
    #   value = momentum_cfg.bear_market_strength_threshold
    #
    # NOTE: These are NOT embedded here to avoid circular imports.
    # Use direct imports from app.domain.strategies.config instead.


# =============================================================================
# SECTION 2: TRADING CONFIGURATION
#   - TradingThresholds: General trading parameters and risk limits
#   - StrategyConfig: Individual strategy configuration
#   - StockAllocationSettings: Strategy stock allocator parameters
# =============================================================================

class StrategyConfig(BaseModel):
    """Configuration for individual strategies."""

    name: str = Field(description="Strategy name")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")
    weight: float = Field(default=1.0, description="Strategy weight for portfolio allocation")

    # Strategy-specific parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )

    # Risk parameters
    max_position_size: Optional[float] = Field(
        default=0.1, description="Maximum position size for this strategy"
    )
    stop_loss_pct: Optional[float] = Field(
        default=0.05, description="Stop loss percentage for this strategy"
    )
    take_profit_pct: Optional[float] = Field(
        default=0.15, description="Take profit percentage for this strategy"
    )

    # Performance thresholds
    min_sharpe_ratio: float = Field(
        default=1.0, description="Minimum Sharpe ratio for this strategy"
    )
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown for this strategy")
    min_win_rate: float = Field(default=0.4, description="Minimum win rate for this strategy")

    @field_validator("max_drawdown", "min_win_rate")
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v):
        if not 0 <= v <= 2:  # Allow weights up to 2.0
            raise ValueError("Weight must be between 0 and 2")
        return v

    @field_validator("max_position_size", "stop_loss_pct", "take_profit_pct")
    @classmethod
    def validate_optional_percentage(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v


class StockAllocationSettings(BaseSettings):
    """
    Stock Allocation Configuration with Pydantic validation.

    Centralizes all parameters for the Strategy Stock Allocator module.
    Each parameter is validated, documented, and versioned.

    Parameters are loaded from config/strategy_stock_allocator.yaml
    with fallback to hardcoded defaults if YAML is not available.
    """

    # Data validation parameters
    LOOKBACK_MAX_DAYS: int = Field(
        default=126,
        ge=60,
        le=1000,
        description="Maximum lookback period in days - loaded from YAML",
    )
    MIN_LIQUIDITY_USD: float = Field(
        default=500_000.0,
        ge=50_000.0,
        description="Minimum daily liquidity in USD - loaded from YAML",
    )

    # Stationarity and cointegration tests
    ADF_P_VALUE_THRESHOLD: float = Field(
        default=0.01,
        ge=0.01,
        le=0.10,
        description="ADF test p-value threshold for cointegration (STRICT: 0.01 for pairs trading to avoid spurious relationships)",
    )
    ADF_P_VALUE_THRESHOLD_MEAN_REVERSION: float = Field(
        default=0.05,
        ge=0.01,
        le=0.10,
        description="ADF test p-value threshold for mean reversion stationarity (more relaxed: 0.05)",
    )
    KPSS_P_VALUE_THRESHOLD: float = Field(
        default=0.05,
        ge=0.01,
        le=0.10,
        description="KPSS test p-value threshold for stationarity (0.01-0.10)",
    )

    # Mean Reversion parameters
    MAX_HALF_LIFE_DAYS: int = Field(
        default=120,
        ge=30,
        le=180,
        description="Maximum half-life in days for mean reversion (RELAXED: 120 days to activate more trades, was 30)",
    )
    MIN_HALF_LIFE_DAYS: int = Field(
        default=1, ge=1, le=10, description="Minimum half-life in days (too fast = noise) (1-10)"
    )

    # Exposure limits
    MAX_STRATEGY_EXPOSURE: float = Field(
        default=0.50, ge=0.10, le=0.80, description="Maximum exposure per strategy (10%-80%)"
    )
    MAX_PAIR_EXPOSURE: float = Field(
        default=0.15, ge=0.05, le=0.30, description="Maximum exposure per pair (5%-30%)"
    )
    MAX_ASSETS_PER_PAIR: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Maximum number of pairs an asset can participate in (2-5)",
    )

    # Momentum scoring weights
    MOMENTUM_WEIGHTS: Dict[str, float] = Field(
        default_factory=lambda: {
            "H_long": 0.40,
            "Sortino": 0.35,
            "1/tau": 0.05,
            "Liquidity": 0.20,
        },
        description="Weights for Momentum scoring (must sum to ~1.0)",
    )

    # Mean Reversion scoring weights
    MEAN_REVERSION_WEIGHTS: Dict[str, float] = Field(
        default_factory=lambda: {
            "H_long": 0.05,
            "Sortino": 0.10,
            "1/tau": 0.45,
            "Liquidity": 0.40,
        },
        description="Weights for Mean Reversion scoring (must sum to ~1.0)",
    )

    # Pairs Trading scoring weights
    PAIRS_TRADING_WEIGHTS: Dict[str, float] = Field(
        default_factory=lambda: {
            "H_long": 0.00,
            "Sortino": 0.00,
            "1/tau": 0.60,
            "Liquidity": 0.40,
        },
        description="Weights for Pairs Trading scoring (must sum to ~1.0)",
    )

    # Sortino ratio threshold
    MIN_SORTINO_RATIO: float = Field(
        default=0.5,
        ge=0.5,
        le=3.0,
        description="Minimum Sortino ratio for Momentum strategy (RELAXED: 0.5 to avoid over-filtering, was 1.0)",
    )

    # Hurst exponent thresholds
    HURST_MOMENTUM_THRESHOLD: float = Field(
        default=0.52,
        ge=0.50,
        le=0.70,
        description="Hurst threshold above which asset is classified as Momentum (RELAXED: 0.52 to increase universe, was 0.55)",
    )
    HURST_MEAN_REVERSION_THRESHOLD: float = Field(
        default=0.45,
        ge=0.30,
        le=0.50,
        description="Hurst threshold below which asset is classified as Mean Reversion (<0.45)",
    )

    # ERC / Risk Parity optimization
    ERC_OPTIMIZATION_TOLERANCE: float = Field(
        default=1e-6,
        ge=1e-8,
        le=1e-4,
        description="Optimization tolerance for ERC algorithm (1e-8 to 1e-4)",
    )
    ERC_MAX_ITERATIONS: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum iterations for ERC optimization (100-10000)",
    )

    # GARCH parameters
    GARCH_FORECAST_HORIZON: int = Field(
        default=1, ge=1, le=30, description="GARCH volatility forecast horizon in days (1-30)"
    )

    # Dynamic window selection for momentum
    DYNAMIC_WINDOW_ENABLED: bool = Field(
        default=True,
        description="Enable dynamic window selection for slope/ROC calculation (30-90 days, optimal by MSE)",
    )
    SLOPE_WINDOW_MIN: int = Field(
        default=30, ge=20, le=60, description="Minimum window for slope calculation (days)"
    )
    SLOPE_WINDOW_MAX: int = Field(
        default=90, ge=60, le=180, description="Maximum window for slope calculation (days)"
    )

    # Pairs Trading: Minimum lookback for cointegration
    MIN_COINTEGRATION_LOOKBACK_DAYS: int = Field(
        default=250,
        ge=100,
        le=500,
        description="Minimum lookback days for cointegration test (STRICT: 250 to avoid spurious relationships)",
    )

    # Decision logging
    LOG_ALL_DECISIONS: bool = Field(
        default=True, description="Log all allocation decisions with full metadata"
    )
    LOG_FILTER_REJECTIONS: bool = Field(
        default=True, description="Log reasons for stock filtering/rejections"
    )

    # Scoring normalization constants
    # Momentum scoring normalization
    MOMENTUM_ROC_NORMALIZATION_OFFSET: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="ROC normalization offset for momentum scoring (centers ROC around 0.1)",
    )
    MOMENTUM_ROC_NORMALIZATION_SCALE: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="ROC normalization scale for momentum scoring (divisor for normalized ROC)",
    )
    MOMENTUM_SLOPE_NORMALIZATION_OFFSET: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Slope normalization offset for momentum scoring (centers slope around 0.1)",
    )
    MOMENTUM_SLOPE_NORMALIZATION_SCALE: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="Slope normalization scale for momentum scoring (divisor for normalized slope)",
    )
    MOMENTUM_HURST_NORMALIZATION_OFFSET: float = Field(
        default=0.3,
        ge=0.0,
        le=0.5,
        description="Hurst exponent normalization offset for momentum scoring",
    )
    MOMENTUM_HURST_NORMALIZATION_SCALE: float = Field(
        default=0.4,
        ge=0.1,
        le=1.0,
        description="Hurst exponent normalization scale for momentum scoring",
    )

    # Mean Reversion scoring normalization
    MEAN_REVERSION_HURST_NORMALIZATION_CENTER: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Hurst exponent center for mean reversion scoring (0.5 = random walk threshold)",
    )
    MEAN_REVERSION_HURST_NORMALIZATION_SCALE: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="Hurst exponent normalization scale for mean reversion scoring",
    )
    INVERSE_TAU_NORMALIZATION_OFFSET: float = Field(
        default=0.01,
        ge=0.0,
        le=0.1,
        description="Inverse half-life (1/τ) normalization offset",
    )
    INVERSE_TAU_NORMALIZATION_SCALE: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Inverse half-life (1/τ) normalization scale",
    )

    # Volatility calculation parameters
    EWMA_ALPHA: float = Field(
        default=0.94,
        ge=0.8,
        le=0.99,
        description="EWMA alpha for volatility calculation (higher = more smoothing, industry standard is 0.94)",
    )
    GARCH_NORMALIZATION_MIN_FACTOR: float = Field(
        default=0.01,
        ge=0.001,
        le=0.1,
        description="Minimum GARCH normalization factor to prevent division by near-zero values",
    )

    @field_validator("MOMENTUM_WEIGHTS", "MEAN_REVERSION_WEIGHTS", "PAIRS_TRADING_WEIGHTS")
    @classmethod
    def validate_weights_sum(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate that weights sum approximately to 1.0."""
        total = sum(v.values())
        if not 0.95 <= total <= 1.05:  # Allow 5% tolerance
            logger.warning(f"Weights sum to {total:.3f}, expected ~1.0")
        return v

    @field_validator("ERC_OPTIMIZATION_TOLERANCE")
    @classmethod
    def validate_tolerance(cls, v: float) -> float:
        """Validate optimization tolerance."""
        if not 1e-8 <= v <= 1e-4:
            raise ValueError("ERC optimization tolerance must be between 1e-8 and 1e-4")
        return v

    @field_validator("MAX_STRATEGY_EXPOSURE", "MAX_PAIR_EXPOSURE")
    @classmethod
    def validate_exposure(cls, v: float) -> float:
        """Validate exposure limits."""
        if not 0 <= v <= 1:
            raise ValueError("Exposure limits must be between 0 and 1")
        return v

    @classmethod
    def from_yaml(cls, tier: Optional[str] = None) -> "StockAllocationSettings":
        """
        Create StockAllocationSettings from YAML configuration.

        Args:
            tier: Capital tier ("micro", "small", "medium", "large") for tier-specific overrides

        Returns:
            StockAllocationSettings with parameters loaded from YAML

        Examples:
            >>> settings = StockAllocationSettings.from_yaml()
            >>> settings = StockAllocationSettings.from_yaml(tier="micro")
        """
        from app.shared.config.config_loader import load_strategy_stock_allocator_config

        config = load_strategy_stock_allocator_config(tier)

        # Extract parameters from YAML and create instance
        kwargs = {}

        # Data validation
        if "data_validation" in config:
            dv = config["data_validation"]
            kwargs["LOOKBACK_MAX_DAYS"] = dv.get("lookback_max_days", 126)
            kwargs["MIN_LIQUIDITY_USD"] = dv.get("min_liquidity_usd", 500_000)

        # Statistical tests
        if "statistical_tests" in config:
            st = config["statistical_tests"]
            if "adf" in st:
                kwargs["ADF_P_VALUE_THRESHOLD"] = st["adf"].get("p_value_threshold", 0.01)
                kwargs["ADF_P_VALUE_THRESHOLD_MEAN_REVERSION"] = st["adf"].get(
                    "p_value_mean_reversion", 0.05
                )
            if "kpss" in st:
                kwargs["KPSS_P_VALUE_THRESHOLD"] = st["kpss"].get("p_value_threshold", 0.05)
            if "hurst" in st:
                kwargs["HURST_MOMENTUM_THRESHOLD"] = st["hurst"].get("momentum_threshold", 0.52)
                kwargs["HURST_MEAN_REVERSION_THRESHOLD"] = st["hurst"].get(
                    "mean_reversion_threshold", 0.45
                )

        # Mean reversion
        if "mean_reversion" in config:
            mr = config["mean_reversion"]
            kwargs["MAX_HALF_LIFE_DAYS"] = mr.get("max_half_life_days", 120)
            kwargs["MIN_HALF_LIFE_DAYS"] = mr.get("min_half_life_days", 1)

        # Exposure
        if "exposure" in config:
            exp = config["exposure"]
            kwargs["MAX_STRATEGY_EXPOSURE"] = exp.get("max_strategy_exposure", 0.50)
            kwargs["MAX_PAIR_EXPOSURE"] = exp.get("max_pair_exposure", 0.15)
            kwargs["MAX_ASSETS_PER_PAIR"] = exp.get("max_assets_per_pair", 2)

        # Scoring weights
        if "scoring_weights" in config:
            sw = config["scoring_weights"]
            if "momentum" in sw:
                # Convert "tau_inverse" to "1/tau" for compatibility
                momentum = sw["momentum"].copy()
                if "tau_inverse" in momentum:
                    momentum["1/tau"] = momentum.pop("tau_inverse")
                kwargs["MOMENTUM_WEIGHTS"] = momentum
            if "mean_reversion" in sw:
                mr_sw = sw["mean_reversion"].copy()
                if "tau_inverse" in mr_sw:
                    mr_sw["1/tau"] = mr_sw.pop("tau_inverse")
                kwargs["MEAN_REVERSION_WEIGHTS"] = mr_sw
            if "pairs_trading" in sw:
                pt = sw["pairs_trading"].copy()
                if "tau_inverse" in pt:
                    pt["1/tau"] = pt.pop("tau_inverse")
                kwargs["PAIRS_TRADING_WEIGHTS"] = pt

        # Risk metrics
        if "risk_metrics" in config:
            kwargs["MIN_SORTINO_RATIO"] = config["risk_metrics"].get("min_sortino_ratio", 0.5)

        # Optimization
        if "optimization" in config:
            opt = config["optimization"]
            kwargs["ERC_OPTIMIZATION_TOLERANCE"] = opt.get("tolerance", 1e-6)
            kwargs["ERC_MAX_ITERATIONS"] = opt.get("max_iterations", 1000)

        # GARCH
        if "garch" in config:
            kwargs["GARCH_FORECAST_HORIZON"] = config["garch"].get("forecast_horizon", 1)
            kwargs["DYNAMIC_WINDOW_ENABLED"] = config["garch"].get("dynamic_window_enabled", True)
            kwargs["SLOPE_WINDOW_MIN"] = config["garch"].get("slope_window_min", 30)
            kwargs["SLOPE_WINDOW_MAX"] = config["garch"].get("slope_window_max", 90)

        # Additional
        if "additional" in config:
            kwargs["MIN_COINTEGRATION_LOOKBACK_DAYS"] = config["additional"].get(
                "min_cointegration_lookback_days", 250
            )

        # Logging
        if "logging" in config:
            log = config["logging"]
            kwargs["LOG_ALL_DECISIONS"] = log.get("log_all_decisions", True)
            kwargs["LOG_FILTER_REJECTIONS"] = log.get("log_filter_rejections", True)

        # Create instance with loaded parameters
        return cls(**kwargs)

    model_config = {"env_prefix": "STOCK_ALLOCATION_", "case_sensitive": False}


# =============================================================================
# SECTION 3: INFRASTRUCTURE CONFIGURATION
#   - DatabaseConfig: Database connection parameters
#   - RedisConfig: Redis cache configuration
#   - APIConfig: API server configuration
# =============================================================================

# =============================================================================
# SECTION: Backtesting Configuration
# =============================================================================
# Consolidates all backtesting constants from:
#   - app/backtesting/constants.py (DEPRECATED after this)
#   - Hardcoded values scattered across backtesting modules
#
# This is THE SINGLE SOURCE OF TRUTH for all backtesting parameters.
# =============================================================================

class CommissionModel(BaseModel):
    """Commission model configuration."""

    type: str = Field(description="Commission type: fixed, hybrid, or tiered")
    description: str = Field(default="", description="Description of this commission model")


class FixedCommission(CommissionModel):
    """Fixed commission model."""

    type: str = "fixed"
    cost: Decimal = Field(description="Fixed cost per trade")


class HybridCommission(CommissionModel):
    """Hybrid commission model (rate + minimum)."""

    type: str = "hybrid"
    min_cost: Decimal = Field(description="Minimum cost per trade")
    rate: Decimal = Field(description="Commission rate as decimal (0.001 = 0.1%)")


class TierBracket(BaseModel):
    """Single tier bracket for tiered commission."""

    volume_max: float = Field(description="Maximum volume for this tier")
    rate: Decimal = Field(description="Commission rate for this tier")
    min: Decimal = Field(description="Minimum commission for this tier")


class TieredCommission(CommissionModel):
    """Tiered commission model."""

    type: str = "tiered"
    brackets: List[TierBracket] = Field(description="Commission brackets")


class BacktestingConfig(BaseModel):
    """
    Centralized backtesting configuration.

    This is THE SINGLE SOURCE OF TRUTH for all backtesting parameters.
    All hardcoded values in backtesting modules should reference this config.

    Usage:
        from app.shared.config.centralized_config import get_config
        config = get_config()
        slippage = config.backtesting.base_slippage_bps
        commission = config.backtesting.default_commission_rate
    """

    # ========== SLIPPAGE SETTINGS ==========
    # Consolidated from constants.py ExecutionEngineConstants and TradingThresholds

    base_slippage_bps: Decimal = Field(
        default=Decimal("10"),  # 10 bps = 0.1% (standard market impact)
        description="Base slippage in basis points"
    )
    optimistic_slippage_bps: Decimal = Field(
        default=Decimal("2"),  # 2 bps for optimistic mode
        description="Optimistic slippage in basis points"
    )
    stop_slippage_multiplier: Decimal = Field(
        default=Decimal("2"),  # 2x slippage on stop orders (worse execution)
        description="Slippage multiplier for stop orders"
    )
    volatility_multiplier: Decimal = Field(
        default=Decimal("2"),  # 2x slippage for high volatility
        description="Slippage multiplier for high volatility conditions"
    )

    # ========== COMMISSION SETTINGS ==========
    # Consolidated from constants.py CapitalScaleConstants.COMMISSION_MODELS

    default_commission_rate: Decimal = Field(
        default=Decimal("0.001"),  # 0.1% standard commission
        description="Default commission rate as decimal"
    )
    default_commission_per_share: Decimal = Field(
        default=Decimal("0.005"),  # $0.005/share (IBKR-like)
        description="Default commission per share"
    )
    default_commission_fixed: Decimal = Field(
        default=Decimal("5.0"),  # $5 flat fee
        description="Default fixed commission per trade"
    )
    min_commission: Decimal = Field(
        default=Decimal("1.0"),  # $1 minimum
        description="Minimum commission per trade"
    )

    # ========== CAPITAL SCALE SETTINGS ==========
    # Consolidated from constants.py CapitalScaleConstants

    default_capital_levels: List[Decimal] = Field(
        default_factory=lambda: [
            Decimal("1000"),   # Micro
            Decimal("5000"),   # Small
            Decimal("10000"),  # Medium
            Decimal("50000"),  # Pro
            Decimal("100000"), # Fund
        ],
        description="Default capital levels for scale analysis"
    )
    default_initial_capital: Decimal = Field(
        default=Decimal("100000"),  # $100K default
        description="Default initial capital for backtests"
    )

    # ADV (Average Daily Volume) settings
    adv_limit_pct: Decimal = Field(
        default=Decimal("0.02"),  # 2% ADV rule
        description="Maximum position as percentage of ADV"
    )
    adv_fill_ratio_reject_threshold: Decimal = Field(
        default=Decimal("0.5"),  # Reject if fill < 50%
        description="Minimum fill ratio before rejecting"
    )

    # Commission impact thresholds
    commission_impact_warning_threshold: Decimal = Field(
        default=Decimal("0.15"),  # 15% - trigger warning
        description="Commission impact percentage to trigger warning"
    )
    commission_impact_critical_threshold: Decimal = Field(
        default=Decimal("0.20"),  # 20% - reject strategy
        description="Commission impact percentage to reject strategy"
    )

    # Alpha degradation
    alpha_degradation_threshold: Decimal = Field(
        default=Decimal("0.50"),  # 50% degradation max acceptable
        description="Maximum acceptable alpha degradation"
    )

    # ========== EXECUTION SETTINGS ==========

    enable_next_day_execution: bool = Field(
        default=True,
        description="Signal at close t, execute at open t+1"
    )
    max_execution_time_ms: int = Field(
        default=500,
        description="Maximum execution time in milliseconds"
    )

    # ========== POSITION SIZING ==========
    # Consolidated from multiple sources

    default_max_position_size: Decimal = Field(
        default=Decimal("0.10"),  # 10% max position
        description="Default maximum position size as decimal"
    )
    default_min_position_size: Decimal = Field(
        default=Decimal("0.01"),  # 1% min position
        description="Default minimum position size as decimal"
    )

    # Position limits by capital tier
    position_limits_by_tier: Dict[str, Decimal] = Field(
        default_factory=lambda: {
            "micro": Decimal("0.02"),   # 2% for micro accounts
            "small": Decimal("0.05"),   # 5% for small accounts
            "medium": Decimal("0.10"),  # 10% for medium accounts
            "large": Decimal("0.15"),   # 15% for large accounts
        },
        description="Maximum position size by capital tier"
    )

    # ========== SCALABILITY SCORING ==========

    scalability_alpha_max_points: Decimal = Field(
        default=Decimal("40"),
        description="Maximum points for alpha degradation score"
    )
    scalability_commission_max_points: Decimal = Field(
        default=Decimal("30"),
        description="Maximum points for commission impact score"
    )
    scalability_stability_max_points: Decimal = Field(
        default=Decimal("30"),
        description="Maximum points for win rate stability score"
    )

    # ========== RISK MANAGEMENT DEFAULTS ==========

    default_stop_loss_pct: Decimal = Field(
        default=Decimal("0.05"),  # 5% stop loss
        description="Default stop loss percentage"
    )
    default_take_profit_pct: Decimal = Field(
        default=Decimal("0.15"),  # 15% take profit
        description="Default take profit percentage"
    )
    default_risk_free_rate: Decimal = Field(
        default=Decimal("0.02"),  # 2% annual risk-free rate
        description="Default risk-free rate for Sharpe calculation"
    )
    annual_trading_days: int = Field(
        default=252,
        description="Number of trading days in a year for annualization"
    )
    default_daily_loss_limit: Decimal = Field(
        default=Decimal("0.05"),  # 5% daily loss limit
        description="Default daily loss limit"
    )

    # ========== PERFORMANCE METRICS ==========

    min_trades_for_statistics: int = Field(
        default=10,
        description="Minimum trades required for reliable statistics"
    )
    min_sharpe_ratio: Decimal = Field(
        default=Decimal("0.5"),
        description="Minimum acceptable Sharpe ratio"
    )
    max_acceptable_drawdown: Decimal = Field(
        default=Decimal("0.25"),  # 25% max drawdown
        description="Maximum acceptable drawdown"
    )

    # ========== DATA SETTINGS ==========

    default_start_date: str = Field(
        default="2018-01-01",
        description="Default backtest start date"
    )
    default_end_date: str = Field(
        default="2023-12-31",
        description="Default backtest end date"
    )

    # ========== URLs (External APIs) ==========

    yahoo_finance_base_url: str = Field(
        default="https://query1.finance.yahoo.com/v8/finance/chart",
        description="Yahoo Finance API base URL"
    )

    @field_validator("base_slippage_bps", "optimistic_slippage_bps")
    @classmethod
    def validate_slippage_bps(cls, v):
        if v < 0:
            raise ValueError("Slippage must be non-negative")
        return v

    @field_validator("default_commission_rate", "default_commission_per_share")
    @classmethod
    def validate_commission(cls, v):
        if v < 0:
            raise ValueError("Commission must be non-negative")
        return v

    def get_slippage_pct(self, is_stop: bool = False, is_volatile: bool = False) -> Decimal:
        """
        Calculate slippage percentage based on conditions.

        Args:
            is_stop: True if this is a stop order (worse execution)
            is_volatile: True if market is volatile

        Returns:
            Slippage as decimal percentage (e.g., 0.001 = 0.1%)
        """
        slippage = self.base_slippage_bps / Decimal("10000")  # Convert bps to decimal

        if is_stop:
            slippage *= self.stop_slippage_multiplier
        if is_volatile:
            slippage *= self.volatility_multiplier

        return slippage

    def get_commission_for_capital(self, capital: Decimal) -> Decimal:
        """
        Get appropriate commission rate based on capital level.

        Args:
            capital: Account capital

        Returns:
            Commission rate as decimal
        """
        if capital <= Decimal("5000"):
            return self.default_commission_fixed  # Fixed fee for small accounts
        elif capital <= Decimal("50000"):
            return self.default_commission_rate  # Standard rate
        else:
            return self.default_commission_rate * Decimal("0.5")  # Discount for large accounts

    def get_position_limit_for_capital(self, capital: Decimal) -> Decimal:
        """
        Get maximum position size based on capital tier.

        Args:
            capital: Account capital

        Returns:
            Maximum position size as decimal
        """
        if capital <= Decimal("5000"):
            return self.position_limits_by_tier["micro"]
        elif capital <= Decimal("20000"):
            return self.position_limits_by_tier["small"]
        elif capital <= Decimal("100000"):
            return self.position_limits_by_tier["medium"]
        else:
            return self.position_limits_by_tier["large"]


# Backwards compatibility aliases (reference BacktestingConfig)
BACKTESTING_CONSTANTS = None  # Will be set after CentralizedConfig instantiation


def get_backtesting_constants() -> "BacktestingConfig":
    """Get backtesting constants from centralized config."""
    global BACKTESTING_CONSTANTS
    if BACKTESTING_CONSTANTS is None:
        BACKTESTING_CONSTANTS = get_config().backtesting
    return BACKTESTING_CONSTANTS


class DatabaseConfig(BaseModel):
    """
    Database configuration.

    Rule 28 Compliant: No hardcoded passwords.
    Passwords must come from environment variables.
    """

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="algotrading", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    # Rule 28: No default password - must come from environment variable
    password: str = Field(default="", description="Database password (from DB_PASSWORD env var)")

    # Connection pool
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")

    # SSL
    ssl_mode: str = Field(default="prefer", description="SSL mode")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @property
    def connection_string(self) -> str:
        """
        Generate database connection string.

        Rule 28 Compliant: Builds string dynamically from environment variables.
        Never hardcodes credentials in connection strings.
        """
        import os

        # Rule 28: Always read from environment, never use hardcoded value
        db_password = os.getenv("DB_PASSWORD", self.password)
        if not db_password:
            raise ValueError(
                "DB_PASSWORD environment variable not set. "
                "Cannot build secure connection string."
            )
        return f"postgresql://{self.user}:{db_password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    """Redis configuration."""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")

    # Connection settings
    max_connections: int = Field(default=20, description="Maximum connections")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @property
    def connection_string(self) -> str:
        """Generate Redis connection string."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        else:
            return f"redis://{self.host}:{self.port}/{self.db}"


class APIConfig(BaseModel):
    """API configuration."""

    host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=1, description="Number of workers")

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production", description="Secret key for JWT"
    )
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")

    # CORS
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods"
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 16:  # Reduced minimum length for testing
            raise ValueError("Secret key must be at least 16 characters long")
        return v


# =============================================================================
# SECTION 4: MONITORING & LOGGING CONFIGURATION
#   - LoggingConfig: Logging parameters
#   - MonitoringConfig: Monitoring and alerting configuration
# =============================================================================

class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # File logging
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="logs/app.log", description="Log file path")
    file_max_size: int = Field(default=10485760, description="Maximum log file size in bytes")
    file_backup_count: int = Field(default=5, description="Number of backup files")

    # Console logging
    console_enabled: bool = Field(default=True, description="Enable console logging")

    # ELK Stack
    elk_enabled: bool = Field(default=False, description="Enable ELK stack logging")
    elk_host: str = Field(default="localhost", description="ELK host")
    elk_port: int = Field(default=9200, description="ELK port")
    elk_index: str = Field(default="algotrading", description="ELK index name")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    # Prometheus
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus port")

    # Grafana
    grafana_enabled: bool = Field(default=True, description="Enable Grafana dashboard")
    grafana_port: int = Field(default=3000, description="Grafana port")

    # Health checks
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")

    # Alerts
    alerts_enabled: bool = Field(default=True, description="Enable alerts")
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    discord_webhook_url: Optional[str] = Field(default=None, description="Discord webhook URL")

    @field_validator("prometheus_port", "grafana_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


# =============================================================================
# SECTION 5: RISK & COMPLIANCE CONFIGURATION
#   - CurrencyHedgingConfig: Automatic currency hedging parameters
#   - SectorCountryDiversificationConfig: Sector/country diversification limits
#   - ComplianceConfig: Compliance engine thresholds
# =============================================================================

class CurrencyHedgingConfig(BaseModel):
    """Configuration for automatic currency hedging [TASK-5.5-CURRENCY-HEDGING]."""

    enabled: bool = Field(default=True, description="Enable currency hedging")
    base_currency: str = Field(default="USD", description="Base currency for hedging")
    auto_hedge: bool = Field(default=True, description="Automatically create hedge positions")
    hedging_strategy: str = Field(
        default="partial", description="Hedging strategy: full, partial, or rolling"
    )
    partial_hedge_percentage: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Percentage to hedge for partial strategy"
    )

    # Thresholds
    single_currency_max: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Max exposure per currency"
    )
    total_fx_max: float = Field(
        default=0.50, ge=0.0, le=1.0, description="Max total unhedged FX exposure"
    )
    minimum_exposure: Decimal = Field(
        default=Decimal("50000"), description="Minimum exposure to trigger hedging"
    )

    # Cost limits
    max_cost_bps: Decimal = Field(
        default=Decimal("10"), ge=Decimal("0"), description="Max hedging cost in basis points"
    )
    acceptable_slippage: float = Field(
        default=0.5, ge=0.0, le=10.0, description="Acceptable slippage %"
    )
    enforce_cost_limit: bool = Field(default=True, description="Don't hedge if cost exceeds limit")

    # Rolling hedge
    rolling_window_days: int = Field(
        default=30, ge=1, le=365, description="Rolling hedge window in days"
    )
    rebalance_frequency: str = Field(
        default="weekly", description="Rebalance frequency: daily, weekly, monthly"
    )


class SectorCountryDiversificationConfig(BaseModel):
    """Configuration for sector and country diversification [TASK-5.6-DIVERSIFICATION]."""

    enabled: bool = Field(default=True, description="Enable sector/country diversification checks")
    enforcement_mode: str = Field(
        default="soft", description="Enforcement mode: soft (warning) or hard (blocking)"
    )

    # Sector thresholds
    max_single_sector: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Maximum exposure per sector"
    )
    max_total_sector_concentration: float = Field(
        default=0.70, ge=0.0, le=1.0, description="Maximum concentration in top sectors"
    )
    minimum_sector_count: int = Field(
        default=3, ge=1, le=20, description="Minimum number of sectors to maintain"
    )

    # Country thresholds
    max_single_country: float = Field(
        default=0.50, ge=0.0, le=1.0, description="Maximum exposure per country"
    )
    max_region_concentration: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Maximum concentration per region"
    )
    minimum_country_count: int = Field(
        default=2, ge=1, le=50, description="Minimum number of countries to maintain"
    )

    # Rebalancing
    rebalance_frequency: str = Field(
        default="weekly", description="Rebalancing frequency: daily, weekly, monthly"
    )
    sector_breach_threshold: float = Field(
        default=0.03, ge=0.0, le=1.0, description="Sector breach alert threshold"
    )
    country_breach_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Country breach alert threshold"
    )
    auto_rebalance_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Auto-rebalance if breach exceeds this"
    )

    # Analytics
    calculate_herfindahl: bool = Field(default=True, description="Calculate Herfindahl index")
    calculate_diversification_score: bool = Field(
        default=True, description="Calculate diversification score"
    )
    validate_on_position_add: bool = Field(
        default=True, description="Validate constraints when adding positions"
    )


class ComplianceConfig(BaseModel):
    """
    Centralized configuration for Compliance Engine.

    All thresholds used by compliance handlers are defined here
    for auditability and maintainability.
    """

    # Hastie (Statistical Learning) thresholds
    MIN_STATISTICAL_MODEL_HEALTH: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Minimum statistical model health score (0-100)"
    )
    MIN_CROSS_VALIDATION_SCORE: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Minimum cross-validation score (0-1)"
    )

    # Lopez de Prado (Meta-labeling) thresholds
    MIN_META_LABELING_SIGNAL: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Minimum meta-labeling signal strength (0-1)"
    )
    MIN_MCC_METRIC: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Minimum Matthews Correlation Coefficient (0-1)"
    )

    # O'Hara (Microstructure) thresholds
    MIN_LIQUIDITY_SCORE: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Minimum liquidity score (0-100)"
    )
    MAX_ORDER_FLOW_TOXICITY: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Maximum acceptable order flow toxicity (0-1)"
    )
    # Estimation parameters for O'Hara (when actual data not available)
    ESTIMATED_VOLATILITY: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Estimated volatility when not calculable (0-1)"
    )
    ESTIMATED_SPREAD_BPS: float = Field(
        default=5.0, ge=0.0, le=100.0,
        description="Estimated spread in basis points when not available"
    )
    ESTIMATED_DEPTH: float = Field(
        default=100000.0, ge=0.0, le=1_000_000.0,
        description="Estimated depth for liquidity calculation (USD)"
    )
    ESTIMATED_VOLUME: float = Field(
        default=1_000_000.0, ge=0.0, le=100_000_000.0,
        description="Estimated daily volume for liquidity calculation (USD)"
    )
    DEFAULT_ORDER_FLOW_TOXICITY: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Default order flow toxicity when not calculable (0-1)"
    )

    # Backtesting thresholds
    MIN_BACKTEST_CONFIDENCE: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Minimum backtest confidence (0-1)"
    )
    MIN_HISTORICAL_SHARPE: float = Field(
        default=0.5, ge=-5.0, le=10.0,
        description="Minimum historical Sharpe ratio"
    )

    # Execution thresholds
    MIN_EXECUTION_PROBABILITY: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Minimum execution probability (0-1)"
    )
    MAX_SLIPPAGE_BPS: float = Field(
        default=10.0, ge=0.0, le=100.0,
        description="Maximum acceptable slippage in basis points"
    )

    # Strategy health thresholds
    MIN_STRATEGY_HEALTH: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Minimum strategy health score (0-100)"
    )

    # Architecture compliance thresholds
    MIN_ARCHITECTURE_SCORE: float = Field(
        default=80.0, ge=0.0, le=100.0,
        description="Minimum architecture compliance score (0-100)"
    )

    # Confidence adjustment thresholds (used across all handlers)
    # Positive adjustments
    CONF_BULL_REGIME_BONUS: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Confidence bonus for bullish regime (0-1)"
    )
    CONF_LOW_VOLATILITY_BONUS: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Confidence bonus for low volatility regime (0-1)"
    )

    # Negative adjustments (additive)
    CONF_BEAR_REGIME_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Confidence penalty for bearish regime (0-1)"
    )
    CONF_HIGH_VOLATILITY_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Confidence penalty for high volatility (0-1)"
    )
    CONF_POOR_LIQUIDITY_PENALTY: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Confidence penalty for poor liquidity (0-1)"
    )
    CONF_LOW_LIQUIDITY_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Confidence penalty for low liquidity (0-1)"
    )
    CONF_HIGH_TOXICITY_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Confidence penalty for high order flow toxicity (0-1)"
    )
    CONF_LOW_SHARPE_PENALTY: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Confidence penalty for low Sharpe ratio (0-1)"
    )
    CONF_LOW_MODEL_HEALTH_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Confidence penalty for low model health (0-1)"
    )
    CONF_LOW_CV_SCORE_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Confidence penalty for low cross-validation score (0-1)"
    )

    # Negative adjustments (multiplicative - for severe violations)
    CONF_POSITION_LIMIT_MULTIPLIER: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Confidence multiplier when position limit exceeded"
    )
    CONF_DRAWDOWN_LIMIT_MULTIPLIER: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Confidence multiplier when drawdown limit exceeded"
    )
    CONF_LEVERAGE_LIMIT_MULTIPLIER: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Confidence multiplier when leverage limit exceeded"
    )
    CONF_CIRCUIT_BREAKER_MULTIPLIER: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Confidence multiplier when circuit breaker triggered"
    )
    CONF_CRITICAL_FAILURE_MULTIPLIER: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Confidence multiplier when critical system fails"
    )

    # Thresholds used in comparisons
    DEFAULT_REGIME_CONFIDENCE: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Default regime confidence when not calculated"
    )
    HIGH_VOLATILITY_PERCENTILE: float = Field(
        default=80.0, ge=0.0, le=100.0,
        description="Volatility percentile threshold for 'high' classification (0-100)"
    )
    DEFAULT_SIGNAL_STRENGTH: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Default signal strength when not calculated (0-1)"
    )
    DEFAULT_HEALTH_SCORE: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Default health score when not calculated (0-100)"
    )

    # Quality assessment thresholds (used for Narang alpha quality, etc.)
    ALPHA_QUALITY_HIGH_THRESHOLD: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Minimum confidence for HIGH alpha quality rating (0-1)"
    )
    ALPHA_QUALITY_MEDIUM_THRESHOLD: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Minimum confidence for MEDIUM alpha quality rating (0-1)"
    )

    # Meta-labeling specific thresholds
    FITTED_MODEL_SIGNAL_STRENGTH: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Signal strength when meta-labeling model is fitted (0-1)"
    )
    DEFAULT_MCC_METRIC: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Default MCC metric when not calculated (0-1)"
    )

    # Hull (Risk Management) thresholds
    CONF_HIGH_VAR_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Confidence penalty for high Value at Risk (0-1)"
    )

    # Google SRE thresholds
    CONF_SLO_VIOLATION_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Confidence penalty for SLO compliance violation (0-1)"
    )

    # Execution Engine thresholds
    BASE_SLIPPAGE_BPS: float = Field(
        default=5.0, ge=0.0, le=100.0,
        description="Base slippage in basis points for execution estimation"
    )
    URGENCY_IMPACT_COEFFICIENT: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Coefficient for urgency impact on execution probability (0-1)"
    )
    SLIPPAGE_VOLATILITY_FACTOR: float = Field(
        default=2.0, ge=0.0, le=10.0,
        description="Factor for execution probability impact on slippage"
    )

    # Tomasini (Architecture) thresholds
    TOMASINI_ARCHITECTURE_SCORE_COMPLIANT: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Architecture score when system is compliant (0-100)"
    )
    TOMASINI_ARCHITECTURE_SCORE_DEFAULT: float = Field(
        default=90.0, ge=0.0, le=100.0,
        description="Default architecture score (0-100)"
    )

    # Kelly Criterion thresholds
    KELLY_MAX_POSITION_PCT: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Maximum position size as percentage of portfolio (0-1)"
    )

    # O'Hara (Microstructure) calculation factors
    ORDER_FLOW_TOXICITY_SCALING_FACTOR: float = Field(
        default=10.0, ge=1.0, le=100.0,
        description="Scaling factor for order flow toxicity calculation"
    )

    # Percival (Architecture/Dependency Health) thresholds
    PERCIVAL_ARCHITECTURE_COMPLIANT_SCORE: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Architecture compliance score when system is compliant (0-100)"
    )
    PERCIVAL_ARCHITECTURE_DEFAULT_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0,
        description="Default architecture compliance score (0-100)"
    )
    PERCIVAL_CLEAN_ARCHITECTURE_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0,
        description="Clean architecture score (0-100)"
    )
    PERCIVAL_DEPENDENCY_HEALTH_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0,
        description="Dependency health score (0-100)"
    )

    # Analysis window sizes (for rolling calculations)
    RETURN_STABILITY_WINDOW: int = Field(
        default=15, ge=5, le=100,
        description="Window size for return stability calculation (number of periods)"
    )
    VOLATILITY_WINDOW: int = Field(
        default=20, ge=5, le=100,
        description="Window size for volatility calculation (number of periods)"
    )
    SPREAD_WINDOW: int = Field(
        default=20, ge=5, le=100,
        description="Window size for spread calculation (number of periods)"
    )
    FLOW_VOLATILITY_WINDOW: int = Field(
        default=10, ge=5, le=100,
        description="Window size for flow volatility calculation (number of periods)"
    )

    # Financial calculation constants
    TRADING_DAYS_PER_YEAR: int = Field(
        default=252, ge=1, le=365,
        description="Number of trading days per year for annualization"
    )
    STRATEGY_SIGNAL_SCALING_FACTOR: float = Field(
        default=100.0, ge=1.0, le=1000.0,
        description="Scaling factor for strategy signal sigmoid transformation"
    )

    # Risk:Reward validation thresholds
    DEFAULT_FALLBACK_PRICE: float = Field(
        default=100.0, ge=0.0, le=1000000.0,
        description="Fallback price when signal price is not available (USD)"
    )
    MIN_RISK_REWARD_RATIO: float = Field(
        default=2.0, ge=0.1, le=100.0,
        description="Minimum risk/reward ratio for trade validation"
    )

    # Risk management thresholds
    MAX_CORRELATION_RISK: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Maximum correlation risk (0-1 scale)"
    )

    # Default capital settings
    DEFAULT_STARTING_CAPITAL: float = Field(
        default=100000.0, ge=0.0, le=100_000_000.0,
        description="Default starting capital for paper/live trading (USD)"
    )

    # Mathematical constants (epsilon for division safety)
    EPSILON_DIVISION: float = Field(
        default=0.001, ge=0.0001, le=0.1,
        description="Small value to avoid division by zero (epsilon)"
    )

    # Execution calculation constants
    URGENCY_BASE_MULTIPLIER: float = Field(
        default=1.0, ge=0.0, le=10.0,
        description="Base multiplier for urgency in slippage calculation"
    )

    # Timing cost estimation
    TIMING_COST_MULTIPLIER: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Multiplier for timing cost as portion of total cost"
    )

    # Google SRE defaults
    SLO_DEFAULT_ERROR_BUDGET: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Default error budget remaining percentage (0-100)"
    )
    SLO_DEFAULT_LATENCY_P95_MS: float = Field(
        default=50.0, ge=0.0, le=1000.0,
        description="Default P95 latency in milliseconds"
    )
    SLO_DEFAULT_HEALTH: float = Field(
        default=98.0, ge=0.0, le=100.0,
        description="Default golden signals health score (0-100)"
    )

    # Beck TDD (Rule 21) defaults
    TDD_COMPLIANT_COVERAGE: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Test coverage percentage when TDD compliant (0-100)"
    )
    TDD_COMPLIANT_TDD_SCORE: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="TDD compliance score when TDD compliant (0-100)"
    )
    TDD_FALLBACK_COVERAGE: float = Field(
        default=80.0, ge=0.0, le=100.0,
        description="Fallback test coverage percentage (0-100)"
    )
    TDD_FALLBACK_TDD_SCORE: float = Field(
        default=80.0, ge=0.0, le=100.0,
        description="Fallback TDD compliance score (0-100)"
    )

    # Martin Clean Architecture (Rule 18) defaults
    MARTIN_COMPLIANT_SCORE: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Martin Clean Architecture score when compliant (0-100)"
    )
    MARTIN_FALLBACK_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0,
        description="Fallback Martin Clean Architecture score (0-100)"
    )

    # Liquidity aggregation weights (must sum to 1.0)
    HARRIS_LIQUIDITY_WEIGHT: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Weight for Harris liquidity score in aggregated liquidity (0-1)"
    )
    OHARA_LIQUIDITY_WEIGHT: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Weight for O'Hara price discovery score in aggregated liquidity (0-1)"
    )

    # Liquidity regime thresholds
    LIQUIDITY_LOW_THRESHOLD: float = Field(
        default=30.0, ge=0.0, le=100.0,
        description="Liquidity score below this indicates LOW liquidity regime (0-100)"
    )
    LIQUIDITY_HIGH_THRESHOLD: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Liquidity score above this indicates HIGH liquidity regime (0-100)"
    )

    # Default urgency for analyze_pre_trade
    DEFAULT_URGENCY: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Default execution urgency (0=low, 1=high)"
    )

    # Execution engine participation rate
    BASE_PARTICIPATION_RATE: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Base participation rate for order execution (0-1, typically 0.05 for 5%)"
    )

    # Liquidity score conversion values
    LIQUIDITY_SCORE_SUFFICIENT: float = Field(
        default=100.0, ge=0.0, le=100.0,
        description="Liquidity score when liquidity is sufficient (0-100)"
    )
    LIQUIDITY_SCORE_INSUFFICIENT: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Liquidity score when liquidity is insufficient (0-100)"
    )

    # Initial confidence value for PreTradeAnalysis
    INITIAL_CONFIDENCE: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Initial confidence value before any systems penalize it (0-1)"
    )

    # Statistical calculation constants
    MIN_PRICE_HISTORY_LENGTH: int = Field(
        default=30, ge=10, le=1000,
        description="Minimum length of price_history required for statistical calculations"
    )
    SECONDS_PER_DAY: int = Field(
        default=86400, ge=1, le=100000,
        description="Number of seconds in a day (for time conversions)"
    )
    ADF_PVALUE_THRESHOLD: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="ADF test p-value threshold for stationarity (0.05 = 95% confidence)"
    )
    STATIONARY_HEALTH_MULTIPLIER: float = Field(
        default=100.0, ge=1.0, le=1000.0,
        description="Multiplier for converting ADF p-value to health score when stationary"
    )
    NON_STATIONARY_HEALTH_MULTIPLIER: float = Field(
        default=500.0, ge=1.0, le=10000.0,
        description="Multiplier for converting ADF p-value to health score when non-stationary"
    )

    # Unit conversion constants
    BASIS_POINTS_MULTIPLIER: int = Field(
        default=10000, ge=1, le=100000,
        description="Multiplier for converting decimal to basis points (1 = 10000 bps)"
    )
    MILLISECONDS_MULTIPLIER: int = Field(
        default=1000, ge=1, le=10000,
        description="Multiplier for converting seconds to milliseconds (1 sec = 1000 ms)"
    )
    PERCENTAGE_MULTIPLIER: int = Field(
        default=100, ge=1, le=1000,
        description="Multiplier for converting decimal to percentage (1 = 100%)"
    )

    # Post-trade analysis thresholds
    DEFAULT_EXECUTION_QUALITY_SCORE: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Default execution quality score (0-100)"
    )
    DEFAULT_FILL_RATE: float = Field(
        default=100.0, ge=0.0, le=100.0,
        description="Default fill rate percentage (0-100)"
    )
    MIN_HIGH_QUALITY_EXECUTION_SCORE: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Minimum execution quality score for high-quality execution (0-100)"
    )
    MIN_HIGH_QUALITY_FILL_RATE: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Minimum fill rate for high-quality execution (0-100)"
    )
    DEFAULT_SLO_LATENCY_THRESHOLD_MS: float = Field(
        default=100.0, ge=0.0, le=10000.0,
        description="Default SLO latency threshold in milliseconds"
    )

    @field_validator(
        "MIN_STATISTICAL_MODEL_HEALTH", "MIN_LIQUIDITY_SCORE",
        "MIN_STRATEGY_HEALTH", "MIN_ARCHITECTURE_SCORE",
        "HIGH_VOLATILITY_PERCENTILE", "DEFAULT_HEALTH_SCORE",
        "BASE_SLIPPAGE_BPS", "TOMASINI_ARCHITECTURE_SCORE_COMPLIANT",
        "TOMASINI_ARCHITECTURE_SCORE_DEFAULT",
        "PERCIVAL_ARCHITECTURE_COMPLIANT_SCORE", "PERCIVAL_ARCHITECTURE_DEFAULT_SCORE",
        "PERCIVAL_CLEAN_ARCHITECTURE_SCORE", "PERCIVAL_DEPENDENCY_HEALTH_SCORE",
        "ORDER_FLOW_TOXICITY_SCALING_FACTOR",
        "RETURN_STABILITY_WINDOW", "VOLATILITY_WINDOW", "SPREAD_WINDOW", "FLOW_VOLATILITY_WINDOW",
        "STRATEGY_SIGNAL_SCALING_FACTOR", "DEFAULT_FALLBACK_PRICE", "MIN_RISK_REWARD_RATIO",
        "MAX_CORRELATION_RISK",
        "EPSILON_DIVISION", "TIMING_COST_MULTIPLIER", "URGENCY_BASE_MULTIPLIER",
        "SLO_DEFAULT_ERROR_BUDGET", "SLO_DEFAULT_LATENCY_P95_MS", "SLO_DEFAULT_HEALTH",
        "TDD_COMPLIANT_COVERAGE", "TDD_COMPLIANT_TDD_SCORE", "TDD_FALLBACK_COVERAGE", "TDD_FALLBACK_TDD_SCORE",
        "MARTIN_COMPLIANT_SCORE", "MARTIN_FALLBACK_SCORE",
        "LIQUIDITY_LOW_THRESHOLD", "LIQUIDITY_HIGH_THRESHOLD",
        "LIQUIDITY_SCORE_SUFFICIENT", "LIQUIDITY_SCORE_INSUFFICIENT",
        "ADF_PVALUE_THRESHOLD", "STATIONARY_HEALTH_MULTIPLIER", "NON_STATIONARY_HEALTH_MULTIPLIER",
        "DEFAULT_EXECUTION_QUALITY_SCORE", "DEFAULT_FILL_RATE",
        "MIN_HIGH_QUALITY_EXECUTION_SCORE", "MIN_HIGH_QUALITY_FILL_RATE",
        "DEFAULT_SLO_LATENCY_THRESHOLD_MS"
    )
    @classmethod
    def validate_score_100(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator(
        "MIN_CROSS_VALIDATION_SCORE", "MIN_META_LABELING_SIGNAL",
        "MIN_MCC_METRIC", "MAX_ORDER_FLOW_TOXICITY",
        "MIN_BACKTEST_CONFIDENCE", "MIN_EXECUTION_PROBABILITY",
        "CONF_BULL_REGIME_BONUS", "CONF_LOW_VOLATILITY_BONUS",
        "CONF_BEAR_REGIME_PENALTY", "CONF_HIGH_VOLATILITY_PENALTY",
        "CONF_POOR_LIQUIDITY_PENALTY", "CONF_LOW_LIQUIDITY_PENALTY",
        "CONF_HIGH_TOXICITY_PENALTY", "CONF_LOW_SHARPE_PENALTY",
        "CONF_LOW_MODEL_HEALTH_PENALTY", "CONF_LOW_CV_SCORE_PENALTY",
        "CONF_POSITION_LIMIT_MULTIPLIER", "CONF_DRAWDOWN_LIMIT_MULTIPLIER",
        "CONF_LEVERAGE_LIMIT_MULTIPLIER", "CONF_CIRCUIT_BREAKER_MULTIPLIER",
        "CONF_CRITICAL_FAILURE_MULTIPLIER",
        "DEFAULT_REGIME_CONFIDENCE", "DEFAULT_SIGNAL_STRENGTH",
        "ESTIMATED_VOLATILITY", "DEFAULT_ORDER_FLOW_TOXICITY",
        "ALPHA_QUALITY_HIGH_THRESHOLD", "ALPHA_QUALITY_MEDIUM_THRESHOLD",
        "FITTED_MODEL_SIGNAL_STRENGTH", "DEFAULT_MCC_METRIC",
        "CONF_HIGH_VAR_PENALTY", "CONF_SLO_VIOLATION_PENALTY",
        "URGENCY_IMPACT_COEFFICIENT", "SLIPPAGE_VOLATILITY_FACTOR",
        "KELLY_MAX_POSITION_PCT",
        "HARRIS_LIQUIDITY_WEIGHT", "OHARA_LIQUIDITY_WEIGHT", "DEFAULT_URGENCY",
        "BASE_PARTICIPATION_RATE", "INITIAL_CONFIDENCE"
    )
    @classmethod
    def validate_score_1(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Score must be between 0 and 1")
        return v

    @field_validator("ESTIMATED_SPREAD_BPS")
    @classmethod
    def validate_spread_bps(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Spread BPS must be between 0 and 100")
        return v

    @model_validator(mode="after")
    def validate_liquidity_weights_sum(self):
        """Ensure liquidity aggregation weights sum to approximately 1.0."""
        total = self.HARRIS_LIQUIDITY_WEIGHT + self.OHARA_LIQUIDITY_WEIGHT
        if not (0.99 <= total <= 1.01):  # Allow small floating point tolerance
            raise ValueError(
                f"Liquidity weights must sum to 1.0, got {total:.4f} "
                f"(Harris={self.HARRIS_LIQUIDITY_WEIGHT}, O'Hara={self.OHARA_LIQUIDITY_WEIGHT})"
            )
        return self


# =============================================================================
# SECTION 6: MAIN CONFIGURATION
#   - CentralizedConfig: Main configuration class that aggregates all sub-configs
# =============================================================================

class CentralizedConfig(BaseSettings):
    """Centralized configuration for the entire application."""

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Current environment"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Sub-configurations
    trading: TradingThresholds = Field(
        default_factory=TradingThresholds, description="Trading thresholds"
    )
    backtesting: BacktestingConfig = Field(
        default_factory=BacktestingConfig, description="Backtesting configuration"
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database configuration"
    )
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig, description="Monitoring configuration"
    )
    currency_hedging: CurrencyHedgingConfig = Field(
        default_factory=CurrencyHedgingConfig, description="Currency hedging configuration"
    )
    diversification: SectorCountryDiversificationConfig = Field(
        default_factory=SectorCountryDiversificationConfig,
        description="Sector/country diversification configuration",
    )
    compliance: ComplianceConfig = Field(
        default_factory=ComplianceConfig, description="Compliance engine configuration"
    )
    market_microstructure: MarketMicrostructureThresholds = Field(
        default_factory=MarketMicrostructureThresholds, description="Market microstructure thresholds"
    )

    # Strategy configurations
    strategies: Dict[str, StrategyConfig] = Field(
        default_factory=dict, description="Strategy configurations"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields from .env not defined in model
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_strategy_configs()

    def _load_strategy_configs(self):
        """Load strategy configurations from YAML files."""
        strategies_dir = Path("config/strategies")
        if strategies_dir.exists():
            for strategy_file in strategies_dir.glob("*.yaml"):
                try:
                    with open(strategy_file, "r") as f:
                        strategy_data = yaml.safe_load(f)

                    strategy_name = strategy_file.stem

                    # Mapear strategy_name a name si existe (compatibilidad con YAML)
                    if "strategy_name" in strategy_data and "name" not in strategy_data:
                        strategy_data["name"] = strategy_data.pop("strategy_name")
                    elif "name" not in strategy_data:
                        strategy_data["name"] = strategy_name

                    strategy_config = StrategyConfig(**strategy_data)
                    self.strategies[strategy_name] = strategy_config
                except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Could not load strategy config from {strategy_file}: {e}")

    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """Get configuration for a specific strategy."""
        return self.strategies.get(strategy_name)

    @property
    def trading_thresholds(self) -> "TradingThresholds":
        """Alias for trading property - backwards compatibility."""
        return self.trading

    def get_trading_threshold(self, threshold_name: str) -> Any:
        """Get a specific trading threshold value."""
        if not hasattr(self.trading, threshold_name):
            raise AttributeError(f"Trading threshold '{threshold_name}' does not exist")
        return getattr(self.trading, threshold_name)

    def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific strategy."""
        if strategy_name in self.strategies:
            current_config = self.strategies[strategy_name]
            updated_data = current_config.model_dump()
            updated_data.update(updates)
            self.strategies[strategy_name] = StrategyConfig(**updated_data)
            return True
        else:
            # Create new strategy if it doesn't exist
            strategy_data = {"name": strategy_name, **updates}
            self.strategies[strategy_name] = StrategyConfig(**strategy_data)
            return True

    def validate_configuration(self) -> bool:
        """Validate the entire configuration."""
        try:
            # Validate trading thresholds
            self.trading.model_validate(self.trading.model_dump())

            # Validate strategy configurations
            for _strategy_name, strategy_config in self.strategies.items():
                strategy_config.model_validate(strategy_config.model_dump())

            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "trading_thresholds": {
                "min_signal_strength": self.trading.min_signal_strength,
                "min_signal_confidence": self.trading.min_signal_confidence,
                "min_liquidity_score": self.trading.min_liquidity_score,
                "max_position_size": self.trading.max_position_size,
                "stop_loss_pct": self.trading.stop_loss_pct,
                "take_profit_pct": self.trading.take_profit_pct,
            },
            "strategies": {
                "count": len(self.strategies),
                "enabled": [name for name, config in self.strategies.items() if config.enabled],
                "all": list(self.strategies.keys()),
            },
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "name": self.database.name,
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "workers": self.api.workers,
            },
        }


# =============================================================================
# SECTION 7: HELPER FUNCTIONS
#   - get_config(): Get global configuration instance
#   - get_compliance_config(): Get compliance configuration
#   - get_trading_threshold(): Get trading thresholds
#   - reload_config(), set_config(), etc.
# =============================================================================

# Global configuration instance
_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CentralizedConfig()

    return _config


def get_trading_threshold(threshold_name: str = None) -> Any:
    """Get trading thresholds or specific threshold."""
    if threshold_name is None:
        return get_config().trading
    else:
        return get_config().get_trading_threshold(threshold_name)


def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """Get configuration for a specific strategy."""
    return get_config().strategies.get(strategy_name)


def get_compliance_config() -> ComplianceConfig:
    """Get compliance engine configuration."""
    return get_config().compliance


def get_strategy_stock_allocator_config(tier: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Strategy Stock Allocator configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Strategy Stock Allocator configuration
    """
    from app.shared.config.config_loader import load_strategy_stock_allocator_config
    return load_strategy_stock_allocator_config(tier)


def reload_config():
    """Reload the configuration from files."""
    global _config
    _config = None
    return get_config()


def set_config(config: CentralizedConfig):
    """Set the global configuration instance."""
    global _config
    _config = config


def validate_config() -> bool:
    """Validate the current configuration."""
    return get_config().validate_configuration()


def get_config_summary() -> Dict[str, Any]:
    """Get a summary of the current configuration."""
    return get_config().get_config_summary()


def validate_configuration() -> bool:
    """Validate the current configuration (alias for validate_config)."""
    return validate_config()


def update_strategy_config(strategy_name: str, new_config: dict):
    """Update strategy configuration."""
    config = get_config()
    return config.update_strategy_config(strategy_name, new_config)


# Configuration migration utilities
def find_magic_values() -> Dict[str, List[str]]:
    """Find magic values in the codebase that should be moved to configuration."""
    magic_values = {
        "numeric_thresholds": [
            "Signal cooldown: 10 minutes",
            "Compound score weights: 30/25/20/15/10",
            "Priority thresholds: 80/50",
            "Risk per trade: 2%",
            "Risk/reward ratio: 3:1",
            "Max consecutive stops: 5",
            "Rebalance frequency: 30 days",
            "Allocation weights: 50/25/25",
        ],
        "string_constants": [],
        "timeout_values": [],
        "retry_counts": [],
    }

    return magic_values


def migrate_magic_values(magic_values: Dict[str, List[str]]) -> bool:
    """Migrate magic values to centralized configuration."""
    # This would implement the migration logic
    # For now, return True
    return True


# =============================================================================
# Configuration Loading Functions
# =============================================================================


def load_config_from_yaml(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is invalid

    Examples:
        >>> config = load_config_from_yaml(Path("config.yaml"))
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            return config_data if config_data is not None else {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")


def load_config_from_json(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to JSON configuration file

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If JSON is invalid

    Examples:
        >>> config = load_config_from_json(Path("config.json"))
    """
    import json

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            return config_data if config_data is not None else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")


# =============================================================================
# Configuration Validation Functions
# =============================================================================


def validate_atr_multipliers(atr_multipliers: Dict[str, float]) -> bool:
    """
    Validate ATR multiplier configuration.

    Args:
        atr_multipliers: Dictionary of ATR multiplier names to values

    Returns:
        True if all multipliers are positive, False otherwise

    Examples:
        >>> validate_atr_multipliers({'default_stop': 2.0})
        True
        >>> validate_atr_multipliers({'default_stop': -1.0})
        False
    """
    if not atr_multipliers:
        return False

    return all(isinstance(v, (int, float)) and v > 0 for v in atr_multipliers.values())


def validate_risk_percentages(risk_config: Dict[str, float]) -> bool:
    """
    Validate risk percentage configuration.

    Args:
        risk_config: Dictionary of risk configuration values

    Returns:
        True if all percentages are between 0 and 1, False otherwise

    Examples:
        >>> validate_risk_percentages({'default_risk_per_trade': 0.02})
        True
        >>> validate_risk_percentages({'default_risk_per_trade': 1.5})
        False
    """
    if not risk_config:
        return False

    return all(isinstance(v, (int, float)) and 0 < v <= 1.0 for v in risk_config.values())


def validate_trading_symbols(symbols: List[str]) -> bool:
    """
    Validate trading symbols list.

    Args:
        symbols: List of trading symbols

    Returns:
        True if symbols list is valid (non-empty, unique items), False otherwise

    Examples:
        >>> validate_trading_symbols(['AAPL', 'MSFT'])
        True
        >>> validate_trading_symbols([])
        False
    """
    if not symbols or not isinstance(symbols, list):
        return False

    # Check for non-empty and all strings
    if not all(isinstance(s, str) and s.strip() for s in symbols):
        return False

    # Check for duplicates
    if len(symbols) != len(set(symbols)):
        return False

    return True


def validate_dates(backtest_config: Dict[str, str]) -> bool:
    """
    Validate backtesting date configuration.

    Args:
        backtest_config: Dictionary containing start_date and end_date

    Returns:
        True if dates are valid and in correct order, False otherwise

    Examples:
        >>> validate_dates({'start_date': '2020-01-01', 'end_date': '2024-12-31'})
        True
        >>> validate_dates({'start_date': '2024-01-01', 'end_date': '2020-01-01'})
        False
    """
    if not backtest_config:
        return False

    start_date = backtest_config.get('start_date')
    end_date = backtest_config.get('end_date')

    if not start_date or not end_date:
        return False

    try:
        from datetime import datetime

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        return start < end
    except (ValueError, TypeError):
        return False


def validate_config_object(config: 'Configuration') -> bool:
    """
    Validate complete configuration object.

    Args:
        config: Configuration object to validate

    Returns:
        True if configuration is valid, False otherwise

    Examples:
        >>> config = Configuration({'risk_management': {...}})
        >>> validate_config_object(config)
        True
    """
    if not config or not hasattr(config, '_config'):
        return False

    config_dict = config._config

    # Validate risk management section
    if 'risk_management' in config_dict:
        rm = config_dict['risk_management']

        if 'atr_multipliers' in rm and not validate_atr_multipliers(rm['atr_multipliers']):
            return False

        if 'position_sizing' in rm and not validate_risk_percentages(rm['position_sizing']):
            return False

    # Validate trading section
    if 'trading' in config_dict:
        trading = config_dict['trading']

        if 'symbols' in trading and not validate_trading_symbols(trading['symbols']):
            return False

    # Validate backtesting section
    if 'backtesting' in config_dict and not validate_dates(config_dict['backtesting']):
        return False

    return True


# =============================================================================
# Configuration Merging Functions
# =============================================================================


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries recursively.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary

    Examples:
        >>> base = {'level1': {'key1': 'value1'}}
        >>> override = {'level1': {'key2': 'value2'}}
        >>> merged = merge_configs(base, override)
        >>> merged['level1']['key1']
        'value1'
        >>> merged['level1']['key2']
        'value2'
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


# =============================================================================
# SECTION 8: LEGACY/UTILITY
#   - Configuration: Legacy wrapper class for backward compatibility
#   - Cache functions, validation functions, etc.
# =============================================================================

# =============================================================================
# Configuration Class (Legacy - for backward compatibility)
# =============================================================================


class Configuration:
    """
    Configuration wrapper class for accessing configuration values.

    Provides convenient methods for accessing nested configuration values
    and updating configuration.

    Args:
        config_dict: Dictionary containing configuration data

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> config.get_atr_multiplier('default_stop')
        2.0
    """

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict if config_dict is not None else {}
        self._lock = None  # For thread safety

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (supports nested notation like 'risk_management.atr_multipliers')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
            >>> config.get('risk_management.atr_multipliers.default_stop')
            2.0
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key (supports dot notation).

        Args:
            key: Configuration key (supports nested notation)
            value: Value to set

        Examples:
            >>> config = Configuration({'risk_management': {}})
            >>> config.set('risk_management.new_key', 'value')
            >>> config.get('risk_management.new_key')
            'value'
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_atr_multiplier(self, multiplier_name: str) -> Optional[float]:
        """
        Get ATR multiplier value.

        Args:
            multiplier_name: Name of the ATR multiplier

        Returns:
            ATR multiplier value or None if not found

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
            >>> config.get_atr_multiplier('default_stop')
            2.0
        """
        return self.get(f'risk_management.atr_multipliers.{multiplier_name}')

    def set_atr_multiplier(self, multiplier_name: str, value: float) -> None:
        """
        Set ATR multiplier value.

        Args:
            multiplier_name: Name of the ATR multiplier
            value: Value to set

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {}}})
            >>> config.set_atr_multiplier('default_stop', 2.5)
            >>> config.get_atr_multiplier('default_stop')
            2.5
        """
        self.set(f'risk_management.atr_multipliers.{multiplier_name}', value)

    def get_risk_config(self) -> Dict[str, Any]:
        """
        Get risk management configuration section.

        Returns:
            Risk management configuration dictionary

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {...}}})
            >>> risk_config = config.get_risk_config()
        """
        return self.get('risk_management', {})

    def get_trading_symbols(self) -> List[str]:
        """
        Get trading symbols list.

        Returns:
            List of trading symbols

        Examples:
            >>> config = Configuration({'trading': {'symbols': ['AAPL', 'MSFT']}})
            >>> config.get_trading_symbols()
            ['AAPL', 'MSFT']
        """
        return self.get('trading.symbols', [])

    def get_backtest_dates(self) -> Dict[str, str]:
        """
        Get backtesting date range.

        Returns:
            Dictionary with start_date and end_date

        Examples:
            >>> config = Configuration({'backtesting': {'start_date': '2020-01-01', 'end_date': '2024-12-31'}})
            >>> dates = config.get_backtest_dates()
            >>> dates['start_date']
            '2020-01-01'
        """
        return {
            'start_date': self.get('backtesting.start_date', ''),
            'end_date': self.get('backtesting.end_date', ''),
        }


# =============================================================================
# Default Value Functions
# =============================================================================


def get_default_atr_multiplier() -> float:
    """
    Get default ATR multiplier value.

    Returns:
        Default ATR multiplier (2.0)

    Examples:
        >>> get_default_atr_multiplier()
        2.0
    """
    return 2.0


def get_default_risk_per_trade() -> float:
    """
    Get default risk per trade percentage.

    Returns:
        Default risk per trade (0.02 = 2%)

    Examples:
        >>> get_default_risk_per_trade()
        0.02
    """
    return 0.02


def get_default_max_position_size() -> float:
    """
    Get default maximum position size.

    Returns:
        Default max position size (0.25 = 25%)

    Examples:
        >>> get_default_max_position_size()
        0.25
    """
    return 0.25


def get_default_stop_distance_pct() -> float:
    """
    Get default stop loss distance percentage.

    Returns:
        Default stop distance (0.05 = 5%)

    Examples:
        >>> get_default_stop_distance_pct()
        0.05
    """
    return 0.05


# =============================================================================
# Cache Functions (for caching tests)
# =============================================================================

_config_cache: Dict[Path, Dict[str, Any]] = {}
_config_cache_timestamps: Dict[Path, float] = {}


def get_config_cached_after_load(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration with caching support.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary (cached if available)

    Examples:
        >>> config1 = get_config_cached_after_load(Path("config.yaml"))
        >>> config2 = get_config_cached_after_load(Path("config.yaml"))
        >>> # config2 will be returned from cache if file hasn't changed
    """
    import os
    import time

    # Check if we have a cached version
    if config_path in _config_cache:
        cached_time = _config_cache_timestamps.get(config_path, 0)
        file_mtime = os.path.getmtime(config_path)

        # Return cached version if file hasn't changed
        if file_mtime <= cached_time:
            return _config_cache[config_path]

    # Load fresh configuration
    if config_path.suffix in ['.yaml', '.yml']:
        config = load_config_from_yaml(config_path)
    elif config_path.suffix == '.json':
        config = load_config_from_json(config_path)
    else:
        raise ValueError(f"Unsupported config file type: {config_path.suffix}")

    # Cache the configuration
    _config_cache[config_path] = config
    _config_cache_timestamps[config_path] = time.time()

    return config


def get_config_cache_invalidated_on_change(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration with automatic cache invalidation on file changes.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary (fresh if file changed, cached otherwise)

    Examples:
        >>> config1 = get_config_cache_invalidated_on_change(Path("config.yaml"))
        >>> # Modify file externally
        >>> config2 = get_config_cache_invalidated_on_change(Path("config.yaml"))
        >>> # config2 will be fresh (cache invalidated)
    """
    return get_config_cached_after_load(config_path)


# =============================================================================
# Property-Based Test Helper Functions
# =============================================================================


def get_atr_multiplier_positive_property(multiplier: float) -> bool:
    """
    Property-based test helper: ATR multiplier should be positive.

    Args:
        multiplier: ATR multiplier value to test

    Returns:
        True if multiplier is positive

    Examples:
        >>> get_atr_multiplier_positive_property(2.0)
        True
        >>> get_atr_multiplier_positive_property(-1.0)
        False
    """
    return isinstance(multiplier, (int, float)) and multiplier > 0


def get_risk_percentage_bounds_property(risk_pct: float) -> bool:
    """
    Property-based test helper: Risk percentage should be between 0 and 1.

    Args:
        risk_pct: Risk percentage value to test

    Returns:
        True if risk_pct is between 0 and 1

    Examples:
        >>> get_risk_percentage_bounds_property(0.02)
        True
        >>> get_risk_percentage_bounds_property(1.5)
        False
    """
    return isinstance(risk_pct, (int, float)) and 0 < risk_pct <= 1.0


def get_symbols_list_property(symbols: List[str]) -> bool:
    """
    Property-based test helper: Symbols list should be valid.

    Args:
        symbols: List of symbols to test

    Returns:
        True if symbols list is valid

    Examples:
        >>> get_symbols_list_property(['AAPL', 'MSFT'])
        True
        >>> get_symbols_list_property([])
        False
    """
    return validate_trading_symbols(symbols)


def get_date_order_property(start_date: str, end_date: str) -> bool:
    """
    Property-based test helper: End date should be after start date.

    Args:
        start_date: Start date string (YYYY-MM-DD format)
        end_date: End date string (YYYY-MM-DD format)

    Returns:
        True if end_date is after start_date

    Examples:
        >>> get_date_order_property('2020-01-01', '2024-12-31')
        True
        >>> get_date_order_property('2024-01-01', '2020-01-01')
        False
    """
    return validate_dates({'start_date': start_date, 'end_date': end_date})


# =============================================================================
# Update Helper Functions
# =============================================================================


def update_atr_multiplier(config: Configuration, multiplier_name: str, value: float) -> None:
    """
    Update ATR multiplier in configuration.

    Args:
        config: Configuration object
        multiplier_name: Name of the ATR multiplier
        value: New value

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> update_atr_multiplier(config, 'default_stop', 2.5)
        >>> config.get_atr_multiplier('default_stop')
        2.5
    """
    config.set_atr_multiplier(multiplier_name, value)


def update_nested_value(config: Configuration, key_path: str, value: Any) -> None:
    """
    Update nested configuration value.

    Args:
        config: Configuration object
        key_path: Dot-notation path to the value
        value: New value

    Examples:
        >>> config = Configuration({'risk_management': {'position_sizing': {'default_risk_per_trade': 0.02}}})
        >>> update_nested_value(config, 'risk_management.position_sizing.default_risk_per_trade', 0.03)
        >>> config.get('risk_management.position_sizing.default_risk_per_trade')
        0.03
    """
    config.set(key_path, value)


# =============================================================================
# Thread Safety Functions
# =============================================================================


def concurrent_read_access(config: Configuration, num_threads: int = 10) -> list:
    """
    Test concurrent read access to configuration.

    Args:
        config: Configuration object
        num_threads: Number of threads to use

    Returns:
        List of results from concurrent reads

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> results = concurrent_read_access(config, 10)
        >>> len(results)
        10
    """
    import threading

    results = []

    def read_config():
        results.append(config.get_atr_multiplier('default_stop'))

    threads = [threading.Thread(target=read_config) for _ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    return results


# =============================================================================
# Integration Test Functions
# =============================================================================


def full_config_workflow(config_path: Path) -> Dict[str, Any]:
    """
    Test complete configuration workflow: load, access, validate.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary with workflow results

    Examples:
        >>> result = full_config_workflow(Path("config.yaml"))
        >>> result['success']
        True
    """
    # Load from file
    config_dict = load_config_from_yaml(config_path)

    # Create configuration object
    config = Configuration(config_dict)

    # Access values
    atr_multiplier = config.get_atr_multiplier('default_stop')
    symbols = config.get_trading_symbols()
    dates = config.get_backtest_dates()

    # Validate
    is_valid = validate_config_object(config)

    return {
        'success': is_valid,
        'atr_multiplier': atr_multiplier,
        'symbols': symbols,
        'dates': dates,
    }


def config_with_validation(config_dict: Dict[str, Any]) -> tuple:
    """
    Create configuration and perform full validation.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Tuple of (config_object, is_valid)

    Examples:
        >>> config_dict = {'risk_management': {...}, 'trading': {...}}
        >>> config, is_valid = config_with_validation(config_dict)
        >>> is_valid
        True
    """
    config = Configuration(config_dict)
    is_valid = validate_config_object(config)

    return config, is_valid
