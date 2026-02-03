# report_generator.py

## Purpose
Generates comprehensive, auditable backtest reports with executive summary, technical analysis, risk metrics, performance attribution, and improvement recommendations.

---

## Type Definitions / Data Classes

### BacktestReportGenerator Class
```python
class BacktestReportGenerator:
    output_dir: Path                    # REQUIRED - Directory for saving reports
```

**Validation Rules:**
- `output_dir` must be writable
- Creates directory if not exists using `mkdir(parents=True, exist_ok=True)`
- Raises `OSError` if directory creation fails

---

## Function Signatures (Contracts)

### `__init__(output_dir: Path) -> None`
**Pre:** output_dir is valid path or can be created
**Post:** Output directory exists and is writable
**Raises:** OSError if directory cannot be created
**Retry:** ❌ No
**Side Effects:** Creates filesystem directory, logs initialization

### `generate_comprehensive_report(result: BacktestResult, config: BacktestConfig, backtest_id: str) -> Dict[str, Path]`
**Pre:** result.performance is not None
**Post:** Creates 5 report files and returns dict with paths
**Raises:** ValueError if performance data is None, IOError if file write fails
**Retry:** ❌ No
**Side Effects:** Writes to filesystem (5 files: executive.md, technical.md, risk.md, metrics.json, recommendations.md)

### `_generate_executive_summary(result: BacktestResult, config: BacktestConfig) -> str`
**Pre:** result.performance exists
**Post:** Returns formatted markdown string with executive summary
**Raises:** None (returns string on error)
**Retry:** ❌ No
**Side Effects:** None

### `_generate_technical_analysis(result: BacktestResult, config: BacktestConfig) -> str`
**Pre:** result.performance exists
**Post:** Returns formatted markdown with technical metrics
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_generate_risk_analysis(result: BacktestResult, config: BacktestConfig) -> str`
**Pre:** result.performance exists
**Post:** Returns formatted markdown with risk analysis
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_generate_recommendations(result: BacktestResult, config: BacktestConfig, metrics: Dict[str, Any]) -> str`
**Pre:** result has valid performance data
**Post:** Returns markdown with prioritized recommendations
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_calculate_cagr(result: BacktestResult) -> float`
**Pre:** result has valid start_date, end_date, final_capital, initial_capital
**Post:** Returns Compound Annual Growth Rate as percentage
**Raises:** None (returns 0.0 on invalid data)
**Retry:** ❌ No
**Side Effects:** None

### `_calculate_kelly(perf: PerformanceMetrics) -> float`
**Pre:** perf has win_rate, avg_win, avg_loss
**Post:** Returns Kelly Criterion percentage
**Raises:** None (returns 0.0 on invalid data)
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] No hardcoded secrets or sensitive data (SEC-001)
- [ ] All file operations use context managers (FMT-008)
- [ ] Error logging for all exceptions with context (LOG-004)
- [ ] Performance data validation before report generation (TRD-005)
- [ ] CAGR calculation uses correct formula: (final/initial)^(1/years) - 1
- [ ] Kelly Criterion handles division by zero (avg_loss <= 0)
- [ ] Report files are created with UTF-8 encoding
- [ ] Metrics JSON is serializable (all values convertible to float/int/str)
- [ ] File naming includes timestamp for uniqueness

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
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - 2026-02-03 - Created proper TypedDict definitionsDict[str, Any]` in `_extract_detailed_metrics` |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-006 | BASE_RULES.md | Add execution time for operations | ✅ FIXED - 2026-02-03 - Added structured timing logs with duration_seconds for all operations |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK |
| FMT-008 | BASE_RULES.md | Context managers for file operations | ✅ OK |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK |
| CC-007 | BASE_RULES.md | Functions < 50 lines | ⚠️ NOT APPLIED - Template generation inherently long |
| TRD-004 | BASE_RULES.md | Audit trail | ✅ OK - Reports provide audit trail |
| TRD-005 | BASE_RULES.md | Price/performance validation | ✅ OK |
| BT-004 | BASE_RULES.md | Realistic costs in reports | ✅ OK |

**GAP Violations Found:**

1. **TYP-003** (P1 - High): Uses `Any` type in `_extract_detailed_metrics` return
   - **Location**: Line 508: `def _extract_detailed_metrics(...) -> Dict[str, Any]`
   - **Fix**: Define specific schema:
   ```python
   def _extract_detailed_metrics(...) -> Dict[str, float | str | None | Dict[str, float | None]]:
   ```

2. **CRITICAL BUG** (P0): CAGR calculation error on line 428
   - **Current**: `((result.final_capital / result.final_capital) ** (1 / years) - 1) * 100`
   - **Issue**: Divides by itself, always returns 0
   - **Fix**: Should be `result.initial_capital` in denominator
   ```python
   ((result.final_capital / result.initial_capital) ** (1 / years) - 1) * 100
   ```

3. **Incomplete Implementation** (P1): Placeholder methods
   - **Methods**: `_analyze_trade_distribution`, `_analyze_market_conditions`, `_analyze_trade_risks`, `_analyze_stop_losses`, `_analyze_position_sizing`, `_analyze_correlations`
   - **Issue**: Return static placeholder strings
   - **Fix**: Implement actual analysis or document as TODO

**FIXED VIOLATIONS:**

✅ **TYP-003** (P1 - High): Dict[str, Any] replaced with proper TypedDict definitions - FIXED 2026-02-03
   - **Fixed**: Created specific TypedDict classes for all return types

✅ **LOG-006** (P2 - Medium): Missing execution time logging - FIXED 2026-02-03
   - **Fixed**: Added structured timing logs for all operations with operation name, duration_seconds, and backtest_id
   - **Implementation**: Each report generation section now logs completion time using `logger.info()` with structured `extra` parameter

---

## Dependencies
- **External:** pathlib, json, logging, datetime, typing (stdlib)
- **Internal:**
  - `app.backtesting.models.BacktestConfig`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.models.PerformanceMetrics`

---

## Required Tests
- **tests/unit/backtesting/test_report_generator.py:**
  - Test successful report generation with valid data (5 files created)
  - Test error handling when performance data is None (raises ValueError)
  - Test CAGR calculation with various date ranges
  - Test CAGR calculation bug fix (final/initial not final/final)
  - Test Kelly Criterion with edge cases (zero loss, zero win rate)
  - Test file creation and write permissions
  - Test JSON serialization of metrics
  - Test encoding (UTF-8) for international characters
  - Test recommendation generation for different performance scenarios
  - Test file naming includes timestamp
  - Test logging includes structured context

---

## Notes
- **Critical Bug**: Line 428 has CAGR calculation bug - uses `result.final_capital / result.final_capital` instead of `result.final_capital / result.initial_capital`
- **Placeholder Methods**: Several analysis methods return placeholder strings indicating incomplete implementation
- **Metric Extraction**: `_extract_detailed_metrics` properly handles Optional fields with None checks
- **Report Format**: Generates markdown (.md) for human-readable reports and JSON for machine-readable metrics
