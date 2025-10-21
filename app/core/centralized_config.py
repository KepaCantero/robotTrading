"""
Centralized Configuration System for AlgoTrading MVP

This module provides a centralized configuration system that eliminates
hardcoded values and magic numbers throughout the application, making it
easier to optimize parameters and manage trading strategies.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum
import json
import os
from pathlib import Path


class ConfigEnvironment(str, Enum):
    """Configuration environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class TradingThresholds(BaseModel):
    """Trading strategy thresholds."""
    min_strength: float = Field(60.0, ge=0, le=100, description="Minimum signal strength")
    min_confidence: float = Field(70.0, ge=0, le=100, description="Minimum signal confidence")
    rsi_oversold: float = Field(30.0, ge=0, le=100, description="RSI oversold threshold")
    rsi_overbought: float = Field(70.0, ge=0, le=100, description="RSI overbought threshold")
    max_position_size: float = Field(0.1, ge=0, le=1, description="Maximum position size (10%)")
    stop_loss_pct: float = Field(0.05, ge=0, le=1, description="Stop loss percentage (5%)")
    take_profit_pct: float = Field(0.15, ge=0, le=1, description="Take profit percentage (15%)")
    
    @validator('rsi_oversold')
    def validate_rsi_oversold(cls, v):
        if v >= 50:
            raise ValueError("RSI oversold threshold must be below 50")
        return v
    
    @validator('rsi_overbought')
    def validate_rsi_overbought(cls, v):
        if v <= 50:
            raise ValueError("RSI overbought threshold must be above 50")
        return v


class RiskManagementThresholds(BaseModel):
    """Risk management thresholds."""
    daily_loss_limit: float = Field(0.05, ge=0, le=1, description="Daily loss limit (5%)")
    max_drawdown_limit: float = Field(0.15, ge=0, le=1, description="Maximum drawdown limit (15%)")
    single_trade_risk_pct: float = Field(0.02, ge=0, le=1, description="Single trade risk percentage (2%)")
    correlation_limit: float = Field(0.7, ge=0, le=1, description="Maximum correlation between positions")
    sector_exposure_limit: float = Field(0.3, ge=0, le=1, description="Maximum sector exposure (30%)")
    
    @validator('daily_loss_limit')
    def validate_daily_loss_limit(cls, v):
        if v > 0.1:
            raise ValueError("Daily loss limit should not exceed 10%")
        return v


class CircuitBreakerThresholds(BaseModel):
    """Circuit breaker thresholds."""
    daily_loss: float = Field(0.03, ge=0, le=1, description="Halt trading if daily loss > 3%")
    drawdown: float = Field(0.1, ge=0, le=1, description="Reduce positions if drawdown > 10%")
    volatility: float = Field(0.05, ge=0, le=1, description="Switch to conservative if volatility > 5%")
    error_rate: float = Field(0.05, ge=0, le=1, description="Halt trading if error rate > 5%")
    latency_ms: int = Field(1000, ge=0, description="Switch to backup if latency > 1000ms")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = Field("localhost", description="Database host")
    port: int = Field(5432, ge=1, le=65535, description="Database port")
    database: str = Field("algotrading", description="Database name")
    username: str = Field("postgres", description="Database username")
    password: str = Field("", description="Database password")
    pool_size: int = Field(10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(20, ge=0, le=100, description="Maximum overflow connections")


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = Field("localhost", description="Redis host")
    port: int = Field(6379, ge=1, le=65535, description="Redis port")
    password: Optional[str] = Field(None, description="Redis password")
    db: int = Field(0, ge=0, le=15, description="Redis database number")
    max_connections: int = Field(20, ge=1, le=100, description="Maximum Redis connections")


class APIConfig(BaseModel):
    """API configuration."""
    host: str = Field("0.0.0.0", description="API host")
    port: int = Field(8000, ge=1, le=65535, description="API port")
    workers: int = Field(1, ge=1, le=10, description="Number of workers")
    reload: bool = Field(False, description="Enable auto-reload")
    log_level: str = Field("INFO", description="Log level")
    cors_origins: list = Field(["*"], description="CORS allowed origins")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    metrics_port: int = Field(9090, ge=1, le=65535, description="Metrics port")
    health_check_interval: int = Field(30, ge=1, le=300, description="Health check interval (seconds)")
    alert_email: Optional[str] = Field(None, description="Alert email address")
    slack_webhook: Optional[str] = Field(None, description="Slack webhook URL")


class CentralizedConfig(BaseModel):
    """Centralized configuration for the entire application."""
    environment: ConfigEnvironment = Field(ConfigEnvironment.DEVELOPMENT, description="Environment")
    trading: TradingThresholds = Field(default_factory=TradingThresholds, description="Trading thresholds")
    risk_management: RiskManagementThresholds = Field(default_factory=RiskManagementThresholds, description="Risk management thresholds")
    circuit_breakers: CircuitBreakerThresholds = Field(default_factory=CircuitBreakerThresholds, description="Circuit breaker thresholds")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "ALGOTRADING_"
        case_sensitive = False


class ConfigManager:
    """Configuration manager for loading and managing application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[CentralizedConfig] = None
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Try different locations in order of preference
        possible_paths = [
            "config.json",
            "config/config.json",
            "app/config/config.json",
            os.path.join(os.path.dirname(__file__), "config.json")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default path if none exist
        return "config.json"
    
    def load_config(self, environment: Optional[ConfigEnvironment] = None) -> CentralizedConfig:
        """Load configuration from file and environment variables."""
        config_data = {}
        
        # Load from file if it exists
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
        
        # Override with environment-specific config if available
        if environment:
            env_config_path = self.config_path.replace('.json', f'_{environment.value}.json')
            if os.path.exists(env_config_path):
                with open(env_config_path, 'r') as f:
                    env_config_data = json.load(f)
                    config_data.update(env_config_data)
        
        # Create configuration object
        self._config = CentralizedConfig(**config_data)
        return self._config
    
    def save_config(self, config: CentralizedConfig, path: Optional[str] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save configuration
        with open(save_path, 'w') as f:
            json.dump(config.dict(), f, indent=2, default=str)
    
    def get_config(self) -> CentralizedConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> CentralizedConfig:
        """Update configuration with new values."""
        if self._config is None:
            self._config = self.load_config()
        
        # Update configuration
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        return self._config
    
    def validate_config(self, config: CentralizedConfig) -> bool:
        """Validate configuration."""
        try:
            # Re-create config to trigger validation
            CentralizedConfig(**config.dict())
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def get_trading_thresholds(self) -> TradingThresholds:
        """Get trading thresholds."""
        return self.get_config().trading
    
    def get_risk_thresholds(self) -> RiskManagementThresholds:
        """Get risk management thresholds."""
        return self.get_config().risk_management
    
    def get_circuit_breaker_thresholds(self) -> CircuitBreakerThresholds:
        """Get circuit breaker thresholds."""
        return self.get_config().circuit_breakers
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.get_config().database
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration."""
        return self.get_config().redis
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        return self.get_config().api
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.get_config().monitoring


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    return config_manager.get_config()


def get_trading_thresholds() -> TradingThresholds:
    """Get trading thresholds."""
    return config_manager.get_trading_thresholds()


def get_risk_thresholds() -> RiskManagementThresholds:
    """Get risk management thresholds."""
    return config_manager.get_risk_thresholds()


def get_circuit_breaker_thresholds() -> CircuitBreakerThresholds:
    """Get circuit breaker thresholds."""
    return config_manager.get_circuit_breaker_thresholds()


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return config_manager.get_database_config()


def get_redis_config() -> RedisConfig:
    """Get Redis configuration."""
    return config_manager.get_redis_config()


def get_api_config() -> APIConfig:
    """Get API configuration."""
    return config_manager.get_api_config()


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration."""
    return config_manager.get_monitoring_config()


def load_config(environment: Optional[ConfigEnvironment] = None) -> CentralizedConfig:
    """Load configuration for the specified environment."""
    return config_manager.load_config(environment)


def save_config(config: CentralizedConfig, path: Optional[str] = None) -> None:
    """Save configuration to file."""
    config_manager.save_config(config, path)

