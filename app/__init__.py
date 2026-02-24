"""
AlgoTrading MVP - Algorithmic Trading System

A comprehensive algorithmic trading system built with Python 3.11+, FastAPI,
PostgreSQL, Redis, and Celery for high-performance trading operations.

Author: AlgoTrading MVP Team
Version: 1.0.0
License: MIT
"""

# Core application metadata
__version__ = "1.0.0"
__description__ = "Algorithmic Trading System with ML and Real-Time Analysis"

APP_NAME = "AlgoTrading MVP"
APP_VERSION = __version__
APP_DESCRIPTION = __description__

# Initialize DI container on import
# This ensures all dependencies are available throughout the application
from app.shared.config.di_config import initialize_container  # noqa: F401

_container = None


def get_di_container():
    """Get the global DI container instance."""
    global _container
    if _container is None:
        _container = initialize_container()
    return _container


__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_DESCRIPTION",
    "get_di_container",
]
