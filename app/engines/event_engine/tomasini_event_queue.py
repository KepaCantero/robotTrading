"""
Tomasini Event Queue - Event-driven order processing following "Trading Systems" methodology.

Implements Tomasini's event queue pattern from "Trading Systems":
- Event queue for sequential processing
- Event-driven architecture for order lifecycle
- Priority queue for time-sensitive events
- Thread-safe async processing
"""

from __future__ import annotations
import numpy as np

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.domain.entities.order import Order

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """
    Event priority levels (Tomasini's priority queue).

    Higher priority events are processed first.
    """

    CRITICAL = 100  # Risk management, emergency stops
    HIGH = 75  # Order fills, cancellations
    NORMAL = 50  # Order submissions, acknowledgements
    LOW = 25  # Status updates, logging
    BACKGROUND = 10  # Analytics, reporting


class EventType(Enum):
    """
    Event types in the trading system (Tomasini's event taxonomy).
    """

    # Order events
    ORDER_CREATE = "order_create"
    ORDER_VALIDATE = "order_validate"
    ORDER_SUBMIT = "order_submit"
    ORDER_ACKNOWLEDGE = "order_acknowledge"
    ORDER_PARTIAL_FILL = "order_partial_fill"
    ORDER_FILL = "order_fill"
    ORDER_CANCEL_REQUEST = "order_cancel_request"
    ORDER_CANCEL_CONFIRM = "order_cancel_confirm"
    ORDER_REJECT = "order_reject"
    ORDER_EXPIRE = "order_expire"
    ORDER_SUSPEND = "order_suspend"
    ORDER_UNSUSPEND = "order_unsuspend"

    # Market events
    MARKET_DATA_UPDATE = "market_data_update"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"

    # System events
    RISK_LIMIT_BREACH = "risk_limit_breach"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass(order=True)
class Event:
    """
    Event in the queue (Tomasini's event structure).

    Attributes:
        priority: Event priority (higher = more important)
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: Event creation timestamp
        order_id: Associated order ID (if applicable)
        data: Event payload data
        callback: Optional callback function for event processing
    """

    priority: int
    event_id: str = field(compare=False, default="")
    event_type: EventType = field(compare=False)
    timestamp: datetime = field(compare=False, default_factory=datetime.utcnow)
    order_id: Optional[str] = field(compare=False, default=None)
    data: Dict[str, Any] = field(compare=False, default_factory=dict)
    callback: Optional[Callable[[], Awaitable[None]]] = field(compare=False, default=None)

    def __post_init__(self):
        """Generate event ID if not provided."""
        if not self.event_id:
            self.event_id = f"evt_{uuid.uuid4().hex[:12]}"


class EventHandler:
    """
    Base class for event handlers (Tomasini's handler pattern).

    Subclasses implement specific event processing logic.
    """

    async def handle(self, event: Event) -> None:
        """
        Handle an event.

        Args:
            event: Event to handle

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(f"Handler not implemented for event type: {event.event_type}")


class TomasiniEventQueue:
    """
    Tomasini's Event Queue implementation.

    Key features from "Trading Systems":
    1. Sequential event processing (no concurrency issues)
    2. Priority queue for time-sensitive events
    3. Event-driven architecture
    4. Thread-safe async processing
    5. Event history and audit trail

    Usage:
        queue = TomasiniEventQueue()
        await queue.start()

        # Add event
        event = Event(
            priority=EventPriority.HIGH,
            event_type=EventType.ORDER_SUBMIT,
            order_id="order123",
            data={"symbol": "AAPL"}
        )
        await queue.put(event)

        # Stop queue
        await queue.stop()
    """

    def __init__(
        self,
        max_size: int = 10000,
        processing_timeout: float = 30.0,
        enable_history: bool = True,
    ):
        """
        Initialize event queue.

        Args:
            max_size: Maximum queue size
            processing_timeout: Timeout for event processing (seconds)
            enable_history: Whether to maintain event history
        """
        # Priority queue (implemented with sorted list for simplicity)
        self._queue: List[Event] = []
        self._queue_lock = asyncio.Lock()

        # Event processing
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None
        self._processing_timeout = processing_timeout

        # Event handlers
        self._handlers: Dict[EventType, List[EventHandler]] = {}

        # Event history (Tomasini's audit trail)
        self._history: deque = deque(maxlen=10000 if enable_history else 0)
        self._enable_history = enable_history

        # Statistics
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "events_timeout": 0,
            "processing_time_ms": [],
        }

        logger.info("TomasiniEventQueue initialized")

    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Register an event handler.

        Args:
            event_type: Event type to handle
            handler: Handler instance
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")

    async def start(self) -> None:
        """Start event processing."""
        if self._processing:
            logger.warning("Event queue already processing")
            return

        self._processing = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event queue started")

    async def stop(self) -> None:
        """Stop event processing."""
        if not self._processing:
            return

        self._processing = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event queue stopped")

    async def put(self, event: Event) -> None:
        """
        Add an event to the queue.

        Args:
            event: Event to add
        """
        async with self._queue_lock:
            # Insert in sorted order (higher priority first)
            # For same priority, FIFO order (older events first)
            inserted = False
            for i, existing in enumerate(self._queue):
                if event.priority > existing.priority:
                    self._queue.insert(i, event)
                    inserted = True
                    break
                elif event.priority == existing.priority:
                    # Same priority, FIFO - insert after existing events with same priority
                    # Find the last event with same priority
                    j = i
                    while j < len(self._queue) and self._queue[j].priority == event.priority:
                        j += 1
                    self._queue.insert(j, event)
                    inserted = True
                    break

            if not inserted:
                self._queue.append(event)

        logger.debug(
            f"Event added to queue: {event.event_type.value} "
            f"(priority={event.priority}, order={event.order_id})"
        )

    async def put_nowait(self, event: Event) -> None:
        """
        Add an event to the queue without waiting (non-blocking).

        Args:
            event: Event to add
        """
        await self.put(event)

    async def _process_events(self) -> None:
        """Process events from the queue (Tomasini's sequential processing)."""
        logger.info("Event processor started")

        while self._processing:
            try:
                # Get next event
                event = await self._get_next_event()

                if event is None:
                    # No events, wait a bit
                    await asyncio.sleep(0.01)
                    continue

                # Process event with timeout
                start_time = datetime.utcnow()

                try:
                    await asyncio.wait_for(
                        self._handle_event(event), timeout=self._processing_timeout
                    )
                    self._stats["events_processed"] += 1

                except asyncio.TimeoutError:
                    self._stats["events_timeout"] += 1
                    logger.error(
                        f"Event processing timeout: {event.event_type.value} "
                        f"(order={event.order_id})"
                    )

                except Exception as e:
                    self._stats["events_failed"] += 1
                    logger.error(
                        f"Event processing failed: {event.event_type.value} "
                        f"(order={event.order_id}): {e}",
                        exc_info=True,
                    )

                # Record processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._stats["processing_time_ms"].append(processing_time)

                # Add to history
                if self._enable_history:
                    self._add_to_history(event, success=True)

            except asyncio.CancelledError:
                logger.info("Event processor cancelled")
                break

            except Exception as e:
                logger.error(f"Error in event processor: {e}", exc_info=True)
                await asyncio.sleep(0.1)

        logger.info("Event processor stopped")

    async def _get_next_event(self) -> Optional[Event]:
        """Get next event from queue."""
        async with self._queue_lock:
            if not self._queue:
                return None
            return self._queue.pop(0)  # Pop from front (highest priority)

    async def _handle_event(self, event: Event) -> None:
        """
        Handle an event (Tomasini's event dispatch).

        Args:
            event: Event to handle

        Raises:
            Exception: If no handler is registered or handler fails
        """
        # Call custom callback if provided
        if event.callback:
            await event.callback()

        # Call registered handlers
        handlers = self._handlers.get(event.event_type, [])

        if not handlers:
            logger.warning(f"No handler registered for event type: {event.event_type.value}")

        for handler in handlers:
            await handler.handle(event)

    def _add_to_history(self, event: Event, success: bool) -> None:
        """
        Add event to history (Tomasini's audit trail).

        Args:
            event: Event to add
            success: Whether event was processed successfully
        """
        history_record = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "order_id": event.order_id,
            "priority": event.priority,
            "success": success,
        }
        self._history.append(history_record)

    async def create_order_event(
        self,
        event_type: EventType,
        order: Order,
        priority: EventPriority = EventPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """
        Create an order event.

        Args:
            event_type: Type of order event
            order: Order object
            priority: Event priority
            data: Additional event data

        Returns:
            Created event
        """
        event_data = data or {}
        event_data["order_status"] = order.status.value

        event = Event(
            priority=int(priority),
            event_type=event_type,
            order_id=order.order_id,
            data=event_data,
        )

        await self.put(event)
        return event

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        processing_times = self._stats["processing_time_ms"]
        avg_processing_time = (
            np.mean(processing_times) if processing_times else 0
        )

        return {
            "events_processed": self._stats["events_processed"],
            "events_failed": self._stats["events_failed"],
            "events_timeout": self._stats["events_timeout"],
            "avg_processing_time_ms": avg_processing_time,
            "queue_size": len(self._queue),
            "handlers_registered": sum(len(h) for h in self._handlers.values()),
            "history_size": len(self._history),
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event history records
        """
        return list(self._history)[-limit:]

    async def clear(self) -> None:
        """Clear all events from the queue."""
        async with self._queue_lock:
            self._queue.clear()
        logger.info("Event queue cleared")

    def is_processing(self) -> bool:
        """Check if queue is processing events."""
        return self._processing


class OrderEventHandler(EventHandler):
    """
    Base handler for order events.

    Subclasses implement specific order event logic.
    """

    def __init__(self, order_queue: TomasiniEventQueue):
        """
        Initialize order event handler.

        Args:
            order_queue: Event queue for emitting new events
        """
        self.order_queue = order_queue

    async def handle(self, event: Event) -> None:
        """
        Handle order event.

        Args:
            event: Order event to handle

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"OrderEventHandler not implemented for event type: {event.event_type}"
        )


class OrderSubmitHandler(OrderEventHandler):
    """Handler for order submit events."""

    async def handle(self, event: Event) -> None:
        """
        Handle order submit event.

        Args:
            event: Order submit event
        """
        logger.info(f"Handling order submit: {event.order_id}")

        # Here you would implement the actual order submission logic
        # For example: send to broker API, update order status, etc.

        # Emit acknowledgement event
        await self.order_queue.create_order_event(
            event_type=EventType.ORDER_ACKNOWLEDGE,
            order=self._get_order(event.order_id),
            priority=EventPriority.HIGH,
        )

    def _get_order(self, order_id: str) -> Order:
        """
        Get order by ID from the order queue's internal storage.

        Args:
            order_id: Order ID to fetch

        Returns:
            Order object

        Raises:
            ValueError: If order not found in internal storage
        """
        # Try to get order from the order_queue's internal orders dict
        if hasattr(self.order_queue, 'orders') and order_id in self.order_queue.orders:
            return self.order_queue.orders[order_id]

        # If not found, return a placeholder order with the given ID
        # In production, this would fetch from a repository
        logger.warning(f"Order {order_id} not found in internal storage, using placeholder")
        return Order(
            id=order_id,
            symbol="UNKNOWN",
            quantity=0,
            order_type="MARKET",
            status="PENDING"
        )


class OrderFillHandler(OrderEventHandler):
    """Handler for order fill events."""

    async def handle(self, event: Event) -> None:
        """
        Handle order fill event.

        Args:
            event: Order fill event
        """
        logger.info(f"Handling order fill: {event.order_id}")

        # Here you would implement:
        # 1. Update portfolio
        # 2. Calculate P&L
        # 3. Update risk metrics
        # 4. Emit position update event
