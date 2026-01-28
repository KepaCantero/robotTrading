"""
Comprehensive tests for Ensemble Methods.

Tests follow ESL methodologies and cover:
1. Bagging
2. Boosting
3. Stacking
4. Random Forest
5. Ensemble Comparison
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.backtesting.ensemble_methods import (
    BaggingConfig,
    BaggingEnsemble,
    BoostingConfig,
    BoostingEnsemble,
    BoostingEnsemble,
    EnsembleAnalyzer,
    EnsembleMethod,
    EnsembleResult,
    RandomForestEnsemble,
    StackingConfig,
    StackingEnsemble,
    bagging_ensemble,
    stacking_ensemble,
)


@pytest.fixture
def sample_regression_data():
    """Create sample regression data."""
    np.random.seed(42)
    n_samples = 300

    X = np.random.randn(n_samples, 10)
    y = X @ np.array([1, 2, 0.5, -1, 0, 0, 0, 0, 0, 0]) + np.random.randn(n_samples) * 0.5

    return X, y


@pytest.fixture
def sample_classification_data():
    """Create sample classification data."""
    np.random.seed(42)
    n_samples = 300

    X = np.random.randn(n_samples, 10)
    # Simple linear decision boundary
    z = X @ np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    y = (z > 0).astype(int)

    return X, y


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame."""
    np.random.seed(42)
    n_samples = 300

    X = pd.DataFrame({
        f"feature_{i}": np.random.randn(n_samples)
        for i in range(10)
    })
    y = pd.Series(np.random.randn(n_samples))

    return X, y


class TestBaggingEnsemble:
    """Tests for Bagging Ensemble."""

    def test_bagging_initialization(self):
        """Test Bagging initialization."""
        estimator = DecisionTreeRegressor()
        config = BaggingConfig(n_estimators=50)

        bagging = BaggingEnsemble(estimator=estimator, config=config)

        assert bagging.estimator == estimator
        assert bagging.config.n_estimators == 50

    def test_bagging_fit(self, sample_regression_data):
        """Test Bagging fitting."""
        X, y = sample_regression_data
        estimator = DecisionTreeRegressor()

        bagging = BaggingEnsemble(estimator=estimator)
        bagging.fit(X, y)

        assert hasattr(bagging, "bagger_")
        assert hasattr(bagging, "bagger_")

    def test_bagging_predict(self, sample_regression_data):
        """Test Bagging prediction."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        estimator = DecisionTreeRegressor()
        bagging = BaggingEnsemble(estimator=estimator)
        bagging.fit(X_train, y_train)

        y_pred = bagging.predict(X_test)

        assert len(y_pred) == len(X_test)
        assert isinstance(y_pred, np.ndarray)

    def test_bagging_score(self, sample_regression_data):
        """Test Bagging scoring."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train, y_test = y[:250], y[250:]

        estimator = DecisionTreeRegressor()
        bagging = BaggingEnsemble(estimator=estimator)
        bagging.fit(X_train, y_train)

        train_score = bagging.score(X_train, y_train)
        test_score = bagging.score(X_test, y_test)

        # R² score should be between -inf and 1
        assert train_score <= 1
        assert test_score <= 1

    def test_bagging_get_estimator_scores(self, sample_regression_data):
        """Test getting individual estimator scores."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train, y_test = y[:250], y[250:]

        estimator = DecisionTreeRegressor()
        bagging = BaggingEnsemble(estimator=estimator, config=BaggingConfig(n_estimators=10))
        bagging.fit(X_train, y_train)

        scores = bagging.get_estimator_scores(X_test, y_test)

        assert len(scores) == 10
        assert all(isinstance(s, (float, np.floating)) for s in scores)

    def test_bagging_oob_score(self, sample_regression_data):
        """Test OOB score computation."""
        X, y = sample_regression_data

        estimator = DecisionTreeRegressor()
        config = BaggingConfig(n_estimators=50, bootstrap=True)
        bagging = BaggingEnsemble(estimator=estimator, config=config)
        bagging.fit(X, y)

        oob_score = bagging.get_oob_score()

        # OOB score might be None or a float
        assert oob_score is None or isinstance(oob_score, (float, np.floating))


class TestBoostingEnsemble:
    """Tests for Boosting Ensemble."""

    def test_boosting_initialization(self):
        """Test Boosting initialization."""
        config = BoostingConfig(n_estimators=50, learning_rate=0.1)

        boosting = BoostingEnsemble(config=config, task_type="regression")

        assert boosting.config.n_estimators == 50
        assert boosting.config.learning_rate == 0.1

    def test_boosting_fit_regression(self, sample_regression_data):
        """Test Boosting for regression."""
        X, y = sample_regression_data

        boosting = BoostingEnsemble(task_type="regression")
        boosting.fit(X, y)

        assert hasattr(boosting, "booster_")

    def test_boosting_fit_classification(self, sample_classification_data):
        """Test Boosting for classification."""
        X, y = sample_classification_data

        boosting = BoostingEnsemble(task_type="classification")
        boosting.fit(X, y)

        assert hasattr(boosting, "booster_")

    def test_boosting_predict(self, sample_regression_data):
        """Test Boosting prediction."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        boosting = BoostingEnsemble(task_type="regression")
        boosting.fit(X_train, y_train)

        y_pred = boosting.predict(X_test)

        assert len(y_pred) == len(X_test)

    def test_boosting_staged_predict(self, sample_regression_data):
        """Test staged predictions."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        boosting = BoostingEnsemble(
            config=BoostingConfig(n_estimators=10),
            task_type="regression"
        )
        boosting.fit(X_train, y_train)

        staged_preds = list(boosting.staged_predict(X_test))

        assert len(staged_preds) == 10
        assert all(len(pred) == len(X_test) for pred in staged_preds)

    def test_boosting_feature_importance(self, sample_regression_data):
        """Test feature importance."""
        X, y = sample_regression_data

        boosting = BoostingEnsemble(task_type="regression")
        boosting.fit(X, y)

        importance = boosting.get_feature_importance()

        assert len(importance) == X.shape[1]
        assert all(imp >= 0 for imp in importance)


class TestStackingEnsemble:
    """Tests for Stacking Ensemble."""

    def test_stacking_initialization(self):
        """Test Stacking initialization."""
        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)

        assert len(stacking.base_estimators) == 2

    def test_stacking_fit(self, sample_regression_data):
        """Test Stacking fitting."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)
        stacking.fit(X_train, y_train)

        assert hasattr(stacking, "stacker_")

    def test_stacking_predict(self, sample_regression_data):
        """Test Stacking prediction."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)
        stacking.fit(X_train, y_train)

        y_pred = stacking.predict(X_test)

        assert len(y_pred) == len(X_test)

    def test_stacking_score(self, sample_regression_data):
        """Test Stacking scoring."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train, y_test = y[:250], y[250:]

        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)
        stacking.fit(X_train, y_train)

        score = stacking.score(X_test, y_test)

        assert isinstance(score, float)

    def test_stacking_get_base_model_scores(self, sample_regression_data):
        """Test getting individual base model scores."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train, y_test = y[:250], y[250:]

        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)
        stacking.fit(X_train, y_train)

        base_scores = stacking.get_base_model_scores(X_test, y_test)

        assert "lr" in base_scores
        assert "ridge" in base_scores
        assert all(isinstance(s, (float, np.floating)) for s in base_scores.values())


class TestRandomForestEnsemble:
    """Tests for Random Forest Ensemble."""

    def test_rf_initialization(self):
        """Test Random Forest initialization."""
        rf = RandomForestEnsemble(
            n_estimators=50,
            max_depth=5,
            random_state=42,
        )

        assert rf.n_estimators == 50
        assert rf.max_depth == 5

    def test_rf_fit(self, sample_regression_data):
        """Test Random Forest fitting."""
        X, y = sample_regression_data

        rf = RandomForestEnsemble(n_estimators=50, random_state=42)
        rf.fit(X, y)

        assert hasattr(rf, "rf_")

    def test_rf_predict(self, sample_regression_data):
        """Test Random Forest prediction."""
        X, y = sample_regression_data
        X_train, X_test = X[:250], X[250:]
        y_train = y[:250]

        rf = RandomForestEnsemble(n_estimators=50, random_state=42)
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)

        assert len(y_pred) == len(X_test)

    def test_rf_feature_importance(self, sample_regression_data):
        """Test feature importance."""
        X, y = sample_regression_data

        rf = RandomForestEnsemble(n_estimators=50, random_state=42)
        rf.fit(X, y)

        importance = rf.get_feature_importance()

        assert len(importance) == X.shape[1]
        assert all(imp >= 0 for imp in importance)

    def test_rf_oob_score(self, sample_regression_data):
        """Test OOB score."""
        X, y = sample_regression_data

        rf = RandomForestEnsemble(
            n_estimators=50,
            bootstrap=True,
            oob_score=True,
            random_state=42,
        )
        rf.fit(X, y)

        oob_score = rf.get_oob_score()

        assert oob_score is not None
        assert isinstance(oob_score, (float, np.floating))


class TestEnsembleAnalyzer:
    """Tests for EnsembleAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = EnsembleAnalyzer(test_size=0.2, random_state=42)

        assert analyzer.test_size == 0.2
        assert analyzer.random_state == 42

    def test_analyze_bagging(self, sample_regression_data):
        """Test bagging analysis."""
        X, y = sample_regression_data
        estimator = DecisionTreeRegressor()

        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_bagging(estimator, X, y, n_estimators=20)

        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.BAGGING
        assert result.n_estimators == 20

    def test_analyze_boosting(self, sample_regression_data):
        """Test boosting analysis."""
        X, y = sample_regression_data

        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_boosting(X, y, n_estimators=20)

        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.GRADIENT_BOOSTING
        assert result.n_estimators == 20

    def test_analyze_stacking(self, sample_regression_data):
        """Test stacking analysis."""
        X, y = sample_regression_data
        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_stacking(base_estimators, X, y)

        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.STACKING

    def test_compare_ensembles(self, sample_regression_data):
        """Test comparing ensemble methods."""
        X, y = sample_regression_data

        analyzer = EnsembleAnalyzer()
        results = analyzer.compare_ensembles(
            X, y,
            base_estimator=DecisionTreeRegressor(),
            n_estimators=20,
        )

        assert "bagging" in results
        assert "boosting" in results

    def test_result_to_dict(self, sample_regression_data):
        """Test EnsembleResult serialization."""
        X, y = sample_regression_data
        estimator = DecisionTreeRegressor()

        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_bagging(estimator, X, y, n_estimators=10)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "method" in result_dict
        assert "n_estimators" in result_dict
        assert "test_score" in result_dict


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_bagging_ensemble_function(self, sample_regression_data):
        """Test bagging_ensemble convenience function."""
        X, y = sample_regression_data

        ensemble, result = bagging_ensemble(X, y, n_estimators=20)

        assert hasattr(ensemble, "bagger_")
        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.BAGGING

    def test_stacking_ensemble_function(self, sample_regression_data):
        """Test stacking_ensemble convenience function."""
        X, y = sample_regression_data
        base_estimators = [
            ("lr", LinearRegression()),
            ("ridge", Ridge()),
        ]

        ensemble, result = stacking_ensemble(X, y, base_estimators)

        assert hasattr(ensemble, "stacker_")
        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.STACKING


class TestEnsembleEdgeCases:
    """Tests for edge cases."""

    def test_bagging_with_single_estimator(self, sample_regression_data):
        """Test bagging with n_estimators=1."""
        X, y = sample_regression_data
        estimator = DecisionTreeRegressor()

        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_bagging(estimator, X, y, n_estimators=1)

        # Should work but with minimal improvement
        assert isinstance(result, EnsembleResult)

    def test_boosting_low_learning_rate(self, sample_regression_data):
        """Test boosting with very low learning rate."""
        X, y = sample_regression_data

        config = BoostingConfig(
            n_estimators=20,
            learning_rate=0.01,  # Very low
        )

        boosting = BoostingEnsemble(config=config, task_type="regression")
        boosting.fit(X, y)

        # Should still work
        assert hasattr(boosting, "booster_")

    def test_stacking_with_single_base_model(self, sample_regression_data):
        """Test stacking with only one base model."""
        X, y = sample_regression_data
        base_estimators = [
            ("lr", LinearRegression()),
        ]

        stacking = StackingEnsemble(base_estimators=base_estimators)

        # Should still work (though not ideal)
        stacking.fit(X, y)
        assert hasattr(stacking, "stacker_")

    def test_ensemble_with_small_data(self):
        """Test ensembles with small dataset."""
        np.random.seed(42)
        X = np.random.randn(50, 5)
        y = np.random.randn(50)

        # Bagging should handle small data
        estimator = DecisionTreeRegressor()
        bagging = BaggingEnsemble(estimator=estimator, config=BaggingConfig(n_estimators=10))
        bagging.fit(X, y)

        assert hasattr(bagging, "bagger_")

    def test_rf_with_max_depth_1(self, sample_regression_data):
        """Test Random Forest with very shallow trees."""
        X, y = sample_regression_data

        rf = RandomForestEnsemble(
            n_estimators=50,
            max_depth=1,  # Stumps
            random_state=42,
        )
        rf.fit(X, y)

        # Should work but with limited capacity
        assert hasattr(rf, "rf_")


@pytest.mark.parametrize("n_estimators", [10, 50, 100])
def test_bagging_different_sizes(sample_regression_data, n_estimators):
    """Test bagging with different numbers of estimators."""
    X, y = sample_regression_data
    estimator = DecisionTreeRegressor()

    analyzer = EnsembleAnalyzer()
    result = analyzer.analyze_bagging(estimator, X, y, n_estimators=n_estimators)

    assert result.n_estimators == n_estimators
    assert isinstance(result, EnsembleResult)


@pytest.mark.parametrize("max_depth", [1, 3, 5, None])
def test_boosting_different_depths(sample_regression_data, max_depth):
    """Test boosting with different tree depths."""
    X, y = sample_regression_data

    config = BoostingConfig(
        n_estimators=20,
        max_depth=max_depth,
    )

    boosting = BoostingEnsemble(config=config, task_type="regression")
    boosting.fit(X, y)

    assert hasattr(boosting, "booster_")
