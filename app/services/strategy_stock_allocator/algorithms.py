"""
Stock Allocation Algorithms - Pure business logic for allocation

This module contains pure algorithms for stock classification,
scoring, and allocation without external dependencies.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np

# pylint: disable=relative-beyond-top-level
from .domain_models import StockCategory

logger = logging.getLogger(__name__)


class StockClassifier:
    """
    Classifies stocks based on statistical properties.

    Uses Hurst exponent, ADF test, and half-life to categorize
    stocks as trending, mean-reverting, or random walk.
    """

    def __init__(
        self,
        hurst_threshold: float = 0.5,
        half_life_threshold: float = 20.0,
        adf_confidence: float = 0.05,
    ):
        """
        Initialize classifier.

        Args:
            hurst_threshold: Hurst exponent threshold for trend detection
            half_life_threshold: Maximum half-life for mean reversion
            adf_confidence: Confidence level for ADF test
        """
        self.hurst_threshold = hurst_threshold
        self.half_life_threshold = half_life_threshold
        self.adf_confidence = adf_confidence

    def classify(
        self,
        hurst_long: Optional[float],
        hurst_short: Optional[float],
        half_life: Optional[float],
        adf_pvalue: Optional[float],
    ) -> StockCategory:
        """
        Classify a stock based on statistical metrics.

        Args:
            hurst_long: Long-term Hurst exponent
            hurst_short: Short-term Hurst exponent
            half_life: Mean reversion half-life
            adf_pvalue: ADF test p-value

        Returns:
            Stock category
        """
        # Check for trend (H > 0.5)
        if hurst_long and hurst_long > self.hurst_threshold:
            return StockCategory.TRENDING

        # Check for mean reversion
        # Criteria: H < 0.5, low half-life, significant ADF test
        if (
            hurst_short
            and hurst_short < self.hurst_threshold
            and half_life
            and half_life < self.half_life_threshold
        ):
            if adf_pvalue and adf_pvalue < self.adf_confidence:
                return StockCategory.MEAN_REVERTING

        # Default to random walk
        return StockCategory.RANDOM_WALK


class MomentumScorer:
    """
    Scores stocks for momentum trading strategies.

    Uses multiple factors to calculate a composite momentum score.
    """

    def __init__(
        self,
        lookback_periods: List[int] = None,
        volatility_weight: Decimal = Decimal('0.3'),
        trend_weight: Decimal = Decimal('0.5'),
        volume_weight: Decimal = Decimal('0.2'),
    ):
        """
        Initialize momentum scorer.

        Args:
            lookback_periods: Lookback periods for momentum calculation
            volatility_weight: Weight for volatility component
            trend_weight: Weight for trend component
            volume_weight: Weight for volume component
        """
        self.lookback_periods = lookback_periods or [20, 60, 120]
        self.volatility_weight = volatility_weight
        self.trend_weight = trend_weight
        self.volume_weight = volume_weight

    def score(
        self,
        returns: np.ndarray,
        volumes: Optional[np.ndarray] = None,
    ) -> Decimal:
        """
        Calculate momentum score for a stock.

        Args:
            returns: Array of returns
            volumes: Array of volumes (optional)

        Returns:
            Momentum score (higher is better)
        """
        if len(returns) < max(self.lookback_periods):
            return Decimal('0')

        score = Decimal('0')

        # Trend component (cumulative returns)
        trend_score = Decimal('0')
        for period in self.lookback_periods:
            if len(returns) >= period:
                period_return = Decimal(str(returns[-period:].sum()))
                trend_score += period_return

        score += trend_score * self.trend_weight

        # Volatility component (lower volatility is better for momentum)
        if len(returns) >= 20:
            volatility = Decimal(str(np.std(returns[-20:])))
            # Normalize: lower volatility = higher score
            vol_score = Decimal('1') / (Decimal('1') + volatility)
            score += vol_score * self.volatility_weight

        # Volume component (volume trend)
        if volumes is not None and len(volumes) >= 20:
            recent_volume = Decimal(str(volumes[-20:].mean()))
            historical_volume = Decimal(str(volumes[:-20].mean()))
            if historical_volume > 0:
                volume_ratio = recent_volume / historical_volume
                # Higher volume trend = higher score
                vol_trend_score = min(volume_ratio, Decimal('2')) / Decimal('2')
                score += vol_trend_score * self.volume_weight

        return score


class MeanReversionScorer:
    """
    Scores stocks for mean reversion trading strategies.

    Identifies stocks likely to revert to their mean.
    """

    def __init__(
        self,
        half_life_weight: Decimal = Decimal('0.4'),
        deviation_weight: Decimal = Decimal('0.4'),
        volatility_weight: Decimal = Decimal('0.2'),
    ):
        """
        Initialize mean reversion scorer.

        Args:
            half_life_weight: Weight for half-life component
            deviation_weight: Weight for deviation component
            volatility_weight: Weight for volatility component
        """
        self.half_life_weight = half_life_weight
        self.deviation_weight = deviation_weight
        self.volatility_weight = volatility_weight

    def score(
        self,
        price: np.ndarray,
        half_life: Optional[float] = None,
    ) -> Decimal:
        """
        Calculate mean reversion score for a stock.

        Args:
            price: Array of prices
            half_life: Mean reversion half-life (optional)

        Returns:
            Mean reversion score (higher is better)
        """
        if len(price) < 20:
            return Decimal('0')

        score = Decimal('0')

        # Current deviation from mean
        current_price = Decimal(str(price[-1]))
        mean_price = Decimal(str(price[-20:].mean()))
        std_price = Decimal(str(price[-20:].std()))

        if std_price > 0:
            z_score = abs(current_price - mean_price) / std_price
            # Higher deviation = higher score (trade the reversion)
            deviation_score = min(z_score, Decimal('3')) / Decimal('3')
            score += deviation_score * self.deviation_weight

        # Half-life component (shorter half-life = higher score)
        if half_life:
            half_life_dec = Decimal(str(half_life))
            # Normalize: shorter half-life = higher score
            hl_score = Decimal('1') / (Decimal('1') + half_life_dec / Decimal('10'))
            score += hl_score * self.half_life_weight

        # Volatility component (moderate volatility is best)
        volatility = Decimal(str(np.std(np.diff(np.log(price[-20:])))))
        # Too low volatility = no opportunity, too high = risky
        if volatility < Decimal('0.01'):
            vol_score = volatility / Decimal('0.01')
        elif volatility > Decimal('0.05'):
            vol_score = Decimal('1') - (volatility - Decimal('0.05')) / Decimal('0.05')
            vol_score = max(vol_score, Decimal('0'))
        else:
            vol_score = Decimal('1')
        score += vol_score * self.volatility_weight

        return score


class PairsTradingScorer:
    """
    Scores stock pairs for pairs trading strategies.

    Identifies cointegrated pairs with suitable properties.
    """

    def __init__(
        self,
        cointegration_threshold: float = 0.05,
        min_correlation: float = 0.7,
        max_half_life: float = 30.0,
    ):
        """
        Initialize pairs trading scorer.

        Args:
            cointegration_threshold: Max p-value for cointegration test
            min_correlation: Minimum correlation for pair
            max_half_life: Maximum acceptable half-life
        """
        self.cointegration_threshold = cointegration_threshold
        self.min_correlation = min_correlation
        self.max_half_life = max_half_life

    def score_pair(
        self,
        price1: np.ndarray,
        price2: np.ndarray,
        cointegration_pvalue: float,
        correlation: float,
        half_life: Optional[float] = None,
    ) -> Tuple[Decimal, str]:
        """
        Score a trading pair.

        Args:
            price1: Price series for first stock
            price2: Price series for second stock
            cointegration_pvalue: P-value from cointegration test
            correlation: Correlation between stocks
            half_life: Half-life of spread (optional)

        Returns:
            Tuple of (score, decision_log)
        """
        decision_log_parts = []
        score = Decimal('0')

        # Check cointegration
        if cointegration_pvalue > self.cointegration_threshold:
            decision_log_parts.append(f"Failed cointegration test (p={cointegration_pvalue:.4f})")
            return Decimal('0'), "; ".join(decision_log_parts)

        decision_log_parts.append(f"Passed cointegration test (p={cointegration_pvalue:.4f})")

        # Check correlation
        if correlation < self.min_correlation:
            decision_log_parts.append(f"Low correlation (r={correlation:.2f})")
            return Decimal('0'), "; ".join(decision_log_parts)

        decision_log_parts.append(f"Good correlation (r={correlation:.2f})")

        # Score based on cointegration strength
        cointegration_score = Decimal(str(1 - cointegration_pvalue))
        score += cointegration_score * Decimal('0.5')

        # Score based on correlation
        correlation_score = Decimal(str(correlation))
        score += correlation_score * Decimal('0.3')

        # Score based on half-life
        if half_life:
            if half_life > self.max_half_life:
                decision_log_parts.append(f"Half-life too long ({half_life:.1f} days)")
                return Decimal('0'), "; ".join(decision_log_parts)

            half_life_dec = Decimal(str(half_life))
            hl_score = Decimal('1') / (Decimal('1') + half_life_dec / Decimal('10'))
            score += hl_score * Decimal('0.2')
            decision_log_parts.append(f"Good half-life ({half_life:.1f} days)")

        return score, "; ".join(decision_log_parts)
