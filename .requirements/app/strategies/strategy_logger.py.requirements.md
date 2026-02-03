# strategy_logger.py

## Purpose
Strategy Logger - Logger centralizado para estrategias. Proporciona logging estructurado y métricas para todas las estrategias, incluyendo señales generadas, ejecutadas, rechazadas y errores.

---

## Type Definitions / Data Classes

No custom dataclasses defined

---

## Function Signatures (Contracts)

### `StrategyLogger.__init__(log_path: str = "logs/strategy_logs.json")`
**Pre:** log_path is valid file path
**Post:** Logger initialized, loads existing logs
**Raises:** None (logs warning on load failure)
**Retry:** No
**Side Effects:** Creates log directory, loads existing logs

### `StrategyLogger._load_existing_logs() -> None`
**Pre:** log_path is set
**Post:** Logs loaded from file if exists
**Raises:** None (logs warning on load failure)
**Retry:** No
**Side Effects:** Sets self.logs from file

### `StrategyLogger._save_logs() -> None`
**Pre:** log_path directory exists
**Post:** Logs saved to file
**Raises:** None (logs error on save failure)
**Retry:** Yes (can retry save)
**Side Effects:** Writes to log file

### `StrategyLogger._create_log_entry(event: str, strategy_name: str, level: str = "INFO", **kwargs) -> Dict[str, Any]`
**Pre:** event and strategy_name are non-empty
**Post:** Returns log entry dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyLogger.log_signal_generated(strategy_name: str, signal: Signal) -> None`
**Pre:** signal is valid
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_signal_rejected(strategy_name: str, signal: Signal, reason: str) -> None`
**Pre:** signal is valid, reason is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_signal_executed(strategy_name: str, signal: Signal, execution_price: Optional[Decimal] = None) -> None`
**Pre:** signal is valid
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_strategy_error(strategy_name: str, error: str, error_type: Optional[str] = None) -> None`
**Pre:** error is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_execution_error(strategy_name: str, signal: Signal, error: str) -> None`
**Pre:** signal is valid, error is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_strategy_loaded(strategy_name: str, config: Dict[str, Any]) -> None`
**Pre:** config is valid
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_strategy_unloaded(strategy_name: str) -> None`
**Pre:** strategy_name is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_strategy_activated(strategy_name: str) -> None`
**Pre:** strategy_name is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger.log_strategy_deactivated(strategy_name: str) -> None`
**Pre:** strategy_name is non-empty
**Post:** Log entry created and saved
**Raises:** None
**Retry:** No
**Side Effects:** Appends to logs, saves to file

### `StrategyLogger._serialize_signal(signal: Signal) -> Dict[str, Any]`
**Pre:** signal is valid
**Post:** Returns serialized signal dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyLogger.get_strategy_metrics(strategy_name: str) -> Dict[str, Any]`
**Pre:** strategy_name exists in logs
**Post:** Returns metrics dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyLogger.get_all_metrics() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns all metrics dict
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyLogger.clear_logs() -> None`
**Pre:** None
**Post:** Logs cleared and saved
**Raises:** None
**Retry:** No
**Side Effects:** Clears logs list, saves empty file

### `StrategyLogger.export_logs(export_path: str) -> None`
**Pre:** export_path is valid
**Post:** Logs exported to file
**Raises:** OSError on export failure
**Retry:** Yes (can retry export)
**Side Effects:** Writes to export file

---

## Acceptance Criteria
- [ ] Initialization creates log directory
- [ ] Initialization loads existing logs from file
- [ ] log_signal_generated creates entry with signal data
- [ ] log_signal_rejected creates entry with reason
- [ ] log_signal_executed creates entry with execution price
- [ ] log_strategy_error creates entry with error type
- [ ] log_execution_error creates entry with signal and error
- [ ] All log methods save to file
- [ ] get_strategy_metrics calculates execution_rate correctly
- [ ] get_strategy_metrics calculates rejection_rate correctly
- [ ] get_strategy_metrics calculates error_rate correctly
- [ ] get_all_metrics returns metrics for all strategies
- [ ] clear_logs empties logs and saves
- [ ] export_logs writes to specified path

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-python-expert (via Tech Lead Orchestrator) |
| **GAPs Fixed** | 0 / ? total |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - Uses Any in metadata/kwargs |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses structured JSON logging |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - Added exc_info=True (no error logging) |
| LOG-005 | BASE_RULES | No sensitive data in logs | ✅ OK - Signal serialization safe |
| CC-006 | BASE_RULES | Explicit error handling | ❌ GAP - Broad exception catching (lines 47, 59) |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ✅ OK - Most functions <20 lines |

---

## Dependencies
- **External:** json, logging, datetime, decimal, pathlib, typing
- **Internal:** app.models.signal.Signal

---

## Required Tests
- **tests/strategies/test_strategy_logger.py:**
  - Test initialization creates log directory
  - Test initialization loads existing logs
  - Test log_signal_generated creates entry
  - Test log_signal_generated saves to file
  - Test log_signal_rejected creates entry with reason
  - Test log_signal_executed creates entry with price
  - Test log_strategy_error creates entry
  - Test log_execution_error creates entry
  - Test log_strategy_loaded creates entry
  - Test log_strategy_unloaded creates entry
  - Test log_strategy_activated creates entry
  - Test log_strategy_deactivated creates entry
  - Test _serialize_signal returns correct dict
  - Test get_strategy_metrics calculates rates correctly
  - Test get_strategy_metrics with no logs
  - Test get_all_metrics returns all strategies
  - Test clear_logs empties logs
  - Test export_logs writes to file
  - Test export_logs raises on failure

---

## Notes
- Spanish language comments and docstrings
- Uses JSON format for structured logging
- Persists logs to disk on every operation
- Loads existing logs on initialization
- Calculates metrics (execution_rate, rejection_rate, error_rate)
- Tracks first and last log timestamps
