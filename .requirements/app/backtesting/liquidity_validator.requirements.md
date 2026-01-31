# liquidity_validator.py

## Purpose
Validate order liquidity and implement realistic fill scenarios to prevent execution of orders that cannot be filled based on actual market volume (addresses HIGH PRIORITY #1 from audit).

---

## Type Definitions / Data Classes

### FillResult (dataclass)
```python
@dataclass
class FillResult:
    requested_quantity: Decimal         # REQUIRED - Original order size
    filled_quantity: Decimal            # REQUIRED - Actual quantity filled
    fill_price: Decimal                 # REQUIRED - Execution price
    fill_status: str                    # REQUIRED - "FILLED", "PARTIAL", or "REJECTED"
    rejection_reason: Optional[str] = None
    avg_fill_price: Optional[Decimal] = None  # Set to fill_price if not provided
    market_impact: Optional[Decimal] = None

    def __post_init__():
        if self.avg_fill_price is None:
            self.avg_fill_price = self.fill_price
```

**Validation Rules:**
- `fill_status` must be one of: "FILLED", "PARTIAL", "REJECTED"
- `filled_quantity` <= `requested_quantity`
- `avg_fill_price` defaults to `fill_price`

---

## Function Signatures (Contracts)

### `LiquidityValidator.__init__(enable_partial_fills: bool = True, max_order_pct_of_volume: Optional[Decimal] = None, warning_order_pct_of_volume: Optional[Decimal] = None, partial_fill_pct: Optional[Decimal] = None)`
**Pre:** All percentages valid (0-1 range)
**Post:** LiquidityValidator initialized with thresholds
**Raises:** None
**Retry:** No
**Side Effects:** Logs initialization with threshold values

### `validate_order(order_quantity: Decimal, symbol: str, current_bar, order_side: str = "buy") -> Tuple[bool, str]`
**Pre:** order_quantity > 0, current_bar has volume attribute
**Post:** Returns (is_valid, reason) tuple
**Raises:** None (returns False with reason if validation fails)
**Retry:** No
**Side Effects:** May log warning for large orders (>5% ADV)

### `simulate_fill(order_quantity: Decimal, current_bar, order_side: str = "buy", symbol: str = "UNKNOWN") -> FillResult`
**Pre:** order_quantity > 0, current_bar has volume
**Post:** Returns FillResult with execution details
**Raises:** None
**Retry:** No
**Side Effects:** May log warning for partial fills

### `_calculate_buy_fill_price(current_bar, quantity: Optional[Decimal] = None) -> Decimal`
**Pre:** current_bar has price attribute (close/last/ask)
**Post:** Returns execution price with slippage and market impact
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_sell_fill_price(current_bar, quantity: Optional[Decimal] = None) -> Decimal`
**Pre:** current_bar has price attribute (close/last/bid)
**Post:** Returns execution price with slippage and market impact
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_market_impact(order_quantity: Decimal, current_bar, order_side: str = "buy") -> Decimal`
**Pre:** order_quantity > 0, current_bar has volume
**Post:** Returns estimated price impact (0-0.05 range, capped at 5%)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_liquidity_metrics(current_bar, order_quantity: Optional[Decimal] = None) -> dict`
**Pre:** current_bar has volume
**Post:** Returns dict with liquidity metrics
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Orders >10% ADV are rejected (MAX_ORDER_PCT_OF_VOLUME)
- [ ] Orders >5% ADV trigger warnings (WARNING_ORDER_PCT_OF_VOLUME)
- [ ] Partial fills cap at 5% of daily volume (PARTIAL_FILL_PCT)
- [ ] Buy orders pay more (slippage + market impact)
- [ ] Sell orders receive less (slippage + market impact)
- [ ] Market impact calculated using square-root model
- [ ] Market impact capped at 5% maximum
- [ ] Base slippage 0.1% applied to all orders
- [ ] Additional slippage scales with order size squared
- [ ] Fill status correctly set (FILLED/PARTIAL/REJECTED)
- [ ] Rejection reason provided for rejected orders
- [ ] Liquidity metrics returned correctly

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ⚠️ GAP - current_bar param not typed |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ✅ OK - Most functions small |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Liquidity validation only |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ✅ OK - Warning for large orders |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| TRADING-001 | Custom | Validate order size before execution | ✅ OK - HIGH PRIORITY #1 |
| TRADING-002 | Custom | Realistic partial fills | ✅ OK - Implemented |
| TRADING-003 | Custom | Market impact calculation | ✅ OK - Square-root model |

**HIGH PRIORITY #1 - Audit Findings:**
- ✅ Volume-based rejection (>10% daily volume)
- ✅ Warning for large orders (>5% daily volume)
- ✅ Partial fills for orders exceeding liquidity
- ✅ Market impact calculation
- ✅ Realistic execution prices with slippage

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, dataclasses, decimal, typing
- **Internal:** None (standalone module)

---

## Required Tests
- **test_liquidity_validator.py:**
  - Success: Small order filled completely
  - Success: Order at 5% warning threshold (warning logged)
  - Success: Order at 10% rejection threshold (rejected)
  - Success: Partial fill for order >5% ADV
  - Success: Market impact calculation (scales with size)
  - Success: Buy price > current price (slippage)
  - Success: Sell price < current price (slippage)
  - Success: Square-root market impact model
  - Success: Market impact capped at 5%
  - Error: Zero or negative volume
  - Error: No volume data on current_bar
  - Edge: Order exactly at warning threshold
  - Edge: Order exactly at max threshold
  - Edge: Partial fills disabled (should reject)
  - Integration: get_liquidity_metrics returns correct values

---

## Notes
- Addresses HIGH PRIORITY #1 from audit report
- Default thresholds: 10% max, 5% warning, 5% partial fill
- Base slippage: 0.1% (unfavorable execution)
- Market impact model: impact = 0.1 * sqrt(order_pct)
- Maximum additional slippage: 1%
- Pessimistic execution (always assumes worst case)
