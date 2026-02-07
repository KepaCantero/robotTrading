# Requirements: app/engines/portfolio_engine/rebalancers/rebalancers.py

## Source File Analysis
- **File Path**: `app/engines/portfolio_engine/rebalancers/rebalancers.py`
- **Lines of Code**: 505
- **Status**: Analysis Complete

## Purpose
Portfolio Rebalancers module implements dynamic rebalancing strategies for automated portfolio management. Provides multiple rebalancing approaches including threshold-based, time-based, volatility-targeting, and transaction cost-aware rebalancing.

## Dependencies

### Internal
- `app.models.portfolio` - Portfolio data models

### External
- `logging` - Structured logging
- `abc.ABC, ABCMeta` - Abstract base classes
- `datetime` - Time handling
- `decimal.Decimal` - Precise financial calculations
- `typing.Any, Dict, List, Optional` - Type hints
- `numpy` - Numerical operations

## Classes/Functions

### class BaseRebalancer(ABC)
**Purpose**: Abstract base class for all rebalancer implementations

**Methods**:
- `should_rebalance(current_weights, target_weights, portfolio_value, **kwargs) -> bool`: Determine if rebalancing is needed
- `calculate_rebalance_trades(current_positions, target_weights, portfolio_value, prices) -> List[Dict]`: Calculate trades for rebalancing

### class ThresholdRebalancer(BaseRebalancer)
**Purpose**: Rebalances when weights deviate from target by threshold percentage

**Configuration**:
- `threshold`: Default 5% deviation trigger
- `min_rebalance_interval_days`: Default 1 day minimum between rebalances

### class TimeBasedRebalancer(BaseRebalancer)
**Purpose**: Rebalances on fixed intervals (daily, weekly, monthly)

**Configuration**:
- `frequency`: 'daily', 'weekly', or 'monthly'

### class VolatilityTargetingRebalancer(BaseRebalancer)
**Purpose**: Rebalances to maintain target portfolio volatility

**Configuration**:
- `target_volatility`: Default 15% annual
- `volatility_threshold`: Default 2% deviation

### class TransactionCostAwareRebalancer(BaseRebalancer)
**Purpose**: Only rebalances when benefit exceeds transaction costs

**Configuration**:
- `commission_rate`: Default 0.1% (10 bps)
- `slippage_rate`: Default 0.05% (5 bps)
- `min_benefit_threshold`: Default 0.1%

### class HybridRebalancer(BaseRebalancer)
**Purpose**: Combines multiple rebalancing strategies

## Business Logic

### Rebalancing Flow
1. Check if rebalancing is needed via `should_rebalance()`
2. Calculate required trades via `calculate_rebalance_trades()`
3. Return list of trades with symbol, quantity, and reason

### Trade Calculation
- Uses Decimal for all financial calculations
- Filters insignificant trades (< 0.01 quantity)
- Returns current_weight vs target_weight for monitoring

### Cost Awareness
- Transaction cost estimator includes commission + slippage
- Benefit estimation based on deviation reduction
- Only executes when benefit > cost

## Critical Rules (de BASE_RULES.md)

### TYP-001: Type hints
- ✅ All functions have complete type hints
- Legacy syntax: `Optional[T]` instead of `T | None` (acceptable for compatibility)

### LOG-001: Structured logging
- ✅ Uses logger.info/warning for rebalance triggers
- ✅ Logs include deviation percentages and reasons

### ERR-001: Error handling
- ✅ No bare except clauses
- ✅ Graceful handling of missing data (returns False, empty lists)

### TRD-002: Trading validations
- ✅ Decimal precision for financial calculations
- ✅ Division by zero checks (portfolio_value > 0)
- ✅ Price validation (> 0) before calculations

### FIN-001: Financial calculations
- ✅ Uses Decimal for all monetary values
- ✅ Proper type casting (Decimal(str(value)))

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T09:00:00Z |
| **Audit Status** | PASSED |
| **Violations** | 0 |
| **Notes** | Uses legacy type hint syntax (acceptable for Python 3.9+ compatibility). Spanish comments in docstrings (international project). All BASE_RULES critical requirements compliant. |

## Notes
- File uses `datetime.utcnow()` which is deprecated in Python 3.12+ (should use `datetime.now(tz=timezone.utc)`) - P2 priority
- All financial calculations use Decimal for precision (best practice)
- No hardcoded values, all configurable via constructor
