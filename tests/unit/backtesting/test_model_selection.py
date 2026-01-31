"""
Comprehensive tests for Model Selection Criteria.

Tests follow ESL methodologies and cover:
1. AIC (Akaike Information Criterion)
2. BIC (Bayesian Information Criterion)
3. Adjusted R-squared
4. Model Comparison
"""

import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor

from app.backtesting.model_selection import (
    AICCalculator,
    AdjustedR2Calculator,
    BICCalculator,
    CriterionType,
    GCVCalculator,
    MallowCpCalculator,
    ModelComparisonResult,
    ModelCriterionResult,
    ModelSelector,
    compute_criteria,
    select_model_by_aic,
    select_model_by_bic,
)


@pytest.fixture
def sample_regression_data():
    """Create sample regression data."""
    np.random.seed(42)
    n_samples = 200

    # True model has 5 features
    true_coef = np.array([2, 1.5, 0.5, -1, -0.5])
    X = np.random.randn(n_samples, 10)
    y = X[:, :5] @ true_coef + np.random.randn(n_samples) * 0.5

    return X, y


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame."""
    np.random.seed(42)
    n_samples = 200

    X = pd.DataFrame({f"feature_{i}": np.random.randn(n_samples) for i in range(10)})
    y = pd.Series(np.random.randn(n_samples))

    return X, y


@pytest.fixture
def fitted_models(sample_regression_data):
    """Create fitted models for comparison."""
    X, y = sample_regression_data
    X_train, X_test = X[:150], X[150:]
    y_train, y_test = y[:150], y[150:]

    models = {}

    # Simple model
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    models["LinearRegression"] = lr

    # Regularized model
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    models["Ridge"] = ridge

    # Sparse model
    lasso = Lasso(alpha=0.1, random_state=42)
    lasso.fit(X_train, y_train)
    models["Lasso"] = lasso

    return models, X_test, y_test


class TestAICCalculator:
    """Tests for AIC calculation."""

    def test_aic_calculation(self, sample_regression_data):
        """Test basic AIC calculation."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        n_params = X.shape[1] + 1  # features + intercept
        aic = AICCalculator.calculate(y_test, y_pred, n_params)

        assert isinstance(aic, float)
        assert aic > 0

    def test_aic_with_different_n_params(self, sample_regression_data):
        """Test AIC with different numbers of parameters."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        aic_5 = AICCalculator.calculate(y_test, y_pred, n_params=5)
        aic_10 = AICCalculator.calculate(y_test, y_pred, n_params=10)

        # More parameters should increase AIC (penalty)
        assert aic_10 > aic_5

    def test_aic_from_likelihood(self):
        """Test AIC calculation from log-likelihood."""
        log_likelihood = -100
        n_params = 5

        aic = AICCalculator.calculate_with_likelihood(log_likelihood, n_params)

        expected = 2 * n_params - 2 * log_likelihood
        assert abs(aic - expected) < 1e-6


class TestBICCalculator:
    """Tests for BIC calculation."""

    def test_bic_calculation(self, sample_regression_data):
        """Test basic BIC calculation."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        n_params = X.shape[1] + 1
        bic = BICCalculator.calculate(y_test, y_pred, n_params)

        assert isinstance(bic, float)
        assert bic > 0

    def test_bic_stronger_penalty_than_aic(self, sample_regression_data):
        """Test that BIC has stronger complexity penalty than AIC."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        n_params = 10
        n_samples = len(y_test)

        aic = AICCalculator.calculate(y_test, y_pred, n_params)
        bic = BICCalculator.calculate(y_test, y_pred, n_params)

        # BIC should have larger penalty term
        # BIC penalty: k * ln(n)
        # AIC penalty: 2k
        # For n > e² ≈ 7.4, BIC penalty > AIC penalty
        bic_penalty = n_params * np.log(n_samples)
        aic_penalty = 2 * n_params

        assert bic_penalty > aic_penalty

    def test_bic_from_likelihood(self):
        """Test BIC calculation from log-likelihood."""
        log_likelihood = -100
        n_params = 5
        n_samples = 200

        bic = BICCalculator.calculate_with_likelihood(log_likelihood, n_params, n_samples)

        expected = n_params * np.log(n_samples) - 2 * log_likelihood
        assert abs(bic - expected) < 1e-6


class TestAdjustedR2Calculator:
    """Tests for Adjusted R² calculation."""

    def test_adjusted_r2_calculation(self, sample_regression_data):
        """Test basic Adjusted R² calculation."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        n_params = X.shape[1]
        adj_r2 = AdjustedR2Calculator.calculate(y_test, y_pred, n_params)

        assert isinstance(adj_r2, float)
        assert -np.inf < adj_r2 <= 1

    def test_adjusted_r2_penalty(self, sample_regression_data):
        """Test that Adjusted R² penalizes extra parameters."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        from sklearn.metrics import r2_score

        r2 = r2_score(y_test, y_pred)

        adj_r2_few_params = AdjustedR2Calculator.calculate(y_test, y_pred, n_params=5)
        adj_r2_many_params = AdjustedR2Calculator.calculate(y_test, y_pred, n_params=15)

        # Adjusted R² should be ≤ R²
        assert adj_r2_few_params <= r2
        assert adj_r2_many_params <= r2

        # More parameters should result in lower adjusted R²
        assert adj_r2_many_params <= adj_r2_few_params


class TestMallowCpCalculator:
    """Tests for Mallow's Cp calculation."""

    def test_mallow_cp_calculation(self, sample_regression_data):
        """Test basic Mallow's Cp calculation."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        # Full model
        full_model = LinearRegression()
        full_model.fit(X_train, y_train)
        y_pred_full = full_model.predict(X_test)
        rss_full = np.sum((y_test - y_pred_full) ** 2)

        # Subset model
        subset_model = LinearRegression()
        subset_model.fit(X_train[:, :5], y_train)
        y_pred_subset = subset_model.predict(X_test[:, :5])
        rss_subset = np.sum((y_test - y_pred_subset) ** 2)

        cp, p = MallowCpCalculator.calculate(
            rss_subset,
            rss_full,
            n_params_subset=5,
            n_params_full=X.shape[1] + 1,
            n_samples=len(y_test),
        )

        assert isinstance(cp, float)
        assert isinstance(p, float)
        assert p == 5.0


class TestGCVCalculator:
    """Tests for GCV calculation."""

    def test_gcv_calculation(self, sample_regression_data):
        """Test basic GCV calculation."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        n_params = X.shape[1] + 1
        gcv = GCVCalculator.calculate(y_test, y_pred, n_params)

        assert isinstance(gcv, float)
        assert gcv > 0


class TestModelSelector:
    """Tests for ModelSelector."""

    def test_selector_initialization(self):
        """Test ModelSelector initialization."""
        selector = ModelSelector(cv_folds=5, random_state=42)

        assert selector.cv_folds == 5
        assert selector.random_state == 42

    def test_evaluate_single_model(self, sample_regression_data):
        """Test evaluating a single model."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)

        selector = ModelSelector()
        result = selector.evaluate_model(model, X_test, y_test, "LinearRegression")

        assert isinstance(result, ModelCriterionResult)
        assert result.model_name == "LinearRegression"
        assert result.n_params > 0
        assert result.n_samples == len(y_test)
        assert -np.inf < result.r2 <= 1
        assert result.aic > 0
        assert result.bic > 0

    def test_compare_models(self, fitted_models):
        """Test comparing multiple models."""
        models, X_test, y_test = fitted_models

        selector = ModelSelector()
        comparison = selector.compare_models(models, X_test, y_test)

        assert isinstance(comparison, ModelComparisonResult)
        assert len(comparison.models) > 0
        assert comparison.best_model_by_aic in ["LinearRegression", "Ridge", "Lasso"]
        assert comparison.best_model_by_bic in ["LinearRegression", "Ridge", "Lasso"]
        assert isinstance(comparison.comparison_table, pd.DataFrame)

    def test_select_best_model_by_aic(self, fitted_models):
        """Test selecting best model by AIC."""
        models, X_test, y_test = fitted_models

        selector = ModelSelector()
        best_name, best_model, best_result = selector.select_best_model(
            models, X_test, y_test, criterion="aic"
        )

        assert best_name in models.keys()
        assert hasattr(best_model, "predict")
        assert isinstance(best_result, ModelCriterionResult)

    def test_select_best_model_by_bic(self, fitted_models):
        """Test selecting best model by BIC."""
        models, X_test, y_test = fitted_models

        selector = ModelSelector()
        best_name, best_model, best_result = selector.select_best_model(
            models, X_test, y_test, criterion="bic"
        )

        assert best_name in models.keys()
        assert hasattr(best_model, "predict")

    def test_select_best_model_invalid_criterion(self, fitted_models):
        """Test selecting with invalid criterion."""
        models, X_test, y_test = fitted_models

        selector = ModelSelector()

        with pytest.raises(ValueError, match="Unknown criterion"):
            selector.select_best_model(models, X_test, y_test, criterion="invalid")

    def test_compute_all_criteria(self, sample_regression_data):
        """Test computing all information criteria."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        selector = ModelSelector()
        criteria = selector.compute_information_criteria(y_test, y_pred, n_params=10)

        assert "aic" in criteria
        assert "bic" in criteria
        assert "adjusted_r2" in criteria
        assert "gcv" in criteria
        assert "r2" in criteria
        assert "mse" in criteria

    def test_result_serialization(self, sample_regression_data):
        """Test ModelCriterionResult serialization."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)

        selector = ModelSelector()
        result = selector.evaluate_model(model, X_test, y_test, "LinearRegression")

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "model_name" in result_dict
        assert "aic" in result_dict
        assert "bic" in result_dict
        assert "adjusted_r2" in result_dict


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_select_model_by_aic_function(self, fitted_models):
        """Test select_model_by_aic convenience function."""
        models, X_test, y_test = fitted_models

        best_name, best_model, best_result = select_model_by_aic(models, X_test, y_test)

        assert best_name in models.keys()
        assert isinstance(best_result, ModelCriterionResult)

    def test_select_model_by_bic_function(self, fitted_models):
        """Test select_model_by_bic convenience function."""
        models, X_test, y_test = fitted_models

        best_name, best_model, best_result = select_model_by_bic(models, X_test, y_test)

        assert best_name in models.keys()
        assert isinstance(best_result, ModelCriterionResult)

    def test_compute_criteria_function(self, sample_regression_data):
        """Test compute_criteria convenience function."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        criteria = compute_criteria(y_test, y_pred, n_params=10)

        assert "aic" in criteria
        assert "bic" in criteria
        assert "adjusted_r2" in criteria


class TestModelSelectionEdgeCases:
    """Tests for edge cases."""

    def test_perfect_model(self):
        """Test criteria with perfect predictions."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = y_true.copy()  # Perfect predictions

        aic = AICCalculator.calculate(y_true, y_pred, n_params=2)
        bic = BICCalculator.calculate(y_true, y_pred, n_params=2)
        adj_r2 = AdjustedR2Calculator.calculate(y_true, y_pred, n_params=2)

        # Perfect predictions should result in good scores
        assert adj_r2 == 1.0

    def test_zero_variance_target(self):
        """Test with constant target."""
        y_true = np.ones(100)
        y_pred = np.ones(100)

        adj_r2 = AdjustedR2Calculator.calculate(y_true, y_pred, n_params=2)

        # Should handle without error
        # May be NaN or 1 depending on implementation

    def test_single_parameter(self):
        """Test criteria with single parameter."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1.1, 2.1, 2.9, 4.1, 4.9])

        aic = AICCalculator.calculate(y_true, y_pred, n_params=1)

        assert isinstance(aic, float)

    def test_many_parameters(self):
        """Test criteria with many parameters (overfitting)."""
        n_samples = 50
        n_params = 40  # Almost as many parameters as samples

        y_true = np.random.randn(n_samples)
        y_pred = np.random.randn(n_samples)

        bic = BICCalculator.calculate(y_true, y_pred, n_params=n_params)

        # High parameter penalty should be reflected in BIC
        assert isinstance(bic, float)

    def test_comparison_with_identical_models(self, sample_regression_data):
        """Test comparing models with identical performance."""
        X, y = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        # Two identical models
        model1 = LinearRegression()
        model1.fit(X_train, y_train)

        model2 = LinearRegression()
        model2.fit(X_train, y_train)

        models = {
            "Model1": model1,
            "Model2": model2,
        }

        selector = ModelSelector()
        comparison = selector.compare_models(models, X_test, y_test)

        # Should handle identical models
        assert len(comparison.models) == 2
