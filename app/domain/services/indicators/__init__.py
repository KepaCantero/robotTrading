"""
Consolidated Technical Indicators Module

This module provides a unified interface for all technical indicators used
throughout the application. It consolidates implementations from:
- app/core/numba_accelerators.py
- app/domain/strategies/crypto_indicators.py
- app/domain/strategies/strategy.py

Usage:
    from app.domain.services.indicators import (
        TechnicalIndicators,
        get_indicator_calculator,
    )

    # Use pandas backend (default)
    indicators = get_indicator_calculator(backend='pandas')
    rsi = indicators.rsi(df['close'], period=14)

    # Use numba backend for high-frequency calculations
    indicators = get_indicator_calculator(backend='numba')
    rsi = indicators.rsi(prices_list, period=14)
"""

from app.domain.services.indicators.technical_indicators import (
    TechnicalIndicators,
    IndicatorResult,
)
from app.domain.services.indicators.factory import (
    get_indicator_calculator,
    get_available_backends,
    IndicatorBackend,
)

__all__ = [
    # Main classes
    "TechnicalIndicators",
    "IndicatorResult",
    # Factory functions
    "get_indicator_calculator",
    "get_available_backends",
    "IndicatorBackend",
]

# Version
__version__ = "1.0.0"
