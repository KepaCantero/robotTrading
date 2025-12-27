"""
Market Data Module

This module provides market data integration capabilities including
real-time quotes, historical data, and data feed management.
"""

from app.data.feeds import (
    AlphaVantageFeed,
    DataFeedInterface,
    MockDataFeed,
    YahooFinanceFeed,
    create_data_feed,
)
from app.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    MarketDataCache,
    MarketDataStatus,
    MarketDataSubscription,
    Quote,
)

# Models
__all__ = [
    "Quote",
    "HistoricalData",
    "DataFeedConfig",
    "DataFeedType",
    "DataFrequency",
    "MarketDataStatus",
    "MarketDataCache",
    "MarketDataSubscription",
    # Feed Interfaces
    "DataFeedInterface",
    "AlphaVantageFeed",
    "YahooFinanceFeed",
    "MockDataFeed",
    "create_data_feed",
]
