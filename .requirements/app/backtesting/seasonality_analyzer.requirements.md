# seasonality_analyzer.py

## Purpose
Seasonality analysis for strategy returns - monthly/quarterly patterns, seasonal decomposition, best/worst periods identification, seasonality strength calculation, and markdown report generation.

---

## Type Definitions / Data Classes

None - uses pandas for grouping and aggregation, no custom dataclasses.

---

## Function Signatures (Contracts)

### `SeasonalityAnalyzer.__init__(min_data_points: int = 60) -> None`
**Pre:** `min_data_points` >= 12 (minimum 1 year of monthly data)
**Post:** Analyzer initialized with minimum data threshold
**Raises:** None
**Retry:** No
**Side Effects:** None (initialization only)

### `SeasonalityAnalyzer.analyze_monthly_returns(equity_curve: List[Tuple[datetime, Decimal]]) -> Optional[Dict]`
**Pre:** `equity_curve` has >= 12 (datetime, equity) tuples
**Post:** Returns dict with month_stats (12 months), best_month, worst_month, overall_avg_return
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None (analysis only)

### `SeasonalityAnalyzer.analyze_quarterly_returns(equity_curve: List[Tuple[datetime, Decimal]]) -> Optional[Dict]`
**Pre:** `equity_curve` has >= 63 tuples (~5 years of quarterly data)
**Post:** Returns dict with quarter_stats (4 quarters), best_quarter, worst_quarter, overall_avg_return
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None (analysis only)

### `SeasonalityAnalyzer.get_best_worst_months(equity_curve: List[Tuple[datetime, Decimal]]) -> Optional[Dict[str, List]]`
**Pre:** `equity_curve` has >= 12 tuples
**Post:** Returns dict with best_months (top 3), worst_months (bottom 3), all_months_ranked
**Raises:** Returns None on error or insufficient data
**Retry:** No
**Side Effects:** None (calls analyze_monthly_returns internally)

### `SeasonalityAnalyzer.get_seasonality_strength(equity_curve: List[Tuple[datetime, Decimal]]) -> Optional[Decimal]`
**Pre:** `equity_curve` has >= 12 tuples
**Post:** Returns seasonality strength (0-1) or None; 0=no seasonality, 1=perfect seasonality
**Raises:** Returns None on error
**Retry:** No
**Side Effects:** None (calls analyze_monthly_returns internally)

### `SeasonalityAnalyzer.decompose_returns(equity_curve: List[Tuple[datetime, Decimal]], method: str = 'additive') -> Optional[Dict]`
**Pre:** `equity_curve` has >= 24 tuples (2 years for decomposition)
**Post:** Returns dict with trend, seasonal, residual components; uses statsmodels or fallback
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None (calls statsmodels.tsa.seasonal.seasonal_decompose or fallback)

### `SeasonalityAnalyzer.generate_seasonality_report(equity_curve: List[Tuple[datetime, Decimal]], strategy_name: str = "Strategy") -> str`
**Pre:** `equity_curve` has >= 12 tuples
**Post:** Returns markdown formatted report with monthly/quarterly tables, insights
**Raises:** Returns error message string on exception
**Retry:** No
**Side Effects:** None (generates report string)

### `SeasonalityAnalyzer._month_name(month: int) -> str` (static)
**Pre:** `month` in [1, 12]
**Post:** Returns full month name (e.g., "January")
**Raises:** Returns "Month {month}" if out of range
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Monthly analysis: 12 months with avg_return, median_return, std_dev, win_rate
- [ ] Quarterly analysis: 4 quarters with same metrics as monthly
- [ ] Best/worst identification: highest/lowest cumulative returns
- [ ] Seasonality strength: 0-1 scale based on coefficient of variation
- [ ] Seasonal decomposition: trend + seasonal + residual components
- [ ] Statsmodels seasonal_decompose with fallback implementation
- [ ] Markdown report: tables, best/worst periods, insights
- [ ] Minimum data requirements: 12 months, 63 quarters, 24 months for decomposition
- [ ] Win rate calculation: positive_count / total_count
- [ ] Cumulative return: `(1 + daily_returns).prod() - 1`
- [ ] All methods return None on insufficient data
- [ ] Error handling with logging
- [ ] Datetime conversion and sorting

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-005 | BASE_RULES.md | Test across different market regimes | ✅ OK - Seasonality captures time patterns |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | Log all exceptions | ✅ OK - logger.error in except blocks |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have hints |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each method analyzes one aspect |
| ARCH-004 | BASE_RULES.md | Small functions | ⚠️ PARTIAL - generate_report > 20 lines |
| DP-006 | BASE_RULES.md | Builder pattern for complex objects | ⚠️ NOT APPLIED - Not applicable |

**NOTE:** All 96 BASE_RULES apply. Critical for seasonality:
- **BT-005:** Seasonality analysis prevents overfitting to specific time periods
- **CC-006:** Explicit error handling prevents silent failures in time series analysis
- **LOG-004:** Logging helps debug time series parsing issues

---

## Dependencies
- **External:** `numpy`, `pandas`, `datetime`, `decimal` (Decimal), `logging`, `typing` (Dict, List, Optional, Tuple)
- **External (optional):** `statsmodels.tsa.seasonal` (seasonal_decompose) - with fallback
- **Internal:** `app.core.statsmodels_fallback` (seasonal_decompose) as fallback

---

## Required Tests
- **tests/backtesting/test_seasonality_analyzer.py:**
  - Test monthly returns analysis with 12+ months of data
  - Test monthly returns with insufficient data (< 12 months)
  - Test quarterly returns analysis with 5+ years of data
  - Test quarterly returns with insufficient data
  - Test best/worst months identification
  - Test seasonality strength calculation (0-1 range)
  - Test seasonal decomposition with statsmodels
  - Test seasonal decomposition with fallback (no statsmodels)
  - Test seasonal decomposition with insufficient data
  - Test markdown report generation
  - Test report includes all sections (monthly, quarterly, strength, insights)
  - Test _month_name static method
  - Test win rate calculation
  - Test cumulative return calculation
  - Test datetime conversion and sorting
  - Test error handling for invalid data
  - Test logging on errors

---

## Notes
- Module purpose: PHASE 4 MODULE 7 PHASE 2 of backtesting system
- Seasonality: time-based patterns in returns (month-of-year, quarter effects)
- Monthly analysis: groups returns by month (January, February, etc.)
- Quarterly analysis: groups returns by quarter (Q1, Q2, Q3, Q4)
- Seasonality strength: normalized measure of seasonal variation
  - < 0.1: very weak, 0.1-0.3: weak, 0.3-0.6: moderate, > 0.6: strong
- Decomposition: separates time series into trend (long-term), seasonal (repeating), residual (noise)
- Additive decomposition: `y = trend + seasonal + residual`
- Multiplicative decomposition: `y = trend * seasonal * residual`
- Statsmodels fallback: uses app.core.statsmodels_fallback if statsmodels not available
- Markdown report: human-readable summary with tables and insights
- All analyses require minimum data points (prevents unreliable statistics)
- Win rate: proportion of positive return periods
- Cumulative return: total return over period (compounded)
- Datetime sorting: ensures chronological order before analysis
- Error handling: returns None or error message string, logs exceptions
