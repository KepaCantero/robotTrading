# slippage.py

## Purpose
Implements various slippage models for realistic backtesting including linear, percentage, volatility-adjusted, time-weighted, and spread-aware slippage following Johnson's Algorithmic Trading & DMA framework.

---

## Type Definitions / Data Classes

### SlippageType Enum
```python
class SlippageType(str, Enum):
    LINEAR = "linear"
    PERCENTAGE = "percentage"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    TIME_WEIGHTED = "time_weighted"
```
**Validation Rules:** Must be one of the four defined slippage model types

### SlippageResult DataClass
```python
@dataclass
class SlippageResult:
    expected_price: Decimal           # REQUIRED - Expected execution price
    execution_price: Decimal          # REQUIRED - Actual execution price
    slippage_amount: Decimal          # REQUIRED - Absolute slippage amount
    slippage_percentage: float        # REQUIRED - Slippage as percentage
    side: str                         # REQUIRED - 'buy' or 'sell'
```
**Validation Rules:**
- `expected_price` and `execution_price` must be > 0
- `slippage_amount` = |execution_price - expected_price|
- `adverse` property returns True if slippage is unfavorable (buy@higher, sell@lower)

### SpreadAwareSlippageConfig DataClass
```python
@dataclass
class SpreadAwareSlippageConfig:
    half_spread: bool = True              # Use half spread for slippage
    spread_skew: float = 0.5              # Skew towards bid or ask (0.5 = centered)
    liquidity_premium: float = 0.0001     # Additional cost for illiquid stocks
```
**Validation Rules:**
- `spread_skew` in range [0.0, 1.0]
- `liquidity_premium` >= 0

---

## Function Signatures (Contracts)

### `SlippageModel.calculate_slippage(symbol, side, quantity, price, timestamp, volume, volatility, spread) -> SlippageResult`
**Pre:** side in ['buy', 'sell'], quantity >= 0, price > 0
**Post:** Returns SlippageResult with execution details
**Raises:** None (returns zero slippage if invalid inputs)
**Retry:** No
**Side Effects:** None (pure calculation)

### `LinearSlippageModel.__init__(base_rate, volume_factor)`
**Pre:** base_rate >= 0, volume_factor >= 0
**Post:** Model initialized with linear slippage parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `LinearSlippageModel.calculate_slippage(...) -> SlippageResult`
**Pre:** volume > 0 if provided
**Post:** Slippage = base_rate + volume_factor * (quantity / volume)
**Post:** Buy orders: execution_price = price + slippage
**Post:** Sell orders: execution_price = price - slippage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PercentageSlippageModel.__init__(buy_slippage, sell_slippage)`
**Pre:** buy_slippage >= 0, sell_slippage >= 0
**Post:** Model initialized with fixed percentage slippage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `PercentageSlippageModel.calculate_slippage(...) -> SlippageResult`
**Pre:** price > 0
**Post:** Applies buy_slippage or sell_slippage based on side
**Post:** Adds half spread to slippage if spread provided
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VolatilityAdjustedSlippage.__init__(base_rate, vol_sensitivity, benchmark_vol)`
**Pre:** base_rate >= 0, vol_sensitivity >= 0, benchmark_vol > 0
**Post:** Model initialized with volatility adjustment parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `VolatilityAdjustedSlippage.calculate_slippage(...) -> SlippageResult`
**Pre:** volatility >= 0 if provided
**Post:** Slippage adjusted by volatility ratio: vol/benchmark_vol
**Post:** Formula: base_rate * (1 + vol_sensitivity * (vol_ratio - 1))
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TimeWeightedSlippageModel.__init__(base_slippage, open_multiplier, close_multiplier)`
**Pre:** base_slippage >= 0, open_multiplier >= 1.0, close_multiplier >= 1.0
**Post:** Model initialized with time-based multipliers
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TimeWeightedSlippageModel._get_time_multiplier(timestamp) -> float`
**Pre:** timestamp is valid datetime or None
**Post:** Returns multiplier based on time of day:
  - Open (9:30-10:00 ET): open_multiplier
  - Close (15:00-16:00 ET): close_multiplier
  - Mid-day: 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TimeWeightedSlippageModel.calculate_slippage(...) -> SlippageResult`
**Pre:** timestamp in valid range
**Post:** Applies time multiplier to base slippage
**Post:** Adds volatility adjustment if provided
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SpreadAwareSlippageModel.__init__(config)`
**Pre:** config is SpreadAwareSlippageConfig or None
**Post:** Model initialized with spread-aware configuration
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SpreadAwareSlippageModel.calculate_slippage(...) -> SlippageResult`
**Pre:** price > 0 if spread provided
**Post:** Applies spread component based on side and skew
**Post:** Buy: spread_pct * (0.5 + skew * 0.5)
**Post:** Sell: spread_pct * (0.5 + (1-skew) * 0.5)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SlippageResult.adverse -> bool`
**Pre:** side is 'buy' or 'sell'
**Post:** Returns True if execution worse than expected
**Post:** Buy adverse: execution_price > expected_price
**Post:** Sell adverse: execution_price < expected_price
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-SLIP-001: Buy orders have higher execution price (slippage adds)
- [ ] AC-SLIP-002: Sell orders have lower execution price (slippage subtracts)
- [ ] AC-SLIP-003: Linear slippage increases with volume ratio
- [ ] AC-SLIP-004: Volatility-adjusted slippage increases with volatility
- [ ] AC-SLIP-005: Time-weighted model applies open/close multipliers correctly
- [ ] AC-SLIP-006: Spread-aware model skews based on side
- [ ] AC-SLIP-007: SlippageResult.adverse correctly identifies unfavorable fills
- [ ] AC-SLIP-008: Zero slippage returned when volume is zero or None

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** See `../../BASE_RULES.md` for 96+ universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-004 | papers/backtesting | Include slippage in backtesting | ✅ OK |
| EXE-002 | papers/johnson-dma | Handle execution timing properly | ✅ OK |
| ARCH-003 | BASE_RULES | Domain has no framework dependencies | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Calculation only |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - Pure functions |

---

## Dependencies
- **External:** numpy (for volatility calculations)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/domain/services/backtesting/test_slippage.py:**
  - Test buy order slippage increases price
  - Test sell order slippage decreases price
  - Test LinearSlippageModel with volume ratio
  - Test PercentageSlippageModel with spread
  - Test VolatilityAdjustedSlippage with high/low volatility
  - Test TimeWeightedSlippageModel at open, midday, close
  - Test SpreadAwareSlippageModel buy/sell skew
  - Test SlippageResult.adverse property
  - Test zero volume returns base slippage only
  - Test None timestamp returns 1.0 multiplier
  - Test spread component calculation (half spread)

---

## Notes
Reference: Johnson, B. (2010) "Algorithmic Trading & DMA" - Industry standard for slippage modeling in electronic trading. Time periods based on US market hours (ET).
