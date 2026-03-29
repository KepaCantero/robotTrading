"""
Strategy Stock Allocation Module

A refactored, SOLID-compliant module for stock allocation across trading strategies.
This module provides a clean separation of concerns with dedicated classes for:

- Stock filtering and validation
- Statistical calculations (Hurst, half-life, stationarity)
- Market regime classification
- Strategy scoring (momentum, mean reversion, pairs trading)
- Capital allocation (ERC/Risk Parity)
- Validation and output generation

Main orchestrator: StrategyStockAllocator
"""

from __future__ import annotations

from .allocators import ERCCapitalAllocator
from .calculators import HalfLifeCalculator, HurstCalculator, StationarityTester
from .classifiers import RegimeClassifier
from .filters import StockFilter
from .orchestrator import StrategyStockAllocator
from .output import OutputGenerator
from .protocols import AllocatorProtocol, CalculatorProtocol, ScorerProtocol, StockFilterProtocol
from .scorers import MeanReversionScorer, MomentumScorer, PairsTradingScorer, WCMScoreCalculator
from .validators import AllocationValidator

__all__ = [
    # Validators
    "AllocationValidator",
    "AllocatorProtocol",
    "CalculatorProtocol",
    # Allocators
    "ERCCapitalAllocator",
    "HalfLifeCalculator",
    # Calculators
    "HurstCalculator",
    "MeanReversionScorer",
    # Scorers
    "MomentumScorer",
    # Output
    "OutputGenerator",
    "PairsTradingScorer",
    # Classifiers
    "RegimeClassifier",
    "ScorerProtocol",
    "StationarityTester",
    # Filters
    "StockFilter",
    # Protocols
    "StockFilterProtocol",
    # Main orchestrator
    "StrategyStockAllocator",
    "WCMScoreCalculator",
]
