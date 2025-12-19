"""
BaseLearningEngine - Clase base abstracta para todos los motores de aprendizaje.
"""

import logging
import os
import pickle
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

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
        pass

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
        pass

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
        pass

    def save_model(self, path: Optional[str] = None) -> bool:
        """
        Guardar modelo entrenado.

        Args:
            path: Ruta opcional (usa self.model_path si no se especifica)

        Returns:
            True si se guardó correctamente
        """
        if not self.is_trained or self.model is None:
            logger.warning(f"{self.name}: No hay modelo entrenado para guardar")
            return False

        save_path = path or self.model_path

        try:
            with open(save_path, 'wb') as f:
                pickle.dump(
                    {
                        'model': self.model,
                        'config': self.config,
                        'trained_at': datetime.now().isoformat(),
                        'engine_type': self.name,
                    },
                    f,
                )
            logger.info(f"{self.name}: Modelo guardado en {save_path}")
            return True
        except Exception as e:
            logger.error(f"{self.name}: Error guardando modelo: {e}")
            return False

    def load_model(self, path: Optional[str] = None) -> bool:
        """
        Cargar modelo previamente entrenado.

        Args:
            path: Ruta opcional (usa self.model_path si no se especifica)

        Returns:
            True si se cargó correctamente
        """
        load_path = path or self.model_path

        if not os.path.exists(load_path):
            logger.warning(f"{self.name}: Modelo no encontrado en {load_path}")
            return False

        try:
            with open(load_path, 'rb') as f:
                saved_data = pickle.load(f)
                self.model = saved_data['model']
                self.is_trained = True
            logger.info(f"{self.name}: Modelo cargado desde {load_path}")
            return True
        except Exception as e:
            logger.error(f"{self.name}: Error cargando modelo: {e}")
            return False

    def is_ready(self) -> bool:
        """Verificar si el motor está listo para usar."""
        return self.enabled and self.is_trained and self.model is not None
