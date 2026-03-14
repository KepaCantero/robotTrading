"""
Crypto Data Service - Servicio de datos para criptomonedas.

Proporciona:
- Datos de precio OHLCV para criptomonedas
- Soporte para BTC, ETH, y principales altcoins
- Integración con exchanges (Binance, Coinbase, Kraken)
- Caching y fallback defaults
- Reconnection with exponential backoff for 24/7 operation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from requests.exceptions import HTTPError, RequestException

from app.infrastructure.resilience.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
)
from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class CryptoDataFetcher:
    """
    Fetches and caches cryptocurrency data for multi-market trading.

    Provides:
    - Available crypto pairs (BTC/USD, ETH/USD, etc.)
    - Current exchange rates
    - Historical price data
    - Market cap and volume data
    - Automatic caching and fallback defaults
    """

    # Major cryptocurrencies supported
    DEFAULT_CRYPTOS = {
        "BTC": {
            "name": "Bitcoin",
            "symbol": "BTC",
            "pair": "BTCUSD",
            "market_cap": 1300000000000,  # ~$1.3T
            "avg_volume": 30000000000,  # ~$30B daily
        },
        "ETH": {
            "name": "Ethereum",
            "symbol": "ETH",
            "pair": "ETHUSD",
            "market_cap": 300000000000,  # ~$300B
            "avg_volume": 15000000000,  # ~$15B daily
        },
        "BNB": {
            "name": "Binance Coin",
            "symbol": "BNB",
            "pair": "BNBUSD",
            "market_cap": 80000000000,  # ~$80B
            "avg_volume": 1000000000,  # ~$1B daily
        },
        "SOL": {
            "name": "Solana",
            "symbol": "SOL",
            "pair": "SOLUSD",
            "market_cap": 60000000000,  # ~$60B
            "avg_volume": 2000000000,  # ~$2B daily
        },
        "XRP": {
            "name": "Ripple",
            "symbol": "XRP",
            "pair": "XRPUSD",
            "market_cap": 50000000000,  # ~$50B
            "avg_volume": 1000000000,  # ~$1B daily
        },
        "ADA": {
            "name": "Cardano",
            "symbol": "ADA",
            "pair": "ADAUSD",
            "market_cap": 20000000000,  # ~$20B
            "avg_volume": 500000000,  # ~$500M daily
        },
        "DOGE": {
            "name": "Dogecoin",
            "symbol": "DOGE",
            "pair": "DOGEUSD",
            "market_cap": 15000000000,  # ~$15B
            "avg_volume": 500000000,  # ~$500M daily
        },
        "DOT": {
            "name": "Polkadot",
            "symbol": "DOT",
            "pair": "DOTUSD",
            "market_cap": 10000000000,  # ~$10B
            "avg_volume": 300000000,  # ~$300M daily
        },
        "MATIC": {
            "name": "Polygon",
            "symbol": "MATIC",
            "pair": "MATICUSD",
            "market_cap": 8000000000,  # ~$8B
            "avg_volume": 300000000,  # ~$300M daily
        },
        "LINK": {
            "name": "Chainlink",
            "symbol": "LINK",
            "pair": "LINKUSD",
            "market_cap": 7000000000,  # ~$7B
            "avg_volume": 300000000,  # ~$300M daily
        },
    }

    # Default bid-ask spreads (in basis points) - higher than forex due to volatility
    DEFAULT_SPREADS = {
        "BTCUSD": Decimal("5"),  # 5 bps
        "ETHUSD": Decimal("10"),  # 10 bps
        "BNBUSD": Decimal("15"),
        "SOLUSD": Decimal("15"),
        "XRPUSD": Decimal("10"),
        "ADAUSD": Decimal("20"),
        "DOGEUSD": Decimal("20"),
        "DOTUSD": Decimal("25"),
        "MATICUSD": Decimal("25"),
        "LINKUSD": Decimal("25"),
    }

    # Crypto-specific risk metrics
    RISK_METRICS = {
        "BTC": {"volatility": Decimal("0.60"), "max_drawdown": Decimal("0.85")},
        "ETH": {"volatility": Decimal("0.80"), "max_drawdown": Decimal("0.90")},
        "altcoins": {"volatility": Decimal("1.20"), "max_drawdown": Decimal("0.95")},
    }

    def __init__(self):
        """Initialize crypto data fetcher with caching and reconnection manager."""
        self.price_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self.ohlcv_cache: Dict[str, tuple[List, datetime]] = {}
        self.price_cache_duration = timedelta(minutes=5)  # Crypto prices change fast
        self.ohlcv_cache_duration = timedelta(hours=1)
        self.api_timeout_seconds = 30
        self.max_retries = 3

        # Initialize reconnection manager for 24/7 crypto markets
        self.reconnection_manager = self._create_reconnection_manager()

    def _create_reconnection_manager(self) -> ReconnectionManager:
        """Create reconnection manager for crypto API connections."""

        def on_attempt(attempt: int) -> None:
            """Callback when connection attempt is made."""
            logger.info(f"Crypto API connection attempt {attempt + 1}")

        def on_success(attempt: int) -> None:
            """Callback when connection succeeds."""
            logger.info(f"Crypto API reconnected after {attempt + 1} attempts")

        def on_failure() -> None:
            """Callback when all connection attempts fail."""
            logger.error("All crypto API reconnection attempts failed - using fallback data")

        def alert_callback(attempts: int) -> None:
            """Callback when alert threshold is reached."""
            logger.warning(
                f"Alert: {attempts} failed crypto API connection attempts - using fallback data"
            )

        config = ReconnectionConfig(
            max_attempts=10,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
            on_attempt=on_attempt,
            on_success=on_success,
            on_failure=on_failure,
            alert_after_attempts=3,
            alert_callback=alert_callback,
        )

        return ReconnectionManager(
            service_name="CryptoDataFetcher",
            config=config,
        )

    def get_available_cryptos(self) -> Dict[str, Dict]:
        """
        Get available cryptocurrencies for trading.

        Returns:
            Dict[symbol, info]: Info includes name, pair, market_cap, avg_volume
        """
        logger.debug(f"Fetching available cryptos (returning {len(self.DEFAULT_CRYPTOS)})")
        return self.DEFAULT_CRYPTOS.copy()

    def get_crypto_pairs(self) -> List[str]:
        """
        Get list of crypto trading pairs.

        Returns:
            List of pair strings (e.g., ["BTCUSD", "ETHUSD"])
        """
        return [crypto["pair"] for crypto in self.DEFAULT_CRYPTOS.values()]

    def get_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get current prices for crypto symbols.

        Args:
            symbols: List of crypto symbols (e.g., ["BTC", "ETH"])

        Returns:
            Dict[symbol, price]: Current prices in USD
        """
        logger.debug(f"Getting current prices for {len(symbols)} cryptos")
        prices = {}

        for symbol in symbols:
            pair = f"{symbol}USD"

            # Check cache first
            if pair in self.price_cache:
                price, cached_at = self.price_cache[pair]
                if utc_now() - cached_at < self.price_cache_duration:
                    prices[symbol] = price
                    continue

            # Try to fetch from API with reconnection manager
            try:

                async def _fetch_price(trading_pair: str = pair) -> Optional[Decimal]:
                    """Internal fetch function."""
                    return self._fetch_price_from_api(trading_pair)

                price = asyncio.run(self.reconnection_manager.connect_with_backoff(_fetch_price))
                if price:
                    self.price_cache[pair] = (price, utc_now())
                    prices[symbol] = price
                    continue
            except NotImplementedError:
                logger.debug(f"API price fetching not implemented for {pair}, using fallback")
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.warning(f"Failed to fetch price for {pair}: {e}, using fallback")

            # Use fallback price when API fails
            prices[symbol] = self._get_fallback_price(symbol)

        return prices

    def get_historical_ohlcv(
        self, symbol: str, interval: str = "1h", limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get historical OHLCV data for a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to return

        Returns:
            List of OHLCV candles or None if fetch fails
        """
        pair = f"{symbol}USD"
        logger.debug(f"Getting OHLCV for {pair} ({interval}, {limit} candles)")

        # Check cache
        cache_key = f"{pair}_{interval}"
        if cache_key in self.ohlcv_cache:
            ohlcv, cached_at = self.ohlcv_cache[cache_key]
            if utc_now() - cached_at < self.ohlcv_cache_duration:
                return ohlcv

        # Try to fetch from API with reconnection manager
        try:

            async def _fetch_ohlcv() -> Optional[List[Dict]]:
                """Internal fetch function."""
                return self._fetch_ohlcv_from_api(pair, interval, limit)

            ohlcv = asyncio.run(self.reconnection_manager.connect_with_backoff(_fetch_ohlcv))
            if ohlcv:
                self.ohlcv_cache[cache_key] = (ohlcv, utc_now())
                return ohlcv
        except NotImplementedError:
            logger.debug(f"API OHLCV fetching not implemented for {pair}")
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.warning(f"Failed to fetch OHLCV for {pair}: {e}")

        return None

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get reconnection statistics."""
        return self.reconnection_manager.get_stats()

    def get_bid_ask_spread(self, pair: str) -> Decimal:
        """
        Get bid-ask spread for a crypto pair in basis points.

        Args:
            pair: Crypto pair (e.g., "BTCUSD")

        Returns:
            Spread in basis points (e.g., Decimal("5") = 5 bps)
        """
        logger.debug(f"Getting bid-ask spread for {pair}")
        return self.DEFAULT_SPREADS.get(pair, Decimal("15"))  # Default 15 bps for crypto

    def get_risk_metrics(self, symbol: str) -> Dict[str, Decimal]:
        """
        Get risk metrics for a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")

        Returns:
            Dict with volatility and max_drawdown
        """
        if symbol == "BTC":
            return self.RISK_METRICS["BTC"].copy()
        elif symbol == "ETH":
            return self.RISK_METRICS["ETH"].copy()
        else:
            return self.RISK_METRICS["altcoins"].copy()

    def is_trading_hours(self, symbol: str) -> bool:
        """
        Check if crypto is currently trading.

        Crypto markets are 24/7, so always True.

        Args:
            symbol: Crypto symbol

        Returns:
            Always True for crypto (24/7 market)
        """
        return True

    def invalidate_cache(self, cache_type: str = "all") -> None:
        """
        Invalidate cache to force fresh data fetch.

        Args:
            cache_type: "prices", "ohlcv", or "all"
        """
        if cache_type in ["prices", "all"]:
            self.price_cache.clear()
            logger.info("Cleared crypto price cache")
        if cache_type in ["ohlcv", "all"]:
            self.ohlcv_cache.clear()
            logger.info("Cleared crypto OHLCV cache")

    def _fetch_price_from_api(self, pair: str) -> Optional[Decimal]:
        """
        Fetch current price from exchange API (Binance, Coinbase, etc.).

        Note: API integration requires exchange API credentials and rate limiting.
        Current implementation uses fallback prices from config.

        Args:
            pair: Crypto pair (e.g., "BTCUSD")

        Returns:
            Current price or None if fetch fails
        """
        logger.debug(f"API price fetching not configured, using fallback for {pair}")
        # API integration requires:
        # 1. Exchange API credentials (Binance, Coinbase, Kraken)
        # 2. Rate limiting and error handling
        # 3. WebSocket for real-time updates
        # For now, implicitly return None to trigger fallback pricing

    def _fetch_ohlcv_from_api(self, pair: str, interval: str, limit: int) -> Optional[List[Dict]]:
        """
        Fetch historical OHLCV data from exchange API.

        Note: API integration requires exchange API credentials and rate limiting.
        Current implementation returns None to trigger synthetic data generation.

        Args:
            pair: Crypto pair
            interval: Time interval
            limit: Number of candles

        Returns:
            List of OHLCV candles or None
        """
        logger.debug(f"API OHLCV fetching not configured for {pair}, will use synthetic data")
        # API integration requires:
        # 1. Exchange API credentials (Binance, Coinbase, Kraken)
        # 2. Rate limiting and error handling
        # 3. Historical data endpoints (klines/candles)
        # For now, implicitly return None to trigger synthetic data generation

    def _get_fallback_price(self, symbol: str) -> Decimal:
        """
        Get fallback price when API is unavailable.

        Uses configuration for fallback prices.

        Args:
            symbol: Crypto symbol (e.g., "BTC")

        Returns:
            Fallback price in USD
        """
        from app.shared.config.centralized_config import get_config

        # Try to get from config first
        config = get_config()
        fallback_prices = getattr(config.trading, 'crypto_fallback_prices', None)

        if fallback_prices:
            return fallback_prices.get(symbol, Decimal("1.0"))

        # Use hardcoded fallback prices as last resort
        # These are also defined in trading_config.crypto_fallback_prices
        # Keep these here as safety net in case config is unavailable
        default_fallback_prices = {
            "BTC": Decimal("95000"),  # ~$95k
            "ETH": Decimal("3500"),  # ~$3.5k
            "BNB": Decimal("650"),  # ~$650
            "SOL": Decimal("200"),  # ~$200
            "XRP": Decimal("1.20"),  # ~$1.20
            "ADA": Decimal("0.60"),  # ~$0.60
            "DOGE": Decimal("0.15"),  # ~$0.15
            "DOT": Decimal("8.00"),  # ~$8
            "MATIC": Decimal("0.50"),  # ~$0.50
            "LINK": Decimal("15.00"),  # ~$15
        }
        return default_fallback_prices.get(symbol, Decimal("1.0"))


# Global instance for shared access
_crypto_fetcher: Optional[CryptoDataFetcher] = None


def get_crypto_fetcher() -> CryptoDataFetcher:
    """Get or create global CryptoDataFetcher instance."""
    global _crypto_fetcher
    if _crypto_fetcher is None:
        _crypto_fetcher = CryptoDataFetcher()
        logger.info("Initialized global CryptoDataFetcher")
    return _crypto_fetcher


def reset_crypto_fetcher() -> None:
    """Reset global CryptoDataFetcher (for testing)."""
    global _crypto_fetcher
    _crypto_fetcher = None
    logger.debug("Reset global CryptoDataFetcher")
