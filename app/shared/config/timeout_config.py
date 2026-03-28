"""
Centralized Timeout Configuration for External API Calls.

This module provides timeout settings for all external service integrations:
- Broker APIs (Alpaca, Interactive Brokers)
- Market data providers (Yahoo Finance, Polygon, Alpha Vantage)
- Database connections (PostgreSQL, Redis, QuestDB)
- External services (MLFlow, Dagster)
- WebSocket connections

All timeouts are configurable via environment variables for deployment flexibility.

Usage:
    from app.shared.config.timeout_config import TIMEOUTS

    # Use in async calls
    result = await asyncio.wait_for(
        external_api_call(),
        timeout=TIMEOUTS.alpaca_read
    )

    # Use in httpx/aiohttp
    async with httpx.AsyncClient(timeout=TIMEOUTS.http_timeout) as client:
        ...
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeoutConfig:
    """
    Centralized timeout configuration for all external services.

    Timeouts are in seconds. All values have sensible defaults
    and can be overridden via environment variables.

    Attributes:
        Broker API timeouts for trading operations.
        Market data timeouts for data fetching.
        Database timeouts for persistence operations.
        External service timeouts for integrations.
        WebSocket timeouts for streaming connections.
    """

    # ==================== Broker API Timeouts ====================
    # Alpaca (primary broker)
    alpaca_connect: float = 10.0
    alpaca_read: float = 30.0
    alpaca_write: float = 30.0
    alpaca_websocket_ping: float = 30.0
    alpaca_websocket_idle: float = 60.0

    # Interactive Brokers
    ib_connect: float = 15.0
    ib_read: float = 30.0
    ib_write: float = 30.0
    ib_order_execution: float = 60.0

    # ==================== Market Data Timeouts ====================
    # Yahoo Finance
    yahoo_finance_connect: float = 10.0
    yahoo_finance_read: float = 30.0

    # Polygon.io
    polygon_connect: float = 10.0
    polygon_read: float = 15.0

    # Alpha Vantage
    alpha_vantage_connect: float = 10.0
    alpha_vantage_read: float = 20.0

    # Crypto exchanges
    binance_connect: float = 10.0
    binance_read: float = 15.0

    # ==================== Database Timeouts ====================
    # PostgreSQL
    postgres_connect: float = 5.0
    postgres_query: float = 30.0
    postgres_long_query: float = 120.0  # For complex analytics

    # Redis
    redis_connect: float = 5.0
    redis_operation: float = 5.0

    # QuestDB (time-series)
    questdb_connect: float = 5.0
    questdb_query: float = 30.0
    questdb_insert: float = 10.0

    # ==================== External Service Timeouts ====================
    # MLFlow (experiment tracking)
    mlflow_connect: float = 10.0
    mlflow_operation: float = 30.0

    # Dagster (orchestration)
    dagster_connect: float = 10.0
    dagster_operation: float = 60.0

    # News/Sentiment APIs
    newsapi_read: float = 15.0
    marketaux_read: float = 15.0
    reddit_read: float = 20.0
    twitter_read: float = 15.0
    financial_modeling_prep_read: float = 20.0

    # Exchange Rate APIs
    boe_read: float = 15.0
    ecb_read: float = 20.0

    # ==================== Backtesting Timeouts ====================
    backtest_executor: float = 300.0  # 5 minutes for backtest execution
    backtest_parallel_join: float = 300.0  # 5 minutes for parallel process join
    backtest_data_load: float = 60.0  # 1 minute for data loading

    # ==================== Strategy/Learning Timeouts ====================
    strategy_subprocess: float = 300.0  # 5 minutes for subprocess operations
    strategy_training: float = 600.0  # 10 minutes for model training
    strategy_optimization: float = 300.0  # 5 minutes for optimization

    # ==================== API Endpoint Timeouts ====================
    api_health_check: float = 5.0
    api_portfolio_analytics: float = 30.0
    api_optimization: float = 300.0  # 5 minutes for optimization endpoint
    api_deployment: float = 60.0
    api_signals: float = 10.0
    api_assets: float = 30.0

    # ==================== Messaging/Queue Timeouts ====================
    messaging_socket_connect: float = 5.0
    messaging_socket_timeout: float = 5.0
    queue_get_timeout: float = 60.0
    process_join_timeout: float = 5.0

    # ==================== Strategy/Learning Timeouts ====================
    strategy_subprocess: float = 300.0  # 5 minutes for subprocess operations
    strategy_training: float = 600.0  # 10 minutes for model training
    strategy_optimization: float = 300.0  # 5 minutes for optimization

    # ==================== API Endpoint Timeouts ====================
    api_health_check: float = 5.0
    api_portfolio_analytics: float = 30.0
    api_optimization: float = 300.0  # 5 minutes for optimization endpoint
    api_deployment: float = 60.0
    api_signals: float = 10.0
    api_assets: float = 30.0
    api_paper_trading: float = 15.0
    api_cost_analysis: float = 10.0
    api_profitability_validation: float = 30.0

    # ==================== Messaging/Queue Timeouts ====================
    messaging_socket_connect: float = 5.0
    messaging_socket_timeout: float = 5.0
    queue_get_timeout: float = 60.0
    process_join_timeout: float = 5.0
    backtest_timeout: float = 300.0  # 5 minutes for backtest execution
    git_operation: float = 5.0
    alert_webhook: float = 10.0
    time_sync: float = 30.0

    # ==================== WebSocket Timeouts ====================
    websocket_ping_interval: float = 30.0
    websocket_ping_timeout: float = 10.0
    websocket_close_timeout: float = 5.0
    websocket_idle_timeout: float = 60.0

    # ==================== General HTTP Timeouts ====================
    http_connect: float = 10.0
    http_read: float = 30.0
    http_write: float = 30.0
    http_pool_timeout: float = 10.0

    # ==================== Retry Configuration ====================
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    retry_jitter_factor: float = 0.1

    @property
    def http_timeout(self) -> float:
        """Combined HTTP timeout (connect + read)."""
        return self.http_connect + self.http_read

    @property
    def alpaca_timeout(self) -> float:
        """Combined Alpaca timeout (connect + read)."""
        return self.alpaca_connect + self.alpaca_read

    @property
    def ib_timeout(self) -> float:
        """Combined IB timeout (connect + read)."""
        return self.ib_connect + self.ib_read

    def get_httpx_timeout(self) -> Dict[str, float]:
        """Get timeout dict for httpx client."""
        return {
            "connect": self.http_connect,
            "read": self.http_read,
            "write": self.http_write,
            "pool": self.http_pool_timeout,
        }

    def get_aiohttp_timeout(self) -> float:
        """Get total timeout for aiohttp client (uses single value)."""
        return self.http_connect + self.http_read

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        """
        Load timeout configuration from environment variables.

        Environment variables follow pattern: TIMEOUT_{SERVICE}_{OPERATION}
        Example: TIMEOUT_ALPACA_READ=45.0

        Returns:
            TimeoutConfig with environment overrides applied
        """
        # Map of parameter names to environment variable names
        env_mappings = {
            # Broker APIs
            "alpaca_connect": "TIMEOUT_ALPACA_CONNECT",
            "alpaca_read": "TIMEOUT_ALPACA_READ",
            "alpaca_write": "TIMEOUT_ALPACA_WRITE",
            "alpaca_websocket_ping": "TIMEOUT_ALPACA_WS_PING",
            "alpaca_websocket_idle": "TIMEOUT_ALPACA_WS_IDLE",
            "ib_connect": "TIMEOUT_IB_CONNECT",
            "ib_read": "TIMEOUT_IB_READ",
            "ib_write": "TIMEOUT_IB_WRITE",
            "ib_order_execution": "TIMEOUT_IB_ORDER",
            # Market Data
            "yahoo_finance_connect": "TIMEOUT_YAHOO_CONNECT",
            "yahoo_finance_read": "TIMEOUT_YAHOO_READ",
            "polygon_connect": "TIMEOUT_POLYGON_CONNECT",
            "polygon_read": "TIMEOUT_POLYGON_READ",
            "alpha_vantage_connect": "TIMEOUT_ALPHAVANTAGE_CONNECT",
            "alpha_vantage_read": "TIMEOUT_ALPHAVANTAGE_READ",
            "binance_connect": "TIMEOUT_BINANCE_CONNECT",
            "binance_read": "TIMEOUT_BINANCE_READ",
            # Databases
            "postgres_connect": "TIMEOUT_POSTGRES_CONNECT",
            "postgres_query": "TIMEOUT_POSTGRES_QUERY",
            "postgres_long_query": "TIMEOUT_POSTGRES_LONG_QUERY",
            "redis_connect": "TIMEOUT_REDIS_CONNECT",
            "redis_operation": "TIMEOUT_REDIS_OPERATION",
            "questdb_connect": "TIMEOUT_QUESTDB_CONNECT",
            "questdb_query": "TIMEOUT_QUESTDB_QUERY",
            "questdb_insert": "TIMEOUT_QUESTDB_INSERT",
            # External Services
            "mlflow_connect": "TIMEOUT_MLFLOW_CONNECT",
            "mlflow_operation": "TIMEOUT_MLFLOW_OPERATION",
            "dagster_connect": "TIMEOUT_DAGSTER_CONNECT",
            "dagster_operation": "TIMEOUT_DAGSTER_OPERATION",
            # HTTP
            "http_connect": "TIMEOUT_HTTP_CONNECT",
            "http_read": "TIMEOUT_HTTP_READ",
            "http_write": "TIMEOUT_HTTP_WRITE",
            "http_pool_timeout": "TIMEOUT_HTTP_POOL",
            # WebSockets
            "websocket_ping_interval": "TIMEOUT_WS_PING_INTERVAL",
            "websocket_ping_timeout": "TIMEOUT_WS_PING_TIMEOUT",
            "websocket_close_timeout": "TIMEOUT_WS_CLOSE",
            "websocket_idle_timeout": "TIMEOUT_WS_IDLE",
        }

        # Start with default values
        kwargs = {}

        for param_name, env_name in env_mappings.items():
            env_value = os.getenv(env_name)
            if env_value is not None:
                try:
                    kwargs[param_name] = float(env_value)
                    logger.debug(f"Override {param_name}={env_value} from {env_name}")
                except ValueError:
                    logger.warning(
                        f"Invalid timeout value for {env_name}: {env_value}, using default"
                    )

        # Create config with overrides
        config = cls(**kwargs) if kwargs else cls()

        if kwargs:
            logger.info(f"Loaded {len(kwargs)} timeout overrides from environment")

        return config


# ==================== Global Instance ====================

# Lazy-loaded global instance
_TIMEOUTS_INSTANCE: Optional[TimeoutConfig] = None


def get_timeouts() -> TimeoutConfig:
    """
    Get the global timeout configuration instance.

    Returns:
        TimeoutConfig singleton instance
    """
    global _TIMEOUTS_INSTANCE
    if _TIMEOUTS_INSTANCE is None:
        _TIMEOUTS_INSTANCE = TimeoutConfig.from_env()
        logger.info("Timeout configuration initialized")
    return _TIMEOUTS_INSTANCE


# Convenience alias
TIMEOUTS = property(lambda self: get_timeouts())


class TimeoutManager:
    """
    Context manager and utilities for timeout handling.

    Provides convenient ways to apply timeouts to async operations.

    Usage:
        async with TimeoutManager.operation("alpaca_read"):
            result = await alpaca_client.get_account()

        # Or use the timeout directly
        timeout = TimeoutManager.get_timeout("alpaca_read")
    """

    def __init__(self, config: Optional[TimeoutConfig] = None):
        """Initialize with optional config override."""
        self._config = config or get_timeouts()

    def get_timeout(self, operation: str) -> float:
        """
        Get timeout value for a named operation.

        Args:
            operation: Name of the operation (e.g., "alpaca_read")

        Returns:
            Timeout value in seconds

        Raises:
            AttributeError: If operation name not found
        """
        return getattr(self._config, operation)

    @classmethod
    def get_timeout_for_service(cls, service: str, operation: str = "read") -> float:
        """
        Get timeout for a service and operation combination.

        Args:
            service: Service name (e.g., "alpaca", "postgres")
            operation: Operation type ("connect", "read", "write")

        Returns:
            Timeout value in seconds
        """
        config = get_timeouts()
        attr_name = f"{service.lower()}_{operation.lower()}"

        if hasattr(config, attr_name):
            return getattr(config, attr_name)

        # Fallback to general HTTP timeout
        return {
            "connect": config.http_connect,
            "read": config.http_read,
            "write": config.http_write,
        }.get(operation, config.http_timeout)


# Module-level convenience
def get_timeout(operation: str) -> float:
    """Get timeout value for a named operation."""
    return TimeoutManager().get_timeout(operation)


# Initialize and log on module load
logger.info("Timeout configuration module loaded")
