"""
API Module - Common utilities and exports
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

# Context variable for correlation ID tracking
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Audit logger instance
audit_logger = logging.getLogger("audit")


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set a correlation ID in context. Generates one if not provided."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _correlation_id.set(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear the correlation ID from context."""
    _correlation_id.set(None)


__all__ = [
    "audit_logger",
    "clear_correlation_id",
    "get_correlation_id",
    "set_correlation_id",
]
