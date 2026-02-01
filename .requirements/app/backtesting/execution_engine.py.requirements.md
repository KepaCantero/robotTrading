# execution_engine.py

## Purpose
Implements pessimistic execution engine for realistic backtesting that eliminates look-ahead bias by executing signals at next bar open and applying worst-case stop-loss execution.

---

## Type Definitions / Data Classes

### ExecutionType (Enum)
```python
class ExecutionType(str, Enum):
    OPTIMISTIC = "optimistic"    # Best case: TP before SL
    PESSIMISTIC = "pessimistic"  # Worst case: SL before TP (Req #10)
    REALISTIC = "realistic"      # Mid-point estimate
```

### ExecutionResult (DataClass)
```python
@dataclass
class ExecutionResult:
    symbol: str                          # REQUIRED - Trading symbol
    side: str                            # REQUIRED - "buy" or "sell"
    quantity: Decimal                    # REQUIRED - Order quantity
    signal_time: datetime                # REQUIRED - Time signal generated (close of bar t)
    execution_time: datetime             # REQUIRED - Time order executed (open of bar t+1)
    signal_price: Decimal                # REQUIRED - Price at signal time
    execution_price: Decimal             # REQUIRED - Actual fill price with slippage
    slippage_bps: Decimal                # REQUIRED - Slippage in basis points
    commission: Decimal                  # REQUIRED - Commission cost
    executed: bool                       # REQUIRED - True if order filled
    partial_fill: bool = False           # OPTIONAL - Partial fill occurred
    fill_ratio: Decimal = Decimal("1")   # OPTIONAL - Amount actually filled (0-1)
    stop_loss_hit: bool = False          # OPTIONAL - Stop loss was triggered
    take_profit_hit: bool = False        # OPTIONAL - Take profit was triggered
    stop_execution_price: Optional[Decimal] = None  # OPTIONAL - Price at which stop executed
```

**Validation Rules:**
- `quantity > 0`
- `signal_time <= execution_time` (signal precedes execution)
- `fill_ratio in (0, 1]`
- `slippage_bps >= 0`

### Position (DataClass)
```python
@dataclass
class Position:
    symbol: str                              # REQUIRED - Trading symbol
    side: str                                # REQUIRED - "long" or "short"
    quantity: Decimal                        # REQUIRED - Position size
    entry_price: Decimal                     # REQUIRED - Entry price
    entry_time: datetime                     # REQUIRED - Entry timestamp
    stop_loss_price: Optional[Decimal] = None        # OPTIONAL - Stop loss level
    take_profit_price: Optional[Decimal] = None     # OPTIONAL - Take profit level
    stop_loss_bps: Optional[Decimal] = None         # OPTIONAL - SL in basis points
    take_profit_bps: Optional[Decimal] = None       # OPTIONAL - TP in basis points
```

**Validation Rules:**
- `quantity > 0`
- `entry_price > 0`
- `side in ["long", "short"]`
- If `stop_loss_price` set: must be < entry_price for long, > entry_price for short
- If `take_profit_price` set: must be > entry_price for long, < entry_price for short

---

## Function Signatures (Contracts)

### `__init__(execution_type, base_slippage_bps, cost_calculator, enable_next_day_execution)`
**Pre:** base_slippage_bps >= 0 (or None for config default)
**Post:** ExecutionEngine initialized with specified parameters
**Raises:** No
**Retry:** No
**Side Effects:** Creates CostCalculator instance if not provided

### `execute_entry_order(symbol, side, quantity, signal_time, signal_price, next_open_price, next_bar_time, volatility) -> ExecutionResult`
**Pre:** quantity > 0, next_open_price > 0, signal_time < next_bar_time
**Post:** Returns ExecutionResult with executed=True, execution_price includes slippage
**Raises:** No
**Retry:** No
**Side Effects:** No state changes (pure execution simulation)

### `process_intra_bar_execution(position, bar_open, bar_high, bar_low, bar_close, bar_time) -> Tuple[Optional[ExecutionResult], Optional[Position]]`
**Pre:** position.quantity > 0, bar_low > 0, bar_high > 0
**Post:** Returns (execution_result, None) if position closed, (None, position) if open
**Raises:** No
**Retry:** No
**Side Effects:** No state changes (pure simulation logic)

### `_calculate_slippage(side, volatility) -> Decimal`
**Pre:** side in ["buy", "sell"], volatility >= 0 or None
**Post:** Returns slippage in bps >= 0
**Raises:** No
**Retry:** No
**Side Effects:** No external state changes

### `compare_vs_optimistic(quotes, signals) -> Dict[str, Any]`
**Pre:** quotes is list of Quote objects, signals is list of signals
**Post:** Returns comparison metrics between pessimistic and optimistic execution
**Raises:** No
**Retry:** No
**Side Effects:** No state changes (comparison only)

### `create_position_with_stops(symbol, side, quantity, entry_price, entry_time, stop_loss_pct, take_profit_pct) -> Position`
**Pre:** quantity > 0, entry_price > 0, stop_loss_pct >= 0, take_profit_pct >= 0
**Post:** Returns Position with calculated stop/take profit prices
**Raises:** No
**Retry:** No
**Side Effects:** No external state changes (pure factory function)

---

## Acceptance Criteria
- [ ] Entry orders execute at next bar open (not current bar close) - prevents look-ahead bias
- [ ] Slippage applied unfavorably (buy pays more, sell receives less)
- [ ] Volatility-based slippage increases with market volatility
- [ ] Pessimistic execution: SL executes before TP when both hit in same bar
- [ ] Commission calculated using CostCalculator for each execution
- [ ] Stop slippage multiplier applied to stop execution (config.STOP_SLIPPAGE_MULTIPLIER)
- [ ] ExecutionResult accurately tracks all execution details
- [ ] Position with stops correctly calculates stop/take profit levels for long and short

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| LOG-004 | 09-logging-observability.md | All exceptions logged | ✅ OK |
| BT-003 | papers/10-robert-carver-systematic-trading | No look-ahead bias | ✅ OK - signals execute at t+1 open |
| BT-004 | papers/10-robert-carver-systematic-trading | Realistic execution | ✅ OK - pessimistic execution |
| CC-006 | 05-architecture.md | Explicit error handling | ⚠️ NOT APPLIED - No explicit error handling needed |
| TST-005 | 06-testing.md | Coverage > 80% | ⚠️ NOT APPLIED - Test coverage not measured |
| SEC-001 | 28-security-and-secrets.md | No hardcoded secrets | ✅ OK |

**GAP Analysis:**
- No critical gaps found - this is a well-structured, focused module
- Class follows SRP (only handles execution simulation)
- Functions are reasonably sized (< 100 lines)
- Clear separation of concerns

---

## Dependencies
- **External:**
  - `dataclasses.dataclass` - Data structures
  - `datetime.datetime` - Timestamps
  - `decimal.Decimal` - Precise financial calculations
  - `enum.Enum` - ExecutionType enumeration
  - `typing` - Type hints (Dict, List, Optional, Tuple, Any)
  - `logging` - Structured logging
- **Internal:**
  - `app.backtesting.constants.BACKTESTING_CONSTANTS` - Configuration constants
  - `app.backtesting.cost_calculator.CostCalculator` - Commission calculation
  - `app.models.market_data.Quote` - Market data model

---

## Required Tests
- **tests/unit/backtesting/test_execution_engine.py:**
  - `test_execute_entry_order_at_next_bar_open` - Execution happens at t+1, not t
  - `test_slippage_applied_unfavorably` - Buy pays more, sell receives less
  - `test_volatility_increases_slippage` - Higher volatility = higher slippage
  - `test_pessimistic_execution_sl_before_tp_long` - Both hit: SL executes first (long)
  - `test_pessimistic_execution_sl_before_tp_short` - Both hit: SL executes first (short)
  - `test_only_stop_loss_triggers` - SL hit, TP not hit
  - `test_only_take_profit_triggers` - TP hit, SL not hit
  - `test_commission_calculated_on_execution` - CostCalculator used for commission
  - `test_stop_slippage_multiplier_applied` - Stop execution has higher slippage
  - `test_create_position_with_stops_long` - Correct SL/TP prices for long
  - `test_create_position_with_stops_short` - Correct SL/TP prices for short
  - `test_compare_vs_optimistic_metrics` - Comparison returns expected structure

---

## Notes
- **Critical:** Pessimistic execution (Req #10) prevents over-optimistic backtesting results
- **Next Day Execution:** When enabled, ensures signals generated at close t execute at open t+1
- **Stop Slippage Multiplier:** From config - typically higher than entry slippage
- **No State Management:** This is a pure execution engine - does not track positions
