"""
Comprehensive tests for Regularization Techniques.

Tests follow ESL methodologies and cover:
1. L1 Regularization (Lasso)
2. L2 Regularization (Ridge)
3. Elastic Net
4. Regularization Path
5. Model Comparison
"""

import numpy as np
import pandas as pd
import pytest

from app.domain.strategies.learning.regularization import (
    AdaptiveLasso,
    ElasticNetRegularization,
    L1Regularization,
    L2Regularization,
    RegularizationAnalyzer,
    RegularizationPath,
    RegularizationResult,
    RegularizationType,
    optimize_regularization,
)


@pytest.fixture
def sample_regression_data():
    """Create sample regression data."""
    np.random.seed(42)
    n_samples = 200
    n_features = 10

    # Create sparse true coefficients (5 non-zero)
    true_coef = np.zeros(n_features)
    true_coef[:5] = [3, 1.5, 0.5, -2, -1]

    X = np.random.randn(n_samples, n_features)
    y = X @ true_coef + np.random.randn(n_samples) * 0.5

    return X, y, true_coef


@pytest.fixture
def sample_collinear_data():
    """Create data with collinear features."""
    np.random.seed(42)
    n_samples = 200

    # Create correlated features
    x1 = np.random.randn(n_samples)
    x2 = x1 + 0.1 * np.random.randn(n_samples)  # Highly correlated with x1
    x3 = np.random.randn(n_samples)

    X = np.column_stack([x1, x2, x3])
    y = 2 * x1 + x2 + 1.5 * x3 + np.random.randn(n_samples) * 0.5

    return X, y


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame."""
    np.random.seed(42)
    n_samples = 200

    X = pd.DataFrame({f"feature_{i}": np.random.randn(n_samples) for i in range(10)})
    y = pd.Series(np.random.randn(n_samples))

    return X, y


class TestL1Regularization:
    """Tests for L1 (Lasso) Regularization."""

    def test_lasso_initialization(self):
        """Test Lasso initialization."""
        lasso = L1Regularization(alpha=1.0, random_state=42)

        assert lasso.alpha == 1.0
        assert lasso.random_state == 42
        assert lasso.fit_intercept is True

    def test_lasso_fit(self, sample_regression_data):
        """Test Lasso fitting."""
        X, y, _ = sample_regression_data

        lasso = L1Regularization(alpha=0.1, random_state=42)
        lasso.fit(X, y)

        assert hasattr(lasso, "lasso_")
        assert hasattr(lasso, "lasso_")

    def test_lasso_predict(self, sample_regression_data):
        """Test Lasso prediction."""
        X, y, _ = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train = y[:150]

        lasso = L1Regularization(alpha=0.1, random_state=42)
        lasso.fit(X_train, y_train)
        y_pred = lasso.predict(X_test)

        assert len(y_pred) == len(X_test)
        assert isinstance(y_pred, np.ndarray)

    def test_lasso_score(self, sample_regression_data):
        """Test Lasso scoring."""
        X, y, _ = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train, y_test = y[:150], y[150:]

        lasso = L1Regularization(alpha=0.1, random_state=42)
        lasso.fit(X_train, y_train)

        train_score = lasso.score(X_train, y_train)
        test_score = lasso.score(X_test, y_test)

        # R² scores should be between -inf and 1
        assert train_score <= 1
        assert test_score <= 1
        # Train score should generally be >= test score
        assert train_score >= test_score

    def test_lasso_sparsity(self, sample_regression_data):
        """Test that Lasso produces sparse solutions."""
        X, y, _ = sample_regression_data

        lasso = L1Regularization(alpha=0.5, random_state=42)
        lasso.fit(X, y)

        coef = lasso.get_coefficients()
        sparsity_mask = lasso.get_sparsity_mask()

        # Some coefficients should be zero
        assert np.sum(sparsity_mask) < len(coef)

    def test_lasso_with_high_alpha(self, sample_regression_data):
        """Test Lasso with very high alpha (more regularization)."""
        X, y, _ = sample_regression_data

        lasso_high = L1Regularization(alpha=10.0, random_state=42)
        lasso_high.fit(X, y)

        lasso_low = L1Regularization(alpha=0.01, random_state=42)
        lasso_low.fit(X, y)

        # Higher alpha should produce more zeros
        n_zero_high = np.sum(lasso_high.get_coefficients() == 0)
        n_zero_low = np.sum(lasso_low.get_coefficients() == 0)

        assert n_zero_high >= n_zero_low

    def test_lasso_get_selected_features(self, sample_regression_data):
        """Test getting selected feature indices."""
        X, y, _ = sample_regression_data

        lasso = L1Regularization(alpha=0.5, random_state=42)
        lasso.fit(X, y)

        selected = lasso.get_selected_features()

        assert isinstance(selected, np.ndarray)
        assert len(selected) <= X.shape[1]


class TestL2Regularization:
    """Tests for L2 (Ridge) Regularization."""

    def test_ridge_initialization(self):
        """Test Ridge initialization."""
        ridge = L2Regularization(alpha=1.0)

        assert ridge.alpha == 1.0
        assert ridge.fit_intercept is True

    def test_ridge_fit(self, sample_regression_data):
        """Test Ridge fitting."""
        X, y, _ = sample_regression_data

        ridge = L2Regularization(alpha=1.0)
        ridge.fit(X, y)

        assert hasattr(ridge, "ridge_")

    def test_ridge_predict(self, sample_regression_data):
        """Test Ridge prediction."""
        X, y, _ = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train = y[:150]

        ridge = L2Regularization(alpha=1.0)
        ridge.fit(X_train, y_train)
        y_pred = ridge.predict(X_test)

        assert len(y_pred) == len(X_test)

    def test_ridge_no_sparsity(self, sample_regression_data):
        """Test that Ridge does NOT produce sparse solutions."""
        X, y, _ = sample_regression_data

        ridge = L2Regularization(alpha=1.0)
        ridge.fit(X, y)

        coef = ridge.get_coefficients()

        # Ridge should NOT produce exact zeros
        # (coefficients are shrunk but rarely exactly zero)
        n_zeros = np.sum(coef == 0)
        # May have a few zeros due to numerical precision, but much fewer than Lasso
        assert n_zeros < len(coef) * 0.2  # Less than 20% zeros

    def test_ridge_with_collinear_features(self, sample_collinear_data):
        """Test Ridge handles collinear features well."""
        X, y = sample_collinear_data

        ridge = L2Regularization(alpha=1.0)
        ridge.fit(X, y)

        # Should fit without errors
        coef = ridge.get_coefficients()

        assert len(coef) == X.shape[1]
        assert not np.any(np.isnan(coef))


class TestElasticNetRegularization:
    """Tests for Elastic Net Regularization."""

    def test_elastic_net_initialization(self):
        """Test Elastic Net initialization."""
        enet = ElasticNetRegularization(alpha=1.0, l1_ratio=0.5, random_state=42)

        assert enet.alpha == 1.0
        assert enet.l1_ratio == 0.5

    def test_elastic_net_fit(self, sample_regression_data):
        """Test Elastic Net fitting."""
        X, y, _ = sample_regression_data

        enet = ElasticNetRegularization(alpha=1.0, l1_ratio=0.5, random_state=42)
        enet.fit(X, y)

        assert hasattr(enet, "enet_")

    def test_elastic_net_l1_ratio_pure_ridge(self, sample_regression_data):
        """Test Elastic Net with l1_ratio=0 (pure Ridge)."""
        X, y, _ = sample_regression_data

        enet = ElasticNetRegularization(alpha=1.0, l1_ratio=0.0, random_state=42)
        enet.fit(X, y)

        coef = enet.get_coefficients()
        n_zeros = np.sum(coef == 0)

        # Very few zeros (like Ridge)
        assert n_zeros < len(coef) * 0.2

    def test_elastic_net_l1_ratio_pure_lasso(self, sample_regression_data):
        """Test Elastic Net with l1_ratio=1 (pure Lasso)."""
        X, y, _ = sample_regression_data

        enet = ElasticNetRegularization(alpha=1.0, l1_ratio=1.0, random_state=42)
        enet.fit(X, y)

        coef = enet.get_coefficients()
        n_zeros = np.sum(coef == 0)

        # More zeros (like Lasso)
        assert n_zeros > 0

    def test_elastic_net_balanced(self, sample_regression_data):
        """Test Elastic Net with balanced l1_ratio."""
        X, y, _ = sample_regression_data

        enet = ElasticNetRegularization(alpha=1.0, l1_ratio=0.5, random_state=42)
        enet.fit(X, y)

        coef = enet.get_coefficients()

        # Should have some sparsity but not as much as pure Lasso
        n_zeros = np.sum(coef == 0)
        assert 0 < n_zeros < len(coef)


class TestAdaptiveLasso:
    """Tests for Adaptive Lasso."""

    def test_adaptive_lasso_fit(self, sample_regression_data):
        """Test Adaptive Lasso fitting."""
        X, y, _ = sample_regression_data

        adalasso = AdaptiveLasso(alpha=0.1, gamma=1.0, random_state=42)
        adalasso.fit(X, y)

        assert hasattr(adalasso, "coef_")
        assert hasattr(adalasso, "intercept_")

    def test_adaptive_lasso_predict(self, sample_regression_data):
        """Test Adaptive Lasso prediction."""
        X, y, _ = sample_regression_data
        X_train, X_test = X[:150], X[150:]
        y_train = y[:150]

        adalasso = AdaptiveLasso(alpha=0.1, gamma=1.0, random_state=42)
        adalasso.fit(X_train, y_train)
        y_pred = adalasso.predict(X_test)

        assert len(y_pred) == len(X_test)
        assert isinstance(y_pred, np.ndarray)

    def test_adaptive_lasso_weights(self, sample_regression_data):
        """Test that Adaptive Lasso computes weights."""
        X, y, _ = sample_regression_data

        adalasso = AdaptiveLasso(alpha=0.1, gamma=1.0, random_state=42)
        adalasso.fit(X, y)

        assert hasattr(adalasso, "weights_")
        assert len(adalasso.weights_) == X.shape[1]


class TestRegularizationAnalyzer:
    """Tests for RegularizationAnalyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = RegularizationAnalyzer(
            cv_folds=5,
            test_size=0.2,
            random_state=42,
        )

        assert analyzer.cv_folds == 5
        assert analyzer.test_size == 0.2

    def test_analyze_l1_regularization(self, sample_regression_data):
        """Test L1 analysis."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        result = analyzer.analyze_l1_regularization(X, y, alpha=0.1)

        assert isinstance(result, RegularizationResult)
        assert result.regularization_type == RegularizationType.L1
        assert result.alpha == 0.1
        assert result.l1_ratio == 1.0
        assert result.n_nonzero_features <= result.n_features

    def test_analyze_l2_regularization(self, sample_regression_data):
        """Test L2 analysis."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        result = analyzer.analyze_l2_regularization(X, y, alpha=1.0)

        assert isinstance(result, RegularizationResult)
        assert result.regularization_type == RegularizationType.L2
        assert result.alpha == 1.0
        assert result.l1_ratio == 0.0
        # L2 should retain all features
        assert result.n_nonzero_features == result.n_features

    def test_analyze_elastic_net(self, sample_regression_data):
        """Test Elastic Net analysis."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        result = analyzer.analyze_elastic_net(X, y, alpha=1.0, l1_ratio=0.5)

        assert isinstance(result, RegularizationResult)
        assert result.regularization_type == RegularizationType.ELASTIC_NET
        assert result.alpha == 1.0
        assert result.l1_ratio == 0.5

    def test_compute_regularization_path(self, sample_regression_data):
        """Test regularization path computation."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        path = analyzer.compute_regularization_path(
            X,
            y,
            regularization_type=RegularizationType.L1,
            n_alphas=10,
        )

        assert isinstance(path, RegularizationPath)
        assert len(path.path_points) > 0
        assert path.optimal_alpha > 0
        assert hasattr(path, "feature_names")

    def test_regularization_path_points(self, sample_regression_data):
        """Test that path points have correct structure."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        path = analyzer.compute_regularization_path(
            X,
            y,
            regularization_type=RegularizationType.L1,
            n_alphas=5,
        )

        for point in path.path_points:
            assert hasattr(point, "alpha")
            assert hasattr(point, "coefficients")
            assert hasattr(point, "n_nonzero")
            assert hasattr(point, "score")

    def test_compare_regularization_methods(self, sample_regression_data):
        """Test comparing multiple methods."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        results = analyzer.compare_regularization_methods(
            X,
            y,
            alphas=[0.1, 1.0],
            l1_ratios=[0.5],
        )

        assert "l1" in results
        assert "l2" in results
        assert "elastic_net" in results

        # Each should have at least one result
        assert len(results["l1"]) > 0
        assert len(results["l2"]) > 0
        assert len(results["elastic_net"]) > 0

    def test_result_to_dict(self, sample_regression_data):
        """Test RegularizationResult serialization."""
        X, y, _ = sample_regression_data

        analyzer = RegularizationAnalyzer()
        result = analyzer.analyze_l1_regularization(X, y, alpha=0.1)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "regularization_type" in result_dict
        assert "alpha" in result_dict
        assert "n_nonzero_features" in result_dict


class TestOptimizeRegularization:
    """Tests for optimize_regularization convenience function."""

    def test_optimize_lasso(self, sample_regression_data):
        """Test automatic Lasso optimization."""
        X, y, _ = sample_regression_data

        result = optimize_regularization(X, y, method="lasso", cv_folds=3)

        assert isinstance(result, RegularizationResult)
        assert result.regularization_type == RegularizationType.L1
        assert result.alpha > 0

    def test_optimize_ridge(self, sample_regression_data):
        """Test automatic Ridge optimization."""
        X, y, _ = sample_regression_data

        result = optimize_regularization(X, y, method="ridge", cv_folds=3)

        assert isinstance(result, RegularizationResult)
        assert result.regularization_type == RegularizationType.L2
        assert result.alpha > 0

    def test_optimize_invalid_method(self, sample_regression_data):
        """Test optimization with invalid method."""
        X, y, _ = sample_regression_data

        with pytest.raises(ValueError, match="Unknown method"):
            optimize_regularization(X, y, method="invalid")


class TestRegularizationEdgeCases:
    """Tests for edge cases."""

    def test_single_feature(self):
        """Test regularization with single feature."""
        np.random.seed(42)
        X = np.random.randn(100, 1)
        y = 2 * X.ravel() + np.random.randn(100) * 0.5

        lasso = L1Regularization(alpha=0.1, random_state=42)
        lasso.fit(X, y)

        coef = lasso.get_coefficients()
        assert len(coef) == 1

    def test_perfect_collinearity(self):
        """Test with perfectly collinear features."""
        np.random.seed(42)
        n = 100
        x1 = np.random.randn(n)
        x2 = x1  # Perfect correlation
        X = np.column_stack([x1, x2])
        y = x1 + np.random.randn(n) * 0.1

        # Ridge should handle this
        ridge = L2Regularization(alpha=1.0)
        ridge.fit(X, y)

        coef = ridge.get_coefficients()
        assert not np.any(np.isnan(coef))

    def test_small_alpha(self, sample_regression_data):
        """Test with very small alpha (little regularization)."""
        X, y, _ = sample_regression_data

        lasso = L1Regularization(alpha=1e-6, random_state=42)
        lasso.fit(X, y)

        # With very small alpha, should select most features
        n_nonzero = np.sum(lasso.get_coefficients() != 0)
        assert n_nonzero > X.shape[1] * 0.5

    def test_large_alpha(self, sample_regression_data):
        """Test with very large alpha (heavy regularization)."""
        X, y, _ = sample_regression_data

        lasso = L1Regularization(alpha=100, random_state=42)
        lasso.fit(X, y)

        # With large alpha, should select very few features
        n_nonzero = np.sum(lasso.get_coefficients() != 0)
        assert n_nonzero < X.shape[1] * 0.3
