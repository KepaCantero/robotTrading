"""
Tests for Meta-Labeling Cross-Validation Module

Tests the purged and embargoed cross-validation implementation
for meta-labeling applications.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from app.backtesting.labeling.meta_labeling_cv import (
    CVConfig,
    MetaLabelingCV,
    PurgedKFold,
    SequentialBootstrap,
    calculate_purge_embargo_sizes,
    cv_score_meta_labeling,
)


class TestPurgedKFold:
    """Tests for PurgedKFold class."""

    def test_init(self):
        """Test PurgedKFold initialization."""
        cv = PurgedKFold(n_folds=5, purge_pct=0.05, embargo_pct=0.01)
        assert cv.n_folds == 5
        assert cv.purge_pct == 0.05
        assert cv.embargo_pct == 0.01

    def test_split_basic(self):
        """Test basic split functionality."""
        cv = PurgedKFold(n_folds=3, purge_pct=0.0, embargo_pct=0.0)
        X = np.random.randn(100, 5)

        splits = list(cv.split(X))
        assert len(splits) == 3

        for train_idx, test_idx in splits:
            # Check no overlap
            assert len(set(train_idx) & set(test_idx)) == 0
            # Check test set is reasonable size
            assert len(test_idx) > 0
            assert len(train_idx) > 0

    def test_split_with_purge_embargo(self):
        """Test split with purge and embargo."""
        cv = PurgedKFold(n_folds=3, purge_pct=0.1, embargo_pct=0.05)
        X = np.random.randn(100, 5)

        splits = list(cv.split(X))
        assert len(splits) == 3

        # Purge and embargo should reduce training set size
        for train_idx, test_idx in splits:
            # Training should be smaller than total - test
            assert len(train_idx) < len(X) - len(test_idx)

    def test_split_with_events_labels(self):
        """Test split with events and labels for label purging."""
        cv = PurgedKFold(n_folds=3)
        X = np.random.randn(100, 5)

        # Create events and labels
        events = pd.date_range("2020-01-01", periods=100, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(1, 10, 100),
            }
        )

        splits = list(cv.split(X, events, labels))
        assert len(splits) > 0

    def test_timeseries_gap(self):
        """Test time-series gap between train and test."""
        cv = PurgedKFold(n_folds=3, timeseries_gap=2)
        X = np.random.randn(100, 5)

        for train_idx, test_idx in cv.split(X):
            # Check that there's a gap
            if len(train_idx) > 0 and len(test_idx) > 0:
                max_train = max(train_idx)
                min_test = min(test_idx)
                assert min_test - max_train >= 2


class TestMetaLabelingCV:
    """Tests for MetaLabelingCV class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 500

        X = np.random.randn(n_samples, 10)
        y = np.random.choice([-1, 0, 1], size=n_samples)

        # Create events and labels
        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(1, 10, n_samples),
            }
        )

        return X, y, events, labels

    def test_init(self):
        """Test MetaLabelingCV initialization."""
        cv = MetaLabelingCV(n_folds=5, scoring="accuracy")
        assert cv.n_folds == 5
        assert cv.scoring == "accuracy"

    def test_cross_validate(self, sample_data):
        """Test cross_validate method."""
        X, y, events, labels = sample_data

        primary_model = RandomForestClassifier(n_estimators=10, random_state=42)
        meta_model = RandomForestClassifier(n_estimators=10, random_state=42)

        cv = MetaLabelingCV(n_folds=3, scoring="accuracy")
        result = cv.cross_validate(primary_model, meta_model, X, y, events, labels)

        # Check result structure
        assert result.mean_score >= 0
        assert result.std_score >= 0
        assert len(result.fold_scores) == 3
        assert len(result.fold_predictions) == 3
        assert len(result.fold_labels) == 3

    def test_cross_validate_with_sample_weights(self, sample_data):
        """Test cross_validate with sample weights."""
        X, y, events, labels = sample_data

        # Create sample weights
        sample_weights = np.random.rand(len(y))

        primary_model = RandomForestClassifier(n_estimators=10, random_state=42)
        meta_model = RandomForestClassifier(n_estimators=10, random_state=42)

        cv = MetaLabelingCV(n_folds=3)
        result = cv.cross_validate(
            primary_model,
            meta_model,
            X,
            y,
            events,
            labels,
            sample_weights=sample_weights,
        )

        assert result.mean_score >= 0

    def test_scoring_methods(self, sample_data):
        """Test different scoring methods."""
        X, y, events, labels = sample_data

        primary_model = RandomForestClassifier(n_estimators=10, random_state=42)
        meta_model = RandomForestClassifier(n_estimators=10, random_state=42)

        for scoring in ["accuracy", "f1"]:
            cv = MetaLabelingCV(n_folds=3, scoring=scoring)
            result = cv.cross_validate(primary_model, meta_model, X, y, events, labels)

            assert result.mean_score >= 0
            assert result.metadata["scoring"] == scoring


class TestSequentialBootstrap:
    """Tests for SequentialBootstrap class."""

    def test_init(self):
        """Test SequentialBootstrap initialization."""
        sb = SequentialBootstrap(n_splits=5, test_size=0.2, gap=1)
        assert sb.n_splits == 5
        assert sb.test_size == 0.2
        assert sb.gap == 1

    def test_split(self):
        """Test split functionality."""
        sb = SequentialBootstrap(n_splits=3, test_size=0.2)
        X = np.random.randn(100, 5)

        splits = list(sb.split(X))
        assert len(splits) == 3

        for train_idx, test_idx in splits:
            # Check no overlap
            assert len(set(train_idx) & set(test_idx)) == 0
            # Check test set size
            assert len(test_idx) > 0
            # Check training comes before test (sequential)
            if len(train_idx) > 0 and len(test_idx) > 0:
                assert max(train_idx) < min(test_idx)

    def test_split_with_gap(self):
        """Test split with gap."""
        sb = SequentialBootstrap(n_splits=3, test_size=0.2, gap=5)
        X = np.random.randn(100, 5)

        for train_idx, test_idx in sb.split(X):
            if len(train_idx) > 0 and len(test_idx) > 0:
                # Check gap
                max_train = max(train_idx)
                min_test = min(test_idx)
                assert min_test - max_train >= 5


class TestCVScoreMetaLabeling:
    """Tests for cv_score_meta_labeling function."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n_samples = 300

        X = np.random.randn(n_samples, 10)
        y = np.random.choice([-1, 0, 1], size=n_samples)

        events = pd.date_range("2020-01-01", periods=n_samples, freq="D")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(1, 10, n_samples),
            }
        )

        return X, y, events, labels

    def test_cv_score_meta_labeling(self, sample_data):
        """Test cv_score_meta_labeling function."""
        X, y, events, labels = sample_data

        primary_model = RandomForestClassifier(n_estimators=10, random_state=42)
        meta_model = RandomForestClassifier(n_estimators=10, random_state=42)

        scores = cv_score_meta_labeling(
            primary_model,
            meta_model,
            X,
            y,
            events,
            labels,
            n_folds=3,
        )

        assert "mean" in scores
        assert "std" in scores
        assert "scores" in scores
        assert scores["mean"] >= 0
        assert scores["std"] >= 0
        assert len(scores["scores"]) == 3


class TestCalculatePurgeEmbargoSizes:
    """Tests for calculate_purge_embargo_sizes function."""

    def test_calculate_sizes(self):
        """Test size calculation."""
        sizes = calculate_purge_embargo_sizes(
            n_samples=1000,
            n_folds=5,
            purge_pct=0.05,
            embargo_pct=0.01,
        )

        assert "fold_size" in sizes
        assert "purge_size" in sizes
        assert "embargo_size" in sizes
        assert "train_size_per_fold" in sizes

        # Check values are reasonable
        assert sizes["fold_size"] == 200  # 1000 / 5
        assert sizes["purge_size"] == 50  # 1000 * 0.05
        assert sizes["embargo_size"] == 10  # 1000 * 0.01

    def test_different_folds(self):
        """Test with different number of folds."""
        sizes = calculate_purge_embargo_sizes(
            n_samples=1000,
            n_folds=10,
            purge_pct=0.05,
            embargo_pct=0.01,
        )

        assert sizes["fold_size"] == 100  # 1000 / 10

    def test_edge_cases(self):
        """Test edge cases."""
        # Small dataset
        sizes = calculate_purge_embargo_sizes(
            n_samples=100,
            n_folds=5,
            purge_pct=0.1,
            embargo_pct=0.05,
        )

        assert sizes["fold_size"] == 20
        assert sizes["purge_size"] == 10
        assert sizes["embargo_size"] == 5


class TestCVConfig:
    """Tests for CVConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = CVConfig()
        assert config.n_folds == 5
        assert config.shuffle == False
        assert config.purge_pct == 0.05
        assert config.embargo_pct == 0.01

    def test_custom_config(self):
        """Test custom configuration."""
        config = CVConfig(
            n_folds=10,
            purge_pct=0.1,
            embargo_pct=0.02,
        )

        assert config.n_folds == 10
        assert config.purge_pct == 0.1
        assert config.embargo_pct == 0.02

    def test_validation(self):
        """Test configuration validation."""
        # Invalid n_folds
        with pytest.raises(ValueError):
            CVConfig(n_folds=0)

        # Invalid purge_pct
        with pytest.raises(ValueError):
            CVConfig(purge_pct=1.5)

        # Invalid embargo_pct
        with pytest.raises(ValueError):
            CVConfig(embargo_pct=-0.1)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for meta-labeling CV."""

    @pytest.fixture
    def realistic_data(self):
        """Create more realistic financial data."""
        np.random.seed(42)
        n_samples = 1000

        # Features with some structure
        X = np.random.randn(n_samples, 20)

        # Labels with some predictability
        y = np.where(X[:, 0] + X[:, 1] > 0, 1, -1)
        y[np.random.choice(n_samples, size=n_samples // 5)] = 0  # Some zeros

        # Events and labels
        events = pd.date_range("2020-01-01", periods=n_samples, freq="H")
        labels = pd.DataFrame(
            {
                "bars_to_barrier": np.random.randint(5, 20, n_samples),
            }
        )

        return X, y, events, labels

    def test_full_meta_labeling_cv_workflow(self, realistic_data):
        """Test complete meta-labeling CV workflow."""
        X, y, events, labels = realistic_data

        primary_model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
        )
        meta_model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
        )

        # Run CV
        cv = MetaLabelingCV(n_folds=5, purge_pct=0.05, embargo_pct=0.01)
        result = cv.cross_validate(primary_model, meta_model, X, y, events, labels)

        # Check results
        assert result.mean_score > 0
        assert len(result.fold_scores) == 5
        assert all(score >= 0 for score in result.fold_scores)

        # Check metadata
        assert result.metadata["n_folds"] == 5
        assert result.metadata["purge_pct"] == 0.05
        assert result.metadata["embargo_pct"] == 0.01

    def test_purged_kfold_with_uniqueness_weights(self, realistic_data):
        """Test PurgedKFold with uniqueness weights."""
        X, y, events, labels = realistic_data

        cv = PurgedKFold(n_folds=5, purge_pct=0.05, embargo_pct=0.01)

        # Calculate uniqueness weights
        from app.backtesting.labeling.triple_barrier import calculate_sample_weights_uniqueness

        price_series = pd.Series(range(len(X)))
        weights = calculate_sample_weights_uniqueness(events, labels, price_series)

        # Train with weights
        model = RandomForestClassifier(n_estimators=10, random_state=42)

        for train_idx, test_idx in cv.split(X, events, labels):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train = weights[train_idx]

            model.fit(X_train, y_train, sample_weight=w_train)
            score = model.score(X_test, y_test)

            assert score >= 0
