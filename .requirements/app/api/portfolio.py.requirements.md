# portfolio.py

## Purpose
FastAPI endpoints for portfolio management and monitoring with circuit breaker pattern for resilience.

---

## Type Definitions / Data Classes

### TradeRequest (Pydantic BaseModel)
```python
class TradeRequest:
    symbol: str                  # REQUIRED - trading symbol
    quantity: float              # REQUIRED - trade quantity (can be negative for sells)
    price: Optional[float]       # OPTIONAL - trade price
```

### TradeResponse (Pydantic BaseModel)
```python
class TradeResponse:
    success: bool                # REQUIRED - whether trade succeeded
    message: str                 # REQUIRED - result message
    symbol: str                  # REQUIRED - traded symbol
    quantity: float              # REQUIRED - traded quantity
    price: Optional[float]       # OPTIONAL - trade price
```

### Position (from app.models.portfolio)
```python
class Position:
    symbol: str                  # REQUIRED - trading symbol
    asset_class: AssetClass      # REQUIRED - asset class enum
    quantity: Decimal            # REQUIRED - position quantity
    avg_price: Decimal           # REQUIRED - average entry price
    market_price: Decimal        # REQUIRED - current market price
    unrealized_pnl: Decimal      # REQUIRED - unrealized PnL
    realized_pnl: Decimal        # REQUIRED - realized PnL
    currency: str                # REQUIRED - position currency
    broker: str                  # REQUIRED - broker identifier
```

### AssetUniverse (from app.models.portfolio)
```python
class AssetUniverse:
    asset_class: AssetClass      # REQUIRED - asset class
    symbols: List[str]           # REQUIRED - available symbols
    description: str             # REQUIRED - description
```

### MarketRegimeData (from app.models.portfolio)
```python
class MarketRegimeData:
    symbol: str                  # REQUIRED - trading symbol
    regime: str                  # REQUIRED - current regime (bull/bear/sideways)
    confidence: float            # REQUIRED - regime confidence
    volatility: str              # REQUIRED - volatility level
    trend: str                   # REQUIRED - trend direction
    timestamp: datetime          # REQUIRED - analysis timestamp
```

---

## Function Signatures (Contracts)

### `get_portfolio_summary(service: PortfolioService) -> Dict[str, Any]`
**Pre:** Service is initialized and circuit breaker is not open
**Post:** Returns portfolio summary with circuit breaker status
**Raises:** HTTPException(503) if circuit breaker open, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only, may trigger circuit breaker)

### `get_positions(service: PortfolioService) -> List[Position]`
**Pre:** Service is initialized and circuit breaker is not open
**Post:** Returns all positions in portfolio
**Raises:** HTTPException(503) if circuit breaker open, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only, may trigger circuit breaker)

### `get_position(symbol: str, service: PortfolioService) -> Position`
**Pre:** symbol is non-empty, service accessible
**Post:** Returns position for symbol or 404 if not found
**Raises:** HTTPException(404) if position not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_asset_universe(service: PortfolioService) -> List[AssetUniverse]`
**Pre:** Service is initialized
**Post:** Returns list of supported asset universes
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_market_regime(symbol: str, service: PortfolioService) -> MarketRegimeData`
**Pre:** symbol is non-empty
**Post:** Returns market regime data for symbol
**Raises:** HTTPException(404) if regime not available, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `simulate_trade(trade_request: TradeRequest, service: PortfolioService) -> TradeResponse`
**Pre:** trade_request has valid symbol and quantity
**Post:** Simulates trade and returns result without executing
**Raises:** HTTPException(500) on simulation errors
**Retry:** No
**Side Effects:** None (simulation only, no state change)

### `get_circuit_breaker_status(service: PortfolioService) -> Dict[str, Dict[str, Any]]`
**Pre:** Service is initialized
**Post:** Returns status of all circuit breakers
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `reset_circuit_breaker(name: str, service: PortfolioService) -> Dict[str, str]`
**Pre:** Circuit breaker name is valid
**Post:** Resets circuit breaker to closed state
**Raises:** HTTPException(500) on reset errors
**Retry:** No
**Side Effects:** Resets circuit breaker state

### `portfolio_health_check(service: PortfolioService) -> Dict[str, Any]`
**Pre:** Service is initialized
**Post:** Returns health status with circuit breaker information
**Raises:** None (returns error status on failure)
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] All symbol parameters converted to uppercase
- [ ] Circuit breaker prevents calls when open (503 response)
- [ ] Portfolio unavailable returns 503 status
- [ ] Position not found returns 404 status
- [ ] Circuit breaker status includes state (open/closed) and failure counts
- [ ] Health check returns degraded status with open breakers
- [ ] All responses use consistent structure
- [ ] Trade simulation validates quantity and price

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - No logging visible |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Basic validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Circuit breaker pattern | ✅ OK - Implemented |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling with context | ⚠️ PARTIAL - Basic error handling |
| API-009 | 09-logging-observability.md | Circuit breaker state logging | ❌ GAP - No CB logging |
| API-010 | 12-logging-observability.md | Health check implementation | ✅ OK - Comprehensive health check |

---

## Dependencies
- **External:** fastapi, pydantic, requests
- **Internal:** app.models.portfolio, app.providers.paper_trading, app.services.portfolio_service

---

## Required Tests
- **test_portfolio_endpoints.py:**
  - Test get_portfolio_summary returns valid summary
  - Test get_portfolio_summary returns 503 when circuit breaker open
  - Test get_positions returns all positions
  - Test get_position returns 404 for non-existent symbol
  - Test get_position converts symbol to uppercase
  - Test get_asset_universe returns supported asset classes
  - Test get_market_regime returns 404 when unavailable
  - Test simulate_trade returns success/failure correctly
  - Test get_circuit_breaker_status returns all breaker states
  - Test reset_circuit_breaker resets breaker state
  - Test portfolio_health_check returns degraded with open breakers
  - Test all endpoints handle timeout/connection errors

---

## Notes
- Implements circuit breaker pattern for resilience
- Uses singleton pattern for PortfolioService (global variable)
- No authentication visible
- Security compliance mentioned in docstring (95%) but implementation needs verification
- Consider adding audit logging for portfolio access
