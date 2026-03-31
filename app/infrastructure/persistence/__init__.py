"""
Infrastructure Persistence - Repository implementations.

This package contains concrete implementations of repository interfaces
defined in the domain layer.
"""

from app.infrastructure.persistence.database import Base

__all__ = [
    "Base",
]
