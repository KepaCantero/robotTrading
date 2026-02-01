# assets.py

## Purpose
FastAPI endpoints for asset management and identification. Provides REST API for managing asset universes, identifying liquid assets, and retrieving asset rankings.

---

## Type Definitions / Data Classes

### AssetClass (Enum)
- **STOCK**: Stock/equity assets
- **ETF**: Exchange-traded funds
- **CRYPTO**: Cryptocurrency assets
- **FOREX**: Foreign exchange pairs
- **COMMODITY**: Commodity assets
- **INDEX**: Market indices
- **BOND**: Bond/fixed income assets

### Exchange (Enum)
- **NYSE**: New York Stock Exchange
- **NASDAQ**: NASDAQ exchange
- **AMEX**: American Stock Exchange
- **LSE**: London Stock Exchange
- **TSE**: Tokyo Stock Exchange
- **HKG**: Hong Kong Stock Exchange
- **Binance**: Binance crypto exchange
- **Kraken**: Kraken crypto exchange
- **Coinbase**: Coinbase crypto exchange
- **Forex.com**: Forex broker
- **Oanda**: Oanda forex broker
- **Interactive_Brokers**: Interactive Brokers

### AssetFilter (Pydantic BaseModel)
```python
class AssetFilter:
    min_liquidity_score: Decimal    # REQUIRED - minimum liquidity threshold (0-100)
    min_volume: Decimal              # REQUIRED - minimum average volume
    max_spread: Decimal              # REQUIRED - maximum bid-ask spread
    exchanges: Optional[List[Exchange]]  # OPTIONAL - filter by exchanges
    active_only: bool                # REQUIRED - only return active assets
```

**Validation Rules:**
- `min_liquidity_score` must be between 0 and 100
- `min_volume` must be positive
- `max_spread` must be non-negative
- `active_only` defaults to True

---

## Function Signatures (Contracts)

### `get_assets_overview(service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** Asset identification service is initialized
**Post:** Returns overview with summary for each asset class
**Raises:** HTTPException(500) on connection/timeout errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_liquid_assets(asset_class: AssetClass, limit: int, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** asset_class is valid, limit is between 1-100
**Post:** Returns top N liquid assets for specified class
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_asset_rankings_by_class(asset_class: AssetClass, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** asset_class is valid enum value
**Post:** Returns asset rankings with ranking_date and rankings list
**Raises:** HTTPException(500) on connection errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_asset_details(symbol: str, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** symbol is a non-empty string
**Post:** Returns detailed asset information or 404 if not found
**Raises:** HTTPException(404) if asset not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_liquidity_metrics(symbol: str, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** symbol is a valid asset identifier
**Post:** Returns liquidity metrics including scores and volatility
**Raises:** HTTPException(404) if metrics not found
**Retry:** No
**Side Effects:** None (read-only)

### `filter_assets(filter_criteria: AssetFilter, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** filter_criteria contains valid constraints
**Post:** Returns filtered assets matching criteria
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `refresh_liquidity_data(background_tasks: BackgroundTasks, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** background_tasks is initialized
**Post:** Schedules background refresh of liquidity data
**Raises:** HTTPException(500) if task scheduling fails
**Retry:** No
**Side Effects:** Initiates background task to update liquidity data

### `identify_liquid_assets(asset_class: AssetClass, limit: int, background_tasks: BackgroundTasks, service: AssetIdentificationService) -> Dict[str, Any]`
**Pre:** asset_class is valid, limit is 1-100
**Post:** Returns identified liquid assets and schedules universe update
**Raises:** HTTPException(500) on identification errors
**Retry:** No
**Side Effects:** Updates asset universe in background

---

## Acceptance Criteria
- [ ] All endpoints return 200 OK on successful requests
- [ ] All endpoints handle ConnectionError, TimeoutError, OSError with 500 status
- [ ] Symbol parameters are converted to uppercase before processing
- [ ] Limit parameters are validated to be between 1-100
- [ ] Background tasks are scheduled for async operations
- [ ] All responses include timestamp in UTC
- [ ] All responses include success boolean flag
- [ ] Asset not found errors return 404 status code

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials in endpoints | ✅ OK |
| API-002 | 09-logging-observability.md | Log all asset access with context | ⚠️ NOT APPLIED - Logging minimal |
| API-003 | 07-async-patterns.md | All service calls must be awaited | ✅ OK |
| API-004 | 08-configuration.md | Validate all input parameters | ✅ OK - Query parameters validated |
| API-005 | 05-architecture.md | API layer only handles HTTP concerns | ✅ OK - Delegates to service |
| API-006 | 06-testing.md | All endpoints have test coverage | ❌ GAP - No evidence of tests |
| API-007 | 12-logging-observability.md | Structured logging with correlation IDs | ❌ GAP - No correlation IDs |
| API-008 | 28-security-and-secrets.md | Rate limiting on expensive endpoints | ❌ GAP - No rate limiting visible |
| API-009 | 09-logging-observability.md | Error logging with stack traces | ⚠️ PARTIAL - Logs errors but no stack traces |
| API-010 | 07-async-patterns.md | Timeout handling for async operations | ❌ GAP - No explicit timeout configuration |

---

## Dependencies
- **External:** fastapi, pydantic, requests
- **Internal:** app.models.assets, app.services.asset_identification

---

## Required Tests
- **test_assets_endpoints.py:**
  - Test get_assets_overview returns all asset class summaries
  - Test get_liquid_assets with valid/invalid limits
  - Test get_asset_details returns 404 for non-existent symbols
  - Test filter_assets with various filter criteria
  - Test refresh_liquidity_data schedules background task
  - Test identify_liquid_assets updates universe in background
  - Test all endpoints handle connection errors gracefully
  - Test symbol parameter normalization (uppercase)

---

## Notes
- Uses BackgroundTasks for async liquidity refresh operations
- No authentication/authorization visible - consider adding for production
- Asset universe data source not specified (likely external API or database)
