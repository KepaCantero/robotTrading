# professional_reporter.py

## Purpose
Generates institutional-quality backtesting reports including executive summary (1-page PDF) and complete interactive HTML with performance, risk, trades, and robustness analysis sections.

---

## Type Definitions / Data Classes

### ReportSection Class
```python
@dataclass
class ReportSection:
    title: str                    # REQUIRED - Section title
    content: str                  # REQUIRED - Markdown content
    charts: List[Dict[str, Any]]  # OPTIONAL - Chart data for visualization
```

**Validation Rules:**
- title must be non-empty string
- content can be empty for placeholder sections
- charts list contains dicts with 'type', 'title', 'data' keys

### ProfessionalReport Class
```python
@dataclass
class ProfessionalReport:
    strategy_name: str                          # REQUIRED - Strategy identifier
    timestamp: datetime                         # REQUIRED - Report generation timestamp
    period_start: datetime                      # REQUIRED - Backtest start date
    period_end: datetime                        # REQUIRED - Backtest end date
    backtest_result: Optional[BacktestResult]   # OPTIONAL - Complete backtest results
    walk_forward_results: Optional[List[ValidationWindow]]  # OPTIONAL - Walk-forward validation
    capital_scale_results: Optional[CapitalScaleAnalysisReport]  # OPTIONAL - Capital scalability
    acceptance_report: Optional[AcceptanceReport]  # OPTIONAL - Acceptance criteria results
    executive_summary: Optional[ReportSection]  # OPTIONAL - Executive summary section
    performance_section: Optional[ReportSection]  # OPTIONAL - Performance metrics section
    risk_section: Optional[ReportSection]       # OPTIONAL - Risk analysis section
    trades_section: Optional[ReportSection]     # OPTIONAL - Trades analysis section
    robustness_section: Optional[ReportSection] # OPTIONAL - Robustness analysis section
    survivorship_bias_warning: bool             # REQUIRED - Survivorship bias flag
    look_ahead_bias_warning: bool               # REQUIRED - Look-ahead bias flag
```

**Validation Rules:**
- strategy_name must be non-empty
- period_start < period_end
- At least one results section should be populated

---

## Function Signatures (Contracts)

### `generate_executive_summary(backtest_result, acceptance_report, benchmark_return) -> ReportSection`
**Pre:** backtest_result has valid performance data, acceptance_report has verdict
**Post:** Returns ReportSection with executive summary including KPIs, verdict, capital recommendation
**Raises:** ValueError if performance data is None
**Retry:** No
**Side Effects:** None (pure function)

### `generate_complete_report(backtest_result, acceptance_report, walk_forward_results, capital_scale_results, benchmark_return) -> ProfessionalReport`
**Pre:** backtest_result is complete with performance metrics
**Post:** Returns ProfessionalReport with all sections populated
**Raises:** ValueError if required data missing
**Retry:** No
**Side Effects:** None (pure function)

### `export_to_html(report) -> str`
**Pre:** report has at least executive_summary populated
**Post:** Returns valid HTML string with complete report structure
**Raises:** None (returns fallback HTML on error)
**Retry:** No
**Side Effects:** None (string generation)

### `_convert_markdown_tables_to_html(content) -> str`
**Pre:** content is markdown-formatted string
**Post:** Returns HTML with tables converted to <table> elements
**Raises:** None
**Retry:** No
**Side Effects:** None (string transformation)

---

## Acceptance Criteria
- [ ] Executive summary includes all required KPIs (CAGR, Sharpe, MaxDD, verdict, capital recommendation)
- [ ] HTML export produces valid, well-formed HTML5 with inline CSS
- [ ] Markdown tables are correctly converted to HTML tables with proper headers
- [ ] Verdict descriptions match APPROVED/REVISION/REJECTED states
- [ ] Capital recommendations are based on Sharpe > 1.5, max DD < 15%, profit factor > 1.5 thresholds
- [ ] Benchmark comparison shows strategy vs benchmark returns and excess return
- [ ] Equity chart data includes dates, strategy values, and benchmark values

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names for functions and variables | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage on all functions | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging with context | ⚠️ NOT APPLIED - Uses basic logging |
| BT-004 | BASE_RULES | Realistic costs and slippage in backtesting | ✅ OK - Handled by backtest engine |
| TRD-004 | BASE_RULES | Audit trail for all decisions | ⚠️ PARTIAL - Report provides audit but no logging of generation decisions |
| ARCH-004 | BASE_RULES | Functions < 20 lines ideally | ⚠️ NOT APPLIED - Some functions > 20 lines (HTML generation) |
| CC-006 | BASE_RULES | Explicit error handling | ❌ GAP - Missing specific exception handling for None performance data |

**NOTE:** This analysis considers all 96 base rules plus file-specific requirements.

---

## Dependencies
- **External:** logging, dataclasses, datetime, typing (stdlib)
- **Internal:**
  - `app.backtesting.acceptance_criteria.AcceptanceReport`
  - `app.backtesting.capital_scale_analyzer.CapitalScaleAnalysisReport`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.walk_forward_validator.ValidationWindow`

---

## Required Tests
- **tests/backtesting/test_professional_reporter.py:**
  - Test executive summary generation with APPROVED verdict
  - Test executive summary with REJECTED verdict
  - Test complete report generation with all sections
  - Test HTML export produces valid HTML
  - Test markdown table to HTML conversion
  - Test equity chart data preparation with benchmark
  - Test capital recommendation logic for all scenarios
  - Test verdict descriptions for all three states
  - Test robustness section with walk-forward results
  - Test robustness section with capital scale results

---

## Notes
Report generation is deterministic (no LLM/NLP) ensuring reproducible, auditable outputs for institutional trading requirements.
