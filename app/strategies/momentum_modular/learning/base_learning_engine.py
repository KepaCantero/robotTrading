"""
BaseLearningEngine - Clase base abstracta para todos los motores de aprendizaje.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

# SECURITY: Using joblib instead of pickle for sklearn model serialization
# joblib is safer than pickle as it only serializes numpy arrays and sklearn objects
# and doesn't execute arbitrary code during deserialization
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logging.warning("joblib not available, model save/load will be limited")

logger = logging.getLogger(__name__)


class BaseLearningEngine(ABC):
    """
    Interfaz base para todos los motores de aprendizaje.

    Proporciona interfaz unificada para:
    - Entrenar modelos
    - Evaluar performance
    - Predecir/Generar recomendaciones
    - Guardar/Cargar modelos
    """

    def __init__(self, name: str, config: Dict):
        """
        Inicializar motor de aprendizaje.

        Args:
            name: Nombre del motor (supervised, deep, reinforcement)
            config: Configuración específica del motor
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.model = None
        self.model_path = config.get("model_path", f"models/{name}_model.pkl")
        self.is_trained = False

        # Crear directorio de modelos si no existe
        os.makedirs(
            os.path.dirname(self.model_path) if os.path.dirname(self.model_path) else "models",
            exist_ok=True,
        )

    @abstractmethod
    def train(
        self, training_data: Dict[str, Any], validation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Entrenar el modelo.

        Args:
            training_data: Datos de entrenamiento (estructura específica por motor)
            validation_data: Datos de validación opcionales

        Returns:
            Dict con métricas de entrenamiento (loss, accuracy, etc.)
        """

    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generar predicciones o recomendaciones.

        Args:
            features: Features actuales del mercado/filtros

        Returns:
            Dict estándar con el siguiente formato:
            {
                'success_probability': float,  # Probabilidad de éxito (0-1)
                'confidence': float,  # Confianza en la predicción (0-1)
                'filter_adjustments': Dict[str, Dict[str, float]],  # Ajustes a filtros
                'recommended_action': str,  # 'BUY', 'SELL', 'HOLD'
                'raw_prediction': Any  # Predicción cruda del modelo (opcional)
            }
        """

    def explain(self, features: Dict[str, Any], prediction: Optional[Dict[str, Any]] = None) -> str:
        """
        Generar explicación textual de la predicción.

        Args:
            features: Features actuales del mercado/filtros
            prediction: Predicción generada (si no se proporciona, se calcula)

        Returns:
            Explicación textual de la decisión
        """
        if prediction is None:
            prediction = self.predict(features)

        action = prediction.get('recommended_action', 'HOLD')
        confidence = prediction.get('confidence', 0.0)
        prob = prediction.get('success_probability', 0.0)

        return (
            f"Acción recomendada: {action}. "
            f"Probabilidad de éxito: {prob:.2%}, "
            f"Confianza: {confidence:.2%}."
        )

    @abstractmethod
    def evaluate(self, test_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluar el modelo con datos de prueba.

        Args:
            test_data: Datos de prueba

        Returns:
            Dict con métricas de evaluación
        """

    def save_model(self, path: Optional[str] = None) -> bool:
        """
        Guardar modelo entrenado usando joblib (seguro para sklearn).

        Args:
            path: Ruta opcional (usa self.model_path si no se especifica)

        Returns:
            True si se guardó correctamente
        """
        if not self.is_trained or self.model is None:
            logger.warning(f"{self.name}: No hay modelo entrenado para guardar")
            return False

        save_path = path or self.model_path

        # Change extension to .joblib for clarity
        if save_path.endswith('.pkl'):
            save_path = save_path.replace('.pkl', '.joblib')
        elif not save_path.endswith('.joblib'):
            save_path = save_path + '.joblib'

        try:
            if not JOBLIB_AVAILABLE:
                logger.error(f"{self.name}: joblib no disponible, no se puede guardar modelo")
                return False

            # Save model using joblib (secure for sklearn objects)
            model_data = {
                'model': self.model,
                'config': self.config,
                'trained_at': datetime.now().isoformat(),
                'engine_type': self.name,
            }
            joblib.dump(model_data, save_path)

            # Also save metadata separately as JSON for easy inspection
            metadata_path = save_path.replace('.joblib', '.metadata.json')
            metadata = {
                'config': self.config,
                'trained_at': datetime.now().isoformat(),
                'engine_type': self.name,
                'model_path': save_path,
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info(f"{self.name}: Modelo guardado en {save_path}")
            return True
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"{self.name}: Error guardando modelo: {e}")
            return False

    def load_model(self, path: Optional[str] = None) -> bool:
        """
        Cargar modelo previamente entrenado usando joblib (seguro).

        Args:
            path: Ruta opcional (usa self.model_path si no se especifica)

        Returns:
            True si se cargó correctamente
        """
        load_path = path or self.model_path

        # Handle migration from old .pkl to new .joblib format
        if load_path.endswith('.pkl'):
            # Try .joblib first
            joblib_path = load_path.replace('.pkl', '.joblib')
            if os.path.exists(joblib_path):
                load_path = joblib_path
            # If .pkl still exists, migrate it
            elif os.path.exists(load_path):
                logger.warning(f"{self.name}: Migrating old .pkl file to .joblib format")
                return self._migrate_pkl_to_joblib(load_path)

        if not os.path.exists(load_path):
            logger.warning(f"{self.name}: Modelo no encontrado en {load_path}")
            return False

        try:
            if not JOBLIB_AVAILABLE:
                logger.error(f"{self.name}: joblib no disponible, no se puede cargar modelo")
                return False

            # Load model using joblib (secure)
            saved_data = joblib.load(load_path)
            self.model = saved_data['model']
            self.is_trained = True
            logger.info(f"{self.name}: Modelo cargado desde {load_path}")
            return True
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"{self.name}: Error cargando modelo: {e}")
            return False

    def _migrate_pkl_to_joblib(self, pkl_path: str) -> bool:
        """
        Migrate old .pkl file to new .joblib format (one-time migration).

        Args:
            pkl_path: Path to old .pkl file

        Returns:
            True if migration succeeded
        """
        try:
            if not JOBLIB_AVAILABLE:
                logger.error("Cannot migrate: joblib not available")
                return False

            # SECURITY: One-time migration from pickle to joblib
            # This is the only place where we still use pickle.load, and it's
            # only for migrating existing trusted model files to the secure format
            import pickle  # noqa: S403 - Only for migration of trusted files

            with open(pkl_path, 'rb') as f:
                saved_data = pickle.load(f)  # noqa: S301 - Trusted migration only

            # Save in new secure format
            joblib_path = pkl_path.replace('.pkl', '.joblib')
            joblib.dump(saved_data, joblib_path)

            # Save metadata
            metadata_path = joblib_path.replace('.joblib', '.metadata.json')
            metadata = {
                'config': saved_data.get('config', {}),
                'trained_at': saved_data.get('trained_at', datetime.now().isoformat()),
                'engine_type': saved_data.get('engine_type', self.name),
                'model_path': joblib_path,
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)

            # Remove old .pkl file after successful migration
            os.remove(pkl_path)

            logger.info(f"Successfully migrated {pkl_path} to {joblib_path}")

            # Load the migrated model
            self.model = saved_data['model']
            self.is_trained = True
            return True

        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error migrating .pkl to .joblib: {e}")
            return False

    def is_ready(self) -> bool:
        """Verificar si el motor está listo para usar."""
        return self.enabled and self.is_trained and self.model is not None
