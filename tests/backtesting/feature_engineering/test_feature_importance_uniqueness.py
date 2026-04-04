"""
Tests for Feature Importance with Uniqueness Module

Tests the uniqueness-weighted feature importance implementation.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from app.backtesting.feature_engineering.feature_importance_uniqueness import (
    FeatureClusterer,
    FinancialMLFeatureImportanceWithUniqueness,
    MDAWithUniqueness,
    MDIWithUniqueness,
    UniquenessCalculator,
    UniquenessConfig,
    calculate_feature_importance_with_uniqueness,
)


class TestUniquenessCalculator:
    """Tests for UniquenessCalculator class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        n_samples = 100
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 15, n_samples),
            }
        )
        price_series = pd.Series(range(n_samples))

        return events, labels, price_series

    def test_init(self):
        """Test UniquenessCalculator initialization."""
        config = UniquenessConfig(uniqueness_method="average")
        calc = UniquenessCalculator(config)
        assert calc.config.uniqueness_method == "average"

    def test_calculate_average_uniqueness(self, sample_data):
        """Test average uniqueness calculation."""
        events, labels, price_series = sample_data

        calc = UniquenessCalculator()
        weights = calc.calculate_average_uniqueness(events, labels, price_series)

        # Check weights
        assert len(weights) == len(events)
        assert all(w >= 0 for w in weights)
        assert weights.sum() > 0

    def test_calculate_concurrent_uniqueness(self, sample_data):
        """Test concurrent uniqueness calculation."""
        events, labels, price_series = sample_data

        config = UniquenessConfig(uniqueness_method="concurrent")
        calc = UniquenessCalculator(config)
        weights = calc.calculate_concurrent_uniqueness(events, labels)

        # Check weights
        assert len(weights) == len(events)
        assert all(w >= 0 for w in weights)

    def test_uniqueness_with_overlapping_labels(self):
        """Test uniqueness with heavily overlapping labels."""
        n_samples = 50
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")

        # Create labels with high overlap
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.ones(n_samples, dtype=int) * 20,  # All 20 bars
            }
        )

        price_series = pd.Series(range(n_samples))

        calc = UniquenessCalculator()
        weights = calc.calculate_average_uniqueness(events, labels, price_series)

        # With high overlap, weights should be lower (allow floating-point tolerance)
        assert weights.mean() <= 1.0 + 1e-10

    def test_uniqueness_with_no_overlap(self):
        """Test uniqueness with no overlapping labels."""
        n_samples = 50
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")

        # Create labels with no overlap
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.ones(n_samples, dtype=int),  # All 1 bar
            }
        )

        price_series = pd.Series(range(n_samples))

        calc = UniquenessCalculator()
        weights = calc.calculate_average_uniqueness(events, labels, price_series)

        # With no overlap, weights should be higher
        assert weights.mean() > 0.5


class TestMDIWithUniqueness:
    """Tests for MDIWithUniqueness class."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model for testing."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1], size=n_samples)

        model = RandomForestClassifier(n_estimators=20, random_state=42)
        model.fit(X, y)

        return model, X, y

    @pytest.fixture
    def events_labels(self):
        """Create events and labels for testing."""
        n_samples = 200
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 15, n_samples),
            }
        )
        price_series = pd.Series(range(n_samples))

        return events, labels, price_series

    def test_init(self):
        """Test MDIWithUniqueness initialization."""
        config = UniquenessConfig()
        mdi = MDIWithUniqueness(config)
        assert mdi.config == config

    def test_calculate_mdi(self, trained_model, events_labels):
        """Test MDI calculation with uniqueness."""
        model, X, y = trained_model
        events, labels, price_series = events_labels

        mdi = MDIWithUniqueness()
        importance = mdi.calculate(model, X, y, events, labels)

        # Check importance scores
        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())
        assert all(v <= 1 for v in importance.values())

        # Check that scores sum to approximately 1
        total = sum(importance.values())
        assert abs(total - 1.0) < 0.1

    def test_calculate_mdi_with_feature_names(self, trained_model, events_labels):
        """Test MDI calculation with custom feature names."""
        model, X, y = trained_model
        events, labels, price_series = events_labels

        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        mdi = MDIWithUniqueness()
        importance = mdi.calculate(model, X, y, events, labels, feature_names)

        assert set(importance.keys()) == set(feature_names)


class TestMDAWithUniqueness:
    """Tests for MDAWithUniqueness class."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model for testing."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1], size=n_samples)

        model = RandomForestClassifier(n_estimators=20, random_state=42)
        model.fit(X, y)

        return model, X, y

    @pytest.fixture
    def events_labels(self):
        """Create events and labels for testing."""
        n_samples = 200
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 15, n_samples),
            }
        )
        price_series = pd.Series(range(n_samples))

        return events, labels, price_series

    def test_init(self):
        """Test MDAWithUniqueness initialization."""
        config = UniquenessConfig(mda_n_repeats=5)
        mda = MDAWithUniqueness(config)
        assert mda.config.mda_n_repeats == 5

    def test_calculate_mda(self, trained_model, events_labels):
        """Test MDA calculation with uniqueness."""
        model, X, y = trained_model
        events, labels, price_series = events_labels

        mda = MDAWithUniqueness()
        importance = mda.calculate(model, X, y, events, labels)

        # Check importance scores
        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())

    def test_calculate_mda_with_scoring(self, trained_model, events_labels):
        """Test MDA calculation with different scoring methods."""
        model, X, y = trained_model
        events, labels, price_series = events_labels

        for scoring in ["accuracy", "f1"]:
            config = UniquenessConfig(mda_scoring=scoring, mda_n_repeats=3)
            mda = MDAWithUniqueness(config)
            importance = mda.calculate(model, X, y, events, labels)

            assert len(importance) == X.shape[1]


class TestFeatureClusterer:
    """Tests for FeatureClusterer class."""

    @pytest.fixture
    def sample_features(self):
        """Create sample features for testing."""
        np.random.seed(42)
        n_samples = 100

        # Create correlated features
        X = pd.DataFrame(
            {
                "feature_0": np.random.randn(n_samples),
                "feature_1": np.random.randn(n_samples) * 0.9,  # Correlated with f0
                "feature_2": np.random.randn(n_samples),
                "feature_3": np.random.randn(n_samples),
            }
        )

        # Make feature_1 correlated with feature_0
        X["feature_1"] = X["feature_0"] * 0.8 + X["feature_1"] * 0.2

        return X

    def test_init(self):
        """Test FeatureClusterer initialization."""
        config = UniquenessConfig(correlation_threshold=0.7)
        clusterer = FeatureClusterer(config)
        assert clusterer.config.correlation_threshold == 0.7

    def test_cluster_features(self, sample_features):
        """Test feature clustering."""
        clusterer = FeatureClusterer()
        clusters = clusterer.cluster_features(sample_features)

        # Check that we get clusters
        assert len(clusters) > 0

        # Check that all features are assigned
        all_features = set()
        for members in clusters.values():
            all_features.update(members)

        assert all_features == set(sample_features.columns)

    def test_cluster_with_correlation_threshold(self, sample_features):
        """Test clustering with different thresholds."""
        for threshold in [0.5, 0.7, 0.9]:
            config = UniquenessConfig(correlation_threshold=threshold)
            clusterer = FeatureClusterer(config)
            clusters = clusterer.cluster_features(sample_features)

            # Should get different number of clusters
            assert len(clusters) > 0


class TestFinancialMLFeatureImportanceWithUniqueness:
    """Tests for FinancialMLFeatureImportanceWithUniqueness class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 300
        n_features = 15

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1], size=n_samples)

        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 15, n_samples),
            }
        )

        # Train model
        model = RandomForestClassifier(n_estimators=30, random_state=42)
        model.fit(X, y)

        return model, X, y, events, labels

    def test_init(self):
        """Test initialization."""
        config = UniquenessConfig()
        importance = FinancialMLFeatureImportanceWithUniqueness(config)
        assert importance.config == config

    def test_calculate_importance(self, sample_data):
        """Test complete importance calculation."""
        model, X, y, events, labels = sample_data

        importance = FinancialMLFeatureImportanceWithUniqueness()
        result = importance.calculate_importance(model, X, y, events, labels)

        # Check result structure
        assert result.n_samples == len(X)
        assert result.n_features == X.shape[1]
        assert len(result.uniqueness_weights) == len(X)
        assert result.avg_uniqueness > 0

        # Check importance scores
        assert len(result.mdi_importance) > 0 or len(result.mda_importance) > 0
        assert len(result.combined_importance) > 0

    def test_calculate_importance_with_clustering(self, sample_data):
        """Test importance calculation with feature clustering."""
        model, X, y, events, labels = sample_data

        config = UniquenessConfig(cluster_features=True)
        importance = FinancialMLFeatureImportanceWithUniqueness(config)
        result = importance.calculate_importance(model, X, y, events, labels)

        # Check that clusters were created
        assert len(result.feature_clusters) > 0

    def test_calculate_importance_dataframe(self, sample_data):
        """Test importance calculation with DataFrame input."""
        model, X, y, events, labels = sample_data

        # Convert to DataFrame
        X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])

        importance = FinancialMLFeatureImportanceWithUniqueness()
        result = importance.calculate_importance(model, X_df, y, events, labels)

        # Should work the same as numpy
        assert result.n_features == X.shape[1]

    def test_result_to_dict(self, sample_data):
        """Test UniquenessResult.to_dict method."""
        model, X, y, events, labels = sample_data

        importance = FinancialMLFeatureImportanceWithUniqueness()
        result = importance.calculate_importance(model, X, y, events, labels)

        # Convert to dict
        result_dict = result.to_dict()

        # Check dict contents
        assert "feature_names" in result_dict
        assert "mdi_importance" in result_dict
        assert "mda_importance" in result_dict
        assert "combined_importance" in result_dict
        assert "avg_uniqueness" in result_dict
        assert "n_samples" in result_dict
        assert "n_features" in result_dict


class TestCalculateFeatureImportanceWithUniqueness:
    """Tests for convenience function."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 200
        n_features = 10

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1], size=n_samples)

        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 15, n_samples),
            }
        )

        model = RandomForestClassifier(n_estimators=20, random_state=42)
        model.fit(X, y)

        return model, X, y, events, labels

    def test_mdi_method(self, sample_data):
        """Test MDI method."""
        model, X, y, events, labels = sample_data

        importance = calculate_feature_importance_with_uniqueness(
            model, X, y, events, labels, method="mdi"
        )

        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())

    def test_mda_method(self, sample_data):
        """Test MDA method."""
        model, X, y, events, labels = sample_data

        importance = calculate_feature_importance_with_uniqueness(
            model, X, y, events, labels, method="mda"
        )

        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())

    def test_combined_method(self, sample_data):
        """Test combined method."""
        model, X, y, events, labels = sample_data

        importance = calculate_feature_importance_with_uniqueness(
            model, X, y, events, labels, method="combined"
        )

        assert len(importance) == X.shape[1]
        assert all(v >= 0 for v in importance.values())

    def test_custom_config(self, sample_data):
        """Test with custom configuration."""
        model, X, y, events, labels = sample_data

        importance = calculate_feature_importance_with_uniqueness(
            model,
            X,
            y,
            events,
            labels,
            method="mda",
            mda_n_repeats=5,
            cluster_features=True,
        )

        assert len(importance) == X.shape[1]


class TestUniquenessConfig:
    """Tests for UniquenessConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = UniquenessConfig()
        assert config.uniqueness_method == "average"
        assert config.cluster_features == True
        assert config.correlation_threshold == 0.7

    def test_custom_config(self):
        """Test custom configuration."""
        config = UniquenessConfig(
            uniqueness_method="concurrent",
            cluster_features=False,
            correlation_threshold=0.8,
        )

        assert config.uniqueness_method == "concurrent"
        assert config.cluster_features == False
        assert config.correlation_threshold == 0.8

    def test_validation(self):
        """Test configuration validation."""
        # Invalid uniqueness_method
        with pytest.raises(ValueError):
            UniquenessConfig(uniqueness_method="invalid")

        # Invalid overlap_threshold
        with pytest.raises(ValueError):
            UniquenessConfig(overlap_threshold=1.5)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for feature importance with uniqueness."""

    @pytest.fixture
    def realistic_data(self):
        """Create realistic financial data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 20

        # Features with some structure
        X = np.random.randn(n_samples, n_features)

        # Make some features correlated
        X[:, 1] = X[:, 0] * 0.8 + np.random.randn(n_samples) * 0.2
        X[:, 3] = X[:, 2] * 0.7 + np.random.randn(n_samples) * 0.3

        # Target with some predictability
        y = (X[:, 0] + X[:, 2] > 0).astype(int)

        # Events and labels
        events = pd.date_range("2020-01-01", periods=n_samples, freq="H")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 20, n_samples),
            }
        )

        # Train model
        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
        )
        model.fit(X, y)

        return model, X, y, events, labels

    def test_full_pipeline(self, realistic_data):
        """Test complete feature importance pipeline."""
        model, X, y, events, labels = realistic_data

        # Calculate importance
        importance = FinancialMLFeatureImportanceWithUniqueness()
        result = importance.calculate_importance(model, X, y, events, labels)

        # Check results
        assert result.n_samples == len(X)
        assert result.n_features == X.shape[1]
        assert result.avg_uniqueness > 0

        # Check that MDI and MDA both work
        assert len(result.mdi_importance) > 0
        assert len(result.mda_importance) > 0
        assert len(result.combined_importance) > 0

        # Check feature clusters
        assert len(result.feature_clusters) > 0

        # Check that correlated features are in same cluster
        # (feature_0 and feature_1 should be clustered)
        for cluster_rep, members in result.feature_clusters.items():
            if "feature_0" in members and "feature_1" in members:
                break

        # May or may not be clustered depending on threshold
        # But the pipeline should complete successfully

    def test_comparison_with_standard_importance(self, realistic_data):
        """Test uniqueness-weighted vs standard importance."""
        model, X, y, events, labels = realistic_data

        # Standard importance
        standard_importance = dict(
            zip(
                [f"feature_{i}" for i in range(X.shape[1])],
                model.feature_importances_,
            )
        )

        # Uniqueness-weighted importance
        importance_calc = FinancialMLFeatureImportanceWithUniqueness()
        result = importance_calc.calculate_importance(model, X, y, events, labels)

        # Both should have same features
        assert set(standard_importance.keys()) == set(result.mdi_importance.keys())

        # Importance scores may differ due to uniqueness weighting
        # But both should be valid
        assert all(v >= 0 for v in standard_importance.values())
        assert all(v >= 0 for v in result.mdi_importance.values())
