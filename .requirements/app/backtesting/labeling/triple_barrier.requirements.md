# triple_barrier.py

## Purpose
Triple Barrier Method for Financial ML Labeling - Implements López de Prado's triple barrier labeling methodology with dynamic volatility-adjusted barriers, Numba acceleration, and sample uniqueness weighting.

---

## Type Definitions / Data Classes

### TripleBarrierConfig
```python
@dataclass
class TripleBarrierConfig:
    """
    Configuration for Triple Barrier labeling.

    Attributes:
        upper_barrier_pct: Profit target as percentage (e.g., 0.02 for 2%)
        lower_barrier_pct: Stop loss as percentage (e.g., -0.01 for -1%)
        vertical_barrier_days: Time horizon in days/bars
        min_return: Minimum return threshold for labeling
        vol_scale: Scaling factor for volatility-based barriers
        vol_window: Window for volatility calculation
        numba_enabled: Enable Numba acceleration
        metadata: Additional metadata dictionary
    """
    upper_barrier_pct: float = 0.02
    lower_barrier_pct: float = -0.01
    vertical_barrier_days: int = 5
    min_return: float = 0.0
    vol_scale: float = 1.5
    vol_window: int = 20
    numba_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Validation in __post_init__:**
- upper_barrier_pct must be positive
- lower_barrier_pct must be negative
- vertical_barrier_days must be positive
- Warns if stop loss is larger than profit target

### TripleBarrierLabeler
```python
class TripleBarrierLabeler:
    """
    Triple Barrier Method labeler for financial ML.

    Implements complete labeling methodology from López de Prado:
    - Dynamic barrier calculation
    - Volatility-adjusted barriers
    - Label generation with timing information
    - Visualization and analysis tools
    """
```

---

## Function Signatures (Contracts)

### `get_barrier_labels(
    prices: np.ndarray,
    events: np.ndarray,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
) -> np.ndarray`
**Pre:** prices is non-empty; events are valid indices; barriers > 0; vertical_barrier > 0
**Post:** Returns labels array (1: upper, -1: lower, 0: vertical)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)
**Accelerated:** Numba JIT (@jit(nopython=True, cache=True))

**Labels:**
- 1: Upper barrier hit (profit target reached)
- -1: Lower barrier hit (stop loss triggered)
- 0: Vertical barrier hit (time expired)

### `get_barrier_labels_with_timing(
    prices: np.ndarray,
    events: np.ndarray,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** prices is non-empty; events are valid indices; barriers > 0
**Post:** Returns (labels array, bars_to_barrier array)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)
**Accelerated:** Numba JIT (@jit(nopython=True, cache=True))

### `calculate_dynamic_barriers(
    prices: pd.Series,
    events: pd.Series,
    config: TripleBarrierConfig,
    vol_scaling: bool = True,
) -> Tuple[pd.Series, pd.Series]`
**Pre:** prices is non-empty Series with datetime index; events non-empty
**Post:** Returns (upper_barriers, lower_barriers) Series aligned with events
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Volatility Scaling:**
- High volatility → Wider barriers
- Low volatility → Narrower barriers
- Formula: `barrier × vol_scale × (event_vol / median_vol)`

### `get_vertical_barriers(
    events: pd.Series,
    prices: pd.Series,
    num_days: int
) -> pd.Series`
**Pre:** events non-empty; prices has datetime index; num_days > 0
**Post:** Returns vertical barrier timestamps aligned with events
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `event_time + pd.Timedelta(days=num_days)`

### `TripleBarrierLabeler.__init__(config: Optional[TripleBarrierConfig] = None) -> None`
**Pre:** None
**Post:** Labeler initialized with config (or defaults)
**Raises:** None
**Retry:** No
**Side Effects:** Initializes state variables

### `TripleBarrierLabeler.fit(
    prices: pd.Series,
    events: pd.Series,
    vol_scaling: bool = True
) -> TripleBarrierLabeler`
**Pre:** prices is non-empty Series with datetime index; events non-empty
**Post:** Returns self with labels_ populated
**Raises:** ValueError if event_idx out of bounds
**Retry:** No
**Side Effects:** Converts datetime events to indices, calculates barriers, generates labels

**Process:**
1. Convert datetime events to positional indices
2. Calculate dynamic barriers (with volatility scaling)
3. Generate labels for each event
4. Store results in labels_ DataFrame

### `TripleBarrierLabeler.transform(prices: pd.Series, events: pd.Series) -> pd.DataFrame`
**Pre:** Labeler already fitted; prices and events valid
**Post:** Returns DataFrame with labels
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** Calls fit() and returns labels_

### `TripleBarrierLabeler.fit_transform(
    prices: pd.Series,
    events: pd.Series,
    vol_scaling: bool = True
) -> pd.DataFrame`
**Pre:** prices is non-empty Series with datetime index; events non-empty
**Post:** Returns DataFrame with labels
**Raises:** ValueError if event_idx out of bounds
**Retry:** No
**Side Effects:** Fits and returns labels_

### `TripleBarrierLabeler.get_label_distribution() -> pd.Series`
**Pre:** Labeler already fitted
**Post:** Returns value counts of labels
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None (query)

### `TripleBarrierLabeler.get_average_holding_period() -> Dict[int, float]`
**Pre:** Labeler already fitted
**Post:** Returns dict mapping label to average bars_to_barrier
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None (query)

### `TripleBarrierLabeler.get_bin_labels(min_return: float = 0.0) -> np.ndarray`
**Pre:** Labeler already fitted
**Post:** Returns binary labels (1: profit, 0: loss)
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None (query)

**Conversion:**
- Label 1 (upper) → 1 (profit)
- Label -1 (lower) → 0 (loss)
- Label 0 (vertical) → 1 (default, can be refined)

### `plot_triple_barrier(
    prices: pd.Series,
    event_idx: int,
    upper_barrier: float,
    lower_barrier: float,
    vertical_barrier: int,
    label: int,
    ax: Optional[plt.Axes] = None,
) -> Optional[plt.Axes]`
**Pre:** prices non-empty; event_idx valid; barriers valid
**Post:** Returns matplotlib axis or None if matplotlib unavailable
**Raises:** None
**Retry:** No
**Side Effects:** Creates visualization plot

**Visualization Elements:**
- Price path (blue line)
- Entry point (green circle)
- Upper barrier (green dashed line)
- Lower barrier (red dashed line)
- Vertical barrier (orange dashed line)
- Barrier hit highlighted

### `meta_labeling(
    primary_labels: np.ndarray,
    features: np.ndarray,
    actual_returns: np.ndarray,
) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns binary meta-labels (1: signal correct, 0: signal wrong)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Meta-Labeling Purpose:** Determines whether primary signal was correct for bet sizing

### `calculate_sample_weights(
    events: pd.Series,
    labels: pd.DataFrame,
    max_holding_period: int
) -> pd.Series`
**Pre:** events and labels have same index
**Post:** Returns sample weights (sum to n_samples)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `weight = 1 / (1 + overlaps)` (normalized)
**Purpose:** Down-weight overlapping samples to prevent overfitting

### `calculate_sample_weights_uniqueness(
    events: pd.Series,
    labels: pd.DataFrame,
    price_series: pd.Series,
    num_threads: int = 1
) -> pd.Series`
**Pre:** events, labels, price_series have compatible indices
**Post:** Returns sample weights based on average uniqueness
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `uniqueness = 1 / (1 + concurrent_samples)` (normalized)
**Reference:** López de Prado, Chapter 4, Section 4.5

### `calculate_sample_weights_td(
    events: pd.Series,
    labels: pd.DataFrame,
    price_series: pd.Series
) -> pd.Series`
**Pre:** events, labels, price_series have compatible indices
**Post:** Returns sample weights using timedelta-based uniqueness
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `purged_cv_split(
    n_samples: int,
    n_folds: int = 5,
    embargo_pct: float = 0.01,
) -> List[Tuple[np.ndarray, np.ndarray]]`
**Pre:** n_samples > 0; n_folds >= 2; embargo_pct in [0, 1]
**Post:** Returns list of (train_indices, test_indices) tuples
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Purpose:** Prevents data leakage by removing samples near train/test boundaries

### `triple_barrier_method(
    prices: pd.Series,
    events: pd.Series,
    upper_barrier_pct: float = 0.02,
    lower_barrier_pct: float = -0.01,
    vertical_barrier_days: int = 5,
    vol_scaling: bool = True,
    vol_window: int = 20,
    vol_scale: float = 1.5,
) -> pd.DataFrame`
**Pre:** prices is non-empty Series with datetime index; events non-empty
**Post:** Returns DataFrame with labels and metadata
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** Creates config, labeler, runs fit_transform

**Convenience Function:** Simplified interface for quick labeling

---

## Acceptance Criteria
- [ ] **AC-001:** TripleBarrierConfig validates parameters in __post_init__
- [ ] **AC-002:** get_barrier_labels() returns 1, -1, or 0
- [ ] **AC-003:** get_barrier_labels() is Numba-accelerated
- [ ] **AC-004:** calculate_dynamic_barriers() scales with volatility
- [ ] **AC-005:** TripleBarrierLabeler.fit() converts datetime to indices
- [ ] **AC-006:** TripleBarrierLabeler.labels_ has all required columns
- [ ] **AC-007:** get_label_distribution() returns value counts
- [ ] **AC-008:** get_bin_labels() converts to binary
- [ ] **AC-009:** meta_labeling() determines signal correctness
- [ ] **AC-010:** calculate_sample_weights() handles overlaps
- [ ] **AC-011:** calculate_sample_weights() normalizes to sum to n_samples
- [ ] **AC-012:** purged_cv_split() prevents data leakage
- [ ] **AC-013:** triple_barrier_method() convenience function works
- [ ] **AC-014:** NumPy 2.0 compatible (no np aliases)
- [ ] **AC-015:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Triple Barrier Method):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Triple Barrier Method | López de Prado (2018) | Chapter 3 implementation | ✅ OK - Complete |
| Volatility-adjusted barriers | López de Prado (2018) | Dynamic barrier widths | ✅ OK - calculate_dynamic_barriers() |
| Numba acceleration | Performance | JIT compilation | ✅ OK - @jit decorators |
| Sample uniqueness | López de Prado (2018) | Chapter 4 weighting | ✅ OK - calculate_sample_weights*() |
| Meta-labeling | López de Prado (2018) | Position sizing | ✅ OK - meta_labeling() |
| Purged CV | López de Prado (2018) | Prevent leakage | ✅ OK - purged_cv_split() |
| Horizontal barriers | Trading | Profit/stop levels | ✅ OK - upper/lower barriers |
| Vertical barrier | Trading | Time limit | ✅ OK - vertical_barrier_days |
| Label encoding | ML | 3-class (1, -1, 0) | ✅ OK - get_barrier_labels() |
| Timing information | ML | Bars to barrier | ✅ OK - get_barrier_labels_with_timing() |
| Scikit-learn API | ML standard | fit/transform pattern | ✅ OK - TripleBarrierLabeler |
| Optional dependencies | Clean code | Graceful degradation | ✅ OK - HAS_MATPLOTLIB |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and López de Prado (2018) "Advances in Financial Machine Learning" for the triple barrier method.

---

## Dependencies
- **External:** `numpy`, `pandas`, `numba` (required), `arch` (optional, for GARCH), `matplotlib` (optional, for plotting)
- **Internal:** None (infrastructure layer)

**Optional Dependencies:**
- `matplotlib`: For visualization (HAS_MATPLOTLIB flag)
- `arch`: For GARCH volatility modeling (HAS_ARCH flag)

---

## Required Tests
- **test_triple_barrier.py:**
  - `test_triple_barrier_config_validation()` - Validates params
  - `test_triple_barrier_config_warns_stop_loss()` - Warns if stop > target
  - `test_get_barrier_labels_upper()` - Returns 1 for upper hit
  - `test_get_barrier_labels_lower()` - Returns -1 for lower hit
  - `test_get_barrier_labels_vertical()` - Returns 0 for time expiry
  - `test_get_barrier_labels_with_timing()` - Returns labels + bars
  - `test_calculate_dynamic_barriers_no_scaling()` - Fixed barriers
  - `test_calculate_dynamic_barriers_with_scaling()` - Volatility-adjusted
  - `test_get_vertical_barriers()` - Correct timestamps
  - `test_triple_barrier_labeler_fit()` - Fits and stores labels_
  - `test_triple_barrier_labeler_convert_datetime()` - Datetime to indices
  - `test_triple_barrier_labeler_fit_transform()` - One-step fit/transform
  - `test_get_label_distribution()` - Value counts
  - `test_get_average_holding_period()` - Average bars per label
  - `test_get_bin_labels()` - Binary conversion
  - `test_meta_labeling()` - Signal correctness
  - `test_calculate_sample_weights()` - Overlap handling
  - `test_calculate_sample_weights_normalize()` - Sum to n_samples
  - `test_calculate_sample_weights_uniqueness()` - Average uniqueness
  - `test_purged_cv_split()` - No data leakage
  - `test_triple_barrier_method()` - Convenience function
  - `test_numba_acceleration()` - JIT compilation works

---

## Notes
- **Critical:** Triple Barrier Method is the GOLD STANDARD for financial ML labeling (López de Prado, 2018)
- **López de Prado Reference:** "Advances in Financial Machine Learning" (2018) - Chapter 3 (Triple Barrier) and Chapter 4 (Sample Weights)
- **Key Innovation:** Addresses shortcomings of fixed-time horizon labeling by using:
  1. **Horizontal barriers:** Profit taking and stop loss levels
  2. **Vertical barrier:** Time limit (prevents indefinite holding)
  3. **First-hit labeling:** Labels based on which barrier is hit first
- **Label Meanings:**
  - **1 (upper):** Profit target hit - trade successful
  - **-1 (lower):** Stop loss hit - trade failed
  - **0 (vertical):** Time expired - trade neither won nor lost
- **Volatility Scaling:**
  - High volatility → Wider barriers (avoids premature stops)
  - Low volatility → Narrower barriers (tighter risk control)
  - Formula: `barrier × vol_scale × (event_vol / median_vol)`
- **Meta-Labeling:**
  - Primary model: Predicts direction (buy/sell)
  - Meta model: Predicts whether primary signal is correct
  - Used for bet sizing, not direction
- **Sample Uniqueness:**
  - Overlapping samples are not independent
  - Must be down-weighted to prevent overfitting
  - Formula: `weight = 1 / (1 + concurrent_samples)`
- **Purged Cross-Validation:**
  - Removes samples near train/test boundaries
  - Prevents data leakage from future to past
  - Critical for time series ML
- **Numba Acceleration:**
  - Core labeling functions JIT-compiled
  - 10-100x speedup for large datasets
  - Cache enabled for faster subsequent runs
- **Visualization:**
  - Optional matplotlib dependency
  - Shows price path, entry, barriers, and outcome
  - Useful for debugging and analysis
- **Production Rule:** Always use triple barrier labeling for financial ML, never fixed-time horizon

---

**File Reference:** `app/backtesting/labeling/triple_barrier.py`
**Last Audited:** 2026-02-01
