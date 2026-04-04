"""
Tests for Statistical Learning and Expected Returns compliance features.

Tests for:
- Bias-variance decomposition (Hastie Rule 15)
- Cross-sectional consistency (Ilmanen Rule 12)
- Feature explosion validation (Ilmanen Rule 12)
- Learning curve analysis (Hastie Rule 15)
- Model stability tests (Hastie Rule 15)
"""

import numpy as np
import pandas as pd
import pytest

from app.backtesting.validation.bias_variance_analysis import (
    BiasVarianceAnalyzer,
    ModelComplexityLevel,
    analyze_bias_variance,
)
from app.backtesting.validation.cross_sectional_consistency import (
    ConsistencyLevel,
    CrossSectionalConsistencyChecker,
    validate_cross_sectional_consistency,
)
from app.backtesting.validation.feature_explosion_validator import (
    FeatureExplosionLevel,
    FeatureExplosionValidator,
    validate_feature_explosion,
)


@pytest.fixture
def sample_signals():
    """Create sample cross-sectional signals.

    Returns DataFrame with:
    - Index: time periods
    - Columns: assets
    """
    np.random.seed(42)
    n_assets = 100
    n_periods = 50

    # Create correlated signals
    base_signal = np.random.randn(n_assets)
    signals = pd.DataFrame(
        np.random.randn(n_periods, n_assets) * 0.1 + base_signal,
        columns=[f"asset_{i}" for i in range(n_assets)],
    )

    return signals


@pytest.fixture
def sample_returns():
    """Create sample forward returns with some signal quality.

    Returns DataFrame with:
    - Index: time periods
    - Columns: assets
    """
    np.random.seed(42)
    n_assets = 100
    n_periods = 50

    # Returns with weak signal
    base_signal = np.random.randn(n_assets)
    returns = pd.DataFrame(
        np.random.randn(n_periods, n_assets) * 0.02 + base_signal * 0.01,
        columns=[f"asset_{i}" for i in range(n_assets)],
    )

    return returns


@pytest.fixture
def sample_signals_transposed():
    """Create sample cross-sectional signals transposed for validate_ic_consistency.

    Returns DataFrame with:
    - Index: assets
    - Columns: time periods
    """
    np.random.seed(42)
    n_assets = 100
    n_periods = 50

    # Create correlated signals
    base_signal = np.random.randn(n_assets)
    signals = pd.DataFrame(
        np.random.randn(n_periods, n_assets) * 0.1 + base_signal,
        columns=[f"asset_{i}" for i in range(n_assets)],
    )

    # Transpose so assets are rows, periods are columns
    return signals.T


@pytest.fixture
def sample_returns_transposed():
    """Create sample forward returns transposed for validate_ic_consistency.

    Returns DataFrame with:
    - Index: assets
    - Columns: time periods
    """
    np.random.seed(42)
    n_assets = 100
    n_periods = 50

    # Returns with weak signal
    base_signal = np.random.randn(n_assets)
    returns = pd.DataFrame(
        np.random.randn(n_periods, n_assets) * 0.02 + base_signal * 0.01,
        columns=[f"asset_{i}" for i in range(n_assets)],
    )

    # Transpose so assets are rows, periods are columns
    return returns.T


@pytest.fixture
def sample_ml_data():
    """Create sample ML data for bias-variance analysis."""
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = np.random.randn(n_samples, n_features)
    # True relationship with some noise
    y = X[:, :5].sum(axis=1) + np.random.randn(n_samples) * 0.5

    return X, y


class TestCrossSectionalConsistency:
    """Test cross-sectional consistency validation (Ilmanen Rule 12)."""

    def test_ic_consistency_calculation(self, sample_signals_transposed, sample_returns_transposed):
        """Test Information Coefficient consistency calculation."""
        checker = CrossSectionalConsistencyChecker()

        # Run through validator with transposed data (assets as rows, periods as columns)
        result = checker.validate_ic_consistency(
            sample_signals_transposed,
            sample_returns_transposed,
        )

        assert result is not None
        assert result.test_name == "IC Consistency"
        assert isinstance(result.information_coefficient, float)
        assert isinstance(result.consistency_level, ConsistencyLevel)
        assert result.assets_tested > 0

    def test_decile_monotonicity(self):
        """Test decile monotonicity analysis."""
        checker = CrossSectionalConsistencyChecker()

        # Create signal with monotonic relationship
        signal_values = np.arange(100)
        returns_values = signal_values * 0.01 + np.random.randn(100) * 0.01

        signals = pd.Series(signal_values, index=[f"asset_{i}" for i in range(100)])
        returns = pd.Series(returns_values, index=[f"asset_{i}" for i in range(100)])

        result = checker.validate_decile_monotonicity(signals, returns)

        assert result is not None
        assert result.long_short_return > 0  # Top decile should outperform
        assert result.monotonicity_score > 0.5  # Should be fairly monotonic

    def test_sector_consistency(self):
        """Test sector-level consistency validation."""
        checker = CrossSectionalConsistencyChecker()

        # Create signals and returns with more samples per sector
        n_assets = 500  # Increase to have more samples per sector
        signals = pd.Series(
            np.random.randn(n_assets),
            index=[f"asset_{i}" for i in range(n_assets)],
        )
        returns = pd.Series(
            np.random.randn(n_assets) * 0.02,
            index=[f"asset_{i}" for i in range(n_assets)],
        )

        # Create sectors (5 sectors with 100 assets each)
        sectors = pd.Series(
            [f"sector_{i % 5}" for i in range(n_assets)],
            index=[f"asset_{i}" for i in range(n_assets)],
        )

        results = checker.validate_sector_consistency(signals, returns, sectors)

        assert isinstance(results, dict)
        # Should have results for each sector (or at least some sectors)
        assert len(results) > 0

    def test_time_stability(self, sample_signals_transposed, sample_returns_transposed):
        """Test time stability of IC."""
        checker = CrossSectionalConsistencyChecker()

        result = checker.validate_time_stability(
            sample_signals_transposed, sample_returns_transposed
        )

        assert result is not None
        assert "mean_ic" in result
        assert "std_ic" in result
        assert "is_stable" in result
        # np.bool_ is also acceptable
        assert isinstance(result["is_stable"], (bool, np.bool_))


class TestBiasVarianceAnalysis:
    """Test bias-variance decomposition (Hastie Rule 15)."""

    def test_bias_variance_decomposition(self, sample_ml_data):
        """Test bias-variance decomposition."""
        X, y = sample_ml_data

        # Use simple model
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()

        analyzer = BiasVarianceAnalyzer()
        result = analyzer.decompose_bias_variance(model, X, y, n_bootstrap=50)

        assert result is not None
        assert result.model_name == "LinearRegression"
        assert result.bias_squared >= 0
        assert result.variance >= 0
        assert result.total_error >= 0
        assert isinstance(result.complexity_level, ModelComplexityLevel)

    def test_learning_curve_analysis(self, sample_ml_data):
        """Test learning curve analysis."""
        X, y = sample_ml_data

        from sklearn.linear_model import Ridge

        model = Ridge(alpha=1.0)

        analyzer = BiasVarianceAnalyzer()
        result = analyzer.analyze_learning_curve(
            model, X, y, train_sizes=np.array([0.2, 0.5, 0.8, 1.0]), cv=3
        )

        assert result is not None
        assert len(result.curve_points) > 0
        # np.bool_ is also acceptable
        assert isinstance(result.is_converged, (bool, np.bool_))
        assert isinstance(result.suffers_high_bias, (bool, np.bool_))
        assert isinstance(result.suffers_high_variance, (bool, np.bool_))
        assert len(result.recommended_action) > 0

    def test_temporal_stability(self, sample_ml_data):
        """Test temporal stability."""
        X, y = sample_ml_data

        from sklearn.linear_model import LinearRegression

        model = LinearRegression()

        # Create fake timestamps
        timestamps = np.arange(len(X))

        analyzer = BiasVarianceAnalyzer()
        result = analyzer.test_temporal_stability(model, X, y, timestamps, n_windows=3)

        assert result is not None
        assert result.test_type == "temporal_stability"
        # np.bool_ is also acceptable
        assert isinstance(result.is_stable, (bool, np.bool_))
        assert 0 <= result.stability_score <= 1

    def test_bootstrap_stability(self, sample_ml_data):
        """Test bootstrap stability."""
        X, y = sample_ml_data

        from sklearn.linear_model import LinearRegression

        model = LinearRegression()

        analyzer = BiasVarianceAnalyzer()
        result = analyzer.test_bootstrap_stability(model, X, y, n_bootstrap=50)

        assert result is not None
        assert result.test_type == "bootstrap_stability"
        # np.bool_ is also acceptable
        assert isinstance(result.is_stable, (bool, np.bool_))
        assert 0 <= result.stability_score <= 1


class TestFeatureExplosionValidator:
    """Test feature explosion validation (Ilmanen Rule 12)."""

    def test_feature_explosion_detection(self):
        """Test feature explosion detection."""
        validator = FeatureExplosionValidator()

        # Case 1: Safe ratio
        n_samples = 1000
        n_features = 50
        X = np.random.randn(n_samples, n_features)

        result = validator.validate_feature_explosion(X)

        assert result.explosion_level in [
            FeatureExplosionLevel.SAFE,
            FeatureExplosionLevel.MODERATE,
        ]
        assert result.n_features == n_features
        assert result.n_samples == n_samples

        # Case 2: Explosion
        n_features_many = 800
        X_many = np.random.randn(n_samples, n_features_many)

        result_many = validator.validate_feature_explosion(X_many)

        assert result_many.explosion_level in [
            FeatureExplosionLevel.SEVERE,
            FeatureExplosionLevel.CRITICAL,
        ]

    def test_multicollinearity_detection(self):
        """Test multicollinearity detection."""
        validator = FeatureExplosionValidator()

        # Create highly correlated features
        n_samples = 100
        base = np.random.randn(n_samples)
        X = pd.DataFrame(
            {
                "feature_1": base,
                "feature_2": base + np.random.randn(n_samples) * 0.01,  # Highly correlated
                "feature_3": np.random.randn(n_samples),
                "feature_4": base * 2 + np.random.randn(n_samples) * 0.01,  # Highly correlated
            }
        )

        result = validator.analyze_multicollinearity(X)

        assert result is not None
        assert result.has_multicollinearity  # Should detect high correlation
        assert len(result.high_correlation_pairs) > 0

    def test_feature_reduction_recommendation(self):
        """Test feature reduction recommendations."""
        validator = FeatureExplosionValidator()

        # Create many features with correlation
        n_samples = 100
        base = np.random.randn(n_samples)
        X = pd.DataFrame(
            {f"feature_{i}": base + np.random.randn(n_samples) * 0.01 for i in range(20)}
        )

        result = validator.recommend_feature_reduction(X, method="correlation")

        assert "features_to_remove" in result
        assert "n_features_remaining" in result
        assert result["n_features_remaining"] < len(X.columns)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_cross_sectional_consistency_function(
        self, sample_signals_transposed, sample_returns_transposed
    ):
        """Test cross-sectional consistency convenience function."""
        result = validate_cross_sectional_consistency(
            sample_signals_transposed.iloc[:, 0],  # First period
            sample_returns_transposed.iloc[:, 0],  # First period
        )

        assert result is not None
        assert "decile_analysis" in result

    def test_bias_variance_convenience_function(self, sample_ml_data):
        """Test bias-variance convenience function."""
        X, y = sample_ml_data

        from sklearn.linear_model import LinearRegression

        model = LinearRegression()

        result = analyze_bias_variance(model, X, y)

        assert result is not None
        assert "bias_variance" in result
        assert "learning_curve" in result

    def test_feature_explosion_convenience_function(self, sample_ml_data):
        """Test feature explosion convenience function."""
        X, y = sample_ml_data

        result = validate_feature_explosion(X)

        assert result is not None
        assert isinstance(result.explosion_level, FeatureExplosionLevel)


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for combined analyses."""

    def test_full_model_validation_pipeline(self, sample_ml_data):
        """Test complete model validation pipeline."""
        X, y = sample_ml_data

        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(n_estimators=50, random_state=42)

        # 1. Bias-variance analysis
        analyzer = BiasVarianceAnalyzer()
        bv_result = analyzer.decompose_bias_variance(model, X, y, n_bootstrap=30)

        # 2. Learning curve
        lc_result = analyzer.analyze_learning_curve(model, X, y, cv=3)

        # 3. Stability tests
        stability_result = analyzer.test_bootstrap_stability(model, X, y, n_bootstrap=30)

        # Verify all results
        assert bv_result.complexity_level in ModelComplexityLevel
        assert len(lc_result.curve_points) > 0
        # np.bool_ is also acceptable
        assert isinstance(stability_result.is_stable, (bool, np.bool_))

    def test_cross_sectional_feature_validation_pipeline(
        self, sample_signals_transposed, sample_returns_transposed
    ):
        """Test cross-sectional validation with feature checks."""
        # 1. Check feature explosion
        validator = FeatureExplosionValidator()
        explosion_result = validator.validate_feature_explosion(
            sample_signals_transposed.T
        )  # Transpose for assets as rows

        # 2. Check IC consistency
        checker = CrossSectionalConsistencyChecker()
        ic_result = checker.validate_ic_consistency(
            sample_signals_transposed, sample_returns_transposed
        )

        # 3. Check time stability
        stability_result = checker.validate_time_stability(
            sample_signals_transposed, sample_returns_transposed
        )

        # Verify results
        assert isinstance(explosion_result.explosion_level, FeatureExplosionLevel)
        assert isinstance(ic_result.consistency_level, ConsistencyLevel)
        # np.bool_ is also acceptable
        assert isinstance(stability_result["is_stable"], (bool, np.bool_))
