"""
Unit Tests for BaselineOptimizationReporter

Test suite for the baseline vs optimization comparison reporter.
"""

import json
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app.backtesting.reports.baseline_optimization_reporter import (
    BaselineOptimizationReporter,
    ParameterChange,
    Recommendation,
    StatisticalTest,
)
from app.core.models.input_profile import InputProfile, RiskTolerance


@pytest.fixture
def sample_profile():
    """Create sample input profile."""
    return InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="medio",
        investment_horizon=24,
    )


@pytest.fixture
def sample_baseline_results():
    """Create sample baseline results."""
    return {
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "equity_curve": [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 2, 1), 102000),
            (datetime(2024, 3, 1), 101500),
            (datetime(2024, 4, 1), 104000),
            (datetime(2024, 5, 1), 106000),
            (datetime(2024, 6, 1), 105000),
        ],
        "performance": {
            "sharpe_ratio": 1.2,
            "total_return": 25.0,
            "max_drawdown_percentage": -15.0,
            "win_rate": 52.0,
            "profit_factor": 1.4,
            "sortino_ratio": 1.8,
            "calmar_ratio": 0.9,
            "omega_ratio": 1.3,
        },
        "parameters": {
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
        },
    }


@pytest.fixture
def sample_optimized_results():
    """Create sample optimized results."""
    return {
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "equity_curve": [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 2, 1), 103000),
            (datetime(2024, 3, 1), 102500),
            (datetime(2024, 4, 1), 107000),
            (datetime(2024, 5, 1), 110000),
            (datetime(2024, 6, 1), 109000),
        ],
        "performance": {
            "sharpe_ratio": 1.6,  # 33% improvement
            "total_return": 35.0,  # 40% improvement
            "max_drawdown_percentage": -12.0,  # 20% improvement
            "win_rate": 55.0,  # 5.8% improvement
            "profit_factor": 1.6,  # 14% improvement
            "sortino_ratio": 2.2,
            "calmar_ratio": 1.3,
            "omega_ratio": 1.5,
        },
        "parameters": {
            "lookback_period": 25,
            "entry_threshold": 2.2,
            "exit_threshold": 0.8,
        },
    }


@pytest.fixture
def sample_walk_forward_results():
    """Create sample walk-forward results."""
    return {
        "windows": [
            {"is_sharpe": 1.5, "oos_sharpe": 1.3},
            {"is_sharpe": 1.6, "oos_sharpe": 1.4},
            {"is_sharpe": 1.7, "oos_sharpe": 1.35},
        ],
        "is_sharpe": 1.6,
        "oos_sharpe": 1.35,
        "is_oos_ratio": 0.84,
    }


class TestBaselineOptimizationReporter:
    """Test suite for BaselineOptimizationReporter."""

    def test_initialization(self, sample_profile):
        """Test reporter initialization."""
        # Default template
        reporter = BaselineOptimizationReporter()
        assert reporter.template is not None
        assert reporter.template_path.exists()

        # Custom template path
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<html><body>{{ test }}</body></html>")
            custom_path = f.name

        try:
            reporter = BaselineOptimizationReporter(template_path=custom_path)
            assert reporter.template_path == Path(custom_path)
        finally:
            Path(custom_path).unlink()

    def test_extract_metrics(self, sample_baseline_results):
        """Test metrics extraction from results."""
        reporter = BaselineOptimizationReporter()
        metrics = reporter._extract_metrics(sample_baseline_results)

        assert metrics["sharpe_ratio"] == 1.2
        assert metrics["total_return"] == 25.0
        assert metrics["max_drawdown"] == 15.0
        assert metrics["win_rate"] == 52.0
        assert metrics["profit_factor"] == 1.4

    def test_calculate_comparison(self, sample_baseline_results, sample_optimized_results):
        """Test comparison calculation."""
        reporter = BaselineOptimizationReporter()

        baseline_metrics = reporter._extract_metrics(sample_baseline_results)
        optimized_metrics = reporter._extract_metrics(sample_optimized_results)

        comparison = reporter._calculate_comparison(baseline_metrics, optimized_metrics)

        # Sharpe improvement (higher is better)
        assert comparison["sharpe_improvement"] > 0
        assert abs(comparison["sharpe_improvement"] - 33.3) < 1.0  # ~33%

        # Return improvement (higher is better)
        assert comparison["return_improvement"] > 0
        assert abs(comparison["return_improvement"] - 40.0) < 1.0  # 40%

        # Drawdown change (lower is better, so positive change = improvement)
        assert comparison["dd_change"] > 0
        assert abs(comparison["dd_change"] - 20.0) < 1.0  # 20% improvement

        # Win rate improvement
        assert comparison["winrate_improvement"] > 0

    def test_pct_improvement(self):
        """Test percentage improvement calculation."""
        reporter = BaselineOptimizationReporter()

        # Higher is better (Sharpe, Return, etc.)
        improvement = reporter._pct_improvement(1.0, 1.5, higher_better=True)
        assert improvement == 50.0

        improvement = reporter._pct_improvement(1.5, 1.0, higher_better=True)
        assert improvement == -33.33

        # Lower is better (Drawdown)
        improvement = reporter._pct_improvement(20.0, 15.0, higher_better=False)
        assert improvement == 25.0  # 25% improvement

        improvement = reporter._pct_improvement(15.0, 20.0, higher_better=False)
        assert improvement == -33.33  # 33% degradation

    def test_extract_parameter_changes(self, sample_baseline_results, sample_optimized_results):
        """Test parameter change extraction."""
        reporter = BaselineOptimizationReporter()

        baseline_params = sample_baseline_results["parameters"]
        optimized_params = sample_optimized_results["parameters"]

        changes = reporter._extract_parameter_changes(baseline_params, optimized_params, {})

        assert len(changes) == 3

        # Check lookback_period change
        lookback_change = [c for c in changes if c.name == "lookback_period"][0]
        assert lookback_change.before == 20
        assert lookback_change.after == 25
        assert lookback_change.impact is not None

    def test_generate_recommendation_use_optimized(
        self, sample_baseline_results, sample_optimized_results, sample_walk_forward_results
    ):
        """Test recommendation generation for USE_OPTIMIZED case."""
        reporter = BaselineOptimizationReporter()

        baseline_metrics = reporter._extract_metrics(sample_baseline_results)
        optimized_metrics = reporter._extract_metrics(sample_optimized_results)

        # Create comparison showing strong improvement
        comparison = {
            "sharpe_improvement": 33.3,
            "return_improvement": 40.0,
            "dd_change": 20.0,
            "winrate_improvement": 5.8,
        }

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, sample_walk_forward_results
        )

        assert recommendation.decision == "USE_OPTIMIZED"
        assert recommendation.confidence > 0.8
        assert len(recommendation.conditions) > 0
        assert len(recommendation.warnings) > 0

    def test_generate_recommendation_consider_optimized(
        self, sample_baseline_results, sample_optimized_results
    ):
        """Test recommendation generation for CONSIDER_OPTIMIZED case."""
        reporter = BaselineOptimizationReporter()

        baseline_metrics = reporter._extract_metrics(sample_baseline_results)

        # Create optimized metrics with marginal improvement
        optimized_metrics = baseline_metrics.copy()
        optimized_metrics["sharpe_ratio"] = 1.3  # Only 8% improvement

        comparison = {
            "sharpe_improvement": 8.3,
            "return_improvement": 10.0,
            "dd_change": 5.0,
            "winrate_improvement": 2.0,
        }

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, None
        )

        assert recommendation.decision == "CONSIDER_OPTIMIZED"
        assert 0.5 < recommendation.confidence < 0.8

    def test_generate_recommendation_use_baseline(self, sample_baseline_results):
        """Test recommendation generation for USE_BASELINE case."""
        reporter = BaselineOptimizationReporter()

        baseline_metrics = reporter._extract_metrics(sample_baseline_results)

        # Create optimized metrics with minimal improvement
        optimized_metrics = baseline_metrics.copy()
        optimized_metrics["sharpe_ratio"] = 1.22  # Only 1.7% improvement

        comparison = {
            "sharpe_improvement": 1.7,
            "return_improvement": 2.0,
            "dd_change": 1.0,
            "winrate_improvement": 0.5,
        }

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, None
        )

        assert recommendation.decision == "USE_BASELINE"

    def test_prepare_chart_data(self, sample_baseline_results, sample_optimized_results):
        """Test chart data preparation."""
        reporter = BaselineOptimizationReporter()

        chart_data = reporter._prepare_chart_data(sample_baseline_results, sample_optimized_results)

        # Check that all chart types are present
        assert "baseline_equity" in chart_data
        assert "optimized_equity" in chart_data
        assert "dual_equity" in chart_data
        assert "drawdown" in chart_data
        assert "risk_radar" in chart_data

        # Verify chart structure
        assert "data" in chart_data["dual_equity"]
        assert "layout" in chart_data["dual_equity"]

    def test_create_dual_equity_chart(self, sample_baseline_results, sample_optimized_results):
        """Test dual equity chart creation."""
        reporter = BaselineOptimizationReporter()

        chart = reporter._create_dual_equity_chart(
            sample_baseline_results["equity_curve"],
            sample_optimized_results["equity_curve"],
        )

        assert "data" in chart
        assert "layout" in chart
        assert len(chart["data"]) == 2  # Two traces

        # Check that both traces are present
        trace_names = [trace["name"] for trace in chart["data"]]
        assert "Baseline" in trace_names
        assert "Optimized" in trace_names

    def test_calculate_drawdown(self):
        """Test drawdown calculation."""
        reporter = BaselineOptimizationReporter()

        equity_curve = [(datetime(2024, 1, 1), value) for value in [100, 105, 103, 108, 106, 110]]

        drawdown = reporter._calculate_drawdown(equity_curve)

        assert len(drawdown) == len(equity_curve)
        assert drawdown[0] == 0  # First point is peak
        assert drawdown[1] == 0  # Second point is new peak
        assert drawdown[2] < 0  # Below peak
        assert drawdown[4] < 0  # Below peak

    def test_prepare_key_metrics_table(self, sample_baseline_results, sample_optimized_results):
        """Test key metrics table preparation."""
        reporter = BaselineOptimizationReporter()

        baseline_metrics = reporter._extract_metrics(sample_baseline_results)
        optimized_metrics = reporter._extract_metrics(sample_optimized_results)

        table_data = reporter._prepare_key_metrics_table(baseline_metrics, optimized_metrics, {})

        assert len(table_data) > 0

        # Check first row structure
        first_row = table_data[0]
        assert "name" in first_row
        assert "baseline" in first_row
        assert "optimized" in first_row
        assert "improvement" in first_row
        assert "improvement_class" in first_row
        assert "significant" in first_row

    def test_generate_report(
        self, sample_profile, sample_baseline_results, sample_optimized_results
    ):
        """Test full report generation."""
        reporter = BaselineOptimizationReporter()

        html = reporter.generate_report(
            profile=sample_profile,
            baseline_results=sample_baseline_results,
            optimization_results=sample_optimized_results,
        )

        assert isinstance(html, str)
        assert len(html) > 0

        # Check that key elements are in HTML
        assert "Baseline vs Optimization Comparison" in html
        assert "maximizar_capital" in html or "Maximizar Capital" in html
        assert "Sharpe Ratio" in html
        assert "Total Return" in html

    def test_save_report(self, sample_profile, sample_baseline_results, sample_optimized_results):
        """Test saving report to file."""
        reporter = BaselineOptimizationReporter()

        html = reporter.generate_report(
            profile=sample_profile,
            baseline_results=sample_baseline_results,
            optimization_results=sample_optimized_results,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            reporter.save_report(html, str(output_path))

            assert output_path.exists()

            # Read and verify content
            with open(output_path, "r") as f:
                saved_html = f.read()

            assert saved_html == html

    def test_generate_report_with_walk_forward(
        self,
        sample_profile,
        sample_baseline_results,
        sample_optimized_results,
        sample_walk_forward_results,
    ):
        """Test report generation with walk-forward validation."""
        reporter = BaselineOptimizationReporter()

        html = reporter.generate_report(
            profile=sample_profile,
            baseline_results=sample_baseline_results,
            optimization_results=sample_optimized_results,
            walk_forward_results=sample_walk_forward_results,
        )

        assert "Out-of-Sample" in html or "walk_forward" in html

    def test_get_recommendation_class(self):
        """Test recommendation CSS class mapping."""
        reporter = BaselineOptimizationReporter()

        assert reporter._get_recommendation_class("USE_OPTIMIZED") == "use-optimized"
        assert reporter._get_recommendation_class("CONSIDER_OPTIMIZED") == "consider-optimized"
        assert reporter._get_recommendation_class("USE_BASELINE") == "use-baseline"

    def test_get_recommendation_icon(self):
        """Test recommendation icon mapping."""
        reporter = BaselineOptimizationReporter()

        assert reporter._get_recommendation_icon("USE_OPTIMIZED") == "✅"
        assert reporter._get_recommendation_icon("CONSIDER_OPTIMIZED") == "⚠️"
        assert reporter._get_recommendation_icon("USE_BASELINE") == "🔄"

    def test_get_card_class(self):
        """Test metric card CSS class mapping."""
        reporter = BaselineOptimizationReporter()

        # Positive improvement
        assert reporter._get_card_class(15.0, higher_better=True) == "success"
        assert reporter._get_card_class(5.0, higher_better=True) == ""

        # Negative improvement
        assert reporter._get_card_class(-15.0, higher_better=True) == "warning"

        # For metrics where lower is better
        assert reporter._get_card_class(15.0, higher_better=False) == "success"

    def test_format_recommended_config(self, sample_optimized_results):
        """Test configuration formatting."""
        reporter = BaselineOptimizationReporter()

        config = reporter._format_recommended_config(sample_optimized_results)

        assert isinstance(config, str)
        assert "Recommended Configuration" in config
        assert "lookback_period:" in config
        assert "entry_threshold:" in config


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_equity_curve(self):
        """Test handling of empty equity curve."""
        reporter = BaselineOptimizationReporter()

        drawdown = reporter._calculate_drawdown([])
        assert drawdown == []

        chart = reporter._create_dual_equity_chart([], [])
        assert chart["data"] == []

    def test_zero_baseline_metrics(self):
        """Test handling when baseline metrics are zero."""
        reporter = BaselineOptimizationReporter()

        improvement = reporter._pct_improvement(0.0, 1.5, higher_better=True)
        assert improvement == 0.0

    def test_missing_performance_data(self):
        """Test handling of missing performance data."""
        reporter = BaselineOptimizationReporter()

        results = {"equity_curve": [], "performance": {}}
        metrics = reporter._extract_metrics(results)

        # Should return zeros for missing metrics
        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["total_return"] == 0.0

    def test_unchanged_parameters(self):
        """Test handling of unchanged parameters."""
        reporter = BaselineOptimizationReporter()

        params = {"lookback_period": 20}
        changes = reporter._extract_parameter_changes(params, params, {})

        assert len(changes) == 0  # No changes detected


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete workflows."""

    def test_complete_report_generation_workflow(
        self, sample_profile, sample_baseline_results, sample_optimized_results
    ):
        """Test complete workflow from data to saved report."""
        reporter = BaselineOptimizationReporter()

        # Generate report
        html = reporter.generate_report(
            profile=sample_profile,
            baseline_results=sample_baseline_results,
            optimization_results=sample_optimized_results,
        )

        # Verify HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

        # Save report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "complete_test_report.html"
            reporter.save_report(html, str(output_path))

            # Verify file was created and is valid
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Verify it can be opened and read
            with open(output_path, "r") as f:
                content = f.read()

            assert len(content) > 1000  # Should be substantial
            assert "Sharpe Ratio" in content
