"""
Portfolio, Signal, and Asset models and interfaces.

This module exports the core portfolio, signal, and asset models and interfaces for the AlgoTrading system.
"""

from .portfolio import (
    AssetClass,
    Position,
    Portfolio,
    MarketRegime,
    MarketRegimeData,
    AssetUniverse,
    CircuitBreakerState,
    CircuitBreaker,
    PortfolioProvider,
    TradingClientInterface,
)

from .signal import (
    SignalType,
    SignalStrength,
    SignalSource,
    Signal,
    MarketData,
    SignalScorer,
    SignalPriorityQueue,
)

from .momentum import (
    MomentumSignal,
    MomentumType,
    Timeframe,
    TechnicalIndicators,
    MomentumStrategy,
    MomentumAnalysis,
    MomentumFilter,
)

__all__ = [
    # Portfolio models
    "AssetClass",
    "Position", 
    "Portfolio",
    "MarketRegime",
    "MarketRegimeData",
    "AssetUniverse",
    "CircuitBreakerState",
    "CircuitBreaker",
    "PortfolioProvider",
    "TradingClientInterface",
    # Signal models
    "SignalType",
    "SignalStrength", 
    "SignalSource",
    "Signal",
    "MarketData",
    "SignalScorer",
    "SignalPriorityQueue",
    # Momentum models
    "MomentumSignal",
    "MomentumType",
    "Timeframe",
    "TechnicalIndicators",
    "MomentumStrategy",
    "MomentumAnalysis",
    "MomentumFilter",
]
