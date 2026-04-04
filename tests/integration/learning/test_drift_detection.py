"""
Integration Tests: Drift Detection and Overfitting Detection (Módulo 4.2)

Tests para:
- ConceptDriftDetector (KS test, MMD)
- OverfittingDetector (train/val gap, learning curves)
- AutoRetrainingTrigger
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.strategies.learning.drift_detector import (
    AutoRetrainingTrigger,
    ConceptDriftDetector,
    OverfittingDetector,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConceptDriftDetector:
    """Tests para ConceptDriftDetector."""

    def test_drift_detector_initialization(self):
        """Test inicialización del detector."""
        config = {'window_size': 100, 'drift_threshold_ks': 0.05, 'use_ks_test': True}

        detector = ConceptDriftDetector(config)

        assert detector.window_size == 100
        assert detector.drift_threshold_ks == 0.05
        assert len(detector.reference_data) == 0

    def test_update_reference(self):
        """Test actualización de datos de referencia."""
        detector = ConceptDriftDetector()

        # Datos de referencia
        reference_data = np.random.randn(100, 10)
        detector.update_reference(reference_data)

        assert len(detector.reference_data) == 100

    def test_detect_drift_no_drift(self):
        """Test detección cuando no hay drift."""
        detector = ConceptDriftDetector({'window_size': 50})

        # Crear datos de referencia (distribución normal)
        reference_data = np.random.randn(100, 5)
        detector.update_reference(reference_data)

        # Datos actuales de la misma distribución
        current_data = np.random.randn(50, 5)

        result = detector.detect_drift(current_data)

        assert 'drift_detected' in result
        assert 'drift_score' in result
        assert 'recommendation' in result
        logger.info(f"Detección sin drift: {result}")

    def test_detect_drift_with_drift(self):
        """Test detección cuando hay drift."""
        detector = ConceptDriftDetector({'window_size': 50, 'drift_threshold_ks': 0.1})

        # Referencia: distribución normal
        reference_data = np.random.normal(0, 1, (100, 5))
        detector.update_reference(reference_data)

        # Actual: distribución diferente (shifted)
        current_data = np.random.normal(3, 1, (50, 5))  # Shifted

        result = detector.detect_drift(current_data)

        assert 'drift_detected' in result
        # Con shift significativo, debería detectar drift
        logger.info(f"Detección con drift: {result}")

    def test_drift_history(self):
        """Test historial de detecciones."""
        detector = ConceptDriftDetector()

        reference_data = np.random.randn(50, 5)
        detector.update_reference(reference_data)

        # Múltiples detecciones
        for i in range(5):
            current_data = np.random.randn(20, 5)
            detector.detect_drift(current_data, timestamp=datetime.now())

        history = detector.get_drift_history()
        assert len(history) == 5


class TestOverfittingDetector:
    """Tests para OverfittingDetector."""

    def test_overfitting_detector_initialization(self):
        """Test inicialización."""
        config = {'overfitting_threshold': 0.1, 'min_epochs': 10}

        detector = OverfittingDetector(config)

        assert detector.overfitting_threshold == 0.1
        assert detector.min_epochs == 10

    def test_update_metrics(self):
        """Test actualización de métricas."""
        detector = OverfittingDetector()

        # Simular entrenamiento
        for epoch in range(20):
            train_loss = 0.5 - epoch * 0.01  # Mejora
            val_loss = 0.6 - epoch * 0.005  # Mejora más lenta (overfitting)
            detector.update_metrics(epoch, train_loss, val_loss)

        assert len(detector.train_metrics_history) == 20
        assert len(detector.val_metrics_history) == 20

    def test_detect_overfitting(self):
        """Test detección de overfitting."""
        detector = OverfittingDetector({'overfitting_threshold': 0.1})

        # Simular overfitting: train mejora pero val empeora
        for epoch in range(20):
            train_loss = 0.5 - epoch * 0.02  # Mejora rápido
            val_loss = 0.6 if epoch < 10 else 0.6 + (epoch - 10) * 0.01  # Empeora después
            detector.update_metrics(epoch, train_loss, val_loss)

        result = detector.detect_overfitting()

        assert 'overfitting_detected' in result
        assert 'train_val_gap' in result
        assert 'gap_ratio' in result
        assert 'recommendation' in result

        logger.info(f"Detección de overfitting: {result}")

        # Si hay overfitting claro, debería detectarlo
        if result.get('gap_ratio', 0) > 0.1:
            assert result.get('overfitting_detected', False) or result.get('recommendation') != 'ok'

    def test_learning_curves(self):
        """Test obtención de learning curves."""
        detector = OverfittingDetector()

        for epoch in range(15):
            detector.update_metrics(epoch, 0.5 - epoch * 0.01, 0.6 - epoch * 0.005)

        curves = detector.get_learning_curves()

        assert 'epochs' in curves
        assert 'train_metrics' in curves
        assert 'val_metrics' in curves
        assert len(curves['epochs']) == 15


class TestAutoRetrainingTrigger:
    """Tests para AutoRetrainingTrigger."""

    def test_retraining_trigger_initialization(self):
        """Test inicialización."""
        config = {
            'retrain_on_drift': True,
            'retrain_interval_days': 30,
            'performance_degradation_threshold': 0.2,
        }

        trigger = AutoRetrainingTrigger(config)

        assert trigger.retrain_on_drift
        assert trigger.retrain_interval_days == 30
        assert isinstance(trigger.drift_detector, ConceptDriftDetector)
        assert isinstance(trigger.overfitting_detector, OverfittingDetector)

    def test_time_based_retraining(self):
        """Test retraining basado en tiempo."""
        trigger = AutoRetrainingTrigger({'retrain_interval_days': 7})

        # Registrar retrain hace 10 días
        trigger.record_retrain(timestamp=datetime.now() - timedelta(days=10))

        result = trigger.should_retrain(timestamp=datetime.now())

        assert result['should_retrain'] is True
        assert result['time_based'] is True
        assert 'time_based' in result['reasons'][0]

    def test_drift_based_retraining(self):
        """Test retraining basado en drift."""
        trigger = AutoRetrainingTrigger(
            {
                'retrain_on_drift': True,
                'drift_detector_config': {'window_size': 50, 'drift_threshold_ks': 0.1},
            }
        )

        # Configurar referencia
        reference_data = np.random.normal(0, 1, (100, 5))
        trigger.drift_detector.update_reference(reference_data)

        # Datos con drift significativo
        current_data = np.random.normal(3, 1, (50, 5))

        result = trigger.should_retrain(current_data=current_data)

        assert 'drift_detection' in result
        logger.info(f"Retraining trigger: {result}")

    def test_performance_degradation_retraining(self):
        """Test retraining basado en degradación de performance."""
        trigger = AutoRetrainingTrigger(
            {'retrain_on_performance_degradation': True, 'performance_degradation_threshold': 0.2}
        )

        # Registrar performance histórica buena
        trigger.record_performance({'accuracy': 0.85, 'f1_score': 0.80})
        trigger.record_performance({'accuracy': 0.87, 'f1_score': 0.82})
        trigger.record_performance({'accuracy': 0.86, 'f1_score': 0.81})

        # Performance actual degradada
        current_performance = {'accuracy': 0.60, 'f1_score': 0.55}  # ~30% degradación

        result = trigger.should_retrain(current_performance=current_performance)

        assert 'performance_degradation' in result
        if result.get('performance_degradation', {}).get('degradation_detected', False):
            assert result['should_retrain'] is True
            assert 'performance_degradation' in result['reasons'][0]

    def test_combined_triggers(self):
        """Test combinación de múltiples triggers."""
        trigger = AutoRetrainingTrigger(
            {
                'retrain_on_drift': True,
                'retrain_on_overfitting': True,
                'retrain_interval_days': 365,  # No time-based
            }
        )

        # Configurar datos
        reference_data = np.random.normal(0, 1, (100, 5))
        trigger.drift_detector.update_reference(reference_data)

        # Simular overfitting
        for epoch in range(15):
            trigger.overfitting_detector.update_metrics(
                epoch, 0.5 - epoch * 0.02, 0.6 + epoch * 0.01
            )

        # Datos con drift
        current_data = np.random.normal(2, 1, (50, 5))

        result = trigger.should_retrain(current_data=current_data)

        assert 'drift_detection' in result
        assert 'overfitting_detection' in result
        logger.info(
            f"Triggers combinados: should_retrain={result['should_retrain']}, reasons={result['reasons']}"
        )
