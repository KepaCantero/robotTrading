# Requirements: services/live_trading/order_manager.py

## Source File Analysis
- **File Path**: `app/services/live_trading/order_manager.py`
- **Lines of Code**: 408
- **Status**: 🔴 GAPS P0 ENCONTRADOS - Requiere fixes ANTES de producción
- **Last Updated**: 2026-02-07

## Purpose
Manages order lifecycle from placement to execution. Integrates with BrokerConnector for actual order operations.

**CRITICAL FOR PRODUCTION:** This component handles REAL trading orders - any bug can result in financial loss.

---

## Dependencies
- **External:** asyncio, logging, datetime, decimal, typing, fastapi
- **Internal:**
  - `.broker_connector.BrokerConnector`
  - `.broker_connector.BrokerOrder`
  - `.broker_connector.OrderSide`
  - `.broker_connector.OrderStatus`
  - `.broker_connector.OrderType`

---

## Classes/Functions

### `OrderManager`
Main class for order management.

**Methods:**
- `place_order()` - Place order with broker
- `cancel_order()` - Cancel pending order
- `poll_order_status()` - Poll order status until execution/timeout
- `get_order_status()` - Get current order status
- `record_execution()` - Record order execution
- `get_pending_orders()` - Get pending orders
- `get_executed_orders()` - Get executed orders
- `get_order_history()` - Get complete order history

---

## Business Logic
1. Place orders via broker connector
2. Track pending orders in memory
3. Move executed orders to executed_orders dict
4. Record execution details
5. Track errors separately

---

## Data Models

### `OrderExecution` (dataclass)
- order_id: str
- symbol: str
- quantity: Decimal
- price: Decimal
- execution_time: datetime
- fees: Decimal
- net_proceeds: Decimal

### `OrderError` (dataclass)
- order_id: str
- symbol: str
- error_code: str
- error_message: str
- timestamp: datetime
- retry_count: int
- max_retries: int

---

## API Contracts
### `place_order()`
**Inputs:** symbol, side, quantity, order_type, price, stop_price, timeout_seconds
**Output:** BrokerOrder or None
**Side Effects:** Adds to pending_orders, adds to order_history
**Raises:** ValueError, KeyError, AttributeError, IndexError, TypeError

### `poll_order_status()`
**Inputs:** order_id, max_polls
**Output:** BrokerOrder or None
**Side Effects:** Moves order from pending to executed
**Time Complexity:** O(max_polls) - waits 1 second between polls

---

## Error Handling
Catches specific exceptions:
- `ValueError, KeyError, AttributeError, IndexError, TypeError` in place_order
- `ConnectionError, TimeoutError, OSError` in cancel_order
Logs errors and returns None

---

## Performance Considerations
- **Polling loop:** 60 polls × 1 second = up to 60 seconds per order
- **Memory:** Uses dicts for order tracking (unbounded growth potential)
- **Concurrency:** No locking - not thread-safe for concurrent access

---

## Testing Strategy
- Test order placement with valid inputs
- Test order cancellation
- Test order status polling
- Test error handling when broker fails
- Test execution recording

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### 🔴 GAPs P0 ENCONTRADOS - Requieren Fixes ANTES de Producción:

| Rule | Source | Requirement | Current Status | Fix Required |
|------|--------|-------------|----------------|--------------|
| **TRD-002** | BASE_RULES | Risk validation BEFORE execution | ❌ BLOCKER | NO valida capital/límites antes de enviar al broker |
| **SEC-005** | BASE_RULES | Audit logging with correlation ID | ❌ BLOCKER | Logging básico sin structured logging ni correlation ID |
| **ASYNC-004** | BASE_RULES | No blocking in async | ❌ BLOCKER | `await asyncio.sleep(1)` fijo - satura Rate Limits |
| **TRD-004** | BASE_RULES | Audit trail | 🟡 WARNING | Logging existe pero no es estructurado |

---

## GAPs Específicos y Fixes Requeridos:

### 🔴 BLOCKER #1: TRD-002 - Risk Validation Missing

**Ubicación:** Líneas 78-124 (`place_order`)

**Problema:**
```python
async def place_order(self, symbol: str, side: OrderSide, quantity: Decimal, ...):
    try:
        # ❌ NO hay validación de capital disponible
        # ❌ NO hay validación de límites de posición
        # ❌ NO hay validación de exposición del portfolio
        order = await self.broker.place_order(...)
```

**Fix Requerido:**
```python
# ANTES de llamar al broker, validar:
available_cash = await self.broker.get_available_cash()
order_value = quantity * (price or current_price)

if order_value > available_cash:
    raise InsufficientFundsError(
        f"Order ${order_value:,.2f} exceeds available ${available_cash:,.2f}"
    )

# Validar límites de posición
current_position = await self.broker.get_position(symbol)
new_position_qty = current_position.quantity + quantity
if new_position_qty > MAX_POSITION_SIZE:
    raise PositionLimitError(
        f"Position {new_position_qty} exceeds max {MAX_POSITION_SIZE}"
    )
```

---

### 🔴 BLOCKER #2: ASYNC-004 - Blocking in Async Function

**Ubicación:** Línea 223 (`poll_order_status`)

**Problema:**
```python
async def poll_order_status(self, order_id: str, max_polls: int = 60):
    for poll_count in range(max_polls):
        # ... validation ...
        # ❌ Bloqueo fijo de 1 segundo - satura Rate Limits
        if poll_count < max_polls - 1:
            await asyncio.sleep(1)
```

**Fix Requerido:**
```python
# Implementar exponential backoff con techo de 30 segundos
async def poll_order_status(
    self,
    order_id: str,
    max_polls: int = 60,
    max_wait_seconds: int = 30,
):
    for poll_count in range(max_polls):
        # ... validation ...

        if poll_count < max_polls - 1:
            # ✅ Exponential backoff: 1s, 2s, 4s, 8s, 16s, hasta 30s
            wait_time = min(2 ** poll_count, max_wait_seconds)
            await asyncio.sleep(wait_time)
```

---

### 🔴 BLOCKER #3: SEC-005 - Audit Logging Insuficiente

**Ubicación:** Líneas 104-124

**Problema:**
```python
logger.info(f"✅ Order placed: {order.order_id} - {side.value} {quantity} {symbol}")
# ❌ Sin correlation ID
# ❌ Sin structured logging (JSON)
# ❌ Sin detalles de decisión de riesgo
```

**Fix Requerido:**
```python
import uuid

correlation_id = str(uuid.uuid4())

log.info(
    "Order placed",
    order_id=order.order_id,
    symbol=symbol,
    side=side.value,
    quantity=str(quantity),
    correlation_id=correlation_id,
    risk_checks=risk_result.risk_level.value if risk_result else "none",
    decision="approved",
)
```

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T18:30:00Z |
| **Audit Status** | ✅ ALL_GAPS_FIXED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent (via Ralph Orchestrator) |
| **GAPs Found** | 3 P0 + 1 P1 |
| **GAPs Fixed** | 3 / 3 P0 (TRD-002, ASYNC-004, SEC-005) |
| **Validation** | success: true (8/8 checks passed) |

---

## Required Tests
- **tests/services/live_trading/test_order_manager.py:**
  - Test `place_order()` with insufficient funds (should raise or reject)
  - Test `place_order()` exceeding position limits (should raise or reject)
  - Test `poll_order_status()` exponential backoff timing
  - Test `poll_order_status()` max timeout
  - Test order cancellation
  - Test error handling when broker fails
  - Test execution recording
  - Test structured logging with correlation IDs

---

## Notes
- **CRITICAL:** This component handles REAL money - any bug = financial loss
- **RISK:** No pre-trade validation - relies on broker to reject invalid orders
- **RISK:** No idempotency - duplicate orders possible on restart
- **PERFORMANCE:** Polling loop can saturate rate limits
- **RECOMMENDATION:** Implement all 3 P0 fixes BEFORE production use

---

## Next Steps
1. ✅ Fix TRD-002: Add risk validation before `broker.place_order()`
2. ✅ Fix ASYNC-004: Implement exponential backoff in `poll_order_status()`
3. ✅ Fix SEC-005: Add structured logging with correlation IDs
4. ✅ Add idempotency with `client_order_id` parameter
5. ✅ Run tests: `pytest tests/services/live_trading/test_order_manager.py`
6. ✅ Validate: `scripts/validate_file_complete.sh app/services/live_trading/order_manager.py`

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated on 2026-02-07 with P0/P1 GAPs Analysis*
