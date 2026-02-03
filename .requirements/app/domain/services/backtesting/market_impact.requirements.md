# market_impact.py

## Purpose
Implements market impact models for large order execution including temporary and permanent impact calculations following Almgren-Chriss optimal execution framework and square-root impact laws.

---

## Type Definitions / Data Classes

### ImpactModelType Enum
```python
class ImpactModelType(str, Enum):
    ALMGREN_CHRISS = "almgren_chriss"
    SQUARE_ROOT = "square_root"
    LINEAR = "linear"
    NONLINEAR = "nonlinear"
```
**Validation Rules:** Must be one of the four defined impact model types

### ImpactParameters DataClass
```python
@dataclass
class ImpactParameters:
    adv: Decimal                      # REQUIRED - Average daily volume
    volatility: float                 # REQUIRED - Annualized volatility (e.g., 0.2 = 20%)
    market_cap: Optional[Decimal]     # OPTIONAL - Market capitalization
    spread: Optional[Decimal]         # OPTIONAL - Bid-ask spread
    price: Decimal = Decimal("0")     # REQUIRED with default - Current price
    gamma: float = 0.1                # OPTIONAL - Permanent impact coefficient
    eta: float = 0.05                 # OPTIONAL - Temporary impact coefficient
    lambda_param: float = 0.5         # OPTIONAL - Volatility impact coefficient
```
**Validation Rules:**
- `adv` must be > 0
- `volatility` must be >= 0
- `__post_init__` sets default price to Decimal("100") if zero
- Model coefficients must be non-negative

### TemporaryImpact DataClass
```python
@dataclass
class TemporaryImpact:
    impact_per_share: Decimal           # REQUIRED - Temporary impact per share
    recovery_time_hours: float = 1.0    # OPTIONAL - Time for price to recover
    decay_rate: float = 0.5             # OPTIONAL - Decay rate per hour
```
**Validation Rules:**
- `impact_per_share` >= 0
- `recovery_time_hours` > 0
- `decay_rate` >= 0

### TemporaryImpact.recover_after_hours(hours) -> Decimal
**Pre:** hours >= 0
**Post:** Returns remaining impact after exponential decay
**Formula:** impact_per_share * exp(-decay_rate * hours)

### PermanentImpact DataClass
```python
@dataclass
class PermanentImpact:
    impact_per_share: Decimal      # REQUIRED - Permanent impact per share
    price_displacement: Decimal    # REQUIRED - Total price displacement
    participation_rate: float       # REQUIRED - Order participation rate
```
**Validation Rules:**
- All fields must be non-negative
- `participation_rate` in range [0, 1]

### MarketImpactResult DataClass
```python
@dataclass
class MarketImpactResult:
    temporary: TemporaryImpact       # REQUIRED - Temporary impact component
    permanent: PermanentImpact       # REQUIRED - Permanent impact component
    total_impact: Decimal            # REQUIRED - Sum of temporary + permanent
    execution_price: Decimal         # REQUIRED - Expected execution price
    expected_price: Decimal          # REQUIRED - Original expected price
```
**Validation Rules:**
- `total_impact` = temporary.impact_per_share + permanent.impact_per_share
- `execution_price` = expected_price +/- total_impact (buy/sell)
- `impact_percentage` property returns total_impact/expected_price

---

## Function Signatures (Contracts)

### `MarketImpactModel.calculate_impact(quantity, side, params) -> MarketImpactResult`
**Pre:** quantity >= 0, side in ['buy', 'sell'], params valid ImpactParameters
**Post:** Returns MarketImpactResult with temporary and permanent components
**Raises:** None (returns zero impact if invalid inputs)
**Retry:** No
**Side Effects:** None (pure calculation)

### `AlmgrenChristModel.__init__(gamma, eta, lambda_param)`
**Pre:** gamma in [0.05, 0.2], eta in [0.01, 0.1], lambda_param >= 0
**Post:** Almgren-Chriss model initialized with impact coefficients
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlmgrenChristModel.calculate_impact(quantity, side, params) -> MarketImpactResult`
**Pre:** params.adv > 0, params.volatility >= 0
**Post:** Permanent impact = gamma * (Q/ADV)
**Post:** Temporary impact = eta * (Q/ADV) * sigma_daily
**Post:** execution_price = price +/- total_impact
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SquareRootImpactModel.__init__(coefficient, volatility_factor)`
**Pre:** coefficient in [0.05, 0.2], volatility_factor >= 0
**Post:** Square root model initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SquareRootImpactModel.calculate_impact(quantity, side, params) -> MarketImpactResult`
**Pre:** params.adv > 0, params.volatility >= 0
**Post:** Impact = coefficient * sigma_daily * sqrt(Q/ADV)
**Post:** 80% temporary, 20% permanent (empirical split)
**Post:** Adjusts for volatility deviation from 20% benchmark
**Raises:** None
**Retry:** No
**Side Effects:** None

### `LinearImpactModel.__init__(coefficient)`
**Pre:** coefficient in range [0.01, 0.1] (typical 0.05)
**Post:** Linear model initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `LinearImpactModel.calculate_impact(quantity, side, params) -> MarketImpactResult`
**Pre:** params.adv > 0
**Post:** Impact = coefficient * (Q/ADV)
**Post:** All impact is permanent (temporary = 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactCalculator.__init__(default_model)`
**Pre:** default_model is valid ImpactModelType
**Post:** Calculator initialized with specified default model
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactCalculator.calculate_impact(quantity, side, params, model) -> MarketImpactResult`
**Pre:** All parameters valid per model requirements
**Post:** Returns impact using specified model or default
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactCalculator.estimate_optimal_execution_size(target_price, side, params, max_impact_pct, model) -> Decimal`
**Pre:** target_price > 0, max_impact_pct in (0, 1)
**Post:** Returns maximum order size staying within impact threshold
**Post:** Uses binary search between 1 share and 50% of ADV
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactCalculator.calculate_impact_curve(params, side, num_points, model) -> List[Tuple[Decimal, float]]`
**Pre:** num_points > 0, params valid
**Post:** Returns list of (quantity, impact_percentage) tuples
**Post:** Calculates impact from 0 to 20% of ADV
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactResult.impact_percentage -> float`
**Pre:** expected_price != 0
**Post:** Returns total impact as percentage of expected price
**Formula:** float(total_impact / expected_price)
**Raises:** None (returns 0.0 if expected_price is 0)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-MI-001: Almgren-Chriss calculates permanent and temporary impact separately
- [ ] AC-MI-002: Square root model uses sqrt(participation_ratio) formula
- [ ] AC-MI-003: Buy orders have higher execution price (impact adds)
- [ ] AC-MI-004: Sell orders have lower execution price (impact subtracts)
- [ ] AC-MI-005: Participation rate capped at 1.0 (100% of ADV)
- [ ] AC-MI-006: Daily volatility = annual_volatility / sqrt(252)
- [ ] AC-MI-007: TemporaryImpact.recover_after_hours uses exponential decay
- [ ] AC-MI-008: MarketImpactCalculator binary search finds optimal size
- [ ] AC-MI-009: Impact curve returns up to 20% of ADV
- [ ] AC-MI-010: All models return non-negative impact values

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** See `../../BASE_RULES.md` for 96+ universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| EXE-003 | papers/almgren-chriss | Consider market impact of trades | ✅ OK |
| TRD-002 | papers/trading | Validate orders before execution | ✅ OK - estimate_optimal_execution_size |
| BT-004 | papers/backtesting | Realistic costs (market impact) | ✅ OK |
| ARCH-003 | BASE_RULES | Domain has no framework dependencies | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Calculation only |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - Pure functions |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - Used in daily vol calc |

---

## Dependencies
- **External:** numpy (for sqrt, exp, volatility calculations)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/domain/services/backtesting/test_market_impact.py:**
  - Test AlmgrenChristModel permanent/temporary impact calculation
  - Test SquareRootImpactModel formula with sqrt
  - Test LinearImpactModel all-permanent impact
  - Test buy order execution price = expected + impact
  - Test sell order execution price = expected - impact
  - Test participation rate capped at 1.0
  - Test daily volatility conversion (annual/252)
  - Test TemporaryImpact.recover_after_hours exponential decay
  - Test MarketImpactCalculator binary search for optimal size
  - Test calculate_impact_curve returns correct number of points
  - Test MarketImpactResult.impact_percentage calculation
  - Test zero quantity returns zero impact
  - Test volatility adjustment in square root model
  - Test 80/20 split in square root model

---

## Notes
Reference: Almgren, R., & Chriss, N. (2001) "Optimal Execution of Portfolio Transactions" - Industry standard for optimal execution and market impact modeling. Square root law based on empirical studies showing impact ~ (Q/ADV)^0.5.
