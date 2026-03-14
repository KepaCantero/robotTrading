"""
API Endpoints Configuration

Centralizes all external API URLs and timeouts to avoid hardcoding.
Load from environment variables with sensible defaults.

Usage:
    from app.shared.config.api_endpoints import APIEndpoints, EndpointConfig

    # Simple URL access
    url = APIEndpoints.ALPACA_PAPER

    # Full endpoint config with timeouts
    endpoint = EndpointConfig.ALPACA_PAPER
    async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
        response = await client.get(endpoint.url)

    # Dynamic URL generation
    url = APIEndpoints.get_yahoo_finance_url(symbol)
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from app.shared.config.timeout_config import get_timeouts


@dataclass(frozen=True)
class EndpointConfig:
    """
    Single API endpoint with URL and timeout configuration.

    Attributes:
        url: The base URL for the endpoint
        connect_timeout: Connection establishment timeout in seconds
        read_timeout: Read operation timeout in seconds
        write_timeout: Write operation timeout in seconds
    """

    url: str
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0

    @property
    def timeout(self) -> Dict[str, float]:
        """Get timeout dict for httpx client."""
        return {
            "connect": self.connect_timeout,
            "read": self.read_timeout,
            "write": self.write_timeout,
            "pool": self.connect_timeout,
        }

    @property
    def total_timeout(self) -> float:
        """Get total timeout (connect + read)."""
        return self.connect_timeout + self.read_timeout


@dataclass(frozen=True)
class APIEndpoints:
    """Centralized API endpoint configuration with URLs only."""

    # Trading Platforms
    ALPACA_PAPER: str = "https://paper-api.alpaca.markets"
    ALPACA_LIVE: str = "https://api.alpaca.markets"

    # Market Data
    YAHOO_FINANCE_V8: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    YAHOO_FINANCE_REFERER: str = "https://finance.yahoo.com/"
    POLYGON: str = "https://api.polygon.io"
    ALPHA_VANTAGE: str = "https://www.alphavantage.co/query"

    # Crypto
    BINANCE: str = "https://api.binance.com"
    BINANCE_TESTNET: str = "https://testnet.binance.vision"

    # Economic Data
    BOE_EXCHANGE_RATES: str = "https://api.bde.es/v1/exchange_rates"
    ECB_EXCHANGE_RATES: str = "https://sdw-wsrest.ecb.europa.eu/service/data/EXR"

    # News & Sentiment
    NEWSAPI: str = "https://newsapi.org/v2"
    MARKETAUX: str = "https://api.marketaux.com/v1"
    TWITTER_API: str = "https://api.twitter.com/2"
    REDDIT_API: str = "https://www.reddit.com"
    REDDIT_TOKEN: str = "https://www.reddit.com/api/v1/access_token"

    # Financial Data
    FINANCIAL_MODELING_PREP: str = "https://financialmodelingprep.com/api/v3"

    # Massive (alternative data)
    MASSIVE: str = "https://api.massive.com"

    @classmethod
    def get_yahoo_finance_url(cls, symbol: str) -> str:
        """Get Yahoo Finance URL for a symbol."""
        logger.debug(
            "Generating Yahoo Finance URL",
            extra={"symbol": symbol, "base_url": cls.YAHOO_FINANCE_V8},
        )
        return f"{cls.YAHOO_FINANCE_V8}/{symbol}"

    @classmethod
    def get_boe_exchange_rate_url(cls, currency: str, date_str: str) -> str:
        """Get BOE exchange rate URL."""
        return f"{cls.BOE_EXCHANGE_RATES}/{currency}/EUR/{date_str}"

    @classmethod
    def get_ecb_exchange_rate_url(cls, currency: str) -> str:
        """Get ECB exchange rate URL."""
        return f"{cls.ECB_EXCHANGE_RATES}/D.{currency}.EUR.SP00.A"

    @classmethod
    def from_env(cls) -> Dict[str, str]:
        """Load endpoints from environment variables (for overrides)."""
        logger.debug("Loading endpoints from environment variables")
        endpoints = {
            "alpaca_paper": os.getenv("ALPACA_PAPER_URL", cls.ALPACA_PAPER),
            "alpaca_live": os.getenv("ALPACA_LIVE_URL", cls.ALPACA_LIVE),
            "yahoo_finance": os.getenv("YAHOO_FINANCE_URL", cls.YAHOO_FINANCE_V8),
            "polygon": os.getenv("POLYGON_URL", cls.POLYGON),
            "alpha_vantage": os.getenv("ALPHA_VANTAGE_URL", cls.ALPHA_VANTAGE),
            "binance": os.getenv("BINANCE_URL", cls.BINANCE),
            "binance_testnet": os.getenv("BINANCE_TESTNET_URL", cls.BINANCE_TESTNET),
        }
        logger.debug(
            "Endpoints loaded from environment",
            extra={"endpoints_count": len(endpoints)},
        )
        return endpoints


class EndpointRegistry:
    """
    Registry of all API endpoints with full configuration including timeouts.

    Provides EndpointConfig objects that include both URL and timeout settings.
    """

    _instance: Optional["EndpointRegistry"] = None
    _endpoints: Dict[str, EndpointConfig]

    def __init__(self) -> None:
        """Initialize the endpoint registry."""
        self._endpoints = {}

    def __new__(cls) -> "EndpointRegistry":
        """Singleton pattern for consistent endpoint configuration."""
        if cls._instance is None:
            logger.info("Creating EndpointRegistry singleton instance")
            cls._instance = super().__new__(cls)
            cls._instance._endpoints = {}
            cls._instance._initialize_endpoints()
        return cls._instance

    def _initialize_endpoints(self) -> None:
        """Initialize all endpoint configurations with timeouts from config."""
        logger.debug("Initializing endpoint configurations")
        timeouts = get_timeouts()

        # Trading Platforms
        self._endpoints["alpaca_paper"] = EndpointConfig(
            url=APIEndpoints.ALPACA_PAPER,
            connect_timeout=timeouts.alpaca_connect,
            read_timeout=timeouts.alpaca_read,
            write_timeout=timeouts.alpaca_write,
        )
        self._endpoints["alpaca_live"] = EndpointConfig(
            url=APIEndpoints.ALPACA_LIVE,
            connect_timeout=timeouts.alpaca_connect,
            read_timeout=timeouts.alpaca_read,
            write_timeout=timeouts.alpaca_write,
        )

        # Market Data
        self._endpoints["yahoo_finance"] = EndpointConfig(
            url=APIEndpoints.YAHOO_FINANCE_V8,
            connect_timeout=timeouts.yahoo_finance_connect,
            read_timeout=timeouts.yahoo_finance_read,
        )
        self._endpoints["polygon"] = EndpointConfig(
            url=APIEndpoints.POLYGON,
            connect_timeout=timeouts.polygon_connect,
            read_timeout=timeouts.polygon_read,
        )
        self._endpoints["alpha_vantage"] = EndpointConfig(
            url=APIEndpoints.ALPHA_VANTAGE,
            connect_timeout=timeouts.alpha_vantage_connect,
            read_timeout=timeouts.alpha_vantage_read,
        )

        # Crypto
        self._endpoints["binance"] = EndpointConfig(
            url=APIEndpoints.BINANCE,
            connect_timeout=timeouts.binance_connect,
            read_timeout=timeouts.binance_read,
        )
        self._endpoints["binance_testnet"] = EndpointConfig(
            url=APIEndpoints.BINANCE_TESTNET,
            connect_timeout=timeouts.binance_connect,
            read_timeout=timeouts.binance_read,
        )

        # Economic Data
        self._endpoints["ecb_rates"] = EndpointConfig(
            url=APIEndpoints.ECB_EXCHANGE_RATES,
            connect_timeout=timeouts.http_connect,
            read_timeout=timeouts.http_read,
        )

        # News & Sentiment
        self._endpoints["newsapi"] = EndpointConfig(
            url=APIEndpoints.NEWSAPI,
            connect_timeout=timeouts.http_connect,
            read_timeout=timeouts.newsapi_read,
        )
        self._endpoints["marketaux"] = EndpointConfig(
            url=APIEndpoints.MARKETAUX,
            connect_timeout=timeouts.http_connect,
            read_timeout=timeouts.marketaux_read,
        )
        self._endpoints["reddit"] = EndpointConfig(
            url=APIEndpoints.REDDIT_API,
            connect_timeout=timeouts.http_connect,
            read_timeout=timeouts.reddit_read,
        )

        logger.info(
            "Endpoint configurations initialized",
            extra={"endpoints_count": len(self._endpoints)},
        )

    def get(self, name: str) -> EndpointConfig:
        """
        Get endpoint configuration by name.

        Args:
            name: Endpoint name (e.g., "alpaca_paper", "yahoo_finance")

        Returns:
            EndpointConfig with URL and timeouts

        Raises:
            KeyError: If endpoint not found
        """
        logger.debug(
            "Getting endpoint configuration",
            extra={"endpoint_name": name},
        )
        if name not in self._endpoints:
            logger.error(
                "Unknown endpoint requested",
                extra={"endpoint_name": name, "available_endpoints": list(self._endpoints.keys())},
            )
            raise KeyError(f"Unknown endpoint: {name}. Available: {list(self._endpoints.keys())}")
        return self._endpoints[name]

    def get_url(self, name: str) -> str:
        """Get just the URL for an endpoint."""
        return self.get(name).url

    def get_timeout(self, name: str) -> Dict[str, float]:
        """Get timeout configuration for an endpoint."""
        return self.get(name).timeout

    @property
    def ALPACA_PAPER(self) -> EndpointConfig:
        """Alpaca paper trading endpoint."""
        return self.get("alpaca_paper")

    @property
    def ALPACA_LIVE(self) -> EndpointConfig:
        """Alpaca live trading endpoint."""
        return self.get("alpaca_live")

    @property
    def YAHOO_FINANCE(self) -> EndpointConfig:
        """Yahoo Finance endpoint."""
        return self.get("yahoo_finance")

    @property
    def POLYGON(self) -> EndpointConfig:
        """Polygon.io endpoint."""
        return self.get("polygon")

    @property
    def BINANCE(self) -> EndpointConfig:
        """Binance endpoint."""
        return self.get("binance")


# Default instances for easy import
ENDPOINTS = APIEndpoints()
ENDPOINT_REGISTRY = EndpointRegistry()


# Convenience function
def get_endpoint(name: str) -> EndpointConfig:
    """
    Get endpoint configuration by name.

    Args:
        name: Endpoint name (e.g., "alpaca_paper")

    Returns:
        EndpointConfig with URL and timeouts
    """
    return ENDPOINT_REGISTRY.get(name)
