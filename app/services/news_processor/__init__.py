"""
News Processor Service - Event-driven news processing.

Phase 3.3: Real-time news processing and sentiment analysis.

Components:
- NewsEventHandler: Process news events in real-time
- Webhook subscription for Marketaux API
- Fallback to polling if webhook fails
- Trade triggers on significant news
- News sentiment cache
"""

from .event_handler import (
    NewsEvent,
    NewsEventHandler,
    NewsEventType,
    SentimentUpdate,
)

__all__ = [
    "NewsEvent",
    "NewsEventHandler",
    "NewsEventType",
    "SentimentUpdate",
]
