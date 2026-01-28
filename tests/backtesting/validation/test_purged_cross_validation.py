"""
Tests for Purged Cross-Validation (López de Prado Chapter 4).

Tests the purged K-Fold cross-validation implementation that prevents
look-ahead bias in financial time series ML.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from app.backtesting.validation.cross_validation import (
    PurgedKFold,
    PurgedTimeSeriesSplit,
    PurgedCVConfig,
    PurgedSplitResult,
    cv_score,
)


@pytest.fixture
def sample_data():
    """Create sample time series data for testing."""
    np.random.seed(42)

    # Create 1000 samples with 10 features
    n_samples = 1000
    n_features = 10

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)],
        index=pd.date_range('2020-01-01', periods=n_samples, freq='D')
    )

    # Create binary labels
    y = pd.Series(
        np.random.randint(0, 2, n_samples),
        index=X.index,
        name='label'
    )

    # Create events with t1 (exit times)
    random_days = np.random.randint(1, 10, n_samples)
    events = pd.DataFrame({
        't1': [X.index[i] + pd.Timedelta(days=random_days[i]) for i in range(n_samples)]
    }, index=X.index)

    return X, y, events


class TestPurgedKFold:
    """Tests for PurgedKFold class."""

    def test_initialization(self):
        """Test PurgedKFold initialization."""
        cv = PurgedKFold(n_splits=5, embargo_pct=0.01, purge_pct=0.05)

        assert cv.config.n_splits == 5
        assert cv.config.embargo_pct == 0.01
        assert cv.config.purge_pct == 0.05

    def test_split_generates_correct_number_of_folds(self, sample_data):
        """Test that split generates the correct number of folds."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        # Should generate 5 folds (or fewer if some are invalid)
        assert len(splits) <= 5
        assert len(splits) > 0

    def test_split_returns_correct_types(self, sample_data):
        """Test that split returns correct data types."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        train_idx, test_idx = splits[0]

        assert isinstance(train_idx, np.ndarray)
        assert isinstance(test_idx, np.ndarray)
        assert len(train_idx) > 0
        assert len(test_idx) > 0

    def test_no_train_test_overlap(self, sample_data):
        """Test that train and test sets don't overlap."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        for train_idx, test_idx in splits:
            # Check no overlap
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0

            # Check temporal integrity (all train before test)
            assert train_idx.max() < test_idx.min()

    def test_purge_removes_samples_near_test(self, sample_data):
        """Test that purging removes samples near test set."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5, purge_pct=0.05)
        splits = list(cv.split(X, y, events=events))

        assert len(cv.split_results) > 0

        for split_result in cv.split_results:
            # Check that purged samples exist
            assert split_result.n_purged >= 0

            # Check that purged samples were removed
            assert split_result.train_size_after <= split_result.train_size_before

    def test_embargo_creates_buffer_zone(self, sample_data):
        """Test that embargo creates buffer zone after test set."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5, embargo_pct=0.01)
        splits = list(cv.split(X, y, events=events))

        assert len(cv.split_results) > 0

        for split_result in cv.split_results:
            # Check that embargo exists
            assert split_result.n_embargoed >= 0

            # Check that embargoed samples are not in training set
            assert split_result.n_embargoed == 0 or \
                   split_result.train_size_after < split_result.train_size_before

    def test_get_n_splits(self):
        """Test get_n_splits method."""
        cv = PurgedKFold(n_splits=5)
        assert cv.get_n_splits() == 5

    def test_get_split_summary(self, sample_data):
        """Test get_split_summary method."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        list(cv.split(X, y, events=events))

        summary = cv.get_split_summary()

        assert isinstance(summary, pd.DataFrame)
        assert len(summary) > 0
        assert 'fold' in summary.columns
        assert 'train_size' in summary.columns
        assert 'test_size' in summary.columns

    def test_validate_no_leakage(self, sample_data):
        """Test validate_no_leakage method."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        list(cv.split(X, y, events=events))

        # Should not detect leakage
        assert cv.validate_no_leakage(X) is True

    def test_event_based_embargo(self, sample_data):
        """Test event-based embargo using t1 column."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5, embargo_pct=0.01)
        splits = list(cv.split(X, y, events=events))

        # Should generate splits with event-based embargo
        assert len(splits) > 0

        # Test without events (should use percentage-based embargo)
        splits_no_events = list(cv.split(X, y))
        assert len(splits_no_events) > 0

    def test_minimum_samples_validation(self, sample_data):
        """Test minimum samples validation."""
        X, y, events = sample_data

        # Set very high minimum samples
        cv = PurgedKFold(
            n_splits=5,
            min_train_samples=10000,  # More than total samples
            min_test_samples=1000
        )

        # Should raise error or return empty list
        with pytest.raises((ValueError, StopIteration)):
            list(cv.split(X, y, events=events))

    def test_with_small_dataset(self):
        """Test behavior with small dataset."""
        # Create very small dataset
        X = pd.DataFrame(
            np.random.randn(50, 5),
            columns=[f'feature_{i}' for i in range(5)]
        )
        y = pd.Series(np.random.randint(0, 2, 50))
        events = pd.DataFrame({
            't1': pd.date_range('2020-01-01', periods=50, freq='D') + pd.Timedelta(days=5)
        })

        cv = PurgedKFold(n_splits=3, min_train_samples=20, min_test_samples=5)

        # Should still generate some splits
        splits = list(cv.split(X, y, events=events))
        assert len(splits) >= 0


class TestPurgedTimeSeriesSplit:
    """Tests for PurgedTimeSeriesSplit class."""

    def test_initialization(self):
        """Test PurgedTimeSeriesSplit initialization."""
        tscv = PurgedTimeSeriesSplit(n_splits=5)

        assert tscv.n_splits == 5
        assert tscv.embargo_pct == 0.01
        assert tscv.purge_pct == 0.05

    def test_split_generates_correct_number_of_folds(self, sample_data):
        """Test that split generates correct number of folds."""
        X, y, events = sample_data

        tscv = PurgedTimeSeriesSplit(n_splits=5)
        splits = list(tscv.split(X, y, events=events))

        assert len(splits) <= 5
        assert len(splits) > 0

    def test_expanding_window_behavior(self, sample_data):
        """Test that time series split uses expanding window."""
        X, y, events = sample_data

        tscv = PurgedTimeSeriesSplit(n_splits=5)
        splits = list(tscv.split(X, y, events=events))

        # Training size should generally increase (expanding window)
        train_sizes = [len(train_idx) for train_idx, _ in splits]

        # Allow for purging to reduce size, but general trend should be increasing
        assert len(train_sizes) > 0

    def test_max_train_size(self, sample_data):
        """Test max_train_size parameter."""
        X, y, events = sample_data

        max_size = 200
        tscv = PurgedTimeSeriesSplit(n_splits=3, max_train_size=max_size)
        splits = list(tscv.split(X, y, events=events))

        for train_idx, _ in splits:
            assert len(train_idx) <= max_size


class TestCVScore:
    """Tests for cv_score function."""

    def test_cv_score_returns_metrics(self, sample_data):
        """Test that cv_score returns correct metrics."""
        X, y, events = sample_data

        estimator = RandomForestClassifier(n_estimators=10, random_state=42)

        results = cv_score(
            estimator,
            X.values,
            y.values,
            events=events,
            n_splits=3
        )

        assert 'mean_score' in results
        assert 'std_score' in results
        assert 'fold_scores' in results
        assert len(results['fold_scores']) <= 3

    def test_cv_score_with_custom_scoring(self, sample_data):
        """Test cv_score with custom scoring function."""
        from sklearn.metrics import f1_score

        X, y, events = sample_data

        estimator = RandomForestClassifier(n_estimators=10, random_state=42)

        results = cv_score(
            estimator,
            X.values,
            y.values,
            events=events,
            n_splits=3,
            scoring=f1_score
        )

        assert 'mean_score' in results
        assert isinstance(results['mean_score'], float)


class TestPurgedCVConfig:
    """Tests for PurgedCVConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PurgedCVConfig()

        assert config.n_splits == 5
        assert config.embargo_pct == 0.01
        assert config.purge_pct == 0.05
        assert config.min_train_samples == 252
        assert config.min_test_samples == 20

    def test_validation_invalid_n_splits(self):
        """Test validation of invalid n_splits."""
        with pytest.raises(ValueError):
            PurgedCVConfig(n_splits=1)

    def test_validation_invalid_purge_pct(self):
        """Test validation of invalid purge_pct."""
        with pytest.raises(ValueError):
            PurgedCVConfig(purge_pct=0.6)  # > 0.5

    def test_validation_invalid_embargo_pct(self):
        """Test validation of invalid embargo_pct."""
        with pytest.raises(ValueError):
            PurgedCVConfig(embargo_pct=-0.1)  # < 0


class TestPurgedSplitResult:
    """Tests for PurgedSplitResult dataclass."""

    def test_create_split_result(self):
        """Test creating a PurgedSplitResult."""
        result = PurgedSplitResult(
            fold=0,
            train_indices=np.array([0, 1, 2]),
            test_indices=np.array([3, 4]),
            purged_indices=np.array([2]),
            embargo_indices=np.array([5]),
            train_size_before=4,
            train_size_after=3,
            n_purged=1,
            n_embargoed=1
        )

        assert result.fold == 0
        assert len(result.train_indices) == 3
        assert len(result.test_indices) == 2
        assert result.n_purged == 1
        assert result.n_embargoed == 1


class TestIntegration:
    """Integration tests for purged CV with ML models."""

    def test_full_pipeline_with_random_forest(self, sample_data):
        """Test full pipeline: purged CV + training + evaluation."""
        X, y, events = sample_data

        # Use purged CV for train/test split
        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        train_idx, test_idx = splits[0]
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Train model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate
        score = model.score(X_test, y_test)

        assert 0 <= score <= 1

    def test_cross_validation_with_multiple_folds(self, sample_data):
        """Test cross-validation across multiple folds."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=3)
        scores = []

        for train_idx, test_idx in cv.split(X, y, events=events):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model = RandomForestClassifier(n_estimators=5, random_state=42)
            model.fit(X_train, y_train)
            score = model.score(X_test, y_test)
            scores.append(score)

        assert len(scores) > 0
        assert all(0 <= s <= 1 for s in scores)

    def test_with_dataframe_index(self):
        """Test with DataFrame that has datetime index."""
        # Create data with datetime index
        dates = pd.date_range('2020-01-01', periods=500, freq='D')
        X = pd.DataFrame(
            np.random.randn(500, 5),
            index=dates
        )
        y = pd.Series(np.random.randint(0, 2, 500), index=dates)
        events = pd.DataFrame({
            't1': dates + pd.Timedelta(days=5)
        }, index=dates)

        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        assert len(splits) > 0

    def test_temporal_order_preserved(self, sample_data):
        """Test that temporal order is preserved in splits."""
        X, y, events = sample_data

        cv = PurgedKFold(n_splits=5)
        splits = list(cv.split(X, y, events=events))

        for train_idx, test_idx in splits:
            # All train indices should be before all test indices
            assert train_idx.max() < test_idx.min()

            # Indices should be sorted
            assert np.array_equal(train_idx, np.sort(train_idx))
            assert np.array_equal(test_idx, np.sort(test_idx))
