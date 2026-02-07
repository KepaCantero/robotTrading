"""
Unit tests for Hierarchical Risk Parity (HRP) optimizer.

Tests cover:
1. HRP weight calculation
2. Linkage methods (single, average, complete, ward)
3. Quasi-diagonalization
4. Recursive bisection
5. Edge cases and error handling
6. Dendrogram generation
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.cluster.hierarchy import linkage

from app.engines.portfolio_engine.optimizers.hierarchical_risk_parity import (
    HierarchicalRiskParity,
    HRPOptimizer,
    compute_hrp_weights,
)


class TestHierarchicalRiskParity:
    """Test suite for HierarchicalRiskParity class."""

    @pytest.fixture
    def sample_covariance(self):
        """Create a sample covariance matrix."""
        # 4 assets with different correlations
        np.random.seed(42)
        n_assets = 4

        # Create correlated assets
        returns = np.random.randn(100, n_assets) * 0.01
        # Add correlation between assets 0 and 1
        returns[:, 1] = 0.8 * returns[:, 0] + 0.2 * np.random.randn(100) * 0.01
        # Add correlation between assets 2 and 3
        returns[:, 3] = 0.7 * returns[:, 2] + 0.3 * np.random.randn(100) * 0.01

        cov_matrix = np.cov(returns.T)
        return cov_matrix

    @pytest.fixture
    def sample_returns(self, sample_covariance):
        """Create sample expected returns."""
        return np.array([0.08, 0.10, 0.12, 0.09])

    def test_initialization(self):
        """Test HRP initialization."""
        # Valid linkage methods
        for method in ["single", "average", "complete", "ward"]:
            hrp = HierarchicalRiskParity(linkage_method=method)
            assert hrp.linkage_method == method
            assert hrp.distance_metric == "euclidean"

        # Invalid linkage method
        with pytest.raises(ValueError, match="linkage_method must be one of"):
            HierarchicalRiskParity(linkage_method="invalid")

    def test_get_weights_basic(self, sample_covariance):
        """Test basic weight calculation."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(sample_covariance)

        # Check weights properties
        assert len(weights) == 4
        assert np.all(weights >= 0), "Weights should be non-negative"
        assert np.allclose(weights.sum(), 1.0, atol=1e-4), "Weights should sum to 1"

    def test_get_weights_all_linkage_methods(self, sample_covariance):
        """Test all linkage methods produce valid weights."""
        for method in ["single", "average", "complete", "ward"]:
            hrp = HierarchicalRiskParity(linkage_method=method)
            weights = hrp.get_weights(sample_covariance)

            assert len(weights) == 4, f"{method}: wrong number of weights"
            assert np.all(weights >= 0), f"{method}: negative weights"
            assert np.allclose(weights.sum(), 1.0, atol=1e-4), f"{method}: weights don't sum to 1"

    def test_two_asset_case(self):
        """Test HRP with only 2 assets."""
        # Simple 2x2 covariance matrix
        cov = np.array([[0.01, 0.005], [0.005, 0.02]])

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        assert len(weights) == 2
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)
        # Asset 1 has higher variance (0.02 vs 0.01), should get lower weight
        assert weights[1] < weights[0], "Higher variance asset should get lower weight"

    def test_single_asset_case(self):
        """Test HRP with only 1 asset (edge case)."""
        cov = np.array([[0.01]])

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        assert len(weights) == 1
        assert np.allclose(weights[0], 1.0), "Single asset should get 100% weight"

    def test_identical_assets(self):
        """Test HRP when all assets are identical."""
        # All assets have same variance and correlation
        n = 5
        cov = np.ones((n, n)) * 0.01
        np.fill_diagonal(cov, 0.01)

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        # With identical assets, HRP creates hierarchical weights
        # (not equal, due to the recursive bisection structure)
        assert len(weights) == 5
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)
        # All weights should be positive
        assert np.all(weights > 0), "Should allocate positively to identical assets"

    def test_uncorrelated_assets(self):
        """Test HRP with uncorrelated assets."""
        # Diagonal covariance (no correlation)
        cov = np.diag([0.01, 0.02, 0.03, 0.04])

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        # Lower variance assets should get higher weights
        assert len(weights) == 4
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)

        # Check inverse variance relationship
        inv_var = 1.0 / np.diag(cov)
        expected = inv_var / inv_var.sum()

        # HRP should be close to inverse variance for uncorrelated assets
        # But may differ slightly due to hierarchical structure
        correlation = np.corrcoef(weights, expected)[0, 1]
        assert (
            correlation > 0.9
        ), "Should be correlated with inverse variance for uncorrelated assets"

    def test_perfectly_correlated_assets(self):
        """Test HRP with perfectly correlated assets."""
        n = 3
        # Perfect correlation: all covariances equal
        cov = np.ones((n, n)) * 0.01
        np.fill_diagonal(cov, 0.01)

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        # Perfectly correlated assets should get positive weights
        # (HRP creates hierarchical structure, not necessarily equal)
        assert len(weights) == 3
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)
        assert np.all(weights > 0), "Should allocate positively to perfectly correlated assets"

    def test_negative_correlation(self):
        """Test HRP with negative correlations."""
        # Assets with negative correlation
        cov = np.array([[0.01, -0.005], [-0.005, 0.01]])

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov)

        assert len(weights) == 2
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)
        assert np.all(weights >= 0), "Should handle negative correlation with positive weights"

    def test_cov_to_corr(self, sample_covariance):
        """Test covariance to correlation conversion."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        corr = hrp._cov_to_corr(sample_covariance)

        # Check diagonal is 1
        assert np.allclose(np.diag(corr), 1.0)

        # Check symmetry
        assert np.allclose(corr, corr.T)

        # Check values are in valid range
        assert np.all(corr >= -1.0) and np.all(corr <= 1.0)

    def test_correlation_to_distance(self, sample_covariance):
        """Test correlation to distance conversion."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        corr = hrp._cov_to_corr(sample_covariance)
        distance = hrp._correlation_to_distance(corr)

        # Check diagonal is 0
        assert np.allclose(np.diag(distance), 0.0)

        # Check symmetry
        assert np.allclose(distance, distance.T)

        # Check non-negative
        assert np.all(distance >= 0.0)

    def test_quasi_diagonalization(self, sample_covariance):
        """Test quasi-diagonalization produces valid ordering."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        corr = hrp._cov_to_corr(sample_covariance)
        linkage_matrix = linkage(corr)

        ordered_indices = hrp._quasi_diagonalization(corr, linkage_matrix)

        # Check ordering
        assert len(ordered_indices) == len(sample_covariance)
        assert set(ordered_indices) == set(range(len(sample_covariance)))

    def test_recursive_bisection(self, sample_covariance):
        """Test recursive bisection allocation."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        corr = hrp._cov_to_corr(sample_covariance)
        linkage_matrix = linkage(corr)

        weights = hrp._recursive_bisection(
            sample_covariance, linkage_matrix, list(range(len(sample_covariance)))
        )

        # Check weights are non-negative
        assert np.all(weights >= 0)

        # Check weights sum to something (will be normalized later)
        assert weights.sum() > 0

    def test_get_metrics(self, sample_covariance):
        """Test metrics calculation."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(sample_covariance)
        metrics = hrp.get_metrics(weights, sample_covariance)

        # Check required metrics
        assert "portfolio_variance" in metrics
        assert "portfolio_volatility" in metrics
        assert "effective_n_assets" in metrics
        assert "max_weight" in metrics
        assert "cophenet_correlation" in metrics

        # Check values are reasonable
        assert metrics["portfolio_variance"] >= 0
        assert metrics["portfolio_volatility"] >= 0
        assert metrics["effective_n_assets"] >= 1
        assert metrics["effective_n_assets"] <= len(weights)
        assert 0 < metrics["max_weight"] <= 1
        assert 0 <= metrics["cophenet_correlation"] <= 1

    def test_cluster_tree(self, sample_covariance):
        """Test cluster tree generation."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        hrp.get_weights(sample_covariance)
        tree = hrp.get_cluster_tree()

        assert tree is not None
        assert "linkage" in tree
        assert "ordered_indices" in tree
        assert "n_assets" in tree

    def test_dendrogram_data(self, sample_covariance):
        """Test dendrogram data generation."""
        hrp = HierarchicalRiskParity(linkage_method="single")
        hrp.get_weights(sample_covariance)
        dendro_data = hrp.get_dendrogram_data()

        assert dendro_data is not None
        assert "linkage_matrix" in dendro_data
        assert "cophenet_correlation" in dendro_data
        assert "ordered_indices" in dendro_data

    def test_invalid_input_empty_matrix(self):
        """Test with empty covariance matrix."""
        hrp = HierarchicalRiskParity(linkage_method="single")

        # Empty 1D array - should fail dimensionality check
        with pytest.raises(ValueError, match="must be 2-dimensional"):
            hrp.get_weights(np.array([]))

        # Empty 2D array - should fail empty check
        with pytest.raises(ValueError, match="cannot be empty"):
            hrp.get_weights(np.array([[]]))

    def test_invalid_input_not_square(self):
        """Test with non-square covariance matrix."""
        hrp = HierarchicalRiskParity(linkage_method="single")

        with pytest.raises(ValueError, match="must be square"):
            hrp.get_weights(np.array([[1, 2, 3], [4, 5, 6]]))

    def test_invalid_input_wrong_dimensions(self):
        """Test with wrong dimensions."""
        hrp = HierarchicalRiskParity(linkage_method="single")

        with pytest.raises(ValueError, match="must be 2-dimensional"):
            hrp.get_weights(np.array([1, 2, 3]))

    def test_invalid_input_type(self):
        """Test with wrong input type."""
        hrp = HierarchicalRiskParity(linkage_method="single")

        with pytest.raises(ValueError, match="must be a numpy array"):
            hrp.get_weights([[1, 0], [0, 1]])


class TestHRPOptimizer:
    """Test suite for HRPOptimizer wrapper class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample covariance and returns."""
        np.random.seed(42)
        returns = np.random.randn(100, 4) * 0.01
        cov_matrix = np.cov(returns.T)
        expected_returns = np.array([0.08, 0.10, 0.12, 0.09])

        return expected_returns, cov_matrix

    def test_optimize_basic(self, sample_data):
        """Test basic optimization."""
        expected_returns, cov_matrix = sample_data

        optimizer = HRPOptimizer(config={"linkage_method": "single"})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check result structure
        assert "weights" in result
        assert "expected_return" in result
        assert "volatility" in result
        assert "method" in result

        # Check weights
        assert len(result["weights"]) == 4
        assert np.allclose(sum(result["weights"].values()), 1.0, atol=1e-4)
        assert all(w >= 0 for w in result["weights"].values())

        # Check method
        assert result["method"] == "hrp"

    def test_optimize_with_constraints(self, sample_data):
        """Test optimization with weight constraints."""
        expected_returns, cov_matrix = sample_data

        optimizer = HRPOptimizer(config={"linkage_method": "average"})
        result = optimizer.optimize(
            expected_returns,
            cov_matrix,
            constraints={"max_weight": 0.5, "min_weight": 0.1},
        )

        # Check constraints are respected
        weights = np.array(list(result["weights"].values()))
        assert np.all(weights <= 0.51), "Max weight constraint violated"
        assert np.all(weights >= 0.09), "Min weight constraint violated"

    def test_optimize_all_linkage_methods(self, sample_data):
        """Test all linkage methods."""
        expected_returns, cov_matrix = sample_data

        for method in ["single", "average", "complete", "ward"]:
            optimizer = HRPOptimizer(config={"linkage_method": method})
            result = optimizer.optimize(expected_returns, cov_matrix)

            assert result["method"] == "hrp"
            assert result["linkage_method"] == method
            assert len(result["weights"]) == 4

    def test_effective_n_assets(self, sample_data):
        """Test effective number of assets metric."""
        expected_returns, cov_matrix = sample_data

        optimizer = HRPOptimizer(config={"linkage_method": "single"})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Effective N should be between 1 and total number of assets
        assert "effective_n_assets" in result
        assert 1 <= result["effective_n_assets"] <= 4

        # Effective N should decrease with concentration
        weights = np.array(list(result["weights"].values()))
        herfindahl = np.sum(weights**2)
        expected_eff_n = 1 / herfindahl
        assert np.allclose(result["effective_n_assets"], expected_eff_n, rtol=1e-4)

    def test_equal_weight_fallback(self):
        """Test that HRP handles non-symmetric matrices by normalizing them."""
        optimizer = HRPOptimizer(config={"linkage_method": "single"})

        # Non-symmetric matrix gets normalized, no error
        result = optimizer.optimize(
            np.array([0.1, 0.2]), np.array([[1, 2], [3, 4]])  # Not symmetric - will be normalized
        )

        # Should return HRP weights (normalized version works)
        assert result["method"] == "hrp"
        assert len(result["weights"]) == 2
        assert np.allclose(sum(result["weights"].values()), 1.0, atol=1e-4)


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @pytest.fixture
    def sample_covariance(self):
        """Create sample covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(100, 4) * 0.01
        return np.cov(returns.T)

    def test_compute_hrp_weights(self, sample_covariance):
        """Test compute_hrp_weights convenience function."""
        weights = compute_hrp_weights(sample_covariance, linkage_method="single")

        assert len(weights) == 4
        assert np.all(weights >= 0)
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)

    def test_compute_hrp_weights_all_methods(self, sample_covariance):
        """Test compute_hrp_weights with all linkage methods."""
        for method in ["single", "average", "complete", "ward"]:
            weights = compute_hrp_weights(sample_covariance, linkage_method=method)

            assert len(weights) == 4
            assert np.all(weights >= 0)
            assert np.allclose(weights.sum(), 1.0, atol=1e-4)

    def test_compute_hrp_weights_two_assets(self):
        """Test with 2 assets."""
        cov = np.array([[0.01, 0.005], [0.005, 0.02]])
        weights = compute_hrp_weights(cov, linkage_method="single")

        assert len(weights) == 2
        assert np.allclose(weights.sum(), 1.0, atol=1e-4)


class TestHRPProperties:
    """Test specific properties and guarantees of HRP."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        np.random.seed(42)
        returns = np.random.randn(252, 10) * 0.01  # 1 year of daily returns for 10 assets
        cov_matrix = np.cov(returns.T)
        expected_returns = np.random.randn(10) * 0.01

        return expected_returns, cov_matrix

    def test_no_negative_weights(self, sample_data):
        """Test that HRP never produces negative weights."""
        expected_returns, cov_matrix = sample_data

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov_matrix)

        assert np.all(weights >= -1e-10), "HRP should not produce negative weights"

    def test_weights_sum_to_one(self, sample_data):
        """Test that weights always sum to 1."""
        expected_returns, cov_matrix = sample_data

        for method in ["single", "average", "complete", "ward"]:
            hrp = HierarchicalRiskParity(linkage_method=method)
            weights = hrp.get_weights(cov_matrix)

            assert np.allclose(weights.sum(), 1.0, atol=1e-4), f"{method}: weights don't sum to 1"

    def test_diversification(self, sample_data):
        """Test that HRP produces diversified portfolios."""
        expected_returns, cov_matrix = sample_data

        hrp = HierarchicalRiskParity(linkage_method="single")
        weights = hrp.get_weights(cov_matrix)

        # Should not be extremely concentrated
        max_weight = weights.max()
        assert max_weight < 0.8, "HRP should not produce extremely concentrated portfolios"

        # Effective N should be reasonable
        effective_n = 1 / np.sum(weights**2)
        assert effective_n >= 2, "Should have at least 2 effective assets"

    def test_stability_across_methods(self, sample_data):
        """Test that different linkage methods give similar results."""
        expected_returns, cov_matrix = sample_data

        weights_list = []
        for method in ["single", "average", "complete", "ward"]:
            hrp = HierarchicalRiskParity(linkage_method=method)
            weights = hrp.get_weights(cov_matrix)
            weights_list.append(weights)

        # All methods should produce valid weights
        for weights in weights_list:
            assert np.all(weights >= 0)
            assert np.allclose(weights.sum(), 1.0, atol=1e-4)

        # Methods should be somewhat correlated (all based on same hierarchy)
        # but may differ significantly
        correlations = []
        for i in range(len(weights_list)):
            for j in range(i + 1, len(weights_list)):
                corr = np.corrcoef(weights_list[i], weights_list[j])[0, 1]
                correlations.append(corr)

        # At least some methods should be correlated
        assert max(correlations) > 0.5, "Linkage methods should have some similarity"

    def test_cophenetic_correlation_reasonable(self, sample_data):
        """Test that cophenetic correlation is reasonable."""
        expected_returns, cov_matrix = sample_data

        for method in ["single", "average", "complete", "ward"]:
            hrp = HierarchicalRiskParity(linkage_method=method)
            hrp.get_weights(cov_matrix)

            # Cophenetic correlation measures how well the dendrogram preserves distances
            # Higher is generally better, but varies by linkage method
            coph_corr = hrp.cophenet_correlation_

            assert coph_corr is not None
            assert 0 <= coph_corr <= 1, "Cophenetic correlation should be in [0, 1]"

            # Ward and average typically have higher cophenetic correlation
            if method in ["ward", "average"]:
                assert coph_corr > 0.5, f"{method} should have reasonable cophenetic correlation"
