"""
Parameter stability analysis module (FASE 5.3).

This module implements comprehensive parameter stability analysis for
walk-forward validation results, detecting drift and measuring consistency.

Key Features:
- Parameter stability scoring (0-100)
- Drift detection using Mann-Kendall trend test
- In-sample vs out-of-sample parameter comparison
- Coefficient of variation calculation
- Actionable recommendations for each parameter

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "Advances in Financial Machine Learning" - Marcos López de Prado
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .models import ParameterStabilityResult, StabilityLevel

logger = logging.getLogger(__name__)


class ParameterStabilityAnalyzer:
    """
    Analyze parameter stability across walk-forward windows.

    This class examines how selected parameters vary across different
    training periods to identify stable vs unstable parameters.

    Example:
        ```python
        analyzer = ParameterStabilityAnalyzer()

        results = analyzer.analyze(
            is_params=[
                {"window": 20, "threshold": 1.5},
                {"window": 22, "threshold": 1.6},
                {"window": 21, "threshold": 1.5},
            ],
            os_params=[
                {"window": 20, "threshold": 1.5},
                {"window": 23, "threshold": 1.7},
                {"window": 20, "threshold": 1.5},
            ]
        )

        for result in results:
            logger.debug(f"{result.parameter_name}: {result.stability_level}")
            logger.debug(f"  Recommendation: {result.recommendation}")
        ```
    """

    def __init__(
        self,
        stable_threshold: float = 70.0,
        moderate_threshold: float = 40.0,
    ):
        """
        Initialize parameter stability analyzer.

        Args:
            stable_threshold: Minimum score for "stable" classification
            moderate_threshold: Minimum score for "moderate" classification
        """
        self.stable_threshold = stable_threshold
        self.moderate_threshold = moderate_threshold

    def analyze(
        self,
        is_params: list[dict[str, Any]],
        os_params: list[dict[str, Any]],
    ) -> list[ParameterStabilityResult]:
        """
        Analyze parameter stability.

        For each parameter:
        - Calculate mean and std across IS windows
        - Calculate mean and std across OS windows
        - Check for drift (trend in parameter values)
        - Assign stability score

        Args:
            is_params: Parameter values from in-sample optimization
            os_params: Parameter values from out-of-sample periods

        Returns:
            List of ParameterStabilityResult for each parameter
        """
        if not is_params:
            logger.warning("No in-sample parameters provided")
            return []

        # Get all parameter names
        param_names = self._get_all_parameter_names(is_params, os_params)

        results = []

        for param_name in param_names:
            # Extract parameter values
            is_values = self._extract_param_values(is_params, param_name)
            os_values = self._extract_param_values(os_params, param_name)

            if not is_values:
                logger.warning(f"No values found for parameter '{param_name}'")
                continue

            # Calculate statistics
            is_mean = Decimal(str(np.mean(is_values)))
            is_std = Decimal(str(np.std(is_values)))
            os_mean = Decimal(str(np.mean(os_values))) if os_values else is_mean
            os_std = Decimal(str(np.std(os_values))) if os_values else is_std

            # Calculate stability score
            stability_score = self.calculate_stability_score(is_std, is_mean)

            # Classify stability level
            stability_level = self._classify_stability(stability_score)

            # Detect drift
            drift_detected = self.detect_drift(is_values + os_values)

            # Generate recommendation
            recommendation = self._generate_recommendation(
                param_name, stability_level, drift_detected, is_values, os_values
            )

            # Calculate coefficient of variation
            cv = self._calculate_cv(is_mean, is_std)

            result = ParameterStabilityResult(
                parameter_name=param_name,
                is_mean=is_mean,
                is_std=is_std,
                os_mean=os_mean,
                os_std=os_std,
                stability_score=stability_score,
                stability_level=stability_level,
                drift_detected=drift_detected,
                recommendation=recommendation,
                coefficient_of_variation=cv,
            )

            results.append(result)

        return results

    def _get_all_parameter_names(
        self,
        is_params: list[dict[str, Any]],
        os_params: list[dict[str, Any]],
    ) -> list[str]:
        """Get all unique parameter names."""
        param_names: set[str] = set()

        for params in is_params:
            param_names.update(params.keys())

        for params in os_params:
            param_names.update(params.keys())

        return sorted(param_names)

    def _extract_param_values(
        self,
        param_list: list[dict[str, Any]],
        param_name: str,
    ) -> list[float]:
        """Extract parameter values as floats."""
        values = []

        for params in param_list:
            if param_name in params:
                try:
                    value = float(params[param_name])
                    values.append(value)
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert parameter '{param_name}' value to float")

        return values

    def calculate_stability_score(
        self,
        is_std: Decimal,
        is_mean: Decimal,
    ) -> Decimal:
        """
        Calculate stability score (0-100).

        Score = 100 * (1 - coefficient_of_variation)
        CV = std / mean

        Args:
            is_std: Standard deviation of parameter values
            is_mean: Mean of parameter values

        Returns:
            Stability score (0-100)
        """
        if is_mean == 0:
            return Decimal("0")

        cv = is_std / is_mean
        score = Decimal("100") * (Decimal("1") - cv)
        score = max(Decimal("0"), min(Decimal("100"), score))

        return score

    def _calculate_cv(
        self,
        mean: Decimal,
        std: Decimal,
    ) -> Decimal:
        """Calculate coefficient of variation."""
        if mean == 0:
            return Decimal("0")
        return std / mean

    def _classify_stability(self, stability_score: Decimal) -> StabilityLevel:
        """
        Classify stability level from score.

        Args:
            stability_score: Stability score (0-100)

        Returns:
            StabilityLevel
        """
        score = float(stability_score)

        if score >= self.stable_threshold:
            return StabilityLevel.STABLE
        elif score >= self.moderate_threshold:
            return StabilityLevel.MODERATE
        else:
            return StabilityLevel.UNSTABLE

    def detect_drift(
        self,
        param_values: list[float],
    ) -> bool:
        """
        Detect parameter drift using Mann-Kendall trend test.

        The Mann-Kendall test is a non-parametric test for monotonic
        trends in a time series. It's robust to non-normal distributions.

        Args:
            param_values: List of parameter values across windows

        Returns:
            True if significant drift detected (p < 0.05)
        """
        if len(param_values) < 3:
            return False

        # Mann-Kendall trend test
        n = len(param_values)
        s = 0

        for i in range(n - 1):
            for j in range(i + 1, n):
                if param_values[j] > param_values[i]:
                    s += 1
                elif param_values[j] < param_values[i]:
                    s -= 1

        # Calculate variance
        var_s = n * (n - 1) * (2 * n + 5) / 18

        # Calculate Z-score
        if var_s > 0:
            z = (s - np.sign(s)) / np.sqrt(var_s)

            # Test for significance (p < 0.05, two-tailed)
            # Critical value is approximately +/-1.96
            return bool(abs(z) > 1.96)

        return False

    def _generate_recommendation(
        self,
        param_name: str,
        stability_level: StabilityLevel,
        drift_detected: bool,
        is_values: list[float],
        os_values: list[float],
    ) -> str:
        """
        Generate recommendation for parameter stability.

        Args:
            param_name: Parameter name
            stability_level: Stability level
            drift_detected: Whether drift was detected
            is_values: In-sample values
            os_values: Out-of-sample values

        Returns:
            Recommendation string
        """
        if drift_detected:
            return (
                f"Parameter '{param_name}' shows significant drift across windows. "
                "Consider using adaptive parameter selection, regime-specific parameters, "
                "or removing this parameter from optimization."
            )

        if stability_level == StabilityLevel.STABLE:
            return (
                f"Parameter '{param_name}' is stable across windows. "
                "Good candidate for fixed-parameter strategy or reduced optimization frequency."
            )

        elif stability_level == StabilityLevel.MODERATE:
            # Check if IS and OS means are similar
            if is_values and os_values:
                is_mean = np.mean(is_values)
                os_mean = np.mean(os_values)
                diff_pct = abs(os_mean - is_mean) / is_mean * 100 if is_mean != 0 else 0

                if diff_pct < 10:
                    return (
                        f"Parameter '{param_name}' shows moderate variability but "
                        "IS and OS values are consistent. Consider periodic reoptimization "
                        f"every {self._estimate_reopt_frequency(is_values)} periods."
                    )
                else:
                    return (
                        f"Parameter '{param_name}' shows moderate variability with "
                        f"{diff_pct:.1f}% difference between IS and OS. Increase "
                        "optimization frequency or consider adaptive selection."
                    )

            return (
                f"Parameter '{param_name}' shows moderate variability. "
                "Consider periodic reoptimization."
            )

        else:  # UNSTABLE
            return (
                f"Parameter '{param_name}' is highly unstable across windows. "
                "Strongly consider removing this parameter, implementing adaptive selection, "
                "or using regime-specific parameter values."
            )

    def _estimate_reopt_frequency(self, values: list[float]) -> int:
        """
        Estimate optimal reoptimization frequency based on variability.

        Args:
            values: Parameter values across windows

        Returns:
            Suggested frequency in number of periods
        """
        if len(values) < 3:
            return 3

        # Calculate how often values change significantly
        changes = 0
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                change_pct = abs(values[i] - values[i - 1]) / values[i - 1]
                if change_pct > 0.1:  # 10% change threshold
                    changes += 1

        if changes > len(values) / 2:
            return 1  # Reoptimize every period
        elif changes > len(values) / 4:
            return 2  # Reoptimize every 2 periods
        else:
            return 3  # Reoptimize every 3 periods

    def compare_parameter_distributions(
        self,
        is_params: list[dict[str, Any]],
        os_params: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare parameter distributions between IS and OS.

        Uses Kolmogorov-Smirnov test to check if IS and OS parameters
        come from the same distribution.

        Args:
            is_params: In-sample parameters
            os_params: Out-of-sample parameters

        Returns:
            Dictionary with KS test results for each parameter
        """
        param_names = self._get_all_parameter_names(is_params, os_params)
        results = {}

        for param_name in param_names:
            is_values = self._extract_param_values(is_params, param_name)
            os_values = self._extract_param_values(os_params, param_name)

            if len(is_values) < 3 or len(os_values) < 3:
                continue

            # Perform KS test
            ks_statistic, p_value = stats.ks_2samp(is_values, os_values)

            results[param_name] = {
                "ks_statistic": ks_statistic,
                "p_value": p_value,
                "same_distribution": p_value > 0.05,
            }

        return results

    def calculate_parameter_correlation(
        self,
        params_history: list[dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix between parameters.

        Helps identify if parameters tend to move together, which
        might indicate redundancy.

        Args:
            params_history: Parameter values across windows

        Returns:
            Correlation matrix as DataFrame
        """
        # Convert to DataFrame
        df = pd.DataFrame(params_history)

        # Select only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        if numeric_df.empty:
            return pd.DataFrame()

        # Calculate correlation
        corr_matrix = numeric_df.corr()

        return corr_matrix

    def find_redundant_parameters(
        self,
        params_history: list[dict[str, Any]],
        threshold: float = 0.9,
    ) -> list[tuple[Any, ...]]:
        """
        Find redundant parameters (highly correlated).

        Args:
            params_history: Parameter values across windows
            threshold: Correlation threshold for redundancy

        Returns:
            List of (param1, param2) tuples with high correlation
        """
        corr_matrix = self.calculate_parameter_correlation(params_history)

        if corr_matrix.empty:
            return []

        redundant_pairs = []

        # Find high correlations
        columns = list(corr_matrix.columns)
        for i, param1 in enumerate(columns):
            for j in range(i + 1, len(columns)):
                param2 = columns[j]

                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) >= threshold:
                    redundant_pairs.append((param1, param2, corr_value))

        return redundant_pairs


def calculate_parameter_stability(
    param_values: list[float],
) -> dict[str, Any]:
    """
    Quick calculation of parameter stability metrics.

    Args:
        param_values: List of parameter values

    Returns:
        Dictionary with stability metrics
    """
    if not param_values:
        return {
            "mean": 0.0,
            "std": 0.0,
            "cv": 0.0,
            "stability_score": 0.0,
            "stability_level": "unknown",
        }

    values_array = np.array(param_values)
    mean = float(np.mean(values_array))
    std = float(np.std(values_array))

    if mean == 0:
        cv = float("inf")
        stability_score = 0.0
    else:
        cv = std / abs(mean)
        stability_score = max(0, min(100, 100 * (1 - cv)))

    # Classify stability level
    if stability_score >= 70:
        stability_level = "stable"
    elif stability_score >= 40:
        stability_level = "moderate"
    else:
        stability_level = "unstable"

    return {
        "mean": mean,
        "std": std,
        "cv": cv,
        "stability_score": stability_score,
        "stability_level": stability_level,
    }


def detect_parameter_drift_simple(
    param_values: list[float],
    window: int = 3,
) -> bool:
    """
    Simple drift detection using rolling means.

    Args:
        param_values: List of parameter values
        window: Window size for rolling mean

    Returns:
        True if drift detected
    """
    # Need at least window + 1 values to have distinct early and late windows
    if len(param_values) < window + 1:
        return False

    # Calculate early and late means
    early_mean = np.mean(param_values[:window])
    late_mean = np.mean(param_values[-window:])

    # Calculate percent change
    if early_mean != 0:
        change_pct = abs(late_mean - early_mean) / abs(early_mean) * 100
        return bool(change_pct > 20)  # 20% change threshold

    return False


def rank_parameters_by_stability(
    stability_results: list[ParameterStabilityResult],
) -> list[ParameterStabilityResult]:
    """
    Rank parameters by stability score.

    Args:
        stability_results: List of stability results

    Returns:
        Sorted list (most stable first)
    """
    return sorted(
        stability_results,
        key=lambda r: r.stability_score,
        reverse=True,
    )


def filter_stable_parameters(
    stability_results: list[ParameterStabilityResult],
    min_score: float = 70.0,
) -> list[str]:
    """
    Filter to get only stable parameters.

    Args:
        stability_results: List of stability results
        min_score: Minimum stability score

    Returns:
        List of stable parameter names
    """
    return [
        r.parameter_name
        for r in stability_results
        if r.stability_score >= Decimal(str(min_score)) and not r.drift_detected
    ]
