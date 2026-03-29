"""
Regime Detection & Analysis - Market regime identification and performance analysis.

Provides:
- K-Means regime detection (Bull/Neutral/Bear)
- Regime transition analysis and probabilities
- Performance metrics by regime
- Walk-forward robustness testing
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class RegimeAnalyzer:
    """
    Detect and analyze market regimes based on volatility and trend.

    Uses K-Means clustering on rolling volatility and returns to identify
    market regimes (Bull/Neutral/Bear market conditions).
    """

    def __init__(self, n_regimes: int = 3, window: int = 20, random_state: int = 42):
        """
        Initialize RegimeAnalyzer.

        Args:
            n_regimes: Number of regimes to detect (default: 3 for Bull/Neutral/Bear)
            window: Rolling window for volatility/trend calculation (default: 20 days)
            random_state: Random state for KMeans reproducibility
        """
        self.n_regimes = n_regimes
        self.window = window
        self.random_state = random_state
        self.kmeans_model: Optional[KMeans] = None
        self.scaler: Optional[StandardScaler] = None
        self.regime_labels: Optional[pd.Series] = None

        logger.info(
            f"RegimeAnalyzer initialized: n_regimes={n_regimes}, window={window}, random_state={random_state}"
        )

    def detect_regimes(self, returns: pd.Series) -> pd.Series:
        """
        Detect market regimes using K-Means clustering.

        Analyzes rolling volatility and trend (mean return) to identify regimes.

        Args:
            returns: Series of daily returns

        Returns:
            Series with regime labels (0, 1, 2, ...) with same index as returns
        """
        if len(returns) < self.window:
            logger.warning(f"Not enough data ({len(returns)}) for {self.window}-day window")
            return pd.Series([0] * len(returns), index=returns.index)

        try:
            # Get trading days from config
            annual_trading_days = get_config().backtesting.annual_trading_days

            # Calculate rolling volatility (annualized)
            rolling_vol = returns.rolling(self.window).std() * np.sqrt(annual_trading_days)

            # Calculate rolling return (annualized)
            rolling_ret = returns.rolling(self.window).mean() * annual_trading_days

            # Create feature matrix
            features = np.column_stack([rolling_vol.values, rolling_ret.values])

            # Handle NaN values (first window rows)
            valid_idx = ~np.isnan(features).any(axis=1)
            features_valid = features[valid_idx]

            if len(features_valid) < self.n_regimes:
                logger.warning(
                    f"Not enough valid data points ({len(features_valid)}) for {self.n_regimes} regimes"
                )
                return pd.Series([0] * len(returns), index=returns.index)

            # Standardize features
            self.scaler = StandardScaler()
            features_scaled = self.scaler.fit_transform(features_valid)

            # Fit KMeans
            self.kmeans_model = KMeans(
                n_clusters=self.n_regimes, random_state=self.random_state, n_init=10
            )
            regime_labels_valid = self.kmeans_model.fit_predict(features_scaled)

            # Map regimes: 0=Bear, 1=Neutral, 2=Bull (based on mean return)
            # Regime with highest mean return = Bull
            regime_means = {}
            for regime in range(self.n_regimes):
                mask = regime_labels_valid == regime
                regime_means[regime] = rolling_ret.values[valid_idx][mask].mean()

            # Sort regimes by mean return
            sorted_regimes = sorted(regime_means.items(), key=lambda x: x[1])
            regime_mapping = {old: new for new, (old, _) in enumerate(sorted_regimes)}

            # Remap labels: 0=Bear, 1=Neutral, 2=Bull
            regime_labels_remapped = np.array(
                [regime_mapping[label] for label in regime_labels_valid]
            )

            # Create full series with initial NaNs mapped to neutral (1)
            full_labels = np.ones(len(returns), dtype=int)
            full_labels[valid_idx] = regime_labels_remapped

            self.regime_labels = pd.Series(full_labels, index=returns.index, name="regime")

            logger.info(
                f"Detected {self.n_regimes} regimes. "
                f"Regime distribution: {np.bincount(full_labels)}"
            )

            return self.regime_labels

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error detecting regimes: {e}", exc_info=True)
            return pd.Series([0] * len(returns), index=returns.index)

    def analyze_regime_performance(
        self, returns: pd.Series, regime_labels: Optional[pd.Series] = None
    ) -> dict[str, Any]:
        """
        Analyze strategy performance for each regime.

        Args:
            returns: Series of returns
            regime_labels: Series with regime labels (default: use self.regime_labels)

        Returns:
            Dict with performance metrics per regime
        """
        if regime_labels is None:
            if self.regime_labels is None:
                logger.warning("No regime labels provided and no previous detection")
                return {}
            regime_labels = self.regime_labels

        if len(returns) != len(regime_labels):
            logger.warning("returns and regime_labels must have same length")
            return {}

        analysis = {}

        for regime in sorted(regime_labels.unique()):
            mask = regime_labels == regime
            regime_returns = returns[mask]

            if len(regime_returns) == 0:
                continue

            # Metrics
            total_return = (1 + regime_returns).prod() - 1
            mean_return = regime_returns.mean()
            volatility = regime_returns.std()
            annual_trading_days = get_config().backtesting.annual_trading_days
            sharpe = (
                (mean_return / volatility * np.sqrt(annual_trading_days)) if volatility > 0 else 0
            )
            max_dd = self._calculate_max_drawdown(regime_returns)
            win_rate = (regime_returns > 0).mean()
            num_periods = len(regime_returns)

            regime_name = {0: "Bear", 1: "Neutral", 2: "Bull"}.get(regime, f"Regime_{regime}")

            analysis[regime_name] = {
                "regime": regime,
                "periods": num_periods,
                "pct_time": num_periods / len(returns) * 100,
                "total_return": float(total_return),
                "annualized_return": float(mean_return * annual_trading_days),
                "volatility": float(volatility * np.sqrt(annual_trading_days)),
                "sharpe_ratio": float(sharpe),
                "max_drawdown": float(max_dd),
                "win_rate": float(win_rate),
                "mean_return": float(mean_return),
                "return_std": float(volatility),
            }

        logger.info(f"Regime performance analysis completed. Regimes: {list(analysis.keys())}")
        return analysis

    def regime_transition_analysis(self, regime_labels: pd.Series) -> dict[str, Any]:
        """
        Analyze regime transitions and transition probabilities.

        Args:
            regime_labels: Series with regime labels

        Returns:
            Dict with transition matrix and statistics
        """
        if len(regime_labels) < 2:
            logger.warning("Not enough data for transition analysis")
            return {}

        try:
            # Get unique regimes
            unique_regimes = sorted(regime_labels.unique())
            n_regimes = len(unique_regimes)

            # Build transition matrix
            transition_matrix = np.zeros((n_regimes, n_regimes))
            for i in range(len(regime_labels) - 1):
                from_regime = regime_labels.iloc[i]
                to_regime = regime_labels.iloc[i + 1]
                from_idx = list(unique_regimes).index(from_regime)
                to_idx = list(unique_regimes).index(to_regime)
                transition_matrix[from_idx, to_idx] += 1

            # Normalize to get probabilities
            transition_probs = transition_matrix.copy()
            for i in range(n_regimes):
                row_sum = transition_matrix[i, :].sum()
                if row_sum > 0:
                    transition_probs[i, :] /= row_sum

            # Regime names
            regime_names = [
                {0: "Bear", 1: "Neutral", 2: "Bull"}.get(regime, f"Regime_{regime}")
                for regime in unique_regimes
            ]

            # Duration analysis
            regime_durations = {}
            current_regime = regime_labels.iloc[0]
            current_duration = 1

            for i in range(1, len(regime_labels)):
                if regime_labels.iloc[i] == current_regime:
                    current_duration += 1
                else:
                    regime_name = {0: "Bear", 1: "Neutral", 2: "Bull"}.get(
                        current_regime, f"Regime_{current_regime}"
                    )
                    if regime_name not in regime_durations:
                        regime_durations[regime_name] = []
                    regime_durations[regime_name].append(current_duration)
                    current_regime = regime_labels.iloc[i]
                    current_duration = 1

            # Add last regime
            regime_name = {0: "Bear", 1: "Neutral", 2: "Bull"}.get(
                current_regime, f"Regime_{current_regime}"
            )
            if regime_name not in regime_durations:
                regime_durations[regime_name] = []
            regime_durations[regime_name].append(current_duration)

            # Calculate duration statistics
            duration_stats = {}
            for regime_name, durations in regime_durations.items():
                duration_stats[regime_name] = {
                    "mean_duration": float(np.mean(durations)),
                    "median_duration": float(np.median(durations)),
                    "min_duration": int(np.min(durations)),
                    "max_duration": int(np.max(durations)),
                    "transitions": len(durations),
                }

            analysis = {
                "transition_matrix": transition_matrix.tolist(),
                "transition_probabilities": transition_probs.tolist(),
                "regime_names": regime_names,
                "duration_statistics": duration_stats,
            }

            logger.info("Regime transition analysis completed")
            return analysis

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error in regime transition analysis: {e}", exc_info=True)
            return {}

    def out_of_sample_regime_robustness(
        self, returns: pd.Series, test_periods: int = 5, train_window: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Walk-forward regime detection robustness testing.

        Detects regimes on rolling training windows and validates stability.

        Args:
            returns: Series of returns
            test_periods: Number of test periods (default: 5)
            train_window: Training window size in days (default: 1 year = annual_trading_days)

        Returns:
            Dict with robustness metrics
        """
        if train_window is None:
            train_window = get_config().backtesting.annual_trading_days
        if len(returns) < train_window + 50:
            logger.warning(f"Not enough data ({len(returns)}) for robustness testing")
            return {}

        try:
            # Calculate step size
            step_size = (len(returns) - train_window) // test_periods

            if step_size < 20:
                logger.warning(f"Step size too small ({step_size}). Adjusting test_periods")
                test_periods = max(1, (len(returns) - train_window) // 20)
                step_size = (len(returns) - train_window) // test_periods

            robustness_results = {
                "test_periods": test_periods,
                "train_window": train_window,
                "step_size": step_size,
                "period_results": [],
            }

            # Walk-forward analysis
            for period in range(test_periods):
                train_start = period * step_size
                train_end = train_start + train_window
                test_start = train_end
                test_end = min(test_start + step_size, len(returns))

                if test_end <= test_start:
                    break

                # Train on training window
                train_returns = returns.iloc[train_start:train_end]
                test_returns = returns.iloc[test_start:test_end]

                # Detect regimes on training window
                self.detect_regimes(train_returns)

                # Analyze test period performance
                if len(test_returns) > 0:
                    test_return = test_returns.sum()
                    test_volatility = test_returns.std()
                    annual_trading_days = get_config().backtesting.annual_trading_days
                    test_sharpe = (
                        test_return / (test_volatility + 1e-8) * np.sqrt(annual_trading_days)
                    )

                    robustness_results["period_results"].append(
                        {
                            "period": period,
                            "train_start": train_start,
                            "train_end": train_end,
                            "test_start": test_start,
                            "test_end": test_end,
                            "test_return": float(test_return),
                            "test_volatility": float(test_volatility),
                            "test_sharpe": float(test_sharpe),
                        }
                    )

            # Calculate robustness metrics
            if robustness_results["period_results"]:
                returns_list = [r["test_return"] for r in robustness_results["period_results"]]
                robustness_results["avg_return"] = float(np.mean(returns_list))
                robustness_results["std_return"] = float(np.std(returns_list))
                robustness_results["consistency"] = float(
                    1 - np.std(returns_list) / (np.mean(np.abs(returns_list)) + 1e-8)
                )

            logger.info(f"Out-of-sample robustness testing completed ({test_periods} periods)")
            return robustness_results

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error in robustness testing: {e}", exc_info=True)
            return {}

    @staticmethod
    def _calculate_max_drawdown(returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())

    def get_regime_names(self) -> dict[int, str]:
        """Get mapping of regime indices to names."""
        return {0: "Bear Market", 1: "Neutral Market", 2: "Bull Market"}

    def get_regime_labels(self) -> Optional[pd.Series]:
        """Get last detected regime labels."""
        return self.regime_labels
