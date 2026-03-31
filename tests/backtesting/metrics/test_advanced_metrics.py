"""
Unit tests for Advanced Financial Metrics Calculator - PHASE 4 MODULE 7

Tests all 10 advanced metrics:
- Calmar Ratio, Omega Ratio, Ulcer Index
- Annualized Volatility, Recovery Factor, Profit Factor
- Skewness, Kurtosis, Value at Risk, Conditional Value at Risk
"""

from decimal import Decimal

import pytest

from app.backtesting.advanced_metrics import AdvancedMetricsCalculator


@pytest.fixture
def calculator():
    """Create an AdvancedMetricsCalculator instance."""
    return AdvancedMetricsCalculator(risk_free_rate=Decimal("0.02"))


@pytest.fixture
def sample_returns():
    """Sample returns for testing."""
    return [
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("-0.01"),
        Decimal("0.015"),
        Decimal("0.005"),
        Decimal("-0.005"),
        Decimal("0.03"),
        Decimal("-0.02"),
        Decimal("0.01"),
        Decimal("0.02"),
    ]


@pytest.fixture
def sample_equity_curve():
    """Sample equity curve for testing."""
    return [
        Decimal("100000"),
        Decimal("101000"),
        Decimal("102050"),
        Decimal("101050"),
        Decimal("102575"),
        Decimal("103050"),
        Decimal("102050"),
        Decimal("104275"),
        Decimal("103210"),
        Decimal("104420"),
        Decimal("106450"),
    ]


class TestCalmarRatio:
    """Test Calmar Ratio calculation."""

    def test_calmar_ratio_positive(self, calculator):
        """Test Calmar ratio with positive metrics."""
        cagr = Decimal("0.20")  # 20% CAGR
        max_drawdown = Decimal("-0.10")  # -10% drawdown

        calmar = calculator.calculate_calmar_ratio(cagr, max_drawdown)

        assert calmar is not None
        assert float(calmar) == pytest.approx(2.0, rel=0.01)

    def test_calmar_ratio_zero_drawdown(self, calculator):
        """Test Calmar ratio with zero drawdown."""
        cagr = Decimal("0.20")
        max_drawdown = Decimal("0")

        calmar = calculator.calculate_calmar_ratio(cagr, max_drawdown)

        assert calmar is None

    def test_calmar_ratio_negative_cagr(self, calculator):
        """Test Calmar ratio with negative CAGR."""
        cagr = Decimal("-0.10")
        max_drawdown = Decimal("-0.20")

        calmar = calculator.calculate_calmar_ratio(cagr, max_drawdown)

        assert calmar is not None
        assert float(calmar) < 0


class TestOmegaRatio:
    """Test Omega Ratio calculation."""

    def test_omega_ratio_positive_returns(self, calculator, sample_returns):
        """Test Omega ratio with positive returns."""
        omega = calculator.calculate_omega_ratio(sample_returns, threshold=0.0)

        assert omega is not None
        assert float(omega) > 1.0  # Positive skew

    def test_omega_ratio_all_positive(self, calculator):
        """Test Omega ratio with all positive returns."""
        returns = [Decimal(f"0.0{i}") for i in range(1, 11)]

        omega = calculator.calculate_omega_ratio(returns, threshold=0.0)

        assert omega is not None
        assert float(omega) == pytest.approx(999999.0, rel=0.1)  # Very high Omega

    def test_omega_ratio_all_negative(self, calculator):
        """Test Omega ratio with all negative returns."""
        returns = [Decimal(f"-0.0{i}") for i in range(1, 11)]

        omega = calculator.calculate_omega_ratio(returns, threshold=0.0)

        assert omega is not None
        assert float(omega) <= 1.0  # Omega <= 1 when all returns are negative

    def test_omega_ratio_insufficient_data(self, calculator):
        """Test Omega ratio with insufficient data."""
        omega = calculator.calculate_omega_ratio([Decimal("0.01")])

        assert omega is None


class TestUlcerIndex:
    """Test Ulcer Index calculation."""

    def test_ulcer_index_stable(self, calculator, sample_equity_curve):
        """Test Ulcer index with stable equity curve."""
        ulcer = calculator.calculate_ulcer_index(sample_equity_curve)

        assert ulcer is not None
        assert float(ulcer) >= 0
        assert float(ulcer) < 1.0  # Should be < 1 for stable growth

    def test_ulcer_index_with_large_drawdown(self, calculator):
        """Test Ulcer index with large drawdown."""
        equity = [
            Decimal("100000"),
            Decimal("150000"),  # Peak
            Decimal("75000"),  # 50% drawdown
            Decimal("80000"),
            Decimal("85000"),
        ]

        ulcer = calculator.calculate_ulcer_index(equity)

        assert ulcer is not None
        assert float(ulcer) > 0.2  # Should be substantial

    def test_ulcer_index_insufficient_data(self, calculator):
        """Test Ulcer index with insufficient data."""
        ulcer = calculator.calculate_ulcer_index([Decimal("100000")])

        assert ulcer is None


class TestAnnualizedVolatility:
    """Test Annualized Volatility calculation."""

    def test_annualized_volatility_low(self, calculator):
        """Test volatility with low dispersion returns."""
        returns = [Decimal("0.01") for _ in range(10)]  # All same

        vol = calculator.calculate_annualized_volatility(returns)

        assert vol is not None
        assert float(vol) < 0.01  # Very low volatility

    def test_annualized_volatility_high(self, calculator):
        """Test volatility with high dispersion returns."""
        returns = [Decimal("0.05"), Decimal("-0.05")] * 10  # Oscillating

        vol = calculator.calculate_annualized_volatility(returns)

        assert vol is not None
        assert float(vol) > 0.5  # High volatility

    def test_annualized_volatility_insufficient_data(self, calculator):
        """Test volatility with insufficient data."""
        vol = calculator.calculate_annualized_volatility([Decimal("0.01")])

        assert vol is None


class TestRecoveryFactor:
    """Test Recovery Factor calculation."""

    def test_recovery_factor_positive(self, calculator):
        """Test recovery factor with profitable strategy."""
        total_pnl = Decimal("50000")
        max_drawdown = Decimal("-10000")

        recovery = calculator.calculate_recovery_factor(total_pnl, max_drawdown)

        assert recovery is not None
        assert float(recovery) == 5.0

    def test_recovery_factor_zero_drawdown(self, calculator):
        """Test recovery factor with zero drawdown."""
        total_pnl = Decimal("50000")
        max_drawdown = Decimal("0")

        recovery = calculator.calculate_recovery_factor(total_pnl, max_drawdown)

        assert recovery is None

    def test_recovery_factor_negative_pnl(self, calculator):
        """Test recovery factor with negative PnL."""
        total_pnl = Decimal("-50000")
        max_drawdown = Decimal("-10000")

        recovery = calculator.calculate_recovery_factor(total_pnl, max_drawdown)

        assert recovery is not None
        assert float(recovery) < 0


class TestProfitFactor:
    """Test Profit Factor calculation."""

    def test_profit_factor_good(self, calculator):
        """Test profit factor with good strategy."""
        gross_profit = Decimal("100000")
        gross_loss = Decimal("-40000")

        pf = calculator.calculate_profit_factor(gross_profit, gross_loss)

        assert pf is not None
        assert float(pf) == pytest.approx(2.5, rel=0.01)

    def test_profit_factor_breakeven(self, calculator):
        """Test profit factor at breakeven."""
        gross_profit = Decimal("50000")
        gross_loss = Decimal("-50000")

        pf = calculator.calculate_profit_factor(gross_profit, gross_loss)

        assert pf is not None
        assert float(pf) == pytest.approx(1.0, rel=0.01)

    def test_profit_factor_zero_loss(self, calculator):
        """Test profit factor with zero losses."""
        gross_profit = Decimal("100000")
        gross_loss = Decimal("0")

        pf = calculator.calculate_profit_factor(gross_profit, gross_loss)

        assert pf is not None
        assert float(pf) > 100  # Perfect scenario


class TestSkewness:
    """Test Skewness calculation."""

    def test_skewness_positive(self, calculator):
        """Test positive skewness."""
        returns = [
            Decimal("-0.02"),
            Decimal("-0.01"),
            Decimal("0.01"),
            Decimal("0.02"),
            Decimal("0.03"),
            Decimal("0.10"),
            Decimal("-0.015"),
            Decimal("0.005"),
            Decimal("0.01"),
            Decimal("0.02"),
        ]

        skew = calculator.calculate_skewness(returns)

        assert skew is not None
        assert float(skew) > 0  # Right tail

    def test_skewness_negative(self, calculator):
        """Test negative skewness."""
        returns = [
            Decimal("0.02"),
            Decimal("0.01"),
            Decimal("-0.01"),
            Decimal("-0.02"),
            Decimal("-0.03"),
            Decimal("-0.10"),
            Decimal("0.015"),
            Decimal("-0.005"),
            Decimal("-0.01"),
            Decimal("-0.02"),
        ]

        skew = calculator.calculate_skewness(returns)

        assert skew is not None
        assert float(skew) < 0  # Left tail

    def test_skewness_insufficient_data(self, calculator):
        """Test skewness with insufficient data."""
        skew = calculator.calculate_skewness([Decimal("0.01"), Decimal("0.02")])

        assert skew is None


class TestKurtosis:
    """Test Kurtosis calculation."""

    def test_kurtosis_normal(self, calculator, sample_returns):
        """Test kurtosis for roughly normal distribution."""
        kurt = calculator.calculate_kurtosis(sample_returns)

        assert kurt is not None
        assert isinstance(kurt, Decimal)

    def test_kurtosis_fat_tails(self, calculator):
        """Test kurtosis with fat tails."""
        # Create returns with extreme values (fat tails)
        returns = [Decimal(f"0.0{i}") for i in range(1, 9)]
        returns.extend([Decimal("-0.50"), Decimal("0.50")])

        kurt = calculator.calculate_kurtosis(returns)

        assert kurt is not None
        assert float(kurt) > 0  # Positive excess kurtosis (fat tails)

    def test_kurtosis_insufficient_data(self, calculator):
        """Test kurtosis with insufficient data."""
        kurt = calculator.calculate_kurtosis([Decimal("0.01"), Decimal("0.02"), Decimal("0.03")])

        assert kurt is None


class TestValueAtRisk:
    """Test Value at Risk (VaR) calculation."""

    def test_var_historical(self, calculator, sample_returns):
        """Test VaR with historical method."""
        var = calculator.calculate_var(sample_returns, confidence=0.95)

        assert var is not None
        assert float(var) < 0  # VaR should be negative (loss)

    def test_var_extreme_loss(self, calculator):
        """Test VaR detects extreme loss."""
        returns = [Decimal("0.01") for _ in range(95)] + [Decimal("-0.20") for _ in range(5)]

        var_95 = calculator.calculate_var(returns, confidence=0.95)

        assert var_95 is not None
        # VaR at 95% confidence should include the worst 5% of returns
        assert float(var_95) < float(Decimal("0.01"))  # Should reflect extreme loss in tail

    def test_var_insufficient_data(self, calculator):
        """Test VaR with insufficient data."""
        var = calculator.calculate_var([Decimal("0.01")])

        assert var is None


class TestConditionalValueAtRisk:
    """Test Conditional Value at Risk (CVaR) / Expected Shortfall."""

    def test_cvar_worse_than_var(self, calculator, sample_returns):
        """Test CVaR is worse than or equal to VaR."""
        var = calculator.calculate_var(sample_returns, confidence=0.95)
        cvar = calculator.calculate_cvar(sample_returns, confidence=0.95)

        assert var is not None
        assert cvar is not None
        # CVaR should be <= VaR (worse or equal)
        assert float(cvar) <= float(var)

    def test_cvar_tail_averaging(self, calculator):
        """Test CVaR averages tail returns."""
        # Create returns with known tail
        returns = [Decimal("0.01") for _ in range(90)] + [
            Decimal(f"-0.{i:02d}") for i in range(1, 11)
        ]

        cvar = calculator.calculate_cvar(returns, confidence=0.95)

        assert cvar is not None
        assert float(cvar) < -0.01  # Should reflect tail average


class TestCalculateAllAdvancedMetrics:
    """Test calculate_all_advanced_metrics method."""

    def test_all_metrics_returned(self, calculator, sample_returns, sample_equity_curve):
        """Test all metrics are returned."""
        metrics = calculator.calculate_all_advanced_metrics(
            returns=sample_returns,
            equity_curve=sample_equity_curve,
            cagr=Decimal("0.15"),
            max_drawdown=Decimal("-0.08"),
            total_pnl=Decimal("15000"),
            gross_profit=Decimal("20000"),
            gross_loss=Decimal("-5000"),
        )

        assert isinstance(metrics, dict)
        assert "calmar_ratio" in metrics
        assert "omega_ratio" in metrics
        assert "ulcer_index" in metrics
        assert "volatility_annualized" in metrics
        assert "recovery_factor" in metrics
        assert "profit_factor" in metrics
        assert "skewness" in metrics
        assert "kurtosis" in metrics
        assert "var_95" in metrics
        assert "cvar_95" in metrics
        assert len(metrics) == 10

    def test_all_metrics_with_valid_data(self, calculator, sample_returns, sample_equity_curve):
        """Test all metrics with realistic data."""
        metrics = calculator.calculate_all_advanced_metrics(
            returns=sample_returns,
            equity_curve=sample_equity_curve,
            cagr=Decimal("0.20"),
            max_drawdown=Decimal("-0.10"),
            total_pnl=Decimal("20000"),
            gross_profit=Decimal("25000"),
            gross_loss=Decimal("-5000"),
        )

        # Verify all metrics are properly formatted
        for key, value in metrics.items():
            if value is not None:
                assert isinstance(value, Decimal)
            assert value is None or isinstance(value, Decimal)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_returns_list(self, calculator):
        """Test with empty returns list."""
        metrics = calculator.calculate_all_advanced_metrics(
            returns=[],
            equity_curve=[Decimal("100000")],
            cagr=Decimal("0"),
            max_drawdown=Decimal("0"),
            total_pnl=Decimal("0"),
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
        )

        # Should not raise error, all metrics should be None
        assert metrics is not None

    def test_single_trade(self, calculator):
        """Test with single trade (minimal data)."""
        returns = [Decimal("0.01")]
        [Decimal("100000"), Decimal("101000")]

        # Most metrics should return None or handle gracefully
        skew = calculator.calculate_skewness(returns)
        assert skew is None

    def test_very_large_numbers(self, calculator):
        """Test with very large portfolio values."""
        returns = [Decimal("0.01"), Decimal("0.02")]
        [Decimal("1000000000"), Decimal("1010000000")]

        vol = calculator.calculate_annualized_volatility(returns)
        assert vol is not None

    def test_very_small_numbers(self, calculator):
        """Test with very small returns."""
        returns = [Decimal("0.00001"), Decimal("0.00002")]

        vol = calculator.calculate_annualized_volatility(returns)
        assert vol is not None
        assert float(vol) > 0


class TestMetricsIntegration:
    """Integration tests for multiple metrics."""

    def test_profitable_strategy_metrics(self, calculator):
        """Test metrics for a profitable strategy."""
        returns = [Decimal("0.01"), Decimal("0.02"), Decimal("0.015")] * 10
        equity = [Decimal(f"{100000 + i * 500}") for i in range(31)]

        metrics = calculator.calculate_all_advanced_metrics(
            returns=returns,
            equity_curve=equity,
            cagr=Decimal("0.25"),
            max_drawdown=Decimal("-0.03"),
            total_pnl=Decimal("25000"),
            gross_profit=Decimal("30000"),
            gross_loss=Decimal("-5000"),
        )

        # Profitable strategy should have:
        assert float(metrics["calmar_ratio"]) > 1.0
        assert float(metrics["recovery_factor"]) > 1.0
        assert float(metrics["profit_factor"]) > 1.0
        assert float(metrics["omega_ratio"]) > 1.0

    def test_losing_strategy_metrics(self, calculator):
        """Test metrics for a losing strategy."""
        returns = [Decimal("-0.01"), Decimal("-0.02"), Decimal("-0.015")] * 10
        equity = [Decimal(f"{100000 - i * 500}") for i in range(31)]

        metrics = calculator.calculate_all_advanced_metrics(
            returns=returns,
            equity_curve=equity,
            cagr=Decimal("-0.25"),
            max_drawdown=Decimal("-0.30"),
            total_pnl=Decimal("-25000"),
            gross_profit=Decimal("5000"),
            gross_loss=Decimal("-30000"),
        )

        # Losing strategy should have:
        assert metrics["calmar_ratio"] is None or float(metrics["calmar_ratio"]) < 0
        assert float(metrics["profit_factor"]) < 1.0
