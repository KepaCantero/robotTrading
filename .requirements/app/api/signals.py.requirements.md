# signals.py

## Purpose
FastAPI endpoints for signal scoring, evaluation, and management with priority queue for actionable trading signals.

---

## Type Definitions / Data Classes

### SignalType (Enum)
- **buy**: Buy signal
- **sell**: Sell signal

### MarketDataRequest (Pydantic BaseModel)
```python
class MarketDataRequest:
    symbol: str          # REQUIRED - trading symbol
    price: float         # REQUIRED - current price
    volume: float        # REQUIRED - current volume
    bid: float           # REQUIRED - current bid
    ask: float           # REQUIRED - current ask
    spread: float        # REQUIRED - bid-ask spread
```

### SignalEvaluationRequest (Pydantic BaseModel)
```python
class SignalEvaluationRequest:
    symbol: str                  # REQUIRED - trading symbol
    signal_type: str             # REQUIRED - "buy" or "sell"
    market_data: MarketDataRequest  # REQUIRED - current market data
    metadata: Dict[str, Any]     # OPTIONAL - additional metadata
```

### SignalResponse (Pydantic BaseModel)
```python
class SignalResponse:
    success: bool                # REQUIRED - whether evaluation succeeded
    signal: Optional[Signal]     # OPTIONAL - evaluated signal if successful
    message: str                 # REQUIRED - result message
```

### SignalStatisticsResponse (Pydantic BaseModel)
```python
class SignalStatisticsResponse:
    signals_processed: int       # REQUIRED - total signals processed
    signals_executed: int        # REQUIRED - total signals executed
    success_rate: float          # REQUIRED - execution success rate
    total_pnl: float             # REQUIRED - total PnL from signals
    queue_size: int              # REQUIRED - current queue size
    queue_summary: Dict[str, Any] # REQUIRED - queue breakdown
    thresholds: Dict[str, float]  # REQUIRED - current thresholds
```

---

## Function Signatures (Contracts)

### `evaluate_signal(request: SignalEvaluationRequest, service: SignalScorerService) -> SignalResponse`
**Pre:** request has valid signal_type, market_data with positive values
**Post:** Returns evaluated signal or rejection if below thresholds
**Raises:** HTTPException(400) on invalid signal_type, HTTPException(500) on errors
**Retry:** No
**Side Effects:** May add signal to priority queue if above thresholds

### `get_next_actionable_signal(service: SignalScorerService) -> SignalResponse`
**Pre:** Service is initialized
**Post:** Returns next highest-priority signal or empty response if none available
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** May remove signal from queue

### `execute_signal(signal_id: str, background_tasks: BackgroundTasks, service: SignalScorerService) -> Dict[str, Any]`
**Pre:** signal_id corresponds to valid symbol
**Post:** Executes signal and returns result
**Raises:** No (returns error in response dict)
**Retry:** No
**Side Effects:** Executes trade, updates signal status

### `get_signal_statistics(service: SignalScorerService) -> SignalStatisticsResponse`
**Pre:** Service is initialized
**Post:** Returns current signal processing statistics
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_signals_by_symbol(symbol: str, service: SignalScorerService) -> List[Signal]`
**Pre:** symbol is non-empty
**Post:** Returns all signals for the symbol
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `clear_expired_signals(max_age_minutes: int, service: SignalScorerService) -> Dict[str, Any]`
**Pre:** max_age_minutes is positive
**Post:** Removes signals older than specified age
**Raises:** HTTPException(500) on errors
**Retry:** No
**Side Effects:** Removes expired signals from queue

### `update_thresholds(confidence_threshold: float, liquidity_threshold: float, service: SignalScorerService) -> Dict[str, Any]`
**Pre:** thresholds are between 0-100
**Post:** Updates minimum thresholds for signal evaluation
**Raises:** HTTPException(400) if thresholds out of range, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Modifies service threshold configuration

### `update_position_size_limit(max_percent: float, service: SignalScorerService) -> Dict[str, Any]`
**Pre:** max_percent is between 0-100
**Post:** Updates maximum position size limit
**Raises:** HTTPException(400) if limit out of range, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Modifies service position size limit

### `signal_health_check(service: SignalScorerService) -> Dict[str, Any]`
**Pre:** Service is initialized
**Post:** Returns health status with statistics
**Raises:** None (returns error status in response)
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] Signal type must be "buy" or "sell" (case-insensitive)
- [ ] Market data values must be positive (price, volume, bid, ask, spread)
- [ ] Thresholds must be between 0-100
- [ ] Position size limit must be between 0-100%
- [ ] Signals below thresholds are rejected with message
- [ ] Next signal returns highest priority from queue
- [ ] Symbol parameters converted to uppercase
- [ ] Max age for clearing expired signals is positive
- [ ] All responses include success indicator
- [ ] Health check returns healthy/unhealthy status

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ✅ FIXED - Added structured logging with correlation IDs |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Good validation |
| API-004 | 06-testing.md | Test coverage | ⚠️ TODO - Requires creating test files |
| API-005 | 28-security-and-secrets.md | Rate limiting | ⚠️ TODO - Requires JWT infrastructure |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling | ✅ FIXED - 2026-02-03 - Added comprehensive error logging with exception handlers |
| API-009 | 09-logging-observability.md | Signal execution logging | ✅ FIXED - Added audit logging for signal operations |
| API-010 | 08-configuration.md | Threshold validation | ✅ OK - Range validation (0-100) |

---

## Dependencies
- **External:** fastapi, pydantic
- **Internal:** app.models.signal, app.providers.paper_trading, app.services.portfolio_service, app.services.signal_scorer

---

## Required Tests
- **test_signals_endpoints.py:**
  - Test evaluate_signal with valid buy signal
  - Test evaluate_signal with valid sell signal
  - Test evaluate_signal rejects invalid signal_type
  - Test evaluate_signal returns rejection when below thresholds
  - Test get_next_actionable_signal returns highest priority
  - Test get_next_actionable_signal returns empty when queue empty
  - Test execute_signal executes trade successfully
  - Test execute_signal returns error for unknown symbol
  - Test get_signal_statistics returns correct stats
  - Test get_signals_by_symbol converts symbol to uppercase
  - Test clear_expired_signals removes old signals
  - Test update_thresholds validates range (0-100)
  - Test update_position_size_limit validates range (0-100)
  - Test signal_health_check returns healthy status

---

## Notes
- Uses singleton pattern for SignalScorerService (global variable)
- Priority queue for signal management
- Background tasks mentioned but not fully utilized
- No authentication visible for signal execution
- Consider WebSocket for real-time signal streaming
- Thresholds configurable at runtime
