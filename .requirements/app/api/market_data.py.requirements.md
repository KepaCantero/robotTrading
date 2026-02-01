# market_data.py

## Purpose
FastAPI endpoints for market data management including quotes, historical data, and feed configuration.

---

## Type Definitions / Data Classes

### CreateFeedConfigRequest (Pydantic BaseModel)
```python
class CreateFeedConfigRequest:
    name: str                           # REQUIRED - feed configuration name
    feed_type: DataFeedType             # REQUIRED - type of data feed (enum)
    api_key: Optional[str]              # OPTIONAL - API key for the feed
    base_url: str                       # REQUIRED - base URL for the API
    rate_limit: int                     # OPTIONAL - requests per minute (1-3600, default 60)
    supported_symbols: List[str]        # OPTIONAL - list of supported symbols
    supported_frequencies: List[DataFrequency]  # OPTIONAL - supported data frequencies
    max_history_days: int               # OPTIONAL - max historical days (1-3650, default 365)
    timeout_seconds: int                # OPTIONAL - request timeout (1-300, default 30)
    retry_attempts: int                 # OPTIONAL - retry attempts (0-10, default 3)
    retry_delay: float                  # OPTIONAL - retry delay in seconds (0.1-60.0, default 1.0)
    is_active: bool                     # OPTIONAL - whether feed is active (default True)
```

**Validation Rules:**
- `rate_limit` must be between 1-3600
- `max_history_days` must be between 1-3650
- `timeout_seconds` must be between 1-300
- `retry_attempts` must be between 0-10
- `retry_delay` must be between 0.1-60.0

### SubscribeRequest (Pydantic BaseModel)
```python
class SubscribeRequest:
    symbols: List[str]                  # REQUIRED - symbols to subscribe to
    feed_id: Optional[UUID]             # OPTIONAL - specific feed ID to use
    frequency: DataFrequency            # OPTIONAL - data update frequency (default REAL_TIME)
```

### QuoteResponse (Pydantic BaseModel)
```python
class QuoteResponse:
    success: bool                       # REQUIRED - whether request succeeded
    data: Optional[Quote]               # OPTIONAL - quote data
    error: Optional[str]                # OPTIONAL - error message
    timestamp: datetime                 # REQUIRED - response timestamp
```

### HistoricalDataResponse (Pydantic BaseModel)
```python
class HistoricalDataResponse:
    success: bool                       # REQUIRED
    data: List[HistoricalData]          # REQUIRED - historical data points
    count: int                          # REQUIRED - number of data points
    error: Optional[str]                # OPTIONAL - error message
    timestamp: datetime                 # REQUIRED
```

---

## Function Signatures (Contracts)

### `get_quote(symbol: str, feed_id: Optional[UUID], service: MarketDataService) -> QuoteResponse`
**Pre:** symbol is non-empty, feed_id is valid UUID if provided
**Post:** Returns quote data or error if unavailable
**Raises:** HTTPException(500) on connection errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_multiple_quotes(symbols: List[str], feed_id: Optional[UUID], service: MarketDataService) -> List[QuoteResponse]`
**Pre:** symbols list is non-empty
**Post:** Returns list of quote responses (one per symbol)
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_top_liquid_quotes(limit: int, service: MarketDataService) -> List[QuoteResponse]`
**Pre:** limit is between 1-100
**Post:** Returns quotes for top liquid assets
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_historical_data(symbol: str, start_date: datetime, end_date: datetime, frequency: DataFrequency, feed_id: Optional[UUID], service: MarketDataService) -> HistoricalDataResponse`
**Pre:** symbol is valid, start_date < end_date, date range <= 365 days
**Post:** Returns historical data points for the period
**Raises:** HTTPException(400) on invalid date range, HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `create_feed_config(request: CreateFeedConfigRequest, service: MarketDataService) -> FeedConfigResponse`
**Pre:** request contains valid feed configuration
**Post:** Creates feed config and returns with generated ID
**Raises:** HTTPException(500) on creation errors
**Retry:** No
**Side Effects:** Creates new feed configuration in service

### `list_feed_configs(service: MarketDataService) -> FeedConfigsResponse`
**Pre:** None
**Post:** Returns all feed configurations
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_feed_config(config_id: UUID, service: MarketDataService) -> FeedConfigResponse`
**Pre:** config_id is valid UUID
**Post:** Returns feed configuration or 404 if not found
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `connect_feed(config_id: UUID, service: MarketDataService) -> Dict`
**Pre:** config_id exists
**Post:** Connects to feed and returns success status
**Raises:** HTTPException(500) if connection fails
**Retry:** No
**Side Effects:** Establishes connection to data feed

### `disconnect_feed(config_id: UUID, service: MarketDataService) -> Dict`
**Pre:** config_id exists
**Post:** Disconnects from feed and returns success status
**Raises:** HTTPException(500) if disconnection fails
**Retry:** No
**Side Effects:** Closes connection to data feed

### `subscribe_to_symbols(request: SubscribeRequest, service: MarketDataService) -> Dict`
**Pre:** symbols list is non-empty
**Post:** Subscribes to real-time updates for symbols
**Raises:** HTTPException(500) if subscription fails
**Retry:** No
**Side Effects:** Initiates real-time data streaming

### `get_service_status(service: MarketDataService) -> ServiceStatusResponse`
**Pre:** None
**Post:** Returns service status information
**Raises:** HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `clear_cache(service: MarketDataService) -> Dict`
**Pre:** None
**Post:** Clears all cached market data
**Raises:** HTTPException(500) on errors
**Retry:** No
**Side Effects:** Removes all cached data

### `get_cache_stats(service: MarketDataService) -> Dict`
**Pre:** None
**Post:** Returns cache statistics
**Raises:** HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] Date range validation enforces max 365 days
- [ ] start_date must be before end_date
- [ ] All responses include UTC timestamp
- [ ] Limit parameter validated 1-100 for quotes endpoints
- [ ] Feed config validation enforces all numeric ranges
- [ ] All endpoints handle connection errors with 500 status
- [ ] get_feed_config returns 404 for non-existent configs
- [ ] Cache operations report success/failure
- [ ] All responses use consistent response model structure

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded API keys | ⚠️ PARTIAL - API keys in config, need validation |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Basic error handling |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Comprehensive Pydantic validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Secure API key storage | ⚠️ PARTIAL - API keys in config object |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-005 | 09-logging-observability.md | Request/response logging | ❌ GAP - No request logging |
| API-006 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-007 | 12-logging-observability.md | Error handling with context | ⚠️ PARTIAL - Generic error messages |
| API-008 | 08-configuration.md | Configuration validation | ✅ OK - Field-level validation |

---

## Dependencies
- **External:** fastapi, pydantic, requests, uuid
- **Internal:** app.models.market_data, app.services.market_data_service

---

## Required Tests
- **test_market_data_endpoints.py:**
  - Test get_quote with valid/invalid symbols
  - Test get_historical_data with invalid date ranges (start >= end)
  - Test get_historical_data rejects ranges > 365 days
  - Test create_feed_config with valid configuration
  - Test create_feed_config validates all numeric constraints
  - Test connect_feed returns success/failure appropriately
  - Test get_feed_config returns 404 for non-existent config
  - Test subscribe_to_symbols with symbol list
  - Test clear_cache clears cached data
  - Test get_cache_stats returns cache metrics
  - Test all endpoints handle connection errors gracefully

---

## Notes
- Comprehensive input validation via Pydantic models
- API keys stored in feed config - ensure encryption at rest
- Cache operations need persistence consideration
- Real-time subscription requires WebSocket or SSE for actual implementation
- No rate limiting visible on expensive historical data queries
