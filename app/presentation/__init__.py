"""
Presentation Layer - API Controllers, Views, and DTOs

This layer handles:
- HTTP API endpoints
- WebSocket connections
- Request/Response DTOs
- Dashboard views

Dependencies: Can depend on Application and Domain layers
"""

from .controllers import *  # noqa: F401, F403
from .dto import *  # noqa: F401, F403

__all__ = ["controllers", "dto", "views"]
