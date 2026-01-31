# config_loader.py

## Purpose
Centralized configuration loading from YAML files with validation for backtest parameters including Decimal validation for financial values and comprehensive error handling.

---

## Type Definitions / Data Classes

### ConfigValidationError(ValueError)
```python
class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""
    pass
```

**Validation Rules:**
- Inherits from ValueError
- Used for all config validation failures

### BacktestConfigLoader
```python
class BacktestConfigLoader:
    config_path: Path                    # REQUIRED - Path to YAML config file
    _raw_config: Dict[str, Any]          # PRIVATE - Loaded YAML dict
```

**Validation Rules:**
- config_path must exist (raises FileNotFoundError)
- YAML must be valid (raises yaml.YAMLError)
- All numeric values validated as Decimal for financial precision

---

## Function Signatures (Contracts)

### `BacktestConfigLoader.__init__(config_path: str) -> None`
**Pre:** config_path is string
**Post:** Config loaded from YAML, _raw_config populated
**Raises:** FileNotFoundError if config_path doesn't exist
**Retry:** No
**Side Effects:** File I/O (reads YAML), YAML parsing

### `BacktestConfigLoader._load() -> None`
**Pre:** config_path is set
**Post:** _raw_config populated with YAML content
**Raises:** FileNotFoundError if path invalid
**Retry:** No
**Side Effects:** File I/O, YAML parsing

### `BacktestConfigLoader._validate_positive_decimal(value: Any, name: str, allow_zero: bool = False) -> Decimal`
**Pre:** value is convertible to Decimal
**Post:** Returns validated Decimal
**Raises:** ConfigValidationError if not convertible or negative (or zero if not allow_zero)
**Retry:** No
**Side Effects:** None (validation only)

### `BacktestConfigLoader._validate_percentage(value: Any, name: str, max_value: Optional[Decimal] = None) -> Decimal`
**Pre:** value is convertible to Decimal
**Post:** Returns validated Decimal percentage (0 to max_value)
**Raises:** ConfigValidationError if > max_value or negative
**Retry:** No
**Side Effects:** None (validation only)

### `BacktestConfigLoader.get_section(section: str, default: Optional[Dict] = None) -> Dict[str, Any]`
**Pre:** section is string
**Post:** Returns config section or default
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_backtest_config() -> BacktestConfig`
**Pre:** _raw_config has 'backtest' or 'input' section
**Post:** Returns validated BacktestConfig
**Raises:** ConfigValidationError if any validation fails
**Retry:** No
**Side Effects:** None (creates BacktestConfig object)

### `BacktestConfigLoader.get_strategy_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'strategy' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_execution_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'execution' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_modules_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'modules' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_learning_engines_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'learning_engines' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_parallelization_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'parallelization' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_reporting_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'reporting' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_meta_analysis_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'meta_analysis' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_input_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'input' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.get_backtests_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns 'backtests' section or {}
**Raises:** No
**Retry:** No
**Side Effects:** None (read-only)

### `BacktestConfigLoader.reload() -> None`
**Pre:** None
**Post:** Config reloaded from file
**Raises:** FileNotFoundError if file removed
**Retry:** No
**Side Effects:** File I/O, YAML parsing

---

## Acceptance Criteria
- [ ] AC-CONFIG-001: __init__ raises FileNotFoundError if config_path missing
- [ ] AC-CONFIG-002: _validate_positive_decimal raises ConfigValidationError for negative values
- [ ] AC-CONFIG-003: _validate_positive_decimal raises ConfigValidationError for zero if allow_zero=False
- [ ] AC-CONFIG-004: _validate_percentage raises ConfigValidationError if > max_value
- [ ] AC-CONFIG-005: get_backtest_config validates all required fields
- [ ] AC-CONFIG-006: get_backtest_config returns BacktestConfig with Decimal types
- [ ] AC-CONFIG-007: get_section returns default dict if section missing
- [ ] AC-CONFIG-008: reload() updates _raw_config from file
- [ ] AC-CONFIG-009: initial_capital validated as positive Decimal
- [ ] AC-CONFIG-010: commission_per_trade allows zero (allow_zero=True)
- [ ] AC-CONFIG-011: slippage_percentage validated as 0-100%
- [ ] AC-CONFIG-012: max_position_size validated as 0-1 (decimal percentage)
- [ ] AC-CONFIG-013: stop_loss_percentage optional (can be None)
- [ ] AC-CONFIG-014: take_profit_percentage optional (can be None)
- [ ] AC-CONFIG-015: risk_free_rate allows negative values

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES.md (CFG-001) | Type-safe configuration | ✅ OK - Uses Decimal for financial values |
| CFG-002 | BASE_RULES.md (CFG-003) | Validate all configuration values | ✅ OK - Comprehensive validation methods |
| CFG-003 | BASE_RULES.md (SEC-007) | Input validation at boundaries | ✅ OK - Validates on load |
| CFG-004 | BASE_RULES.md (TRD-001) | Decimal for financial precision | ✅ OK - All values converted to Decimal |
| CFG-005 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - Full type hints |
| CFG-006 | BASE_RULES.md (LOG-001) | Structured logging | ✅ OK - Uses logger |
| CFG-007 | BASE_RULES.md (ARCH-004) | Small functions | ✅ OK - Methods focused and concise |

**GAP Analysis:**
- No critical gaps found. Configuration validation is comprehensive with proper Decimal handling for financial values.

---

## Dependencies
- **External:** yaml (PyYAML), pathlib.Path, decimal.Decimal
- **Internal:**
  - `app.backtesting.models.BacktestConfig`

---

## Required Tests
- **tests/backtesting/core/test_config_loader.py:**
  - Test __init__ with valid config path
  - Test __init__ raises FileNotFoundError if missing
  - Test _validate_positive_decimal with valid values
  - Test _validate_positive_decimal raises on negative
  - Test _validate_positive_decimal raises on zero if allow_zero=False
  - Test _validate_percentage with valid percentages
  - Test _validate_percentage raises if > max_value
  - Test get_backtest_config with all fields
  - Test get_backtest_config validates initial_capital
  - Test get_backtest_config validates commission_per_trade (allows zero)
  - Test get_backtest_config validates slippage (0-100%)
  - Test get_backtest_config validates max_position_size (0-1)
  - Test get_backtest_config allows optional stop_loss/take_profit
  - Test get_section returns default if missing
  - Test get_strategy_config returns strategy section
  - Test reload() updates config
  - Test invalid YAML raises appropriate error
  - Test non-numeric values raise ConfigValidationError

---

## Notes
Critical for type-safe configuration loading. Decimal validation prevents floating-point precision errors in financial calculations. Comprehensive validation prevents invalid backtest configurations.
