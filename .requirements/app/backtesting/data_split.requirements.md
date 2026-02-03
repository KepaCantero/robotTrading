# data_split.py

## Purpose
Prevent overfitting and data snooping by properly splitting time-series data into train/validation/test sets with purged K-Fold cross-validation per López de Prado.

---

## Type Definitions / Data Classes

### DataSplit (dataclass)
```python
@dataclass
class DataSplit:
    train_pct: float = 0.70          # REQUIRED - Percentage for training (default 70%)
    val_pct: float = 0.15            # REQUIRED - Percentage for validation (default 15%)
    test_pct: float = 0.15           # REQUIRED - Percentage for testing (default 15%)
    min_train_days: int = 252        # REQUIRED - Minimum training days (1 year)
    use_purged_kfold: bool = False   # OPTIONAL - Use Purged K-Fold CV
    n_splits: int = 5                # OPTIONAL - Number of folds for Purged K-Fold
    purge_pct: float = 0.05          # OPTIONAL - Percentage to purge before test set
    embargo_pct: float = 0.02        # OPTIONAL - Percentage to embargo after test set
```

**Validation Rules:**
- `train_pct + val_pct + test_pct` must equal 1.0 (±0.01 tolerance)
- All percentages must be positive
- `min_train_days` default is 252 (1 trading year)

---

## Function Signatures (Contracts)

### `TrainValTestSplitter.__init__(split_config: Optional[DataSplit] = None)`
**Pre:** split_config valid or None
**Post:** TrainValTestSplitter initialized with default or custom config
**Raises:** ValueError if split_config percentages don't sum to 1.0
**Retry:** No
**Side Effects:** None

### `split_data(market_data: List, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Tuple[List, List, List]`
**Pre:** market_data non-empty
**Post:** Returns (train_data, val_data, test_data) time-based split
**Raises:** ValueError if market_data empty or no data after date filters
**Retry:** No
**Side Effects:** None (splits are new lists)

### `walk_forward_split(market_data: List, window_size: int = 252, step_size: int = 63) -> List[Tuple[List, List, List]]`
**Pre:** market_data has sufficient data (>= window_size * 3)
**Post:** Returns list of (train, val, test) tuples for rolling windows
**Raises:** None (returns [] if insufficient data)
**Retry:** No
**Side Effects:** None

### `purged_kfold_split(market_data: List) -> List[Tuple[List, List]]`
**Pre:** market_data sorted by timestamp
**Post:** Returns list of (train_data, test_data) tuples with purged splits
**Raises:** None
**Retry:** No
**Side Effects:** None

### `purged_kfold_split_with_validation(market_data: List) -> List[Tuple[List, List, List]]`
**Pre:** market_data sorted by timestamp
**Post:** Returns list of (train_data, val_data, test_data) tuples
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MultipleTestingCorrector.__init__(num_tests: int, base_confidence: float = 0.95)`
**Pre:** num_tests > 0, base_confidence between 0-1
**Post:** Corrector initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `bonferroni_correction() -> float`
**Pre:** __init__ called with num_tests
**Post:** Returns adjusted confidence level (conservative)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `benjamini_hochberg_correction(p_values: List[float]) -> List[bool]`
**Pre:** p_values valid list of floats 0-1
**Post:** Returns list of bool indicating significance at 5% FDR
**Raises:** None
**Retry:** No
**Side Effects:** None

### `holm_bonferroni_correction(p_values: List[float]) -> List[bool]`
**Pre:** p_values valid list
**Post:** Returns list of bool indicating significance at 5% level
**Raises:** None
**Retry:** No
**Side Effects:** None

### `validate_out_of_sample_performance(train_sharpe: float, val_sharpe: float, test_sharpe: float, min_performance_ratio: float = 0.7) -> bool`
**Pre:** All Sharpe ratios valid floats
**Post:** Returns True if test_sharpe >= min_ratio * val_sharpe and no sign flip
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings if validation fails

---

## Acceptance Criteria
- [ ] Split percentages must sum to 1.0 (validated in __init__)
- [ ] Time-based split preserves temporal order (no random shuffling)
- [ ] Train/Val/Test splits are chronological (train → val → test)
- [ ] Walk-forward splits create rolling windows correctly
- [ ] Purged K-Fold prevents look-ahead bias
- [ ] Embargo period prevents data leakage between folds
- [ ] Minimum train days warning logged if insufficient data
- [ ] Bonferroni correction controls family-wise error rate
- [ ] Benjamini-Hochberg controls false discovery rate
- [ ] Out-of-sample validation detects overfitting
- [ ] Sign flip detection (positive val, negative test)

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
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ✅ OK - Most functions small |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| ML-001 | Custom | No data leakage from future to past | ✅ OK - Time-based splits |
| ML-002 | Custom | Prevent look-ahead bias | ✅ OK - Purged K-Fold implemented |

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, datetime, typing, numpy
- **Internal:**
  - app.backtesting.validation.purged_kfold.PurgedKFold (conditional import)

---

## Required Tests
- **test_data_split.py:**
  - Success: Basic train/val/test split
  - Success: Split percentages sum to 1.0
  - Success: Time-based split preserves order
  - Success: Walk-forward split creates correct windows
  - Success: Purged K-Fold with embargo
  - Success: Purged K-Fold with validation
  - Error: Percentages don't sum to 1.0 (ValueError)
  - Error: Empty market_data (ValueError)
  - Error: No data after date filtering (ValueError)
  - Edge: Insufficient data for walk-forward (warning logged, returns [])
  - Edge: Minimum train days warning
  - Integration: Bonferroni correction reduces confidence appropriately
  - Integration: Benjamini-Hochberg FDR control
  - Integration: Out-of-sample validation catches overfitting

---

## Notes
- Implements López de Prado's "Advances in Financial Machine Learning" methodology
- Purged K-Fold prevents look-ahead bias in time-series cross-validation
- Embargo period adds additional buffer after test set
- Multiple testing corrections prevent data snooping bias
- OOS validation ratio default 0.7 (test Sharpe must be >= 70% of val Sharpe)
