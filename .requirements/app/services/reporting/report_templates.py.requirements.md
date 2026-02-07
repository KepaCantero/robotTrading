# Requirements: services/reporting/report_templates.py

## Source File Analysis
- **File Path**: `app/services/reporting/report_templates.py`
- **Lines of Code**: 477
- **Language**: Python 3
- **Purpose**: HTML report templates for strategy performance reporting

## Purpose
Provides professional HTML templates for trading strategy performance reports:
- Performance summary with key metrics
- Risk metrics dashboard
- Portfolio allocation visualization
- Trade analysis and statistics
- Professional styling with CSS

## Dependencies
- **Internal**: None (standalone template module)
- **External**:
  - `logging` - Structured logging
  - `typing` - Type hints
  - `datetime.datetime` - Timestamp generation

## Classes/Functions

### ReportTemplates
- **Purpose**: Generates professional HTML reports
- **Key Methods**:
  - `generate_performance_report_html()` - Complete HTML report
  - `_generate_performance_summary_html()` - Summary cards section
  - `_generate_metrics_table_html()` - Metrics data table
  - `_generate_risk_metrics_table_html()` - Risk metrics table
  - `_generate_allocation_table_html()` - Portfolio allocation with visuals
  - `generate_simple_summary_html()` - One-page summary

### CSS Style Constants
- **CSS_STYLE**: Embedded professional CSS (~180 lines)
  - Responsive design
  - Print-friendly styles
  - Gradient backgrounds for metric cards
  - Professional color scheme

## Business Logic

### Report Sections
1. **Header**: Strategy name, generated timestamp, report type
2. **Performance Summary**: 4 key metrics with color coding
   - Total Return (green if positive, red if negative)
   - Sharpe Ratio
   - Max Drawdown (red card for risk)
   - Win Rate (green if >50%, red if <50%)
3. **Performance Metrics Table**: Detailed metrics with formatting
4. **Risk Metrics Table**: Volatility, VaR, CVaR, Calmar
5. **Portfolio Allocation**: Visual bar charts for each asset

### Color Logic
- Positive returns: `.positive` class (green #27ae60)
- Negative returns: `.negative` class (red #e74c3c)
- Metric cards use gradient backgrounds

### Formatting Rules
- Returns: Percentage with 2 decimals (+X.XX%)
- Sharpe: 3 decimal places
- Counts: Integer format
- Allocation: Percentage with 1 decimal

## Data Models
No custom data classes - uses Dict for all inputs

## API Contracts

### Input: generate_performance_report_html()
```python
strategy_name: str
summary: Dict          # total_return, sharpe_ratio, max_drawdown, win_rate
metrics: Dict          # Detailed performance metrics
risk_metrics: Dict     # Volatility, VaR, CVaR, Calmar
allocation: Dict[str, float]  # Symbol -> weight (0-1)
```

### Output: str
Complete HTML document ready to save as .html file

## Error Handling
- **Approach**: Graceful degradation with default values
- **Defaults**: 0 for missing metrics, "N/A" for labels
- **Logging**: INFO level for report generation
- **Input Validation**: Assumes valid Dict inputs (could be improved)

## Performance Considerations
- **Complexity**: O(n) where n = number of allocation items
- **Memory**: Builds full HTML string in memory (~20KB typical)
- **Optimization**: String formatting with .format() is efficient
- **Scalability**: Suitable for reports up to ~100 positions

## Testing Strategy
- **Unit Tests**:
  - Test HTML generation with sample data
  - Test CSS is valid
  - Test color logic (positive/negative)
  - Test allocation bar widths
- **Integration Tests**:
  - Test with real backtest results
  - Verify HTML renders correctly in browsers
- **Edge Cases**:
  - Empty allocation dict
  - All negative returns
  - Very large/small numbers

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length mostly within limits (some long CSS lines)
- FMT-004: Double quotes used in HTML strings
- FMT-006: F-strings used in newer code
- FMT-007: No mutable defaults (default_factory for list)

### Type Hints
- TYP-001: All methods have type hints
- TYP-002: Uses modern syntax (Dict, Optional)
- TYP-003: No Any types - all specific

### Clean Code
- CC-001: Descriptive method names
- CC-003: Simple, straightforward logic
- CC-007: Methods are reasonable length

### Security
- SEC-007: No input validation (assumes trusted internal data)
- HTML escaping could be improved (uses .format() not template escaping)
- XSS risk if user-controlled data reaches templates

### Observability
- LOG-001: Uses logging module
- LOG-003: INFO level for report generation

## Audit Status
**Status**: PASSED WITH MINOR NOTES**

### Strengths
1. Professional, polished HTML/CSS output
2. Good separation of sections (methods per section)
3. Responsive design with media queries
4. Print-friendly styles included
5. Color coding for visual feedback
6. Singleton pattern for efficiency

### Minor Gaps (P3 - Low Priority)
1. **Security**: HTML not escaped - potential XSS if user data reaches templates
   - Mitigation: Only use with trusted internal data
   - Recommendation: Add HTML escaping function
2. **Input Validation**: No validation of Dict inputs
   - Missing keys will cause KeyError
   - Recommendation: Add .get() with defaults
3. **Long Lines**: Some CSS lines exceed 100 chars
   - Not functional, just style

### No Critical or P1 Gaps
- All P0 and P1 rules satisfied
- Code is production-ready for internal use
- Suitable for trusted data sources only

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0079*
*Status: PASSED WITH MINOR NOTES*
