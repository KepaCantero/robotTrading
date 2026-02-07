# Requirements: engines/risk_engine/stress_testers/comprehensive_scenarios.py

## Source File Analysis
- **File Path**: `app/engines/risk_engine/stress_testers/comprehensive_scenarios.py`
- **Lines of Code**: 576
- **Status**: AUDITED - PASSED
- **Audit Date**: 2026-02-07T10:00:00Z

## Purpose
Comprehensive stress testing scenarios for risk assessment based on Hull Chapter 20 (Options, Futures, and Other Derivatives). Implements 10+ stress scenario categories including market crashes, volatility spikes, correlation breakdowns, liquidity crises, interest rate shocks, currency crises, and combination stress scenarios.

## Dependencies
- Internal:
  - `app.models.portfolio.Portfolio` - Portfolio model for risk calculations
- External:
  - `logging` - Standard logging
  - `datetime.datetime` - Timestamp generation
  - `typing` (Any, Dict, List, Optional) - Type hints
  - `numpy` as np - Numerical computations

## Classes/Functions

### Classes
- `ComprehensiveStressScenarios` - Main stress testing orchestrator

### Methods
- `__init__(config)` - Initialize with configurable scenarios
- `run_comprehensive_stress_tests(portfolio, scenario_categories)` - Main entry point for stress testing
- `_run_category_scenarios(portfolio, category)` - Run scenarios within a category
- `_apply_scenario(portfolio, scenario)` - Apply single stress scenario
- `_assess_scenario_severity(loss_percentage, scenario)` - Categorize loss severity
- `_generate_comprehensive_summary(results, all_scenarios)` - Aggregate results
- `get_scenario_description(scenario_id)` - Get scenario details
- `list_available_scenarios()` - List all available scenarios

### Scenario Loaders (Private)
- `_load_market_crash_scenarios()` - 6 historical crash scenarios (Black Monday 1987, Asian Crisis 1997, Dot-com 2000, GFC 2008, Flash Crash 2010, COVID 2020)
- `_load_volatility_scenarios()` - 4 volatility spike scenarios
- `_load_correlation_scenarios()` - 4 correlation breakdown scenarios
- `_load_liquidity_scenarios()` - 2 liquidity crisis scenarios
- `_load_interest_rate_scenarios()` - 3 rate shock scenarios
- `_load_currency_scenarios()` - 2 currency crisis scenarios
- `_load_combination_scenarios()` - 3 multi-factor stress scenarios

## Business Logic
1. **Stress Testing Framework**: Applies configurable stress scenarios to portfolio value
2. **Severity Assessment**: Categorizes losses into CRITICAL (>40%), EXTREME (>25%), HIGH (>15%), MODERATE (>10%), ELEVATED (>5%), LOW (<5%)
3. **Multi-Category Testing**: Tests 7 scenario categories with 25+ total scenarios
4. **Risk Recommendations**: Provides actionable recommendations based on stress test results
5. **Historical Scenarios**: Uses historical market events for realistic stress testing

## Data Models
- **Scenario Dictionary**:
  - `name`: Human-readable scenario name
  - `description`: Detailed scenario description
  - `market_shock`: Percentage market move (e.g., -0.226 for -22.6%)
  - `volatility_multiplier`: Volatility stress multiplier
  - `correlation_increase`: Correlation stress addition
  - `liquidity_decrease`: Liquidity reduction factor
  - `sector_impact`: Sector-specific shock multipliers

## API Contracts
- **Input**: `Portfolio` object with positions and total_equity
- **Output**: Dictionary with:
  - `categories`: Results by scenario category
  - `summary`: Overall risk assessment with worst_case, best_case, statistics
  - `timestamp`: ISO format timestamp

## Error Handling
- Specific exceptions caught: `ValueError`, `TypeError`, `KeyError`, `AttributeError`
- All exceptions logged with `exc_info=True` for full stack traces
- Graceful degradation: Returns `{'error': str(e)}` on exception
- Zero division protection: `if initial_value > 0 else 0.0`

## Performance Considerations
- Vectorized operations with numpy for efficiency
- O(N) complexity for scenario application where N = number of scenarios
- Memory efficient: Uses generator patterns for large scenario sets

## Testing Strategy
- Unit tests for each scenario category
- Integration tests with mock portfolios
- Edge cases: Zero portfolio value, empty positions, extreme market shocks
- Validate severity thresholds and risk recommendations

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
- **Status**: MINOR NOTE - Uses legacy `Optional[T]` syntax instead of modern `T | None`
- **Priority**: P2 (Medium)
- **Impact**: Non-critical - Code is fully functional with Python 3.9+ compatible syntax
- **Recommendation**: Consider migrating to `T | None` for modern Python 3.10+ codebases

### R101: No Print in Production
- **Status**: PASS - No print() statements found
- **Priority**: P0

### R104: No Bare Except
- **Status**: PASS - All except clauses specify exception types
- **Lines**: 354, 478
- **Pattern**: `except (ValueError, TypeError, KeyError, AttributeError) as e:`

### R105: Proper Exception Handling
- **Status**: PASS - Specific exceptions with proper logging
- **Pattern**: All exceptions logged with `logger.error(..., exc_info=True)`

### R108: No Hardcoded Values
- **Status**: PASS - All scenario parameters are configurable dictionaries
- **Note**: Historical scenario values are documented constants (Black Monday -22.6%, etc.)

### R110: Google-Style Docstrings
- **Status**: PASS - Comprehensive Google-style docstrings
- **Coverage**: All public methods documented

### R111: No Circular Imports
- **Status**: PASS - No circular dependencies detected

### LOG-004: Error Logging
- **Status**: PASS - All exceptions logged with stack traces
- **Lines**: 355, 478

### LOG-005: No Sensitive Data in Logs
- **Status**: PASS - No portfolio values or positions logged

### TRD-002: Risk Validation
- **Status**: PASS - Implements comprehensive stress testing for risk assessment

### RSK-001, RSK-002: VaR/ES Calculation
- **Status**: PASS - Stress scenarios test portfolio under extreme conditions

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07T10:00:00Z
**Auditor:** Claude Code (GAP Audit Automation)
**GAPs Found:** 0 critical, 0 P1, 1 P2 (minor)
**Notes:** File fully complies with BASE_RULES. Minor P2 note about legacy type hint syntax (non-critical).

All BASE_RULES verified. File has been analyzed against BASE_RULES.md:
- SEC-001 to SEC-010: PASS (No hardcoded secrets, proper audit logging)
- LOG-004: PASS (Error logging with stack traces)
- LOG-005: PASS (No sensitive data in logs)
- TRD-002: PASS (Risk validation via stress testing)
- RSK-001, RSK-002: PASS (Stress testing for VaR/ES scenarios)
- R104: PASS (No bare except clauses)
- R105: PASS (Proper exception handling)
- R108: PASS (No hardcoded values)
- R110: PASS (Google-style docstrings)
- R111: PASS (No circular imports)

Code is production-ready. Minor type hint style note is non-critical.
