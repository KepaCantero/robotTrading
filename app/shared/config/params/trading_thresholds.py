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
    signal_liquidity_score: float = Field(
        default=70.0, description="Default liquidity score for signals (0-100)"
    )
    signal_priority_score: float = Field(
        default=50.0, description="Default priority score for signals (0-100)"
    )

    # Technical indicators
    rsi_oversold: float = Field(default=30.0, description="RSI oversold threshold")
    rsi_overbought: float = Field(default=70.0, description="RSI overbought threshold")
    rsi_sell_overbought: float = Field(default=70.0, description="RSI sell overbought threshold")
    rsi_recovering_threshold: float = Field(
        default=50.0, description="RSI recovering threshold for buy signals"
    )
    rsi_neutral_zone_min: float = Field(default=40.0, description="RSI neutral zone minimum")
    rsi_neutral_zone_max: float = Field(default=60.0, description="RSI neutral zone maximum")

    # History lengths for technical indicators
    default_price_history_length: int = Field(
        default=200, description="Default price history length for indicators"
    )
    rsi_history_length: int = Field(default=14, description="RSI calculation period")
    atr_history_length: int = Field(default=14, description="ATR calculation period")

    # ATR filter settings
    min_atr_threshold: float = Field(
        default=0.5, description="Minimum ATR threshold for volatility filter"
    )
    atr_filter_enabled: bool = Field(default=True, description="Enable ATR volatility filter")
    use_relative_atr: bool = Field(default=True, description="Use relative ATR (ATR/price)")

    # Position sizing
    max_position_size: float = Field(default=0.1, description="Maximum position size (0-1)")
    min_position_size: float = Field(default=0.01, description="Minimum position size (0-1)")
    validator_default_max_position_pct: float = Field(
        default=0.25, description="Default max position as % of capital"
    )
    validator_min_position_pct: float = Field(
        default=0.05, description="Minimum position as % of capital"
    )
    validator_max_position_pct: float = Field(
        default=0.25, description="Maximum position limit as % of capital"
    )
    validator_stop_loss_warning_pct: float = Field(
        default=0.08, description="Stop loss warning threshold %"
    )
    validator_min_reward_risk_ratio: float = Field(
        default=2.0, description="Minimum reward/risk ratio"
    )

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

    # Momentum zones
    momentum_zone_min: float = Field(default=40.0, description="Minimum momentum zone threshold")
    momentum_zone_max: float = Field(default=60.0, description="Maximum momentum zone threshold")

    # Logging intervals
    log_interval_bars: int = Field(default=100, description="Logging interval in bars")

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

    # Mean Reversion parameters
    min_z_score_default: float = Field(
        default=-2.0, description="Default minimum z-score for mean reversion entry"
    )
    max_z_score_default: float = Field(
        default=2.0, description="Default maximum z-score for mean reversion exit"
    )

    # Dividend strategy parameters
    dividend_min_yield: float = Field(
        default=0.02, description="Minimum dividend yield for dividend strategy"
    )
    dividend_max_payout_ratio: float = Field(
        default=0.75, description="Maximum payout ratio for dividend stocks"
    )

    # Mean Reversion strategy parameters
    min_z_score_default: float = Field(
        default=-2.0, description="Default minimum z-score for mean reversion entry"
    )
    max_z_score_default: float = Field(
        default=2.0, description="Default maximum z-score for mean reversion exit"
    )
    mean_reversion_max_exposure: float = Field(
        default=0.30, description="Maximum total exposure for mean reversion strategy"
    )
    mean_reversion_simulated_std_dev: float = Field(
        default=0.02, description="Simulated standard deviation for mean reversion testing"
    )
    mean_reversion_simulated_volatility: float = Field(
        default=0.15, description="Simulated volatility for mean reversion testing"
    )
    z_score_entry_multiplier: float = Field(
        default=1.0, description="Multiplier for z-score entry threshold"
    )
    z_score_modified_threshold: float = Field(
        default=0.5, description="Modified threshold for additional z-score checks"
    )
    mean_reversion_default_confidence: float = Field(
        default=70.0, description="Default confidence for mean reversion signals"
    )
    mean_reversion_default_liquidity: float = Field(
        default=80.0, description="Default liquidity score for mean reversion signals"
    )
    mean_reversion_default_priority: float = Field(
        default=60.0, description="Default priority score for mean reversion signals"
    )

    # Multi-factor strategy parameters
    multi_factor_history_length: int = Field(
        default=252, description="History length for multi-factor strategy calculations"
    )
    dividend: Dict[str, float] = Field(
        default_factory=lambda: {
            "min_yield": 0.02,
            "max_yield": 0.08,
            "min_payout": 0.75,
        },
        description="Dividend strategy parameters",
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

    # Learning Configuration (FASE 3.1 - Centralized Config)
    learning_min_capital: float = Field(
        default=10000.0, description="Minimum capital for learning engine to be economically viable"
    )
    learning_max_cost_ratio: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Maximum acceptable learning cost as ratio of alpha",
    )

    # Capital Tier Configuration (FASE 3.1 - Centralized Config)
    tier_default_position_size: float = Field(
        default=0.10, ge=0.01, le=0.25, description="Default position size % for capital tier"
    )
    tier_default_max_daily_loss: float = Field(
        default=0.03, ge=0.01, le=0.10, description="Default max daily loss % for capital tier"
    )
    tier_micro_max_drawdown: float = Field(
        default=0.10, ge=0.05, le=0.20, description="Max drawdown for micro tier accounts"
    )
    tier_small_max_drawdown: float = Field(
        default=0.15, ge=0.10, le=0.25, description="Max drawdown for small tier accounts"
    )

    # Capital Viability Configuration (FASE 3.1 - Centralized Config)
    capital_viability_alpha_threshold: float = Field(
        default=0.15, ge=0.05, le=0.30, description="Alpha threshold for capital viability"
    )
    capital_viability_min_achievable: float = Field(
        default=0.01,
        ge=0.005,
        le=0.05,
        description="Minimum achievable alpha for capital viability",
    )
    capital_viability_max_achievable: float = Field(
        default=0.30, ge=0.10, le=0.50, description="Maximum achievable alpha for capital viability"
    )

    # Reconnection Configuration (FASE 3.1 - Centralized Config)
    reconnection_max_attempts: int = Field(
        default=5, ge=1, le=20, description="Maximum reconnection attempts"
    )
    reconnection_base_delay_seconds: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Base delay for reconnection attempts"
    )
    reconnection_max_delay_seconds: float = Field(
        default=60.0, ge=10.0, le=300.0, description="Maximum delay for reconnection attempts"
    )
    reconnection_exponential_base: float = Field(
        default=2.0, ge=1.5, le=3.0, description="Exponential backoff base"
    )
    reconnection_jitter_factor: float = Field(
        default=0.1, ge=0.0, le=0.5, description="Jitter factor for reconnection delays"
    )
    reconnection_alert_after_attempts: int = Field(
        default=3, ge=1, le=10, description="Alert after N failed reconnection attempts"
    )
    reconnection_default_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="Default timeout for reconnection"
    )
    reconnection_maintain_delay: float = Field(
        default=5.0, ge=1.0, le=30.0, description="Maintain delay for reconnection"
    )
    reconnection_health_check_interval: float = Field(
        default=60.0, ge=10.0, le=300.0, description="Health check interval in seconds"
    )

    # Position Monitor Configuration (FASE 3.1 - Centralized Config)
    position_monitor_check_interval: float = Field(
        default=5.0, ge=1.0, le=60.0, description="Position monitor check interval in seconds"
    )
    position_monitor_max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum price fetch retries"
    )
    position_monitor_price_fetch_timeout: float = Field(
        default=10.0, ge=1.0, le=30.0, description="Price fetch timeout in seconds"
    )
    position_monitor_state_sync_interval: float = Field(
        default=30.0, ge=5.0, le=120.0, description="State sync interval in seconds"
    )
    position_monitor_stop_execution_timeout: float = Field(
        default=60.0, ge=10.0, le=300.0, description="Stop execution timeout in seconds"
    )

    # Transaction Cost Configuration (FASE 3.1 - Centralized Config)
    bps_multiplier: float = Field(
        default=10000.0, description="Basis points multiplier (1 bps = 0.0001)"
    )
    tx_market_order_slippage_pct: float = Field(
        default=0.001, ge=0.0001, le=0.01, description="Market order slippage percentage"
    )
    tx_sec_fee_per_share: float = Field(
        default=0.0000278, ge=0.0, le=0.001, description="SEC fee per share"
    )
    tx_trading_fee_per_share: float = Field(
        default=0.000166, ge=0.0, le=0.001, description="Trading activity fee per share"
    )

    # Execution Configuration (FASE 3.1 - Centralized Config)
    execution_history_max_size: int = Field(
        default=1000, ge=100, le=10000, description="Maximum execution history size"
    )
    simulated_latency_ms: float = Field(
        default=50.0, ge=0.0, le=500.0, description="Simulated latency in milliseconds"
    )

    # Order Limits Configuration (FASE 3.1 - Centralized Config)
    max_order_quantity_shares: int = Field(
        default=100000, ge=1000, le=1000000, description="Maximum order quantity in shares"
    )
    max_order_price_usd: float = Field(
        default=10000.0, ge=100.0, le=100000.0, description="Maximum order price in USD"
    )
    max_order_timestamp_age_days: int = Field(
        default=1, ge=1, le=7, description="Maximum order timestamp age in days"
    )

    # Drawdown Monitor Configuration (FASE 3.1 - Centralized Config)
    drawdown_max_limit: float = Field(
        default=0.15, ge=0.05, le=0.25, description="Maximum drawdown limit"
    )
    drawdown_caution_threshold: float = Field(
        default=0.05, ge=0.02, le=0.10, description="Drawdown caution threshold"
    )
    drawdown_warning_threshold: float = Field(
        default=0.10, ge=0.05, le=0.15, description="Drawdown warning threshold"
    )
    drawdown_caution_scale: float = Field(
        default=0.8, ge=0.5, le=1.0, description="Position scale at caution level"
    )
    drawdown_warning_scale: float = Field(
        default=0.5, ge=0.25, le=0.75, description="Position scale at warning level"
    )
    drawdown_halt_scale: float = Field(
        default=0.0, ge=0.0, le=0.25, description="Position scale at halt level"
    )

    # Trailing Stop Configuration (FASE 3.1 - Centralized Config)
    trailing_stop_default_pct: float = Field(
        default=0.02, ge=0.01, le=0.10, description="Default trailing stop percentage"
    )

    # Currency Hedging Configuration (FASE 3.1 - Centralized Config)
    currency_single_max: float = Field(
        default=0.30, ge=0.10, le=0.50, description="Maximum single currency exposure"
    )
    currency_total_max: float = Field(
        default=0.50, ge=0.30, le=0.80, description="Maximum total FX exposure"
    )
    currency_min_exposure: float = Field(
        default=0.05, ge=0.01, le=0.10, description="Minimum exposure for hedging consideration"
    )
    currency_max_cost_bps: float = Field(
        default=20.0, ge=5.0, le=50.0, description="Maximum hedging cost in basis points"
    )
    currency_partial_hedge_pct: float = Field(
        default=0.50, ge=0.25, le=0.75, description="Partial hedge percentage"
    )

    # Volatility Monitor Configuration (FASE 3.1 - Centralized Config)
    volatility_atr_period: int = Field(
        default=14, ge=5, le=30, description="ATR period for volatility monitoring"
    )
    volatility_lookback_periods: int = Field(
        default=30, ge=10, le=60, description="Lookback periods for volatility monitoring"
    )

    # Annual Trading Configuration (FASE 3.1 - Centralized Config)
    annual_trading_days: int = Field(
        default=252, ge=200, le=260, description="Number of trading days per year"
    )
    annual_trading_days_const: int = Field(
        default=252, ge=200, le=260, description="Annual trading days constant"
    )
    percentage_multiplier: float = Field(
        default=100.0, description="Percentage multiplier (1% = 0.01 * 100)"
    )

    # Opportunity Cost Configuration (FASE 3.1 - Centralized Config)
    opportunity_risk_free_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.15,
        description="Risk-free rate for opportunity cost calculations",
    )

    # Dynamic Reallocation Configuration (FASE 3.1 - Centralized Config)
    dynamic_realloc_rebalance_days: int = Field(
        default=30, ge=7, le=90, description="Rebalance frequency in days"
    )
    dynamic_realloc_rolling_window: int = Field(
        default=90, ge=30, le=180, description="Rolling window for reallocation calculations"
    )
    dynamic_realloc_min_weight: float = Field(
        default=0.05, ge=0.01, le=0.15, description="Minimum strategy weight"
    )
    dynamic_realloc_max_weight: float = Field(
        default=0.60, ge=0.30, le=0.80, description="Maximum strategy weight"
    )
    dynamic_realloc_volatility_target: float = Field(
        default=0.15, ge=0.05, le=0.30, description="Target volatility for reallocation"
    )
    dynamic_realloc_min_trades: int = Field(
        default=10, ge=5, le=30, description="Minimum trades for reallocation consideration"
    )

    # Emergency Handler Configuration (FASE 3.1 - Centralized Config)
    emergency_confirmation_timeout: float = Field(
        default=30.0, ge=10.0, le=60.0, description="Emergency confirmation timeout in seconds"
    )
    emergency_position_close_timeout: float = Field(
        default=60.0, ge=30.0, le=120.0, description="Emergency position close timeout in seconds"
    )

    # Spread Configuration (FASE 3.1 - Centralized Config)
    spread_skew_base: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Base spread skew factor"
    )

    # Kelly Criterion Configuration (FASE 3.1 - Centralized Config)
    kelly_fallback_fraction: float = Field(
        default=0.25, ge=0.10, le=0.50, description="Fallback Kelly fraction when calculation fails"
    )
    kelly_half_multiplier: float = Field(
        default=0.5, ge=0.25, le=0.75, description="Half-Kelly multiplier"
    )
    kelly_max_position_pct: float = Field(
        default=0.25, ge=0.10, le=0.40, description="Maximum position from Kelly calculation"
    )
    kelly_min_positive_threshold: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Minimum positive threshold for Kelly"
    )

    # Rate Limiting Configuration (FASE 3.1 - Centralized Config)
    rate_limit_max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum rate limit retries"
    )
    rate_limit_initial_backoff: float = Field(
        default=1.0, ge=0.5, le=5.0, description="Initial backoff in seconds"
    )
    rate_limit_backoff_jitter_pct: float = Field(
        default=0.1, ge=0.0, le=0.3, description="Backoff jitter percentage"
    )
    rate_limit_default_timeout: float = Field(
        default=30.0, ge=5.0, le=60.0, description="Default rate limit timeout"
    )
    rate_limit_alert_threshold: float = Field(
        default=0.8, ge=0.5, le=0.95, description="Alert when rate limit usage exceeds threshold"
    )
    rate_limit_alpaca_requests_per_second: float = Field(
        default=200.0, ge=10.0, le=500.0, description="Alpaca requests per second limit"
    )
    rate_limit_alpaca_burst_capacity: int = Field(
        default=400, ge=50, le=1000, description="Alpaca burst capacity"
    )
    rate_limit_polygon_requests_per_second: float = Field(
        default=5.0, ge=1.0, le=20.0, description="Polygon requests per second limit"
    )
    rate_limit_polygon_burst_capacity: int = Field(
        default=10, ge=5, le=50, description="Polygon burst capacity"
    )
    rate_limit_ibkr_requests_per_second: float = Field(
        default=50.0, ge=10.0, le=100.0, description="IBKR requests per second limit"
    )
    rate_limit_ibkr_burst_capacity: int = Field(
        default=100, ge=20, le=200, description="IBKR burst capacity"
    )
    rate_limit_binance_requests_per_second: float = Field(
        default=50.0, ge=10.0, le=120.0, description="Binance requests per second limit"
    )
    rate_limit_binance_burst_capacity: int = Field(
        default=1200, ge=100, le=3000, description="Binance burst capacity"
    )

    # Circuit Breaker Extended Configuration (FASE 3.1 - Centralized Config)
    circuit_breaker_recovery_timeout: int = Field(
        default=300, ge=60, le=900, description="Circuit breaker recovery timeout in seconds"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5, ge=3, le=10, description="Failure threshold for circuit breaker"
    )
    circuit_breaker_vix_high: float = Field(
        default=25.0, ge=20.0, le=30.0, description="VIX high threshold for circuit breaker"
    )
    circuit_breaker_vix_extreme: float = Field(
        default=35.0, ge=30.0, le=50.0, description="VIX extreme threshold for circuit breaker"
    )
    circuit_breaker_stock_volatility: float = Field(
        default=0.05, ge=0.02, le=0.10, description="Stock volatility threshold for circuit breaker"
    )

    # Loss Monitor Configuration (FASE 3.1 - Centralized Config)
    loss_monitor_lookback_trades: int = Field(
        default=20, ge=5, le=50, description="Lookback trades for loss monitoring"
    )
    loss_monitor_reset_threshold: int = Field(
        default=3, ge=1, le=5, description="Reset threshold for loss monitor"
    )
    loss_monitor_window_trades: int = Field(
        default=10, ge=5, le=20, description="Window trades for loss monitoring"
    )
    loss_monitor_scale_max_reduction: float = Field(
        default=0.5, ge=0.25, le=0.75, description="Maximum scale reduction from loss monitor"
    )
    consecutive_losses_threshold: int = Field(
        default=5, ge=3, le=10, description="Consecutive losses threshold for alert"
    )

    # Liquidity Configuration (FASE 3.1 - Centralized Config)
    liquidity_max_spread_percent: float = Field(
        default=0.05, ge=0.01, le=0.10, description="Maximum spread percentage for liquidity"
    )
    liquidity_volume_weight: float = Field(
        default=0.4, ge=0.1, le=0.6, description="Weight for volume in liquidity score"
    )
    liquidity_depth_weight: float = Field(
        default=0.3, ge=0.1, le=0.5, description="Weight for depth in liquidity score"
    )
    liquidity_spread_weight: float = Field(
        default=0.3, ge=0.1, le=0.5, description="Weight for spread in liquidity score"
    )
    liquidity_volume_normalization: float = Field(
        default=1000000.0, description="Volume normalization factor"
    )
    liquidity_depth_normalization: float = Field(
        default=100000.0, description="Depth normalization factor"
    )
    liquidity_stress_multiplier: float = Field(
        default=2.0, ge=1.0, le=3.0, description="Stress multiplier for liquidity calculations"
    )

    # Order Size Configuration (FASE 3.1 - Centralized Config)
    order_size_tiny_threshold: float = Field(
        default=0.01, ge=0.001, le=0.02, description="Tiny order size threshold"
    )
    order_size_small_threshold: float = Field(
        default=0.05, ge=0.02, le=0.10, description="Small order size threshold"
    )
    order_size_small_multiplier: float = Field(
        default=1.5, ge=1.0, le=2.0, description="Small order slippage multiplier"
    )
    order_size_large_multiplier: float = Field(
        default=2.0, ge=1.5, le=3.0, description="Large order slippage multiplier"
    )

    # Performance Thresholds (FASE 3.1 - Centralized Config)
    poor_performance_threshold: float = Field(
        default=-0.10, le=-0.05, description="Poor performance threshold"
    )
    moderate_performance_reduction: float = Field(
        default=0.8, ge=0.5, le=1.0, description="Moderate performance scale factor"
    )
    strong_performance_reduction: float = Field(
        default=0.6, ge=0.4, le=0.8, description="Strong performance scale factor"
    )
    weak_performance_threshold: float = Field(
        default=-0.05, le=-0.02, description="Weak performance threshold"
    )
    max_reduction_factor: float = Field(
        default=0.5, ge=0.25, le=0.75, description="Maximum reduction factor"
    )

    # P-Value Configuration (FASE 3.1 - Centralized Config)
    p_value_significance: float = Field(
        default=0.05, ge=0.01, le=0.10, description="P-value significance threshold"
    )

    # Alert Configuration (FASE 3.1 - Centralized Config)
    alert_limit_price_offset: float = Field(
        default=0.01, ge=0.001, le=0.05, description="Alert limit price offset"
    )

    # Volume Configuration (FASE 3.1 - Centralized Config)
    strong_volume_multiplier: float = Field(
        default=2.0, ge=1.5, le=3.0, description="Strong volume multiplier"
    )

    # Valuation Configuration (FASE 3.1 - Centralized Config)
    valuation_ratio_cheap: float = Field(
        default=0.8, ge=0.6, le=1.0, description="Valuation ratio cheap threshold"
    )
    valuation_ratio_fair: float = Field(
        default=1.2, ge=1.0, le=1.5, description="Valuation ratio fair threshold"
    )

    # FX Configuration (FASE 3.1 - Centralized Config)
    fx_default_interest_rate: float = Field(
        default=0.05, ge=0.0, le=0.15, description="Default FX interest rate"
    )
    fx_daily_variation_factor: float = Field(
        default=0.01, ge=0.001, le=0.05, description="FX daily variation factor"
    )
    fx_long_term_variation_factor: float = Field(
        default=0.10, ge=0.05, le=0.20, description="FX long-term variation factor"
    )
    fx_months_per_year: int = Field(
        default=12, ge=12, le=12, description="Months per year for FX calculations"
    )
    fx_quantization_precision: int = Field(
        default=4, ge=2, le=6, description="FX quantization precision (decimal places)"
    )

    # Volatility Trend Configuration (FASE 3.1 - Centralized Config)
    volatility_trend_increasing_threshold: float = Field(
        default=1.2, ge=1.0, le=1.5, description="Volatility trend increasing threshold"
    )
    volatility_trend_decreasing_threshold: float = Field(
        default=0.8, ge=0.5, le=1.0, description="Volatility trend decreasing threshold"
    )

    # Covered Call Configuration (FASE 3.1 - Centralized Config)
    covered_call_otm_multiplier: float = Field(
        default=1.1, ge=1.0, le=1.3, description="Covered call OTM multiplier"
    )

    # Pairs Trading Configuration (FASE 3.1 - Centralized Config)
    pairs_correlation_min: float = Field(
        default=0.7, ge=0.5, le=0.9, description="Minimum correlation for pairs trading"
    )

    # Dividend Score Configuration (FASE 3.1 - Centralized Config)
    dividend_score_good: float = Field(
        default=60.0, ge=40.0, le=80.0, description="Good dividend score threshold"
    )
    dividend_score_excellent: float = Field(
        default=80.0, ge=60.0, le=100.0, description="Excellent dividend score threshold"
    )

    # Stop Loss Configuration (FASE 3.1 - Centralized Config)
    default_stop_loss_pct: float = Field(
        default=0.08, ge=0.02, le=0.15, description="Default stop loss percentage"
    )
    max_stop_distance_pct: float = Field(
        default=0.15, ge=0.05, le=0.25, description="Maximum stop distance percentage"
    )

    # Risk Per Trade Configuration (FASE 3.1 - Centralized Config)
    risk_per_trade_default: float = Field(
        default=0.02, ge=0.005, le=0.05, description="Default risk per trade percentage"
    )

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
