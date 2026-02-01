# config_loader.py

## Purpose
Loads and manages YAML configuration for meta-analyzer components. Provides dot-notation access to nested configuration values with fallback to defaults when file not available. Intentionally returns Dict[str, Any] instead of value objects (see design note in docstring).

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses Dict[str, Any] return type by design (not value objects).

### ConfigLoader Class
```python
class ConfigLoader:
    config_path: Path                    # REQUIRED - Path to YAML config file
    config: Dict[str, Any]               # REQUIRED - Loaded configuration dictionary
```

**Validation Rules:**
- YAML file must be valid YAML syntax
- Missing config file falls back to defaults (no exception)
- Dot-separated keys traverse nested dictionaries

### Default Configuration Structure
```python
{
    "metric_thresholds": {
        "sharpe_ratio": {"excellent": 2.0, "good": 1.0, "warning": 0.5, "critical": -0.5},
        "max_drawdown": {"warning": -0.20, "critical": -0.50},
        "win_rate": {"excellent": 0.60, "good": 0.50, "warning": 0.40, "critical": 0.25},
        "profit_factor": {"excellent": 2.5, "good": 1.5, "warning": 1.0, "critical": 0.5}
    },
    "analysis": {
        "rolling_windows": {"sharpe_calculation_days": 252, "volatility_window_days": 20},
        "seasonality": {"min_history_months": 60, "min_history_days": 1260},
        "regime_detection": {"enabled": True, "n_regimes": 3, "volatility_window": 20}
    },
    "visualization": {"static_plots": {"enabled": True, "dpi": 300}, "interactive": {"enabled": True}},
    "reporting": {"include_sections": {...}},
    "advanced": {"random_state": 42, "logging": {"level": "INFO"}}
}
```

---

## Function Signatures (Contracts)

### `ConfigLoader.__init__(config_path: Optional[str] = None) -> None`
**Pre:** config_path is None or valid file path string
**Post:** ConfigLoader initialized with loaded config or defaults
**Raises:** ❌ No (falls back to defaults on error)
**Side Effects:** Reads YAML file from disk, logs success/error

### `ConfigLoader._load_config() -> None`
**Pre:** self.config_path is set
**Post:** self.config populated with YAML content or defaults
**Raises:** ❌ No (catches all exceptions, uses defaults)
**Side Effects:** File I/O, logging

### `ConfigLoader._get_default_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns default configuration dictionary
**Raises:** ❌ No
**Side Effects:** None (static method)

### `ConfigLoader.get(key: str, default: Any = None) -> Any`
**Pre:** key is dot-separated string (e.g., "metric_thresholds.sharpe_ratio.excellent")
**Post:** Returns configuration value or default if not found
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_section(section: str) -> Dict[str, Any]`
**Pre:** section is top-level key name
**Post:** Returns section dictionary or {} if not found
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_metric_thresholds(metric: str) -> Dict[str, float]`
**Pre:** metric is valid metric name
**Post:** Returns threshold dictionary for metric
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_analysis_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns analysis section dictionary
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_visualization_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns visualization section dictionary
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_reporting_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns reporting section dictionary
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_alerts_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns alerts section dictionary
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_regime_detection_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns regime_detection config or {}
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_seasonality_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns seasonality config or {}
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_clustering_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns clustering config or {}
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_walk_forward_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns walk_forward config or {}
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_alert_threshold(metric: str, level: str = "warning") -> Optional[float]`
**Pre:** metric exists in thresholds, level in ["excellent", "good", "warning", "critical"]
**Post:** Returns threshold value or None
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.is_enabled(feature: str) -> bool`
**Pre:** feature is dot-separated path ending in ".enabled"
**Post:** Returns True if enabled, False otherwise
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_random_state() -> int`
**Pre:** None
**Post:** Returns random_state (default 42)
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.get_logging_level() -> str`
**Pre:** None
**Post:** Returns logging level (default "INFO")
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns copy of config dictionary
**Raises:** ❌ No
**Side Effects:** None

### `ConfigLoader.reload() -> None`
**Pre:** None
**Post:** Config reloaded from file
**Raises:** ❌ No (falls back to defaults on error)
**Side Effects:** File I/O, logging

### `get_config(config_path: Optional[str] = None) -> ConfigLoader`
**Pre:** config_path is None or valid file path
**Post:** Returns singleton ConfigLoader instance
**Raises:** ❌ No
**Side Effects:** Creates singleton on first call

### `reset_config() -> None`
**Pre:** None
**Post:** Global config instance reset to None
**Raises:** ❌ No
**Side Effects:** Modifies module-level global

---

## Acceptance Criteria
- [ ] Missing config file falls back to defaults (no exception)
- [ ] Dot-separated keys traverse nested dictionaries correctly
- [ ] Invalid keys return default value (no KeyError)
- [ ] get() handles missing intermediate keys gracefully
- [ ] YAML parsing errors logged and fall back to defaults
- [ ] to_dict() returns copy (not reference to internal dict)
- [ ] reload() re-reads file from disk
- [ ] Singleton pattern enforced in get_config()
- [ ] reset_config() clears global instance
- [ ] All section getters return {} if section missing
- [ ] is_enabled() returns False for missing features
- [ ] No hardcoded secrets in default config

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Use modern syntax | ✅ OK - Uses Optional[T], Dict[str, Any] |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All exceptions caught |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - Uses exc_info=True |
| CFG-001 | BASE_RULES.md | Pydantic Settings | ❌ GAP - Uses plain dict instead of Pydantic |
| CFG-003 | BASE_RULES.md | Validate all configuration values | ❌ GAP - No validation on load |
| CFG-004 | BASE_RULES.md | Extra forbid | ❌ GAP - No schema validation |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Only loads config |
| ARCH-004 | BASE_RULES.md | Functions < 20 lines (ideally) | ✅ OK - Most functions < 20 lines |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets in defaults |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - No tests exist yet |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

**Design Note:** This file intentionally returns Dict[str, Any] instead of value objects. See docstring for justification (configuration is not a domain entity).

---

## Dependencies
- **External:** PyYAML
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/test_config_loader.py:**
  - Success: Load valid YAML config file
  - Success: Missing file falls back to defaults
  - Success: get() with dot-separated key works
  - Success: get() returns default for missing key
  - Success: get_section() returns section dictionary
  - Success: to_dict() returns copy (not reference)
  - Success: reload() re-reads file
  - Success: get_config() returns singleton
  - Success: reset_config() clears global
  - Success: is_enabled() returns True/False correctly
  - Error: Invalid YAML syntax falls back to defaults
  - Error: Missing intermediate key returns default
  - Edge: Empty YAML file uses defaults
  - Edge: get() with empty string returns default
  - Edge: Nested key with None value handled

---

## Notes
- **Fallback Pattern:** Never raises exceptions for missing/invalid config (uses defaults)
- **Singleton:** Global instance managed by get_config()/reset_config()
- **Dot Notation:** Supports "metric_thresholds.sharpe_ratio.excellent" style keys
- **Mutable Dict:** Returns Dict[str, Any] by design (see docstring for rationale)
- **No Validation:** Configuration values not validated on load (downstream consumers validate)
