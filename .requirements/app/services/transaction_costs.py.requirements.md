# Requirements: services/transaction_costs.py

## Source File Analysis
- **File Path**: `app/services/transaction_costs.py`
- **Lines of Code**: 685
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
Transaction cost models implementing Rishi Narang's "Inside the Black Box" framework. Calculates commission, market impact, slippage, timing risk, and total cost of ownership.

## Dependencies
- Internal: None (standalone module)
- External:
  - `logging`, `dataclasses`, `datetime`, `decimal`, `enum`, `typing` (Standard library)
  - `numpy` (Numerical calculations)

## Classes/Functions

### Enums
- `CostComponent`: COMMISSION, SPREAD, MARKET_IMPACT, TIMING_RISK, SLIPPAGE, FEES, TAXES
- `MarketImpactModel`: SQUARE_ROOT, LINEAR, POWER_LAW, NONE
- `ExecutionAlgorithm`: VWAP, TWAP, POV, IMPLEMENTATION_SHORTFALL, MARKET, LIMIT

### Data Classes
- `MarketData`: symbol, bid, ask, last, volume, ADV, volatility, timestamp
- `OrderSpecification`: symbol, side, quantity, order_type, limit_price, time_in_force, execution_algorithm, urgency
- `CostBreakdown`: Complete cost breakdown with all components
- `CostAnalysis`: Aggregated analysis with recommendations

### Classes
- `TransactionCostModel`: Base transaction cost model
  - `calculate_transaction_costs(order, market_data, order_id)`: Main calculation
  - `validate_order_type(order, market_data)`: Order type validation
  - `recommend_execution_algorithm(order, market_data)`: Algorithm selection
  - `analyze_cost_impact(cost_breakdown)`: Impact analysis

- `CommissionModel`: Commission-only model
- `AlmgrenChrissModel`: Almgren-Chriss market impact model

### Functions
- `get_transaction_cost_model(config)`: Factory function

## Business Logic

### Total Transaction Cost Formula
```
total_cost = commission + spread_cost + market_impact +
             timing_risk + slippage + fees + taxes
```

### Market Impact Models (Almgren-Chriss)
- **Square Root**: impact ~ sqrt(participation_rate)
- **Linear**: impact ~ participation_rate
- **Power Law**: impact ~ participation^alpha

### Cost per Share Calculation
```
cost_per_share = total_cost / quantity
cost_bps = (total_cost / trade_value) * 10000
```

### Execution Algorithm Recommendations
- **< 1% ADV**: Market orders acceptable
- **1-5% ADV**: Limit or market based on urgency
- **5-10% ADV**: TWAP or POV
- **> 10% ADV**: VWAP or implementation shortfall

## Data Models
- Input: OrderSpecification, MarketData
- Output: CostBreakdown, CostAnalysis
- Configuration: commission_per_share, impact_coefficient, thresholds

## API Contracts

### TransactionCostModel.calculate_transaction_costs()
```python
def calculate_transaction_costs(
    order: OrderSpecification,
    market_data: MarketData,
    order_id: str = "",
) -> CostBreakdown
```

### TransactionCostModel.recommend_execution_algorithm()
```python
def recommend_execution_algorithm(
    order: OrderSpecification,
    market_data: MarketData,
) -> ExecutionAlgorithm
```

## Error Handling
- Validates order quantity > 0
- Validates limit orders have price
- Validates stop orders have stop price
- No exceptions raised for missing market data (uses defaults)

## Performance Considerations
- O(1) calculations per order
- numpy for statistical calculations
- Minimal memory overhead

## Testing Strategy
- Unit tests for each cost component
- Verify Almgren-Chriss model accuracy
- Test algorithm recommendation logic
- Edge cases: zero quantity, missing prices

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Full type coverage with dataclasses |
| Error Handling | ✅ PASS | Input validation in _validate_order |
| SOLID Principles | ✅ PASS | Base class with inheritance (OCP) |
| Logging | ✅ PASS | Info logging for operations |
| No Hardcoded Secrets | ✅ PASS | No secrets in code |
| Input Validation | ✅ PASS | Validates quantity, prices, order types |
| Async Patterns | ✅ PASS | N/A - synchronous module |
| Documentation | ✅ PASS | Comprehensive docstrings with Narang references |
| Financial Precision | ✅ PASS | Uses Decimal for all monetary values |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
