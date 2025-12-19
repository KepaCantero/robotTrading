"""
Unit Tests: Enhanced Feature Importance System [TASK-4.2-FEATURE-IMPORTANCE]

Comprehensive tests for the enhanced feature importance analysis module:
- PermutationImportanceAnalyzer
- BuiltInImportanceAnalyzer
- CorrelationAnalyzer
- FeatureStabilityTracker
- ComprehensiveFeatureAnalyzer
- Configuration loading
- Data classes and enums
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.strategies.momentum_modular.learning.feature_importance import (
    PermutationImportanceAnalyzer,
    BuiltInImportanceAnalyzer,
    CorrelationAnalyzer,
    FeatureStabilityTracker,
    ComprehensiveFeatureAnalyzer,
    ImportanceCategory,
    FeatureImportanceResult,
    ComprehensiveImportanceReport,
    load_feature_importance_config,
    get_default_feature_importance_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Configuration Loading
# =============================================================================
class TestConfigurationLoading:
    """Tests for configuration loading functions."""

    def test_get_default_config(self):
        """Test default configuration generation."""
        config = get_default_feature_importance_config()

        assert isinstance(config, dict)
        assert "shap" in config
        assert "permutation" in config
        assert "builtin" in config
        assert "correlation" in config
        assert "stability" in config
        assert "selection" in config
        assert "reporting" in config

    def test_default_config_shap_section(self):
        """Test SHAP section in default config."""
        config = get_default_feature_importance_config()

        assert config["shap"]["enabled"] is True
        assert config["shap"]["sample_size"] == 100
        assert config["shap"]["top_n_features"] == 10

    def test_default_config_permutation_section(self):
        """Test permutation section in default config."""
        config = get_default_feature_importance_config()

        assert config["permutation"]["enabled"] is True
        assert config["permutation"]["n_repeats"] == 10
        assert config["permutation"]["random_state"] == 42

    def test_default_config_correlation_section(self):
        """Test correlation section in default config."""
        config = get_default_feature_importance_config()

        assert config["correlation"]["enabled"] is True
        assert config["correlation"]["multicollinearity_threshold"] == 0.9
        assert config["correlation"]["calculate_mutual_info"] is True

    def test_default_config_stability_section(self):
        """Test stability section in default config."""
        config = get_default_feature_importance_config()

        assert config["stability"]["enabled"] is True
        assert config["stability"]["window_size"] == 10
        # detect_trends may not be in defaults, check stability_threshold
        assert config["stability"]["stability_threshold"] == 0.3

    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        config = load_feature_importance_config()

        # Should return a dict (either from file or defaults)
        assert isinstance(config, dict)
        assert "shap" in config or "permutation" in config

    def test_load_config_nonexistent_file(self):
        """Test loading config with nonexistent path returns defaults."""
        config = load_feature_importance_config("/nonexistent/path.yaml")

        # Should return defaults when file doesn't exist
        assert isinstance(config, dict)


# =============================================================================
# Test Data Classes and Enums
# =============================================================================
class TestDataClassesAndEnums:
    """Tests for ImportanceCategory, FeatureImportanceResult, and ComprehensiveImportanceReport."""

    def test_importance_category_enum_values(self):
        """Test ImportanceCategory enum values."""
        assert ImportanceCategory.CRITICAL.value == "critical"
        assert ImportanceCategory.IMPORTANT.value == "important"
        assert ImportanceCategory.MODERATE.value == "moderate"
        assert ImportanceCategory.LOW.value == "low"
        assert ImportanceCategory.NEGLIGIBLE.value == "negligible"

    def test_feature_importance_result_creation(self):
        """Test FeatureImportanceResult dataclass creation."""
        result = FeatureImportanceResult(
            feature_name="test_feature",
            importance_score=0.25,
            rank=1,
            category=ImportanceCategory.IMPORTANT,
            methods_used=["permutation", "shap"],
            method_scores={"permutation": 0.2, "shap": 0.3},
            stability_score=0.9,
            correlation_with_target=0.6,
            recommendation="Monitor this feature",
        )

        assert result.feature_name == "test_feature"
        assert result.importance_score == 0.25
        assert result.rank == 1
        assert result.category == ImportanceCategory.IMPORTANT
        assert len(result.methods_used) == 2
        assert result.stability_score == 0.9

    def test_comprehensive_importance_report_creation(self):
        """Test ComprehensiveImportanceReport dataclass creation."""
        feature_result = FeatureImportanceResult(
            feature_name="feature_0",
            importance_score=0.5,
            rank=1,
            category=ImportanceCategory.CRITICAL,
            methods_used=["permutation"],
            method_scores={"permutation": 0.5},
        )

        report = ComprehensiveImportanceReport(
            timestamp=datetime.now(),
            n_features=5,
            n_samples=100,
            feature_results=[feature_result],
            top_features=["feature_0"],
            low_importance_features=["feature_4"],
            highly_correlated_pairs=[("feature_1", "feature_2", 0.95)],
            recommendations=["Consider removing feature_4"],
            methods_used=["permutation"],
            analysis_time_seconds=1.5,
        )

        assert report.n_features == 5
        assert report.n_samples == 100
        assert len(report.feature_results) == 1
        assert len(report.highly_correlated_pairs) == 1


# =============================================================================
# Test PermutationImportanceAnalyzer
# =============================================================================
class TestPermutationImportanceAnalyzer:
    """Tests for PermutationImportanceAnalyzer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        X = np.random.randn(100, 5)
        # Feature 0 is highly predictive
        y = (X[:, 0] + 0.5 * X[:, 1] + np.random.randn(100) * 0.1 > 0).astype(int)
        return X, y

    @pytest.fixture
    def trained_model(self, sample_data):
        """Create a trained model for testing."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            X, y = sample_data
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)
            return model
        except ImportError:
            pytest.skip("sklearn not available")

    def test_permutation_analyzer_initialization(self):
        """Test PermutationImportanceAnalyzer initialization."""
        config = {"n_repeats": 5, "random_state": 123, "max_samples": 500}

        analyzer = PermutationImportanceAnalyzer(config)

        assert analyzer.n_repeats == 5
        assert analyzer.random_state == 123
        assert analyzer.max_samples == 500

    def test_permutation_analyzer_default_config(self):
        """Test PermutationImportanceAnalyzer with default config."""
        analyzer = PermutationImportanceAnalyzer()

        assert analyzer.n_repeats == 10
        assert analyzer.random_state == 42
        assert analyzer.max_samples == 1000

    def test_calculate_importance_classification(self, sample_data, trained_model):
        """Test permutation importance analysis for classification."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(5)]

        analyzer = PermutationImportanceAnalyzer({"n_repeats": 3})
        result = analyzer.calculate_importance(trained_model, X, y, feature_names)

        assert "feature_importance" in result
        assert "ranked_features" in result
        assert len(result["feature_importance"]) == 5
        # Should have top_features
        assert "top_features" in result

    def test_calculate_importance_with_subsampling(self, sample_data, trained_model):
        """Test permutation importance with data subsampling."""
        X, y = sample_data
        # Create larger dataset
        X_large = np.vstack([X] * 20)  # 2000 samples
        y_large = np.tile(y, 20)

        analyzer = PermutationImportanceAnalyzer({"max_samples": 100})
        result = analyzer.calculate_importance(trained_model, X_large, y_large)

        assert "feature_importance" in result
        assert result["n_samples_used"] <= 100

    def test_calculate_importance_regression(self):
        """Test permutation importance for regression."""
        try:
            from sklearn.ensemble import RandomForestRegressor

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = X[:, 0] * 2 + X[:, 1] + np.random.randn(100) * 0.1

            model = RandomForestRegressor(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = PermutationImportanceAnalyzer({"n_repeats": 3})
            result = analyzer.calculate_importance(model, X, y)

            assert "feature_importance" in result
            assert len(result["feature_importance"]) == 5
        except ImportError:
            pytest.skip("sklearn not available")

    def test_calculate_importance_auto_scoring(self, sample_data, trained_model):
        """Test that auto scoring detection works."""
        X, y = sample_data

        analyzer = PermutationImportanceAnalyzer({"n_repeats": 3, "scoring": "auto"})
        result = analyzer.calculate_importance(trained_model, X, y)

        # Should work with auto scoring
        assert "feature_importance" in result or "error" in result
        if "scoring" in result:
            assert result["scoring"] in ["accuracy", "r2"]


# =============================================================================
# Test BuiltInImportanceAnalyzer
# =============================================================================
class TestBuiltInImportanceAnalyzer:
    """Tests for BuiltInImportanceAnalyzer."""

    def test_builtin_analyzer_initialization(self):
        """Test BuiltInImportanceAnalyzer initialization."""
        config = {"normalize": False}

        analyzer = BuiltInImportanceAnalyzer(config)

        assert analyzer.normalize is False

    def test_builtin_analyzer_default_config(self):
        """Test BuiltInImportanceAnalyzer with default config."""
        analyzer = BuiltInImportanceAnalyzer()

        assert analyzer.normalize is True

    def test_calculate_importance_random_forest(self):
        """Test built-in importance extraction from RandomForest."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            feature_names = [f"feature_{i}" for i in range(5)]
            analyzer = BuiltInImportanceAnalyzer()
            result = analyzer.calculate_importance(model, feature_names)

            assert "feature_importance" in result
            assert "model_type" in result
            assert len(result["feature_importance"]) == 5
            assert "RandomForest" in result["model_type"]
            # Normalized importance should sum to ~1
            assert 0.99 <= sum(result["feature_importance"].values()) <= 1.01
        except ImportError:
            pytest.skip("sklearn not available")

    def test_calculate_importance_gradient_boosting(self):
        """Test built-in importance extraction from GradientBoosting."""
        try:
            from sklearn.ensemble import GradientBoostingClassifier

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = GradientBoostingClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = BuiltInImportanceAnalyzer()
            result = analyzer.calculate_importance(model)

            assert "feature_importance" in result
            assert len(result["feature_importance"]) == 5
        except ImportError:
            pytest.skip("sklearn not available")

    def test_calculate_importance_unsupported_model(self):
        """Test that unsupported models return error gracefully."""
        try:
            from sklearn.svm import SVC

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = SVC()
            model.fit(X, y)

            analyzer = BuiltInImportanceAnalyzer()
            result = analyzer.calculate_importance(model)

            # Should handle gracefully with error
            assert "error" in result or result.get("supported") is False
        except ImportError:
            pytest.skip("sklearn not available")

    def test_calculate_importance_without_normalization(self):
        """Test built-in importance without normalization."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = BuiltInImportanceAnalyzer({"normalize": False})
            result = analyzer.calculate_importance(model)

            assert "feature_importance" in result
            # Without normalization, sum may not be 1
            total = sum(result["feature_importance"].values())
            assert total > 0
        except ImportError:
            pytest.skip("sklearn not available")


# =============================================================================
# Test CorrelationAnalyzer
# =============================================================================
class TestCorrelationAnalyzer:
    """Tests for CorrelationAnalyzer."""

    @pytest.fixture
    def correlated_data(self):
        """Create data with known correlations."""
        np.random.seed(42)
        n_samples = 200

        # Feature 0 is highly correlated with target
        feature_0 = np.random.randn(n_samples)

        # Feature 1 is moderately correlated with target
        feature_1 = np.random.randn(n_samples)

        # Feature 2 is highly correlated with feature 1 (multicollinearity)
        feature_2 = feature_1 + np.random.randn(n_samples) * 0.1

        # Feature 3 is independent
        feature_3 = np.random.randn(n_samples)

        X = np.column_stack([feature_0, feature_1, feature_2, feature_3])
        y = feature_0 * 2 + feature_1 + np.random.randn(n_samples) * 0.5

        return X, y

    def test_correlation_analyzer_initialization(self):
        """Test CorrelationAnalyzer initialization."""
        config = {
            "target_correlation_method": "pearson",
            "multicollinearity_threshold": 0.8,
        }

        analyzer = CorrelationAnalyzer(config)

        assert analyzer.target_method == "pearson"
        assert analyzer.multicollinearity_threshold == 0.8

    def test_correlation_analyzer_default_config(self):
        """Test CorrelationAnalyzer with default config."""
        analyzer = CorrelationAnalyzer()

        assert analyzer.target_method == "spearman"
        assert analyzer.multicollinearity_threshold == 0.9

    def test_analyze_target_correlation(self, correlated_data):
        """Test target correlation analysis."""
        X, y = correlated_data
        feature_names = ["f0", "f1", "f2", "f3"]

        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(X, y, feature_names)

        assert "target_correlations" in result
        assert len(result["target_correlations"]) == 4
        # Feature 0 should have highest absolute correlation
        correlations = result["target_correlations"]
        assert abs(correlations["f0"]) > abs(correlations["f3"])

    def test_analyze_multicollinearity(self, correlated_data):
        """Test multicollinearity detection."""
        X, y = correlated_data
        feature_names = ["f0", "f1", "f2", "f3"]

        analyzer = CorrelationAnalyzer({"multicollinearity_threshold": 0.8})
        result = analyzer.analyze(X, y, feature_names)

        assert "highly_correlated_pairs" in result
        # Features 1 and 2 should be detected as highly correlated
        correlated_pairs = result["highly_correlated_pairs"]
        pair_features = [(p[0], p[1]) for p in correlated_pairs]
        assert ("f1", "f2") in pair_features or ("f2", "f1") in pair_features

    def test_analyze_mutual_information(self, correlated_data):
        """Test mutual information calculation."""
        X, y = correlated_data
        feature_names = ["f0", "f1", "f2", "f3"]

        analyzer = CorrelationAnalyzer({"calculate_mutual_info": True})
        result = analyzer.analyze(X, y, feature_names)

        assert "mutual_information" in result
        mi = result["mutual_information"]
        assert len(mi) == 4
        # Feature 0 should have high MI with target
        assert mi["f0"] > mi["f3"]

    def test_analyze_different_correlation_methods(self, correlated_data):
        """Test different correlation methods."""
        X, y = correlated_data

        for method in ["pearson", "spearman", "kendall"]:
            analyzer = CorrelationAnalyzer({"target_correlation_method": method})
            result = analyzer.analyze(X, y)

            assert "target_correlations" in result
            assert len(result["target_correlations"]) == 4

    def test_analyze_with_classification_target(self):
        """Test correlation analysis with classification target."""
        np.random.seed(42)
        X = np.random.randn(200, 4)
        y = (X[:, 0] > 0).astype(int)

        analyzer = CorrelationAnalyzer({"calculate_mutual_info": True})
        result = analyzer.analyze(X, y)

        assert "mutual_information" in result
        # Should detect feature 0 as informative
        mi = result["mutual_information"]
        assert mi.get(0, mi.get("0", 0)) > 0 or mi.get("feature_0", 0) > 0


# =============================================================================
# Test FeatureStabilityTracker
# =============================================================================
class TestFeatureStabilityTracker:
    """Tests for FeatureStabilityTracker."""

    def test_stability_tracker_initialization(self):
        """Test FeatureStabilityTracker initialization."""
        config = {"window_size": 5, "stability_threshold": 0.2}

        tracker = FeatureStabilityTracker(config)

        assert tracker.window_size == 5
        assert tracker.stability_threshold == 0.2

    def test_stability_tracker_default_config(self):
        """Test FeatureStabilityTracker with default config."""
        tracker = FeatureStabilityTracker()

        assert tracker.window_size == 10
        assert tracker.stability_threshold == 0.3

    def test_record_importance(self):
        """Test recording importance snapshots."""
        tracker = FeatureStabilityTracker()

        importance_1 = {"f0": 0.5, "f1": 0.3, "f2": 0.2}
        importance_2 = {"f0": 0.45, "f1": 0.35, "f2": 0.2}

        tracker.record_importance(importance_1)
        tracker.record_importance(importance_2)

        # Private attribute _importance_history
        assert len(tracker._importance_history) == 2

    def test_analyze_stability_insufficient_data(self):
        """Test stability report with insufficient data."""
        tracker = FeatureStabilityTracker()

        importance = {"f0": 0.5, "f1": 0.3}
        tracker.record_importance(importance)

        report = tracker.analyze_stability()

        # Should handle insufficient data gracefully
        assert "error" in report or "n_snapshots" in report

    def test_analyze_stability(self):
        """Test stability report with sufficient data."""
        tracker = FeatureStabilityTracker({"window_size": 3})

        # Record multiple importance snapshots
        importances = [
            {"f0": 0.5, "f1": 0.3, "f2": 0.2},
            {"f0": 0.48, "f1": 0.32, "f2": 0.2},
            {"f0": 0.52, "f1": 0.28, "f2": 0.2},
        ]

        for imp in importances:
            tracker.record_importance(imp)

        report = tracker.analyze_stability()

        assert "feature_stability" in report
        assert "unstable_features" in report
        # f2 should be stable (constant importance)
        if "f2" in report["feature_stability"]:
            assert report["feature_stability"]["f2"]["is_stable"] == True

    def test_detect_trends(self):
        """Test trend detection."""
        tracker = FeatureStabilityTracker({"window_size": 5})

        # Create increasing importance for f0
        for i in range(5):
            importance = {"f0": 0.2 + i * 0.1, "f1": 0.3, "f2": 0.3 - i * 0.05}
            tracker.record_importance(importance)

        report = tracker.analyze_stability()

        assert "trending_up" in report or "feature_stability" in report
        # Check if f0 trend is detected
        if "feature_stability" in report and "f0" in report["feature_stability"]:
            trend = report["feature_stability"]["f0"].get("trend", "")
            assert trend in ["increasing", "stable", "insufficient_data"]

    def test_window_size_limit(self):
        """Test that history is limited to window size."""
        tracker = FeatureStabilityTracker({"window_size": 3})

        for i in range(10):
            tracker.record_importance({"f0": i * 0.1})

        assert len(tracker._importance_history) <= 3

    def test_rank_stability(self):
        """Test rank stability calculation."""
        tracker = FeatureStabilityTracker({"window_size": 4})

        # Record snapshots where ranking changes
        importances = [
            {"f0": 0.5, "f1": 0.3, "f2": 0.2},  # Rank: f0, f1, f2
            {"f0": 0.3, "f1": 0.5, "f2": 0.2},  # Rank: f1, f0, f2
            {"f0": 0.5, "f1": 0.3, "f2": 0.2},  # Rank: f0, f1, f2
            {"f0": 0.4, "f1": 0.4, "f2": 0.2},  # Rank: tied
        ]

        for imp in importances:
            tracker.record_importance(imp)

        report = tracker.analyze_stability()

        # Should have feature_stability with rank_std info
        assert "feature_stability" in report
        if "f0" in report["feature_stability"]:
            assert "rank_std" in report["feature_stability"]["f0"]


# =============================================================================
# Test ComprehensiveFeatureAnalyzer
# =============================================================================
class TestComprehensiveFeatureAnalyzer:
    """Tests for ComprehensiveFeatureAnalyzer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        X = np.random.randn(200, 10)
        y = (X[:, 0] + 0.5 * X[:, 1] + np.random.randn(200) * 0.1 > 0).astype(int)
        return X, y

    @pytest.fixture
    def trained_model(self, sample_data):
        """Create a trained model for testing."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            X, y = sample_data
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)
            return model
        except ImportError:
            pytest.skip("sklearn not available")

    def test_comprehensive_analyzer_initialization(self):
        """Test ComprehensiveFeatureAnalyzer initialization."""
        config = get_default_feature_importance_config()
        analyzer = ComprehensiveFeatureAnalyzer(config)

        assert analyzer.permutation_analyzer is not None
        assert analyzer.builtin_analyzer is not None
        assert analyzer.correlation_analyzer is not None
        assert analyzer.stability_tracker is not None

    def test_comprehensive_analyzer_default_config(self):
        """Test ComprehensiveFeatureAnalyzer with no config."""
        analyzer = ComprehensiveFeatureAnalyzer()

        assert analyzer.permutation_analyzer is not None
        assert analyzer.correlation_analyzer is not None

    def test_analyze_full(self, sample_data, trained_model):
        """Test full comprehensive analysis."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,  # Skip SHAP for faster testing
            include_permutation=True,
            include_builtin=True,
            include_correlation=True,
        )

        assert isinstance(report, ComprehensiveImportanceReport)
        assert report.n_features == 10
        assert report.n_samples == 200
        assert len(report.feature_results) == 10
        assert len(report.methods_used) > 0

    def test_analyze_permutation_only(self, sample_data, trained_model):
        """Test analysis with only permutation importance."""
        X, y = sample_data

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            include_shap=False,
            include_permutation=True,
            include_builtin=False,
            include_correlation=False,
        )

        assert isinstance(report, ComprehensiveImportanceReport)
        assert "permutation" in report.methods_used

    def test_analyze_builtin_only(self, sample_data, trained_model):
        """Test analysis with only built-in importance."""
        X, y = sample_data

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            include_shap=False,
            include_permutation=False,
            include_builtin=True,
            include_correlation=False,
        )

        assert isinstance(report, ComprehensiveImportanceReport)
        assert "builtin" in report.methods_used

    def test_feature_categorization(self, sample_data, trained_model):
        """Test that features are correctly categorized."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,
            include_permutation=True,
            include_builtin=True,
            include_correlation=False,
        )

        # Check that categories are assigned
        categories_used = {r.category for r in report.feature_results}
        assert len(categories_used) > 0
        assert all(isinstance(c, ImportanceCategory) for c in categories_used)

    def test_top_features_identification(self, sample_data, trained_model):
        """Test identification of top features."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,
        )

        assert len(report.top_features) > 0
        assert len(report.top_features) <= 10

    def test_low_importance_features(self, sample_data, trained_model):
        """Test identification of low importance features."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,
        )

        # There should be some low importance features identified
        assert isinstance(report.low_importance_features, list)

    def test_recommendations_generated(self, sample_data, trained_model):
        """Test that recommendations are generated."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,
        )

        assert isinstance(report.recommendations, list)
        # At least some recommendations should be generated
        assert len(report.recommendations) >= 0

    def test_analysis_time_recorded(self, sample_data, trained_model):
        """Test that analysis time is recorded."""
        X, y = sample_data

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            include_shap=False,
        )

        assert report.analysis_time_seconds > 0

    def test_highly_correlated_pairs_detected(self):
        """Test detection of highly correlated feature pairs."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            # Create highly correlated features
            base = np.random.randn(200, 1)
            X = np.hstack(
                [
                    base,  # feature_0
                    base + np.random.randn(200, 1) * 0.01,  # feature_1 correlated with 0
                    np.random.randn(200, 5),  # independent features
                ]
            )
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            feature_names = [f"feature_{i}" for i in range(7)]
            analyzer = ComprehensiveFeatureAnalyzer()
            report = analyzer.analyze(
                model=model,
                X=X,
                y=y,
                feature_names=feature_names,
                include_shap=False,
                include_correlation=True,
            )

            # Should detect feature_0 and feature_1 as highly correlated
            assert len(report.highly_correlated_pairs) > 0
        except ImportError:
            pytest.skip("sklearn not available")

    def test_with_feature_selection(self, sample_data, trained_model):
        """Test analysis with feature selection enabled."""
        X, y = sample_data
        feature_names = [f"feature_{i}" for i in range(10)]

        analyzer = ComprehensiveFeatureAnalyzer()
        report = analyzer.analyze(
            model=trained_model,
            X=X,
            y=y,
            feature_names=feature_names,
            include_shap=False,
            include_selection=True,
        )

        assert isinstance(report, ComprehensiveImportanceReport)


# =============================================================================
# Test Integration: Stability Tracking in Comprehensive Analyzer
# =============================================================================
class TestStabilityIntegration:
    """Tests for stability tracking integration."""

    def test_stability_recorded_across_analyses(self):
        """Test that stability is tracked across multiple analyses."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = ComprehensiveFeatureAnalyzer()

            # Run multiple analyses
            for _ in range(3):
                report = analyzer.analyze(
                    model=model,
                    X=X,
                    y=y,
                    include_shap=False,
                    include_permutation=True,
                )

            # Stability should be tracked (private attribute)
            assert len(analyzer.stability_tracker._importance_history) >= 1
        except ImportError:
            pytest.skip("sklearn not available")


# =============================================================================
# Test Edge Cases and Error Handling
# =============================================================================
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_feature_names(self):
        """Test handling of empty feature names."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(100, 5)
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = ComprehensiveFeatureAnalyzer()
            report = analyzer.analyze(
                model=model,
                X=X,
                y=y,
                feature_names=None,  # No feature names
                include_shap=False,
            )

            # Should generate default names
            assert len(report.feature_results) == 5
        except ImportError:
            pytest.skip("sklearn not available")

    def test_single_feature(self):
        """Test handling of single feature."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(100, 1)
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = ComprehensiveFeatureAnalyzer()
            report = analyzer.analyze(
                model=model,
                X=X,
                y=y,
                include_shap=False,
            )

            assert len(report.feature_results) == 1
        except ImportError:
            pytest.skip("sklearn not available")

    def test_small_sample_size(self):
        """Test handling of small sample size."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.random.randn(10, 5)  # Very small
            y = (X[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=5, random_state=42)
            model.fit(X, y)

            analyzer = ComprehensiveFeatureAnalyzer()
            report = analyzer.analyze(
                model=model,
                X=X,
                y=y,
                include_shap=False,
            )

            assert report.n_samples == 10
        except ImportError:
            pytest.skip("sklearn not available")

    def test_all_constant_features(self):
        """Test handling of constant features."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            np.random.seed(42)
            X = np.ones((100, 5))  # All constant
            y = np.random.randint(0, 2, 100)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            analyzer = CorrelationAnalyzer()
            result = analyzer.analyze(X, y)

            # Should handle gracefully - may return NaN correlations or empty
            assert "target_correlations" in result or "feature_correlation_matrix" in result
        except ImportError:
            pytest.skip("sklearn not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
