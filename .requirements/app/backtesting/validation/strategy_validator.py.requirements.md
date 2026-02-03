# strategy_validator.py

## Purpose
Validates trading strategies against critical acceptance criteria from Chan (2013): Sharpe ratio >= 1.0 and maximum drawdown <= 25%. Ensures strategies meet minimum performance standards before deployment.

---

## Type Definitions / Data Classes

### ValidationLevel Enum
```python
class ValidationLevel(str, Enum):
    PASS = "pass"      # Strategy meets all criteria
    FAIL = "fail"      # Strategy fails critical criteria
    WARNING = "warning"  # Strategy passes but with warnings
```

### ValidationResult Class
```python
@dataclass
class ValidationResult:
    is_valid: bool                        # REQUIRED - Overall pass/fail
    sharpe_ratio: Optional[Decimal]       # OPTIONAL - Sharpe ratio
    max_drawdown: Optional[Decimal]       # OPTIONAL - Max drawdown (negative)
    sharpe_passes: bool                   # REQUIRED - Sharpe meets threshold
    drawdown_passes: bool                 # REQUIRED - Drawdown meets threshold
    validation_level: ValidationLevel     # REQUIRED - Pass/Fail/Warning
    warnings: List[str]                   # REQUIRED - Warning messages
    errors: List[str]                     # REQUIRED - Error messages
    metadata: Dict[str, Any]              # REQUIRED - Additional metadata
```

**Validation Rules:**
- `is_valid == sharpe_passes and drawdown_passes` (logical consistency)
- `sharpe_ratio is None or sharpe_ratio >= 0` (Sharpe is non-negative)
- `max_drawdown is None or max_drawdown <= 0` (drawdown is negative or zero)
- `warnings` list is non-empty when `validation_level == WARNING`
- `errors` list is non-empty when `validation_level == FAIL`
- `metadata` contains `min_sharpe_threshold` and `max_drawdown_threshold`

---

## Function Signatures (Contracts)

### `StrategyValidator.__init__(min_sharpe: Optional[Decimal] = None, max_drawdown: Optional[Decimal] = None)`
**Pre:** None
**Post:** Validator initialized with provided or default thresholds
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Sets instance attributes `self.min_sharpe` and `self.max_drawdown`

### `StrategyValidator.validate_sharpe_ratio(sharpe: Decimal) -> bool`
**Pre:** `sharpe >= 0`
**Post:** Returns True if `sharpe >= self.min_sharpe`, False otherwise
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `StrategyValidator.validate_max_drawdown(max_dd: Decimal) -> bool`
**Pre:** `max_dd <= 0` (drawdown is negative)
**Post:** Returns True if `max_dd >= self.max_drawdown` (less negative is better)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `StrategyValidator.validate(sharpe_ratio: Optional[Decimal] = None, max_drawdown: Optional[Decimal] = None, **metadata) -> ValidationResult`
**Pre:** At least one of `sharpe_ratio` or `max_drawdown` is provided
**Post:** Returns ValidationResult with detailed validation status
**Raises:** ValueError if neither metric is provided
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `StrategyValidator.validate_backtest_result(backtest_result: Dict[str, Any]) -> ValidationResult`
**Pre:** `backtest_result` is a dict with optional `'sharpe_ratio'` and `'max_drawdown'` keys
**Post:** Returns ValidationResult by extracting metrics from dict
**Raises:** ❌ No (gracefully handles missing keys)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ValidationResult.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dictionary with all fields converted to JSON-serializable types
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `validate_strategy(sharpe_ratio: Optional[Decimal] = None, max_drawdown: Optional[Decimal] = None) -> ValidationResult`
**Pre:** At least one metric is provided
**Post:** Returns ValidationResult using default thresholds
**Raises:** ValueError if neither metric provided
**Retry:** ❌ No
**Side Effects:** None (convenience function, creates new validator)

---

## Acceptance Criteria
- [ ] `StrategyValidator.MIN_SHARPE_RATIO == Decimal("1.0")` (Chan #8)
- [ ] `StrategyValidator.MAX_MAX_DRAWDOWN == Decimal("-0.25")` (Chan #10, 25%)
- [ ] `validate()` raises ValueError when both metrics are None
- [ ] `validate_sharpe_ratio(Decimal("1.0"))` returns True (boundary case)
- [ ] `validate_sharpe_ratio(Decimal("0.99"))` returns False
- [ ] `validate_max_drawdown(Decimal("-0.25"))` returns True (boundary case)
- [ ] `validate_max_drawdown(Decimal("-0.26"))` returns False (exceeds 25%)
- [ ] `validate()` adds warning when Sharpe < 1.5 but >= 1.0
- [ ] `validate()` adds warning when drawdown < -20% but >= -25%
- [ ] `ValidationResult.to_dict()` converts Decimal to float
- [ ] `validate_backtest_result()` handles missing keys gracefully
- [ ] `is_valid == True` only when both `sharpe_passes` and `drawdown_passes` are True
- [ ] `validation_level == FAIL` when errors list is non-empty
- [ ] `validation_level == PASS` when `is_valid == True`
- [ ] Module-level constants `MIN_SHARPE_RATIO` and `MAX_MAX_DRAWDOWN` are exported

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

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| TYP-002 | 02-type-hints.md | Use modern syntax (Optional, Dict, List) | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ⚠️ NOT APPLIED - No exceptions raised |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - ValueError for missing metrics |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - No future data access |
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - Validates drawdown threshold |
| TRD-003 | BASE_RULES.md | Position limits | ⚠️ NOT APPLIED - Not in scope |
| TRD-004 | BASE_RULES.md | Audit trail | ⚠️ NOT APPLIED - No logging in validation |

**GAPS Found:**
- **LOG-004 (P0):** No logging of validation results or warnings
- **LOG-001 (P1):** No structured logging (no logger defined in module)
- **TRD-004 (P0):** No audit trail for validation decisions

---

## Dependencies
- **External:**
  - `decimal.Decimal` (standard library)
  - `enum.Enum` (standard library)
  - `dataclasses.dataclass` (standard library)
  - `typing` (standard library)
  - `logging` (standard library)

- **Internal:** None (standalone validator module)

---

## Required Tests
- **tests/unit/backtesting/validation/test_strategy_validator.py:**
  - Test `validate_sharpe_ratio()` with boundary values (0.99, 1.0, 1.5)
  - Test `validate_max_drawdown()` with boundary values (-0.26, -0.25, -0.20)
  - Test `validate()` raises ValueError when both metrics are None
  - Test `validate()` returns PASS when both metrics pass
  - Test `validate()` returns FAIL when either metric fails
  - Test `validate()` returns WARNING when metrics pass but are marginal
  - Test `validate()` adds warnings for marginal Sharpe (1.0-1.5)
  - Test `validate()` adds warnings for elevated drawdown (-20% to -25%)
  - Test `validate_backtest_result()` extracts metrics correctly
  - Test `validate_backtest_result()` handles missing keys
  - Test `ValidationResult.to_dict()` converts Decimal to float
  - Test `is_valid` is True only when both validations pass
  - Test `validation_level` is set correctly based on errors/warnings
  - Test custom thresholds via `__init__()`
  - Test module-level constants match class defaults

---

## Notes
- **Chan (2013) References:**
  - Chapter 8: Sharpe ratio >= 1.0 for adequate risk-adjusted returns
  - Chapter 10: Maximum drawdown <= 25% for acceptable risk exposure
- Drawdown is represented as negative decimal (e.g., -0.15 = -15% loss)
- "Less negative" drawdown is better (-0.20 > -0.30)
- This is a FASE 5 Task 1 module for strategy validation
- ValidationLevel enum supports three-tier classification (PASS/FAIL/WARNING)
- Module exports convenience function `validate_strategy()` for quick validation
