"""
API Endpoints Configuration

Centralizes all external API URLs to avoid hardcoding.
Load from environment variables with sensible defaults.

Usage:
    from app.shared.config.api_endpoints import APIEndpoints

    url = APIEndpoints.ALPACA_PAPER
    url = APIEndpoints.get_yahoo_finance_url(symbol)
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class APIEndpoints:
    """Centralized API endpoint configuration."""

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
        return {
            "alpaca_paper": os.getenv("ALPACA_PAPER_URL", cls.ALPACA_PAPER),
            "alpaca_live": os.getenv("ALPACA_LIVE_URL", cls.ALPACA_LIVE),
            "yahoo_finance": os.getenv("YAHOO_FINANCE_URL", cls.YAHOO_FINANCE_V8),
            "polygon": os.getenv("POLYGON_URL", cls.POLYGON),
            "alpha_vantage": os.getenv("ALPHA_VANTAGE_URL", cls.ALPHA_VANTAGE),
            "binance": os.getenv("BINANCE_URL", cls.BINANCE),
            "binance_testnet": os.getenv("BINANCE_TESTNET_URL", cls.BINANCE_TESTNET),
        }


# Default instance for easy import
ENDPOINTS = APIEndpoints()
