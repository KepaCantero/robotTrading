# baseline_optimization_reporter.py

## Purpose
Generates professional comparison reports between baseline and optimized strategies with interactive Plotly charts, statistical significance testing, and implementation recommendations.

---

## Type Definitions / Data Classes

### ComparisonMetrics
```python
@dataclass
class ComparisonMetrics:
    sharpe_ratio: tuple[float, float]  # REQUIRED - (baseline, optimized)
    total_return: tuple[float, float]  # REQUIRED - (baseline, optimized)
    max_drawdown: tuple[float, float]  # REQUIRED - (baseline, optimized)
    win_rate: tuple[float, float]  # REQUIRED - (baseline, optimized)
    profit_factor: tuple[float, float]  # REQUIRED - (baseline, optimized)
    sortino_ratio: tuple[float, float]  # REQUIRED - (baseline, optimized)
    calmar_ratio: tuple[float, float]  # REQUIRED - (baseline, optimized)
    omega_ratio: tuple[float, float]  # REQUIRED - (baseline, optimized)
    # Optional out-of-sample metrics
    oos_sharpe: tuple[float, float] | None  # OPTIONAL - (baseline, optimized)
    is_oos_ratio: float | None  # OPTIONAL - In-sample / Out-of-sample ratio
```

**Validation Rules:**
- All tuples must have exactly 2 elements (baseline, optimized)
- Drawdown stored as positive value (absolute)
- oos_sharpe only available if walk-forward validation performed

### ParameterChange
```python
@dataclass
class ParameterChange:
    name: str  # REQUIRED - Parameter name
    before: Any  # REQUIRED - Baseline value
    after: Any  # REQUIRED - Optimized value
    impact: str | None  # OPTIONAL - Impact description
    sensitivity: float | None  # OPTIONAL - Sensitivity score
```

**Validation Rules:**
- name must be non-empty string
- before and after can be any type (int, float, str, bool, list)
- impact is heuristic-based estimation

### StatisticalTest
```python
@dataclass
class StatisticalTest:
    metric_name: str  # REQUIRED - Name of metric tested
    baseline_mean: float  # REQUIRED - Baseline mean
    optimized_mean: float  # REQUIRED - Optimized mean
    p_value: float  # REQUIRED - Statistical p-value
    is_significant: bool  # REQUIRED - Significant at 95% confidence (p < 0.05)
    test_statistic: float  # REQUIRED - T-test statistic
```

**Validation Rules:**
- p_value must be in range [0, 1]
- is_significant = (p_value < 0.05)
- Uses scipy.stats.ttest_rel (paired t-test)

### Recommendation
```python
@dataclass
class Recommendation:
    decision: str  # REQUIRED - "USE_OPTIMIZED", "CONSIDER_OPTIMIZED", "USE_BASELINE"
    rationale: str  # REQUIRED - Text explanation
    confidence: float  # REQUIRED - 0-1 confidence score
    conditions: list[str]  # OPTIONAL - Deployment conditions
    warnings: list[str]  # OPTIONAL - Risk warnings
```

**Validation Rules:**
- decision must be one of: "USE_OPTIMIZED", "CONSIDER_OPTIMIZED", "USE_BASELINE"
- confidence must be in range [0, 1]
- conditions and warnings default to empty lists

---

## Function Signatures (Contracts)

### `__init__(template_path: str | None = None) -> None`
**Pre:** template_path must exist if provided, otherwise uses default template
**Post:** Reporter initialized with loaded Jinja2 template
**Raises:** FileNotFoundError (template not found)
**Retry:** No
**Side Effects:** Reads template file from disk

### `generate_report(profile: InputProfile, baseline_results: dict, optimization_results: dict, comparison: dict | None = None, walk_forward_results: dict | None = None, sensitivity_results: dict | None = None) -> str`
**Pre:** All result dictionaries contain required metrics (sharpe_ratio, total_return, etc.)
**Post:** Returns HTML report as string with interactive charts
**Raises:** ValueError (empty metrics), KeyError (missing required fields)
**Retry:** No
**Side Effects:** None (pure function, generates HTML)

### `save_report(html: str, output_path: str) -> None`
**Pre:** html must be non-empty string, output_path must be valid file path
**Post:** HTML content written to file, directories created as needed
**Raises:** OSError (directory creation failed), ValueError (html empty)
**Retry:** No
**Side Effects:** Creates directories, writes file to disk

### `generate_pdf(html: str, output_path: str | None = None) -> bytes`
**Pre:** html must be non-empty
**Post:** Returns PDF as bytes (placeholder implementation)
**Raises:** No (returns empty bytes, logs warning)
**Retry:** No
**Side Effects:** None (placeholder, logs warning)

### `_extract_metrics(results: dict) -> dict[str, float]`
**Pre:** results contains 'performance' and 'equity_curve' keys
**Post:** Returns dict with sharpe_ratio, total_return, max_drawdown, etc.
**Raises:** KeyError (missing required keys), ZeroDivisionError (initial capital = 0)
**Retry:** No
**Side Effects:** None (pure function)

### `_perform_significance_tests(baseline_results: dict, optimized_results: dict) -> dict[str, StatisticalTest]`
**Pre:** Both result dicts have 'equity_curve' with sufficient data points
**Post:** Returns dict of StatisticalTest objects for Sharpe and return
**Raises:** ValueError (insufficient data)
**Retry:** No
**Side Effects:** Uses scipy.stats.ttest_rel for paired samples

### `_generate_recommendation(...) -> Recommendation`
**Pre:** All metric dictionaries valid and non-empty
**Post:** Returns Recommendation with decision, confidence, rationale, conditions, warnings
**Raises:** No (defaults to USE_BASELINE on error)
**Retry:** No
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] AC-001: Template loaded successfully from default or custom path
- [ ] AC-002: HTML report generated with all required sections (executive summary, metrics, parameters, charts)
- [ ] AC-003: Statistical significance tests use paired t-test (ttest_rel)
- [ ] AC-004: All Plotly charts render correctly (equity, drawdown, radar, walk-forward)
- [ ] AC-005: Decision logic: USE_OPTIMIZED if Sharpe > 1.2x baseline AND OOS Sharpe > 0.8x IS Sharpe
- [ ] AC-006: CONSIDER_OPTIMIZED if Sharpe > 1.05x baseline but conditions not fully met
- [ ] AC-007: USE_BASELINE if improvement marginal (< 1.05x)
- [ ] AC-008: Confidence scores: 0.85 (USE_OPTIMIZED), 0.65 (CONSIDER_OPTIMIZED), 0.75 (USE_BASELINE)
- [ ] AC-009: Parameter impact estimation for lookback, threshold, size parameters
- [ ] AC-010: Drawdown stored as positive value (absolute)
- [ ] AC-011: Percentage improvement rounded to 2 decimal places
- [ ] AC-012: Chart data serializable to JSON (datetime objects converted to strings)
- [ ] AC-013: Save report creates parent directories if needed
- [ ] AC-014: Error handling for template rendering failures
- [ ] AC-015: Type hints cover all methods (mypy --strict)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage for all methods | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK (try/except in save_report) |
| TST-005 | 06-testing.md | Coverage > 80% | ❌ GAP - Need test coverage metrics |
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 | ✅ OK (black formatted) |
| SEC-001 | 28-security-and-secrets.md | No hardcoded secrets | ✅ OK (template path from config) |
| ARCH-004 | 05-architecture.md | Small functions < 20 lines | ⚠️ NOT APPLIED - Complex chart generation |
| QL-001 | 00-checklist.md | Complexity < 10 per function | ⚠️ NOT APPLIED - Chart data preparation |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, jinja2, scipy (for t-test)
- **Internal:**
  - app.core.models.input_profile.InputProfile

---

## Required Tests
- **tests/unit/backtesting/reports/test_baseline_optimization_reporter.py:**
  - Test template loading (default and custom paths)
  - Test metric extraction from results dict
  - Test percentage improvement calculation (higher_better and lower_better)
  - Test statistical significance testing (paired t-test)
  - Test recommendation generation logic (3 decision paths)
  - Test parameter change extraction and impact estimation
  - Test chart data preparation (equity, drawdown, radar)
  - Test HTML report generation with all sections
  - Test save report creates directories and writes file
  - Test error handling for missing template
  - Test error handling for empty HTML in save_report
  - Test datetime serialization to JSON in chart data
  - Test drawdown conversion to positive value

- **tests/integration/backtesting/reports/test_baseline_optimization_reporter_integration.py:**
  - Test full report generation with real backtest results
  - Test HTML template rendering with all variables
  - Test Plotly charts render in browser
  - Test statistical significance with real equity curves
  - Test recommendation confidence scores match criteria

---

## Notes
- Uses Jinja2 for template rendering (default template in templates/ subdirectory)
- Implements paired t-test (ttest_rel) because both strategies tested on same market data
- PDF generation is placeholder (requires weasyprint or similar for production)
- Chart data uses JSON serialization with datetime converter
- Decision logic based on Tomasini walk-forward validation principles
