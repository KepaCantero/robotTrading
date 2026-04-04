"""
Unit Tests: Parameter Stability Metrics (TASK-6.1 Phase 2)

Tests for:
- Variance calculation across windows
- Convergence speed detection
- Stability scoring
- Parameter ranking and recommendations
"""

import json
import logging
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from app.domain.optimization.parameter_stability_metrics import (
    ParameterStabilityMetrics,
    ParameterStabilityResult,
    StabilityReport,
    WindowOptimalValue,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWindowOptimalValue:
    """Tests for WindowOptimalValue data structure."""

    def test_create_window_result(self):
        """Test creation of WindowOptimalValue."""
        window_result = WindowOptimalValue(
            window_id=1,
            parameter_name="rsi_threshold",
            optimal_value=40,
            performance_metric=0.85,
        )

        assert window_result.window_id == 1
        assert window_result.parameter_name == "rsi_threshold"
        assert window_result.optimal_value == 40
        assert window_result.performance_metric == 0.85


class TestParameterStabilityMetricsInitialization:
    """Tests for ParameterStabilityMetrics initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default configuration."""
        analyzer = ParameterStabilityMetrics()

        assert analyzer.config is not None
        assert "stability" in analyzer.config

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        custom_config = {
            "stability": {
                "stability_thresholds": {"stable": 75.0, "unstable": 35.0},
            }
        }

        analyzer = ParameterStabilityMetrics(config=custom_config)

        assert analyzer.config == custom_config


class TestVarianceCalculation:
    """Tests for variance calculation across windows."""

    def test_stable_parameter_low_variance(self):
        """Test detection of stable parameter with low variance."""
        analyzer = ParameterStabilityMetrics()

        # Stable parameter: values are consistent (39, 40, 41, 40)
        window_results = [
            WindowOptimalValue(1, "rsi_threshold", 39, 0.85),
            WindowOptimalValue(2, "rsi_threshold", 40, 0.86),
            WindowOptimalValue(3, "rsi_threshold", 41, 0.85),
            WindowOptimalValue(4, "rsi_threshold", 40, 0.87),
        ]

        result = analyzer.calculate_variance_across_windows("rsi_threshold", window_results)

        assert result.coefficient_of_variation < 0.05  # CV < 5% = stable
        assert result.std_dev < 1.0

    def test_unstable_parameter_high_variance(self):
        """Test detection of unstable parameter with high variance."""
        analyzer = ParameterStabilityMetrics()

        # Unstable parameter: values bounce around (5, 50, 10, 60)
        window_results = [
            WindowOptimalValue(1, "rsi_threshold", 5, 0.80),
            WindowOptimalValue(2, "rsi_threshold", 50, 0.85),
            WindowOptimalValue(3, "rsi_threshold", 10, 0.82),
            WindowOptimalValue(4, "rsi_threshold", 60, 0.78),
        ]

        result = analyzer.calculate_variance_across_windows("rsi_threshold", window_results)

        assert result.coefficient_of_variation > 0.7  # CV > 70% = unstable
        assert result.std_dev > 20.0

    def test_single_window_result(self):
        """Test handling of single window result."""
        analyzer = ParameterStabilityMetrics()

        window_results = [WindowOptimalValue(1, "rsi_threshold", 40, 0.85)]

        result = analyzer.calculate_variance_across_windows("rsi_threshold", window_results)

        assert result.mean_optimal_value == 40.0
        assert result.variance == 0.0

    def test_empty_window_results(self):
        """Test handling of empty window results."""
        analyzer = ParameterStabilityMetrics()

        result = analyzer.calculate_variance_across_windows("rsi_threshold", [])

        assert result.parameter_name == "rsi_threshold"
        assert len(result.window_results) == 0


class TestConvergenceSpeed:
    """Tests for convergence speed calculation."""

    def test_fast_convergence(self):
        """Test detection of fast convergence."""
        analyzer = ParameterStabilityMetrics()

        # Fast convergence: values stabilize after first few windows
        window_results = [
            WindowOptimalValue(1, "rsi_threshold", 30, 0.80),
            WindowOptimalValue(2, "rsi_threshold", 38, 0.84),
            WindowOptimalValue(3, "rsi_threshold", 40, 0.85),
            WindowOptimalValue(4, "rsi_threshold", 40, 0.86),
            WindowOptimalValue(5, "rsi_threshold", 40, 0.85),
        ]

        convergence = analyzer.calculate_convergence_speed("rsi_threshold", window_results)

        assert convergence > 0.0, "Should show some convergence (not zero)"
        assert convergence < 1.0, "Perfect convergence only with single value"

    def test_slow_convergence(self):
        """Test detection of slow convergence."""
        analyzer = ParameterStabilityMetrics()

        # Slow convergence: values keep bouncing
        window_results = [
            WindowOptimalValue(1, "rsi_threshold", 30, 0.80),
            WindowOptimalValue(2, "rsi_threshold", 50, 0.83),
            WindowOptimalValue(3, "rsi_threshold", 35, 0.82),
            WindowOptimalValue(4, "rsi_threshold", 55, 0.81),
            WindowOptimalValue(5, "rsi_threshold", 40, 0.80),
        ]

        convergence = analyzer.calculate_convergence_speed("rsi_threshold", window_results)

        assert convergence < 0.5, "Should show slow convergence"

    def test_single_window_convergence(self):
        """Test convergence calculation with single window."""
        analyzer = ParameterStabilityMetrics()

        window_results = [WindowOptimalValue(1, "rsi_threshold", 40, 0.85)]

        convergence = analyzer.calculate_convergence_speed("rsi_threshold", window_results)

        assert convergence == 1.0  # Can't measure, assume full convergence


class TestStabilityScoring:
    """Tests for stability score calculation."""

    def test_stable_parameter_high_score(self):
        """Test scoring of stable parameter."""
        analyzer = ParameterStabilityMetrics()

        # Create stable result
        window_results = [
            WindowOptimalValue(i, "rsi_threshold", 40 + np.random.randint(-1, 2), 0.85)
            for i in range(8)
        ]

        result = analyzer.calculate_variance_across_windows("rsi_threshold", window_results)
        result.convergence_speed = 0.9

        stability_score = analyzer.calculate_stability_score(result)

        assert stability_score > 70, "Stable parameter should score > 70"

    def test_unstable_parameter_low_score(self):
        """Test scoring of unstable parameter."""
        analyzer = ParameterStabilityMetrics()

        # Create unstable result with very high CV
        window_results = [
            WindowOptimalValue(i, "rsi_threshold", value, 0.85)
            for i, value in enumerate([10, 80, 20, 70, 15, 75, 25, 85])  # High variance
        ]

        result = analyzer.calculate_variance_across_windows("rsi_threshold", window_results)
        result.convergence_speed = 0.1  # Very low convergence

        stability_score = analyzer.calculate_stability_score(result)

        assert stability_score < 60, "Unstable parameter with high variance should score < 60"

    def test_stability_score_range(self):
        """Test that stability score is in valid range."""
        analyzer = ParameterStabilityMetrics()

        window_results = [WindowOptimalValue(i, "param", 40 + i, 0.85) for i in range(5)]

        result = analyzer.calculate_variance_across_windows("param", window_results)
        result.convergence_speed = 0.5

        score = analyzer.calculate_stability_score(result)

        assert 0.0 <= score <= 100.0


class TestAnalyzeParameterStability:
    """Tests for comprehensive stability analysis."""

    def test_analyze_multiple_parameters(self):
        """Test analysis of multiple parameters."""
        analyzer = ParameterStabilityMetrics()

        # Parameter 1: stable
        param1_results = [WindowOptimalValue(i, "rsi_threshold", 40, 0.85) for i in range(5)]

        # Parameter 2: unstable
        param2_results = [
            WindowOptimalValue(i, "momentum_threshold", 10 + i * 10, 0.80) for i in range(5)
        ]

        parameters = {
            "rsi_threshold": param1_results,
            "momentum_threshold": param2_results,
        }

        report = analyzer.analyze_parameter_stability(parameters)

        assert len(report.parameter_results) == 2
        assert "rsi_threshold" in report.parameter_results
        assert "momentum_threshold" in report.parameter_results

    def test_stable_parameters_identified(self):
        """Test that stable parameters are correctly identified."""
        analyzer = ParameterStabilityMetrics()

        stable_results = [WindowOptimalValue(i, "stable_param", 40, 0.85) for i in range(6)]

        parameters = {"stable_param": stable_results}
        report = analyzer.analyze_parameter_stability(parameters)

        assert "stable_param" in report.stable_parameters

    def test_unstable_parameters_identified(self):
        """Test that unstable parameters are correctly identified."""
        analyzer = ParameterStabilityMetrics()

        unstable_results = [
            WindowOptimalValue(i, "unstable_param", 10 + i * 15, 0.80) for i in range(6)
        ]

        parameters = {"unstable_param": unstable_results}
        report = analyzer.analyze_parameter_stability(parameters)

        # Parameter should be in unstable or neither (depending on threshold)
        assert (
            "unstable_param" in report.unstable_parameters
            or "unstable_param" not in report.stable_parameters
        )

    def test_overall_stability_score(self):
        """Test overall stability score calculation."""
        analyzer = ParameterStabilityMetrics()

        param_results = [
            WindowOptimalValue(i, f"param_{j}", 40, 0.85) for j in range(3) for i in range(4)
        ]

        parameters = {
            f"param_{j}": [wr for wr in param_results if wr.parameter_name == f"param_{j}"]
            for j in range(3)
        }

        report = analyzer.analyze_parameter_stability(parameters)

        assert 0.0 <= report.overall_stability_score <= 100.0


class TestParameterRanking:
    """Tests for parameter ranking by stability."""

    def test_rank_parameters_by_stability(self):
        """Test ranking of parameters by stability score."""
        analyzer = ParameterStabilityMetrics()

        # Create report with different stability scores
        report = StabilityReport()
        for i, param_name in enumerate(["param_a", "param_b", "param_c"]):
            result = ParameterStabilityResult(parameter_name=param_name)
            result.stability_score = float(80 - i * 20)  # 80, 60, 40
            report.parameter_results[param_name] = result

        rankings = analyzer.rank_parameters_by_stability(report)

        # Should be sorted highest to lowest
        assert rankings[0][0] == "param_a"
        assert rankings[1][0] == "param_b"
        assert rankings[2][0] == "param_c"
        assert rankings[0][1] > rankings[1][1] > rankings[2][1]


class TestUnstableParameterDetection:
    """Tests for unstable parameter detection."""

    def test_detect_unstable_parameters(self):
        """Test detection of unstable parameters."""
        analyzer = ParameterStabilityMetrics()

        report = StabilityReport()
        for param_name, score in [("param_a", 80), ("param_b", 40), ("param_c", 25)]:
            result = ParameterStabilityResult(parameter_name=param_name)
            result.stability_score = float(score)
            report.parameter_results[param_name] = result

        unstable = analyzer.detect_unstable_parameters(report, threshold=50.0)

        assert "param_b" in unstable
        assert "param_c" in unstable
        assert "param_a" not in unstable


class TestParameterSimplificationRecommendations:
    """Tests for parameter simplification recommendations."""

    def test_recommend_parameter_simplification(self):
        """Test generation of simplification recommendations."""
        analyzer = ParameterStabilityMetrics()

        report = StabilityReport()
        for param_name, score in [
            ("stable_param", 95),  # > 90 for EXCELLENT
            ("monitor_param", 55),
            ("unstable_param", 35),
        ]:
            result = ParameterStabilityResult(parameter_name=param_name)
            result.stability_score = float(score)
            report.parameter_results[param_name] = result

        recommendations = analyzer.recommend_parameter_simplification(report)

        assert "stable_param" in recommendations
        assert "monitor_param" in recommendations
        assert "unstable_param" in recommendations

        # Check recommendation content
        assert "EXCELLENT" in recommendations["stable_param"]
        assert "MONITOR" in recommendations["monitor_param"]
        assert "SIMPLIFY" in recommendations["unstable_param"]


class TestStabilityResultSerialization:
    """Tests for serialization of stability results."""

    def test_parameter_stability_result_to_dict(self):
        """Test conversion of ParameterStabilityResult to dict."""
        result = ParameterStabilityResult(
            parameter_name="rsi_threshold",
            mean_optimal_value=40.0,
            variance=1.0,
            stability_score=85.0,
        )

        result_dict = result.to_dict()

        assert result_dict["parameter_name"] == "rsi_threshold"
        assert result_dict["mean_optimal_value"] == 40.0
        assert result_dict["stability_score"] == 85.0

    def test_stability_report_to_dict(self):
        """Test conversion of StabilityReport to dict."""
        report = StabilityReport()
        report.stable_parameters = ["param_a"]
        report.overall_stability_score = 80.0

        report_dict = report.to_dict()

        assert report_dict["stable_parameters"] == ["param_a"]
        assert report_dict["overall_stability_score"] == 80.0

    def test_stability_report_json_serialization(self):
        """Test JSON serialization of report."""
        report = StabilityReport()
        report.stable_parameters = ["param_a"]

        json_str = report.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["stable_parameters"] == ["param_a"]


class TestPlateauWidthCalculation:
    """Tests for plateau width calculation."""

    def test_plateau_width_stable_parameter(self):
        """Test plateau width for stable parameter."""
        analyzer = ParameterStabilityMetrics()

        # Create stable result with low variance
        result = ParameterStabilityResult(parameter_name="param")
        result.mean_optimal_value = 40.0
        result.std_dev = 1.0
        result.variance = 1.0

        plateau_width = analyzer.get_parameter_plateau_width(result)

        assert plateau_width > 0.0
        assert plateau_width <= 1.0

    def test_plateau_width_zero_mean(self):
        """Test plateau width when mean is zero."""
        analyzer = ParameterStabilityMetrics()

        result = ParameterStabilityResult(parameter_name="param")
        result.mean_optimal_value = 0.0
        result.std_dev = 1.0
        result.variance = 1.0

        plateau_width = analyzer.get_parameter_plateau_width(result)

        assert plateau_width == 0.0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_parameters_dict(self):
        """Test analysis with empty parameters dictionary."""
        analyzer = ParameterStabilityMetrics()

        report = analyzer.analyze_parameter_stability({})

        assert len(report.parameter_results) == 0
        assert report.overall_stability_score == 0.0

    def test_very_large_variance(self):
        """Test handling of very large variance."""
        analyzer = ParameterStabilityMetrics()

        window_results = [WindowOptimalValue(i, "param", 10**i, 0.85) for i in range(5)]

        result = analyzer.calculate_variance_across_windows("param", window_results)

        # Should handle gracefully without overflow
        assert not np.isinf(result.variance)
        assert not np.isnan(result.variance)

    def test_negative_parameter_values(self):
        """Test handling of negative parameter values."""
        analyzer = ParameterStabilityMetrics()

        window_results = [WindowOptimalValue(i, "param", -40 + i, 0.85) for i in range(5)]

        result = analyzer.calculate_variance_across_windows("param", window_results)

        assert result.mean_optimal_value < 0
        assert not np.isnan(result.coefficient_of_variation)


class TestPrintingReport:
    """Tests for report printing functionality."""

    def test_print_stability_report(self, capsys):
        """Test that stability report can be printed."""
        analyzer = ParameterStabilityMetrics()

        report = StabilityReport()
        result = ParameterStabilityResult(
            parameter_name="param_a",
            stability_score=85.0,
            is_stable=True,
        )
        report.parameter_results["param_a"] = result
        report.stable_parameters = ["param_a"]

        # Should not raise exception
        try:
            analyzer.print_stability_report(report)
        except Exception as e:
            pytest.fail(f"print_stability_report raised exception: {e}")
