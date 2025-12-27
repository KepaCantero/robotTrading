"""
BATCH G - T9.1: Unit Tests for ReportingGenerator

Tests:
- Performance report generation
- Overall performance rating assessment
- Strength identification (based on metrics)
- Weakness identification (based on gaps)
- Recommendation generation for improvements
- Metric threshold evaluation
- Report content generation
- History tracking and status reporting
"""

from decimal import Decimal

import pytest

from app.services.reporting_generator.models import (
    AllocationSnapshot,
    ReportGenerationRequest,
    StrategyMetrics,
)
from app.services.reporting_generator.reporting_generator import ReportingGenerator


@pytest.fixture
def reporting_generator():
    """Create ReportingGenerator instance for tests."""
    return ReportingGenerator()


class TestBasicReportGeneration:
    """Test basic report generation."""

    @pytest.mark.asyncio
    async def test_generate_excellent_performance_report(self, reporting_generator):
        """Test report generation for excellent performance."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("25"),
            sharpe_ratio=Decimal("2.5"),
            sortino_ratio=Decimal("3.0"),
            max_drawdown_pct=Decimal("8"),
            win_rate_pct=Decimal("65"),
            profit_factor=Decimal("2.5"),
            calmar_ratio=Decimal("3.1"),
            volatility_pct=Decimal("10"),
            cumulative_return_pct=Decimal("120"),
            num_trades=250,
        )

        request = ReportGenerationRequest(
            report_id="RPT-001",
            profile_id="PROF-001",
            input_id="INPUT-001",
            strategy_name="momentum_growth",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("50"),
                    expected_return_contribution_pct=Decimal("15"),
                    risk_contribution_pct=Decimal("40"),
                ),
                AllocationSnapshot(
                    module_name="ensemble_strategy",
                    allocation_pct=Decimal("50"),
                    expected_return_contribution_pct=Decimal("10"),
                    risk_contribution_pct=Decimal("30"),
                ),
            ],
            capital_eur=Decimal("250000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        report = await reporting_generator.generate_report(request)

        assert report is not None
        assert report.success is True
        assert report.report_id == "RPT-001"
        assert report.strategy_name == "momentum_growth"

    @pytest.mark.asyncio
    async def test_generate_poor_performance_report(self, reporting_generator):
        """Test report generation for poor performance."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("2"),
            sharpe_ratio=Decimal("0.3"),
            sortino_ratio=Decimal("0.2"),
            max_drawdown_pct=Decimal("35"),
            win_rate_pct=Decimal("35"),
            profit_factor=Decimal("0.8"),
            calmar_ratio=Decimal("0.06"),
            volatility_pct=Decimal("25"),
            cumulative_return_pct=Decimal("5"),
            num_trades=150,
        )

        request = ReportGenerationRequest(
            report_id="RPT-002",
            profile_id="PROF-002",
            input_id="INPUT-002",
            strategy_name="failing_strategy",
            backtest_metrics=metrics,
            allocations=[
                AllocationSnapshot(
                    module_name="momentum",
                    allocation_pct=Decimal("100"),
                    expected_return_contribution_pct=Decimal("2"),
                    risk_contribution_pct=Decimal("100"),
                ),
            ],
            capital_eur=Decimal("100000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        report = await reporting_generator.generate_report(request)

        assert report.success is True
        # Poor performance should have clear weaknesses
        assert len(report.weaknesses) > 0


class TestPerformanceRating:
    """Test performance rating assessment."""

    @pytest.mark.asyncio
    async def test_excellent_rating(self, reporting_generator):
        """Test excellent performance rating."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("28"),
            sharpe_ratio=Decimal("2.8"),
            sortino_ratio=Decimal("3.5"),
            max_drawdown_pct=Decimal("7"),
            win_rate_pct=Decimal("70"),
            profit_factor=Decimal("3.0"),
            calmar_ratio=Decimal("4.0"),
            volatility_pct=Decimal("9"),
            cumulative_return_pct=Decimal("140"),
            num_trades=300,
        )

        request = ReportGenerationRequest(
            report_id="RPT-003",
            profile_id="PROF-003",
            input_id="INPUT-003",
            strategy_name="excellent_strategy",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("250000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        report = await reporting_generator.generate_report(request)

        assert report.overall_rating in ["excellent", "good"]

    @pytest.mark.asyncio
    async def test_neutral_rating(self, reporting_generator):
        """Test neutral/medium performance rating."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("10"),
            sharpe_ratio=Decimal("0.8"),
            sortino_ratio=Decimal("0.9"),
            max_drawdown_pct=Decimal("22"),
            win_rate_pct=Decimal("48"),
            profit_factor=Decimal("1.2"),
            calmar_ratio=Decimal("0.45"),
            volatility_pct=Decimal("18"),
            cumulative_return_pct=Decimal("50"),
            num_trades=200,
        )

        request = ReportGenerationRequest(
            report_id="RPT-004",
            profile_id="PROF-004",
            input_id="INPUT-004",
            strategy_name="neutral_strategy",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("150000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("25"),
        )

        report = await reporting_generator.generate_report(request)

        assert report.overall_rating in ["neutral", "good", "poor"]


class TestStrengthIdentification:
    """Test strength identification."""

    @pytest.mark.asyncio
    async def test_identify_high_return_strength(self, reporting_generator):
        """Test identification of strong returns."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("30"),  # Excellent return
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("1.8"),
            max_drawdown_pct=Decimal("15"),
            win_rate_pct=Decimal("55"),
            profit_factor=Decimal("1.8"),
            calmar_ratio=Decimal("2.0"),
            volatility_pct=Decimal("15"),
            cumulative_return_pct=Decimal("150"),
            num_trades=200,
        )

        request = ReportGenerationRequest(
            report_id="RPT-005",
            profile_id="PROF-005",
            input_id="INPUT-005",
            strategy_name="high_return",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("200000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        report = await reporting_generator.generate_report(request)

        # Should identify strong return as strength
        assert len(report.strengths) > 0

    @pytest.mark.asyncio
    async def test_identify_low_drawdown_strength(self, reporting_generator):
        """Test identification of low drawdown strength."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.6"),
            sortino_ratio=Decimal("1.9"),
            max_drawdown_pct=Decimal("5"),  # Excellent low drawdown
            win_rate_pct=Decimal("60"),
            profit_factor=Decimal("2.0"),
            calmar_ratio=Decimal("2.4"),
            volatility_pct=Decimal("8"),
            cumulative_return_pct=Decimal("60"),
            num_trades=180,
        )

        request = ReportGenerationRequest(
            report_id="RPT-006",
            profile_id="PROF-006",
            input_id="INPUT-006",
            strategy_name="low_drawdown",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("200000"),
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        report = await reporting_generator.generate_report(request)

        assert len(report.strengths) > 0


class TestWeaknessIdentification:
    """Test weakness identification."""

    @pytest.mark.asyncio
    async def test_identify_low_return_weakness(self, reporting_generator):
        """Test identification of low return weakness."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("3"),  # Below target
            sharpe_ratio=Decimal("0.4"),
            sortino_ratio=Decimal("0.5"),
            max_drawdown_pct=Decimal("18"),
            win_rate_pct=Decimal("42"),
            profit_factor=Decimal("1.0"),
            calmar_ratio=Decimal("0.17"),
            volatility_pct=Decimal("20"),
            cumulative_return_pct=Decimal("15"),
            num_trades=150,
        )

        request = ReportGenerationRequest(
            report_id="RPT-007",
            profile_id="PROF-007",
            input_id="INPUT-007",
            strategy_name="low_return",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("150000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        report = await reporting_generator.generate_report(request)

        # Should identify low return as weakness
        assert len(report.weaknesses) > 0

    @pytest.mark.asyncio
    async def test_identify_high_drawdown_weakness(self, reporting_generator):
        """Test identification of high drawdown weakness."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("15"),
            sharpe_ratio=Decimal("0.6"),
            sortino_ratio=Decimal("0.7"),
            max_drawdown_pct=Decimal("40"),  # Above target
            win_rate_pct=Decimal("45"),
            profit_factor=Decimal("1.3"),
            calmar_ratio=Decimal("0.375"),
            volatility_pct=Decimal("28"),
            cumulative_return_pct=Decimal("75"),
            num_trades=200,
        )

        request = ReportGenerationRequest(
            report_id="RPT-008",
            profile_id="PROF-008",
            input_id="INPUT-008",
            strategy_name="high_drawdown",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("200000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        report = await reporting_generator.generate_report(request)

        # Should identify high drawdown as weakness
        assert len(report.weaknesses) > 0


class TestRecommendationGeneration:
    """Test recommendation generation."""

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, reporting_generator):
        """Test recommendation generation based on weaknesses."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("8"),
            sharpe_ratio=Decimal("0.6"),
            sortino_ratio=Decimal("0.7"),
            max_drawdown_pct=Decimal("25"),
            win_rate_pct=Decimal("42"),
            profit_factor=Decimal("1.1"),
            calmar_ratio=Decimal("0.32"),
            volatility_pct=Decimal("22"),
            cumulative_return_pct=Decimal("40"),
            num_trades=180,
        )

        request = ReportGenerationRequest(
            report_id="RPT-009",
            profile_id="PROF-009",
            input_id="INPUT-009",
            strategy_name="underperforming",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("150000"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("18"),
        )

        report = await reporting_generator.generate_report(request)

        # Should generate recommendations
        assert len(report.recommendations) > 0


class TestReportHistory:
    """Test report history tracking."""

    @pytest.mark.asyncio
    async def test_report_history_tracked(self, reporting_generator):
        """Test reports are tracked in history."""
        metrics = StrategyMetrics(
            annual_return_pct=Decimal("15"),
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("1.8"),
            max_drawdown_pct=Decimal("12"),
            win_rate_pct=Decimal("55"),
            profit_factor=Decimal("1.8"),
            calmar_ratio=Decimal("1.25"),
            volatility_pct=Decimal("12"),
            cumulative_return_pct=Decimal("75"),
            num_trades=200,
        )

        request = ReportGenerationRequest(
            report_id="RPT-010",
            profile_id="PROF-010",
            input_id="INPUT-010",
            strategy_name="tracked_strategy",
            backtest_metrics=metrics,
            allocations=[],
            capital_eur=Decimal("200000"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        await reporting_generator.generate_report(request)

        history = await reporting_generator.get_report_history()
        assert len(history) > 0
        assert history[-1].report_id == "RPT-010"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
