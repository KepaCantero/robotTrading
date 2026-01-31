# transaction_costs.py

## Purpose
Implements transaction cost models for realistic backtesting including linear costs, piecewise linear tiered pricing, and market impact models following Almgren-Chriss framework for optimal execution.

---

## Type Definitions / Data Classes

### CostModelType Enum
```python
class CostModelType(str, Enum):
    LINEAR = "linear"
    PIECEWISE_LINEAR = "piecewise_linear"
    NONLINEAR = "nonlinear"
```
**Validation Rules:** Must be one of the three defined cost model types

### CostBreakdown DataClass
```python
@dataclass
class CostBreakdown:
    commission: Decimal           # REQUIRED - Broker commission fee
    exchange_fees: Decimal        # REQUIRED - Exchange transaction fees
    sec_fees: Decimal             # REQUIRED - SEC regulatory fees (US stocks)
    nasdaq_fees: Decimal          # REQUIRED - NASDAQ fees
    slippage: Decimal             # REQUIRED - Price slippage cost
    market_impact: Decimal        # REQUIRED - Market impact cost
    total: Decimal                # REQUIRED - Sum of all cost components
```
**Validation Rules:**
- All fields must be non-negative Decimal values
- `total` must equal sum of all other fields
- `cost_as_percentage` property returns total cost as percentage (0-100)

### ImpactParameters DataClass
```python
@dataclass
class ImpactParameters:
    adv: Decimal                      # REQUIRED - Average daily volume
    volatility: float                 # REQUIRED - Annualized volatility (e.g., 0.2 = 20%)
    market_cap: Optional[Decimal]     # OPTIONAL - Market capitalization
    spread: Optional[Decimal]         # OPTIONAL - Bid-ask spread
    price: Decimal = Decimal("0")     # REQUIRED with default - Current price
```
**Validation Rules:**
- `adv` must be > 0
- `volatility` must be >= 0
- `__post_init__` sets default price to Decimal("100") if zero

### TemporaryImpact DataClass
```python
@dataclass
class TemporaryImpact:
    impact_per_share: Decimal         # REQUIRED - Temporary impact per share
    recovery_time_hours: float = 1.0  # OPTIONAL - Time for price recovery
```

### PermanentImpact DataClass
```python
@dataclass
class PermanentImpact:
    impact_per_share: Decimal      # REQUIRED - Permanent impact per share
    price_displacement: Decimal    # REQUIRED - Total price displacement
```

---

## Function Signatures (Contracts)

### `TransactionCostModel.calculate_cost(symbol, side, quantity, price, volume, adv) -> CostBreakdown`
**Pre:** symbol is valid str, side in ['buy', 'sell'], quantity > 0, price > 0
**Post:** Returns CostBreakdown with all cost components calculated
**Raises:** None (returns zero costs if invalid inputs)
**Retry:** No
**Side Effects:** None (pure calculation)

### `TransactionCostModel.estimate_total_cost(trades) -> Decimal`
**Pre:** trades is list of tuples (symbol, side, quantity, price)
**Post:** Returns total estimated cost for all trades
**Raises:** None
**Retry:** No
**Side Effects:** None

### `LinearCostModel.__init__(commission_per_share, min_commission, exchange_fee_rate, sec_fee_rate)`
**Pre:** commission_per_share >= 0, min_commission >= 0, all rates >= 0
**Post:** Model initialized with specified cost parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `LinearCostModel.calculate_cost(...) -> CostBreakdown`
**Pre:** quantity >= 0, price > 0
**Post:** Commission = max(quantity * commission_per_share, min_commission)
**Post:** SEC fees only applied to sell orders
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PiecewiseLinearCostModel.__init__(tiers, min_commission)`
**Pre:** tiers is list of (threshold, rate) tuples, sorted ascending
**Post:** Model initialized with tiered pricing structure
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PiecewiseLinearCostModel._get_rate_for_quantity(quantity) -> Decimal`
**Pre:** quantity >= 0
**Post:** Returns applicable rate for quantity tier
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.calculate_impact(quantity, price, adv, volatility, participation_rate) -> Decimal`
**Pre:** quantity >= 0, price > 0, adv > 0, volatility >= 0
**Post:** Returns market impact cost per share as Decimal
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlmgrenChristModel.__init__(permanent_impact, temporary_impact, volatility_impact)`
**Pre:** All coefficients >= 0 (typical: gamma=0.1, eta=0.05, lambda=0.5)
**Post:** Almgren-Chriss model initialized with impact coefficients
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlmgrenChristModel.calculate_impact(...) -> Decimal`
**Pre:** adv > 0, volatility >= 0
**Post:** Returns total impact = permanent + temporary components
**Post:** Permanent impact = gamma * participation_rate
**Post:** Temporary impact = eta * (Q/ADV) * daily_volatility
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlmgrenChristModel.calculate_permanent_impact(quantity, adv) -> float`
**Pre:** adv > 0
**Post:** Returns permanent impact percentage (0-1 range)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlmgrenChristModel.calculate_temporary_impact(quantity, adv, volatility) -> float`
**Pre:** adv > 0, volatility >= 0
**Post:** Returns temporary impact percentage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SquareRootImpactModel.__init__(coefficient)`
**Pre:** coefficient in range [0.05, 0.2] (typical values)
**Post:** Square root model initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SquareRootImpactModel.calculate_impact(...) -> Decimal`
**Pre:** adv > 0, volatility >= 0
**Post:** Impact = coefficient * sigma_daily * sqrt(Q/ADV)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-TC-001: LinearCostModel calculates commission correctly with minimum
- [ ] AC-TC-002: SEC fees only applied to sell orders (not buys)
- [ ] AC-TC-003: PiecewiseLinearCostModel applies correct tier for quantity
- [ ] AC-TC-004: Almgren-Chriss model calculates permanent and temporary impact
- [ ] AC-TC-005: Square root model uses sqrt(Q/ADV) formula correctly
- [ ] AC-TC-006: All cost models return non-negative values
- [ ] AC-TC-007: CostBreakdown total equals sum of components
- [ ] AC-TC-008: Market impact models use daily volatility (annual/252)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** See `../../BASE_RULES.md` for 96+ universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-006 | papers/backtesting | Include transaction costs in backtesting | ✅ OK |
| BT-004 | papers/backtesting | Realistic costs (slippage, commissions) | ✅ OK |
| EXE-003 | papers/almgren-chriss | Consider market impact of trades | ✅ OK |
| ARCH-003 | BASE_RULES | Domain has no framework dependencies | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Calculation only, no I/O |
| LOG-004 | BASE_RULES | Error logging with stack traces | ⚠️ NOT APPLIED - Pure functions, no errors |

---

## Dependencies
- **External:** numpy (for sqrt, volatility calculations)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/domain/services/backtesting/test_transaction_costs.py:**
  - Test LinearCostModel with minimum commission edge case
  - Test SEC fees only on sell orders
  - Test PiecewiseLinearCostModel tier selection
  - Test Almgren-Chriss permanent/temporary impact calculation
  - Test SquareRootImpactModel formula
  - Test zero quantity returns zero costs
  - Test large order impact (participation rate capping at 1.0)
  - Test volatility conversion (annual to daily: vol/sqrt(252))
  - Test CostBreakdown total aggregation
  - Test estimate_total_cost with multiple trades

---

## Notes
Reference: Almgren, R., & Chriss, N. (2001) "Optimal Execution of Portfolio Transactions" - Industry standard for market impact modeling in algorithmic trading systems.
