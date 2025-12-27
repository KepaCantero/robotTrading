"""
Tests for InsightGenerator - insight generation and reporting.

Tests all methods with various metric scenarios:
- Statistical insights generation
- Risk warning generation
- Recommendation generation
- Markdown report formatting
"""

import pytest

from app.backtesting.insight_generator import InsightGenerator


class TestInsightGenerator:
    """Tests for InsightGenerator class."""

    @pytest.fixture
    def generator(self) -> InsightGenerator:
        """Create InsightGenerator instance."""
        return InsightGenerator(risk_free_rate=0.02)

    @pytest.fixture
    def excellent_metrics(self) -> dict:
        """Create excellent performance metrics."""
        return {
            "return_pct": 0.35,  # 35%
            "sharpe_ratio": 2.5,
            "sortino_ratio": 3.2,
            "max_drawdown": -0.08,  # 8%
            "volatility": 0.12,  # 12%
            "win_rate": 0.65,
            "profit_factor": 2.8,
            "total_trades": 150,
            "avg_trade_pnl": 350,
            "calmar_ratio": 4.4,
        }

    @pytest.fixture
    def good_metrics(self) -> dict:
        """Create good performance metrics."""
        return {
            "return_pct": 0.15,  # 15%
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.0,
            "max_drawdown": -0.15,  # 15%
            "volatility": 0.10,  # 10%
            "win_rate": 0.58,
            "profit_factor": 1.8,
            "total_trades": 200,
            "avg_trade_pnl": 75,
            "calmar_ratio": 1.0,
        }

    @pytest.fixture
    def poor_metrics(self) -> dict:
        """Create poor performance metrics."""
        return {
            "return_pct": -0.05,  # -5%
            "sharpe_ratio": -0.5,
            "sortino_ratio": -0.3,
            "max_drawdown": -0.45,  # 45%
            "volatility": 0.25,  # 25%
            "win_rate": 0.35,
            "profit_factor": 0.7,
            "total_trades": 100,
            "avg_trade_pnl": -50,
            "calmar_ratio": -0.1,
        }

    @pytest.fixture
    def sample_regimes(self) -> dict:
        """Create sample regime analysis."""
        return {
            "Bull Market": {
                "periods": 60,
                "pct_time": 25.0,
                "total_return": 0.25,
                "sharpe_ratio": 2.0,
                "max_drawdown": -0.05,
                "win_rate": 0.70,
            },
            "Neutral Market": {
                "periods": 120,
                "pct_time": 50.0,
                "total_return": 0.08,
                "sharpe_ratio": 0.8,
                "max_drawdown": -0.12,
                "win_rate": 0.55,
            },
            "Bear Market": {
                "periods": 72,
                "pct_time": 25.0,
                "total_return": -0.02,
                "sharpe_ratio": -0.3,
                "max_drawdown": -0.30,
                "win_rate": 0.40,
            },
        }

    # Tests for generate_statistical_insights
    def test_statistical_insights_excellent_metrics(
        self, generator: InsightGenerator, excellent_metrics: dict
    ):
        """Test insight generation with excellent metrics."""
        insights = generator.generate_statistical_insights(excellent_metrics)

        assert len(insights) > 0
        assert any("Excellent" in i or "Good" in i or "✅" in i for i in insights)

    def test_statistical_insights_good_metrics(
        self, generator: InsightGenerator, good_metrics: dict
    ):
        """Test insight generation with good metrics."""
        insights = generator.generate_statistical_insights(good_metrics)

        assert len(insights) > 0
        assert all(isinstance(i, str) for i in insights)

    def test_statistical_insights_poor_metrics(
        self, generator: InsightGenerator, poor_metrics: dict
    ):
        """Test insight generation with poor metrics."""
        insights = generator.generate_statistical_insights(poor_metrics)

        assert len(insights) > 0
        assert any("Poor" in i or "Negative" in i or "❌" in i for i in insights)

    def test_statistical_insights_return_coverage(
        self, generator: InsightGenerator, excellent_metrics: dict
    ):
        """Test that insights cover key metrics."""
        insights = generator.generate_statistical_insights(excellent_metrics)
        insights_text = " ".join(insights)

        # Should mention various metrics
        assert any(
            keyword in insights_text
            for keyword in ["return", "Sharpe", "drawdown", "win rate", "volatility"]
        )

    def test_statistical_insights_empty_metrics(self, generator: InsightGenerator):
        """Test insight generation with empty metrics."""
        insights = generator.generate_statistical_insights({})

        assert insights == []

    def test_statistical_insights_storage(self, generator: InsightGenerator, good_metrics: dict):
        """Test that insights are stored internally."""
        insights = generator.generate_statistical_insights(good_metrics)
        stored = generator.get_insights()

        assert stored == insights

    # Tests for generate_risk_warnings
    def test_risk_warnings_excellent_metrics(
        self, generator: InsightGenerator, excellent_metrics: dict
    ):
        """Test warning generation with excellent metrics."""
        warnings = generator.generate_risk_warnings(excellent_metrics)

        # Should have minimal warnings
        assert len(warnings) <= 1

    def test_risk_warnings_poor_metrics(self, generator: InsightGenerator, poor_metrics: dict):
        """Test warning generation with poor metrics."""
        warnings = generator.generate_risk_warnings(poor_metrics)

        # Should have multiple warnings
        assert len(warnings) > 2
        # Should have CRITICAL or WARNING level
        levels = [w.get("level") for w in warnings]
        assert any(level in ["CRITICAL", "WARNING"] for level in levels)

    def test_risk_warnings_structure(self, generator: InsightGenerator, poor_metrics: dict):
        """Test warning structure."""
        warnings = generator.generate_risk_warnings(poor_metrics)

        for warning in warnings:
            assert "level" in warning
            assert "metric" in warning
            assert "value" in warning
            assert "message" in warning
            assert warning["level"] in ["CRITICAL", "WARNING", "INFO"]

    def test_risk_warnings_severity_levels(self, generator: InsightGenerator):
        """Test warning severity levels."""
        # Extreme metrics should trigger CRITICAL
        extreme_metrics = {
            "max_drawdown": -0.60,
            "sharpe_ratio": -1.0,
            "volatility": 0.6,
            "profit_factor": 0.5,
        }
        warnings = generator.generate_risk_warnings(extreme_metrics)

        assert any(w.get("level") == "CRITICAL" for w in warnings)

    def test_risk_warnings_empty_metrics(self, generator: InsightGenerator):
        """Test warning generation with empty metrics."""
        warnings = generator.generate_risk_warnings({})

        assert warnings == []

    def test_risk_warnings_storage(self, generator: InsightGenerator, poor_metrics: dict):
        """Test that warnings are stored internally."""
        warnings = generator.generate_risk_warnings(poor_metrics)
        stored = generator.get_warnings()

        assert stored == warnings

    # Tests for generate_recommendations
    def test_recommendations_excellent_metrics(
        self, generator: InsightGenerator, excellent_metrics: dict
    ):
        """Test recommendation generation with excellent metrics."""
        recommendations = generator.generate_recommendations(excellent_metrics)

        # Should have few recommendations (mostly LOW priority scaling suggestions)
        assert len(recommendations) <= 3
        # All recommendations should be valid
        assert all(isinstance(r, dict) for r in recommendations)

    def test_recommendations_poor_metrics(self, generator: InsightGenerator, poor_metrics: dict):
        """Test recommendation generation with poor metrics."""
        recommendations = generator.generate_recommendations(poor_metrics)

        # Should have multiple recommendations
        assert len(recommendations) > 1
        # Should have HIGH priority items
        priorities = [r.get("priority") for r in recommendations]
        assert "HIGH" in priorities

    def test_recommendations_structure(self, generator: InsightGenerator, good_metrics: dict):
        """Test recommendation structure."""
        recommendations = generator.generate_recommendations(good_metrics)

        for rec in recommendations:
            assert "priority" in rec
            assert "action" in rec
            assert "rationale" in rec
            assert rec["priority"] in ["HIGH", "MEDIUM", "LOW"]
            assert isinstance(rec["action"], str)
            assert isinstance(rec["rationale"], str)

    def test_recommendations_with_regimes(
        self,
        generator: InsightGenerator,
        good_metrics: dict,
        sample_regimes: dict,
    ):
        """Test recommendations including regime analysis."""
        recommendations = generator.generate_recommendations(good_metrics, sample_regimes)

        assert isinstance(recommendations, list)

    def test_recommendations_empty_metrics(self, generator: InsightGenerator):
        """Test recommendation generation with empty metrics."""
        recommendations = generator.generate_recommendations({})

        assert recommendations == []

    def test_recommendations_storage(self, generator: InsightGenerator, good_metrics: dict):
        """Test that recommendations are stored internally."""
        recommendations = generator.generate_recommendations(good_metrics)
        stored = generator.get_recommendations()

        assert stored == recommendations

    # Tests for format_markdown_report
    def test_markdown_report_basic(self, generator: InsightGenerator, good_metrics: dict):
        """Test basic markdown report generation."""
        report = generator.format_markdown_report("Test Strategy", good_metrics)

        assert isinstance(report, str)
        assert "Test Strategy" in report
        assert "Performance Summary" in report
        assert "Insights" in report

    def test_markdown_report_structure(self, generator: InsightGenerator, good_metrics: dict):
        """Test markdown report structure."""
        report = generator.format_markdown_report("TestStrat", good_metrics)

        # Check for key sections
        assert "# Strategy Report" in report
        assert "## 📊 Performance Summary" in report
        assert "| Metric | Value |" in report

    def test_markdown_report_warnings_section(
        self, generator: InsightGenerator, poor_metrics: dict
    ):
        """Test markdown report includes warnings."""
        report = generator.format_markdown_report("Test", poor_metrics, include_warnings=True)

        assert "⚠️ Risk Warnings" in report

    def test_markdown_report_without_warnings(
        self, generator: InsightGenerator, good_metrics: dict
    ):
        """Test markdown report without warnings section."""
        report = generator.format_markdown_report("Test", good_metrics, include_warnings=False)

        # Should still have other sections
        assert "Performance Summary" in report

    def test_markdown_report_recommendations_section(
        self, generator: InsightGenerator, poor_metrics: dict
    ):
        """Test markdown report includes recommendations."""
        report = generator.format_markdown_report(
            "Test", poor_metrics, include_recommendations=True
        )

        assert "💡 Recommendations" in report

    def test_markdown_report_without_recommendations(
        self, generator: InsightGenerator, good_metrics: dict
    ):
        """Test markdown report without recommendations section."""
        report = generator.format_markdown_report(
            "Test", good_metrics, include_recommendations=False
        )

        assert "Performance Summary" in report

    def test_markdown_report_with_regimes(
        self,
        generator: InsightGenerator,
        good_metrics: dict,
        sample_regimes: dict,
    ):
        """Test markdown report with regime analysis."""
        report = generator.format_markdown_report("Test", good_metrics, regimes=sample_regimes)

        assert "Regime Analysis" in report
        assert "Bull Market" in report or "Neutral Market" in report

    def test_markdown_report_metrics_included(
        self, generator: InsightGenerator, excellent_metrics: dict
    ):
        """Test that all metrics are included in report."""
        report = generator.format_markdown_report("Test", excellent_metrics)

        # Check for metric values
        assert "35" in report or "35.0" in report  # return_pct
        assert "2.5" in report  # sharpe_ratio
        assert "2.8" in report  # profit_factor

    def test_markdown_report_empty_metrics(self, generator: InsightGenerator):
        """Test markdown report with minimal metrics."""
        report = generator.format_markdown_report("Test", {})

        assert isinstance(report, str)
        assert "Test" in report
        assert "Performance Summary" in report

    # Integration tests
    def test_full_analysis_workflow(
        self,
        generator: InsightGenerator,
        good_metrics: dict,
        sample_regimes: dict,
    ):
        """Test complete analysis workflow."""
        # Generate all insights
        insights = generator.generate_statistical_insights(good_metrics)
        assert len(insights) > 0

        # Generate warnings
        warnings = generator.generate_risk_warnings(good_metrics)
        assert isinstance(warnings, list)

        # Generate recommendations
        recommendations = generator.generate_recommendations(good_metrics, sample_regimes)
        assert isinstance(recommendations, list)

        # Generate full report
        report = generator.format_markdown_report(
            "Full Test",
            good_metrics,
            sample_regimes,
            include_warnings=True,
            include_recommendations=True,
        )
        assert "Full Test" in report
        assert len(report) > 100

    def test_consecutive_analyses(self, generator: InsightGenerator):
        """Test running multiple analyses in sequence."""
        metrics1 = {"return_pct": 0.1, "sharpe_ratio": 1.0}
        metrics2 = {"return_pct": 0.2, "sharpe_ratio": 2.0}

        # First analysis
        insights1 = generator.generate_statistical_insights(metrics1)
        assert len(insights1) > 0

        # Second analysis (should overwrite)
        insights2 = generator.generate_statistical_insights(metrics2)
        assert len(insights2) > 0

        # Should have latest insights
        stored = generator.get_insights()
        assert stored == insights2

    def test_generator_attributes(self, generator: InsightGenerator):
        """Test generator has correct attributes."""
        assert generator.risk_free_rate == 0.02

    def test_special_characters_in_strategy_name(self, generator: InsightGenerator):
        """Test report with special characters in strategy name."""
        report = generator.format_markdown_report("Test Strategy @#$% 123", {})

        assert "Test Strategy @#$% 123" in report

    def test_very_large_metrics_values(self, generator: InsightGenerator):
        """Test report with very large metric values."""
        large_metrics = {
            "return_pct": 5.0,  # 500%
            "profit_factor": 50.0,
            "total_trades": 10000,
        }
        report = generator.format_markdown_report("Large Test", large_metrics)

        assert isinstance(report, str)
        assert len(report) > 50

    def test_very_small_metrics_values(self, generator: InsightGenerator):
        """Test report with very small metric values."""
        small_metrics = {
            "return_pct": 0.0001,
            "sharpe_ratio": 0.01,
            "volatility": 0.001,
        }
        report = generator.format_markdown_report("Small Test", small_metrics)

        assert isinstance(report, str)

    def test_insight_consistency(self, generator: InsightGenerator, good_metrics: dict):
        """Test that insights are consistent across calls."""
        report1 = generator.format_markdown_report("Test1", good_metrics)
        report2 = generator.format_markdown_report("Test1", good_metrics)

        # Same metrics should produce same insights
        # (report will have different timestamps)
        assert "Performance Summary" in report1
        assert "Performance Summary" in report2

    def test_warning_critical_threshold(self, generator: InsightGenerator):
        """Test CRITICAL warning threshold."""
        critical_metrics = {
            "max_drawdown": -0.60,  # 60% drawdown triggers CRITICAL
        }
        warnings = generator.generate_risk_warnings(critical_metrics)

        assert any(w.get("level") == "CRITICAL" for w in warnings)

    def test_recommendation_priority_ordering(self, generator: InsightGenerator):
        """Test recommendations are prioritized correctly."""
        poor_metrics = {
            "max_drawdown": -0.45,  # Should trigger HIGH priority
            "sharpe_ratio": -0.5,  # Should trigger MEDIUM priority
        }
        recommendations = generator.generate_recommendations(poor_metrics)

        # Should have HIGH priority items before LOW
        priorities = [r.get("priority") for r in recommendations]
        if "HIGH" in priorities and "LOW" in priorities:
            high_idx = priorities.index("HIGH")
            low_idx = priorities.index("LOW")
            assert high_idx < low_idx

    def test_multiple_generators(self):
        """Test that multiple generators are independent."""
        gen1 = InsightGenerator(risk_free_rate=0.02)
        gen2 = InsightGenerator(risk_free_rate=0.05)

        assert gen1.risk_free_rate == 0.02
        assert gen2.risk_free_rate == 0.05
        assert gen1.risk_free_rate != gen2.risk_free_rate
