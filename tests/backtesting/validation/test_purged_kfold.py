"""
Unit tests for Purged K-Fold with Embargo cross-validation.

Tests the implementation of López de Prado's cross-validation method
to ensure it prevents look-ahead bias and information leakage.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression

from app.backtesting.validation.purged_kfold import (
    PurgedKFold,
    PurgedKFoldConfig,
    PurgedSplit,
    PurgedTimeSeriesSplit,
    apply_embargo,
    cross_validate_with_purging,
    get_embargo_indices,
    get_purge_indices,
    purged_kfold_splits,
)


class TestPurgedKFoldConfig(unittest.TestCase):
    """Test PurgedKFoldConfig validation."""

    def test_valid_config(self):
        """Test creating a valid configuration."""
        config = PurgedKFoldConfig(
            n_splits=5,
            purge_pct=0.05,
            embargo_pct=0.02,
        )
        self.assertEqual(config.n_splits, 5)
        self.assertEqual(config.purge_pct, 0.05)
        self.assertEqual(config.embargo_pct, 0.02)

    def test_invalid_n_splits(self):
        """Test that n_splits < 2 raises ValueError."""
        with self.assertRaises(ValueError):
            PurgedKFoldConfig(n_splits=1)

    def test_invalid_purge_pct(self):
        """Test that purge_pct > 0.5 raises ValueError."""
        with self.assertRaises(ValueError):
            PurgedKFoldConfig(purge_pct=0.6)

    def test_invalid_embargo_pct(self):
        """Test that embargo_pct > 0.5 raises ValueError."""
        with self.assertRaises(ValueError):
            PurgedKFoldConfig(embargo_pct=0.6)

    def test_negative_percentages(self):
        """Test that negative percentages are accepted (0 is allowed)."""
        config = PurgedKFoldConfig(purge_pct=0.0, embargo_pct=0.0)
        self.assertEqual(config.purge_pct, 0.0)
        self.assertEqual(config.embargo_pct, 0.0)


class TestGetPurgeIndices(unittest.TestCase):
    """Test get_purge_indices function."""

    def test_basic_purge(self):
        """Test basic purging functionality."""
        train_idx = np.arange(0, 100)
        test_idx = np.arange(100, 120)

        purged = get_purge_indices(train_idx, test_idx, purge_pct=0.05, n_samples=120)

        # Should purge some samples from the end of train
        self.assertGreater(len(purged), 0)
        self.assertTrue(np.all(purged < test_idx[0]))

    def test_no_overlap_purge(self):
        """Test purging when there's no overlap."""
        train_idx = np.arange(0, 80)
        test_idx = np.arange(100, 120)

        purged = get_purge_indices(train_idx, test_idx, purge_pct=0.05, n_samples=120)

        # Should still purge samples near test set
        self.assertGreater(len(purged), 0)

    def test_zero_purge_pct(self):
        """Test with zero purge percentage."""
        train_idx = np.arange(0, 100)
        test_idx = np.arange(100, 120)

        purged = get_purge_indices(train_idx, test_idx, purge_pct=0.0, n_samples=120)

        # Should purge minimum 1 sample (guaranteed by max(1, ...))
        self.assertEqual(len(purged), 1)


class TestGetEmbargoIndices(unittest.TestCase):
    """Test get_embargo_indices function."""

    def test_basic_embargo(self):
        """Test basic embargo functionality."""
        test_idx = np.arange(100, 120)

        embargo = get_embargo_indices(test_idx, embargo_pct=0.02, n_samples=150)

        # Should create buffer after test set
        self.assertGreater(len(embargo), 0)
        self.assertTrue(np.all(embargo > test_idx[-1]))

    def test_embargo_at_boundary(self):
        """Test embargo at array boundary."""
        test_idx = np.arange(140, 150)

        embargo = get_embargo_indices(test_idx, embargo_pct=0.02, n_samples=150)

        # Should handle boundary correctly
        self.assertTrue(np.all(embargo <= 149))

    def test_zero_embargo_pct(self):
        """Test with zero embargo percentage."""
        test_idx = np.arange(100, 120)

        embargo = get_embargo_indices(test_idx, embargo_pct=0.0, n_samples=150)

        # Should embargo minimum 1 sample (guaranteed by max(1, ...))
        self.assertEqual(len(embargo), 1)


class TestApplyEmbargo(unittest.TestCase):
    """Test apply_embargo function."""

    def test_apply_embargo_removes_samples(self):
        """Test that embargo removes samples from training set."""
        train_idx = np.arange(0, 100)
        test_idx = np.arange(100, 120)

        train_after, embargo_idx = apply_embargo(
            train_idx, test_idx, embargo_pct=0.02, n_samples=150
        )

        # Training set should be smaller or equal
        self.assertLessEqual(len(train_after), len(train_idx))

        # Embargo indices should be after test set
        self.assertTrue(np.all(embargo_idx > test_idx[-1]))

    def test_embargo_not_in_train(self):
        """Test that embargo indices are not in training set."""
        train_idx = np.arange(0, 100)
        test_idx = np.arange(100, 120)

        train_after, embargo_idx = apply_embargo(
            train_idx, test_idx, embargo_pct=0.02, n_samples=150
        )

        # None of the embargo indices should be in the new training set
        overlap = np.intersect1d(train_after, embargo_idx)
        self.assertEqual(len(overlap), 0)


class TestPurgedKFold(unittest.TestCase):
    """Test PurgedKFold class."""

    def setUp(self):
        """Set up test fixtures."""
        self.n_samples = 1000
        self.X = np.random.randn(self.n_samples, 10)
        self.y = np.random.randint(0, 2, self.n_samples)

    def test_basic_split(self):
        """Test basic splitting functionality."""
        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(self.X, self.y)

        # Should generate splits
        self.assertGreater(len(splits), 0)

        # Each split should have train and test indices
        for train_idx, test_idx in splits:
            self.assertIsInstance(train_idx, np.ndarray)
            self.assertIsInstance(test_idx, np.ndarray)
            self.assertGreater(len(train_idx), 0)
            self.assertGreater(len(test_idx), 0)

    def test_split_sizes(self):
        """Test that splits have reasonable sizes."""
        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(self.X, self.y)

        for train_idx, test_idx in splits:
            # Training set should be larger than test set
            self.assertGreater(len(train_idx), len(test_idx))

            # Combined size should be less than total (due to purge/embargo)
            self.assertLess(len(train_idx) + len(test_idx), self.n_samples)

    def test_temporal_ordering(self):
        """Test that temporal ordering is preserved."""
        purged_cv = PurgedKFold(n_splits=5, shuffle=False)
        splits = purged_cv.split(self.X, self.y)

        for train_idx, test_idx in splits:
            # All training indices should be before test indices
            # (after purging)
            train_max = train_idx.max()
            test_min = test_idx.min()

            # Due to purging, training max should be less than test min
            self.assertLess(train_max, test_min)

    def test_insufficient_samples_error(self):
        """Test error when samples are insufficient."""
        X_small = np.random.randn(50, 10)

        purged_cv = PurgedKFold(
            n_splits=5, min_train_samples=252, min_test_samples=20
        )

        with self.assertRaises(ValueError):
            list(purged_cv.split(X_small))

    def test_get_split_summary(self):
        """Test split summary generation."""
        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(self.X, self.y)

        summary = purged_cv.get_split_summary()

        # Summary should be a DataFrame
        self.assertIsInstance(summary, pd.DataFrame)

        # Should have one row per split
        self.assertEqual(len(summary), len(splits))

        # Should have required columns
        required_cols = ['fold', 'train_size', 'test_size', 'purged_count', 'embargo_size']
        for col in required_cols:
            self.assertIn(col, summary.columns)

    def test_validate_no_leakage(self):
        """Test leakage validation."""
        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(self.X, self.y)

        # Should not have leakage
        self.assertTrue(purged_cv.validate_no_leakage(self.X))

    def test_with_pandas_dataframe(self):
        """Test with pandas DataFrame."""
        X_df = pd.DataFrame(
            self.X,
            index=pd.date_range('2020-01-01', periods=self.n_samples)
        )

        purged_cv = PurgedKFold(n_splits=5)
        splits = purged_cv.split(X_df)

        # Should handle DataFrame correctly
        self.assertGreater(len(splits), 0)

        for train_idx, test_idx in splits:
            # Indices should be numpy arrays
            self.assertIsInstance(train_idx, np.ndarray)
            self.assertIsInstance(test_idx, np.ndarray)


class TestPurgedTimeSeriesSplit(unittest.TestCase):
    """Test PurgedTimeSeriesSplit class."""

    def setUp(self):
        """Set up test fixtures."""
        self.n_samples = 500
        self.X = np.random.randn(self.n_samples, 10)

    def test_basic_split(self):
        """Test basic time series splitting."""
        tscv = PurgedTimeSeriesSplit(n_splits=5)
        splits = tscv.split(self.X)

        # Should generate splits
        self.assertEqual(len(splits), 5)

        # Each split should have train and test indices
        for train_idx, test_idx in splits:
            self.assertGreater(len(train_idx), 0)
            self.assertGreater(len(test_idx), 0)

    def test_expanding_window(self):
        """Test expanding window behavior."""
        tscv = PurgedTimeSeriesSplit(n_splits=5, max_train_size=None)
        splits = tscv.split(self.X)

        train_sizes = [len(train_idx) for train_idx, _ in splits]

        # Training sizes should be non-decreasing (expanding window)
        for i in range(1, len(train_sizes)):
            self.assertGreaterEqual(train_sizes[i], train_sizes[i-1])

    def test_fixed_window(self):
        """Test fixed window behavior."""
        max_train_size = 200
        tscv = PurgedTimeSeriesSplit(n_splits=5, max_train_size=max_train_size)
        splits = tscv.split(self.X)

        train_sizes = [len(train_idx) for train_idx, _ in splits]

        # Training sizes should not exceed max_train_size
        for size in train_sizes:
            self.assertLessEqual(size, max_train_size)

    def test_fixed_test_size(self):
        """Test fixed test size behavior."""
        test_size = 50
        tscv = PurgedTimeSeriesSplit(n_splits=5, test_size=test_size)
        splits = tscv.split(self.X)

        # All test sets should have the same size (except possibly last)
        test_sizes = [len(test_idx) for _, test_idx in splits]

        # Most should have the requested test size
        self.assertTrue(all(size == test_size for size in test_sizes[:-1]))


class TestPurgedKfoldSplits(unittest.TestCase):
    """Test purged_kfold_splits convenience function."""

    def test_convenience_function(self):
        """Test the convenience function."""
        X = np.random.randn(500, 10)

        splits = purged_kfold_splits(X, n_splits=5, purge_pct=0.05)

        # Should generate splits
        self.assertGreater(len(splits), 0)

        # Each split should be a tuple
        for split in splits:
            self.assertIsInstance(split, tuple)
            self.assertEqual(len(split), 2)


class TestCrossValidateWithPurging(unittest.TestCase):
    """Test cross_validate_with_purging function."""

    def test_with_classifier(self):
        """Test cross-validation with a classifier."""
        X = np.random.randn(500, 10)
        y = np.random.randint(0, 2, 500)

        clf = RandomForestClassifier(n_estimators=10, random_state=42)

        results = cross_validate_with_purging(
            clf, X, y, n_splits=3, purge_pct=0.05, embargo_pct=0.02
        )

        # Should have test scores
        self.assertIn('test_score', results)
        self.assertGreater(len(results['test_score']), 0)

        # All scores should be between 0 and 1
        for score in results['test_score']:
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)

    def test_with_regressor(self):
        """Test cross-validation with a regressor."""
        X = np.random.randn(500, 10)
        y = np.random.randn(500)

        reg = LinearRegression()

        results = cross_validate_with_purging(
            reg, X, y, n_splits=3, purge_pct=0.05, embargo_pct=0.02
        )

        # Should have test scores
        self.assertIn('test_score', results)
        self.assertGreater(len(results['test_score']), 0)

    def test_custom_scoring(self):
        """Test with custom scoring function."""
        X = np.random.randn(500, 10)
        y = np.random.randint(0, 2, 500)

        clf = RandomForestClassifier(n_estimators=10, random_state=42)

        from sklearn.metrics import f1_score

        results = cross_validate_with_purging(
            clf, X, y, n_splits=3,
            scoring=lambda y_true, y_pred: f1_score(y_true, y_pred, average='weighted')
        )

        # Should have test scores
        self.assertIn('test_score', results)
        self.assertGreater(len(results['test_score']), 0)

    def test_with_fit_params(self):
        """Test with additional fit parameters."""
        X = np.random.randn(500, 10)
        y = np.random.randint(0, 2, 500)

        clf = RandomForestClassifier(n_estimators=10, random_state=42)

        results = cross_validate_with_purging(
            clf, X, y, n_splits=3,
            fit_params={'sample_weight': np.ones(500)}
        )

        # Should complete without error
        self.assertIn('test_score', results)


class TestLeakageDetection(unittest.TestCase):
    """Test information leakage detection."""

    def test_no_leakage_in_purged_splits(self):
        """Test that purged splits have no leakage."""
        n_samples = 1000
        X = np.random.randn(n_samples, 10)

        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(X)

        # Check each split for leakage
        for train_idx, test_idx in splits:
            # No training sample should be after any test sample
            self.assertLess(train_idx.max(), test_idx.min())

    def test_purge_zone_created(self):
        """Test that purge zone is properly created."""
        n_samples = 1000
        X = np.random.randn(n_samples, 10)

        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.10)
        splits = purged_cv.split(X)

        # Check that purge zone exists
        summary = purged_cv.get_split_summary()

        # At least some splits should have purged samples
        self.assertGreater(summary['purged_count'].sum(), 0)

    def test_embargo_zone_created(self):
        """Test that embargo zone is properly created."""
        n_samples = 1000
        X = np.random.randn(n_samples, 10)

        purged_cv = PurgedKFold(n_splits=5, embargo_pct=0.05)
        splits = purged_cv.split(X)

        # Check that embargo zone exists
        summary = purged_cv.get_split_summary()

        # All splits should have embargo
        self.assertTrue((summary['embargo_size'] > 0).all())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_very_small_dataset(self):
        """Test with a very small dataset."""
        X = np.random.randn(100, 5)

        purged_cv = PurgedKFold(
            n_splits=3,
            purge_pct=0.01,
            embargo_pct=0.01,
            min_train_samples=20,
            min_test_samples=5
        )

        splits = purged_cv.split(X)

        # Should still generate some splits
        self.assertGreater(len(splits), 0)

    def test_large_purge_embargo(self):
        """Test with large purge and embargo percentages."""
        X = np.random.randn(1000, 10)

        purged_cv = PurgedKFold(
            n_splits=3,
            purge_pct=0.20,
            embargo_pct=0.15
        )

        splits = purged_cv.split(X)

        # Should generate fewer splits due to large purge/embargo
        self.assertGreater(len(splits), 0)
        self.assertLessEqual(len(splits), 3)

    def test_single_feature(self):
        """Test with single feature dataset."""
        X = np.random.randn(500, 1)

        purged_cv = PurgedKFold(n_splits=3)
        splits = purged_cv.split(X)

        # Should handle single feature correctly
        self.assertGreater(len(splits), 0)


class TestSyntheticData(unittest.TestCase):
    """Test with synthetic time series data."""

    def test_with_autocorrelated_data(self):
        """Test with autocorrelated time series."""
        np.random.seed(42)

        # Generate autocorrelated data
        n = 500
        X = np.zeros((n, 1))
        for i in range(1, n):
            X[i] = 0.7 * X[i-1] + np.random.randn()

        purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        splits = purged_cv.split(X)

        # Should handle autocorrelated data
        self.assertGreater(len(splits), 0)

        # Validate no leakage
        self.assertTrue(purged_cv.validate_no_leakage(X))

    def test_with_trend_data(self):
        """Test with trending time series."""
        np.random.seed(42)

        # Generate trending data
        n = 500
        trend = np.linspace(0, 10, n).reshape(-1, 1)
        noise = np.random.randn(n, 1) * 0.1
        X = trend + noise

        purged_cv = PurgedKFold(n_splits=5)
        splits = purged_cv.split(X)

        # Should handle trending data
        self.assertGreater(len(splits), 0)


if __name__ == '__main__':
    unittest.main()
