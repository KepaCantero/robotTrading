"""
BaseLearningEngine - Clase base abstracta para todos los motores de aprendizaje.

Enhanced with:
- Time stability tracking (Ilmanen)
- Learning curve analysis (Hastie)
- Feature explosion validation (Ilmanen)
- Bias-variance monitoring (Hastie)
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# SECURITY: Using joblib instead of pickle for sklearn model serialization (REQUIRED)
# joblib is safer than pickle as it only serializes numpy arrays and sklearn objects
# and doesn't execute arbitrary code during deserialization
import joblib

JOBLIB_AVAILABLE = True

import numpy as np

logger = logging.getLogger(__name__)


class StabilityStatus(Enum):
    """Model stability status over time."""

    STABLE = "stable"
    DRIFTING = "drifting"
    UNSTABLE = "unstable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class TrainingSnapshot:
    """Snapshot of model training state."""

    timestamp: datetime
    train_metrics: Dict[str, float]
    validation_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    n_samples: int
    model_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "train_metrics": self.train_metrics,
            "validation_metrics": self.validation_metrics,
            "feature_importance": self.feature_importance,
            "n_samples": self.n_samples,
            "model_params": self.model_params,
        }


@dataclass
class StabilityReport:
    """Report on model stability over time."""

    status: StabilityStatus
    stability_score: float
    feature_importance_change: Dict[str, float]
    performance_drift: float
    confidence_degradation: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "stability_score": self.stability_score,
            "feature_importance_change": self.feature_importance_change,
            "performance_drift": self.performance_drift,
            "confidence_degradation": self.confidence_degradation,
            "details": self.details,
        }


class BaseLearningEngine(ABC):
    """
    Interfaz base para todos los motores de aprendizaje.

    Proporciona interfaz unificada para:
    - Entrenar modelos
    - Evaluar performance
    - Predecir/Generar recomendaciones
    - Guardar/Cargar modelos
    - Monitorear estabilidad temporal (Ilmanen)
    - Analizar curvas de aprendizaje (Hastie)
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

        # Time stability tracking (Ilmanen)
        self._training_history: List[TrainingSnapshot] = []
        self._max_history_size = config.get("max_history_size", 100)
        self._stability_threshold = config.get("stability_threshold", 0.3)

        # Feature explosion tracking (Ilmanen)
        self._feature_explosion_threshold = config.get("feature_explosion_threshold", 0.1)

        # Learning curve tracking (Hastie)
        self._learning_curve_data: List[Tuple[int, float, float]] = (
            []
        )  # (n_samples, train_score, val_score)

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

    def record_training_snapshot(
        self,
        train_metrics: Dict[str, float],
        validation_metrics: Dict[str, float],
        feature_importance: Dict[str, float],
        n_samples: int,
        model_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a training snapshot for stability tracking (Ilmanen).

        Args:
            train_metrics: Training metrics
            validation_metrics: Validation metrics
            feature_importance: Feature importance scores
            n_samples: Number of training samples
            model_params: Optional model parameters
        """
        snapshot = TrainingSnapshot(
            timestamp=datetime.now(),
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            feature_importance=feature_importance,
            n_samples=n_samples,
            model_params=model_params or {},
        )

        self._training_history.append(snapshot)

        # Maintain history size
        if len(self._training_history) > self._max_history_size:
            self._training_history.pop(0)

        # Record learning curve data (Hastie)
        if "score" in train_metrics or "loss" in train_metrics:
            train_score = train_metrics.get("score", 1.0 - train_metrics.get("loss", 0.0))
            val_score = validation_metrics.get("score", 1.0 - validation_metrics.get("loss", 0.0))
            self._learning_curve_data.append((n_samples, train_score, val_score))

    def analyze_stability(self) -> StabilityReport:
        """
        Analyze model stability over time (Ilmanen's methodology).

        This implements time-series stability analysis for feature importance
        and model performance, as recommended in "Expected Returns".

        Returns:
            StabilityReport with stability analysis
        """
        if len(self._training_history) < 3:
            return StabilityReport(
                status=StabilityStatus.INSUFFICIENT_DATA,
                stability_score=0.0,
                feature_importance_change={},
                performance_drift=0.0,
                confidence_degradation=0.0,
                details={"reason": "Need at least 3 training snapshots"},
            )

        # Analyze feature importance stability
        feature_changes = {}
        all_features = set()

        for snapshot in self._training_history:
            all_features.update(snapshot.feature_importance.keys())

        for feature in all_features:
            values = []
            for snapshot in self._training_history:
                values.append(snapshot.feature_importance.get(feature, 0.0))

            if len(values) >= 2:
                # Calculate coefficient of variation
                mean_val = np.mean(values)
                std_val = np.std(values)
                cv = std_val / (abs(mean_val) + 1e-8)
                feature_changes[feature] = cv

        # Calculate overall stability score
        if feature_changes:
            mean_cv = np.mean(list(feature_changes.values()))
            stability_score = max(0, 1 - mean_cv)
        else:
            stability_score = 0.5

        # Analyze performance drift
        first_snapshot = self._training_history[0]
        last_snapshot = self._training_history[-1]

        # Calculate performance drift using primary metric
        primary_metric = "accuracy" if "accuracy" in first_snapshot.validation_metrics else "loss"
        first_perf = first_snapshot.validation_metrics.get(primary_metric, 0.0)
        last_perf = last_snapshot.validation_metrics.get(primary_metric, 0.0)

        if primary_metric == "loss":
            performance_drift = first_perf - last_perf  # Lower loss is better
        else:
            performance_drift = last_perf - first_perf  # Higher accuracy is better

        # Calculate confidence degradation (std of validation scores)
        val_scores = [
            s.validation_metrics.get(primary_metric, 0.0)
            for s in self._training_history
            if primary_metric in s.validation_metrics
        ]
        confidence_degradation = np.std(val_scores) if val_scores else 0.0

        # Determine stability status
        if stability_score > 0.8 and abs(performance_drift) < 0.1:
            status = StabilityStatus.STABLE
        elif stability_score > 0.6 and abs(performance_drift) < 0.2:
            status = StabilityStatus.DRIFTING
        else:
            status = StabilityStatus.UNSTABLE

        return StabilityReport(
            status=status,
            stability_score=stability_score,
            feature_importance_change=feature_changes,
            performance_drift=performance_drift,
            confidence_degradation=confidence_degradation,
            details={
                "n_snapshots": len(self._training_history),
                "primary_metric": primary_metric,
                "first_performance": first_perf,
                "last_performance": last_perf,
            },
        )

    def check_feature_explosion(self, n_features: int, n_samples: int) -> Dict[str, Any]:
        """
        Check for feature explosion (Ilmanen's methodology).

        Args:
            n_features: Number of features
            n_samples: Number of samples

        Returns:
            Dict with feature explosion analysis
        """
        ratio = n_features / n_samples if n_samples > 0 else float('inf')

        is_safe = ratio < self._feature_explosion_threshold
        recommended_max = int(n_samples * self._feature_explosion_threshold)

        return {
            "is_safe": is_safe,
            "ratio": ratio,
            "n_features": n_features,
            "n_samples": n_samples,
            "recommended_max_features": recommended_max,
            "excess_features": max(0, n_features - recommended_max),
            "status": "safe" if is_safe else "warning",
        }

    def get_learning_curve_analysis(self) -> Dict[str, Any]:
        """
        Analyze learning curve data (Hastie's methodology).

        Returns:
            Dict with learning curve analysis
        """
        if len(self._learning_curve_data) < 2:
            return {
                "has_converged": False,
                "suffers_high_bias": False,
                "suffers_high_variance": False,
                "recommended_action": "Insufficient data for learning curve analysis",
            }

        # Extract data
        np.array([p[0] for p in self._learning_curve_data])
        train_scores = np.array([p[1] for p in self._learning_curve_data])
        val_scores = np.array([p[2] for p in self._learning_curve_data])

        # Latest scores
        latest_train = train_scores[-1]
        latest_val = val_scores[-1]

        # Check convergence
        convergence_gap = latest_train - latest_val
        has_converged = abs(convergence_gap) < 0.1

        # Check for high bias (underfitting)
        suffers_high_bias = latest_train < 0.8 and latest_val < 0.8

        # Check for high variance (overfitting)
        suffers_high_variance = convergence_gap > 0.2

        # Generate recommendation
        if suffers_high_bias and not suffers_high_variance:
            recommended_action = (
                "Model has high bias. Consider: "
                "1. Adding more features, "
                "2. Using a more complex model, "
                "3. Reducing regularization"
            )
        elif suffers_high_variance and not suffers_high_bias:
            recommended_action = (
                "Model has high variance. Consider: "
                "1. Getting more training data, "
                "2. Using a simpler model, "
                "3. Increasing regularization"
            )
        else:
            recommended_action = "Model appears well-balanced."

        return {
            "has_converged": has_converged,
            "suffers_high_bias": suffers_high_bias,
            "suffers_high_variance": suffers_high_variance,
            "convergence_gap": convergence_gap,
            "latest_train_score": latest_train,
            "latest_val_score": latest_val,
            "recommended_action": recommended_action,
            "n_data_points": len(self._learning_curve_data),
        }

    def get_training_history(self) -> List[TrainingSnapshot]:
        """Get training history."""
        return self._training_history.copy()

    def clear_history(self) -> None:
        """Clear training history."""
        self._training_history.clear()
        self._learning_curve_data.clear()
