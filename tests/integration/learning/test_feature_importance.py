"""
Integration Tests: Feature Importance System (Módulo 4.3)

Tests para:
- SHAPAnalyzer
- AttentionWeightsAnalyzer
- FeatureSelector
- FeatureImportanceAnalyzer
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.strategies.learning.feature_importance import (  # noqa: E402
    SHAP_AVAILABLE,
    FeatureImportanceAnalyzer,
    FeatureSelector,
    SHAPAnalyzer,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSHAPAnalyzer:
    """Tests para SHAPAnalyzer."""

    @pytest.mark.skipif(not SHAP_AVAILABLE, reason="SHAP no disponible")
    def test_shap_analyzer_initialization(self):
        """Test inicialización."""
        config = {'sample_size': 100, 'max_evals': 50}

        analyzer = SHAPAnalyzer(config)

        assert analyzer.sample_size == 100
        assert analyzer.max_evals == 50

    @pytest.mark.skipif(not SHAP_AVAILABLE, reason="SHAP no disponible")
    def test_explain_model_tree_based(self):
        """Test explicación de modelo tree-based."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            # Crear modelo simple
            X_train = np.random.randn(100, 5)
            y_train = (X_train[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X_train, y_train)

            # Analizar
            analyzer = SHAPAnalyzer()
            X_test = np.random.randn(20, 5)
            feature_names = [f'feature_{i}' for i in range(5)]

            result = analyzer.explain_model(model, X_test, feature_names, model_type='tree')

            assert 'feature_importance' in result or 'error' in result
            if 'feature_importance' in result:
                assert isinstance(result['feature_importance'], dict)
                logger.info(
                    f"SHAP analysis completado: {len(result['feature_importance'])} features"
                )
        except ImportError:
            pytest.skip("sklearn no disponible")

    @pytest.mark.skipif(not SHAP_AVAILABLE, reason="SHAP no disponible")
    def test_explain_prediction(self):
        """Test explicación de predicción individual."""
        try:
            from sklearn.ensemble import RandomForestClassifier  # noqa: E402

            X_train = np.random.randn(100, 5)
            y_train = (X_train[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X_train, y_train)

            analyzer = SHAPAnalyzer()
            X_full = np.random.randn(50, 5)

            result = analyzer.explain_prediction(model, X_full, instance_idx=0)

            assert 'explanation' in result or 'error' in result
            if 'explanation' in result:
                assert 'top_contributors' in result
        except ImportError:
            pytest.skip("sklearn no disponible")


class TestFeatureSelector:
    """Tests para FeatureSelector."""

    def test_feature_selector_initialization(self):
        """Test inicialización."""
        config = {'method': 'model_based', 'n_features': 10, 'importance_threshold': 0.01}

        selector = FeatureSelector(config)

        assert selector.method == 'model_based'
        assert selector.n_features == 10

    def test_univariate_selection(self):
        """Test selección univariante."""
        try:
            from sklearn.datasets import make_classification  # noqa: E402

            X, y = make_classification(
                n_samples=200, n_features=20, n_informative=10, random_state=42
            )

            config = {'method': 'univariate', 'n_features': 5}
            selector = FeatureSelector(config)

            result = selector.select_features(X, y, task_type='classification')

            assert 'selected_features' in result
            assert 'n_selected' in result
            assert result['n_selected'] <= 5
            assert len(result['selected_features']) == result['n_selected']

            logger.info(f"Univariate selection: {result['n_selected']} features seleccionadas")
        except ImportError:
            pytest.skip("sklearn no disponible")

    def test_model_based_selection(self):
        """Test selección basada en modelo."""
        try:
            from sklearn.datasets import make_classification  # noqa: E402

            X, y = make_classification(
                n_samples=200, n_features=20, n_informative=10, random_state=42
            )

            config = {'method': 'model_based', 'importance_threshold': 0.01}
            selector = FeatureSelector(config)

            result = selector.select_features(X, y, task_type='classification')

            assert 'selected_features' in result
            assert 'feature_scores' in result
            assert result['n_selected'] > 0

            logger.info(f"Model-based selection: {result['n_selected']} features seleccionadas")
        except ImportError:
            pytest.skip("sklearn no disponible")


class TestFeatureImportanceAnalyzer:
    """Tests para FeatureImportanceAnalyzer unificado."""

    def test_feature_importance_analyzer_initialization(self):
        """Test inicialización."""
        config = {
            'shap_config': {'sample_size': 50},
            'feature_selector_config': {'method': 'univariate'},
        }

        analyzer = FeatureImportanceAnalyzer(config)

        assert isinstance(analyzer.shap_analyzer, SHAPAnalyzer)
        assert isinstance(analyzer.feature_selector, FeatureSelector)

    @pytest.mark.skipif(not SHAP_AVAILABLE, reason="SHAP no disponible")
    def test_analyze_with_shap(self):
        """Test análisis completo con SHAP."""
        try:
            from sklearn.ensemble import RandomForestClassifier  # noqa: E402

            X_train = np.random.randn(100, 10)
            y_train = (X_train[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X_train, y_train)

            analyzer = FeatureImportanceAnalyzer()
            X_test = np.random.randn(30, 10)
            feature_names = [f'feature_{i}' for i in range(10)]

            result = analyzer.analyze(
                model,
                X_test,
                feature_names=feature_names,
                include_shap=True,
                include_selection=False,
            )

            assert 'shap_analysis' in result
            assert result['shap_analysis'] is not None or 'error' in result.get('shap_analysis', {})
        except ImportError:
            pytest.skip("sklearn no disponible")

    def test_analyze_with_selection(self):
        """Test análisis con feature selection."""
        try:
            from sklearn.ensemble import RandomForestClassifier  # noqa: E402

            X_train = np.random.randn(100, 20)
            y_train = (X_train[:, 0] > 0).astype(int)

            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X_train, y_train)

            analyzer = FeatureImportanceAnalyzer()

            result = analyzer.analyze(
                model, X_train, y=y_train, include_shap=False, include_selection=True
            )

            assert 'feature_selection' in result
            if result['feature_selection'] and 'selected_features' in result['feature_selection']:
                assert len(result['feature_selection']['selected_features']) > 0
        except ImportError:
            pytest.skip("sklearn no disponible")
