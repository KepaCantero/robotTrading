"""
Meta-learners for Portfolio Allocation

Implementa meta-learning para optimizar asignación de capital entre estrategias:
- Reinforcement learning para portfolio management
- Historical performance-based allocation
- Aprendizaje de pesos óptimos entre estrategias
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# REQUIRED: PyTorch is REQUIRED - NO FALLBACKS
import torch
import torch.nn as nn


class BaseMetaLearner(ABC):
    """Clase base para meta-learners."""

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar meta-learner.

        Args:
            config: Configuracion del meta-learner
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.learning_history: list[dict[str, Any]] = []

    @abstractmethod
    def learn_weights(
        self,
        strategy_performance: dict[str, dict[str, float]],
        market_context: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Aprender pesos óptimos para estrategias.

        Args:
            strategy_performance: Dict con métricas de performance por estrategia
            market_context: Contexto de mercado actual

        Returns:
            Dict con pesos aprendidos por estrategia
        """

    @abstractmethod
    def update(
        self,
        strategy_performance: dict[str, dict[str, float]],
        portfolio_return: float,
        market_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Actualizar modelo con nueva experiencia.

        Args:
            strategy_performance: Performance de estrategias
            portfolio_return: Retorno del portfolio combinado
            market_context: Contexto de mercado
        """


class HistoricalPerformanceLearner(BaseMetaLearner):
    """
    Historical Performance-based Learner.

    Asigna pesos basándose en performance histórica reciente.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar historical performance learner."""
        super().__init__(config)
        self.lookback_period = config.get("lookback_period", 30)  # días
        self.smoothing_factor = config.get("smoothing_factor", 0.1)  # Exponencial smoothing
        self.use_sharpe = config.get("use_sharpe", True)
        self.use_return = config.get("use_return", True)
        self.use_drawdown = config.get("use_drawdown", False)

        # Historial de performance
        self.performance_history: dict[
            str, list[dict[str, datetime | dict[str, float] | float]]
        ] = {}

    def learn_weights(
        self,
        strategy_performance: dict[str, dict[str, float]],
        market_context: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Aprender pesos basados en performance histórica.

        Args:
            strategy_performance: Performance reciente por estrategia
            market_context: Contexto de mercado (opcional)

        Returns:
            Pesos aprendidos
        """
        if not strategy_performance:
            return {}

        # Calcular scores para cada estrategia
        strategy_scores = {}

        for strategy, metrics in strategy_performance.items():
            score = 0.0

            # Sharpe ratio (normalizado)
            if self.use_sharpe and "sharpe_ratio" in metrics:
                sharpe = metrics["sharpe_ratio"]
                # Normalizar Sharpe (asumir rango típico -2 a 5)
                normalized_sharpe = (sharpe + 2) / 7.0
                normalized_sharpe = max(0.0, min(1.0, normalized_sharpe))
                score += normalized_sharpe * 0.4

            # Return (normalizado)
            if self.use_return and "return" in metrics:
                ret = metrics["return"]
                # Normalizar return (asumir rango típico -50% a 100%)
                normalized_return = (ret + 0.5) / 1.5
                normalized_return = max(0.0, min(1.0, normalized_return))
                score += normalized_return * 0.4

            # Drawdown penalty
            if self.use_drawdown and "max_drawdown" in metrics:
                drawdown = abs(metrics["max_drawdown"])
                # Penalizar drawdowns grandes
                drawdown_penalty = max(0.0, 1.0 - drawdown / 0.5)  # Penalizar si > 50%
                score += drawdown_penalty * 0.2

            strategy_scores[strategy] = score

        # Normalizar scores a pesos (suma = 1)
        total_score = sum(strategy_scores.values())
        if total_score > 0:
            weights = {s: score / total_score for s, score in strategy_scores.items()}
        else:
            # Fallback a pesos iguales
            n = len(strategy_scores)
            weights = dict.fromkeys(strategy_scores.keys(), 1.0 / n)

        # Aplicar smoothing exponencial si hay historial
        if self.performance_history:
            weights = self._apply_smoothing(weights, strategy_scores)

        # Guardar en historial
        self._update_history(strategy_performance)

        return weights

    def _apply_smoothing(
        self, new_weights: dict[str, float], new_scores: dict[str, float]
    ) -> dict[str, float]:
        """Aplicar smoothing exponencial a los pesos."""
        # Obtener último peso del historial
        if self.learning_history:
            last_weights = self.learning_history[-1].get("weights", {})

            # Smoothing: nuevo_peso = alpha * nuevo + (1-alpha) * anterior
            smoothed_weights = {}
            for strategy in set(list(new_weights.keys()) + list(last_weights.keys())):
                new_weight = new_weights.get(strategy, 0.0)
                last_weight = last_weights.get(strategy, 0.0)
                smoothed_weight = (
                    self.smoothing_factor * new_weight + (1 - self.smoothing_factor) * last_weight
                )
                smoothed_weights[strategy] = smoothed_weight

            # Normalizar
            total = sum(smoothed_weights.values())
            if total > 0:
                smoothed_weights = {s: w / total for s, w in smoothed_weights.items()}

            return smoothed_weights

        return new_weights

    def _update_history(self, performance: dict[str, dict[str, float]]) -> None:
        """Actualizar historial de performance."""
        for strategy, metrics in performance.items():
            if strategy not in self.performance_history:
                self.performance_history[strategy] = []

            self.performance_history[strategy].append(
                {"timestamp": datetime.utcnow(), "metrics": metrics}
            )

            # Mantener solo lookback_period días
            cutoff = datetime.utcnow() - timedelta(days=self.lookback_period)
            self.performance_history[strategy] = [
                entry for entry in self.performance_history[strategy] if entry["timestamp"] > cutoff
            ]

    def update(
        self,
        strategy_performance: dict[str, dict[str, float]],
        portfolio_return: float,
        market_context: dict[str, Any] | None = None,
    ) -> None:
        """Actualizar con nueva experiencia."""
        self._update_history(strategy_performance)

        # Guardar en learning history
        weights = self.learn_weights(strategy_performance, market_context)
        self.learning_history.append(
            {
                "timestamp": datetime.utcnow(),
                "weights": weights,
                "portfolio_return": portfolio_return,
                "market_context": market_context,
            }
        )

        # Mantener historial limitado
        max_history = self.config.get("max_history_size", 1000)
        if len(self.learning_history) > max_history:
            self.learning_history = self.learning_history[-max_history:]


class ReinforcementLearningLearner(BaseMetaLearner):
    """
    Reinforcement Learning Learner.

    Usa RL para aprender política óptima de asignación.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar RL learner."""
        super().__init__(config)

        # PyTorch es REQUIRED - ya importado al inicio del módulo
        self._initialize_model()

        self.learning_rate = config.get("learning_rate", 0.001)
        self.discount_factor = config.get("discount_factor", 0.99)
        self.exploration_rate = config.get("exploration_rate", 0.1)
        self.exploration_decay = config.get("exploration_decay", 0.995)

    def _initialize_model(self) -> None:
        """Inicializar modelo de RL."""
        # PyTorch es REQUIRED - ya importado al inicio del módulo

        # Red neuronal simple para Q-learning
        class AllocationNetwork(nn.Module):
            def __init__(self, input_size: int, output_size: int):
                super().__init__()
                self.fc1 = nn.Linear(input_size, 64)
                self.fc2 = nn.Linear(64, 32)
                self.fc3 = nn.Linear(32, output_size)
                self.relu = nn.ReLU()

            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.relu(self.fc2(x))
                x = self.fc3(x)
                return torch.softmax(x, dim=-1)  # Normalizar a pesos

        # Tamaño input: features de estrategias + contexto de mercado
        # Tamaño output: número de estrategias
        self.input_size = 20  # Ajustar según features
        self.output_size = 5  # Máximo número de estrategias

        self.model = AllocationNetwork(self.input_size, self.output_size)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

    def learn_weights(
        self,
        strategy_performance: dict[str, dict[str, float]],
        market_context: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Aprender pesos usando RL.

        Args:
            strategy_performance: Performance de estrategias
            market_context: Contexto de mercado

        Returns:
            Pesos aprendidos
        """
        if not self.model:
            raise RuntimeError(
                "ReinforcementLearningLearner model not initialized. "
                "PyTorch is required and must be available."
            )

        try:
            # Preparar features
            features = self._extract_features(strategy_performance, market_context)

            # Predecir pesos
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features).unsqueeze(0)
                weights_tensor = self.model(features_tensor)
                weights_array = weights_tensor.squeeze().numpy()

            # Mapear a estrategias
            strategy_names = list(strategy_performance.keys())
            weights = {
                strategy_names[i]: float(weights_array[i])
                for i in range(min(len(strategy_names), len(weights_array)))
            }

            # Normalizar
            total = sum(weights.values())
            if total > 0:
                weights = {s: w / total for s, w in weights.items()}

            return weights

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error en RL learner: {e}", exc_info=True)
            # No fallback - PyTorch is REQUIRED
            raise RuntimeError(f"RL learner failed: {e}") from e

    def _extract_features(
        self,
        strategy_performance: dict[str, dict[str, float]],
        market_context: dict[str, Any] | None,
    ) -> np.ndarray:
        """Extraer features para el modelo."""
        features = []

        # Features de performance de estrategias
        for _strategy, metrics in strategy_performance.items():
            features.append(metrics.get("return", 0.0))
            features.append(metrics.get("sharpe_ratio", 0.0))
            features.append(metrics.get("max_drawdown", 0.0))
            features.append(metrics.get("win_rate", 0.0))

        # Features de contexto de mercado
        if market_context:
            features.append(market_context.get("regime", 0.0))  # Codificado
            features.append(market_context.get("volatility", 0.0))
            features.append(market_context.get("trend_strength", 0.0))
        else:
            features.extend([0.0, 0.0, 0.0])

        # Padding si es necesario
        while len(features) < self.input_size:
            features.append(0.0)

        return np.array(features[: self.input_size], dtype=np.float64)

    def update(
        self,
        strategy_performance: dict[str, dict[str, float]],
        portfolio_return: float,
        market_context: dict[str, Any] | None = None,
    ) -> None:
        """Actualizar modelo RL con nueva experiencia."""
        if not self.model:
            raise RuntimeError(
                "ReinforcementLearningLearner model not initialized. "
                "PyTorch is required and must be available."
            )

        try:
            # Preparar features y target
            features = self._extract_features(strategy_performance, market_context)
            features_tensor = torch.FloatTensor(features).unsqueeze(0)

            # Reward basado en portfolio return
            reward = portfolio_return

            # Actualizar modelo (simplificado - en producción usar algoritmo completo)
            self.model.train()
            self.optimizer.zero_grad()

            # Predecir pesos
            self.model(features_tensor)

            # Loss simplificado (en producción usar algoritmo RL completo)
            # Por ahora, solo guardar experiencia
            self.learning_history.append(
                {
                    "timestamp": datetime.utcnow(),
                    "features": features.tolist(),
                    "reward": reward,
                    "market_context": market_context,
                }
            )

            # Decay exploration rate
            self.exploration_rate *= self.exploration_decay

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error actualizando RL learner: {e}", exc_info=True)


class EnsembleMetaLearner(BaseMetaLearner):
    """
    Ensemble Meta-Learner.

    Combina múltiples meta-learners para mejor asignación.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar ensemble meta-learner."""
        super().__init__(config)

        # Crear multiples learners
        self.learners: list[BaseMetaLearner] = []

        if config.get("use_historical", True):
            self.learners.append(HistoricalPerformanceLearner(config))

        if config.get("use_rl", False):
            # PyTorch es REQUIRED - ya importado al inicio del módulo
            self.learners.append(ReinforcementLearningLearner(config))

        # Pesos del ensemble
        self.learner_weights: dict[str, float] = config.get("learner_weights", {})
        if not self.learner_weights:
            # Pesos iguales por defecto
            self.learner_weights = {
                type(learner).__name__: 1.0 / len(self.learners) for learner in self.learners
            }

    def learn_weights(
        self,
        strategy_performance: dict[str, dict[str, float]],
        market_context: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Aprender pesos usando ensemble de learners.

        Args:
            strategy_performance: Performance de estrategias
            market_context: Contexto de mercado

        Returns:
            Pesos aprendidos combinados
        """
        if not self.learners:
            # Fallback a pesos iguales
            n = len(strategy_performance)
            return dict.fromkeys(strategy_performance.keys(), 1.0 / n)

        # Obtener pesos de cada learner
        all_weights = []
        learner_names = []

        for learner in self.learners:
            try:
                weights = learner.learn_weights(strategy_performance, market_context)
                all_weights.append(weights)
                learner_names.append(type(learner).__name__)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Learner {type(learner).__name__} falló: {e}")

        if not all_weights:
            # Fallback
            n = len(strategy_performance)
            return dict.fromkeys(strategy_performance.keys(), 1.0 / n)

        # Combinar pesos usando weighted average
        combined_weights: dict[str, float] = {}
        all_strategies: set[str] = set()
        for weights in all_weights:
            all_strategies.update(weights.keys())

        for strategy in all_strategies:
            weighted_sum = 0.0
            total_weight = 0.0

            for i, weights in enumerate(all_weights):
                learner_name = learner_names[i]
                learner_weight = self.learner_weights.get(learner_name, 1.0 / len(self.learners))
                strategy_weight = weights.get(strategy, 0.0)

                weighted_sum += strategy_weight * learner_weight
                total_weight += learner_weight

            if total_weight > 0:
                combined_weights[strategy] = weighted_sum / total_weight
            else:
                combined_weights[strategy] = 0.0

        # Normalizar
        total = sum(combined_weights.values())
        if total > 0:
            combined_weights = {s: w / total for s, w in combined_weights.items()}

        return combined_weights

    def update(
        self,
        strategy_performance: dict[str, dict[str, float]],
        portfolio_return: float,
        market_context: dict[str, Any] | None = None,
    ) -> None:
        """Actualizar todos los learners."""
        for learner in self.learners:
            try:
                learner.update(strategy_performance, portfolio_return, market_context)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                self.logger.warning(f"Error actualizando learner {type(learner).__name__}: {e}")
