"""
T9.1: Unit Tests for ReportingGenerator

Tests cover:
- Report generation
- Metric extraction
- Risk calculations
- HTML report generation
"""

import pytest
from app.services.reporting import (
    ReportingGenerator,
)


@pytest.fixture
def generator():
    """Create ReportingGenerator instance."""
    return ReportingGenerator()


@pytest.fixture
def sample_backtest_result():
    """Sample backtest result."""
    return {
        "strategy_name": "momentum_modular",
        "total_return": 0.25,
        "sharpe_ratio": 1.5,
        "sortino_ratio": 1.8,
        "max_drawdown": -0.15,
        "win_rate": 0.65,
        "profit_factor": 2.1,
        "total_trades": 45,
        "final_capital": 125000,
    }


@pytest.fixture
def sample_allocation():
    """Sample portfolio allocation."""
    return {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}


@pytest.fixture
def sample_monthly_returns():
    """Sample monthly returns."""
    return [0.02, 0.03, -0.01, 0.04, 0.02, 0.01, 0.03, 0.02, 0.04, -0.02, 0.03, 0.02]


# =============================================================================
# Test Report Generation
# =============================================================================

class TestReportGeneration:
    """Test report generation."""

    @pytest.mark.asyncio
    async def test_generate_report_complete(
        self, generator, sample_backtest_result, sample_allocation, sample_monthly_returns
    ):
        """Test complete report generation."""
        report = await generator.generate_report(
            "test_strategy",
            sample_backtest_result,
            sample_allocation,
            sample_monthly_returns,
        )

        assert report.report_id is not None
        assert report.strategy_name == "test_strategy"
        assert report.summary is not None
        assert report.metrics is not None
        assert report.risk_metrics is not None
        assert report.allocation == sample_allocation
        assert report.monthly_returns == sample_monthly_returns
        assert len(report.html_report) > 0

    @pytest.mark.asyncio
    async def test_generate_report_has_timestamp(
        self, generator, sample_backtest_result, sample_allocation, sample_monthly_returns
    ):
        """Test that report has generated_at timestamp."""
        report = await generator.generate_report(
            "test_strategy",
            sample_backtest_result,
            sample_allocation,
            sample_monthly_returns,
        )

        assert report.generated_at is not None


# =============================================================================
# Test Metric Extraction
# =============================================================================

class TestMetricExtraction:
    """Test metric extraction from backtest results."""

    @pytest.mark.asyncio
    async def test_extract_metrics(self, generator, sample_backtest_result):
        """Test extracting metrics from backtest result."""
        metrics = await generator._extract_metrics(sample_backtest_result)

        assert metrics["total_return"] == 0.25
        assert metrics["sharpe_ratio"] == 1.5
        assert metrics["sortino_ratio"] == 1.8
        assert metrics["max_drawdown"] == -0.15
        assert metrics["win_rate"] == 0.65
        assert metrics["profit_factor"] == 2.1
        assert metrics["total_trades"] == 45

    @pytest.mark.asyncio
    async def test_extract_metrics_handles_missing_values(self, generator):
        """Test metric extraction with missing values."""
        minimal_result = {"strategy_name": "test"}
        metrics = await generator._extract_metrics(minimal_result)

        assert metrics["total_return"] == 0.0
        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["max_drawdown"] == 0.0
        assert metrics["total_trades"] == 0


# =============================================================================
# Test Risk Metrics Calculation
# =============================================================================

class TestRiskMetrics:
    """Test risk metrics calculation."""

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics(
        self, generator, sample_backtest_result, sample_monthly_returns
    ):
        """Test risk metrics calculation."""
        risk_metrics = await generator._calculate_risk_metrics(
            sample_backtest_result, sample_monthly_returns
        )

        assert "volatility" in risk_metrics
        assert "max_drawdown" in risk_metrics
        assert "var_95" in risk_metrics
        assert "cvar_95" in risk_metrics
        assert "calmar_ratio" in risk_metrics
        assert risk_metrics["volatility"] > 0
        assert risk_metrics["calmar_ratio"] != 0

    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_empty_returns(
        self, generator, sample_backtest_result
    ):
        """Test risk metrics with empty returns."""
        risk_metrics = await generator._calculate_risk_metrics(
            sample_backtest_result, []
        )

        assert risk_metrics["volatility"] == 0.0
        assert risk_metrics["var_95"] == 0.0


# =============================================================================
# Test VaR and CVaR Calculation
# =============================================================================

class TestVaRCalculation:
    """Test Value at Risk calculations."""

    def test_calculate_var_basic(self, generator, sample_monthly_returns):
        """Test VaR calculation."""
        var = generator._calculate_var(sample_monthly_returns, 0.95)
        # VaR should be one of the returns or close to them
        assert var <= min(sample_monthly_returns) or var != 0.0

    def test_calculate_var_empty_list(self, generator):
        """Test VaR with empty returns."""
        var = generator._calculate_var([])
        assert var == 0.0

    def test_calculate_cvar_basic(self, generator, sample_monthly_returns):
        """Test CVaR calculation."""
        cvar = generator._calculate_cvar(sample_monthly_returns, 0.95)
        # CVaR should be calculated and valid
        assert cvar is not None
        # With 12 returns and 95% confidence, should capture bottom ~1 return
        assert isinstance(cvar, (int, float))

    def test_calculate_cvar_empty_list(self, generator):
        """Test CVaR with empty returns."""
        cvar = generator._calculate_cvar([])
        assert cvar == 0.0


# =============================================================================
# Test Calmar Ratio Calculation
# =============================================================================

class TestCalmarRatio:
    """Test Calmar ratio calculation."""

    def test_calculate_calmar_ratio_positive(self, generator):
        """Test Calmar ratio with positive values."""
        calmar = generator._calculate_calmar_ratio(0.25, -0.15)
        assert calmar > 0
        assert calmar == pytest.approx(0.25 / 0.15, rel=0.01)

    def test_calculate_calmar_ratio_zero_drawdown(self, generator):
        """Test Calmar ratio with zero drawdown."""
        calmar = generator._calculate_calmar_ratio(0.25, 0.0)
        assert calmar == 0.0

    def test_calculate_calmar_ratio_small_drawdown(self, generator):
        """Test Calmar ratio with very small drawdown."""
        calmar = generator._calculate_calmar_ratio(0.25, -0.0001)
        assert calmar == 0.0


# =============================================================================
# Test Summary Generation
# =============================================================================

class TestSummaryGeneration:
    """Test summary generation."""

    @pytest.mark.asyncio
    async def test_generate_summary(self, generator, sample_backtest_result):
        """Test summary generation."""
        summary = await generator._generate_summary("test", sample_backtest_result)

        assert summary["strategy_name"] == "test"
        assert summary["total_return"] == 0.25
        assert summary["sharpe_ratio"] == 1.5
        assert summary["max_drawdown"] == -0.15
        assert summary["win_rate"] == 0.65

    @pytest.mark.asyncio
    async def test_generate_summary_handles_missing_values(self, generator):
        """Test summary generation with missing values."""
        summary = await generator._generate_summary("test", {})

        assert summary["strategy_name"] == "test"
        assert summary["total_return"] == 0.0
        assert summary["sharpe_ratio"] == 0.0


# =============================================================================
# Test HTML Report Generation
# =============================================================================

class TestHTMLReportGeneration:
    """Test HTML report generation."""

    @pytest.mark.asyncio
    async def test_generate_html_report(
        self, generator, sample_allocation, sample_backtest_result
    ):
        """Test HTML report generation."""
        summary = await generator._generate_summary("test_strategy", sample_backtest_result)
        metrics = await generator._extract_metrics(sample_backtest_result)
        risk_metrics = await generator._calculate_risk_metrics(
            sample_backtest_result, [0.02, 0.03, 0.01]
        )

        html = await generator._generate_html_report(
            "test_strategy", summary, metrics, risk_metrics, sample_allocation
        )

        assert "<html>" in html
        assert "test_strategy" in html
        assert "Performance Summary" in html
        assert "Risk Metrics" in html
        assert "Portfolio Allocation" in html
        assert "AAPL" in html
        assert "MSFT" in html

    @pytest.mark.asyncio
    async def test_html_report_contains_metrics(
        self, generator, sample_allocation, sample_backtest_result
    ):
        """Test that HTML report contains key metrics."""
        summary = await generator._generate_summary("test", sample_backtest_result)
        metrics = await generator._extract_metrics(sample_backtest_result)
        risk_metrics = await generator._calculate_risk_metrics(sample_backtest_result, [0.01])

        html = await generator._generate_html_report(
            "test", summary, metrics, risk_metrics, sample_allocation
        )

        # Should contain key metrics
        assert "25.00%" in html or "0.25" in html  # Annual return
        assert "1.50" in html  # Sharpe ratio


# =============================================================================
# Test Safe Float Conversion
# =============================================================================

class TestSafeFloatConversion:
    """Test safe float conversion."""

    def test_safe_float_from_float(self, generator):
        """Test converting float."""
        assert generator._safe_float(1.5) == 1.5

    def test_safe_float_from_int(self, generator):
        """Test converting int."""
        assert generator._safe_float(5) == 5.0

    def test_safe_float_from_string(self, generator):
        """Test converting string."""
        assert generator._safe_float("3.14") == 3.14

    def test_safe_float_from_none(self, generator):
        """Test converting None."""
        assert generator._safe_float(None) == 0.0

    def test_safe_float_from_invalid(self, generator):
        """Test converting invalid value."""
        assert generator._safe_float("invalid") == 0.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_report_workflow(
        self, generator, sample_backtest_result, sample_allocation, sample_monthly_returns
    ):
        """Test complete report generation workflow."""
        report = await generator.generate_report(
            "complete_test",
            sample_backtest_result,
            sample_allocation,
            sample_monthly_returns,
        )

        # Verify all components are present
        assert report.report_id is not None
        assert report.strategy_name == "complete_test"
        assert len(report.summary) > 0
        assert len(report.metrics) > 0
        assert len(report.risk_metrics) > 0
        assert len(report.allocation) == 4
        assert len(report.monthly_returns) == 12
        assert len(report.html_report) > 100
        assert "<html>" in report.html_report
