"""
Market Data Service

Provides market data retrieval and management.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for retrieving and managing market data."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._feeds: dict[str, Any] = {}
        self._feed_configs: dict[UUID, Any] = {}
        self._subscriptions: set[str] = set()

    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        """Get current quote for a symbol."""
        # Return cached quote if available
        if symbol in self._cache:
            return self._cache[symbol]

        # Return mock quote for testing
        return {
            "symbol": symbol,
            "price": Decimal("100.00"),
            "bid": Decimal("99.99"),
            "ask": Decimal("100.01"),
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get historical data for a symbol."""
        return []

    async def get_top_liquid_quotes(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top liquid assets quotes."""
        return []

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_quotes": len(self._cache),
            "cache_size_mb": 0,
        }

    async def add_feed_config(self, config: object) -> UUID:
        """Add a feed configuration."""
        import uuid

        config_id = uuid.uuid4()
        if hasattr(config, "id"):
            config.id = config_id
        self._feed_configs[config_id] = config
        return config_id

    async def list_feed_configs(self) -> list[object]:
        """List all feed configurations."""
        return list(self._feed_configs.values())

    async def get_feed_config(self, config_id: UUID) -> object | None:
        """Get a specific feed configuration."""
        return self._feed_configs.get(config_id)

    async def connect_feed(self, config_id: UUID) -> bool:
        """Connect to a data feed."""
        if config_id in self._feed_configs:
            self._feeds[str(config_id)] = {"connected": True}
            return True
        return False

    async def disconnect_feed(self, config_id: UUID) -> bool:
        """Disconnect from a data feed."""
        feed_key = str(config_id)
        if feed_key in self._feeds:
            del self._feeds[feed_key]
            return True
        return False

    async def subscribe_to_symbols(self, symbols: list[str], feed_id: UUID | None = None) -> bool:
        """Subscribe to real-time updates for symbols."""
        self._subscriptions.update(symbols)
        return True

    async def get_service_status(self) -> dict[str, Any]:
        """Get market data service status."""
        return {
            "status": "running",
            "active_feeds": len(self._feeds),
            "cached_quotes": len(self._cache),
            "subscriptions": len(self._subscriptions),
        }


# Singleton instance
_market_data_service: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    """Get the singleton MarketDataService instance."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
