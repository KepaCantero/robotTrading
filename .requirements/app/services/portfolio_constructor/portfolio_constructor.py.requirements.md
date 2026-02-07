# Requirements: services/portfolio_constructor/portfolio_constructor.py

## Source File Analysis
- **File Path**: `app/services/portfolio_constructor/portfolio_constructor.py`
- **Lines of Code:** 582
- **Status:** AUDIT COMPLETE

## Purpose
T7.1: PortfolioConstructor - Portfolio optimization and construction using multiple strategies (equal-weight, risk-parity, efficient frontier) with graceful fallback chain.

## Dependencies
- Internal:
  - `.models`: AllocationWeight, PortfolioAllocation, PortfolioConstructionRequest
- External:
  - `logging`, `datetime`, `decimal`, `typing`

## Classes/Functions

### Main Class: PortfolioConstructor
- `__init__()`: Initialize with history
- `construct_portfolio(request)`: Main entry point with fallback chain
- `_construct_efficient_frontier_portfolio(request, risk_config)`: Sharpe ratio maximization
- `_construct_risk_parity_portfolio(request)`: Inverse volatility weighting
- `_construct_equal_weight_portfolio(request)`: Simple 1/N baseline

### Module-Level Data
- `RISK_PROFILE_CONFIG`: Aggressive/balanced/conservative parameters
- `MODULE_CHARACTERISTICS`: Volatility, return, min/max allocation per module

### Global Functions
- `get_portfolio_constructor()`: Get singleton instance

## Business Logic
1. **Fallback Chain**:
   - Try: Efficient Frontier (Sharpe maximization)
   - Fallback 1: Risk Parity (inverse volatility)
   - Fallback 2: Equal Weight (1/N)

2. **Module Characteristics**:
   - momentum: 18% vol, 12% return
   - mean_reversion: 15% vol, 8% return
   - pairs_trading: 12% vol, 6% return
   - ML modules: 20-28% vol, 15-22% return
   - ensemble: 16% vol, 14% return

3. **Risk Profile Adjustment**:
   - Aggressive: 70% weight on efficiency
   - Balanced: 50% weight on efficiency
   - Conservative: 30% weight on efficiency

4. **Metrics Calculation**:
   - Expected portfolio return
   - Portfolio volatility (sqrt of weighted sum)
   - Sharpe ratio (assuming 2% risk-free)
   - Max drawdown (≈ 2σ)
   - Diversification ratio

## Data Models
- PortfolioAllocation: success, allocations, metrics, optimization notes
- AllocationWeight: module_name, weight_pct, capital_allocation, rationale

## API Contracts
- PortfolioConstructionRequest: profile_id, capital_eur, enabled_modules, risk_profile
- Returns PortfolioAllocation with complete metrics

## Error Handling
- Exception types: `(ValueError, TypeError, KeyError, AttributeError, IndexError)`
- Returns failed PortfolioAllocation on error
- Graceful fallback to simpler methods

## Performance Considerations
- Simple calculations (no heavy optimization)
- O(n) where n = number of modules
- History tracking for statistics

## Testing Strategy
- Test efficient frontier optimization
- Test risk parity calculation
- Test equal-weight fallback
- Test risk profile adjustments
- Test metric calculations

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Well-designed fallback architecture

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Clear method names
- ✅ CC-003: Simple, focused methods
- ✅ CC-006: Explicit error handling with fallbacks
- ✅ LOG-004: Error logging with context
- ✅ LOG-006: Timing info captured (elapsed_ms)
- ✅ DP-003: Strategy pattern for optimization methods
- ✅ ARCH-004: Functions mostly < 20 lines
- ✅ FMT-007: No mutable defaults

**Minor Notes:**
- sqrt() call on Decimal - may need float conversion
- Efficient frontier is simplified (full mean-variance would need covariance)

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0077*
