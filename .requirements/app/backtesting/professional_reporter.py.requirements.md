# Requirements: backtesting/professional_reporter.py

## Source File Analysis
- **File Path:** `app/backtesting/professional_reporter.py`
- **Lines of Code:** 528
- **Audit Status:** PASSED_WITH_NOTES
- **Audit Date:** 2026-02-07T05:30:00Z

## Purpose
Generates institutional-quality professional reports for backtesting results (Req #16). Creates executive summary PDFs and complete interactive HTML reports.

## Dependencies
- **Internal:**
  - `app.backtesting.acceptance_criteria.AcceptanceReport`
  - `app.backtesting.capital_scale_analyzer.CapitalScaleAnalysisReport`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.walk_forward_validator.ValidationWindow`
- **External:**
  - `logging`
  - `dataclasses` (dataclass, field)
  - `datetime`
  - `typing` (Any, Dict, List, Optional, TypedDict, Union)

## Classes/Functions

### TypedDict Definitions
- **ChartDataDict:** Chart data structure
- **ChartDict:** Chart metadata and data
- **ReportSectionCharts:** Report section chart structure

### Data Classes
- **ReportSection:** A section of the report
  - `title: str`
  - `content: str`
  - `charts: List[ChartDict] = field(default_factory=list)`

- **ProfessionalReport:** Complete backtesting report
  - `strategy_name: str`
  - `timestamp: datetime`
  - `period_start: datetime`
  - `period_end: datetime`
  - `backtest_result: Optional[BacktestResult] = None`
  - `walk_forward_results: Optional[List[ValidationWindow]] = None`
  - `capital_scale_results: Optional[CapitalScaleAnalysisReport] = None`
  - `acceptance_report: Optional[AcceptanceReport] = None`
  - `executive_summary: Optional[ReportSection] = None`
  - `performance_section: Optional[ReportSection] = None`
  - `risk_section: Optional[ReportSection] = None`
  - `trades_section: Optional[ReportSection] = None`
  - `robustness_section: Optional[ReportSection] = None`
  - `survivorship_bias_warning: bool = False`
  - `look_ahead_bias_warning: bool = False`

### Main Class
- **ProfessionalReporter:** Report generator (Req #16)
  - `__init__(include_pdf: bool = True, include_html: bool = True, pdf_template_path: Optional[str] = None)`
  - `generate_executive_summary(...) -> ReportSection`
  - `generate_complete_report(...) -> ProfessionalReport`
  - `_generate_performance_section(result: BacktestResult) -> ReportSection`
  - `_generate_risk_section(result: BacktestResult) -> ReportSection`
  - `_generate_trades_section(result: BacktestResult) -> ReportSection`
  - `_generate_robustness_section(...) -> ReportSection`
  - `_get_verdict_description(verdict: str, score: float) -> str`
  - `_generate_capital_recommendation(sharpe: float, max_dd: float, profit_factor: float) -> str`
  - `_prepare_equity_chart_data(result: BacktestResult, benchmark_return: float) -> ChartDataDict`
  - `export_to_html(report: ProfessionalReport) -> str`
  - `_convert_markdown_tables_to_html(content: str) -> str`
  - `_section_to_html(section: Optional[ReportSection]) -> str`

## Business Logic

### Executive Summary Generation
Extracts KPIs for 1-page PDF:
- CAGR, Sharpe Ratio, Max Drawdown
- Profit Factor, Win Rate
- Equity curve vs benchmark chart
- Automatic verdict (APPROVED/REVISION/REJECTED)
- Capital recommendation

### Complete Report Sections
1. **Performance Section:** Basic metrics, return metrics, risk-adjusted returns
2. **Risk Section:** Drawdown metrics, tail risk, volatility
3. **Trades Section:** Trade statistics, averages, duration
4. **Robustness Section:** Walk-forward analysis, capital scale analysis

### Verict System
- **APPROVED:** All acceptance criteria met (Sharpe >1.0, DD <25%, PF >1.3)
- **REVISION:** Marginal performance (Sharpe >0.5)
- **REJECTED:** Insufficient performance (Sharpe <0.5)

### HTML Export
- Converts markdown tables to HTML
- Generates responsive HTML with CSS styling
- Color-coded verdicts (green/orange/red)

## Data Models
Uses TypedDict for type-safe data structures:
- `ChartDataDict`, `ChartDict`, `ReportSectionCharts`
- Data classes for `ReportSection`, `ProfessionalReport`

## API Contracts
N/A - This is a library module

## Error Handling
- Catches specific exceptions: `KeyError`, `TypeError`, `ValueError`
- All exceptions logged with context
- Graceful degradation (returns empty charts on failure)
- Raises `ValueError` for missing performance data

## Performance Considerations
- Single-pass report generation
- Minimal string concatenation (uses list join)
- Chart data prepared in O(n) where n = data points

## Testing Strategy
- Unit tests for each section generator
- Test verdict logic with various metric combinations
- Verify HTML table conversion
- Test chart data preparation
- Edge cases: missing data, None values

## Audit Notes

### Non-Critical Issues
1. **Type Hints (TYP-002):** Uses old syntax `Optional[X]` in many places
   - Lines: 97, 212, 329, 330
   - Impact: Low - code is functional and type-safe
   - Recommendation: Update to `X | None` syntax in future refactor

2. **Any Type Usage (TYP-003):** Uses `Any` in TypedDict and data classes
   - Lines: 13, 44, 123
   - Impact: Low - TypedDict provides structure
   - Recommendation: Create more specific types for `Any` fields

3. **Union Type (TYP-002):** Uses `Union` instead of `|` syntax
   - Line 329: `Optional[Union[List[ValidationWindow], Dict]]`
   - Should be: `List[ValidationWindow] | Dict | None`

### What Was Checked
- ✅ No print() statements (uses logger)
- ✅ No mutable default arguments (uses `field(default_factory=...)`)
- ✅ Proper exception handling with specific types
- ✅ Google style docstrings
- ✅ Absolute imports only
- ✅ All functions have return type hints
- ✅ Uses TypedDict for structured data (modern Python)

### BASE_RULES Compliance
See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

**File-specific rules:**
- FMT-007: No mutable defaults ✅
- TYP-001: 100% type coverage ✅
- TYP-002: Modern syntax - mixed (TypedDict is modern, Optional/Union is old)
- TYP-006: Uses TypedDict for duck typing ✅
- LOG-004: Error logging with context ✅
- CC-006: Explicit error handling ✅

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated: 2026-02-07T05:30:00Z*
