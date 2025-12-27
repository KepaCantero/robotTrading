"""
Unit Tests: Sensitivity Analysis Framework (TASK-6.1 Phase 1)

Tests for:
- SensitivityAnalyzer parameter variation analysis
- Elasticity score calculation
- Sensitivity level classification
- Plateau detection
- Monte Carlo sensitivity testing
"""

import json
import logging
from pathlib import Path
from typing import Dict, Union

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from app.optimization.sensitivity_analyzer import (
    SensitivityAnalyzer,
    SensitivityReport,
    SensitivityResult,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockBacktester:
    """Mock backtester for testing sensitivity analysis."""

    def __init__(self, performance_function=None):
        """Initialize with optional custom performance function."""
        self.call_count = 0
        self.performance_function = performance_function or self._default_performance

    def _default_performance(self, params: Dict[str, Union[float, int]]) -> Dict[str, float]:
        """Default performance function (quadratic around optimal values)."""
        # Example: Sharpe ratio is maximized at specific parameter values
        # RSI=40 optimal, momentum_threshold=20 optimal
        sharpe = 1.0

        # Penalize deviations from optimal (quadratic penalty)
        for param_name, param_value in params.items():
            if param_name == "rsi_threshold":
                optimal = 40
                sharpe -= 0.1 * ((param_value - optimal) / optimal) ** 2
            elif param_name == "momentum_threshold":
                optimal = 20
                sharpe -= 0.15 * ((param_value - optimal) / optimal) ** 2
            elif param_name == "lookback_period":
                optimal = 20
                sharpe -= 0.05 * ((param_value - optimal) / optimal) ** 2

        return {
            "sharpe_ratio": max(0.1, sharpe),  # Ensure non-negative
            "total_return": sharpe * 0.5,
            "max_drawdown": -0.15,
            "win_rate": 0.5 + (sharpe * 0.1),
        }

    def backtest(self, params: Dict[str, Union[float, int]]) -> Dict[str, float]:
        """Run backtest with given parameters."""
        self.call_count += 1
        return self.performance_function(params)


class TestSensitivityAnalyzerInitialization:
    """Tests for SensitivityAnalyzer initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default configuration."""
        analyzer = SensitivityAnalyzer()

        assert analyzer.config is not None
        assert "sensitivity" in analyzer.config
        assert "variation_steps" in analyzer.config["sensitivity"]
        assert "elasticity_thresholds" in analyzer.config["sensitivity"]

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        custom_config = {
            "sensitivity": {
                "variation_steps": [-0.20, -0.10, 0.0, 0.10, 0.20],
                "elasticity_thresholds": {
                    "robust": (0.0, 0.3),
                    "normal": (0.3, 2.0),
                    "critical": (2.0, float("inf")),
                },
            }
        }

        analyzer = SensitivityAnalyzer(config=custom_config)

        assert analyzer.config == custom_config
        assert analyzer.config["sensitivity"]["variation_steps"] == [
            -0.20,
            -0.10,
            0.0,
            0.10,
            0.20,
        ]

    def test_initialization_with_backtest_function(self):
        """Test initialization with custom backtest function."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        assert analyzer.backtest_function == mock_backtest.backtest


class TestElasticityCalculation:
    """Tests for elasticity score calculation."""

    def test_robust_parameter_elasticity(self):
        """Test elasticity calculation for robust parameter."""
        analyzer = SensitivityAnalyzer()

        # Robust parameter: performance barely changes with variation
        performances = {-0.10: 0.95, -0.05: 0.98, 0.0: 1.0, 0.05: 0.99, 0.10: 0.96}
        varied_values = {-0.10: 90, -0.05: 95, 0.0: 100, 0.05: 105, 0.10: 110}

        elasticity = analyzer._calculate_elasticity(performances, varied_values)

        assert elasticity < 0.5, "Robust parameter should have low elasticity"

    def test_critical_parameter_elasticity(self):
        """Test elasticity calculation for critical parameter."""
        analyzer = SensitivityAnalyzer()

        # Critical parameter: performance varies sharply with changes
        performances = {-0.10: 0.5, -0.05: 0.7, 0.0: 1.0, 0.05: 0.7, 0.10: 0.5}
        varied_values = {-0.10: 90, -0.05: 95, 0.0: 100, 0.05: 105, 0.10: 110}

        elasticity = analyzer._calculate_elasticity(performances, varied_values)

        assert elasticity > 1.5, "Critical parameter should have high elasticity"

    def test_elasticity_zero_base_performance(self):
        """Test elasticity when base performance is zero."""
        analyzer = SensitivityAnalyzer()

        performances = {-0.10: 0.0, -0.05: 0.0, 0.0: 0.0, 0.05: 0.0, 0.10: 0.0}
        varied_values = {-0.10: 90, -0.05: 95, 0.0: 100, 0.05: 105, 0.10: 110}

        elasticity = analyzer._calculate_elasticity(performances, varied_values)

        # Should handle zero base gracefully
        assert elasticity >= 0.0


class TestSensitivityLevelClassification:
    """Tests for sensitivity level classification."""

    def test_classify_robust(self):
        """Test classification of robust parameter."""
        analyzer = SensitivityAnalyzer()

        level = analyzer._classify_sensitivity(elasticity_score=0.3)

        assert level == "ROBUST"

    def test_classify_normal(self):
        """Test classification of normal parameter."""
        analyzer = SensitivityAnalyzer()

        level = analyzer._classify_sensitivity(elasticity_score=1.0)

        assert level == "NORMAL"

    def test_classify_critical(self):
        """Test classification of critical parameter."""
        analyzer = SensitivityAnalyzer()

        level = analyzer._classify_sensitivity(elasticity_score=2.5)

        assert level == "CRITICAL"


class TestPlateauDetection:
    """Tests for plateau width detection."""

    def test_wide_plateau(self):
        """Test detection of wide performance plateau."""
        analyzer = SensitivityAnalyzer()

        # Wide plateau: performance stays high across wide range
        performances = {-0.10: 0.95, -0.05: 0.99, 0.0: 1.0, 0.05: 0.98, 0.10: 0.96}
        varied_values = {-0.10: 90, -0.05: 95, 0.0: 100, 0.05: 105, 0.10: 110}
        base_perf = 1.0

        plateau = analyzer._calculate_plateau_width(performances, varied_values, base_perf)

        assert plateau > 0.15, "Wide plateau should be detected as wide"

    def test_narrow_peak(self):
        """Test detection of narrow performance peak."""
        analyzer = SensitivityAnalyzer()

        # Narrow peak: performance drops quickly away from optimal
        performances = {-0.10: 0.6, -0.05: 0.8, 0.0: 1.0, 0.05: 0.8, 0.10: 0.6}
        varied_values = {-0.10: 90, -0.05: 95, 0.0: 100, 0.05: 105, 0.10: 110}
        base_perf = 1.0

        plateau = analyzer._calculate_plateau_width(performances, varied_values, base_perf)

        assert plateau < 0.10, "Narrow peak should be detected as narrow"


class TestMonteCarloSensitivity:
    """Tests for Monte Carlo sensitivity analysis."""

    def test_monte_carlo_simulation_runs(self):
        """Test that Monte Carlo simulation completes successfully."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(
            config={"sensitivity": {"monte_carlo": {"enabled": True, "n_simulations": 100}}},
            backtest_function=mock_backtest.backtest,
        )

        base_params = {"rsi_threshold": 40, "momentum_threshold": 20}
        results = analyzer._run_monte_carlo_sensitivity(
            "rsi_threshold", 40, base_params, "sharpe_ratio"
        )

        assert "mean" in results
        assert "std" in results
        assert "min" in results
        assert "max" in results
        assert results["n_simulations"] > 0

    def test_monte_carlo_results_statistics(self):
        """Test that Monte Carlo results contain valid statistics."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(
            config={"sensitivity": {"monte_carlo": {"enabled": True, "n_simulations": 50}}},
            backtest_function=mock_backtest.backtest,
        )

        base_params = {"rsi_threshold": 40}
        results = analyzer._run_monte_carlo_sensitivity(
            "rsi_threshold", 40, base_params, "sharpe_ratio"
        )

        if results:  # Only check if results were generated
            assert results["mean"] >= 0
            assert results["min"] <= results["max"]
            assert results["std"] >= 0
            assert 0 <= results["success_rate"] <= 1


class TestSingleParameterAnalysis:
    """Tests for single parameter sensitivity analysis."""

    def test_analyze_single_parameter(self):
        """Test analysis of a single parameter."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        base_params = {"rsi_threshold": 40, "momentum_threshold": 20}
        result = analyzer._analyze_single_parameter(
            "rsi_threshold",
            40,
            base_params,
            [-0.10, -0.05, 0.0, 0.05, 0.10],
            "sharpe_ratio",
        )

        assert result.parameter_name == "rsi_threshold"
        assert result.base_value == 40
        assert result.elasticity_score >= 0.0
        assert result.sensitivity_level in ["ROBUST", "NORMAL", "CRITICAL"]

    def test_optimal_value_detection(self):
        """Test detection of optimal parameter value."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        base_params = {"rsi_threshold": 40}
        result = analyzer._analyze_single_parameter(
            "rsi_threshold", 40, base_params, [-0.10, -0.05, 0.0, 0.05, 0.10], "sharpe_ratio"
        )

        # Optimal should be close to base value (40)
        assert result.optimal_value is not None


class TestComprehensiveSensitivityAnalysis:
    """Tests for comprehensive multi-parameter sensitivity analysis."""

    def test_analyze_multiple_parameters(self):
        """Test sensitivity analysis across multiple parameters."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40, "momentum_threshold": 20, "lookback_period": 20}

        report = analyzer.analyze_parameter_sensitivity(initial_params, "sharpe_ratio")

        assert len(report.parameter_results) == 3
        assert report.overall_robustness_score >= 0
        assert report.overall_robustness_score <= 100

    def test_report_parameter_classification(self):
        """Test that parameters are correctly classified in report."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40, "momentum_threshold": 20, "lookback_period": 20}
        report = analyzer.analyze_parameter_sensitivity(initial_params, "sharpe_ratio")

        # All parameters should be classified
        total_classified = (
            len(report.robust_parameters)
            + len(report.normal_parameters)
            + len(report.critical_parameters)
        )
        assert total_classified == len(report.parameter_results)

    def test_report_robustness_score_calculation(self):
        """Test overall robustness score calculation."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40, "momentum_threshold": 20}
        report = analyzer.analyze_parameter_sensitivity(initial_params, "sharpe_ratio")

        # Score should be in valid range
        assert 0.0 <= report.overall_robustness_score <= 100.0


class TestSensitivityResultSerialization:
    """Tests for sensitivity result serialization."""

    def test_sensitivity_result_to_dict(self):
        """Test conversion of SensitivityResult to dictionary."""
        result = SensitivityResult(
            parameter_name="rsi_threshold",
            base_value=40,
            elasticity_score=0.8,
            sensitivity_level="NORMAL",
            optimal_value=40,
        )

        result_dict = result.to_dict()

        assert result_dict["parameter_name"] == "rsi_threshold"
        assert result_dict["elasticity_score"] == 0.8
        assert result_dict["sensitivity_level"] == "NORMAL"

    def test_sensitivity_report_to_dict(self):
        """Test conversion of SensitivityReport to dictionary."""
        report = SensitivityReport()
        report.robust_parameters = ["param1"]
        report.critical_parameters = ["param2"]
        report.overall_robustness_score = 75.0

        report_dict = report.to_dict()

        assert report_dict["robust_parameters"] == ["param1"]
        assert report_dict["critical_parameters"] == ["param2"]
        assert report_dict["overall_robustness_score"] == 75.0

    def test_sensitivity_report_json_serialization(self):
        """Test JSON serialization of report."""
        report = SensitivityReport()
        report.robust_parameters = ["param1"]
        report.overall_robustness_score = 80.0

        json_str = report.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["robust_parameters"] == ["param1"]


class TestSensitivitySummaryAndReporting:
    """Tests for sensitivity summary and reporting."""

    def test_get_sensitivity_summary(self):
        """Test generation of sensitivity summary."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40, "momentum_threshold": 20}
        report = analyzer.analyze_parameter_sensitivity(initial_params, "sharpe_ratio")
        summary = analyzer.get_sensitivity_summary(report)

        assert "analysis_date" in summary
        assert "total_parameters_analyzed" in summary
        assert "robust_parameters" in summary
        assert "critical_parameters" in summary
        assert "overall_robustness_score" in summary
        assert "parameter_elasticities" in summary

    def test_print_sensitivity_report(self):
        """Test that sensitivity report can be printed without errors."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40}
        report = analyzer.analyze_parameter_sensitivity(initial_params, "sharpe_ratio")

        # Should not raise exception
        try:
            analyzer.print_sensitivity_report(report)
        except Exception as e:
            pytest.fail(f"print_sensitivity_report raised exception: {e}")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_no_backtest_function_provided(self):
        """Test error when no backtest function is provided."""
        analyzer = SensitivityAnalyzer()

        initial_params = {"rsi_threshold": 40}

        with pytest.raises(ValueError):
            analyzer.analyze_parameter_sensitivity(initial_params)

    def test_empty_parameter_dict(self):
        """Test handling of empty parameter dictionary."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {}
        report = analyzer.analyze_parameter_sensitivity(initial_params)

        assert len(report.parameter_results) == 0
        assert report.overall_robustness_score == 0.0

    def test_single_parameter(self):
        """Test analysis with only one parameter."""
        mock_backtest = MockBacktester()
        analyzer = SensitivityAnalyzer(backtest_function=mock_backtest.backtest)

        initial_params = {"rsi_threshold": 40}
        report = analyzer.analyze_parameter_sensitivity(initial_params)

        assert len(report.parameter_results) == 1

    def test_negative_parameter_variations(self):
        """Test handling of variations that would create negative values."""

        def backtest_with_constraint(params):
            # Ensure all parameters are positive
            for v in params.values():
                if v <= 0:
                    raise ValueError("Parameter must be positive")
            return {"sharpe_ratio": 1.0}

        analyzer = SensitivityAnalyzer(backtest_function=backtest_with_constraint)

        # Use small parameter value that could go negative
        initial_params = {"small_param": 1}
        result = analyzer._analyze_single_parameter(
            "small_param", 1, initial_params, [-0.50, 0.0, 0.50], "sharpe_ratio"
        )

        # Should handle gracefully by skipping invalid variations
        assert result.parameter_name == "small_param"
