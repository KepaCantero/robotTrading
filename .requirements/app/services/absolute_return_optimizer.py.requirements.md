# Requirements: services/absolute_return_optimizer.py

## Source File Analysis
- **File Path**: `app/services/absolute_return_optimizer.py`
- **Lines of Code**: 859
- **Status**: AUDIT COMPLETE

## Purpose
Transforms profit targets (€800/month) into optimized trading parameters. This service is the bridge between strategic goals and operational execution, orchestrating 5 specialist components for parameter optimization.

## Dependencies
- Internal:
  - `app.services.account_configuration` (AccountConfiguration, AccountTier)
  - `app.services.capital_tier_strategy_selector` (RiskProfile)
- External:
  - `decimal` (Decimal)
  - `logging`
  - `dataclasses`
  - `typing`

## Classes/Functions

### Data Classes
1. **AlphaTarget** (lines 47-75)
   - Purpose: Required alpha to achieve profit goal
   - Attributes: monthly_profit_goal, monthly_alpha_needed, gross_profit_needed, net_profit_expected, confidence_score
   - Validation: `.validate()` method

2. **CapacityFadeEstimate** (lines 79-114)
   - Purpose: Alpha decay with increasing capital
   - Attributes: capital, base_monthly_alpha, estimated_decay_rate, adjusted_alpha, alpha_at_2x_capital, alpha_at_5x_capital
   - Validation: `.validate()` method

3. **OptimizedParameters** (lines 118-165)
   - Purpose: Optimized trading parameters for achieving profit target
   - Attributes: position_size_pct, position_size_usd, leverage_multiplier, max_concurrent_trades, monthly_target_return, required_monthly_alpha, feasibility_score, confidence_level, risk_level, constraints, recommendations
   - Validation: `.validate()` method

4. **MonthlyProfitForecast** (lines 169-207)
   - Purpose: P&L projection given optimized parameters
   - Attributes: expected_monthly_profit, profit_confidence_interval, expected_monthly_trades, expected_win_rate, expected_sharpe_ratio, expected_max_drawdown, probability_of_target, percentile_5, percentile_95
   - Validation: `.validate()` method

5. **FeasibilityReport** (lines 211-237)
   - Purpose: Assessment of whether profit goal is achievable
   - Attributes: is_feasible, confidence_level, required_alpha, available_alpha, gap, tier, constraints, recommendations, deployment_status

### Specialist Components
1. **AlphaTargetCalculator** (lines 245-327)
   - `calculate_required_alpha()`: Calculate alpha required to achieve profit goal

2. **CapacityFadeAnalyzer** (lines 330-429)
   - `estimate_capacity_fade()`: Estimate alpha decay from current to target capital

3. **ParameterScaler** (lines 432-513)
   - `scale_for_target()`: Scale position sizing to achieve target return

4. **ReturnDistributionValidator** (lines 516-552)
   - `validate_achievability()`: Check if target is statistically reasonable

5. **MonthlyProfitForecaster** (lines 555-612)
   - `forecast_profit()`: Forecast monthly P&L given trading parameters

### Core Service
1. **AbsoluteReturnOptimizer** (lines 620-858)
   - `__init__()`: Initialize with capital and account_id
   - `optimize_for_target()`: Main optimization method
   - `validate_feasibility()`: Check if profit goal is feasible
   - `forecast_monthly_profit()`: Forecast monthly P&L

## Business Logic
1. Accepts profit target (€800/month) and expected monthly alpha from backtesting
2. Calculates required alpha working backwards from profit goal
3. Estimates capacity fade (alpha decay as capital increases)
4. Scales position sizing and leverage to achieve target within risk constraints
5. Validates feasibility and returns optimized parameters

## Data Models
All data classes use `@dataclass` decorator with validation methods:
- Input validation in `__post_init__` for data classes that have it
- Explicit `.validate()` methods returning `(bool, str)` tuples

## API Contracts
No REST API - this is a service layer module.

## Error Handling
- ValueErrors raised for invalid inputs (capital <= 0, invalid win rates, etc.)
- All calculations use Decimal for precision
- Comprehensive logging at INFO and ERROR levels

## Performance Considerations
- Uses Decimal for financial calculations (precision over speed)
- Mathematical operations (log10, power) for capacity fade calculations
- No database operations (stateless service)

## Testing Strategy
Recommended test coverage:
1. Unit tests for each calculator component
2. Integration tests for full optimization workflow
3. Edge cases: zero capital, negative targets, extreme decay rates
4. Validation: all dataclass validate methods

## Compliance with BASE_RULES.md

### PASSING Rules:
- ✅ **ARCH-001**: Layered architecture - service layer correctly positioned
- ✅ **CC-001**: Descriptive names - all classes and variables clearly named
- ✅ **CC-003**: KISS - straightforward calculation logic
- ✅ **CC-006**: Explicit error handling - ValueErrors for invalid inputs
- ✅ **LOG-003**: Appropriate logging levels - info/error used correctly
- ✅ **TYP-001**: Type hints - comprehensive type coverage
- ✅ **DP-004**: Dependency injection - RiskProfile injected via parameters

### GAPS IDENTIFIED:
None - Code quality is high. All BASE_RULES are satisfied.

## Audit Status: PASSED

**Audited By:** Claude (Backend Developer Agent)
**Audit Date:** 2026-02-07
**Batches:** 0097

### Summary
This module demonstrates excellent code quality:
- Clear separation of concerns with 5 specialist components
- Comprehensive data classes with validation
- Proper dependency injection
- Financial precision using Decimal
- Good error handling and logging
- Extensive documentation

No critical gaps found. Module is production-ready.

---
*Auto-generated on Thu Feb  5 20:33:01 CET 2026*
*Updated for GAP audit on 2026-02-07*
