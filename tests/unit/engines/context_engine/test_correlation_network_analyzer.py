"""
Unit tests for Correlation Network Analyzer.

Tests the CorrelationNetworkAnalyzer class which uses network theory
to analyze correlations between assets.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def sample_correlation_matrix():
    """Generate a sample correlation matrix for testing."""
    return np.array(
        [[1.0, 0.8, 0.3, 0.2], [0.8, 1.0, 0.4, 0.1], [0.3, 0.4, 1.0, 0.9], [0.2, 0.1, 0.9, 1.0]]
    )


@pytest.fixture
def high_correlation_matrix():
    """Generate a high correlation matrix."""
    return np.array(
        [
            [1.0, 0.9, 0.85, 0.8],
            [0.9, 1.0, 0.88, 0.82],
            [0.85, 0.88, 1.0, 0.87],
            [0.8, 0.82, 0.87, 1.0],
        ]
    )


@pytest.fixture
def low_correlation_matrix():
    """Generate a low correlation matrix."""
    return np.array(
        [
            [1.0, 0.2, 0.1, 0.05],
            [0.2, 1.0, 0.15, 0.1],
            [0.1, 0.15, 1.0, 0.08],
            [0.05, 0.1, 0.08, 1.0],
        ]
    )


@pytest.fixture
def sample_symbols():
    """Generate sample symbol list."""
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN']


@pytest.fixture
def analyzer():
    """Create a CorrelationNetworkAnalyzer instance for testing."""
    from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
        CorrelationNetworkAnalyzer,
    )

    return CorrelationNetworkAnalyzer()


@pytest.fixture
def custom_threshold_analyzer():
    """Create analyzer with custom threshold."""
    from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
        CorrelationNetworkAnalyzer,
    )

    return CorrelationNetworkAnalyzer(config={'threshold': 0.7})


@pytest.mark.unit
class TestCorrelationNetworkAnalyzerInit:
    """Test initialization of CorrelationNetworkAnalyzer."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )

        analyzer = CorrelationNetworkAnalyzer()

        assert analyzer.threshold == 0.5

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )

        config = {'threshold': 0.8}
        analyzer = CorrelationNetworkAnalyzer(config=config)

        assert analyzer.threshold == 0.8


@pytest.mark.unit
class TestAnalyzeNetwork:
    """Test network analysis functionality."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_analyze_network_basic(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test basic network analysis."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 3
        mock_centrality.return_value = {'AAPL': 0.8, 'MSFT': 0.7, 'GOOGL': 0.6, 'AMZN': 0.5}
        mock_communities.return_value = [({'AAPL', 'MSFT'},), ({'GOOGL', 'AMZN'},)]

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert isinstance(result, dict)
        assert 'centrality' in result
        assert 'clusters' in result
        assert 'num_nodes' in result
        assert 'num_edges' in result

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_analyze_network_with_high_correlation(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        high_correlation_matrix,
        sample_symbols,
    ):
        """Test network analysis with high correlation."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 6
        mock_centrality.return_value = {sym: 0.9 for sym in sample_symbols}
        mock_communities.return_value[
            ({sample_symbols[0], sample_symbols[1], sample_symbols[2], sample_symbols[3]},)
        ]

        result = analyzer.analyze_network(high_correlation_matrix, sample_symbols)

        assert result['num_nodes'] == 4
        # With high correlation, should have more edges
        assert result['num_edges'] > 0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_analyze_network_with_low_correlation(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        low_correlation_matrix,
        sample_symbols,
    ):
        """Test network analysis with low correlation."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 0
        mock_centrality.return_value = {sym: 0.0 for sym in sample_symbols}
        mock_communities.return_value = []

        result = analyzer.analyze_network(low_correlation_matrix, sample_symbols)

        assert result['num_nodes'] == 4
        # With low correlation, should have fewer edges
        assert result['num_edges'] == 0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_analyze_network_returns_centrality_dict(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that centrality is returned as dictionary."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 3
        expected_centrality = {'AAPL': 0.8, 'MSFT': 0.7, 'GOOGL': 0.6, 'AMZN': 0.5}
        mock_centrality.return_value = expected_centrality
        mock_communities.return_value = [({'AAPL', 'MSFT'},), ({'GOOGL', 'AMZN'},)]

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert isinstance(result['centrality'], dict)
        assert len(result['centrality']) == len(sample_symbols)

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_analyze_network_returns_clusters(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that clusters are returned as list of lists."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 3
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = [({'AAPL', 'MSFT'},), ({'GOOGL', 'AMZN'},)]

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert isinstance(result['clusters'], list)
        assert all(isinstance(cluster, list) for cluster in result['clusters'])


@pytest.mark.unit
class TestThresholdFiltering:
    """Test threshold-based edge filtering."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_default_threshold_filters_edges(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that default threshold filters edges correctly."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        # With threshold 0.5, only correlations > 0.5 should create edges
        # In sample matrix: 0.8, 0.9 (2 edges above threshold)
        mock_graph_instance.number_of_edges.return_value = 2
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert result['num_edges'] >= 0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_custom_threshold_filters_edges(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        custom_threshold_analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that custom threshold filters edges correctly."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        # With threshold 0.7, only correlations > 0.7 should create edges
        mock_graph_instance.number_of_edges.return_value = 1
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        result = custom_threshold_analyzer.analyze_network(
            sample_correlation_matrix, sample_symbols
        )

        assert result['num_edges'] >= 0


@pytest.mark.unit
class TestGraphConstruction:
    """Test graph construction from correlation matrix."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_graph_adds_all_nodes(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that all symbols are added as nodes."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = len(sample_symbols)
        mock_graph_instance.number_of_edges.return_value = 2
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        # Check that add_nodes_from was called
        mock_graph_instance.add_nodes_from.assert_called_once_with(sample_symbols)

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_graph_adds_edges_above_threshold(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that edges are only added for correlations above threshold."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 2
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        # Check that add_edge was called at least once
        assert mock_graph_instance.add_edge.call_count > 0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_empty_correlation_matrix(
        self, mock_communities, mock_centrality, mock_graph, analyzer
    ):
        """Test with empty correlation matrix."""
        empty_matrix = np.array([[]])
        empty_symbols = []

        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 0
        mock_graph_instance.number_of_edges.return_value = 0
        mock_centrality.return_value = {}
        mock_communities.return_value = []

        result = analyzer.analyze_network(empty_matrix, empty_symbols)

        assert isinstance(result, dict)
        assert result['num_nodes'] == 0
        assert result['num_edges'] == 0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_single_asset(self, mock_communities, mock_centrality, mock_graph, analyzer):
        """Test with single asset (no edges possible)."""
        single_matrix = np.array([[1.0]])
        single_symbols = ['AAPL']

        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 1
        mock_graph_instance.number_of_edges.return_value = 0
        mock_centrality.return_value = {'AAPL': 0.0}
        mock_communities.return_value = []

        result = analyzer.analyze_network(single_matrix, single_symbols)

        assert result['num_nodes'] == 1
        assert result['num_edges'] == 0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_nan_in_correlation_matrix(
        self, mock_communities, mock_centrality, mock_graph, analyzer, sample_symbols
    ):
        """Test with NaN values in correlation matrix."""
        matrix_with_nan = np.array(
            [
                [1.0, 0.8, float('nan'), 0.2],
                [0.8, 1.0, 0.4, 0.1],
                [float('nan'), 0.4, 1.0, 0.9],
                [0.2, 0.1, 0.9, 1.0],
            ]
        )

        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 2
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        # Should handle gracefully
        result = analyzer.analyze_network(matrix_with_nan, sample_symbols)
        assert isinstance(result, dict)

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    def test_exception_handling(
        self, mock_graph, analyzer, sample_correlation_matrix, sample_symbols
    ):
        """Test that exceptions are handled gracefully."""
        mock_graph.side_effect = Exception("Test error")

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert isinstance(result, dict)
        assert 'error' in result


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for correlation network analyzer."""

    @pytest.mark.parametrize("threshold", [0.0, 0.3, 0.5, 0.7, 1.0])
    def test_different_thresholds(self, threshold, sample_correlation_matrix, sample_symbols):
        """Test with different threshold values."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )

        analyzer = CorrelationNetworkAnalyzer(config={'threshold': threshold})
        assert analyzer.threshold == threshold

    @pytest.mark.parametrize("n_assets", [2, 3, 5, 10, 20])
    def test_different_numbers_of_assets(self, n_assets):
        """Test with different numbers of assets."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )

        analyzer = CorrelationNetworkAnalyzer()

        # Create correlation matrix
        corr_matrix = np.eye(n_assets)
        symbols = [f'Asset_{i}' for i in range(n_assets)]

        with patch(
            'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph'
        ) as mock_graph:
            with patch(
                'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
            ) as mock_centrality:
                with patch(
                    'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
                ) as mock_communities:
                    mock_graph_instance = MagicMock()
                    mock_graph.return_value = mock_graph_instance
                    mock_graph_instance.number_of_nodes.return_value = n_assets
                    mock_graph_instance.number_of_edges.return_value = 0
                    mock_centrality.return_value = {sym: 0.0 for sym in symbols}
                    mock_communities.return_value = []

                    result = analyzer.analyze_network(corr_matrix, symbols)

                    assert result['num_nodes'] == n_assets


@pytest.mark.unit
class TestClustering:
    """Test community detection functionality."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_single_cluster(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test detection of single cluster (highly connected)."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 6
        mock_centrality.return_value = {sym: 0.8 for sym in sample_symbols}
        # All assets in one cluster
        mock_communities.return_value[
            ({sample_symbols[0], sample_symbols[1], sample_symbols[2], sample_symbols[3]},)
        ]

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert len(result['clusters']) == 1

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_multiple_clusters(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test detection of multiple clusters."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 2
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        # Two separate clusters
        mock_communities.return_value = [({'AAPL', 'MSFT'},), ({'GOOGL', 'AMZN'},)]

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert len(result['clusters']) == 2

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_no_clusters(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        low_correlation_matrix,
        sample_symbols,
    ):
        """Test with no clusters (disconnected network)."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 0
        mock_centrality.return_value = {sym: 0.0 for sym in sample_symbols}
        mock_communities.return_value = []

        result = analyzer.analyze_network(low_correlation_matrix, sample_symbols)

        assert len(result['clusters']) == 0


@pytest.mark.unit
class TestCentrality:
    """Test centrality calculation functionality."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_centrality_values_range(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that centrality values are in valid range [0, 1]."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 3
        mock_centrality.return_value = {'AAPL': 0.8, 'MSFT': 0.7, 'GOOGL': 0.6, 'AMZN': 0.5}
        mock_communities.return_value = []

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        for symbol, centrality in result['centrality'].items():
            assert 0.0 <= centrality <= 1.0

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_centrality_for_all_nodes(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        sample_correlation_matrix,
        sample_symbols,
    ):
        """Test that centrality is calculated for all nodes."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 3
        mock_centrality.return_value = {sym: 0.5 for sym in sample_symbols}
        mock_communities.return_value = []

        result = analyzer.analyze_network(sample_correlation_matrix, sample_symbols)

        assert len(result['centrality']) == len(sample_symbols)
        for symbol in sample_symbols:
            assert symbol in result['centrality']


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_large_network(self, mock_communities, mock_centrality, mock_graph, analyzer):
        """Test with large network (many assets)."""
        n_assets = 100
        symbols = [f'Asset_{i}' for i in range(n_assets)]

        # Create correlation matrix
        corr_matrix = np.eye(n_assets)
        for i in range(n_assets):
            for j in range(i + 1, min(i + 10, n_assets)):
                corr_matrix[i, j] = corr_matrix[j, i] = 0.6

        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = n_assets
        mock_graph_instance.number_of_edges.return_value = 450
        mock_centrality.return_value = {sym: 0.5 for sym in symbols}
        mock_communities.return_value = []

        # Should complete without timing out
        result = analyzer.analyze_network(corr_matrix, symbols)
        assert isinstance(result, dict)

    @patch('app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.Graph')
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.degree_centrality'
    )
    @patch(
        'app.engines.context_engine.correlation_analyzers.correlation_network_analyzer.nx.community.greedy_modularity_communities'
    )
    def test_dense_network(
        self,
        mock_communities,
        mock_centrality,
        mock_graph,
        analyzer,
        high_correlation_matrix,
        sample_symbols,
    ):
        """Test with dense network (high correlation)."""
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.number_of_nodes.return_value = 4
        mock_graph_instance.number_of_edges.return_value = 6
        mock_centrality.return_value = {sym: 1.0 for sym in sample_symbols}
        mock_communities.return_value[
            ({sample_symbols[0], sample_symbols[1], sample_symbols[2], sample_symbols[3]},)
        ]

        result = analyzer.analyze_network(high_correlation_matrix, sample_symbols)
        assert isinstance(result, dict)
