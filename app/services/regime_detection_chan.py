from __future__ import annotations

"""
Ernest Chan - Quantitative Trading: Regime Detection Implementation

This module implements market regime detection methodologies as described in
Ernest Chan's "Quantitative Trading: How to Build Your Own Algorithmic Trading Business".

Key Concepts:
- Market regime switching (Bull/Bear/Neutral)
- Volatility regime detection (High/Low volatility periods)
- Trend-following vs Mean-reversion regimes
- Hidden Markov Models (HMM) for regime detection
- Regime-dependent strategy selection
- Regime transition probability estimation

Based on:
- Chan, E. P. (2013). Algorithmic Trading: Winning Strategies and Their Rationale.
- Hamilton, J. D. (1989). A new approach to the economic analysis of nonstationary time series.

Author: Algorithmic Trading System
Date: 2026-01-28
"""

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Optional: hmmlearn with fallback for regime detection
try:
    from hmmlearn import hmm as hmmlearn_module

    HMM_AVAILABLE = True
    logger.info("hmmlearn is available - using Hidden Markov Models for Chan's regime detection")
except ImportError:
    HMM_AVAILABLE = False
    logger.warning(
        "hmmlearn is not available. HMM-based regime detection will use fallback to GaussianMixture. "
        "For optimal results with Ernest Chan's regime detection methods, install hmmlearn: pip install hmmlearn"
    )
    # Import fallback
    from sklearn.mixture import GaussianMixture

    class HMMFallback:
        """
        Fallback adapter for hmmlearn using sklearn's GaussianMixture.

        Provides similar interface to hmmlearn.GaussianHMM for backward compatibility.
        This is a simplified version that doesn't capture temporal dynamics but provides
        clustering functionality for regime detection.
        """

        def __init__(
            self, n_components=2, covariance_type="full", n_iter=1000, random_state=None, **kwargs
        ):
            self.n_components = n_components
            self.covariance_type = covariance_type
            self.n_iter = n_iter
            self.random_state = random_state
            self.gmm = GaussianMixture(
                n_components=n_components,
                covariance_type=covariance_type,
                max_iter=n_iter,
                random_state=random_state,
                **kwargs,
            )
            self.means_ = None
            self.covars_ = None
            self.transmat_ = None

        def fit(self, X, lengths=None):
            """Fit the Gaussian Mixture Model."""
            self.gmm.fit(X)
            self.means_ = self.gmm.means_
            self.covars_ = self.gmm.covariances_
            # Create a simple transition matrix (stationary distribution)
            self.transmat_ = np.full(
                (self.n_components, self.n_components), 1.0 / self.n_components
            )
            return self

        def predict(self, X):
            """Predict component labels."""
            return self.gmm.predict(X)

        def score_samples(self, X):
            """Compute the weighted log probabilities for each sample."""
            return self.gmm.score_samples(X)

        def score(self, X, lengths=None):
            """Compute the log probability under the model."""
            return self.gmm.score(X)

    class HMMModule:
        """Namespace for fallback HMM implementation."""

        GaussianHMM = HMMFallback


class RegimeType(Enum):
    """Market regime types."""

    BULL = "bull"  # Rising prices, low volatility
    BEAR = "bear"  # Falling prices, high volatility
    NEUTRAL = "neutral"  # Sideways, moderate volatility
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"


@dataclass
class RegimeState:
    """Represents a detected regime state."""

    regime_type: RegimeType
    probability: float
    expected_return: float
    expected_volatility: float
    duration_days: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp | None = None


@dataclass
class RegimeTransition:
    """Represents a regime transition."""

    from_regime: RegimeType
    to_regime: RegimeType
    probability: float
    expected_duration_days: float


class MarketRegimeDetector:
    """
    Market Regime Detection using multiple methodologies.

    Implements various regime detection approaches:
    1. Trend-Volatility clustering (K-Means)
    2. Hidden Markov Models (HMM)
    3. Statistical threshold-based detection
    4. Momentum-based regime identification

    Usage:
        >>> detector = MarketRegimeDetector(n_regimes=3)
        >>> regimes = detector.detect_regimes(returns)
    """

    def __init__(
        self,
        n_regimes: int = 3,
        method: str = "hmm",
        lookback_window: int = 60,
    ):
        """
        Initialize Market Regime Detector.

        Args:
            n_regimes: Number of regimes to detect
            method: Detection method ('hmm', 'kmeans', 'threshold', 'momentum')
            lookback_window: Lookback window for feature calculation
        """
        self.n_regimes = n_regimes
        self.method = method
        self.lookback_window = lookback_window

        self.model: object | None = None
        self.scaler: StandardScaler | None = None
        self.regime_history: list[RegimeState] = []

        logger.info(f"MarketRegimeDetector initialized: n_regimes={n_regimes}, method={method}")

    def detect_regimes(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
        volume: pd.Series | None = None,
    ) -> pd.Series:
        """
        Detect market regimes from price/return data.

        Args:
            returns: Series of asset returns
            prices: Series of prices (optional, for trend analysis)
            volume: Series of volume (optional, for volume analysis)

        Returns:
            Series of regime labels with same index as returns
        """
        try:
            if len(returns) < self.lookback_window:
                raise ValueError(f"Insufficient data: {len(returns)} < {self.lookback_window}")

            if self.method == "hmm":
                return self._detect_hmm(returns, prices)
            elif self.method == "kmeans":
                return self._detect_kmeans(returns, prices)
            elif self.method == "threshold":
                return self._detect_threshold(returns, prices)
            elif self.method == "momentum":
                return self._detect_momentum(returns)
            else:
                raise ValueError(f"Unknown method: {self.method}")

        except (ValueError, TypeError) as e:
            logger.error(f"Regime detection failed: {e}")
            # Return neutral regime
            return pd.Series(RegimeType.NEUTRAL.value, index=returns.index)

    def _detect_hmm(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
    ) -> pd.Series:
        """
        Detect regimes using Hidden Markov Model.

        HMM assumes that observable returns are generated by a hidden
        state variable (regime) that follows a Markov process.

        Args:
            returns: Series of returns
            prices: Series of prices (optional)

        Returns:
            Series of regime labels
        """
        # Prepare features
        features = self._prepare_features(returns, prices)

        # Fit HMM
        model = hmmlearn_module.GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=1000,
            random_state=42,
        )

        model.fit(features)

        # Predict regimes
        hidden_states = model.predict(features)

        # Map regimes to labels based on mean return
        regime_mapping = self._map_regimes_to_labels(
            hidden_states, returns.values[self.lookback_window - 1 :]
        )

        # Create series
        regime_series = pd.Series(
            [regime_mapping[s] for s in hidden_states],
            index=returns.index[self.lookback_window - 1 :],
        )

        # Pad initial values
        full_series = pd.Series(
            [regime_series.iloc[0]] * (self.lookback_window - 1) + list(regime_series),
            index=returns.index,
        )

        # Store model
        self.model = model

        # Analyze regime transitions
        transition_matrix = model.transmat_
        self._analyze_regime_transitions(transition_matrix, regime_mapping)

        logger.info(f"HMM regime detection complete: {len(regime_mapping)} regimes identified")

        return full_series

    def _detect_kmeans(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
    ) -> pd.Series:
        """
        Detect regimes using K-Means clustering.

        Clusters periods based on volatility and trend characteristics.

        Args:
            returns: Series of returns
            prices: Series of prices (optional)

        Returns:
            Series of regime labels
        """
        # Prepare features
        features = self._prepare_features(returns, prices)

        # Standardize features
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features)

        # Fit K-Means
        model = KMeans(
            n_clusters=self.n_regimes,
            random_state=42,
            n_init=10,
        )

        regime_labels = model.fit_predict(features_scaled)

        # Map clusters to regime types
        regime_mapping = self._map_regimes_to_labels(
            regime_labels, returns.values[self.lookback_window - 1 :]
        )

        # Create series
        regime_series = pd.Series(
            [regime_mapping[label] for label in regime_labels],
            index=returns.index[self.lookback_window - 1 :],
        )

        # Pad initial values
        full_series = pd.Series(
            [regime_series.iloc[0]] * (self.lookback_window - 1) + list(regime_series),
            index=returns.index,
        )

        self.model = model

        logger.info("K-Means regime detection complete")

        return full_series

    def _detect_threshold(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
    ) -> pd.Series:
        """
        Detect regimes using statistical thresholds.

        Simple but effective method based on:
        - Return magnitude (bull/bear)
        - Volatility level (high/low vol)

        Args:
            returns: Series of returns
            prices: Series of prices (optional)

        Returns:
            Series of regime labels
        """
        # Calculate rolling metrics
        rolling_return = returns.rolling(self.lookback_window).mean()
        rolling_vol = returns.rolling(self.lookback_window).std()

        # Define thresholds (using historical percentiles)
        return_threshold_low = rolling_return.quantile(0.33)
        return_threshold_high = rolling_return.quantile(0.67)
        vol_threshold = rolling_vol.quantile(0.5)

        # Classify regimes
        regimes = []

        for ret, vol in zip(rolling_return, rolling_vol):
            if pd.isna(ret) or pd.isna(vol):
                regimes.append(RegimeType.NEUTRAL.value)
            elif vol > vol_threshold:
                if ret > 0:
                    regimes.append(RegimeType.BULL.value)
                else:
                    regimes.append(RegimeType.BEAR.value)
            else:
                if ret > return_threshold_high:
                    regimes.append(RegimeType.BULL.value)
                elif ret < return_threshold_low:
                    regimes.append(RegimeType.BEAR.value)
                else:
                    regimes.append(RegimeType.NEUTRAL.value)

        regime_series = pd.Series(regimes, index=returns.index)

        logger.info("Threshold-based regime detection complete")

        return regime_series

    def _detect_momentum(
        self,
        returns: pd.Series,
    ) -> pd.Series:
        """
        Detect regimes based on momentum characteristics.

        Identifies trend-following vs mean-reversion regimes based on:
        - Autocorrelation of returns
        - Momentum persistence

        Args:
            returns: Series of returns

        Returns:
            Series of regime labels
        """
        regimes = []

        for i in range(self.lookback_window, len(returns) + 1):
            window_returns = returns.iloc[i - self.lookback_window : i]

            # Calculate autocorrelation at lag 1
            autocorr = window_returns.autocorr(lag=1)

            # Calculate momentum
            momentum = window_returns.sum()

            # Classify
            if autocorr > 0.1:
                # Positive autocorr = trend-following
                if momentum > 0:
                    regimes.append(RegimeType.TREND_FOLLOWING.value)
                else:
                    regimes.append(RegimeType.BEAR.value)
            elif autocorr < -0.1:
                # Negative autocorr = mean-reversion
                regimes.append(RegimeType.MEAN_REVERSION.value)
            else:
                # Low autocorr = neutral
                regimes.append(RegimeType.NEUTRAL.value)

        # Pad initial values
        regimes = [RegimeType.NEUTRAL.value] * (self.lookback_window - 1) + regimes

        regime_series = pd.Series(regimes, index=returns.index)

        logger.info("Momentum-based regime detection complete")

        return regime_series

    def _prepare_features(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
    ) -> np.ndarray:
        """
        Prepare features for regime detection.

        Args:
            returns: Series of returns
            prices: Series of prices (optional)

        Returns:
            Feature matrix (n_samples, n_features)
        """
        features_list = []

        # Rolling volatility (annualized)
        rolling_vol = returns.rolling(self.lookback_window).std() * np.sqrt(252)
        features_list.append(rolling_vol)

        # Rolling return (annualized)
        rolling_ret = returns.rolling(self.lookback_window).mean() * 252
        features_list.append(rolling_ret)

        # Skewness
        rolling_skew = returns.rolling(self.lookback_window).skew()
        features_list.append(rolling_skew)

        # Kurtosis
        rolling_kurt = returns.rolling(self.lookback_window).kurt()
        features_list.append(rolling_kurt)

        if prices is not None:
            # Trend indicator (price momentum)
            price_momentum = prices.pct_change(self.lookback_window)
            features_list.append(price_momentum)

        # Combine features
        features = pd.concat(features_list, axis=1)

        # Remove NaN values
        features = features.dropna()

        return features.values

    def _map_regimes_to_labels(
        self,
        regime_labels: np.ndarray,
        returns: np.ndarray,
    ) -> dict[int, str]:
        """
        Map numeric regime labels to semantic labels.

        Args:
            regime_labels: Array of numeric regime labels
            returns: Returns for calculating regime characteristics

        Returns:
            Dict mapping numeric labels to regime types
        """
        unique_labels = np.unique(regime_labels)
        regime_characteristics = {}

        for label in unique_labels:
            mask = regime_labels == label
            regime_returns = returns[mask]

            regime_characteristics[label] = {
                "mean_return": float(np.mean(regime_returns)),
                "volatility": float(np.std(regime_returns)),
            }

        # Sort by mean return
        sorted_labels = sorted(regime_characteristics.items(), key=lambda x: x[1]["mean_return"])

        # Map to regime types
        if self.n_regimes == 3:
            # Simple 3-regime mapping
            regime_mapping = {
                sorted_labels[0][0]: RegimeType.BEAR.value,
                sorted_labels[1][0]: RegimeType.NEUTRAL.value,
                sorted_labels[2][0]: RegimeType.BULL.value,
            }
        else:
            # Map to general regime types
            regime_mapping = {}
            for i, (label, _chars) in enumerate(sorted_labels):
                if i == 0:
                    regime_mapping[label] = RegimeType.BEAR.value
                elif i == len(sorted_labels) - 1:
                    regime_mapping[label] = RegimeType.BULL.value
                else:
                    regime_mapping[label] = RegimeType.NEUTRAL.value

        return regime_mapping

    def _analyze_regime_transitions(
        self,
        transition_matrix: np.ndarray,
        regime_mapping: dict[int, str],
    ) -> list[RegimeTransition]:
        """
        Analyze regime transition probabilities.

        Args:
            transition_matrix: Transition probability matrix
            regime_mapping: Mapping of regime indices to labels

        Returns:
            List of RegimeTransition objects
        """
        transitions = []

        for i, row in enumerate(transition_matrix):
            for j, prob in enumerate(row):
                if prob > 0.01:  # Only include significant transitions
                    from_type = regime_mapping.get(i, RegimeType.NEUTRAL.value)
                    to_type = regime_mapping.get(j, RegimeType.NEUTRAL.value)

                    transitions.append(
                        RegimeTransition(
                            from_regime=RegimeType(from_type),
                            to_regime=RegimeType(to_type),
                            probability=float(prob),
                            expected_duration_days=(
                                1.0 / (1.0 - transition_matrix[i, i])
                                if transition_matrix[i, i] < 1
                                else 0
                            ),
                        )
                    )

        return transitions

    def get_current_regime(
        self,
        returns: pd.Series,
        prices: pd.Series | None = None,
    ) -> RegimeState:
        """
        Get the current market regime.

        Args:
            returns: Series of returns
            prices: Series of prices (optional)

        Returns:
            Current RegimeState
        """
        if len(returns) < self.lookback_window:
            raise ValueError("Insufficient data for regime detection")

        # Detect regimes
        regimes = self.detect_regimes(returns, prices)

        # Get most recent regime
        current_regime_label = regimes.iloc[-1]
        recent_returns = returns.iloc[-self.lookback_window :]

        return RegimeState(
            regime_type=RegimeType(current_regime_label),
            probability=1.0,  # Hard assignment
            expected_return=float(recent_returns.mean() * 252),
            expected_volatility=float(recent_returns.std() * np.sqrt(252)),
            duration_days=self.lookback_window,
            start_date=returns.index[-self.lookback_window],
        )

    def backtest_regime_aware_strategy(
        self,
        returns: pd.Series,
        regime_signals: pd.Series,
        bull_strategy_returns: pd.Series,
        bear_strategy_returns: pd.Series,
        neutral_strategy_returns: pd.Series,
    ) -> pd.Series:
        """
        Backtest a regime-aware switching strategy.

        Args:
            returns: Market returns
            regime_signals: Regime labels for each period
            bull_strategy_returns: Strategy returns in bull regime
            bear_strategy_returns: Strategy returns in bear regime
            neutral_strategy_returns: Strategy returns in neutral regime

        Returns:
            Combined strategy returns
        """
        # Initialize strategy returns
        combined_returns = pd.Series(0.0, index=returns.index)

        # Apply regime-specific returns
        for date, regime in regime_signals.items():
            if regime == RegimeType.BULL.value and date in bull_strategy_returns.index:
                combined_returns[date] = bull_strategy_returns[date]
            elif regime == RegimeType.BEAR.value and date in bear_strategy_returns.index:
                combined_returns[date] = bear_strategy_returns[date]
            elif regime == RegimeType.NEUTRAL.value and date in neutral_strategy_returns.index:
                combined_returns[date] = neutral_strategy_returns[date]

        return combined_returns


class VolatilityRegimeDetector:
    """
    Volatility Regime Detection.

    Specialized detector for identifying high vs low volatility regimes.
    Important for risk management and strategy selection.

    Usage:
        >>> detector = VolatilityRegimeDetector(n_regimes=2)
        >>> regimes = detector.detect_volatility_regimes(returns)
    """

    def __init__(
        self,
        n_regimes: int = 2,
        lookback_window: int = 20,
        method: str = "hmm",
    ):
        """
        Initialize Volatility Regime Detector.

        Args:
            n_regimes: Number of volatility regimes (typically 2: high/low)
            lookback_window: Lookback for volatility calculation
            method: Detection method
        """
        self.n_regimes = n_regimes
        self.lookback_window = lookback_window
        self.method = method

        self.model: object | None = None

        logger.info(f"VolatilityRegimeDetector initialized: n_regimes={n_regimes}")

    def detect_volatility_regimes(
        self,
        returns: pd.Series,
    ) -> pd.Series:
        """
        Detect volatility regimes.

        Args:
            returns: Series of returns

        Returns:
            Series of volatility regime labels ('high', 'low', 'medium')
        """
        # Calculate realized volatility
        realized_vol = returns.rolling(self.lookback_window).std() * np.sqrt(252)

        # Remove NaN values
        valid_vol = realized_vol.dropna()

        if self.method == "hmm":
            return self._detect_hmm_volatility(valid_vol, returns.index)
        elif self.method == "threshold":
            return self._detect_threshold_volatility(valid_vol, returns.index)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _detect_hmm_volatility(
        self,
        volatility: pd.Series,
        original_index: pd.Index,
    ) -> pd.Series:
        """Detect volatility regimes using HMM."""
        # Reshape for HMM
        vol_values = volatility.values.reshape(-1, 1)

        # Fit HMM
        model = hmmlearn_module.GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=1000,
            random_state=42,
        )

        model.fit(vol_values)
        self.model = model

        # Predict regimes
        states = model.predict(vol_values)

        # Map to high/low volatility
        regime_means = [model.means_[i][0] for i in range(self.n_regimes)]
        sorted_indices = np.argsort(regime_means)

        regime_mapping = {}
        if self.n_regimes == 2:
            regime_mapping[sorted_indices[0]] = "low"
            regime_mapping[sorted_indices[1]] = "high"
        elif self.n_regimes == 3:
            regime_mapping[sorted_indices[0]] = "low"
            regime_mapping[sorted_indices[1]] = "medium"
            regime_mapping[sorted_indices[2]] = "high"

        # Create series
        regime_series = pd.Series(
            [regime_mapping[s] for s in states],
            index=volatility.index,
        )

        # Reindex to original
        full_series = pd.Series("medium", index=original_index)
        full_series.update(regime_series)

        return full_series

    def _detect_threshold_volatility(
        self,
        volatility: pd.Series,
        original_index: pd.Index,
    ) -> pd.Series:
        """Detect volatility regimes using thresholds."""
        # Use percentiles
        low_threshold = volatility.quantile(0.33)
        high_threshold = volatility.quantile(0.67)

        regimes = []
        for vol in volatility:
            if vol <= low_threshold:
                regimes.append("low")
            elif vol >= high_threshold:
                regimes.append("high")
            else:
                regimes.append("medium")

        regime_series = pd.Series(regimes, index=volatility.index)

        # Reindex to original
        full_series = pd.Series("medium", index=original_index)
        full_series.update(regime_series)

        return full_series


def detect_market_regimes(
    returns: pd.Series,
    method: str = "hmm",
    n_regimes: int = 3,
    **kwargs,
) -> pd.Series:
    """
    High-level function for market regime detection.

    Args:
        returns: Series of returns
        method: Detection method
        n_regimes: Number of regimes
        **kwargs: Additional arguments

    Returns:
        Series of regime labels

    Example:
        >>> regimes = detect_market_regimes(returns, method='hmm', n_regimes=3)
        >>> print(regimes.tail())
    """
    detector = MarketRegimeDetector(n_regimes=n_regimes, method=method, **kwargs)
    return detector.detect_regimes(returns)


def get_regime_statistics(
    returns: pd.Series,
    regimes: pd.Series,
) -> pd.DataFrame:
    """
    Calculate statistics for each regime.

    Args:
        returns: Series of returns
        regimes: Series of regime labels

    Returns:
        DataFrame with regime statistics
    """
    stats_list = []

    for regime in regimes.unique():
        mask = regimes == regime
        regime_returns = returns[mask]

        stats_list.append(
            {
                "regime": regime,
                "periods": mask.sum(),
                "percentage": mask.mean() * 100,
                "mean_return": float(regime_returns.mean()),
                "volatility": float(regime_returns.std()),
                "sharpe": float(regime_returns.mean() / regime_returns.std() * np.sqrt(252)),
                "max_drawdown": float(_calculate_max_drawdown(regime_returns)),
            }
        )

    return pd.DataFrame(stats_list)


def _calculate_max_drawdown(returns: pd.Series) -> float:
    """Calculate maximum drawdown."""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


# =============================================================================
# GETTER FUNCTIONS FOR COMPLIANCE ENGINE INTEGRATION
# =============================================================================


def get_regime_detector(method: str = "hmm", n_regimes: int = 3, **kwargs):
    """
    Get a regime detector instance for use with the compliance engine.

    This function provides a factory interface for creating regime detectors
    that can be used by the ComplianceEngine for pre-trade analysis.

    Args:
        method: Detection method ('hmm', 'kmeans', 'db', 'threshold')
        n_regimes: Number of regimes to detect
        **kwargs: Additional arguments passed to the detector

    Returns:
        MarketRegimeDetector instance configured with the specified parameters

    Example:
        >>> detector = get_regime_detector(method='hmm', n_regimes=3)
        >>> regimes = detector.detect_regimes(returns)
        >>> print(f"Detected {len(regimes.unique())} regimes")
    """
    return MarketRegimeDetector(n_regimes=n_regimes, method=method, **kwargs)
