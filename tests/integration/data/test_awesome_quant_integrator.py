"""
Test suite for app.backtesting.awesome_quant_integrator

Addresses TST-005: Test coverage for AwesomeQuantIntegrator
"""

import numpy as np
import pandas as pd
import pytest

from app.backtesting.awesome_quant_integrator import (
    EMPYRICAL_AVAILABLE,
    QUANTSTATS_AVAILABLE,
    AwesomeQuantIntegrator,
)


class TestAwesomeQuantIntegratorImport:
    """Test module imports."""

    def test_import_awesome_quant_integrator(self):
        """Test that AwesomeQuantIntegrator can be imported."""
        from app.backtesting.awesome_quant_integrator import AwesomeQuantIntegrator

        assert AwesomeQuantIntegrator is not None

    def test_import_typed_dicts(self):
        """Test that TypedDict classes can be imported."""
        from app.backtesting.awesome_quant_integrator import (
            EmpyricalMetrics,
            PyfolioMetrics,
            QuantstatsMetrics,
        )

        assert QuantstatsMetrics is not None
        assert EmpyricalMetrics is not None
        assert PyfolioMetrics is not None

    def test_import_constants(self):
        """Test that constants are available."""
        from app.backtesting.awesome_quant_integrator import TRADING_DAYS

        assert TRADING_DAYS == 252


class TestAwesomeQuantIntegratorInitialization:
    """Test AwesomeQuantIntegrator initialization."""

    def test_default_initialization(self):
        """Test initialization with default risk-free rate."""
        integrator = AwesomeQuantIntegrator()
        assert integrator.risk_free_rate == 0.02

    def test_custom_risk_free_rate(self):
        """Test initialization with custom risk-free rate."""
        integrator = AwesomeQuantIntegrator(risk_free_rate=0.03)
        assert integrator.risk_free_rate == 0.03

    def test_check_availability(self):
        """Test availability check logs."""
        integrator = AwesomeQuantIntegrator()
        # Just ensure it doesn't raise
        integrator._check_availability()


class TestLibraryAvailability:
    """Test library availability flags."""

    def test_quantstats_availability_flag(self):
        """Test QUANTSTATS_AVAILABLE flag exists."""
        from app.backtesting.awesome_quant_integrator import QUANTSTATS_AVAILABLE

        assert isinstance(QUANTSTATS_AVAILABLE, bool)

    def test_empyrical_availability_flag(self):
        """Test EMPYRICAL_AVAILABLE flag exists."""
        from app.backtesting.awesome_quant_integrator import EMPYRICAL_AVAILABLE

        assert isinstance(EMPYRICAL_AVAILABLE, bool)

    def test_pyfolio_availability_flag(self):
        """Test PYFOLIO_AVAILABLE flag exists."""
        from app.backtesting.awesome_quant_integrator import PYFOLIO_AVAILABLE

        assert isinstance(PYFOLIO_AVAILABLE, bool)


class TestFallbackMetrics:
    """Test fallback metrics calculation."""

    def test_calculate_fallback_metrics(self):
        """Test fallback metrics calculation."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        metrics = integrator._calculate_fallback_metrics(returns)

        assert isinstance(metrics, dict)
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "volatility" in metrics

    def test_fallback_metrics_with_benchmark(self):
        """Test fallback metrics with benchmark."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()
        benchmark = self._generate_test_returns(mean=0.0001)

        metrics = integrator._calculate_fallback_metrics(returns, benchmark)

        assert "alpha" in metrics
        assert "beta" in metrics
        assert "information_ratio" in metrics

    def test_fallback_metrics_empty_returns(self):
        """Test fallback metrics with empty returns."""
        integrator = AwesomeQuantIntegrator()
        returns = pd.Series([])

        metrics = integrator._calculate_fallback_metrics(returns)

        assert isinstance(metrics, dict)

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)


class TestQuantstatsMetrics:
    """Test quantstats metrics calculation (if available)."""

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="quantstats not available")
    def test_calculate_quantstats_metrics(self):
        """Test quantstats metrics calculation."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        metrics = integrator.calculate_quantstats_metrics(returns)

        assert isinstance(metrics, dict)
        assert "sharpe" in metrics

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="quantstats not available")
    def test_calculate_quantstats_metrics_with_benchmark(self):
        """Test quantstats with benchmark."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()
        benchmark = self._generate_test_returns(mean=0.0003)

        metrics = integrator.calculate_quantstats_metrics(returns, benchmark)

        assert "beta" in metrics
        assert "alpha" in metrics

    def test_calculate_quantstats_metrics_fallback(self):
        """Test quantstats uses fallback when unavailable."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        # If quantstats is not available, should use fallback
        if not QUANTSTATS_AVAILABLE:
            metrics = integrator.calculate_quantstats_metrics(returns)
            assert isinstance(metrics, dict)

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)


class TestEmpyricalMetrics:
    """Test empyrical metrics calculation (if available)."""

    @pytest.mark.skipif(not EMPYRICAL_AVAILABLE, reason="empyrical not available")
    def test_calculate_empyrical_metrics(self):
        """Test empyrical metrics calculation."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        metrics = integrator.calculate_empyrical_metrics(returns)

        assert isinstance(metrics, dict)
        assert "sharpe_ratio" in metrics
        assert "total_return" in metrics

    def test_calculate_empyrical_metrics_fallback(self):
        """Test empyrical uses fallback when unavailable."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        # If empyrical is not available, should use fallback
        if not EMPYRICAL_AVAILABLE:
            metrics = integrator.calculate_empyrical_metrics(returns)
            assert isinstance(metrics, dict)

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)


class TestPyfolioMetrics:
    """Test pyfolio metrics calculation."""

    def test_calculate_pyfolio_metrics(self):
        """Test pyfolio metrics calculation."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        metrics = integrator.calculate_pyfolio_metrics(returns)

        assert isinstance(metrics, dict)
        assert "sharpe_ratio" in metrics
        assert "total_return" in metrics

    def test_calculate_pyfolio_metrics_with_positions(self):
        """Test pyfolio metrics with positions."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()
        positions = pd.DataFrame(
            {"AAPL": np.random.randn(252) * 1000}, index=pd.date_range("2024-01-01", periods=252)
        )

        metrics = integrator.calculate_pyfolio_metrics(returns, positions)

        assert isinstance(metrics, dict)

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)


class TestUnifiedMetrics:
    """Test unified metrics calculation."""

    def test_get_unified_metrics(self):
        """Test getting unified metrics."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        metrics = integrator.get_unified_metrics(returns)

        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_get_unified_metrics_with_benchmark(self):
        """Test unified metrics with benchmark."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()
        benchmark = self._generate_test_returns(mean=0.0003)

        metrics = integrator.get_unified_metrics(returns, benchmark)

        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)


class TestIsAvailable:
    """Test library availability checking."""

    def test_is_available_quantstats(self):
        """Test checking quantstats availability."""
        integrator = AwesomeQuantIntegrator()
        result = integrator.is_available("quantstats")
        assert isinstance(result, bool)

    def test_is_available_empyrical(self):
        """Test checking empyrical availability."""
        integrator = AwesomeQuantIntegrator()
        result = integrator.is_available("empyrical")
        assert isinstance(result, bool)

    def test_is_available_pyfolio(self):
        """Test checking pyfolio availability."""
        integrator = AwesomeQuantIntegrator()
        result = integrator.is_available("pyfolio")
        assert isinstance(result, bool)

    def test_is_available_invalid_library(self):
        """Test checking invalid library."""
        integrator = AwesomeQuantIntegrator()
        result = integrator.is_available("invalid")
        assert result is False


class TestGetAvailableLibraries:
    """Test getting available libraries list."""

    def test_get_available_libraries(self):
        """Test getting list of available libraries."""
        integrator = AwesomeQuantIntegrator()
        available = integrator.get_available_libraries()
        assert isinstance(available, list)
        assert all(isinstance(lib, str) for lib in available)


class TestCalculateAllMetrics:
    """Test calculating all available metrics."""

    def test_calculate_all_awesome_quant_metrics(self):
        """Test calculating all metrics."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()

        all_metrics = integrator.calculate_all_awesome_quant_metrics(returns)

        assert isinstance(all_metrics, dict)
        assert "quantstats" in all_metrics
        assert "empyrical" in all_metrics
        assert "pyfolio" in all_metrics

    def test_calculate_all_metrics_with_benchmark(self):
        """Test calculating all metrics with benchmark."""
        integrator = AwesomeQuantIntegrator()
        returns = self._generate_test_returns()
        benchmark = self._generate_test_returns(mean=0.0003)

        all_metrics = integrator.calculate_all_awesome_quant_metrics(
            returns, benchmark_returns=benchmark
        )

        assert isinstance(all_metrics, dict)

    def _generate_test_returns(self, mean=0.0005, std=0.01, n=252):
        """Generate test returns series with DatetimeIndex for quantstats compatibility."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=n, freq="B")
        return pd.Series(np.random.normal(mean, std, n), index=dates)
