"""
HyperparameterTuner - Sistema de optimización automática de hiperparámetros.

Incluye:
1. Bayesian optimization con Optuna
2. Early stopping adaptativo
3. Resource-aware tuning (GPU/CPU constraints)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

import numpy as np

# Configurar logger
logger = logging.getLogger(__name__)

# Verificar disponibilidad de dependencias opcionales
try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None

try:
    import torch

    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    torch = None


class EarlyStoppingAdaptive:
    """
    Early stopping adaptativo que ajusta patience basado en mejoras.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar early stopping adaptativo.

        Args:
            config: Configuración
        """
        config = config or {}
        self.patience = config.get("patience", 10)
        self.min_delta = config.get("min_delta", 1e-4)
        self.mode = config.get("mode", "min")  # 'min' o 'max'
        self.adaptive_patience = config.get("adaptive_patience", True)

        self.best_score: Optional[float] = None
        self.best_epoch = 0
        self.current_epoch = 0
        self.wait = 0
        self.stopped_epoch = 0
        self.improvement_history: list[float] = []

    def __call__(self, score: float) -> bool:
        """
        Verificar si se debe parar.

        Args:
            score: Score actual

        Returns:
            True si se debe parar
        """
        self.current_epoch += 1

        if self.best_score is None:
            self.best_score = score
            self.best_epoch = self.current_epoch
            self.wait = 0
            return False

        # Determinar si hay mejora
        if self.mode == "min":
            improved = score < (self.best_score - self.min_delta)
        else:
            improved = score > (self.best_score + self.min_delta)

        if improved:
            improvement = abs(score - self.best_score)
            self.improvement_history.append(improvement)

            # Si hay muchas mejoras pequeñas, aumentar patience
            if self.adaptive_patience and len(self.improvement_history) > 5:
                recent_improvements = self.improvement_history[-5:]
                avg_improvement = np.mean(recent_improvements)

                # Si mejoras son pequeñas pero consistentes, aumentar patience
                if avg_improvement < self.min_delta * 2:
                    self.patience = min(self.patience + 2, 30)  # Cap en 30
                    logger.debug(f"Adaptive patience aumentado a {self.patience}")

            self.best_score = score
            self.best_epoch = self.current_epoch
            self.wait = 0
            return False
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.stopped_epoch = self.current_epoch
                return True

        return False

    def reset(self) -> None:
        """Resetear estado."""
        self.best_score = None
        self.best_epoch = 0
        self.current_epoch = 0
        self.wait = 0
        self.stopped_epoch = 0
        self.improvement_history = []

    def get_best_score(self) -> Optional[float]:
        """Obtener mejor score."""
        return self.best_score

    def get_best_epoch(self) -> int:
        """Obtener epoch del mejor score."""
        return self.best_epoch


class ResourceAwareTuner:
    """
    Tuner que considera recursos disponibles (GPU/CPU, memoria, tiempo).
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar resource-aware tuner.

        Args:
            config: Configuración
        """
        config = config or {}
        self.max_trials = config.get("max_trials", 50)
        self.max_time_seconds: float = float(config.get("max_time_seconds", 3600))  # 1 hora default
        self.max_memory_gb = config.get("max_memory_gb", 8.0)

        self.start_time: Optional[float] = None
        self.trials_run = 0
        self.gpu_available = self._check_gpu()

        logger.info(
            f"ResourceAwareTuner: GPU={self.gpu_available}, Max trials={self.max_trials}, Max time={self.max_time_seconds}s"
        )

    def _check_gpu(self) -> bool:
        """Verificar si GPU está disponible."""
        if not PYTORCH_AVAILABLE:
            return False
        try:
            result = torch.cuda.is_available()
            return bool(result)
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            return False

    def should_continue(self) -> bool:
        """
        Verificar si se debe continuar tuning.

        Returns:
            True si se debe continuar
        """
        # Verificar número de trials
        if self.trials_run >= self.max_trials:
            logger.info(f"Max trials alcanzado: {self.trials_run}/{self.max_trials}")
            return False

        # Verificar tiempo
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            if elapsed >= self.max_time_seconds:
                logger.info(f"Max time alcanzado: {elapsed:.1f}s/{self.max_time_seconds}s")
                return False

        return True

    def start_tuning(self) -> None:
        """Iniciar sesión de tuning."""
        self.start_time = time.time()
        self.trials_run = 0

    def record_trial(self) -> None:
        """Registrar que un trial se ejecutó."""
        self.trials_run += 1

    def get_remaining_time(self) -> Optional[float]:
        """Obtener tiempo restante en segundos."""
        if self.start_time is None:
            return None
        elapsed = time.time() - self.start_time
        remaining = self.max_time_seconds - elapsed
        return max(0, remaining)

    def get_resource_info(self) -> dict[str, Any]:
        """Obtener información de recursos."""
        info = {
            "gpu_available": self.gpu_available,
            "trials_run": self.trials_run,
            "max_trials": self.max_trials,
        }

        if self.start_time is not None:
            info["elapsed_time"] = time.time() - self.start_time
            info["remaining_time"] = self.get_remaining_time()

        return info


class HyperparameterTuner:
    """
    Tuner principal usando Optuna para Bayesian optimization.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar hyperparameter tuner.

        Args:
            config: Configuración
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna requerido para HyperparameterTuner")

        self.config = config

        # Configuración de Optuna
        study_name = config.get("study_name", "hyperparameter_tuning")
        direction = config.get("direction", "maximize")  # 'maximize' o 'minimize'

        # Crear study
        self.study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=optuna.samplers.TPESampler(seed=42),
            pruner=optuna.pruners.MedianPruner(),
        )

        # Early stopping
        self.early_stopping = EarlyStoppingAdaptive(config.get("early_stopping_config", {}))

        # Resource-aware tuning
        self.resource_manager = ResourceAwareTuner(config.get("resource_config", {}))

        # Callback para training
        self.training_callback: Optional[Callable[..., float]] = None

    def set_training_callback(self, callback: Callable) -> None:
        """
        Establecer callback para entrenar modelo.

        Args:
            callback: Función que recibe (trial, params) y retorna score
        """
        self.training_callback = callback

    def optimize(
        self,
        n_trials: Optional[int] = None,
        timeout: Optional[float] = None,
        search_space: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Optimizar hiperparámetros.

        Args:
            n_trials: Número de trials (usa config si None)
            timeout: Timeout en segundos (usa config si None)
            search_space: Espacio de búsqueda (define en callback si None)

        Returns:
            Mejores parámetros y métricas
        """
        if self.training_callback is None:
            raise ValueError("training_callback debe estar configurado")

        training_callback = self.training_callback

        n_trials = n_trials or self.resource_manager.max_trials
        timeout = timeout or self.resource_manager.max_time_seconds

        self.resource_manager.start_tuning()

        def objective(trial):
            """Objective function para Optuna."""
            # Verificar recursos
            if not self.resource_manager.should_continue():
                raise optuna.TrialPruned()

            # Obtener hiperparámetros del trial (si no hay search_space, el callback debe sugerir parámetros)
            params = self._suggest_parameters(trial, search_space) if search_space else {}

            # Entrenar modelo y obtener score
            try:
                score = training_callback(trial, params)

                # Actualizar early stopping
                should_stop = self.early_stopping(score)
                if should_stop:
                    logger.info(f"Early stopping activado en trial {trial.number}")
                    raise optuna.TrialPruned()

                self.resource_manager.record_trial()

                return score

            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.error(f"Error en trial {trial.number}: {e}")
                raise optuna.TrialPruned() from e

        # Optimizar
        try:
            self.study.optimize(objective, n_trials=n_trials, timeout=timeout)
        except KeyboardInterrupt:
            logger.info("Optimización interrumpida por usuario")

        # Obtener mejores parámetros
        best_trial = self.study.best_trial
        best_params = best_trial.params
        best_score = best_trial.value

        return {
            "best_params": best_params,
            "best_score": best_score,
            "n_trials": len(self.study.trials),
            "study_name": self.study.study_name,
            "resource_info": self.resource_manager.get_resource_info(),
        }

    def _suggest_parameters(self, trial, search_space: dict[str, Any]) -> dict[str, Any]:
        """
        Sugerir parámetros basado en search_space.

        Args:
            trial: Optuna trial
            search_space: Espacio de búsqueda

        Returns:
            Parámetros sugeridos
        """
        params = {}

        for param_name, param_config in search_space.items():
            param_type = param_config.get("type", "float")

            if param_type == "float":
                params[param_name] = trial.suggest_float(
                    param_name,
                    param_config["low"],
                    param_config["high"],
                    log=param_config.get("log", False),
                )
            elif param_type == "int":
                params[param_name] = trial.suggest_int(
                    param_name,
                    param_config["low"],
                    param_config["high"],
                    log=param_config.get("log", False),
                )
            elif param_type == "categorical":
                params[param_name] = trial.suggest_categorical(param_name, param_config["choices"])
            else:
                logger.warning(f"Tipo de parámetro desconocido: {param_type}")

        return params

    def get_best_params(self) -> dict[str, Any]:
        """Obtener mejores parámetros encontrados."""
        if len(self.study.trials) == 0:
            return {}
        return dict(self.study.best_trial.params)

    def get_trial_history(self) -> list[dict[str, Any]]:
        """Obtener historial de trials."""
        history = []
        for trial in self.study.trials:
            history.append(
                {
                    "number": trial.number,
                    "value": trial.value,
                    "params": trial.params,
                    "state": trial.state.name,
                }
            )
        return history

    def visualize_optimization(self, output_path: Optional[str] = None) -> None:
        """
        Visualizar proceso de optimización.

        Args:
            output_path: Ruta para guardar gráficos (opcional)
        """
        try:
            import optuna.visualization as vis

            # Optimization history
            fig = vis.plot_optimization_history(self.study)
            if output_path:
                fig.write_html(f"{output_path}_optimization_history.html")

            # Parameter importance
            fig = vis.plot_param_importances(self.study)
            if output_path:
                fig.write_html(f"{output_path}_param_importances.html")

        except ImportError:
            logger.warning("Optuna visualization no disponible")


class LearningEngineTuner:
    """
    Tuner especializado para learning engines.
    """

    def __init__(
        self,
        learning_engine_class,
        engine_config: dict[str, Any],
        tuner_config: dict[str, Any],
    ):
        """
        Inicializar tuner para learning engine.

        Args:
            learning_engine_class: Clase del learning engine
            engine_config: Configuración base del engine
            tuner_config: Configuración del tuner
        """
        self.learning_engine_class = learning_engine_class
        self.engine_config = engine_config
        self.tuner = HyperparameterTuner(tuner_config)

        # Configurar callback
        self.tuner.set_training_callback(self._train_and_evaluate)

    def _train_and_evaluate(self, trial: object, params: dict[str, object]) -> float:
        """
        Entrenar y evaluar modelo con parámetros dados.

        Args:
            trial: Optuna trial
            params: Parámetros sugeridos

        Returns:
            Score (métrica a optimizar)
        """
        # Actualizar config con parámetros sugeridos
        updated_config = self.engine_config.copy()
        updated_config.update(params)

        # Crear engine
        engine = self.learning_engine_class(updated_config)

        # Obtener datos de entrenamiento (debe estar en config o pasado de otra forma)
        training_data = self.engine_config.get("training_data")
        validation_data = self.engine_config.get("validation_data")

        if training_data is None:
            raise ValueError("training_data debe estar en engine_config")

        # Entrenar
        try:
            metrics = engine.train(training_data, validation_data)

            # Retornar métrica a optimizar (ej: accuracy, f1_score, o neg_sharpe)
            metric_name = self.tuner.config.get("optimize_metric", "accuracy")
            score = float(metrics.get(metric_name, 0.0))

            # Si direction es 'maximize', retornar score tal cual
            # Si es 'minimize', retornar negativo
            if self.tuner.config.get("direction") == "minimize":
                score = -score

            return score

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            trial_num = getattr(trial, "number", 0)
            logger.error(f"Error entrenando en trial {trial_num}: {e}")
            raise optuna.TrialPruned() from e

    def tune(
        self,
        training_data: dict[str, Any],
        validation_data: Optional[dict[str, Any]] = None,
        search_space: Optional[dict[str, Any]] = None,
        n_trials: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Tunear learning engine.

        Args:
            training_data: Datos de entrenamiento
            validation_data: Datos de validación
            search_space: Espacio de búsqueda
            n_trials: Número de trials

        Returns:
            Mejores parámetros y métricas
        """
        # Guardar datos en config para callback
        self.engine_config["training_data"] = training_data
        self.engine_config["validation_data"] = validation_data

        # Optimizar
        results = self.tuner.optimize(search_space=search_space, n_trials=n_trials)

        return results
