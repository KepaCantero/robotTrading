# report_generator.py

## Purpose
Generates HTML reports for batch backtesting results. Handles report creation and data export to multiple formats.

---

## Type Definitions / Data Classes

### ReportGenerator Class
```python
class ReportGenerator:
    output_dir: Path                    # REQUIRED - Directory for report files
```

**Validation Rules:**
- `output_dir` must be valid directory path
- `output_dir` is created if it doesn't exist (parents=True, exist_ok=True)

---

## Function Signatures (Contracts)

### `ReportGenerator.__init__(output_dir: Path) -> None`
**Pre:** output_dir must be valid path
**Post:** ReportGenerator initialized with output_dir created
**Raises:** OSError if directory creation fails
**Retry:** No
**Side Effects:** Creates output_dir with parents=True, exist_ok=True

### `ReportGenerator.generate_comparison_report(results: Dict[str, Any]) -> str`
**Pre:** results must be dict of profile_id to ProfileResult
**Post:** Returns HTML report string and saves to file
**Raises:** Exception on template rendering failure
**Retry:** No
**Side Effects:** Creates HTML file in output_dir with timestamp

### `ReportGenerator._group_best_strategies(results_list: List[Any]) -> List[Dict[str, Any]]`
**Pre:** results_list must contain ProfileResult objects
**Post:** Returns list of best strategies grouped by objective
**Raises:** No (handles empty results)
**Retry:** No
**Side Effects:** None (groups results in memory)

### `ReportGenerator.generate_batch_summary(results: Dict[str, Any], fallback_metrics: Dict[str, int]) -> None`
**Pre:** results must be dict of ProfileResult, fallback_metrics must be dict
**Post:** Creates batch summary JSON file
**Raises:** No (JSON dump errors handled)
**Retry:** No
**Side Effects:** Creates JSON file with timestamp

### `ReportGenerator.export_results(results: Dict[str, Any], format: str = "json") -> Path`
**Pre:** results must be dict, format must be "json" | "csv" | "excel"
**Post:** Returns path to exported file
**Raises:** ValueError on unsupported format
**Retry:** No
**Side Effects:** Creates export file (JSON, CSV, or Excel)

### `ReportGenerator._export_json(results: Dict[str, Any], timestamp: str) -> Path`
**Pre:** results must be dict, timestamp must be string
**Post:** Returns path to JSON file
**Raises:** No
**Retry:** No
**Side Effects:** Creates JSON file with timestamp

### `ReportGenerator._export_csv(results: Dict[str, Any], timestamp: str) -> Path`
**Pre:** results must be dict, timestamp must be string
**Post:** Returns path to CSV file
**Raises:** No
**Retry:** No
**Side Effects:** Creates CSV file with timestamp

### `ReportGenerator._export_excel(results: Dict[str, Any], timestamp: str) -> Path`
**Pre:** results must be dict, timestamp must be string
**Post:** Returns path to Excel file
**Raises:** No
**Retry:** No
**Side Effects:** Creates Excel file with multiple sheets

### `ReportGenerator._result_to_dict(result: Any) -> Dict[str, Any]`
**Pre:** result must be ProfileResult object
**Post:** Returns dictionary representation of result
**Raises:** No
**Retry:** No
**Side Effects:** None (converts to dict)

### `ReportGenerator._get_html_template() -> str`
**Pre:** None
**Post:** Returns HTML template string
**Raises:** No
**Retry:** No
**Side Effects:** None (returns static template)

---

## Acceptance Criteria
- [ ] generate_comparison_report() creates HTML file with timestamp
- [ ] generate_comparison_report() calculates summary stats (ready_count, avg_sharpe_imp, etc.)
- [ ] generate_comparison_report() aggregates parameter importance
- [ ] generate_comparison_report() groups best strategies by objective
- [ ] generate_comparison_report() uses Jinja2 for template rendering
- [ ] _group_best_strategies() groups by (risk_tolerance, capital_flag)
- [ ] _group_best_strategies() selects best by optimized_sharpe
- [ ] generate_batch_summary() creates JSON file with timestamp
- [ ] generate_batch_summary() includes fallback_metrics
- [ ] export_results() with format="json" calls _export_json
- [ ] export_results() with format="csv" calls _export_csv
- [ ] export_results() with format="excel" calls _export_excel
- [ ] export_results() raises ValueError for unsupported format
- [ ] _export_csv() flattens nested results with prefixes (opt_, imp_)
- [ ] _export_excel() creates Summary sheet + one sheet per objective
- [ ] _export_excel() truncates sheet names to 31 chars (Excel limit)
- [ ] _get_html_template() includes all required CSS and HTML structure
- [ ] All output files include timestamp in filename

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - No mutable defaults |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Minimal error logging |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ PARTIAL - Some functions lack error handling |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure/presentation layer |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Report generation only |
| LOG-001 | BASE_RULES.md | Structured logging | ⚠️ GAP - Uses basic logging, not structlog |
| QL-007 | BASE_RULES.md | Max 7 parameters | ✅ OK - All functions under limit |
| CC-007 | BASE_RULES.md | Small functions | ❌ GAP - _get_html_template() is 147 lines (inline HTML) |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** json, logging, datetime, pathlib, typing, numpy, pandas, jinja2
- **Internal:**
  - `app.core.models.input_profile.ObjectivoInversion`

---

## Required Tests
- **tests/backtesting/profile_batch/test_report_generator.py:**
  - Test __init__() creates output directory
  - Test generate_comparison_report() creates HTML file
  - Test generate_comparison_report() calculates correct summary stats
  - Test generate_comparison_report() aggregates parameter importance
  - Test generate_comparison_report() groups by objective
  - Test _group_best_strategies() selects best by sharpe ratio
  - Test _group_best_strategies() handles empty results
  - Test generate_batch_summary() includes fallback_metrics
  - Test generate_batch_summary() calculates average improvements
  - Test export_results() with format="json"
  - Test export_results() with format="csv"
  - Test export_results() with format="excel"
  - Test export_results() raises ValueError for invalid format
  - Test _export_csv() prefixes nested fields (opt_, imp_)
  - Test _export_excel() creates multiple sheets
  - Test _export_excel() truncates sheet names to 31 chars
  - Test _result_to_dict() includes all required fields
  - Test _get_html_template() returns valid HTML
  - Test all output files include timestamp in filename

---

## Notes
- HTML template is inline (147 lines) - consider extracting to separate template file
- Filename pattern: comparison_report_YYYYMMDD_HHMMSS.html
- Batch summary filename: batch_summary_YYYYMMDD_HHMMSS.json
- Export filename pattern: profile_batch_results_YYYYMMDD_HHMMSS.{json|csv|xlsx}
- Excel sheet names limited to 31 characters (Excel limitation)
- HTML template uses CSS Grid for responsive layout
- Parameter importance visualized with progress bars
- Best strategies grouped by objective, then risk_tier and capital_flag
- All timestamps use datetime.now().strftime('%Y%m%d_%H%M%S')
- Pandas DataFrame.to_excel() uses openpyxl engine
