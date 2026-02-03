# market_impact.py

## Purpose
Almgren-Chriss market impact model implementation for realistic execution simulation, decomposing impact into permanent and temporary components.

---

## Type Definitions / Data Classes

### ImpactType Enum
```python
class ImpactType(str, Enum):
    PERMANENT = "permanent"    # REQUIRED - Permanent price shift
    TEMPORARY = "temporary"    # REQUIRED - Temporary price movement that recovers
    TOTAL = "total"            # REQUIRED - Combined permanent + temporary
```

**Validation Rules:**
- Used for identifying impact types
- Must match enum values

### AlmgrenChrissConfig Class
```python
@dataclass
class AlmgrenChrissConfig:
    permanent_coef: Decimal = Decimal("0.05")    # OPTIONAL - Permanent impact coefficient γ (gt 0)
    temporary_coef: Decimal = Decimal("0.1")     # OPTIONAL - Temporary impact coefficient η (gt 0)
    volatility_exponent: Decimal = Decimal("0.5")# OPTIONAL - Exponent for volatility (gt 0)
    adv_exponent: Decimal = Decimal("0.5")       # OPTIONAL - Exponent for order size vs ADV (gt 0)
    max_impact_bps: Decimal = Decimal("100")     # OPTIONAL - Maximum impact in bps (gte 0)
```

**Validation Rules:**
- All coefficients must be positive
- Exponents must be positive (typically 0.5 for square root)
- `max_impact_bps` sets upper limit

### MarketImpact Class
```python
@dataclass
class MarketImpact:
    temporary_impact_bps: Decimal              # REQUIRED - Temporary impact in bps (gte 0)
    permanent_impact_bps: Decimal              # REQUIRED - Permanent impact in bps (gte 0)
    total_impact_bps: Decimal                  # REQUIRED - Combined impact in bps (gte 0)
    estimated_price: Decimal                   # REQUIRED - Price after impact (gt 0)
    temporary_impact_dollars: Decimal           # REQUIRED - Temporary impact in $ (gte 0)
    permanent_impact_dollars: Decimal           # REQUIRED - Permanent impact in $ (gte 0)
    total_impact_dollars: Decimal               # REQUIRED - Total impact in $ (gte 0)
```

**Validation Rules:**
- All impact values must be non-negative
- `total_impact_bps` = `permanent_impact_bps` + `temporary_impact_bps`
- `estimated_price` must be positive

### ImpactConfig Class
```python
@dataclass
class ImpactConfig:
    temporary_coef: Decimal = Decimal("0.1")   # OPTIONAL - Temporary coefficient (gt 0)
    permanent_coef: Decimal = Decimal("0.05")  # OPTIONAL - Permanent coefficient (gt 0)
    max_impact_bps: Decimal = Decimal("100")    # OPTIONAL - Maximum impact (gte 0)
```

**Validation Rules:**
- All coefficients must be positive
- `max_impact_bps` must be non-negative

---

## Function Signatures (Contracts)

### `MarketImpactModel.__init__(config: Optional[ImpactConfig] = None) -> None`
**Pre:** config is None or valid ImpactConfig
**Post:** MarketImpactModel initialized with config or defaults
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.calculate_permanent_impact(order_size: Decimal, adv: Decimal, side: str) -> Decimal`
**Pre:** order_size > 0, adv > 0, side in ['buy', 'sell']
**Post:** Returns permanent impact in basis points (gte 0)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.calculate_temporary_impact(order_size: Decimal, adv: Decimal, volatility: Decimal, side: str) -> Decimal`
**Pre:** order_size > 0, adv > 0, volatility >= 0, side in ['buy', 'sell']
**Post:** Returns temporary impact in basis points (gte 0)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.calculate_impact(order_size: Decimal, adv: Decimal, volatility: Decimal, side: str, base_price: Optional[Decimal] = None) -> MarketImpact`
**Pre:** order_size > 0, adv > 0, volatility >= 0, side in ['buy', 'sell']
**Post:** Returns MarketImpact with detailed breakdown
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.calibrate_coefficients(historical_impacts: List[Dict[str, Any]]) -> AlmgrenChrissConfig`
**Pre:** historical_impacts is list of dicts with required keys
**Post:** Returns calibrated AlmgrenChrissConfig
**Raises:** None
**Retry:** No
**Side Effects:** None (currently returns defaults)

### `MarketImpactModel.estimate_impact_range(order_size: Decimal, adv_min: Decimal, adv_max: Decimal, volatility: Decimal, side: str, base_price: Optional[Decimal] = None) -> Tuple[MarketImpact, MarketImpact]`
**Pre:** order_size > 0, adv_min > 0, adv_max >= adv_min, volatility >= 0, side in ['buy', 'sell']
**Post:** Returns (max_impact, min_impact) tuple
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `MarketImpactModel.get_participation_rate_limit(max_impact_bps: Decimal, volatility: Decimal) -> Decimal`
**Pre:** max_impact_bps >= 0, volatility >= 0
**Post:** Returns max participation rate (0 to 0.20)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Permanent impact uses formula: γ * (order_size / ADV)
- [ ] Temporary impact uses formula: η * σ_daily * sqrt(order_size / ADV)
- [ ] Daily volatility = annual_vol / sqrt(252)
- [ ] Total impact never exceeds max_impact_bps
- [ ] Buy orders have estimated_price >= base_price
- [ ] Sell orders have estimated_price <= base_price
- [ ] Participation rate calculation caps at 20%
- [ ] All type hints are present and accurate
- [ ] All Decimal operations use proper quantization

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T00:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit v2.0) |
| **GAPs Found** | 0 P0, 0 P1, 1 P2, 0 P3 |
| **Notes** | Excellent Almgren-Chriss implementation. Minor edge case handling improvement recommended. |

## GAP Details

### P2 (Medium) - 1 gap

#### GAP-P2-001: Edge Case in Participation Rate Calculation (TRD-002 partial violation)
**Rule:** TRD-002 from BASE_RULES.md - "Risk validation: Validate orders before execution"
**Current State:** When `daily_vol = 0`, returns default 1% without warning
**Impact:** Minor - could mask zero volatility inputs which may be invalid
**Location:** Line 452-494
**Evidence:**
```python
def get_participation_rate_limit(self, max_impact_bps: Decimal, volatility: Decimal) -> Decimal:
    # ...
    daily_vol = volatility * self.ANNUAL_TO_DAILY_VOL_FACTOR if volatility > 0 else Decimal("0")
    # ...
    if daily_vol > 0 and self.ac_config.temporary_coef > 0:
        sqrt_x = max_impact_decimal / (self.ac_config.temporary_coef * daily_vol)
        participation_rate = sqrt_x**2
    else:
        participation_rate = Decimal("0.01")  # Default 1% - no warning
```
**Acceptance Criteria:**
- [ ] Add `logger.warning()` when returning default due to zero volatility
- [ ] Document that zero volatility is an edge case
- [ ] Consider raising ValueError for zero volatility if it's invalid input

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule ID | Source | Requirement | Current Status | Gap ID |
|---------|--------|-------------|----------------|---------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK | |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs | |
| EXE-003 | BASE_RULES | Market impact considered | ✅ OK - Core functionality | |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - Logger used for calibration warning | |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ FIXED - All dataclasses frozen=True |
| TRD-002 | BASE_RULES | Risk validation | ⚠️ PARTIAL | GAP-P2-001 |
| TRD-006 | BASE_RULES | Transaction costs in backtesting | ✅ OK - Market impact included |

---

## Dependencies
- **External:** logging, decimal, enum, typing
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/execution/test_market_impact.py:**
  - Test permanent impact calculation
  - Test temporary impact calculation
  - Test complete impact calculation
  - Test impact capped at max_impact_bps
  - Test estimated price for buy orders
  - Test estimated price for sell orders
  - Test daily volatility conversion (annual / sqrt(252))
  - Test participation rate limit calculation
  - Test participation rate capped at 20%
  - Test impact range estimation
  - Test coefficient calibration (currently returns defaults)
  - Test error handling for invalid inputs (negative order_size, zero ADV, negative volatility, invalid side)
  - Test edge case: zero volatility

---

## Notes
- Implements Almgren-Chriss model from "Optimal Execution of Portfolio Transactions" (2001)
- Permanent impact represents information content of trade (persists after execution)
- Temporary impact represents liquidity demand (recovers after execution)
- Daily volatility conversion: daily_vol = annual_vol / sqrt(252)
- Typical coefficient ranges: Permanent 1-10 bps per %ADV, Temporary 5-50 bps
- Overall excellent implementation with proper validation and safety limits
