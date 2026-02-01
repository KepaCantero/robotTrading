# triple_barrier.py

## Purpose
Implements López de Prado's Triple Barrier Method for financial ML labeling, using horizontal barriers (profit taking/stop loss) and vertical barriers (time limit) to generate realistic trading labels that account for volatility and risk-reward ratios.

---

## Type Definitions / Data Classes

### TripleBarrierConfig Class/DataClass
```python
@dataclass
class TripleBarrierConfig:
    upper_barrier_pct: float = 0.02        # REQUIRED - Profit target (positive, e.g., 0.02 for 2%)
    lower_barrier_pct: float = -0.01       # REQUIRED - Stop loss (negative, e.g., -0.01 for -1%)
    vertical_barrier_days: int = 5        # REQUIRED - Time horizon in days/bars > 0
    min_return: float = 0.0                # OPTIONAL - Minimum return threshold
    vol_scale: float = 1.5                 # OPTIONAL - Volatility scaling factor > 0
    vol_window: int = 20                   # OPTIONAL - Volatility calculation window > 0
    numba_enabled: bool = True             # OPTIONAL - Enable Numba JIT acceleration
    metadata: Dict[str, Any]               # OPTIONAL - Additional metadata
```

**Validation Rules:**
- upper_barrier_pct must be > 0
- lower_barrier_pct must be < 0
- vertical_barrier_days must be > 0
- abs(lower_barrier_pct) > upper_barrier_pct triggers warning (poor risk-reward)
- vol_scale must be > 0
- vol_window must be > 0

---

## Function Signatures (Contracts)

### `get_barrier_labels(prices: np.ndarray, events: np.ndarray, upper_barrier: float, lower_barrier: float, vertical_barrier: int) -> np.ndarray`
**Pre:** prices array length > max(events) + vertical_barrier, events are valid indices
**Post:** Returns labels array: 1 (upper hit), -1 (lower hit), 0 (vertical hit)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure JIT-compiled function)

### `get_barrier_labels_with_timing(prices: np.ndarray, events: np.ndarray, upper_barrier: float, lower_barrier: float, vertical_barrier: int) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** prices array length > max(events) + vertical_barrier, events are valid indices
**Post:** Returns (labels, bars_to_barrier) tuple with timing information
**Raises:** None
**Retry:** No
**Side Effects:** None (pure JIT-compiled function)

### `calculate_dynamic_barriers(prices: pd.Series, events: pd.Series, config: TripleBarrierConfig, vol_scaling: bool = True) -> Tuple[pd.Series, pd.Series]`
**Pre:** prices not empty, events not empty, prices has DatetimeIndex or RangeIndex
**Post:** Returns (upper_barriers, lower_barriers) series aligned with events
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_vertical_barriers(events: pd.Series, prices: pd.Series, num_days: int) -> pd.Series`
**Pre:** events not empty, prices has DatetimeIndex, num_days > 0
**Post:** Returns series of vertical barrier timestamps
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TripleBarrierLabeler.__init__(config: Optional[TripleBarrierConfig] = None) -> None`
**Pre:** config is None or valid TripleBarrierConfig
**Post:** Instance initialized with default config if None
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `TripleBarrierLabeler.fit(prices: pd.Series, events: pd.Series, vol_scaling: bool = True) -> TripleBarrierLabeler`
**Pre:** prices and events not empty, events aligned with prices index
**Post:** Sets prices, events, labels_, barrier_info_; returns self
**Raises:** ValueError if event indices out of bounds
**Retry:** No
**Side Effects:** Converts events to indices, calculates barriers, generates labels

### `TripleBarrierLabeler.transform(prices: pd.Series, events: pd.Series) -> pd.DataFrame`
**Pre:** Labeler is fitted, prices and events valid
**Post:** Returns DataFrame with labels
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** Calls fit internally

### `TripleBarrierLabeler.fit_transform(prices: pd.Series, events: pd.Series, vol_scaling: bool = True) -> pd.DataFrame`
**Pre:** prices and events not empty
**Post:** Returns labels DataFrame
**Raises:** ValueError on validation failures
**Retry:** No
**Side Effects:** Fits and returns labels

### `TripleBarrierLabeler.get_label_distribution() -> pd.Series`
**Pre:** Labeler is fitted (labels_ not None)
**Post:** Returns value counts of labels
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None

### `TripleBarrierLabeler.get_average_holding_period() -> Dict[int, float]`
**Pre:** Labeler is fitted
**Post:** Returns dict mapping label to average bars_to_barrier
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None

### `TripleBarrierLabeler.get_bin_labels(min_return: float = 0.0) -> np.ndarray`
**Pre:** Labeler is fitted
**Post:** Returns binary labels (1 for profit, 0 for loss)
**Raises:** ValueError if not fitted
**Retry:** No
**Side Effects:** None

### `plot_triple_barrier(prices: pd.Series, event_idx: int, upper_barrier: float, lower_barrier: float, vertical_barrier: int, label: int, ax: Optional[plt.Axes] = None) -> Optional[plt.Axes]`
**Pre:** prices length > event_idx + vertical_barrier, label in {-1, 0, 1}
**Post:** Returns matplotlib axis or None if matplotlib unavailable
**Raises:** None (warns if matplotlib missing)
**Retry:** No
**Side Effects:** Creates plot on ax or new figure

### `meta_labeling(primary_labels: np.ndarray, features: np.ndarray, actual_returns: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns binary meta-labels (1 if signal correct, 0 otherwise)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sample_weights(events: pd.Series, labels: pd.DataFrame, max_holding_period: int) -> pd.Series`
**Pre:** events and labels have same length, labels has 'bars_to_barrier' column
**Post:** Returns weights normalized to sum to n_samples
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sample_weights_uniqueness(events: pd.Series, labels: pd.DataFrame, price_series: pd.Series, num_threads: int = 1) -> pd.Series`
**Pre:** All inputs have compatible lengths, labels has 'bars_to_barrier'
**Post:** Returns uniqueness-based weights
**Raises:** None
**Retry:** No
**Side Effects:** None (O(n²) algorithm, could be slow for large datasets)

### `calculate_sample_weights_td(events: pd.Series, labels: pd.DataFrame, price_series: pd.Series) -> pd.Series`
**Pre:** All inputs valid, labels has 'bars_to_barrier'
**Post:** Returns timedelta-based uniqueness weights
**Raises:** None (handles KeyError/AttributeError gracefully)
**Retry:** No
**Side Effects:** None

### `purged_cv_split(n_samples: int, n_folds: int = 5, embargo_pct: float = 0.01) -> List[Tuple[np.ndarray, np.ndarray]]`
**Pre:** n_samples > 0, n_folds > 1, embargo_pct in [0,1)
**Post:** Returns list of (train_idx, test_idx) tuples with purged splits
**Raises:** None
**Retry:** No
**Side Effects:** None

### `triple_barrier_method(prices: pd.Series, events: pd.Series, upper_barrier_pct: float = 0.02, lower_barrier_pct: float = -0.01, vertical_barrier_days: int = 5, vol_scaling: bool = True, vol_window: int = 20, vol_scale: float = 1.5) -> pd.DataFrame`
**Pre:** prices and events not empty, valid percentages
**Post:** Returns DataFrame with labels and metadata
**Raises:** ValueError on invalid parameters
**Retry:** No
**Side Effects:** Creates TripleBarrierLabeler and fits

---

## Acceptance Criteria
- [ ] All public functions have type hints (TYP-001)
- [ ] TripleBarrierConfig validates all constraints in __post_init__
- [ ] Numba JIT functions marked with @jit(nopython=True, cache=True)
- [ ] Barrier labels are exactly -1, 0, or 1
- [ ] Upper barrier checked before lower barrier (profit taking priority)
- [ ] Vertical barrier label (0) when neither horizontal barrier hit
- [ ] Dynamic barriers scale with volatility when vol_scaling=True
- [ ] Event datetime to index conversion handles missing timestamps
- [ ] get_bin_labels converts -1 to 0, keeps 1 as 1
- [ ] Sample weights normalized to sum to n_samples
- [ ] Uniqueness calculation prevents double-counting overlapping samples
- [ ] Purged CV removes overlapping train/test samples
- [ ] Warning issued when stop loss > profit target
- [ ] Matplotlib import failure handled gracefully (HAS_MATPLOTLIB flag)
- [ ] ARCH import failure handled gracefully (HAS_ARCH flag)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ⚠️ NOT APPLIED - Some functions lack hints |
| PERF-005 | BASE_RULES.md | Use Numba JIT for hot paths | ✅ OK - Core labeling functions use @jit |
| ARCH-004 | BASE_RULES.md | Small functions | ❌ GAP - calculate_sample_weights_uniqueness is 90 lines |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ PARTIAL - Some ValueError handling generic |
| LOG-001 | BASE_RULES.md | Structured logging | ⚠️ NOT APPLIED - No logging in current implementation |
| LOG-004 | BASE_RULES.md | Error logging | ⚠️ NOT APPLIED - Uses warnings instead of logging |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Separate functions for each concern |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Barriers prevent future leakage |
| TRD-004 | BASE_RULES.md | Audit trail | ⚠️ NOT APPLIED - No audit logging |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, numba (required), matplotlib (optional), arch (optional)
- **Internal:** None (standalone module)

---

## Required Tests
- **tests/unit/backtesting/labeling/test_triple_barrier.py:**
  - Test TripleBarrierConfig validation for all parameters
  - Test get_barrier_labels returns correct -1, 0, 1 values
  - Test get_barrier_labels_with_timing returns correct bars_to_barrier
  - Test upper barrier checked before lower barrier
  - Test vertical barrier when neither horizontal hit
  - Test calculate_dynamic_barriers with vol_scaling=True and False
  - Test get_vertical_barriers calculates correct timestamps
  - Test TripleBarrierLabeler.fit with datetime and integer events
  - Test TripleBarrierLabeler raises ValueError on out-of-bounds events
  - Test get_label_distribution returns correct counts
  - Test get_average_holding_period groups by label correctly
  - Test get_bin_labels converts -1 to 0
  - Test calculate_sample_weights normalizes correctly
  - Test calculate_sample_weights_uniqueness handles overlaps
  - Test purged_cv_split generates non-overlapping splits
  - Test triple_barrier_method convenience function
  - Test plot_triple_barrier handles missing matplotlib
  - Test warning when abs(lower) > upper
  - Test edge cases: single event, event at boundary

---

## Notes
Core implementation of López de Prado's triple barrier method. Numba JIT acceleration provides 10-100x speedup for label generation. The uniqueness weighting is critical for preventing overfitting on overlapping samples.
