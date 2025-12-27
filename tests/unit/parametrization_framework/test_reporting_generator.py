"""
T9.1: ReportingGenerator Tests

Tests for comprehensive performance report generation.
"""

from decimal import Decimal

import pytest

from app.services.reporting_generator import (
    AllocationSnapshot,
    ReportGenerationRequest,
    ReportingGenerator,
    StrategyMetrics,
    get_reporting_generator,
)


# REPORTING GENERATOR INITIALIZATION TESTS
class TestReportingGeneratorInitialization:
    def test_generator_init(self):
        """Test generator initialization."""
        gen = ReportingGenerator()
        assert len(gen.report_history) == 0

    def test_generator_singleton(self):
        """Test generator singleton pattern."""
        g1 = get_reporting_generator()
        g2 = get_reporting_generator()
        assert g1 is g2

    def test_generator_status(self):
        """Test generator status reporting."""
        gen = ReportingGenerator()
        status = gen.get_generator_status()

        assert "total_reports" in status
        assert "successful_reports" in status
        assert "success_rate" in status
        assert "rating_distribution" in status


# EXCELLENT PERFORMANCE TESTS
class TestExcellentPerformance:
    @pytest.mark.asyncio
    async def test_excellent_rating_high_sharpe(self):
        """Test excellent rating with high Sharpe ratio."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("30"),
            sharpe_ratio=Decimal("2.5"),
            sortino_ratio=Decimal("3.0"),
            max_drawdown_pct=Decimal("8"),
            win_rate_pct=Decimal("65"),
            profit_factor=Decimal("2.8"),
            calmar_ratio=Decimal("3.75"),
            volatility_pct=Decimal("12"),
            cumulative_return_pct=Decimal("45"),
            num_trades=250,
        )

        request = ReportGenerationRequest(
            report_id="test_excellent_001",
            profile_id="profile_excellent",
            input_id="user_excellent",
            strategy_name="High Performance Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("40"),
                    expected_return_contribution_pct=Decimal("50"),
                    risk_contribution_pct=Decimal("35"),
                ),
                AllocationSnapshot(
                    module_name="mean_reversion",
                    allocation_pct=Decimal("30"),
                    expected_return_contribution_pct=Decimal("25"),
                    risk_contribution_pct=Decimal("25"),
                ),
                AllocationSnapshot(
                    module_name="pairs_trading",
                    allocation_pct=Decimal("30"),
                    expected_return_contribution_pct=Decimal("25"),
                    risk_contribution_pct=Decimal("40"),
                ),
            ],
            capital_eur=Decimal("500000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert result.overall_rating == "excellent"
        assert len(result.strengths) > 0
        assert "Exceptional risk-adjusted returns" in " ".join(result.strengths)
        assert result.html_content is not None
        assert "High Performance Strategy" in result.html_content

    @pytest.mark.asyncio
    async def test_excellent_strengths_identified(self):
        """Test that strengths are properly identified for excellent performance."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("35"),
            sharpe_ratio=Decimal("2.2"),
            sortino_ratio=Decimal("2.8"),
            max_drawdown_pct=Decimal("7"),
            win_rate_pct=Decimal("62"),
            profit_factor=Decimal("2.5"),
            calmar_ratio=Decimal("5.0"),
            volatility_pct=Decimal("15"),
            cumulative_return_pct=Decimal("50"),
            num_trades=300,
        )

        request = ReportGenerationRequest(
            report_id="test_strengths_001",
            profile_id="profile_strengths",
            input_id="user_strengths",
            strategy_name="Strong Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("250000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await gen.generate_report(request)

        assert result.success
        # Should identify multiple strengths
        assert len(result.strengths) >= 3
        assert any("Exceptional" in s for s in result.strengths)
        assert any("exceeds target" in s.lower() for s in result.strengths)
        assert any("downside protection" in s.lower() for s in result.strengths)


# GOOD PERFORMANCE TESTS
class TestGoodPerformance:
    @pytest.mark.asyncio
    async def test_good_rating(self):
        """Test good performance rating."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("18"),
            sharpe_ratio=Decimal("1.3"),
            sortino_ratio=Decimal("1.7"),
            max_drawdown_pct=Decimal("15"),
            win_rate_pct=Decimal("52"),
            profit_factor=Decimal("1.8"),
            calmar_ratio=Decimal("1.2"),
            volatility_pct=Decimal("18"),
            cumulative_return_pct=Decimal("25"),
            num_trades=180,
        )

        request = ReportGenerationRequest(
            report_id="test_good_001",
            profile_id="profile_good",
            input_id="user_good",
            strategy_name="Good Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="ensemble",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("100000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert result.overall_rating == "good"


# NEUTRAL PERFORMANCE TESTS
class TestNeutralPerformance:
    @pytest.mark.asyncio
    async def test_neutral_rating(self):
        """Test neutral performance rating."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("8"),
            sharpe_ratio=Decimal("0.6"),
            sortino_ratio=Decimal("0.8"),
            max_drawdown_pct=Decimal("18"),
            win_rate_pct=Decimal("45"),
            profit_factor=Decimal("1.2"),
            calmar_ratio=Decimal("0.44"),
            volatility_pct=Decimal("22"),
            cumulative_return_pct=Decimal("10"),
            num_trades=120,
        )

        request = ReportGenerationRequest(
            report_id="test_neutral_001",
            profile_id="profile_neutral",
            input_id="user_neutral",
            strategy_name="Neutral Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="mean_reversion",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("50000"),
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert result.overall_rating == "neutral"
        assert len(result.weaknesses) >= 0


# POOR PERFORMANCE TESTS
class TestPoorPerformance:
    @pytest.mark.asyncio
    async def test_poor_rating(self):
        """Test poor performance rating."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("2"),
            sharpe_ratio=Decimal("0.15"),
            sortino_ratio=Decimal("0.2"),
            max_drawdown_pct=Decimal("35"),
            win_rate_pct=Decimal("35"),
            profit_factor=Decimal("0.8"),
            calmar_ratio=Decimal("0.06"),
            volatility_pct=Decimal("35"),
            cumulative_return_pct=Decimal("3"),
            num_trades=80,
        )

        request = ReportGenerationRequest(
            report_id="test_poor_001",
            profile_id="profile_poor",
            input_id="user_poor",
            strategy_name="Poor Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("25000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert result.overall_rating == "poor"
        assert len(result.weaknesses) > 0

    @pytest.mark.asyncio
    async def test_poor_weaknesses_identified(self):
        """Test that weaknesses are properly identified for poor performance."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("1"),
            sharpe_ratio=Decimal("0.05"),
            sortino_ratio=Decimal("0.1"),
            max_drawdown_pct=Decimal("50"),
            win_rate_pct=Decimal("30"),
            profit_factor=Decimal("0.5"),
            calmar_ratio=Decimal("0.02"),
            volatility_pct=Decimal("40"),
            cumulative_return_pct=Decimal("1"),
            num_trades=50,
        )

        request = ReportGenerationRequest(
            report_id="test_poor_weakness_001",
            profile_id="profile_poor_weakness",
            input_id="user_poor_weakness",
            strategy_name="Very Poor Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="transformer_engine",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("10000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("10"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert len(result.weaknesses) >= 3
        assert any("Poor risk-adjusted" in w for w in result.weaknesses)
        assert any("Underperforming" in w for w in result.weaknesses)
        assert any("Exceeding" in w for w in result.weaknesses)


# HTML CONTENT TESTS
class TestHTMLContent:
    @pytest.mark.asyncio
    async def test_html_content_generated(self):
        """Test that HTML content is generated."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.0"),
            sortino_ratio=Decimal("1.2"),
            max_drawdown_pct=Decimal("12"),
            win_rate_pct=Decimal("50"),
            profit_factor=Decimal("1.5"),
            calmar_ratio=Decimal("1.0"),
            volatility_pct=Decimal("15"),
            cumulative_return_pct=Decimal("15"),
            num_trades=100,
        )

        request = ReportGenerationRequest(
            report_id="test_html_001",
            profile_id="profile_html",
            input_id="user_html",
            strategy_name="Test Strategy HTML",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("50"),
                    expected_return_contribution_pct=Decimal("60"),
                    risk_contribution_pct=Decimal("50"),
                ),
                AllocationSnapshot(
                    module_name="mean_reversion",
                    allocation_pct=Decimal("50"),
                    expected_return_contribution_pct=Decimal("40"),
                    risk_contribution_pct=Decimal("50"),
                ),
            ],
            capital_eur=Decimal("100000"),
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert result.html_content is not None
        assert "<!DOCTYPE html>" in result.html_content
        assert "Test Strategy HTML" in result.html_content
        assert "Annual Return" in result.html_content
        assert "Sharpe Ratio" in result.html_content
        assert "Portfolio Allocation" in result.html_content

    @pytest.mark.asyncio
    async def test_html_contains_metrics(self):
        """Test that HTML contains all metrics."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("25"),
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("2.0"),
            max_drawdown_pct=Decimal("10"),
            win_rate_pct=Decimal("55"),
            profit_factor=Decimal("2.0"),
            calmar_ratio=Decimal("2.5"),
            volatility_pct=Decimal("15"),
            cumulative_return_pct=Decimal("30"),
            num_trades=150,
        )

        request = ReportGenerationRequest(
            report_id="test_html_metrics_001",
            profile_id="profile_html_metrics",
            input_id="user_html_metrics",
            strategy_name="Metrics Test Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="ensemble",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("200000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert "25.00%" in result.html_content  # Annual return
        assert "1.50" in result.html_content  # Sharpe ratio


# RECOMMENDATIONS TESTS
class TestRecommendations:
    @pytest.mark.asyncio
    async def test_recommendations_for_high_drawdown(self):
        """Test recommendations generated for high drawdown."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("20"),
            sharpe_ratio=Decimal("0.8"),
            sortino_ratio=Decimal("1.0"),
            max_drawdown_pct=Decimal("40"),  # High drawdown
            win_rate_pct=Decimal("50"),
            profit_factor=Decimal("1.5"),
            calmar_ratio=Decimal("0.5"),
            volatility_pct=Decimal("30"),
            cumulative_return_pct=Decimal("25"),
            num_trades=100,
        )

        request = ReportGenerationRequest(
            report_id="test_rec_dd_001",
            profile_id="profile_rec_dd",
            input_id="user_rec_dd",
            strategy_name="High Drawdown Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("100000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert len(result.recommendations) > 0
        assert any(
            "defensive" in rec.lower() or "drawdown" in rec.lower()
            for rec in result.recommendations
        )

    @pytest.mark.asyncio
    async def test_recommendations_for_low_return(self):
        """Test recommendations for underperforming return."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("5"),  # Low return
            sharpe_ratio=Decimal("0.7"),
            sortino_ratio=Decimal("0.9"),
            max_drawdown_pct=Decimal("8"),
            win_rate_pct=Decimal("50"),
            profit_factor=Decimal("1.5"),
            calmar_ratio=Decimal("0.625"),
            volatility_pct=Decimal("12"),
            cumulative_return_pct=Decimal("6"),
            num_trades=80,
        )

        request = ReportGenerationRequest(
            report_id="test_rec_return_001",
            profile_id="profile_rec_return",
            input_id="user_rec_return",
            strategy_name="Low Return Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="pairs_trading",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("75000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert any("return" in rec.lower() for rec in result.recommendations)


# REPORT HISTORY TESTS
class TestReportHistory:
    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test that report history is tracked."""
        gen = ReportingGenerator()

        for i in range(3):
            metrics = StrategyMetrics(
                annual_return_pct=Decimal("15"),
                sharpe_ratio=Decimal("1.2"),
                sortino_ratio=Decimal("1.5"),
                max_drawdown_pct=Decimal("12"),
                win_rate_pct=Decimal("50"),
                profit_factor=Decimal("1.6"),
                calmar_ratio=Decimal("1.25"),
                volatility_pct=Decimal("15"),
                cumulative_return_pct=Decimal("18"),
                num_trades=100,
            )

            request = ReportGenerationRequest(
                report_id=f"test_hist_{i}",
                profile_id=f"profile_hist_{i}",
                input_id=f"user_hist_{i}",
                strategy_name=f"Strategy {i}",
                backtest_metrics=metrics,
                allocations=[
                    AllocationSnapshot(
                        module_name="momentum",
                        allocation_pct=Decimal("100"),
                        expected_return_contribution_pct=Decimal("100"),
                        risk_contribution_pct=Decimal("100"),
                    ),
                ],
                capital_eur=Decimal("100000"),
                target_annual_return_pct=Decimal("12"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )

            await gen.generate_report(request)

        history = await gen.get_report_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history retrieval with limit."""
        gen = ReportingGenerator()

        for i in range(5):
            metrics = StrategyMetrics(
                annual_return_pct=Decimal("12"),
                sharpe_ratio=Decimal("1.0"),
                sortino_ratio=Decimal("1.3"),
                max_drawdown_pct=Decimal("10"),
                win_rate_pct=Decimal("48"),
                profit_factor=Decimal("1.4"),
                calmar_ratio=Decimal("1.2"),
                volatility_pct=Decimal("14"),
                cumulative_return_pct=Decimal("15"),
                num_trades=90,
            )

            request = ReportGenerationRequest(
                report_id=f"test_limit_{i}",
                profile_id=f"profile_limit_{i}",
                input_id=f"user_limit_{i}",
                strategy_name=f"Strategy {i}",
                backtest_metrics=metrics,
                allocations=[
                    AllocationSnapshot(
                        module_name="mean_reversion",
                        allocation_pct=Decimal("100"),
                        expected_return_contribution_pct=Decimal("100"),
                        risk_contribution_pct=Decimal("100"),
                    ),
                ],
                capital_eur=Decimal("100000"),
                target_annual_return_pct=Decimal("10"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )

            await gen.generate_report(request)

        history = await gen.get_report_history(limit=2)
        assert len(history) == 2


# SUMMARY GENERATION TESTS
class TestSummaryGeneration:
    @pytest.mark.asyncio
    async def test_summary_excellent(self):
        """Test summary generation for excellent performance."""
        gen = ReportingGenerator()

        metrics = StrategyMetrics(
            annual_return_pct=Decimal("28"),
            sharpe_ratio=Decimal("2.0"),
            sortino_ratio=Decimal("2.5"),
            max_drawdown_pct=Decimal("9"),
            win_rate_pct=Decimal("60"),
            profit_factor=Decimal("2.5"),
            calmar_ratio=Decimal("3.1"),
            volatility_pct=Decimal("14"),
            cumulative_return_pct=Decimal("35"),
            num_trades=200,
        )

        request = ReportGenerationRequest(
            report_id="test_summary_exc_001",
            profile_id="profile_summary_exc",
            input_id="user_summary_exc",
            strategy_name="Excellent Performance Strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="transformer_engine",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("100"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("500000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await gen.generate_report(request)

        assert result.success
        assert "strong risk-adjusted return profile" in result.summary.lower()
        assert "28.0%" in result.summary or "28.00%" in result.summary
        assert "200 trades" in result.summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
