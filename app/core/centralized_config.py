"""
Centralized Configuration System
TASK-10: Centralización de Configuración
"""

import os
from typing import Dict, Any, Optional, List
from decimal import Decimal
from enum import Enum
from pathlib import Path
import yaml
import json
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class TradingThresholds(BaseModel):
    """Trading thresholds configuration."""
    
    # Signal thresholds
    min_signal_strength: float = Field(default=60.0, ge=0, le=100)
    min_signal_confidence: float = Field(default=70.0, ge=0, le=100)
    min_liquidity_score: float = Field(default=50.0, ge=0, le=100)
    
    # RSI thresholds
    rsi_oversold: float = Field(default=30.0, ge=0, le=100)
    rsi_overbought: float = Field(default=70.0, ge=0, le=100)
    
    # Position sizing
    max_position_size: float = Field(default=0.1, ge=0, le=1)
    min_position_size: float = Field(default=0.01, ge=0, le=1)
    
    # Risk management
    stop_loss_pct: float = Field(default=0.05, ge=0, le=1)
    take_profit_pct: float = Field(default=0.15, ge=0, le=1)
    daily_loss_limit: float = Field(default=0.05, ge=0, le=1)
    max_drawdown_limit: float = Field(default=0.15, ge=0, le=1)
    
    # Exposure limits
    max_total_exposure: float = Field(default=0.8, ge=0, le=1)
    max_sector_exposure: float = Field(default=0.3, ge=0, le=1)
    max_correlation: float = Field(default=0.7, ge=0, le=1)
    
    # Circuit breaker thresholds
    circuit_breaker_daily_loss: float = Field(default=0.03, ge=0, le=1)
    circuit_breaker_drawdown: float = Field(default=0.1, ge=0, le=1)
    circuit_breaker_volatility: float = Field(default=0.05, ge=0, le=1)
    circuit_breaker_error_rate: float = Field(default=0.05, ge=0, le=1)
    
    # Latency thresholds
    max_latency_ms: int = Field(default=1000, ge=0)
    max_execution_time_ms: int = Field(default=500, ge=0)
    
    @validator('max_position_size')
    def validate_max_position_size(cls, v):
        if v <= 0 or v > 1:
            raise ValueError("max_position_size must be between 0 and 1")
        return v
    
    @validator('stop_loss_pct')
    def validate_stop_loss(cls, v):
        if v <= 0 or v > 0.5:
            raise ValueError("stop_loss_pct must be between 0 and 0.5")
        return v


class StrategyConfig(BaseModel):
    """Configuration for individual strategies."""
    
    name: str
    enabled: bool = True
    weight: float = Field(default=1.0, ge=0, le=10)
    
    # Strategy-specific parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Risk parameters
    max_position_size: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    
    # Performance thresholds
    min_sharpe_ratio: float = Field(default=1.0, ge=0)
    max_drawdown: float = Field(default=0.15, ge=0, le=1)
    min_win_rate: float = Field(default=0.4, ge=0, le=1)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    # Connection settings
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="algotrading")
    user: str = Field(default="postgres")
    password: str = Field(default="password")
    
    # Pool settings
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    
    # SSL settings
    ssl_mode: str = Field(default="prefer")
    
    @property
    def connection_string(self) -> str:
        """Get database connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    """Redis configuration."""
    
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    password: Optional[str] = None
    db: int = Field(default=0, ge=0, le=15)
    
    # Connection settings
    max_connections: int = Field(default=20, ge=1, le=100)
    socket_timeout: int = Field(default=5, ge=1, le=60)
    
    @property
    def connection_string(self) -> str:
        """Get Redis connection string."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class APIConfig(BaseModel):
    """API configuration."""
    
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=32)
    
    # Security settings
    secret_key: str = Field(default="your-secret-key-change-in-production")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, ge=1, le=10000)
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"])
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"])
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # File logging
    log_file: Optional[str] = None
    max_file_size: int = Field(default=10485760, ge=1024)  # 10MB
    backup_count: int = Field(default=5, ge=1, le=100)
    
    # ELK Stack settings
    elk_enabled: bool = Field(default=False)
    elk_host: str = Field(default="localhost")
    elk_port: int = Field(default=9200, ge=1, le=65535)
    elk_index: str = Field(default="algotrading-logs")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    
    # Prometheus settings
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090, ge=1, le=65535)
    
    # Grafana settings
    grafana_enabled: bool = Field(default=True)
    grafana_port: int = Field(default=3000, ge=1, le=65535)
    
    # Health check settings
    health_check_interval: int = Field(default=30, ge=5, le=300)
    health_check_timeout: int = Field(default=10, ge=1, le=60)
    
    # Alerting settings
    alerts_enabled: bool = Field(default=True)
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None


class CentralizedConfig(BaseSettings):
    """Centralized configuration system."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    
    # Sub-configurations
    trading: TradingThresholds = Field(default_factory=TradingThresholds)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Strategies configuration
    strategies: Dict[str, StrategyConfig] = Field(default_factory=dict)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_strategy_configs()
    
    def _load_strategy_configs(self) -> None:
        """Load strategy configurations from files."""
        try:
            config_dir = Path("config/strategies")
            if config_dir.exists():
                for config_file in config_dir.glob("*.yaml"):
                    with open(config_file, 'r') as f:
                        strategy_data = yaml.safe_load(f)
                        for strategy_name, strategy_config in strategy_data.items():
                            self.strategies[strategy_name] = StrategyConfig(
                                **strategy_config
                            )
        except Exception as e:
            raise ValueError(f"Failed to load strategy configurations: {str(e)}")
    
    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """Get configuration for a specific strategy."""
        return self.strategies.get(strategy_name)
    
    def get_trading_threshold(self, threshold_name: str) -> Any:
        """Get a trading threshold value."""
        if hasattr(self.trading, threshold_name):
            return getattr(self.trading, threshold_name)
        raise ValueError(f"Unknown threshold: {threshold_name}")
    
    def update_strategy_config(self, strategy_name: str, config: Dict[str, Any]) -> None:
        """Update strategy configuration."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name] = StrategyConfig(
                name=strategy_name,
                **config
            )
        else:
            self.strategies[strategy_name] = StrategyConfig(
                name=strategy_name,
                **config
            )
    
    def save_strategy_config(self, strategy_name: str) -> None:
        """Save strategy configuration to file."""
        try:
            config_dir = Path("config/strategies")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / f"{strategy_name}.yaml"
            strategy_config = self.strategies.get(strategy_name)
            
            if strategy_config:
                with open(config_file, 'w') as f:
                    yaml.dump({strategy_name: strategy_config.dict()}, f, default_flow_style=False)
        except Exception as e:
            raise ValueError(f"Failed to save strategy configuration: {str(e)}")
    
    def validate_configuration(self) -> bool:
        """Validate the entire configuration."""
        try:
            # Validate trading thresholds
            self.trading.validate()
            
            # Validate database config
            self.database.validate()
            
            # Validate Redis config
            self.redis.validate()
            
            # Validate API config
            self.api.validate()
            
            # Validate logging config
            self.logging.validate()
            
            # Validate monitoring config
            self.monitoring.validate()
            
            # Validate strategies
            for strategy_config in self.strategies.values():
                strategy_config.validate()
            
            return True
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {str(e)}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "trading_thresholds": self.trading.dict(),
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "name": self.database.name,
                "pool_size": self.database.pool_size
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "workers": self.api.workers
            },
            "strategies": {
                name: {
                    "enabled": config.enabled,
                    "weight": config.weight,
                    "parameters": config.parameters
                }
                for name, config in self.strategies.items()
            }
        }


# Global configuration instance
_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CentralizedConfig()
    return _config


def reload_config() -> CentralizedConfig:
    """Reload the configuration."""
    global _config
    _config = CentralizedConfig()
    return _config


def set_config(config: CentralizedConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


# Configuration utilities
def get_trading_threshold(threshold_name: str) -> Any:
    """Get a trading threshold value."""
    return get_config().get_trading_threshold(threshold_name)


def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """Get strategy configuration."""
    return get_config().get_strategy_config(strategy_name)


def update_strategy_config(strategy_name: str, config: Dict[str, Any]) -> None:
    """Update strategy configuration."""
    get_config().update_strategy_config(strategy_name, config)


def save_strategy_config(strategy_name: str) -> None:
    """Save strategy configuration."""
    get_config().save_strategy_config(strategy_name)


def validate_configuration() -> bool:
    """Validate the entire configuration."""
    return get_config().validate_configuration()


def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary."""
    return get_config().get_config_summary()