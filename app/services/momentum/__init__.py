"""
Momentum analysis module.

This module provides SOLID-compliant momentum analysis services for trading.
Each component has a single responsibility and follows dependency inversion.

Components:
- protocols: Interface definitions for all momentum services
- indicators: Technical indicator calculators (separate concerns)
- analyzer: Core momentum analysis logic
- signal_generator: Trading signal generation
- strategy_manager: Strategy lifecycle management
- storage: Analysis persistence layer
- orchestrator: Service orchestration and coordination
"""

from app.services.momentum.orchestrator import get_momentum_analysis_service
from app.services.momentum.protocols import (
    IndicatorCalculator,
    MomentumAnalyzer,
    SignalGenerator,
    StorageBackend,
    StrategyManager,
)

__all__ = [
    "get_momentum_analysis_service",
    "IndicatorCalculator",
    "MomentumAnalyzer",
    "SignalGenerator",
    "StrategyManager",
    "StorageBackend",
]
