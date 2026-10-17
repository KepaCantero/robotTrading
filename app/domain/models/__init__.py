"""
Portfolio, Signal, and Asset models and interfaces.

This module exports the core portfolio, signal, and asset models and interfaces for the AlgoTrading system.
"""

from __future__ import annotations

# Optional imports - pydantic is a required dependency for momentum models
try:
    from .momentum import (
        MomentumAnalysis,
        MomentumFilter,
        MomentumSignal,
        MomentumStrategy,
        MomentumType,
        TechnicalIndicators,
        Timeframe,
    )

    MOMENTUM_AVAILABLE = True
except ImportError:
    # pydantic not available - momentum models will not be available
    MOMENTUM_AVAILABLE = False

_OPTIONAL_MOMENTUM_NAMES = frozenset(
    {
        "MomentumAnalysis",
        "MomentumFilter",
        "MomentumSignal",
        "MomentumStrategy",
        "MomentumType",
        "TechnicalIndicators",
        "Timeframe",
    }
)


def __getattr__(name: str) -> object:
    """Resolve optional momentum re-exports when pydantic is unavailable (PEP 562)."""
    if name in _OPTIONAL_MOMENTUM_NAMES and not MOMENTUM_AVAILABLE:
        return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from .portfolio import (
    AssetClass,
    AssetUniverse,
    CircuitBreaker,
    CircuitBreakerState,
    MarketRegime,
    MarketRegimeData,
    Portfolio,
    PortfolioProvider,
    Position,
    TradingClientInterface,
)
from .signal import (
    MarketData,
    Signal,
    SignalPriorityQueue,
    SignalScorer,
    SignalSource,
    SignalStrength,
    SignalType,
)

# Portfolio models
__all__ = [
    "AssetClass",
    "AssetUniverse",
    "CircuitBreaker",
    "CircuitBreakerState",
    "MarketData",
    "MarketRegime",
    "MarketRegimeData",
    "MomentumAnalysis",
    "MomentumFilter",
    # Momentum models
    "MomentumSignal",
    "MomentumStrategy",
    "MomentumType",
    "Portfolio",
    "PortfolioProvider",
    "Position",
    "Signal",
    "SignalPriorityQueue",
    "SignalScorer",
    "SignalSource",
    "SignalStrength",
    # Signal models
    "SignalType",
    "TechnicalIndicators",
    "Timeframe",
    "TradingClientInterface",
]
