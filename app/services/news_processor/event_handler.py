"""
News Event Processor - Process news events in real-time.

Handles:
- Webhook subscription for news
- Real-time sentiment updates
- Trade triggers on significant news
- News sentiment cache
- Fallback to polling if webhook fails
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class NewsEventType(Enum):
    """Types of news events."""

    EARNINGS = "earnings"
    MERGER = "merger"
    GUIDANCE = "guidance"
    REGULATORY = "regulatory"
    MACRO = "macro"
    ANALYST = "analyst"
    OTHER = "other"


@dataclass
class NewsEvent:
    """Represents a news event."""

    event_id: str
    symbol: str
    headline: str
    sentiment_score: Decimal  # -1 to 1
    event_type: NewsEventType
    published_at: datetime
    source: str
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "symbol": self.symbol,
            "headline": self.headline,
            "sentiment_score": str(self.sentiment_score),
            "event_type": self.event_type.value,
            "published_at": self.published_at.isoformat(),
            "source": self.source,
            "url": self.url,
        }


@dataclass
class SentimentUpdate:
    """Sentiment update for a symbol."""

    symbol: str
    sentiment_score: Decimal
    previous_score: Optional[Decimal]
    change: Decimal
    timestamp: datetime
    news_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "sentiment_score": str(self.sentiment_score),
            "previous_score": str(self.previous_score) if self.previous_score else None,
            "change": str(self.change),
            "timestamp": self.timestamp.isoformat(),
            "news_count": self.news_count,
        }


class NewsEventHandler:
    """
    Process news events in real-time.

    Features:
    - Webhook subscription for news
    - Real-time sentiment updates
    - Trade triggers on significant news
    - News sentiment cache
    - Fallback to polling if webhook fails
    """

    def __init__(
        self,
        marketaux_client=None,
        on_trade_trigger: Optional[Callable[[str, Decimal], None]] = None,
        cache_ttl_seconds: float = 300.0,  # 5 minutes
    ):
        """
        Initialize news event handler.

        Args:
            marketaux_client: Marketaux API client
            on_trade_trigger: Callback when news triggers trade
            cache_ttl_seconds: Cache time-to-live
        """
        self.marketaux_client = marketaux_client
        self.on_trade_trigger = on_trade_trigger
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

        # State
        self._is_running = False
        self._subscriptions: Set[str] = set()
        self._sentiment_cache: Dict[str, SentimentUpdate] = {}
        self._event_history: List[NewsEvent] = []
        self._webhook_active = False
        self._polling_interval = 300.0  # 5 minutes

        logger.info("NewsEventHandler initialized")

    async def start(self) -> bool:
        """Start news event processing."""
        if self._is_running:
            logger.warning("NewsEventHandler already running")
            return False

        self._is_running = True

        # Try to setup webhooks
        if self.marketaux_client:
            await self._setup_webhooks()

        # Start polling fallback
        asyncio.create_task(self._polling_loop())

        logger.info("NewsEventHandler started")
        return True

    async def stop(self) -> bool:
        """Stop news event processing."""
        if not self._is_running:
            logger.warning("NewsEventHandler not running")
            return False

        self._is_running = False

        # Unsubscribe from all webhooks
        for symbol in list(self._subscriptions):
            await self.unsubscribe_from_news(symbol)

        logger.info("NewsEventHandler stopped")
        return True

    async def subscribe_to_news(
        self,
        symbols: List[str],
        webhook_url: Optional[str] = None,
    ) -> None:
        """
        Subscribe to news webhooks for symbols.

        Args:
            symbols: List of symbols to subscribe
            webhook_url: Optional webhook URL
        """
        for symbol in symbols:
            try:
                if self.marketaux_client and hasattr(self.marketaux_client, 'subscribe_webhook'):
                    await self.marketaux_client.subscribe_webhook(
                        symbol=symbol,
                        webhook_url=webhook_url,
                    )
                    self._subscriptions.add(symbol)
                    logger.info(f"Subscribed to news for {symbol}")
                else:
                    # Fallback: just track for polling
                    self._subscriptions.add(symbol)
                    logger.info(f"Tracking news for {symbol} (polling mode)")

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")

    async def unsubscribe_from_news(self, symbol: str) -> None:
        """Unsubscribe from news for symbol."""
        try:
            if self.marketaux_client and hasattr(self.marketaux_client, 'unsubscribe_webhook'):
                await self.marketaux_client.unsubscribe_webhook(symbol)

            self._subscriptions.discard(symbol)
            logger.info(f"Unsubscribed from news for {symbol}")

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Failed to unsubscribe from {symbol}: {e}")

    async def on_news_event(self, event: NewsEvent) -> None:
        """
        Called when news article published.

        Args:
            event: News event from webhook or polling
        """
        logger.info(
            f"News event: {event.symbol} - {event.headline[:50]}... "
            f"(sentiment: {event.sentiment_score:.2f})"
        )

        # Add to history
        self._event_history.append(event)

        # Keep only last 1000 events
        if len(self._event_history) > 1000:
            self._event_history = self._event_history[-1000:]

        # Update sentiment
        previous_score = None
        if event.symbol in self._sentiment_cache:
            previous_score = self._sentiment_cache[event.symbol].sentiment_score

        # Update sentiment score (exponential moving average)
        if previous_score is not None:
            alpha = Decimal("0.3")  # EMA smoothing factor
            new_score = alpha * event.sentiment_score + (Decimal("1") - alpha) * previous_score
        else:
            new_score = event.sentiment_score

        sentiment_update = SentimentUpdate(
            symbol=event.symbol,
            sentiment_score=new_score,
            previous_score=previous_score,
            change=new_score - (previous_score or Decimal("0")),
            timestamp=utc_now(),
        )

        self._sentiment_cache[event.symbol] = sentiment_update

        # Check if sentiment change triggers trade
        if self.should_trigger_trade(event):
            await self.execute_trade_signal(event, sentiment_update)

    def should_trigger_trade(self, event: NewsEvent) -> bool:
        """
        Check if sentiment change triggers trade.

        Args:
            event: News event

        Returns:
            True if trade should be triggered
        """
        # Trigger on very positive or very negative sentiment
        if abs(event.sentiment_score) > Decimal("0.5"):
            return True

        # Trigger on large sentiment change
        if event.symbol in self._sentiment_cache:
            cached = self._sentiment_cache[event.symbol]
            if abs(cached.change) > Decimal("0.3"):
                return True

        return False

    async def execute_trade_signal(
        self,
        event: NewsEvent,
        sentiment: SentimentUpdate,
    ) -> None:
        """
        Create signal from news event.

        Args:
            event: News event
            sentiment: Sentiment update
        """
        signal = {
            "symbol": event.symbol,
            "action": "BUY" if sentiment.sentiment_score > 0 else "SELL",
            "confidence": min(abs(sentiment.sentiment_score), Decimal("1")),
            "source": "news_sentiment",
            "timestamp": utc_now().isoformat(),
            "event_id": event.event_id,
        }

        logger.info(f"Trade signal from news: {signal}")

        # Call callback if provided
        if self.on_trade_trigger:
            try:
                self.on_trade_trigger(event.symbol, sentiment.sentiment_score)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error in trade trigger callback: {e}")

    async def _polling_loop(self) -> None:
        """Fallback polling loop for news."""
        while self._is_running:
            try:
                for symbol in self._subscriptions:
                    # Poll for recent news
                    await self._poll_news(symbol)

                # Wait 5 minutes between polls
                await asyncio.sleep(self._polling_interval)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(60.0)

    async def _poll_news(self, symbol: str) -> None:
        """Poll for recent news on symbol."""
        if not self.marketaux_client:
            return

        try:
            # Get news from last 5 minutes
            since = utc_now() - timedelta(minutes=5)

            news = await self.marketaux_client.get_news(
                symbol=symbol,
                since=since,
                limit=10,
            )

            for article in news:
                event = NewsEvent(
                    event_id=f"{symbol}_{article.get('id', '')}",
                    symbol=symbol,
                    headline=article.get('headline', ''),
                    sentiment_score=Decimal(str(article.get('sentiment', 0))),
                    event_type=self._classify_event(article),
                    published_at=since,
                    source=article.get('source', 'marketaux'),
                    url=article.get('url'),
                )

                await self.on_news_event(event)

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.debug(f"Error polling news for {symbol}: {e}")

    def _classify_event(self, article: Dict[str, Any]) -> NewsEventType:
        """Classify news event type."""
        headline = article.get('headline', '').lower()

        keywords = {
            NewsEventType.EARNINGS: ['earnings', 'eps', 'revenue', 'quarterly'],
            NewsEventType.MERGER: ['merger', 'acquisition', 'buyout', 'takeover'],
            NewsEventType.REGULATORY: ['sec', 'fda', 'regulation', 'lawsuit'],
            NewsEventType.MACRO: ['fed', 'inflation', 'gdp', 'interest rate'],
        }

        for event_type, words in keywords.items():
            if any(word in headline for word in words):
                return event_type

        return NewsEventType.OTHER

    def get_sentiment(self, symbol: str) -> Optional[SentimentUpdate]:
        """Get cached sentiment for symbol."""
        return self._sentiment_cache.get(symbol)

    def get_recent_events(self, symbol: Optional[str] = None, limit: int = 50) -> List[NewsEvent]:
        """Get recent news events."""
        if symbol:
            return [e for e in self._event_history if e.symbol == symbol][-limit:]
        return self._event_history[-limit:]

    async def _setup_webhooks(self) -> None:
        """Setup webhook subscriptions."""
        # This would be implemented based on Marketaux webhook API
        # For now, we'll mark webhooks as inactive and use polling
        self._webhook_active = False
        logger.info("Webhooks not configured, using polling mode")

    def is_running(self) -> bool:
        """Check if handler is running."""
        return self._is_running

    def get_subscribed_symbols(self) -> Set[str]:
        """Get all subscribed symbols."""
        return self._subscriptions.copy()

    def clear_cache(self) -> None:
        """Clear sentiment cache."""
        self._sentiment_cache.clear()
        logger.info("Sentiment cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_symbols": len(self._sentiment_cache),
            "total_events": len(self._event_history),
            "subscriptions": len(self._subscriptions),
            "webhook_active": self._webhook_active,
        }
