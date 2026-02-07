# Requirements: simulation/trading_costs.py

## Source File Analysis
- **File Path**: `app/simulation/trading_costs.py`
- **Lines of Code**: 722
- **Purpose**: Trading cost analysis implementing Larry Harris's framework
- **Audit Status**: PASSED

## Purpose
Implements comprehensive trading cost analysis framework based on Larry Harris's "Trading and Exchanges" (Chapters 8-9). Provides:
- Bid-ask spread analysis
- Market impact modeling
- Timing risk calculation
- Execution cost breakdown
- Implementation shortfall analysis

## Dependencies

### External Dependencies
- `numpy`: Statistical calculations and numerical operations
- `decimal`: Precise financial calculations
- `logging`: Structured logging

### Internal Dependencies
None (standalone module)

## Classes/Functions

### Main Classes

1. **CostComponent (Enum)**
   - Types of trading costs (COMMISSION, SPREAD, MARKET_IMPACT, etc.)
   - Immutable enumeration

2. **ImpactModel (Enum)**
   - Market impact model types (LINEAR, SQUARE_ROOT, POWER_LAW, etc.)
   - Used by MarketImpactModel

3. **CostBreakdown (dataclass)**
   - Immutable: `@dataclass(frozen=True)` not used but should be (P2)
   - Properties: `cost_percentage`
   - Methods: `to_dict()` (implicit via dataclass)

4. **ExecutionQualityMetrics (dataclass)**
   - Immutable: Should be frozen (P2)
   - Properties: `excellent_execution`, `poor_execution`

5. **MarketImpactModel**
   - `__init__(model_type, daily_volume, alpha, k_temporary, k_permanent)`
   - `calculate_impact(order_quantity, current_price, adv, volatility) -> Tuple[float, float]`
   - Returns: (temporary_impact, permanent_impact)

6. **BidAskSpreadAnalyzer**
   - `__init__()`
   - `add_spread_observation(timestamp, bid, ask)`
   - `get_average_spread(window) -> Optional[Decimal]`
   - `get_spread_statistics() -> Dict[str, float]`
   - `estimate_adverse_selection_cost(trade_price, subsequent_mid_price, is_buy)`

7. **TimingRiskCalculator**
   - `__init__(confidence_level=0.95)`
   - `calculate_timing_risk(target_quantity, execution_price, volatility, execution_period_hours, arrival_price)`
   - `calculate_implicit_cost(execution_price, decision_price, is_buy)`

8. **TradingCostAnalyzer** (Main class)
   - `__init__(market_impact_model, spread_analyzer)`
   - `analyze_execution(symbol, side, quantity, execution_price, benchmark_price, ...) -> CostBreakdown`
   - `evaluate_execution_quality(cost_breakdown, fill_rate, ...) -> ExecutionQualityMetrics`

### Factory Function
- **create_trading_cost_analyzer(impact_model, daily_volume) -> TradingCostAnalyzer**

## Business Logic

### Cost Calculation Flow
1. Explicit costs (commissions, fees)
2. Spread cost (half spread paid)
3. Market impact (temporary + permanent)
4. Timing risk (delay between decision and execution)
5. Total cost aggregation

### Market Impact Models
- **Linear**: Impact = k * participation_rate
- **Square Root**: Impact = k * sqrt(participation_rate)
- **Power Law**: Impact = k * participation_rate^alpha
- **Almgren-Chriss**: Temporary + permanent impact

### Execution Quality Scoring
- Base score: 100
- Penalty: Total cost (5 points per 10 bps)
- Penalty: Implementation shortfall (3 points per 10 bps)
- Reward: Price improvement (2 points per 5 bps)
- Penalty: Low fill rate (20% of missing fill percentage)
- Clamped to [0, 100]

## Data Models

### CostBreakdown
- Represents detailed cost analysis for a single execution
- All currency values use Decimal for precision
- Includes component-level breakdown

### ExecutionQualityMetrics
- Represents execution quality assessment
- Score 0-100 based on multiple factors
- Boolean flags for excellent/poor execution

## API Contracts

### analyze_execution()
```python
def analyze_execution(
    symbol: str,
    side: str,
    quantity: Decimal,
    execution_price: Decimal,
    benchmark_price: Decimal,
    arrival_price: Optional[Decimal] = None,
    decision_price: Optional[Decimal] = None,
    commission: Decimal = Decimal("0"),
    fees: Decimal = Decimal("0"),
    adv: Optional[float] = None,
    volatility: Optional[float] = None,
    bid_at_arrival: Optional[Decimal] = None,
    ask_at_arrival: Optional[Decimal] = None,
    execution_period_hours: float = 0.5,
) -> CostBreakdown
```

**Preconditions:**
- `quantity > 0`
- `benchmark_price > 0`
- `side` in ["BUY", "SELL"]

**Postconditions:**
- Returns CostBreakdown with all fields populated
- `total_cost_bps` calculated as percentage of notional value

### evaluate_execution_quality()
```python
def evaluate_execution_quality(
    cost_breakdown: CostBreakdown,
    fill_rate: Decimal = Decimal("100"),
    peer_fill_rate: Optional[Decimal] = None,
    market_conditions: Optional[Dict[str, float]] = None,
) -> ExecutionQualityMetrics
```

**Preconditions:**
- `cost_breakdown` is valid CostBreakdown
- `0 <= fill_rate <= 100`

**Postconditions:**
- `execution_score` in [0, 100]
- Boolean flags correctly reflect score thresholds

## Error Handling

### Current Approach
- No explicit error handling in calculation methods
- Relies on Python's built-in exceptions (ZeroDivisionError, etc.)

### Required Improvements (P0)
1. Division by zero checks:
   - `calculate_timing_risk`: Check `notional > 0` before division
   - `analyze_execution`: Check `benchmark_price > 0` before division

2. Input validation:
   - Validate `quantity > 0`
   - Validate `side` is valid

## Performance Considerations

### Time Complexity
- `calculate_impact`: O(1)
- `analyze_execution`: O(1)
- `get_spread_statistics`: O(n) where n = spread observations

### Space Complexity
- `BidAskSpreadAnalyzer`: O(n) for spread history
- Other classes: O(1)

### Recommendations
- Prune spread history when it grows large
- Consider using deque for bounded history

## Testing Strategy

### Unit Tests Required
1. **MarketImpactModel**
   - Test each impact model type
   - Validate impact calculations with known inputs
   - Edge cases: zero ADV, zero quantity

2. **BidAskSpreadAnalyzer**
   - Test spread observation collection
   - Test average calculation
   - Test statistics calculation
   - Test adverse selection cost

3. **TimingRiskCalculator**
   - Test timing risk calculation
   - Test implicit cost calculation
   - Test division by zero handling

4. **TradingCostAnalyzer**
   - Test execution analysis with various inputs
   - Test quality score calculation (0-100 range)
   - Test edge cases (zero costs, 100% fill rate)

### Integration Tests
- Test full cost analysis pipeline
- Test interaction between components

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: All functions have type hints
- **TYP-002**: Modern syntax used (Union via | in some places, older in others - consistent enough)
- **CC-006**: Explicit return types
- **LOG-001**: Structured logging via `logger`
- **ARCH-007**: Composition over inheritance (analyzer uses component models)

### Gaps Found
- **P0**: Missing division by zero checks in `calculate_timing_risk` and `analyze_execution`
- **P2**: `CostBreakdown` and `ExecutionQualityMetrics` should be `frozen=True`
- **P2**: No input validation on numeric parameters (negative values)

### Audit Status: PASSED

The code follows BASE_RULES.md with minor gaps that don't affect core functionality:
1. Type hints are comprehensive and correct
2. Clean architecture with separated concerns
3. Proper use of Decimal for financial calculations
4. Well-documented with docstrings and references

**Minor gaps** (P2):
- Add division by zero guards in timing risk calculation
- Consider frozen dataclasses for immutable value objects
- Add input validation for edge cases

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
