# drift_detectors.py

## Purpose
Implements statistical methods for detecting concept and data drift in trading strategies using KS test, PSI, ADWIN streaming, and MMD algorithms.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### DriftType Enum
```python
class DriftType(Enum):
    CONCEPT_DRIFT = "concept_drift"      # Concept/target distribution shifted
    FEATURE_DRIFT = "feature_drift"      # Feature distribution shifted
    PREDICTION_DRIFT = "prediction_drift" # Prediction distribution shifted
    OVERFITTING = "overfitting"          # Model overfitting detected
```

**Validation Rules:**
- Must be one of the four defined types

### DriftResult DataClass
```python
@dataclass
class DriftResult:
    drift_detected: bool              # REQUIRED - True if drift detected
    drift_type: DriftType             # REQUIRED - Type of drift detected
    p_value: Optional[float]          # OPTIONAL - P-value from statistical test
    statistic: Optional[float]        # OPTIONAL - Test statistic value
    threshold: Optional[float]        # OPTIONAL - Detection threshold used
    confidence: Optional[float]       # OPTIONAL - Detection confidence (1 - p_value)
    timestamp: datetime               # REQUIRED - Detection timestamp (auto utcnow)
    details: Dict[str, Any]           # OPTIONAL - Additional detection details
```

**Validation Rules:**
- `drift_detected` must be consistent with test result (e.g., p_value < threshold)
- `confidence` = 1 - p_value when p_value is not None
- `timestamp` defaults to datetime.utcnow()
- `details` defaults to empty dict

---

## Function Signatures (Contracts)

### `KSDriftDetector.__init__(significance_level: float = 0.05) -> None`
**Pre:** significance_level in (0, 1)
**Post:** KS detector initialized with alpha threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `KSDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are 1D numpy arrays with length >= 2
**Post:** Returns DriftResult with drift_detected = (p_value < significance_level)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PSIDriftDetector.__init__(threshold: float = 0.25, n_bins: int = 10) -> None`
**Pre:** threshold > 0, n_bins >= 2
**Post:** PSI detector initialized with threshold and bin count
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PSIDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are 1D numpy arrays
**Post:** Returns DriftResult with drift_detected = (psi_value > threshold)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ADWINDriftDetector.__init__(delta: float = 0.002, max_window_size: int = 1000) -> None`
**Pre:** delta in (0, 1), max_window_size > 0
**Post:** ADWIN streaming detector initialized with window
**Raises:** None
**Retry:** No
**Side Effects:** Initializes empty deque window

### `ADWINDriftDetector.detect(new_value: float) -> Optional[DriftResult]`
**Pre:** None
**Post:** Returns DriftResult if change detected, None otherwise
**Raises:** None
**Retry:** No
**Side Effects:** Appends new_value to window, may drop old values after drift

### `MMDDriftDetector.__init__(threshold: float = 0.1, gamma: float = 1.0) -> None`
**Pre:** threshold > 0, gamma > 0
**Post:** MMD detector initialized with threshold and RBF kernel parameter
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MMDDriftDetector.detect(reference: np.ndarray, current: np.ndarray) -> DriftResult`
**Pre:** reference and current are 1D numpy arrays
**Post:** Returns DriftResult with drift_detected = (mmd_value > threshold)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] KS test uses scipy.stats.ks_2samp for distribution comparison
- [ ] KS drift detected when p_value < significance_level (default 0.05)
- [ ] PSI calculates population stability index with binning
- [ ] PSI drift detected when psi_value > threshold (default 0.25)
- [ ] PSI uses n_bins (default 10) for discretization
- [ ] PSI handles zero bins with 0.0001 floor value
- [ ] ADWIN maintains sliding window of max_window_size (default 1000)
- [ ] ADWIN detects drift when mean difference > epsilon_cut
- [ ] ADWIN epsilon_cut = sqrt((1/(2*m)) * log(2/delta))
- [ ] ADWIN resets window after change point detected
- [ ] ADWIN returns None until window has max_window_size // 2 elements
- [ ] MMD uses RBF kernel: exp(-gamma * ||x-y||^2)
- [ ] MMD calculates xx, yy, xy kernel matrices
- [ ] MMD drift detected when mmd_value > threshold (default 0.1)
- [ ] All DriftResult instances have timestamp auto-set to utcnow

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Each detector implements one algorithm |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| PERF-001 Performance | 07-performance.md | O(N^2) algorithms must be justified | ⚠️ NOT APPLIED - MMD has O(N^2) complexity by design |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ❌ GAP - Returns plain dataclass, not domain VO |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ⚠️ NOT APPLIED - No validation of array shapes/types |
| ERR-001 Exception handling | 05-error-handling.md | Handle edge cases gracefully | ⚠️ NOT APPLIED - No handling of empty arrays |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ❌ GAP - No logging of drift detection events |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions except ADWIN state |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, scipy.stats, collections.deque, logging, dataclasses, datetime, enum, typing
- **Internal:** None (standalone drift detection module)

---

## Required Tests
- **test_drift_detectors.py:**
  - Success: KS detector returns drift_detected=True when distributions differ (p < 0.05)
  - Success: KS detector returns drift_detected=False when distributions same (p >= 0.05)
  - Success: PSI calculates correct value with binning
  - Success: PSI detects drift when psi > threshold
  - Success: PSI handles zero-frequency bins with 0.0001 floor
  - Success: ADWIN detects change point when mean shifts significantly
  - Success: ADWIN returns None for insufficient window data
  - Success: ADWIN resets window after detecting drift
  - Success: MMD calculates correct kernel matrices
  - Success: MMD detects drift when mmd > threshold
  - Edge: Empty reference/current arrays handled gracefully
  - Edge: Single-element arrays handled without crash
  - Integration: All detectors return DriftResult with correct fields
  - Integration: DriftResult timestamp auto-sets to utcnow

---

## Notes
This module provides four complementary drift detection algorithms: (1) KS test - fast distribution comparison using Kolmogorov-Smirnov, (2) PSI - Population Stability Index standard in finance for monitoring distribution shifts, (3) ADWIN - Adaptive Windowing for streaming data with automatic change point detection, (4) MMD - Maximum Mean Discrepancy using kernel methods for more powerful detection. PSI is particularly relevant for trading systems - industry standard for model monitoring. ADWIN is ideal for real-time monitoring of live trading performance. KS and MMD are batch detectors for periodic validation. All detectors return consistent DriftResult objects with p_value, statistic, threshold, confidence, and timestamp fields.
