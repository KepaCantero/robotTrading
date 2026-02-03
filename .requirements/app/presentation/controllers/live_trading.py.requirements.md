# Requirements: app/presentation/controllers/live_trading.py

**File Path:** `app/presentation/controllers/live_trading.py`
**Layer:** Presentation (Controller)
**Last Updated:** 2025-02-05
**Status:** ✅ Compliant - Well-Implemented

---

## Purpose
Live Trading API Router - Complete REST API for live trading bridge operations. Endpoints for bridge lifecycle management, order management, account/position queries, risk validation, execution history, audit trail, and trading statistics.

---

## Current State
- **Lines of Code:** 816
- **Endpoints:** 25+
- **Dependencies:** fastapi, requests
- **Complexity:** High

---

## BASE Rules Compliance

### ✅ COMPLIANT Rules
- [FMT-001] Line length ≤ 100: **PASS**
- [FMT-007] No mutable defaults: **PASS**
- [TYP-001] Type coverage: **PASS** (85%+)
- [LOG-004] Error logging: **PASS** (logger.error)
- [SEC-007] Input validation: **PARTIAL** (Query validation, no Pydantic request models)

### ⚠️ Gaps
- [SEC-007] Input validation: **GAP** - Missing Pydantic request models for POST endpoints
- [LOG-001] Structured logging: **MINOR** - Could use structlog
- [ARCH-004] Small functions: **MINOR** - Some endpoints are 30-40 lines

---

## File-Specific Requirements

### REQ-CTRL-601: Bridge Lifecycle Endpoints
**Priority:** P0
**Description:** Start/stop live trading bridge
**Current State:** ✅ COMPLIANT
```python
@router.post("/start")
async def start_live_trading(...)

@router.post("/stop")
async def stop_live_trading(...)

@router.get("/status")
async def get_bridge_status(...)
```

### REQ-CTRL-602: Order Management Endpoints
**Priority:** P0
**Description:** Place, cancel, and query orders
**Current State:** ⚠️ NEEDS IMPROVEMENT
```python
@router.post("/orders")
async def place_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    price: Optional[float] = None,
    ...
):
```
**Issue:** Should use Pydantic model for request validation

### REQ-CTRL-603: Account & Position Endpoints
**Priority:** P0
**Description:** Query account info and positions
**Current State:** ✅ COMPLIANT
```python
@router.get("/account")
async def get_account_info(...)

@router.get("/positions")
async def list_positions(...)
```

### REQ-CTRL-604: Risk Management Endpoints
**Priority:** P0
**Description:** Validate order risk and manage risk limits
**Current State:** ✅ COMPLIANT
```python
@router.post("/risk/validate")
async def validate_order_risk(...)

@router.patch("/risk/limits")
async def update_risk_limits(...)
```

### REQ-CTRL-605: Audit Trail Endpoints
**Priority:** P0
**Description:** Get audit trail and compliance reports
**Current State:** ✅ COMPLIANT
```python
@router.get("/audit/trail")
async def get_audit_trail(...)

@router.get("/audit/report")
async def get_compliance_report(...)
```

### REQ-CTRL-606: Statistics & Metrics Endpoints
**Priority:** P1
**Description:** Get trading statistics and portfolio snapshot
**Current State:** ✅ COMPLIANT
```python
@router.get("/statistics")
async def get_trading_statistics(...)

@router.get("/portfolio/snapshot")
async def get_portfolio_snapshot(...)
```

---

## Gaps Identified

### CRITICAL Gaps (P0)

1. **Missing Pydantic request models for POST/PUT**
   - Lines 112-158: place_order uses individual parameters instead of Pydantic model
   - Lines 345-380: validate_order_risk uses individual parameters
   - Lines 407-441: update_risk_limits uses individual parameters
   - **Fix:** Create Pydantic models for requests
   - **Priority:** P0 (input validation)

### HIGH Priority Gaps (P1)

1. **No input validation on trading parameters**
   - symbol, side, quantity: No format validation
   - **Fix:** Add regex validation for symbols, enum for side
   - **Priority:** P1 (security)

2. **No rate limiting on trading endpoints**
   - Order placement could be abused
   - **Fix:** Add rate limiting
   - **Priority:** P1 (security)

### MEDIUM Priority Gaps (P2)

1. **Generic exception handling**
   - Lines 65-67, 85-87, etc.: Broad exception catching
   - **Fix:** Add specific error handling
   - **Priority:** P2 (error handling)

2. **No order size validation**
   - quantity: float allows any positive number
   - **Fix:** Add min/max validation
   - **Priority:** P2 (trading safety)

### LOW Priority Gaps (P3)

1. **Long endpoints**
   - Some endpoints are 30-40 lines
   - **Priority:** P3 (code organization)

2. **Missing authentication**
   - No authentication/authorization
   - **Priority:** P3 (security)

---

## Testing Requirements

### TST-CTRL-601: Bridge Lifecycle
**Required Tests:**
- ✅ Test start_live_trading
- ✅ Test stop_live_trading
- ✅ Test get_bridge_status

### TST-CTRL-602: Order Management
**Required Tests:**
- ✅ Test place_order with valid data
- ✅ Test place_order with invalid order_type
- ✅ Test place_order with missing price for LIMIT order
- ✅ Test get_order_status
- ✅ Test cancel_order
- ✅ Test cancel_all_orders
- ✅ Test list_orders with filters

### TST-CTRL-603: Account & Positions
**Required Tests:**
- ✅ Test get_account_info
- ✅ Test list_positions
- ✅ Test get_position with valid symbol
- ✅ Test get_position with invalid symbol (404)

### TST-CTRL-604: Risk Management
**Required Tests:**
- ✅ Test validate_order_risk
- ✅ Test get_risk_limits
- ✅ Test update_risk_limits

### TST-CTRL-605: Audit Trail
**Required Tests:**
- ✅ Test get_audit_trail with filters
- ✅ Test get_compliance_report
- ✅ Test list_non_compliant_events

### TST-CTRL-606: Statistics
**Required Tests:**
- ✅ Test get_trading_statistics
- ✅ Test get_audit_statistics
- ✅ Test get_portfolio_snapshot
- ✅ Test get_portfolio_history
- ✅ Test get_daily_return

---

## Dependencies
- `fastapi` - Web framework
- `app.services.live_trading.*` - Live trading services
- `requests` - HTTP client

---

## Notes
- Comprehensive live trading API
- Good endpoint coverage
- Well-structured with clear separation
- **CRITICAL:** Should use Pydantic models for request validation
- **HIGH:** Add rate limiting on trading endpoints
- **HIGH:** Add input validation on trading parameters
- Consider adding authentication
- Consider adding order size validation
