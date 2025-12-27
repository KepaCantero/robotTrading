"""
Sensitivity Analysis Framework (TASK-6.1 Phase 1)

Measures how performance metrics change when varying each parameter.
Core capability: elasticity analysis to identify critical vs robust parameters.

Elasticity = % change in Sharpe / % change in parameter
- Elasticity > 2.0: CRITICAL parameter (small changes = big impact)
- Elasticity 0.5-2.0: NORMAL parameter (balanced sensitivity)
- Elasticity < 0.5: ROBUST parameter (insensitive to changes)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis for a single parameter."""

    parameter_name: str
    base_value: Union[float, int]
    variations_tested: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    elasticity_score: float = 0.0
    sensitivity_level: str = "UNKNOWN"  # ROBUST, NORMAL, CRITICAL
    optimal_value: Optional[Union[float, int]] = None
    plateau_width: float = 0.0  # Width of good performance zone around optimal
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    monte_carlo_results: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "parameter_name": self.parameter_name,
            "base_value": self.base_value,
            "elasticity_score": float(self.elasticity_score),
            "sensitivity_level": self.sensitivity_level,
            "optimal_value": self.optimal_value,
            "plateau_width": float(self.plateau_width),
            "confidence_interval_95": self.confidence_interval_95,
            "variations_tested": self.variations_tested,
            "monte_carlo_results": self.monte_carlo_results,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SensitivityReport:
    """Comprehensive sensitivity analysis report."""

    analysis_date: datetime = field(default_factory=datetime.now)
    parameter_results: Dict[str, SensitivityResult] = field(default_factory=dict)
    stability_heatmap: Dict[str, Dict[float, float]] = field(
        default_factory=dict
    )  # param -> variation -> performance
    robust_parameters: List[str] = field(default_factory=list)
    critical_parameters: List[str] = field(default_factory=list)
    normal_parameters: List[str] = field(default_factory=list)
    overall_robustness_score: float = 0.0  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "parameter_results": {
                name: result.to_dict() for name, result in self.parameter_results.items()
            },
            "stability_heatmap": self.stability_heatmap,
            "robust_parameters": self.robust_parameters,
            "critical_parameters": self.critical_parameters,
            "normal_parameters": self.normal_parameters,
            "overall_robustness_score": float(self.overall_robustness_score),
        }

    def to_json(self, filepath: Optional[Path] = None) -> str:
        """Serialize to JSON string or file."""
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(json_str)
            logger.info(f"Sensitivity report saved to {filepath}")
        return json_str


class SensitivityAnalyzer:
    """
    Analyze parameter sensitivity to identify robust vs critical parameters.

    Core concept: Test each parameter at multiple variation levels (±10%, ±5%, base)
    and measure how sharply performance changes.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        backtest_function: Optional[Callable] = None,
    ):
        """
        Initialize sensitivity analyzer.

        Args:
            config: Configuration dictionary with sensitivity settings
            backtest_function: Function to run backtests (signature: backtest_function(params) -> metrics_dict)
        """
        self.config = config or self._get_default_config()
        self.backtest_function = backtest_function
        self.analysis_cache: Dict[str, Any] = {}

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default sensitivity analysis configuration."""
        return {
            "sensitivity": {
                "variation_steps": [-0.10, -0.05, 0.0, 0.05, 0.10],
                "elasticity_thresholds": {
                    "robust": (0.0, 0.5),  # elasticity < 0.5 = robust
                    "normal": (0.5, 2.0),  # 0.5 <= elasticity < 2.0 = normal
                    "critical": (2.0, float("inf")),  # elasticity >= 2.0 = critical
                },
                "monte_carlo": {
                    "enabled": True,
                    "n_simulations": 1000,
                    "variation_band": 0.10,  # ±10% band for random variations
                    "confidence_level": 0.95,
                },
                "plateau_detection": {
                    "enabled": True,
                    "threshold_drop": 0.05,  # Performance drop within 5% of optimal
                },
            }
        }

    def analyze_parameter_sensitivity(
        self,
        initial_params: Dict[str, Union[float, int]],
        performance_metric: str = "sharpe_ratio",
    ) -> SensitivityReport:
        """
        Analyze sensitivity of each parameter by testing variations.

        Args:
            initial_params: Base parameter values to test
            performance_metric: Performance metric to optimize (sharpe_ratio, total_return, calmar_ratio)

        Returns:
            Comprehensive sensitivity analysis report
        """
        logger.info(f"Starting sensitivity analysis on {len(initial_params)} parameters")

        if not self.backtest_function:
            raise ValueError("backtest_function must be provided")

        report = SensitivityReport()
        variation_steps = self.config["sensitivity"]["variation_steps"]

        # Analyze each parameter individually
        for param_name, param_value in initial_params.items():
            logger.info(f"Analyzing parameter: {param_name} (base value: {param_value})")

            result = self._analyze_single_parameter(
                param_name, param_value, initial_params, variation_steps, performance_metric
            )

            report.parameter_results[param_name] = result
            report.stability_heatmap[param_name] = result.variations_tested

            # Classify parameter by sensitivity level
            if result.sensitivity_level == "ROBUST":
                report.robust_parameters.append(param_name)
            elif result.sensitivity_level == "CRITICAL":
                report.critical_parameters.append(param_name)
            else:
                report.normal_parameters.append(param_name)

        # Calculate overall robustness score
        report.overall_robustness_score = self._calculate_overall_robustness(report)

        logger.info(
            f"Sensitivity analysis complete. "
            f"Robust: {len(report.robust_parameters)}, "
            f"Normal: {len(report.normal_parameters)}, "
            f"Critical: {len(report.critical_parameters)}"
        )

        return report

    def _analyze_single_parameter(
        self,
        param_name: str,
        param_value: Union[float, int],
        base_params: Dict[str, Union[float, int]],
        variation_steps: List[float],
        performance_metric: str,
    ) -> SensitivityResult:
        """
        Analyze sensitivity of a single parameter.

        Tests variations: -10%, -5%, 0%, +5%, +10% of base value.
        Calculates elasticity: % change in performance / % change in parameter.
        """
        result = SensitivityResult(parameter_name=param_name, base_value=param_value)
        performances = {}
        varied_values = {}

        # Test each variation level
        for variation_pct in variation_steps:
            # Calculate varied value
            if isinstance(param_value, int):
                varied_value = int(param_value * (1 + variation_pct))
            else:
                varied_value = param_value * (1 + variation_pct)

            # Ensure value stays within reasonable bounds (e.g., > 0)
            if varied_value <= 0:
                logger.warning(
                    f"Skipping invalid variation {variation_pct} for {param_name} "
                    f"(resulted in {varied_value})"
                )
                continue

            varied_values[variation_pct] = varied_value

            # Create test params with this variation
            test_params = base_params.copy()
            test_params[param_name] = varied_value

            try:
                # Run backtest with varied parameters
                metrics = self.backtest_function(test_params)
                perf_value = metrics.get(performance_metric, 0.0)
                performances[variation_pct] = perf_value

                result.variations_tested[f"{variation_pct:+.1%}"] = {
                    "parameter_value": float(varied_value),
                    "performance": float(perf_value),
                    "metric": performance_metric,
                }

                logger.debug(
                    f"  Variation {variation_pct:+.1%}: {performance_metric}={perf_value:.4f}"
                )

            except Exception as e:
                logger.error(f"Error testing variation {variation_pct} for {param_name}: {e}")
                continue

        if len(performances) < 2:
            logger.warning(
                f"Not enough valid variations for {param_name}, skipping elasticity calculation"
            )
            return result

        # Calculate elasticity
        base_perf = performances.get(0.0)
        if base_perf is None or base_perf == 0:
            logger.warning(f"Base performance for {param_name} is invalid, using fallback")
            base_perf = np.mean(list(performances.values()))

        result.elasticity_score = self._calculate_elasticity(performances, varied_values)
        result.sensitivity_level = self._classify_sensitivity(result.elasticity_score)

        # Detect optimal value and plateau width
        if performances:
            optimal_variation = max(performances, key=performances.get)
            result.optimal_value = varied_values[optimal_variation]
            result.plateau_width = self._calculate_plateau_width(
                performances, varied_values, base_perf
            )

        # Calculate confidence intervals
        perf_values = list(performances.values())
        if len(perf_values) >= 2:
            result.confidence_interval_95 = (
                np.percentile(perf_values, 2.5),
                np.percentile(perf_values, 97.5),
            )

        # Run Monte Carlo sensitivity if enabled
        mc_config = self.config.get("sensitivity", {}).get("monte_carlo", {})
        if mc_config.get("enabled", True):
            result.monte_carlo_results = self._run_monte_carlo_sensitivity(
                param_name, param_value, base_params, performance_metric
            )

        return result

    def _calculate_elasticity(
        self, performances: Dict[float, float], varied_values: Dict[float, Union[float, int]]
    ) -> float:
        """
        Calculate elasticity: % change in performance / % change in parameter.

        Returns:
            Elasticity score (higher = more sensitive to changes)
        """
        if len(performances) < 2:
            return 0.0

        # Use ±5% and ±10% variations for calculation
        base_perf = performances.get(0.0)
        if not base_perf or base_perf == 0:
            return 0.0

        elasticities = []

        for variation_pct in [0.05, 0.10]:
            if variation_pct not in performances or -variation_pct not in performances:
                continue

            up_perf = performances.get(variation_pct, base_perf)
            down_perf = performances.get(-variation_pct, base_perf)

            # Calculate average elasticity across up and down directions
            if up_perf != base_perf:
                pct_perf_change = (up_perf - base_perf) / abs(base_perf) if base_perf != 0 else 0.0
                elasticity_up = abs(pct_perf_change / variation_pct) if variation_pct != 0 else 0.0
                elasticities.append(elasticity_up)

            if down_perf != base_perf:
                pct_perf_change = (
                    (down_perf - base_perf) / abs(base_perf) if base_perf != 0 else 0.0
                )
                elasticity_down = (
                    abs(pct_perf_change / (-variation_pct)) if variation_pct != 0 else 0.0
                )
                elasticities.append(elasticity_down)

        return float(np.mean(elasticities)) if elasticities else 0.0

    def _classify_sensitivity(self, elasticity_score: float) -> str:
        """Classify parameter sensitivity based on elasticity score."""
        thresholds = self.config["sensitivity"]["elasticity_thresholds"]

        if elasticity_score < thresholds["robust"][1]:
            return "ROBUST"
        elif elasticity_score < thresholds["critical"][0]:
            return "NORMAL"
        else:
            return "CRITICAL"

    def _calculate_plateau_width(
        self,
        performances: Dict[float, float],
        varied_values: Dict[float, Union[float, int]],
        base_perf: float,
    ) -> float:
        """
        Calculate plateau width: how wide is the zone of good performance.

        Returns:
            Width as percentage of base value
        """
        if not performances or base_perf == 0:
            return 0.0

        threshold_drop = self.config["sensitivity"]["plateau_detection"]["threshold_drop"]
        acceptable_perf = base_perf * (1 - threshold_drop)

        # Find variations where performance is still acceptable
        acceptable_variations = []
        for variation_pct, perf in performances.items():
            if perf >= acceptable_perf:
                acceptable_variations.append(variation_pct)

        if len(acceptable_variations) < 2:
            return 0.0

        # Calculate width as difference between max and min acceptable variations
        max_var = max(acceptable_variations)
        min_var = min(acceptable_variations)
        return abs(max_var - min_var)

    def _run_monte_carlo_sensitivity(
        self,
        param_name: str,
        param_value: Union[float, int],
        base_params: Dict[str, Union[float, int]],
        performance_metric: str,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo sensitivity test with random parameter variations.

        Tests 1000 random combinations within ±10% band and calculates
        confidence intervals on performance outcomes.
        """
        mc_config = self.config["sensitivity"]["monte_carlo"]
        n_simulations = mc_config.get("n_simulations", 1000)
        variation_band = mc_config.get("variation_band", 0.10)
        confidence_level = mc_config.get("confidence_level", 0.95)

        logger.info(
            f"Running Monte Carlo sensitivity for {param_name} ({n_simulations} simulations)"
        )

        results = []

        for _ in range(n_simulations):
            # Generate random variation within ±variation_band
            random_variation = np.random.uniform(-variation_band, variation_band)

            # Calculate varied value
            if isinstance(param_value, int):
                varied_value = int(param_value * (1 + random_variation))
            else:
                varied_value = param_value * (1 + random_variation)

            if varied_value <= 0:
                continue

            # Test this variation
            test_params = base_params.copy()
            test_params[param_name] = varied_value

            try:
                metrics = self.backtest_function(test_params)
                perf_value = metrics.get(performance_metric, 0.0)
                results.append(perf_value)
            except Exception as e:
                logger.debug(f"Error in Monte Carlo iteration: {e}")
                continue

        if not results:
            return {}

        # Calculate statistics
        results_array = np.array(results)
        percentile_lower = (1 - confidence_level) / 2 * 100
        percentile_upper = (1 + confidence_level) / 2 * 100

        return {
            "mean": float(np.mean(results_array)),
            "std": float(np.std(results_array)),
            "min": float(np.min(results_array)),
            "max": float(np.max(results_array)),
            f"percentile_{percentile_lower:.1f}": float(
                np.percentile(results_array, percentile_lower)
            ),
            f"percentile_{percentile_upper:.1f}": float(
                np.percentile(results_array, percentile_upper)
            ),
            "n_simulations": len(results),
            "success_rate": float(len(results) / n_simulations),
        }

    def _calculate_overall_robustness(self, report: SensitivityReport) -> float:
        """
        Calculate overall robustness score (0-100).

        Robustness is higher when more parameters are ROBUST and fewer are CRITICAL.
        """
        total_params = (
            len(report.robust_parameters)
            + len(report.normal_parameters)
            + len(report.critical_parameters)
        )

        if total_params == 0:
            return 0.0

        # Score formula: robust params increase score, critical params decrease
        robust_weight = 100 / total_params if total_params > 0 else 0
        normal_weight = 50 / total_params if total_params > 0 else 0
        critical_penalty = -100 / total_params if total_params > 0 else 0

        score = (
            len(report.robust_parameters) * robust_weight
            + len(report.normal_parameters) * normal_weight
            + len(report.critical_parameters) * critical_penalty
        )

        return max(0.0, min(100.0, score))

    def get_sensitivity_summary(self, report: SensitivityReport) -> Dict[str, Any]:
        """Get readable summary of sensitivity analysis."""
        return {
            "analysis_date": report.analysis_date.isoformat(),
            "total_parameters_analyzed": len(report.parameter_results),
            "robust_parameters": report.robust_parameters,
            "critical_parameters": report.critical_parameters,
            "normal_parameters": report.normal_parameters,
            "overall_robustness_score": report.overall_robustness_score,
            "parameter_elasticities": {
                name: {
                    "elasticity": result.elasticity_score,
                    "sensitivity_level": result.sensitivity_level,
                    "optimal_value": result.optimal_value,
                    "plateau_width": result.plateau_width,
                }
                for name, result in report.parameter_results.items()
            },
        }

    def print_sensitivity_report(self, report: SensitivityReport) -> None:
        """Print human-readable sensitivity analysis report."""
        print("\n" + "=" * 80)
        print("SENSITIVITY ANALYSIS REPORT")
        print("=" * 80)
        print(f"Analysis Date: {report.analysis_date.isoformat()}")
        print(f"Overall Robustness Score: {report.overall_robustness_score:.1f}/100")
        print(f"\nTotal Parameters Analyzed: {len(report.parameter_results)}")
        print(f"  - Robust (elasticity < 0.5): {len(report.robust_parameters)}")
        print(f"  - Normal (0.5 ≤ elasticity < 2.0): {len(report.normal_parameters)}")
        print(f"  - Critical (elasticity ≥ 2.0): {len(report.critical_parameters)}")

        print("\n" + "-" * 80)
        print("PARAMETER DETAILS")
        print("-" * 80)

        for param_name, result in sorted(report.parameter_results.items()):
            print(f"\n{param_name}:")
            print(f"  Base Value: {result.base_value}")
            print(f"  Optimal Value: {result.optimal_value}")
            print(f"  Elasticity Score: {result.elasticity_score:.4f}")
            print(f"  Sensitivity Level: {result.sensitivity_level}")
            print(f"  Plateau Width: {result.plateau_width:.2%}")
            if result.confidence_interval_95[1] > result.confidence_interval_95[0]:
                print(
                    f"  95% CI: [{result.confidence_interval_95[0]:.4f}, {result.confidence_interval_95[1]:.4f}]"
                )

        print("\n" + "=" * 80)
