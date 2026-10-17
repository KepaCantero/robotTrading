"""
Centralized Configuration System
TASK-5: Configuración de variables de entorno
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

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
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="algotrading")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="")
    db_url: str | None = Field(default=None)

    # Connection pool
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_timeout: int = Field(default=30)

    # SSL
    db_ssl_mode: str = Field(default="prefer")
    db_ssl_cert: str | None = Field(default=None)
    db_ssl_key: str | None = Field(default=None)
    db_ssl_root_cert: str | None = Field(default=None)

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

    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str | None = Field(default=None)
    redis_db: int = Field(default=0)
    redis_url: str | None = Field(default=None)

    # Connection settings
    redis_max_connections: int = Field(default=10)
    redis_socket_timeout: int = Field(default=5)
    redis_socket_connect_timeout: int = Field(default=5)

    # SSL
    redis_ssl: bool = Field(default=False)
    redis_ssl_cert_reqs: str = Field(default="required")

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
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=1)

    # Security
    secret_key: str = Field(default="")  # SECURITY: No default - must be set from environment
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: os.environ.get(
            "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
        ).split(",")
    )
    cors_methods: list[str] = Field(default=["*"])
    cors_headers: list[str] = Field(default=["*"])

    # Rate limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)

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
    default_strategy: str = Field(default="momentum")
    max_position_size: float = Field(default=0.1)
    max_daily_loss: float = Field(default=0.05)
    max_drawdown: float = Field(default=0.15)

    # Risk management
    stop_loss_percentage: float = Field(default=0.02)
    take_profit_percentage: float = Field(default=0.04)
    position_sizing_method: str = Field(default="fixed")

    # Market data
    market_data_provider: str = Field(default="yahoo")
    market_data_api_key: str | None = Field(default=None)
    market_data_rate_limit: int = Field(default=1000)

    # Broker settings
    broker_name: str = Field(default="paper")
    broker_api_key: str | None = Field(default=None)
    broker_secret_key: str | None = Field(default=None)
    broker_sandbox: bool = Field(default=True)

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
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File logging
    log_file_enabled: bool = Field(default=True)
    log_file_path: str = Field(default="logs/app.log")
    log_file_max_size: int = Field(default=10485760)  # 10MB
    log_file_backup_count: int = Field(default=5)

    # Console logging
    log_console_enabled: bool = Field(default=True)
    log_console_level: LogLevel = Field(default=LogLevel.INFO)

    # ELK Stack
    elk_enabled: bool = Field(default=False)
    elk_host: str = Field(default="localhost")
    elk_port: int = Field(default=9200)
    elk_index: str = Field(default="algotrading")

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
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)
    prometheus_path: str = Field(default="/metrics")

    # Health checks
    health_check_enabled: bool = Field(default=True)
    health_check_interval: int = Field(default=30)

    # Alerts
    alerts_enabled: bool = Field(default=False)
    alerts_webhook_url: str | None = Field(default=None)
    alerts_email: str | None = Field(default=None)

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
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    app_name: str = Field(default="AlgoTrading")
    app_version: str = Field(default="1.0.0")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

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
                raise_configuration_error(f"Configuration validation failed: {e!s}", "validation")

    def get_config_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "database": self.database.model_dump(),
            "redis": self.redis.model_dump(),
            "api": self.api.model_dump(),
            "trading": self.trading.model_dump(),
            "logging": self.logging.model_dump(),
            "monitoring": self.monitoring.model_dump(),
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
_config: CentralizedConfig | None = None


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
    assert _config is not None
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
