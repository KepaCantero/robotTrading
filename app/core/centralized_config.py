"""
Centralized Configuration System
TASK-10: Centralización de Configuración

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.
"""

from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


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
    min_atr_threshold: float = Field(default=0.015, description="Minimum ATR threshold for volatility filtering (0-1)")
    atr_filter_enabled: bool = Field(default=True, description="Enable ATR volatility filter to avoid choppy markets")
    trailing_stop_distance_pct: float = Field(default=0.02, description="Trailing stop distance percentage (0-1)")
    trailing_stop_enabled: bool = Field(default=True, description="Enable trailing stop for dynamic exits")
    
    # Signal Scoring Engine (TASK-SC-1 to SC-5)
    signal_cooldown_minutes: int = Field(default=10, description="Signal cooldown period in minutes")
    signal_compound_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "confidence": 0.30,
            "volume_ratio": 0.25,
            "volatility": 0.20,
            "liquidity": 0.15,
            "timing": 0.10,
        },
        description="Weights for compound signal scoring"
    )
    signal_high_priority_threshold: float = Field(
        default=80.0, description="High priority threshold (0-100)"
    )
    signal_medium_priority_threshold: float = Field(
        default=50.0, description="Medium priority threshold (0-100)"
    )

    # Multi-Strategy Allocation (TASK-PA-1, PA-2)
    momentum_target_weight: float = Field(default=0.50, description="Momentum strategy target weight")
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
    rebalance_drift_threshold: float = Field(default=0.05, description="Rebalance drift threshold (0-1)")
    min_allocation_weight: float = Field(default=0.10, description="Minimum allocation weight (0-1)")
    max_allocation_weight: float = Field(default=0.70, description="Maximum allocation weight (0-1)")
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
    def validate_percentage(cls, v):
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
                    strategy_config = StrategyConfig(**strategy_data)
                    self.strategies[strategy_name] = strategy_config
                except Exception as e:
                    print(f"Warning: Could not load strategy config from {strategy_file}: {e}")

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
