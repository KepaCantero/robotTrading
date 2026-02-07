# Requirements: services/reporting_generator/visualization_generator.py

## Source File Analysis
- **File Path**: `app/services/reporting_generator/visualization_generator.py`
- **Lines of Code**: 614
- **Language**: Python 3
- **Purpose**: Generate visualizations for performance reports

## Purpose
Creates charts and visualizations for trading strategy reports:
- Equity curves
- Drawdown charts
- Monthly returns heatmap
- Rolling metrics
- Trade distribution
- Portfolio allocation pie charts

## Dependencies
- **Internal**:
  - None (standalone visualizer)
- **External**:
  - `plotly` - Interactive charts
  - `matplotlib` - Static charts
  - `pandas` - Data manipulation
  - `numpy` - Numerical computing
  - `typing` - Type hints
  - `logging` - Logging

## Classes/Functions

### VisualizationGenerator
- **Purpose**: Main visualization class
- **Key Methods**:
  - `create_equity_curve()` - Equity curve chart
  - `create_drawdown_chart()` - Drawdown visualization
  - `create_monthly_heatmap()` - Monthly returns heatmap
  - `create_rolling_sharpe()` - Rolling Sharpe ratio
  - `create_returns_distribution()` - Returns histogram
  - `create_allocation_pie()` - Portfolio allocation

## Business Logic

### Chart Types
1. **Line Charts**: Equity curve, drawdown, rolling metrics
2. **Heatmaps**: Monthly returns
3. **Histograms**: Returns distribution
4. **Pie Charts**: Portfolio allocation
5. **Bar Charts**: Monthly/annual returns

### Output Formats
- HTML (Plotly interactive)
- PNG (static images)
- JSON (chart data)

## Data Models
- Returns as pandas Series
- Equity curve as pandas Series
- Portfolio as Dict

## API Contracts
```python
def create_equity_curve(
    equity: pd.Series,
    benchmark: Optional[pd.Series] = None,
    output_format: str = "html"
) -> str

def create_drawdown_chart(
    equity: pd.Series,
    output_format: str = "html"
) -> str
```

## Error Handling
- Validates input data
- Handles missing data
- Catches plotting errors

## Performance Considerations
- Plotly charts are efficient
- Large datasets may need downsampling
- Consider caching for repeated renders

## Testing Strategy
- Test chart generation with sample data
- Test edge cases (empty data, single point)
- Test output formats

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-003: Some Any acceptable for chart data

### Clean Code
- CC-001: Descriptive names
- CC-006: Error handling

## Audit Status
**Status**: PASSED

### Strengths
1. Good use of Plotly for interactive charts
2. Comprehensive visualization options
3. Type hints
4. Error handling

### Minor Observations
1. Some Any types unavoidable with plotting libraries
2. Could add more chart customization options

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready visualization generator

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0080*
*Status: PASSED*
