"""
Centralized Configuration System
TASK-10: Centralización de Configuración

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path


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
    min_signal_confidence: float = Field(default=70.0, description="Minimum signal confidence (0-100)")
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
    circuit_breaker_daily_loss: float = Field(default=0.03, description="Circuit breaker daily loss threshold")
    circuit_breaker_drawdown: float = Field(default=0.1, description="Circuit breaker drawdown threshold")
    circuit_breaker_volatility: float = Field(default=0.05, description="Circuit breaker volatility threshold")
    circuit_breaker_error_rate: float = Field(default=0.05, description="Circuit breaker error rate threshold")
    
    # Performance thresholds
    max_latency_ms: int = Field(default=1000, description="Maximum acceptable latency in milliseconds")
    max_execution_time_ms: int = Field(default=500, description="Maximum execution time in milliseconds")
    
    @field_validator('max_position_size', 'min_position_size', 'stop_loss_pct', 'take_profit_pct', 
                     'daily_loss_limit', 'max_drawdown_limit', 'max_total_exposure', 'max_sector_exposure', 
                     'max_correlation', 'circuit_breaker_daily_loss', 'circuit_breaker_drawdown', 
                     'circuit_breaker_volatility', 'circuit_breaker_error_rate')
    @classmethod
    def validate_percentage(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v
    
    @field_validator('min_signal_strength', 'min_signal_confidence', 'min_liquidity_score')
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
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy-specific parameters")
    
    # Risk parameters
    max_position_size: float = Field(default=0.1, description="Maximum position size for this strategy")
    stop_loss_pct: float = Field(default=0.05, description="Stop loss percentage for this strategy")
    take_profit_pct: float = Field(default=0.1, description="Take profit percentage for this strategy")
    
    # Performance thresholds
    min_sharpe_ratio: float = Field(default=1.0, description="Minimum Sharpe ratio for this strategy")
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown for this strategy")
    min_win_rate: float = Field(default=0.4, description="Minimum win rate for this strategy")
    
    @field_validator('weight', 'max_position_size', 'stop_loss_pct', 'take_profit_pct', 'max_drawdown', 'min_win_rate')
    @classmethod
    def validate_percentage(cls, v):
        if not 0 < v <= 1:
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
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class RedisConfig(BaseModel):
    """Redis configuration."""
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    
    # Connection settings
    max_connections: int = Field(default=20, description="Maximum connections")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class APIConfig(BaseModel):
    """API configuration."""
    
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=1, description="Number of workers")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for JWT")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    
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
    
    @field_validator('prometheus_port', 'grafana_port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class CentralizedConfig(BaseSettings):
    """Centralized configuration for the entire application."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Current environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Sub-configurations
    trading: TradingThresholds = Field(default_factory=TradingThresholds, description="Trading thresholds")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    
    # Strategy configurations
    strategies: Dict[str, StrategyConfig] = Field(default_factory=dict, description="Strategy configurations")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
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
                    with open(strategy_file, 'r') as f:
                        strategy_data = yaml.safe_load(f)
                    
                    strategy_name = strategy_file.stem
                    strategy_config = StrategyConfig(**strategy_data)
                    self.strategies[strategy_name] = strategy_config
                except Exception as e:
                    print(f"Warning: Could not load strategy config from {strategy_file}: {e}")


# Global configuration instance
_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CentralizedConfig()
    return _config


def get_trading_threshold() -> TradingThresholds:
    """Get trading thresholds."""
    return get_config().trading


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


def update_strategy_config(strategy_name: str, new_config: dict):
    """Update strategy configuration."""
    config = get_config()
    if strategy_name not in config.strategies:
        config.strategies[strategy_name] = StrategyConfig(name=strategy_name)
    
    # Update with new config
    strategy_config = config.strategies[strategy_name]
    for key, value in new_config.items():
        if hasattr(strategy_config, key):
            setattr(strategy_config, key, value)
    
    return config.strategies[strategy_name]


def validate_config() -> bool:
    """Validate the current configuration."""
    try:
        config = get_config()
        
        # Validate trading thresholds
        trading = config.trading
        assert 0 < trading.max_position_size <= 1, "Invalid max_position_size"
        assert 0 < trading.stop_loss_pct <= 1, "Invalid stop_loss_pct"
        assert 0 < trading.take_profit_pct <= 1, "Invalid take_profit_pct"
        
        # Validate strategy configurations
        for strategy_name, strategy_config in config.strategies.items():
            assert 0 < strategy_config.weight <= 1, f"Invalid weight for {strategy_name}"
            assert 0 < strategy_config.max_position_size <= 1, f"Invalid max_position_size for {strategy_name}"
        
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


# Configuration migration utilities
def find_magic_values() -> Dict[str, List[str]]:
    """Find magic values in the codebase that should be moved to configuration."""
    magic_values = {
        "numeric_thresholds": [],
        "string_constants": [],
        "timeout_values": [],
        "retry_counts": []
    }
    
    # This would be implemented with AST parsing to find hardcoded values
    # For now, return empty structure
    return magic_values


def migrate_magic_values(magic_values: Dict[str, List[str]]) -> bool:
    """Migrate magic values to centralized configuration."""
    # This would implement the migration logic
    # For now, return True
    return True