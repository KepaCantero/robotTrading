"""
Event Engine - Tomasini's event-driven architecture.

This module implements the event queue pattern from Tomasini's "Trading Systems":
- Event queue for sequential processing
- Event-driven order lifecycle management
- Priority queue for time-sensitive events
"""

from .tomasini_event_queue import (
    Event,
    EventHandler,
    EventPriority,
    EventType,
    OrderEventHandler,
    OrderFillHandler,
    OrderSubmitHandler,
    TomasiniEventQueue,
)

__all__ = [
    "Event",
    "EventHandler",
    "EventPriority",
    "EventType",
    "OrderEventHandler",
    "OrderFillHandler",
    "OrderSubmitHandler",
    "TomasiniEventQueue",
]
