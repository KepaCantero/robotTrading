# Requirements: services/multi_strategy_allocation.py

## Source File Analysis
- **File Path**: `app/services/multi_strategy_allocation.py`
- **Lines of Code**: 415
- **Status:** AUDIT COMPLETE

## Purpose
Implements TASK-PA-1, PA-2, PORT-SEL-1: Multi-Strategy Portfolio Allocation System with dynamic capital allocation across multiple strategies (Momentum 50%, Mean Reversion 25%, Pairs Trading 25%) and rolling 30-day performance-based rebalancing.

## Dependencies
- Internal:
  - `app.core.centralized_config.get_config`
- External:
  - `logging`, `datetime`, `decimal`, `typing`

## Classes/Functions

### Classes
- `StrategyCapitalAllocation`: Manages target/current allocations and performance data per strategy
- `MultiStrategyAllocationManager`: Distributes capital across strategies with normalization
- `DynamicPortfolioSelector`: Adjusts weights based on rolling 30-day performance

### Key Methods
- `allocate(total_capital)`: Calculate allocated capital for this strategy
- `update_weight(new_weight)`: Update weight respecting min/max constraints
- `add_performance_data(timestamp, pnl, returns)`: Track performance (keeps 90 days)
- `calculate_rolling_returns(days)`: Calculate rolling returns over period
- `allocate_capital()`: Allocate capital to each strategy based on current weights
- `rebalance_allocations()`: Rebalance based on rolling 30-day performance
- `should_rebalance()`: Check if rebalancing needed based on drift threshold

### Global Functions
- `get_multi_strategy_manager(total_capital)`: Get singleton manager
- `get_dynamic_selector()`: Get singleton selector

## Business Logic
1. **Default Allocations**: From centralized config (momentum, mean_reversion, pairs_trading)
2. **Normalization**: Ensures allocations sum exactly to total capital
3. **Rebalancing**: 5% drift threshold, uses rolling 30-day returns
4. **Performance Adjustment**: Better performers get higher weight (1.5x target max)
5. **Precision Handling**: Handles rounding errors with largest strategy adjustment

## Data Models
- Uses Decimal for all financial calculations
- 90-day rolling performance window
- Performance data with timestamp, P&L, returns

## API Contracts
- Centralized config integration via `get_config().trading`
- Allocation weights from config
- Min/max constraints enforced

## Error Handling
- Returns Decimal("0") for missing strategies (graceful degradation)
- Logs warnings for unknown strategies
- Handles division by zero in normalization

## Performance Considerations
- Rolling returns calculation filters by date (O(n))
- Normalization ensures exact capital allocation
- Cache of performance data limited to 90 days

## Testing Strategy
- Test allocation normalization with rounding
- Test rolling returns calculation
- Test rebalancing triggers at 5% threshold
- Test performance-based weight adjustments
- Test missing strategy handling

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Clean implementation with good precision handling

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Clear, descriptive names
- ✅ CC-002: Minimal duplication (DRY)
- ✅ CC-003: Simple, straightforward logic
- ✅ FMT-007: No mutable defaults
- ✅ LOG-003: Appropriate log levels
- ✅ ARCH-004: Functions mostly < 20 lines
- ✅ ARCH-005: Early returns for error conditions

**Minor Notes:**
- Rounding fix in `rebalance_allocations()` is well-implemented
- 90-day performance data limit prevents memory issues

---
*Auto-generated on Thu Feb  5 20:33:02 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0076*
