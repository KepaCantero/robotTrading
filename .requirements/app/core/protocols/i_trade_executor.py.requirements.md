# i_trade_executor.py

## Purpose
Protocol interface for trade execution via broker. Defines contract for executing orders with pre-trade validations, canceling/modifying existing orders, checking order status, and retrieving open orders.

---

## Type Definitions / Data Classes

### ITradeExecutor (Protocol)
```python
class ITradeExecutor(Protocol):
    async def execute_order(self, signal: "TradeSignal") -> "TradeResult":
        """Ejecutar orden con validaciones"""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden existente"""

    async def modify_order(self, order_id: str, new_price: Decimal) -> bool:
        """Modificar orden existente"""

    async def get_order_status(self, order_id: str) -> str:
        """Obtener estado de orden"""

    async def get_open_orders(self) -> list["TradeSignal"]:
        """Obtener órdenes abiertas"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (TradeResult, bool, str, list)
- 5 methods maximum (as noted in class docstring)

---

## Function Signatures (Contracts)

### `async execute_order(signal: "TradeSignal") -> "TradeResult"`
**Pre:** signal must be a valid TradeSignal with symbol, quantity, side, etc.
**Post:** Returns TradeResult with execution status, order_id, filled price, etc.
**Raises:** NotImplementedError if not implemented, ValidationError for invalid signal
**Retry:** Yes - Should implement retry logic for transient failures
**Side Effects:** Places order via broker adapter after pre-trade validations

### `async cancel_order(order_id: str) -> bool`
**Pre:** order_id must be a valid order reference
**Post:** Returns True if cancellation successful, False otherwise
**Raises:** NotImplementedError if not implemented, ValueError if order_id invalid
**Retry:** Yes - Should retry if order state is in flux
**Side Effects:** Cancels pending order at broker

### `async modify_order(order_id: str, new_price: Decimal) -> bool`
**Pre:** order_id must be valid, new_price must be positive Decimal
**Post:** Returns True if modification successful, False otherwise
**Raises:** NotImplementedError if not implemented, ValueError for invalid order_id
**Retry:** Yes - Should retry if order state is in flux
**Side Effects:** Modifies existing order at broker

### `async get_order_status(order_id: str) -> str`
**Pre:** order_id must be a valid order reference
**Post:** Returns order status as string (pending, filled, canceled, rejected, etc.)
**Raises:** NotImplementedError if not implemented, ValueError for invalid order_id
**Retry:** Yes - May retry on transient API failures
**Side Effects:** None (read-only query)

### `async get_open_orders() -> list["TradeSignal"]`
**Pre:** Order tracking must be initialized
**Post:** Returns list of currently open orders as TradeSignal objects
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient API failures
**Side Effects:** None (read-only query)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified
- [ ] execute_order runs pre-trade validations (R1-R4, R9) before broker call
- [ ] cancel_order works with valid and invalid order_ids
- [ ] modify_order only modifies existing orders
- [ ] get_order_status returns standard status strings
- [ ] get_open_orders returns list of TradeSignal objects

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 1 P3 |
| **Notes** | Well-defined Protocol interface for trade execution. Good separation of concerns. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - execute_order mentions validations |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| ASYNC-005 | BASE_RULES | Timeouts for external calls | ⚠️ P3 - Consider adding timeout parameter |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P3 - Add type hints for list parameters |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ⚠️ P3 - Specify error logging requirements |

---

## Dependencies
- **External:** typing (Protocol)
- **Internal:** decimal (Decimal)

---

## Required Tests
- **tests/core/protocols/test_i_trade_executor.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test execute_order returns TradeResult structure
  - Test cancel_order with valid/invalid order_id
  - Test modify_order updates existing order
  - Test get_order_status returns valid status strings
  - Test get_open_orders returns list structure

---

## Notes

**P3 - Type hints for list parameters:**
```python
# CURRENT:
async def execute_cycle_phase(self, phase: str, signals: list) -> dict:

# SUGGESTED:
async def execute_cycle_phase(self, phase: str, signals: list["TradeSignal"]) -> dict[str, Any]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Ejecuta trades vía broker") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**P3 - Order status types:** The get_order_status method should document expected status string values (pending, filled, partially_filled, canceled, rejected, etc.) for type safety.

**Trading Context:** This Protocol sits between signal generation and broker execution. It runs pre-trade validations (R1-R4, R9) before placing orders, ensuring all trades comply with risk management rules.
