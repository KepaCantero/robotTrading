"""
Database models for position monitoring and other features.

This module re-exports all models from the parent models.py module
to maintain backward compatibility with existing imports.

REFACTORED: Uses TYPE_CHECKING and lazy imports to avoid circular dependencies.
Instead of dynamic importlib, we use deferred imports in functions.
"""

from __future__ import annotations

from datetime import datetime

from typing import TYPE_CHECKING, Protocol, runtime_checkable

# Use TYPE_CHECKING for type hints only
if TYPE_CHECKING:
    # These imports are only for static type checking
    from sqlalchemy.orm import DeclarativeBase as DeclarativeBase


# Define protocols for type hints without importing the actual models
@runtime_checkable
class UserModelProtocol(Protocol):
    """Protocol for User model to avoid circular imports."""

    id: int
    email: str
    username: str
    hashed_password: str
    is_active: bool


@runtime_checkable
class APIKeyModelProtocol(Protocol):
    """Protocol for APIKey model to avoid circular imports."""

    id: int
    key: str
    user_id: int
    is_active: bool


@runtime_checkable
class PortfolioModelProtocol(Protocol):
    """Protocol for Portfolio model to avoid circular imports."""

    id: int
    name: str
    user_id: int
    capital: float


@runtime_checkable
class AssetModelProtocol(Protocol):
    """Protocol for Asset model to avoid circular imports."""

    id: int
    symbol: str
    name: str
    asset_type: str


@runtime_checkable
class PositionModelProtocol(Protocol):
    """Protocol for Position model to avoid circular imports."""

    id: int
    portfolio_id: int
    asset_id: int
    quantity: float
    avg_price: float


@runtime_checkable
class TradeModelProtocol(Protocol):
    """Protocol for Trade model to avoid circular imports."""

    id: int
    portfolio_id: int
    asset_id: int
    quantity: float
    price: float
    side: str


@runtime_checkable
class MarketDataModelProtocol(Protocol):
    """Protocol for MarketData model to avoid circular imports."""

    id: int
    asset_id: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@runtime_checkable
class SignalModelProtocol(Protocol):
    """Protocol for Signal model to avoid circular imports."""

    id: int
    asset_id: int
    strategy_id: int
    signal_type: str
    timestamp: datetime


@runtime_checkable
class BacktestModelProtocol(Protocol):
    """Protocol for Backtest model to avoid circular imports."""

    id: int
    strategy_id: int
    start_date: datetime
    end_date: datetime
    initial_capital: float


@runtime_checkable
class RiskMetricsModelProtocol(Protocol):
    """Protocol for RiskMetrics model to avoid circular imports."""

    id: int
    portfolio_id: int
    timestamp: datetime
    var_value: float


@runtime_checkable
class SystemLogModelProtocol(Protocol):
    """Protocol for SystemLog model to avoid circular imports."""

    id: int
    timestamp: datetime
    level: str
    message: str
    module: str


@runtime_checkable
class PositionStateModelProtocol(Protocol):
    """Protocol for PositionState model to avoid circular imports."""

    id: int
    position_id: int
    timestamp: datetime
    state: str


# Lazy import cache
_model_cache: dict = {}


def _get_models_module():
    """
    Lazily import the models module to avoid circular dependencies.

    Returns:
        The models module with all model classes
    """
    if "models_module" not in _model_cache:
        # Import the parent models module
        # Using direct import with deferred loading pattern
        import sys
        from pathlib import Path

        models_file = Path(__file__).parent.parent / "models.py"

        # Check if already in sys.modules
        module_name = "app.infrastructure.persistence.database.models_direct"
        if module_name in sys.modules:
            _model_cache["models_module"] = sys.modules[module_name]
        else:
            # Try direct import first (preferred)
            try:
                from .. import models as models_module

                _model_cache["models_module"] = models_module
            except ImportError:
                # Fallback to importlib if needed
                import importlib.util

                spec = importlib.util.spec_from_file_location(module_name, models_file)
                if spec and spec.loader:
                    models_module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = models_module
                    spec.loader.exec_module(models_module)
                    _model_cache["models_module"] = models_module

    return _model_cache["models_module"]


def _get_model(model_name: str):
    """
    Get a specific model class by name using lazy loading.

    Args:
        model_name: Name of the model class to retrieve

    Returns:
        The requested model class
    """
    models_module = _get_models_module()
    return getattr(models_module, model_name)


# Lazy-loaded model properties
def __getattr__(name: str):
    """
    Lazy load model classes when accessed.

    This allows importing models without triggering circular imports:
        from app.infrastructure.persistence.database.models import User

    The actual import only happens when the model is first accessed.
    """
    model_names = {
        "User",
        "APIKey",
        "Portfolio",
        "Asset",
        "Position",
        "Trade",
        "MarketData",
        "Signal",
        "Backtest",
        "RiskMetrics",
        "SystemLog",
        "PositionState",
    }

    if name in model_names:
        return _get_model(name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For explicit exports and type hints
# Note: Model classes are dynamically loaded via __getattr__
# Only export the protocols which are defined at module level
__all__ = [
    # Protocols for type hints
    "UserModelProtocol",
    "APIKeyModelProtocol",
    "PortfolioModelProtocol",
    "AssetModelProtocol",
    "PositionModelProtocol",
    "TradeModelProtocol",
    "MarketDataModelProtocol",
    "SignalModelProtocol",
    "BacktestModelProtocol",
    "RiskMetricsModelProtocol",
    "SystemLogModelProtocol",
    "PositionStateModelProtocol",
    # Model classes (dynamically loaded)
    "PositionState",
]
