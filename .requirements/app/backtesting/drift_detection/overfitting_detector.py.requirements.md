# overfitting_detector.py

## Purpose
Detects overfitting in trading strategies through cross-validation analysis, learning curves, and train/validation performance gaps using domain BacktestResultValue objects.

---

## Type Definitions / Data Classes

### OverfittingResult DataClass
```python
@dataclass
class OverfittingResult:
    is_overfitting: bool                    # REQUIRED - Whether overfitting detected
    severity: str                           # REQUIRED - One of: 'none', 'mild', 'moderate', 'severe'
    train_val_gap: Optional[float] = None   # OPTIONAL - Performance gap between train/val
    confidence: float = 0.0                 # REQUIRED - Detection confidence [0, 1]
    timestamp: datetime = None              # AUTO - Detection time (set in __post_init__)
    details: Dict[str, Any] = None          # OPTIONAL - Additional metrics context
```

**Validation Rules:**
- `severity` must be one of: 'none', 'mild', 'moderate', 'severe'
- `confidence` must be in range [0, 1]
- `train_val_gap` can be None if gap not calculated
- `timestamp` and `details` auto-initialized in `__post_init__` if None
- `details` may contain: train_return, val_return, gap, gap_threshold, cv_mean, cv_std, etc.

---

## Function Signatures (Contracts)

### `OverfittingDetector.__init__(max_acceptable_gap: float = 0.15, cv_threshold: float = 0.10, oos_threshold: float = 0.20)`
**Pre:** max_acceptable_gap > 0, cv_threshold > 0, oos_threshold > 0
**Post:** detector initialized with thresholds
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `OverfittingDetector.detect_from_results(train_result: BacktestResultValue, val_result: BacktestResultValue, oos_result: Optional[BacktestResultValue] = None) -> OverfittingResult`
**Pre:** train_result and val_result have valid total_return_pct values
**Post:** OverfittingResult with severity and confidence assessment
**Raises:** AttributeError if BacktestResultValue missing required fields
**Retry:** ❌ No
**Side Effects:** Logs overfitting detection event with structured logging

### `OverfittingDetector.detect_from_cv_scores(cv_scores: List[float], train_scores: Optional[List[float]] = None) -> OverfittingResult`
**Pre:** cv_scores is non-empty list of numbers
**Post:** OverfittingResult based on CV stability and train/val gap
**Raises:** ❌ No (returns error result if cv_scores empty)
**Retry:** ❌ No
**Side Effects:** Logs detection event; returns error result if cv_scores empty

### `OverfittingDetector.calculate_learning_curve_gap(train_sizes: List[int], train_scores: List[float], val_scores: List[float]) -> Dict[str, Any]`
**Pre:** All lists have same length >= 2
**Post:** Dict with learning curve analysis metrics
**Raises:** ❌ No (returns error dict if insufficient data)
**Retry:** ❌ No
**Side Effects:** Logs analysis event

---

## Acceptance Criteria
- [ ] detect_from_results correctly calculates train/validation gap
- [ ] Severity classification follows thresholds: none (< 0.5*gap), mild (0.5-1*gap), moderate (1-2*gap), severe (> 2*gap)
- [ ] detect_from_cv_scores handles empty cv_scores gracefully
- [ ] CV stability calculated as cv_std / cv_mean (coefficient of variation)
- [ ] OOS degradation correctly increases severity
- [ ] Learning curve convergence detection uses cv_threshold
- [ ] All detection events logged with structured logging
- [ ] Type hints present on all methods
- [ ] Error cases return valid OverfittingResult objects (not exceptions)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK - All functions have type hints |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK - Uses logger.info/warning with extra dict |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Handles errors, returns valid results |
| TRD-002 | BASE_RULES.md | Validate domain inputs | ⚠️ PARTIAL - Relies on BacktestResultValue validation |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - Supports OOS result parameter |
| ARCH-004 | BASE_RULES.md | Small functions < 20 lines | ❌ GAP - detect_from_results is 108 lines |
| SOL-001 | BASE_RULES.md | Single Responsibility | ⚠️ PARTIAL - Does detection + severity + logging |

**GAP Analysis:**

1. **ARCH-004 (Function Length):** `detect_from_results` is 108 lines, exceeds 20-line guideline.
   - Impact: Low (function is readable but long)
   - Recommendation: Extract severity calculation and detail building into private methods

2. **SOL-001 (Single Responsibility):** `detect_from_results` does gap calculation, severity assessment, OOS check, logging, confidence calculation.
   - Impact: Low (cohesive within overfitting detection)
   - Recommendation: Consider extracting `_assess_severity()` and `_build_details()` helpers

3. **TRD-002 (Domain Input Validation):** Relies on BacktestResultValue being valid. Doesn't validate total_return_pct is numeric.
   - Impact: Medium (could crash on invalid domain objects)
   - Recommendation: Add validation: `assert isinstance(train_result.total_return_pct, (int, float, Decimal))`

---

## Dependencies
- **External:**
  - numpy (statistical calculations: mean, std)
  - logging (structured logging)
  - dataclasses (OverfittingResult)
  - datetime (timestamps)
  - typing (type hints)
- **Internal:**
  - app.backtesting.domain.value_objects.backtest_result.BacktestResultValue (domain result object)

---

## Required Tests
- **tests/unit/backtesting/test_overfitting_detector.py:**
  - Test detect_from_results with no overfitting (small gap)
  - Test detect_from_results with mild overfitting
  - Test detect_from_results with moderate overfitting
  - Test detect_from_results with severe overfitting
  - Test detect_from_results with OOS degradation
  - Test detect_from_cv_scores with stable CV
  - Test detect_from_cv_scores with unstable CV (high cv_cv)
  - Test detect_from_cv_scores with train/val gap
  - Test detect_from_cv_scores with empty cv_scores (error case)
  - Test calculate_learning_curve_gap convergence detection
  - Test calculate_learning_curve_gap high variance detection
  - Test calculate_learning_curve_gap insufficient data
  - Test severity confidence values align with thresholds
  - Test structured logging output for all detection methods
  - Test OverfittingResult __post_init__ default values

---

## Notes
- Design note DOM-001: OverfittingResult is a plain dataclass (not a domain VO) as it's analytical metadata, not a trading domain concept
- Detector operates on domain BacktestResultValue objects but produces analysis results (cross-cutting utility)
- Confidence values are heuristic estimates, not statistical confidence intervals
- Severity thresholds are configurable via __init__ parameters (not hardcoded)
- Logging includes both info (completion) and warning (detection) levels
