"""
Tests for Ernest Chan Portfolio Optimization Implementation
"""

import pytest

# Check if cvxpy is available
cvxpy = pytest.importorskip("cvxpy", reason="cvxpy not installed, skipping optimization tests")

import numpy as np
import pandas as pd
from app.services.optimization_chan import (
    MeanVarianceOptimizer,
    RiskParityOptimizer,
    HierarchicalRiskParityOptimizer,
    MaximumDiversificationOptimizer,
    CVaROptimizer,
    optimize_portfolio,
)


class TestMeanVarianceOptimizer:
    """Test Mean-Variance optimizer."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test optimizer initialization."""
        optimizer = MeanVarianceOptimizer()
        assert optimizer.last_result is None

    def test_maximize_sharpe(self, sample_returns):
        """Test maximizing Sharpe ratio."""
        optimizer = MeanVarianceOptimizer()

        result = optimizer.optimize(sample_returns, objective='max_sharpe')

        assert result.method == "mean_variance_max_sharpe"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)
        assert all(result.weights >= 0)
        assert result.expected_return is not None
        assert result.volatility > 0

    def test_minimize_variance(self, sample_returns):
        """Test minimizing variance."""
        optimizer = MeanVarianceOptimizer()

        result = optimizer.optimize(sample_returns, objective='min_variance')

        assert result.method == "mean_variance_min_variance"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_maximize_diversification(self, sample_returns):
        """Test maximizing diversification."""
        optimizer = MeanVarianceOptimizer()

        result = optimizer.optimize(sample_returns, objective='max_diversification')

        assert result.method == "mean_variance_max_diversification"
        assert result.diversification_ratio is not None
        assert result.diversification_ratio >= 0

    def test_with_weight_constraints(self, sample_returns):
        """Test with weight constraints."""
        optimizer = MeanVarianceOptimizer()

        result = optimizer.optimize(
            sample_returns,
            objective='max_sharpe',
            weight_constraints={
                'min_weight': 0.05,
                'max_weight': 0.40,
                'max_positions': 5,
            }
        )

        assert all(result.weights >= 0.05 - 1e-4)
        assert all(result.weights <= 0.40 + 1e-4)
        assert np.sum(result.weights > 0.01) <= 6  # Allow some rounding


class TestRiskParityOptimizer:
    """Test Risk Parity optimizer."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test optimizer initialization."""
        optimizer = RiskParityOptimizer()
        assert optimizer.last_result is None

    def test_risk_parity_optimization(self, sample_returns):
        """Test risk parity optimization."""
        optimizer = RiskParityOptimizer()

        result = optimizer.optimize(sample_returns)

        assert result.method == "risk_parity"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)
        assert result.risk_contributions is not None

        # Verify risk contributions are approximately equal
        risk_contribs = result.risk_contributions
        normalized_contribs = risk_contribs / risk_contribs.sum()

        # Standard deviation of contributions should be low
        assert np.std(normalized_contribs) < 0.15  # Within 15%

    def test_risk_parity_with_constraints(self, sample_returns):
        """Test risk parity with weight constraints."""
        optimizer = RiskParityOptimizer()

        result = optimizer.optimize(
            sample_returns,
            weight_constraints={
                'min_weight': 0.05,
                'max_weight': 0.50,
            }
        )

        assert all(result.weights >= 0.05 - 1e-4)
        assert all(result.weights <= 0.50 + 1e-4)


class TestHierarchicalRiskParityOptimizer:
    """Test HRP optimizer."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test HRP initialization."""
        optimizer = HierarchicalRiskParityOptimizer()
        assert optimizer.last_result is None
        assert optimizer.linkage_matrix is None

    def test_hrp_optimization(self, sample_returns):
        """Test HRP optimization."""
        optimizer = HierarchicalRiskParityOptimizer()

        result = optimizer.optimize(sample_returns, method='ward')

        assert result.method == "hierarchical_risk_parity"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)
        assert optimizer.linkage_matrix is not None

    def test_hrp_different_methods(self, sample_returns):
        """Test HRP with different linkage methods."""
        methods = ['single', 'complete', 'average', 'ward']

        for method in methods:
            optimizer = HierarchicalRiskParityOptimizer()
            result = optimizer.optimize(sample_returns, method=method)

            assert result.method == "hierarchical_risk_parity"
            assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)


class TestMaximumDiversificationOptimizer:
    """Test Maximum Diversification optimizer."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test optimizer initialization."""
        optimizer = MaximumDiversificationOptimizer()
        assert optimizer.last_result is None

    def test_maximum_diversification(self, sample_returns):
        """Test maximum diversification optimization."""
        optimizer = MaximumDiversificationOptimizer()

        result = optimizer.optimize(sample_returns)

        assert result.method == "maximum_diversification"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)
        assert result.diversification_ratio is not None
        assert result.diversification_ratio >= 0


class TestCVaROptimizer:
    """Test CVaR optimizer."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test CVaR optimizer initialization."""
        optimizer = CVaROptimizer(confidence_level=0.95)
        assert optimizer.confidence_level == 0.95
        assert optimizer.last_result is None

    def test_cvar_optimization(self, sample_returns):
        """Test CVaR optimization."""
        optimizer = CVaROptimizer(confidence_level=0.95)

        result = optimizer.optimize(sample_returns)

        assert result.method == "cvar_optimization"
        assert len(result.weights) == sample_returns.shape[1]
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)
        assert result.metadata is not None
        assert 'cvar' in result.metadata
        assert 'var' in result.metadata

    def test_cvar_different_confidence_levels(self, sample_returns):
        """Test CVaR with different confidence levels."""
        for confidence in [0.90, 0.95, 0.99]:
            optimizer = CVaROptimizer(confidence_level=confidence)
            result = optimizer.optimize(sample_returns)

            assert result.method == "cvar_optimization"
            assert result.metadata['confidence_level'] == confidence


class TestHighLevelFunction:
    """Test high-level optimization function."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_optimize_portfolio_mean_variance(self, sample_returns):
        """Test high-level function with mean-variance."""
        result = optimize_portfolio(sample_returns, method='mean_variance')

        assert result.method.startswith("mean_variance")
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_optimize_portfolio_risk_parity(self, sample_returns):
        """Test high-level function with risk parity."""
        result = optimize_portfolio(sample_returns, method='risk_parity')

        assert result.method == "risk_parity"
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_optimize_portfolio_hrp(self, sample_returns):
        """Test high-level function with HRP."""
        result = optimize_portfolio(sample_returns, method='hrp')

        assert result.method == "hierarchical_risk_parity"
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_optimize_portfolio_max_div(self, sample_returns):
        """Test high-level function with max diversification."""
        result = optimize_portfolio(sample_returns, method='max_div')

        assert result.method == "maximum_diversification"
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_optimize_portfolio_cvar(self, sample_returns):
        """Test high-level function with CVaR."""
        result = optimize_portfolio(sample_returns, method='cvar', confidence_level=0.95)

        assert result.method == "cvar_optimization"
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-4)

    def test_invalid_method(self, sample_returns):
        """Test with invalid optimization method."""
        with pytest.raises(ValueError):
            optimize_portfolio(sample_returns, method='invalid_method')
