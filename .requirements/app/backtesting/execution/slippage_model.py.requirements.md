# slippage_model.py

## Purpose
Advanced slippage modeling for realistic execution simulation based on order size, volatility, bid-ask spread, time-of-day, and market capitalization.

---

## Type Definitions / Data Classes

### TimeOfDay Enum
```python
class TimeOfDay(str, Enum):
    PRE_MARKET = "pre_market"      # REQUIRED - Before 9:30 AM ET
    OPEN = "open"                  # REQUIRED - 9:30-10:00 AM ET (high slippage)
    MORNING = "morning"            # REQUIRED - 10:00 AM - 12:00 PM ET
    LUNCH = "lunch"                # REQUIRED - 12:00 PM - 1:00 PM ET (lower slippage)
    AFTERNOON = "afternoon"        # REQUIRED - 1:00 PM - 3:30 PM ET
    CLOSE = "close"                # REQUIRED - 3:30-4:00 PM ET (high slippage)
    AFTER_HOURS = "after_hours"    # REQUIRED - After 4:00 PM ET
```

**Validation Rules:**
- Enum values must be valid time periods
- Used for time-of-day impact multipliers

### MarketCapCategory Enum
```python
class MarketCapCategory(str, Enum):
    LARGE_CAP = "large_cap"    # REQUIRED - >$10B market cap
    MID_CAP = "mid_cap"        # REQUIRED - $1B-$10B market cap
    SMALL_CAP = "small_cap"    # REQUIRED - $100M-$1B market cap
    MICRO_CAP = "micro_cap"    # REQUIRED - <$100M market cap
```

**Validation Rules:**
- Used for determining base slippage rates
- Classification based on average daily dollar volume

### TimeOfDayImpact Class
```python
@dataclass
class TimeOfDayImpact:
    time_of_day: TimeOfDay                    # REQUIRED - Time category
    slippage_multiplier: Decimal              # REQUIRED - Multiplier applied to base slippage (gt 0)
    volume_participation_rate: Decimal        # REQUIRED - Typical participation rate (gte 0, lte 1)
    description: str                          # REQUIRED - Human-readable description
```

**Validation Rules:**
- `slippage_multiplier` must be positive
- `volume_participation_rate` must be between 0 and 1
- Used for applying time-based slippage adjustments

### SlippageConfig Class
```python
@dataclass
class SlippageConfig:
    base_slippage_bps: Decimal = Decimal("5")              # OPTIONAL - Base slippage in basis points (gte 0)
    vol_multiplier: Decimal = Decimal("2")                 # OPTIONAL - Volatility multiplier (gt 0)
    adv_impact_exponent: Decimal = Decimal("2")            # OPTIONAL - Exponent for ADV impact (gt 0)
    spread_impact: bool = True                            # OPTIONAL - Include spread impact
    time_of_day_impact: bool = True                       # OPTIONAL - Apply time-of-day multipliers
    market_cap_impact: bool = True                        # OPTIONAL - Adjust for market cap
    max_slippage_bps: Decimal = Decimal("50")             # OPTIONAL - Maximum slippage (gte 0)
```

**Validation Rules:**
- All Decimal fields must be non-negative
- Multipliers must be positive
- `max_slippage_bps` sets upper limit on calculated slippage

### SlippageEstimate Class
```python
@dataclass
class SlippageEstimate:
    basis_points: Decimal                        # REQUIRED - Slippage in basis points (gte 0)
    price_adjustment: Decimal                    # REQUIRED - Adjustment to price (gte 0, lte 1)
    fill_probability: float                      # REQUIRED - Probability of fill (gte 0, lte 1)
    estimated_fill_price: Decimal                # REQUIRED - Estimated execution price (gt 0)
    time_of_day_impact: Decimal                  # REQUIRED - Applied time-of-day multiplier (gt 0)
    volatility_impact: Decimal                   # REQUIRED - Applied volatility multiplier (gt 0)
    adv_impact: Decimal                          # REQUIRED - Impact from order size vs ADV (gte 0)
    spread_impact: Decimal                       # REQUIRED - Impact from bid-ask spread (gte 0)
    components: Dict[str, Decimal]               # OPTIONAL - Detailed breakdown (default empty)
```

**Validation Rules:**
- `basis_points` must be non-negative
- `price_adjustment` must be between 0 and 1
- `fill_probability` must be between 0 and 1
- `estimated_fill_price` must be positive

---

## Function Signatures (Contracts)

### `SlippageModel.__init__(config: Optional[SlippageConfig] = None) -> None`
**Pre:** config is None or valid SlippageConfig
**Post:** SlippageModel initialized with config or defaults
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.classify_market_cap(adv_dollar_volume: Decimal) -> MarketCapCategory`
**Pre:** adv_dollar_volume > 0
**Post:** Returns appropriate MarketCapCategory
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.calculate_base_slippage(adv: Decimal, volatility: Optional[Decimal] = None) -> Decimal`
**Pre:** adv > 0
**Post:** Returns base slippage in basis points (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.calculate_adv_impact(order_value: Decimal, adv: Decimal) -> Decimal`
**Pre:** order_value > 0, adv > 0
**Post:** Returns additional slippage in basis points from order size (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.calculate_volatility_impact(volatility: Optional[Decimal], vix: Optional[Decimal] = None) -> Decimal`
**Pre:** volatility is None or >= 0, vix is None or >= 0
**Post:** Returns volatility multiplier (gte 1.0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.calculate_time_of_day_impact(time_of_day: TimeOfDay) -> Decimal`
**Pre:** time_of_day is valid TimeOfDay enum
**Post:** Returns time-of-day multiplier (gt 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.calculate_spread_impact(bid: Decimal, ask: Decimal, current_price: Decimal) -> Decimal`
**Pre:** bid > 0, ask > 0, current_price > 0, ask > bid
**Post:** Returns spread impact in basis points (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageModel.estimate_slippage(symbol: str, side: str, shares: int, current_price: Decimal, bid: Decimal, ask: Decimal, adv: Decimal, volatility: Optional[Decimal] = None, vix: Optional[Decimal] = None, timestamp: Optional[object] = None) -> SlippageEstimate`
**Pre:** shares > 0, current_price > 0, bid > 0, ask > bid, adv > 0, side in ['buy', 'sell']
**Post:** Returns SlippageEstimate with detailed breakdown
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All slippage calculations return non-negative values
- [ ] Fill probability is always between 0 and 1
- [ ] Maximum slippage is never exceeded
- [ ] Buy orders have estimated_fill_price >= current_price
- [ ] Sell orders have estimated_fill_price <= current_price
- [ ] Time-of-day multipliers match documented values
- [ ] Market cap classification uses correct ADV thresholds
- [ ] All type hints are present and accurate
- [ ] All Decimal operations use proper quantization

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T00:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit v2.0) |
| **GAPs Found** | 0 P0, 0 P1, 1 P2, 0 P3 |
| **Notes** | Minor Decimal quantization issue only. Overall excellent implementation. |

## GAP Details

### P2 (Medium) - 1 gap

#### GAP-P2-001: Decimal Quantization Inconsistency (TRD-006 partial violation)
**Rule:** TRD-006 from BASE_RULES.md - "Transaction costs: Include costs in backtesting"
**Current State:** `SlippageEstimate.total_impact_dollars()` calculation missing quantization
**Impact:** Minor floating point precision issues in cost calculations
**Location:** Line 180-191
**Evidence:**
```python
def total_impact_dollars(self, shares: int) -> Decimal:
    price_value = Decimal(str(shares)) * self.estimated_fill_price
    return price_value * (self.basis_points / Decimal("10000"))  # No quantize
```
**Acceptance Criteria:**
- [ ] Add `.quantize(Decimal("0.01"))` to return value
- [ ] Document precision requirements in docstring
- [ ] Add test for decimal precision

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule ID | Source | Requirement | Current Status | Gap ID |
|---------|--------|-------------|----------------|---------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK | |
| TYP-002 | BASE_RULES | Modern syntax | ✅ OK | |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - field_default_factory used | |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs | |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - Logger imported and used | |
| TRD-006 | BASE_RULES | Transaction costs in backtesting | ⚠️ PARTIAL | GAP-P2-001 |
| EXE-001 | BASE_RULES | Order validation | ✅ OK - Input validation in estimate_slippage | |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ FIXED - All dataclasses frozen=True |

---

## Dependencies
- **External:** logging, decimal, enum
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/execution/test_slippage_model.py:**
  - Test market cap classification with various ADV values
  - Test base slippage calculation for each market cap category
  - Test ADV impact calculation with different order sizes
  - Test volatility impact with various VIX levels
  - Test time-of-day impact multipliers
  - Test spread impact calculation
  - Test complete slippage estimation for buy orders
  - Test complete slippage estimation for sell orders
  - Test maximum slippage cap is enforced
  - Test fill probability estimation
  - Test error handling for invalid inputs (negative shares, zero price, invalid side)

---

## Notes
- Slippage model implements Almgren-Chriss framework for realistic execution simulation
- Time-of-day impacts based on "Algorithmic Trading" by Barry Johnson
- Market cap base slippage ranges: Large cap 2-5 bps, Mid cap 5-10 bps, Small cap 10-25 bps, Micro cap 25-50 bps
- Overall excellent implementation with comprehensive input validation
