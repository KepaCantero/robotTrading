# position.py

## Purpose
Position Entity - Represents a single holding in a portfolio with entry/exit information, profit/loss calculations, and risk metrics.

---

## Type Definitions / Data Classes

### PositionSide (Enum)
```python
class PositionSide(str, Enum):
    LONG = "long"      # Long position (benefits from price increase)
    SHORT = "short"    # Short position (benefits from price decrease)
```

### PositionStatus (Enum)
```python
class PositionStatus(str, Enum):
    OPEN = "open"        # Position is currently open
    CLOSED = "closed"    # Position has been closed
    PENDING = "pending"  # Position is pending execution
```

### Position
```python
@dataclass
class Position:
    # Identity
    symbol: str                      # REQUIRED - Trading symbol
    entry_date: datetime             # Default: utcnow()

    # Position details
    side: PositionSide               # Default: LONG
    quantity: Decimal                # Default: 0
    avg_entry_price: Decimal         # Default: 0
    current_price: Decimal           # Default: 0
    currency: str                    # Default: "USD"

    # Tracking
    status: PositionStatus           # Default: OPEN
    exit_date: Optional[datetime]    # Default: None
    avg_exit_price: Decimal          # Default: 0

    # Risk metrics
    stop_loss: Optional[Decimal]     # Default: None
    take_profit: Optional[Decimal]   # Default: None
    max_price: Decimal               # Default: 0 (init to current_price)
    min_price: Decimal               # Default: 0 (init to current_price)

    # Metadata
    created_at: datetime             # Default: utcnow()
    updated_at: datetime             # Default: utcnow()
```

**Properties:**
- `avg_price` - Alias for avg_entry_price (backward compatibility)

**Invariants (enforced in _validate):**
- `symbol` must be non-empty
- `quantity` >= 0
- `avg_entry_price` >= 0
- `current_price` > 0

---

## Function Signatures (Contracts)

### `Position.__init__(...) -> None`
**Pre:** symbol non-empty; quantity >= 0; avg_entry_price >= 0; current_price > 0
**Post:** Position initialized and validated
**Raises:** `ValueError` if validation fails
**Retry:** No
**Side Effects:** Validates invariants via _validate()

### `_validate() -> None` (private)
**Pre:** None
**Post:** Position invariants verified
**Raises:** `ValueError` if symbol empty, quantity negative, or prices invalid
**Retry:** No
**Side Effects:** None (validation only)

### `get_value() -> Money`
**Pre:** None
**Post:** Returns Money with quantity × current_price
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_cost_basis() -> Money`
**Pre:** None
**Post:** Returns Money with quantity × avg_entry_price
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_unrealized_pnl_amount() -> Decimal`
**Pre:** None
**Post:** Returns signed P&L: (current - entry) × quantity for LONG, -(current - entry) × quantity for SHORT; 0 if CLOSED
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_unrealized_pnl() -> Money`
**Pre:** None
**Post:** Returns Money with abs(unrealized_pnl_amount)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_realized_pnl_amount() -> Decimal`
**Pre:** None
**Post:** Returns signed P&L: (exit - entry) × quantity for LONG, -(exit - entry) × quantity for SHORT; 0 if OPEN or exit_price = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_realized_pnl() -> Money`
**Pre:** None
**Post:** Returns Money with abs(realized_pnl_amount)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_pnl_percent() -> Decimal`
**Pre:** None
**Post:** Returns (pnl / cost_basis) × 100; uses realized if CLOSED else unrealized; 0 if cost = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_pnl() -> Decimal`
**Pre:** None
**Post:** Returns unrealized_pnl_amount (backward compatibility alias)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_quantity() -> Decimal`
**Pre:** None
**Post:** Returns quantity
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_current_price() -> Decimal`
**Pre:** None
**Post:** Returns current_price
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `update_price(new_price) -> None`
**Pre:** new_price > 0
**Post:** current_price updated; max_price/min_price updated; updated_at refreshed
**Raises:** `ValueError` if price <= 0
**Retry:** No
**Side Effects:** Updates state

### `add_shares(quantity, price) -> None`
**Pre:** quantity >= 0; price >= 0
**Post:** Shares added, avg_entry_price recalculated: (old_cost + new_cost) / total_quantity
**Raises:** `ValueError` if quantity or price negative
**Retry:** No
**Side Effects:** Updates quantity, avg_entry_price, updated_at

### `remove_shares(quantity, price) -> None`
**Pre:** quantity >= 0; quantity <= current quantity
**Post:** Shares removed; if quantity reaches 0, status = CLOSED, exit_date set
**Raises:** `ValueError` if quantity negative or exceeds holdings
**Retry:** No
**Side Effects:** Updates quantity, avg_exit_price, status, exit_date, updated_at

### `is_stop_loss_hit() -> bool`
**Pre:** None
**Post:** Returns True if stop_loss triggered (price <= stop for LONG, price >= stop for SHORT)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_take_profit_hit() -> bool`
**Pre:** None
**Post:** Returns True if take_profit triggered (price >= tp for LONG, price <= tp for SHORT)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_risk_reward_ratio() -> Optional[Decimal]`
**Pre:** None
**Post:** Returns reward/risk = abs(tp - entry) / abs(entry - stop); None if stop or tp not set or risk = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_age_days() -> int`
**Pre:** None
**Post:** Returns (exit_date - entry_date).days if CLOSED else (now - entry_date).days
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_open() -> bool`
**Pre:** None
**Post:** Returns True if status == OPEN
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_closed() -> bool`
**Pre:** None
**Post:** Returns True if status == CLOSED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_profitable() -> bool`
**Pre:** None
**Post:** Returns True if pnl_amount > 0 (realized if CLOSED else unrealized)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `create_long(symbol, quantity, entry_price, currency, stop_loss, take_profit) -> Position` (classmethod)
**Pre:** symbol non-empty; quantity > 0; entry_price > 0
**Post:** Returns new LONG position with side=LONG, status=OPEN
**Raises:** None (validation in __init__)
**Retry:** No
**Side Effects:** None (factory)

### `create_short(symbol, quantity, entry_price, currency, stop_loss, take_profit) -> Position` (classmethod)
**Pre:** symbol non-empty; quantity > 0; entry_price > 0
**Post:** Returns new SHORT position with side=SHORT, status=OPEN
**Raises:** None (validation in __init__)
**Retry:** No
**Side Effects:** None (factory)

### `to_dict() -> dict`
**Pre:** None
**Post:** Returns dict representation with all fields and computed P&L
**Raises:** None
**Retry:** No
**Side Effects:** None (serialization)

---

## Acceptance Criteria
- [ ] **AC-001:** Symbol must be non-empty
- [ ] **AC-002:** Quantity must be non-negative
- [ ] **AC-003:** Entry price and current price must be positive (cannot be zero)
- [ ] **AC-004:** Long P&L = (current - entry) × quantity
- [ ] **AC-005:** Short P&L = -(current - entry) × quantity (inverse)
- [ ] **AC-006:** Cost basis = quantity × avg_entry_price
- [ ] **AC-007:** Position value = quantity × current_price
- [ ] **AC-008:** Add shares recalculates average entry price
- [ ] **AC-009:** Remove shares to zero sets status = CLOSED
- [ ] **AC-010:** Stop loss triggers for LONG when price <= stop_loss
- [ ] **AC-011:** Stop loss triggers for SHORT when price >= stop_loss
- [ ] **AC-012:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Position Entity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Entity invariants | DDD (Evans) | Validate invariants on creation | ✅ OK - _validate() |
| Identity | DDD (Evans) | Symbol + entry_date = identity | ✅ OK - No surrogate ID |
| Encapsulation | BASE_RULES.md (ARCH-004) | Private methods with _ prefix | ✅ OK - _validate() |
| Long P&L formula | Trading standard | (current - entry) × quantity | ✅ OK - get_unrealized_pnl_amount() |
| Short P&L formula | Trading standard | -(current - entry) × quantity | ✅ OK - Inverse calculation |
| Cost basis | Trading standard | quantity × avg_entry_price | ✅ OK - get_cost_basis() |
| Average up/down | Trading standard | (old_cost + new_cost) / total_qty | ✅ OK - add_shares() |
| Stop loss LONG | Risk management | Trigger when price <= stop_loss | ✅ OK - is_stop_loss_hit() |
| Stop loss SHORT | Risk management | Trigger when price >= stop_loss | ✅ OK - Inverse logic |
| Take profit LONG | Risk management | Trigger when price >= take_profit | ✅ OK - is_take_profit_hit() |
| Take profit SHORT | Risk management | Trigger when price <= take_profit | ✅ OK - Inverse logic |
| Risk/reward ratio | Trading standard | reward / risk | ✅ OK - get_risk_reward_ratio() |
| Max/min price tracking | Trading analytics | Track highest/lowest since entry | ✅ OK - update_price() |
| Closed position P&L | Trading standard | Use exit price for realized P&L | ✅ OK - get_realized_pnl_amount() |
| Factory methods | GoF patterns | create_long(), create_short() | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only value objects |
| Value objects | DDD (Evans) | Money is value object | ✅ OK - Used correctly |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for entity design patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:**
  - `app.domain.value_objects.money` (Money)

---

## Required Tests
- **test_position_entity.py:**
  - `test_create_position_success()` - Valid position created
  - `test_create_position_empty_symbol()` - Raises ValueError
  - `test_create_position_negative_quantity()` - Raises ValueError
  - `test_create_position_negative_entry_price()` - Raises ValueError
  - `test_create_position_zero_current_price()` - Raises ValueError
  - `test_get_value()` - quantity × current_price
  - `test_get_cost_basis()` - quantity × avg_entry_price
  - `test_long_unrealized_pnl_profit()` - (current - entry) × qty > 0
  - `test_long_unrealized_pnl_loss()` - (current - entry) × qty < 0
  - `test_short_unrealized_pnl_profit()` - -(current - entry) × qty > 0 (price down)
  - `test_short_unrealized_pnl_loss()` - -(current - entry) × qty < 0 (price up)
  - `test_realized_pnl_closed()` - (exit - entry) × qty
  - `test_realized_pnl_open_returns_zero()` - Open positions return 0
  - `test_pnl_percent()` - (pnl / cost) × 100
  - `test_pnl_percent_zero_cost()` - Returns 0
  - `test_update_price()` - Updates price and max/min
  - `test_update_price_negative()` - Raises ValueError
  - `test_add_shares_average_up()` - Recalculates avg_entry_price
  - `test_add_shares_average_down()` - Recalculates avg_entry_price
  - `test_add_shares_negative_quantity()` - Raises ValueError
  - `test_remove_shares_partial()` - Reduces quantity
  - `test_remove_shares_full_exit()` - Sets status CLOSED, exit_date
  - `test_remove_shares_exceeds_holdings()` - Raises ValueError
  - `test_is_stop_loss_hit_long()` - True when price <= stop
  - `test_is_stop_loss_hit_short()` - True when price >= stop
  - `test_is_stop_loss_not_set()` - Returns False
  - `test_is_take_profit_hit_long()` - True when price >= tp
  - `test_is_take_profit_hit_short()` - True when price <= tp
  - `test_is_take_profit_not_set()` - Returns False
  - `test_risk_reward_ratio()` - reward / risk
  - `test_risk_reward_ratio_no_levels()` - Returns None
  - `test_risk_reward_ratio_zero_risk()` - Returns None
  - `test_get_age_days_open()` - (now - entry_date).days
  - `test_get_age_days_closed()` - (exit_date - entry_date).days
  - `test_is_open()` - True if status == OPEN
  - `test_is_closed()` - True if status == CLOSED
  - `test_is_profitable_long()` - True if unrealized > 0
  - `test_is_profitable_short()` - True if unrealized > 0 (price down)
  - `test_create_long_factory()` - Creates LONG position
  - `test_create_short_factory()` - Creates SHORT position
  - `test_to_dict()` - Serialization
  - `test_avg_price_alias()` - Returns avg_entry_price
  - `test_max_price_tracking()` - Updates on price increase
  - `test_min_price_tracking()` - Updates on price decrease

---

## Notes
- **Critical:** Position is an entity within the Portfolio aggregate
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003)
- **Entity Identity:** symbol + entry_date uniquely identifies a position
- **Long Position:** Profits when price increases (current > entry)
- **Short Position:** Profits when price decreases (current < entry)
- **Unrealized P&L:** Paper profit/loss on open positions
- **Realized P&L:** Actual profit/loss on closed positions
- **Cost Basis:** Total cost to acquire position (quantity × avg_entry_price)
- **Position Value:** Current market value (quantity × current_price)
- **Average Price Update:** When adding shares, recalculate weighted average: (old_cost + new_cost) / total_quantity
- **Stop Loss (LONG):** Sell trigger when price drops to or below stop_loss
- **Stop Loss (SHORT):** Buy to cover trigger when price rises to or above stop_loss
- **Take Profit (LONG):** Sell trigger when price reaches or exceeds take_profit
- **Take Profit (SHORT):** Buy to cover trigger when price drops to or below take_profit
- **Risk/Reward Ratio:** Potential profit divided by potential risk (reward/risk)
- **Max/Min Price:** Tracks highest and lowest prices since entry (for analytics)
- **Closed Position:** When quantity reaches 0, status becomes CLOSED and exit_date is set
- **Money Value Object:** get_value(), get_cost_basis() return Money (not Decimal)
- **P&L as Money:** get_unrealized_pnl(), get_realized_pnl() return Money with absolute value
- **P&L as Decimal:** get_unrealized_pnl_amount(), get_realized_pnl_amount() return signed values
- **Backward Compatibility:** avg_price property aliases avg_entry_price

---

**File Reference:** `app/domain/entities/position.py`
**Last Audited:** 2026-02-01
