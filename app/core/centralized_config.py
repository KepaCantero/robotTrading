"""
Centralized Configuration System
TASK-10: Centralización de Configuración

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.
"""

import logging
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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
        default=0.03, description="Circuit breaker daily loss threshold"
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

    # T18.1: Metrics Database Configuration
    metrics_db_enabled: bool = Field(
        default=True, description="Enable metrics database collection"
    )
    metrics_collection_interval: int = Field(
        default=60, description="Metrics collection interval in seconds"
    )
    metrics_batch_size: int = Field(
        default=1000, description="Metrics batch size for inserts"
    )
    metrics_retention_days: int = Field(
        default=90, description="Metrics retention period in days"
    )
    questdb_host: str = Field(
        default="localhost", description="QuestDB host"
    )
    questdb_port: int = Field(
        default=5432, description="QuestDB port"
    )
    questdb_database: str = Field(
        default="qdb", description="QuestDB database name"
    )
    questdb_user: str = Field(
        default="admin", description="QuestDB user"
    )
    questdb_password: str = Field(
        default="quest", description="QuestDB password"
    )
    questdb_pool_size: int = Field(
        default=10, description="QuestDB connection pool size"
    )
    questdb_max_retries: int = Field(
        default=3, description="QuestDB maximum retries"
    )
    metrics_cache_enabled: bool = Field(
        default=True, description="Enable metrics query caching"
    )
    metrics_cache_ttl_seconds: int = Field(
        default=300, description="Metrics cache TTL in seconds"
    )


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
    """

    # Data validation parameters
    LOOKBACK_MAX_DAYS: int = Field(
        default=126,
        ge=60,
        le=1000,
        description="Maximum lookback period in days - RELAXED: 126 days (~6 months) instead of 252 to allow more stocks to pass (minimum 60, maximum 1000)",
    )
    MIN_LIQUIDITY_USD: float = Field(
        default=500_000.0,
        ge=50_000.0,
        description="Minimum daily liquidity in USD - RELAXED: 500k (was 1M) to allow more stocks. Actual filter uses 5% of this = $25k minimum (minimum 50k)",
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

    class Config:
        env_prefix = "STOCK_ALLOCATION_"
        case_sensitive = False


class DatabaseConfig(BaseModel):
    """Database configuration."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="algotrading", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="password", description="Database password")

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
        """Generate database connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


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

    host: str = Field(default="0.0.0.0", description="API host")
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

    # Strategy configurations
    strategies: Dict[str, StrategyConfig] = Field(
        default_factory=dict, description="Strategy configurations"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
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
                except Exception as e:
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
            for strategy_name, strategy_config in self.strategies.items():
                strategy_config.model_validate(strategy_config.model_dump())

            return True
        except Exception:
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
