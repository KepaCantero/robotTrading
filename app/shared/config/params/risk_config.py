"""
Risk and Compliance Configuration

Extracted from centralized_config.py for SRP compliance.
Contains CurrencyHedgingConfig, SectorCountryDiversificationConfig, ComplianceConfig.

TASK-10: Centralización de Configuración
TASK-24: SRP Refactoring
"""

import logging
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


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
        default=70.0, ge=0.0, le=100.0, description="Minimum statistical model health score (0-100)"
    )
    MIN_CROSS_VALIDATION_SCORE: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum cross-validation score (0-1)"
    )

    # Lopez de Prado (Meta-labeling) thresholds
    MIN_META_LABELING_SIGNAL: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum meta-labeling signal strength (0-1)"
    )
    MIN_MCC_METRIC: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum Matthews Correlation Coefficient (0-1)"
    )

    # O'Hara (Microstructure) thresholds
    MIN_LIQUIDITY_SCORE: float = Field(
        default=50.0, ge=0.0, le=100.0, description="Minimum liquidity score (0-100)"
    )
    MAX_ORDER_FLOW_TOXICITY: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Maximum acceptable order flow toxicity (0-1)"
    )
    # Estimation parameters for O'Hara (when actual data not available)
    ESTIMATED_VOLATILITY: float = Field(
        default=0.02, ge=0.0, le=1.0, description="Estimated volatility when not calculable (0-1)"
    )
    ESTIMATED_SPREAD_BPS: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Estimated spread in basis points when not available",
    )
    ESTIMATED_DEPTH: float = Field(
        default=100000.0,
        ge=0.0,
        le=1_000_000.0,
        description="Estimated depth for liquidity calculation (USD)",
    )
    ESTIMATED_VOLUME: float = Field(
        default=1_000_000.0,
        ge=0.0,
        le=100_000_000.0,
        description="Estimated daily volume for liquidity calculation (USD)",
    )
    DEFAULT_ORDER_FLOW_TOXICITY: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Default order flow toxicity when not calculable (0-1)",
    )

    # Backtesting thresholds
    MIN_BACKTEST_CONFIDENCE: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum backtest confidence (0-1)"
    )
    MIN_HISTORICAL_SHARPE: float = Field(
        default=0.5, ge=-5.0, le=10.0, description="Minimum historical Sharpe ratio"
    )

    # Execution thresholds
    MIN_EXECUTION_PROBABILITY: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Minimum execution probability (0-1)"
    )
    MAX_SLIPPAGE_BPS: float = Field(
        default=10.0, ge=0.0, le=100.0, description="Maximum acceptable slippage in basis points"
    )

    # Strategy health thresholds
    MIN_STRATEGY_HEALTH: float = Field(
        default=50.0, ge=0.0, le=100.0, description="Minimum strategy health score (0-100)"
    )

    # Architecture compliance thresholds
    MIN_ARCHITECTURE_SCORE: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Minimum architecture compliance score (0-100)"
    )

    # Confidence adjustment thresholds (used across all handlers)
    # Positive adjustments
    CONF_BULL_REGIME_BONUS: float = Field(
        default=0.05, ge=0.0, le=0.5, description="Confidence bonus for bullish regime (0-1)"
    )
    CONF_LOW_VOLATILITY_BONUS: float = Field(
        default=0.05, ge=0.0, le=0.5, description="Confidence bonus for low volatility regime (0-1)"
    )

    # Negative adjustments (additive)
    CONF_BEAR_REGIME_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Confidence penalty for bearish regime (0-1)"
    )
    CONF_HIGH_VOLATILITY_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Confidence penalty for high volatility (0-1)"
    )
    CONF_POOR_LIQUIDITY_PENALTY: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Confidence penalty for poor liquidity (0-1)"
    )
    CONF_LOW_LIQUIDITY_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Confidence penalty for low liquidity (0-1)"
    )
    CONF_HIGH_TOXICITY_PENALTY: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Confidence penalty for high order flow toxicity (0-1)",
    )
    CONF_LOW_SHARPE_PENALTY: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Confidence penalty for low Sharpe ratio (0-1)"
    )
    CONF_LOW_MODEL_HEALTH_PENALTY: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Confidence penalty for low model health (0-1)"
    )
    CONF_LOW_CV_SCORE_PENALTY: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Confidence penalty for low cross-validation score (0-1)",
    )

    # Negative adjustments (multiplicative - for severe violations)
    CONF_POSITION_LIMIT_MULTIPLIER: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Confidence multiplier when position limit exceeded",
    )
    CONF_DRAWDOWN_LIMIT_MULTIPLIER: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Confidence multiplier when drawdown limit exceeded",
    )
    CONF_LEVERAGE_LIMIT_MULTIPLIER: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Confidence multiplier when leverage limit exceeded",
    )
    CONF_CIRCUIT_BREAKER_MULTIPLIER: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence multiplier when circuit breaker triggered",
    )
    CONF_CRITICAL_FAILURE_MULTIPLIER: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence multiplier when critical system fails"
    )

    # Thresholds used in comparisons
    DEFAULT_REGIME_CONFIDENCE: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Default regime confidence when not calculated"
    )
    HIGH_VOLATILITY_PERCENTILE: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Volatility percentile threshold for 'high' classification (0-100)",
    )
    DEFAULT_SIGNAL_STRENGTH: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Default signal strength when not calculated (0-1)"
    )
    DEFAULT_HEALTH_SCORE: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Default health score when not calculated (0-100)",
    )

    # Quality assessment thresholds (used for Narang alpha quality, etc.)
    ALPHA_QUALITY_HIGH_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for HIGH alpha quality rating (0-1)",
    )
    ALPHA_QUALITY_MEDIUM_THRESHOLD: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for MEDIUM alpha quality rating (0-1)",
    )

    # Meta-labeling specific thresholds
    FITTED_MODEL_SIGNAL_STRENGTH: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Signal strength when meta-labeling model is fitted (0-1)",
    )
    DEFAULT_MCC_METRIC: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Default MCC metric when not calculated (0-1)"
    )

    # Hull (Risk Management) thresholds
    CONF_HIGH_VAR_PENALTY: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Confidence penalty for high Value at Risk (0-1)"
    )

    # Google SRE thresholds
    CONF_SLO_VIOLATION_PENALTY: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Confidence penalty for SLO compliance violation (0-1)",
    )

    # Execution Engine thresholds
    BASE_SLIPPAGE_BPS: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Base slippage in basis points for execution estimation",
    )
    URGENCY_IMPACT_COEFFICIENT: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Coefficient for urgency impact on execution probability (0-1)",
    )
    SLIPPAGE_VOLATILITY_FACTOR: float = Field(
        default=2.0,
        ge=0.0,
        le=10.0,
        description="Factor for execution probability impact on slippage",
    )

    # Tomasini (Architecture) thresholds
    TOMASINI_ARCHITECTURE_SCORE_COMPLIANT: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Architecture score when system is compliant (0-100)",
    )
    TOMASINI_ARCHITECTURE_SCORE_DEFAULT: float = Field(
        default=90.0, ge=0.0, le=100.0, description="Default architecture score (0-100)"
    )

    # Kelly Criterion thresholds
    KELLY_MAX_POSITION_PCT: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Maximum position size as percentage of portfolio (0-1)",
    )

    # O'Hara (Microstructure) calculation factors
    ORDER_FLOW_TOXICITY_SCALING_FACTOR: float = Field(
        default=10.0,
        ge=1.0,
        le=100.0,
        description="Scaling factor for order flow toxicity calculation",
    )

    # Percival (Architecture/Dependency Health) thresholds
    PERCIVAL_ARCHITECTURE_COMPLIANT_SCORE: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Architecture compliance score when system is compliant (0-100)",
    )
    PERCIVAL_ARCHITECTURE_DEFAULT_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0, description="Default architecture compliance score (0-100)"
    )
    PERCIVAL_CLEAN_ARCHITECTURE_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0, description="Clean architecture score (0-100)"
    )
    PERCIVAL_DEPENDENCY_HEALTH_SCORE: float = Field(
        default=90.0, ge=0.0, le=100.0, description="Dependency health score (0-100)"
    )

    # Analysis window sizes (for rolling calculations)
    RETURN_STABILITY_WINDOW: int = Field(
        default=15,
        ge=5,
        le=100,
        description="Window size for return stability calculation (number of periods)",
    )
    VOLATILITY_WINDOW: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Window size for volatility calculation (number of periods)",
    )
    SPREAD_WINDOW: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Window size for spread calculation (number of periods)",
    )
    FLOW_VOLATILITY_WINDOW: int = Field(
        default=10,
        ge=5,
        le=100,
        description="Window size for flow volatility calculation (number of periods)",
    )

    # Financial calculation constants
    TRADING_DAYS_PER_YEAR: int = Field(
        default=252, ge=1, le=365, description="Number of trading days per year for annualization"
    )
    STRATEGY_SIGNAL_SCALING_FACTOR: float = Field(
        default=100.0,
        ge=1.0,
        le=1000.0,
        description="Scaling factor for strategy signal sigmoid transformation",
    )

    # Risk:Reward validation thresholds
    DEFAULT_FALLBACK_PRICE: float = Field(
        default=100.0,
        ge=0.0,
        le=1000000.0,
        description="Fallback price when signal price is not available (USD)",
    )
    MIN_RISK_REWARD_RATIO: float = Field(
        default=2.0, ge=0.1, le=100.0, description="Minimum risk/reward ratio for trade validation"
    )

    # Risk management thresholds
    MAX_CORRELATION_RISK: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Maximum correlation risk (0-1 scale)"
    )

    # Default capital settings
    DEFAULT_STARTING_CAPITAL: float = Field(
        default=100000.0,
        ge=0.0,
        le=100_000_000.0,
        description="Default starting capital for paper/live trading (USD)",
    )

    # Mathematical constants (epsilon for division safety)
    EPSILON_DIVISION: float = Field(
        default=0.001,
        ge=0.0001,
        le=0.1,
        description="Small value to avoid division by zero (epsilon)",
    )

    # Execution calculation constants
    URGENCY_BASE_MULTIPLIER: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Base multiplier for urgency in slippage calculation",
    )

    # Timing cost estimation
    TIMING_COST_MULTIPLIER: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Multiplier for timing cost as portion of total cost",
    )

    # Google SRE defaults
    SLO_DEFAULT_ERROR_BUDGET: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Default error budget remaining percentage (0-100)",
    )
    SLO_DEFAULT_LATENCY_P95_MS: float = Field(
        default=50.0, ge=0.0, le=1000.0, description="Default P95 latency in milliseconds"
    )
    SLO_DEFAULT_HEALTH: float = Field(
        default=98.0, ge=0.0, le=100.0, description="Default golden signals health score (0-100)"
    )

    # Beck TDD (Rule 21) defaults
    TDD_COMPLIANT_COVERAGE: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Test coverage percentage when TDD compliant (0-100)",
    )
    TDD_COMPLIANT_TDD_SCORE: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="TDD compliance score when TDD compliant (0-100)",
    )
    TDD_FALLBACK_COVERAGE: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Fallback test coverage percentage (0-100)"
    )
    TDD_FALLBACK_TDD_SCORE: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Fallback TDD compliance score (0-100)"
    )

    # Martin Clean Architecture (Rule 18) defaults
    MARTIN_COMPLIANT_SCORE: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Martin Clean Architecture score when compliant (0-100)",
    )
    MARTIN_FALLBACK_SCORE: float = Field(
        default=90.0,
        ge=0.0,
        le=100.0,
        description="Fallback Martin Clean Architecture score (0-100)",
    )

    # Liquidity aggregation weights (must sum to 1.0)
    HARRIS_LIQUIDITY_WEIGHT: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for Harris liquidity score in aggregated liquidity (0-1)",
    )
    OHARA_LIQUIDITY_WEIGHT: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for O'Hara price discovery score in aggregated liquidity (0-1)",
    )

    # Liquidity regime thresholds
    LIQUIDITY_LOW_THRESHOLD: float = Field(
        default=30.0,
        ge=0.0,
        le=100.0,
        description="Liquidity score below this indicates LOW liquidity regime (0-100)",
    )
    LIQUIDITY_HIGH_THRESHOLD: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        description="Liquidity score above this indicates HIGH liquidity regime (0-100)",
    )

    # Default urgency for analyze_pre_trade
    DEFAULT_URGENCY: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Default execution urgency (0=low, 1=high)"
    )

    # Execution engine participation rate
    BASE_PARTICIPATION_RATE: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Base participation rate for order execution (0-1, typically 0.05 for 5%)",
    )

    # Liquidity score conversion values
    LIQUIDITY_SCORE_SUFFICIENT: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Liquidity score when liquidity is sufficient (0-100)",
    )
    LIQUIDITY_SCORE_INSUFFICIENT: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Liquidity score when liquidity is insufficient (0-100)",
    )

    # Initial confidence value for PreTradeAnalysis
    INITIAL_CONFIDENCE: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Initial confidence value before any systems penalize it (0-1)",
    )

    # Statistical calculation constants
    MIN_PRICE_HISTORY_LENGTH: int = Field(
        default=30,
        ge=10,
        le=1000,
        description="Minimum length of price_history required for statistical calculations",
    )
    SECONDS_PER_DAY: int = Field(
        default=86400,
        ge=1,
        le=100000,
        description="Number of seconds in a day (for time conversions)",
    )
    ADF_PVALUE_THRESHOLD: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="ADF test p-value threshold for stationarity (0.05 = 95% confidence)",
    )
    STATIONARY_HEALTH_MULTIPLIER: float = Field(
        default=100.0,
        ge=1.0,
        le=1000.0,
        description="Multiplier for converting ADF p-value to health score when stationary",
    )
    NON_STATIONARY_HEALTH_MULTIPLIER: float = Field(
        default=500.0,
        ge=1.0,
        le=10000.0,
        description="Multiplier for converting ADF p-value to health score when non-stationary",
    )

    # Unit conversion constants
    BASIS_POINTS_MULTIPLIER: int = Field(
        default=10000,
        ge=1,
        le=100000,
        description="Multiplier for converting decimal to basis points (1 = 10000 bps)",
    )
    MILLISECONDS_MULTIPLIER: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Multiplier for converting seconds to milliseconds (1 sec = 1000 ms)",
    )
    PERCENTAGE_MULTIPLIER: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Multiplier for converting decimal to percentage (1 = 100%)",
    )

    # Post-trade analysis thresholds
    DEFAULT_EXECUTION_QUALITY_SCORE: float = Field(
        default=50.0, ge=0.0, le=100.0, description="Default execution quality score (0-100)"
    )
    DEFAULT_FILL_RATE: float = Field(
        default=100.0, ge=0.0, le=100.0, description="Default fill rate percentage (0-100)"
    )
    MIN_HIGH_QUALITY_EXECUTION_SCORE: float = Field(
        default=70.0,
        ge=0.0,
        le=100.0,
        description="Minimum execution quality score for high-quality execution (0-100)",
    )
    MIN_HIGH_QUALITY_FILL_RATE: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Minimum fill rate for high-quality execution (0-100)",
    )
    DEFAULT_SLO_LATENCY_THRESHOLD_MS: float = Field(
        default=100.0,
        ge=0.0,
        le=10000.0,
        description="Default SLO latency threshold in milliseconds",
    )

    @field_validator(
        "MIN_STATISTICAL_MODEL_HEALTH",
        "MIN_LIQUIDITY_SCORE",
        "MIN_STRATEGY_HEALTH",
        "MIN_ARCHITECTURE_SCORE",
        "HIGH_VOLATILITY_PERCENTILE",
        "DEFAULT_HEALTH_SCORE",
        "BASE_SLIPPAGE_BPS",
        "TOMASINI_ARCHITECTURE_SCORE_COMPLIANT",
        "TOMASINI_ARCHITECTURE_SCORE_DEFAULT",
        "PERCIVAL_ARCHITECTURE_COMPLIANT_SCORE",
        "PERCIVAL_ARCHITECTURE_DEFAULT_SCORE",
        "PERCIVAL_CLEAN_ARCHITECTURE_SCORE",
        "PERCIVAL_DEPENDENCY_HEALTH_SCORE",
        "ORDER_FLOW_TOXICITY_SCALING_FACTOR",
        "RETURN_STABILITY_WINDOW",
        "VOLATILITY_WINDOW",
        "SPREAD_WINDOW",
        "FLOW_VOLATILITY_WINDOW",
        "STRATEGY_SIGNAL_SCALING_FACTOR",
        "DEFAULT_FALLBACK_PRICE",
        "MIN_RISK_REWARD_RATIO",
        "MAX_CORRELATION_RISK",
        "EPSILON_DIVISION",
        "TIMING_COST_MULTIPLIER",
        "URGENCY_BASE_MULTIPLIER",
        "SLO_DEFAULT_ERROR_BUDGET",
        "SLO_DEFAULT_LATENCY_P95_MS",
        "SLO_DEFAULT_HEALTH",
        "TDD_COMPLIANT_COVERAGE",
        "TDD_COMPLIANT_TDD_SCORE",
        "TDD_FALLBACK_COVERAGE",
        "TDD_FALLBACK_TDD_SCORE",
        "MARTIN_COMPLIANT_SCORE",
        "MARTIN_FALLBACK_SCORE",
        "LIQUIDITY_LOW_THRESHOLD",
        "LIQUIDITY_HIGH_THRESHOLD",
        "LIQUIDITY_SCORE_SUFFICIENT",
        "LIQUIDITY_SCORE_INSUFFICIENT",
        "ADF_PVALUE_THRESHOLD",
        "STATIONARY_HEALTH_MULTIPLIER",
        "NON_STATIONARY_HEALTH_MULTIPLIER",
        "DEFAULT_EXECUTION_QUALITY_SCORE",
        "DEFAULT_FILL_RATE",
        "MIN_HIGH_QUALITY_EXECUTION_SCORE",
        "MIN_HIGH_QUALITY_FILL_RATE",
        "DEFAULT_SLO_LATENCY_THRESHOLD_MS",
    )
    @classmethod
    def validate_score_100(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator(
        "MIN_CROSS_VALIDATION_SCORE",
        "MIN_META_LABELING_SIGNAL",
        "MIN_MCC_METRIC",
        "MAX_ORDER_FLOW_TOXICITY",
        "MIN_BACKTEST_CONFIDENCE",
        "MIN_EXECUTION_PROBABILITY",
        "CONF_BULL_REGIME_BONUS",
        "CONF_LOW_VOLATILITY_BONUS",
        "CONF_BEAR_REGIME_PENALTY",
        "CONF_HIGH_VOLATILITY_PENALTY",
        "CONF_POOR_LIQUIDITY_PENALTY",
        "CONF_LOW_LIQUIDITY_PENALTY",
        "CONF_HIGH_TOXICITY_PENALTY",
        "CONF_LOW_SHARPE_PENALTY",
        "CONF_LOW_MODEL_HEALTH_PENALTY",
        "CONF_LOW_CV_SCORE_PENALTY",
        "CONF_POSITION_LIMIT_MULTIPLIER",
        "CONF_DRAWDOWN_LIMIT_MULTIPLIER",
        "CONF_LEVERAGE_LIMIT_MULTIPLIER",
        "CONF_CIRCUIT_BREAKER_MULTIPLIER",
        "CONF_CRITICAL_FAILURE_MULTIPLIER",
        "DEFAULT_REGIME_CONFIDENCE",
        "DEFAULT_SIGNAL_STRENGTH",
        "ESTIMATED_VOLATILITY",
        "DEFAULT_ORDER_FLOW_TOXICITY",
        "ALPHA_QUALITY_HIGH_THRESHOLD",
        "ALPHA_QUALITY_MEDIUM_THRESHOLD",
        "FITTED_MODEL_SIGNAL_STRENGTH",
        "DEFAULT_MCC_METRIC",
        "CONF_HIGH_VAR_PENALTY",
        "CONF_SLO_VIOLATION_PENALTY",
        "URGENCY_IMPACT_COEFFICIENT",
        "SLIPPAGE_VOLATILITY_FACTOR",
        "KELLY_MAX_POSITION_PCT",
        "HARRIS_LIQUIDITY_WEIGHT",
        "OHARA_LIQUIDITY_WEIGHT",
        "DEFAULT_URGENCY",
        "BASE_PARTICIPATION_RATE",
        "INITIAL_CONFIDENCE",
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
