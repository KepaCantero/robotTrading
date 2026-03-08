"""
Market Data Feeds Module
"""

from app.infrastructure.feeds.market_data import MarketDataService, get_market_data_service

__all__ = [
    "MarketDataService",
    "get_market_data_service",
]
