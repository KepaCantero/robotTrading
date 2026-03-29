"""
Overfitting detection module (FASE 5.3).

This module implements comprehensive overfitting detection using multiple
methods including IS vs OS comparison, parameter stability analysis, White's
reality check, and MCS test.

Key Features:
- IS vs OS Sharpe ratio degradation analysis
- Return degradation metrics
- Parameter stability scoring
- White's reality check for data snooping
- MCS (Multiple Comparison Systems) test
- Actionable recommendations based on overfitting level

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "A Reality Check for Data Snooping" - Halbert White
    - "Advances in Financial Machine Learning" - Marcos López de Prado
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np

from app.backtesting.validation.models import (
    OverfittingLevel,
    OverfittingMetrics,
    ParameterStabilityResult,
    PeriodResult,
    StabilityLevel,
)

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class OverfittingDetector:
    """
    Detect overfitting using multiple methods.

    This class analyzes in-sample vs out-of-sample performance to detect
    signs of overfitting in trading strategies.

    Example:
        ```python
        detector = OverfittingDetector()

        metrics = detector.detect(
            is_results=is_results,
            os_results=os_results,
            n_params=5
        )

        if metrics.is_overfitted():
            logger.debug(f"Overfitting detected: {metrics.overfitting_level}")
            for rec in metrics.recommendations:
                logger.debug(f"- {rec}")
        ```
    """

    # Thresholds for overfitting levels
    SEVERE_THRESHOLD = 0.5  # OS Sharpe < 50% of IS Sharpe
    MODERATE_THRESHOLD = 0.7  # OS Sharpe < 70% of IS Sharpe
    MILD_THRESHOLD = 0.85  # OS Sharpe < 85% of IS Sharpe

    def __init__(
        self,
        severe_threshold: float = SEVERE_THRESHOLD,
        moderate_threshold: float = MODERATE_THRESHOLD,
        mild_threshold: float = MILD_THRESHOLD,
    ):
        """
        Initialize overfitting detector.

        Args:
            severe_threshold: Threshold for severe overfitting
            moderate_threshold: Threshold for moderate overfitting
            mild_threshold: Threshold for mild overfitting
        """
        self.severe_threshold = severe_threshold
        self.moderate_threshold = moderate_threshold
        self.mild_threshold = mild_threshold

    def detect(
        self,
        is_results: list[PeriodResult],
        os_results: list[PeriodResult],
        n_params: int = 0,
        parameter_history: list[dict[str, Any]] | None = None,
    ) -> OverfittingMetrics:
        """
        Detect overfitting using multiple methods.

        Rules:
        - Severe: OS Sharpe < 0.5 * IS Sharpe
        - Moderate: OS Sharpe < 0.7 * IS Sharpe
        - Mild: OS Sharpe < 0.85 * IS Sharpe
        - None: OS Sharpe >= 0.85 * IS Sharpe

        Args:
            is_results: List of in-sample period results
            os_results: List of out-of-sample period results
            n_params: Number of optimized parameters
            parameter_history: Parameter values across windows

        Returns:
            OverfittingMetrics with detailed analysis
        """
        # Calculate aggregate metrics
        is_metrics = self._aggregate_period_metrics(is_results)
        os_metrics = self._aggregate_period_metrics(os_results)

        # Extract Sharpe ratios
        is_sharpe = is_metrics.get("sharpe_ratio", Decimal("0"))
        os_sharpe = os_metrics.get("sharpe_ratio", Decimal("0"))

        # Extract returns
        is_return = is_metrics.get("total_return", Decimal("0"))
        os_return = os_metrics.get("total_return", Decimal("0"))

        # Calculate degradation ratios
        degradation_ratio = self.calculate_degradation(float(is_sharpe), float(os_sharpe))
        return_degradation = self.calculate_degradation(float(is_return), float(os_return))

        # Determine overfitting level
        overfitting_level = self._classify_overfitting(degradation_ratio)

        # Calculate overfitting probability
        overfitting_probability = self._calculate_overfitting_probability(
            degradation_ratio=degradation_ratio,
            n_params=n_params,
            n_periods=len(os_results),
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overfitting_level=overfitting_level,
            degradation_ratio=degradation_ratio,
            return_degradation=return_degradation,
            n_params=n_params,
        )

        # Calculate parameter stability score
        parameter_stability_score = Decimal("100")
        if parameter_history:
            stability_results = analyze_parameter_stability(parameter_history, parameter_history)
            if stability_results:
                parameter_stability_score = Decimal(
                    str(np.mean([r.stability_score for r in stability_results]))
                )

        # Create metrics object
        metrics = OverfittingMetrics(
            is_sharpe=is_sharpe,
            os_sharpe=os_sharpe,
            degradation_ratio=Decimal(str(degradation_ratio)),
            is_return=is_return,
            os_return=os_return,
            return_degradation=Decimal(str(return_degradation)),
            overfitting_probability=overfitting_probability,
            overfitting_level=overfitting_level,
            recommendations=recommendations,
            parameter_stability_score=parameter_stability_score,
        )

        return metrics

    def calculate_degradation(self, is_value: float, os_value: float) -> float:
        """
        Calculate degradation ratio.

        Args:
            is_value: In-sample value
            os_value: Out-of-sample value

        Returns:
            Degradation ratio (OS/IS)
        """
        if is_value == 0:
            return 0.0
        return os_value / is_value

    def _aggregate_period_metrics(self, results: list[PeriodResult]) -> dict[str, Decimal]:
        """
        Aggregate metrics across periods.

        Args:
            results: List of period results

        Returns:
            Dictionary of aggregate metrics
        """
        if not results:
            return {
                "sharpe_ratio": Decimal("0"),
                "total_return": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "win_rate": Decimal("0"),
            }

        # Average Sharpe ratio
        sharpes = [r.sharpe_ratio for r in results if r.sharpe_ratio is not None]
        avg_sharpe = Decimal(str(np.mean([float(s) for s in sharpes]))) if sharpes else Decimal("0")

        # Average return
        returns = [float(r.total_return) for r in results]
        avg_return = Decimal(str(np.mean(returns))) if returns else Decimal("0")

        # Max drawdown (worst across all periods)
        max_dd = max([float(r.max_drawdown) for r in results], default=0.0)

        # Average win rate
        win_rates = [float(r.win_rate) for r in results]
        avg_win_rate = Decimal(str(np.mean(win_rates))) if win_rates else Decimal("0")

        return {
            "sharpe_ratio": avg_sharpe,
            "total_return": avg_return,
            "max_drawdown": Decimal(str(max_dd)),
            "win_rate": avg_win_rate,
        }

    def _classify_overfitting(self, degradation_ratio: float) -> OverfittingLevel:
        """
        Classify overfitting level based on degradation ratio.

        Args:
            degradation_ratio: OS/IS Sharpe ratio

        Returns:
            OverfittingLevel
        """
        if degradation_ratio < self.severe_threshold:
            return OverfittingLevel.SEVERE
        elif degradation_ratio < self.moderate_threshold:
            return OverfittingLevel.MODERATE
        elif degradation_ratio < self.mild_threshold:
            return OverfittingLevel.MILD
        else:
            return OverfittingLevel.NONE

    def _calculate_overfitting_probability(
        self,
        degradation_ratio: float,
        n_params: int,
        n_periods: int,
    ) -> float:
        """
        Calculate probability of overfitting.

        Considers:
        - Degradation ratio (more degradation = higher probability)
        - Number of parameters (more params = higher probability)
        - Number of periods (more periods = more confidence)

        Args:
            degradation_ratio: OS/IS Sharpe ratio
            n_params: Number of optimized parameters
            n_periods: Number of validation periods

        Returns:
            Probability (0-1)
        """
        # Base probability from degradation
        if degradation_ratio >= 1.0:
            degradation_prob = 0.0
        elif degradation_ratio >= 0.85:
            degradation_prob = 0.2
        elif degradation_ratio >= 0.7:
            degradation_prob = 0.5
        elif degradation_ratio >= 0.5:
            degradation_prob = 0.7
        else:
            degradation_prob = 0.9

        # Adjust for number of parameters (more params = more overfitting risk)
        param_factor = min(n_params / 20.0, 1.0)  # Cap at 20 params

        # Adjust for number of periods (more periods = less uncertainty)
        period_factor = max(1.0 - n_periods / 20.0, 0.2)  # Minimum 0.2

        # Combine factors
        probability = degradation_prob * (1 + param_factor) * period_factor
        probability = min(max(probability, 0.0), 1.0)

        return probability

    def _generate_recommendations(
        self,
        overfitting_level: OverfittingLevel,
        degradation_ratio: float,
        return_degradation: float,
        n_params: int,
    ) -> list[str]:
        """
        Generate actionable recommendations.

        Args:
            overfitting_level: Detected overfitting level
            degradation_ratio: Sharpe degradation ratio
            return_degradation: Return degradation ratio
            n_params: Number of parameters

        Returns:
            List of recommendations
        """
        recommendations = []

        if overfitting_level == OverfittingLevel.SEVERE:
            recommendations.extend(
                [
                    "CRITICAL: Severe overfitting detected.",
                    "Strategy should NOT be used in production.",
                    "Consider: Simplifying strategy logic",
                    f"Consider: Reducing number of parameters from {n_params} to fewer than 5",
                    "Consider: Adding stronger regularization",
                    "Consider: Using ensemble methods to reduce variance",
                ]
            )
        elif overfitting_level == OverfittingLevel.MODERATE:
            recommendations.extend(
                [
                    "WARNING: Moderate overfitting detected.",
                    "Strategy requires improvement before production use.",
                    "Consider: Reducing parameter complexity",
                    "Consider: Increasing training data size",
                    "Consider: Implementing walk-forward optimization",
                ]
            )
        elif overfitting_level == OverfittingLevel.MILD:
            recommendations.extend(
                [
                    "CAUTION: Mild overfitting detected.",
                    "Monitor strategy performance closely.",
                    "Consider: Regular parameter reoptimization",
                    "Consider: Implementing regime filters",
                ]
            )
        else:
            recommendations.append("GOOD: No significant overfitting detected.")

        # Parameter-specific recommendations
        if n_params > 10:
            recommendations.append(
                f"High parameter count ({n_params}). Consider dimensionality reduction "
                "or feature selection."
            )

        # Return degradation specific
        if return_degradation < degradation_ratio:
            recommendations.append(
                "Return degradation is worse than Sharpe degradation. "
                "Check for outliers or non-normal return distribution."
            )

        return recommendations

    def whites_reality_check(
        self,
        returns: pd.Series,
        null_returns: pd.Series,
        n_bootstrap: int = 1000,
    ) -> tuple[float, bool]:
        """
        Perform White's reality check for data snooping.

        Tests whether a strategy's performance is significantly better
        than a null hypothesis (e.g., random trading or benchmark).

        Args:
            returns: Strategy returns
            null_returns: Null hypothesis returns
            n_bootstrap: Number of bootstrap iterations

        Returns:
            (p_value, is_significant) where is_significant is True if p < 0.05
        """
        # Calculate test statistic (mean return)
        test_stat = float(returns.mean())

        # Bootstrap null distribution
        null_stats = []
        for _ in range(n_bootstrap):
            # Bootstrap sample from null returns
            sample = null_returns.sample(n=len(returns), replace=True)
            null_stats.append(float(sample.mean()))

        null_stats = np.array(null_stats)

        # Calculate p-value (proportion of null stats >= test stat)
        p_value = np.mean(null_stats >= test_stat)

        # Significant if p < 0.05
        is_significant = p_value < 0.05

        return p_value, is_significant

    def mcs_test(
        self,
        strategies_returns: list[pd.Series],
        benchmark_returns: pd.Series | None = None,
        alpha: float = 0.05,
    ) -> tuple[float, bool]:
        """
        Perform Model Confidence Set (MCS) test.

        Tests whether a strategy belongs to the set of superior models.

        Args:
            strategies_returns: List of strategy return series
            benchmark_returns: Optional benchmark returns
            alpha: Significance level

        Returns:
            (p_value, is_in_mcs) where is_in_mcs is True if strategy passes
        """
        # Simplified MCS implementation
        # Full implementation would use the Hansen et al. method

        if not strategies_returns:
            return 1.0, False

        # Calculate performance statistics for each strategy
        stats_list = []
        for returns in strategies_returns:
            sharpe = float(returns.mean() / returns.std()) if returns.std() > 0 else 0
            stats_list.append(sharpe)

        # Compare to benchmark if provided
        if benchmark_returns is not None:
            benchmark_sharpe = (
                float(benchmark_returns.mean() / benchmark_returns.std())
                if benchmark_returns.std() > 0
                else 0
            )
            stats_list.append(benchmark_sharpe)

        # Calculate relative performance
        max_stat = max(stats_list)
        relative_stats = [s - max_stat for s in stats_list]

        # P-value based on relative performance
        # (This is a simplified version)
        p_value = max(0.05, 1.0 - max([max(0, s) for s in relative_stats]))

        # Strategy is in MCS if p-value > alpha
        is_in_mcs = p_value > alpha

        return p_value, is_in_mcs


def analyze_parameter_stability(
    is_params: list[dict[str, Any]],
    os_params: list[dict[str, Any]],
) -> list[ParameterStabilityResult]:
    """
    Analyze parameter stability across walk-forward windows.

    Args:
        is_params: Parameter values from in-sample periods
        os_params: Parameter values from out-of-sample periods

    Returns:
        List of ParameterStabilityResult for each parameter
    """
    if not is_params or not os_params:
        return []

    # Get all parameter names
    param_names = set()
    for params in is_params:
        param_names.update(params.keys())
    for params in os_params:
        param_names.update(params.keys())

    results = []

    for param_name in param_names:
        # Extract parameter values
        is_values = [
            float(params.get(param_name, 0)) for params in is_params if param_name in params
        ]
        os_values = [
            float(params.get(param_name, 0)) for params in os_params if param_name in params
        ]

        if not is_values:
            continue

        # Calculate statistics
        is_mean = Decimal(str(np.mean(is_values)))
        is_std = Decimal(str(np.std(is_values)))
        os_mean = Decimal(str(np.mean(os_values))) if os_values else is_mean
        os_std = Decimal(str(np.std(os_values))) if os_values else is_std

        # Calculate stability score
        stability_score = calculate_stability_score(is_std, is_mean)
        stability_level = classify_stability(stability_score)

        # Detect drift
        drift_detected = detect_parameter_drift(is_values + os_values)

        # Generate recommendation
        recommendation = generate_stability_recommendation(
            param_name=param_name,
            stability_level=stability_level,
            drift_detected=drift_detected,
        )

        # Calculate coefficient of variation
        cv = Decimal(str(is_std / is_mean)) if is_mean > 0 else Decimal("0")

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


def calculate_stability_score(is_std: Decimal, is_mean: Decimal) -> Decimal:
    """
    Calculate stability score (0-100).

    Score = 100 * (1 - coefficient_of_variation)
    CV = std / mean

    Args:
        is_std: Standard deviation
        is_mean: Mean value

    Returns:
        Stability score (0-100)
    """
    if is_mean == 0:
        return Decimal("0")

    cv = is_std / is_mean
    score = Decimal("100") * (Decimal("1") - cv)
    return max(Decimal("0"), min(Decimal("100"), score))


def classify_stability(stability_score: Decimal) -> StabilityLevel:
    """
    Classify stability level from score.

    Args:
        stability_score: Stability score (0-100)

    Returns:
        StabilityLevel
    """
    score = float(stability_score)
    if score >= 70:
        return StabilityLevel.STABLE
    elif score >= 40:
        return StabilityLevel.MODERATE
    else:
        return StabilityLevel.UNSTABLE


def detect_parameter_drift(param_values: list[float]) -> bool:
    """
    Detect parameter drift using Mann-Kendall trend test.

    Args:
        param_values: List of parameter values across windows

    Returns:
        True if significant drift detected
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
        return abs(z) > 1.96

    return False


def generate_stability_recommendation(
    param_name: str,
    stability_level: StabilityLevel,
    drift_detected: bool,
) -> str:
    """
    Generate recommendation for parameter stability.

    Args:
        param_name: Parameter name
        stability_level: Stability level
        drift_detected: Whether drift was detected

    Returns:
        Recommendation string
    """
    if drift_detected:
        return (
            f"Parameter '{param_name}' shows significant drift across windows. "
            "Consider using adaptive parameter selection or regime-specific parameters."
        )

    if stability_level == StabilityLevel.STABLE:
        return (
            f"Parameter '{param_name}' is stable across windows. "
            "Good candidate for fixed-parameter strategy."
        )
    elif stability_level == StabilityLevel.MODERATE:
        return (
            f"Parameter '{param_name}' shows moderate variability. "
            "Consider periodic reoptimization."
        )
    else:  # UNSTABLE
        return (
            f"Parameter '{param_name}' is highly unstable. "
            "Consider removing this parameter or implementing adaptive selection."
        )


def calculate_overfitting_metrics(
    is_sharpe: float,
    os_sharpe: float,
    is_return: float,
    os_return: float,
    n_params: int = 0,
    n_periods: int = 0,
) -> OverfittingMetrics:
    """
    Quick calculation of overfitting metrics.

    Args:
        is_sharpe: In-sample Sharpe ratio
        os_sharpe: Out-of-sample Sharpe ratio
        is_return: In-sample return
        os_return: Out-of-sample return
        n_params: Number of parameters
        n_periods: Number of test periods

    Returns:
        OverfittingMetrics
    """
    detector = OverfittingDetector()

    # Create dummy period results
    is_result = PeriodResult(
        sharpe_ratio=Decimal(str(is_sharpe)),
        total_return=Decimal(str(is_return)),
    )
    os_result = PeriodResult(
        sharpe_ratio=Decimal(str(os_sharpe)),
        total_return=Decimal(str(os_return)),
    )

    return detector.detect(
        is_results=[is_result],
        os_results=[os_result],
        n_params=n_params,
    )
