"""
Market Data Module

This module provides market data integration capabilities including
real-time quotes, historical data, and data feed management.

NOTE: Mock data has been removed - only real data sources are supported.
"""

from app.domain.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    MarketDataCache,
    MarketDataStatus,
    MarketDataSubscription,
    Quote,
)
from app.infrastructure.data.feeds import (
    AlphaVantageFeed,
    DataFeedInterface,
    PolygonFeed,
    YahooFinanceFeed,
    create_data_feed,
)

# Models
__all__ = [
    "AlphaVantageFeed",
    "DataFeedConfig",
    # Feed Interfaces
    "DataFeedInterface",
    "DataFeedType",
    "DataFrequency",
    "HistoricalData",
    "MarketDataCache",
    "MarketDataStatus",
    "MarketDataSubscription",
    "PolygonFeed",
    "Quote",
    "YahooFinanceFeed",
    "create_data_feed",
]
