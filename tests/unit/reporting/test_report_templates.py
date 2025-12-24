"""
Tests for ReportTemplates (T9.1.1)

Tests HTML template generation for performance reports.
"""

import pytest
from app.services.reporting.report_templates import ReportTemplates, get_report_templates


class TestReportTemplates:
    """Test suite for ReportTemplates."""

    @pytest.fixture
    def templates(self):
        """Create templates instance."""
        return ReportTemplates()

    def test_generates_valid_html(self, templates):
        """Test HTML generation produces valid HTML structure."""
        html = templates.generate_performance_report_html(
            strategy_name="Test Strategy",
            summary={"total_return": 0.15, "sharpe_ratio": 1.5, "max_drawdown": -0.10, "win_rate": 0.55},
            metrics={"total_trades": 100, "profit_factor": 2.0},
            risk_metrics={"volatility": 0.12, "var_95": -0.08},
            allocation={"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2},
        )

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "Test Strategy" in html

    def test_includes_performance_metrics(self, templates):
        """Test HTML includes performance metrics."""
        html = templates.generate_performance_report_html(
            strategy_name="Momentum",
            summary={"total_return": 0.25, "sharpe_ratio": 2.0, "max_drawdown": -0.05, "win_rate": 0.65},
            metrics={"total_trades": 50, "profit_factor": 3.5},
            risk_metrics={},
            allocation={},
        )

        # Check for key metrics
        assert "+25.00%" in html  # total return
        assert "2.00" in html or "2.0" in html  # sharpe ratio
        assert "65." in html or "65.0" in html  # win rate

    def test_includes_portfolio_allocation(self, templates):
        """Test HTML includes portfolio allocation."""
        html = templates.generate_performance_report_html(
            strategy_name="Test",
            summary={},
            metrics={},
            risk_metrics={},
            allocation={"AAPL": 0.4, "GOOGL": 0.6},
        )

        assert "AAPL" in html
        assert "GOOGL" in html
        assert "40.0%" in html or "40." in html
        assert "60." in html or "60.0%" in html

    def test_handles_empty_metrics(self, templates):
        """Test HTML generation with empty metrics."""
        html = templates.generate_performance_report_html(
            strategy_name="Empty",
            summary={},
            metrics={},
            risk_metrics={},
            allocation={},
        )

        assert "Empty" in html
        assert "<!DOCTYPE html>" in html

    def test_includes_css_styling(self, templates):
        """Test HTML includes CSS styling."""
        html = templates.generate_performance_report_html(
            strategy_name="Test",
            summary={},
            metrics={},
            risk_metrics={},
            allocation={},
        )

        assert "<style>" in html
        assert "font-family" in html
        assert "color:" in html

    def test_includes_generated_timestamp(self, templates):
        """Test HTML includes timestamp."""
        html = templates.generate_performance_report_html(
            strategy_name="Test",
            summary={},
            metrics={},
            risk_metrics={},
            allocation={},
        )

        assert "Generated:" in html
        assert "UTC" in html

    def test_simple_summary_html(self, templates):
        """Test simple summary generation."""
        html = templates.generate_simple_summary_html(
            strategy_name="Quick Test",
            return_pct=12.5,
            sharpe=1.8,
            drawdown_pct=-8.0,
        )

        assert "Quick Test" in html
        assert "+12.50%" in html or "12.50" in html
        assert "1.80" in html or "1.8" in html
        assert "-8.00%" in html or "8.00" in html

    def test_negative_returns_styling(self, templates):
        """Test negative returns get proper styling."""
        html = templates.generate_performance_report_html(
            strategy_name="Loser",
            summary={"total_return": -0.15, "sharpe_ratio": -0.5, "max_drawdown": -0.30, "win_rate": 0.30},
            metrics={},
            risk_metrics={},
            allocation={},
        )

        assert "-15.00%" in html or "-15" in html
        assert "30." in html or "30.0" in html

    def test_singleton_pattern(self):
        """Test get_report_templates returns singleton."""
        t1 = get_report_templates()
        t2 = get_report_templates()

        assert t1 is t2, "Should return same instance"
