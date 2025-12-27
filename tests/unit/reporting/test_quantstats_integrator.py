"""Unit tests for T9.1 QuantStatsIntegrator component"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from app.services.reporting_generator.quantstats_integrator import (
    AdvancedMetrics,
    QuantStatsIntegrator,
    StatisticsReport,
    get_quantstats_integrator,
)


class TestAdvancedMetrics:
    """Test AdvancedMetrics data class."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = AdvancedMetrics(
            calmar_ratio=Decimal("2.5"),
            stability_index=Decimal("0.85"),
            tail_ratio=Decimal("1.2"),
            var_95=Decimal("-2.5"),
            cvar_95=Decimal("-3.5"),
            omega_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("3.0"),
        )

        assert metrics.calmar_ratio == Decimal("2.5")
        assert metrics.stability_index == Decimal("0.85")
        assert metrics.tail_ratio == Decimal("1.2")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = AdvancedMetrics(
            calmar_ratio=Decimal("2.5"),
            stability_index=Decimal("0.85"),
            tail_ratio=Decimal("1.2"),
            var_95=Decimal("-2.5"),
            cvar_95=Decimal("-3.5"),
            omega_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("3.0"),
            information_ratio=Decimal("0.5"),
            kurtosis=Decimal("0.3"),
            skewness=Decimal("-0.1"),
        )

        metrics_dict = metrics.to_dict()

        assert "calmar_ratio" in metrics_dict
        assert metrics_dict["calmar_ratio"] == 2.5
        assert metrics_dict["information_ratio"] == 0.5
        assert isinstance(metrics_dict, dict)


class TestStatisticsReport:
    """Test StatisticsReport data class."""

    def test_initialization(self):
        """Test report initialization."""
        metrics = AdvancedMetrics(
            calmar_ratio=Decimal("2.5"),
            stability_index=Decimal("0.85"),
            tail_ratio=Decimal("1.2"),
            var_95=Decimal("-2.5"),
            cvar_95=Decimal("-3.5"),
            omega_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("3.0"),
        )

        report = StatisticsReport(
            report_date=datetime.utcnow(),
            total_return_pct=Decimal("25.5"),
            annual_return_pct=Decimal("15.0"),
            annual_volatility_pct=Decimal("12.0"),
            sharpe_ratio=Decimal("1.25"),
            max_drawdown_pct=Decimal("18.0"),
            win_rate_pct=Decimal("55.0"),
            advanced_metrics=metrics,
            num_trades=150,
            best_day_pct=Decimal("5.5"),
            worst_day_pct=Decimal("-4.2"),
            best_month_pct=Decimal("8.5"),
            worst_month_pct=Decimal("-6.5"),
        )

        assert report.total_return_pct == Decimal("25.5")
        assert report.num_trades == 150
        assert report.best_day_pct == Decimal("5.5")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = AdvancedMetrics(
            calmar_ratio=Decimal("2.5"),
            stability_index=Decimal("0.85"),
            tail_ratio=Decimal("1.2"),
            var_95=Decimal("-2.5"),
            cvar_95=Decimal("-3.5"),
            omega_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("3.0"),
        )

        report = StatisticsReport(
            report_date=datetime.utcnow(),
            total_return_pct=Decimal("25.5"),
            annual_return_pct=Decimal("15.0"),
            annual_volatility_pct=Decimal("12.0"),
            sharpe_ratio=Decimal("1.25"),
            max_drawdown_pct=Decimal("18.0"),
            win_rate_pct=Decimal("55.0"),
            advanced_metrics=metrics,
            num_trades=150,
            best_day_pct=Decimal("5.5"),
            worst_day_pct=Decimal("-4.2"),
            best_month_pct=Decimal("8.5"),
            worst_month_pct=Decimal("-6.5"),
        )

        report_dict = report.to_dict()

        assert "total_return_pct" in report_dict
        assert report_dict["num_trades"] == 150
        assert "advanced_metrics" in report_dict


class TestQuantStatsIntegrator:
    """Test QuantStatsIntegrator component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.integrator = QuantStatsIntegrator()
        # Sample returns: 252 daily returns (1 year of trading)
        np.random.seed(42)
        self.returns = np.random.normal(0.0005, 0.01, 252)  # Daily returns ~5% annual, 10% vol
        self.returns_decimal = [Decimal(str(r)) for r in self.returns]

    def test_initialization(self):
        """Test integrator initialization."""
        assert self.integrator.reports_generated == 0
        assert isinstance(self.integrator, QuantStatsIntegrator)

    # Calmar Ratio Tests
    def test_calculate_calmar_ratio_valid(self):
        """Test Calmar ratio calculation with valid inputs."""
        calmar = self.integrator._calculate_calmar_ratio(self.returns, Decimal("15"))

        assert calmar > Decimal("0")
        assert isinstance(calmar, Decimal)

    def test_calculate_calmar_ratio_zero_drawdown(self):
        """Test Calmar ratio with zero drawdown."""
        calmar = self.integrator._calculate_calmar_ratio(self.returns, Decimal("0"))

        assert calmar == Decimal("0")

    def test_calculate_calmar_ratio_none_drawdown(self):
        """Test Calmar ratio with None drawdown."""
        calmar = self.integrator._calculate_calmar_ratio(self.returns, None)

        assert calmar == Decimal("0")

    # Stability Index Tests
    def test_calculate_stability_index(self):
        """Test stability index calculation."""
        stability = self.integrator._calculate_stability_index(self.returns)

        assert Decimal("0") <= stability <= Decimal("1")
        assert isinstance(stability, Decimal)

    def test_stability_index_bounds(self):
        """Test stability index is bounded [0, 1]."""
        stability = self.integrator._calculate_stability_index(self.returns)
        assert stability >= Decimal("0")
        assert stability <= Decimal("1")

    # Tail Ratio Tests
    def test_calculate_tail_ratio(self):
        """Test tail ratio calculation."""
        tail_ratio = self.integrator._calculate_tail_ratio(self.returns)

        assert tail_ratio > Decimal("0")
        assert isinstance(tail_ratio, Decimal)

    def test_tail_ratio_zero_std_dev(self):
        """Test tail ratio with zero standard deviation."""
        constant_returns = np.zeros(10)
        tail_ratio = self.integrator._calculate_tail_ratio(constant_returns)

        assert tail_ratio == Decimal("1")

    # VaR Tests
    def test_calculate_var(self):
        """Test Value at Risk calculation."""
        var = self.integrator._calculate_var(self.returns, confidence=0.95)

        assert var < Decimal("0")  # Should be negative (loss)
        assert isinstance(var, Decimal)

    def test_var_confidence_levels(self):
        """Test VaR at different confidence levels."""
        var_95 = self.integrator._calculate_var(self.returns, confidence=0.95)
        var_99 = self.integrator._calculate_var(self.returns, confidence=0.99)

        # Higher confidence should have more extreme loss
        assert var_99 <= var_95

    # CVaR Tests
    def test_calculate_cvar(self):
        """Test Conditional VaR calculation."""
        cvar = self.integrator._calculate_cvar(self.returns, confidence=0.95)

        assert cvar < Decimal("0")
        assert isinstance(cvar, Decimal)

    def test_cvar_worse_than_var(self):
        """Test CVaR is worse than VaR."""
        var = self.integrator._calculate_var(self.returns, confidence=0.95)
        cvar = self.integrator._calculate_cvar(self.returns, confidence=0.95)

        assert cvar <= var  # CVaR is average of worst cases

    # Omega Ratio Tests
    def test_calculate_omega_ratio(self):
        """Test Omega ratio calculation."""
        omega = self.integrator._calculate_omega_ratio(self.returns)

        assert omega > Decimal("0")
        assert isinstance(omega, Decimal)

    # Sortino Ratio Tests
    def test_calculate_sortino_ratio(self):
        """Test Sortino ratio calculation."""
        sortino = self.integrator._calculate_sortino_ratio(self.returns)

        assert sortino >= Decimal("0")
        assert isinstance(sortino, Decimal)

    def test_sortino_ratio_no_losses(self):
        """Test Sortino ratio when no downside returns."""
        positive_returns = np.abs(self.returns)  # All positive
        sortino = self.integrator._calculate_sortino_ratio(positive_returns)

        assert sortino == Decimal("0")

    # Information Ratio Tests
    def test_calculate_information_ratio(self):
        """Test Information ratio calculation."""
        benchmark = self.returns + np.random.normal(0, 0.005, len(self.returns))
        info_ratio = self.integrator._calculate_information_ratio(self.returns, benchmark)

        assert isinstance(info_ratio, Decimal)

    # Monthly Distribution Tests
    def test_calculate_monthly_distribution(self):
        """Test monthly return distribution calculation."""
        monthly_dist = self.integrator._calculate_monthly_distribution(self.returns)

        assert isinstance(monthly_dist, dict)
        assert len(monthly_dist) > 0
        assert all(isinstance(k, str) for k in monthly_dist.keys())

    def test_monthly_distribution_insufficient_data(self):
        """Test monthly distribution with insufficient data."""
        short_returns = np.random.normal(0, 0.01, 10)
        monthly_dist = self.integrator._calculate_monthly_distribution(short_returns)

        assert monthly_dist == {}

    # Advanced Metrics Tests
    def test_calculate_advanced_metrics(self):
        """Test advanced metrics calculation."""
        metrics = self.integrator.calculate_advanced_metrics(
            self.returns_decimal,
            max_drawdown_pct=Decimal("15"),
        )

        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.calmar_ratio >= Decimal("0")
        assert Decimal("0") <= metrics.stability_index <= Decimal("1")
        assert metrics.tail_ratio > Decimal("0")

    def test_advanced_metrics_with_benchmark(self):
        """Test advanced metrics with benchmark returns."""
        benchmark = self.returns + np.random.normal(0, 0.005, len(self.returns))
        benchmark_decimal = [Decimal(str(b)) for b in benchmark]

        metrics = self.integrator.calculate_advanced_metrics(
            self.returns_decimal,
            benchmark_returns=benchmark_decimal,
            max_drawdown_pct=Decimal("15"),
        )

        assert metrics.information_ratio is not None

    def test_advanced_metrics_all_fields(self):
        """Test all advanced metrics fields are populated."""
        metrics = self.integrator.calculate_advanced_metrics(
            self.returns_decimal,
            max_drawdown_pct=Decimal("15"),
        )

        assert metrics.calmar_ratio is not None
        assert metrics.stability_index is not None
        assert metrics.tail_ratio is not None
        assert metrics.var_95 is not None
        assert metrics.cvar_95 is not None
        assert metrics.omega_ratio is not None
        assert metrics.sortino_ratio is not None
        assert metrics.kurtosis is not None
        assert metrics.skewness is not None

    # Statistics Report Tests
    def test_generate_statistics_report(self):
        """Test statistics report generation."""
        report = self.integrator.generate_statistics_report(
            returns=self.returns_decimal,
            annual_return_pct=Decimal("15.0"),
            annual_volatility_pct=Decimal("12.0"),
            sharpe_ratio=Decimal("1.25"),
            max_drawdown_pct=Decimal("18.0"),
            win_rate_pct=Decimal("55.0"),
            num_trades=150,
        )

        assert isinstance(report, StatisticsReport)
        assert report.annual_return_pct == Decimal("15.0")
        assert report.num_trades == 150
        assert isinstance(report.advanced_metrics, AdvancedMetrics)

    def test_statistics_report_increments_counter(self):
        """Test report generation increments counter."""
        initial_count = self.integrator.reports_generated

        self.integrator.generate_statistics_report(
            returns=self.returns_decimal,
            annual_return_pct=Decimal("15.0"),
            annual_volatility_pct=Decimal("12.0"),
            sharpe_ratio=Decimal("1.25"),
            max_drawdown_pct=Decimal("18.0"),
            win_rate_pct=Decimal("55.0"),
            num_trades=150,
        )

        assert self.integrator.reports_generated == initial_count + 1

    def test_statistics_report_multiple_generations(self):
        """Test multiple report generations."""
        for i in range(3):
            self.integrator.generate_statistics_report(
                returns=self.returns_decimal,
                annual_return_pct=Decimal("15.0"),
                annual_volatility_pct=Decimal("12.0"),
                sharpe_ratio=Decimal("1.25"),
                max_drawdown_pct=Decimal("18.0"),
                win_rate_pct=Decimal("55.0"),
                num_trades=150,
            )

        assert self.integrator.reports_generated == 3

    # Status Query Tests
    def test_get_integrator_status(self):
        """Test integrator status query."""
        status = self.integrator.get_integrator_status()

        assert "reports_generated" in status
        assert "status" in status
        assert "last_update" in status
        assert status["status"] == "operational"

    # Singleton Pattern Tests
    def test_singleton_pattern(self):
        """Test singleton pattern for integrator."""
        integrator1 = get_quantstats_integrator()
        integrator2 = get_quantstats_integrator()

        assert integrator1 is integrator2

    # Edge Case Tests
    def test_empty_returns_list(self):
        """Test with empty returns list."""
        empty_returns = np.array([])
        metrics = self.integrator._calculate_stability_index(empty_returns)

        assert metrics == Decimal("0")

    def test_single_return_value(self):
        """Test with single return value."""
        single_return = np.array([0.01])
        stability = self.integrator._calculate_stability_index(single_return)

        assert stability == Decimal("0")

    def test_constant_returns(self):
        """Test with constant returns (zero volatility)."""
        constant = np.ones(100) * 0.001
        metrics = self.integrator.calculate_advanced_metrics(
            [Decimal(str(r)) for r in constant],
            max_drawdown_pct=Decimal("5"),
        )

        assert metrics.stability_index == Decimal("1")  # Perfect linear fit

    def test_extreme_gains_and_losses(self):
        """Test with extreme gains and losses."""
        extreme_returns = np.array([-0.5, 0.5, -0.3, 0.8, -0.2])
        metrics = self.integrator.calculate_advanced_metrics(
            [Decimal(str(r)) for r in extreme_returns],
            max_drawdown_pct=Decimal("50"),
        )

        assert metrics.tail_ratio is not None
        assert metrics.omega_ratio is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
