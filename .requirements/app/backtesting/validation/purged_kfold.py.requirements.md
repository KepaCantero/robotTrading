# Requirements: backtesting/validation/purged_kfold.py

## Source File Analysis
- **File Path**: `app/backtesting/validation/purged_kfold.py`
- **Lines of Code**: 782
- **Audit Date**: 2026-02-07T12:00:00Z

## Audit Status
**Status**: PASSED_WITH_NOTES

### Critical Rules Compliance
- ✅ R099: Absolute imports only
- ✅ R098: No relative imports from parent packages
- ✅ R104: No bare except clauses
- ✅ R105: No print() statements in production code
- ✅ R107: No mutable default arguments
- ✅ R108: Proper exception handling
- ✅ R110: Google-style docstrings
- ✅ R111: No circular imports
- ⚠️  R100: Uses `Optional[T]` and `Union[T, U]` instead of modern `T | None` (acceptable for compatibility)
- ⚠️  R102: One `Any` usage for ML estimator interface (appropriately generic)

## Purpose
Implements López de Prado's Purged K-Fold cross-validation with embargo for financial time series. This module prevents look-ahead bias and information leakage in backtesting by:
- Removing training samples that overlap with test period (purge)
- Adding buffer period after test set (embargo)
- Maintaining temporal integrity for time series data

Reference: "Advances in Financial Machine Learning" by Marcos López de Prado, Chapter 3

## Dependencies

### External Dependencies
- `numpy`: Numerical operations and array handling
- `pandas`: DataFrame/Series operations
- `sklearn.model_selection.KFold`: Base K-Fold implementation
- `dataclasses`: Configuration dataclasses
- `logging`: Structured logging

### Internal Dependencies
None (self-contained validation module)

## Classes/Functions

### Configuration Classes
- `PurgedKFoldConfig`: Configuration dataclass with validation
  - n_splits: Number of folds (default: 5)
  - purge_pct: Percentage to purge before test set (default: 0.05)
  - embargo_pct: Percentage to embargo after test set (default: 0.02)
  - min_train_samples: Minimum training samples (default: 252)
  - min_test_samples: Minimum test samples (default: 20)
  - shuffle: Whether to shuffle (default: False for time series)
  - random_state: Random state for reproducibility

- `PurgedSplit`: Dataclass representing a single purged split
  - fold: Fold number
  - train_indices: Training indices after purging
  - test_indices: Test indices
  - purged_indices: Indices removed from training
  - embargo_indices: Buffer zone indices
  - Metadata: train_size_purged, train_size_after_purge, purge_pct_actual, embargo_size

### Main Classes
- `PurgedKFold`: Main cross-validator class
  - `__init__(config)`: Initialize with configuration
  - `split(X, y, groups)`: Generate purged train/test splits
  - `get_n_splits()`: Return number of splits
  - `validate_no_leakage(X)`: Validate no information leakage
  - `get_split_summary()`: Get DataFrame summary of splits

- `PurgedTimeSeriesSplit`: Time series specific validator
  - Supports expanding/sliding windows
  - Configurable max_train_size and test_size

### Standalone Functions
- `get_purge_indices()`: Calculate which training indices to purge
- `get_embargo_indices()`: Calculate embargo buffer indices
- `apply_embargo()`: Apply embargo to training set
- `purged_kfold_splits()`: Convenience function for quick usage
- `cross_validate_with_purging()`: sklearn-like cross_validate interface

## Business Logic

### Purging Process
1. Create base K-Fold splits (never shuffle for time series)
2. Calculate purge zone before test set (prevents look-ahead bias)
3. Calculate embargo zone after test set (prevents information leakage)
4. Remove overlapping training samples
5. Validate minimum sizes after purging

### Temporal Integrity
- Ensures all training samples are before test samples
- Applies purge before test set
- Applies embargo after test set
- Logs warnings for insufficient samples

### Validation
- `validate_no_leakage()`: Checks temporal integrity, purge application, embargo application
- Returns boolean indicating if leakage detected
- Logs detailed error messages for each violation

## Data Models

### Configuration Model
```python
@dataclass
class PurgedKFoldConfig:
    n_splits: int = 5
    purge_pct: float = 0.05
    embargo_pct: float = 0.02
    min_train_samples: int = 252
    min_test_samples: int = 20
    shuffle: bool = False
    random_state: Optional[int] = None
```

### Split Result Model
```python
@dataclass
class PurgedSplit:
    fold: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    purged_indices: np.ndarray
    embargo_indices: np.ndarray
    train_size_purged: int
    train_size_after_purge: int
    purge_pct_actual: float
    embargo_size: int
```

## API Contracts

### PurgedKFold.split()
```python
def split(
    X: Union[pd.DataFrame, pd.Series, np.ndarray],
    y: Optional[Union[pd.Series, np.ndarray]] = None,
    groups: Optional[Union[pd.Series, np.ndarray]] = None,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Returns list of (train_indices, test_indices) tuples."""
```

### PurgedKFold.validate_no_leakage()
```python
def validate_no_leakage(
    X: Union[pd.DataFrame, pd.Series, np.ndarray]
) -> bool:
    """Returns True if no leakage detected, False otherwise."""
```

## Error Handling

### Validation Errors
- `ValueError`: Insufficient samples for min_train_samples + min_test_samples
- `ValueError`: No valid folds generated
- `ValueError`: No splits available for validation

### Logging
- DEBUG: Split details (train/test/purged/embargo counts)
- INFO: Number of splits generated
- WARNING: Insufficient samples (skipping fold)
- ERROR: Temporal leakage detected

### Exception Handling
- All exceptions are specific and well-documented
- No bare except clauses
- Graceful handling of edge cases (empty arrays, boundary conditions)

## Performance Considerations

### Computational Complexity
- O(n) per fold for array operations
- Memory efficient: uses boolean masking instead of copying
- Vectorized operations with NumPy

### Optimization Notes
- Uses `np.isin()` for efficient membership testing
- Pre-calculates purge/embargo sizes once per split
- Avoids unnecessary array copies

### Scalability
- Handles large datasets efficiently
- Scales linearly with number of samples
- Memory usage: O(n) for indices

## Testing Strategy

### Unit Tests Required
- Test purge calculation with various percentages
- Test embargo calculation at boundaries
- Test temporal integrity validation
- Test minimum size validation
- Test edge cases (empty arrays, single sample)

### Integration Tests Required
- Test with real financial time series
- Test no leakage in generated splits
- Test sklearn compatibility

### Validation Tests
- Verify all training indices < all test indices
- Verify purge zone properly excluded
- Verify embargo zone properly excluded
- Test with various n_splits values

## Notes

### Type Hints
- Uses `Optional[T]` and `Union[T, U]` for Python 3.9+ compatibility
- Migration to `T | None` syntax planned for Python 3.10+

### Any Usage Justification
- Line 555: `estimator: Any` - Generic ML estimator interface
  - Accepts any sklearn-compatible estimator
  - Must have fit() and predict() methods
  - Documented in function docstring

### Compliance with BASE_RULES.md
- See ../../BASE_RULES.md for universal rules
- All P0 and P1 rules satisfied
- Type hint style is compatibility choice, not violation

---
*Audited on 2026-02-07T12:00:00Z - PASSED_WITH_NOTES*
*No critical violations found. Code is production-ready.*
