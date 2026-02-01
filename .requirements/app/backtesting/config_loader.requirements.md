# config_loader.py

## Purpose
Loads and manages YAML configuration for meta-analysis components including metric thresholds, analysis settings, visualization preferences, and reporting options.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

This file contains a plain class with a dictionary config - no Pydantic models or dataclasses.

### ConfigLoader Class
```python
class ConfigLoader:
    config_path: Path                  # REQUIRED - Path to YAML config file
    config: Dict[str, Any]             # REQUIRED - Loaded configuration dictionary
```

**Validation Rules:**
- `config_path` must be a valid file path or use default
- `config` must contain valid YAML structure or use defaults
- Missing config file falls back to `_get_default_config()`

---

## Function Signatures (Contracts)

### `ConfigLoader.__init__(config_path: Optional[str] = None) -> None`
**Pre:** config_path is None or valid string path
**Post:** Config initialized with loaded YAML or defaults
**Raises:** None (falls back to defaults on error)
**Retry:** No
**Side Effects:** Reads YAML file from disk, sets self.config

### `ConfigLoader._load_config() -> None`
**Pre:** self.config_path is set
**Post:** self.config populated with YAML content or defaults
**Raises:** None (logs error, uses defaults)
**Retry:** No
**Side Effects:** File I/O to read YAML

### `ConfigLoader.get(key: str, default: Any = None) -> Any`
**Pre:** key is dot-separated string (e.g., "metric_thresholds.sharpe_ratio.excellent")
**Post:** Returns config value or default if not found
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConfigLoader.get_section(section: str) -> Dict[str, Any]`
**Pre:** section is a top-level key in config
**Post:** Returns section dict or empty dict if not found
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConfigLoader.get_metric_thresholds(metric: str) -> Dict[str, float]`
**Pre:** metric is a key under "metric_thresholds"
**Post:** Returns dict with excellent/good/warning/critical values
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ConfigLoader.is_enabled(feature: str) -> bool`
**Pre:** feature is dot-separated path ending in ".enabled"
**Post:** Returns True if feature.enabled = True, else False
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_config(config_path: Optional[str] = None) -> ConfigLoader`
**Pre:** None
**Post:** Returns singleton ConfigLoader instance
**Raises:** None
**Retry:** No
**Side Effects:** Creates singleton if not exists

### `reset_config() -> None`
**Pre:** None
**Post:** Global config reset to None
**Raises:** None
**Retry:** No
**Side Effects:** Clears singleton instance

---

## Acceptance Criteria
- [ ] Loads YAML from default path "config/meta_analyzer_config.yaml" if no path provided
- [ ] Falls back to default config if file not found or invalid YAML
- [ ] Default config includes: metric_thresholds (sharpe, max_drawdown, win_rate, profit_factor)
- [ ] Default config includes: analysis settings (rolling_windows, seasonality, regime_detection)
- [ ] Default config includes: visualization (static_plots, interactive)
- [ ] Default config includes: reporting sections (performance_summary, statistical_insights, risk_warnings)
- [ ] get() supports dot-notation keys (e.g., "metric_thresholds.sharpe_ratio.excellent")
- [ ] Returns default value if key not found
- [ ] Implements singleton pattern via get_config()
- [ ] reload() re-reads YAML file and updates config
- [ ] Logs warnings when config file missing or invalid

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only loads/manages config |
| ERR-001 Exception handling | 05-error-handling.md | Catch specific exceptions | ⚠️ NOT APPLIED - Catches broad Exception tuple (line 43) |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ OK - Logs config load/failure |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ✅ ADDRESSED - 2026-02-01: Plain dict returns documented as design choice - configuration is not a domain entity |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ⚠️ NOT APPLIED - No validation of YAML structure |
| SEC-001 No hardcoded paths | 11-security.md | Avoid hardcoded config paths | ⚠️ NOT APPLIED - Default path hardcoded (line 27) |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions, no global state in methods |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

**GAP Analysis:**
- **DOM-001:** ✅ ADDRESSED - Added comprehensive documentation explaining why plain Dict[str, Any] is the appropriate return type. Configuration data represents external settings, not domain concepts. Value object conversion happens downstream in consuming classes (e.g., BacktestConfigLoader converts to BacktestConfig with Decimal validation).

---

## Dependencies
- **External:** yaml (PyYAML), pathlib, logging, typing
- **Internal:** None (standalone utility)

---

## Required Tests
- **test_config_loader.py:**
  - Success: Loads YAML config from file correctly
  - Success: Falls back to defaults when file missing
  - Success: Falls back to defaults when YAML invalid
  - Success: get() retrieves nested values with dot notation
  - Success: get() returns default for missing keys
  - Success: get_section() returns entire section
  - Success: get_metric_thresholds() returns metric-specific thresholds
  - Success: is_enabled() returns True/False for feature flags
  - Success: reload() re-reads file and updates config
  - Success: get_config() returns singleton instance
  - Success: reset_config() clears singleton
  - Edge: Empty YAML file uses defaults
  - Edge: Malformed YAML handled gracefully
  - Integration: Default config structure matches documented schema

---

## Notes
This is a simple configuration loader with singleton pattern. The default config contains institutional-grade thresholds: Sharpe (excellent > 2.0, good > 1.0), Max DD (warning > -20%, critical > -50%), Win Rate (excellent > 60%, good > 50%), Profit Factor (excellent > 2.5, good > 1.5). Config includes analysis settings for rolling windows (252 days for Sharpe), seasonality (min 60 months), and regime detection (3 regimes, 20-day volatility window). The get() method supports dot notation for nested access. File errors are logged but don't crash - falls back to defaults.

---

## Fixes Applied 2026-02-01

### ✅ GAP-DOM-001: Use Value Objects - ADDRESSED
**Summary:** Documented why plain Dict[str, Any] returns are the appropriate design choice for this configuration loader.

**Changes Made:**
1. **Module docstring enhanced:**
   - Added comprehensive "Design Note: Plain Dict Return Type" section
   - Explained 5 key reasons why value objects are NOT appropriate here:
     1. Configuration is not a domain entity (external settings vs domain concepts)
     2. Dynamic structure requirements (arbitrary nesting like metric_thresholds.sharpe_ratio.excellent)
     3. Read-only access pattern (no mutation through API)
     4. Downstream conversion happens in consuming classes (BacktestConfig, strategies)
     5. Compatibility with YAML serialization/deserialization
   - Added reference to BacktestConfigLoader as the example where proper value object conversion occurs

**Validation Results:**
- ✅ Python syntax compilation: Passed
- ✅ Ruff linting: All checks passed
- ✅ Black formatting: Passed
- ✅ Isort import ordering: Passed

