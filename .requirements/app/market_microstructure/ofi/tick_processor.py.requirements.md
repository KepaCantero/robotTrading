# tick_processor.py

## Purpose
Process tick-level trade data for real-time OFI calculation, distinguishing aggressive market orders from passive limit orders.

---

## Type Definitions / Data Classes

### TickOFIResult (dataclass)
```python
@dataclass
class TickOFIResult:
    timestamp: datetime               # REQUIRED - Tick timestamp
    ofi: float                        # REQUIRED - Current rolling OFI
    tick_ofi: float                   # REQUIRED - This tick's OFI contribution
    market_buy_volume: int            # REQUIRED - Total market buy volume
    market_sell_volume: int           # REQUIRED - Total market sell volume
    aggressive_ratio: float           # REQUIRED - Aggressive / total volume ratio
    order_book_depth: int             # REQUIRED - Total depth at top 5 levels
```

### OrderBookLevel (dataclass)
```python
@dataclass
class OrderBookLevel:
    price: Decimal                    # REQUIRED - Price level
    quantity: int                     # REQUIRED - Available quantity
    orders_count: int = 1             # Default: 1 - Number of orders at level
```

### OrderBookState (dataclass)
```python
@dataclass
class OrderBookState:
    symbol: str                       # REQUIRED - Trading symbol
    timestamp: datetime               # REQUIRED - Last update time
    bids: Dict[Decimal, int]         # Price -> quantity mapping
    asks: Dict[Decimal, int]         # Price -> quantity mapping
    last_update: str = "init"         # Default: "init"
```

**Methods:**
- `update_bid(price: Decimal, quantity: int) -> None` - Updates or removes bid level
- `update_ask(price: Decimal, quantity: int) -> None` - Updates or removes ask level
- `get_best_bid() -> Optional[Tuple[Decimal, int]]` - Returns highest bid
- `get_best_ask() -> Optional[Tuple[Decimal, int]]` - Returns lowest ask
- `to_snapshot() -> OrderBookSnapshot` - Converts to OrderBookSnapshot
- `get_depth(levels: int = 5) -> Tuple[int, int]` - Returns (bid_depth, ask_depth)

### TickLevelOFIProcessor Class
```python
class TickLevelOFIProcessor:
    window_size: int                   # Rolling window size for OFI calculation
    calculator: OFICalculator          # OFI calculator instance
    tick_buffer: Deque[TickData]       # Rolling tick buffer (maxlen=window_size)
    order_book: Optional[OrderBookState] # Current order book state
    market_buy_volume: int             # Accumulated market buy volume
    market_sell_volume: int            # Accumulated market sell volume
    total_aggressive_volume: int       # Sum of aggressive trades
    current_ofi: float                 # Current rolling OFI value
    ofi_history: Deque[float]          # OFI history (maxlen=window_size)
```

---

## Function Signatures (Contracts)

### `__init__(window_size: int = 100, calculator: Optional[OFICalculator] = None) -> None`
**Pre:** window_size >= 1
**Post:** Processor initialized with empty buffers
**Raises:** None
**Retry:** No
**Side Effects:** Creates OFICalculator if None provided

### `process_tick(tick: TickData) -> TickOFIResult`
**Pre:** tick has symbol, timestamp, price, quantity, side
**Post:** Returns TickOFIResult with updated OFI and volumes
**Raises:** None (handles all error cases)
**Retry:** No
**Side Effects:** Updates tick_buffer, order_book state, OFI history

### `_process_market_buy(tick: TickData) -> float`
**Pre:** tick.is_market_buy == True
**Post:** Returns OFI contribution (+quantity/total_volume)
**Raises:** None
**Retry:** No
**Side Effects:** Increments market_buy_volume, removes liquidity from asks

### `_process_market_sell(tick: TickData) -> float`
**Pre:** tick.is_market_sell == True
**Post:** Returns OFI contribution (-quantity/total_volume)
**Raises:** None
**Retry:** No
**Side Effects:** Increments market_sell_volume, removes liquidity from bids

### `_process_limit_order(tick: TickData) -> float`
**Pre:** tick is not aggressive (limit order)
**Post:** Returns OFI from updated order book or 0.0
**Raises:** None
**Retry:** No
**Side Effects:** Updates order_book state

### `calculate_tick_ofi(ticks: List[TickData]) -> float`
**Pre:** ticks is list of TickData
**Post:** Returns OFI = (market_buys - market_sells) / total_volume
**Raises:** None (returns 0.0 if empty or zero total)
**Retry:** No
**Side Effects:** None

### `get_aggressive_flow_ratio(window: int = 50) -> float`
**Pre:** tick_buffer has data
**Post:** Returns market_buy_vol / market_sell_vol ratio
**Raises:** None (returns 1.0 if insufficient data or zero sell vol)
**Retry:** No
**Side Effects:** None

### `detect_aggressive_surge(threshold: float = 2.0, window: int = 20) -> Optional[str]`
**Pre:** tick_buffer length >= window * 2
**Post:** Returns "buy_surge", "sell_surge", or None
**Raises:** None (returns None if insufficient data)
**Retry:** No
**Side Effects:** None

### `reset() -> None`
**Pre:** None
**Post:** All buffers cleared, volumes reset to 0
**Raises:** None
**Retry:** No
**Side Effects:** Clears all state

---

## Acceptance Criteria
- [ ] Market buy orders add +quantity/total_volume to OFI
- [ ] Market sell orders add -quantity/total_volume to OFI
- [ ] Limit orders update order book and recalculate OFI
- [ ] Rolling OFI uses exponential weighted moving average
- [ ] Aggressive ratio = aggressive_volume / total_volume
- [ ] Surge detection compares recent vs previous window volume
- [ ] Order book updates handle quantity=0 as removal
- [ ] Statistics include mean and std of OFI history

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - Tick validation implicit |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Imports from models and calculator |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ NOT APPLIED - No exception logging |
| SEC-007 | BASE_RULES | Input validation | ⚠️ NOT APPLIED - Assumes valid TickData |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Uses try/except with returns |

---

## Dependencies
- **External:** numpy (np), collections (deque), datetime, decimal (Decimal), dataclasses, typing
- **Internal:** app.market_microstructure.ofi.models (CumulativeOFI, OrderBookSnapshot, OrderSide, TickData), app.market_microstructure.ofi.ofi_calculator (OFICalculator, OFIResult)

---

## Required Tests
- **tests/market_microstructure/ofi/test_tick_processor.py:**
  - Test market buy processing (OFI contribution positive)
  - Test market sell processing (OFI contribution negative)
  - Test limit order processing (order book update)
  - Test rolling OFI calculation with window
  - Test aggressive flow ratio calculation
  - Test aggressive surge detection (buy/sell/none)
  - Test order book state updates (add/remove levels)
  - Test to_snapshot conversion
  - Test get_depth calculation
  - Test reset() clears all state
  - Test edge cases: empty buffer, zero volume

---

## Notes
Distinguishes aggressive (market) orders from passive (limit) orders. Market orders remove liquidity, limit orders add liquidity. Uses Hasbrouck (1991) methodology for trade classification.
