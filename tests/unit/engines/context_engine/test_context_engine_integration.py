"""
Integration tests for Context Engine modules.

Tests the integration between different context engine components
including regime detectors, correlation analyzers, and volatility analyzers.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def multi_asset_sample_data():
    """Generate sample multi-asset price data for integration testing."""
    np.random.seed(42)

    # Create correlated price data for 5 assets over 300 days
    n_days = 300
    base_returns = np.random.normal(0.001, 0.02, n_days)

    # Simulate regime changes
    regime_returns = base_returns.copy()
    regime_returns[100:200] *= 0.5  # Lower volatility regime
    regime_returns[200:] *= 1.5  # Higher volatility regime

    price_data = {
        'AAPL': [100.0],
        'MSFT': [100.0],
        'GOOGL': [100.0],
        'AMZN': [100.0],
        'TSLA': [100.0],
    }

    correlations = {
        'AAPL': 0.8,  # High correlation with market
        'MSFT': 0.75,
        'GOOGL': 0.7,
        'AMZN': 0.6,
        'TSLA': 0.4,  # Lower correlation
    }

    for i, ret in enumerate(regime_returns):
        for symbol, corr in correlations.items():
            noise = np.random.normal(0, 0.01)
            price_data[symbol].append(price_data[symbol][-1] * (1 + corr * ret + noise))

    return price_data


@pytest.fixture
def bull_market_data():
    """Generate bull market data."""
    np.random.seed(123)
    n_days = 200

    price_data = {'SPY': [100.0], 'QQQ': [100.0]}

    for i in range(n_days):
        # Strong upward trend
        trend = 0.002 + (i / n_days) * 0.003  # Increasing trend
        noise = np.random.normal(0, 0.015)

        for symbol in price_data:
            price_data[symbol].append(price_data[symbol][-1] * (1 + trend + noise))

    return price_data


@pytest.fixture
def bear_market_data():
    """Generate bear market data."""
    np.random.seed(456)
    n_days = 200

    price_data = {'SPY': [100.0], 'QQQ': [100.0]}

    for i in range(n_days):
        # Downward trend with high volatility
        trend = -0.002
        noise = np.random.normal(0, 0.025)

        for symbol in price_data:
            price_data[symbol].append(price_data[symbol][-1] * (1 + trend + noise))

    return price_data


@pytest.fixture
def sideways_market_data():
    """Generate sideways/range-bound market data."""
    np.random.seed(789)
    n_days = 200

    price_data = {'SPY': [100.0], 'QQQ': [100.0]}

    for i in range(n_days):
        # No clear trend, range-bound
        mean_reversion = -0.0001 * (i % 50 - 25) / 25  # Mean-reverting
        noise = np.random.normal(0, 0.012)

        for symbol in price_data:
            price_data[symbol].append(price_data[symbol][-1] * (1 + mean_reversion + noise))

    return price_data


@pytest.mark.unit
class TestClusteringRegimeDetectorIntegration:
    """Integration tests for ClusteringRegimeDetector."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_clustering_detector_with_different_markets(self, mock_kmeans):
        """Test clustering detector across different market conditions."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])  # Bull
        mock_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_model

        detector = ClusteringRegimeDetector()

        # Test with bull market
        bull_prices = bull_market_data()['SPY']
        bull_result = detector.detect(bull_prices)
        assert isinstance(bull_result, dict)

        # Test with bear market
        mock_model.predict.return_value = np.array([0])  # Bear
        bear_prices = bear_market_data()['SPY']
        bear_result = detector.detect(bear_prices)
        assert isinstance(bear_result, dict)

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_clustering_detector_feature_extraction_consistency(self, mock_kmeans):
        """Test that feature extraction is consistent across similar data."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector()

        # Generate similar price series
        np.random.seed(42)
        prices1 = [100.0]
        prices2 = [100.0]

        for _ in range(100):
            ret = np.random.normal(0.001, 0.02)
            prices1.append(prices1[-1] * (1 + ret))
            prices2.append(prices2[-1] * (1 + ret))

        features1 = detector._extract_features(prices1)
        features2 = detector._extract_features(prices2)

        # Features should be identical for identical data
        assert np.allclose(features1, features2)


@pytest.mark.unit
class TestCorrelationRegimeDetectorIntegration:
    """Integration tests for CorrelationRegimeDetector."""

    def test_correlation_detector_with_market_regimes(self, multi_asset_sample_data):
        """Test correlation detector across different market regimes."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector()

        # Test overall detection
        result = detector.detect(multi_asset_sample_data)

        assert 'correlation_regime' in result
        assert 'average_correlation' in result
        assert 'pca_variance' in result

    def test_correlation_detector_baseline_functionality(self, multi_asset_sample_data):
        """Test baseline setting and comparison."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector()

        # Set baseline with first half of data
        first_half = {
            symbol: prices[: len(prices) // 2] for symbol, prices in multi_asset_sample_data.items()
        }
        detector.set_baseline(first_half)

        # Detect with second half
        second_half = {
            symbol: prices[len(prices) // 2 :] for symbol, prices in multi_asset_sample_data.items()
        }
        result = detector.detect(second_half)

        assert 'baseline_comparison' in result

    def test_correlation_detector_with_high_correlation_assets(self, bull_market_data):
        """Test with highly correlated assets (ETFs)."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'correlation_threshold': 0.8})

        result = detector.detect(bull_market_data)

        # ETFs should be highly correlated
        assert result['average_correlation'] > 0.5


@pytest.mark.unit
class TestHMMRegimeDetectorIntegration:
    """Integration tests for HMMRegimeDetector."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_hmm_detector_regime_classification(self, mock_hmm):
        """Test HMM detector regime classification."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2, 2, 1, 1, 0])
        mock_model.score_samples.return_value = (
            np.array([-1.0, -2.0, -3.0, -4.0, -5.0]),
            np.array([[0.1, 0.2, 0.7]]),
        )
        mock_model.transmat_ = np.eye(3)
        mock_model.means_ = np.zeros((3, 2))
        mock_hmm.return_value = mock_model

        detector = HMMRegimeDetector()

        # Test with bull market
        bull_prices = bull_market_data()['SPY']
        result = detector.detect(bull_prices)

        assert 'regime' in result
        assert 'regime_probabilities' in result
        assert len(result['regime_probabilities']) == 3

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_hmm_detector_volatility_calculation(self, mock_hmm):
        """Test HMM volatility calculation."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector()

        # Generate returns
        prices = [100.0]
        for _ in range(100):
            prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.02)))

        returns = np.diff(prices) / prices[:-1]
        volatility = detector._calculate_rolling_volatility(returns)

        assert len(volatility) == len(returns)
        assert np.all(volatility >= 0)


@pytest.mark.unit
class TestCorrelationNetworkAnalyzerIntegration:
    """Integration tests for CorrelationNetworkAnalyzer."""

    def test_network_analyzer_with_multi_asset_data(self, multi_asset_sample_data):
        """Test network analysis with multiple assets."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )
        from app.engines.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        # First get correlation matrix
        corr_detector = CorrelationRegimeDetector()
        result = corr_detector.detect(multi_asset_sample_data)

        # Then analyze network
        network_analyzer = CorrelationNetworkAnalyzer(config={'threshold': 0.5})

        symbols = list(multi_asset_sample_data.keys())
        corr_matrix = np.array(result['correlation_matrix'])

        network_result = network_analyzer.analyze_network(corr_matrix, symbols)

        assert 'centrality' in network_result
        assert 'clusters' in network_result
        assert 'num_nodes' in network_result
        assert network_result['num_nodes'] == len(symbols)

    def test_network_analyzer_cluster_detection(self, multi_asset_sample_data):
        """Test cluster detection in network analysis."""
        from app.engines.context_engine.correlation_analyzers.correlation_network_analyzer import (
            CorrelationNetworkAnalyzer,
        )
        from app.engines.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        corr_detector = CorrelationRegimeDetector()
        result = corr_detector.detect(multi_asset_sample_data)

        network_analyzer = CorrelationNetworkAnalyzer(config={'threshold': 0.6})

        symbols = list(multi_asset_sample_data.keys())
        corr_matrix = np.array(result['correlation_matrix'])

        network_result = network_analyzer.analyze_network(corr_matrix, symbols)

        # Check that clusters were detected
        assert isinstance(network_result['clusters'], list)


@pytest.mark.unit
class TestGARCHAnalyzerIntegration:
    """Integration tests for GARCHAnalyzer."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_garch_clustering_detection(self, mock_arch_model):
        """Test GARCH clustering detection across market conditions."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer()

        # Generate returns with volatility clustering
        np.random.seed(42)
        returns = []
        vol_state = 0.01
        for i in range(200):
            vol_state = 0.9 * vol_state + 0.1 * abs(np.random.normal(0, 0.005))
            returns.append(np.random.normal(0.001, vol_state))

        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.3, 'beta[1]': 0.6}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.3, 'beta[1]': 0.6}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.detect_clustering(returns)

        assert 'clustering_detected' in result
        assert 'persistence' in result

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_garch_prediction_workflow(self, mock_arch_model):
        """Test complete GARCH prediction workflow."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer()

        # Generate returns
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 200).tolist()

        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        mock_forecast = MagicMock()
        mock_forecast.variance.values = np.array([[0.0004], [0.0005], [0.0006]])
        mock_fit_result.forecast.return_value = mock_forecast

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Fit
        fit_result = analyzer.fit(returns)
        assert fit_result is True

        # Predict with different horizons
        for horizon in [1, 3, 5]:
            pred_result = analyzer.predict_volatility(horizon=horizon)
            assert pred_result['volatility'] is not None


@pytest.mark.unit
class TestStructuralChangeDetectorIntegration:
    """Integration tests for StructuralChangeDetector."""

    @patch(
        'app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid'
    )
    def test_structural_change_detection_methods(self, mock_cusum):
        """Test both CUSUM and Chow test methods."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import (
            StructuralChangeDetector,
        )

        # Mock CUSUM
        mock_cusum.return_value = (5.5, 0.03, 4.8)

        # Generate prices with structural change
        prices = [100.0]
        for i in range(100):
            prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.015)))
        for i in range(100):
            prices.append(prices[-1] * (1 + np.random.normal(-0.002, 0.03)))

        # Test CUSUM
        cusum_detector = StructuralChangeDetector(config={'method': 'cusum'})
        cusum_result = cusum_detector.detect(prices)
        assert 'change_detected' in cusum_result

        # Test Chow
        chow_detector = StructuralChangeDetector(config={'method': 'chow'})
        chow_result = chow_detector.detect(prices)
        assert 'change_detected' in chow_result

    @patch(
        'app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid'
    )
    def test_structural_change_across_market_regimes(self, mock_cusum):
        """Test structural change detection across different market regimes."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import (
            StructuralChangeDetector,
        )

        mock_cusum.return_value = (6.0, 0.01, 4.8)

        detector = StructuralChangeDetector(config={'method': 'cusum'})

        # Test with bull to bear transition
        bull_prices = bull_market_data()['SPY']
        bear_prices = bear_market_data()['SPY']
        transition_prices = bull_prices + bear_prices

        result = detector.detect(transition_prices)

        assert 'change_detected' in result
        assert 'confidence' in result


@pytest.mark.unit
class TestCrossModuleIntegration:
    """Test integration between different context engine modules."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_regime_and_volatility_integration(self, mock_arch, mock_kmeans):
        """Test integration between regime detection and volatility analysis."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_model

        mock_fit_result = MagicMock()
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.3, 'beta[1]': 0.6}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.3, 'beta[1]': 0.6}
        mock_fit_result.params = mock_params
        mock_model.fit.return_value = mock_fit_result
        mock_arch.return_value = mock_model

        # Generate prices
        np.random.seed(42)
        prices = [100.0]
        for _ in range(200):
            prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.02)))

        # Detect regime
        regime_detector = ClusteringRegimeDetector()
        regime_result = regime_detector.detect(prices)

        # Analyze volatility
        returns = np.diff(prices) / prices[:-1].tolist()
        vol_analyzer = GARCHAnalyzer()
        vol_analyzer.fit(returns)
        vol_result = vol_analyzer.detect_clustering(returns)

        # Both should return results
        assert isinstance(regime_result, dict)
        assert isinstance(vol_result, dict)

    @patch(
        'app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid'
    )
    def test_correlation_and_structural_change_integration(
        self, mock_cusum, multi_asset_sample_data
    ):
        """Test integration between correlation analysis and structural change detection."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import (
            StructuralChangeDetector,
        )

        mock_cusum.return_value = (5.5, 0.03, 4.8)

        # Analyze correlations
        corr_detector = CorrelationRegimeDetector()
        corr_result = corr_detector.detect(multi_asset_sample_data)

        # Detect structural changes in one asset
        prices = multi_asset_sample_data['AAPL']
        change_detector = StructuralChangeDetector()
        change_result = change_detector.detect(prices)

        # Both should return results
        assert isinstance(corr_result, dict)
        assert isinstance(change_result, dict)


@pytest.mark.unit
class TestPerformanceIntegration:
    """Performance tests for integrated context engine workflows."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_multiple_detectors_on_same_data(self, mock_hmm, mock_kmeans):
        """Test running multiple detectors on the same data."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        mock_clustering_model = MagicMock()
        mock_clustering_model.predict.return_value = np.array([1])
        mock_clustering_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_clustering_model

        mock_hmm_model = MagicMock()
        mock_hmm_model.predict.return_value = np.array([1])
        mock_hmm_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.1, 0.7, 0.2]]))
        mock_hmm.return_value = mock_hmm_model

        # Generate prices
        np.random.seed(42)
        prices = [100.0]
        for _ in range(200):
            prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.02)))

        # Run both detectors
        clustering_detector = ClusteringRegimeDetector()
        hmm_detector = HMMRegimeDetector()

        clustering_result = clustering_detector.detect(prices)
        hmm_result = hmm_detector.detect(prices)

        # Both should complete successfully
        assert isinstance(clustering_result, dict)
        assert isinstance(hmm_result, dict)
