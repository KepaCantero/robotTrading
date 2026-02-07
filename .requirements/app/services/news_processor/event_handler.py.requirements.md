# Requirements: services/news_processor/event_handler.py

## Source File Analysis
- **File Path**: `app/services/news_processor/event_handler.py`
- **Lines of Code**: 402
- **Status:** AUDIT COMPLETE

## Purpose
Real-time news event processor with webhook subscription, sentiment updates, trade triggers on significant news, sentiment cache, and polling fallback.

## Dependencies
- Internal:
  - `app.core.timezone_utils.utc_now`
- External:
  - `asyncio`, `logging`, `dataclasses`, `datetime`, `decimal`, `enum`

## Classes/Functions

### Enums
- `NewsEventType`: EARNINGS, MERGER, GUIDANCE, REGULATORY, MACRO, ANALYST, OTHER

### Data Classes
- `NewsEvent`: Represents news article with sentiment
- `SentimentUpdate`: Sentiment change for symbol

### Main Class: NewsEventHandler
- `__init__(marketaux_client, on_trade_trigger, cache_ttl_seconds)`: Initialize handler
- `start()`: Start event processing with webhooks/polling
- `stop()`: Stop processing and unsubscribe
- `subscribe_to_news(symbols, webhook_url)`: Subscribe to webhooks
- `unsubscribe_from_news(symbol)`: Unsubscribe from symbol
- `on_news_event(event)`: Process news event and update sentiment
- `should_trigger_trade(event)`: Check if sentiment triggers trade
- `execute_trade_signal(event, sentiment)`: Create and execute signal
- `_polling_loop()`: Fallback polling loop
- `_poll_news(symbol)`: Poll for recent news
- `_classify_event(article)`: Classify news type by keywords
- `get_sentiment(symbol)`: Get cached sentiment
- `get_recent_events(symbol, limit)`: Get event history
- `clear_cache()`: Clear sentiment cache
- `get_cache_stats()`: Get cache statistics

## Business Logic
1. **Webhook First**: Tries webhook subscriptions, falls back to polling
2. **Sentiment EMA**: Updates sentiment using exponential moving average (alpha=0.3)
3. **Trade Triggers**:
   - Sentiment > 0.5 or < -0.5 triggers trade
   - Change > 0.3 triggers trade
4. **Event History**: Keeps last 1000 events
5. **Polling Fallback**: 5-minute intervals if webhooks fail

## Data Models
- NewsEvent with event_id, symbol, headline, sentiment_score, event_type
- SentimentUpdate with previous_score, change, news_count

## API Contracts
- Optional `marketaux_client` for API integration
- Optional `on_trade_trigger` callback
- Configurable cache TTL (default 300 seconds)

## Error Handling
- Exception types: `(asyncio.TimeoutError, ConnectionError, OSError)`
- Graceful degradation on webhook failures
- Cancellation handling in polling loop

## Performance Considerations
- Event history limited to 1000 entries
- 5-minute cache TTL
- Polling every 5 minutes (configurable)
- Async operations for concurrent processing

## Testing Strategy
- Test webhook subscription failure fallback
- Test sentiment EMA calculation
- Test trade trigger thresholds
- Test cache overflow handling
- Test polling loop cancellation

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Clean async implementation with proper error handling

**Checks Against BASE_RULES.md:**
- ✅ ASYNC-001: Proper async def usage
- ✅ ASYNC-002: All async calls properly awaited
- ✅ ASYNC-003: Async context managers would be beneficial
- ✅ ASYNC-004: No time.sleep() (uses asyncio.sleep())
- ✅ ASYNC-006: Handles asyncio.TimeoutError
- ✅ CC-001: Descriptive class/method names
- ✅ LOG-003: Appropriate log levels (info, warning, error)
- ✅ LOG-004: Error logging with context
- ✅ FMT-007: No mutable defaults

**Minor Notes:**
- `asyncio.create_task()` for polling loop - fire-and-forget acceptable here
- Event history cleanup is simple but effective

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0076*
