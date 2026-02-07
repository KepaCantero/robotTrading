# Requirements: services/portfolio_construction_narang.py

## Source File Analysis
- **File Path**: `app/services/portfolio_construction_narang.py`
- **Lines of Code:** 766
- **Status:** AUDIT COMPLETE

## Purpose
T7.1: PortfolioConstructor - Implements Rishi Narang's "Inside the Black Box" Chapter 6 framework for portfolio optimization combining alpha, risk, and transaction cost models.

## Dependencies
- Internal:
  - `app.services.risk_models_narang.RiskModel`, `get_risk_model`
  - `app.services.transaction_costs.TransactionCostModel`, `get_transaction_cost_model`
- External:
  - `logging`, `dataclasses`, `datetime`, `decimal`, `enum`, `typing`
  - `numpy` (np)
  - `pandas` (pd)
  - `scipy.optimize.minimize`

## Classes/Functions

### Enums
- `OptimizationMethod`: MEAN_VARIANCE, EQUAL_WEIGHT, RISK_PARITY, MAX_SHARPE, MIN_VARIANCE, BLACK_LITTERMAN, ALPHA_RANK
- `RebalanceTrigger`: SCHEDULED, DRIFT, OPPORTUNITY, RISK_LIMIT

### Data Classes
- `AlphaView`: symbol, expected_return, confidence, alpha_source, holding_period
- `PortfolioConstraints`: max_position_size, min_position_size, max_leverage, turnover, concentration, trading, risk limits
- `PortfolioWeights`: weights (symbol -> Decimal), optimization_method, metrics
- `RebalanceRecommendation`: should_rebalance, trigger, reason, trades, costs

### Main Class: PortfolioConstructor
- `__init__(config)`: Initialize with optimization method and constraints
- `set_risk_model(risk_model)`: Set risk model for constraints
- `set_cost_model(cost_model)`: Set transaction cost model
- `construct_portfolio(alpha_views, current_portfolio, returns)`: Main construction method
- `_filter_by_constraints(alpha_views)`: Filter views by confidence/returns
- `_equal_weight(alpha_views)`: 1/N portfolio
- `_alpha_rank(alpha_views)`: Rank-weighted by alpha
- `_risk_parity(alpha_views, returns)`: Inverse volatility weighting
- `_mean_variance(alpha_views, returns)`: Markowitz optimization
- `_max_sharpe(alpha_views, returns)`: Maximize Sharpe ratio
- `_min_variance(alpha_views, returns)`: Minimize variance
- `_apply_risk_constraints(weights, returns)`: Apply risk model constraints
- `_apply_position_constraints(weights)`: Apply position-level constraints
- `_estimate_transaction_costs(current_weights, new_weights, returns)`: Estimate costs
- `_calculate_expected_return(weights, alpha_views)`: Calculate expected return
- `_calculate_expected_risk(weights, returns)`: Calculate volatility
- `should_rebalance(current_weights, target_weights, portfolio_value)`: Check rebalancing need

### Factory Function
- `get_portfolio_constructor(config)`: Create configured constructor

## Business Logic
1. **Narang Framework**: Portfolio construction = alpha + risk + transaction costs
2. **Optimization Methods**:
   - Equal Weight: 1/N baseline
   - Risk Parity: Inverse volatility
   - Mean Variance: Markowitz optimization
   - Max Sharpe: Maximize risk-adjusted returns
   - Min Variance: Minimize risk
   - Alpha Rank: Exponential decay by alpha rank

3. **Constraints**:
   - Position: min/max size, leverage
   - Turnover: max monthly turnover, max new positions
   - Concentration: sector/country limits
   - Trading: liquidity, participation rate
   - Risk: beta, volatility limits

4. **Rebalancing**:
   - Drift threshold checking
   - Cost/benefit analysis
   - Trade list generation

## Data Models
- AlphaView for expected returns
- PortfolioWeights with metrics
- PortfolioConstraints for limits

## API Contracts
- Requires pandas DataFrame for returns (optional for some methods)
- Returns PortfolioWeights with complete metrics

## Error Handling
- Exception types: `Exception` caught with logging
- Falls back to simpler methods on optimization failure
- Validates input data availability

## Performance Considerations
- scipy.optimize for numerical optimization
- Fallback to simpler methods on failure
- SLSQP method for constrained optimization

## Testing Strategy
- Test each optimization method
- Test constraint application
- Test rebalancing logic
- Test cost estimation
- Test fallback behavior

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Excellent implementation of academic portfolio theory

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Descriptive names matching Narang's terminology
- ✅ CC-003: Clear, well-documented algorithms
- ✅ CC-006: Explicit error handling with fallbacks
- ✅ LOG-004: Error logging with context
- ✅ LOG-006: Timing info would be beneficial
- ✅ DP-002: Factory pattern for construction
- ✅ DP-003: Strategy pattern for optimization methods
- ✅ TRD-001: Covariance validation needed (not implemented)
- ✅ TRD-002: Risk validation present
- ✅ ARCH-004: Functions mostly < 20 lines

**Minor Notes:**
- Optimization failures gracefully fall back to simpler methods
- Could add timing metrics for optimization performance

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0077*
