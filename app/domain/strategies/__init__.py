"""
Trading Strategies Domain Module

This module contains domain services for trading strategies
following academic research and best practices.
"""

from .covered_call import (
    CallSignal,
    CoveredCallPortfolio,
    CoveredCallPosition,
    CoveredCallStrategy,
    OptionData,
)
from .cross_sectional_momentum import (
    CrossSectionalMomentum,
    MomentumAsset,
    MomentumMetrics,
    MomentumPortfolio,
    MomentumSignal,
)
from .dividend_investing import (
    DividendInvesting,
    DividendMetrics,
    DividendPortfolio,
    DividendSignal,
)
from .fama_french_factors import (
    FactorLoadings,
    FactorModelResult,
    FactorReturns,
    FactorTiming,
    FamaFrenchModel,
)
from .low_volatility_anomaly import (
    LowVolatilityAnomaly,
    LowVolatilityPortfolio,
    VolatilityCategory,
    VolatilityMetrics,
)
from .pairs_trading import CointegrationResult, PairPosition, PairSignal, PairsTrading, TradingPair
from .quality_screen import QualityInvesting, QualityMetrics, QualityPortfolio, QualitySignal
from .statistical_arbitrage import (
    BollingerBandSignal,
    MeanReversionMetrics,
    ReversionState,
    StatisticalArbitrage,
    ZScoreSignal,
)
from .time_series_momentum import TimeSeriesMomentum, TimeSeriesSignal, TrendState

__all__ = [
    # Cross-sectional momentum
    "CrossSectionalMomentum",
    "MomentumAsset",
    "MomentumPortfolio",
    "MomentumSignal",
    "MomentumMetrics",
    # Time-series momentum
    "TimeSeriesMomentum",
    "TimeSeriesSignal",
    "TrendState",
    # Fama-French factors
    "FamaFrenchModel",
    "FactorReturns",
    "FactorLoadings",
    "FactorModelResult",
    "FactorTiming",
    # Statistical arbitrage / mean reversion
    "StatisticalArbitrage",
    "ZScoreSignal",
    "BollingerBandSignal",
    "MeanReversionMetrics",
    "ReversionState",
    # Pairs trading
    "PairsTrading",
    "TradingPair",
    "PairPosition",
    "CointegrationResult",
    "PairSignal",
    # Dividend investing
    "DividendInvesting",
    "DividendMetrics",
    "DividendPortfolio",
    "DividendSignal",
    # Quality investing
    "QualityInvesting",
    "QualityMetrics",
    "QualityPortfolio",
    "QualitySignal",
    # Low volatility anomaly
    "LowVolatilityAnomaly",
    "VolatilityMetrics",
    "LowVolatilityPortfolio",
    "VolatilityCategory",
    # Covered call
    "CoveredCallStrategy",
    "CoveredCallPosition",
    "CoveredCallPortfolio",
    "OptionData",
    "CallSignal",
]
