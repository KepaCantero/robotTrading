# trade.py

## Purpose
Trade Entity - Represents a completed trade with entry/exit information, profit/loss, and trade metadata.

---

## Type Definitions / Data Classes

### TradeStatus (Enum)
```python
class TradeStatus(str, Enum):
    FILLED = "filled"                    # Trade fully executed
    PARTIALLY_FILLED = "partially_filled"  # Partial execution
    CANCELLED = "cancelled"              # Trade cancelled
    REJECTED = "rejected"                # Trade rejected
    PENDING = "pending"                  # Trade pending execution
```

### TradeType (Enum)
```python
class TradeType(str, Enum):
    MARKET = "market"                    # Market order trade
    LIMIT = "limit"                      # Limit order trade
    STOP = "stop"                        # Stop order trade
    STOP_LIMIT = "stop_limit"            # Stop limit order trade
```

### ExitReason (Enum)
```python
class ExitReason(str, Enum):
    TAKE_PROFIT = "take_profit"          # Take profit hit
    STOP_LOSS = "stop_loss"              # Stop loss hit
    MANUAL = "manual"                    # Manual exit
    SIGNAL_REVERSAL = "signal_reversal"  # Trading signal reversed
    RISK_LIMIT = "risk_limit"            # Risk limit exceeded
    TIME_EXIT = "time_exit"              # Time-based exit
    LIQUIDATION = "liquidation"          # Position liquidated
```

### Trade
```python
@dataclass
class Trade:
    # Identity
    trade_id: str                        # REQUIRED - Unique trade identifier
    symbol: str                          # REQUIRED - Trading symbol

    # Trade details
    side: PositionSide                   # REQUIRED - LONG or SHORT
    quantity: Decimal                    # REQUIRED - Trade quantity
    entry_price: Decimal                 # REQUIRED - Entry price
    exit_price: Decimal                  # REQUIRED - Exit price
    currency: str                        # Default: "USD"

    # Timestamps
    entry_date: datetime                 # Default: utcnow()
    exit_date: Optional[datetime]        # Default: None

    # Execution details
    trade_type: TradeType                # Default: MARKET
    status: TradeStatus                  # Default: FILLED
    exit_reason: Optional[ExitReason]    # Default: None

    # Costs
    commission_paid: Decimal             # Default: 0
    slippage_cost: Decimal               # Default: 0

    # Risk management
    stop_loss: Optional[Decimal]         # Default: None
    take_profit: Optional[Decimal]       # Default: None

    # Metadata
    strategy_name: Optional[str]         # Default: None
    notes: Optional[str]                 # Default: None
    tags: list[str]                      # Default: []
```

**Invariants (enforced in __post_init__):**
- `trade_id` must be non-empty
- `symbol` must be non-empty
- `quantity` must be positive (> 0)
- `entry_price` must be non-negative
- `exit_price` must be non-negative

---

## Function Signatures (Contracts)

### `Trade.__post_init__() -> None`
**Pre:** None
**Post:** Trade validated
**Raises:** `ValueError` if invariants violated
**Retry:** No
**Side Effects:** Validates invariants

### `get_gross_pnl() -> Money`
**Pre:** None
**Post:** Returns Money with (exit_price - entry_price) × quantity for LONG, -(exit - entry) × quantity for SHORT; 0 if exit_price = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_net_pnl() -> Money`
**Pre:** None
**Post:** Returns Money with gross_pnl - commission_paid - slippage_cost
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_pnl_percent() -> Decimal`
**Pre:** None
**Post:** Returns (net_pnl / entry_value) × 100; 0 if entry_value = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_total_cost() -> Money`
**Pre:** None
**Post:** Returns Money with commission_paid + slippage_cost
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_holding_period_days() -> int`
**Pre:** None
**Post:** Returns (exit_date - entry_date).days if closed, else (now - entry_date).days
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_holding_period_hours() -> float`
**Pre:** None
**Post:** Returns holding period in hours (delta.total_seconds() / 3600)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_risk_reward_ratio() -> Optional[Decimal]`
**Pre:** None
**Post:** Returns reward/risk = abs(tp - entry) / abs(entry - stop); None if stop or tp not set or risk = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_actual_r_reward() -> Optional[Decimal]`
**Pre:** None
**Post:** Returns actual reward/risk = net_pnl / (abs(entry - stop) × quantity); None if stop not set or risk = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_profitable() -> bool`
**Pre:** None
**Post:** Returns True if net_pnl > 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_winner() -> bool`
**Pre:** None
**Post:** Returns True if net_pnl > 0 (synonym for is_profitable)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_loser() -> bool`
**Pre:** None
**Post:** Returns True if net_pnl < 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_break_even() -> bool`
**Pre:** None
**Post:** Returns True if abs(net_pnl) < 0.01
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_open() -> bool`
**Pre:** None
**Post:** Returns True if exit_date is None OR exit_price = 0
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_closed() -> bool`
**Pre:** None
**Post:** Returns True if not is_open()
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_long() -> bool`
**Pre:** None
**Post:** Returns True if side == LONG
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_short() -> bool`
**Pre:** None
**Post:** Returns True if side == SHORT
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `from_position(trade_id, position_quantity, entry_price, exit_price, symbol, side, entry_date, exit_date, exit_reason, commission, strategy_name) -> Trade` (classmethod)
**Pre:** trade_id non-empty; position_quantity > 0; entry_price >= 0; exit_price >= 0
**Post:** Returns Trade with status = FILLED
**Raises:** None
**Retry:** No
**Side Effects:** None (factory)

### `create_long(trade_id, symbol, quantity, entry_price, exit_price, entry_date, exit_date, stop_loss, take_profit, commission, strategy_name) -> Trade` (classmethod)
**Pre:** trade_id non-empty; quantity > 0; entry_price >= 0; exit_price >= 0
**Post:** Returns Trade with side = LONG, status = FILLED
**Raises:** None
**Retry:** No
**Side Effects:** None (factory)

### `create_short(trade_id, symbol, quantity, entry_price, exit_price, entry_date, exit_date, stop_loss, take_profit, commission, strategy_name) -> Trade` (classmethod)
**Pre:** trade_id non-empty; quantity > 0; entry_price >= 0; exit_price >= 0
**Post:** Returns Trade with side = SHORT, status = FILLED
**Raises:** None
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
- [ ] **AC-001:** Trade ID must be non-empty
- [ ] **AC-002:** Symbol must be non-empty
- [ ] **AC-003:** Quantity must be positive
- [ ] **AC-004:** Entry price and exit price must be non-negative
- [ ] **AC-005:** Long gross P&L = (exit - entry) × quantity
- [ ] **AC-006:** Short gross P&L = -(exit - entry) × quantity (inverse)
- [ ] **AC-007:** Net P&L = gross P&L - commission - slippage
- [ ] **AC-008:** P&L percent = (net_pnl / entry_value) × 100
- [ ] **AC-009:** Trade is open if exit_date is None OR exit_price = 0
- [ ] **AC-010:** All public methods have complete type hints

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Trade Entity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Entity invariants | DDD (Evans) | Validate on creation | ✅ OK - __post_init__ |
| Trade vs Position | DDD (Evans) | Trade = historical (closed), Position = current (open) | ✅ OK - Design intent |
| Long P&L formula | Trading standard | (exit - entry) × quantity | ✅ OK - get_gross_pnl() |
| Short P&L formula | Trading standard | -(exit - entry) × quantity | ✅ OK - Inverse calculation |
| Net P&L | Trading standard | Gross - commission - slippage | ✅ OK - get_net_pnl() |
| P&L percent | Trading standard | (net_pnl / entry_value) × 100 | ✅ OK - get_pnl_percent() |
| Holding period | Trading analytics | Time between entry and exit | ✅ OK - get_holding_period_days() |
| Risk/reward ratio | Trading standard | reward / risk | ✅ OK - get_risk_reward_ratio() |
| Actual R/R | Trading analytics | Actual pnl / Planned risk | ✅ OK - get_actual_r_reward() |
| Exit reason | Trading analytics | Why trade was closed | ✅ OK - ExitReason enum |
| Commission | Trading costs | Broker fees | ✅ OK - commission_paid |
| Slippage | Trading costs | Execution slippage cost | ✅ OK - slippage_cost |
| Winner/Loser | Trading analytics | Profitability classification | ✅ OK - is_winner/is_loser |
| Factory methods | GoF patterns | from_position, create_long, create_short | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only domain types |
| Value objects | DDD (Evans) | Money is value object | ✅ OK - Used correctly |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for entity design patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:**
  - `app.domain.entities.position` (PositionSide)
  - `app.domain.value_objects.money` (Money)

---

## Required Tests
- **test_trade_entity.py:**
  - `test_create_trade_success()` - Valid trade created
  - `test_create_trade_empty_id()` - Raises ValueError
  - `test_create_trade_empty_symbol()` - Raises ValueError
  - `test_create_trade_zero_quantity()` - Raises ValueError
  - `test_create_trade_negative_entry_price()` - Raises ValueError
  - `test_create_trade_negative_exit_price()` - Raises ValueError
  - `test_long_gross_pnl_profit()` - (exit - entry) × qty > 0
  - `test_long_gross_pnl_loss()` - (exit - entry) × qty < 0
  - `test_short_gross_pnl_profit()` - -(exit - entry) × qty > 0 (price down)
  - `test_short_gross_pnl_loss()` - -(exit - entry) × qty < 0 (price up)
  - `test_net_pnl_with_costs()` - Gross - commission - slippage
  - `test_pnl_percent()` - (net_pnl / entry_value) × 100
  - `test_pnl_percent_zero_entry()` - Returns 0
  - `test_total_cost()` - Commission + slippage
  - `test_holding_period_closed()` - (exit - entry).days
  - `test_holding_period_open()` - (now - entry).days
  - `test_holding_period_hours()` - delta / 3600
  - `test_risk_reward_ratio()` - reward / risk
  - `test_risk_reward_ratio_no_levels()` - Returns None
  - `test_risk_reward_ratio_zero_risk()` - Returns None
  - `test_actual_r_reward()` - Actual pnl / Planned risk
  - `test_actual_r_reward_no_stop()` - Returns None
  - `test_is_profitable()` - True if net_pnl > 0
  - `test_is_winner()` - Synonym for is_profitable
  - `test_is_loser()` - True if net_pnl < 0
  - `test_is_break_even()` - True if abs(pnl) < 0.01
  - `test_is_open_no_exit_date()` - True when exit_date is None
  - `test_is_open_zero_exit_price()` - True when exit_price = 0
  - `test_is_closed()` - True when has exit
  - `test_is_long()` - True if side == LONG
  - `test_is_short()` - True if side == SHORT
  - `test_from_position_factory()` - Creates from position data
  - `test_create_long_factory()` - Creates LONG trade
  - `test_create_short_factory()` - Creates SHORT trade
  - `test_to_dict()` - Serialization
  - `test_exit_reason_take_profit()` - ExitReason.TAKE_PROFIT
  - `test_exit_reason_stop_loss()` - ExitReason.STOP_LOSS
  - `test_exit_reason_manual()` - ExitReason.MANUAL

---

## Notes
- **Critical:** Trade represents a COMPLETED trade (historical record), while Position represents a CURRENT holding
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003)
- **Entity Identity:** trade_id uniquely identifies a trade
- **Long Trade:** Profits when exit_price > entry_price
- **Short Trade:** Profits when exit_price < entry_price (inverse)
- **Gross P&L:** Raw profit/loss before costs
- **Net P&L:** Gross P&L minus all trading costs (commission + slippage)
- **Commission:** Broker fees paid for execution
- **Slippage:** Cost from execution price difference vs expected
- **P&L Percent:** Return as percentage of entry value
- **Holding Period:** Time from entry to exit (critical for analytics)
- **Risk/Reward Ratio:** Planned ratio (take_profit - entry) / (entry - stop_loss)
- **Actual R/R:** Realized ratio (net_pnl / planned_risk)
- **Winner:** Trade with positive net P&L
- **Loser:** Trade with negative net P&L
- **Break Even:** Trade with net P&L ≈ 0 (within $0.01 tolerance)
- **Exit Reason:** Why the trade was closed (important for strategy analysis)
- **Trade Type:** Order type used for execution (MARKET, LIMIT, STOP, etc.)
- **Strategy Name:** Which strategy generated the trade (for analytics)
- **Tags:** Flexible metadata for categorization/tracking
- **Factory Methods:** from_position() for converting closed positions to trades
- **Open Trade:** Trade without exit_date or with exit_price = 0
- **Closed Trade:** Trade with exit_date and exit_price > 0
- **Status:** Default is FILLED (completed execution)
- **Trade vs Order:** Order = intent to trade, Trade = completed execution
- **Trade vs Position:** Trade = historical record, Position = current holding

---

**File Reference:** `app/domain/entities/trade.py`
**Last Audited:** 2026-02-01
