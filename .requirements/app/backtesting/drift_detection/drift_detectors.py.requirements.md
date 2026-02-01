# drift_detectors.py

## Purpose
Statistical methods for detecting concept and data drift in ML models and financial time series using KS test, PSI, ADWIN, and MMD algorithms.

---

## Type Definitions / Data Classes

### DriftType Enum
```python
class DriftType(Enum):
    CONCEPT_DRIFT = "concept_drift"      # Relationship between features and target changed
    FEATURE_DRIFT = "feature_drift"      # Feature distribution changed
    PREDICTION_DRIFT = "prediction_drift" # Prediction distribution changed
    OVERFITTING = "overfitting"          # Model overfitting detected
```

### DriftResult DataClass
```python
@dataclass
class DriftResult:
    drift_detected: bool                    # REQUIRED - Whether drift was detected
    drift_type: DriftType                   # REQUIRED - Type of drift detected
    p_value: Optional[float] = None         # OPTIONAL - Statistical p-value (KS/MMD tests)
    statistic: Optional[float] = None       # OPTIONAL - Test statistic value
    threshold: Optional[float] = None       # OPTIONAL - Detection threshold used
    confidence: Optional[float] = None      # OPTIONAL - Confidence level (1 - p_value)
    timestamp: datetime = field(default_factory=datetime.utcnow)  # AUTO - Detection timestamp
    details: Dict[str, Any] = field(default_factory=dict)  # OPTIONAL - Additional context
```

**Validation Rules:**
- `drift_detected` must be boolean
- `p_value` must be in range [0, 1] if provided
- `confidence` must be in range [0, 1] if provided
- `timestamp` auto-generated but can be overridden
- `details` can contain any detector-specific metadata

---

## Function Signatures (Contracts)

### `KSDriftDetector.__init__(significance_level: float = 0.05)`
**Pre:** significance_level in (0, 1)
**Post:** detector initialized with threshold
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `KSDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are non-empty numeric arrays
**Post:** DriftResult with KS test p-value and detection status
**Raises:** ValueError if arrays are empty or invalid
**Retry:** ❌ No
**Side Effects:** Logs drift detection event with structured logging

### `PSIDriftDetector.__init__(threshold: float = 0.25, n_bins: int = 10)`
**Pre:** threshold > 0, n_bins > 0
**Post:** detector initialized with PSI parameters
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `PSIDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are non-empty numeric arrays
**Post:** DriftResult with PSI value and detection status
**Raises:** ValueError if arrays are empty
**Retry:** ❌ No
**Side Effects:** Logs drift detection event with structured logging

### `PSIDriftDetector._calculate_psi(reference: np.ndarray, current: np.ndarray) -> float`
**Pre:** reference and current are non-empty arrays
**Post:** PSI value >= 0
**Raises:** ValueError on invalid input
**Retry:** ❌ No
**Side Effects:** None

### `ADWINDriftDetector.__init__(delta: float = 0.002, max_window_size: int = 1000)`
**Pre:** delta in (0, 1), max_window_size > 0
**Post:** detector initialized with adaptive window
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ADWINDriftDetector.detect(new_value: float) -> Optional[DriftResult]`
**Pre:** new_value is numeric
**Post:** DriftResult if change point detected, None otherwise
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Modifies internal window state (appends new_value)

### `ADWINDriftDetector._find_change_point() -> Optional[int]`
**Pre:** window has sufficient data
**Post:** Change point index or None
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `MMDDriftDetector.__init__(threshold: float = 0.1, gamma: float = 1.0)`
**Pre:** threshold > 0, gamma > 0
**Post:** detector initialized with MMD parameters
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `MMDDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are non-empty arrays
**Post:** DriftResult with MMD value and detection status
**Raises:** ValueError on invalid input
**Retry:** ❌ No
**Side Effects:** Logs drift detection event

### `MMDDriftDetector._calculate_mmd(reference: np.ndarray, current: np.ndarray) -> float`
**Pre:** reference and current are non-empty arrays
**Post:** MMD value >= 0
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] KS detector correctly identifies distribution differences using scipy.stats.ks_2samp
- [ ] PSI detector correctly calculates Population Stability Index
- [ ] ADWIN detector maintains sliding window and detects change points
- [ ] MMD detector correctly calculates Maximum Mean Discrepancy
- [ ] All detectors log structured events on drift detection
- [ ] All detectors handle edge cases (empty arrays, NaN values, zero variance)
- [ ] DriftResult objects contain all required fields with valid values
- [ ] Type hints present on all public methods
- [ ] All mathematical operations are numerically stable (no division by zero)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK - All functions have type hints |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK - Uses logger.info with extra dict |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Logs info/warning, no error logging |
| TRD-001 | BASE_RULES.md | Validate statistical inputs | ✅ OK - Validates array inputs |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Handles ValueError, TypeError |
| ARCH-004 | BASE_RULES.md | Small functions < 20 lines | ⚠️ PARTIAL - Some methods exceed 20 lines |
| PERF-005 | BASE_RULES.md | Consider Numba for hot paths | ❌ GAP - MMD calculation has nested loops, could use Numba |

**GAP Analysis:**
1. **PERF-005 (MMD Performance):** The `_calculate_mmd` method has nested loops computing RBF kernel matrices. For large arrays, this is O(n² + m² + n*m). Could benefit from Numba JIT compilation.
   - Impact: Medium (affects large datasets)
   - Recommendation: Add `@numba.jit(nopython=True)` to `_calculate_mmd` and `_rbf_kernel`

2. **LOG-004 (Error Logging):** Missing error logging in exception handlers. Errors are logged but not with full stack traces.
   - Impact: Low (currently logs error messages)
   - Recommendation: Add `logger.error(..., exc_info=True)` for better debugging

---

## Dependencies
- **External:**
  - numpy (array operations, statistical calculations)
  - scipy.stats.ks_2samp (Kolmogorov-Smirnov test)
  - logging (structured logging)
  - dataclasses (DriftResult)
  - enum (DriftType)
  - datetime (timestamps)
  - typing (type hints)
- **Internal:** None (pure utility module)

---

## Required Tests
- **tests/unit/backtesting/test_drift_detectors.py:**
  - Test KS detector with identical distributions (no drift)
  - Test KS detector with different distributions (drift detected)
  - Test PSI detector with various threshold values
  - Test PSI bin edge calculation edge cases
  - Test ADWIN detector window accumulation
  - Test ADWIN detector change point detection
  - Test ADWIN detector window reset after drift
  - Test MMD detector with same distributions
  - Test MMD detector with different distributions
  - Test MMD detector numerical stability (zero variance, NaN)
  - Test DriftResult object validation
  - Test logging output format and content
  - Test edge cases: empty arrays, single element arrays, all NaN arrays

---

## Notes
- This module implements cross-cutting concerns (drift detection) and is intentionally framework-agnostic
- Design note DOM-001: DriftResult is a plain dataclass, not a domain Value Object, as drift detection is a utility concern
- ADWIN maintains mutable state (window) - not thread-safe for concurrent use
- MMD calculation is computationally expensive for large datasets - consider subsampling or approximation algorithms
