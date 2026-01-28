"""
Order Entity - Trading order representation with comprehensive state machine.

Implements Tomasini's order state machine methodology from "Trading Systems":
- Comprehensive order lifecycle management
- State transitions with validation
- Event-driven order processing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """
    Order status enumeration (Tomasini's comprehensive state machine).

    States:
    - PENDING: Order created but not yet submitted
    - VALIDATED: Order has passed validation checks
    - SUBMITTED: Order submitted to broker/exchange
    - ACKNOWLEDGED: Order acknowledged by broker
    - PARTIALLY_FILLED: Order partially filled
    - FILLED: Order completely filled
    - CANCEL_PENDING: Cancellation requested
    - CANCELLED: Order cancelled
    - REJECTED: Order rejected by broker or validation
    - EXPIRED: Order expired (e.g., Good-Til-Cancelled)
    - SUSPENDED: Order temporarily suspended (risk limits)
    """

    PENDING = "pending"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_PENDING = "cancel_pending"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class OrderEvent(Enum):
    """
    Order events for state machine (Tomasini's event-driven approach).

    Events that trigger state transitions in the order lifecycle.
    """

    CREATE = "create"
    VALIDATE = "validate"
    SUBMIT = "submit"
    ACKNOWLEDGE = "acknowledge"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    CANCEL_REQUEST = "cancel_request"
    CANCEL_CONFIRM = "cancel_confirm"
    REJECT = "reject"
    EXPIRE = "expire"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"


@dataclass
class OrderFill:
    """Record of an order fill."""

    fill_id: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    fee: Optional[Decimal] = None
    liquidity: Optional[str] = None  # "maker" or "taker"


@dataclass
class Order:
    """
    Order entity representing a trading order with comprehensive state machine.

    Implements Tomasini's order state machine from "Trading Systems":
    - Comprehensive state tracking
    - Event-driven state transitions
    - Fill tracking with multiple partial fills
    - Validation and error handling
    """

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None  # For stop-loss orders
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    avg_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Extended state machine attributes (Tomasini)
    fills: List[OrderFill] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    expiry_time: Optional[datetime] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK, DAY

    # Event tracking
    event_history: List[Dict[str, Any]] = field(default_factory=list)

    # Validation flags
    is_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # External identifiers
    broker_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None

    # Callbacks for event-driven processing (Tomasini)
    on_fill: Optional[Callable[[OrderFill], None]] = None
    on_cancel: Optional[Callable[[], None]] = None
    on_reject: Optional[Callable[[str], None]] = None

    def __post_init__(self):
        """Validate order invariants."""
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("Stop price must be positive")

        # Record initial state
        self._record_event(OrderEvent.CREATE, {"status": self.status.value})

    def _record_event(self, event: OrderEvent, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an event in the order history (Tomasini's event tracking).

        Args:
            event: The order event
            data: Additional event data
        """
        event_record = {
            "event": event.value,
            "timestamp": datetime.utcnow().isoformat(),
            "status": self.status.value,
            "data": data or {},
        }
        self.event_history.append(event_record)

    def _validate_state_transition(self, new_status: OrderStatus) -> bool:
        """
        Validate state transition (Tomasini's state machine).

        Args:
            new_status: Target status

        Returns:
            True if transition is valid
        """
        # Define valid state transitions
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.VALIDATED,
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.VALIDATED: [
                OrderStatus.SUBMITTED,
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.SUBMITTED: [
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.REJECTED,
                OrderStatus.CANCEL_PENDING,
            ],
            OrderStatus.ACKNOWLEDGED: [
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED,
                OrderStatus.CANCEL_PENDING,
                OrderStatus.SUSPENDED,
            ],
            OrderStatus.PARTIALLY_FILLED: [
                OrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED,
                OrderStatus.CANCEL_PENDING,
            ],
            OrderStatus.FILLED: [],  # Terminal state
            OrderStatus.CANCEL_PENDING: [OrderStatus.CANCELLED, OrderStatus.ACKNOWLEDGED],
            OrderStatus.CANCELLED: [],  # Terminal state
            OrderStatus.REJECTED: [],  # Terminal state
            OrderStatus.EXPIRED: [],  # Terminal state
            OrderStatus.SUSPENDED: [
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.CANCEL_PENDING,
                OrderStatus.EXPIRED,
            ],
        }

        valid_targets = valid_transitions.get(self.status, [])
        return new_status in valid_targets

    def validate(self) -> bool:
        """
        Validate order before submission (Tomasini's pre-submission validation).

        Returns:
            True if order is valid
        """
        self.validation_errors = []

        # Check quantity
        if self.quantity <= 0:
            self.validation_errors.append("Quantity must be positive")

        # Check price for limit orders
        if self.order_type == OrderType.LIMIT and self.price is None:
            self.validation_errors.append("Limit orders must have a price")

        # Check stop price for stop orders
        if (
            self.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LIMIT)
            and self.stop_price is None
        ):
            self.validation_errors.append(f"{self.order_type.value} orders must have a stop price")

        # Check time in force
        if self.time_in_force not in ("GTC", "IOC", "FOK", "DAY"):
            self.validation_errors.append(f"Invalid time in force: {self.time_in_force}")

        # Check expiry for GTC orders
        if self.time_in_force == "GTC" and self.expiry_time is None:
            self.validation_errors.append("GTC orders must have an expiry time")

        is_valid = len(self.validation_errors) == 0
        self.is_validated = is_valid

        if is_valid:
            self._transition_to(OrderStatus.VALIDATED, OrderEvent.VALIDATE)
        else:
            self._transition_to(
                OrderStatus.REJECTED,
                OrderEvent.REJECT,
                {"reason": "; ".join(self.validation_errors)},
            )

        return is_valid

    def submit(self) -> None:
        """
        Submit order to broker.

        Raises:
            ValueError: If order is not in a valid state for submission
        """
        if self.status != OrderStatus.VALIDATED:
            raise ValueError(
                f"Cannot submit order with status {self.status.value}. " f"Order must be VALIDATED."
            )

        self._transition_to(OrderStatus.SUBMITTED, OrderEvent.SUBMIT)
        self.submitted_at = datetime.utcnow()

    def acknowledge(self, broker_order_id: Optional[str] = None) -> None:
        """
        Acknowledge order receipt from broker.

        Args:
            broker_order_id: Broker's order ID

        Raises:
            ValueError: If order is not in a valid state for acknowledgement
        """
        if self.status != OrderStatus.SUBMITTED:
            raise ValueError(
                f"Cannot acknowledge order with status {self.status.value}. "
                f"Order must be SUBMITTED."
            )

        if broker_order_id:
            self.broker_order_id = broker_order_id

        self._transition_to(OrderStatus.ACKNOWLEDGED, OrderEvent.ACKNOWLEDGE)

    def fill(
        self,
        fill_price: Decimal,
        fill_quantity: Optional[Decimal] = None,
        fee: Optional[Decimal] = None,
        liquidity: Optional[str] = None,
    ) -> None:
        """
        Fill order (partial or complete) with comprehensive tracking (Tomasini).

        Args:
            fill_price: Fill price
            fill_quantity: Fill quantity (None for full fill)
            fee: Transaction fee
            liquidity: "maker" or "taker"

        Raises:
            ValueError: If order is not in a valid state for filling
        """
        valid_states = (
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.SUSPENDED,
        )
        if self.status not in valid_states:
            raise ValueError(
                f"Cannot fill order with status {self.status.value}. "
                f"Order must be ACKNOWLEDGED or PARTIALLY_FILLED."
            )

        qty_to_fill = fill_quantity or (self.quantity - self.filled_quantity)

        if qty_to_fill <= 0:
            raise ValueError("Fill quantity must be positive")

        if self.filled_quantity + qty_to_fill > self.quantity:
            raise ValueError("Fill quantity exceeds order quantity")

        # Create fill record
        fill = OrderFill(
            fill_id=f"{self.order_id}_fill_{len(self.fills) + 1}",
            quantity=qty_to_fill,
            price=fill_price,
            timestamp=datetime.utcnow(),
            fee=fee,
            liquidity=liquidity,
        )
        self.fills.append(fill)

        # Update filled quantity and average price
        total_value = self.filled_quantity * (self.avg_fill_price or 0)
        fill_value = qty_to_fill * fill_price
        self.filled_quantity += qty_to_fill
        self.avg_fill_price = (total_value + fill_value) / self.filled_quantity

        # Update status
        if self.filled_quantity == self.quantity:
            self._transition_to(OrderStatus.FILLED, OrderEvent.FILL)
            self.filled_at = datetime.utcnow()
        else:
            self._transition_to(OrderStatus.PARTIALLY_FILLED, OrderEvent.PARTIAL_FILL)

        # Trigger callback
        if self.on_fill:
            try:
                self.on_fill(fill)
            except Exception:
                # Log but don't raise - callbacks should be robust
                pass

    def request_cancel(self) -> None:
        """
        Request order cancellation.

        Raises:
            ValueError: If order is not in a valid state for cancellation
        """
        if self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ):
            raise ValueError(
                f"Cannot cancel order with status {self.status.value}. "
                f"Order is in a terminal state."
            )

        self._transition_to(OrderStatus.CANCEL_PENDING, OrderEvent.CANCEL_REQUEST)

    def confirm_cancel(self) -> None:
        """
        Confirm order cancellation.

        Raises:
            ValueError: If order is not in CANCEL_PENDING state
        """
        if self.status != OrderStatus.CANCEL_PENDING:
            raise ValueError(
                f"Cannot confirm cancel for order with status {self.status.value}. "
                f"Order must be CANCEL_PENDING."
            )

        self._transition_to(OrderStatus.CANCELLED, OrderEvent.CANCEL_CONFIRM)
        self.cancelled_at = datetime.utcnow()

        # Trigger callback
        if self.on_cancel:
            try:
                self.on_cancel()
            except Exception:
                pass

    def reject(self, reason: str) -> None:
        """
        Reject order.

        Args:
            reason: Rejection reason

        Raises:
            ValueError: If order is not in a valid state for rejection
        """
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            raise ValueError(
                f"Cannot reject order with status {self.status.value}. "
                f"Order is already in a terminal state."
            )

        self.rejection_reason = reason
        self._transition_to(OrderStatus.REJECTED, OrderEvent.REJECT, {"reason": reason})

        # Trigger callback
        if self.on_reject:
            try:
                self.on_reject(reason)
            except Exception:
                pass

    def suspend(self) -> None:
        """
        Suspend order (e.g., due to risk limits).

        Raises:
            ValueError: If order is not in a valid state for suspension
        """
        if self.status != OrderStatus.ACKNOWLEDGED:
            raise ValueError(
                f"Cannot suspend order with status {self.status.value}. "
                f"Order must be ACKNOWLEDGED."
            )

        self._transition_to(OrderStatus.SUSPENDED, OrderEvent.SUSPEND)

    def unsuspend(self) -> None:
        """
        Unsuspend order.

        Raises:
            ValueError: If order is not SUSPENDED
        """
        if self.status != OrderStatus.SUSPENDED:
            raise ValueError(
                f"Cannot unsuspend order with status {self.status.value}. "
                f"Order must be SUSPENDED."
            )

        self._transition_to(OrderStatus.ACKNOWLEDGED, OrderEvent.UNSUSPEND)

    def expire(self) -> None:
        """
        Mark order as expired.

        Raises:
            ValueError: If order is not in a valid state for expiration
        """
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            raise ValueError(
                f"Cannot expire order with status {self.status.value}. "
                f"Order is already in a terminal state."
            )

        self._transition_to(OrderStatus.EXPIRED, OrderEvent.EXPIRE)

    def _transition_to(
        self, new_status: OrderStatus, event: OrderEvent, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Transition to new state with validation (Tomasini's state machine).

        Args:
            new_status: Target status
            event: Event triggering the transition
            data: Additional event data

        Raises:
            ValueError: If transition is invalid
        """
        if not self._validate_state_transition(new_status):
            raise ValueError(
                f"Invalid state transition: {self.status.value} -> {new_status.value} "
                f"(event: {event.value})"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        self._record_event(
            event, {"old_status": old_status.value, "new_status": new_status.value, **(data or {})}
        )

    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED

    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.status == OrderStatus.PARTIALLY_FILLED

    def is_pending(self) -> bool:
        """Check if order is pending (not yet filled)."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.VALIDATED,
            OrderStatus.SUBMITTED,
            OrderStatus.ACKNOWLEDGED,
        )

    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        )

    def is_active(self) -> bool:
        """Check if order is still active (can be filled)."""
        return self.status in (
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.SUSPENDED,
        )

    def get_remaining_quantity(self) -> Decimal:
        """Get remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    def get_fill_rate(self) -> float:
        """Get fill rate (0.0 to 1.0)."""
        if self.quantity == 0:
            return 0.0
        return float(self.filled_quantity / self.quantity)

    def get_total_fees(self) -> Decimal:
        """Get total fees paid across all fills."""
        return sum(((fill.fee or Decimal('0')) for fill in self.fills), start=Decimal('0'))

    def get_age_seconds(self) -> float:
        """Get order age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary representation."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity),
            "price": str(self.price) if self.price else None,
            "stop_price": str(self.stop_price) if self.stop_price else None,
            "status": self.status.value,
            "filled_quantity": str(self.filled_quantity),
            "avg_fill_price": str(self.avg_fill_price) if self.avg_fill_price else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "broker_order_id": self.broker_order_id,
            "exchange_order_id": self.exchange_order_id,
            "fill_count": len(self.fills),
            "fill_rate": self.get_fill_rate(),
            "rejection_reason": self.rejection_reason,
            "event_count": len(self.event_history),
        }
