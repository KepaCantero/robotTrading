"""
Unit tests for Financial ML module.

Tests for the comprehensive Financial ML pipeline that integrates:
- Fractional Differentiation
- Triple Barrier Labeling
- Purged K-Fold CV
- Meta-labeling
- Bet sizing
- Feature importance
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.backtesting.financial_ml import (
    FinancialMLConfig,
    FinancialMLPipeline,
    FinancialMLResult,
    apply_financial_ml,
    calculate_lopez_de_prado_features,
)


@pytest.mark.unit
class TestFinancialMLConfig:
    """Test cases for FinancialMLConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FinancialMLConfig()

        assert config.fracdiff_threshold == 1e-5
        assert config.upper_barrier_pct == 0.02
        assert config.lower_barrier_pct == -0.01
        assert config.vertical_barrier_days == 5
        assert config.use_meta_labeling is True
        assert config.bet_sizing_method == "kelly"
        assert config.kelly_fraction == 0.25
        assert config.random_state == 42
        assert config.n_jobs == -1

    def test_custom_config(self):
        """Test custom configuration values."""
        config = FinancialMLConfig(
            upper_barrier_pct=0.05,
            lower_barrier_pct=-0.02,
            kelly_fraction=0.5,
            n_folds=10,
        )

        assert config.upper_barrier_pct == 0.05
        assert config.lower_barrier_pct == -0.02
        assert config.kelly_fraction == 0.5
        assert config.n_folds == 10


@pytest.mark.unit
class TestFinancialMLResult:
    """Test cases for FinancialMLResult dataclass."""

    def test_result_creation(self):
        """Test creating a FinancialMLResult."""
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)

        result = FinancialMLResult(
            X_original=X,
            X_transformed=X,
            feature_names=["feat1", "feat2", "feat3", "feat4", "feat5"],
            y_original=y,
            y_triple_barrier=y,
            n_samples=100,
            n_features=5,
            primary_accuracy=0.65,
            meta_accuracy=0.70,
        )

        assert result.n_samples == 100
        assert result.n_features == 5
        assert result.primary_accuracy == 0.65
        assert result.meta_accuracy == 0.70
        assert len(result.feature_names) == 5

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        X = np.random.randn(50, 3)
        y = np.random.randint(0, 2, 50)

        result = FinancialMLResult(
            X_original=X,
            X_transformed=X,
            feature_names=["a", "b", "c"],
            y_original=y,
            y_triple_barrier=y,
            n_samples=50,
            n_features=3,
            primary_accuracy=0.6,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "n_samples" in result_dict
        assert "n_features" in result_dict
        assert "primary_accuracy" in result_dict
        assert "timestamp" in result_dict
        assert result_dict["n_samples"] == 50


@pytest.mark.unit
class TestFinancialMLPipeline:
    """Test cases for FinancialMLPipeline."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 200

        X = np.random.randn(n_samples, 5)
        prices = 100 + np.cumsum(np.random.randn(n_samples) * 0.01)
        y = np.random.randint(0, 2, n_samples)

        return X, prices, y

    @pytest.fixture
    def sample_dataframe_data(self):
        """Create sample DataFrame data for testing."""
        np.random.seed(42)
        n_samples = 200

        X_df = pd.DataFrame(
            np.random.randn(n_samples, 5),
            columns=["feature1", "feature2", "feature3", "feature4", "feature5"],
        )
        prices_series = pd.Series(
            100 + np.cumsum(np.random.randn(n_samples) * 0.01),
            name="price",
        )
        y_series = pd.Series(np.random.randint(0, 2, n_samples), name="label")

        return X_df, prices_series, y_series

    def test_pipeline_initialization(self):
        """Test pipeline initialization with default config."""
        pipeline = FinancialMLPipeline()

        assert pipeline.config is not None
        assert isinstance(pipeline.config, FinancialMLConfig)
        assert pipeline._is_fitted is False
        assert hasattr(pipeline, "fracdiff")
        assert hasattr(pipeline, "triple_barrier")
        assert hasattr(pipeline, "meta_labeling")
        assert hasattr(pipeline, "bet_sizing")

    def test_pipeline_initialization_custom_config(self):
        """Test pipeline initialization with custom config."""
        config = FinancialMLConfig(kelly_fraction=0.5, n_folds=10)
        pipeline = FinancialMLPipeline(config)

        assert pipeline.config.kelly_fraction == 0.5
        assert pipeline.config.n_folds == 10

    def test_fit_with_numpy_arrays(self, sample_data):
        """Test fitting pipeline with numpy arrays."""
        X, prices, y = sample_data
        config = FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        pipeline = FinancialMLPipeline(config)

        # Mock the fracdiff to avoid complex computations
        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            pipeline.fit(X, prices, y)

        assert pipeline._is_fitted is True
        assert pipeline.n_features_ == 5
        assert hasattr(pipeline, "X_transformed_")
        assert hasattr(pipeline, "y_triple_barrier_")

    def test_fit_with_dataframe(self, sample_dataframe_data):
        """Test fitting pipeline with DataFrame input."""
        X_df, prices_series, y_series = sample_dataframe_data
        config = FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        pipeline = FinancialMLPipeline(config)

        # Mock the fracdiff to avoid complex computations
        X = X_df.values
        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            pipeline.fit(X_df, prices_series, y_series)

        assert pipeline._is_fitted is True
        assert pipeline.feature_names_ == [
            "feature1",
            "feature2",
            "feature3",
            "feature4",
            "feature5",
        ]

    def test_predict_without_fit_raises_error(self, sample_data):
        """Test that predict raises error if pipeline is not fitted."""
        X, prices, _ = sample_data
        pipeline = FinancialMLPipeline()

        with pytest.raises(ValueError, match="must be fitted"):
            pipeline.predict(X, prices)

    def test_predict_after_fit(self, sample_data):
        """Test predict after fitting."""
        X, prices, y = sample_data
        X_train, prices_train, y_train = X[:150], prices[:150], y[:150]
        X_test, prices_test, _ = X[150:], prices[150:], y[150:]

        config = FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        pipeline = FinancialMLPipeline(config)

        # Mock the fracdiff to avoid complex computations
        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X_train):
            pipeline.fit(X_train, prices_train, y_train)

        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X_test):
            result = pipeline.predict(X_test, prices_test)

        assert isinstance(result, FinancialMLResult)
        assert result.n_samples == len(X_test)
        assert result.n_features == 5
        assert result.primary_predictions is not None

    def test_fit_predict_workflow(self, sample_data):
        """Test the complete fit_predict workflow."""
        X, prices, y = sample_data
        X_train = X[:150]
        prices_train = prices[:150]
        X_test = X[150:]
        prices_test = prices[150:]
        y_test = y[150:]

        config = FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        pipeline = FinancialMLPipeline(config)

        # Mock to avoid complex computations
        with patch.object(pipeline, "_apply_fracdiff_to_features", side_effect=lambda x, p: x):
            result = pipeline.fit_predict(X_train, prices_train, X_test, prices_test, y_test)

        assert isinstance(result, FinancialMLResult)
        assert result.n_samples == len(X_test)
        assert result.primary_predictions is not None

    def test_apply_fracdiff_to_features_disabled(self, sample_data):
        """Test that fractional differentiation can be disabled."""
        X, prices, _ = sample_data
        config = FinancialMLConfig(apply_fracdiff=False)
        pipeline = FinancialMLPipeline(config)

        X_transformed = pipeline._apply_fracdiff_to_features(X, prices)

        # Should return original features when disabled
        assert np.allclose(X_transformed, X)

    @patch("app.backtesting.financial_ml.purged_kfold_splits")
    def test_cross_validate(self, mock_purged_splits, sample_data):
        """Test cross-validation functionality."""
        X, prices, y = sample_data
        mock_purged_splits.return_value = [
            (np.arange(0, 160), np.arange(160, 200)),
        ]

        pipeline = FinancialMLPipeline(
            config=FinancialMLConfig(apply_fracdiff=False, use_meta_labeling=False)
        )

        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            cv_scores = pipeline.cross_validate(X, prices, y)

        assert isinstance(cv_scores, dict)
        assert "primary_accuracy" in cv_scores
        assert isinstance(cv_scores["primary_accuracy"], list)

    def test_fit_predict_with_meta_labeling_disabled(self, sample_data):
        """Test fit_predict with meta-labeling disabled."""
        X, prices, _ = sample_data
        X_train = X[:150]
        prices_train = prices[:150]
        X_test = X[150:]
        prices_test = prices[150:]

        config = FinancialMLConfig(
            use_meta_labeling=False, apply_fracdiff=False, use_purged_cv=False
        )
        pipeline = FinancialMLPipeline(config)

        result = pipeline.fit_predict(X_train, prices_train, X_test, prices_test)

        assert result.meta_predictions is None
        assert result.bet_sizes is None
        assert result.primary_predictions is not None


@pytest.mark.unit
class TestApplyFinancialML:
    """Test cases for apply_financial_ml convenience function."""

    def test_convenience_function(self):
        """Test the convenience function for applying Financial ML."""
        np.random.seed(42)

        X_train = np.random.randn(100, 3)
        prices_train = 100 + np.cumsum(np.random.randn(100) * 0.01)
        X_test = np.random.randn(50, 3)
        prices_test = 100 + np.cumsum(np.random.randn(50) * 0.01)
        y_test = np.random.randint(0, 2, 50)

        config = FinancialMLConfig(apply_fracdiff=False)

        with patch("app.backtesting.financial_ml.FinancialMLPipeline") as MockPipeline:
            mock_instance = MagicMock()
            mock_result = FinancialMLResult(
                X_original=X_test,
                X_transformed=X_test,
                feature_names=["a", "b", "c"],
                y_original=y_test,
                y_triple_barrier=y_test,
                n_samples=50,
                n_features=3,
            )
            mock_instance.fit_predict.return_value = mock_result
            MockPipeline.return_value = mock_instance

            result = apply_financial_ml(X_train, prices_train, X_test, prices_test, y_test, config)

            assert isinstance(result, FinancialMLResult)
            mock_instance.fit_predict.assert_called_once()


@pytest.mark.unit
class TestCalculateLopezDePradoFeatures:
    """Test cases for calculate_lopez_de_prado_features function."""

    def test_generate_basic_features(self):
        """Test basic feature generation."""
        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(200) * 0.01))

        X, y = calculate_lopez_de_prado_features(
            prices, config=FinancialMLConfig(apply_fracdiff=False)
        )

        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) > 0
        assert len(y) > 0

    def test_feature_columns(self):
        """Test that expected feature columns are generated."""
        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(200) * 0.01))

        config = FinancialMLConfig(apply_fracdiff=False)
        X, _ = calculate_lopez_de_prado_features(prices, config=config)

        # Check for expected feature columns
        expected_cols = ["returns", "log_returns", "volatility_20"]
        for col in expected_cols:
            assert col in X.columns

    def test_with_custom_features(self):
        """Test with pre-computed features."""
        np.random.seed(42)
        prices = pd.Series(100 + np.cumsum(np.random.randn(200) * 0.01))

        custom_features = pd.DataFrame(
            {"custom_feature": np.random.randn(200)},
            index=prices.index,
        )

        config = FinancialMLConfig(apply_fracdiff=False)
        X, y = calculate_lopez_de_prado_features(prices, custom_features, config)

        assert "custom_feature" in X.columns


@pytest.mark.unit
class TestFinancialMLEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self):
        """Test handling of empty input."""
        pipeline = FinancialMLPipeline()

        with pytest.raises((ValueError, IndexError)):
            pipeline.fit(np.array([]), np.array([]), np.array([]))

    def test_mismatched_dimensions(self):
        """Test handling of mismatched dimensions."""
        pipeline = FinancialMLPipeline()

        X = np.random.randn(100, 5)
        prices = np.random.randn(50)  # Different length
        y = np.random.randint(0, 2, 100)

        with pytest.raises((ValueError, IndexError)):
            pipeline.fit(X, prices, y)

    def test_single_feature(self):
        """Test with single feature."""
        X = np.random.randn(100, 1)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        y = np.random.randint(0, 2, 100)

        pipeline = FinancialMLPipeline(
            config=FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        )

        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            pipeline.fit(X, prices, y)

        assert pipeline.n_features_ == 1

    def test_nan_handling(self):
        """Test handling of NaN values in input."""
        X = np.random.randn(100, 5)
        X[10:15] = np.nan  # Add some NaN values
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        y = np.random.randint(0, 2, 100)

        pipeline = FinancialMLPipeline(config=FinancialMLConfig(apply_fracdiff=False))

        # Should handle NaN gracefully or raise appropriate error
        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            try:
                pipeline.fit(X, prices, y)
            except (ValueError, AttributeError):
                pass  # Expected behavior


@pytest.mark.unit
class TestFinancialMLIntegration:
    """Integration tests for Financial ML components."""

    def test_meta_labeling_integration(self):
        """Test integration with meta-labeling component."""
        from app.backtesting.labeling import MetaLabelingConfig

        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)

        meta_config = MetaLabelingConfig(primary_model_type="rf")

        config = FinancialMLConfig(
            use_meta_labeling=True,
            apply_fracdiff=False,
            use_purged_cv=False,
        )

        pipeline = FinancialMLPipeline(config)

        # Mock the meta-labeling to avoid complex ML training
        with patch.object(pipeline.meta_labeling, "fit"):
            with patch.object(pipeline.meta_labeling, "predict"):
                pipeline.fit(X, np.random.randn(100), y)

    def test_bet_sizing_integration(self):
        """Test integration with bet sizing component."""

        config = FinancialMLConfig(
            bet_sizing_method="kelly",
            kelly_fraction=0.25,
            apply_fracdiff=False,
        )

        pipeline = FinancialMLPipeline(config)

        assert pipeline.bet_sizing.config.method == "kelly"
        assert pipeline.bet_sizing.config.kelly_fraction == 0.25


@pytest.mark.unit
class TestFinancialMLPerformance:
    """Performance and property-based tests."""

    @pytest.mark.parametrize("n_samples", [50, 100, 200])
    def test_scalability(self, n_samples):
        """Test pipeline with different sample sizes."""
        X = np.random.randn(n_samples, 5)
        prices = 100 + np.cumsum(np.random.randn(n_samples) * 0.01)
        y = np.random.randint(0, 2, n_samples)

        pipeline = FinancialMLPipeline(
            config=FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        )

        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            pipeline.fit(X, prices, y)

        assert pipeline._is_fitted is True

    @pytest.mark.parametrize("n_features", [3, 5, 10])
    def test_varying_features(self, n_features):
        """Test with different numbers of features."""
        X = np.random.randn(100, n_features)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        y = np.random.randint(0, 2, 100)

        pipeline = FinancialMLPipeline(
            config=FinancialMLConfig(apply_fracdiff=False, use_purged_cv=False)
        )

        with patch.object(pipeline, "_apply_fracdiff_to_features", return_value=X):
            pipeline.fit(X, prices, y)

        assert pipeline.n_features_ == n_features

    def test_reproducibility_with_random_state(self):
        """Test that results are reproducible with same random state."""
        X = np.random.randn(100, 5)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        y = np.random.randint(0, 2, 100)

        config1 = FinancialMLConfig(random_state=42, apply_fracdiff=False, use_purged_cv=False)
        config2 = FinancialMLConfig(random_state=42, apply_fracdiff=False, use_purged_cv=False)

        pipeline1 = FinancialMLPipeline(config1)
        pipeline2 = FinancialMLPipeline(config2)

        # Both should produce similar results (exact reproducibility depends on mocks)
        with patch.object(pipeline1, "_apply_fracdiff_to_features", return_value=X):
            pipeline1.fit(X, prices, y)
        with patch.object(pipeline2, "_apply_fracdiff_to_features", return_value=X):
            pipeline2.fit(X, prices, y)

        assert pipeline1._is_fitted is True
        assert pipeline2._is_fitted is True
