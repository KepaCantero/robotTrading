# order.py

## Purpose
Order Entity - Trading order representation with comprehensive state machine based on Tomasini's order lifecycle methodology.

---

## Type Definitions / Data Classes

### OrderSide (Enum)
```python
class OrderSide(Enum):
    BUY = "buy"      # Buy order
    SELL = "sell"    # Sell order
```

### OrderType (Enum)
```python
class OrderType(Enum):
    MARKET = "market"          # Market order (immediate execution)
    LIMIT = "limit"            # Limit order (price limit)
    STOP_LOSS = "stop_loss"    # Stop loss order
    TAKE_PROFIT = "take_profit"  # Take profit order
    STOP_LIMIT = "stop_limit"  # Stop limit order
```

### OrderStatus (Enum)
```python
class OrderStatus(Enum):
    PENDING = "pending"                  # Created but not submitted
    VALIDATED = "validated"              # Passed validation
    SUBMITTED = "submitted"              # Submitted to broker
    ACKNOWLEDGED = "acknowledged"        # Acknowledged by broker
    PARTIALLY_FILLED = "partially_filled"  # Partial fill
    FILLED = "filled"                    # Completely filled (terminal)
    CANCEL_PENDING = "cancel_pending"    # Cancellation requested
    CANCELLED = "cancelled"              # Cancelled (terminal)
    REJECTED = "rejected"                # Rejected (terminal)
    EXPIRED = "expired"                  # Expired (terminal)
    SUSPENDED = "suspended"              # Temporarily suspended
```

### OrderEvent (Enum)
```python
class OrderEvent(Enum):
    CREATE = "create"              # Order created
    VALIDATE = "validate"          # Validation completed
    SUBMIT = "submit"              # Submitted to broker
    ACKNOWLEDGE = "acknowledge"    # Broker acknowledged
    PARTIAL_FILL = "partial_fill"  # Partial fill occurred
    FILL = "fill"                  # Full fill occurred
    CANCEL_REQUEST = "cancel_request"  # Cancel requested
    CANCEL_CONFIRM = "cancel_confirm"   # Cancel confirmed
    REJECT = "reject"              # Order rejected
    EXPIRE = "expire"              # Order expired
    SUSPEND = "suspend"            # Order suspended
    UNSUSPEND = "unsuspend"        # Order unsuspended
```

### OrderFill
```python
@dataclass
class OrderFill:
    fill_id: str                      # REQUIRED - Unique fill identifier
    quantity: Decimal                  # REQUIRED - Fill quantity
    price: Decimal                     # REQUIRED - Fill price
    timestamp: datetime                # REQUIRED - Fill timestamp
    fee: Optional[Decimal]             # OPTIONAL - Transaction fee
    liquidity: Optional[str]           # OPTIONAL - "maker" or "taker"
```

### Order
```python
@dataclass
class Order:
    order_id: str                      # REQUIRED - Unique order identifier
    symbol: str                        # REQUIRED - Trading symbol
    side: OrderSide                    # REQUIRED - BUY or SELL
    order_type: OrderType              # REQUIRED - Order type
    quantity: Decimal                   # REQUIRED - Order quantity
    price: Optional[Decimal]           # OPTIONAL - Limit price
    stop_price: Optional[Decimal]      # OPTIONAL - Stop price (for stop orders)

    status: OrderStatus                # Default: PENDING
    filled_quantity: Decimal            # Default: 0
    avg_fill_price: Optional[Decimal]   # Default: None

    created_at: datetime                # Default: utcnow()
    updated_at: datetime                # Default: utcnow()
    submitted_at: Optional[datetime]    # Default: None
    filled_at: Optional[datetime]       # Default: None
    cancelled_at: Optional[datetime]    # Default: None

    # Extended state machine attributes (Tomasini)
    fills: List[OrderFill]              # Default: []
    rejection_reason: Optional[str]     # Default: None
    expiry_time: Optional[datetime]     # Default: None
    time_in_force: str                  # Default: "GTC"

    # Event tracking
    event_history: List[Dict[str, Any]]  # Default: []

    # Validation flags
    is_validated: bool                  # Default: False
    validation_errors: List[str]        # Default: []

    # External identifiers
    broker_order_id: Optional[str]      # Default: None
    exchange_order_id: Optional[str]     # Default: None

    # Callbacks for event-driven processing
    on_fill: Optional[Callable[[OrderFill], None]]      # Default: None
    on_cancel: Optional[Callable[[], None]]             # Default: None
    on_reject: Optional[Callable[[str], None]]          # Default: None
```

**Invariants (enforced in __post_init__):**
- `order_id` must be non-empty
- `quantity` must be positive (> 0)
- `price` (if set) must be positive
- `stop_price` (if set) must be positive

---

## Function Signatures (Contracts)

### `Order.__post_init__() -> None`
**Pre:** None
**Post:** Order validated, CREATE event recorded
**Raises:** `ValueError` if invariants violated
**Retry:** No
**Side Effects:** Validates invariants, records initial event

### `_record_event(event, data) -> None` (private)
**Pre:** event is valid OrderEvent
**Post:** Event appended to event_history with timestamp
**Raises:** None
**Retry:** No
**Side Effects:** Modifies event_history

### `_validate_state_transition(new_status) -> bool` (private)
**Pre:** new_status is valid OrderStatus
**Post:** Returns True if transition from current status to new_status is valid
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Valid State Transitions:**
- PENDING → VALIDATED, REJECTED, CANCELLED
- VALIDATED → SUBMITTED, REJECTED, CANCELLED
- SUBMITTED → ACKNOWLEDGED, REJECTED, CANCEL_PENDING
- ACKNOWLEDGED → PARTIALLY_FILLED, FILLED, CANCEL_PENDING, SUSPENDED
- PARTIALLY_FILLED → PARTIALLY_FILLED, FILLED, CANCEL_PENDING
- CANCEL_PENDING → CANCELLED, ACKNOWLEDGED
- SUSPENDED → ACKNOWLEDGED, CANCEL_PENDING, EXPIRED
- FILLED, CANCELLED, REJECTED, EXPIRED → [] (terminal states)

### `validate() -> bool`
**Pre:** None
**Post:** Returns True if order valid; transitions to VALIDATED or REJECTED
**Raises:** None
**Retry:** No
**Side Effects:** Sets validation_errors, is_validated, status

**Validation Rules:**
- quantity > 0
- LIMIT orders must have price
- STOP_LOSS/STOP_LIMIT must have stop_price
- time_in_force in ["GTC", "IOC", "FOK", "DAY"]
- GTC orders must have expiry_time

### `submit() -> None`
**Pre:** status == VALIDATED
**Post:** status = SUBMITTED; submitted_at set
**Raises:** `ValueError` if status != VALIDATED
**Retry:** No
**Side Effects:** Updates status, timestamp, records event

### `acknowledge(broker_order_id) -> None`
**Pre:** status == SUBMITTED
**Post:** status = ACKNOWLEDGED; broker_order_id set (if provided)
**Raises:** `ValueError` if status != SUBMITTED
**Retry:** No
**Side Effects:** Updates status, broker_order_id, records event

### `fill(fill_price, fill_quantity, fee, liquidity) -> None`
**Pre:** status in [ACKNOWLEDGED, PARTIALLY_FILLED, SUSPENDED]; fill_price > 0
**Post:** Fill recorded; status updated to PARTIALLY_FILLED or FILLED
**Raises:** `ValueError` if invalid state or fill_quantity exceeds remaining
**Retry:** No
**Side Effects:** Updates fills, filled_quantity, avg_fill_price, status, timestamps; triggers on_fill callback

**Fill Logic:**
- Creates OrderFill record
- Updates filled_quantity
- Recalculates avg_fill_price: (old_value + new_value) / filled_quantity
- Transitions to FILLED if filled_quantity == quantity
- Transitions to PARTIALLY_FILLED if partially filled

### `request_cancel() -> None`
**Pre:** status not in terminal states [FILLED, CANCELLED, REJECTED, EXPIRED]
**Post:** status = CANCEL_PENDING
**Raises:** `ValueError` if in terminal state
**Retry:** No
**Side Effects:** Updates status, records event

### `confirm_cancel() -> None`
**Pre:** status == CANCEL_PENDING
**Post:** status = CANCELLED; cancelled_at set
**Raises:** `ValueError` if status != CANCEL_PENDING
**Retry:** No
**Side Effects:** Updates status, timestamp, records event; triggers on_cancel callback

### `reject(reason) -> None`
**Pre:** status not in [FILLED, CANCELLED]
**Post:** status = REJECTED; rejection_reason set
**Raises:** `ValueError` if already FILLED or CANCELLED
**Retry:** No
**Side Effects:** Updates status, rejection_reason, records event; triggers on_reject callback

### `suspend() -> None`
**Pre:** status == ACKNOWLEDGED
**Post:** status = SUSPENDED
**Raises:** `ValueError` if status != ACKNOWLEDGED
**Retry:** No
**Side Effects:** Updates status, records event

### `unsuspend() -> None`
**Pre:** status == SUSPENDED
**Post:** status = ACKNOWLEDGED
**Raises:** `ValueError` if status != SUSPENDED
**Retry:** No
**Side Effects:** Updates status, records event

### `expire() -> None`
**Pre:** status not in [FILLED, CANCELLED, REJECTED]
**Post:** status = EXPIRED
**Raises:** `ValueError` if in terminal state
**Retry:** No
**Side Effects:** Updates status, records event

### `_transition_to(new_status, event, data) -> None` (private)
**Pre:** new_status reachable from current status
**Post:** status updated; event recorded; updated_at refreshed
**Raises:** `ValueError` if transition invalid
**Retry:** No
**Side Effects:** Updates status, timestamp, event_history

### `is_filled() -> bool`
**Pre:** None
**Post:** Returns True if status == FILLED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_partially_filled() -> bool`
**Pre:** None
**Post:** Returns True if status == PARTIALLY_FILLED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_pending() -> bool`
**Pre:** None
**Post:** Returns True if status in [PENDING, VALIDATED, SUBMITTED, ACKNOWLEDGED]
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_terminal() -> bool`
**Pre:** None
**Post:** Returns True if status in [FILLED, CANCELLED, REJECTED, EXPIRED]
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_active() -> bool`
**Pre:** None
**Post:** Returns True if status in [ACKNOWLEDGED, PARTIALLY_FILLED, SUSPENDED]
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_remaining_quantity() -> Decimal`
**Pre:** None
**Post:** Returns quantity - filled_quantity
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_fill_rate() -> float`
**Pre:** None
**Post:** Returns filled_quantity / quantity (0.0 to 1.0)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_total_fees() -> Decimal`
**Pre:** None
**Post:** Returns sum of all fill.fee values
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_age_seconds() -> float`
**Pre:** None
**Post:** Returns (now - created_at).total_seconds()
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict representation of order
**Raises:** None
**Retry:** No
**Side Effects:** None (serialization)

---

## Acceptance Criteria
- [ ] **AC-001:** Order ID must be non-empty
- [ ] **AC-002:** Quantity must be positive
- [ ] **AC-003:** Price and stop_price must be positive (if set)
- [ ] **AC-004:** LIMIT orders require price
- [ ] **AC-005:** STOP_LOSS/STOP_LIMIT require stop_price
- [ ] **AC-006:** State transitions follow Tomasini's valid transitions
- [ ] **AC-007:** Terminal states cannot transition (FILLED, CANCELLED, REJECTED, EXPIRED)
- [ ] **AC-008:** Partial fills update avg_fill_price correctly
- [ ] **AC-009:** Event history records all state changes
- [ ] **AC-010:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Order Entity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Entity invariants | DDD (Evans) | Validate on creation | ✅ OK - __post_init__ |
| State machine | Tomasini (2008) | Valid state transitions only | ✅ OK - _validate_state_transition() |
| Terminal states | State machine | No transitions from terminal | ✅ OK - Enforced in validation |
| Event-driven | Tomasini (2008) | Record all events | ✅ OK - _record_event() |
| Fill tracking | Tomasini (2008) | Multiple partial fills | ✅ OK - fills list |
| Average price | Trading standard | VWAP of fills | ✅ OK - avg_fill_price calculation |
| Callbacks | Event-driven | on_fill, on_cancel, on_reject | ✅ OK - Implemented |
| Time in force | Order types | GTC, IOC, FOK, DAY | ✅ OK - validate() |
| Validation pre-submit | Tomasini (2008) | Validate before submit | ✅ OK - validate() method |
| Order types | Trading standard | MARKET, LIMIT, STOP_LOSS, etc. | ✅ OK - OrderType enum |
| Fill rate | Trading analytics | filled_qty / total_qty | ✅ OK - get_fill_rate() |
| Remaining quantity | Trading standard | total - filled | ✅ OK - get_remaining_quantity() |
| Broker IDs | Integration | broker_order_id, exchange_order_id | ✅ OK - External identifiers |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Tomasini (2008) "Trading Systems" for order state machine patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:** None (domain entity)

---

## Required Tests
- **test_order_entity.py:**
  - `test_create_order_success()` - Valid order created
  - `test_create_order_empty_id()` - Raises ValueError
  - `test_create_order_zero_quantity()` - Raises ValueError
  - `test_create_order_negative_price()` - Raises ValueError
  - `test_validate_success()` - Transitions to VALIDATED
  - `test_validate_no_limit_price()` - Adds error, transitions to REJECTED
  - `test_validate_no_stop_price()` - Adds error for stop orders
  - `test_validate_invalid_tif()` - Adds error for invalid time_in_force
  - `test_submit_from_validated()` - Transitions to SUBMITTED
  - `test_submit_from_pending()` - Raises ValueError
  - `test_acknowledge_from_submitted()` - Transitions to ACKNOWLEDGED
  - `test_acknowledge_sets_broker_id()` - broker_order_id set
  - `test_fill_full()` - Transitions to FILLED
  - `test_fill_partial()` - Transitions to PARTIALLY_FILLED
  - `test_fill_multiple_partial()` - Updates avg_fill_price
  - `test_fill_exceeds_quantity()` - Raises ValueError
  - `test_fill_from_invalid_state()` - Raises ValueError
  - `test_request_cancel_from_active()` - Transitions to CANCEL_PENDING
  - `test_request_cancel_from_terminal()` - Raises ValueError
  - `test_confirm_cancel_from_pending()` - Transitions to CANCELLED
  - `test_confirm_cancel_from_acknowledged()` - Transitions to ACKNOWLEDGED
  - `test_reject_from_pending()` - Transitions to REJECTED
  - `test_reject_from_filled()` - Raises ValueError
  - `test_suspend_from_acknowledged()` - Transitions to SUSPENDED
  - `test_unsuspend_from_suspended()` - Transitions to ACKNOWLEDGED
  - `test_expire_from_active()` - Transitions to EXPIRED
  - `test_invalid_state_transition()` - Raises ValueError
  - `test_is_filled()` - True when FILLED
  - `test_is_partially_filled()` - True when PARTIALLY_FILLED
  - `test_is_pending()` - True for pending states
  - `test_is_terminal()` - True for terminal states
  - `test_is_active()` - True for active states
  - `test_get_remaining_quantity()` - total - filled
  - `test_get_fill_rate()` - filled / total
  - `test_get_total_fees()` - Sum of fill fees
  - `test_get_age_seconds()` - Time since created
  - `test_event_history()` - All events recorded
  - `test_on_fill_callback()` - Callback triggered on fill
  - `test_on_cancel_callback()` - Callback triggered on cancel
  - `test_on_reject_callback()` - Callback triggered on reject
  - `test_to_dict()` - Serialization

---

## Notes
- **Critical:** Order implements comprehensive state machine per Tomasini's "Trading Systems"
- **Tomasini Reference:** "Trading Systems: A New Approach to Systematic Trading Strategy Development" (2008)
- **State Machine Design:** Prevents invalid state transitions via _validate_state_transition()
- **Event Tracking:** All state changes recorded in event_history with timestamps
- **Fill Tracking:** Supports multiple partial fills with VWAP calculation
- **Average Fill Price:** VWAP = (Σ(fill_price × fill_quantity)) / total_filled_quantity
- **Terminal States:** FILLED, CANCELLED, REJECTED, EXPIRED (no transitions allowed)
- **Active States:** ACKNOWLEDGED, PARTIALLY_FILLED, SUSPENDED (can be filled)
- **Pending States:** PENDING, VALIDATED, SUBMITTED, ACKNOWLEDGED (not yet filled)
- **Callbacks:** Event-driven design with on_fill, on_cancel, on_reject hooks
- **Time in Force:** GTC (Good-Til-Cancelled), IOC (Immediate-or-Cancel), FOK (Fill-or-Kill), DAY
- **Validation:** Pre-submission validation checks order constraints
- **Partial Fills:** Order can be filled across multiple executions
- **Fill Rate:** Ratio of filled_quantity to total_quantity (0.0 to 1.0)
- **Remaining Quantity:** quantity - filled_quantity (unfilled amount)
- **Age:** Time elapsed since order creation (in seconds)
- **Event History:** Complete audit trail of order lifecycle
- **Broker Integration:** External IDs for broker and exchange order tracking

---

**File Reference:** `app/domain/entities/order.py`
**Last Audited:** 2026-02-01
