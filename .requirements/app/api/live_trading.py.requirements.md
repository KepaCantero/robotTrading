# live_trading.py

## Purpose
Complete REST API for live trading bridge operations - provides endpoints for bridge lifecycle, order management, account/position queries, risk validation, execution history, audit trail, and trading statistics.

---

## Type Definitions / Data Classes

### APIRouter
```python
router = APIRouter(prefix="/live-trading", tags=["live-trading"])
```

### Endpoint Categories
1. **Bridge Lifecycle** - Start/stop/status
2. **Order Management** - Place, cancel, list orders
3. **Account & Positions** - Get account info, list positions
4. **Risk Management** - Validate orders, get/update risk limits
5. **Execution History** - List executions, get execution details
6. **Audit Trail & Compliance** - Get audit trail, compliance reports
7. **Statistics & Metrics** - Trading statistics, audit statistics
8. **Portfolio** - Snapshot, history, daily return
9. **Alert-to-Trade Mapping** - Create/delete rules, list signals

---

## Function Signatures (Contracts)

### Bridge Lifecycle Endpoints

### `@router.post("/start") async start_live_trading(orchestrator) -> dict`
**Pre:** orchestrator initialized
**Post:** Trading bridge started
**Raises:** HTTPException 500 if start fails
**Retry:** No
**Side Effects:** Initializes components, starts monitoring

**Returns:**
```python
{
    "status": "started",
    "message": "Live trading bridge started successfully",
    "timestamp": ISO format
}
```

### `@router.post("/stop") async stop_live_trading(orchestrator) -> dict`
**Pre:** orchestrator running
**Post:** Trading bridge stopped gracefully
**Raises:** HTTPException 500 if stop fails
**Retry:** No
**Side Effects:** Shuts down all components

### `@router.get("/status") async get_bridge_status(orchestrator) -> dict`
**Pre:** orchestrator initialized
**Post:** Returns bridge status and statistics
**Raises:** HTTPException 500 if status retrieval fails
**Retry:** No
**Side Effects:** None

### Order Management Endpoints

### `@router.post("/orders") async place_order(symbol, side, quantity, order_type, price, stop_price, order_manager) -> dict`
**Pre:** order_manager initialized, symbol valid
**Post:** Order placed and order_id returned
**Raises:** ValueError if validation fails, HTTPException 400/500
**Retry:** No
**Side Effects:** Submits order to broker

**Validations:**
- LIMIT orders require price
- STOP orders require stop_price

### `@router.get("/orders/{order_id}") async get_order_status(order_id, order_manager) -> dict`
**Pre:** order_manager initialized
**Post:** Returns order status
**Raises:** HTTPException 404 if not found, 500 if error
**Retry:** No
**Side Effects:** None

### `@router.delete("/orders/{order_id}") async cancel_order(order_id, order_manager) -> dict`
**Pre:** order_manager initialized, order exists
**Post:** Order cancelled
**Raises:** HTTPException 400 if cancel fails, 404 if not found, 500 if error
**Retry:** No
**Side Effects:** Submits cancel request to broker

### `@router.post("/orders/cancel-all") async cancel_all_orders(order_manager) -> dict`
**Pre:** order_manager initialized
**Post:** All pending orders cancelled
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** Cancels all orders

### `@router.get("/orders") async list_orders(status, symbol, limit, order_manager) -> dict`
**Pre:** order_manager initialized
**Post:** Returns filtered list of orders
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

**Filters:**
- status: "pending", "executed", or None (all)
- symbol: Filter by symbol
- limit: Max results (1-1000, default 100)

### Account & Position Endpoints

### `@router.get("/account") async get_account_info(broker) -> dict`
**Pre:** broker connected
**Post:** Returns account information
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

**Returns:** account_id, broker_type, currency, cash_available, portfolio_value, buying_power, equity, margin_used, margin_multiplier

### `@router.get("/positions") async list_positions(broker) -> dict`
**Pre:** broker connected
**Post:** Returns all positions
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### `@router.get("/positions/{symbol}") async get_position(symbol, broker) -> dict`
**Pre:** broker connected
**Post:** Returns position for symbol
**Raises:** HTTPException 404 if not found, 500 if error
**Retry:** No
**Side Effects:** None

### Risk Management Endpoints

### `@router.post("/risk/validate") async validate_order_risk(symbol, side, quantity, risk_gates, broker) -> dict`
**Pre:** risk_gates and broker initialized
**Post:** Returns validation result
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

**Returns:** is_valid, risk_level, violations, warnings

### `@router.get("/risk/limits") async get_risk_limits(risk_gates) -> dict`
**Pre:** risk_gates initialized
**Post:** Returns current risk limits
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### `@router.patch("/risk/limits") async update_risk_limits(...) -> dict`
**Pre:** risk_gates initialized
**Post:** Risk limits updated
**Raises:** HTTPException 400 if update fails
**Retry:** No
**Side Effects:** Updates risk gate configuration

### Execution History Endpoints

### `@router.get("/executions") async list_executions(status, symbol, start_date, end_date, limit, orchestrator) -> dict`
**Pre:** orchestrator initialized
**Post:** Returns filtered executions
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

**Filters:** status, symbol, date range (start/end), limit (1-1000)

### `@router.get("/executions/{execution_id}") async get_execution(execution_id, orchestrator) -> dict`
**Pre:** orchestrator initialized
**Post:** Returns execution details
**Raises:** HTTPException 404 if not found, 500 if error
**Retry:** No
**Side Effects:** None

### Audit Trail & Compliance Endpoints

### `@router.get("/audit/trail") async get_audit_trail(event_type, symbol, start_date, end_date, limit, audit_trail) -> dict`
**Pre:** audit_trail initialized
**Post:** Returns filtered audit events
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

**Filters:** event_type, symbol, date range, limit

### `@router.get("/audit/report") async get_compliance_report(days, audit_trail) -> dict`
**Pre:** audit_trail initialized
**Post:** Returns compliance report
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** Generates report for period

**Parameters:** days (1-365, default 30)

### `@router.get("/audit/non-compliant") async list_non_compliant_events(limit, audit_trail) -> dict`
**Pre:** audit_trail initialized
**Post:** Returns non-compliant events
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### Statistics & Metrics Endpoints

### `@router.get("/statistics") async get_trading_statistics(orchestrator) -> dict`
**Pre:** orchestrator initialized
**Post:** Returns trading statistics
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### `@router.get("/audit/statistics") async get_audit_statistics(audit_trail) -> dict`
**Pre:** audit_trail initialized
**Post:** Returns audit statistics
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### Portfolio Endpoints

### `@router.get("/portfolio/snapshot") async get_portfolio_snapshot(account_sync) -> dict`
**Pre:** account_sync initialized
**Post:** Returns portfolio snapshot
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** Takes snapshot

### `@router.get("/portfolio/history") async get_portfolio_history(days, account_sync) -> dict`
**Pre:** account_sync initialized
**Post:** Returns portfolio history
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** Retrieves history

### `@router.get("/portfolio/daily-return") async get_daily_return(account_sync) -> dict`
**Pre:** account_sync initialized
**Post:** Returns daily P&L
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** Calculates daily return

### Alert-to-Trade Mapping Endpoints

### `@router.post("/rules") async create_alert_to_trade_rule(rule_data, mapper) -> dict`
**Pre:** mapper initialized
**Post:** Rule created
**Raises:** HTTPException 400 if creation fails
**Retry:** No
**Side Effects:** Registers new rule

### `@router.delete("/rules/{rule_id}") async delete_alert_to_trade_rule(rule_id, mapper) -> dict`
**Pre:** mapper initialized, rule exists
**Post:** Rule deleted
**Raises:** HTTPException 400 if deletion fails
**Retry:** No
**Side Effects:** Unregisters rule

### `@router.get("/signals/pending") async list_pending_signals(limit, mapper) -> dict`
**Pre:** mapper initialized
**Post:** Returns pending signals
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

### `@router.get("/signals/statistics") async get_signal_statistics(mapper) -> dict`
**Pre:** mapper initialized
**Post:** Returns signal statistics
**Raises:** HTTPException 500 if error
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All endpoints use FastAPI dependency injection
- [ ] All endpoints catch specific exceptions
- [ ] All endpoints log errors
- [ ] All endpoints return ISO format timestamps
- [ ] All query parameters validated (limit, days, etc.)
- [ ] Order validation (LIMIT needs price, STOP needs stop_price)
- [ ] Risk limits dynamically updatable
- [ ] Compliance reports generated for configurable periods
- [ ] Portfolio history filtered by date range
- [ ] All endpoints have appropriate HTTP status codes

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input Validation | BASE_RULES.md | All inputs validated | ✅ OK |
| Error Handling | BASE_RULES.md | Specific exceptions | ✅ OK |
| Logging | BASE_RULES.md | All operations logged | ✅ OK |
| Type Hints | BASE_RULES.md | All functions typed | ✅ OK |
| HTTP Status Codes | BASE_RULES.md | Appropriate codes | ✅ OK |
| Dependency Injection | BASE_RULES.md | FastAPI Depends | ✅ OK |
| Timestamp Format | BASE_RULES.md | ISO 8601 | ✅ OK |
| Query Limits | BASE_RULES.md | Enforce max/min | ✅ OK |

---

## Dependencies
- **External:** logging, datetime, typing, fastapi, requests
- **Internal:**
  - app.services.live_trading.* (10+ services)

---

## Required Tests
- **test_live_trading_api.py:**
  - Test bridge lifecycle (start/stop/status)
  - Test order placement with validation
  - Test order cancellation
  - Test order listing with filters
  - Test account info retrieval
  - Test position retrieval
  - Test risk validation
  - Test risk limit updates
  - Test execution history with filters
  - Test audit trail retrieval
  - Test compliance report generation
  - Test portfolio snapshot
  - Test alert-to-trade rule creation/deletion
  - Test error handling for each endpoint

---

## Notes
- CRITICAL: This is the main API for live trading operations
- All endpoints use dependency injection for services
- Comprehensive error handling with specific exceptions
- All timestamps in ISO 8601 format
- Query parameters validated (ge/le constraints)
- Risk limits dynamically configurable
- Full audit trail and compliance reporting
