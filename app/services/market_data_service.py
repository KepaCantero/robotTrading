"""
Market Data Service with Caching

This module provides a centralized service for managing market data feeds,
caching, and real-time data subscriptions.
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.decimal_utils import to_decimal, validate_price, validate_quantity
from app.core.timezone_utils import utc_now
from app.data.feeds import DataFeedInterface, create_data_feed
from app.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    MarketDataCache,
    MarketDataSubscription,
    Quote,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """Centralized market data service with caching and feed management."""

    def __init__(self):
        self.feed_configs: Dict[UUID, DataFeedConfig] = {}
        self.active_feeds: Dict[UUID, DataFeedInterface] = {}
        self.subscriptions: Dict[UUID, MarketDataSubscription] = {}
        self.cache: Dict[str, MarketDataCache] = {}
        self._cache_lock = asyncio.Lock()
        self._feed_lock = asyncio.Lock()

        # Default cache settings
        self.default_cache_ttl = 60  # 1 minute
        self.max_cache_size = 1000

        # Initialize default feeds
        self._initialize_default_feeds()

    def _initialize_default_feeds(self):
        """Initialize default data feed configurations."""
        # Get symbols from MarketUniverseLoader (lazy import to avoid circular dependency)
        try:
            from app.services.market_universe_loader import MarketUniverseLoader

            loader = MarketUniverseLoader()
            # Get top 20 equities as default symbols
            default_symbols = loader.SP500_FALLBACK[
                :20
            ]  # Use fallback for immediate initialization
        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            default_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

        # Yahoo Finance feed (PRIMARY - free, real data)
        yahoo_config = DataFeedConfig(
            name="Yahoo Finance",
            feed_type=DataFeedType.YAHOO_FINANCE,
            base_url="https://query1.finance.yahoo.com",
            rate_limit=100,
            supported_symbols=default_symbols[:8],
            supported_frequencies=[
                DataFrequency.REAL_TIME,
                DataFrequency.DAILY,
                DataFrequency.HOURLY,
            ],
            max_history_days=730,
            timeout_seconds=30,
            retry_attempts=3,
            retry_delay=2.0,
            is_active=True,
        )
        self.feed_configs[yahoo_config.id] = yahoo_config

    async def add_feed_config(self, config: DataFeedConfig) -> UUID:
        """Add a new data feed configuration."""
        async with self._feed_lock:
            self.feed_configs[config.id] = config
            logger.info(f"Added feed config: {config.name}")
            return config.id

    async def remove_feed_config(self, config_id: UUID) -> bool:
        """Remove a data feed configuration."""
        async with self._feed_lock:
            if config_id in self.feed_configs:
                # Disconnect active feed if exists
                if config_id in self.active_feeds:
                    await self.active_feeds[config_id].disconnect()
                    del self.active_feeds[config_id]

                del self.feed_configs[config_id]
                logger.info(f"Removed feed config: {config_id}")
                return True
            return False

    async def get_feed_config(self, config_id: UUID) -> Optional[DataFeedConfig]:
        """Get a data feed configuration."""
        return self.feed_configs.get(config_id)

    async def list_feed_configs(self) -> List[DataFeedConfig]:
        """List all data feed configurations."""
        return list(self.feed_configs.values())

    async def connect_feed(self, config_id: UUID) -> bool:
        """Connect to a data feed."""
        config = self.feed_configs.get(config_id)
        if not config:
            logger.error(f"Feed config not found: {config_id}")
            return False

        if not config.is_active:
            logger.warning(f"Feed config is inactive: {config_id}")
            return False

        try:
            feed = create_data_feed(config)
            success = await feed.connect()

            if success:
                self.active_feeds[config_id] = feed
                logger.info(f"Connected to feed: {config.name}")
                return True
            else:
                logger.error(f"Failed to connect to feed: {config.name}")
                return False
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error connecting to feed {config.name}: {e}")
            return False

    async def disconnect_feed(self, config_id: UUID) -> bool:
        """Disconnect from a data feed."""
        if config_id in self.active_feeds:
            feed = self.active_feeds[config_id]
            success = await feed.disconnect()
            del self.active_feeds[config_id]
            logger.info(f"Disconnected from feed: {config_id}")
            return success
        return False

    async def get_quote(self, symbol: str, feed_id: Optional[UUID] = None) -> Optional[Quote]:
        """Get real-time quote for a symbol."""
        # Check cache first
        cached_quote = await self._get_cached_quote(symbol)
        if cached_quote:
            logger.debug(f"Returning cached quote for {symbol}")
            return cached_quote

        # Get from active feed
        feed = await self._get_active_feed(feed_id)
        if not feed:
            logger.error("No active feed available")
            return None

        try:
            quote = await feed.get_quote(symbol)
            if quote:
                # Cache the quote
                await self._cache_quote(symbol, quote)
                logger.debug(f"Retrieved fresh quote for {symbol}")
                return quote
            else:
                logger.warning(f"No quote data for {symbol}")
                return None
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
        feed_id: Optional[UUID] = None,
    ) -> List[HistoricalData]:
        """Get historical data for a symbol."""
        # Check cache first
        cache_key = f"{symbol}_{frequency}_{start_date.date()}_{end_date.date()}"
        cached_data = await self._get_cached_historical_data(cache_key)
        if cached_data:
            logger.debug(f"Returning cached historical data for {symbol}")
            return cached_data

        # Get from active feed
        feed = await self._get_active_feed(feed_id)
        if not feed:
            logger.error("No active feed available")
            return []

        try:
            historical_data = await feed.get_historical_data(
                symbol, start_date, end_date, frequency
            )

            if historical_data:
                # Cache the data
                await self._cache_historical_data(cache_key, historical_data)
                logger.debug(f"Retrieved fresh historical data for {symbol}")
                return historical_data
            else:
                logger.warning(f"No historical data for {symbol}")
                return []
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []

    async def subscribe_to_symbols(
        self, symbols: List[str], feed_id: Optional[UUID] = None
    ) -> bool:
        """Subscribe to real-time updates for symbols."""
        feed = await self._get_active_feed(feed_id)
        if not feed:
            logger.error("No active feed available")
            return False

        try:
            success = await feed.subscribe_to_symbols(symbols)
            if success:
                # Create subscription records
                for symbol in symbols:
                    subscription = MarketDataSubscription(
                        symbol=symbol,
                        feed_config_id=feed_id or list(self.feed_configs.keys())[0],
                        frequency=DataFrequency.REAL_TIME,
                    )
                    self.subscriptions[subscription.id] = subscription

                logger.info(f"Subscribed to symbols: {symbols}")
                return True
            else:
                logger.warning(f"Failed to subscribe to symbols: {symbols}")
                return False
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error subscribing to symbols {symbols}: {e}")
            return False

    async def get_top_liquid_assets_quotes(self, limit: int = 20) -> List[Quote]:
        """Get quotes for top liquid assets."""
        # Default liquid assets
        liquid_symbols = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "TSLA",
            "AMZN",
            "NVDA",
            "META",
            "NFLX",
            "BRK.A",
            "JPM",
            "JNJ",
            "V",
            "PG",
            "UNH",
            "HD",
            "MA",
            "DIS",
            "PYPL",
            "ADBE",
            "CRM",
        ]

        quotes = []
        for symbol in liquid_symbols[:limit]:
            quote = await self.get_quote(symbol)
            if quote:
                quotes.append(quote)

        return quotes

    async def _get_active_feed(self, feed_id: Optional[UUID] = None) -> Optional[DataFeedInterface]:
        """Get an active feed, preferring the specified one."""
        if feed_id and feed_id in self.active_feeds:
            return self.active_feeds[feed_id]

        # Return first available active feed
        for fid, feed in self.active_feeds.items():
            if self.feed_configs[fid].is_active:
                return feed

        return None

    async def _get_cached_quote(self, symbol: str) -> Optional[MarketDataCache]:
        """Get cached quote data."""
        async with self._cache_lock:
            cache_key = f"quote_{symbol}"
            cache_item = self.cache.get(cache_key)
            if cache_item and cache_item.is_cache_valid():
                # Convert dict back to Quote object
                quote_data = cache_item.data
                # Convert string enum values back to enum objects
                if "feed_type" in quote_data and isinstance(quote_data["feed_type"], str):
                    from app.models.market_data import DataFeedType

                    quote_data["feed_type"] = DataFeedType.YAHOO_FINANCE
                if "status" in quote_data and isinstance(quote_data["status"], str):
                    from app.models.market_data import MarketDataStatus

                    quote_data["status"] = MarketDataStatus(quote_data["status"])
                return Quote(**quote_data)
            return None

    async def _cache_quote(self, symbol: str, quote: Quote):
        """Cache quote data."""
        async with self._cache_lock:
            cache_key = f"quote_{symbol}"
            self.cache[cache_key] = MarketDataCache(
                symbol=symbol,
                data_type="quote",
                data=quote.model_dump(),
                ttl_seconds=self.default_cache_ttl,
                feed_type=quote.feed_type,
            )

            # Cleanup old cache entries if needed
            await self._cleanup_cache()

    async def _get_cached_historical_data(self, cache_key: str) -> Optional[List[HistoricalData]]:
        """Get cached historical data."""
        async with self._cache_lock:
            cache_item = self.cache.get(cache_key)
            if cache_item and cache_item.is_cache_valid():
                # Convert list of dicts back to HistoricalData objects
                historical_data = [HistoricalData(**item) for item in cache_item.data]
                return historical_data
            return None

    async def _cache_historical_data(self, cache_key: str, data: List[HistoricalData]):
        """Cache historical data."""
        async with self._cache_lock:
            self.cache[cache_key] = MarketDataCache(
                symbol=cache_key.split("_")[0],
                data_type="historical",
                data=[item.model_dump() for item in data],  # Convert to list of dicts
                ttl_seconds=self.default_cache_ttl * 60,  # Longer TTL for historical data
                feed_type=data[0].feed_type if data else DataFeedType.YAHOO_FINANCE,
            )

            # Cleanup old cache entries if needed
            await self._cleanup_cache()

    async def _cleanup_cache(self):
        """Cleanup expired cache entries."""
        if len(self.cache) <= self.max_cache_size:
            return

        # Remove expired entries
        expired_keys = []
        for key, cache_item in self.cache.items():
            if not cache_item.is_cache_valid():
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        # If still over limit, remove oldest entries
        if len(self.cache) > self.max_cache_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1].timestamp)

            items_to_remove = len(self.cache) - self.max_cache_size
            for key, _ in sorted_items[:items_to_remove]:
                del self.cache[key]

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._cache_lock:
            total_entries = len(self.cache)
            expired_entries = sum(
                1 for cache_item in self.cache.values() if not cache_item.is_cache_valid()
            )

            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries,
                "max_size": self.max_cache_size,
                "cache_hit_ratio": 0.0,  # Would need to track hits/misses
            }

    async def clear_cache(self):
        """Clear all cached data."""
        async with self._cache_lock:
            self.cache.clear()
            logger.info("Cache cleared")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status information."""
        return {
            "active_feeds": len(self.active_feeds),
            "total_configs": len(self.feed_configs),
            "active_subscriptions": len(self.subscriptions),
            "cache_entries": len(self.cache),
            "cache_stats": await self.get_cache_stats(),
        }


# Global service instance
market_data_service = MarketDataService()


async def get_market_data_service() -> MarketDataService:
    """Get the global market data service instance."""
    return market_data_service
