# logging_config.py

## Purpose
Centralized logging configuration with file rotation, separation by log level, and module-specific loggers for production trading systems.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### Configuration Parameters
```python
def setup_file_logging(
    log_dir: str = "logs",              # REQUIRED - Directory for log files
    root_level: int = logging.INFO,     # REQUIRED - Minimum level for root logger
    file_level: int = logging.WARNING,  # REQUIRED - Minimum level for file handlers
    console_level: Optional[int] = logging.INFO,  # None disables console in production
) -> None
```

---

## Function Signatures (Contracts)

### `setup_file_logging(log_dir: str, root_level: int, file_level: int, console_level: Optional[int]) -> None`
**Pre:** log_dir must be creatable, levels must be valid logging constants
**Post:** Creates 3 rotating file handlers (all.log, warnings.log, errors.log) + optional console handler
**Raises:** OSError if log_dir cannot be created
**Retry:** ❌ No
**Side Effects:** Creates log files, modifies root logger handlers, clears existing handlers

### `setup_module_loggers() -> None`
**Pre:** None
**Post:** Creates module-specific error loggers for strategies, backtesting, services, api, core
**Raises:** OSError if logs/ directory cannot be created
**Retry:** ❌ No
**Side Effects:** Creates rotating file handlers for each module

---

## Acceptance Criteria
- [ ] Log directory is created with parents=True if it doesn't exist
- [ ] Warnings and errors are written to SEPARATE files (warnings.log, errors.log)
- [ ] All logs (INFO+) are written to all.log
- [ ] RotatingFileHandler uses 10MB max size with 10-20 backups
- [ ] Console logging is DISABLED in production (ENVIRONMENT=production)
- [ ] Error logs include full path: %(pathname)s
- [ ] Warning logs include function name and line number
- [ ] Module-specific loggers are created for all 5 important modules
- [ ] Existing handlers are cleared before adding new ones (prevents duplicates)
- [ ] UTF-8 encoding is used for all log files
- [ ] Known warnings are suppressed (pydantic, pandas deprecations)
- [ ] Warnings are shown only once per unique message

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-001 | BASE_RULES.md | Structured logging (JSON format) | ❌ GAP - Using text format, not JSON |
| LOG-002 | BASE_RULES.md | Include correlation IDs | ❌ GAP - No correlation ID support |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Formatters include function/line info |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ⚠️ NOT ENFORCED - No sanitization |
| LOG-006 | BASE_RULES.md | Add timing info for operations | ❌ GAP - No timing field in formatters |
| LOG-007 | BASE_RULES.md | Implement health check endpoints | ⚠️ NOT APPLIED - This is config module |

### Logging-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| LOG-ROTATE-001 | RotatingFileHandler must prevent unlimited disk usage | ✅ OK - 10MB max, 10-20 backups |
| LOG-PROD-001 | Production must disable console logging | ✅ OK - Checks ENVIRONMENT var |
| LOG-ENC-001 | UTF-8 encoding for international characters | ✅ OK |
| LOG-INIT-001 | Logging configured on module import | ✅ OK - Auto-initializes at import |
| LOG-CLR-001 | Clear existing handlers before setup | ✅ OK - handlers.clear() called |
| LOG-SEP-001 | Separate files by severity (INFO, WARNING, ERROR) | ✅ OK |

---

## Dependencies
- **External:** None (standard library only)
- **Internal:** None (pure infrastructure module)
- **Standard Library:** `logging`, `logging.handlers.RotatingFileHandler`, `os`, `sys`, `warnings`, `pathlib.Path`

---

## Required Tests
- **tests/core/test_logging_config.py:**
  - Test log directory creation if it doesn't exist
  - Test all.log receives INFO+ messages
  - Test warnings.log receives only WARNING+ messages
  - Test errors.log receives only ERROR+ messages
  - Test RotatingFileHandler rotates at 10MB
  - Test console logging disabled when ENVIRONMENT=production
  - Test console logging enabled when ENVIRONMENT!=production
  - Test existing handlers are cleared on setup
  - Test module-specific loggers are created for all 5 modules
  - Test UTF-8 encoding handles international characters
  - Test warning formatters include funcName and lineno
  - Test error formatters include pathname
  - Test known warnings are suppressed (pydantic, pandas)
  - Test warnings.simplefilter("once") shows unique warnings once
  - Edge case: Log directory with no write permissions
  - Edge case: Log file already exists (appends, doesn't overwrite)

---

## Notes
- **Initialization:** Logging is configured automatically on module import - may cause side effects if imported in tests.
- **Structured Logging:** Currently using text format. Consider migrating to structlog for JSON logging (LOG-001 GAP).
- **Correlation IDs:** No support for request tracing. Add filter to inject correlation IDs for async operations.
- **Disk Space:** With 3 files x 10MB x 20 backups = 600MB max per log type. Monitor disk usage in production.
- **Warning Suppression:** Specific warnings are hardcoded. May need to expand list as dependencies evolve.
