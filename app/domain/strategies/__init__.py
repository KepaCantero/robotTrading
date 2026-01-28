"""
Trading Strategies Domain Module

This module contains domain services for trading strategies
following academic research and best practices.
"""

from .cross_sectional_momentum import (
    CrossSectionalMomentum,
    MomentumAsset,
    MomentumPortfolio,
    MomentumSignal,
    MomentumMetrics,
)
from .time_series_momentum import (
    TimeSeriesMomentum,
    TimeSeriesSignal,
    TrendState,
)
from .fama_french_factors import (
    FamaFrenchModel,
    FactorReturns,
    FactorLoadings,
    FactorModelResult,
    FactorTiming,
)
from .statistical_arbitrage import (
    StatisticalArbitrage,
    ZScoreSignal,
    BollingerBandSignal,
    MeanReversionMetrics,
    ReversionState,
)
from .pairs_trading import (
    PairsTrading,
    TradingPair,
    PairPosition,
    CointegrationResult,
    PairSignal,
)
from .dividend_investing import (
    DividendInvesting,
    DividendMetrics,
    DividendPortfolio,
    DividendSignal,
)
from .quality_screen import (
    QualityInvesting,
    QualityMetrics,
    QualityPortfolio,
    QualitySignal,
)
from .low_volatility_anomaly import (
    LowVolatilityAnomaly,
    VolatilityMetrics,
    LowVolatilityPortfolio,
    VolatilityCategory,
)
from .covered_call import (
    CoveredCallStrategy,
    CoveredCallPosition,
    CoveredCallPortfolio,
    OptionData,
    CallSignal,
)

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
