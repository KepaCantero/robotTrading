# Test Summary Reporting for Backtesting Tests

## Overview

The test summary reporting system provides comprehensive documentation of test execution, capturing input data, configuration, output metrics, and validation results. This helps verify what data was used, what tests returned, and whether results match expectations.

## Location

- **Module**: `/app/backtesting/test_summary.py`
- **Reports Directory**: `/reports/test_summaries/`

## Features

### Data Models

The system includes Pydantic models for structured data:

- **TestMetadata**: Test name, description, file, type, tags
- **InputDataSummary**: Symbols, date ranges, data points, market regime, data source
- **TestConfig**: Initial capital, commission, slippage, strategy parameters
- **OutputMetrics**: P&L, Sharpe ratio, win rate, drawdown, trades, advanced metrics
- **ValidationCriteria**: Expected vs actual values with pass/fail status
- **TestSummaryReport**: Complete report combining all above

### Report Formats

Each test generates two reports:

1. **JSON Report** (`test_name_YYYYMMDD_HHMMSS.json`)
   - Machine-readable format
   - Easy to parse and analyze
   - Contains all data structures

2. **Text Report** (`test_name_YYYYMMDD_HHMMSS.txt`)
   - Human-readable format
   - Formatted sections with clear structure
   - Easy to review manually

## Usage

### Basic Usage

```python
from app.backtesting.test_summary import TestSummaryReporter

# Create reporter
reporter = TestSummaryReporter(
    test_name="test_backtest_basic",
    test_description="Basic backtest with GBM data",
    test_file="test_backtest_basic.py",
    test_type="integration"
)

# Add input data
reporter.add_input_data(
    symbols=["AAPL"],
    date_range=(datetime(2023, 1, 1), datetime(2023, 12, 31)),
    data_points=500,
    market_regime="bullish",
    data_source="GBM simulation (drift=5%, vol=20%)",
    price_range=(Decimal("95.50"), Decimal("110.25"))
)

# Add configuration
reporter.add_config(
    initial_capital=Decimal("100000"),
    commission=Decimal("1.0"),
    slippage=Decimal("0.1"),
    strategy="SMA Crossover",
    strategy_params={"fast_period": 20, "slow_period": 50}
)

# Add results
reporter.add_results(
    final_capital=Decimal("115000"),
    total_pnl=Decimal("15000"),
    total_pnl_percentage=Decimal("15.0"),
    sharpe_ratio=Decimal("1.5"),
    max_drawdown=Decimal("-0.08"),
    win_rate=Decimal("60.0"),
    total_trades=50,
    winning_trades=30,
    losing_trades=20
)

# Add validation criteria
reporter.add_validation_criteria(
    criteria_name="Sharpe ratio threshold",
    expected_value=">= 1.0",
    actual_value="1.5",
    passed=True,
    reason="Sharpe ratio exceeds minimum threshold"
)

# Mark as passed
reporter.mark_passed("All metrics within acceptable ranges")

# Save reports
json_path, txt_path = reporter.save_reports()
```

### Adding Warnings and Anomalies

```python
# Add warning
reporter.add_warning("Low trade count: only 50 trades executed")

# Add anomaly
reporter.add_anomaly("Unexpected gap in data: 5-day period with no quotes")

# Add note
reporter.add_note("Test run with reduced data for faster execution")

# Add attachment (e.g., chart image)
reporter.add_attachment("/path/to/equity_curve.png")
```

### Convenience Function

For quick summary creation:

```python
from app.backtesting.test_summary import create_backtest_summary

reporter = create_backtest_summary(
    test_name="test_sma_crossover",
    symbols=["AAPL"],
    date_range=(datetime(2023, 1, 1), datetime(2023, 12, 31)),
    initial_capital=Decimal("100000"),
    final_capital=Decimal("115000"),
    total_pnl=Decimal("15000"),
    total_trades=50,
    passed=True,
    reason="All metrics acceptable",
    sharpe_ratio=Decimal("1.5"),
    win_rate=Decimal("60.0")
)

reporter.save_reports()
```

## Report Structure

### JSON Report

```json
{
  "metadata": {
    "test_name": "test_backtest_basic",
    "test_description": "Basic backtest with GBM data",
    "test_file": "test_backtest_basic.py",
    "test_type": "integration",
    "test_id": "test_20260126_120000",
    "created_at": "2026-01-26T12:00:00"
  },
  "input_data": {
    "symbols": ["AAPL"],
    "date_range": ["2023-01-01T00:00:00", "2023-12-31T00:00:00"],
    "data_points": 500,
    "market_regime": "bullish",
    "data_source": "GBM simulation (drift=5%, vol=20%)",
    "price_range": [95.50, 110.25]
  },
  "config": {
    "initial_capital": "100000",
    "commission": "1.0",
    "slippage": "0.1",
    "strategy": "SMA Crossover",
    "strategy_params": {"fast_period": 20, "slow_period": 50}
  },
  "output": {
    "final_capital": "115000",
    "total_pnl": "15000",
    "total_pnl_percentage": "15.0",
    "sharpe_ratio": "1.5",
    "max_drawdown": "-0.08",
    "win_rate": "60.0",
    "total_trades": 50
  },
  "validation_criteria": [...],
  "passed": true,
  "pass_reason": "All metrics within acceptable ranges",
  "warnings": [],
  "anomalies": [],
  "duration_seconds": 2.45
}
```

### Text Report

```
================================================================================
TEST SUMMARY REPORT: TEST_BACKTESTER_WITH_REALISTIC_DATA
================================================================================

## METADATA
----------------------------------------
Test Name:        test_backtester_with_realistic_data
Description:      Basic backtest with GBM data and SMA crossover strategy
Test File:        test_backtest_basic.py
Test Type:        integration
Test ID:          test_20260126_120000
Created:          2026-01-26 12:00:00

## TEST STATUS
----------------------------------------
✓ Status:          PASSED
Reason:           All assertions passed, backtest executed successfully
Duration:         2.45 seconds

## INPUT DATA
----------------------------------------
Symbols:          AAPL
Date Range:       2023-01-01 to 2023-12-31
Data Points:      500
Market Regime:    bullish
Data Source:      GBM simulation (drift=5%, vol=20%)
Price Range:      $95.50 - $110.25

## CONFIGURATION
----------------------------------------
Initial Capital:  $100,000.00
Commission:       $1.00 per trade
Slippage:         0.10%
Strategy:         SMA Crossover (20/50)
Strategy Parameters:
  fast_period: 20
  slow_period: 50
  min_slope: 0.001

## OUTPUT METRICS
----------------------------------------

### Financial Performance
Final Capital:     $115,000.00
Total P&L:        $15,000.00
Total Return:      15.00%

### Risk Metrics
Sharpe Ratio:      1.50
Max Drawdown:      $-8,000.00
Max Drawdown %:    -8.00%

### Trade Statistics
Total Trades:      50
Winning Trades:    30
Losing Trades:     20
Win Rate:          60.0%

## VALIDATION CRITERIA
----------------------------------------
✓ Final capital in range: PASSED
   Expected: 50000-150000
   Actual:   115000
   Reason: Final capital $115,000.00 is within realistic range

================================================================================
End of Report - Generated 2026-01-26 12:00:02
================================================================================
```

## Integration with Tests

### Example: Integration Test

```python
def test_backtester_with_realistic_data(self, realistic_quotes, realistic_signals, default_config):
    """Test backtest with realistic GBM data."""
    # Initialize summary reporter
    reporter = TestSummaryReporter(
        test_name="test_backtester_with_realistic_data",
        test_description="Basic backtest with GBM data and SMA crossover strategy",
        test_file="test_backtest_basic.py",
        test_type="integration",
    )

    # Run backtest
    backtester = SimpleBacktester(default_config)
    result = backtester.run_backtest(realistic_quotes, realistic_signals)

    # Add input data to summary
    reporter.add_input_data(
        symbols=["AAPL"],
        date_range=(realistic_quotes[0].timestamp, realistic_quotes[-1].timestamp),
        data_points=len(realistic_quotes),
        market_regime="bullish" if float(realistic_quotes[-1].close) > float(realistic_quotes[0].close) else "bearish",
        data_source="GBM simulation (drift=5%, vol=20%)",
    )

    # Add configuration to summary
    reporter.add_config(
        initial_capital=default_config.initial_capital,
        commission=default_config.commission_per_trade,
        slippage=default_config.slippage_percentage,
        strategy="SMA Crossover (20/50)",
    )

    # Run assertions
    assert Decimal("50000") <= result.final_capital <= Decimal("150000")

    # Add results to summary
    total_pnl = result.final_capital - default_config.initial_capital
    reporter.add_results(
        final_capital=result.final_capital,
        total_pnl=total_pnl,
        total_trades=result.performance.total_trades if result.performance else 0,
        sharpe_ratio=result.performance.sharpe_ratio if result.performance else None,
    )

    # Add validation criteria
    reporter.add_validation_criteria(
        criteria_name="Final capital in range",
        expected_value="50000-150000",
        actual_value=str(result.final_capital),
        passed=Decimal("50000") <= result.final_capital <= Decimal("150000"),
    )

    # Mark as passed and save
    reporter.mark_passed("All assertions passed, backtest executed successfully")
    try:
        reporter.save_reports()
    except Exception as e:
        # Don't fail test if reporting fails
        print(f"Warning: Failed to save test summary: {e}")
```

## Best Practices

1. **Always add input data**: Document what data was used (symbols, dates, source)
2. **Add configuration**: Record all test parameters (capital, commission, strategy)
3. **Add results**: Capture all metrics (P&L, Sharpe, win rate, drawdown)
4. **Use validation criteria**: Document expected vs actual values
5. **Handle exceptions**: Don't let reporting failures fail tests
6. **Add warnings**: Note any anomalies or issues during execution
7. **Be descriptive**: Use clear test names and descriptions

## Reading Test Summaries

### View All Summaries

```bash
ls -la reports/test_summaries/
```

### View Specific Summary

```bash
cat reports/test_summaries/test_backtest_basic_20260126_120000.txt
```

### Search for Failures

```bash
grep -l "FAILED" reports/test_summaries/*.txt
```

### Parse JSON Reports

```python
import json

with open("reports/test_summaries/test_backtest_basic_20260126_120000.json") as f:
    report = json.load(f)

# Access data
print(f"Test: {report['metadata']['test_name']}")
print(f"Passed: {report['passed']}")
print(f"Final Capital: ${report['output']['final_capital']}")
print(f"Sharpe Ratio: {report['output']['sharpe_ratio']}")
```

## Troubleshooting

### Reports Not Generated

1. Check directory permissions: `reports/test_summaries/` must be writable
2. Verify import: `from app.backtesting.test_summary import TestSummaryReporter`
3. Check save_reports() is called

### Missing Data in Reports

1. Ensure all add_* methods are called before save_reports()
2. Verify mark_passed() or mark_failed() is called
3. Check for exceptions during report generation

## Files Updated with Summary Reporting

1. **tests/integration/backtesting/test_backtest_basic.py**
   - Added summary reporting to `test_backtester_with_realistic_data`

2. **tests/integration/backtesting/test_capital_scaling.py**
   - Added summary reporting to `test_full_pipeline_without_mocks`

3. **tests/integration/backtesting/test_strategy_validation.py**
   - Added summary reporting to dataset integrity tests

## Future Enhancements

- HTML report generation with charts
- Database storage for historical analysis
- Comparison reports (test vs baseline)
- CI/CD integration for automated reporting
- Dashboard for viewing all test summaries
