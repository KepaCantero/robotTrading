# Requirements: services/reporting_generator/reporting_generator.py

## Source File Analysis
- **File Path**: `app/services/reporting_generator/reporting_generator.py`
- **Lines of Code**: 568
- **Language**: Python 3
- **Purpose**: Main reporting generator orchestrating all reporting components

## Purpose
Main service for generating comprehensive trading strategy reports:
- Combines pyfolio and quantstats metrics
- Generates HTML/PDF reports
- Creates visualizations
- Handles delivery
- Supports multiple output formats

## Dependencies
- **Internal**:
  - `app.services.reporting_generator.pyfolio_integrator.PyfolioIntegrator`
  - `app.services.reporting_generator.quantstats_integrator.QuantstatsIntegrator`
  - `app.services.reporting_generator.visualization_generator.VisualizationGenerator`
  - `app.services.reporting_generator.delivery_manager.ReportDeliveryManager`
- **External**:
  - `pandas` - Data manipulation
  - `asyncio` - Async operations
  - `logging` - Logging
  - `typing` - Type hints

## Classes/Functions

### ReportingGenerator
- **Purpose**: Main reporting orchestrator
- **Key Methods**:
  - `generate_full_report()` - Complete report with all metrics
  - `generate_quick_report()` - Quick summary report
  - `generate_comparison_report()` - Compare multiple strategies
  - `generate_backtest_report()` - Backtest-specific report
  - `schedule_report()` - Schedule periodic reports
  - `deliver_report()` - Deliver via configured channels

### ReportType (Enum)
- FULL - Complete analysis
- QUICK - Summary only
- COMPARISON - Strategy comparison
- BACKTEST - Backtest results
- LIVE - Live trading performance

## Business Logic

### Report Generation Flow
1. Collect data (trades, returns, positions)
2. Calculate metrics (pyfolio + quantstats)
3. Generate visualizations
4. Create HTML report
5. Convert to PDF if needed
6. Deliver to recipients

### Metrics Included
- Return metrics (total, annual, monthly)
- Risk metrics (volatility, drawdown, VaR)
- Risk-adjusted returns (Sharpe, Sortino, Calmar)
- Trade statistics (win rate, profit factor)
- Portfolio analytics (allocation, turnover)

## Data Models
- ReportRequest - Input specification
- ReportResponse - Generated report
- ReportMetadata - Report metadata

## API Contracts
```python
async def generate_full_report(
    strategy_name: str,
    backtest_results: Dict,
    include_visualizations: bool = True,
    output_format: str = "html"
) -> ReportResponse
```

## Error Handling
- Validates inputs
- Handles missing data gracefully
- Comprehensive error logging
- Returns partial results on error

## Performance Considerations
- Async for parallel metric calculation
- Caching for expensive operations
- Streaming for large reports

## Testing Strategy
- Test full report generation
- Test with missing data
- Test output formats
- Test delivery

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used
- FMT-007: No mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-005: Dataclasses typed

### Async
- ASYNC-001: Proper async/await
- ASYNC-004: No blocking calls

### Clean Code
- CC-001: Descriptive names
- CC-006: Error handling
- CC-007: Reasonable function length

## Audit Status
**Status**: PASSED

### Strengths
1. Comprehensive reporting functionality
2. Good async implementation
3. Type hints throughout
4. Proper error handling
5. Multiple output formats

### Minor Observations
1. Could add more input validation
2. Some long functions could be split

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready reporting system

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0080*
*Status: PASSED*
