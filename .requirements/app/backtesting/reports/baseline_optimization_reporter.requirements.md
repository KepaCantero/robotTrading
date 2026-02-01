# baseline_optimization_reporter.py

## Purpose
Generates professional HTML reports comparing baseline vs optimized strategies with statistical significance testing, parameter impact analysis, and interactive Plotly charts.

---

## Type Definitions / Data Classes

### ComparisonMetrics Class
```python
@dataclass
class ComparisonMetrics:
    sharpe_ratio: Tuple[float, float]           # REQUIRED - (baseline, optimized)
    total_return: Tuple[float, float]            # REQUIRED - (baseline, optimized)
    max_drawdown: Tuple[float, float]            # REQUIRED - (baseline, optimized) as positive values
    win_rate: Tuple[float, float]                # REQUIRED - (baseline, optimized)
    profit_factor: Tuple[float, float]           # REQUIRED - (baseline, optimized)
    sortino_ratio: Tuple[float, float]           # REQUIRED - (baseline, optimized)
    calmar_ratio: Tuple[float, float]            # REQUIRED - (baseline, optimized)
    omega_ratio: Tuple[float, float]             # REQUIRED - (baseline, optimized)
    oos_sharpe: Optional[Tuple[float, float]]    # OPTIONAL - Out-of-sample Sharpe
    is_oos_ratio: Optional[float]                # OPTIONAL - IS/OOS Sharpe ratio
```

**Validation Rules:**
- All tuple pairs are (baseline_value, optimized_value)
- max_drawdown stored as positive value (absolute)
- Optional fields only populated if OOS data available

### ParameterChange Class
```python
@dataclass
class ParameterChange:
    name: str                  # REQUIRED - Parameter name
    before: Any                # REQUIRED - Baseline value
    after: Any                 # REQUIRED - Optimized value
    impact: Optional[str]      # OPTIONAL - Impact description
    sensitivity: Optional[float] # OPTIONAL - Sensitivity score
```

**Validation Rules:**
- name must be non-empty
- before != after (only track changed parameters)

### StatisticalTest Class
```python
@dataclass
class StatisticalTest:
    metric_name: str      # REQUIRED - Metric being tested
    baseline_mean: float  # REQUIRED - Baseline mean
    optimized_mean: float # REQUIRED - Optimized mean
    p_value: float        # REQUIRED - Test p-value
    is_significant: bool  # REQUIRED - Significance at 95% confidence
    test_statistic: float # REQUIRED - Test statistic value
```

**Validation Rules:**
- p_value in range [0, 1]
- is_significant = (p_value < 0.05)

### Recommendation Class
```python
@dataclass
class Recommendation:
    decision: str                    # REQUIRED - "USE_OPTIMIZED" | "CONSIDER_OPTIMIZED" | "USE_BASELINE"
    rationale: str                   # REQUIRED - Reasoning for decision
    confidence: float                # REQUIRED - 0-1 confidence score
    conditions: List[str]            # OPTIONAL - Implementation steps
    warnings: List[str]              # OPTIONAL - Risk warnings
```

**Validation Rules:**
- decision must be one of three valid values
- confidence in range [0, 1]
- rationale non-empty

---

## Function Signatures (Contracts)

### `generate_report(profile, baseline_results, optimization_results, comparison, walk_forward_results, sensitivity_results) -> str`
**Pre:** profile is valid InputProfile, results have complete metrics and equity curves
**Post:** Returns HTML string with complete comparison report
**Raises:** FileNotFoundError if template not found, ValueError if metrics incomplete
**Retry:** No
**Side Effects:** None (string generation via Jinja2)

### `save_report(html, output_path) -> None`
**Pre:** html is valid HTML string, output_path is writable
**Post:** Creates file at output_path with HTML content
**Raises:** OSError if directory creation fails, PermissionError if not writable
**Retry:** No
**Side Effects:** Creates/overwrites file on disk

### `generate_pdf(html, output_path) -> bytes`
**Pre:** html is valid HTML
**Post:** Returns PDF bytes (placeholder - not implemented)
**Raises:** None (returns empty bytes with warning)
**Retry:** No
**Side Effects:** None (when implemented, will write file if output_path provided)

### `_extract_metrics(results) -> Dict[str, float]`
**Pre:** results dict has 'performance' key with required metrics
**Post:** Returns dict with 10+ metrics normalized for comparison
**Raises:** KeyError if required metrics missing
**Retry:** No
**Side Effects:** None (dict extraction)

### `_calculate_comparison(baseline, optimized) -> Dict[str, Any]`
**Pre:** baseline and optimized dicts have matching keys
**Post:** Returns dict with 4 improvement percentages
**Raises:** ZeroDivisionError if baseline value is 0 (handled)
**Retry:** No
**Side Effects:** None (calculation)

### `_pct_improvement(baseline, optimized, higher_better) -> float`
**Pre:** baseline and optimized are numeric
**Post:** Returns percentage improvement rounded to 2 decimals
**Raises:** ZeroDivisionError if baseline is 0 (returns 0)
**Retry:** No
**Side Effects:** None (calculation)

### `_perform_significance_tests(baseline_results, optimized_results) -> Dict[str, StatisticalTest]`
**Pre:** results have equity_curve data with multiple points
**Post:** Returns dict of StatisticalTest objects
**Raises:** ValueError if insufficient data for t-test
**Retry:** No
**Side Effects:** None (statistical calculation)

### `_t_test_means(baseline_returns, optimized_returns, metric_name) -> StatisticalTest`
**Pre:** Both arrays have same length > 0
**Post:** Returns StatisticalTest with p-value and significance flag
**Raises:** ValueError if arrays too short
**Retry:** No
**Side Effects:** None (uses scipy.stats.ttest_rel)

### `_extract_parameter_changes(baseline_params, optimized_params, comparison) -> List[ParameterChange]`
**Pre:** Both dicts have string keys
**Post:** Returns list of ParameterChange for differing parameters
**Raises:** None
**Retry:** No
**Side Effects:** None (comparison)

### `_generate_recommendation(baseline_metrics, optimized_metrics, comparison, walk_forward_results) -> Recommendation`
**Pre:** All inputs have required metrics
**Post:** Returns Recommendation with decision and confidence score
**Raises:** None
**Retry:** No
**Side Effects:** None (logic)

### `_prepare_chart_data(baseline_results, optimized_results, walk_forward_results, sensitivity_results) -> Dict[str, Any]`
**Pre:** Results have equity_curve data
**Post:** Returns dict with 6+ Plotly chart specifications
**Raises:** None (returns empty charts on error)
**Retry:** No
**Side Effects:** None (data transformation)

---

## Acceptance Criteria
- [ ] HTML report renders with all sections: header, recommendation, metrics, parameters, charts
- [ ] Recommendation logic: USE_OPTIMIZED if Sharpe > 1.2x baseline AND OOS stable
- [ ] Statistical significance uses paired t-test (ttest_rel) for same market data
- [ ] Significance threshold: p-value < 0.05 for 95% confidence
- [ ] Chart data includes: dual equity, drawdown, risk radar, walk-forward
- [ ] Parameter impact estimation for lookback, threshold, size parameters
- [ ] Confidence scores: 0.85 for USE_OPTIMIZED, 0.65 for CONSIDER_OPTIMIZED, 0.75 for USE_BASELINE
- [ ] Template loading falls back gracefully or raises clear error
- [ ] All datetime objects converted to strings for JSON serialization
- [ ] Drawdown stored as positive value for comparisons

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ FIXED - 2026-02-01 - Added error logging for chart creation failures |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - 2026-02-01 - Added ValueError/OSError/IOError handling for file operations |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ NOT APPLIED - Many methods > 20 lines (chart data prep) |
| BT-003 | BASE_RULES | No look-ahead bias | ✅ OK - Uses equity_curve from completed backtest |
| BT-005 | BASE_RULES | Multiple periods testing | ✅ OK - Walk-forward validation |
| RSK-002 | BASE_RULES | Expected Shortfall | ⚠️ NOT APPLIED - Uses provided metrics |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Report provides audit trail |

**NOTE:** Uses scipy.stats.ttest_rel (paired) not ttest_ind (independent) which is critical for same-market-data comparison.

---

## Dependencies
- **External:** json, logging, dataclasses, datetime, pathlib, typing, numpy (stdlib + numpy), jinja2 (Template)
- **Internal:**
  - `app.core.models.input_profile.InputProfile`
  - `scipy.stats` (for t-test)

---

## Required Tests
- **tests/backtesting/reports/test_baseline_optimization_reporter.py:**
  - Test report generation with valid data
  - Test recommendation decision logic for all three outcomes
  - Test statistical significance testing with paired t-test
  - Test p-value < 0.05 triggers is_significant=True
  - Test parameter change extraction
  - Test parameter impact estimation for different types
  - Test dual equity chart data preparation
  - Test drawdown chart with normalized values
  - Test risk radar chart with normalized metrics
  - Test walk-forward chart data structure
  - Test markdown tables to HTML conversion
  - Test template not found raises FileNotFoundError
  - Test datetime serialization in chart data

---

## Notes
PDF generation is placeholder (TODO). Implementation should use weasyprint or similar for production.
