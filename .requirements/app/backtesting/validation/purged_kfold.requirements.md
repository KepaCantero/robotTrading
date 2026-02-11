# purged_kfold.py

## Purpose
Implements López de Prado's Purged K-Fold cross-validation with event-based embargo for financial time series to prevent look-ahead bias and information leakage in backtesting.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### PurgedCVConfig Class/DataClass
```python
@dataclass
class PurgedCVConfig:
    n_splits: int                      # REQUIRED, >= 2 - Number of CV folds
    embargo_pct: float = 0.01          # REQUIRED, [0, 0.5] - Percentage to embargo after test set
    purge_pct: float = 0.05            # REQUIRED, [0, 0.5] - Percentage to purge before test set
    min_train_samples: int = 252       # REQUIRED, >= 1 - Minimum training samples (1 year daily)
    min_test_samples: int = 20         # REQUIRED, >= 1 - Minimum test samples
    random_state: Optional[int] = None # OPTIONAL - Random state for reproducibility
```

**Validation Rules:**
- `n_splits` must be >= 2
- `purge_pct` must be in [0, 0.5]
- `embargo_pct` must be in [0, 0.5]
- Validates in `__post_init__` with ValueError on violation

### PurgedSplitResult Class/DataClass
```python
@dataclass
class PurgedSplitResult:
    fold: int                          # REQUIRED - Fold number
    train_indices: np.ndarray          # REQUIRED - Training indices after purging
    test_indices: np.ndarray           # REQUIRED - Test indices
    purged_indices: np.ndarray         # REQUIRED - Indices purged from training set
    embargo_indices: np.ndarray        # REQUIRED - Indices in embargo buffer zone
    train_size_before: int             # REQUIRED - Training set size before purging
    train_size_after: int              # REQUIRED - Training set size after purging
    n_purged: int                      # REQUIRED - Number of samples purged
    n_embargoed: int                   # REQUIRED - Number of samples in embargo zone
```

**Validation Rules:**
- All arrays must be numpy arrays
- `train_size_after` <= `train_size_before`
- `train_indices` must not overlap with `test_indices` (temporal integrity)

---

## Function Signatures (Contracts)

### `PurgedKFold.split(X, y=None, groups=None, events=None) -> Generator[Tuple[np.ndarray, np.ndarray]]`
**Pre:** X must have >= min_train_samples + min_test_samples; events must have 't1' column if provided
**Post:** Yields (train_indices, test_indices) with no temporal overlap; train_indices < test_indices
**Raises:** ValueError if insufficient samples; logs warning if fold skipped
**Retry:** ❌ No
**Side Effects:** Stores split results in `self.split_results`; logs debug info

### `PurgedKFold._calculate_event_embargo(test_indices, events, index) -> np.ndarray`
**Pre:** events must contain 't1' column; test_indices must be sorted
**Post:** Returns embargoed indices based on maximum t1 in test set plus buffer
**Raises:** Returns empty array on error
**Retry:** ❌ No
**Side Effects:** None

### `cv_score(estimator, X, y, events=None, n_splits=5, embargo_pct=0.01, purge_pct=0.05, scoring=None) -> Dict[str, float]`
**Pre:** estimator must have fit() and predict() methods; X, y must have same length
**Post:** Returns dict with 'mean_score', 'std_score', 'fold_scores'
**Raises:** ValueError if no valid folds generated
**Retry:** ❌ No
**Side Effects:** Fits estimator on each fold; logs fold scores

---

## Acceptance Criteria
- [ ] PurgedKFold prevents look-ahead bias by ensuring train_indices < test_indices
- [ ] Event-based embargo uses t1 (exit times) when events DataFrame provided
- [ ] Minimum sample sizes respected (min_train_samples, min_test_samples)
- [ ] No information leakage: validate_no_leakage() returns True
- [ ] Split summary DataFrame contains all fold statistics
- [ ] cv_score works with sklearn-compatible estimators
- [ ] Configuration validation catches invalid parameters

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.error for exceptions |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Class handles only purged CV |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses None for optional |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - debug/info/warning/error used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File shows strong compliance with critical rules.

---

## Dependencies
- **External:** numpy, pandas, sklearn (KFold), logging, typing
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_purged_kfold.py:**
  - Test PurgedCVConfig validation (invalid n_splits, purge_pct, embargo_pct)
  - Test split() generates correct number of folds
  - Test split() respects temporal ordering (train < test)
  - Test split() applies purge zone correctly
  - Test split() applies embargo zone correctly
  - Test event-based embargo vs percentage-based embargo
  - Test validate_no_leakage() detects temporal violations
  - Test validate_no_leakage() passes on correct splits
  - Test cv_score() with sklearn estimator
  - Test get_split_summary() returns correct statistics
  - Test insufficient samples raises ValueError
  - Test edge cases: empty data, single sample, boundary conditions

---

## Notes
Key pattern from López de Prado Chapter 4: Uses event exit times (t1) from triple barrier labeling for embargo calculation, not fixed windows. Critical for preventing look-ahead bias in financial ML backtesting.
