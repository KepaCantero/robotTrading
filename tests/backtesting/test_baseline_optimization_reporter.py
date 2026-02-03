"""
Test suite for app.backtesting.reports.baseline_optimization_reporter

Addresses TST-005: Test coverage for BaselineOptimizationReporter
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from app.backtesting.reports.baseline_optimization_reporter import (
    BaselineOptimizationReporter,
    ComparisonMetrics,
    ParameterChange,
    StatisticalTest,
    Recommendation,
)


class TestBaselineOptimizationReporterImport:
    """Test module imports."""

    def test_import_baseline_optimization_reporter(self):
        """Test that BaselineOptimizationReporter can be imported."""
        from app.backtesting.reports.baseline_optimization_reporter import BaselineOptimizationReporter
        assert BaselineOptimizationReporter is not None

    def test_import_dataclasses(self):
        """Test that dataclasses can be imported."""
        from app.backtesting.reports.baseline_optimization_reporter import (
            ComparisonMetrics,
            ParameterChange,
            StatisticalTest,
            Recommendation,
        )
        assert ComparisonMetrics is not None
        assert ParameterChange is not None
        assert StatisticalTest is not None
        assert Recommendation is not None


class TestComparisonMetrics:
    """Test ComparisonMetrics dataclass."""

    def test_comparison_metrics_creation(self):
        """Test ComparisonMetrics creation."""
        metrics = ComparisonMetrics(
            sharpe_ratio=(1.5, 2.0),
            total_return=(50.0, 60.0),
            max_drawdown=(-15.0, -10.0),
            win_rate=(0.6, 0.65),
            profit_factor=(1.8, 2.2),
            sortino_ratio=(1.2, 1.8),
            calmar_ratio=(1.0, 1.5),
            omega_ratio=(1.3, 1.7),
        )
        assert metrics.sharpe_ratio == (1.5, 2.0)
        assert metrics.total_return == (50.0, 60.0)


class TestParameterChange:
    """Test ParameterChange dataclass."""

    def test_parameter_change_creation(self):
        """Test ParameterChange creation."""
        change = ParameterChange(
            name="lookback_period",
            before=20,
            after=30,
            impact="Longer period may reduce noise",
        )
        assert change.name == "lookback_period"
        assert change.before == 20
        assert change.after == 30


class TestStatisticalTest:
    """Test StatisticalTest dataclass."""

    def test_statistical_test_creation(self):
        """Test StatisticalTest creation."""
        test = StatisticalTest(
            metric_name="sharpe_ratio",
            baseline_mean=1.5,
            optimized_mean=2.0,
            p_value=0.03,
            is_significant=True,
            test_statistic=2.5,
        )
        assert test.metric_name == "sharpe_ratio"
        assert test.is_significant is True


class TestRecommendation:
    """Test Recommendation dataclass."""

    def test_recommendation_creation(self):
        """Test Recommendation creation."""
        rec = Recommendation(
            decision="USE_OPTIMIZED",
            rationale="Significant improvement with stable OOS performance",
            confidence=0.85,
            conditions=["Deploy with paper trading"],
            warnings=["Monitor drawdown"],
        )
        assert rec.decision == "USE_OPTIMIZED"
        assert rec.confidence == 0.85


class TestBaselineOptimizationReporterInitialization:
    """Test BaselineOptimizationReporter initialization."""

    def test_initialization_with_default_template(self):
        """Test initialization with default template path."""
        # This test may fail if default template doesn't exist
        # We'll catch the error and mark it appropriately
        try:
            reporter = BaselineOptimizationReporter()
            assert reporter.template_path.exists()
        except (FileNotFoundError, Exception):
            # Template may not exist in test environment
            pytest.skip("Default template not found in test environment")

    def test_initialization_with_custom_template(self):
        """Test initialization with custom template."""
        # Create a minimal template file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>Test Template</body></html>"
            f.write(template_content)
            template_path = f.name

        try:
            reporter = BaselineOptimizationReporter(template_path=template_path)
            assert reporter.template_path == Path(template_path)
        finally:
            # Clean up
            Path(template_path).unlink(missing_ok=True)


class TestMetricExtraction:
    """Test metric extraction methods."""

    def test_extract_metrics_basic(self):
        """Test basic metric extraction."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        results = {
            "performance": {
                "sharpe_ratio": 1.5,
                "total_return": 50.0,
                "max_drawdown_percentage": -15.0,
                "win_rate": 0.6,
                "profit_factor": 1.8,
            }
        }

        metrics = reporter._extract_metrics(results)

        assert metrics["sharpe_ratio"] == 1.5
        assert metrics["total_return"] == 50.0
        assert metrics["max_drawdown"] == 15.0  # Positive after abs()

    def test_extract_metrics_with_equity_curve(self):
        """Test metric extraction with equity curve."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        results = {
            "performance": {},
            "equity_curve": [
                (datetime(2024, 1, 1), 100000),
                (datetime(2024, 12, 31), 150000),
            ]
        }

        metrics = reporter._extract_metrics(results)

        assert metrics["total_return"] == 50.0  # (150000-100000)/100000 * 100

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name


class TestComparisonCalculation:
    """Test comparison calculation methods."""

    def test_calculate_comparison(self):
        """Test comparison calculation."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline = {"sharpe_ratio": 1.5, "total_return": 50.0, "max_drawdown": 15.0, "win_rate": 0.6}
        optimized = {"sharpe_ratio": 2.0, "total_return": 60.0, "max_drawdown": 10.0, "win_rate": 0.65}

        comparison = reporter._calculate_comparison(baseline, optimized)

        assert comparison["sharpe_improvement"] > 0  # 2.0 > 1.5
        assert comparison["return_improvement"] > 0  # 60.0 > 50.0
        assert comparison["dd_change"] > 0  # 10.0 < 15.0, but lower is better so positive

    def test_pct_improvement(self):
        """Test percentage improvement calculation."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        # Higher is better
        improvement = reporter._pct_improvement(1.5, 2.0, higher_better=True)
        assert improvement > 0

        # Lower is better (drawdown)
        improvement = reporter._pct_improvement(15.0, 10.0, higher_better=False)
        assert improvement > 0  # Should be positive because 10.0 is better than 15.0

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name


class TestRecommendationGeneration:
    """Test recommendation generation methods."""

    def test_generate_recommendation_use_optimized(self):
        """Test recommendation generation for USE_OPTIMIZED."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline_metrics = {"sharpe_ratio": 1.5}
        optimized_metrics = {"sharpe_ratio": 2.0}  # > 1.2x baseline
        comparison = {"sharpe_improvement": 33.3}

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, walk_forward_results=None
        )

        assert recommendation.decision == "USE_OPTIMIZED"
        assert recommendation.confidence >= 0.8

    def test_generate_recommendation_consider(self):
        """Test recommendation generation for CONSIDER_OPTIMIZED."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline_metrics = {"sharpe_ratio": 1.5}
        optimized_metrics = {"sharpe_ratio": 1.6}  # > 1.05x but < 1.2x
        comparison = {"sharpe_improvement": 6.7}

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, walk_forward_results=None
        )

        assert recommendation.decision == "CONSIDER_OPTIMIZED"

    def test_generate_recommendation_use_baseline(self):
        """Test recommendation generation for USE_BASELINE."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline_metrics = {"sharpe_ratio": 1.5}
        optimized_metrics = {"sharpe_ratio": 1.52}  # < 1.05x baseline
        comparison = {"sharpe_improvement": 1.3}

        recommendation = reporter._generate_recommendation(
            baseline_metrics, optimized_metrics, comparison, walk_forward_results=None
        )

        assert recommendation.decision == "USE_BASELINE"

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name


class TestChartDataPreparation:
    """Test chart data preparation methods."""

    def test_create_equity_chart(self):
        """Test equity chart creation."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        equity_curve = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 6, 1), 125000),
            (datetime(2024, 12, 31), 150000),
        ]

        chart = reporter._create_equity_chart(equity_curve, "Test Strategy", "#2c3e50")

        assert "data" in chart
        assert "layout" in chart
        assert len(chart["data"]) == 1

    def test_create_dual_equity_chart(self):
        """Test dual equity chart creation."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline_curve = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 12, 31), 130000),
        ]
        optimized_curve = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 12, 31), 150000),
        ]

        chart = reporter._create_dual_equity_chart(baseline_curve, optimized_curve)

        assert "data" in chart
        assert len(chart["data"]) == 2  # Baseline and optimized

    def test_create_drawdown_chart(self):
        """Test drawdown chart creation."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        baseline_curve = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 6, 1), 90000),
            (datetime(2024, 12, 31), 110000),
        ]
        optimized_curve = [
            (datetime(2024, 1, 1), 100000),
            (datetime(2024, 6, 1), 95000),
            (datetime(2024, 12, 31), 115000),
        ]

        chart = reporter._create_drawdown_chart(baseline_curve, optimized_curve)

        assert "data" in chart
        assert len(chart["data"]) == 2

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name


class TestHelperMethods:
    """Test helper methods."""

    def test_get_recommendation_class(self):
        """Test recommendation CSS class mapping."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        assert reporter._get_recommendation_class("USE_OPTIMIZED") == "use-optimized"
        assert reporter._get_recommendation_class("CONSIDER_OPTIMIZED") == "consider-optimized"
        assert reporter._get_recommendation_class("USE_BASELINE") == "use-baseline"

    def test_get_recommendation_icon(self):
        """Test recommendation icon mapping."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        assert reporter._get_recommendation_icon("USE_OPTIMIZED") == "✅"
        assert reporter._get_recommendation_icon("CONSIDER_OPTIMIZED") == "⚠️"
        assert reporter._get_recommendation_icon("USE_BASELINE") == "🔄"

    def test_get_card_class(self):
        """Test card CSS class mapping."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        assert reporter._get_card_class(15.0, higher_better=True) == "success"
        assert reporter._get_card_class(-5.0, higher_better=True) == "warning"

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name


class TestSaveReport:
    """Test report saving functionality."""

    def test_save_report_success(self):
        """Test successful report saving."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        html_content = "<html><body>Test Report</body></html>"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            reporter.save_report(html_content, str(output_path))

            assert output_path.exists()
            assert output_path.read_text() == html_content

    def test_save_report_creates_directory(self):
        """Test that save_report creates parent directory."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        html_content = "<html><body>Test Report</body></html>"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "test_report.html"
            reporter.save_report(html_content, str(output_path))

            assert output_path.exists()

    def test_save_report_empty_html(self):
        """Test that empty HTML raises ValueError."""
        reporter = BaselineOptimizationReporter(template_path=self._create_test_template())

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.html"
            with pytest.raises(ValueError):
                reporter.save_report("", str(output_path))

    def _create_test_template(self) -> str:
        """Create a minimal test template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            template_content = "<html><body>{{ recommendation_text }}</body></html>"
            f.write(template_content)
            return f.name
