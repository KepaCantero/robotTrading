# trade.py

## Purpose
Trade entity representing a completed trade - historical record of closed positions with entry/exit information, profit/loss calculations, and trade metadata.

---

## Type Definitions / Data Classes

### TradeStatus (Enum)
```python
class TradeStatus(str, Enum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PENDING = "pending"
```

### TradeType (Enum)
```python
class TradeType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
```

### ExitReason (Enum)
```python
class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    SIGNAL_REVERSAL = "signal_reversal"
    RISK_LIMIT = "risk_limit"
    TIME_EXIT = "time_exit"
    LIQUIDATION = "liquidation"
```

### Trade DataClass
```python
@dataclass
class Trade:
    # Identity
    trade_id: str                          # REQUIRED - Unique identifier
    symbol: str                            # REQUIRED - Trading symbol

    # Trade details
    side: PositionSide                     # REQUIRED - LONG or SHORT
    quantity: Decimal                      # REQUIRED - Trade quantity
    entry_price: Decimal                   # REQUIRED - Entry price
    exit_price: Decimal                    # REQUIRED - Exit price
    currency: str = "USD"                  # REQUIRED - Currency code

    # Timestamps
    entry_date: datetime = ...             # REQUIRED - Entry timestamp
    exit_date: Optional[datetime] = None   # OPTIONAL - Exit timestamp

    # Execution details
    trade_type: TradeType = MARKET         # REQUIRED - Trade type
    status: TradeStatus = FILLED           # REQUIRED - Trade status
    exit_reason: Optional[ExitReason] = None # OPTIONAL - Exit reason

    # Costs
    commission_paid: Decimal = 0           # REQUIRED - Commission
    slippage_cost: Decimal = 0             # REQUIRED - Slippage

    # Risk management
    stop_loss: Optional[Decimal] = None    # OPTIONAL - Stop loss price
    take_profit: Optional[Decimal] = None  # OPTIONAL - Take profit price

    # Metadata
    strategy_name: Optional[str] = None    # OPTIONAL - Strategy name
    notes: Optional[str] = None            # OPTIONAL - Trade notes
    tags: list[str] = []                   # REQUIRED - Trade tags
```

**Validation Rules (__post_init__):**
- trade_id cannot be empty
- symbol cannot be empty
- quantity must be positive
- entry_price cannot be negative
- exit_price cannot be negative

---

## Function Signatures (Contracts)

### P&L Calculation Methods

### `get_gross_pnl(self) -> Money`
**Pre:** None
**Post:** Returns gross profit/loss (before costs)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:**
- LONG: (exit_price - entry_price) * quantity
- SHORT: (entry_price - exit_price) * quantity
- Returns 0 if exit_price is 0

### `get_net_pnl(self) -> Money`
**Pre:** None
**Post:** Returns net profit/loss (after costs)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** gross_pnl - (commission_paid + slippage_cost)

### `get_pnl_percent(self) -> Decimal`
**Pre:** None
**Post:** Returns P&L as percentage of entry value
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (net_pnl / (quantity * entry_price)) * 100

### `get_total_cost(self) -> Money`
**Pre:** None
**Post:** Returns total cost (commission + slippage)
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Trade Metrics Methods

### `get_holding_period_days(self) -> int`
**Pre:** None
**Post:** Returns holding period in days
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** exit_date - entry_date (or now if no exit_date)

### `get_holding_period_hours(self) -> float`
**Pre:** None
**Post:** Returns holding period in hours
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (exit_date - entry_date).total_seconds() / 3600

### `get_risk_reward_ratio(self) -> Optional[Decimal]`
**Pre:** stop_loss and take_profit set
**Post:** Returns risk/reward ratio
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** reward / risk
- reward: abs(take_profit - entry_price)
- risk: abs(entry_price - stop_loss)
- Returns None if either is not set or risk is 0

### `get_actual_r_reward(self) -> Optional[Decimal]`
**Pre:** stop_loss set
**Post:** Returns actual risk/reward ratio based on P&L
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** reward_amount / risk_amount
- risk_amount: abs(entry_price - stop_loss) * quantity
- reward_amount: net_pnl
- Returns None if stop_loss not set or risk is 0

---

## Trade Status Methods

### `is_open(self) -> bool`
**Pre:** None
**Post:** Returns True if trade is still open
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:** Returns True if exit_date is None or exit_price is 0

### `is_closed(self) -> bool`
**Pre:** None
**Post:** Returns True if trade is closed
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:** Returns not is_open()

### `is_long(self) -> bool`
**Pre:** None
**Post:** Returns True if this is a long trade
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_short(self) -> bool`
**Pre:** None
**Post:** Returns True if this is a short trade
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_profitable(self) -> bool`
**Pre:** None
**Post:** Returns True if trade was profitable
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:** Returns net_pnl > 0

### `is_winner(self) -> bool`
**Pre:** None
**Post:** Returns True if trade was a winner
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Synonym for is_profitable()

### `is_loser(self) -> bool`
**Pre:** None
**Post:** Returns True if trade was a loser
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:** Returns net_pnl < 0

### `is_break_even(self) -> bool`
**Pre:** None
**Post:** Returns True if trade broke even
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:** Returns abs(net_pnl) < 0.01

---

## Factory Methods

### `from_position(cls, trade_id, position_quantity, entry_price, exit_price, symbol, side, entry_date, exit_date, exit_reason=None, commission=0, strategy_name=None) -> Trade`
**Pre:** All required parameters provided
**Post:** Returns Trade from closed position
**Raises:** No
**Retry:** No
**Side Effects:** None

### `create_long(cls, trade_id, symbol, quantity, entry_price, exit_price, entry_date=None, exit_date=None, stop_loss=None, take_profit=None, commission=0, strategy_name=None) -> Trade`
**Pre:** trade_id and symbol not empty, quantity and prices > 0
**Post:** Returns long trade
**Raises:** No
**Retry:** No
**Side Effects:** None

### `create_short(cls, trade_id, symbol, quantity, entry_price, exit_price, entry_date=None, exit_date=None, stop_loss=None, take_profit=None, commission=0, strategy_name=None) -> Trade`
**Pre:** trade_id and symbol not empty, quantity and prices > 0
**Post:** Returns short trade
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Serialization

### `to_dict(self) -> dict`
**Pre:** None
**Post:** Returns dictionary representation
**Raises:** No
**Retry:** No
**Side Effects:** None

### `__str__(self) -> str`
**Pre:** None
**Post:** Returns human-readable string
**Raises:** No
**Retry:** No
**Side Effects:** None

### `__repr__(self) -> str`
**Pre:** None
**Post:** Returns developer representation
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] trade_id cannot be empty
- [ ] symbol cannot be empty
- [ ] quantity must be positive
- [ ] Prices cannot be negative
- [ ] Gross P&L calculated correctly for LONG
- [ ] Gross P&L calculated correctly for SHORT
- [ ] Net P&L includes costs (commission + slippage)
- [ ] P&L percent calculated from entry value
- [ ] Holding periods calculated correctly
- [ ] Risk/reward ratio calculated from stop/take profit
- [ ] Actual R/R calculated from actual P&L
- [ ] Exit reason tracked
- [ ] Strategy name tracked
- [ ] Tags supported for categorization
- [ ] Factory methods create valid trades
- [ ] Serialization includes all calculated fields

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Decimal Precision | CRITICAL_RULES.md | Use Decimal for money | ✅ OK |
| Value Objects | BASE_RULES.md | Use Money for returns | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Immutability | BASE_RULES.md | Return new Money objects | ✅ OK |
| Error Handling | BASE_RULES.md | Specific exceptions | ✅ OK |
| Historical Record | BASE_RULES.md | Trade is immutable | ⚠️ NOT APPLIED - dataclass |
| Domain Layer Purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK |
| Type Hints Coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK |
| Transaction Costs | TRD-006 | Include costs in backtesting | ✅ OK - commission + slippage |
| Audit Trail | TRD-004 | Log all trade decisions | ⚠️ GAP - No audit logging in entity |
| Price Validation | TRD-005 | Validate price inputs | ⚠️ PARTIAL - No zero price check |
| Exit Reason Tracking | Trading standard | Record why trade exited | ✅ OK - ExitReason enum |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** dataclasses, datetime, decimal, enum, typing
- **Internal:**
  - app.domain.entities.position.PositionSide
  - app.domain.value_objects.money.Money

---

## Required Tests
- **test_trade.py:**
  - Test Trade.__post_init__ validation
  - Test Trade.__post_init__ with empty trade_id
  - Test Trade.__post_init__ with negative quantity
  - Test Trade.__post_init__ with negative prices
  - Test get_gross_pnl() for LONG
  - Test get_gross_pnl() for SHORT
  - Test get_gross_pnl() returns 0 if no exit
  - Test get_net_pnl() subtracts costs
  - Test get_pnl_percent() calculation
  - Test get_pnl_percent() returns 0 if no entry value
  - Test get_total_cost() returns commission + slippage
  - Test get_holding_period_days() with exit_date
  - Test get_holding_period_days() without exit_date
  - Test get_holding_period_hours() calculation
  - Test get_risk_reward_ratio() returns None if stop not set
  - Test get_risk_reward_ratio() returns None if take_profit not set
  - Test get_risk_reward_ratio() returns None if risk is 0
  - Test get_risk_reward_ratio() calculation
  - Test get_actual_r_reward() returns None if stop_loss not set
  - Test get_actual_r_reward() returns None if risk is 0
  - Test get_actual_r_reward() calculation
  - Test is_open() returns True when no exit
  - Test is_closed() returns True when exit exists
  - Test is_long() returns True for LONG
  - Test is_short() returns True for SHORT
  - Test is_profitable() returns True when net_pnl > 0
  - Test is_winner() synonym for is_profitable
  - Test is_loser() returns True when net_pnl < 0
  - Test is_break_even() returns True when |net_pnl| < 0.01
  - Test from_position() factory method
  - Test create_long() factory method
  - Test create_short() factory method
  - Test to_dict() serialization
  - Test __str__() representation
  - Test __repr__() developer representation
  - Test ExitReason enum values
  - Test TradeType enum values
  - Test TradeStatus enum values

---

## Notes
- CRITICAL: This is a core domain entity
- Trade represents historical record (closed positions)
- Position represents current holdings (open)
- All financial calculations use Decimal
- Returns Money value objects (immutable)
- Comprehensive exit reason tracking (7 reasons)
- Support for strategy attribution
- Tags for categorization and analysis
- GAP: Should validate exit_price > 0 (TRD-005)
- GAP: No audit logging in entity (TRD-004) - should be in application layer
