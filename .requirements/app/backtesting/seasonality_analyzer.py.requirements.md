# Requirements: backtesting/seasonality_analyzer.py

## Source File Analysis
- **File Path**: `app/backtesting/seasonality_analyzer.py`
- **Lines of Code**: 505
- **Audit Status**: PASSED
- **Audit Date**: 2026-02-07T05:30:00Z

## Purpose
Seasonality Analyzer (Phase 4 Module 7 Phase 2). Analyzes seasonal patterns in strategy returns including monthly/quarterly return patterns, seasonal decomposition (additive/multiplicative), best/worst month identification, and seasonality strength index.

## Dependencies
- Internal:
  - `app.core.statsmodels_fallback` (fallback seasonal_decompose)
- External:
  - `logging` (for structured logging)
  - `datetime` (datetime)
  - `decimal` (Decimal)
  - `typing` (Dict, List, Optional, Tuple)
  - `numpy` (np)
  - `pandas` (pd)
  - `statsmodels.tsa.seasonal` (optional - with fallback)

## Classes/Functions
### Main Class
- `SeasonalityAnalyzer`: Analyzer for seasonal patterns in returns
  - `__init__(min_data_points)`: Initialize with minimum data requirement
  - `analyze_monthly_returns(equity_curve)`: Monthly return patterns
  - `analyze_quarterly_returns(equity_curve)`: Quarterly return patterns
  - `get_best_worst_months(equity_curve)`: Ranking of months
  - `get_seasonality_strength(equity_curve)`: Seasonality strength index (0-1)
  - `decompose_returns(equity_curve, method)`: Seasonal decomposition
  - `generate_seasonality_report(equity_curve, strategy_name)`: Markdown report
  - `_month_name(month)`: Static method for month name lookup

## Business Logic
- Monthly return pattern analysis (minimum 12 months required)
- Quarterly return analysis (minimum 5 years required)
- Seasonality strength index: measures variance explained by seasonal component (0=none, 1=perfect)
- Seasonal decomposition: trend, seasonal, and residual components
- Best/worst month identification
- Markdown report generation with insights
- Fallback implementation when statsmodels not available

## Data Models
- Input: `List[Tuple[datetime, Decimal]]` for equity curve
- Output: `Optional[Dict]` with statistics
- Monthly: avg_return, median_return, std_dev, cumulative_return, win rate
- Quarterly: same metrics as monthly
- Strength: `Decimal` in range 0-1

## API Contracts
- `analyze_monthly_returns(curve) -> Optional[Dict]`: Returns None if <12 months
- `analyze_quarterly_returns(curve) -> Optional[Dict]`: Returns None if <5 years
- `get_seasonality_strength(curve) -> Optional[Decimal]`: Returns 0-1 or None
- `decompose_returns(curve, method) -> Optional[Dict]`: Returns None if <24 months
- `generate_seasonality_report(curve, name) -> str`: Markdown formatted report

## Error Handling
- Specific exception handling: `(ValueError, TypeError, KeyError, AttributeError, IndexError, RuntimeError)`
- Graceful handling of insufficient data (returns None with warning)
- Try/except for statsmodels import with fallback
- Validates minimum data points before processing

## Performance Considerations
- O(n) for monthly/quarterly aggregations using pandas groupby
- O(n) for decomposition (depends on algorithm)
- Efficient pandas operations for time series
- Early return on insufficient data

## Testing Strategy
- Test monthly analysis with known datasets
- Test quarterly analysis
- Test seasonality strength calculation
- Test decomposition with/without statsmodels
- Test report generation
- Test edge cases (empty data, insufficient data)
- Test fallback behavior

## Compliance with BASE_RULES.md
- ✅ FMT-001: Line length ≤ 100
- ✅ TYP-001: 100% type coverage
- ✅ TYP-002: Modern type hints (Optional[T], List[T])
- ✅ TYP-003: Any used only in return type annotation context
- ✅ LOG-001: Uses logging module
- ✅ LOG-003: Appropriate log levels (warning, error)
- ✅ LOG-004: Error logging with context
- ✅ CC-006: Specific exception handling
- ✅ ARCH-004: Focused methods with single responsibility

## Trading-Specific Features
- Seasonality strength index for pattern detection
- Win rate calculation by month/quarter
- Cumulative return tracking
- Insight generation for strategy adjustment

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Audited on 2026-02-07T05:30:00Z - Status: PASSED*
