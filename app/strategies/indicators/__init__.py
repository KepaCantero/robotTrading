"""
Technical Indicators for Algorithmic Trading Strategies.

This module provides technical indicators commonly used in quantitative
trading strategies, with a focus on Ernest Chan's recommended indicators.

Key Components:
- BollingerBands: Volatility-based mean reversion indicator
- (Additional indicators to be added)

Reference:
    "Algorithmic Trading" by Ernest P. Chan
    "Quantitative Trading" by Ernest P. Chan
"""

from .bollinger_bands import (
    BollingerBandsConfig,
    BollingerBandsIndicator,
    BollingerBandsSignal,
    calculate_bollinger_bands,
)

__all__ = [
    "BollingerBandsConfig",
    "BollingerBandsIndicator",
    "BollingerBandsSignal",
    "calculate_bollinger_bands",
]
