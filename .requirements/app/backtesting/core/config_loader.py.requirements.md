# config_loader.py

## Purpose
Centralized configuration loading from YAML files with validation for backtesting parameters, strategy settings, and execution options.

---

## Type Definitions / Data Classes

### ConfigValidationError (Exception)
```python
class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""
```
**Validation Rules:**
- Inherits from ValueError
- Used for all configuration-specific validation errors
- Provides clear error messages about what failed validation

### BacktestConfigLoader
```python
class BacktestConfigLoader:
    config_path: Path                      # Path to YAML config file
    _raw_config: Dict[str, Any]            # Raw loaded YAML data
```
**Validation Rules:**
- config_path must exist at initialization
- YAML must be valid
- Empty YAML files result in empty dict (not error)

---

## Function Signatures (Contracts)

### `BacktestConfigLoader.__init__(config_path: str) -> None`
**Pre:** config_path is valid path string
**Post:** Loader initialized, config loaded from file
**Raises:** FileNotFoundError if config_path doesn't exist
**Retry:** No
**Side Effects:** Reads YAML file, stores raw config

### `BacktestConfigLoader._load() -> None`
**Pre:** config_path is set
**Post:** _raw_config populated with YAML data
**Raises:** FileNotFoundError if config_path doesn't exist
**Retry:** No
**Side Effects:** Opens and reads YAML file

### `BacktestConfigLoader._validate_positive_decimal(value: Any, name: str, allow_zero: bool = False) -> Decimal`
**Pre:** value is Any type, name is string
**Post:** Returns validated Decimal
**Raises:** ConfigValidationError if value cannot be converted to Decimal or is negative (or zero if allow_zero=False)
**Retry:** No
**Side Effects:** None (pure validation)

**Validation Logic:**
1. Convert value to Decimal via Decimal(str(value))
2. Raise ConfigValidationError if conversion fails
3. Raise ConfigValidationError if decimal_value < 0
4. Raise ConfigValidationError if decimal_value == 0 and not allow_zero
5. Return decimal_value

### `BacktestConfigLoader._validate_percentage(value: Any, name: str, max_value: Optional[Decimal] = None) -> Decimal`
**Pre:** value is Any type, name is string
**Post:** Returns validated Decimal percentage
**Raises:** ConfigValidationError if validation fails
**Retry:** No
**Side Effects:** Calls _validate_positive_decimal with allow_zero=True

**Validation Logic:**
1. Call _validate_positive_decimal(value, name, allow_zero=True)
2. Default max_value is Decimal("100")
3. Raise ConfigValidationError if decimal_value > max_value
4. Return decimal_value

### `BacktestConfigLoader.raw_config (property) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns _raw_config
**Raises:** No
**Retry:** No
**Side Effects:** None (property getter)

### `BacktestConfigLoader.get_section(section: str, default: Optional[Dict] = None) -> Dict[str, Any]`
**Pre:** section is string
**Post:** Returns config section or default
**Raises:** No
**Retry:** No
**Side Effects:** None (dict lookup)

### `BacktestConfigLoader.get_backtest_config() -> BacktestConfig`
**Pre:** _raw_config loaded
**Post:** Returns validated BacktestConfig
**Raises:** ConfigValidationError if any parameter invalid
**Retry:** No
**Side Effects:** Creates BacktestConfig object

**Validation Rules:**
- initial_capital: must be positive Decimal (> 0)
- commission_per_trade: must be non-negative Decimal (>= 0, zero allowed)
- slippage_percentage: must be 0-100 as Decimal
- max_position_size: must be 0-1 as Decimal (0.0 to 1.0 for 0-100%)
- stop_loss_percentage: optional, must be 0-100 as Decimal if provided
- take_profit_percentage: optional, must be positive Decimal if provided
- risk_free_rate: can be any Decimal (positive, zero, or negative)

**Fallback Logic:**
- initial_capital falls back to input.initial_capital if not in backtest section
- Defaults: initial_capital=100000, commission=1.0, slippage=0.1, max_position=0.20

### `BacktestConfigLoader.get_strategy_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns strategy section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_execution_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns execution section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_modules_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns modules section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_learning_engines_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns learning_engines section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_parallelization_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns parallelization section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_reporting_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns reporting section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_meta_analysis_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns meta_analysis section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_input_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns input section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.get_backtests_config() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns backtests section
**Raises:** No
**Retry:** No
**Side Effects:** None (calls get_section)

### `BacktestConfigLoader.reload() -> None`
**Pre:** config_path still valid
**Post:** _raw_config reloaded from file
**Raises:** FileNotFoundError if config file removed
**Retry:** No
**Side Effects:** Re-reads YAML file, updates _raw_config

---

## Acceptance Criteria
- [ ] BacktestConfigLoader raises FileNotFoundError if config_path doesn't exist
- [ ] BacktestConfigLoader loads empty dict from empty YAML file
- [ ] _validate_positive_decimal raises ConfigValidationError for non-numeric values
- [ ] _validate_positive_decimal raises ConfigValidationError for negative values
- [ ] _validate_positive_decimal raises ConfigValidationError for zero when allow_zero=False
- [ ] _validate_positive_decimal returns Decimal when valid
- [ ] _validate_percentage raises ConfigValidationError for values > max_value
- [ ] _validate_percentage uses max_value=100 by default
- [ ] get_backtest_config validates initial_capital is positive
- [ ] get_backtest_config allows commission_per_trade to be zero
- [ ] get_backtest_config falls back to input.initial_capital for initial_capital
- [ ] get_backtest_config uses default values when config keys missing
- [ ] get_backtest_config returns BacktestConfig with all parameters
- [ ] get_section returns empty dict when section not found and no default
- [ ] get_section returns default when provided and section not found
- [ ] reload re-reads config from file

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` for 96 universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Configuration loading only |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have type hints |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ OK - Any used only for generic config values |
| LOG-001 | BASE_RULES.md | Structured logging | ⚠️ PARTIAL - Uses f-strings, should use extra={} |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ NOT APPLIED - No error logging with exceptions |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - ConfigValidationError for validation failures |
| ARCH-006 | BASE_RULES.md | Value objects immutable | ✅ OK - BacktestConfig is immutable |
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - Validates max_position_size, stop_loss, take_profit |

---

## Dependencies
- **External:** logging, decimal.Decimal, pathlib.Path, typing, yaml
- **Internal:** app.backtesting.models.BacktestConfig

---

## Required Tests
- **tests/unit/backtesting/core/test_config_loader.py:**
  - Test __init__ raises FileNotFoundError when config doesn't exist
  - Test __init__ loads valid YAML successfully
  - Test __init__ loads empty dict from empty YAML
  - Test _validate_positive_decimal with valid positive number
  - Test _validate_positive_decimal raises ConfigValidationError for negative
  - Test _validate_positive_decimal raises ConfigValidationError for zero when allow_zero=False
  - Test _validate_positive_decimal allows zero when allow_zero=True
  - Test _validate_positive_decimal raises ConfigValidationError for non-numeric
  - Test _validate_percentage with valid percentage
  - Test _validate_percentage raises ConfigValidationError for value > max_value
  - Test _validate_percentage uses max_value=100 by default
  - Test _validate_percentage with custom max_value
  - Test get_section returns section when exists
  - Test get_section returns empty dict when not found
  - Test get_section returns default when provided
  - Test get_backtest_config with all parameters
  - Test get_backtest_config with missing optional parameters
  - Test get_backtest_config validates initial_capital is positive
  - Test get_backtest_config allows commission_per_trade to be zero
  - Test get_backtest_config falls back to input.initial_capital
  - Test get_backtest_config raises ConfigValidationError for invalid initial_capital
  - Test get_backtest_config raises ConfigValidationError for invalid slippage
  - Test get_backtest_config raises ConfigValidationError for invalid max_position_size
  - Test get_strategy_config returns strategy section
  - Test get_execution_config returns execution section
  - Test get_modules_config returns modules section
  - Test get_learning_engines_config returns learning_engines section
  - Test get_parallelization_config returns parallelization section
  - Test get_reporting_config returns reporting section
  - Test get_meta_analysis_config returns meta_analysis section
  - Test get_input_config returns input section
  - Test get_backtests_config returns backtests section
  - Test reload re-reads config from file
  - Test raw_config property returns _raw_config

---

## Notes
- Configuration loading is critical for backtesting system
- All monetary values use Decimal for precision
- Percentage validation has two modes: 0-100 (slippage) and 0-1 (max_position_size)
- Optional parameters (stop_loss, take_profit) return None if not in config
- risk_free_rate can be negative for some markets
- YAML file must exist at initialization (not lazy loaded)
