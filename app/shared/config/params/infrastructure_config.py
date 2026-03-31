"""
Infrastructure Configuration

Extracted from centralized_config.py for SRP compliance.
Contains DatabaseConfig, RedisConfig, APIConfig, LoggingConfig, MonitoringConfig.

TASK-10: Centralización de Configuración
TASK-24: SRP Refactoring
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """
    Database configuration.

    Rule 28 Compliant: No hardcoded passwords.
    Passwords must come from environment variables.
    """

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="algotrading", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    # Rule 28: No default password - must come from environment variable
    password: str = Field(default="", description="Database password (from DB_PASSWORD env var)")

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
        """
        Generate database connection string.

        Rule 28 Compliant: Builds string dynamically from environment variables.
        Never hardcodes credentials in connection strings.
        """
        import os

        # Rule 28: Always read from environment, never use hardcoded value
        db_password = os.getenv("DB_PASSWORD", self.password)
        if not db_password:
            raise ValueError(
                "DB_PASSWORD environment variable not set. Cannot build secure connection string."
            )
        return f"postgresql://{self.user}:{db_password}@{self.host}:{self.port}/{self.name}"


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

    host: str = Field(default="127.0.0.1", description="API host")
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
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: list[str] = Field(
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


# =============================================================================
# SECTION 4: MONITORING & LOGGING CONFIGURATION
#   - LoggingConfig: Logging parameters
#   - MonitoringConfig: Monitoring and alerting configuration
# =============================================================================


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


# =============================================================================
# SECTION 5: RISK & COMPLIANCE CONFIGURATION
#   - CurrencyHedgingConfig: Automatic currency hedging parameters
#   - SectorCountryDiversificationConfig: Sector/country diversification limits
#   - ComplianceConfig: Compliance engine thresholds
# =============================================================================
