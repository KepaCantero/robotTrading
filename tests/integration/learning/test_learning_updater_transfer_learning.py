"""
Integration Tests: Transfer Learning in LearningEngineUpdater (Módulo 4.2)

Tests para:
- LearningEngineUpdater con Transfer Learning habilitado
- Market regime detection
- Pre-trained model lookup y fine-tuning
- Model registration después del entrenamiento
- Public API methods
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.strategies.learning.learning_updater import (
    LearningEngineUpdater,
    load_transfer_learning_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLoadTransferLearningConfig:
    """Tests para carga de configuración de Transfer Learning."""

    def test_load_config_defaults(self):
        """Test que cargue configuración por defecto."""
        config = load_transfer_learning_config()

        assert config is not None
        assert config.get("enabled") is not None
        assert "market_regime" in config
        assert "fine_tuner" in config
        assert "distiller" in config

    def test_config_has_required_fields(self):
        """Test que config tiene campos requeridos."""
        config = load_transfer_learning_config()

        required_fields = ["enabled", "registry_path", "market_regime", "fine_tuner", "distiller"]
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"


class TestMarketRegimeDetection:
    """Tests para detección de régimen de mercado."""

    @pytest.fixture
    def mock_learning_engine(self):
        """Crear mock learning engine."""
        engine = MagicMock()
        engine.enabled = True
        engine.is_trained = False
        engine.algorithm = "test_algo"
        engine.model = None
        return engine

    @pytest.fixture
    def updater(self, mock_learning_engine):
        """Crear LearningEngineUpdater con mocks."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager"
        ):
            updater = LearningEngineUpdater(mock_learning_engine)
        return updater

    def test_detect_bullish_market(self, updater):
        """Test detección de mercado alcista."""
        training_data = {
            "targets": np.array([0.01, 0.02, 0.015, 0.01, 0.02]),  # Positive returns
            "features": np.random.randn(5, 10),
        }

        regime = updater._detect_market_regime(training_data)

        assert "bull" in regime
        logger.info(f"Bull market regime: {regime}")

    def test_detect_bearish_market(self, updater):
        """Test detección de mercado bajista."""
        training_data = {
            "targets": np.array([-0.01, -0.015, -0.01, -0.02, -0.01]),  # Negative returns
            "features": np.random.randn(5, 10),
        }

        regime = updater._detect_market_regime(training_data)

        assert "bear" in regime
        logger.info(f"Bear market regime: {regime}")

    def test_detect_sideways_market(self, updater):
        """Test detección de mercado lateral."""
        training_data = {
            "targets": np.array([0.0001, -0.0002, 0.0001, -0.0001, 0.0002]),  # Minimal returns
            "features": np.random.randn(5, 10),
        }

        regime = updater._detect_market_regime(training_data)

        assert "sideways" in regime
        logger.info(f"Sideways market regime: {regime}")

    def test_detect_high_volatility(self, updater):
        """Test detección de alta volatilidad."""
        training_data = {
            "targets": np.array([0.1, -0.08, 0.12, -0.09, 0.11]),  # High volatility
            "features": np.random.randn(5, 10),
        }

        regime = updater._detect_market_regime(training_data)

        assert "high_volatility" in regime
        logger.info(f"High volatility regime: {regime}")

    def test_detect_no_targets(self, updater):
        """Test manejo cuando no hay targets."""
        training_data = {"features": np.random.randn(5, 10)}

        regime = updater._detect_market_regime(training_data)

        assert regime == "normal"


class TestTransferLearningIntegration:
    """Tests para integración de Transfer Learning."""

    @pytest.fixture
    def mock_learning_engine(self):
        """Crear mock learning engine."""
        engine = MagicMock()
        engine.enabled = True
        engine.is_trained = False
        engine.algorithm = "test_algo"
        engine.model = None
        engine.train = MagicMock(return_value={"loss": 0.1, "accuracy": 0.95})
        return engine

    @pytest.fixture
    def mock_transfer_manager(self):
        """Crear mock transfer learning manager."""
        manager = MagicMock()
        manager.find_best_model = MagicMock(return_value=None)  # No pre-trained by default
        manager.load_and_finetune = MagicMock(
            return_value=(MagicMock(), {"loss": 0.05, "accuracy": 0.98})
        )
        manager.create_pretrained_model = MagicMock(return_value="model_123")
        manager.registry = MagicMock()
        manager.registry.list_models = MagicMock(
            return_value={"bull": ["model_1"], "bear": ["model_2"]}
        )
        manager.list_models = MagicMock(return_value={"bull": ["model_1"], "bear": ["model_2"]})
        return manager

    def test_tl_disabled_by_default_config(self, mock_learning_engine):
        """Test que TL se inicializa cuando está habilitado en config."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager"
        ) as mock_tm:
            with patch(
                "app.strategies.momentum_modular.learning.learning_updater.load_transfer_learning_config"
            ) as mock_config:
                mock_config.return_value = {"enabled": True, "registry_path": "models/registry"}
                mock_tm.return_value = MagicMock()

                updater = LearningEngineUpdater(mock_learning_engine)

                assert updater._transfer_learning_enabled is True
                assert updater._transfer_manager is not None

    def test_tl_execution_no_model(self, mock_learning_engine, mock_transfer_manager):
        """Test ejecución de TL cuando no hay modelo pre-entrenado."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            training_data = {
                "targets": np.random.randn(100),
                "features": np.random.randn(100, 10),
            }

            result = updater._execute_transfer_learning_step(training_data, datetime.now())

            assert result is None  # No pre-trained model found
            mock_transfer_manager.find_best_model.assert_called()

    def test_tl_execution_with_model(self, mock_learning_engine, mock_transfer_manager):
        """Test ejecución de TL cuando hay modelo pre-entrenado."""
        mock_transfer_manager.find_best_model.return_value = "model_bull_123"

        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            training_data = {
                "targets": np.array([0.01, 0.02, 0.015]),  # Bullish
                "features": np.random.randn(3, 10),
            }

            result = updater._execute_transfer_learning_step(training_data, datetime.now())

            assert result is not None
            mock_transfer_manager.load_and_finetune.assert_called()


class TestPublicAPIMethods:
    """Tests para public API methods de Transfer Learning."""

    @pytest.fixture
    def mock_learning_engine(self):
        """Crear mock learning engine."""
        engine = MagicMock()
        engine.enabled = True
        engine.algorithm = "test_algo"
        return engine

    @pytest.fixture
    def mock_transfer_manager(self):
        """Crear mock transfer learning manager."""
        manager = MagicMock()
        manager.registry = MagicMock()
        manager.registry.list_models = MagicMock(
            return_value={"bull": ["model_1"], "bear": ["model_2"]}
        )
        manager.list_models = MagicMock(return_value={"bull": ["model_1"], "bear": ["model_2"]})
        return manager

    def test_get_transfer_learning_status(self, mock_learning_engine, mock_transfer_manager):
        """Test obtener estado de Transfer Learning."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            status = updater.get_transfer_learning_status()

            assert "enabled" in status
            assert "manager_initialized" in status
            assert "total_operations" in status
            assert "registrations" in status
            assert "fine_tunes" in status

    def test_get_transfer_history_empty(self, mock_learning_engine, mock_transfer_manager):
        """Test obtener historial vacío de TL."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            history = updater.get_transfer_history()

            assert isinstance(history, list)
            assert len(history) == 0

    def test_get_available_pretrained_models(self, mock_learning_engine, mock_transfer_manager):
        """Test obtener modelos pre-entrenados disponibles."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            models = updater.get_available_pretrained_models()

            assert "status" in models
            assert "models" in models
            mock_transfer_manager.registry.list_models.assert_called_with(regime=None)

    def test_get_available_models_filtered_by_regime(
        self, mock_learning_engine, mock_transfer_manager
    ):
        """Test filtrar modelos por régimen."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            models = updater.get_available_pretrained_models(regime="bull")  # noqa: F841

            mock_transfer_manager.registry.list_models.assert_called_with(regime="bull")

    def test_get_last_transfer_operation_none(self, mock_learning_engine, mock_transfer_manager):
        """Test obtener última operación cuando no hay."""
        with patch(
            "app.strategies.momentum_modular.learning.learning_updater.TransferLearningManager",
            return_value=mock_transfer_manager,
        ):
            updater = LearningEngineUpdater(mock_learning_engine)

            last_op = updater.get_last_transfer_operation()

            assert last_op is None
