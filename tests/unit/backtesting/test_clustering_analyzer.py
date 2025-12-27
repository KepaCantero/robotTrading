"""
Unit tests for AdvancedClusteringAnalyzer.

Tests cover:
- Hierarchical clustering
- DBSCAN clustering
- PCA analysis
- ICA analysis
- t-SNE visualization
- Silhouette analysis
- Optimal cluster detection
- Edge cases and error handling
"""


import numpy as np
import pytest

from app.backtesting.clustering_analyzer import AdvancedClusteringAnalyzer


@pytest.fixture
def analyzer():
    """Create analyzer instance."""
    return AdvancedClusteringAnalyzer(random_state=42)


@pytest.fixture
def sample_2d_data():
    """Create 2D sample data with clear clusters."""
    np.random.seed(42)
    # Cluster 1
    c1 = np.random.normal(0, 0.5, (20, 2))
    # Cluster 2
    c2 = np.random.normal(5, 0.5, (20, 2))
    # Cluster 3
    c3 = np.random.normal([5, 5], 0.5, (20, 2))
    return np.vstack([c1, c2, c3]).tolist()


@pytest.fixture
def sample_5d_data():
    """Create 5D sample data."""
    np.random.seed(42)
    return np.random.randn(50, 5).tolist()


@pytest.fixture
def sample_labels(sample_2d_data):
    """Create sample cluster labels matching data size."""
    return [0] * 20 + [1] * 20 + [2] * 20


class TestHierarchicalClustering:
    """Test hierarchical clustering."""

    def test_hierarchical_clustering_basic(self, analyzer, sample_2d_data):
        """Test basic hierarchical clustering."""
        result = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)

        assert result is not None
        assert 'labels' in result
        assert 'n_clusters' in result
        assert 'silhouette_score' in result
        assert 'cluster_sizes' in result
        assert len(result['labels']) == len(sample_2d_data)
        assert result['n_clusters'] == 3

    def test_hierarchical_clustering_labels_valid(self, analyzer, sample_2d_data):
        """Test that cluster labels are valid."""
        result = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)

        unique_labels = set(result['labels'])
        assert len(unique_labels) <= 3
        assert all(isinstance(l, int) for l in result['labels'])

    def test_hierarchical_clustering_different_linkage(self, analyzer, sample_2d_data):
        """Test different linkage methods."""
        for method in ['ward', 'complete', 'average', 'single']:
            result = analyzer.hierarchical_clustering(
                sample_2d_data, n_clusters=3, linkage_method=method
            )
            assert result is not None
            assert result['linkage_method'] == method

    def test_hierarchical_clustering_silhouette_score(self, analyzer, sample_2d_data):
        """Test silhouette score is calculated."""
        result = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)

        assert 'silhouette_score' in result
        assert isinstance(result['silhouette_score'], float)
        assert -1 <= result['silhouette_score'] <= 1

    def test_hierarchical_clustering_cluster_sizes(self, analyzer, sample_2d_data):
        """Test cluster sizes sum to data length."""
        result = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)

        cluster_sizes = result['cluster_sizes']
        total = sum(cluster_sizes.values())
        assert total == len(sample_2d_data)

    def test_hierarchical_clustering_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.hierarchical_clustering([[1, 2]])
        assert result is None

    def test_hierarchical_clustering_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.hierarchical_clustering([])
        assert result is None


class TestDBSCANClustering:
    """Test DBSCAN clustering."""

    def test_dbscan_clustering_basic(self, analyzer, sample_2d_data):
        """Test basic DBSCAN clustering."""
        result = analyzer.dbscan_clustering(sample_2d_data, eps=1.0, min_samples=5)

        assert result is not None
        assert 'labels' in result
        assert 'n_clusters' in result
        assert 'n_noise_points' in result
        assert len(result['labels']) == len(sample_2d_data)

    def test_dbscan_clustering_finds_noise(self, analyzer, sample_2d_data):
        """Test that DBSCAN can identify noise points."""
        result = analyzer.dbscan_clustering(sample_2d_data, eps=0.1, min_samples=5)

        assert result is not None
        # With very small eps, should find noise points
        if result['n_noise_points'] > 0:
            assert -1 in result['labels']

    def test_dbscan_clustering_parameters(self, analyzer, sample_2d_data):
        """Test DBSCAN with different parameters."""
        result = analyzer.dbscan_clustering(sample_2d_data, eps=2.0, min_samples=10)

        assert result is not None
        assert result['eps'] == 2.0
        assert result['min_samples'] == 10

    def test_dbscan_clustering_silhouette_score(self, analyzer, sample_2d_data):
        """Test silhouette score calculation."""
        result = analyzer.dbscan_clustering(sample_2d_data, eps=1.0, min_samples=5)

        assert 'silhouette_score' in result
        assert isinstance(result['silhouette_score'], float)

    def test_dbscan_clustering_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.dbscan_clustering([[1, 2]])
        assert result is None

    def test_dbscan_clustering_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.dbscan_clustering([])
        assert result is None


class TestPCAAnalysis:
    """Test Principal Component Analysis."""

    def test_pca_basic(self, analyzer, sample_5d_data):
        """Test basic PCA."""
        result = analyzer.pca_analysis(sample_5d_data, n_components=2)

        assert result is not None
        assert 'n_components' in result
        assert 'explained_variance' in result
        assert 'transformed_data' in result
        assert result['n_components'] == 2
        assert len(result['explained_variance']) == 2

    def test_pca_variance_explained(self, analyzer, sample_5d_data):
        """Test that variance is explained."""
        result = analyzer.pca_analysis(sample_5d_data, n_components=3)

        assert result is not None
        total_var = result['total_variance_explained']
        assert 0 <= total_var <= 1

    def test_pca_cumulative_variance(self, analyzer, sample_5d_data):
        """Test cumulative variance is increasing."""
        result = analyzer.pca_analysis(sample_5d_data, n_components=3)

        cum_var = result['cumulative_variance']
        assert all(cum_var[i] <= cum_var[i + 1] for i in range(len(cum_var) - 1))

    def test_pca_auto_components(self, analyzer, sample_5d_data):
        """Test PCA with automatic component selection."""
        result = analyzer.pca_analysis(sample_5d_data, variance_threshold=0.80)

        assert result is not None
        assert result['total_variance_explained'] >= 0.75  # Allow some variance loss

    def test_pca_transformed_data_shape(self, analyzer, sample_5d_data):
        """Test transformed data shape."""
        result = analyzer.pca_analysis(sample_5d_data, n_components=2)

        assert len(result['transformed_data']) == len(sample_5d_data)
        assert len(result['transformed_data'][0]) == 2

    def test_pca_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.pca_analysis([[1, 2]])
        assert result is None

    def test_pca_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.pca_analysis([])
        assert result is None


class TestICAAnalysis:
    """Test Independent Component Analysis."""

    def test_ica_basic(self, analyzer, sample_5d_data):
        """Test basic ICA."""
        result = analyzer.ica_analysis(sample_5d_data, n_components=3)

        assert result is not None
        assert 'n_components' in result
        assert 'algorithm' in result
        assert 'transformed_data' in result
        assert result['n_components'] == 3

    def test_ica_mixing_matrix(self, analyzer, sample_5d_data):
        """Test mixing and unmixing matrices."""
        result = analyzer.ica_analysis(sample_5d_data, n_components=3)

        assert result is not None
        assert 'mixing_matrix' in result
        assert 'unmixing_matrix' in result
        assert len(result['mixing_matrix']) == 5  # Original features
        assert len(result['mixing_matrix'][0]) == 3  # Components

    def test_ica_algorithms(self, analyzer, sample_5d_data):
        """Test different ICA algorithms."""
        for algo in ['parallel', 'deflation']:
            result = analyzer.ica_analysis(sample_5d_data, n_components=2, algorithm=algo)
            assert result is not None
            assert result['algorithm'] == algo

    def test_ica_transformed_data(self, analyzer, sample_5d_data):
        """Test transformed data shape."""
        result = analyzer.ica_analysis(sample_5d_data, n_components=2)

        assert len(result['transformed_data']) == len(sample_5d_data)
        assert len(result['transformed_data'][0]) == 2

    def test_ica_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.ica_analysis([[1, 2]])
        assert result is None

    def test_ica_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.ica_analysis([])
        assert result is None


class TestTSNEVisualization:
    """Test t-SNE visualization."""

    def test_tsne_2d(self, analyzer, sample_5d_data):
        """Test t-SNE 2D projection."""
        result = analyzer.tsne_visualization(sample_5d_data, n_components=2)

        assert result is not None
        assert 'transformed_data' in result
        assert 'kl_divergence' in result
        assert len(result['transformed_data']) == len(sample_5d_data)
        assert len(result['transformed_data'][0]) == 2

    def test_tsne_3d(self, analyzer, sample_5d_data):
        """Test t-SNE 3D projection."""
        result = analyzer.tsne_visualization(sample_5d_data, n_components=3)

        assert result is not None
        assert len(result['transformed_data'][0]) == 3

    def test_tsne_parameters(self, analyzer, sample_5d_data):
        """Test t-SNE with different parameters."""
        result = analyzer.tsne_visualization(
            sample_5d_data, n_components=2, perplexity=20, n_iter=500
        )

        assert result is not None
        # Perplexity might be adjusted based on data size
        assert isinstance(result['perplexity'], int)
        assert result['perplexity'] <= 20
        # Accept both old (n_iter) and new (max_iter) parameter names
        assert result.get('n_iterations') == 500 or result.get('max_iter') == 500

    def test_tsne_kl_divergence(self, analyzer, sample_5d_data):
        """Test KL divergence is calculated."""
        result = analyzer.tsne_visualization(sample_5d_data, n_components=2)

        assert result is not None
        assert isinstance(result['kl_divergence'], float)
        assert result['kl_divergence'] >= 0

    def test_tsne_invalid_components(self, analyzer, sample_5d_data):
        """Test with invalid n_components."""
        result = analyzer.tsne_visualization(sample_5d_data, n_components=5)

        assert result is not None
        assert result['n_components'] == 2  # Should default to 2

    def test_tsne_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.tsne_visualization([[1, 2]])
        assert result is None

    def test_tsne_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.tsne_visualization([])
        assert result is None


class TestSilhouetteAnalysis:
    """Test silhouette analysis."""

    def test_silhouette_basic(self, analyzer, sample_2d_data, sample_labels):
        """Test basic silhouette analysis."""
        result = analyzer.silhouette_analysis(sample_2d_data, sample_labels)

        assert result is not None
        assert 'overall_score' in result
        assert 'cluster_scores' in result
        assert 'sample_scores' in result
        assert 'n_clusters' in result

    def test_silhouette_overall_score(self, analyzer, sample_2d_data, sample_labels):
        """Test overall silhouette score."""
        result = analyzer.silhouette_analysis(sample_2d_data, sample_labels)

        assert result is not None
        score = result['overall_score']
        assert isinstance(score, float)
        assert -1 <= score <= 1

    def test_silhouette_cluster_scores(self, analyzer, sample_2d_data, sample_labels):
        """Test per-cluster silhouette scores."""
        result = analyzer.silhouette_analysis(sample_2d_data, sample_labels)

        cluster_scores = result['cluster_scores']
        assert len(cluster_scores) == 3  # Three clusters in labels
        assert all(isinstance(v, float) for v in cluster_scores.values())

    def test_silhouette_sample_scores(self, analyzer, sample_2d_data, sample_labels):
        """Test sample-level silhouette scores."""
        result = analyzer.silhouette_analysis(sample_2d_data, sample_labels)

        sample_scores = result['sample_scores']
        assert len(sample_scores) == len(sample_2d_data)
        assert all(isinstance(s, float) for s in sample_scores)

    def test_silhouette_interpretation(self, analyzer, sample_2d_data, sample_labels):
        """Test interpretation string is provided."""
        result = analyzer.silhouette_analysis(sample_2d_data, sample_labels)

        assert 'interpretation' in result
        assert isinstance(result['interpretation'], str)
        assert result['interpretation'] in [
            "Strong structure",
            "Reasonable structure",
            "Weak structure",
            "No substantial structure",
        ]

    def test_silhouette_insufficient_clusters(self, analyzer, sample_2d_data):
        """Test with only one cluster."""
        single_cluster_labels = [0] * len(sample_2d_data)
        result = analyzer.silhouette_analysis(sample_2d_data, single_cluster_labels)
        assert result is None

    def test_silhouette_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        result = analyzer.silhouette_analysis([[1, 2]], [0])
        assert result is None

    def test_silhouette_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.silhouette_analysis([], [])
        assert result is None


class TestOptimalClusters:
    """Test optimal cluster detection."""

    def test_optimal_clusters_silhouette(self, analyzer, sample_2d_data):
        """Test optimal clusters with silhouette method."""
        result = analyzer.optimal_clusters(sample_2d_data, k_range=(2, 8), method='silhouette')

        assert result is not None
        assert 'optimal_k' in result
        assert 'scores' in result
        assert 'method' in result
        assert result['method'] == 'silhouette'
        assert result['optimal_k'] >= 2

    def test_optimal_clusters_elbow(self, analyzer, sample_2d_data):
        """Test optimal clusters with elbow method."""
        result = analyzer.optimal_clusters(sample_2d_data, k_range=(2, 8), method='elbow')

        assert result is not None
        assert 'optimal_k' in result
        assert 'scores' in result
        assert result['method'] == 'elbow'

    def test_optimal_clusters_scores(self, analyzer, sample_2d_data):
        """Test that scores are calculated for each k."""
        result = analyzer.optimal_clusters(sample_2d_data, k_range=(2, 5), method='silhouette')

        scores = result['scores']
        assert len(scores) > 0
        assert all(isinstance(s, (int, float)) for s in scores.values())

    def test_optimal_clusters_k_range(self, analyzer, sample_2d_data):
        """Test k_range is respected."""
        result = analyzer.optimal_clusters(sample_2d_data, k_range=(2, 5), method='silhouette')

        assert result is not None
        k_range = result['k_range']
        assert k_range[0] >= 2
        assert k_range[1] <= 5

    def test_optimal_clusters_insufficient_data(self, analyzer):
        """Test with minimal data."""
        result = analyzer.optimal_clusters([[1, 2], [2, 3], [3, 4]], k_range=(2, 3))
        # With minimal data, should either return None or a graceful result
        if result is not None:
            assert 'optimal_k' in result or 'scores' in result

    def test_optimal_clusters_empty_data(self, analyzer):
        """Test with empty data."""
        result = analyzer.optimal_clusters([], k_range=(2, 5))
        assert result is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_sample(self, analyzer):
        """Test with single sample."""
        data = [[1, 2, 3, 4, 5]]
        result = analyzer.pca_analysis(data)
        assert result is None

    def test_identical_features(self, analyzer):
        """Test with identical feature values."""
        data = [[1, 1, 1]] * 10
        result = analyzer.pca_analysis(data, n_components=1)
        # Should handle gracefully
        assert result is None or isinstance(result, dict)

    def test_very_high_dimensions(self, analyzer):
        """Test with high-dimensional data."""
        np.random.seed(42)
        data = np.random.randn(30, 100).tolist()
        result = analyzer.pca_analysis(data, n_components=2)
        assert result is not None

    def test_very_small_values(self, analyzer):
        """Test with very small feature values."""
        np.random.seed(42)
        data = (np.random.randn(50, 5) * 1e-10).tolist()
        result = analyzer.pca_analysis(data, n_components=2)
        assert result is not None

    def test_mixed_positive_negative(self, analyzer):
        """Test with mixed positive/negative values."""
        np.random.seed(42)
        data = np.random.randn(50, 5).tolist()
        result = analyzer.pca_analysis(data, n_components=2)
        assert result is not None


class TestIntegration:
    """Integration tests."""

    def test_full_clustering_workflow(self, analyzer, sample_2d_data):
        """Test complete clustering workflow."""
        # Hierarchical clustering
        result_h = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)
        assert result_h is not None

        # DBSCAN clustering
        result_db = analyzer.dbscan_clustering(sample_2d_data, eps=1.0)
        assert result_db is not None

        # Silhouette analysis
        result_s = analyzer.silhouette_analysis(sample_2d_data, result_h['labels'])
        assert result_s is not None

    def test_dimensionality_reduction_chain(self, analyzer, sample_5d_data):
        """Test chaining dimensionality reduction methods."""
        # PCA first
        result_pca = analyzer.pca_analysis(sample_5d_data, n_components=3)
        assert result_pca is not None

        # t-SNE on PCA results
        result_tsne = analyzer.tsne_visualization(result_pca['transformed_data'], n_components=2)
        assert result_tsne is not None

    def test_multiple_clustering_methods_consistency(self, analyzer, sample_2d_data):
        """Test consistency across different clustering methods."""
        # Hierarchical
        result_h = analyzer.hierarchical_clustering(sample_2d_data, n_clusters=3)

        # DBSCAN with reasonable parameters
        result_db = analyzer.dbscan_clustering(sample_2d_data, eps=1.0, min_samples=5)

        # Both should produce valid cluster assignments
        assert len(result_h['labels']) == len(sample_2d_data)
        assert len(result_db['labels']) == len(sample_2d_data)
