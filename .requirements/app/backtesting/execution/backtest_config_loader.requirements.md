# backtest_config_loader.py

## Purpose
Loads and validates backtest configurations from YAML files with default value fallbacks and business rule validation.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

This file contains a plain class - no Pydantic models or dataclasses.

### BacktestConfigLoader Class
```python
class BacktestConfigLoader:
    config_path: Path              # REQUIRED - Path to YAML config file
    raw_config: Dict[str, Any]     # REQUIRED - Merged configuration (defaults + loaded)
```

**Validation Rules:**
- `config_path` must be valid Path object
- `raw_config` must contain all required sections or defaults

---

## Function Signatures (Contracts)

### `BacktestConfigLoader.__init__(config_path: str) -> None`
**Pre:** config_path is valid string path
**Post:** Config loaded with defaults merged into loaded YAML
**Raises:** None (falls back to DEFAULT_CONFIG on error)
**Retry:** No
**Side Effects:** Reads YAML file from disk

### `BacktestConfigLoader._load_config() -> Dict[str, Any]`
**Pre:** self.config_path is set
**Post:** Returns merged config (loaded values override defaults)
**Raises:** None (logs error, returns defaults)
**Retry:** No
**Side Effects:** File I/O to read YAML

### `BacktestConfigLoader._merge_with_defaults(config: Dict[str, Any]) -> Dict[str, Any]`
**Pre:** config is loaded YAML dict
**Post:** Returns merged dict with defaults filled in for missing keys
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestConfigLoader.get_backtest_config() -> Dict[str, Any]`
**Pre:** raw_config is loaded
**Post:** Returns flattened backtest config with all required fields
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestConfigLoader.validate() -> List[str]`
**Pre:** raw_config is loaded
**Post:** Returns list of error messages (empty if valid)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BacktestConfigLoader.is_valid() -> bool`
**Pre:** raw_config is loaded
**Post:** Returns True if validate() returns empty list
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Loads YAML from provided path or uses DEFAULT_CONFIG if file missing
- [ ] DEFAULT_CONFIG includes: input (dates, symbols), strategy (name, parameters), capital (initial, currency)
- [ ] DEFAULT_CONFIG includes: risk (max_position_size, stop_loss, take_profit)
- [ ] DEFAULT_CONFIG includes: execution (commission, slippage), reporting (output_directory)
- [ ] DEFAULT_CONFIG includes: parallelization (enabled, max_workers)
- [ ] DEFAULT_CONFIG includes: meta_analysis (enabled, enable_audit, enable_storage, enable_analysis)
- [ ] Merges loaded config with defaults (loaded values override)
- [ ] get_backtest_config() returns flattened dict with all backtest parameters
- [ ] validate() checks required fields: input, strategy, capital
- [ ] validate() checks input has at least one symbol
- [ ] validate() checks strategy has a name
- [ ] validate() checks initial_capital > 0
- [ ] is_valid() returns True if validate() returns empty list
- [ ] Logs warning when config file not found
- [ ] Logs error when config file invalid

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only loads/validates config |
| ERR-001 Exception handling | 05-error-handling.md | Catch specific exceptions | ⚠️ NOT APPLIED - Catches broad Exception (line 99) - acceptable for config loading |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ OK - Logs warnings/errors with context |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ⚠️ NOT APPLIED - Returns plain Dict[str, Any] (by design for YAML config) |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ✅ OK - validate() checks all required fields |
| SEC-001 No hardcoded paths | 11-security.md | Avoid hardcoded config paths | ✅ OK - Path passed as constructor arg |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions, no global state |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** yaml (PyYAML), pathlib, logging, typing
- **Internal:** None (standalone config loader)

---

## Required Tests
- **test_backtest_config_loader.py:**
  - Success: Loads valid YAML config file
  - Success: Falls back to DEFAULT_CONFIG when file missing
  - Success: Falls back to DEFAULT_CONFIG when YAML invalid
  - Success: Merges loaded config with defaults (loaded values override)
  - Success: get_backtest_config() returns all required fields
  - Success: validate() returns empty list for valid config
  - Success: validate() returns errors for missing required fields (input, strategy, capital)
  - Success: validate() returns error when symbols list empty
  - Success: validate() returns error when strategy name missing
  - Success: validate() returns error when initial_capital <= 0
  - Success: is_valid() returns True when validate() returns []
  - Success: is_valid() returns False when validate() returns errors
  - Edge: Empty YAML file uses all defaults
  - Edge: Partial YAML uses defaults for missing sections
  - Edge: Malformed YAML handled gracefully
  - Integration: Default config structure matches all expected backtest parameters

---

## Notes
This is the backtest-specific config loader with comprehensive defaults. DEFAULT_CONFIG provides sensible baseline: 4-year backtest (2020-2023), tech stocks (AAPL, MSFT, GOOGL), 100K initial capital, 10% max position, 3% stop loss, 6% take profit, 0.1% commission, 0.01% slippage. Meta-analysis flags enable audit, storage, and analysis by default but not enabled. Parallelization enabled by default. The merge strategy is: start with DEFAULT_CONFIG, update with loaded values at section level (dict.update), allowing partial configs to override specific sections while keeping defaults for others. Validation ensures basic business rules: at least one symbol, strategy has name, positive capital. File errors are logged but don't crash - falls back to complete defaults.
