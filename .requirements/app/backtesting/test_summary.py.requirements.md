# Requirements: backtesting/test_summary.py

## Source File Analysis
- **File Path**: `app/backtesting/test_summary.py`
- **Lines of Code**: 890
- **Module**: Backtesting - Test Reporting

## Purpose
Comprehensive test summary report generator for backtesting tests.

Captures and reports:
- Test metadata (name, description, type, ID, author, tags)
- Input data summary (symbols, date range, data points, market regime)
- Test configuration (capital, commission, slippage, strategy parameters)
- Output metrics (financial, risk, trade statistics, advanced metrics)
- Validation criteria results with pass/fail status
- Warnings, anomalies, and attachments
- Timing information (start, end, duration)

Generates both JSON (machine-readable) and human-readable text reports.

## Dependencies

### External Dependencies
- `pydantic` - Data validation with BaseModel
- `json` - JSON serialization
- `logging` - Structured logging
- `decimal` - Financial precision
- `pathlib.Path` - File path handling
- `datetime` - Timestamps

### Internal Dependencies
- None (self-contained test reporting module)

## Classes/Functions

### Pydantic Data Models
- `TestMetadata` - Test metadata (name, description, file, type, ID, author, tags)
- `InputDataSummary` - Input data (symbols, date range, data points, market regime, source)
- `TestConfig` - Test configuration (capital, commission, slippage, strategy, risk management)
- `OutputMetrics` - Output metrics (financial, risk, trade statistics, advanced metrics)
- `ValidationCriteria` - Validation criteria result (expected, actual, passed, tolerance, reason)
- `TestSummaryReport` - Complete test summary report (all sections combined)

### Main Classes
- `TestSummaryReporter` - Test summary reporter
  - `add_input_data()` - Add input data summary
  - `add_config()` - Add test configuration
  - `add_results()` - Add test results/metrics
  - `add_validation_criteria()` - Add validation criteria result
  - `add_warning()` - Add warning message
  - `add_anomaly()` - Add anomaly detection
  - `add_note()` - Add note to report
  - `add_attachment()` - Add attachment path
  - `mark_passed()` - Mark test as passed
  - `mark_failed()` - Mark test as failed
  - `generate_report()` - Generate complete TestSummaryReport
  - `save_reports()` - Save JSON and text reports
  - `_format_human_readable()` - Format report as human-readable text

### Convenience Functions
- `create_backtest_summary()` - Quick backtest summary creation

## Business Logic

### Report Generation Flow
1. Initialize TestSummaryReporter with test metadata
2. Add input data summary (symbols, dates, market regime)
3. Add test configuration (capital, costs, strategy)
4. Add output metrics (P&L, Sharpe, drawdown, etc.)
5. Add validation criteria with pass/fail
6. Mark test as passed or failed
7. Generate and save reports (JSON + text)

### Human-Readable Report Format
- Header with test name and status
- Metadata section
- Test status with duration
- Input data section
- Configuration section
- Output metrics (financial, risk, trade statistics, advanced)
- Validation criteria with checkmarks
- Warnings and anomalies
- Additional notes and attachments
- Footer with timestamp

### JSON Report Format
- Complete TestSummaryReport model_dump
- Machine-parseable for automated testing
- All fields included with proper types

## Data Models

### TestMetadata (Pydantic)
```python
test_name: str
test_description: str
test_file: str
test_type: str  # unit, integration, functional
test_id: Optional[str]
author: Optional[str]
tags: List[str]
created_at: datetime
```

### OutputMetrics (Pydantic)
```python
# Basic metrics
final_capital: Decimal
total_pnl: Decimal
total_pnl_percentage: Optional[Decimal]

# Risk metrics
sharpe_ratio: Optional[Decimal]
sortino_ratio: Optional[Decimal]
max_drawdown: Optional[Decimal]

# Trade metrics
win_rate: Optional[Decimal]
total_trades: int
winning_trades: int
losing_trades: int

# Advanced metrics
calmar_ratio: Optional[Decimal]
omega_ratio: Optional[Decimal]
profit_factor: Optional[Decimal]
expectancy: Optional[Decimal]

# Additional metrics
additional_metrics: Dict[str, Union[Decimal, float, int, str]]
```

## API Contracts

### Validation
- `initial_capital` must be > 0 (Pydantic validation)
- `commission` and `slippage` must be >= 0
- `total_trades` must be >= 0

### Required for Report Generation
- Input data (add_input_data must be called)
- Config (add_config must be called)
- Output (add_results must be called)
- Status (mark_passed or mark_failed must be called)

### File Output
- JSON: `{test_name}_{timestamp}.json`
- Text: `{test_name}_{timestamp}.txt`
- Default directory: `reports/test_summaries/`

## Error Handling
- `generate_report()` raises `ValueError` if required fields missing
- `save_reports()` raises `ValueError` if file operations fail
- All exceptions logged with context
- Graceful handling of missing optional fields

## Performance Considerations
- Reports generated in-memory before writing
- Large attachments handled via path references
- JSON serialization uses `default=str` for datetime/Decimal

## Testing Strategy
- Unit tests for each Pydantic model validation
- Test report generation with sample data
- Verify JSON round-trip (serialize/deserialize)
- Test human-readable formatting
- Edge cases: missing fields, invalid values

## Critical Rules (BASE_RULES.md)

### Compliance Status: ✅ PASSED

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports | ✅ PASS | All imports are absolute |
| R104 | No bare except | ✅ PASS | Uses `except Exception as e:` |
| R105 | No print statements | ✅ PASS | Uses `logger` throughout |
| R108 | Exception handling | ✅ PASS | Comprehensive error handling |
| R110 | Docstrings | ✅ PASS | Google-style docstrings for all classes/functions |
| R111 | No circular imports | ✅ PASS | No internal dependencies |

### Notes
- Pydantic models provide automatic validation
- Clear separation between data models and reporter logic
- Type hints use `Union` appropriately for flexible fields
- All optional fields properly typed

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T06:00:00Z |
| **Audit Status** | PASSED |
| **Auditor** | Ralph GAP Audit Automation |
| **Violations** | 0 critical violations |

---
*Generated on 2026-02-07T06:00:00Z*
