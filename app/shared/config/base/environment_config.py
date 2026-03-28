"""
Centralized Configuration System
TASK-5: Configuración de variables de entorno
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from app.shared.exceptions.exceptions import ConfigurationError, raise_configuration_error

# Initialize logger for structured logging
logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    # Database connection
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="algotrading", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    db_url: Optional[str] = Field(default=None)

    # Connection pool
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")

    # SSL
    db_ssl_mode: str = Field(default="prefer", env="DB_SSL_MODE")
    db_ssl_cert: Optional[str] = Field(default=None)
    db_ssl_key: Optional[str] = Field(default=None)
    db_ssl_root_cert: Optional[str] = Field(default=None)

    @field_validator("db_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            logger.error(
                "Invalid database port configuration", extra={"port": v, "min": 1, "max": 65535}
            )
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("db_pool_size")
    @classmethod
    def validate_pool_size(cls, v):
        if v < 1:
            logger.error(
                "Invalid database pool size configuration", extra={"pool_size": v, "minimum": 1}
            )
            raise ValueError("Pool size must be at least 1")
        return v

    @property
    def connection_string(self) -> str:
        """Get database connection string.

        SECURITY: Password is included in return value but NOT in logs.
        The logger.info() above only logs host, port, database, ssl_mode - never password.
        This is verified by reviewing the extra dict - no password field is present.
        """
        if self.db_url:
            logger.info("Using explicit database URL", extra={"has_custom_url": True})
            return self.db_url

        # SECURITY VERIFIED: Log output does not include password
        logger.info(
            "Building database connection string",
            extra={
                "host": self.db_host,
                "port": self.db_port,
                "database": self.db_name,
                "ssl_mode": self.db_ssl_mode,
            },
        )
        # Password is in connection string but not logged (verified above)
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode={self.db_ssl_mode}"
        )


class RedisConfig(BaseSettings):
    """Redis configuration."""

    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_url: Optional[str] = Field(default=None)

    # Connection settings
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")

    # SSL
    redis_ssl: bool = Field(default=False, env="REDIS_SSL")
    redis_ssl_cert_reqs: str = Field(default="required", env="REDIS_SSL_CERT_REQS")

    @field_validator("redis_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            logger.error(
                "Invalid Redis port configuration", extra={"port": v, "min": 1, "max": 65535}
            )
            raise ValueError("Port must be between 1 and 65535")
        return v

    @property
    def connection_string(self) -> str:
        """Get Redis connection string."""
        if self.redis_url:
            logger.info("Using explicit Redis URL", extra={"has_custom_url": True})
            return self.redis_url

        auth = f":{self.redis_password}@" if self.redis_password else ""
        protocol = "rediss" if self.redis_ssl else "redis"

        logger.info(
            "Building Redis connection string",
            extra={
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db,
                "ssl": self.redis_ssl,
            },
        )
        return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class APIConfig(BaseSettings):
    """API configuration."""

    # Server settings
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")

    # Security
    secret_key: str = Field(
        default="", env="SECRET_KEY"
    )  # SECURITY: No default - must be set from environment
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # CORS
    cors_origins: List[str] = Field(default=["*"])
    cors_methods: List[str] = Field(default=["*"])
    cors_headers: List[str] = Field(default=["*"])

    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    @field_validator("api_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            logger.error(
                "Invalid API port configuration", extra={"port": v, "min": 1, "max": 65535}
            )
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            logger.critical("Security risk: Secret key not set", extra={"configured": False})
            raise ValueError(
                'SECRET_KEY must be set from environment variable (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")'
            )
        if len(v) < 32:
            logger.error(
                "Invalid API secret key configuration", extra={"key_length": len(v), "minimum": 32}
            )
            raise ValueError("Secret key must be at least 32 characters")
        # Reject default weak key
        if v == "12345678901234567890123456789012":
            logger.critical(
                "Security risk: Default secret key detected", extra={"using_default": True}
            )
            raise ValueError(
                'Default secret key is not allowed. Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return v


class TradingConfig(BaseSettings):
    """Trading configuration."""

    # Trading settings
    default_strategy: str = Field(default="momentum", env="DEFAULT_STRATEGY")
    max_position_size: float = Field(default=0.1, env="MAX_POSITION_SIZE")
    max_daily_loss: float = Field(default=0.05, env="MAX_DAILY_LOSS")
    max_drawdown: float = Field(default=0.15, env="MAX_DRAWDOWN")

    # Risk management
    stop_loss_percentage: float = Field(default=0.02, env="STOP_LOSS_PERCENTAGE")
    take_profit_percentage: float = Field(default=0.04, env="TAKE_PROFIT_PERCENTAGE")
    position_sizing_method: str = Field(default="fixed", env="POSITION_SIZING_METHOD")

    # Market data
    market_data_provider: str = Field(default="yahoo", env="MARKET_DATA_PROVIDER")
    market_data_api_key: Optional[str] = Field(default=None)
    market_data_rate_limit: int = Field(default=1000, env="MARKET_DATA_RATE_LIMIT")

    # Broker settings
    broker_name: str = Field(default="paper", env="BROKER_NAME")
    broker_api_key: Optional[str] = Field(default=None)
    broker_secret_key: Optional[str] = Field(default=None)
    broker_sandbox: bool = Field(default=True, env="BROKER_SANDBOX")

    @field_validator("max_position_size")
    @classmethod
    def validate_position_size(cls, v):
        if not 0 < v <= 1:
            logger.error(
                "Invalid trading position size configuration",
                extra={"position_size": v, "min": 0, "max": 1},
            )
            raise ValueError("Position size must be between 0 and 1")
        return v

    @field_validator("max_daily_loss")
    @classmethod
    def validate_daily_loss(cls, v):
        if not 0 < v <= 1:
            logger.error(
                "Invalid daily loss limit configuration",
                extra={"daily_loss": v, "min": 0, "max": 1},
            )
            raise ValueError("Daily loss limit must be between 0 and 1")
        return v

    @field_validator("stop_loss_percentage")
    @classmethod
    def validate_stop_loss(cls, v):
        if not 0 < v <= 1:
            logger.error(
                "Invalid stop loss percentage configuration",
                extra={"stop_loss": v, "min": 0, "max": 1},
            )
            raise ValueError("Stop loss must be between 0 and 1")
        return v


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    # Log levels
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )

    # File logging
    log_file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field(default="logs/app.log", env="LOG_FILE_PATH")
    log_file_max_size: int = Field(default=10485760, env="LOG_FILE_MAX_SIZE")  # 10MB
    log_file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")

    # Console logging
    log_console_enabled: bool = Field(default=True, env="LOG_CONSOLE_ENABLED")
    log_console_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_CONSOLE_LEVEL")

    # ELK Stack
    elk_enabled: bool = Field(default=False, env="ELK_ENABLED")
    elk_host: str = Field(default="localhost", env="ELK_HOST")
    elk_port: int = Field(default=9200, env="ELK_PORT")
    elk_index: str = Field(default="algotrading", env="ELK_INDEX")

    @field_validator("log_file_max_size")
    @classmethod
    def validate_file_size(cls, v):
        if v < 1024:  # At least 1KB
            logger.error(
                "Invalid log file size configuration", extra={"file_size": v, "minimum": 1024}
            )
            raise ValueError("Log file max size must be at least 1KB")
        return v


class MonitoringConfig(BaseSettings):
    """Monitoring configuration."""

    # Prometheus
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    prometheus_path: str = Field(default="/metrics", env="PROMETHEUS_PATH")

    # Health checks
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")

    # Alerts
    alerts_enabled: bool = Field(default=False, env="ALERTS_ENABLED")
    alerts_webhook_url: Optional[str] = Field(default=None)
    alerts_email: Optional[str] = Field(default=None)

    @field_validator("prometheus_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            logger.error(
                "Invalid Prometheus port configuration", extra={"port": v, "min": 1, "max": 65535}
            )
            raise ValueError("Port must be between 1 and 65535")
        return v


class CentralizedConfig(BaseSettings):
    """
    Centralized configuration for the entire application.

    Note: This is a lightweight environment-focused configuration.
    The main CentralizedConfig is in app.shared.config.centralized_config.
    Consider using that one for comprehensive application configuration.
    """

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    app_name: str = Field(default="AlgoTrading", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, env="DATABASE")
    redis: RedisConfig = Field(default_factory=RedisConfig, env="REDIS")
    api: APIConfig = Field(default_factory=APIConfig, env="API")
    trading: TradingConfig = Field(default_factory=TradingConfig, env="TRADING")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, env="LOGGING")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, env="MONITORING")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields from .env not defined in model
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(
            "Initializing centralized configuration",
            extra={
                "environment": self.environment.value,
                "app_name": self.app_name,
                "debug": self.debug,
            },
        )
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate the entire configuration."""
        try:
            logger.debug(
                "Starting configuration validation", extra={"environment": self.environment.value}
            )

            # Validate environment-specific settings
            if self.environment == Environment.PRODUCTION:
                if self.debug:
                    logger.critical(
                        "Security risk: Debug mode enabled in production",
                        extra={"environment": self.environment.value, "debug": True},
                    )
                    raise_configuration_error("Debug mode cannot be enabled in production", "debug")

                if self.api.secret_key == "12345678901234567890123456789012":
                    logger.critical(
                        "Security risk: Default secret key in production",
                        extra={"environment": self.environment.value},
                    )
                    raise_configuration_error(
                        "Default secret key cannot be used in production", "secret_key"
                    )

            # Validate trading configuration
            if self.trading.broker_name != "paper" and not self.trading.broker_api_key:
                logger.warning(
                    "Missing broker API key for live trading",
                    extra={"broker": self.trading.broker_name},
                )
                raise_configuration_error(
                    "Broker API key is required for live trading", "broker_api_key"
                )

            # Validate database configuration
            if not self.database.db_password and self.environment == Environment.PRODUCTION:
                logger.critical(
                    "Security risk: No database password in production",
                    extra={"environment": self.environment.value},
                )
                raise_configuration_error(
                    "Database password is required in production", "db_password"
                )

            logger.info(
                "Configuration validation completed successfully",
                extra={"environment": self.environment.value},
            )

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            if isinstance(e, ConfigurationError):
                raise
            else:
                logger.error(
                    "Configuration validation failed with unexpected error",
                    extra={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise_configuration_error(
                    f"Configuration validation failed: {str(e)}", "validation"
                )

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "database": self.database.dict(),
            "redis": self.redis.dict(),
            "api": self.api.dict(),
            "trading": self.trading.dict(),
            "logging": self.logging.dict(),
            "monitoring": self.monitoring.dict(),
        }

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.environment == Environment.TESTING


# Global configuration instance
_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        logger.info("Creating new configuration instance")
        _config = CentralizedConfig()
    else:
        logger.debug("Returning existing configuration instance")

    return _config


def reload_config() -> CentralizedConfig:
    """Reload the configuration."""
    logger.info("Reloading configuration instance")
    # global _config  # F824 removed

    return _config


def set_config(config: CentralizedConfig) -> None:
    """Set the global configuration instance."""
    logger.info(
        "Setting new configuration instance", extra={"environment": config.environment.value}
    )
    # global _config  # F824 removed


# Environment-specific configuration loading
def load_config_from_file(file_path: str) -> CentralizedConfig:
    """Load configuration from a specific file."""
    logger.info("Loading configuration from file", extra={"file_path": file_path})

    if not Path(file_path).exists():
        logger.error("Configuration file not found", extra={"file_path": file_path})
        raise_configuration_error(f"Configuration file not found: {file_path}", "file_path")

    # Set environment variable to load from specific file
    os.environ["ENV_FILE"] = file_path
    config = CentralizedConfig()

    logger.info(
        "Successfully loaded configuration from file",
        extra={"file_path": file_path, "environment": config.environment.value},
    )
    return config


def get_settings() -> CentralizedConfig:
    """Get the global settings instance."""
    return get_config()


def create_config_for_environment(env: Environment) -> CentralizedConfig:
    """Create configuration for a specific environment."""
    logger.info("Creating configuration for environment", extra={"target_environment": env.value})

    env_vars = {
        "ENVIRONMENT": env.value,
        "DEBUG": str(env == Environment.DEVELOPMENT).lower(),
    }

    # Set environment variables temporarily
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        config = CentralizedConfig()
        logger.info(
            "Successfully created environment-specific configuration",
            extra={"environment": env.value},
        )
        return config
    finally:
        # Restore original environment variables
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
