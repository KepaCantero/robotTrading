"""
Market regime detection module (FASE 5.3).

This module implements market regime detection using multiple methods including
trend analysis, volatility analysis, and Hidden Markov Models (optional).

Key Features:
- Bull/Bear/Neutral market classification
- Volatility regime detection (Low/Normal/High)
- Trend vs Range-bound market detection
- Regime transition probability matrix
- Expected duration calculation for each regime
- Regime-aware strategy recommendations

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "Expected Returns" - Antti Ilmanen
    - "Advances in Financial Machine Learning" - Marcos López de Prado
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import argrelextrema

from .models import (
    MarketRegime,
    RegimeConfig,
    RegimeTransitionMatrix,
    RegimeType,
    TrendRegime,
    VolatilityRegime,
)

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Detect market regimes using multiple indicators.

    This class identifies market regimes by analyzing trend, volatility,
    and market structure. It can detect bull/bear markets, volatility
    regimes, and trend vs range-bound conditions.

    Example:
        ```python
        detector = RegimeDetector(config)

        # Detect current regime
        current_regime = detector.detect_regime(
            prices=price_series,
            returns=return_series,
            as_of_date=date.today()
        )

        logger.debug(current_regime.description())

        # Get regime history
        history = detector.detect_regime_history(
            prices=price_series,
            returns=return_series
        )

        # Calculate transition probabilities
        transition_matrix = detector.calculate_transition_matrix(history)
        ```
    """

    def __init__(self, config: Optional[RegimeConfig] = None):
        """
        Initialize regime detector.

        Args:
            config: Regime detection configuration
        """
        self.config = config or RegimeConfig()

    def detect_regime(
        self,
        prices: pd.Series,
        returns: pd.Series,
        as_of_date: date,
    ) -> MarketRegime:
        """
        Detect current market regime.

        Regime classification:
        - Bull: Price > SMA(200) AND rising slope
        - Bear: Price < SMA(200) AND falling slope
        - Neutral: Between SMA(100) and SMA(200)

        Volatility:
        - Low: Vol < historical median × 0.8
        - Normal: Within 0.8-1.2× median
        - High: Vol > historical median × 1.2

        Args:
            prices: Price series
            returns: Return series
            as_of_date: Date as of which to detect regime

        Returns:
            MarketRegime with current regime information
        """
        # Detect market type (bull/bear/neutral)
        regime_type = self._detect_regime_type(prices, as_of_date)

        # Detect volatility regime
        volatility_regime = self._detect_volatility_regime(returns)

        # Detect trend regime
        trend_regime = self._detect_trend_regime(prices)

        # Calculate confidence
        confidence = self._calculate_confidence(
            prices, returns, regime_type, volatility_regime, trend_regime
        )

        # Calculate expected duration
        expected_duration = self._calculate_expected_duration(
            prices, regime_type, volatility_regime
        )

        # Get regime characteristics
        characteristics = self._get_regime_characteristics(
            prices, returns, regime_type, volatility_regime, trend_regime
        )

        return MarketRegime(
            regime_type=regime_type,
            volatility_regime=volatility_regime,
            trend_regime=trend_regime,
            confidence=confidence,
            start_date=as_of_date,
            expected_duration=expected_duration,
            characteristics=characteristics,
        )

    def detect_regime_history(
        self,
        prices: pd.Series,
        returns: pd.Series,
    ) -> List[MarketRegime]:
        """
        Detect regime history and transitions.

        Args:
            prices: Price series
            returns: Return series

        Returns:
            List of MarketRegime objects representing regime history
        """
        regimes = []

        # Use rolling window for regime detection
        window = self.config.lookback_period

        for i in range(window, len(prices), window // 2):
            window_prices = prices.iloc[i - window : i]
            window_returns = returns.iloc[i - window : i]

            as_of_date = (
                prices.index[i].date() if hasattr(prices.index[i], 'date') else prices.index[i]
            )

            try:
                regime = self.detect_regime(
                    prices=window_prices,
                    returns=window_returns,
                    as_of_date=as_of_date,
                )

                # Set end date
                if regimes:
                    regimes[-1].end_date = as_of_date

                regime.start_date = as_of_date
                regimes.append(regime)

            except Exception as e:
                logger.warning(f"Error detecting regime at {as_of_date}: {e}")
                continue

        return regimes

    def calculate_transition_matrix(
        self,
        regime_history: List[MarketRegime],
    ) -> RegimeTransitionMatrix:
        """
        Calculate regime transition probabilities.

        Returns matrix like:
                     bull   bear  neutral
        bull       0.85   0.05   0.10
        bear       0.10   0.80   0.10
        neutral    0.30   0.20   0.50

        Args:
            regime_history: List of historical regimes

        Returns:
            RegimeTransitionMatrix with transition probabilities
        """
        # Get unique regimes
        regimes = ["bull", "bear", "neutral"]

        # Initialize transition counts
        transitions = {r: {r: 0 for r in regimes} for r in regimes}

        # Count transitions
        for i in range(len(regime_history) - 1):
            from_regime = regime_history[i].regime_type.value
            to_regime = regime_history[i + 1].regime_type.value

            if from_regime in transitions and to_regime in transitions[from_regime]:
                transitions[from_regime][to_regime] += 1

        # Convert to probabilities
        matrix = {}
        for from_regime in regimes:
            total = sum(transitions[from_regime].values())
            if total > 0:
                matrix[from_regime] = {
                    to_regime: count / total
                    for to_regime, count in transitions[from_regime].items()
                }
            else:
                matrix[from_regime] = {to_regime: 0.0 for to_regime in regimes}

        # Calculate expected durations
        expected_durations = {}
        for regime in regimes:
            # Expected duration = 1 / (1 - P(regime | regime))
            stay_prob = matrix.get(regime, {}).get(regime, 0.5)
            if stay_prob < 1.0:
                expected_duration = 1.0 / (1.0 - stay_prob)
                expected_durations[regime] = expected_duration * 21  # Convert to trading days
            else:
                expected_durations[regime] = float("inf")

        return RegimeTransitionMatrix(
            matrix=matrix,
            regimes=regimes,
            expected_durations=expected_durations,
            last_update=datetime.utcnow(),
        )

    def _detect_regime_type(self, prices: pd.Series, as_of_date: date) -> RegimeType:
        """
        Detect market type (bull/bear/neutral).

        Args:
            prices: Price series
            as_of_date: Date for detection

        Returns:
            RegimeType
        """
        if len(prices) < self.config.sma_long:
            return RegimeType.NEUTRAL

        # Calculate SMAs
        sma_short = prices.rolling(window=self.config.sma_short).mean()
        sma_long = prices.rolling(window=self.config.sma_long).mean()

        current_price = float(prices.iloc[-1])
        current_sma_short = float(sma_short.iloc[-1])
        current_sma_long = float(sma_long.iloc[-1])

        # Calculate slope (trend)
        if len(prices) >= self.config.sma_short:
            recent_prices = prices.iloc[-self.config.sma_short :]
            x = np.arange(len(recent_prices))
            slope, _ = np.polyfit(x, recent_prices.values, 1)
            # Normalize slope by price
            slope = slope / current_price * 100  # Percentage change per period
        else:
            slope = 0

        # Classification
        if current_price > current_sma_long and slope > self.config.trend_threshold:
            return RegimeType.BULL
        elif current_price < current_sma_long and slope < -self.config.trend_threshold:
            return RegimeType.BEAR
        elif current_price > current_sma_short and current_price < current_sma_long:
            return RegimeType.NEUTRAL
        else:
            # Check if between short and long SMA
            if current_sma_short < current_price < current_sma_long:
                return RegimeType.NEUTRAL
            elif slope > 0:
                return RegimeType.BULL
            else:
                return RegimeType.BEAR

    def _detect_volatility_regime(self, returns: pd.Series) -> VolatilityRegime:
        """
        Detect volatility regime.

        Args:
            returns: Return series

        Returns:
            VolatilityRegime
        """
        if len(returns) < self.config.volatility_window:
            return VolatilityRegime.NORMAL

        # Calculate rolling volatility
        rolling_vol = returns.rolling(window=self.config.volatility_window).std()

        # Calculate historical median
        historical_median = rolling_vol.median()

        if pd.isna(historical_median) or historical_median == 0:
            return VolatilityRegime.NORMAL

        current_vol = float(rolling_vol.iloc[-1])

        # Classification
        threshold = self.config.volatility_threshold

        if current_vol < historical_median * (1 / threshold):
            return VolatilityRegime.LOW
        elif current_vol > historical_median * threshold:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.NORMAL

    def _detect_trend_regime(self, prices: pd.Series) -> TrendRegime:
        """
        Detect trend regime (trend/range/transition).

        Args:
            prices: Price series

        Returns:
            TrendRegime
        """
        if len(prices) < self.config.lookback_period:
            return TrendRegime.TRANSITION

        lookback_prices = prices.iloc[-self.config.lookback_period :]

        # Find local maxima and minima
        maxima_idx = argrelextrema(lookback_prices.values, np.greater, order=5)[0]
        minima_idx = argrelextrema(lookback_prices.values, np.less, order=5)[0]

        # Calculate trend strength
        if len(lookback_prices) >= 2:
            x = np.arange(len(lookback_prices))
            slope, intercept = np.polyfit(x, lookback_prices.values, 1)

            # Calculate R²
            y_pred = slope * x + intercept
            ss_res = np.sum((lookback_prices.values - y_pred) ** 2)
            ss_tot = np.sum((lookback_prices.values - np.mean(lookback_prices.values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        else:
            r_squared = 0
            slope = 0

        # Detect range-bound
        price_range = float(lookback_prices.max() - lookback_prices.min())
        price_mean = float(lookback_prices.mean())
        normalized_range = price_range / price_mean if price_mean > 0 else 0

        # Classification
        if r_squared > 0.7:  # Strong trend
            return TrendRegime.TREND
        elif normalized_range < 0.05:  # Tight range
            return TrendRegime.RANGE
        elif (
            abs(maxima_idx[0] - minima_idx[0])
            if len(maxima_idx) > 0 and len(minima_idx) > 0
            else 0 > len(lookback_prices) / 2
        ):
            # Clear peaks and valleys indicate range
            return TrendRegime.RANGE
        else:
            return TrendRegime.TRANSITION

    def _calculate_confidence(
        self,
        prices: pd.Series,
        returns: pd.Series,
        regime_type: RegimeType,
        volatility_regime: VolatilityRegime,
        trend_regime: TrendRegime,
    ) -> float:
        """
        Calculate confidence in regime detection.

        Args:
            prices: Price series
            returns: Return series
            regime_type: Detected regime type
            volatility_regime: Detected volatility regime
            trend_regime: Detected trend regime

        Returns:
            Confidence score (0-1)
        """
        confidence_factors = []

        # Factor 1: Data length
        if len(prices) >= self.config.sma_long * 2:
            confidence_factors.append(1.0)
        elif len(prices) >= self.config.sma_long:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)

        # Factor 2: Signal strength (price vs SMA)
        if len(prices) >= self.config.sma_long:
            sma_long = prices.rolling(window=self.config.sma_long).mean()
            current_price = float(prices.iloc[-1])
            current_sma = float(sma_long.iloc[-1])

            distance = abs(current_price - current_sma) / current_sma
            confidence_factors.append(min(distance * 10, 1.0))

        # Factor 3: Volatility clarity
        if len(returns) >= self.config.volatility_window * 2:
            rolling_vol = returns.rolling(window=self.config.volatility_window).std()
            vol_cv = float(rolling_vol.std() / rolling_vol.mean()) if rolling_vol.mean() > 0 else 0
            # Lower CV = more stable regime classification
            confidence_factors.append(max(1.0 - vol_cv, 0.5))

        # Return average confidence
        return np.mean(confidence_factors)

    def _calculate_expected_duration(
        self,
        prices: pd.Series,
        regime_type: RegimeType,
        volatility_regime: VolatilityRegime,
    ) -> Optional[int]:
        """
        Calculate expected duration of current regime in days.

        Args:
            prices: Price series
            regime_type: Current regime type
            volatility_regime: Current volatility regime

        Returns:
            Expected days until transition
        """
        # Historical averages (could be calibrated from data)
        base_durations = {
            RegimeType.BULL: 252 * 2,  # ~2 years
            RegimeType.BEAR: 252 * 1.5,  # ~1.5 years
            RegimeType.NEUTRAL: 252 * 0.5,  # ~6 months
        }

        vol_multipliers = {
            VolatilityRegime.LOW: 1.5,
            VolatilityRegime.NORMAL: 1.0,
            VolatilityRegime.HIGH: 0.5,
        }

        base_duration = base_durations.get(regime_type, 252)
        vol_multiplier = vol_multipliers.get(volatility_regime, 1.0)

        expected_duration = int(base_duration * vol_multiplier)

        return expected_duration

    def _get_regime_characteristics(
        self,
        prices: pd.Series,
        returns: pd.Series,
        regime_type: RegimeType,
        volatility_regime: VolatilityRegime,
        trend_regime: TrendRegime,
    ) -> Dict[str, Any]:
        """
        Get additional regime characteristics.

        Args:
            prices: Price series
            returns: Return series
            regime_type: Regime type
            volatility_regime: Volatility regime
            trend_regime: Trend regime

        Returns:
            Dictionary of characteristics
        """
        characteristics = {}

        # Current price level
        characteristics["current_price"] = float(prices.iloc[-1]) if len(prices) > 0 else None

        # Price vs SMAs
        if len(prices) >= self.config.sma_long:
            sma_short = prices.rolling(window=self.config.sma_short).mean()
            sma_long = prices.rolling(window=self.config.sma_long).mean()

            characteristics["price_vs_sma_short"] = float(
                (prices.iloc[-1] - sma_short.iloc[-1]) / sma_short.iloc[-1]
            )
            characteristics["price_vs_sma_long"] = float(
                (prices.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1]
            )

        # Volatility level
        if len(returns) >= self.config.volatility_window:
            characteristics["current_volatility"] = float(
                returns.iloc[-self.config.volatility_window :].std()
            )
            characteristics["volatility_percentile"] = float(
                returns.rolling(window=self.config.volatility_window).std().rank(pct=True).iloc[-1]
            )

        # Momentum
        if len(prices) >= 20:
            momentum_1m = float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)
            momentum_3m = (
                float((prices.iloc[-1] / prices.iloc[-63] - 1) * 100) if len(prices) >= 63 else None
            )
            characteristics["momentum_1m"] = momentum_1m
            characteristics["momentum_3m"] = momentum_3m

        # Drawdown from peak
        if len(prices) >= self.config.lookback_period:
            lookback_prices = prices.iloc[-self.config.lookback_period :]
            peak = lookback_prices.max()
            drawdown = float((prices.iloc[-1] / peak - 1) * 100)
            characteristics["drawdown_from_peak_pct"] = drawdown

        return characteristics

    def get_regime_aware_recommendation(self, regime: MarketRegime) -> List[str]:
        """
        Get strategy recommendations based on current regime.

        Args:
            regime: Current market regime

        Returns:
            List of strategy recommendations
        """
        recommendations = []

        # Bull market recommendations
        if regime.regime_type == RegimeType.BULL:
            if regime.trend_regime == TrendRegime.TREND:
                recommendations.extend(
                    [
                        "Strong bull trend detected.",
                        "Favorable for: Trend-following, Momentum strategies",
                        "Reduce: Mean-reversion, Short-selling strategies",
                        "Consider: Long-only equity exposure",
                    ]
                )
            else:
                recommendations.extend(
                    [
                        "Bull market with choppy price action.",
                        "Favorable for: Buy-the-dip, Swing trading",
                        "Caution on: Pure trend-following",
                    ]
                )

        # Bear market recommendations
        elif regime.regime_type == RegimeType.BEAR:
            recommendations.extend(
                [
                    "Bear market detected.",
                    "Consider: Reduce exposure, increase cash allocation",
                    "Favorable for: Short-selling (if permitted), Hedging strategies",
                    "Avoid: Buy-and-hold, Long-only momentum",
                ]
            )

        # Neutral market recommendations
        else:
            if regime.trend_regime == TrendRegime.RANGE:
                recommendations.extend(
                    [
                        "Range-bound market detected.",
                        "Favorable for: Mean-reversion, Oscillator-based strategies",
                        "Reduce: Trend-following strategies",
                        "Consider: Options income strategies (iron condors, etc.)",
                    ]
                )
            else:
                recommendations.extend(
                    [
                        "Transitional market phase.",
                        "Reduce position sizes until clearer trend emerges",
                        "Focus: Capital preservation",
                    ]
                )

        # Volatility-specific recommendations
        if regime.volatility_regime == VolatilityRegime.HIGH:
            recommendations.extend(
                [
                    "High volatility environment.",
                    "Reduce: Position sizes, leverage",
                    "Consider: Volatility-based position sizing",
                    "Opportunity: Elevated option premiums for income strategies",
                ]
            )
        elif regime.volatility_regime == VolatilityRegime.LOW:
            recommendations.extend(
                [
                    "Low volatility environment.",
                    "Caution: Options may be underpriced",
                    "Consider: Strategies that benefit from volatility expansion",
                ]
            )

        return recommendations


def detect_regime_from_data(
    prices: pd.Series,
    returns: Optional[pd.Series] = None,
    config: Optional[RegimeConfig] = None,
) -> MarketRegime:
    """
    Quick regime detection from price data.

    Args:
        prices: Price series with datetime index
        returns: Optional return series (calculated if not provided)
        config: Optional regime configuration

    Returns:
        Current market regime
    """
    if returns is None:
        returns = prices.pct_change().dropna()

    detector = RegimeDetector(config)

    as_of_date = prices.index[-1].date() if hasattr(prices.index[-1], 'date') else prices.index[-1]

    return detector.detect_regime(prices, returns, as_of_date)


def classify_market_state(
    prices: pd.Series,
    lookback: int = 50,
) -> str:
    """
    Simple market state classification.

    Args:
        prices: Price series
        lookback: Lookback period

    Returns:
        Market state string
    """
    if len(prices) < lookback:
        return "insufficient_data"

    recent_prices = prices.iloc[-lookback:]

    # Calculate returns
    total_return = float((recent_prices.iloc[-1] / recent_prices.iloc[0] - 1) * 100)

    # Calculate volatility
    returns = recent_prices.pct_change().dropna()
    volatility = float(returns.std() * 100)

    # Classify
    if total_return > 5:
        trend = "bull"
    elif total_return < -5:
        trend = "bear"
    else:
        trend = "neutral"

    if volatility > 2:
        vol_state = "high_vol"
    elif volatility < 1:
        vol_state = "low_vol"
    else:
        vol_state = "normal_vol"

    return f"{trend}_{vol_state}"
