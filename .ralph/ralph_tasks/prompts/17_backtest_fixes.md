# Task 17: Backtest Fixes - Implementation Prompt

## Objective
Fix bugs and add validation utilities to the backtesting engine to ensure
accurate P&L calculations and drawdown metrics.

## Context
The backtesting engine is critical for strategy validation. Issues with P&L
calculations or drawdown metrics can lead to incorrect strategy assessment
and poor trading decisions.

## Implementation Steps

### 1. Create P&L Validator
- File: `app/backtesting/validation/pnl_validator.py`
- Validates individual trade P&L calculations
- Checks commission calculations are reasonable
- Validates total P&L matches sum of trades
- Ensures capital consistency

### 2. Create Drawdown Validator
- File: `app/backtesting/validation/drawdown_validator.py`
- Validates max drawdown calculations
- Checks drawdown is always negative (or zero)
- Validates drawdown recovery tracking
- Provides comprehensive drawdown statistics

### 3. Update Package Exports
- File: `app/backtesting/validation/__init__.py`
- Export validators and error classes

### 4. Create Tests
- File: `tests/unit/backtesting/test_pnl_validator.py`
- File: `tests/unit/backtesting/test_drawdown_validator.py`
- Comprehensive test coverage for all validation functions

### 5. Validate Implementation
- Compile all new files
- Run all tests
- Ensure 100% pass rate

## Existing Code Notes

### Already Fixed (performance_calculator.py:147)
The Sharpe ratio calculation in performance_calculator.py already has a
CRITICAL BUG FIX applied (line 147). The implementation now correctly:
1. Builds equity curve from closed trades
2. Calculates period-over-period returns
3. Properly annualizes the Sharpe ratio

### Known TODOs (Lower Priority)
- `baseline_optimization_reporter.py:293` - PDF generation (not critical)
- `market_impact.py:416` - Regression calibration (advanced feature)

## Success Criteria
- All validators pass with correct data
- All validators fail with incorrect data
- Test coverage > 90%
- No compilation errors

## Output
Event: `backtest_fixes.complete` with task details
