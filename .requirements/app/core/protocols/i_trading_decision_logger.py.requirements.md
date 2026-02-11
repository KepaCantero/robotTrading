# i_trading_decision_logger.py

## Purpose
Protocol interface for append-only trading decision logging with correlation ID tracking. Defines contract for logging signals (R15), execution results, validation results, querying by correlation ID, and exporting for Hacienda (R28: 5 years).

---

## Type Definitions / Data Classes

### ITradingDecisionLogger (Protocol)
```python
class ITradingDecisionLogger(Protocol):
    def log_signal(self, signal: "TradeSignal", metadata: dict) -> str:
        """Log signal con correlation ID"""

    def log_execution(self, correlation_id: str, result: "TradeResult") -> None:
        """Log execution result"""

    def log_validation_result(self, correlation_id: str, validator: str, passed: bool) -> None:
        """Log validation result"""

    def get_logs_by_correlation_id(self, correlation_id: str) -> list:
        """Obtener logs por correlation ID"""

    def export_for_hacienda(self, year: int) -> list:
        """R28: Exportar logs para Hacienda (5 años)"""
```

**Contract Rules:**
- Methods are NOT async (synchronous logging operations - append-only pattern)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (str correlation_id, None, list)
- 5 methods maximum (as noted in class docstring)
- R15, R28 compliance for decision logging and Hacienda export

---

## Function Signatures (Contracts)

### `log_signal(signal: "TradeSignal", metadata: dict) -> str`
**Pre:** signal must be valid TradeSignal, metadata must be dict with context
**Post:** Returns correlation_id (UUID) for tracking this signal through its lifecycle
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should retry on append failures
**Side Effects:** Appends log entry to storage (file, database)

### `log_execution(correlation_id: str, result: "TradeResult") -> None`
**Pre:** correlation_id must be valid UUID from previous log_signal call
**Post:** Returns None (log entry appended)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should retry on append failures
**Side Effects:** Appends execution result to storage

### `log_validation_result(correlation_id: str, validator: str, passed: bool) -> None`
**Pre:** correlation_id must be valid UUID
**Post:** Returns None (log entry appended)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should retry on append failures
**Side Effects:** Appends validation result to storage

### `get_logs_by_correlation_id(correlation_id: str) -> list`
**Pre:** correlation_id must be valid UUID
**Post:** Returns list of all log entries for this correlation_id (signal, validations, execution)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient storage failures
**Side Effects:** None (read-only query)

### `export_for_hacienda(year: int) -> list`
**Pre:** year must be valid integer (typically current or past year)
**Post:** Returns list of all trading logs for the year (R28: 5 years retention)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on large export operations
**Side Effects:** None (read-only export generation)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as def (not async - logging is synchronous)
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified
- [ ] log_signal generates and returns correlation_id
- [ ] correlation_id links signal → validation → execution logs
- [ ] get_logs_by_correlation_id returns complete lifecycle for a trade
- [ ] export_for_hacienda exports 5 years of data (R28)
- [ ] Implementations use append-only pattern for thread safety

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 2 P3 |
| **Notes** | Well-defined Protocol interface for audit logging. Correlation ID pattern is correct. R28 (5 years) documented. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| R15 | SERVICE_REQUIREMENTS | Audit logging - all decisions logged | ✅ OK - log_signal, log_execution, log_validation_result |
| R28 | SERVICE_REQUIREMENTS | Hacienda export 5 years | ✅ OK - export_for_hacienda method |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Complete logging lifecycle via correlation_id |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses dict metadata, correlation ID |
| LOG-002 | BASE_RULES | Context in logs (correlation ID) | ✅ OK - correlation_id links all entries |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused logging methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P3 - Add type hints for list/dict parameters |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |

---

## Dependencies
- **External:** typing (Protocol)

---

## Required Tests
- **tests/core/protocols/test_i_trading_decision_logger.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test methods can be called on mock implementation
  - Test log_signal returns correlation_id (UUID format)
  - Test correlation_id links signal → validation → execution
  - Test get_logs_by_correlation_id returns complete list
  - Test export_for_hacienda returns all trades for year
  - Test append-only pattern (no mutations, only appends)

---

## Notes

**P3 - Type hints for list/dict parameters:**
```python
# CURRENT:
def log_signal(self, signal: "TradeSignal", metadata: dict) -> str:

# SUGGESTED:
from typing import Any
def log_signal(self, signal: "TradeSignal", metadata: dict[str, Any]) -> str:
def get_logs_by_correlation_id(self, correlation_id: str) -> list[dict[str, Any]]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Logger append-only con correlation ID") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**P3 - Correlation ID format:** Should specify UUID format requirement (UUID v4 string) for type safety.

**Trading Context:** This Protocol implements R15 (audit trail) and R28 (Hacienda export 5 years) requirements. The correlation_id pattern enables tracing a trade decision from signal generation through all validations to final execution - critical for debugging and compliance.

**Append-Only Pattern:** Logging methods use append-only writes (no mutations) for thread safety and performance. This is especially important for concurrent trading operations.
