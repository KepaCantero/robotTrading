# overfitting_detector.py

## Purpose
Detects overfitting in trading strategies through train/validation performance gap analysis, cross-validation stability checks, and out-of-sample degradation metrics.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### OverfittingResult DataClass
```python
@dataclass
class OverfittingResult:
    is_overfitting: bool              # REQUIRED - True if overfitting detected
    severity: str                     # REQUIRED - One of: 'none', 'mild', 'moderate', 'severe'
    train_val_gap: Optional[float]    # OPTIONAL - Performance gap between train and validation
    confidence: float                 # REQUIRED - Detection confidence 0-1
    timestamp: datetime               # REQUIRED - Detection timestamp (auto-set to utcnow if None)
    details: Dict[str, Any]           # OPTIONAL - Additional detection details
```

**Validation Rules:**
- `severity` must be one of: 'none', 'mild', 'moderate', 'severe'
- `confidence` must be in range [0, 1]
- `timestamp` defaults to datetime.utcnow() if None
- `details` defaults to empty dict if None
- `is_overfitting` = True when severity != 'none'

---

## Function Signatures (Contracts)

### `OverfittingDetector.__init__(max_acceptable_gap: float = 0.15, cv_threshold: float = 0.10, oos_threshold: float = 0.20) -> None`
**Pre:** max_acceptable_gap > 0, cv_threshold > 0, oos_threshold > 0
**Post:** Detector initialized with gap thresholds
**Raises:** None
**Retry:** No
**Side Effects:** None

### `detect_from_results(train_result: BacktestResultValue, val_result: BacktestResultValue, oos_result: Optional[BacktestResultValue] = None) -> OverfittingResult`
**Pre:** train_result and val_result have total_return_pct attributes
**Post:** Returns OverfittingResult with severity based on train/val gap
**Raises:** None
**Retry:** No
**Side Effects:** None

### `detect_from_cv_scores(cv_scores: List[float], train_scores: Optional[List[float]] = None) -> OverfittingResult`
**Pre:** cv_scores is non-empty list of floats
**Post:** Returns OverfittingResult based on CV stability
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_learning_curve_gap(train_sizes: List[int], train_scores: List[float], val_scores: List[float]) -> Dict[str, Any]`
**Pre:** All lists have same length >= 2
**Post:** Returns dict with avg_gap, final_gap, is_converged, is_high_variance
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Severity levels: 'none' (gap <= 7.5%), 'mild' (7.5% < gap <= 15%), 'moderate' (15% < gap <= 30%), 'severe' (gap > 30%)
- [ ] Confidence increases with severity: mild=60%, moderate=80%, severe=95%
- [ ] CV stability measured by coefficient of variation (cv = std/mean)
- [ ] CV considered unstable if cv > cv_threshold (default 0.10)
- [ ] OOS degradation measured as val_return - oos_return
- [ ] OOS degradation > oos_threshold (default 0.20) indicates overfitting
- [ ] Learning curve gap analysis checks convergence and high variance
- [ ] Handles empty cv_scores by returning is_overfitting=False, confidence=0.0
- [ ] Details dict contains train/val returns, gap, thresholds
- [ ] Timestamp auto-sets to utcnow in __post_init__

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
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only detects overfitting |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ✅ FIXED - Documented rationale for dataclass use (see code comments) |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ⚠️ NOT APPLIED - No validation of list lengths in calculate_learning_curve_gap |
| ERR-001 Exception handling | 05-error-handling.md | Handle missing optional data gracefully | ✅ OK - Handles None for optional parameters |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ FIXED - Added structured logging for all detection events |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions, no side effects |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, logging, dataclasses, datetime, typing
- **Internal:** `app.domain.value_objects.backtest_result.BacktestResultValue`

---

## Required Tests
- **test_overfitting_detector.py:**
  - Success: 'none' severity when train/val gap <= 7.5%
  - Success: 'mild' severity when 7.5% < gap <= 15%
  - Success: 'moderate' severity when 15% < gap <= 30%
  - Success: 'severe' severity when gap > 30%
  - Success: Confidence increases with severity (60%, 80%, 95%)
  - Success: CV detection identifies unstable models (cv > threshold)
  - Success: OOS degradation detected when val - oos > threshold
  - Success: Learning curve analysis detects convergence issues
  - Success: Learning curve analysis detects high variance
  - Edge: Empty cv_scores returns not overfitting with 0.0 confidence
  - Edge: Missing train_scores still performs CV stability check
  - Edge: Missing oos_result skips OOS degradation check
  - Integration: detect_from_results includes train/val returns in details
  - Integration: detect_from_cv_scores includes CV stats in details

---

## Notes
Overfitting detection uses three complementary methods: (1) Train/validation gap analysis with severity thresholds, (2) Cross-validation stability via coefficient of variation, (3) Out-of-sample degradation tracking. Severity mapping: gap <= max_acceptable_gap * 0.5 = 'none', gap <= max_acceptable_gap = 'mild', gap <= max_acceptable_gap * 2 = 'moderate', gap > max_acceptable_gap * 2 = 'severe'. CV instability detected when cv_cv > cv_threshold (default 0.10). Learning curve analysis checks for convergence (val_score_range < cv_threshold) and high variance (std > cv_threshold). The detector uses BacktestResultValue domain object for integration with the backtesting system.
