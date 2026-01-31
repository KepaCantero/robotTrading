# execution_engine.py

## Purpose
Pessimistic Execution Engine for Professional Backtesting - Implements realistic order execution that eliminates Look-Ahead Bias with signal at close t, execution at open t+1, and pessimistic execution (SL before TP in same bar).

---

## Type Definitions / Data Classes

### ExecutionType (str, Enum)
```python
class ExecutionType(str, Enum):
    OPTIMISTIC = "optimistic"      # Best case: TP before SL
    PESSIMISTIC = "pessimistic"    # Worst case: SL before TP (Req #10)
    REALISTIC = "realistic"        # Mid-point estimate
```

### ExecutionResult
```python
@dataclass
class ExecutionResult:
    """Result of an order execution."""
    symbol: str
    side: str                              # "buy" or "sell"
    quantity: Decimal
    signal_time: datetime                  # Time signal was generated (close of bar t)
    execution_time: datetime               # Time order was executed (open of bar t+1)
    signal_price: Decimal                  # Price at signal time
    execution_price: Decimal               # Actual fill price (with slippage)
    slippage_bps: Decimal                  # Slippage in basis points
    commission: Decimal
    executed: bool
    partial_fill: bool = False
    fill_ratio: Decimal = Decimal("1")
    stop_loss_hit: bool = False
    take_profit_hit: bool = False
    stop_execution_price: Optional[Decimal] = None
```

### Position
```python
@dataclass
class Position:
    """Open position tracking for intra-bar execution."""
    symbol: str
    side: str                              # "long" or "short"
    quantity: Decimal
    entry_price: Decimal
    entry_time: datetime
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    stop_loss_bps: Optional[Decimal] = None
    take_profit_bps: Optional[Decimal] = None
```

### PessimisticExecutionEngine
```python
class PessimisticExecutionEngine:
    """
    Pessimistic Execution Engine (Req #10 - CRITICAL).

    Implements:
    1. Signal at close t, execution at open t+1 (prevents Look-Ahead Bias)
    2. Pessimistic Execution: SL before TP in same bar (worst-case)
    3. Realistic slippage on execution

    This provides more conservative backtesting results.
    """
```

---

## Function Signatures (Contracts)

### `PessimisticExecutionEngine.__init__(
    execution_type: ExecutionType = ExecutionType.PESSIMISTIC,
    base_slippage_bps: Optional[Decimal] = None,
    cost_calculator: Optional[CostCalculator] = None,
    enable_next_day_execution: Optional[bool] = None,
) -> None`
**Pre:** execution_type is valid ExecutionType
**Post:** Engine initialized with config or provided defaults
**Raises:** None
**Retry:** No
**Side Effects:** Initializes open_positions list

**Defaults (from config if not provided):**
- execution_type: PESSIMISTIC
- base_slippage_bps: EXEC_CONSTANTS.BASE_SLIPPAGE_BPS
- enable_next_day_execution: EXEC_CONSTANTS.ENABLE_NEXT_DAY_EXECUTION
- cost_calculator: New CostCalculator() if not provided

### `PessimisticExecutionEngine.execute_entry_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    signal_time: datetime,
    signal_price: Decimal,
    next_open_price: Decimal,
    next_bar_time: datetime,
    volatility: Optional[Decimal] = None,
) -> ExecutionResult`
**Pre:** symbol non-empty; side is "buy" or "sell"; quantity > 0; prices > 0
**Post:** Returns ExecutionResult with execution details
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Execution Rule:** Signal generated at close of bar t, executed at open of bar t+1

**Slippage Application:**
- **Buy:** `execution_price = next_open_price × (1 + slippage_bps/10000)` - pay more
- **Sell:** `execution_price = next_open_price × (1 - slippage_bps/10000)` - receive less

**Volatility Adjustment:** Higher volatility → higher slippage (using config multiplier)

### `PessimisticExecutionEngine.process_intra_bar_execution(
    position: Position,
    bar_open: Decimal,
    bar_high: Decimal,
    bar_low: Decimal,
    bar_close: Decimal,
    bar_time: datetime,
) -> Tuple[Optional[ExecutionResult], Optional[Position]]`
**Pre:** position is valid; OHLC prices > 0
**Post:** Returns (execution_result_if_closed, remaining_position)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Pessimistic Execution Rule (Req #10 - CRITICAL):**
- If BOTH SL and TP are hit in same bar, SL executes FIRST (worst case)
- This prevents over-optimistic backtesting

**Long Position:**
- SL hit: bar_low <= stop_loss_price
- TP hit: bar_high >= take_profit_price

**Short Position:**
- SL hit: bar_high >= stop_loss_price
- TP hit: bar_low <= take_profit_price

**Stop Slippage:** Applied using config multiplier (EXEC_CONSTANTS.STOP_SLIPPAGE_MULTIPLIER)

### `PessimisticExecutionEngine._calculate_slippage(side: str, volatility: Optional[Decimal]) -> Decimal`
**Pre:** side is "buy" or "sell"
**Post:** Returns slippage in basis points
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `base_slippage_bps × (1 + volatility × VOLATILITY_MULTIPLIER)`

### `PessimisticExecutionEngine.compare_vs_optimistic(
    quotes: List[Quote],
    signals: List[Any],
) -> Dict[str, Any]`
**Pre:** quotes and signals are valid lists
**Post:** Returns comparison dictionary
**Raises:** None
**Retry:** No
**Side Effects:** Runs both optimistic and pessimistic simulations

**Output Format:**
```python
{
    'pessimistic': {...},
    'optimistic': {...},
    'slippage_difference': float,
    'pessimistic_more_expensive': bool
}
```

### `create_position_with_stops(
    symbol: str,
    side: str,
    quantity: Decimal,
    entry_price: Decimal,
    entry_time: datetime,
    stop_loss_pct: Optional[Decimal] = None,
    take_profit_pct: Optional[Decimal] = None,
) -> Position`
**Pre:** symbol non-empty; side is "long" or "short"; prices > 0; pcts >= 0
**Post:** Returns Position with calculated stop prices
**Raises:** None
**Retry:** No
**Side Effects:** None (pure factory)

**Stop Price Calculation:**
- **Long SL:** `entry_price × (1 - stop_loss_pct)`
- **Long TP:** `entry_price × (1 + take_profit_pct)`
- **Short SL:** `entry_price × (1 + stop_loss_pct)`
- **Short TP:** `entry_price × (1 - take_profit_pct)`

---

## Acceptance Criteria
- [ ] **AC-001:** ExecutionType has OPTIMISTIC, PESSIMISTIC, REALISTIC values
- [ ] **AC-002:** execute_entry_order() executes at next_bar_time (t+1), not signal_time
- [ ] **AC-003:** execute_entry_order() applies slippage to execution price
- [ ] **AC-004:** Buy orders pay more (slippage increases price)
- [ ] **AC-005:** Sell orders receive less (slippage decreases price)
- [ ] **AC-006:** process_intra_bar_execution() checks SL and TP hits
- [ ] **AC-007:** Pessimistic execution: SL before TP when both hit in same bar
- [ ] **AC-008:** Slippage applied to stop execution using multiplier
- [ ] **AC-009:** Volatility increases slippage calculation
- [ ] **AC-010:** compare_vs_optimistic() shows pessimistic vs optimistic difference
- [ ] **AC-011:** create_position_with_stops() calculates correct stop prices
- [ ] **AC-012:** Long SL is below entry, TP is above entry
- [ ] **AC-013:** Short SL is above entry, TP is below entry
- [ ] **AC-014:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Execution Engine):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Look-ahead bias prevention | Pardo (2008) | Signal at close t, exec at open t+1 | ✅ OK - execute_entry_order() |
| Pessimistic execution | Pardo (2008) | SL before TP in same bar | ✅ OK - process_intra_bar_execution() |
| Slippage modeling | Backtesting standard | Realistic price adjustment | ✅ OK - _calculate_slippage() |
| Commission calculation | Backtesting standard | Transaction costs | ✅ OK - CostCalculator |
| Volatility-based slippage | Market microstructure | Higher vol = higher slip | ✅ OK - _calculate_slippage() |
| Stop execution | Trading | Intra-bar stop checking | ✅ OK - process_intra_bar_execution() |
| Position tracking | Backtracking | Open position management | ✅ OK - Position dataclass |
| Cost calculator dependency | DDD (DIP) | Injected or created | ✅ OK - __init__() |
| Configuration constants | Clean code | From BACKTESTING_CONSTANTS | ✅ OK - EXEC_CONSTANTS |
| Factory function | Clean code | create_position_with_stops() | ✅ OK - Factory |
| Enum for execution type | Clean code | ExecutionType enum | ✅ OK - ExecutionType |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for prices | ✅ OK - Decimal types |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008) for backtesting standards.

---

## Dependencies
- **External:** `decimal` (std), `datetime` (std), `dataclasses` (std), `enum` (std), `logging` (std), `typing` (std)
- **Internal:**
  - `app.backtesting.constants.BACKTESTING_CONSTANTS`
  - `app.backtesting.cost_calculator.CostCalculator`
  - `app.models.market_data.Quote`

---

## Required Tests
- **test_execution_engine.py:**
  - `test_execution_type_enum()` - OPTIMISTIC, PESSIMISTIC, REALISTIC
  - `test_init_with_defaults()` - Uses config defaults
  - `test_init_with_overrides()` - Uses provided values
  - `test_execute_entry_order_buy()` - Executes at next_bar_time
  - `test_execute_entry_order_sell()` - Executes at next_bar_time
  - `test_execute_entry_buy_slippage()` - Price increased
  - `test_execute_entry_sell_slippage()` - Price decreased
  - `test_execute_entry_commission()` - Commission calculated
  - `test_volatility_increases_slippage()` - Higher vol = higher slip
  - `test_process_intra_bar_long_sl_hit()` - Closes position
  - `test_process_intra_bar_long_tp_hit()` - Closes position
  - `test_process_intra_bar_long_both_hit()` - SL executes first (pessimistic)
  - `test_process_intra_bar_short_sl_hit()` - Closes position
  - `test_process_intra_bar_short_tp_hit()` - Closes position
  - `test_process_intra_bar_short_both_hit()` - SL executes first (pessimistic)
  - `test_process_intra_bar_no_hit()` - Position unchanged
  - `test_process_intra_bar_slippage_on_stop()` - Slippage applied
  - `test_calculate_slippage()` - Returns base slippage
  - `test_calculate_slippage_with_volatility()` - Increased with vol
  - `test_compare_vs_optimistic()` - Returns comparison
  - `test_create_position_with_stops_long()` - SL below, TP above
  - `test_create_position_with_stops_short()` - SL above, TP below
  - `test_create_position_no_stops()` - None values

---

## Notes
- **Critical:** PessimisticExecutionEngine prevents LOOK-AHEAD BIAS (Pardo, 2008)
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008)
- **Look-Ahead Bias:** Occurs when backtesting assumes execution at signal price
  - **Reality:** Signal generated at close of bar t, can only execute at open of bar t+1
  - **This Engine:** Correctly implements next-bar execution
- **Pessimistic Execution (Req #10 - CRITICAL):**
  - When BOTH stop loss AND take profit are hit in the same bar
  - **Pessimistic:** Stop loss executes FIRST (worst case)
  - **Prevents:** Over-optimistic results assuming TP before SL
  - **Realistic:** Markets can move through both levels in either direction
- **Slippage Modeling:**
  - **Base slippage:** From config (EXEC_CONSTANTS.BASE_SLIPPAGE_BPS)
  - **Volatility adjustment:** Higher volatility → higher slippage
  - **Multiplier:** From config (EXEC_CONSTANTS.VOLATILITY_MULTIPLIER)
  - **Stop slippage:** Uses separate multiplier (EXEC_CONSTANTS.STOP_SLIPPAGE_MULTIPLIER)
- **Directional Slippage:**
  - **Buy:** Pay more (price increases)
  - **Sell:** Receive less (price decreases)
  - Always worse for the trader (realistic)
- **Commission:** Calculated via CostCalculator
- **Position Tracking:** Tracks open positions with SL/TP levels
- **Factory Function:** `create_position_with_stops()` for easy position creation
- **Comparison:** `compare_vs_optimistic()` shows impact of pessimistic execution
- **Production Rule:** Always use pessimistic execution for production backtesting

---

**File Reference:** `app/backtesting/execution_engine.py`
**Last Audited:** 2026-02-01
