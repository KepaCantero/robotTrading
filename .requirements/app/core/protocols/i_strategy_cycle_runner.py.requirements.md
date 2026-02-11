# i_strategy_cycle_runner.py

## Purpose
Protocol interface for strategy cycle execution. Defines contract for running complete trading cycles, validating inputs, executing phases, handling errors, and tracking metrics.

---

## Type Definitions / Data Classes

### IStrategyCycleRunner (Protocol)
```python
class IStrategyCycleRunner(Protocol):
    async def run_cycle(self, signals: list["TradeSignal"]) -> "CycleResult":
        """Ejecutar ciclo completo"""

    async def validate_cycle_input(self, signals: list) -> bool:
        """Valida entrada del ciclo"""

    async def execute_cycle_phase(self, phase: str, signals: list) -> dict:
        """Ejecuta fase del ciclo"""

    async def handle_cycle_error(self, error: Exception) -> None:
        """Maneja errores del ciclo"""

    async def get_cycle_metrics(self) -> dict:
        """Obtener métricas del ciclo"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (CycleResult, bool, dict, None)
- 5 methods maximum (as noted in class docstring)

---

## Function Signatures (Contracts)

### `async run_cycle(signals: list["TradeSignal"]) -> "CycleResult"`
**Pre:** signals must be a list of valid TradeSignal objects
**Post:** Returns CycleResult with execution summary, positions opened/closed, PnL
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - Should implement retry logic for transient failures
**Side Effects:** May open/close positions, update state

### `async validate_cycle_input(signals: list) -> bool`
**Pre:** signals must be a list (may be empty)
**Post:** Returns True if all signals are valid, False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure validation function)

### `async execute_cycle_phase(phase: str, signals: list) -> dict`
**Pre:** phase must be valid phase name (e.g., "scan", "validate", "execute")
**Post:** Returns dictionary with phase execution results
**Raises:** NotImplementedError if not implemented, ValueError for invalid phase
**Retry:** Yes - Should implement retry logic for transient failures
**Side Effects:** Executes specific phase logic (scanning, validation, trading)

### `async handle_cycle_error(error: Exception) -> None`
**Pre:** error must be an Exception instance
**Post:** Returns None (error is logged/handled internally)
**Raises:** NotImplementedError if not implemented
**Retry:** No (this is the error handler itself)
**Side Effects:** May log error, send alerts, update circuit breakers

### `async get_cycle_metrics() -> dict`
**Pre:** Cycle execution tracking must be initialized
**Post:** Returns dictionary with metrics (signals processed, trades executed, PnL, duration)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient database failures
**Side Effects:** None (read-only aggregation)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified
- [ ] run_cycle validates input via validate_cycle_input before execution
- [ ] execute_cycle_phase handles multiple phases (scan, validate, execute)
- [ ] handle_cycle_error properly logs exceptions
- [ ] get_cycle_metrics returns complete metrics

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 2 P3 |
| **Notes** | Well-defined Protocol interface for strategy cycle orchestration. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| ASYNC-006 | BASE_RULES | Handle asyncio.TimeoutError | ⚠️ P3 - Add timeout handling requirement |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ⚠️ P3 - Specify logging in handle_cycle_error |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P3 - Add type hints for list/dict parameters |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |

---

## Dependencies
- **External:** typing (Protocol)

---

## Required Tests
- **tests/core/protocols/test_i_strategy_cycle_runner.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test run_cycle returns CycleResult structure
  - Test validate_cycle_input with valid/invalid signals
  - Test execute_cycle_phase with different phases
  - Test handle_cycle_error logs exceptions
  - Test get_cycle_metrics returns complete metrics

---

## Notes

**P3 - Type hints for list/dict parameters:**
```python
# CURRENT:
async def run_cycle(self, signals: list["TradeSignal"]) -> "CycleResult":

# SUGGESTED:
from typing import Any
async def run_cycle(self, signals: list["TradeSignal"]) -> "CycleResult":
async def execute_cycle_phase(self, phase: str, signals: list) -> dict[str, Any]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Ejecuta ciclos de estrategia") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**P3 - Phase types:** The execute_cycle_phase method should document expected phase names (scan, validate, execute, etc.) for type safety.

**Trading Context:** This Protocol orchestrates the complete trading cycle: signal generation → validation → execution → post-trade analysis. Breaking cycles into phases enables better error handling, retry logic, and observability.
