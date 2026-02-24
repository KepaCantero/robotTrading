"""
Technical Indicators Configuration Module

Contains configuration for technical indicators, windows,
and analysis parameters.
"""

from decimal import Decimal

from pydantic import BaseModel, Field

from app.shared.config.base import ConfigBase


class TechnicalIndicatorThresholds(ConfigBase):
    """Configuration for technical indicator thresholds."""

    # RSI thresholds
    rsi_oversold: float = Field(default=30.0, description="RSI oversold threshold")
    rsi_overbought: float = Field(default=70.0, description="RSI overbought threshold")

    # Mean reversion specific
    mean_reversion_entry_z_score: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Z-score threshold for mean reversion entry"
    )
    mean_reversion_exit_z_score: float = Field(
        default=0.5, ge=0.0, le=2.0, description="Z-score threshold for mean reversion exit"
    )
    mean_reversion_lookback_period: int = Field(
        default=20, ge=5, le=100, description="Lookback period for mean reversion"
    )

    # Pairs trading correlation
    pairs_trading_correlation_lookback: int = Field(
        default=30, ge=10, le=252, description="Lookback period for correlation calculation"
    )
    pairs_trading_min_correlation: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum correlation for pairs trading"
    )
    pairs_trading_entry_z_score: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Z-score threshold for pairs entry"
    )
    pairs_trading_exit_z_score: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Z-score threshold for pairs exit"
    )
    pairs_trading_max_pair_exposure: float = Field(
        default=0.10, ge=0.01, le=0.5, description="Maximum exposure per pair"
    )

    # Spread threshold for pairs
    spread_threshold_half_divisor: float = Field(
        default=2.0, ge=1.1, le=10.0, description="Divisor for half spread threshold"
    )
    cointegration_relaxed_multiplier: float = Field(
        default=0.8, ge=0.1, le=1.0, description="Multiplier for relaxed cointegration threshold"
    )


class WindowSizes(ConfigBase):
    """Configuration for window sizes and history lengths."""

    # Momentum windows
    momentum_short_window: int = Field(default=10, ge=3, le=50, description="Short window for momentum")
    momentum_long_window: int = Field(default=30, ge=10, le=200, description="Long window for momentum")

    # Moving average windows
    ma_short_window: int = Field(default=10, ge=3, le=50, description="Short MA window")
    ma_long_window: int = Field(default=30, ge=10, le=200, description="Long MA window")

    # Volatility windows
    volatility_window: int = Field(default=20, ge=5, le=100, description="Volatility calculation window")
    atr_window: int = Field(default=14, ge=5, le=50, description="ATR calculation window")

    # Volume windows
    volume_ma_window: int = Field(default=20, ge=5, le=100, description="Volume MA window")

    # History lengths
    min_history_length: int = Field(default=60, ge=30, le=200, description="Minimum history length for signals")
    auto_train_min_history: int = Field(
        default=100, ge=50, le=500, description="Minimum history for auto-training"
    )

    # Deep learning sequence lengths
    default_sequence_length: int = Field(default=60, ge=20, le=200, description="Default sequence length")
    transformer_sequence_length: int = Field(default=30, ge=10, le=100, description="Transformer sequence length")


class ConversionMultipliers(ConfigBase):
    """Configuration for conversion multipliers."""

    # Basis points conversion
    bps_multiplier: int = Field(default=10000, ge=1, le=100000, description="Multiplier for basis points conversion")

    # Percentage conversion
    percentage_multiplier: int = Field(default=100, ge=1, le=1000, description="Multiplier for percentage conversion")

    # Milliseconds conversion
    milliseconds_multiplier: int = Field(default=1000, ge=1, le=10000, description="Multiplier for ms conversion")

    # Time conversions
    seconds_per_day: int = Field(default=86400, ge=1, le=100000, description="Seconds per day")


class PerformanceMetrics(ConfigBase):
    """Configuration for performance metric thresholds."""

    # Sharpe ratio
    min_sharpe_ratio: float = Field(default=1.0, ge=0.0, le=10.0, description="Minimum Sharpe ratio")

    # Fill rate
    min_fill_rate: float = Field(default=0.95, ge=0.0, le=1.0, description="Minimum fill rate")

    # Confidence levels
    high_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="High confidence threshold")
    medium_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Medium confidence threshold")
    low_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Low confidence threshold")


class FundamentalAnalysisThresholds(ConfigBase):
    """Configuration for fundamental analysis parameters."""

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

    # Dividend coverage
    dividend_coverage_excellent: float = Field(default=2.0, ge=1.0, le=10.0, description="Excellent dividend coverage")
    dividend_coverage_good: float = Field(default=1.5, ge=1.0, le=5.0, description="Good dividend coverage")

    # Score thresholds
    dividend_buy_score: float = Field(default=70.0, ge=0.0, le=100.0, description="Dividend buy score threshold")
    dividend_hold_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Dividend hold score threshold")


class DividendThresholds(ConfigBase):
    """Configuration for dividend investing parameters."""

    # Minimum dividend yield
    min_dividend_yield: float = Field(default=0.02, ge=0.0, le=0.2, description="Minimum dividend yield (2%)")
    max_dividend_yield: float = Field(default=0.10, ge=0.0, le=0.5, description="Maximum dividend yield (10%)")

    # Dividend growth
    min_dividend_growth_rate: float = Field(default=0.05, ge=0.0, le=1.0, description="Minimum dividend growth rate")

    # Payout ratio
    max_payout_ratio: float = Field(default=0.7, ge=0.0, le=1.0, description="Maximum payout ratio (70%)")

    # Dividend history
    min_dividend_history_years: int = Field(default=5, ge=1, le=30, description="Minimum dividend history years")


class FXCarryTradeThresholds(ConfigBase):
    """Configuration for FX carry trade parameters."""

    # FX rate simulation
    fx_daily_variation_factor: float = Field(
        default=0.0001, ge=0.0, le=0.01, description="Daily FX rate variation factor"
    )
    fx_long_term_variation_factor: float = Field(
        default=0.00001, ge=0.0, le=0.001, description="Long-term FX rate variation factor"
    )
    fx_quantization_precision: str = Field(default="0.0001", description="FX rate quantization precision")

    # Interest rate differential
    min_interest_differential: float = Field(default=0.02, ge=0.0, le=0.2, description="Minimum interest differential")


class CoveredCallThresholds(ConfigBase):
    """Configuration for covered calls strategy."""

    # OTM percentage for calls
    otm_percentage_default: float = Field(
        default=0.05, ge=0.0, le=0.5, description="Default OTM percentage for calls (5%)"
    )
    otm_percentage_conservative: float = Field(
        default=0.02, ge=0.0, le=0.2, description="Conservative OTM percentage (2%)"
    )
    otm_percentage_aggressive: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Aggressive OTM percentage (10%)"
    )

    # Days to expiration
    default_dte: int = Field(default=30, ge=1, le=180, description="Default days to expiration")
    min_dte: int = Field(default=7, ge=1, le=30, description="Minimum days to expiration")
    max_dte: int = Field(default=90, ge=30, le=365, description="Maximum days to expiration")
