# professional_reporter.py

## Purpose
Generates institutional-quality professional backtesting reports including executive summary (PDF), complete interactive HTML report with performance, risk, trades, and robustness tabs.

---

## Type Definitions / Data Classes

### ReportSection Class
```python
@dataclass
class ReportSection:
    title: str                              # REQUIRED - Section title
    content: str                            # REQUIRED - Markdown content
    charts: List[Dict[str, Any]]            # OPTIONAL - Chart data for visualization
```

**Validation Rules:**
- `title` must be non-empty string
- `content` can be empty (for placeholder sections)
- `charts` defaults to empty list if not provided

### ProfessionalReport Class
```python
@dataclass
class ProfessionalReport:
    strategy_name: str                      # REQUIRED - Strategy identifier
    timestamp: datetime                     # REQUIRED - Report generation time
    period_start: datetime                  # REQUIRED - Backtest start date
    period_end: datetime                    # REQUIRED - Backtest end date
    backtest_result: Optional[BacktestResult] = None      # OPTIONAL - Core results
    walk_forward_results: Optional[List[ValidationWindow]] = None  # OPTIONAL - Walk-forward validation
    capital_scale_results: Optional[CapitalScaleAnalysisReport] = None  # OPTIONAL - Capital scaling
    acceptance_report: Optional[AcceptanceReport] = None  # OPTIONAL - Acceptance criteria
    executive_summary: Optional[ReportSection] = None     # OPTIONAL - Executive summary
    performance_section: Optional[ReportSection] = None   # OPTIONAL - Performance metrics
    risk_section: Optional[ReportSection] = None          # OPTIONAL - Risk analysis
    trades_section: Optional[ReportSection] = None        # OPTIONAL - Trade analysis
    robustness_section: Optional[ReportSection] = None   # OPTIONAL - Robustness tests
    survivorship_bias_warning: bool = False   # OPTIONAL - Bias detection flag
    look_ahead_bias_warning: bool = False     # OPTIONAL - Bias detection flag
```

**Validation Rules:**
- `strategy_name` must be non-empty
- `period_start` must be before `period_end`
- All Optional fields default to None

### ProfessionalReporter Class
```python
class ProfessionalReporter:
    include_pdf: bool                       # OPTIONAL - Generate PDF report (default: True)
    include_html: bool                      # OPTIONAL - Generate HTML report (default: True)
    pdf_template_path: Optional[str]        # OPTIONAL - Custom PDF template path
```

**Validation Rules:**
- Both `include_pdf` and `include_html` can be False (no output)
- `pdf_template_path` is optional, uses default if None

---

## Function Signatures (Contracts)

### `__init__(include_pdf: bool = True, include_html: bool = True, pdf_template_path: Optional[str] = None) -> None`
**Pre:** None (all parameters optional)
**Post:** Reporter initialized with specified output format options
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (configuration only)

### `generate_executive_summary(backtest_result: BacktestResult, acceptance_report: AcceptanceReport, benchmark_return: float) -> ReportSection`
**Pre:** backtest_result.performance is not None
**Post:** Returns ReportSection with KPIs, verdict, capital recommendation
**Raises:** ValueError if performance data is None
**Retry:** ❌ No
**Side Effects:** None (generates in-memory structure)

### `generate_complete_report(backtest_result: BacktestResult, acceptance_report: AcceptanceReport, walk_forward_results: Optional[List[ValidationWindow]] = None, capital_scale_results: Optional[CapitalScaleAnalysisReport] = None, benchmark_return: float = 0.0) -> ProfessionalReport`
**Pre:** backtest_result.performance is not None
**Post:** Returns complete ProfessionalReport with all sections
**Raises:** ValueError if performance data is None
**Retry:** ❌ No
**Side Effects:** None (generates in-memory structure)

### `export_to_html(report: ProfessionalReport) -> str`
**Pre:** report has at least one section populated
**Post:** Returns HTML string with complete report
**Raises:** None (returns empty HTML on error)
**Retry:** ❌ No
**Side Effects:** None (string generation)

### `_convert_markdown_tables_to_html(content: str) -> str`
**Pre:** content contains markdown table syntax
**Post:** Returns HTML with tables converted to <table> tags
**Raises:** None (returns original content on error)
**Retry:** ❌ No
**Side Effects:** None (string transformation)

### `_section_to_html(section: Optional[ReportSection]) -> str`
**Pre:** None (handles None gracefully)
**Post:** Returns HTML string or empty string if section is None
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_get_verdict_description(verdict: str, score: float) -> str`
**Pre:** verdict is one of: "APPROVED", "REVISION", "REJECTED"
**Post:** Returns human-readable verdict description
**Raises:** None (returns default description for unknown verdict)
**Retry:** ❌ No
**Side Effects:** None

### `_generate_capital_recommendation(sharpe: float, max_dd: float, profit_factor: float) -> str`
**Pre:** All parameters are valid floats
**Post:** Returns recommendation string (full/moderate/minimal/no allocation)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_prepare_equity_chart_data(result: BacktestResult, benchmark_return: float) -> Dict[str, Any]`
**Pre:** result.equity_curve may be empty
**Post:** Returns dict with dates, strategy values, benchmark values
**Raises:** KeyError, TypeError, ValueError (caught and logged)
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] No hardcoded secrets or sensitive data (SEC-001)
- [ ] Executive summary includes KPIs: CAGR, Sharpe, MaxDD, Profit Factor, Win Rate
- [ ] Verdict description matches acceptance criteria (APPROVED/REVISION/REJECTED)
- [ ] Capital recommendation thresholds: Sharpe > 1.5, MaxDD < 15%, Profit Factor > 1.5 for full allocation
- [ ] HTML export converts markdown tables to HTML tables
- [ ] Walk-forward results handle both dict and list formats
- [ ] Benchmark comparison calculates excess return
- [ ] Structured logging with context for all operations (LOG-001)
- [ ] Error handling for missing performance data

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - 2026-02-03 - Created proper TypedDict definitionsDict[str, Any]` in charts and metrics |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK |
| ARCH-004 | BASE_RULES.md | Functions < 50 lines (ideally < 20) | ⚠️ NOT APPLIED - HTML generation inherently long |
| TRD-004 | BASE_RULES.md | Audit trail | ✅ OK - Reports provide audit trail |
| RSK-001 | BASE_RULES.md | VaR calculation included | ✅ OK - In risk section |

**GAP Violations Found:**

1. **TYP-003** (P1 - High): Uses `Any` type in multiple locations
   - **Location 1**: Line 29: `charts: List[Dict[str, Any]]`
   - **Location 2**: Line 170: `chart_data = {"dates": [], "strategy": [], "benchmark": []}`
   - **Location 3**: Line 381: `def _prepare_equity_chart_data(...) -> Dict[str, Any]`
   - **Fix**: Define specific schema for chart data:
   ```python
   from typing import TypedDict

   class ChartData(TypedDict):
       dates: List[str]
       strategy: List[float]
       benchmark: List[float]

   charts: List[ChartData]
   def _prepare_equity_chart_data(...) -> ChartData
   ```

2. **ARCH-004** (P2 - Medium): Some functions exceed recommended length
   - `_convert_markdown_tables_to_html`: ~50 lines (table parsing logic)
   - `export_to_html`: ~35 lines (HTML template)
   - **Justification**: HTML/markdown conversion requires sequential processing
   - **Recommendation**: Accept as exception, but consider extracting HTML template to separate file

3. **Missing Validation** (P1): No validation for benchmark_return parameter
   - **Location**: `generate_executive_summary` and `generate_complete_report`
   - **Issue**: Could receive infinite or NaN values
   - **Fix**: Add validation:
   ```python
   if not math.isfinite(benchmark_return):
       raise ValueError("benchmark_return must be finite")
   ```



**FIXED VIOLATIONS:**

✅ **TYP-003** (P1 - High): Dict[str, Any] replaced with proper TypedDict definitions - FIXED 2026-02-03
   - **Fixed**: Created specific TypedDict classes for all return types
   - **Implementation**: 
     - awesome_quant_integrator.py: QuantstatsMetrics, EmpyricalMetrics, PyfolioMetrics, AwesomeQuantMetricsDict, FallbackMetrics
     - report_generator.py: PeriodInfoDict, ConfigInfoDict, ReturnsDict, PerformanceDict, RiskDict, DetailedMetrics
     - professional_reporter.py: ChartDataDict, ChartDict, ReportSectionCharts
     - constants.py: FixedCommissionModel, HybridCommissionModel, TierBracket, TieredCommissionModel, CommissionModel
   - **Validation**: All files compile successfully with proper type hints
---

## Dependencies
- **External:** logging, datetime, dataclasses, typing (stdlib)
- **Internal:**
  - `app.backtesting.acceptance_criteria.AcceptanceReport`
  - `app.backtesting.capital_scale_analyzer.CapitalScaleAnalysisReport`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.walk_forward_validator.ValidationWindow`

---

## Required Tests
- **tests/unit/backtesting/test_professional_reporter.py:**
  - Test executive summary generation with positive performance
  - Test executive summary with negative performance
  - Test verdict description for all three outcomes (APPROVED/REVISION/REJECTED)
  - Test capital recommendation thresholds
  - Test complete report generation with all sections
  - Test HTML export with markdown tables
  - Test HTML export with None sections (graceful handling)
  - Test walk-forward results with dict format
  - Test walk-forward results with list format
  - Test equity chart data preparation with empty curve
  - Test benchmark comparison calculation
  - Test structured logging includes all context
  - Test error handling for missing performance data

---

## Notes
- **Flexible Walk-Forward Format**: Handles both dict (from `WalkForwardValidator.validate_strategy()`) and list formats for walk-forward results
- **HTML Table Conversion**: Custom implementation converts markdown tables to HTML tables for better rendering
- **Capital Allocation Logic**: Three-tier recommendation system based on Sharpe > 1.5/1.0/0.5 thresholds
- **Bias Detection Flags**: Includes `survivorship_bias_warning` and `look_ahead_bias_warning` flags (not currently set in code)
- **Verdict System**: Three-tier verdict (APPROVED/REVISION/REJECTED) with score 0-100
