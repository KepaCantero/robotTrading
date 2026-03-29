"""
Strategy Configuration

Extracted from centralized_config.py for SRP compliance.
Contains StrategyConfig and StockAllocationSettings.

TASK-10: Centralización de Configuración
TASK-24: SRP Refactoring
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class StrategyConfig(BaseModel):
    """Configuration for individual strategies."""

    name: str = Field(description="Strategy name")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")
    weight: float = Field(default=1.0, description="Strategy weight for portfolio allocation")

    # Strategy-specific parameters
    parameters: dict[str, Any] = Field(
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
    MOMENTUM_WEIGHTS: dict[str, float] = Field(
        default_factory=lambda: {
            "H_long": 0.40,
            "Sortino": 0.35,
            "1/tau": 0.05,
            "Liquidity": 0.20,
        },
        description="Weights for Momentum scoring (must sum to ~1.0)",
    )

    # Mean Reversion scoring weights
    MEAN_REVERSION_WEIGHTS: dict[str, float] = Field(
        default_factory=lambda: {
            "H_long": 0.05,
            "Sortino": 0.10,
            "1/tau": 0.45,
            "Liquidity": 0.40,
        },
        description="Weights for Mean Reversion scoring (must sum to ~1.0)",
    )

    # Pairs Trading scoring weights
    PAIRS_TRADING_WEIGHTS: dict[str, float] = Field(
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
    def validate_weights_sum(cls, v: dict[str, float]) -> dict[str, float]:
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
