"""
Regime Analyzer Module

Extracted from comprehensive_backtest_runner.py for SRP compliance.

Provides regime detection and analysis functionality for backtesting:
- Simple regime detection based on returns and volatility
- Regime name mapping based on characteristics
- Regime transition analysis using Markov chains
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RegimeAnalyzer:
    """
    Analyzes market regimes for backtesting.

    Provides methods for:
    - Detecting market regimes (Bear, Neutral, Bull)
    - Mapping regime indices to descriptive names
    - Analyzing regime transitions and building transition matrices
    """

    # Default window for rolling calculations
    DEFAULT_WINDOW = 20

    def detect_simple_regimes(
        self, returns: np.ndarray, window: Optional[int] = None
    ) -> np.ndarray:
        """
        Simple regime detection based on returns and volatility.

        Fallback method when advanced detectors are unavailable.
        Classifies regimes based on return and volatility thresholds.

        Args:
            returns: Array of returns
            window: Rolling window for calculations (default: 20)

        Returns:
            Array of regime labels (0=Bear, 1=Neutral, 2=Bull)
        """
        window = window or self.DEFAULT_WINDOW

        # Calculate rolling volatility and returns
        rolling_vol = pd.Series(returns).rolling(window).std().values
        rolling_ret = pd.Series(returns).rolling(window).mean().values

        # Thresholds for classification
        vol_median = np.nanmedian(rolling_vol)
        ret_median = np.nanmedian(rolling_ret)

        regimes = np.ones(len(returns), dtype=int)  # Default to Neutral

        for i in range(len(returns)):
            vol = rolling_vol[i] if not np.isnan(rolling_vol[i]) else vol_median
            ret = rolling_ret[i] if not np.isnan(rolling_ret[i]) else ret_median

            # Classify based on volatility and return
            if ret > ret_median * 1.5 and vol < vol_median * 1.2:
                regimes[i] = 2  # Bull: high return, low vol
            elif ret < ret_median * 0.5 and vol > vol_median * 1.2:
                regimes[i] = 0  # Bear: low return, high vol
            else:
                regimes[i] = 1  # Neutral

        return regimes

    def get_regime_name_mapping(
        self, regime_labels: np.ndarray, returns: pd.Series
    ) -> dict[int, str]:
        """
        Map regime indices to descriptive names based on characteristics.

        Args:
            regime_labels: Array of regime labels
            returns: Series of returns

        Returns:
            Dictionary mapping regime indices to names
        """
        unique_regimes = sorted(np.unique(regime_labels))
        regime_stats = {}

        for regime in unique_regimes:
            mask = regime_labels == regime
            regime_returns = returns[mask]

            regime_stats[regime] = {
                "mean_return": float(regime_returns.mean()),
                "volatility": float(regime_returns.std()),
            }

        # Sort regimes by mean return to determine Bear/Neutral/Bull
        sorted_regimes = sorted(regime_stats.items(), key=lambda x: x[1]["mean_return"])

        regime_names = {}
        if len(sorted_regimes) == 3:
            regime_names[sorted_regimes[0][0]] = "Bear Market"
            regime_names[sorted_regimes[1][0]] = "Neutral Market"
            regime_names[sorted_regimes[2][0]] = "Bull Market"
        elif len(sorted_regimes) == 2:
            regime_names[sorted_regimes[0][0]] = "Bear Market"
            regime_names[sorted_regimes[1][0]] = "Bull Market"
        else:
            for regime, stats in sorted_regimes:
                if stats["mean_return"] > 0:
                    regime_names[regime] = f"Positive_Regime_{regime}"
                else:
                    regime_names[regime] = f"Negative_Regime_{regime}"

        return regime_names

    def analyze_regime_transitions(
        self, regime_labels: np.ndarray, regime_names: dict[int, str]
    ) -> dict[str, Any]:
        """
        Analyze regime transitions and build transition probability matrix.

        Implements Markov chain analysis for regime switching (Tsay).

        Args:
            regime_labels: Array of regime labels
            regime_names: Mapping of regime indices to names

        Returns:
            Dictionary with transition analysis results
        """
        unique_regimes = sorted(np.unique(regime_labels))
        n_regimes = len(unique_regimes)

        # Build transition matrix
        transition_matrix = np.zeros((n_regimes, n_regimes))
        for i in range(len(regime_labels) - 1):
            from_regime = regime_labels[i]
            to_regime = regime_labels[i + 1]
            from_idx = unique_regimes.index(from_regime)
            to_idx = unique_regimes.index(to_regime)
            transition_matrix[from_idx, to_idx] += 1

        # Normalize to get probabilities
        transition_probs = transition_matrix.copy()
        for i in range(n_regimes):
            row_sum = transition_matrix[i, :].sum()
            if row_sum > 0:
                transition_probs[i, :] /= row_sum

        # Build named transition matrix
        named_transition_probs = {}
        for i, from_regime in enumerate(unique_regimes):
            from_name = regime_names.get(from_regime, f"Regime_{from_regime}")
            named_transition_probs[from_name] = {}
            for j, to_regime in enumerate(unique_regimes):
                to_name = regime_names.get(to_regime, f"Regime_{to_regime}")
                named_transition_probs[from_name][to_name] = float(transition_probs[i, j])

        # Analyze regime durations
        regime_durations = {name: [] for name in regime_names.values()}
        current_regime = regime_labels[0]
        current_duration = 1

        for i in range(1, len(regime_labels)):
            if regime_labels[i] == current_regime:
                current_duration += 1
            else:
                regime_name = regime_names.get(current_regime, f"Regime_{current_regime}")
                if regime_name in regime_durations:
                    regime_durations[regime_name].append(current_duration)
                current_regime = regime_labels[i]
                current_duration = 1

        # Add last regime duration
        regime_name = regime_names.get(current_regime, f"Regime_{current_regime}")
        if regime_name in regime_durations:
            regime_durations[regime_name].append(current_duration)

        # Calculate average durations
        avg_durations = {}
        for name, durations in regime_durations.items():
            if durations:
                avg_durations[name] = float(np.mean(durations))

        return {
            "transition_matrix": named_transition_probs,
            "average_durations": avg_durations,
            "regime_counts": {
                regime_names.get(r, f"Regime_{r}"): int(np.sum(regime_labels == r))
                for r in unique_regimes
            },
        }

    def get_regime_statistics(
        self, regime_labels: np.ndarray, returns: pd.Series, regime_names: dict[int, str]
    ) -> dict[str, dict[str, float]]:
        """
        Calculate statistics for each regime.

        Args:
            regime_labels: Array of regime labels
            returns: Series of returns
            regime_names: Mapping of regime indices to names

        Returns:
            Dictionary with statistics per regime
        """
        unique_regimes = sorted(np.unique(regime_labels))
        stats = {}

        for regime in unique_regimes:
            mask = regime_labels == regime
            regime_returns = returns[mask]

            name = regime_names.get(regime, f"Regime_{regime}")
            stats[name] = {
                "count": int(np.sum(mask)),
                "mean_return": float(regime_returns.mean()),
                "volatility": float(regime_returns.std()),
                "min_return": float(regime_returns.min()),
                "max_return": float(regime_returns.max()),
                "sharpe": (
                    float(regime_returns.mean() / regime_returns.std())
                    if regime_returns.std() > 0
                    else 0.0
                ),
            }

        return stats


# Module-level convenience functions
def detect_regimes(returns: np.ndarray, window: int = 20) -> np.ndarray:
    """Convenience function for regime detection."""
    analyzer = RegimeAnalyzer()
    return analyzer.detect_simple_regimes(returns, window)
