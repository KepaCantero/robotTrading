# i_alert_processor.py

## Purpose
Protocol interface for alert processing in trading system. Defines contract for processing market alerts, validation, duplicate filtering, prioritization, and history retrieval.

---

## Type Definitions / Data Classes

### IAlertProcessor (Protocol)
```python
class IAlertProcessor(Protocol):
    async def process_alert(self, alert: dict) -> Optional["TradeSignal"]:
        """Procesa alerta y genera señal"""

    async def validate_alert(self, alert: dict) -> bool:
        """Valida formato de alerta"""

    async def filter_duplicate_alerts(self, alerts: list) -> list:
        """Filtra alertas duplicadas"""

    async def prioritize_alerts(self, alerts: list) -> list:
        """Prioriza alertas por urgencia"""

    async def get_alert_history(self, symbol: str, days: int) -> list:
        """Obtener historial de alertas"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (Optional["TradeSignal"], bool, list)

---

## Function Signatures (Contracts)

### `async process_alert(alert: dict) -> Optional["TradeSignal"]`
**Pre:** alert must be a valid dictionary with alert data
**Post:** Returns TradeSignal if alert is valid and actionable, None otherwise
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** Yes - May retry on transient failures
**Side Effects:** May trigger order execution if signal is generated

### `async validate_alert(alert: dict) -> bool`
**Pre:** alert must be a dictionary
**Post:** Returns True if alert format is valid, False otherwise
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** No
**Side Effects:** None (pure validation function)

### `async filter_duplicate_alerts(alerts: list) -> list`
**Pre:** alerts must be a list of alert dictionaries
**Post:** Returns list with duplicate alerts removed
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** No
**Side Effects:** None (pure filtering function)

### `async prioritize_alerts(alerts: list) -> list`
**Pre:** alerts must be a list of alert dictionaries
**Post:** Returns list sorted/prioritized by urgency
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** No
**Side Effects:** None (pure sorting/prioritization function)

### `async get_alert_history(symbol: str, days: int) -> list`
**Pre:** symbol must be non-empty string, days must be positive integer
**Post:** Returns list of historical alerts for the symbol within the specified days
**Raises:** NotImplementedError if not implemented by concrete class
**Retry:** Yes - May retry on database/network failures
**Side Effects:** May query database or external storage

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified
- [ ] Methods align with SOLID interface segregation (focused, single purpose)
- [ ] TradeSignal is properly forward-referenced (string with quotes)
- [ ] Implementations must handle None returns appropriately

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 1 P2, 1 P3 |
| **Notes** | Well-defined Protocol interface. Minor improvements suggested below. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P2 - Add type hints for dict parameters (e.g., dict[str, Any]) |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ P3 - Could add docstring exception documentation |

---

## Dependencies
- **External:** typing (Protocol, Optional)

---

## Required Tests
- **tests/core/protocols/test_i_alert_processor.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required ( NotImplementedError raised if not implemented )
  - Test async methods can be called on mock implementation
  - Test Optional return type handling

---

## Notes
**GAPs Found:**

**P2 - Type hints for dict parameters:**
```python
# CURRENT:
async def process_alert(self, alert: dict) -> Optional["TradeSignal"]:

# SUGGESTED:
from typing import Any
async def process_alert(self, alert: dict[str, Any]) -> Optional["TradeSignal"]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Procesa alertas") but file comments use English. Consider standardizing to English for consistency with rest of codebase.

**Trading Context:** This Protocol processes market alerts (e.g., from scanning services, technical indicators) and converts them into TradeSignals for the execution engine. The duplicate filtering and prioritization methods help manage signal quality in high-frequency scenarios.
