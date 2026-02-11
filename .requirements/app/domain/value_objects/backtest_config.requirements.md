# backtest_config.py

## Purpose
BacktestConfig Value Object - Immutable configuration for backtesting operations with validation and serialization.

---

## Type Definitions / Data Classes

### BacktestConfigValue (frozen=True)
```python
@dataclass(frozen=True)
class BacktestConfigValue:
    # Strategy configuration
    strategy_name: str                      # REQUIRED - Strategy identifier
    strategy_params: Dict[str, Any]         # Default: {} - Strategy-specific parameters

    # Data configuration
    symbols: List[str]                      # Default: [] - Trading symbols
    start_date: datetime                    # Default: None - Backtest start date
    end_date: datetime                      # Default: None - Backtest end date
    initial_capital: Decimal                # Default: 100000 - Starting capital

    # Backtest type
    backtest_type: BacktestType             # Default: BASELINE - Backtest classification

    # Risk parameters
    max_position_size: Decimal              # Default: 0.10 - Max position size (0-1)
    stop_loss: Decimal                      # Default: 0.03 - Stop loss percentage (0-1)
    take_profit: Decimal                    # Default: 0.06 - Take profit percentage (0-1)

    # Execution parameters
    commission: Decimal                     # Default: 0.001 - Commission rate (>= 0)
    slippage: Decimal                       # Default: 0.0001 - Slippage rate (>= 0)

    # Output configuration
    output_dir: Optional[Path]              # Default: None - Output directory path
    save_results: bool                      # Default: True - Whether to save results

    # Advanced parameters
    enable_regime_detection: bool           # Default: False - Enable regime detection
    enable_meta_learning: bool              # Default: False - Enable meta-learning
    parallel_workers: Optional[int]         # Default: None - Number of parallel workers
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by all configuration fields, no identity)

**Invariants (enforced in __post_init__):**
- `strategy_name` must be non-empty
- `initial_capital` > 0
- `max_position_size` in (0, 1]
- `stop_loss` in (0, 1]
- `take_profit` in (0, 1]
- `commission` >= 0
- `slippage` >= 0
- `start_date` < `end_date` (if both provided)
- `parallel_workers` > 0 (if provided)

---

## Function Signatures (Contracts)

### `BacktestConfigValue.__post_init__() -> None`
**Pre:** None
**Post:** Configuration validated
**Raises:** `ValueError` if any invariant violated
**Retry:** No
**Side Effects:** None (validation only)

### `from_dict(config_dict: Dict[str, Any]) -> BacktestConfigValue` (classmethod)
**Pre:** None
**Post:** Returns BacktestConfigValue from dictionary
**Raises:** None (invalid backtest_type defaults to BASELINE)
**Retry:** No
**Side Effects:** None (factory method)

**Dictionary Mapping:**
- `start_date` / `end_date`: ISO format strings → datetime
- `backtest_type`: String → BacktestType (defaults to BASELINE if invalid)
- `output_directory`: String → Path
- Decimal values: String → Decimal (using Decimal(str()))

### `to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns configuration as dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure serialization)

**Dictionary Output:**
- Dates: ISO format strings
- Decimals: String representation
- Path: String representation
- BacktestType: value property

---

## Acceptance Criteria
- [ ] **AC-001:** strategy_name must be non-empty
- [ ] **AC-002:** initial_capital must be positive (> 0)
- [ ] **AC-003:** max_position_size must be between 0 and 1 (exclusive of 0)
- [ ] **AC-004:** stop_loss must be between 0 and 1 (exclusive of 0)
- [ ] **AC-005:** take_profit must be between 0 and 1 (exclusive of 0)
- [ ] **AC-006:** commission must be non-negative (>= 0)
- [ ] **AC-007:** slippage must be non-negative (>= 0)
- [ ] **AC-008:** start_date must be before end_date (if both provided)
- [ ] **AC-009:** parallel_workers must be positive (if provided)
- [ ] **AC-010:** Value object is immutable (frozen=True)
- [ ] **AC-011:** from_dict() handles invalid backtest_type gracefully
- [ ] **AC-012:** to_dict() serializes all fields correctly
- [ ] **AC-013:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (BacktestConfig Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Strategy name required | Backtesting | Non-empty identifier | ✅ OK - __post_init__ |
| Initial capital positive | Risk management | capital > 0 | ✅ OK - __post_init__ |
| Position size bounded | Risk management | 0 < size <= 1 | ✅ OK - __post_init__ |
| Stop loss bounded | Risk management | 0 < stop_loss <= 1 | ✅ OK - __post_init__ |
| Take profit bounded | Risk management | 0 < take_profit <= 1 | ✅ OK - __post_init__ |
| Commission non-negative | Execution | commission >= 0 | ✅ OK - __post_init__ |
| Slippage non-negative | Execution | slippage >= 0 | ✅ OK - __post_init__ |
| Date ordering | Temporal logic | start < end | ✅ OK - __post_init__ |
| Parallel workers positive | Concurrency | workers > 0 | ✅ OK - __post_init__ |
| Dict serialization | Clean code | from_dict/to_dict | ✅ OK - Implemented |
| Date ISO format | Serialization | ISO 8601 strings | ✅ OK - to_dict/from_dict |
| Invalid backtest_type | Defensive | Defaults to BASELINE | ✅ OK - from_dict() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib + BacktestType |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for value object patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `pathlib` (std), `typing` (std)
- **Internal:** `app.domain.value_objects.backtest_type.BacktestType`

---

## Required Tests
- **test_backtest_config_value_object.py:**
  - `test_create_valid_config()` - Valid configuration created
  - `test_empty_strategy_name()` - Raises ValueError
  - `test_negative_initial_capital()` - Raises ValueError
  - `test_invalid_max_position_size()` - Raises ValueError (not 0-1)
  - `test_invalid_stop_loss()` - Raises ValueError (not 0-1)
  - `test_invalid_take_profit()` - Raises ValueError (not 0-1)
  - `test_negative_commission()` - Raises ValueError
  - `test_negative_slippage()` - Raises ValueError
  - `test_invalid_date_order()` - Raises ValueError (start >= end)
  - `test_negative_parallel_workers()` - Raises ValueError
  - `test_from_dict_basic()` - Creates config from dict
  - `test_from_dict_with_dates()` - Parses ISO date strings
  - `test_from_dict_invalid_backtest_type()` - Defaults to BASELINE
  - `test_from_dict_with_output_dir()` - Parses Path
  - `test_to_dict()` - Serializes all fields
  - `test_to_dict_dates_iso()` - Dates as ISO strings
  - `test_to_dict_decimals_as_strings()` - Decimals as strings
  - `test_round_trip_serialization()` - to_dict → from_dict preserves data
  - `test_immutability()` - Cannot modify after creation
  - `test_defaults()` - All defaults applied correctly
  - `test_regime_detection_flag()` - enable_regime_detection stored
  - `test_meta_learning_flag()` - enable_meta_learning stored

---

## Notes
- **Critical:** BacktestConfigValue is a VALUE OBJECT (immutable, defined by all configuration fields, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Strategy Configuration:** strategy_name identifies the strategy; strategy_params holds strategy-specific configuration
- **Data Configuration:** symbols list defines universe; start/end dates define backtest period
- **Initial Capital:** Starting capital for backtest (default $100,000)
- **Backtest Type:** Categorizes backtest (BASELINE, WALK_FORWARD, etc.)
- **Risk Parameters:**
  - max_position_size: Maximum position size as percentage (10% = 0.10)
  - stop_loss: Stop loss percentage (3% = 0.03)
  - take_profit: Take profit percentage (6% = 0.06)
- **Execution Parameters:**
  - commission: Commission rate per trade (0.1% = 0.001)
  - slippage: Slippage per trade (0.01% = 0.0001)
- **Output Configuration:** output_dir for saving results; save_results flag
- **Advanced Features:**
  - enable_regime_detection: Enables Chan-style regime detection
  - enable_meta_learning: Enables meta-learning optimization
  - parallel_workers: Number of parallel workers for computation
- **Factory Method:** from_dict() creates from dictionary with ISO date parsing and defensive backtest_type handling
- **Serialization:** to_dict() converts to dictionary with ISO date formatting
- **Validation:** All parameters validated on creation via __post_init__
- **Default Values:** Sensible defaults provided for all optional fields

---

**File Reference:** `app/domain/value_objects/backtest_config.py`
**Last Audited:** 2026-02-01
