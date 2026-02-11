# i_broker_adapter.py

## Purpose
Protocol interface for broker adapter implementations. Defines contract for connecting to trading brokers, placing/canceling orders, and retrieving account data. Enables dependency inversion for different broker implementations (IBKR, Binance, paper trading, etc.).

---

## Type Definitions / Data Classes

### IBrokerAdapter (Protocol)
```python
class IBrokerAdapter(Protocol):
    async def connect(self) -> bool:
        """Conectar al broker"""

    async def disconnect(self) -> bool:
        """Desconectar del broker"""

    async def place_order(self, order: dict) -> str:
        """Colocar orden, retorna order_id"""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""

    async def get_account(self) -> dict:
        """Obtener datos de cuenta"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (bool, str, dict)
- 5 methods maximum (as noted in class docstring)

---

## Function Signatures (Contracts)

### `async connect() -> bool`
**Pre:** Broker credentials and configuration must be available
**Post:** Returns True if connection successful, False otherwise
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** Yes - Should implement retry logic with exponential backoff
**Side Effects:** Establishes network connection to broker API

### `async disconnect() -> bool`
**Pre:** Broker must be currently connected
**Post:** Returns True if disconnection successful, False otherwise
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** Yes - Should ensure clean disconnect even on retry
**Side Effects:** Closes network connection and releases resources

### `async place_order(order: dict) -> str`
**Pre:** order must be a valid dictionary with order parameters (symbol, qty, side, etc.)
**Post:** Returns order_id as string for tracking
**Raises:** NotImplementedError if not implemented, ConnectionError if not connected
**Retry:** Yes - May retry on transient network failures
**Side Effects:** Submits order to broker, may trigger immediate execution

### `async cancel_order(order_id: str) -> bool`
**Pre:** order_id must be a valid order reference from previous place_order call
**Post:** Returns True if cancellation successful, False otherwise
**Raises:** NotImplementedError if not implemented, ValueError if order_id not found
**Retry:** Yes - Should retry if order state is in flux
**Side Effects:** Cancels pending order at broker, releases capital

### `async get_account() -> dict`
**Pre:** Broker must be connected
**Post:** Returns dictionary with account data (balance, positions, margin, etc.)
**Raises:** NotImplementedError if not implemented, ConnectionError if not connected
**Retry:** Yes - May retry on transient network failures
**Side Effects:** None (read-only operation)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified (bool, str, dict)
- [ ] Methods align with SOLID interface segregation (focused broker operations)
- [ ] connect/disconnect are paired methods
- [ ] place_order returns string order_id for tracking
- [ ] cancel_order takes string order_id parameter
- [ ] Implementations handle retry logic for network failures

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 1 P1, 0 P2, 1 P3 |
| **Notes** | Well-defined Protocol interface for broker operations. See gaps below. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused broker methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| ASYNC-005 | BASE_RULES | Timeouts for external calls | ⚠️ P1 - No timeout parameter specified in Protocol |
| TRD-002 | BASE_RULES | Validate orders before execution | ⚠️ P3 - Could add validate_order() method |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P2 - Add type hints for dict parameters |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| SEC-005 | BASE_RULES | Audit logging | ⚠️ P3 - No log_order method defined |

---

## Dependencies
- **External:** typing (Protocol)

---

## Required Tests
- **tests/core/protocols/test_i_broker_adapter.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test connect/disconnect pairing
  - Test place_order returns order_id string
  - Test cancel_order with valid/invalid order_id

---

## Notes
**GAPs Found:**

**P1 - Timeout parameters:** External broker calls should have timeout specifications to prevent hanging. Consider adding:
```python
async def connect(self, timeout: float = 30.0) -> bool:
async def place_order(self, order: dict, timeout: float = 10.0) -> str:
```

**P2 - Type hints for dict parameters:**
```python
# CURRENT:
async def place_order(self, order: dict) -> str:

# SUGGESTED:
from typing import Any
async def place_order(self, order: dict[str, Any]) -> str:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Conectar al broker") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**P3 - Missing methods for complete broker interface:** Consider adding for completeness:
- `validate_order(order: dict) -> bool` - Pre-trade validation
- `get_order_status(order_id: str) -> dict` - Order status checking
- `get_open_orders() -> list[dict]` - List pending orders

**Trading Context:** This Protocol abstracts broker-specific operations for multi-broker support. Implementations exist for Interactive Brokers (IBKR), Binance (crypto), and paper trading for backtesting.
