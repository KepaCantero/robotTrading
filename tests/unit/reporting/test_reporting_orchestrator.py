"""
Tests for ReportingOrchestrator (T9.1.3)

Tests end-to-end report generation orchestration.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np

from app.services.reporting.reporting_orchestrator import (
    ReportingOrchestrator,
    get_reporting_orchestrator,
)


class TestReportingOrchestrator:
    """Test suite for ReportingOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return ReportingOrchestrator()

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture
    def backtest_result(self):
        """Create sample backtest result."""
        return {
            "total_return": 0.25,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.1,
            "max_drawdown": -0.12,
            "win_rate": 0.58,
            "profit_factor": 2.3,
            "total_trades": 100,
            "volatility": 0.15,
            "monthly_returns": [0.02, 0.01, -0.01, 0.03, 0.015],
        }

    @pytest.fixture
    def allocation(self):
        """Create portfolio allocation."""
        return {
            "AAPL": 0.3,
            "GOOGL": 0.25,
            "MSFT": 0.2,
            "TSLA": 0.15,
            "AMZN": 0.1,
        }

    @pytest.fixture
    def returns_series(self):
        """Create returns series."""
        np.random.seed(42)
        return pd.Series(
            np.random.normal(0.001, 0.01, 252),
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

    # =========================================================================
    # TEST: Comprehensive Report Generation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_comprehensive_report(self, orchestrator, backtest_result, allocation):
        """Test comprehensive report generation."""
        report = await orchestrator.generate_comprehensive_report(
            strategy_name="Momentum Strategy",
            backtest_result=backtest_result,
            portfolio_allocation=allocation,
        )

        assert "report_id" in report
        assert "strategy_name" in report
        assert report["strategy_name"] == "Momentum Strategy"
        assert "html_report" in report
        assert "<html" in report["html_report"]

    @pytest.mark.asyncio
    async def test_report_includes_all_sections(self, orchestrator, backtest_result, allocation):
        """Test report includes all required sections."""
        report = await orchestrator.generate_comprehensive_report(
            strategy_name="Test",
            backtest_result=backtest_result,
            portfolio_allocation=allocation,
        )

        assert "summary" in report
        assert "metrics" in report
        assert "risk_metrics" in report
        assert "allocation" in report
        assert "generated_at" in report

    @pytest.mark.asyncio
    async def test_report_with_returns_series(
        self, orchestrator, backtest_result, allocation, returns_series
    ):
        """Test report generation with returns series."""
        report = await orchestrator.generate_comprehensive_report(
            strategy_name="With Returns",
            backtest_result=backtest_result,
            portfolio_allocation=allocation,
            returns=returns_series,
        )

        assert "advanced_metrics" in report
        assert len(report["advanced_metrics"]) > 0

    @pytest.mark.asyncio
    async def test_report_with_recommendation(self, orchestrator, backtest_result, allocation):
        """Test report generation with recommendation."""
        rec = {"action": "BUY", "confidence": "HIGH"}

        report = await orchestrator.generate_comprehensive_report(
            strategy_name="With Rec",
            backtest_result=backtest_result,
            portfolio_allocation=allocation,
            recommendation=rec,
        )

        assert report["recommendation"] == rec

    # =========================================================================
    # TEST: Risk Metrics Calculation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, orchestrator, backtest_result):
        """Test risk metrics are calculated."""
        risk_metrics = await orchestrator._calculate_risk_metrics(backtest_result)

        assert "volatility" in risk_metrics
        assert "max_drawdown" in risk_metrics
        assert "var_95" in risk_metrics
        assert "cvar_95" in risk_metrics
        assert "calmar_ratio" in risk_metrics

    # =========================================================================
    # TEST: Executive Summary
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_executive_summary(self, orchestrator):
        """Test executive summary generation."""
        html = await orchestrator.generate_executive_summary(
            strategy_name="Quick Summary",
            total_return_pct=15.5,
            sharpe_ratio=1.8,
            max_drawdown_pct=-10.0,
            recommendation_text="Recommended for deployment",
        )

        assert "Quick Summary" in html
        assert "15.5" in html or "15.50" in html
        assert "<html" in html

    @pytest.mark.asyncio
    async def test_executive_summary_includes_recommendation(self, orchestrator):
        """Test executive summary includes recommendation."""
        html = await orchestrator.generate_executive_summary(
            strategy_name="Test",
            total_return_pct=10.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-8.0,
            recommendation_text="Deploy immediately",
        )

        assert "Deploy immediately" in html or "recommendation" in html.lower()

    # =========================================================================
    # TEST: Singleton
    # =========================================================================

    def test_singleton_pattern(self):
        """Test get_reporting_orchestrator returns singleton."""
        orch1 = get_reporting_orchestrator()
        orch2 = get_reporting_orchestrator()

        assert orch1 is orch2, "Should return same instance"

    # =========================================================================
    # TEST: Edge Cases
    # =========================================================================

    @pytest.mark.asyncio
    async def test_handles_missing_fields(self, orchestrator):
        """Test handles missing fields gracefully."""
        minimal_result = {"total_return": 0.05}
        minimal_allocation = {"Asset1": 1.0}

        report = await orchestrator.generate_comprehensive_report(
            strategy_name="Minimal",
            backtest_result=minimal_result,
            portfolio_allocation=minimal_allocation,
        )

        assert "report_id" in report
        assert report["strategy_name"] == "Minimal"

    @pytest.mark.asyncio
    async def test_empty_backtest_result(self, orchestrator, allocation):
        """Test with empty backtest result."""
        report = await orchestrator.generate_comprehensive_report(
            strategy_name="Empty",
            backtest_result={},
            portfolio_allocation=allocation,
        )

        assert isinstance(report, dict)
        assert "html_report" in report
