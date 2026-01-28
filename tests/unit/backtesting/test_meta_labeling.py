"""
Unit tests for Meta-labeling module.

Tests for the meta-labeling implementation based on López de Prado's work.
Meta-labeling separates signal direction from position sizing.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from app.backtesting.labeling.meta_labeling import (
    MetaLabelingConfig,
    MetaLabelingResult,
    MetaLabeling,
    apply_meta_labeling,
    calculate_meta_labels,
    snv_to_signal,
)


@pytest.mark.unit
class TestMetaLabelingConfig:
    """Test cases for MetaLabelingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MetaLabelingConfig()

        assert config.primary_model_type == "rf"
        assert config.meta_model_type == "rf"
        assert config.primary_threshold == 0.5
        assert config.meta_threshold == 0.5
        assert config.bet_sizing_method == "kelly"
        assert config.max_bet_size == 1.0
        assert config.min_bet_size == 0.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MetaLabelingConfig(
            primary_model_type="xgb",
            meta_model_type="logistic",
            kelly_fraction=0.5,
            max_bet_size=0.8,
        )

        assert config.primary_model_type == "xgb"
        assert config.meta_model_type == "logistic"
        assert config.kelly_fraction == 0.5
        assert config.max_bet_size == 0.8

    def test_config_validation_invalid_threshold(self):
        """Test configuration validation with invalid threshold."""
        with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
            MetaLabelingConfig(primary_threshold=1.5)

    def test_config_validation_invalid_bet_size(self):
        """Test configuration validation with invalid bet size."""
        with pytest.raises(ValueError, match="max_bet_size must be between 0 and 1"):
            MetaLabelingConfig(max_bet_size=1.5)

    def test_config_validation_min_exceeds_max(self):
        """Test configuration validation when min exceeds max."""
        with pytest.raises(ValueError, match="min_bet_size must be between 0 and max_bet_size"):
            MetaLabelingConfig(min_bet_size=0.8, max_bet_size=0.5)


@pytest.mark.unit
class TestMetaLabelingResult:
    """Test cases for MetaLabelingResult dataclass."""

    def test_result_creation(self):
        """Test creating a MetaLabelingResult."""
        n_samples = 100
        predictions = np.random.randint(0, 2, n_samples)
        proba = np.random.rand(n_samples)
        bet_sizes = np.random.rand(n_samples) * 0.5

        result = MetaLabelingResult(
            primary_predictions=predictions,
            primary_proba=proba,
            meta_predictions=predictions,
            meta_proba=proba,
            primary_accuracy=0.65,
            meta_accuracy=0.70,
            combined_accuracy=0.68,
            bet_sizes=bet_sizes,
            n_samples=n_samples,
            n_features=5,
        )

        assert result.n_samples == n_samples
        assert result.n_features == 5
        assert result.primary_accuracy == 0.65
        assert result.meta_accuracy == 0.70
        assert len(result.bet_sizes) == n_samples

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        n_samples = 50
        predictions = np.random.randint(0, 2, n_samples)
        proba = np.random.rand(n_samples)
        bet_sizes = np.random.rand(n_samples) * 0.5

        result = MetaLabelingResult(
            primary_predictions=predictions,
            primary_proba=proba,
            meta_predictions=predictions,
            meta_proba=proba,
            primary_accuracy=0.6,
            meta_accuracy=0.65,
            combined_accuracy=0.62,
            bet_sizes=bet_sizes,
            n_samples=n_samples,
            n_features=3,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "primary_predictions" in result_dict
        assert "primary_accuracy" in result_dict
        assert "n_samples" in result_dict
        assert result_dict["n_samples"] == n_samples


@pytest.mark.unit
class TestMetaLabeling:
    """Test cases for MetaLabeling class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 200

        X = np.random.randn(n_samples, 5)
        y = np.random.randint(0, 2, n_samples)

        return X, y

    def test_initialization(self):
        """Test MetaLabeling initialization."""
        meta_labeling = MetaLabeling()

        assert meta_labeling.config is not None
        assert isinstance(meta_labeling.config, MetaLabelingConfig)
        assert meta_labeling._is_fitted is False
        assert meta_labeling.primary_model is None
        assert meta_labeling.meta_model is None

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = MetaLabelingConfig(primary_model_type="xgb")
        meta_labeling = MetaLabeling(config)

        assert meta_labeling.config.primary_model_type == "xgb"

    def test_fit_with_numpy_arrays(self, sample_data):
        """Test fitting with numpy arrays."""
        X, y = sample_data
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )

        meta_labeling.fit(X, y)

        assert meta_labeling._is_fitted is True
        assert meta_labeling.n_features_ == 5
        assert meta_labeling.primary_model is not None
        assert meta_labeling.meta_model is not None

    def test_fit_with_dataframe(self, sample_data):
        """Test fitting with DataFrame input."""
        X, y = sample_data
        X_df = pd.DataFrame(X, columns=["f1", "f2", "f3", "f4", "f5"])
        y_series = pd.Series(y)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )

        meta_labeling.fit(X_df, y_series)

        assert meta_labeling._is_fitted is True

    def test_fit_mismatched_dimensions(self, sample_data):
        """Test fitting with mismatched dimensions."""
        X, y = sample_data
        X_mismatched = np.random.randn(100, 5)  # Different length

        meta_labeling = MetaLabeling()

        with pytest.raises(ValueError, match="must have same length"):
            meta_labeling.fit(X_mismatched, y)

    def test_predict_without_fit_raises_error(self, sample_data):
        """Test that predict raises error if not fitted."""
        X, _ = sample_data
        meta_labeling = MetaLabeling()

        with pytest.raises(ValueError, match="must be fitted"):
            meta_labeling.predict(X)

    def test_predict_after_fit(self, sample_data):
        """Test predict after fitting."""
        X_train, y_train = sample_data[0][:150], sample_data[1][:150]
        X_test = sample_data[0][150:]

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        meta_labeling.fit(X_train, y_train)

        result = meta_labeling.predict(X_test)

        assert isinstance(result, MetaLabelingResult)
        assert result.n_samples == len(X_test)
        assert len(result.primary_predictions) == len(X_test)
        assert len(result.meta_predictions) == len(X_test)
        assert len(result.bet_sizes) == len(X_test)

    def test_fit_predict_workflow(self, sample_data):
        """Test the complete fit_predict workflow."""
        X_train, y_train = sample_data[0][:150], sample_data[1][:150]
        X_test = sample_data[0][150:]
        y_test = sample_data[1][150:]

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )

        result = meta_labeling.fit_predict(X_train, y_train, X_test, y_test)

        assert isinstance(result, MetaLabelingResult)
        assert result.n_samples == len(X_test)
        assert result.primary_predictions is not None
        assert result.meta_predictions is not None

    def test_create_model_rf(self):
        """Test creating RandomForest model."""
        meta_labeling = MetaLabeling()
        model = meta_labeling._create_model("rf")

        assert model is not None
        assert hasattr(model, "fit")
        assert hasattr(model, "predict")

    def test_create_model_xgb_with_fallback(self):
        """Test creating XGBoost model with fallback."""
        meta_labeling = MetaLabeling()

        # Mock XGBoost import error
        with patch("app.backtesting.labeling.meta_labeling.XGBClassifier", side_effect=ImportError):
            model = meta_labeling._create_model("xgb")
            # Should fallback to RandomForest
            assert model is not None

    def test_create_model_unknown_type(self):
        """Test creating model with unknown type."""
        meta_labeling = MetaLabeling()

        with pytest.raises(ValueError, match="Unknown model type"):
            meta_labeling._create_model("unknown_model")

    def test_get_proba_with_predict_proba(self, sample_data):
        """Test _get_proba with model that has predict_proba."""
        X, y = sample_data
        meta_labeling = MetaLabeling()
        meta_labeling.fit(X[:50], y[:50])

        # Model should have predict_proba
        proba = meta_labeling._get_proba(meta_labeling.primary_model, X[:10])

        assert isinstance(proba, np.ndarray)
        assert len(proba) == 10
        assert all((p >= 0) & (p <= 1) for p in proba)

    def test_calculate_bet_sizes_kelly(self):
        """Test bet size calculation with Kelly method."""
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(bet_sizing_method="kelly")
        )

        meta_proba = np.array([0.6, 0.7, 0.8, 0.4, 0.9])
        bet_sizes = meta_labeling._calculate_bet_sizes(meta_proba)

        # Kelly: f = 2p - 1
        expected = np.array([0.2, 0.4, 0.6, 0.0, 0.8])

        np.testing.assert_allclose(bet_sizes, expected, atol=1e-5)

    def test_calculate_bet_sizes_probability(self):
        """Test bet size calculation with probability method."""
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(bet_sizing_method="probability")
        )

        meta_proba = np.array([0.6, 0.7, 0.8, 0.4, 0.9])
        bet_sizes = meta_labeling._calculate_bet_sizes(meta_proba)

        # Should use probability directly
        expected = meta_proba.copy()

        np.testing.assert_allclose(bet_sizes, expected, atol=1e-5)

    def test_calculate_bet_sizes_fixed(self):
        """Test bet size calculation with fixed method."""
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(bet_sizing_method="fixed")
        )

        meta_proba = np.array([0.6, 0.7, 0.8, 0.4, 0.9])
        bet_sizes = meta_labeling._calculate_bet_sizes(meta_proba)

        # Should be binary based on threshold
        assert all(b in [0.0, 1.0] for b in bet_sizes)

    def test_calculate_bet_size_clipping(self):
        """Test that bet sizes are clipped to bounds."""
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(
                bet_sizing_method="kelly",
                min_bet_size=0.1,
                max_bet_size=0.5
            )
        )

        meta_proba = np.array([0.9, 0.99])  # Would give > 0.5 with Kelly
        bet_sizes = meta_labeling._calculate_bet_sizes(meta_proba)

        # Should be clipped to max_bet_size
        assert all(b <= 0.5 for b in bet_sizes if b > 0)

    def test_calculate_bet_sizes_unknown_method(self):
        """Test bet size calculation with unknown method."""
        # Temporarily change the method to something invalid
        meta_labeling = MetaLabeling()
        meta_labeling.config.bet_sizing_method = "unknown"

        with pytest.raises(ValueError, match="Unknown bet sizing method"):
            meta_labeling._calculate_bet_sizes(np.array([0.6, 0.7]))


@pytest.mark.unit
class TestApplyMetaLabeling:
    """Test cases for apply_meta_labeling convenience function."""

    def test_convenience_function(self):
        """Test the convenience function."""
        np.random.seed(42)

        X_train = np.random.randn(100, 3)
        y_train = np.random.randint(0, 2, 100)
        X_test = np.random.randn(50, 3)
        y_test = np.random.randint(0, 2, 50)

        result = apply_meta_labeling(X_train, y_train, X_test, y_test)

        assert isinstance(result, MetaLabelingResult)
        assert result.n_samples == 50


@pytest.mark.unit
class TestCalculateMetaLabels:
    """Test cases for calculate_meta_labels function."""

    def test_calculate_meta_labels_basic(self):
        """Test basic meta-label calculation."""
        primary_predictions = np.array([1, -1, 1, 1, -1])
        actual_returns = np.array([0.02, -0.01, 0.015, -0.005, -0.02])

        meta_labels = calculate_meta_labels(primary_predictions, actual_returns)

        # Meta-label is 1 if prediction was correct and profitable
        expected = np.array([1, 1, 1, 0, 1])
        np.testing.assert_array_equal(meta_labels, expected)

    def test_calculate_meta_labels_with_threshold(self):
        """Test meta-label calculation with threshold."""
        primary_predictions = np.array([1, 1, -1])
        actual_returns = np.array([0.005, 0.02, -0.005])  # 0.005 is below threshold

        meta_labels = calculate_meta_labels(
            primary_predictions, actual_returns, threshold=0.01
        )

        # Only 0.02 exceeds threshold
        expected = np.array([0, 1, 0])
        np.testing.assert_array_equal(meta_labels, expected)

    def test_calculate_meta_labels_wrong_prediction(self):
        """Test meta-label when prediction was wrong."""
        primary_predictions = np.array([1, 1, -1])
        actual_returns = np.array([-0.02, -0.01, 0.02])  # All wrong

        meta_labels = calculate_meta_labels(primary_predictions, actual_returns)

        # All should be 0 (wrong predictions)
        expected = np.array([0, 0, 0])
        np.testing.assert_array_equal(meta_labels, expected)


@pytest.mark.unit
class TestSnvToSignal:
    """Test cases for snv_to_signal function."""

    def test_snv_to_signal_basic(self):
        """Test basic signal conversion."""
        side = np.array([1, -1, 0, 1, -1])
        meta_labels = np.array([1, 0, 1, 1, 0])

        signals = snv_to_signal(side, meta_labels)

        expected = np.array([1, 0, 0, 1, 0])
        np.testing.assert_array_equal(signals, expected)

    def test_snv_to_signal_all_meta_zero(self):
        """Test when all meta-labels are zero."""
        side = np.array([1, -1, 1, -1])
        meta_labels = np.array([0, 0, 0, 0])

        signals = snv_to_signal(side, meta_labels)

        # All signals should be zero
        expected = np.array([0, 0, 0, 0])
        np.testing.assert_array_equal(signals, expected)

    def test_snv_to_signal_all_meta_one(self):
        """Test when all meta-labels are one."""
        side = np.array([1, -1, 0, 1])
        meta_labels = np.array([1, 1, 1, 1])

        signals = snv_to_signal(side, meta_labels)

        # Should equal side
        np.testing.assert_array_equal(signals, side)


@pytest.mark.unit
class TestMetaLabelingEdgeCases:
    """Test edge cases for meta-labeling."""

    def test_empty_data(self):
        """Test with empty data."""
        meta_labeling = MetaLabeling()

        X = np.array([]).reshape(0, 5)
        y = np.array([])

        # Should handle gracefully or raise appropriate error
        try:
            meta_labeling.fit(X, y)
            assert False, "Should have raised an error"
        except (ValueError, IndexError):
            pass  # Expected

    def test_single_sample(self):
        """Test with single sample."""
        meta_labeling = MetaLabeling()

        X = np.random.randn(1, 5)
        y = np.array([1])

        # Should handle gracefully
        try:
            meta_labeling.fit(X, y)
            # Some models may fail with single sample
        except ValueError:
            pass  # Expected for some models

    def test_single_feature(self):
        """Test with single feature."""
        X = np.random.randn(100, 1)
        y = np.random.randint(0, 2, 100)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        meta_labeling.fit(X, y)

        assert meta_labeling._is_fitted is True

    def test_imbalanced_labels(self):
        """Test with highly imbalanced labels."""
        X = np.random.randn(200, 5)
        y = np.array([0] * 190 + [1] * 10)  # 95% zeros

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        meta_labeling.fit(X, y)

        assert meta_labeling._is_fitted is True


@pytest.mark.unit
class TestMetaLabelingIntegration:
    """Integration tests for meta-labeling."""

    def test_complete_workflow(self):
        """Test complete meta-labeling workflow."""
        # Generate synthetic data
        np.random.seed(42)
        n_train, n_test = 500, 200

        X_train = np.random.randn(n_train, 10)
        y_train = np.random.randint(0, 2, n_train)
        X_test = np.random.randn(n_test, 10)
        y_test = np.random.randint(0, 2, n_test)

        # Fit meta-labeling
        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        result = meta_labeling.fit_predict(X_train, y_train, X_test, y_test)

        # Verify result structure
        assert isinstance(result, MetaLabelingResult)
        assert len(result.primary_predictions) == n_test
        assert len(result.meta_predictions) == n_test
        assert len(result.bet_sizes) == n_test
        assert result.primary_accuracy >= 0
        assert result.primary_accuracy <= 1

    def test_bet_sizing_distribution(self):
        """Test bet sizing distribution properties."""
        np.random.seed(42)
        X = np.random.randn(300, 5)
        y = np.random.randint(0, 2, 300)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        meta_labeling.fit(X, y)

        result = meta_labeling.predict(X[:50])

        # Bet sizes should be in [0, max_bet_size]
        assert all(result.bet_sizes >= 0)
        assert all(result.bet_sizes <= meta_labeling.config.max_bet_size)

        # Some bet sizes should be zero (below threshold)
        assert (result.bet_sizes == 0).sum() > 0

    def test_meta_predictions_filter_primary(self):
        """Test that meta-labels act as filter on primary predictions."""
        np.random.seed(42)
        X = np.random.randn(300, 5)
        y = np.random.randint(0, 2, 300)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )
        result = meta_labeling.fit_predict(X[:200], y[:200], X[200:], y[200:])

        # When meta says no (0), we should skip the trade
        # Verify combined accuracy is calculated correctly
        mask = result.meta_predictions == 1
        if mask.sum() > 0:
            combined_acc = np.mean(
                result.primary_predictions[mask] == y[200:][mask]
            )
            assert result.combined_accuracy == combined_acc


@pytest.mark.unit
class TestMetaLabelingPerformance:
    """Performance tests for meta-labeling."""

    @pytest.mark.parametrize("n_samples", [100, 500, 1000])
    def test_scalability(self, n_samples):
        """Test meta-labeling with different sample sizes."""
        X = np.random.randn(n_samples, 10)
        y = np.random.randint(0, 2, n_samples)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )

        # Should complete without error
        meta_labeling.fit(X, y)
        assert meta_labeling._is_fitted is True

    @pytest.mark.parametrize("n_features", [5, 10, 20])
    def test_varying_features(self, n_features):
        """Test with different numbers of features."""
        X = np.random.randn(200, n_features)
        y = np.random.randint(0, 2, 200)

        meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(compute_importance=False)
        )

        meta_labeling.fit(X, y)
        assert meta_labeling.n_features_ == n_features
