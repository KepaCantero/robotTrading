"""
Trading strategy recommender based on market regime.

This module implements the Single Responsibility Principle by focusing
solely on recommending trading strategies based on market regime
and Hurst exponent values.

Strategy mapping:
- H << 0.5: Strong mean reversion (use mean reversion strategies)
- H ≈ 0.5: Random walk (use neutral/market-making strategies)
- H >> 0.5: Strong trend (use trend following strategies)
"""

from __future__ import annotations

import logging

from app.services.hurst_analysis.models import MarketRegime, StrategyRecommendation

logger = logging.getLogger(__name__)


class StrategyRecommender:
    """
    Recommends trading strategies based on market regime.

    This class follows the Single Responsibility Principle - it only
    recommends strategies based on regime classification. It does not
    classify regimes, calculate Hurst exponents, or detect changes.

    Example:
        >>> recommender = StrategyRecommender()
        >>> strategy = recommender.recommend(MarketRegime.MEAN_REVERTING, 0.3)
        >>> print(strategy)  # StrategyRecommendation.MEAN_REVERSION
    """

    def __init__(self) -> None:
        """Initialize strategy recommender."""

    def recommend(self, regime: MarketRegime, hurst_exponent: float) -> StrategyRecommendation:
        """
        Recommend trading strategy based on regime and Hurst value.

        Strategy mapping:
        - MEAN_REVERTING: Use mean reversion strategies
                          (pairs trading, statistical arbitrage)
        - RANDOM_WALK: Use neutral strategies
                       (market making, arbitrage)
        - TRENDING: Use trend following strategies
                    (momentum, breakout strategies)

        Args:
            regime: Classified market regime
            hurst_exponent: Hurst exponent value (for future enhancements)

        Returns:
            StrategyRecommendation

        Example:
            >>> recommender = StrategyRecommender()
            >>> recommender.recommend(MarketRegime.MEAN_REVERTING, 0.3)
            StrategyRecommendation.MEAN_REVERSION
            >>> recommender.recommend(MarketRegime.TRENDING, 0.7)
            StrategyRecommendation.TREND_FOLLOWING
            >>> recommender.recommend(MarketRegime.RANDOM_WALK, 0.5)
            StrategyRecommendation.NEUTRAL
        """
        if regime == MarketRegime.MEAN_REVERTING:
            return StrategyRecommendation.MEAN_REVERSION
        elif regime == MarketRegime.TRENDING:
            return StrategyRecommendation.TREND_FOLLOWING
        else:
            return StrategyRecommendation.NEUTRAL
