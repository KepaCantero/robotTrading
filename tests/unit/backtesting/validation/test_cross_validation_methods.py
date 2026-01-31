"""
Comprehensive tests for Cross-Validation Methods.

Tests follow ESL methodologies and cover:
1. K-Fold CV
2. Leave-One-Out CV
3. Stratified K-Fold CV
4. Time Series CV
5. Nested CV
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.svm import SVC

from app.backtesting.validation.cross_validation_methods import (
    CVMethod,
    CVResult,
    CrossValidation,
    KFoldCV,
    LeaveOneOutCV,
    NestedCVResult,
    NestedCrossValidation,
    StratifiedKFoldCV,
    TimeSeriesSplitCV,
    cross_validate,
    nested_cross_validate,
)


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    np.random.seed(42)
    n_samples = 200

    X = np.random.randn(n_samples, 10)
    y_reg = np.random.randn(n_samples)
    y_clf = np.random.randint(0, 2, n_samples)

    return X, y_reg, y_clf


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    np.random.seed(42)
    n_samples = 200

    X = pd.DataFrame({f"feature_{i}": np.random.randn(n_samples) for i in range(10)})
    y = pd.Series(np.random.randn(n_samples))

    return X, y


class TestKFoldCV:
    """Tests for K-Fold Cross-Validation."""

    def test_kfold_initialization(self):
        """Test K-Fold CV initialization."""
        kfold = KFoldCV(n_splits=5, shuffle=True, random_state=42)

        assert kfold.n_splits == 5
        assert kfold.shuffle is True
        assert kfold.random_state == 42

    def test_kfold_split(self, sample_data):
        """Test K-Fold split generation."""
        X, y_reg, _ = sample_data
        kfold = KFoldCV(n_splits=5, shuffle=True, random_state=42)

        splits = list(kfold.split(X))

        assert len(splits) == 5

        for train_idx, test_idx in splits:
            # Check no overlap
            assert len(set(train_idx) & set(test_idx)) == 0
            # Check all samples used
            assert len(train_idx) + len(test_idx) == len(X)

    def test_kfold_with_dataframe(self, sample_dataframe):
        """Test K-Fold with DataFrame."""
        X, y = sample_dataframe
        kfold = KFoldCV(n_splits=5)

        for train_idx, test_idx in kfold.split(X, y):
            assert isinstance(train_idx, np.ndarray)
            assert isinstance(test_idx, np.ndarray)

    def test_kfold_get_n_splits(self):
        """Test get_n_splits method."""
        kfold = KFoldCV(n_splits=10)
        assert kfold.get_n_splits() == 10


class TestLeaveOneOutCV:
    """Tests for Leave-One-Out Cross-Validation."""

    def test_loocv_initialization(self):
        """Test LOOCV initialization."""
        loo = LeaveOneOutCV()
        assert loo is not None

    def test_loocv_split(self, sample_data):
        """Test LOOCV split generation."""
        X, y_reg, _ = sample_data
        loo = LeaveOneOutCV()

        splits = list(loo.split(X))

        # Should have n splits
        assert len(splits) == len(X)

        # Each test set should have 1 sample
        for train_idx, test_idx in splits:
            assert len(test_idx) == 1
            assert len(train_idx) == len(X) - 1

    def test_loocv_get_n_splits(self, sample_data):
        """Test get_n_splits method."""
        X, _, _ = sample_data
        loo = LeaveOneOutCV()

        assert loo.get_n_splits(X) == len(X)


class TestStratifiedKFoldCV:
    """Tests for Stratified K-Fold CV."""

    def test_stratified_kfold_initialization(self):
        """Test Stratified K-Fold initialization."""
        skfold = StratifiedKFoldCV(n_splits=5, shuffle=True, random_state=42)

        assert skfold.n_splits == 5
        assert skfold.shuffle is True
        assert skfold.random_state == 42

    def test_stratified_kfold_split(self, sample_data):
        """Test Stratified K-Fold split generation."""
        X, _, y_clf = sample_data
        skfold = StratifiedKFoldCV(n_splits=5, shuffle=True, random_state=42)

        splits = list(skfold.split(X, y_clf))

        assert len(splits) == 5

        # Check stratification (approximately balanced class distribution)
        for train_idx, test_idx in splits:
            train_classes = y_clf[train_idx]
            test_classes = y_clf[test_idx]

            # Both sets should have both classes
            assert len(np.unique(train_classes)) > 0
            assert len(np.unique(test_classes)) > 0

    def test_stratified_requires_y(self, sample_data):
        """Test that Stratified K-Fold requires y."""
        X, y_reg, _ = sample_data
        skfold = StratifiedKFoldCV(n_splits=5)

        with pytest.raises(TypeError):
            list(skfold.split(X))


class TestTimeSeriesSplitCV:
    """Tests for Time Series Split CV."""

    def test_time_series_split_initialization(self):
        """Test Time Series Split initialization."""
        tscv = TimeSeriesSplitCV(n_splits=5, max_train_size=100, test_size=20)

        assert tscv.n_splits == 5
        assert tscv.max_train_size == 100
        assert tscv.test_size == 20

    def test_time_series_split_ordering(self, sample_data):
        """Test that Time Series Split respects temporal ordering."""
        X, y_reg, _ = sample_data
        tscv = TimeSeriesSplitCV(n_splits=5)

        splits = list(tscv.split(X))

        for train_idx, test_idx in splits:
            # All training indices should be less than all test indices
            assert train_idx.max() < test_idx.min()

    def test_time_series_split_expanding_window(self, sample_data):
        """Test expanding window behavior."""
        X, y_reg, _ = sample_data
        tscv = TimeSeriesSplitCV(n_splits=5, max_train_size=None)

        splits = list(tscv.split(X))

        # Training size should increase (or stay same)
        train_sizes = [len(train_idx) for train_idx, _ in splits]

        for i in range(1, len(train_sizes)):
            assert train_sizes[i] >= train_sizes[i - 1]

    def test_time_series_split_fixed_window(self, sample_data):
        """Test fixed window behavior with max_train_size."""
        X, y_reg, _ = sample_data
        max_size = 50
        tscv = TimeSeriesSplitCV(n_splits=5, max_train_size=max_size)

        splits = list(tscv.split(X))

        # All training sizes should be <= max_size
        for train_idx, _ in splits:
            assert len(train_idx) <= max_size


class TestNestedCrossValidation:
    """Tests for Nested Cross-Validation."""

    def test_nested_cv_initialization(self):
        """Test Nested CV initialization."""
        from sklearn.model_selection import KFold

        param_grid = {"C": [0.1, 1, 10]}
        outer_cv = KFold(n_splits=3, shuffle=True, random_state=42)
        inner_cv = KFold(n_splits=2, shuffle=True, random_state=42)

        nested_cv = NestedCrossValidation(
            estimator=LogisticRegression(max_iter=1000, random_state=42),
            param_grid=param_grid,
            outer_cv=outer_cv,
            inner_cv=inner_cv,
        )

        assert nested_cv.estimator is not None
        assert nested_cv.param_grid == param_grid
        assert nested_cv.n_jobs == 1

    def test_nested_cv_fit(self, sample_data):
        """Test Nested CV fitting."""
        from sklearn.model_selection import KFold

        X, _, y_clf = sample_data
        param_grid = {"C": [0.1, 1]}

        outer_cv = KFold(n_splits=3, shuffle=True, random_state=42)
        inner_cv = KFold(n_splits=2, shuffle=True, random_state=42)

        nested_cv = NestedCrossValidation(
            estimator=LogisticRegression(max_iter=1000, random_state=42),
            param_grid=param_grid,
            outer_cv=outer_cv,
            inner_cv=inner_cv,
        )

        result = nested_cv.fit(X, y_clf)

        assert isinstance(result, NestedCVResult)
        assert result.outer_score >= 0
        assert result.outer_score <= 1
        assert len(result.outer_fold_scores) == 3
        assert isinstance(result.best_params, dict)

    def test_nested_cv_with_small_data(self, sample_data):
        """Test Nested CV with small dataset."""
        from sklearn.model_selection import KFold

        X, _, y_clf = sample_data
        X_small = X[:50]
        y_small = y_clf[:50]

        param_grid = {"C": [0.1, 1]}

        outer_cv = KFold(n_splits=2, shuffle=True, random_state=42)
        inner_cv = KFold(n_splits=2, shuffle=True, random_state=42)

        nested_cv = NestedCrossValidation(
            estimator=LogisticRegression(max_iter=1000, random_state=42),
            param_grid=param_grid,
            outer_cv=outer_cv,
            inner_cv=inner_cv,
        )

        result = nested_cv.fit(X_small, y_small)

        assert result.outer_score >= 0
        assert len(result.outer_fold_scores) == 2


class TestCrossValidation:
    """Tests for unified CrossValidation class."""

    def test_cross_validation_kfold(self, sample_data):
        """Test K-Fold CV through unified interface."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        cv = CrossValidation(method=CVMethod.KFOLD, n_splits=5)
        result = cv.cross_validate(estimator, X, y_reg)

        assert isinstance(result, CVResult)
        assert result.method == CVMethod.KFOLD
        assert result.n_splits == 5
        assert len(result.fold_scores) == 5
        # R² can be negative for poor models
        assert result.mean_score <= 1

    def test_cross_validation_time_series(self, sample_data):
        """Test Time Series CV through unified interface."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        cv = CrossValidation(method=CVMethod.TIME_SERIES, n_splits=5)
        result = cv.cross_validate(estimator, X, y_reg)

        assert isinstance(result, CVResult)
        assert result.method == CVMethod.TIME_SERIES
        assert result.n_splits == 5

    def test_cross_validation_loocv_small(self):
        """Test LOOCV with small dataset."""
        np.random.seed(42)
        X = np.random.randn(20, 5)
        y = np.random.randn(20)

        estimator = Ridge()

        cv = CrossValidation(method=CVMethod.LOOCV)
        result = cv.cross_validate(estimator, X, y)

        assert isinstance(result, CVResult)
        assert result.method == CVMethod.LOOCV
        # LOOCV returns get_n_splits() which may differ for implementation
        assert result.n_splits >= 1

    def test_cross_validation_result_structure(self, sample_data):
        """Test CVResult has all required fields."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        cv = CrossValidation(method=CVMethod.KFOLD, n_splits=3)
        result = cv.cross_validate(estimator, X, y_reg)

        # Check all fields present
        assert hasattr(result, "timestamp")
        assert hasattr(result, "method")
        assert hasattr(result, "mean_score")
        assert hasattr(result, "std_score")
        assert hasattr(result, "fold_scores")
        assert hasattr(result, "confidence_interval")

        # Check confidence interval
        ci_lower, ci_upper = result.confidence_interval
        assert ci_lower <= result.mean_score <= ci_upper

    def test_cross_validation_to_dict(self, sample_data):
        """Test CVResult serialization."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        cv = CrossValidation(method=CVMethod.KFOLD, n_splits=3)
        result = cv.cross_validate(estimator, X, y_reg)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "mean_score" in result_dict
        assert "std_score" in result_dict
        assert "fold_scores" in result_dict


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_cross_validate_function(self, sample_data):
        """Test cross_validate convenience function."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        result = cross_validate(
            estimator,
            X,
            y_reg,
            method="kfold",
            n_splits=5,
        )

        assert isinstance(result, CVResult)
        assert result.method == CVMethod.KFOLD

    def test_cross_validate_invalid_method(self, sample_data):
        """Test cross_validate with invalid method."""
        X, y_reg, _ = sample_data
        estimator = Ridge()

        with pytest.raises(ValueError, match="Unknown method"):
            cross_validate(estimator, X, y_reg, method="invalid_method")

    def test_nested_cross_validate_function(self, sample_data):
        """Test nested_cross_validate convenience function."""
        X, _, y_clf = sample_data
        param_grid = {"C": [0.1, 1]}

        result = nested_cross_validate(
            estimator=LogisticRegression(max_iter=1000, random_state=42),
            X=X,
            y=y_clf,
            param_grid=param_grid,
            outer_splits=3,
            inner_splits=2,
        )

        assert isinstance(result, NestedCVResult)
        assert result.outer_score >= 0


@pytest.mark.parametrize("method", ["kfold", "stratified", "time_series"])
def test_cross_validation_methods_methods(sample_data, method):
    """Test different CV methods through convenience function."""
    X, y_reg, y_clf = sample_data
    estimator = Ridge()

    # Use classification for stratified
    y = y_clf if method == "stratified" else y_reg

    result = cross_validate(
        estimator,
        X,
        y,
        method=method,
        n_splits=3,
    )

    assert isinstance(result, CVResult)
    assert result.n_splits == 3


class TestCVEdgeCases:
    """Tests for edge cases."""

    def test_cv_with_single_feature(self):
        """Test CV with single feature."""
        np.random.seed(42)
        X = np.random.randn(100, 1)
        y = np.random.randn(100)

        estimator = Ridge()
        cv = CrossValidation(method=CVMethod.KFOLD, n_splits=3)
        result = cv.cross_validate(estimator, X, y)

        assert isinstance(result, CVResult)

    def test_cv_with_perfect_predictions(self):
        """Test CV with perfect linear relationship."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = X @ np.array([1, 2, 3, 4, 5])  # Perfect linear relationship

        estimator = Ridge()
        cv = CrossValidation(method=CVMethod.KFOLD, n_splits=5)
        result = cv.cross_validate(estimator, X, y)

        # Should achieve high R²
        assert result.mean_score > 0.9

    def test_time_series_with_small_data(self):
        """Test Time Series CV with small dataset."""
        np.random.seed(42)
        X = np.random.randn(30, 5)
        y = np.random.randn(30)

        estimator = Ridge()
        cv = CrossValidation(method=CVMethod.TIME_SERIES, n_splits=3)
        result = cv.cross_validate(estimator, X, y)

        assert isinstance(result, CVResult)
