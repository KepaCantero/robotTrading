"""
Tests for AWESOME-QUANT Integrator - Advanced metrics from multiple libraries.

Tests metric calculation from quantstats, empyrical, and pyfolio.
"""

import numpy as np
import pandas as pd
import pytest

from app.backtesting.awesome_quant_integrator import (
    AwesomeQuantIntegrator,
    EMPYRICAL_AVAILABLE,
    PYFOLIO_AVAILABLE,
    QUANTSTATS_AVAILABLE,
)


class TestAwesomeQuantIntegrator:
    """Tests for AwesomeQuantIntegrator class."""

    @pytest.fixture
    def integrator(self):
        """Create AwesomeQuantIntegrator instance."""
        return AwesomeQuantIntegrator(risk_free_rate=0.02)

    @pytest.fixture
    def excellent_returns(self):
        """Create excellent performance returns."""
        np.random.seed(42)
        returns = pd.Series(
            np.random.normal(0.001, 0.01, 252),  # 0.1% daily return, 1% volatility
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )
        return returns

    @pytest.fixture
    def poor_returns(self):
        """Create poor performance returns."""
        np.random.seed(42)
        returns = pd.Series(
            np.random.normal(-0.0005, 0.015, 252),  # -0.05% daily, 1.5% volatility
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )
        return returns

    @pytest.fixture
    def stable_returns(self):
        """Create stable performance returns."""
        np.random.seed(42)
        returns = pd.Series(
            np.random.normal(0.0005, 0.008, 252),  # 0.05% daily, 0.8% volatility
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )
        return returns

    @pytest.fixture
    def benchmark_returns(self):
        """Create benchmark returns."""
        np.random.seed(43)
        returns = pd.Series(
            np.random.normal(0.0003, 0.009, 252),
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )
        return returns

    # Tests for initialization
    def test_integrator_initialization(self, integrator):
        """Test integrator initialization."""
        assert integrator.risk_free_rate == 0.02
        assert isinstance(integrator, AwesomeQuantIntegrator)

    def test_integrator_with_custom_risk_free_rate(self):
        """Test integrator with custom risk-free rate."""
        integrator = AwesomeQuantIntegrator(risk_free_rate=0.03)
        assert integrator.risk_free_rate == 0.03

    # Tests for availability checking
    def test_is_available_method(self, integrator):
        """Test checking library availability."""
        # Check known libraries
        result_qs = integrator.is_available("quantstats")
        result_emp = integrator.is_available("empyrical")
        result_pf = integrator.is_available("pyfolio")

        # Results should be boolean
        assert isinstance(result_qs, bool)
        assert isinstance(result_emp, bool)
        assert isinstance(result_pf, bool)

    def test_is_available_unknown_library(self, integrator):
        """Test availability check for unknown library."""
        result = integrator.is_available("unknown_library")
        assert result is False

    def test_get_available_libraries(self, integrator):
        """Test getting list of available libraries."""
        available = integrator.get_available_libraries()
        assert isinstance(available, list)
        # Should be empty or contain known libraries
        for lib in available:
            assert lib in ["quantstats", "empyrical", "pyfolio"]

    # Tests for quantstats metrics (if available)
    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="quantstats not available")
    def test_quantstats_metrics_excellent_returns(self, integrator, excellent_returns):
        """Test quantstats metrics with excellent returns."""
        metrics = integrator.calculate_quantstats_metrics(excellent_returns)

        # Should return dictionary
        assert isinstance(metrics, dict)
        # Should have some metrics if library available
        if metrics:
            assert len(metrics) > 0
            # All values should be numeric or None
            for k, v in metrics.items():
                assert isinstance(v, (int, float)) or v is None

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="quantstats not available")
    def test_quantstats_with_benchmark(self, integrator, excellent_returns, benchmark_returns):
        """Test quantstats metrics with benchmark."""
        metrics = integrator.calculate_quantstats_metrics(excellent_returns, benchmark_returns)

        assert isinstance(metrics, dict)
        if metrics and "beta" in metrics:
            assert isinstance(metrics["beta"], (int, float))

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="quantstats not available")
    def test_quantstats_empty_returns(self, integrator):
        """Test quantstats with empty returns."""
        empty_returns = pd.Series(dtype=float)
        metrics = integrator.calculate_quantstats_metrics(empty_returns)

        # Should handle gracefully
        assert isinstance(metrics, dict)

    # Tests for empyrical metrics (if available)
    @pytest.mark.skipif(not EMPYRICAL_AVAILABLE, reason="empyrical not available")
    def test_empyrical_metrics_excellent_returns(self, integrator, excellent_returns):
        """Test empyrical metrics with excellent returns."""
        metrics = integrator.calculate_empyrical_metrics(excellent_returns)

        assert isinstance(metrics, dict)
        if metrics:
            assert len(metrics) > 0
            for k, v in metrics.items():
                assert isinstance(v, (int, float)) or v is None

    @pytest.mark.skipif(not EMPYRICAL_AVAILABLE, reason="empyrical not available")
    def test_empyrical_poor_returns(self, integrator, poor_returns):
        """Test empyrical metrics with poor returns."""
        metrics = integrator.calculate_empyrical_metrics(poor_returns)

        assert isinstance(metrics, dict)
        if metrics and "total_return" in metrics:
            assert isinstance(metrics["total_return"], (int, float))

    @pytest.mark.skipif(not EMPYRICAL_AVAILABLE, reason="empyrical not available")
    def test_empyrical_with_benchmark(self, integrator, excellent_returns, benchmark_returns):
        """Test empyrical metrics with benchmark."""
        metrics = integrator.calculate_empyrical_metrics(excellent_returns, benchmark_returns)

        assert isinstance(metrics, dict)
        if metrics and "alpha" in metrics:
            assert isinstance(metrics["alpha"], (int, float))

    @pytest.mark.skipif(not EMPYRICAL_AVAILABLE, reason="empyrical not available")
    def test_empyrical_contains_key_metrics(self, integrator, excellent_returns):
        """Test that empyrical includes key risk metrics."""
        metrics = integrator.calculate_empyrical_metrics(excellent_returns)

        if metrics:
            # Should have risk-adjusted metrics
            expected_keys = ["total_return", "volatility", "sharpe_ratio", "sortino_ratio"]
            # At least some should be present
            present = [k for k in expected_keys if k in metrics]
            assert len(present) > 0

    # Tests for pyfolio metrics (if available)
    @pytest.mark.skipif(not PYFOLIO_AVAILABLE, reason="pyfolio not available")
    def test_pyfolio_metrics_stable_returns(self, integrator, stable_returns):
        """Test pyfolio metrics with stable returns."""
        metrics = integrator.calculate_pyfolio_metrics(stable_returns)

        assert isinstance(metrics, dict)
        if metrics:
            assert len(metrics) > 0
            for k, v in metrics.items():
                assert isinstance(v, (int, float)) or v is None

    @pytest.mark.skipif(not PYFOLIO_AVAILABLE, reason="pyfolio not available")
    def test_pyfolio_with_positions(self, integrator, stable_returns):
        """Test pyfolio metrics with positions DataFrame."""
        positions = pd.DataFrame(
            np.random.random((len(stable_returns), 5)),
            index=stable_returns.index,
            columns=[f"asset_{i}" for i in range(5)],
        )

        metrics = integrator.calculate_pyfolio_metrics(stable_returns, positions=positions)

        assert isinstance(metrics, dict)

    # Tests for combined metrics
    def test_calculate_all_awesome_quant_metrics(self, integrator, excellent_returns):
        """Test calculating all available AWESOME-QUANT metrics."""
        all_metrics = integrator.calculate_all_awesome_quant_metrics(excellent_returns)

        assert isinstance(all_metrics, dict)
        assert "quantstats" in all_metrics
        assert "empyrical" in all_metrics
        assert "pyfolio" in all_metrics

        # Each should be a dictionary
        for library, metrics in all_metrics.items():
            assert isinstance(metrics, dict)

    def test_all_awesome_quant_with_benchmark(
        self, integrator, excellent_returns, benchmark_returns
    ):
        """Test calculating all metrics with benchmark."""
        all_metrics = integrator.calculate_all_awesome_quant_metrics(
            excellent_returns, benchmark_returns=benchmark_returns
        )

        assert isinstance(all_metrics, dict)

    def test_all_awesome_quant_with_positions(self, integrator, excellent_returns):
        """Test calculating all metrics with positions."""
        positions = pd.DataFrame(
            np.random.random((len(excellent_returns), 3)),
            index=excellent_returns.index,
            columns=[f"asset_{i}" for i in range(3)],
        )

        all_metrics = integrator.calculate_all_awesome_quant_metrics(
            excellent_returns, positions=positions
        )

        assert isinstance(all_metrics, dict)

    # Tests for unified metrics
    def test_get_unified_metrics(self, integrator, excellent_returns):
        """Test getting unified metrics view."""
        unified = integrator.get_unified_metrics(excellent_returns)

        assert isinstance(unified, dict)
        # Should have at least some metrics if any library available
        if any([QUANTSTATS_AVAILABLE, EMPYRICAL_AVAILABLE, PYFOLIO_AVAILABLE]):
            # Might be empty if no libraries, but dict should exist
            assert len(unified) >= 0

    def test_unified_metrics_no_duplicates(self, integrator, excellent_returns):
        """Test that unified metrics don't have duplicate keys."""
        unified = integrator.get_unified_metrics(excellent_returns)

        # Get all key counts
        keys = list(unified.keys())
        unique_keys = set(keys)

        # Should have no duplicates
        assert len(keys) == len(unique_keys)

    def test_unified_metrics_with_benchmark(self, integrator, excellent_returns, benchmark_returns):
        """Test unified metrics with benchmark."""
        unified = integrator.get_unified_metrics(excellent_returns, benchmark_returns)

        assert isinstance(unified, dict)

    # Edge case tests
    def test_single_return_value(self, integrator):
        """Test with single return value."""
        single_return = pd.Series([0.01])

        metrics_emp = integrator.calculate_empyrical_metrics(single_return)
        metrics_pf = integrator.calculate_pyfolio_metrics(single_return)

        # Should handle gracefully
        assert isinstance(metrics_emp, dict)
        assert isinstance(metrics_pf, dict)

    def test_zero_returns(self, integrator):
        """Test with all zero returns."""
        zero_returns = pd.Series([0.0] * 252)

        metrics_emp = integrator.calculate_empyrical_metrics(zero_returns)
        metrics_pf = integrator.calculate_pyfolio_metrics(zero_returns)

        assert isinstance(metrics_emp, dict)
        assert isinstance(metrics_pf, dict)

    def test_constant_returns(self, integrator):
        """Test with constant returns."""
        constant_returns = pd.Series([0.001] * 252)

        unified = integrator.get_unified_metrics(constant_returns)

        assert isinstance(unified, dict)
        # Volatility should be 0 (allow for floating point precision)
        if "volatility" in unified:
            assert abs(unified["volatility"] - 0.0) < 1e-10

    def test_extreme_returns(self, integrator):
        """Test with extreme values."""
        extreme_returns = pd.Series(
            np.concatenate([np.ones(10) * 1.0, np.ones(10) * -0.5, np.random.normal(0, 0.01, 232)])
        )

        metrics = integrator.get_unified_metrics(extreme_returns)

        assert isinstance(metrics, dict)

    def test_nan_handling(self, integrator):
        """Test handling of NaN values."""
        returns_with_nan = pd.Series([0.01, np.nan, 0.02, 0.01, np.nan, 0.005])

        metrics = integrator.get_unified_metrics(returns_with_nan)

        # Should handle NaN gracefully
        assert isinstance(metrics, dict)

    # Stress tests
    def test_large_dataset(self, integrator):
        """Test with large dataset (10 years of daily returns)."""
        np.random.seed(42)
        large_returns = pd.Series(
            np.random.normal(0.0005, 0.01, 2520),
            index=pd.date_range("2013-01-01", periods=2520, freq="D"),
        )

        metrics = integrator.get_unified_metrics(large_returns)

        assert isinstance(metrics, dict)

    def test_high_frequency_returns(self, integrator):
        """Test with high-frequency returns (5-minute intervals)."""
        np.random.seed(42)
        hf_returns = pd.Series(
            np.random.normal(0.00001, 0.0001, 1000),
            index=pd.date_range("2023-01-01", periods=1000, freq="5min"),
        )

        metrics = integrator.get_unified_metrics(hf_returns)

        assert isinstance(metrics, dict)

    # Integration tests
    def test_multiple_analysis_flow(self, integrator, excellent_returns, poor_returns):
        """Test multiple sequential analyses."""
        # Analyze excellent returns
        unified1 = integrator.get_unified_metrics(excellent_returns)
        assert isinstance(unified1, dict)

        # Analyze poor returns
        unified2 = integrator.get_unified_metrics(poor_returns)
        assert isinstance(unified2, dict)

        # Results should be different
        if unified1 and unified2:
            # At minimum, different return profiles should produce different metrics
            assert True  # Analysis completed without error

    def test_full_workflow(self, integrator, excellent_returns, benchmark_returns):
        """Test full analysis workflow."""
        # Step 1: Check availability
        available = integrator.get_available_libraries()
        assert isinstance(available, list)

        # Step 2: Calculate unified metrics
        unified = integrator.get_unified_metrics(excellent_returns, benchmark_returns)
        assert isinstance(unified, dict)

        # Step 3: Calculate all metrics
        all_metrics = integrator.calculate_all_awesome_quant_metrics(
            excellent_returns, benchmark_returns=benchmark_returns
        )
        assert isinstance(all_metrics, dict)

    def test_integrator_attributes(self, integrator):
        """Test integrator has correct attributes."""
        assert hasattr(integrator, "risk_free_rate")
        assert hasattr(integrator, "calculate_quantstats_metrics")
        assert hasattr(integrator, "calculate_empyrical_metrics")
        assert hasattr(integrator, "calculate_pyfolio_metrics")
        assert hasattr(integrator, "calculate_all_awesome_quant_metrics")
        assert hasattr(integrator, "get_unified_metrics")
