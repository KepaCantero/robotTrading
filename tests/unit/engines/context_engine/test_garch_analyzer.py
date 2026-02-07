"""
Unit tests for GARCH Analyzer.

Tests the GARCHAnalyzer class which uses GARCH models
to detect volatility clustering and predict future volatility.
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest


@pytest.fixture
def sample_returns():
    """Generate sample return data for testing."""
    np.random.seed(42)
    # Generate returns with some volatility clustering
    returns = []
    volatility_state = 0.02
    for i in range(200):
        volatility_state = 0.9 * volatility_state + 0.1 * abs(np.random.normal(0, 0.01))
        returns.append(np.random.normal(0.001, volatility_state))
    return returns


@pytest.fixture
def high_volatility_returns():
    """Generate high volatility return data."""
    np.random.seed(123)
    returns = np.random.normal(0, 0.05, 150).tolist()
    return returns


@pytest.fixture
def low_volatility_returns():
    """Generate low volatility return data."""
    np.random.seed(456)
    returns = np.random.normal(0.001, 0.005, 150).tolist()
    return returns


@pytest.fixture
def analyzer():
    """Create a GARCHAnalyzer instance for testing."""
    from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

    return GARCHAnalyzer()


@pytest.fixture
def egarch_analyzer():
    """Create a GARCHAnalyzer with EGARCH model."""
    from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

    return GARCHAnalyzer(config={'model_type': 'EGARCH'})


@pytest.fixture
def gjr_garch_analyzer():
    """Create a GARCHAnalyzer with GJR-GARCH model."""
    from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

    return GARCHAnalyzer(config={'model_type': 'GJR-GARCH'})


@pytest.mark.unit
class TestGARCHAnalyzerInit:
    """Test initialization of GARCHAnalyzer."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer()

        assert analyzer.model_type == 'GARCH'
        assert analyzer.p == 1
        assert analyzer.q == 1
        assert analyzer.dist == 'normal'
        assert analyzer.model is None
        assert analyzer.fitted_model is None

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        config = {'model_type': 'EGARCH', 'p': 2, 'q': 2, 'dist': 't'}
        analyzer = GARCHAnalyzer(config=config)

        assert analyzer.model_type == 'EGARCH'
        assert analyzer.p == 2
        assert analyzer.q == 2
        assert analyzer.dist == 't'

    def test_gjr_garch_initialization(self):
        """Test GJR-GARCH initialization."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer(config={'model_type': 'GJR-GARCH'})

        assert analyzer.model_type == 'GJR-GARCH'


@pytest.mark.unit
class TestFit:
    """Test model fitting functionality."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.GARCHAnalyzer')
    def test_fit_garch_success(self, mock_analyzer, mock_arch_model, analyzer, sample_returns):
        """Test successful GARCH model fitting."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.fit(sample_returns)

        assert result is True
        assert analyzer.fitted_model is not None

    def test_fit_insufficient_data(self, analyzer):
        """Test fitting with insufficient data."""
        short_returns = [0.01] * 50  # Less than 100

        result = analyzer.fit(short_returns)

        assert result is False
        assert analyzer.fitted_model is None

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_fit_egarch(self, mock_arch_model, egarch_analyzer, sample_returns):
        """Test EGARCH model fitting."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = egarch_analyzer.fit(sample_returns)

        assert result is True

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_fit_gjr_garch(self, mock_arch_model, gjr_garch_analyzer, sample_returns):
        """Test GJR-GARCH model fitting."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = gjr_garch_analyzer.fit(sample_returns)

        assert result is True

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_fit_unknown_model_type(self, mock_arch_model, sample_returns):
        """Test fitting with unknown model type (should default to GARCH)."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer(config={'model_type': 'UNKNOWN'})
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.fit(sample_returns)

        assert result is True

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_fit_with_exception(self, mock_arch_model, analyzer, sample_returns):
        """Test fit when arch_model raises an exception."""
        mock_arch_model.side_effect = ValueError("Test error")

        result = analyzer.fit(sample_returns)

        assert result is False


@pytest.mark.unit
class TestPredictVolatility:
    """Test volatility prediction functionality."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_predict_volatility_without_fit(self, mock_arch_model, analyzer):
        """Test prediction without prior fitting."""
        result = analyzer.predict_volatility()

        assert result['volatility'] is None
        assert result['forecast'] is None
        assert result['confidence'] == 0.0

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_predict_volatility_basic(self, mock_arch_model, analyzer, sample_returns):
        """Test basic volatility prediction."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # Mock forecast
        mock_forecast = MagicMock()
        mock_forecast.variance.values = np.array([[0.0004], [0.0005]])
        mock_fit_result.forecast.return_value = mock_forecast

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Fit first
        analyzer.fit(sample_returns)

        # Predict
        result = analyzer.predict_volatility(horizon=1)

        assert 'volatility' in result
        assert 'forecast' in result
        assert 'confidence' in result

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_predict_volatility_with_horizon(self, mock_arch_model, analyzer, sample_returns):
        """Test prediction with different horizons."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        mock_forecast = MagicMock()
        # Mock forecast for horizon 5
        mock_forecast.variance.values = np.array([[0.0004 + i * 0.0001] for i in range(5)])
        mock_fit_result.forecast.return_value = mock_forecast

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)

        result = analyzer.predict_volatility(horizon=5)

        assert result['volatility'] is not None
        assert len(result['forecast']) == 5

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_predict_volatility_with_exception(self, mock_arch_model, analyzer, sample_returns):
        """Test prediction when forecast raises an exception."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_fit_result.forecast.side_effect = ValueError("Test error")
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)

        result = analyzer.predict_volatility()

        assert result['volatility'] is None
        assert result['confidence'] == 0.0


@pytest.mark.unit
class TestDetectClustering:
    """Test volatility clustering detection."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_detect_clustering_without_fit(self, mock_arch_model, analyzer, sample_returns):
        """Test clustering detection without prior fitting (should auto-fit)."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # Mock parameters
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.3, 'beta[1]': 0.65}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.3, 'beta[1]': 0.65}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.detect_clustering(sample_returns)

        assert 'clustering_detected' in result
        assert 'persistence' in result
        assert 'confidence' in result

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_detect_clustering_high_persistence(self, mock_arch_model, analyzer, sample_returns):
        """Test clustering detection with high persistence (clustering present)."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # High persistence: alpha + beta > 0.9
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.4, 'beta[1]': 0.55}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.4, 'beta[1]': 0.55}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)
        result = analyzer.detect_clustering(sample_returns)

        assert result['clustering_detected'] is True
        assert result['persistence'] > 0.9

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_detect_clustering_low_persistence(self, mock_arch_model, analyzer, sample_returns):
        """Test clustering detection with low persistence (no clustering)."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # Low persistence: alpha + beta < 0.9
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.2, 'beta[1]': 0.3}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.2, 'beta[1]': 0.3}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)
        result = analyzer.detect_clustering(sample_returns)

        assert result['clustering_detected'] is False
        assert result['persistence'] < 0.9

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_detect_clustering_confidence_calculation(
        self, mock_arch_model, analyzer, sample_returns
    ):
        """Test confidence calculation in clustering detection."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # Persistence = 0.95, confidence should be min(1.0, 0.95) = 0.95
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.45, 'beta[1]': 0.5}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.45, 'beta[1]': 0.5}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)
        result = analyzer.detect_clustering(sample_returns)

        assert result['confidence'] == min(1.0, result['persistence'])

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_detect_clustering_with_exception(self, mock_arch_model, analyzer, sample_returns):
        """Test clustering detection when exception occurs."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_fit_result.params.side_effect = ValueError("Test error")
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)

        result = analyzer.detect_clustering(sample_returns)

        assert result['clustering_detected'] is False
        assert result['confidence'] == 0.0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_returns(self, analyzer):
        """Test with empty returns."""
        result = analyzer.fit([])

        assert result is False

    def test_single_return(self, analyzer):
        """Test with single return."""
        result = analyzer.fit([0.01])

        assert result is False

    def test_nan_in_returns(self, analyzer):
        """Test with NaN values in returns."""
        returns_with_nan = [0.01, 0.02, float('nan'), 0.03, 0.04]

        # Should handle gracefully
        result = analyzer.fit(returns_with_nan)
        assert isinstance(result, bool)

    def test_inf_in_returns(self, analyzer):
        """Test with infinite values in returns."""
        returns_with_inf = [0.01, 0.02, float('inf'), 0.03, 0.04]

        # Should handle gracefully
        result = analyzer.fit(returns_with_inf)
        assert isinstance(result, bool)

    def test_zero_returns(self, analyzer):
        """Test with all zero returns."""
        zero_returns = [0.0] * 150

        # Should handle gracefully
        result = analyzer.fit(zero_returns)
        assert isinstance(result, bool)

    def test_constant_returns(self, analyzer):
        """Test with constant returns."""
        constant_returns = [0.01] * 150

        # Should handle gracefully
        result = analyzer.fit(constant_returns)
        assert isinstance(result, bool)


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for GARCH analyzer."""

    @pytest.mark.parametrize("model_type", ['GARCH', 'EGARCH', 'GJR-GARCH'])
    def test_different_model_types(self, model_type, sample_returns):
        """Test with different model types."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer(config={'model_type': model_type})

        assert analyzer.model_type == model_type

    @pytest.mark.parametrize("p,q", [(1, 1), (1, 2), (2, 1), (2, 2)])
    def test_different_pq_orders(self, p, q, sample_returns):
        """Test with different p and q orders."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer(config={'p': p, 'q': q})

        assert analyzer.p == p
        assert analyzer.q == q

    @pytest.mark.parametrize("dist", ['normal', 't', 'skewt'])
    def test_different_distributions(self, dist, sample_returns):
        """Test with different error distributions."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer(config={'dist': dist})

        assert analyzer.dist == dist


@pytest.mark.unit
class TestVolatilityLevels:
    """Test with different volatility levels."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_high_volatility_data(self, mock_arch_model, analyzer, high_volatility_returns):
        """Test fitting with high volatility data."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.fit(high_volatility_returns)

        assert isinstance(result, bool)

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_low_volatility_data(self, mock_arch_model, analyzer, low_volatility_returns):
        """Test fitting with low volatility data."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        result = analyzer.fit(low_volatility_returns)

        assert isinstance(result, bool)


@pytest.mark.unit
class TestIntegration:
    """Integration tests for GARCH analyzer."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_full_workflow(self, mock_arch_model, sample_returns):
        """Test complete workflow: fit, predict, detect clustering."""
        from app.engines.context_engine.volatility_analyzers.garch_analyzer import GARCHAnalyzer

        analyzer = GARCHAnalyzer()

        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        # Mock forecast
        mock_forecast = MagicMock()
        mock_forecast.variance.values = np.array([[0.0004]])
        mock_fit_result.forecast.return_value = mock_forecast

        # Mock parameters
        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.3, 'beta[1]': 0.6}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': 0.3, 'beta[1]': 0.6}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Fit
        fit_result = analyzer.fit(sample_returns)
        assert fit_result is True

        # Predict
        predict_result = analyzer.predict_volatility()
        assert predict_result['volatility'] is not None

        # Detect clustering
        clustering_result = analyzer.detect_clustering(sample_returns)
        assert 'clustering_detected' in clustering_result

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_multiple_predictions(self, mock_arch_model, analyzer, sample_returns):
        """Test multiple predictions after single fit."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        mock_forecast = MagicMock()
        mock_forecast.variance.values = np.array([[0.0004]])
        mock_fit_result.forecast.return_value = mock_forecast

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Fit once
        analyzer.fit(sample_returns)

        # Predict multiple times
        for _ in range(5):
            result = analyzer.predict_volatility()
            assert result['volatility'] is not None


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_large_dataset(self, mock_arch_model, analyzer):
        """Test with large dataset."""
        np.random.seed(42)
        large_returns = np.random.normal(0, 0.02, 5000).tolist()

        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Should complete without timing out
        result = analyzer.fit(large_returns)
        assert isinstance(result, bool)

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_extreme_volatility(self, mock_arch_model, analyzer):
        """Test with extreme volatility data."""
        np.random.seed(42)
        extreme_returns = np.random.normal(0, 0.2, 200).tolist()  # 20% daily volatility

        mock_model = MagicMock()
        mock_fit_result = MagicMock()
        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        # Should handle extreme volatility
        result = analyzer.fit(extreme_returns)
        assert isinstance(result, bool)


@pytest.mark.unit
class TestModelParameters:
    """Test model parameter handling."""

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_parameters_included_in_clustering_result(
        self, mock_arch_model, analyzer, sample_returns
    ):
        """Test that parameters are included in clustering detection result."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': 0.3, 'beta[1]': 0.6}.get(x, 0))
        expected_dict = {'alpha[1]': 0.3, 'beta[1]': 0.6}
        mock_params.to_dict.return_value = expected_dict
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)
        result = analyzer.detect_clustering(sample_returns)

        assert 'parameters' in result
        assert isinstance(result['parameters'], dict)

    @patch('app.engines.context_engine.volatility_analyzers.garch_analyzer.arch_model')
    def test_persistence_calculation(self, mock_arch_model, analyzer, sample_returns):
        """Test persistence calculation from parameters."""
        mock_model = MagicMock()
        mock_fit_result = MagicMock()

        alpha = 0.35
        beta = 0.55
        expected_persistence = alpha + beta

        mock_params = MagicMock()
        mock_params.get = Mock(side_effect=lambda x: {'alpha[1]': alpha, 'beta[1]': beta}.get(x, 0))
        mock_params.to_dict.return_value = {'alpha[1]': alpha, 'beta[1]': beta}
        mock_fit_result.params = mock_params

        mock_model.fit.return_value = mock_fit_result
        mock_arch_model.return_value = mock_model

        analyzer.fit(sample_returns)
        result = analyzer.detect_clustering(sample_returns)

        assert abs(result['persistence'] - expected_persistence) < 1e-10
