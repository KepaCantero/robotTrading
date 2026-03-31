"""
MultiTaskLearning - Sistema de aprendizaje multi-tarea para trading.

Incluye:
1. Compartir representaciones entre tareas (return, Sharpe, drawdown)
2. Multi-objective optimization con pesos adaptativos
3. Task-specific heads con shared backbone
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Importaciones opcionales para PyTorch
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim

    PYTORCH_AVAILABLE = True
except ImportError:  # B014: ModuleNotFoundError is a subclass of ImportError
    torch = None
    nn = None
    optim = None
    PYTORCH_AVAILABLE = False


class SharedBackbone(nn.Module):
    """
    Backbone compartido para múltiples tareas.

    Extrae características que son compartidas entre todas las tareas.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int],
        dropout: float = 0.1,
    ):
        """
        Inicializar backbone compartido.

        Args:
            input_dim: Dimensión de entrada (número de features)
            hidden_dims: Lista de dimensiones de capas ocultas
            dropout: Dropout rate
        """
        super().__init__()

        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido para SharedBackbone")

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim

        self.shared_layers = nn.Sequential(*layers)
        self.output_dim = prev_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass del backbone compartido."""
        return self.shared_layers(x)


class TaskHead(nn.Module):
    """
    Head específico para una tarea.

    Toma la representación compartida y genera predicción para la tarea.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int],
        output_dim: int = 1,
        task_type: str = "regression",
    ):
        """
        Inicializar task head.

        Args:
            input_dim: Dimensión de entrada (output del backbone)
            hidden_dims: Dimensiones de capas ocultas
            output_dim: Dimensión de salida
            task_type: Tipo de tarea ('regression' o 'classification')
        """
        super().__init__()

        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido para TaskHead")

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, output_dim))

        if task_type == "classification":
            layers.append(nn.Sigmoid())

        self.head = nn.Sequential(*layers)
        self.task_type = task_type

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass del task head."""
        return self.head(x)


class MultiTaskModel(nn.Module):
    """
    Modelo multi-tarea con backbone compartido y heads específicos.
    """

    def __init__(
        self,
        input_dim: int,
        shared_hidden_dims: list[int],
        task_configs: dict[str, dict[str, Any]],
        dropout: float = 0.1,
    ):
        """
        Inicializar modelo multi-tarea.

        Args:
            input_dim: Dimensión de entrada
            shared_hidden_dims: Dimensiones de capas ocultas compartidas
            task_configs: Configuración de tareas
                Ejemplo: {
                    'return': {'hidden_dims': [64, 32], 'type': 'regression'},
                    'sharpe': {'hidden_dims': [64, 32], 'type': 'regression'},
                    'drawdown': {'hidden_dims': [64, 32], 'type': 'regression'}
                }
            dropout: Dropout rate
        """
        super().__init__()

        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido para MultiTaskModel")

        # Backbone compartido
        self.backbone = SharedBackbone(input_dim, shared_hidden_dims, dropout)
        backbone_output_dim = self.backbone.output_dim

        # Task heads
        self.task_heads = nn.ModuleDict()
        for task_name, task_config in task_configs.items():
            hidden_dims = task_config.get("hidden_dims", [64, 32])
            task_type = task_config.get("type", "regression")
            output_dim = task_config.get("output_dim", 1)

            self.task_heads[task_name] = TaskHead(
                backbone_output_dim, hidden_dims, output_dim, task_type
            )

    def forward(self, x: torch.Tensor, task_name: Optional[str] = None) -> dict[str, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Input features
            task_name: Nombre de la tarea (si None, retorna todas)

        Returns:
            Dict con predicciones por tarea
        """
        # Extraer representación compartida
        shared_repr = self.backbone(x)

        # Generar predicciones
        if task_name:
            return {task_name: self.task_heads[task_name](shared_repr)}
        else:
            return {name: head(shared_repr) for name, head in self.task_heads.items()}


class MultiObjectiveOptimizer:
    """
    Optimizador multi-objetivo para balancear múltiples métricas.

    Soporta:
    - Return (maximizar)
    - Sharpe ratio (maximizar)
    - Drawdown (minimizar)
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar optimizador multi-objetivo.

        Args:
            config: Configuración con pesos iniciales
        """
        config = config or {}

        # Pesos adaptativos para cada objetivo
        self.weights = {
            "return": config.get("return_weight", 0.4),
            "sharpe": config.get("sharpe_weight", 0.4),
            "drawdown": config.get("drawdown_weight", 0.2),
        }

        # Normalización de objetivos
        self.normalize_objectives = config.get("normalize_objectives", True)

        # Historial para adaptación de pesos
        self.objective_history: dict[str, list[float]] = defaultdict(list)

    def compute_weighted_loss(
        self,
        predictions: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
        task_losses: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        """
        Calcular pérdida ponderada multi-objetivo.

        Args:
            predictions: Predicciones por tarea
            targets: Targets por tarea
            task_losses: Pérdidas por tarea (ya calculadas)

        Returns:
            Pérdida total ponderada
        """
        total_loss = torch.tensor(0.0)

        for task_name, loss in task_losses.items():
            if task_name in self.weights:
                weight = self.weights[task_name]
                total_loss += weight * loss

        return total_loss

    def update_weights_adaptive(
        self, performance_history: dict[str, list[float]], window_size: int = 10
    ) -> dict[str, float]:
        """
        Actualizar pesos adaptativamente basado en performance reciente.

        Args:
            performance_history: Historial de performance por objetivo
            window_size: Tamaño de ventana para análisis

        Returns:
            Nuevos pesos
        """
        if not performance_history:
            return self.weights

        # Calcular tendencias recientes
        trends: dict[str, float] = {}
        for objective, history in performance_history.items():
            if len(history) >= window_size:
                recent = history[-window_size:]
                trend = float(np.mean(np.diff(recent)))  # Tendencia (positiva = mejorando)
                trends[objective] = trend
            else:
                trends[objective] = 0.0

        # Ajustar pesos: más peso a objetivos que están mejorando
        total_trend = sum(abs(t) for t in trends.values())
        if total_trend > 0:
            for objective in self.weights:
                if objective in trends:
                    # Normalizar tendencia
                    normalized_trend = trends[objective] / total_trend if total_trend > 0 else 0
                    # Ajustar peso (pequeño ajuste)
                    adjustment = normalized_trend * 0.1
                    self.weights[objective] = max(
                        0.1, min(0.7, self.weights[objective] + adjustment)
                    )

        # Normalizar pesos
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

        return self.weights.copy()

    def get_objective_weights(self) -> dict[str, float]:
        """Obtener pesos actuales."""
        return self.weights.copy()


class MultiTaskLearningEngine:
    """
    Engine de aprendizaje multi-tarea para trading.

    Combina:
    - SharedBackbone para representaciones compartidas
    - TaskHeads específicos para cada objetivo
    - MultiObjectiveOptimizer para balancear objetivos
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar multi-task learning engine.

        Args:
            config: Configuración
        """
        self.config = config
        self.model: Optional[MultiTaskModel] = None
        self.optimizer: Optional[Any] = None  # optim.Adam when torch is available
        self.multi_objective_optimizer = MultiObjectiveOptimizer(
            config.get("multi_objective_config", {})
        )

        # Configuración de tareas
        self.task_configs = config.get(
            "tasks",
            {
                "return": {"hidden_dims": [64, 32], "type": "regression", "output_dim": 1},
                "sharpe": {"hidden_dims": [64, 32], "type": "regression", "output_dim": 1},
                "drawdown": {"hidden_dims": [64, 32], "type": "regression", "output_dim": 1},
            },
        )

        # Parámetros de entrenamiento
        self.input_dim = config.get("input_dim", 50)
        self.shared_hidden_dims = config.get("shared_hidden_dims", [128, 64])
        self.learning_rate = config.get("learning_rate", 0.001)
        self.epochs = config.get("epochs", 100)
        self.batch_size = config.get("batch_size", 32)

        self.is_trained = False

    def _prepare_training_data(
        self, training_data: dict[str, Any]
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """
        Preparar datos de entrenamiento.

        Args:
            training_data: Datos con features y targets por tarea

        Returns:
            (features_tensor, targets_dict)
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido")

        # Features
        features = training_data.get("features")
        if isinstance(features, np.ndarray):
            features_tensor = torch.FloatTensor(features)
        elif isinstance(features, pd.DataFrame):
            features_tensor = torch.FloatTensor(features.values)
        else:
            raise ValueError("Features deben ser numpy array o DataFrame")

        # Targets por tarea
        targets_dict = {}
        for task_name in self.task_configs:
            task_targets = training_data.get(f"targets_{task_name}")
            if task_targets is not None:
                if isinstance(task_targets, np.ndarray):
                    targets_dict[task_name] = torch.FloatTensor(task_targets)
                elif isinstance(task_targets, pd.Series):
                    targets_dict[task_name] = torch.FloatTensor(task_targets.values)
                else:
                    raise ValueError(f"Targets para {task_name} deben ser numpy array o Series")

        return features_tensor, targets_dict

    def train(
        self, training_data: dict[str, Any], validation_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Entrenar modelo multi-tarea.

        Args:
            training_data: Datos de entrenamiento
            validation_data: Datos de validación opcionales

        Returns:
            Métricas de entrenamiento
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido")

        try:
            # Preparar datos
            X_train, y_train_dict = self._prepare_training_data(training_data)

            # Crear modelo si no existe
            if self.model is None:
                self.model = MultiTaskModel(
                    self.input_dim,
                    self.shared_hidden_dims,
                    self.task_configs,
                    dropout=self.config.get("dropout", 0.1),
                )
            model = self.model  # Local reference for type narrowing

            # Optimizer
            if self.optimizer is None:
                self.optimizer = optim.Adam(model.parameters(), lr=self.learning_rate)
            optimizer = self.optimizer  # Local reference for type narrowing

            # Loss functions por tarea
            loss_functions = {}
            for task_name, task_config in self.task_configs.items():
                task_type = task_config.get("type", "regression")
                if task_type == "regression":
                    loss_functions[task_name] = nn.MSELoss()
                else:
                    loss_functions[task_name] = nn.BCELoss()

            # Training loop
            metrics: dict[str, list[float]] = defaultdict(list)
            model.train()

            for epoch in range(self.epochs):
                optimizer.zero_grad()

                # Forward pass
                predictions = model(X_train)

                # Calcular pérdidas por tarea
                task_losses = {}
                for task_name in self.task_configs:
                    if task_name in y_train_dict and task_name in predictions:
                        loss_fn = loss_functions[task_name]
                        loss = loss_fn(predictions[task_name], y_train_dict[task_name].unsqueeze(1))
                        task_losses[task_name] = loss
                        metrics[f"{task_name}_loss"].append(float(loss.item()))

                # Pérdida total ponderada
                total_loss = self.multi_objective_optimizer.compute_weighted_loss(
                    predictions, y_train_dict, task_losses
                )

                # Backward pass
                total_loss.backward()
                optimizer.step()

                metrics["total_loss"].append(float(total_loss.item()))

                # Actualizar pesos adaptativos cada 10 epochs
                if (epoch + 1) % 10 == 0 and epoch > 0:
                    # Usar historial de pérdidas para actualizar pesos
                    recent_performance = {
                        task_name: metrics[f"{task_name}_loss"][-10:]
                        for task_name in self.task_configs
                        if f"{task_name}_loss" in metrics
                    }
                    new_weights = self.multi_objective_optimizer.update_weights_adaptive(
                        recent_performance, window_size=10
                    )
                    logger.debug(f"Epoch {epoch + 1}: Updated weights = {new_weights}")

                if (epoch + 1) % 20 == 0:
                    logger.info(
                        f"Epoch {epoch + 1}/{self.epochs}, "
                        f"Total Loss: {total_loss.item():.4f}, "
                        f"Task Losses: {[f'{k}={v.item():.4f}' for k, v in task_losses.items()]}"
                    )

            # Validation
            if validation_data:
                val_metrics = self._evaluate(validation_data)
                for k, v in val_metrics.items():
                    metrics[f"val_{k}"] = [v]

            self.is_trained = True

            return {
                "final_total_loss": metrics["total_loss"][-1],
                "final_task_losses": {
                    task_name: metrics[f"{task_name}_loss"][-1]
                    for task_name in self.task_configs
                    if f"{task_name}_loss" in metrics
                },
                "final_weights": self.multi_objective_optimizer.get_objective_weights(),
            }

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error entrenando multi-task model: {e}", exc_info=True)
            raise

    def _evaluate(self, test_data: dict[str, Any]) -> dict[str, float]:
        """Evaluar modelo."""
        if not PYTORCH_AVAILABLE or self.model is None:
            return {}

        try:
            X_test, y_test_dict = self._prepare_training_data(test_data)

            self.model.eval()
            with torch.no_grad():
                predictions = self.model(X_test)

                metrics = {}
                for task_name in self.task_configs:
                    if task_name in predictions and task_name in y_test_dict:
                        pred = predictions[task_name].cpu().numpy().flatten()
                        true = y_test_dict[task_name].cpu().numpy().flatten()

                        # MSE para regresión
                        mse = np.mean((pred - true) ** 2)
                        mae = np.mean(np.abs(pred - true))

                        metrics[f"{task_name}_mse"] = float(mse)
                        metrics[f"{task_name}_mae"] = float(mae)

            return metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error evaluando: {e}", exc_info=True)
            return {}

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Predecir para todas las tareas.

        Args:
            features: Features de entrada

        Returns:
            Dict con predicciones por tarea
        """
        if not PYTORCH_AVAILABLE or self.model is None or not self.is_trained:
            return {"return": 0.0, "sharpe": 0.0, "drawdown": 0.0, "confidence": 0.0}

        try:
            # Preparar features
            if isinstance(features, np.ndarray):
                features_tensor = torch.FloatTensor(features)
            elif isinstance(features, pd.DataFrame):
                features_tensor = torch.FloatTensor(features.values)
            elif isinstance(features, dict):
                # Convertir dict a array
                features_array = np.array(
                    [features.get(f"feature_{i}", 0.0) for i in range(self.input_dim)]
                )
                features_tensor = torch.FloatTensor(features_array).unsqueeze(0)
            else:
                raise ValueError("Features deben ser numpy array, DataFrame o dict")

            self.model.eval()
            with torch.no_grad():
                predictions = self.model(features_tensor)

                # Convertir a dict de valores
                result = {}
                for task_name, pred_tensor in predictions.items():
                    result[task_name] = float(pred_tensor.item())

                # Calcular confidence basado en consistencia de predicciones
                if len(result) >= 2:
                    # Confidence = inverso de varianza de predicciones normalizadas
                    values = list(result.values())
                    normalized = np.array(values) / (float(np.max(np.abs(values))) + 1e-8)
                    confidence = 1.0 - min(1.0, float(np.std(normalized)))
                    result["confidence"] = float(confidence)
                else:
                    result["confidence"] = 0.5

                return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error prediciendo: {e}", exc_info=True)
            return {"return": 0.0, "sharpe": 0.0, "drawdown": 0.0, "confidence": 0.0}
