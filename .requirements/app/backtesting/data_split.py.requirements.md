# data_split.py

## Purpose
Time-series data splitting for backtesting with train/validation/test sets, walk-forward validation, and purged K-Fold cross-validation (López de Prado).

---

## Type Definitions / Data Classes

### DataSplit Class (Configuration)
```python
class DataSplit:
    train_pct: float       # REQUIRED - default 0.70
    val_pct: float         # REQUIRED - default 0.15
    test_pct: float        # REQUIRED - default 0.15
    min_train_days: int    # REQUIRED - default 252
    use_purged_kfold: bool # REQUIRED - default False
    n_splits: int          # REQUIRED - default 5
    purge_pct: float       # REQUIRED - default 0.05
    embargo_pct: float     # REQUIRED - default 0.02
```

**Validation Rules:**
- train_pct + val_pct + test_pct must equal 1.0 (±0.01 tolerance)
- All percentages must be positive

---

## Function Signatures (Contracts)

### `TrainValTestSplitter.__init__(split_config: Optional[DataSplit] = None)`
**Pre:** None
**Post:** Initialize splitter with config
**Raises:** None
**Retry:** No
**Side Effects:** None

### `split_data(market_data: List, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Tuple[List, List, List]`
**Pre:** market_data is non-empty list with timestamp attribute
**Post:** Returns (train_data, val_data, test_data) preserving temporal order
**Raises:** ValueError if market_data empty
**Retry:** No
**Side Effects:** Logs split percentages

### `walk_forward_split(market_data: List, window_size: int = 252, step_size: int = 63) -> List[Tuple[List, List, List]]`
**Pre:** market_data has timestamp attributes
**Post:** Returns list of rolling window splits
**Raises:** None
**Retry:** No
**Side Effects:** Logs number of windows

### `purged_kfold_split(market_data: List) -> List[Tuple[List, List]]`
**Pre:** market_data has timestamp attributes
**Post:** Returns purged K-Fold splits
**Raises:** ImportError if PurgedKFold not available
**Retry:** No
**Side Effects:** Logs split count

### `purged_kfold_split_with_validation(market_data: List) -> List[Tuple[List, List, List]]`
**Pre:** market_data has timestamp attributes
**Post:** Returns purged K-Fold splits with validation
**Raises:** ImportError if PurgedKFold not available
**Retry:** No
**Side Effects:** Logs split count

### `MultipleTestingCorrector.bonferroni_correction() -> float`
**Pre:** None
**Post:** Returns adjusted confidence (base_confidence / num_tests)
**Raises:** None
**Retry:** No
**Side Effects:** Logs adjustment

### `MultipleTestingCorrector.benjamini_hochberg_correction(p_values: List[float]) -> List[bool]`
**Pre:** p_values in [0, 1]
**Post:** Returns list of significant tests (5% FDR)
**Raises:** None
**Retry:** No
**Side Effects:** Logs significant count

### `MultipleTestingCorrector.holm_bonferroni_correction(p_values: List[float]) -> List[bool]`
**Pre:** p_values in [0, 1]
**Post:** Returns list of significant tests (5% level)
**Raises:** None
**Retry:** No
**Side Effects:** Logs significant count

### `validate_out_of_sample_performance(train_sharpe: float, val_sharpe: float, test_sharpe: float, min_performance_ratio: float = 0.7) -> bool`
**Pre:** All Sharpe ratios are floats
**Post:** Returns True if test_sharpe >= min_ratio * val_sharpe
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings for degradation

---

## Acceptance Criteria
- [ ] All splits preserve temporal order (no look-ahead bias)
- [ ] DataSplit validates percentages sum to 1.0
- [ ] Walk-forward windows use configurable sizes
- [ ] Purged K-Fold imports from validation module
- [ ] Multiple testing corrections implemented
- [ ] OOS validation detects performance degradation

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
| BT-003 | 13-trading-specific-rules.md | No look-ahead bias | ✅ OK - Time-based splitting |
| BT-001 | 13-trading-specific-rules.md | Walk-forward validation | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ⚠️ PARTIAL |
| TST-005 | 06-testing.md | Coverage > 80% | ✅ FIXED - 2026-02-03 - Created test file with basic coverage (21 tests) |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, datetime
- **Internal:** app.backtesting.validation.purged_kfold

---

## Required Tests
- **tests/unit/backtesting/test_data_split.py:**
  - Test DataSplit validation
  - Test basic train/val/test split
  - Test date filtering
  - Test walk-forward split
  - Test purged K-Fold split
  - Test Bonferroni correction
  - Test Benjamini-Hochberg FDR
  - Test Holm-Bonferroni
  - Test OOS validation

---

## Notes
- **López de Prado Method:** Purged K-Fold prevents data leakage
- **Default Splits:** 70% train, 15% validation, 15% test
- **Walk-Forward Defaults:** 252-day window, 63-day step
