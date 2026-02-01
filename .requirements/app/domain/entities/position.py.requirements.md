# position.py

## Purpose
Position entity representing a holding in a portfolio - tracks entry/exit prices, quantities, P&L calculations, and risk metrics with support for both long and short positions.

---

## Type Definitions / Data Classes

### PositionSide (Enum)
```python
class PositionSide(str, Enum):
    LONG = "long"          # Long position (benefit from price increase)
    SHORT = "short"        # Short position (benefit from price decrease)
```

### PositionStatus (Enum)
```python
class PositionStatus(str, Enum):
    OPEN = "open"          # Position is currently open
    CLOSED = "closed"      # Position has been closed
    PENDING = "pending"    # Position is pending execution
```

### Position DataClass
```python
@dataclass
class Position:
    # Identity
    symbol: str                          # REQUIRED - Trading symbol
    entry_date: datetime = ...           # REQUIRED - Entry timestamp

    # Position details
    side: PositionSide = LONG            # REQUIRED - LONG or SHORT
    quantity: Decimal = 0                # REQUIRED - Number of shares/contracts
    avg_entry_price: Decimal = 0         # REQUIRED - Average entry price
    current_price: Decimal = 0           # REQUIRED - Current market price
    currency: str = "USD"                # REQUIRED - Currency code

    # Tracking
    status: PositionStatus = OPEN        # REQUIRED - Current status
    exit_date: Optional[datetime] = None # OPTIONAL - Exit timestamp
    avg_exit_price: Decimal = 0          # REQUIRED - Average exit price (when closed)

    # Risk metrics
    stop_loss: Optional[Decimal] = None  # OPTIONAL - Stop loss price
    take_profit: Optional[Decimal] = None # OPTIONAL - Take profit price
    max_price: Decimal = 0               # REQUIRED - Highest price since entry
    min_price: Decimal = 0               # REQUIRED - Lowest price since entry

    # Metadata
    created_at: datetime = ...           # REQUIRED - Creation timestamp
    updated_at: datetime = ...           # REQUIRED - Last update timestamp
```

**Validation Rules (_validate):**
- symbol cannot be empty
- quantity cannot be negative
- avg_entry_price cannot be negative
- current_price cannot be negative or zero

**Special Handling:**
- avg_price is alias for avg_entry_price (backward compatibility)
- Custom __init__ for max_price/min_price initialization
- Direct __dict__ setting to bypass dataclass __init__

---

## Function Signatures (Contracts)

### Initialization

### `__init__(self, symbol, entry_date=None, side=LONG, quantity=0, avg_entry_price=0, avg_price=None, current_price=0, currency="USD", status=OPEN, exit_date=None, avg_exit_price=0, stop_loss=None, take_profit=None, max_price=0, min_price=0, created_at=None, updated_at=None) -> None`
**Pre:** symbol not empty
**Post:** Position initialized with validation
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** Calls _validate()

**Special Logic:**
- avg_price alias mapped to avg_entry_price
- max_price defaults to current_price if 0
- min_price defaults to current_price if 0
- Timestamps default to now if None

### `_validate(self) -> None`
**Pre:** None
**Post:** Validation passes or ValueError raised
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** None

**Validations:**
- symbol not empty
- quantity >= 0
- avg_entry_price >= 0
- current_price > 0

### Properties

### `avg_price (property) -> Decimal`
**Pre:** None
**Post:** Returns avg_entry_price
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Alias for backward compatibility

### Position Value Methods

### `get_value(self) -> Money`
**Pre:** None
**Post:** Returns current position value
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** quantity * current_price

### `get_cost_basis(self) -> Money`
**Pre:** None
**Post:** Returns total cost basis
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** quantity * avg_entry_price

### P&L Calculation Methods

### `get_unrealized_pnl_amount(self) -> Decimal`
**Pre:** None
**Post:** Returns unrealized P&L (signed, can be negative)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:**
- LONG: (current_price - avg_entry_price) * quantity
- SHORT: (avg_entry_price - current_price) * quantity
- CLOSED: Returns 0

### `get_unrealized_pnl(self) -> Money`
**Pre:** None
**Post:** Returns unrealized P&L (absolute value)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Uses abs() because Money cannot be negative

### `get_realized_pnl_amount(self) -> Decimal`
**Pre:** None
**Post:** Returns realized P&L (signed, can be negative)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:**
- LONG: (avg_exit_price - avg_entry_price) * quantity
- SHORT: (avg_entry_price - avg_exit_price) * quantity
- Not CLOSED or no exit_price: Returns 0

### `get_realized_pnl(self) -> Money`
**Pre:** None
**Post:** Returns realized P&L (absolute value)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Uses abs() because Money cannot be negative

### `get_pnl_percent(self) -> Decimal`
**Pre:** None
**Post:** Returns P&L as percentage of cost basis
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (pnl_amount / cost_basis) * 100
- Uses unrealized if OPEN
- Uses realized if CLOSED

### Backward Compatibility Methods

### `get_pnl(self) -> Decimal`
**Pre:** None
**Post:** Returns unrealized P&L amount
**Raises:** No
**Retry:** No
**Side Effects:** None

**Note:** Backward compatibility alias

### `get_quantity(self) -> Decimal`
**Pre:** None
**Post:** Returns quantity
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_current_price(self) -> Decimal`
**Pre:** None
**Post:** Returns current_price
**Raises:** No
**Retry:** No
**Side Effects:** None

### Position Management Methods

### `update_price(self, new_price: Decimal) -> None`
**Pre:** new_price > 0
**Post:** current_price updated, max/min updated
**Raises:** ValueError if new_price invalid
**Retry:** No
**Side Effects:** Updates current_price, max_price, min_price, updated_at

### `add_shares(self, quantity: Decimal, price: Decimal) -> None`
**Pre:** quantity > 0, price > 0
**Post:** Position increased with new shares
**Raises:** No
**Retry:** No
**Side Effects:** Recalculates avg_entry_price, updates quantity

**Calculation:** Weighted average of existing + new shares

### `remove_shares(self, quantity: Decimal, price: Decimal) -> None`
**Pre:** quantity > 0, price > 0
**Post:** Position decreased
**Raises:** ValueError if quantity exceeds current position
**Retry:** No
**Side Effects:** Updates quantity, updates avg_exit_price, may set status to CLOSED

### Risk Management Methods

### `is_stop_loss_hit(self) -> bool`
**Pre:** None
**Post:** Returns True if stop loss triggered
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:**
- LONG: current_price <= stop_loss
- SHORT: current_price >= stop_loss
- Returns False if stop_loss is None

### `is_take_profit_hit(self) -> bool`
**Pre:** None
**Post:** Returns True if take profit triggered
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:**
- LONG: current_price >= take_profit
- SHORT: current_price <= take_profit
- Returns False if take_profit is None

### `get_risk_reward_ratio(self) -> Optional[Decimal]`
**Pre:** stop_loss and take_profit are set
**Post:** Returns risk/reward ratio or None
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** reward / risk
- reward: abs(take_profit - avg_entry_price)
- risk: abs(avg_entry_price - stop_loss)
- Returns None if either is not set or risk is 0

### Position Info Methods

### `get_age_days(self) -> int`
**Pre:** None
**Post:** Returns age in days
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (exit_date or now) - entry_date

### `is_open(self) -> bool`
**Pre:** None
**Post:** Returns True if status is OPEN
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_closed(self) -> bool`
**Pre:** None
**Post:** Returns True if status is CLOSED
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_profitable(self) -> bool`
**Pre:** None
**Post:** Returns True if position is profitable
**Raises:** No
**Retry:** No
**Side Effects:** None

**Logic:**
- CLOSED: Checks realized_pnl > 0
- OPEN: Checks unrealized_pnl > 0

### Factory Methods

### `create_long(cls, symbol, quantity, entry_price, currency="USD", stop_loss=None, take_profit=None) -> Position`
**Pre:** symbol not empty, quantity > 0, entry_price > 0
**Post:** Returns new long position
**Raises:** No
**Retry:** No
**Side Effects:** None

### `create_short(cls, symbol, quantity, entry_price, currency="USD", stop_loss=None, take_profit=None) -> Position`
**Pre:** symbol not empty, quantity > 0, entry_price > 0
**Post:** Returns new short position
**Raises:** No
**Retry:** No
**Side Effects:** None

### Serialization

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

---

## Acceptance Criteria
- [ ] symbol cannot be empty
- [ ] quantity cannot be negative
- [ ] Prices cannot be negative or zero
- [ ] avg_price alias works for backward compatibility
- [ ] Unrealized P&L calculated correctly for LONG
- [ ] Unrealized P&L calculated correctly for SHORT
- [ ] Realized P&L calculated when CLOSED
- [ ] P&L percent calculated from cost basis
- [ ] max_price tracks highest price
- [ ] min_price tracks lowest price
- [ ] avg_entry_price recalculated on add_shares
- [ ] Cost basis returns Money
- [ ] Position value returns Money
- [ ] Stop loss triggers correctly for LONG
- [ ] Stop loss triggers correctly for SHORT
- [ ] Take profit triggers correctly for LONG
- [ ] Take profit triggers correctly for SHORT
- [ ] Risk/reward ratio calculated correctly
- [ ] Position age calculated correctly
- [ ] Factory methods create valid positions

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Decimal Precision | CRITICAL_RULES.md | Use Decimal for money | ✅ OK |
| Value Objects | BASE_RULES.md | Return Money objects | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Error Handling | BASE_RULES.md | Specific exceptions | ✅ OK |
| Backward Compatibility | BASE_RULES.md | avg_price alias | ✅ OK |
| Long/Short Logic | CRITICAL_RULES.md | Correct P&L calc | ✅ OK |
| Custom Init | BASE_RULES.md | Direct __dict__ setting | ✅ OK |
| Domain Layer Purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK |
| Type Hints Coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK |
| Immutable Value Objects | BASE_RULES.md (ARCH-006) | Money is immutable | ✅ OK |
| Stop Loss Validation | TRD-002 | Validate stop loss | ⚠️ GAP - No validation stop_loss < 0 for LONG |
| Take Profit Validation | TRD-002 | Validate take profit | ⚠️ GAP - No validation take_profit < 0 for LONG |
| Position Limits | TRD-003 | Enforce max position size | ⚠️ GAP - No max quantity check |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** dataclasses, datetime, decimal, enum, typing
- **Internal:**
  - app.domain.value_objects.money.Money

---

## Required Tests
- **test_position.py:**
  - Test Position._validate with valid data
  - Test Position._validate with empty symbol raises ValueError
  - Test Position._validate with negative quantity raises ValueError
  - Test Position._validate with negative prices raises ValueError
  - Test Position._validate with zero current_price raises ValueError
  - Test avg_price property returns avg_entry_price
  - Test get_value calculation
  - Test get_cost_basis calculation
  - Test get_unrealized_pnl_amount for LONG
  - Test get_unrealized_pnl_amount for SHORT
  - Test get_unrealized_pnl_amount for CLOSED returns 0
  - Test get_realized_pnl_amount for OPEN returns 0
  - Test get_realized_pnl_amount for CLOSED
  - Test get_pnl_percent calculation
  - Test get_pnl backward compatibility
  - Test get_quantity returns quantity
  - Test get_current_price returns current_price
  - Test is_open status check
  - Test is_closed status check
  - Test is_profitable for OPEN position
  - Test is_profitable for CLOSED position
  - Test add_shares recalculates avg_entry_price
  - Test remove_shares updates quantity
  - Test remove_shares sets status to CLOSED when quantity = 0
  - Test remove_shares raises ValueError if quantity exceeds position
  - Test update_price updates current_price and max/min
  - Test is_stop_loss_hit for LONG
  - Test is_stop_loss_hit for SHORT
  - Test is_stop_loss_hit returns False when stop_loss is None
  - Test is_take_profit_hit for LONG
  - Test is_take_profit_hit for SHORT
  - Test is_take_profit_hit returns False when take_profit is None
  - Test get_risk_reward_ratio returns ratio
  - Test get_risk_reward_ratio returns None when stop_loss not set
  - Test get_risk_reward_ratio returns None when take_profit not set
  - Test get_risk_reward_ratio returns None when risk is 0
  - Test get_age_days calculation
  - Test create_long factory method
  - Test create_short factory method
  - Test to_dict serialization
  - Test __str__ representation

---

## Notes
- CRITICAL: This is a core domain entity
- Represents current holdings (vs Trade for historical)
- Supports both LONG and SHORT positions
- P&L calculations differ for LONG vs SHORT
- Backward compatibility maintained (avg_price alias)
- Custom __init__ for max_price/min_price initialization
- Money value objects returned for financial values
- All calculations use Decimal for precision
- GAP: Should validate stop_loss/take_profit > 0 for LONG positions
- GAP: Should validate stop_loss/take_profit < entry_price for LONG (logical)
- GAP: No maximum position size enforcement (TRD-003)
