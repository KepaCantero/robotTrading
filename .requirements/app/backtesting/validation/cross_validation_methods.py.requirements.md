# Requirements: app/backtesting/validation/cross_validation_methods.py

## Source File Analysis
- **File Path**: `app/backtesting/validation/cross_validation_methods.py`
- **Lines of Code**: 852
- **Status**: Analysis Complete

## Purpose
Cross-validation methods for statistical learning following Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning" (ESL) Chapter 7.

Implements:
- K-Fold Cross-Validation
- Leave-One-Out Cross-Validation (LOOCV)
- Nested Cross-Validation for hyperparameter tuning
- Stratified K-Fold for classification
- Time Series Cross-Validation
- Custom CV with purging and embargo for financial data

## Dependencies

### Internal
- None (pure validation module)

### External
- `dataclasses`: Dataclass decorators for result models
- `datetime`: Timestamp handling
- `enum`: CVMethod enumeration
- `logging`: Structured logging
- `typing`: Type hints (Any, Callable, Dict, Generator, List, Optional, Tuple, Union)
- `numpy`: Numerical operations
- `pandas`: DataFrame/Series handling
- `sklearn.base`: BaseEstimator, clone
- `sklearn.model_selection`: KFold, LeaveOneOut, StratifiedKFold, GridSearchCV
- `sklearn.metrics`: check_scoring

## Classes/Functions

### class CVMethod(Enum)
**Purpose**: Enumeration of cross-validation method types
**Values**: KFOLD, LOOCV, STRATIFIED_KFOLD, TIME_SERIES, NESTED, PURGED

### @dataclass class CVResult
**Purpose**: Results from cross-validation with comprehensive statistics
**Fields**:
- `timestamp: datetime` - When CV was performed
- `method: CVMethod` - Method used
- `n_splits: int` - Number of folds
- `mean_score: float` - Mean score across folds
- `std_score: float` - Standard deviation
- `fold_scores: List[float]` - Individual fold scores
- `fit_times: List[float]` - Time per fold
- `score_times: List[float]` - Scoring time per fold
- `params: Dict[str, Any]` - Additional parameters
- Plus: min_score, max_score, score_range, confidence_interval, model_name, scorer_name

**Methods**:
- `def to_dict(self) -> Dict[str, Any]`: Convert to dictionary

### @dataclass class NestedCVResult
**Purpose**: Results from nested cross-validation
**Fields**:
- `timestamp: datetime`
- `outer_score: float` - Outer CV mean score
- `outer_std: float` - Outer CV std
- `best_params: Dict[str, Any]` - Best hyperparameters
- `best_inner_score: float` - Best inner CV score
- `n_outer_splits: int` - Number of outer folds
- `n_inner_splits: int` - Number of inner folds
- `outer_fold_scores: List[float]` - Individual outer fold scores
- `selected_params_per_fold: List[Dict[str, Any]]` - Params per fold

**Methods**:
- `def to_dict(self) -> Dict[str, Any]`: Convert to dictionary

### class KFoldCV
**Purpose**: K-Fold Cross-Validation (ESL Section 7.10)

**Methods**:
- `def __init__(self, n_splits: int = 5, shuffle: bool = False, random_state: Optional[int] = None)`: Initialize
- `def split(self, X: Union[pd.DataFrame, np.ndarray], y: Optional[Union[pd.Series, np.ndarray]] = None, groups: Optional[Union[pd.Series, np.ndarray]] = None) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]`: Generate splits
- `def get_n_splits(self) -> int`: Return number of splits

### class LeaveOneOutCV
**Purpose**: Leave-One-Out Cross-Validation (ESL Section 7.10)

**Methods**:
- `def __init__(self)`: Initialize
- `def split(self, X, y, groups) -> Generator`: Generate splits
- `def get_n_splits(self, X) -> int`: Return sample count

### class StratifiedKFoldCV
**Purpose**: Stratified K-Fold for classification with imbalanced classes

**Methods**:
- `def __init__(self, n_splits: int = 5, shuffle: bool = False, random_state: Optional[int] = None)`: Initialize
- `def split(self, X, y, groups) -> Generator`: Generate stratified splits
- `def get_n_splits(self) -> int`: Return number of splits

### class TimeSeriesSplitCV
**Purpose**: Time series CV respecting temporal ordering (BT-003)

**Methods**:
- `def __init__(self, n_splits: int = 5, max_train_size: Optional[int] = None, test_size: Optional[int] = None)`: Initialize
- `def split(self, X, y, groups) -> Generator`: Generate time-series splits
- `def get_n_splits(self) -> int`: Return number of splits

### class NestedCrossValidation
**Purpose**: Nested CV for unbiased hyperparameter tuning

**Methods**:
- `def __init__(self, estimator: BaseEstimator, param_grid: Dict[str, List[Any]], outer_cv: Any = None, inner_cv: Any = None, scoring: Optional[Union[str, Callable]] = None, n_jobs: int = 1)`: Initialize
- `def fit(self, X, y) -> NestedCVResult`: Perform nested CV
- `def _split_data(self, X, train_idx, test_idx) -> Tuple[Any, Any]`: Split feature matrix
- `def _split_target(self, y, train_idx, test_idx) -> Tuple[Any, Any]`: Split target vector

### class CrossValidation
**Purpose**: Unified interface for all CV methods

**Methods**:
- `def __init__(self, method: CVMethod = CVMethod.KFOLD, n_splits: int = 5, shuffle: bool = False, random_state: Optional[int] = None, **kwargs)`: Initialize
- `def split(self, X, y, groups) -> Generator`: Generate splits
- `def cross_validate(self, estimator, X, y, scoring, return_estimator) -> CVResult`: Perform CV
- `def _split_data(self, X, train_idx, test_idx)`: Split feature matrix
- `def _split_target(self, y, train_idx, test_idx)`: Split target vector
- `def get_n_splits(self) -> int`: Return number of splits

### def cross_validate(...)
**Purpose**: Convenience function for cross-validation
**Parameters**:
- `estimator: BaseEstimator` - ML estimator
- `X: Union[pd.DataFrame, np.ndarray]` - Feature matrix
- `y: Union[pd.Series, np.ndarray]` - Target vector
- `method: str` - CV method ('kfold', 'loocv', 'stratified', 'time_series')
- `n_splits: int` - Number of splits
- `scoring: Optional[Union[str, Callable]]` - Scoring metric
**Returns**: `CVResult`

### def nested_cross_validate(...)
**Purpose**: Convenience function for nested cross-validation
**Parameters**:
- `estimator: BaseEstimator` - Base estimator
- `X: Union[pd.DataFrame, np.ndarray]` - Feature matrix
- `y: Union[pd.Series, np.ndarray]` - Target vector
- `param_grid: Dict[str, List[Any]]` - Parameter grid
- `outer_splits: int` - Number of outer folds
- `inner_splits: int` - Number of inner folds
- `scoring: Optional[Union[str, Callable]]` - Scoring metric
- `n_jobs: int` - Number of parallel jobs
**Returns**: `NestedCVResult`

## Business Logic

1. **K-Fold CV**: Divides data into K parts, uses each as test set once
2. **LOOCV**: Each observation is test set once (n models trained)
3. **Stratified K-Fold**: Preserves class distribution in each fold
4. **Time Series CV**: Respects temporal ordering to prevent look-ahead bias (BT-003)
5. **Nested CV**: Inner loop for hyperparameter tuning, outer loop for error estimation

## Critical Rules (from BASE_RULES.md)

### Type Hints (TYP-001, TYP-002)
- ✅ All functions have complete type hints
- ✅ Uses modern syntax: `Optional[T]`, `Union[X, Y]`, `Tuple[K, V]`
- ✅ `from __future__ import annotations` for forward references

### Structured Logging (LOG-001, LOG-003)
- ✅ Uses logging module with appropriate levels
- ✅ Info logs for progress tracking
- Note: Could use structured logging with correlation IDs (LOG-002)

### Error Handling (CC-006, ERR-001)
- ✅ ValueError raised for invalid `n_splits`
- ✅ ValueError raised for missing `y` in stratified K-fold
- ✅ ValueError raised for unknown CV method

### Trading-Specific Rules
- ✅ BT-003: TimeSeriesSplitCV prevents look-ahead bias
- ✅ BT-005: Multiple periods support via n_splits parameter

### Clean Code (CC-001, CC-003, CC-005)
- ✅ Descriptive names: `KFoldCV`, `StratifiedKFoldCV`, `NestedCrossValidation`
- ✅ Simple, clear implementation
- ✅ Early returns in generator patterns

### SOLID Principles
- ✅ SOL-001: Each class has single responsibility (one CV method per class)
- ✅ SOL-004: Small, focused interfaces via Enum and dataclasses
- ✅ SOL-005: CrossValidation depends on abstraction (CVMethod Enum)

### Type Safety
- ✅ TYP-001: 100% type coverage
- ✅ TYP-003: `Any` types documented (e.g., `outer_cv: Any` for sklearn CV splitters)

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T07:01:00Z |
| **Audit Status** | PASSED |
| **Violations** | 0 |
| **Notes** | Clean implementation of ESL cross-validation methods. All BASE_RULES critical requirements satisfied. |

## Notes
- File implements academic-standard cross-validation methods
- TimeSeriesSplitCV is critical for financial data (BT-003 compliance)
- NestedCV prevents information leakage in hyperparameter tuning
- All `Any` types are for sklearn compatibility (acceptable)

---
*Regenerated from code analysis on 2026-02-07T07:01:00Z*
