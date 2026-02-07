"""
Test suite for app.backtesting.ensemble_methods

Addresses TST-005: Test coverage for ensemble methods
"""

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor

from app.backtesting.ensemble_methods import (
    BaggingConfig,
    BaggingEnsemble,
    BoostingConfig,
    BoostingEnsemble,
    EnsembleAnalyzer,
    EnsembleMethod,
    EnsembleResult,
    RandomForestEnsemble,
    StackingConfig,
    StackingEnsemble,
    bagging_ensemble,
)


class TestEnsembleMethodsImport:
    """Test module imports."""

    def test_import_ensemble_method(self):
        """Test that EnsembleMethod enum can be imported."""
        from app.backtesting.ensemble_methods import EnsembleMethod

        assert EnsembleMethod.BAGGING == "bagging"
        assert EnsembleMethod.BOOSTING == "boosting"
        assert EnsembleMethod.STACKING == "stacking"
        assert EnsembleMethod.RANDOM_FOREST == "random_forest"

    def test_import_bagging_ensemble(self):
        """Test that BaggingEnsemble can be imported."""
        from app.backtesting.ensemble_methods import BaggingEnsemble

        assert BaggingEnsemble is not None

    def test_import_boosting_ensemble(self):
        """Test that BoostingEnsemble can be imported."""
        from app.backtesting.ensemble_methods import BoostingEnsemble

        assert BoostingEnsemble is not None

    def test_import_stacking_ensemble(self):
        """Test that StackingEnsemble can be imported."""
        from app.backtesting.ensemble_methods import StackingEnsemble

        assert StackingEnsemble is not None

    def test_import_random_forest_ensemble(self):
        """Test that RandomForestEnsemble can be imported."""
        from app.backtesting.ensemble_methods import RandomForestEnsemble

        assert RandomForestEnsemble is not None

    def test_import_ensemble_analyzer(self):
        """Test that EnsembleAnalyzer can be imported."""
        from app.backtesting.ensemble_methods import EnsembleAnalyzer

        assert EnsembleAnalyzer is not None


class TestConfigurationClasses:
    """Test configuration dataclasses."""

    def test_bagging_config_default(self):
        """Test BaggingConfig with defaults."""
        config = BaggingConfig()
        assert config.n_estimators == 100
        assert config.bootstrap is True

    def test_bagging_config_custom(self):
        """Test BaggingConfig with custom values."""
        config = BaggingConfig(n_estimators=50, bootstrap=False)
        assert config.n_estimators == 50
        assert config.bootstrap is False

    def test_boosting_config_default(self):
        """Test BoostingConfig with defaults."""
        config = BoostingConfig()
        assert config.n_estimators == 100
        assert config.learning_rate == 0.1

    def test_stacking_config_initialization(self):
        """Test StackingConfig initialization."""
        base_estimators = [("lr", LinearRegression())]
        meta_estimator = Ridge()
        config = StackingConfig(base_estimators=base_estimators, meta_estimator=meta_estimator)
        assert config.base_estimators == base_estimators
        assert config.meta_estimator == meta_estimator


class TestBaggingEnsemble:
    """Test BaggingEnsemble functionality."""

    def test_initialization(self):
        """Test BaggingEnsemble initialization."""
        ensemble = BaggingEnsemble()
        assert ensemble.config.n_estimators == 100
        assert ensemble.estimator is not None

    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = BaggingConfig(n_estimators=50)
        ensemble = BaggingEnsemble(config=config)
        assert ensemble.config.n_estimators == 50

    def test_fit_and_predict(self):
        """Test fitting and prediction."""
        X, y = self._generate_test_data()
        ensemble = BaggingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        predictions = ensemble.predict(X)
        assert len(predictions) == len(y)

    def test_score(self):
        """Test scoring."""
        X, y = self._generate_test_data()
        ensemble = BaggingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        score = ensemble.score(X, y)
        assert isinstance(score, float)

    def test_get_estimator_scores(self):
        """Test getting individual estimator scores."""
        X, y = self._generate_test_data()
        ensemble = BaggingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        scores = ensemble.get_estimator_scores(X, y)
        assert len(scores) == 10

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestBoostingEnsemble:
    """Test BoostingEnsemble functionality."""

    def test_initialization(self):
        """Test BoostingEnsemble initialization."""
        ensemble = BoostingEnsemble()
        assert ensemble.config.n_estimators == 100
        assert ensemble.task_type == "auto"

    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = BoostingConfig(n_estimators=50, learning_rate=0.05)
        ensemble = BoostingEnsemble(config=config)
        assert ensemble.config.n_estimators == 50
        assert ensemble.config.learning_rate == 0.05

    def test_fit_and_predict(self):
        """Test fitting and prediction."""
        X, y = self._generate_test_data()
        ensemble = BoostingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        predictions = ensemble.predict(X)
        assert len(predictions) == len(y)

    def test_staged_predict(self):
        """Test staged predictions."""
        X, y = self._generate_test_data()
        ensemble = BoostingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        staged_preds = list(ensemble.staged_predict(X))
        assert len(staged_preds) == 10

    def test_get_feature_importance(self):
        """Test feature importance."""
        X, y = self._generate_test_data()
        ensemble = BoostingEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        importance = ensemble.get_feature_importance()
        assert len(importance) == X.shape[1]

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestStackingEnsemble:
    """Test StackingEnsemble functionality."""

    def test_initialization(self):
        """Test StackingEnsemble initialization."""
        base_estimators = [("lr", LinearRegression())]
        ensemble = StackingEnsemble(base_estimators=base_estimators)
        assert ensemble.base_estimators == base_estimators
        assert ensemble.cv == 5

    def test_initialization_with_meta_estimator(self):
        """Test initialization with meta estimator."""
        base_estimators = [("lr", LinearRegression())]
        meta_estimator = Ridge(alpha=1.0)
        ensemble = StackingEnsemble(base_estimators=base_estimators, meta_estimator=meta_estimator)
        assert ensemble.meta_estimator == meta_estimator

    def test_fit_and_predict(self):
        """Test fitting and prediction."""
        X, y = self._generate_test_data()
        base_estimators = [("lr", LinearRegression()), ("dt", DecisionTreeRegressor(max_depth=3))]
        ensemble = StackingEnsemble(base_estimators=base_estimators, cv=2)
        ensemble.fit(X, y)
        predictions = ensemble.predict(X)
        assert len(predictions) == len(y)

    def test_get_base_model_scores(self):
        """Test getting base model scores."""
        X, y = self._generate_test_data()
        base_estimators = [("lr", LinearRegression()), ("dt", DecisionTreeRegressor(max_depth=3))]
        ensemble = StackingEnsemble(base_estimators=base_estimators, cv=2)
        ensemble.fit(X, y)
        scores = ensemble.get_base_model_scores(X, y)
        assert "lr" in scores
        assert "dt" in scores

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestRandomForestEnsemble:
    """Test RandomForestEnsemble functionality."""

    def test_initialization(self):
        """Test RandomForestEnsemble initialization."""
        ensemble = RandomForestEnsemble()
        assert ensemble.n_estimators == 100
        assert ensemble.bootstrap is True

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        ensemble = RandomForestEnsemble(n_estimators=50, max_depth=5, bootstrap=False)
        assert ensemble.n_estimators == 50
        assert ensemble.max_depth == 5
        assert ensemble.bootstrap is False

    def test_fit_and_predict(self):
        """Test fitting and prediction."""
        X, y = self._generate_test_data()
        ensemble = RandomForestEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        predictions = ensemble.predict(X)
        assert len(predictions) == len(y)

    def test_score(self):
        """Test scoring."""
        X, y = self._generate_test_data()
        ensemble = RandomForestEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        score = ensemble.score(X, y)
        assert isinstance(score, float)

    def test_get_feature_importance(self):
        """Test feature importance."""
        X, y = self._generate_test_data()
        ensemble = RandomForestEnsemble(n_estimators=10)
        ensemble.fit(X, y)
        importance = ensemble.get_feature_importance()
        assert len(importance) == X.shape[1]

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestEnsembleAnalyzer:
    """Test EnsembleAnalyzer functionality."""

    def test_initialization(self):
        """Test EnsembleAnalyzer initialization."""
        analyzer = EnsembleAnalyzer()
        assert analyzer.test_size == 0.2
        assert analyzer.random_state == 42

    def test_analyze_bagging(self):
        """Test bagging analysis."""
        X, y = self._generate_test_data()
        estimator = DecisionTreeRegressor()
        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_bagging(estimator, X, y, n_estimators=10)
        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.BAGGING

    def test_analyze_boosting(self):
        """Test boosting analysis."""
        X, y = self._generate_test_data()
        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_boosting(X, y, n_estimators=10)
        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.GRADIENT_BOOSTING

    def test_analyze_stacking(self):
        """Test stacking analysis."""
        X, y = self._generate_test_data()
        base_estimators = [("lr", LinearRegression()), ("dt", DecisionTreeRegressor(max_depth=3))]
        analyzer = EnsembleAnalyzer()
        result = analyzer.analyze_stacking(base_estimators, X, y)
        assert isinstance(result, EnsembleResult)
        assert result.method == EnsembleMethod.STACKING

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_bagging_ensemble_function(self):
        """Test bagging_ensemble convenience function."""
        X, y = self._generate_test_data()
        ensemble, result = bagging_ensemble(X, y, n_estimators=10)
        assert ensemble is not None
        assert isinstance(result, EnsembleResult)

    def _generate_test_data(self):
        """Generate simple test data."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.sum(X, axis=1) + np.random.randn(100) * 0.1
        return X, y


class TestEnsembleResult:
    """Test EnsembleResult dataclass."""

    def test_ensemble_result_to_dict(self):
        """Test EnsembleResult.to_dict method."""
        from datetime import datetime

        result = EnsembleResult(
            timestamp=datetime.now(),
            method=EnsembleMethod.BAGGING,
            n_estimators=10,
            train_score=0.9,
            test_score=0.85,
            estimator_scores=[0.8, 0.85, 0.9],
            ensemble_improvement=0.05,
            diversity=0.3,
            model_name="DecisionTreeRegressor",
        )
        result_dict = result.to_dict()
        assert "method" in result_dict
        assert "n_estimators" in result_dict
        assert result_dict["method"] == "bagging"
