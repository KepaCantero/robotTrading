"""
Tests for XAI Explainer (SHAP, LIME, Feature Importance)
"""

from unittest.mock import Mock

import numpy as np
import pytest

from app.services.xai.explainer import (
    FeatureImportanceCalculator,
    LIMEExplainer,
    SHAPExplainer,
    get_importance_calculator,
    get_lime_explainer,
    get_shap_explainer,
)


@pytest.fixture
def sample_model():
    """Create a mock model for testing."""
    model = Mock()
    model.predict = Mock(return_value=np.array([0.75]))
    return model


@pytest.fixture
def sample_data():
    """Create sample training data."""
    np.random.seed(42)
    return np.random.randn(100, 5)


@pytest.fixture
def feature_names():
    """Create feature names."""
    return ["feature_1", "feature_2", "feature_3", "feature_4", "feature_5"]


@pytest.fixture
def sample_input(feature_names):
    """Create sample input for explanation."""
    return np.random.randn(len(feature_names))


class TestSHAPExplainer:
    """Test SHAP explainer functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_model, sample_data):
        """Test SHAP explainer initialization."""
        explainer = SHAPExplainer(sample_model, sample_data)
        assert explainer.connected is False
        assert len(explainer.data) == 100

    @pytest.mark.asyncio
    async def test_connect(self, sample_model, sample_data):
        """Test SHAP explainer connection."""
        explainer = SHAPExplainer(sample_model, sample_data)
        result = await explainer.connect()
        assert result is True
        assert explainer.connected is True

    @pytest.mark.asyncio
    async def test_explain_prediction(self, sample_model, sample_data, sample_input, feature_names):
        """Test single prediction explanation."""
        explainer = SHAPExplainer(sample_model, sample_data)
        await explainer.connect()

        explanation = await explainer.explain_prediction(
            sample_input, feature_names, prediction_id="pred_001", model_name="test_model"
        )

        assert explanation["prediction_id"] == "pred_001"
        assert "predicted_value" in explanation
        assert "base_value" in explanation
        assert len(explanation["shap_values"]) == len(feature_names)
        assert explanation["model_name"] == "test_model"

    @pytest.mark.asyncio
    async def test_explain_prediction_shap_values_structure(
        self, sample_model, sample_data, sample_input, feature_names
    ):
        """Test SHAP values structure."""
        explainer = SHAPExplainer(sample_model, sample_data)
        await explainer.connect()

        explanation = await explainer.explain_prediction(
            sample_input, feature_names, prediction_id="pred_001"
        )

        for shap_val in explanation["shap_values"]:
            assert "feature_name" in shap_val
            assert "feature_value" in shap_val
            assert "shap_value" in shap_val
            assert "base_value" in shap_val

    @pytest.mark.asyncio
    async def test_explain_batch(self, sample_model, sample_data, feature_names):
        """Test batch prediction explanation."""
        explainer = SHAPExplainer(sample_model, sample_data)
        await explainer.connect()

        samples = np.random.randn(3, len(feature_names))
        explanations = await explainer.explain_batch(
            samples, feature_names, model_name="test_model"
        )

        assert len(explanations) == 3
        for exp in explanations:
            assert "prediction_id" in exp
            assert "shap_values" in exp

    @pytest.mark.asyncio
    async def test_explain_when_not_connected(
        self, sample_model, sample_data, sample_input, feature_names
    ):
        """Test explanation when not connected."""
        explainer = SHAPExplainer(sample_model, sample_data)
        explanation = await explainer.explain_prediction(sample_input, feature_names)
        assert explanation == {}

    def test_get_explainer_status(self, sample_model, sample_data):
        """Test getting explainer status."""
        explainer = SHAPExplainer(sample_model, sample_data)
        status = explainer.get_explainer_status()
        assert "connected" in status
        assert "explainer_type" in status
        assert status["explainer_type"] == "SHAP"


class TestLIMEExplainer:
    """Test LIME explainer functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_model, sample_data):
        """Test LIME explainer initialization."""
        explainer = LIMEExplainer(sample_model, sample_data)
        assert explainer.connected is False

    @pytest.mark.asyncio
    async def test_connect(self, sample_model, sample_data):
        """Test LIME explainer connection."""
        explainer = LIMEExplainer(sample_model, sample_data)
        result = await explainer.connect()
        assert result is True
        assert explainer.connected is True

    @pytest.mark.asyncio
    async def test_explain_prediction(self, sample_model, sample_data, sample_input, feature_names):
        """Test single prediction explanation."""
        explainer = LIMEExplainer(sample_model, sample_data)
        await explainer.connect()

        explanation = await explainer.explain_prediction(
            sample_input, feature_names, prediction_id="pred_001", num_features=5
        )

        assert explanation["prediction_id"] == "pred_001"
        assert "predicted_class" in explanation
        assert "predicted_probability" in explanation
        assert "explanation" in explanation
        assert len(explanation["explanation"]) <= 5

    @pytest.mark.asyncio
    async def test_lime_explanation_structure(
        self, sample_model, sample_data, sample_input, feature_names
    ):
        """Test LIME explanation structure."""
        explainer = LIMEExplainer(sample_model, sample_data)
        await explainer.connect()

        explanation = await explainer.explain_prediction(sample_input, feature_names)

        for feat in explanation["explanation"]:
            assert "feature_name" in feat
            assert "contribution" in feat
            assert "is_positive" in feat

    def test_get_explainer_status(self, sample_model, sample_data):
        """Test getting explainer status."""
        explainer = LIMEExplainer(sample_model, sample_data)
        status = explainer.get_explainer_status()
        assert status["explainer_type"] == "LIME"


class TestFeatureImportanceCalculator:
    """Test feature importance calculation."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_model, sample_data):
        """Test calculator initialization."""
        y_data = np.random.randn(100)
        calc = FeatureImportanceCalculator(sample_model, sample_data, y_data)
        assert calc.X_data is not None
        assert calc.y_data is not None

    @pytest.mark.asyncio
    async def test_calculate_permutation_importance(self, sample_model, sample_data, feature_names):
        """Test permutation importance calculation."""
        y_data = np.random.randn(100)
        calc = FeatureImportanceCalculator(sample_model, sample_data, y_data)

        importance = await calc.calculate_permutation_importance(feature_names)

        assert len(importance) == len(feature_names)
        assert all(0 <= score <= 1 for score in importance.values())

    @pytest.mark.asyncio
    async def test_calculate_tree_importance(self, sample_model, sample_data, feature_names):
        """Test tree-based importance calculation."""
        # Add feature_importances_ to mock model
        sample_model.feature_importances_ = np.random.randn(len(feature_names))

        y_data = np.random.randn(100)
        calc = FeatureImportanceCalculator(sample_model, sample_data, y_data)

        importance = await calc.calculate_tree_importance(feature_names)

        assert len(importance) == len(feature_names)

    @pytest.mark.asyncio
    async def test_calculate_all_importance_methods(self, sample_model, sample_data, feature_names):
        """Test calculating importance with all methods."""
        sample_model.feature_importances_ = np.random.randn(len(feature_names))
        y_data = np.random.randn(100)
        calc = FeatureImportanceCalculator(sample_model, sample_data, y_data)

        results = await calc.calculate_all_importance_methods(feature_names)

        assert "permutation" in results
        assert "tree" in results

    def test_get_calculator_status(self, sample_model, sample_data):
        """Test getting calculator status."""
        y_data = np.random.randn(100)
        calc = FeatureImportanceCalculator(sample_model, sample_data, y_data)
        status = calc.get_calculator_status()
        assert status["num_features"] == 5
        assert status["num_samples"] == 100


class TestExplainerSingletons:
    """Test singleton pattern for explainers."""

    @pytest.mark.asyncio
    async def test_shap_explainer_singleton(self, sample_model, sample_data):
        """Test SHAP explainer singleton."""
        explainer1 = get_shap_explainer(sample_model, sample_data)
        explainer2 = get_shap_explainer(sample_model, sample_data)
        assert explainer1 is explainer2

    @pytest.mark.asyncio
    async def test_lime_explainer_singleton(self, sample_model, sample_data):
        """Test LIME explainer singleton."""
        explainer1 = get_lime_explainer(sample_model, sample_data)
        explainer2 = get_lime_explainer(sample_model, sample_data)
        assert explainer1 is explainer2

    @pytest.mark.asyncio
    async def test_importance_calculator_singleton(self, sample_model, sample_data):
        """Test feature importance calculator singleton."""
        y_data = np.random.randn(100)
        calc1 = get_importance_calculator(sample_model, sample_data, y_data)
        calc2 = get_importance_calculator(sample_model, sample_data, y_data)
        assert calc1 is calc2
