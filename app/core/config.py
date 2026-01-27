"""
Configuration management for AlgoTrading MVP.

This module provides centralized configuration management using Pydantic BaseSettings
to load environment variables from .env files and provide type-safe configuration.
"""

import logging
from typing import List, Optional

import os
from pydantic import ConfigDict, Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic BaseSettings for automatic environment variable loading,
    type validation, and default value management.
    """

    # Application Settings
    app_name: str = Field(default="AlgoTrading MVP", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(
        default="Algorithmic Trading System MVP", description="Application description"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # API Settings
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_reload: bool = Field(default=False, description="Enable auto-reload for development")
    secret_key: str = Field(
        default="",
        description="Secret key for JWT tokens and encryption (REQUIRED in production)",
    )
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration time in days"
    )

    # Dashboard Settings
    dashboard_host: str = Field(default="localhost", description="Dashboard server host")
    dashboard_port: int = Field(default=8501, description="Dashboard server port")

    # Database Settings
    database_url: str = Field(
        default="postgresql://algotrading:algotrading@localhost:5432/algotrading",
        description="PostgreSQL database URL",
    )
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(
        default=20, description="Database connection pool max overflow"
    )

    # Redis Settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and task queue",
    )
    redis_password: Optional[str] = Field(default=None, description="Redis password (optional)")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_max_connections: int = Field(default=10, description="Redis connection pool size")

    # Celery Settings
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )
    celery_task_serializer: str = Field(default="json", description="Celery task serializer")
    celery_result_serializer: str = Field(default="json", description="Celery result serializer")
    celery_accept_content: List[str] = Field(
        default=["json"], description="Celery accepted content types"
    )

    # Trading API Keys (for production, these should be loaded from secure vault)
    # Interactive Brokers
    ib_api_key: Optional[str] = Field(default=None, description="Interactive Brokers API key")
    ib_secret: Optional[str] = Field(default=None, description="Interactive Brokers API secret")

    # Alpaca
    alpaca_api_key: Optional[str] = Field(default=None, description="Alpaca API key")
    alpaca_api_secret: Optional[str] = Field(default=None, description="Alpaca API secret")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca API base URL (paper or live)",
    )
    alpaca_paper_trading: bool = Field(default=True, description="Use Alpaca paper trading account")

    # Binance
    binance_api_key: Optional[str] = Field(default=None, description="Binance API key")
    binance_secret: Optional[str] = Field(default=None, description="Binance API secret")

    # Alpha Vantage (Market Data)
    alpha_vantage_api_key: Optional[str] = Field(
        default=None, description="Alpha Vantage API key for market data"
    )
    polygon_api_key: Optional[str] = Field(
        default=None, description="Polygon.io API key for real-time market data"
    )

    # Trading Settings
    default_currency: str = Field(default="USD", description="Default trading currency")
    max_position_size: float = Field(
        default=10000.0, description="Maximum position size in default currency"
    )
    risk_free_rate: float = Field(
        default=0.02, description="Risk-free rate for calculations (2% annual)"
    )

    # Paper Trading Settings
    paper_trading_initial_capital: float = Field(
        default=100000.0, description="Initial capital for paper trading"
    )
    paper_trading_commission_per_trade: float = Field(
        default=1.0, description="Commission per trade in paper trading"
    )

    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format",
    )
    log_file: Optional[str] = Field(default=None, description="Log file path (optional)")

    # CORS Settings
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    cors_allow_methods: List[str] = Field(default=["*"], description="CORS allowed methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="CORS allowed headers")

    # Security Settings
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(
        default=True, description="Require uppercase letters in password"
    )
    password_require_lowercase: bool = Field(
        default=True, description="Require lowercase letters in password"
    )
    password_require_numbers: bool = Field(default=True, description="Require numbers in password")
    password_require_special: bool = Field(
        default=True, description="Require special characters in password"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate SECRET_KEY is strong in ALL environments.

        Security requirements:
        - At least 32 characters long (ALWAYS enforced)
        - Not a common weak default value
        - Weak keys only allowed with explicit ALLOW_WEAK_SECRET_KEY=true override
        """
        # Always require minimum length, even in debug mode
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                f"Current length: {len(v) if v else 0}. "
                "Generate one: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Check for known weak keys
        weak_keys = [
            'your_secret_key_change_this_in_production',
            'dev', 'test', 'secret', 'changeme', 'password',
            '0123456789abcdef0123456789abcdef',  # Common hex pattern
            'secret', 'SECRET', 'key', 'KEY',
            'change-this-secret-key-in-production-min-32-chars',
            '12345678901234567890123456789012',
        ]

        if v and v.lower() in [k.lower() for k in weak_keys]:
            # Only allow weak keys with explicit override
            allow_weak = os.getenv('ALLOW_WEAK_SECRET_KEY', '').lower() == 'true'
            if not allow_weak:
                raise ValueError(
                    f"Weak SECRET_KEY detected ('{v[:10]}...'). "
                    "This is a security risk. To use this key anyway, set "
                    "ALLOW_WEAK_SECRET_KEY=true environment variable."
                )
            logger.warning(
                "⚠️ Using weak SECRET_KEY - this should NEVER be done in production!"
            )

        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v

    @field_validator("celery_accept_content", mode="before")
    @classmethod
    def parse_celery_content(cls, v):
        """Parse Celery content types from string or list."""
        if isinstance(v, str):
            return [content.strip() for content in v.split(",")]
        return v

    def get_database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.database_url

    def get_database_url_async(self) -> str:
        """Get asynchronous database URL."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("sqlite://"):
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return self.database_url

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug

    def get_cors_config(self) -> dict:
        """Get CORS configuration dictionary."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allow_methods,
            "allow_headers": self.cors_allow_headers,
        }

    def get_celery_config(self) -> dict:
        """Get Celery configuration dictionary."""
        return {
            "broker_url": self.celery_broker_url,
            "result_backend": self.celery_result_backend,
            "task_serializer": self.celery_task_serializer,
            "result_serializer": self.celery_result_serializer,
            "accept_content": self.celery_accept_content,
            "timezone": "UTC",
            "enable_utc": True,
        }


# Global settings instance (will be created lazily to avoid validation issues)
_settings_instance: Optional[Settings] = None


def get_global_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()

    return _settings_instance


# For backward compatibility
settings = None


def get_settings() -> Settings:
    """
    Get application settings instance.

    This function provides a dependency injection pattern for FastAPI.

    Returns:
        Settings: Application settings instance
    """
    return get_global_settings()


# Convenience functions for common settings
def get_database_url() -> str:
    """Get database URL."""
    return get_global_settings().database_url


def get_redis_url() -> str:
    """Get Redis URL."""
    return get_global_settings().redis_url


def get_secret_key() -> str:
    """Get secret key."""
    return get_global_settings().secret_key


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return get_global_settings().debug


def get_cors_config() -> dict:
    """Get CORS configuration."""
    return get_global_settings().get_cors_config()


def get_celery_config() -> dict:
    """Get Celery configuration."""
    return get_global_settings().get_celery_config()
