"""
Parameter Stability Metrics (TASK-6.1 Phase 2)

Tracks how consistently a parameter performs across time periods/folds/regimes.
Core concept: Stable parameters should have consistent optimal values across windows.

Key Metrics:
- Variance across walk-forward windows
- Convergence speed detection
- Stability scoring (0-100)
- Parameter plateau width

Stable = parameter value doesn't change much across windows (low variance)
Unstable = parameter value bounces around across windows (high variance, curve-fitted)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WindowOptimalValue:
    """Optimal parameter value for a single window/fold/period."""

    window_id: Union[int, str]
    parameter_name: str
    optimal_value: Union[float, int]
    performance_metric: float  # Sharpe, return, etc. at this optimal value
    window_start: Optional[Any] = None
    window_end: Optional[Any] = None
    confidence: float = 1.0  # How confident are we in this value (0-1)


@dataclass
class ParameterStabilityResult:
    """Stability analysis result for a single parameter."""

    parameter_name: str
    window_results: List[WindowOptimalValue] = field(default_factory=list)
    mean_optimal_value: float = 0.0
    variance: float = 0.0
    std_dev: float = 0.0
    coefficient_of_variation: float = 0.0  # std_dev / mean
    min_value: float = 0.0
    max_value: float = 0.0
    value_range: float = 0.0
    convergence_speed: float = 0.0  # How quickly values converge to stable value (0-1)
    stability_score: float = 0.0  # 0-100, higher is more stable
    is_stable: bool = False  # True if score >= 70
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "parameter_name": self.parameter_name,
            "mean_optimal_value": float(self.mean_optimal_value),
            "variance": float(self.variance),
            "std_dev": float(self.std_dev),
            "coefficient_of_variation": float(self.coefficient_of_variation),
            "min_value": float(self.min_value),
            "max_value": float(self.max_value),
            "value_range": float(self.value_range),
            "convergence_speed": float(self.convergence_speed),
            "stability_score": float(self.stability_score),
            "is_stable": self.is_stable,
            "num_windows": len(self.window_results),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StabilityReport:
    """Comprehensive parameter stability analysis report."""

    analysis_date: datetime = field(default_factory=datetime.now)
    parameter_results: Dict[str, ParameterStabilityResult] = field(default_factory=dict)
    stable_parameters: List[str] = field(default_factory=list)
    unstable_parameters: List[str] = field(default_factory=list)
    overall_stability_score: float = 0.0  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "stable_parameters": self.stable_parameters,
            "unstable_parameters": self.unstable_parameters,
            "overall_stability_score": float(self.overall_stability_score),
            "parameter_results": {
                name: result.to_dict() for name, result in self.parameter_results.items()
            },
        }

    def to_json(self, filepath: Optional[Path] = None) -> str:
        """Serialize to JSON string or file."""
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(json_str)
            logger.info(f"Stability report saved to {filepath}")
        return json_str


class ParameterStabilityMetrics:
    """
    Analyze parameter stability across multiple windows/folds/periods.

    A parameter is stable if its optimal value is consistent across different time
    periods or validation folds. Unstable parameters suggest curve-fitting.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize parameter stability metrics analyzer.

        Args:
            config: Configuration dictionary
        """
        self.config = config or self._get_default_config()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "stability": {
                "stability_thresholds": {
                    "stable": 70.0,  # Score >= 70 is stable
                    "unstable": 40.0,  # Score < 40 is unstable
                },
                "convergence": {
                    "window_weight_decay": 0.1,  # Later windows matter more (0.1 = 10% decay per window)
                    "min_windows": 3,  # Minimum windows to measure stability
                },
            }
        }

    def calculate_variance_across_windows(
        self,
        parameter_name: str,
        window_results: List[WindowOptimalValue],
    ) -> ParameterStabilityResult:
        """
        Calculate variance of parameter values across windows.

        High variance = parameter bounces around = unstable (curve-fitted)
        Low variance = parameter consistent = stable

        Args:
            parameter_name: Name of the parameter
            window_results: List of optimal values across windows

        Returns:
            ParameterStabilityResult with variance metrics
        """
        result = ParameterStabilityResult(
            parameter_name=parameter_name,
            window_results=window_results,
        )

        if len(window_results) < 1:
            logger.warning(f"No window results for {parameter_name}")
            return result

        # Extract optimal values
        optimal_values = [wr.optimal_value for wr in window_results]

        # Calculate basic statistics
        result.mean_optimal_value = float(np.mean(optimal_values))
        result.min_value = float(np.min(optimal_values))
        result.max_value = float(np.max(optimal_values))
        result.value_range = result.max_value - result.min_value

        if len(optimal_values) >= 2:
            result.variance = float(np.var(optimal_values))
            result.std_dev = float(np.std(optimal_values))

            # Coefficient of variation (std / mean) - normalized measure
            if result.mean_optimal_value != 0:
                result.coefficient_of_variation = result.std_dev / abs(result.mean_optimal_value)
            else:
                result.coefficient_of_variation = 0.0

        logger.debug(
            f"{parameter_name}: mean={result.mean_optimal_value:.2f}, "
            f"std={result.std_dev:.4f}, cv={result.coefficient_of_variation:.4f}"
        )

        return result

    def calculate_convergence_speed(
        self,
        parameter_name: str,
        window_results: List[WindowOptimalValue],
    ) -> float:
        """
        Calculate convergence speed: how quickly parameter values stabilize.

        Returns:
            0-1 score where 1 = fast convergence (stable), 0 = no convergence (unstable)
        """
        if len(window_results) < 2:
            return 1.0  # Can't measure convergence with < 2 windows

        optimal_values = [wr.optimal_value for wr in window_results]
        decay = self.config["stability"]["convergence"]["window_weight_decay"]

        # Calculate weighted variance: early windows have less weight
        weighted_sum = 0.0
        weight_sum = 0.0

        for i, value in enumerate(optimal_values):
            # Weight increases with window index (later windows matter more)
            weight = np.exp(i * decay)
            weighted_sum += (value - np.mean(optimal_values)) ** 2 * weight
            weight_sum += weight

        if weight_sum > 0:
            weighted_variance = weighted_sum / weight_sum
        else:
            weighted_variance = 0.0

        # Convergence speed: inverse relationship with variance
        # Low variance = high convergence (1.0)
        # High variance = low convergence (0.0)
        max_variance = np.var(optimal_values)
        if max_variance > 0:
            convergence = 1.0 - min(weighted_variance / max_variance, 1.0)
        else:
            convergence = 1.0

        return float(convergence)

    def calculate_stability_score(
        self,
        result: ParameterStabilityResult,
    ) -> float:
        """
        Calculate composite stability score (0-100).

        Considers:
        1. Coefficient of variation (normalized variance)
        2. Convergence speed
        3. Number of windows (more windows = higher confidence)

        Score formula:
        - CV score: 100 * (1 - min(CV, 1)) = higher for low variance
        - Convergence score: 100 * convergence_speed
        - Window confidence: min(windows / 8, 1) * 20 points
        """
        if len(result.window_results) == 0:
            return 0.0

        # CV-based score (40% of total)
        cv = result.coefficient_of_variation
        cv_score = max(0.0, 40.0 * (1.0 - min(cv / 1.0, 1.0)))  # cv > 1 = unstable

        # Convergence-based score (40% of total)
        convergence_score = 40.0 * result.convergence_speed

        # Window confidence (20% of total)
        n_windows = len(result.window_results)
        window_confidence = min(n_windows / 8.0, 1.0) * 20.0

        total_score = cv_score + convergence_score + window_confidence

        return float(min(total_score, 100.0))

    def analyze_parameter_stability(
        self,
        parameters: Dict[str, List[WindowOptimalValue]],
    ) -> StabilityReport:
        """
        Analyze stability of multiple parameters across windows.

        Args:
            parameters: Dict mapping parameter names to list of WindowOptimalValue objects

        Returns:
            Comprehensive stability analysis report
        """
        logger.info(f"Starting stability analysis on {len(parameters)} parameters")

        report = StabilityReport()
        stable_threshold = self.config["stability"]["stability_thresholds"]["stable"]
        unstable_threshold = self.config["stability"]["stability_thresholds"]["unstable"]

        for param_name, window_results in parameters.items():
            logger.debug(f"Analyzing stability of {param_name}")

            # Calculate variance across windows
            result = self.calculate_variance_across_windows(param_name, window_results)

            # Calculate convergence speed
            result.convergence_speed = self.calculate_convergence_speed(param_name, window_results)

            # Calculate composite stability score
            result.stability_score = self.calculate_stability_score(result)

            # Classify as stable or unstable
            if result.stability_score >= stable_threshold:
                result.is_stable = True
                report.stable_parameters.append(param_name)
            elif result.stability_score < unstable_threshold:
                report.unstable_parameters.append(param_name)

            report.parameter_results[param_name] = result

        # Calculate overall stability score
        report.overall_stability_score = self._calculate_overall_stability(report)

        logger.info(
            f"Stability analysis complete. "
            f"Stable: {len(report.stable_parameters)}, "
            f"Unstable: {len(report.unstable_parameters)}"
        )

        return report

    def _calculate_overall_stability(self, report: StabilityReport) -> float:
        """
        Calculate overall portfolio stability score (0-100).

        Formula: Average stability score with weight towards stable parameters.
        """
        if not report.parameter_results:
            return 0.0

        scores = [result.stability_score for result in report.parameter_results.values()]

        # Average score
        avg_score = float(np.mean(scores))

        # Boost for having many stable parameters
        stable_ratio = len(report.stable_parameters) / len(report.parameter_results)
        stability_bonus = stable_ratio * 10.0  # Up to 10 point bonus

        total_score = avg_score + stability_bonus

        return float(min(total_score, 100.0))

    def get_parameter_plateau_width(
        self,
        result: ParameterStabilityResult,
        acceptable_variance_ratio: float = 0.2,
    ) -> float:
        """
        Get width of "good performance zone" around mean optimal value.

        Parameters with wide plateaus are more robust than those with narrow peaks.

        Args:
            result: ParameterStabilityResult
            acceptable_variance_ratio: What ratio of total variance is acceptable (0.2 = 20%)

        Returns:
            Width as percentage of mean value
        """
        if result.mean_optimal_value == 0 or result.std_dev == 0:
            return 0.0

        # Acceptable variance = acceptable_variance_ratio * total_variance
        acceptable_variance = acceptable_variance_ratio * result.variance

        if acceptable_variance > 0:
            # Approximate plateau width as 2 * std_dev at acceptable variance level
            plateau_width_in_units = 2.0 * np.sqrt(acceptable_variance)
        else:
            plateau_width_in_units = 0.0

        # Convert to percentage of mean
        if result.mean_optimal_value != 0:
            plateau_width_pct = plateau_width_in_units / abs(result.mean_optimal_value)
        else:
            plateau_width_pct = 0.0

        return float(min(plateau_width_pct, 1.0))  # Cap at 100%

    def rank_parameters_by_stability(
        self,
        report: StabilityReport,
    ) -> List[Tuple[str, float]]:
        """
        Rank parameters by stability score (highest to lowest).

        Returns:
            List of (parameter_name, stability_score) tuples
        """
        rankings = [
            (name, result.stability_score) for name, result in report.parameter_results.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def detect_unstable_parameters(
        self,
        report: StabilityReport,
        threshold: float = 50.0,
    ) -> List[str]:
        """
        Detect parameters that may be curve-fitted (unstable).

        Args:
            report: StabilityReport
            threshold: Stability score threshold below which parameter is considered unstable

        Returns:
            List of unstable parameter names
        """
        return [
            name
            for name, result in report.parameter_results.items()
            if result.stability_score < threshold
        ]

    def recommend_parameter_simplification(
        self,
        report: StabilityReport,
    ) -> Dict[str, str]:
        """
        Recommend which parameters could be simplified or removed.

        Returns:
            Dict mapping parameter names to recommendations
        """
        recommendations = {}

        for param_name, result in report.parameter_results.items():
            if result.stability_score < 30.0:
                recommendations[param_name] = (
                    f"REMOVE: Very unstable (score={result.stability_score:.1f}). "
                    f"Parameter varies too much across windows."
                )
            elif result.stability_score < 50.0:
                recommendations[param_name] = (
                    f"SIMPLIFY: Unstable (score={result.stability_score:.1f}). "
                    f"Consider fixed value or reduce complexity."
                )
            elif 50.0 <= result.stability_score < 70.0:
                recommendations[param_name] = (
                    f"MONITOR: Moderately stable (score={result.stability_score:.1f}). "
                    f"Watch for consistency in production."
                )
            elif result.stability_score >= 90.0:
                recommendations[param_name] = (
                    f"EXCELLENT: Very stable (score={result.stability_score:.1f}). "
                    f"Robust parameter, safe to use."
                )

        return recommendations

    def print_stability_report(self, report: StabilityReport) -> None:
        """Print human-readable stability analysis report."""
        print("\n" + "=" * 80)
        print("PARAMETER STABILITY REPORT")
        print("=" * 80)
        print(f"Analysis Date: {report.analysis_date.isoformat()}")
        print(f"Overall Stability Score: {report.overall_stability_score:.1f}/100")
        print(f"\nTotal Parameters Analyzed: {len(report.parameter_results)}")
        print(f"  - Stable: {len(report.stable_parameters)}")
        print(f"  - Unstable: {len(report.unstable_parameters)}")

        print("\n" + "-" * 80)
        print("PARAMETER RANKINGS (by stability)")
        print("-" * 80)

        rankings = self.rank_parameters_by_stability(report)
        for rank, (param_name, score) in enumerate(rankings, 1):
            result = report.parameter_results[param_name]
            status = "✓ STABLE" if result.is_stable else "✗ UNSTABLE"
            print(
                f"{rank}. {param_name:25s} | Score: {score:6.1f}/100 | {status:15s} | "
                f"CV: {result.coefficient_of_variation:.4f}"
            )

        recommendations = self.recommend_parameter_simplification(report)
        if recommendations:
            print("\n" + "-" * 80)
            print("RECOMMENDATIONS")
            print("-" * 80)
            for param_name, recommendation in recommendations.items():
                print(f"{param_name}: {recommendation}")

        print("\n" + "=" * 80)
