"""
Crypto Momentum Strategy Package

This package implements a momentum strategy optimized for cryptocurrency assets,
accounting for their unique characteristics:
- 24/7 trading (continuous market)
- High volatility
- Lower liquidity (especially in smaller cap tokens)
- Bitcoin correlation effects
- Social sentiment impact

Modules:
    models: Data models for crypto assets and strategy configuration
    crypto_screener: Screen crypto assets by liquidity, market cap, and listing
    crypto_indicators: Crypto-specific technical indicators
    crypto_portfolio: Portfolio construction for crypto assets
    crypto_momentum_strategy: Main momentum strategy implementation
"""

from .crypto_indicators import CryptoIndicators
from .crypto_momentum_strategy import CryptoMomentumStrategy
from .crypto_portfolio import CryptoPortfolioConstructor
from .crypto_screener import CryptoAsset, CryptoScreener
from .models import (
    CryptoAsset,
    CryptoMomentumConfig,
    CryptoMomentumScore,
    CryptoPortfolio,
    CryptoPosition,
    OnChainMetrics,
)

__all__ = [
    "CryptoMomentumStrategy",
    "CryptoAsset",
    "CryptoScreener",
    "CryptoIndicators",
    "CryptoPortfolioConstructor",
    "CryptoMomentumConfig",
    "CryptoMomentumScore",
    "CryptoPortfolio",
    "CryptoPosition",
    "OnChainMetrics",
]

__version__ = "1.0.0"
__author__ = "AlgoTrading Team"
