"""
Unit tests for Nested Clustered Optimization (NCO).

Tests cover:
1. Configuration validation
2. Clustering methods (K-means, DBSCAN)
3. Within-cluster optimization
4. Cross-cluster allocation
5. Full NCO pipeline
6. Edge cases and error handling
"""

from __future__ import annotations

import pytest
import numpy as np

from app.domain.portfolio_optimization.nested_clustered_optimization import (
    NestedClusteredOptimization,
    NCOConfig,
    NCOResult,
    ClusteringMethod,
    compute_nco_weights,
)


@pytest.mark.unit
class TestNCOConfig:
    """Test NCOConfig validation and defaults."""

    def test_default_config(self):
        """Test default configuration values."""
        config = NCOConfig()

        assert config.n_clusters == 5
        assert config.clustering_method == ClusteringMethod.KMEANS
        assert config.dbscan_eps == 0.5
        assert config.min_samples == 2
        assert config.min_cluster_size == 2
        assert config.max_weight_single_asset == 0.20
        assert config.risk_free_rate == 0.02
        assert config.random_state == 42

    def test_custom_config(self):
        """Test custom configuration values."""
        config = NCOConfig(
            n_clusters=10,
            clustering_method=ClusteringMethod.DBSCAN,
            dbscan_eps=0.8,
            min_samples=3,
            min_cluster_size=3,
            max_weight_single_asset=0.15,
            risk_free_rate=0.03,
            random_state=123,
        )

        assert config.n_clusters == 10
        assert config.clustering_method == ClusteringMethod.DBSCAN
        assert config.dbscan_eps == 0.8
        assert config.min_samples == 3
        assert config.min_cluster_size == 3
        assert config.max_weight_single_asset == 0.15
        assert config.risk_free_rate == 0.03
        assert config.random_state == 123

    def test_invalid_n_clusters_raises_error(self):
        """Test that invalid n_clusters raises ValueError."""
        with pytest.raises(ValueError, match="n_clusters must be at least 2"):
            NCOConfig(n_clusters=1)

        with pytest.raises(ValueError, match="n_clusters must be at least 2"):
            NCOConfig(n_clusters=0)

    def test_invalid_dbscan_eps_raises_error(self):
        """Test that invalid dbscan_eps raises ValueError."""
        with pytest.raises(ValueError, match="dbscan_eps must be positive"):
            NCOConfig(dbscan_eps=0)

        with pytest.raises(ValueError, match="dbscan_eps must be positive"):
            NCOConfig(dbscan_eps=-0.1)

    def test_invalid_min_samples_raises_error(self):
        """Test that invalid min_samples raises ValueError."""
        with pytest.raises(ValueError, match="min_samples must be at least 1"):
            NCOConfig(min_samples=0)

    def test_invalid_max_weight_raises_error(self):
        """Test that invalid max_weight raises ValueError."""
        with pytest.raises(ValueError, match="max_weight_single_asset must be in \\(0, 1\\]"):
            NCOConfig(max_weight_single_asset=0)

        with pytest.raises(ValueError, match="max_weight_single_asset must be in \\(0, 1\\]"):
            NCOConfig(max_weight_single_asset=1.5)

    def test_config_is_frozen(self):
        """Test that config is immutable (frozen dataclass)."""
        config = NCOConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.n_clusters = 10


@pytest.mark.unit
class TestCorrelationToDistance:
    """Test correlation to distance matrix conversion."""

    def test_perfect_correlation_zero_distance(self):
        """Test that perfect correlation gives zero distance."""
        nco = NestedClusteredOptimization()
        corr = np.array([[1.0, 1.0], [1.0, 1.0]])
        distance = nco._correlation_to_distance(corr)

        expected = np.array([[0.0, 0.0], [0.0, 0.0]])
        np.testing.assert_array_almost_equal(distance, expected, decimal=10)

    def test_zero_correlation_distance(self):
        """Test that zero correlation gives expected distance."""
        nco = NestedClusteredOptimization()
        corr = np.array([[1.0, 0.0], [0.0, 1.0]])
        distance = nco._correlation_to_distance(corr)

        # d = sqrt(0.5 * (1 - 0)) = sqrt(0.5)
        expected = np.array([[0.0, np.sqrt(0.5)], [np.sqrt(0.5), 0.0]])
        np.testing.assert_array_almost_equal(distance, expected, decimal=10)

    def test_negative_correlation_max_distance(self):
        """Test that negative correlation gives maximum distance."""
        nco = NestedClusteredOptimization()
        corr = np.array([[1.0, -1.0], [-1.0, 1.0]])
        distance = nco._correlation_to_distance(corr)

        # d = sqrt(0.5 * (1 - (-1))) = sqrt(1) = 1
        expected = np.array([[0.0, 1.0], [1.0, 0.0]])
        np.testing.assert_array_almost_equal(distance, expected, decimal=10)

    def test_diagonal_is_zero(self):
        """Test that diagonal elements are always zero."""
        nco = NestedClusteredOptimization()
        corr = np.array([[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]])
        distance = nco._correlation_to_distance(corr)

        np.testing.assert_array_almost_equal(np.diag(distance), [0.0, 0.0, 0.0])

    def test_correlation_clipping(self):
        """Test that correlations are clipped to [-1, 1]."""
        nco = NestedClusteredOptimization()
        corr = np.array([[1.0, 1.5], [-1.5, 1.0]])  # Invalid correlations
        distance = nco._correlation_to_distance(corr)

        # Should be clipped to valid range
        assert distance[0, 1] >= 0
        assert distance[1, 0] >= 0


@pytest.mark.unit
class TestCovarianceToCorrelation:
    """Test covariance to correlation matrix conversion."""

    def test_basic_conversion(self):
        """Test basic covariance to correlation conversion."""
        nco = NestedClusteredOptimization()
        cov = np.array([[4.0, 2.0], [2.0, 9.0]])  # std: 2, 3
        corr = nco._covariance_to_correlation(cov)

        # corr[i,j] = cov[i,j] / (std[i] * std[j])
        # corr[0,1] = 2 / (2 * 3) = 1/3
        expected = np.array([[1.0, 1.0 / 3.0], [1.0 / 3.0, 1.0]])
        np.testing.assert_array_almost_equal(corr, expected, decimal=10)

    def test_diagonal_is_one(self):
        """Test that diagonal elements are always 1."""
        nco = NestedClusteredOptimization()
        cov = np.array([[4.0, 2.0, 1.0], [2.0, 9.0, 3.0], [1.0, 3.0, 16.0]])
        corr = nco._covariance_to_correlation(cov)

        np.testing.assert_array_almost_equal(np.diag(corr), [1.0, 1.0, 1.0])

    def test_zero_variance_handling(self):
        """Test handling of zero variance assets."""
        nco = NestedClusteredOptimization()
        cov = np.array([[0.0, 0.0], [0.0, 4.0]])
        corr = nco._covariance_to_correlation(cov)

        # Should handle zero variance gracefully
        assert not np.isnan(corr).any()
        assert not np.isinf(corr).any()


@pytest.mark.unit
class TestKMeansClustering:
    """Test K-means clustering for NCO."""

    @pytest.fixture
    def sample_covariance(self):
        """Sample covariance matrix for testing."""
        # 4 assets with different correlation structures
        # Assets 0,1 highly correlated; Assets 2,3 highly correlated
        cov = np.array(
            [
                [0.04, 0.035, 0.005, 0.005],
                [0.035, 0.036, 0.006, 0.006],
                [0.005, 0.006, 0.0225, 0.02],
                [0.005, 0.006, 0.02, 0.025],
            ]
        )
        return cov

    def test_kmeans_clusters_assets(self, sample_covariance):
        """Test that K-means groups similar assets."""
        config = NCOConfig(n_clusters=2, random_state=42)
        nco = NestedClusteredOptimization(config)

        labels = nco._cluster_assets(sample_covariance)

        # Should have 2 clusters
        unique_labels = np.unique(labels)
        assert len(unique_labels) <= 2

        # All labels should be non-negative (K-means doesn't produce noise)
        assert np.all(labels >= 0)

    def test_kmeans_deterministic(self, sample_covariance):
        """Test that K-means is deterministic with same random_state."""
        config1 = NCOConfig(n_clusters=2, random_state=42)
        config2 = NCOConfig(n_clusters=2, random_state=42)

        nco1 = NestedClusteredOptimization(config1)
        nco2 = NestedClusteredOptimization(config2)

        labels1 = nco1._cluster_assets(sample_covariance)
        labels2 = nco2._cluster_assets(sample_covariance)

        np.testing.assert_array_equal(labels1, labels2)

    def test_kmeans_with_n_equals_assets(self, sample_covariance):
        """Test K-means when n_clusters equals n_assets."""
        config = NCOConfig(n_clusters=4, random_state=42)
        nco = NestedClusteredOptimization(config)

        labels = nco._cluster_assets(sample_covariance)

        # Each asset should be in its own cluster (or similar)
        assert len(np.unique(labels)) <= 4


@pytest.mark.unit
class TestDBSCANClustering:
    """Test DBSCAN clustering for NCO."""

    @pytest.fixture
    def sample_covariance(self):
        """Sample covariance matrix for testing."""
        # 6 assets: 2 distinct groups + 1 outlier
        cov = np.array(
            [
                [0.04, 0.035, 0.002, 0.002, 0.002, 0.002],
                [0.035, 0.036, 0.002, 0.002, 0.002, 0.002],
                [0.002, 0.002, 0.0225, 0.02, 0.002, 0.002],
                [0.002, 0.002, 0.02, 0.025, 0.002, 0.002],
                [0.002, 0.002, 0.002, 0.002, 0.01, 0.003],
                [0.002, 0.002, 0.002, 0.002, 0.003, 0.01],
            ]
        )
        return cov

    def test_dbscan_identifies_clusters(self, sample_covariance):
        """Test that DBSCAN identifies clusters."""
        config = NCOConfig(
            clustering_method=ClusteringMethod.DBSCAN,
            dbscan_eps=0.3,
            min_samples=2,
        )
        nco = NestedClusteredOptimization(config)

        labels = nco._cluster_assets(sample_covariance)

        # Should find at least 1 cluster
        unique_labels = np.unique(labels[labels >= 0])
        assert len(unique_labels) >= 1

    def test_dbscan_with_noise(self, sample_covariance):
        """Test DBSCAN can identify noise points."""
        config = NCOConfig(
            clustering_method=ClusteringMethod.DBSCAN,
            dbscan_eps=0.2,  # Smaller eps -> more noise
            min_samples=3,
        )
        nco = NestedClusteredOptimization(config)

        labels = nco._cluster_assets(sample_covariance)

        # May have noise points (label = -1)
        # This is expected behavior for DBSCAN
        assert len(labels) == 6  # All assets labeled

    def test_dbscan_no_clusters_fallback(self):
        """Test behavior when DBSCAN finds no clusters."""
        # Identity matrix = all assets uncorrelated
        cov = np.eye(5)

        config = NCOConfig(
            clustering_method=ClusteringMethod.DBSCAN,
            dbscan_eps=0.1,
            min_samples=3,
        )
        nco = NestedClusteredOptimization(config)

        labels = nco._cluster_assets(cov)

        # All points should be noise (-1)
        assert np.all(labels == -1)


@pytest.mark.unit
class TestWithinClusterOptimization:
    """Test within-cluster optimization."""

    @pytest.fixture
    def sample_data(self):
        """Sample returns and covariance for 4 assets."""
        expected_returns = np.array([0.08, 0.10, 0.12, 0.09])
        cov_matrix = np.array(
            [
                [0.010, 0.005, 0.003, 0.004],
                [0.005, 0.020, 0.006, 0.005],
                [0.003, 0.006, 0.015, 0.007],
                [0.004, 0.005, 0.007, 0.018],
            ]
        )
        return expected_returns, cov_matrix

    def test_optimize_two_assets(self, sample_data):
        """Test optimization within a 2-asset cluster."""
        expected_returns, cov_matrix = sample_data
        nco = NestedClusteredOptimization()

        # Cluster with assets 0 and 1
        cluster_mask = np.array([True, True, False, False])

        weights = nco._optimize_within_cluster(expected_returns, cov_matrix, cluster_mask)

        # Only assets in cluster should have non-zero weights
        assert weights[0] > 0 or weights[1] > 0
        assert weights[2] == 0
        assert weights[3] == 0

        # Weights should sum to 1
        assert abs(weights.sum() - 1.0) < 1e-6

    def test_optimize_single_asset_fallback(self, sample_data):
        """Test that single asset cluster uses equal weight."""
        expected_returns, cov_matrix = sample_data
        config = NCOConfig(min_cluster_size=2)
        nco = NestedClusteredOptimization(config)

        # Cluster with only 1 asset (below min_cluster_size)
        cluster_mask = np.array([True, False, False, False])

        weights = nco._optimize_within_cluster(expected_returns, cov_matrix, cluster_mask)

        # Should fall back to equal weight (100% to single asset)
        assert weights[0] == 1.0
        assert weights[1] == 0
        assert weights[2] == 0
        assert weights[3] == 0

    def test_long_only_constraint(self, sample_data):
        """Test that within-cluster optimization respects long-only."""
        expected_returns, cov_matrix = sample_data
        nco = NestedClusteredOptimization()

        cluster_mask = np.array([True, True, True, False])

        weights = nco._optimize_within_cluster(expected_returns, cov_matrix, cluster_mask)

        # All weights should be non-negative
        assert np.all(weights >= 0)

    def test_max_weight_constraint(self, sample_data):
        """Test that max weight constraint is enforced."""
        expected_returns, cov_matrix = sample_data
        config = NCOConfig(max_weight_single_asset=0.4)
        nco = NestedClusteredOptimization(config)

        cluster_mask = np.array([True, True, True, True])

        weights = nco._optimize_within_cluster(expected_returns, cov_matrix, cluster_mask)

        # No single weight should exceed max
        assert np.all(weights <= config.max_weight_single_asset)


@pytest.mark.unit
class TestClusterAllocation:
    """Test cross-cluster allocation (risk parity)."""

    @pytest.fixture
    def sample_data(self):
        """Sample data with 3 clusters."""
        expected_returns = np.array([0.08, 0.10, 0.12, 0.09, 0.11, 0.07])
        cov_matrix = np.array(
            [
                [0.010, 0.008, 0.002, 0.002, 0.002, 0.002],
                [0.008, 0.020, 0.002, 0.002, 0.002, 0.002],
                [0.002, 0.002, 0.015, 0.012, 0.002, 0.002],
                [0.002, 0.002, 0.012, 0.018, 0.002, 0.002],
                [0.002, 0.002, 0.002, 0.002, 0.025, 0.02],
                [0.002, 0.002, 0.002, 0.002, 0.02, 0.022],
            ]
        )
        # Clusters: [0,1], [2,3], [4,5]
        cluster_labels = np.array([0, 0, 1, 1, 2, 2])
        return expected_returns, cov_matrix, cluster_labels

    def test_allocate_three_clusters(self, sample_data):
        """Test allocation across 3 clusters."""
        expected_returns, cov_matrix, cluster_labels = sample_data
        nco = NestedClusteredOptimization()

        cluster_weights = nco._allocate_clusters(expected_returns, cov_matrix, cluster_labels)

        # Should have 3 cluster weights
        assert len(cluster_weights) == 3

        # Weights should sum to 1
        assert abs(cluster_weights.sum() - 1.0) < 1e-6

        # All weights should be positive
        assert np.all(cluster_weights > 0)

    def test_risk_parity_allocation(self, sample_data):
        """Test that lower volatility clusters get higher weights."""
        expected_returns, cov_matrix, cluster_labels = sample_data
        nco = NestedClusteredOptimization()

        cluster_weights = nco._allocate_clusters(expected_returns, cov_matrix, cluster_labels)

        # Compute cluster volatilities
        cluster_vols = []
        for i in range(3):
            cluster_mask = cluster_labels == i
            cluster_cov = cov_matrix[np.ix_(cluster_mask, cluster_mask)]
            equal_w = np.ones(cluster_mask.sum()) / 2
            vol = np.sqrt(equal_w @ cluster_cov @ equal_w)
            cluster_vols.append(vol)

        # Risk parity: weight proportional to 1/volatility
        # Lower volatility -> higher weight
        for i in range(2):
            if cluster_vols[i] < cluster_vols[i + 1]:
                assert cluster_weights[i] >= cluster_weights[i + 1]

    def test_allocate_with_noise(self):
        """Test allocation when DBSCAN produces noise points."""
        expected_returns = np.array([0.08, 0.10, 0.12, 0.09])
        cov_matrix = np.eye(4)  # Uncorrelated assets
        cluster_labels = np.array([-1, -1, 0, 0])  # 2 noise, 1 cluster

        nco = NestedClusteredOptimization()

        cluster_weights = nco._allocate_clusters(expected_returns, cov_matrix, cluster_labels)

        # Should handle noise gracefully
        assert len(cluster_weights) >= 1
        assert np.all(cluster_weights >= 0)


@pytest.mark.unit
class TestFullNCO:
    """Test complete NCO pipeline."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for 6 assets with 2 natural clusters."""
        np.random.seed(42)

        # Cluster 1: Assets 0-2 (highly correlated)
        # Cluster 2: Assets 3-5 (highly correlated)
        expected_returns = np.array([0.08, 0.10, 0.09, 0.12, 0.11, 0.13])

        cov_matrix = np.array(
            [
                # Cluster 1
                [0.010, 0.008, 0.007, 0.002, 0.002, 0.002],
                [0.008, 0.020, 0.009, 0.002, 0.002, 0.002],
                [0.007, 0.009, 0.015, 0.002, 0.002, 0.002],
                # Cluster 2
                [0.002, 0.002, 0.002, 0.025, 0.022, 0.021],
                [0.002, 0.002, 0.002, 0.022, 0.030, 0.023],
                [0.002, 0.002, 0.002, 0.021, 0.023, 0.028],
            ]
        )

        return expected_returns, cov_matrix

    def test_get_weights_returns_result(self, sample_data):
        """Test that get_weights returns NCOResult."""
        expected_returns, cov_matrix = sample_data
        nco = NestedClusteredOptimization()

        result = nco.get_weights(expected_returns, cov_matrix)

        assert isinstance(result, NCOResult)
        assert isinstance(result.weights, np.ndarray)
        assert isinstance(result.cluster_labels, np.ndarray)

    def test_weights_are_valid(self, sample_data):
        """Test that computed weights are valid."""
        expected_returns, cov_matrix = sample_data
        nco = NestedClusteredOptimization()

        result = nco.get_weights(expected_returns, cov_matrix)

        # All weights should be non-negative
        assert np.all(result.weights >= 0)

        # Weights should sum to 1
        assert abs(result.weights.sum() - 1.0) < 1e-4

    def test_cluster_labels_valid(self, sample_data):
        """Test that cluster labels are valid."""
        expected_returns, cov_matrix = sample_data
        config = NCOConfig(n_clusters=2, random_state=42)
        nco = NestedClusteredOptimization(config)

        result = nco.get_weights(expected_returns, cov_matrix)

        # Should have cluster labels for all assets
        assert len(result.cluster_labels) == len(expected_returns)

        # Number of clusters should be reasonable
        assert result.n_clusters >= 1
        assert result.n_clusters <= len(expected_returns)

    def test_portfolio_metrics_calculated(self, sample_data):
        """Test that portfolio metrics are calculated."""
        expected_returns, cov_matrix = sample_data
        nco = NestedClusteredOptimization()

        result = nco.get_weights(expected_returns, cov_matrix)

        # Expected return should be in range
        min_return = expected_returns.min()
        max_return = expected_returns.max()
        assert min_return <= result.expected_return <= max_return

        # Risk should be positive
        assert result.expected_risk > 0

        # Sharpe ratio should be reasonable
        assert isinstance(result.sharpe_ratio, float)

    def test_kmeans_vs_dbscan_difference(self, sample_data):
        """Test that K-means and DBSCAN may produce different results."""
        expected_returns, cov_matrix = sample_data

        config_kmeans = NCOConfig(
            n_clusters=2,
            clustering_method=ClusteringMethod.KMEANS,
            random_state=42,
        )
        config_dbscan = NCOConfig(
            n_clusters=2,
            clustering_method=ClusteringMethod.DBSCAN,
            dbscan_eps=0.3,
            min_samples=2,
        )

        nco_kmeans = NestedClusteredOptimization(config_kmeans)
        nco_dbscan = NestedClusteredOptimization(config_dbscan)

        result_kmeans = nco_kmeans.get_weights(expected_returns, cov_matrix)
        result_dbscan = nco_dbscan.get_weights(expected_returns, cov_matrix)

        # Results may differ
        # (they might be the same by chance, but usually different)
        assert isinstance(result_kmeans, NCOResult)
        assert isinstance(result_dbscan, NCOResult)

    def test_reproducibility(self, sample_data):
        """Test that results are reproducible with same seed."""
        expected_returns, cov_matrix = sample_data

        config1 = NCOConfig(n_clusters=2, random_state=42)
        config2 = NCOConfig(n_clusters=2, random_state=42)

        nco1 = NestedClusteredOptimization(config1)
        nco2 = NestedClusteredOptimization(config2)

        result1 = nco1.get_weights(expected_returns, cov_matrix)
        result2 = nco2.get_weights(expected_returns, cov_matrix)

        np.testing.assert_array_almost_equal(result1.weights, result2.weights)
        np.testing.assert_array_equal(result1.cluster_labels, result2.cluster_labels)


@pytest.mark.unit
class TestNCOResult:
    """Test NCOResult methods."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample NCOResult."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        cluster_labels = np.array([0, 0, 1, 1])
        cluster_weights = np.array([0.5, 0.5])
        within_cluster_weights = {
            0: np.array([0.5, 0.5]),
            1: np.array([0.5, 0.5]),
        }

        return NCOResult(
            weights=weights,
            cluster_labels=cluster_labels,
            n_clusters=2,
            expected_return=0.10,
            expected_risk=0.15,
            sharpe_ratio=0.67,
            cluster_weights=cluster_weights,
            within_cluster_weights=within_cluster_weights,
            converged=True,
        )

    def test_get_weight_dict(self, sample_result):
        """Test getting weights as dictionary."""
        asset_names = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        weight_dict = sample_result.get_weight_dict(asset_names)

        assert isinstance(weight_dict, dict)
        assert len(weight_dict) == 4
        assert weight_dict["AAPL"] == 0.25
        assert weight_dict["MSFT"] == 0.25
        assert weight_dict["GOOGL"] == 0.25
        assert weight_dict["AMZN"] == 0.25

    def test_get_weight_dict_wrong_length(self, sample_result):
        """Test that wrong number of asset names raises error."""
        asset_names = ["AAPL", "MSFT", "GOOGL"]  # Only 3 names for 4 weights

        with pytest.raises(ValueError, match="Number of asset names"):
            sample_result.get_weight_dict(asset_names)

    def test_get_cluster_summary(self, sample_result):
        """Test getting cluster summary."""
        summary = sample_result.get_cluster_summary()

        assert isinstance(summary, dict)
        assert summary["n_clusters"] == 2
        assert "cluster_sizes" in summary
        assert "cluster_weights" in summary
        assert summary["largest_cluster"] in [0, 1]
        assert summary["largest_cluster_size"] == 2

    def test_is_diversified(self, sample_result):
        """Test diversification check."""
        # All weights are 0.25, so should pass 0.30 threshold
        assert sample_result.is_diversified(max_concentration=0.30)

        # But fail at 0.20 threshold
        assert not sample_result.is_diversified(max_concentration=0.20)


@pytest.mark.unit
class TestConvenienceFunction:
    """Test convenience function compute_nco_weights."""

    def test_compute_nco_weights_basic(self):
        """Test basic usage of convenience function."""
        expected_returns = np.array([0.08, 0.10, 0.12])
        cov_matrix = np.array(
            [
                [0.01, 0.005, 0.003],
                [0.005, 0.02, 0.006],
                [0.003, 0.006, 0.015],
            ]
        )

        weights = compute_nco_weights(
            expected_returns,
            cov_matrix,
            n_clusters=2,
            clustering_method="kmeans",
        )

        assert isinstance(weights, np.ndarray)
        assert len(weights) == 3
        assert np.all(weights >= 0)
        assert abs(weights.sum() - 1.0) < 1e-4

    def test_compute_nco_weights_dbscan(self):
        """Test convenience function with DBSCAN."""
        expected_returns = np.array([0.08, 0.10, 0.12, 0.09])
        cov_matrix = np.eye(4)

        weights = compute_nco_weights(
            expected_returns,
            cov_matrix,
            n_clusters=2,
            clustering_method="dbscan",
        )

        assert isinstance(weights, np.ndarray)
        assert len(weights) == 4


@pytest.mark.unit
class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.fixture
    def valid_data(self):
        """Valid test data."""
        return (
            np.array([0.08, 0.10, 0.12]),
            np.array([[0.01, 0.005, 0.003], [0.005, 0.02, 0.006], [0.003, 0.006, 0.015]]),
        )

    def test_invalid_returns_ndim(self, valid_data):
        """Test that 2D returns raises error."""
        _, cov_matrix = valid_data
        expected_returns = np.array([[0.08, 0.10], [0.12, 0.09]])  # 2D

        nco = NestedClusteredOptimization()

        with pytest.raises(ValueError, match="expected_returns must be 1D"):
            nco.get_weights(expected_returns, cov_matrix)

    def test_invalid_cov_ndim(self, valid_data):
        """Test that 1D cov_matrix raises error."""
        expected_returns, _ = valid_data
        cov_matrix = np.array([0.01, 0.02, 0.015])  # 1D

        nco = NestedClusteredOptimization()

        with pytest.raises(ValueError, match="cov_matrix must be 2D"):
            nco.get_weights(expected_returns, cov_matrix)

    def test_shape_mismatch(self, valid_data):
        """Test that mismatched shapes raise error."""
        expected_returns, _ = valid_data
        cov_matrix = np.array([[0.01, 0.005], [0.005, 0.02]])  # 2x2

        nco = NestedClusteredOptimization()

        with pytest.raises(ValueError, match="incompatible"):
            nco.get_weights(expected_returns, cov_matrix)

    def test_insufficient_assets(self):
        """Test that too few assets raise error."""
        expected_returns = np.array([0.08])
        cov_matrix = np.array([[0.01]])

        nco = NestedClusteredOptimization()

        with pytest.raises(ValueError, match="Need at least 2 assets"):
            nco.get_weights(expected_returns, cov_matrix)

    def test_list_input_conversion(self, valid_data):
        """Test that list inputs are converted to numpy arrays."""
        expected_returns = [0.08, 0.10, 0.12]
        cov_matrix = [[0.01, 0.005, 0.003], [0.005, 0.02, 0.006], [0.003, 0.006, 0.015]]

        nco = NestedClusteredOptimization()

        # Should not raise error - lists are converted
        result = nco.get_weights(expected_returns, cov_matrix)

        assert isinstance(result, NCOResult)


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_identical_assets(self):
        """Test with perfectly correlated assets."""
        expected_returns = np.array([0.08, 0.10, 0.12])
        # All assets perfectly correlated
        cov_matrix = np.array(
            [
                [0.01, 0.01, 0.01],
                [0.01, 0.02, 0.014],
                [0.01, 0.014, 0.018],
            ]
        )

        nco = NestedClusteredOptimization()
        result = nco.get_weights(expected_returns, cov_matrix)

        # Should still produce valid weights
        assert np.all(result.weights >= 0)
        assert abs(result.weights.sum() - 1.0) < 1e-4

    def test_uncorrelated_assets(self):
        """Test with uncorrelated assets."""
        expected_returns = np.array([0.08, 0.10, 0.12])
        cov_matrix = np.eye(3) * 0.01

        nco = NestedClusteredOptimization()
        result = nco.get_weights(expected_returns, cov_matrix)

        # Should produce valid weights
        assert np.all(result.weights >= 0)
        assert abs(result.weights.sum() - 1.0) < 1e-4

    def test_two_assets_minimum(self):
        """Test with minimum 2 assets."""
        expected_returns = np.array([0.08, 0.10])
        cov_matrix = np.array([[0.01, 0.005], [0.005, 0.02]])

        nco = NestedClusteredOptimization()
        result = nco.get_weights(expected_returns, cov_matrix)

        assert len(result.weights) == 2
        assert abs(result.weights.sum() - 1.0) < 1e-4

    def test_many_assets(self):
        """Test with many assets."""
        n_assets = 50
        np.random.seed(42)

        # Generate random correlation matrix
        corr = np.random.uniform(0.1, 0.5, (n_assets, n_assets))
        corr = (corr + corr.T) / 2
        np.fill_diagonal(corr, 1.0)

        # Convert to covariance
        vols = np.random.uniform(0.1, 0.3, n_assets)
        cov_matrix = corr * np.outer(vols, vols)

        expected_returns = np.random.uniform(0.05, 0.15, n_assets)

        nco = NestedClusteredOptimization()
        result = nco.get_weights(expected_returns, cov_matrix)

        assert len(result.weights) == n_assets
        assert np.all(result.weights >= 0)
        assert abs(result.weights.sum() - 1.0) < 1e-4

    def test_zero_variance_asset(self):
        """Test handling of zero variance asset."""
        expected_returns = np.array([0.08, 0.10, 0.12])
        cov_matrix = np.array(
            [
                [0.01, 0.005, 0.003],
                [0.005, 0.00, 0.00],  # Zero variance
                [0.003, 0.00, 0.015],
            ]
        )

        nco = NestedClusteredOptimization()
        result = nco.get_weights(expected_returns, cov_matrix)

        # Should handle gracefully
        assert isinstance(result, NCOResult)


@pytest.mark.unit
class TestGetDistanceMatrix:
    """Test get_distance_matrix method."""

    def test_distance_matrix_none_initially(self):
        """Test that distance matrix is None initially."""
        nco = NestedClusteredOptimization()
        assert nco.get_distance_matrix() is None

    def test_distance_matrix_after_clustering(self):
        """Test that distance matrix is available after clustering."""
        expected_returns = np.array([0.08, 0.10, 0.12])
        cov_matrix = np.array(
            [
                [0.01, 0.005, 0.003],
                [0.005, 0.02, 0.006],
                [0.003, 0.006, 0.015],
            ]
        )

        nco = NestedClusteredOptimization()
        nco.get_weights(expected_returns, cov_matrix)

        distance_matrix = nco.get_distance_matrix()

        assert distance_matrix is not None
        assert distance_matrix.shape == (3, 3)
        assert np.all(np.diag(distance_matrix) == 0)
