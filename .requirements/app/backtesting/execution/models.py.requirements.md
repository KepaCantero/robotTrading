# models.py (Execution Module)

## Purpose
Data models for the execution system including Order, MarketSnapshot, FillResult, ExecutionResult, and related enums with comprehensive validation.

---

## Type Definitions / Data Classes

### OrderSide Enum
```python
class OrderSide(str, Enum):
    BUY = "buy"        # REQUIRED - Buy order
    SELL = "sell"      # REQUIRED - Sell order
```

### OrderType Enum
```python
class OrderType(str, Enum):
    MARKET = "market"              # REQUIRED - Market order
    LIMIT = "limit"                # REQUIRED - Limit order
    STOP = "stop"                  # REQUIRED - Stop order
    STOP_LIMIT = "stop_limit"      # REQUIRED - Stop-limit order
```

### OrderStatus Enum
```python
class OrderStatus(str, Enum):
    PENDING = "pending"                    # REQUIRED - Order pending
    SUBMITTED = "submitted"                # REQUIRED - Order submitted
    PARTIALLY_FILLED = "partially_filled"  # REQUIRED - Partially filled
    FILLED = "filled"                      # REQUIRED - Fully filled
    CANCELLED = "cancelled"                # REQUIRED - Cancelled
    REJECTED = "rejected"                  # REQUIRED - Rejected
    EXPIRED = "expired"                    # REQUIRED - Expired
```

### TimeOfDay Enum
```python
class TimeOfDay(str, Enum):
    PRE_MARKET = "pre_market"      # REQUIRED - Before 9:30 AM ET
    OPEN = "open"                  # REQUIRED - 9:30-10:00 AM ET
    MORNING = "morning"            # REQUIRED - 10:00 AM - 12:00 PM ET
    LUNCH = "lunch"                # REQUIRED - 12:00 PM - 1:00 PM ET
    AFTERNOON = "afternoon"        # REQUIRED - 1:00 PM - 3:30 PM ET
    CLOSE = "close"                # REQUIRED - 3:30-4:00 PM ET
    AFTER_HOURS = "after_hours"    # REQUIRED - After 4:00 PM ET
```

### FillReason Enum
```python
class FillReason(str, Enum):
    FULL_FILL = "full_fill"                      # REQUIRED - Order filled completely
    PARTIAL_FILL = "partial_fill"                # REQUIRED - Order partially filled
    MULTIPLE_FILL = "multiple_fill"              # REQUIRED - Filled in multiple portions
    IMMEDIATE_FILL = "immediate_fill"            # REQUIRED - Market order filled immediately
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"  # REQUIRED - Not enough volume
    PRICE_LIMIT = "price_limit"                  # REQUIRED - Price moved outside limit
    MARKET_CLOSED = "market_closed"              # REQUIRED - Market not open
    CAPITAL_LIMIT = "capital_limit"              # REQUIRED - Insufficient capital
    POSITION_LIMIT = "position_limit"            # REQUIRED - Position size limit
    RISK_LIMIT = "risk_limit"                    # REQUIRED - Risk management limit
    EXCEEDS_ADV = "exceeds_adv"                  # REQUIRED - Order too large for ADV
```

### MarketSnapshot Class
```python
@dataclass
class MarketSnapshot:
    timestamp: datetime                              # REQUIRED - Snapshot time
    symbol: str                                      # REQUIRED - Trading symbol

    # Price data
    bid: Decimal                                     # REQUIRED - Bid price (gt 0)
    ask: Decimal                                     # REQUIRED - Ask price (gt 0, gt bid)
    last_price: Decimal                              # REQUIRED - Last price (gt 0)
    open_price: Optional[Decimal] = None             # OPTIONAL - Open price (gt 0)
    high_price: Optional[Decimal] = None             # OPTIONAL - High price (gt 0)
    low_price: Optional[Decimal] = None              # OPTIONAL - Low price (gt 0)
    close_price: Optional[Decimal] = None            # OPTIONAL - Close price (gt 0)

    # Volume data
    bid_size: int = 0                                # OPTIONAL - Bid size (gte 0)
    ask_size: int = 0                                # OPTIONAL - Ask size (gte 0)
    volume: int = 0                                  # OPTIONAL - Volume (gte 0)
    average_daily_volume: Decimal = Decimal("0")     # OPTIONAL - ADV (gte 0)

    # Volatility data
    implied_volatility: Optional[Decimal] = None     # OPTIONAL - Implied vol (gte 0)
    historical_volatility_20d: Optional[Decimal] = None # OPTIONAL - 20-day hist vol (gte 0)
    vix: Optional[Decimal] = None                    # OPTIONAL - VIX index (gte 0)

    # Market conditions
    is_market_open: bool = True                      # OPTIONAL - Market open flag
    is_trading_halt: bool = False                    # OPTIONAL - Trading halt flag
    is_short_sale_restricted: bool = False           # OPTIONAL - Short sale restriction
```

**Validation Rules:**
- `ask` must be > `bid`
- All prices must be positive if set
- All volumes/sizes must be non-negative

### Order Class
```python
@dataclass
class Order:
    order_id: str                                    # REQUIRED - Unique order ID
    symbol: str                                      # REQUIRED - Trading symbol
    side: OrderSide                                  # REQUIRED - Buy/sell
    order_type: OrderType                            # REQUIRED - Order type
    quantity: int                                    # REQUIRED - Number of shares (gt 0)

    # Price fields
    limit_price: Optional[Decimal] = None            # OPTIONAL - Limit price (gt 0 if set)
    stop_price: Optional[Decimal] = None             # OPTIONAL - Stop price (gt 0 if set)

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow) # OPTIONAL - Creation time
    submitted_at: Optional[datetime] = None          # OPTIONAL - Submission time
    expires_at: Optional[datetime] = None            # OPTIONAL - Expiration time

    # Constraints
    max_slippage_bps: Optional[Decimal] = None       # OPTIONAL - Max slippage (gte 0 if set)
    min_fill_quantity: int = 0                       # OPTIONAL - Min fill (gte 0)
    adv_limit_pct: Decimal = Decimal("0.1")          # OPTIONAL - Max % ADV (gt 0, lte 1)

    # Status tracking
    status: OrderStatus = OrderStatus.PENDING        # OPTIONAL - Order status
    filled_quantity: int = 0                         # OPTIONAL - Filled shares (gte 0)
    avg_fill_price: Decimal = Decimal("0")           # OPTIONAL - Avg fill price (gte 0)

    # Metadata
    strategy_name: str = ""                          # OPTIONAL - Strategy name
    reason: str = ""                                 # OPTIONAL - Order reason
```

**Validation Rules:**
- `quantity` must be positive
- `limit_price` required for LIMIT and STOP_LIMIT orders
- `stop_price` required for STOP and STOP_LIMIT orders
- `max_slippage_bps` must be non-negative if set
- `adv_limit_pct` must be between 0 and 1
- `filled_quantity` must be <= `quantity`

### FillResult Class
```python
@dataclass
class FillResult:
    order_id: str                                    # REQUIRED - Order ID
    symbol: str                                      # REQUIRED - Symbol
    side: OrderSide                                  # REQUIRED - Side

    # Fill details
    filled: bool                                     # REQUIRED - Whether filled
    filled_shares: int                               # REQUIRED - Shares filled (gte 0)
    fill_price: Decimal                              # REQUIRED - Fill price (gte 0)
    fill_time: Optional[datetime] = None             # OPTIONAL - Fill time

    # Cost breakdown
    commission: Decimal                              # REQUIRED - Commission (gte 0)
    slippage_bps: Decimal                            # REQUIRED - Slippage in bps (gte 0)
    market_impact_bps: Decimal                       # REQUIRED - Market impact in bps (gte 0)
    total_cost: Decimal                              # REQUIRED - Total cost (gte 0)

    # Fill reason
    fill_reason: FillReason                          # REQUIRED - Reason for fill/rejection

    # Additional context
    bid_at_fill: Optional[Decimal] = None            # OPTIONAL - Bid at fill
    ask_at_fill: Optional[Decimal] = None            # OPTIONAL - Ask at fill
    spread_at_fill_bps: Optional[Decimal] = None      # OPTIONAL - Spread at fill
    adv_at_fill: Decimal = Decimal("0")              # OPTIONAL - ADV at fill
    volatility_at_fill: Optional[Decimal] = None      # OPTIONAL - Volatility at fill

    # Partial fill info
    is_partial_fill: bool = False                    # OPTIONAL - Is partial fill
    remaining_shares: int = 0                        # OPTIONAL - Remaining shares (gte 0)
    estimated_remaining_cost: Decimal = Decimal("0") # OPTIONAL - Est remaining cost

    # Metadata
    execution_time_ms: int = 0                       # OPTIONAL - Execution time ms (gte 0)
    warnings: List[str] = field(default_factory=list) # OPTIONAL - Warning messages
```

**Validation Rules:**
- All cost fields must be non-negative
- `filled_shares` must be non-negative
- If `filled` is True, `fill_price` must be positive
- `remaining_shares` must be non-negative

---

## Function Signatures (Contracts)

### `MarketSnapshot.get_time_of_day() -> TimeOfDay`
**Pre:** timestamp is set
**Post:** Returns TimeOfDay based on timestamp
**Raises:** None
**Retry:** No
**Side Effects:** None

### `Order.validate() -> bool`
**Pre:** All fields set
**Post:** Returns True if valid
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `Order.remaining_quantity (property) -> int`
**Pre:** None
**Post:** Returns quantity - filled_quantity
**Raises:** None
**Retry:** No
**Side Effects:** None

### `Order.is_fully_filled (property) -> bool`
**Pre:** None
**Post:** Returns True if filled_quantity >= quantity
**Raises:** None
**Retry:** No
**Side Effects:** None

### `Order.is_active (property) -> bool`
**Pre:** None
**Post:** Returns True if status in PENDING/SUBMITTED/PARTIALLY_FILLED
**Raises:** None
**Retry:** No
**Side Effects:** None

### `FillResult.fill_value (property) -> Decimal`
**Pre:** None
**Post:** Returns filled_shares * fill_price
**Raises:** None
**Retry:** No
**Side Effects:** None

### `FillResult.effective_cost_bps (property) -> Decimal`
**Pre:** None
**Post:** Returns (total_cost / fill_value) * 10000
**Raises:** None
**Retry:** No
**Side Effects:** None

### `FillResult.net_profit_loss (property) -> Decimal`
**Pre:** None
**Post:** Returns fill_value - total_cost (SELL) or -total_cost (BUY)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All enums have valid string values
- [ ] MarketSnapshot validates ask > bid
- [ ] Order validation enforces limit/stop price requirements
- [ ] Order validation enforces quantity > 0
- [ ] Order remaining_quantity is correctly calculated
- [ ] FillResult properties calculate correctly
- [ ] All type hints are present and accurate
- [ ] Pydantic fallback works when pydantic not installed

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError in validate() |
| EXE-001 | BASE_RULES | Order validation | ✅ OK - validate() method |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - No logging |
| ARCH-006 | BASE_RULES | Value objects immutable | ❌ GAP - dataclass not frozen |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - field_default_factory used |

---

## Dependencies
- **External:** datetime, decimal, enum, typing
- **Internal:** None
- **Optional:** pydantic (with fallback to dataclasses)

---

## Required Tests
- **tests/unit/backtesting/execution/test_models.py:**
  - Test OrderSide enum values
  - Test OrderType enum values
  - Test OrderStatus enum values
  - Test TimeOfDay enum values
  - Test FillReason enum values
  - Test MarketSnapshot creation with valid data
  - Test MarketSnapshot ask > bid validation
  - Test MarketSnapshot get_time_of_day() method
  - Test MarketSnapshot spread calculation
  - Test MarketSnapshot spread_bps calculation
  - Test MarketSnapshot mid_price calculation
  - Test Order creation with valid data
  - Test Order validation enforces quantity > 0
  - Test Order validation requires limit_price for LIMIT orders
  - Test Order validation requires stop_price for STOP orders
  - Test Order remaining_quantity property
  - Test Order is_fully_filled property
  - Test Order is_active property
  - Test FillResult creation with valid data
  - Test FillResult fill_value property
  - Test FillResult effective_cost_bps property
  - Test FillResult net_profit_loss property for BUY
  - Test FillResult net_profit_loss property for SELL
  - Test Pydantic fallback when pydantic not installed

---

## Notes
- Execution models support both pydantic and dataclass fallback
- MarketSnapshot provides comprehensive market data for execution decisions
- Order includes validation for limit/stop price requirements
- FillResult provides detailed cost breakdown and context
- TimeOfDay categorization for time-based slippage adjustments
