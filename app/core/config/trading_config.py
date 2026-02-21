"""
Modular Trading Configuration System

This module provides a centralized, modular configuration system for trading.
It aggregates configuration from the modular components.

Usage:
    from app.core.config.trading_config import get_config, CentralizedConfig

    config = get_config()
    print(config.trading.min_signal_strength)
    print(config.compliance.MIN_LIQUIDITY_SCORE)

Backward Compatibility:
    The centralized_config.py file imports from this module to maintain
    compatibility with existing code.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import Field

# Import modular configuration components
from app.core.config.base import Environment, SettingsBase
from decimal import Decimal
from typing import Dict
from app.core.config.compliance import ComplianceConfig, SpainTaxConfig
from app.core.config.infrastructure import (
    APIConfig,
    DatabaseConfig,
    LoggingConfig,
    MonitoringConfig,
    RedisConfig,
)
from app.core.config.position_sizing import (
    AccountConfiguration as _AccountConfiguration,
    PortfolioAllocationThresholds,
    PositionSizingThresholds,
)
from app.core.config.signal_risk import (
    CircuitBreakerThresholds,
    MarketMicrostructureThresholds,
    PerformanceThresholds,
    RiskManagementThresholds,
    SignalThresholds,
    SlippageThresholds,
    TradingCostThresholds,
)
from app.core.config.technical_indicators import (
    ConversionMultipliers,
    CoveredCallThresholds,
    DividendThresholds,
    FXCarryTradeThresholds,
    FundamentalAnalysisThresholds,
    PerformanceMetrics,
    TechnicalIndicatorThresholds,
    WindowSizes,
)

# Import modular strategy configs
from app.core.strategy_config import (
    DividendStrategyConfig,
    FXCarryTradeStrategyConfig,
    MomentumModularConfig,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# AGGREGATED TRADING THRESHOLDS
# =============================================================================

class TradingThresholds(BaseModel):
    """
    Centralized trading thresholds.

    This class aggregates all trading-related configuration from
    the modular components for backward compatibility.
    """

    # Signal thresholds
    min_signal_strength: float = Field(default=60.0, description="Minimum signal strength (0-100)")
    min_signal_confidence: float = Field(default=70.0, description="Minimum signal confidence (0-100)")
    min_liquidity_score: float = Field(default=50.0, description="Minimum liquidity score (0-100)")
    min_strength: float = Field(default=60.0, description="Minimum strength threshold for momentum analysis")

    # Signal Scoring Engine
    signal_cooldown_minutes: int = Field(default=10, description="Signal cooldown period in minutes")
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
    signal_high_priority_threshold: float = Field(default=80.0, description="High priority threshold (0-100)")
    signal_medium_priority_threshold: float = Field(default=50.0, description="Medium priority threshold (0-100)")

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
    capital_loss_threshold: float = Field(default=0.40, description="Capital loss threshold for deployment decisions (0-1)")
    max_cost_impact_ratio: float = Field(default=0.30, description="Maximum cost impact ratio (Chan's 30% threshold) (0-1)")
    low_volatility_portfolio_threshold: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Volatility threshold for low volatility portfolio classification (15%)"
    )
    risk_free_rate: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Risk-free rate for Sharpe/Sortino calculations (2%)"
    )
    p_value_significance_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="P-value threshold for statistical significance testing (5%)"
    )

    # Dividend Investing Strategy
    dividend_min_yield: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Minimum dividend yield for dividend investing strategy (2%)"
    )
    dividend_min_weight: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Minimum position weight for dividend portfolio construction (2%)"
    )

    # Time Series Momentum Strategy
    momentum_volatility_target: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Target annual volatility for momentum position sizing (15%)"
    )
    momentum_volatility_floor: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Minimum volatility floor to prevent division by zero (1%)"
    )
    momentum_fixed_max_position: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Max position size for fixed position sizing (50%)"
    )
    momentum_default_max_position: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Default max position size for momentum strategy (30%)"
    )

    # Portfolio limits
    max_total_exposure: float = Field(default=0.8, description="Maximum total exposure (0-1)")
    max_sector_exposure: float = Field(default=0.3, description="Maximum sector exposure (0-1)")
    max_correlation: float = Field(default=0.7, description="Maximum correlation between positions")

    # Circuit breakers
    circuit_breaker_daily_loss: float = Field(default=0.05, description="Circuit breaker daily loss threshold")
    circuit_breaker_drawdown: float = Field(default=0.1, description="Circuit breaker drawdown threshold")
    circuit_breaker_volatility: float = Field(default=0.05, description="Circuit breaker volatility threshold")
    circuit_breaker_error_rate: float = Field(default=0.05, description="Circuit breaker error rate threshold")

    # Performance thresholds
    max_latency_ms: int = Field(default=1000, description="Maximum acceptable latency in milliseconds")
    max_execution_time_ms: int = Field(default=500, description="Maximum execution time in milliseconds")

    # Multi-Strategy Allocation
    momentum_target_weight: float = Field(default=0.50, description="Momentum strategy target weight")
    mean_reversion_target_weight: float = Field(default=0.25, description="Mean reversion strategy target weight")
    pairs_trading_target_weight: float = Field(default=0.25, description="Pairs trading strategy target weight")

    # Risk Management
    max_risk_per_trade: float = Field(default=0.02, description="Maximum risk per trade (0-1)")
    min_risk_reward_ratio: float = Field(default=3.0, description="Minimum risk/reward ratio")
    max_momentum_exposure: float = Field(default=0.50, description="Max momentum exposure (0-1)")
    max_mean_reversion_exposure: float = Field(default=0.30, description="Max mean reversion exposure (0-1)")
    max_pairs_trading_exposure: float = Field(default=0.30, description="Max pairs trading exposure (0-1)")
    max_consecutive_stops: int = Field(default=5, description="Max consecutive stops before pause")

    # Portfolio Rebalancing
    rebalance_frequency_days: int = Field(default=30, description="Rebalancing frequency in days")
    rebalance_drift_threshold: float = Field(default=0.05, description="Rebalance drift threshold (0-1)")
    min_allocation_weight: float = Field(default=0.10, description="Minimum allocation weight (0-1)")
    max_allocation_weight: float = Field(default=0.70, description="Maximum allocation weight (0-1)")
    capital_adjustment_factor: float = Field(default=0.20, description="Capital adjustment factor per negative streak (0-1)")

    # ATR Volatility Filter
    min_atr_threshold: float = Field(default=0.015, description="Minimum ATR threshold for volatility filtering (0-1)")
    atr_filter_enabled: bool = Field(default=True, description="Enable ATR volatility filter to avoid choppy markets")
    trailing_stop_distance_pct: float = Field(default=0.02, description="Trailing stop distance percentage (0-1)")
    trailing_stop_enabled: bool = Field(default=True, description="Enable trailing stop for dynamic exits")

    # Validator parameters
    validator_default_max_position_pct: float = Field(default=0.25, description="Default max position as % of capital")
    validator_min_position_pct: float = Field(default=0.01, description="Minimum position as % of capital")
    validator_max_position_pct: float = Field(default=0.50, description="Maximum position as % of capital")
    validator_stop_loss_warning_pct: float = Field(default=0.10, description="Warning threshold for stop-loss distance")
    validator_min_reward_risk_ratio: float = Field(default=2.0, description="Minimum reward/risk ratio")

    # Conversion multipliers
    bps_multiplier: int = Field(default=10000, description="Multiplier for basis points conversion")
    percentage_multiplier: int = Field(default=100, description="Multiplier for percentage conversion")
    milliseconds_multiplier: int = Field(default=1000, description="Multiplier for milliseconds conversion")
    seconds_per_day: int = Field(default=86400, description="Seconds per day")

    # Spread and pairs trading
    spread_threshold_half_divisor: float = Field(default=2.0, description="Divisor for half spread threshold")
    cointegration_relaxed_multiplier: float = Field(default=0.8, description="Multiplier for relaxed cointegration threshold")

    # Performance metrics
    min_sharpe_ratio: float = Field(default=1.0, description="Minimum Sharpe ratio threshold")
    min_fill_rate: float = Field(default=0.95, description="Minimum fill rate threshold")
    high_confidence_threshold: float = Field(default=0.8, description="High confidence threshold")
    medium_confidence_threshold: float = Field(default=0.7, description="Medium confidence threshold")
    low_confidence_threshold: float = Field(default=0.5, description="Low confidence threshold")

    # Crypto fallback prices (used when API is unavailable)
    crypto_fallback_prices: Dict[str, Decimal] = Field(
        default_factory=lambda: {
            "BTC": Decimal("95000"),
            "ETH": Decimal("3500"),
            "BNB": Decimal("650"),
            "SOL": Decimal("200"),
            "XRP": Decimal("1.20"),
            "ADA": Decimal("0.60"),
            "DOGE": Decimal("0.15"),
            "DOT": Decimal("8.00"),
            "MATIC": Decimal("0.50"),
            "LINK": Decimal("15.00"),
        },
        description="Fallback crypto prices when API is unavailable"
    )

    # Fallback Strategy Parameters
    fallback_conservative_annual_return: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Conservative annual return for fallback backtest strategy (5% = 0.05)"
    )
    fallback_expected_max_drawdown: float = Field(
        default=-0.15,
        ge=-1.0,
        le=0.0,
        description="Expected maximum drawdown for fallback backtest strategy (-15% = -0.15)"
    )
    fallback_conservative_sharpe_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Conservative Sharpe ratio for fallback backtest strategy"
    )
    fallback_feasibility_ratio: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Feasibility ratio for fallback backtest strategy"
    )

    # Position Sizing Optimization Parameters
    position_size_small_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Threshold below which position size is considered 'small' for sizing strategy (5% = 0.05)"
    )

    # Market Impact Calculation Parameters
    market_impact_large_order_threshold: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Volume ratio threshold for large orders (>10% of avg volume = 0.10)"
    )
    market_impact_medium_order_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Volume ratio threshold for medium orders (>5% of avg volume = 0.05)"
    )
    market_impact_large_order_rate: float = Field(
        default=0.005,
        ge=0.0,
        le=0.1,
        description="Market impact rate for large orders (0.5% = 0.005)"
    )
    market_impact_medium_order_rate: float = Field(
        default=0.002,
        ge=0.0,
        le=0.1,
        description="Market impact rate for medium orders (0.2% = 0.002)"
    )
    market_impact_small_order_rate: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.1,
        description="Market impact rate for small orders (0.05% = 0.0005)"
    )

    # Cost Analysis Parameters
    borrowing_cost_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Annual borrowing cost rate for short positions (5% = 0.05)"
    )
    annual_trading_days_const: int = Field(
        default=252,
        ge=200,
        le=365,
        description="Number of trading days per year (252 is standard for US markets)"
    )

    # Fundamental Law of Active Management thresholds
    breadth_high_threshold: Decimal = Field(
        default=Decimal("1000"),
        description="High breadth threshold for Fundamental Law analysis"
    )
    breadth_medium_threshold: Decimal = Field(
        default=Decimal("100"),
        description="Medium breadth threshold for Fundamental Law analysis"
    )

    # Reconciliation tolerance thresholds (R16)
    reconciliation_quantity_tolerance: float = Field(
        default=1.0, ge=0.0, le=100.0,
        description="Quantity tolerance for reconciliation (shares)"
    )
    reconciliation_price_tolerance_pct: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Price tolerance for reconciliation (0.1%)"
    )
    reconciliation_value_tolerance_pct: float = Field(
        default=0.005, ge=0.0, le=0.5,
        description="Value tolerance for reconciliation (0.5%)"
    )

    # Pairs trading specific thresholds
    pairs_trading_sell_exposure_limit: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Max exposure for SELL operations in pairs trading (15%)"
    )
    pairs_trading_default_volatility: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Default volatility when price history is unavailable (2%)"
    )
    pairs_trading_default_correlation: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Default correlation when price history is unavailable (75%)"
    )
    pairs_trading_default_cointegration: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Default cointegration score when price history is unavailable (75%)"
    )
    pairs_trading_min_history_length: int = Field(
        default=250, ge=10, le=1000,
        description="Minimum price history length for pairs trading calculations"
    )
    pairs_trading_history_length: int = Field(
        default=250, ge=10, le=1000,
        description="Price history length for pairs trading (days)"
    )
    pairs_trading_default_spread: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Default spread for pairs trading signal metadata (2%)"
    )

    # Ernest Chan risk management parameters
    chan_atr_multiplier: float = Field(
        default=2.0, ge=1.0, le=5.0,
        description="ATR multiplier for Chan stop-loss calculation (Ernest Chan recommends 2-3x)"
    )
    chan_fixed_stop_pct: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Fixed percentage stop loss for Chan methods (5%)"
    )
    volatility_threshold_extreme: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Extreme volatility threshold for position sizing (%)"
    )

    # Risk tolerance level parameters (for InputProfileRouter)
    # LOW risk tolerance
    risk_low_max_drawdown: float = Field(default=0.15, ge=0.0, le=0.5, description="Max drawdown for LOW risk tolerance (15%)")
    risk_low_max_volatility: float = Field(default=0.20, ge=0.0, le=1.0, description="Max volatility for LOW risk tolerance (20%)")
    risk_low_max_position: float = Field(default=0.05, ge=0.0, le=0.5, description="Max position size for LOW risk tolerance (5%)")
    risk_low_atr_multiplier: float = Field(default=2.0, ge=1.0, le=5.0, description="ATR multiplier for LOW risk tolerance stop loss")
    risk_low_take_profit_multiplier: float = Field(default=3.0, ge=1.0, le=10.0, description="Take profit multiplier for LOW risk tolerance")
    risk_low_var_confidence: float = Field(default=0.95, ge=0.5, le=0.99, description="VaR confidence for LOW risk tolerance")
    risk_low_es_confidence: float = Field(default=0.95, ge=0.5, le=0.99, description="Expected shortfall confidence for LOW risk tolerance")

    # MEDIUM risk tolerance
    risk_medium_max_drawdown: float = Field(default=0.25, ge=0.0, le=0.5, description="Max drawdown for MEDIUM risk tolerance (25%)")
    risk_medium_max_volatility: float = Field(default=0.30, ge=0.0, le=1.0, description="Max volatility for MEDIUM risk tolerance (30%)")
    risk_medium_max_position: float = Field(default=0.10, ge=0.0, le=0.5, description="Max position size for MEDIUM risk tolerance (10%)")
    risk_medium_max_leverage: float = Field(default=1.5, ge=1.0, le=3.0, description="Max leverage for MEDIUM risk tolerance (1.5x)")
    risk_medium_atr_multiplier: float = Field(default=2.5, ge=1.0, le=5.0, description="ATR multiplier for MEDIUM risk tolerance stop loss")
    risk_medium_take_profit_multiplier: float = Field(default=4.0, ge=1.0, le=10.0, description="Take profit multiplier for MEDIUM risk tolerance")
    risk_medium_var_confidence: float = Field(default=0.95, ge=0.5, le=0.99, description="VaR confidence for MEDIUM risk tolerance")
    risk_medium_es_confidence: float = Field(default=0.95, ge=0.5, le=0.99, description="Expected shortfall confidence for MEDIUM risk tolerance")

    # HIGH risk tolerance
    risk_high_max_drawdown: float = Field(default=0.40, ge=0.0, le=0.8, description="Max drawdown for HIGH risk tolerance (40%)")
    risk_high_max_volatility: float = Field(default=0.50, ge=0.0, le=1.0, description="Max volatility for HIGH risk tolerance (50%)")
    risk_high_max_position: float = Field(default=0.20, ge=0.0, le=0.5, description="Max position size for HIGH risk tolerance (20%)")
    risk_high_max_leverage: float = Field(default=2.0, ge=1.0, le=3.0, description="Max leverage for HIGH risk tolerance (2x)")
    risk_high_atr_multiplier: float = Field(default=3.0, ge=1.0, le=5.0, description="ATR multiplier for HIGH risk tolerance stop loss")
    risk_high_take_profit_multiplier: float = Field(default=6.0, ge=1.0, le=10.0, description="Take profit multiplier for HIGH risk tolerance")
    risk_high_var_confidence: float = Field(default=0.99, ge=0.5, le=0.999, description="VaR confidence for HIGH risk tolerance")
    risk_high_es_confidence: float = Field(default=0.975, ge=0.5, le=0.999, description="Expected shortfall confidence for HIGH risk tolerance")

    # Optimization configuration (for InputProfileRouter)
    opt_lookback_short: int = Field(default=63, ge=10, le=500, description="Short lookback period (3 months)")
    opt_lookback_medium: int = Field(default=126, ge=10, le=500, description="Medium lookback period (6 months)")
    opt_lookback_long: int = Field(default=252, ge=10, le=500, description="Long lookback period (1 year)")
    opt_min_weight_low: float = Field(default=0.01, ge=0.0, le=0.1, description="Min weight for LOW risk tolerance optimization")
    opt_max_weight_low: float = Field(default=0.05, ge=0.0, le=0.5, description="Max weight for LOW risk tolerance optimization")
    opt_min_weight_medium: float = Field(default=0.02, ge=0.0, le=0.1, description="Min weight for MEDIUM risk tolerance optimization")
    opt_max_weight_medium: float = Field(default=0.10, ge=0.0, le=0.5, description="Max weight for MEDIUM risk tolerance optimization")
    opt_min_weight_high: float = Field(default=0.02, ge=0.0, le=0.1, description="Min weight for HIGH risk tolerance optimization")
    opt_max_weight_high: float = Field(default=0.20, ge=0.0, le=0.5, description="Max weight for HIGH risk tolerance optimization")
    opt_max_turnover: float = Field(default=0.50, ge=0.0, le=1.0, description="Max portfolio turnover (50%)")

    # Constraint configuration (for InputProfileRouter)
    constraint_capital_small: float = Field(default=10000.0, ge=0.0, description="Small portfolio capital threshold")
    constraint_capital_medium: float = Field(default=100000.0, ge=0.0, description="Medium portfolio capital threshold")
    constraint_max_pos_small: int = Field(default=10, ge=1, le=50, description="Max positions for small portfolios")
    constraint_max_pos_medium: int = Field(default=25, ge=1, le=100, description="Max positions for medium portfolios")
    constraint_max_pos_large: int = Field(default=50, ge=1, le=200, description="Max positions for large portfolios")
    constraint_min_liquidity_low: float = Field(default=0.5, ge=0.0, le=1.0, description="Min liquidity score for small portfolios")
    constraint_min_liquidity_high: float = Field(default=0.7, ge=0.0, le=1.0, description="Min liquidity score for large portfolios")
    constraint_sector_exposure_low: float = Field(default=0.25, ge=0.0, le=1.0, description="Max sector exposure for LOW risk (25%)")
    constraint_sector_exposure_high: float = Field(default=0.40, ge=0.0, le=1.0, description="Max sector exposure for MEDIUM/HIGH risk (40%)")
    constraint_capital_liquidity: float = Field(default=50000.0, ge=0.0, description="Capital threshold for high liquidity requirement")

    # Strategy-specific configuration (for InputProfileRouter)
    strat_mom_lookback: int = Field(default=252, ge=10, le=500, description="Momentum strategy lookback period (days)")
    strat_mom_top_pct: float = Field(default=0.3, ge=0.0, le=1.0, description="Momentum strategy top percentile (30%)")
    strat_mom_bottom_pct: float = Field(default=0.3, ge=0.0, le=1.0, description="Momentum strategy bottom percentile (30%)")
    strat_div_min_yield: float = Field(default=0.02, ge=0.0, le=0.5, description="Dividend strategy minimum yield (2%)")
    strat_div_max_yield: float = Field(default=0.10, ge=0.0, le=1.0, description="Dividend strategy maximum yield (10%)")
    strat_div_min_growth: float = Field(default=0.0, ge=-1.0, le=1.0, description="Dividend strategy minimum dividend growth rate")
    strat_div_max_payout: float = Field(default=0.8, ge=0.0, le=1.0, description="Dividend strategy maximum payout ratio (80%)")
    strat_div_min_years: int = Field(default=5, ge=1, le=20, description="Dividend strategy minimum years of dividends")
    strat_lv_max_beta: float = Field(default=0.8, ge=0.0, le=2.0, description="Low volatility strategy maximum beta")
    strat_lv_max_vol: float = Field(default=0.25, ge=0.0, le=1.0, description="Low volatility strategy maximum volatility (25%)")
    strat_mf_weight_value: float = Field(default=0.25, ge=0.0, le=1.0, description="Multi-factor value weight")
    strat_mf_weight_size: float = Field(default=0.25, ge=0.0, le=1.0, description="Multi-factor size weight")
    strat_mf_weight_momentum: float = Field(default=0.25, ge=0.0, le=1.0, description="Multi-factor momentum weight")
    strat_mf_weight_quality: float = Field(default=0.25, ge=0.0, le=1.0, description="Multi-factor quality weight")

    # Covered Call Strategy Configuration
    covered_call_max_position_size: float = Field(
        default=0.10, ge=0.0, le=0.5,
        description="Maximum position size for covered call strategy (10%)"
    )
    covered_call_target_otm_pct: float = Field(
        default=0.03, ge=0.0, le=0.20,
        description="Target out-of-the-money percentage for covered calls (3%)"
    )
    covered_call_min_premium_pct: float = Field(
        default=0.01, ge=0.0, le=0.10,
        description="Minimum premium percentage for covered calls (1%)"
    )
    covered_call_roll_threshold_itm: float = Field(
        default=0.02, ge=0.0, le=0.20,
        description="In-the-money threshold for rolling covered calls (2%)"
    )
    covered_call_roll_threshold_otm: float = Field(
        default=0.05, ge=0.0, le=0.50,
        description="Out-of-the-money threshold for rolling covered calls (5%)"
    )
    covered_call_strike_tolerance: float = Field(
        default=0.02, ge=0.0, le=0.10,
        description="Strike selection tolerance for covered calls (2%)"
    )
    covered_call_max_total_exposure: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Maximum total exposure for covered call strategy (30%)"
    )
    covered_call_min_moneyness_multiplier: float = Field(
        default=0.5, ge=0.1, le=1.0,
        description="Minimum moneyness multiplier for screening (0.5x target OTM)"
    )
    covered_call_max_moneyness_multiplier: float = Field(
        default=2.0, ge=1.0, le=5.0,
        description="Maximum moneyness multiplier for screening (2.0x target OTM)"
    )
    covered_call_min_otm_pct: float = Field(
        default=0.01, ge=0.0, le=0.10,
        description="Minimum allowed OTM percentage for validation (1%)"
    )
    covered_call_max_otm_pct: float = Field(
        default=0.20, ge=0.10, le=0.50,
        description="Maximum allowed OTM percentage for validation (20%)"
    )
    covered_call_min_premium_lower: float = Field(
        default=0.005, ge=0.0, le=0.05,
        description="Minimum premium lower bound for validation (0.5%)"
    )
    covered_call_min_premium_upper: float = Field(
        default=0.10, ge=0.05, le=0.50,
        description="Minimum premium upper bound for validation (10%)"
    )
    covered_call_min_position_size: float = Field(
        default=0.01, ge=0.0, le=0.10,
        description="Minimum position size for validation (1%)"
    )
    covered_call_max_position_upper: float = Field(
        default=0.50, ge=0.10, le=1.0,
        description="Maximum position size upper bound for validation (50%)"
    )

    # Asset universe configuration (for paper trading/test environments)
    asset_universe_equity_max_spread: float = Field(
        default=0.01, ge=0.0, le=0.1,
        description="Maximum spread for equity assets in paper trading (1%)"
    )
    asset_universe_equity_min_volume: float = Field(
        default=1000000.0, ge=0.0,
        description="Minimum daily volume for equity assets in paper trading"
    )
    asset_universe_crypto_max_spread: float = Field(
        default=0.005, ge=0.0, le=0.1,
        description="Maximum spread for crypto assets in paper trading (0.5%)"
    )
    asset_universe_crypto_min_volume: float = Field(
        default=10000000.0, ge=0.0,
        description="Minimum daily volume for crypto assets in paper trading"
    )

    # Market regime mock data defaults (for paper trading/test environments)
    market_regime_default_confidence: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Default confidence for market regime detection"
    )
    market_regime_default_atr_ratio: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Default ATR ratio for market regime detection"
    )
    market_regime_default_trend_strength: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Default trend strength for market regime detection"
    )
    market_regime_default_volatility_level: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Default volatility level for market regime detection"
    )

    # Multi-asset portfolio configuration
    portfolio_rebalance_threshold: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Portfolio rebalance threshold (5%)"
    )
    portfolio_tolerance_pct: float = Field(
        default=0.01, ge=0.0, le=0.1,
        description="Portfolio tolerance for reconciliation (1%)"
    )
    portfolio_max_deviation_warning: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Max deviation before warning (5%)"
    )
    portfolio_max_deviation_moderate: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Max deviation before moderate risk alert (10%)"
    )
    portfolio_max_deviation_high: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Max deviation before high risk alert (15%)"
    )
    portfolio_tax_rate: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Default tax rate for portfolio calculations (25%)"
    )
    portfolio_risk_free_rate: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Risk-free rate for portfolio calculations (2%)"
    )
    portfolio_income_need_min: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="Minimum income need for portfolio allocation (3%)"
    )
    portfolio_income_need_max: float = Field(
        default=0.08, ge=0.0, le=1.0,
        description="Maximum income need for portfolio allocation (8%)"
    )

    # Portfolio analytics configuration
    analytics_benchmark_return: float = Field(
        default=0.08, ge=0.0, le=1.0,
        description="Benchmark return for portfolio analytics (8%)"
    )
    analytics_var_95_confidence: float = Field(
        default=0.95, ge=0.5, le=0.99,
        description="VaR 95% confidence level"
    )
    analytics_var_99_confidence: float = Field(
        default=0.99, ge=0.5, le=0.99,
        description="VaR 99% confidence level"
    )
    analytics_rebalance_threshold: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Rebalancing threshold for portfolio (5%)"
    )
    analytics_target_equity_allocation: float = Field(
        default=0.60, ge=0.0, le=1.0,
        description="Target equity allocation for default portfolio (60%)"
    )
    analytics_target_cash_allocation: float = Field(
        default=0.40, ge=0.0, le=1.0,
        description="Target cash allocation for default portfolio (40%)"
    )
    analytics_sharpe_ratio_threshold: float = Field(
        default=0.5, ge=0.0, le=5.0,
        description="Sharpe ratio threshold for recommendations (0.5)"
    )
    analytics_annualized_return_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Annualized return threshold for recommendations (5%)"
    )
    analytics_volatility_high_threshold: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="High volatility threshold (20%)"
    )
    analytics_volatility_extreme_threshold: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Extreme volatility threshold (30%)"
    )
    analytics_largest_position_high_threshold: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="High largest position threshold (20%)"
    )
    analytics_largest_position_extreme_threshold: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Extreme largest position threshold (30%)"
    )
    analytics_max_drawdown_high_threshold: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="High max drawdown threshold (20%)"
    )
    analytics_var_95_high_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="High VaR 95% threshold (10%)"
    )
    analytics_cash_ratio_high_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="High cash ratio threshold (50%)"
    )
    analytics_risk_score_low_threshold: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Low risk score threshold (25%)"
    )
    analytics_risk_score_moderate_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Moderate risk score threshold (50%)"
    )
    analytics_risk_score_high_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="High risk score threshold (75%)"
    )
    analytics_default_average_correlation: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Default average correlation for mock data (30%)"
    )
    analytics_risk_impact_factor: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Risk impact factor per 1% allocation change (0.1%)"
    )
    analytics_return_impact_factor: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Return impact factor per 1% allocation change (0.05%)"
    )
    analytics_mock_daily_return: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Mock daily return for portfolio value calculation (0.1%)"
    )
    analytics_volatility_max_score: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Max volatility for risk score calculation (20%)"
    )
    analytics_concentration_max_score: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Max concentration for risk score calculation (20%)"
    )
    analytics_max_performance_return: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Max annualized return for health score (20%)"
    )
    analytics_max_risk_score: float = Field(
        default=0.50, ge=0.0, le=1.0,
        description="Max risk score for health score calculation (50%)"
    )
    analytics_well_diversified_positions: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Max effective positions for well diversified (10%)"
    )
    analytics_min_position_count_diversified: int = Field(
        default=5, ge=1, le=50,
        description="Minimum position count for good diversification (5)"
    )
    analytics_tail_ratio_size: float = Field(
        default=0.1, ge=0.01, le=0.5,
        description="Tail size for tail ratio calculation (10%)"
    )

    # Transaction costs by asset class (per trade)
    tx_cost_equity: float = Field(
        default=0.0005, ge=0.0, le=0.1,
        description="Transaction cost for equity (0.05%)"
    )
    tx_cost_crypto: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Transaction cost for crypto (0.1%)"
    )
    tx_cost_forex: float = Field(
        default=0.0001, ge=0.0, le=0.1,
        description="Transaction cost for forex (0.01%)"
    )
    tx_cost_fixed_income: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Transaction cost for fixed income (0.1%)"
    )
    tx_cost_commodity: float = Field(
        default=0.0005, ge=0.0, le=0.1,
        description="Transaction cost for commodities (0.05%)"
    )
    tx_cost_real_estate: float = Field(
        default=0.001, ge=0.0, le=0.1,
        description="Transaction cost for real estate (0.1%)"
    )

    # Fundamental Law of Active Management thresholds
    fundamental_law_ic_excellent: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="IC threshold for excellent skill level (5%)"
    )
    fundamental_law_ic_good: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="IC threshold for good skill level (3%)"
    )
    fundamental_law_ic_fair: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="IC threshold for fair skill level (1%)"
    )
    fundamental_law_ir_excellent: float = Field(
        default=1.0, ge=0.0, le=10.0,
        description="IR threshold for excellent (1.0)"
    )
    fundamental_law_ir_good: float = Field(
        default=0.5, ge=0.0, le=10.0,
        description="IR threshold for good (0.5)"
    )
    fundamental_law_ir_fair: float = Field(
        default=0.25, ge=0.0, le=10.0,
        description="IR threshold for fair (0.25)"
    )
    fundamental_law_tc_excellent: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="TC threshold for excellent (80%)"
    )
    fundamental_law_tc_good: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="TC threshold for good (60%)"
    )
    fundamental_law_tc_fair: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="TC threshold for fair (40%)"
    )
    fundamental_law_trading_days_per_year: int = Field(
        default=252, ge=1, le=365,
        description="Number of trading days per year for IR calculation"
    )

    # Signal quality calculation thresholds
    signal_spread_excellent: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Spread threshold for excellent signal quality (1%)"
    )
    signal_spread_poor: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Spread threshold for poor signal quality (5%)"
    )
    signal_volume_high: float = Field(
        default=1000000.0, ge=0.0,
        description="High volume threshold for signal quality (1M shares)"
    )
    signal_volume_low: float = Field(
        default=100000.0, ge=0.0,
        description="Low volume threshold for signal quality (100K shares)"
    )
    signal_volume_very_high: float = Field(
        default=5000000.0, ge=0.0,
        description="Very high volume threshold for signal quality (5M shares)"
    )
    signal_ema_trend_strong: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Strong EMA trend threshold (2%)"
    )
    signal_spread_very_tight: float = Field(
        default=0.005, ge=0.0, le=1.0,
        description="Very tight spread threshold for liquidity (0.5%)"
    )
    signal_spread_acceptable: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Acceptable spread threshold for liquidity (10%)"
    )
    signal_spread_very_wide: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Very wide spread threshold for liquidity penalty (20%)"
    )

    # Signal volatility thresholds
    signal_volatility_default: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Default volatility for signal scoring (2%)"
    )
    signal_volatility_optimal_min: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Optimal minimum volatility for signal quality (1%)"
    )
    signal_volatility_optimal_max: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="Optimal maximum volatility for signal quality (3%)"
    )
    signal_volatility_acceptable_min: float = Field(
        default=0.005, ge=0.0, le=1.0,
        description="Acceptable minimum volatility (0.5%)"
    )
    signal_volatility_acceptable_max: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Acceptable maximum volatility (5%)"
    )
    signal_volatility_high_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="High volatility threshold (5%)"
    )
    signal_volatility_low_threshold: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Low volatility threshold (1%)"
    )
    signal_volatility_moderate_threshold: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Moderate volatility threshold for good trading (2%)"
    )
    signal_volatility_atr_high: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="High ATR ratio threshold (3%)"
    )
    signal_volatility_atr_low: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Low ATR ratio threshold (1%)"
    )

    # Signal spread thresholds for liquidity scoring
    signal_spread_very_low: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Very low spread threshold for excellent liquidity (0.1%)"
    )
    signal_spread_low: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Low spread threshold for good liquidity (0.2%)"
    )
    signal_spread_moderate: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Moderate spread threshold (0.5%)"
    )
    signal_spread_high: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="High spread threshold (1%)"
    )
    signal_spread_stable_low: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Low spread for price stability (0.1%)"
    )
    signal_spread_stable_moderate: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Moderate spread for price stability (0.3%)"
    )
    signal_spread_stable_high: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="High spread for price stability (0.5%)"
    )

    # Signal volume trend thresholds
    signal_volume_trend_high: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="High volume trend threshold (10%)"
    )
    signal_volume_trend_low: float = Field(
        default=-0.1, le=0.0, ge=-1.0,
        description="Low volume trend threshold (-10%)"
    )

    # Momentum confidence thresholds (for MomentumStrategyEngine)
    momentum_confidence_high_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="High momentum threshold for confidence calculation (5%)"
    )
    momentum_confidence_medium_threshold: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Medium momentum threshold for confidence calculation (2%)"
    )
    momentum_volume_ratio_high_threshold: float = Field(
        default=2.0, ge=1.0, le=10.0,
        description="High volume ratio threshold for confidence calculation (2.0x)"
    )
    momentum_volume_ratio_medium_threshold: float = Field(
        default=1.5, ge=1.0, le=10.0,
        description="Medium volume ratio threshold for confidence calculation (1.5x)"
    )
    momentum_rsi_very_oversold: float = Field(
        default=30.0, ge=0.0, le=50.0,
        description="Very oversold RSI threshold for high confidence boost (30)"
    )
    momentum_rsi_oversold: float = Field(
        default=40.0, ge=0.0, le=50.0,
        description="Oversold RSI threshold for medium confidence boost (40)"
    )
    momentum_rsi_neutral_low: float = Field(
        default=50.0, ge=0.0, le=70.0,
        description="Neutral low RSI threshold for low confidence boost (50)"
    )


    # Breakout strategy confidence thresholds
    breakout_distance_high_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="High distance ratio threshold for breakout confidence (5%)"
    )
    breakout_distance_medium_threshold: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Medium distance ratio threshold for breakout confidence (2%)"
    )
    breakout_distance_low_threshold: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Low distance ratio threshold for breakout confidence (1%)"
    )
    breakout_volume_ratio_high_threshold: float = Field(
        default=3.0, ge=1.0, le=10.0,
        description="High volume ratio threshold for breakout confidence (3.0x)"
    )
    breakout_volume_ratio_medium_threshold: float = Field(
        default=2.0, ge=1.0, le=10.0,
        description="Medium volume ratio threshold for breakout confidence (2.0x)"
    )
    # Signal bid/ask spread for mock market data
    signal_mock_spread: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Default spread for mock market data generation (1%)"
    )

    # Currency hedging configuration
    currency_urgency_immediate: float = Field(
        default=0.35, ge=0.0, le=1.0,
        description="Exposure threshold for immediate hedge urgency (35%)"
    )
    currency_urgency_normal: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Exposure threshold for normal hedge urgency (25%)"
    )
    currency_default_correlation: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Default correlation for currency pairs"
    )
    currency_hedge_rolling_base: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Base hedge ratio for rolling hedge strategy"
    )
    currency_hedge_rolling_immediate: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Hedge ratio for immediate urgency in rolling strategy"
    )
    currency_hedge_rolling_normal: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Hedge ratio for normal urgency in rolling strategy"
    )
    currency_correlation_adjustment: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Correlation adjustment factor for hedge ratio"
    )
    currency_execution_cost_factor: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Execution cost factor as fraction of spread"
    )
    currency_slippage_base_bps: float = Field(
        default=0.5, ge=0.0, le=10.0,
        description="Base slippage in basis points"
    )
    currency_size_large_threshold: float = Field(
        default=1000000.0, ge=0.0,
        description="Large contract size threshold for better rates"
    )
    currency_size_large_factor: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Size reduction factor for large contracts"
    )

    # Slippage analysis configuration
    slippage_market_stress_threshold: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Market cap ratio threshold for market stress condition (1%)"
    )
    slippage_vol_adjustment_extreme: float = Field(
        default=2.0, ge=0.0, le=10.0,
        description="Volatility adjustment factor for extreme events"
    )
    slippage_vol_adjustment_high: float = Field(
        default=1.0, ge=0.0, le=5.0,
        description="Volatility adjustment factor for high volatility"
    )
    slippage_vol_adjustment_normal: float = Field(
        default=0.2, ge=0.0, le=2.0,
        description="Volatility adjustment factor for normal conditions"
    )

    # Value at Risk (VaR) configuration
    var_max_limit_pct: float = Field(
        default=0.02, ge=0.0, le=0.1,
        description="Maximum VaR limit as percentage of portfolio (2%)"
    )
    var_confidence_level: float = Field(
        default=0.95, ge=0.5, le=0.99,
        description="Confidence level for VaR calculation (95%)"
    )
    var_lookback_days: int = Field(
        default=60, ge=10, le=250,
        description="Lookback period in days for VaR calculation"
    )
    var_warning_threshold_pct: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Warning threshold as percentage of VaR limit (80%)"
    )
    var_default_volatility: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Default annual volatility for symbols without data (20%)"
    )

    # Risk Limits Enforcer configuration
    var_enforcer_warning_limit: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="VaR warning threshold for risk limits enforcer (2%)"
    )
    var_enforcer_critical_limit: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="VaR critical threshold for risk limits enforcer (3%)"
    )
    var_enforcer_halt_limit: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="VaR halt threshold for risk limits enforcer (5%)"
    )
    risk_enforcer_max_position_pct: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Max position size for risk limits enforcer (20%)"
    )
    risk_enforcer_max_concentration_pct: float = Field(
        default=0.40, ge=0.0, le=1.0,
        description="Max concentration for risk limits enforcer (40%)"
    )
    risk_enforcer_max_leverage: float = Field(
        default=2.0, ge=1.0, le=5.0,
        description="Max leverage for risk limits enforcer (2x)"
    )
    risk_heatmap_high_threshold: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="High risk threshold for risk heatmap (15%)"
    )
    risk_heatmap_medium_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Medium risk threshold for risk heatmap (10%)"
    )
    risk_concentration_high_threshold: float = Field(
        default=60.0, ge=0.0, le=100.0,
        description="High concentration threshold (% of top 3 risk)"
    )
    risk_concentration_medium_threshold: float = Field(
        default=40.0, ge=0.0, le=100.0,
        description="Medium concentration threshold (% of top 3 risk)"
    )
    dynamic_position_max_utilization: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Max VaR utilization for dynamic position sizing (80%)"
    )
    risk_enforcer_default_volatility: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Default volatility fallback for risk attribution (20%)"
    )

    # Post-trade analysis configuration
    default_execution_quality_score: float = Field(
        default=50.0, ge=0.0, le=100.0,
        description="Default execution quality score (0-100)"
    )
    default_fill_rate: float = Field(
        default=100.0, ge=0.0, le=100.0,
        description="Default fill rate percentage (0-100%)"
    )
    slo_latency_threshold_ms: float = Field(
        default=100.0, ge=0.0,
        description="SLO latency threshold in milliseconds"
    )
    min_high_quality_execution_score: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Minimum execution quality score for high-quality execution (0-100)"
    )
    min_high_quality_fill_rate: float = Field(
        default=95.0, ge=0.0, le=100.0,
        description="Minimum fill rate for high-quality execution (0-100%)"
    )

    # Limit adjuster configuration - default limits by tier
    limit_micro_stop_loss_pct: float = Field(
        default=0.02, ge=0.0, le=0.5,
        description="Stop loss percentage for micro tier (2%)"
    )
    limit_micro_daily_loss_limit_pct: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Daily loss limit percentage for micro tier (5%)"
    )
    limit_micro_max_position_pct: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Max position percentage for micro tier (10%)"
    )
    limit_micro_leverage: float = Field(
        default=1.0, ge=1.0, le=3.0,
        description="Leverage for micro tier (1x)"
    )
    limit_micro_margin_requirement: float = Field(
        default=0.50, ge=0.0, le=1.0,
        description="Margin requirement for micro tier (50%)"
    )
    limit_micro_max_drawdown_pct: float = Field(
        default=0.10, ge=0.0, le=0.5,
        description="Max drawdown percentage for micro tier (10%)"
    )

    limit_small_stop_loss_pct: float = Field(
        default=0.025, ge=0.0, le=0.5,
        description="Stop loss percentage for small tier (2.5%)"
    )
    limit_small_daily_loss_limit_pct: float = Field(
        default=0.08, ge=0.0, le=0.5,
        description="Daily loss limit percentage for small tier (8%)"
    )
    limit_small_max_position_pct: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Max position percentage for small tier (15%)"
    )
    limit_small_leverage: float = Field(
        default=1.0, ge=1.0, le=3.0,
        description="Leverage for small tier (1x)"
    )
    limit_small_margin_requirement: float = Field(
        default=0.33, ge=0.0, le=1.0,
        description="Margin requirement for small tier (33%)"
    )
    limit_small_max_drawdown_pct: float = Field(
        default=0.15, ge=0.0, le=0.5,
        description="Max drawdown percentage for small tier (15%)"
    )

    limit_medium_stop_loss_pct: float = Field(
        default=0.03, ge=0.0, le=0.5,
        description="Stop loss percentage for medium tier (3%)"
    )
    limit_medium_daily_loss_limit_pct: float = Field(
        default=0.10, ge=0.0, le=0.5,
        description="Daily loss limit percentage for medium tier (10%)"
    )
    limit_medium_max_position_pct: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Max position percentage for medium tier (20%)"
    )
    limit_medium_leverage: float = Field(
        default=1.5, ge=1.0, le=3.0,
        description="Leverage for medium tier (1.5x)"
    )
    limit_medium_margin_requirement: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Margin requirement for medium tier (25%)"
    )
    limit_medium_max_drawdown_pct: float = Field(
        default=0.20, ge=0.0, le=0.5,
        description="Max drawdown percentage for medium tier (20%)"
    )

    limit_large_stop_loss_pct: float = Field(
        default=0.035, ge=0.0, le=0.5,
        description="Stop loss percentage for large tier (3.5%)"
    )
    limit_large_daily_loss_limit_pct: float = Field(
        default=0.15, ge=0.0, le=0.5,
        description="Daily loss limit percentage for large tier (15%)"
    )
    limit_large_max_position_pct: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Max position percentage for large tier (25%)"
    )
    limit_large_leverage: float = Field(
        default=2.0, ge=1.0, le=3.0,
        description="Leverage for large tier (2x)"
    )
    limit_large_margin_requirement: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Margin requirement for large tier (20%)"
    )
    limit_large_max_drawdown_pct: float = Field(
        default=0.25, ge=0.0, le=0.5,
        description="Max drawdown percentage for large tier (25%)"
    )

    # Volatility multipliers for limit adjustment
    limit_vol_multiplier_very_low: float = Field(
        default=1.2, ge=0.5, le=2.0,
        description="Volatility multiplier for very low volatility (expand limits)"
    )
    limit_vol_multiplier_low: float = Field(
        default=1.1, ge=0.5, le=2.0,
        description="Volatility multiplier for low volatility"
    )
    limit_vol_multiplier_normal: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="Volatility multiplier for normal volatility (baseline)"
    )
    limit_vol_multiplier_high: float = Field(
        default=0.8, ge=0.0, le=1.5,
        description="Volatility multiplier for high volatility (contract limits)"
    )
    limit_vol_multiplier_extreme: float = Field(
        default=0.5, ge=0.0, le=1.5,
        description="Volatility multiplier for extreme volatility (severe contraction)"
    )

    # Drawdown multipliers for limit adjustment
    limit_dd_multiplier_healthy: float = Field(
        default=1.0, ge=0.0, le=1.5,
        description="Drawdown multiplier for healthy state (< 5% drawdown)"
    )
    limit_dd_multiplier_caution: float = Field(
        default=0.8, ge=0.0, le=1.5,
        description="Drawdown multiplier for caution state (5-10% drawdown)"
    )
    limit_dd_multiplier_warning: float = Field(
        default=0.6, ge=0.0, le=1.5,
        description="Drawdown multiplier for warning state (10-15% drawdown)"
    )
    limit_dd_multiplier_critical: float = Field(
        default=0.3, ge=0.0, le=1.5,
        description="Drawdown multiplier for critical state (15-20% drawdown)"
    )
    limit_dd_multiplier_halt: float = Field(
        default=0.0, ge=0.0, le=1.5,
        description="Drawdown multiplier for halt state (> 20% drawdown)"
    )

    # Volatility ratio thresholds for limit adjustment
    limit_vol_ratio_very_low_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Volatility ratio threshold for very low state"
    )
    limit_vol_ratio_low_threshold: float = Field(
        default=0.9, ge=0.0, le=1.0,
        description="Volatility ratio threshold for low state"
    )
    limit_vol_ratio_normal_upper: float = Field(
        default=1.1, ge=1.0, le=2.0,
        description="Upper threshold for normal volatility ratio"
    )
    limit_vol_ratio_high_upper: float = Field(
        default=1.5, ge=1.0, le=3.0,
        description="Upper threshold for high volatility ratio"
    )

    # Drawdown thresholds for limit adjustment
    limit_dd_healthy_threshold: float = Field(
        default=0.05, ge=0.0, le=0.5,
        description="Drawdown threshold for healthy state (5%)"
    )
    limit_dd_caution_threshold: float = Field(
        default=0.10, ge=0.0, le=0.5,
        description="Drawdown threshold for caution state (10%)"
    )
    limit_dd_warning_threshold: float = Field(
        default=0.15, ge=0.0, le=0.5,
        description="Drawdown threshold for warning state (15%)"
    )
    limit_dd_critical_threshold: float = Field(
        default=0.20, ge=0.0, le=0.5,
        description="Drawdown threshold for critical state (20%)"
    )

    # Asset class configuration
    asset_class_max_volatility: float = Field(
        default=2.0, ge=0.0, le=5.0,
        description="Maximum reasonable volatility for asset class validation (200%)"
    )
    asset_class_max_expected_return: float = Field(
        default=2.0, ge=-1.0, le=5.0,
        description="Maximum reasonable expected return for asset class validation (200%)"
    )
    asset_class_min_expected_return: float = Field(
        default=-1.0, ge=-1.0, le=1.0,
        description="Minimum reasonable expected return for asset class validation (-100%)"
    )

    # Asset class typical volatility ranges (min, max as decimals)
    asset_class_equity_vol_min: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Equity minimum typical volatility (10%)"
    )
    asset_class_equity_vol_max: float = Field(
        default=0.30, ge=0.0, le=2.0,
        description="Equity maximum typical volatility (30%)"
    )
    asset_class_crypto_vol_min: float = Field(
        default=0.40, ge=0.0, le=2.0,
        description="Crypto minimum typical volatility (40%)"
    )
    asset_class_crypto_vol_max: float = Field(
        default=1.20, ge=0.0, le=3.0,
        description="Crypto maximum typical volatility (120%)"
    )
    asset_class_forex_vol_min: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Forex minimum typical volatility (5%)"
    )
    asset_class_forex_vol_max: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Forex maximum typical volatility (15%)"
    )
    asset_class_fixed_income_vol_min: float = Field(
        default=0.02, ge=0.0, le=0.5,
        description="Fixed income minimum typical volatility (2%)"
    )
    asset_class_fixed_income_vol_max: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Fixed income maximum typical volatility (10%)"
    )
    asset_class_commodity_vol_min: float = Field(
        default=0.15, ge=0.0, le=1.0,
        description="Commodity minimum typical volatility (15%)"
    )
    asset_class_commodity_vol_max: float = Field(
        default=0.40, ge=0.0, le=2.0,
        description="Commodity maximum typical volatility (40%)"
    )
    asset_class_real_estate_vol_min: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Real estate minimum typical volatility (10%)"
    )
    asset_class_real_estate_vol_max: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Real estate maximum typical volatility (25%)"
    )
    asset_class_cash_vol_min: float = Field(
        default=0.00, ge=0.0, le=0.1,
        description="Cash minimum typical volatility (0%)"
    )
    asset_class_cash_vol_max: float = Field(
        default=0.02, ge=0.0, le=0.5,
        description="Cash maximum typical volatility (2%)"
    )
    asset_class_default_vol_min: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Default minimum typical volatility (5%)"
    )
    asset_class_default_vol_max: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Default maximum typical volatility (20%)"
    )

    # Asset class typical expected return ranges (min, max as decimals)
    asset_class_equity_return_min: float = Field(
        default=0.05, ge=-0.5, le=1.0,
        description="Equity minimum typical expected return (5%)"
    )
    asset_class_equity_return_max: float = Field(
        default=0.12, ge=0.0, le=2.0,
        description="Equity maximum typical expected return (12%)"
    )
    asset_class_crypto_return_min: float = Field(
        default=-0.20, ge=-1.0, le=1.0,
        description="Crypto minimum typical expected return (-20%)"
    )
    asset_class_crypto_return_max: float = Field(
        default=0.50, ge=0.0, le=2.0,
        description="Crypto maximum typical expected return (50%)"
    )
    asset_class_forex_return_min: float = Field(
        default=-0.05, ge=-0.5, le=1.0,
        description="Forex minimum typical expected return (-5%)"
    )
    asset_class_forex_return_max: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Forex maximum typical expected return (10%)"
    )
    asset_class_fixed_income_return_min: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description="Fixed income minimum typical expected return (1%)"
    )
    asset_class_fixed_income_return_max: float = Field(
        default=0.06, ge=0.0, le=1.0,
        description="Fixed income maximum typical expected return (6%)"
    )
    asset_class_commodity_return_min: float = Field(
        default=-0.10, ge=-0.5, le=1.0,
        description="Commodity minimum typical expected return (-10%)"
    )
    asset_class_commodity_return_max: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Commodity maximum typical expected return (20%)"
    )
    asset_class_real_estate_return_min: float = Field(
        default=0.03, ge=0.0, le=1.0,
        description="Real estate minimum typical expected return (3%)"
    )
    asset_class_real_estate_return_max: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Real estate maximum typical expected return (10%)"
    )
    asset_class_cash_return_min: float = Field(
        default=0.00, ge=0.0, le=0.5,
        description="Cash minimum typical expected return (0%)"
    )
    asset_class_cash_return_max: float = Field(
        default=0.03, ge=0.0, le=0.5,
        description="Cash maximum typical expected return (3%)"
    )
    asset_class_default_return_min: float = Field(
        default=0.00, ge=-0.5, le=1.0,
        description="Default minimum typical expected return (0%)"
    )
    asset_class_default_return_max: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Default maximum typical expected return (10%)"
    )

    # Cost analysis configuration
    cost_profitability_threshold: float = Field(
        default=0.02, ge=0.0, le=1.0,
        description="Default profitability threshold for cost analysis (2%)"
    )
    cost_max_commission_rate: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Maximum allowed commission rate (10%)"
    )
    cost_max_slippage_rate: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Maximum allowed slippage rate (5%)"
    )
    # Cost impact ratio threshold (Chan's 30% threshold for trade profitability)
    max_cost_impact_ratio: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Maximum cost impact ratio (Chan's 30% threshold) (0-1)"
    )
    # Portfolio rebalancing thresholds (multi-asset rebalancer)
    portfolio_max_deviation_high: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="High priority rebalancing threshold (10%)"
    )
    portfolio_max_deviation_moderate: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Medium priority rebalancing threshold (5%)"
    )
    # Multi-factor strategy thresholds
    factor_weights_tolerance: float = Field(
        default=0.05, ge=0.0, le=0.2,
        description="Tolerance for factor weights sum deviation from 1.0 (5%)"
    )
    max_single_position_limit: float = Field(
        default=0.50, ge=0.01, le=1.0,
        description="Maximum allowed single position size (50%)"
    )
    max_total_tilt: float = Field(
        default=0.80, ge=0.1, le=2.0,
        description="Maximum total absolute tilt for factor strategies (80%)"
    )
    # FX Intermarket strategy thresholds
    fx_intermarket_min_significance: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Minimum significance for intermarket relationship (0-100)"
    )
    fx_corr_very_strong: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Very strong correlation threshold (80%)"
    )
    fx_corr_strong: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Strong correlation threshold (60%)"
    )
    fx_corr_moderate: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Moderate correlation threshold (40%)"
    )
    fx_signal_strong_threshold: float = Field(
        default=80.0, ge=0.0, le=100.0,
        description="Strong signal strength threshold (0-100)"
    )
    fx_signal_min_confidence_strong: float = Field(
        default=70.0, ge=0.0, le=100.0,
        description="Minimum confidence for strong signals (0-100)"
    )
    fx_signal_max_expected_move: float = Field(
        default=0.10, ge=0.01, le=1.0,
        description="Maximum expected daily move (10%)"
    )
    fx_signal_min_actionable_confidence: float = Field(
        default=60.0, ge=0.0, le=100.0,
        description="Minimum confidence for actionable signals (0-100)"
    )
    # Signal persistence thresholds (fundamental law)
    signal_persistence_long: float = Field(
        default=0.70, ge=0.0, le=1.0,
        description="Long signal persistence threshold (70% decay ratio)"
    )
    signal_persistence_medium: float = Field(
        default=0.40, ge=0.0, le=1.0,
        description="Medium signal persistence threshold (40% decay ratio)"
    )
    # Portfolio validation tolerances
    portfolio_value_tolerance: float = Field(
        default=0.01, ge=0.001, le=0.1,
        description="Portfolio value validation tolerance (1%)"
    )
    portfolio_allocation_tolerance: float = Field(
        default=0.01, ge=0.001, le=0.1,
        description="Portfolio allocation sum validation tolerance (1%)"
    )
    portfolio_pnl_tolerance: float = Field(
        default=0.01, ge=0.001, le=0.1,
        description="Position P&L calculation validation tolerance (1%)"
    )


# =============================================================================
# ADDITIONAL CONFIG CLASSES
# =============================================================================

class StrategyConfig(BaseModel):
    """Configuration for individual trading strategies."""

    name: str = Field(..., description="Strategy name")
    enabled: bool = Field(default=True, description="Whether the strategy is enabled")
    max_position_size: float = Field(default=0.1, description="Maximum position size (0-1)")
    stop_loss_pct: float = Field(default=0.05, description="Stop loss percentage (0-1)")
    take_profit_pct: float = Field(default=0.15, description="Take profit percentage (0-1)")
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown (0-1)")
    min_win_rate: float = Field(default=0.5, description="Minimum win rate (0-1)")
    weight: float = Field(default=0.1, description="Strategy weight in portfolio (0-1)")


class CurrencyHedgingConfig(BaseModel):
    """Configuration for currency hedging."""

    enabled: bool = Field(default=False, description="Enable currency hedging")
    hedging_strategy: str = Field(
        default="partial", description="Hedging strategy: full, partial, or rolling"
    )
    hedge_ratio: float = Field(default=0.5, description="Hedge ratio (0-1)")
    volatility_window: int = Field(default=20, description="Volatility calculation window")
    correlation_threshold: float = Field(
        default=0.7, description="Correlation threshold for hedging"
    )


class SectorCountryDiversificationConfig(BaseModel):
    """Configuration for sector and country diversification."""

    max_sector_exposure: float = Field(default=0.3, description="Maximum sector exposure (0-1)")
    max_country_exposure: float = Field(default=0.5, description="Maximum country exposure (0-1)")
    validate_on_position_add: bool = Field(default=True, description="Validate constraints when adding positions")


# =============================================================================
# MAIN CENTRALIZED CONFIG
# =============================================================================

class CentralizedConfig(SettingsBase):
    """
    Centralized configuration for the entire application.

    Note: This is an alternative configuration class for trading-specific
    contexts. The main CentralizedConfig is in app.core.centralized_config.
    Consider using that one for new code.
    """
    # This class is deprecated - use app.core.centralized_config.CentralizedConfig instead
    # Kept for backward compatibility with portfolio_analytics_service.py

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Current environment")
    debug: bool = Field(default=True, description="Debug mode")

    # Sub-configurations
    trading: TradingThresholds = Field(default_factory=TradingThresholds, description="Trading thresholds")
    trading_costs: TradingCostThresholds = Field(default_factory=TradingCostThresholds, description="Trading cost thresholds for profitability validation")
    market_microstructure: MarketMicrostructureThresholds = Field(default_factory=MarketMicrostructureThresholds, description="Market microstructure and liquidity analysis thresholds")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    currency_hedging: CurrencyHedgingConfig = Field(
        default_factory=CurrencyHedgingConfig, description="Currency hedging configuration"
    )
    diversification: SectorCountryDiversificationConfig = Field(
        default_factory=SectorCountryDiversificationConfig,
        description="Sector/country diversification configuration",
    )
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig, description="Compliance engine configuration")
    spain_tax: SpainTaxConfig = Field(default_factory=SpainTaxConfig, description="Spain-specific tax configuration (IRPF, Modelo 720)")

    # Strategy configurations
    strategies: Dict[str, StrategyConfig] = Field(default_factory=dict, description="Strategy configurations")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
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
            strategy_data = {"name": strategy_name, **updates}
            self.strategies[strategy_name] = StrategyConfig(**strategy_data)
            return True

    def validate_configuration(self) -> bool:
        """Validate the entire configuration."""
        try:
            self.trading.model_validate(self.trading.model_dump())
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
# GLOBAL CONFIG INSTANCE AND HELPER FUNCTIONS
# =============================================================================

_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CentralizedConfig()
    return _config


def set_config(config: CentralizedConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reload_config() -> CentralizedConfig:
    """Reload configuration from environment and files."""
    global _config
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


def get_spain_tax_config() -> SpainTaxConfig:
    """Get Spain-specific tax configuration (IRPF, Modelo 720)."""
    return get_config().spain_tax


# =============================================================================
# PUBLIC API EXPORTS
# =============================================================================

# Re-export AccountConfiguration with proper name
AccountConfiguration = _AccountConfiguration

__all__ = [
    # Main configuration
    "CentralizedConfig",
    "get_config",
    "set_config",
    "reload_config",
    "get_trading_threshold",
    "get_strategy_config",
    "get_compliance_config",
    "get_spain_tax_config",
    # Configuration classes
    "Environment",
    "TradingThresholds",
    "StrategyConfig",
    "DatabaseConfig",
    "RedisConfig",
    "APIConfig",
    "LoggingConfig",
    "MonitoringConfig",
    "CurrencyHedgingConfig",
    "SectorCountryDiversificationConfig",
    "ComplianceConfig",
    "SpainTaxConfig",
    # Modular components (for direct access)
    "SignalThresholds",
    "RiskManagementThresholds",
    "CircuitBreakerThresholds",
    "SlippageThresholds",
    "PerformanceThresholds",
    "MarketMicrostructureThresholds",
    "TradingCostThresholds",
    "PositionSizingThresholds",
    "PortfolioAllocationThresholds",
    "AccountConfiguration",
    "TechnicalIndicatorThresholds",
    "WindowSizes",
    "ConversionMultipliers",
    "PerformanceMetrics",
    "FundamentalAnalysisThresholds",
    "DividendThresholds",
    "FXCarryTradeThresholds",
    "CoveredCallThresholds",
]
