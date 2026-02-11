# i_kill_switch_monitor.py

## Purpose
Protocol interface for kill switch monitoring (R2: Drawdown 15% stop trading). Defines contract for monitoring maximum drawdown and activating emergency trading halt when risk threshold is exceeded.

---

## Type Definitions / Data Classes

### IKillSwitchMonitor (Protocol)
```python
class IKillSwitchMonitor(Protocol):
    async def check_kill_switch(self) -> bool:
        """R2: Verificar si drawdown >= 15%"""

    async def get_current_drawdown(self) -> float:
        """Obtener drawdown actual"""

    async def activate_kill_switch(self, reason: str) -> bool:
        """Activar kill switch"""

    async def deactivate_kill_switch(self) -> bool:
        """Desactivar kill switch"""

    async def get_kill_switch_status(self) -> dict:
        """Obtener estado del kill switch"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (bool, float, dict)
- 5 methods maximum (as noted in class docstring)
- R2 compliance: 15% drawdown threshold (see BASE_RULES RSK-003)

---

## Function Signatures (Contracts)

### `async check_kill_switch() -> bool`
**Pre:** Portfolio and drawdown tracking must be initialized
**Post:** Returns True if kill switch should activate (drawdown >= 15%), False otherwise
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** Yes - May retry on transient calculation failures
**Side Effects:** May automatically activate_kill_switch if threshold exceeded

### `async get_current_drawdown() -> float`
**Pre:** Portfolio value history must be available for calculation
**Post:** Returns current drawdown as decimal (e.g., 0.15 for 15%)
**Raises:** NotImplementedError if not implemented, ValueError if insufficient history
**Retry:** No
**Side Effects:** None (read-only calculation)

### `async activate_kill_switch(reason: str) -> bool`
**Pre:** reason must be non-empty string describing activation trigger
**Post:** Returns True if activation successful, False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should ensure activation even on retry
**Side Effects:** Stops all new trading, may close existing positions

### `async deactivate_kill_switch() -> bool`
**Pre:** Kill switch must be currently active
**Post:** Returns True if deactivation successful, False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should ensure deactivation completes
**Side Effects:** Resumes trading operations

### `async get_kill_switch_status() -> dict`
**Pre:** Kill switch state tracking must be initialized
**Post:** Returns dictionary with status information (active, drawdown, last_check, etc.)
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (read-only operation)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified (bool, float, dict)
- [ ] Methods align with R2 requirement (15% drawdown threshold)
- [ ] activate/deactivate are paired methods
- [ ] check_kill_switch implements R2 logic
- [ ] get_kill_switch_status returns complete state information
- [ ] Implementations log all state changes for audit trail

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 1 P2, 0 P3 |
| **Notes** | Well-defined Protocol interface for risk monitoring. R2 compliance documented. See P2 gap below. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| RSK-003 | BASE_RULES | Drawdown control (15% threshold) | ✅ OK - R2: Verificar si drawdown >= 15% |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused risk management methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| TRD-004 | BASE_RULES | Audit trail - log all trade decisions | ⚠️ P2 - activate/deactivate should log events |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P2 - Add type hints for dict return/parameters |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ⚠️ P2 - Add logging requirements to contract |
| SEC-005 | BASE_RULES | Audit logging | ⚠️ P2 - State changes should be logged |

---

## Dependencies
- **External:** typing (Protocol)

---

## Required Tests
- **tests/core/protocols/test_i_kill_switch_monitor.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test check_kill_switch returns True at 15% drawdown
  - Test check_kill_switch returns False below 15% drawdown
  - Test activate/deactivate pairing
  - Test get_kill_switch_status returns dict with required fields

---

## Notes
**GAPs Found:**

**P2 - Type hints for dict parameters:**
```python
# CURRENT:
async def get_kill_switch_status(self) -> dict:

# SUGGESTED:
from typing import Any
async def get_kill_switch_status(self) -> dict[str, Any]:
```

**P2 - Logging and Audit Trail:** The Protocol should specify that implementations MUST log kill switch activation/deactivation for audit trail. Consider adding to docstrings:
```python
async def activate_kill_switch(self, reason: str) -> bool:
    """Activar kill switch. MUST log activation event with timestamp and reason."""
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Obtener historial de alertas") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**Trading Context:** This Protocol implements R2 from SERVICE_REQUIREMENTS.md: "Drawdown 15% stop trading". When drawdown reaches 15% of portfolio value, the kill switch MUST activate to prevent further losses. This is a critical risk management component.
