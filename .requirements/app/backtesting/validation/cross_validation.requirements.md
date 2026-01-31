# cross_validation.py

## Purpose
Provides purged cross-validation wrappers and utilities following López de Prado's methodology for financial time series with event-based embargo and purging to prevent look-ahead bias.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### PurgedKFoldConfig Class/DataClass
```python
@dataclass
class PurgedKFoldConfig:
    n_splits: int = 5                     # REQUIRED, >= 2 - Number of folds for cross-validation
    purge_pct: float = 0.05               # REQUIRED, [0, 0.5] - Percentage to purge before test set
    embargo_pct: float = 0.02             # REQUIRED, [0, 0.5] - Percentage to embargo after test set
    min_train_samples: int = 252          # REQUIRED, >= 1 - Minimum training samples (1 year daily)
    min_test_samples: int = 20            # REQUIRED, >= 1 - Minimum test samples
    shuffle: bool = False                 # REQUIRED - Never shuffle time series data
    random_state: Optional[int] = None    # OPTIONAL - Random state for reproducibility
```

**Validation Rules:**
- `n_splits` must be >= 2
- `purge_pct` must be in [0, 0.5]
- `embargo_pct` must be in [0, 0.5]
- `min_train_samples` must be >= 1
- `min_test_samples` must be >= 1
- `shuffle` MUST be False for time series (enforced)
- All validation in `__post_init__` raises ValueError

### PurgedSplit Class/DataClass
```python
@dataclass
class PurgedSplit:
    fold: int                       # REQUIRED - Fold number
    train_indices: np.ndarray       # REQUIRED - Training indices after purging
    test_indices: np.ndarray        # REQUIRED - Test indices
    purged_indices: np.ndarray      # REQUIRED - Indices purged from training set
    embargo_indices: np.ndarray     # REQUIRED - Indices embargoed (buffer zone)
    train_size_purged: int          # REQUIRED - Training set size before purging
    train_size_after_purge: int     # REQUIRED - Training set size after purging
    purge_pct_actual: float         # REQUIRED - Actual purge percentage applied
    embargo_size: int               # REQUIRED - Number of embargoed samples
```

**Validation Rules:**
- `train_size_after_purge` <= `train_size_purged`
- `train_indices` must not overlap with `test_indices` or `embargo_indices`
- `purge_pct_actual` in [0, 1]

---

## Function Signatures (Contracts)

### `PurgedKFold.split(X, y=None, groups=None) -> List[Tuple[np.ndarray, np.ndarray]]`
**Pre:** X length >= min_train_samples + min_test_samples; X must be DataFrame, Series, or array
**Post:** Returns list of (train_indices, test_indices) with temporal integrity maintained
**Raises:** ValueError if insufficient samples or no valid folds generated
**Retry:** ❌ No
**Side Effects:** Stores split details in `self.split_details`; logs warnings for skipped folds

### `PurgedKFold.validate_no_leakage(X) -> bool`
**Pre:** split() must have been called; `self.split_details` must not be empty
**Post:** Returns True if no temporal leakage detected (train_max < test_min for all folds)
**Raises:** ValueError if no splits available
**Retry:** ❌ No
**Side Effects:** Logs error messages for each leakage detected

### `PurgedKFold.get_split_summary() -> pd.DataFrame`
**Pre:** split() must have been called
**Post:** Returns DataFrame with fold statistics (train_size, test_size, purged_count, embargo_size, purge_pct)
**Raises:** ValueError if no splits available
**Retry:** ❌ No
**Side Effects:** None

### `get_purge_indices(train_indices, test_indices, purge_pct=0.05, n_samples=None) -> np.ndarray`
**Pre:** train_indices and test_indices must be numpy arrays; must not overlap
**Post:** Returns array of training indices to purge (closest to test set)
**Raises:** No explicit exceptions (returns empty array if edge cases)
**Retry:** ❌ No
**Side Effects:** None

### `get_embargo_indices(test_indices, embargo_pct=0.02, n_samples=None) -> np.ndarray`
**Pre:** test_indices must be non-empty numpy array
**Post:** Returns array of embargo indices after test set (buffer zone)
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

### `purged_kfold_splits(X, n_splits=5, purge_pct=0.05, embargo_pct=0.02, min_train_samples=252, min_test_samples=20) -> List[Tuple[np.ndarray, np.ndarray]]`
**Pre:** X must have sufficient samples
**Post:** Returns list of purged (train_indices, test_indices) tuples
**Raises:** ValueError from PurgedKFold.split()
**Retry:** ❌ No
**Side Effects:** Creates PurgedKFold instance and calls split()

### `cross_validate_with_purging(estimator, X, y, n_splits=5, purge_pct=0.05, embargo_pct=0.02, scoring=None, fit_params=None) -> Dict[str, List[float]]`
**Pre:** estimator must have fit() and predict() methods; X and y must have same length
**Post:** Returns dict with 'test_score' list (one per fold)
**Raises:** Exceptions from model fitting or prediction
**Retry:** ❌ No
**Side Effects:** Fits estimator on each fold; modifies estimator state

### `PurgedTimeSeriesSplit.split(X, y=None, groups=None) -> List[Tuple[np.ndarray, np.ndarray]]`
**Pre:** X must have sufficient samples for n_splits splits
**Post:** Returns list of time-ordered (train_indices, test_indices) with purging
**Raises:** No explicit exceptions (logs warnings for skipped splits)
**Retry:** ❌ No
**Side Effects:** Stores split details in `self.split_details`

---

## Acceptance Criteria
- [ ] PurgedKFold enforces shuffle=False for time series integrity
- [ ] All splits maintain temporal ordering (train < test)
- [ ] Purge zone removes samples immediately before test set
- [ ] Embargo zone creates buffer after test set
- [ ] validate_no_leakage() catches temporal violations
- [ ] get_split_summary() returns complete fold statistics
- [ ] cross_validate_with_purging() works with sklearn estimators
- [ ] PurgedTimeSeriesSplit generates expanding window splits
- [ ] Configuration validation prevents invalid parameters
- [ ] Edge cases handled: small datasets, boundary conditions

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.warning for skipped folds |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each class/function has single purpose |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses None for optional parameters |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - debug/warning/info/error used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File demonstrates strong adherence to validation patterns and temporal integrity requirements.

---

## Dependencies
- **External:** numpy, pandas, sklearn (KFold), logging, typing
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_cross_validation.py:**
  - Test PurgedKFoldConfig validation (all parameters)
  - Test PurgedKFold.split() generates correct fold count
  - Test PurgedKFold.split() maintains temporal ordering
  - Test PurgedKFold.split() applies purge and embargo correctly
  - Test PurgedKFold.validate_no_leakage() detects violations
  - Test PurgedKFold.validate_no_leakage() passes on valid splits
  - Test PurgedKFold.get_split_summary() returns correct DataFrame
  - Test get_purge_indices() function edge cases
  - Test get_embargo_indices() function edge cases
  - Test apply_embargo() removes embargoed samples
  - Test purged_kfold_splits() convenience function
  - Test cross_validate_with_purging() with sklearn estimator
  - Test PurgedTimeSeriesSplit generates correct splits
  - Test PurgedTimeSeriesSplit with max_train_size sliding window
  - Test insufficient samples raises ValueError
  - Test edge cases: empty arrays, single sample, boundary conditions

---

## Notes
Critical for financial ML: Implements López de Prado's Chapter 4 methodology with purge and embargo. Key innovation: prevents look-ahead bias by removing overlapping training samples and adding buffer zones. Never shuffle time series data.
