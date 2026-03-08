# mypy: ignore-errors
"""
Random Search Optimizer - FASE 6.1

Implements random parameter sampling from parameter space with:
- Linear and log scale support
- Continuous and categorical parameters
- More efficient than grid for high dimensions
"""

import logging
import random
from datetime import datetime
from math import exp, log
from typing import Any, Callable, Dict, List

import numpy as np
from tqdm import tqdm

from .base_optimizer import BaseOptimizer, OptimizationConfig, OptimizationResult
from .models import ParameterGrid, ParameterRange, ParameterScale, ParameterType
from .trial import TrialHistory, TrialResult, TrialStatus, create_trial_id

logger = logging.getLogger(__name__)


class RandomSearchOptimizer(BaseOptimizer):
    """
    Random search over parameter space.

    More efficient than grid search for high-dimensional parameter spaces.
    Samples random points from parameter space without systematic enumeration.

    Features:
    - Random sampling from parameter space
    - Support for linear and log scales
    - Handles continuous, discrete, and categorical parameters
    - Early stopping support
    - Best parameters tracking

    Advantages over grid search:
    - More efficient in high dimensions
    - Better coverage of continuous parameters
    - No combinatorial explosion

    Example:
        ```python
        from app.domain.optimization.parameter import RandomSearchOptimizer, ParameterGrid, ParameterRange

        param_grid = ParameterGrid(parameters=[
            ParameterRange(name="learning_rate", min_value=1e-5, max_value=1e-1, scale="log"),
            ParameterRange(name="batch_size", min_value=16, max_value=256, step=16),
            ParameterRange(name="optimizer", values=["adam", "sgd", "rmsprop"]),
        ])

        config = OptimizationConfig(
            max_iterations=100,
            n_jobs=4,
            early_stopping=True,
        )

        optimizer = RandomSearchOptimizer(config)

        def objective(params):
            # Evaluate model with these hyperparameters
            return train_and_evaluate(params)["validation_accuracy"]

        result = await optimizer.optimize(objective, param_grid)
        logger.debug(f"Best params: {result.best_params}")
        ```
    """

    def __init__(self, config: OptimizationConfig):
        """
        Initialize random search optimizer.

        Args:
            config: Optimization configuration
        """
        super().__init__(config)
        self._sampled_params: List[Dict[str, Any]] = []

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        param_grid: ParameterGrid,
    ) -> OptimizationResult:
        """
        Run random search optimization.

        Process:
        1. Sample random parameter combinations
        2. Evaluate each combination
        3. Track best parameters throughout
        4. Apply early stopping if enabled
        5. Return best parameters found

        Args:
            objective: Function to maximize/minimize
            param_grid: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        self._start_time = datetime.now()
        self.history = TrialHistory()
        self._iteration_count = 0
        self._sampled_params = []

        if self.config.verbose >= 1:
            logger.info("Starting random search optimization")
            logger.info(f"Max iterations: {self.config.max_iterations}")

        best_params = {}
        best_score = float("-inf") if self.config.maximize else float("inf")

        # Setup progress bar
        pbar = None
        if self.config.progress_bar and self.config.verbose >= 1:
            pbar = tqdm(
                total=self.config.max_iterations,
                desc="Random Search",
                unit="iter",
            )

        try:
            for iteration in range(self.config.max_iterations):
                # Check timeout
                if self._check_timeout():
                    logger.warning("Timeout reached, stopping optimization")
                    break

                # Sample random parameters
                params = self._sample_random_params(param_grid)

                # Check for duplicates
                if params in self._sampled_params:
                    if self.config.verbose >= 2:
                        logger.debug(f"Duplicate sample at iteration {iteration}, resampling")
                    continue

                self._sampled_params.append(params)

                # Evaluate parameters
                result = await self._evaluate_params_async(params, objective, iteration)
                self.history.add_trial(result)

                # Update best
                if result.is_success:
                    if self.config.maximize:
                        is_better = result.objective_value > best_score
                    else:
                        is_better = result.objective_value < best_score

                    if is_better:
                        best_score = result.objective_value
                        best_params = result.params

                        if self.config.verbose >= 1:
                            logger.info(f"Iteration {iteration}: New best score = {best_score:.6f}")

                self._iteration_count += 1

                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({"best": f"{best_score:.4f}"})

                self._log_progress(iteration, best_score, best_params)

                # Check early stopping
                if self._should_stop_early():
                    if self.config.verbose >= 1:
                        logger.info("Early stopping triggered")
                    break

                # Save checkpoint
                if self.config.checkpoint_interval > 0:
                    self._save_checkpoint(iteration)

        finally:
            if pbar:
                pbar.close()

        self._end_time = datetime.now()
        self.history.finish()

        result = self._create_result(best_params, best_score)

        if self.config.verbose >= 1:
            logger.info(f"Random search completed in {result.optimization_time:.2f}s")
            logger.info(f"Best score: {result.best_score:.6f}")
            logger.info(f"Evaluated {len(result.all_trials)} combinations")

        return result

    def _sample_random_params(self, param_grid: ParameterGrid) -> Dict[str, Any]:
        """
        Sample a random parameter combination.

        Args:
            param_grid: Parameter grid defining search space

        Returns:
            Random parameter dictionary
        """
        max_attempts = 100

        for attempt in range(max_attempts):
            params = {}

            for param_range in param_grid.parameters:
                params[param_range.name] = self._sample_parameter(param_range)

            # Check constraints
            if param_grid._check_constraints(params):
                return params

            if self.config.verbose >= 2:
                logger.debug(f"Sampled params violate constraints, attempt {attempt + 1}")

        # If no valid sample found, return without constraint checking
        return {p.name: self._sample_parameter(p) for p in param_grid.parameters}

    def _sample_parameter(self, param: ParameterRange) -> Any:
        """
        Sample a single parameter value.

        Args:
            param: ParameterRange defining the parameter

        Returns:
            Sampled value
        """
        if param.parameter_type == ParameterType.CATEGORICAL:
            return self._sample_categorical(param)

        elif param.parameter_type == ParameterType.DISCRETE:
            return self._sample_discrete(param)

        elif param.parameter_type == ParameterType.INTEGER:
            return self._sample_integer(param)

        elif param.parameter_type == ParameterType.CONTINUOUS:
            return self._sample_continuous(param)

        raise ValueError(f"Unknown parameter type: {param.parameter_type}")

    def _sample_categorical(self, param: ParameterRange) -> Any:
        """Sample from categorical values."""
        return random.choice(param.values)  # type: ignore

    def _sample_discrete(self, param: ParameterRange) -> Any:
        """Sample from discrete values."""
        return random.choice(param.values)  # type: ignore

    def _sample_integer(self, param: ParameterRange) -> int:
        """
        Sample from integer range.

        Args:
            param: ParameterRange with integer type

        Returns:
            Random integer value
        """
        min_val = int(param.min_value)  # type: ignore
        max_val = int(param.max_value)  # type: ignore
        step = int(param.step) if param.step else 1  # type: ignore

        if step == 1:
            return random.randint(min_val, max_val)
        else:
            num_steps = (max_val - min_val) // step
            random_step = random.randint(0, num_steps)
            return min_val + random_step * step

    def _sample_continuous(self, param: ParameterRange) -> float:
        """
        Sample from continuous range.

        Supports both linear and log scales.

        Args:
            param: ParameterRange with continuous type

        Returns:
            Random float value
        """
        min_val = float(param.min_value)  # type: ignore
        max_val = float(param.max_value)  # type: ignore
        step = float(param.step) if param.step else None  # type: ignore

        if param.scale == ParameterScale.LOG:
            # Log scale sampling
            log_min = log(min_val)
            log_max = log(max_val)
            log_value = random.uniform(log_min, log_max)
            value = exp(log_value)

            # Apply step if specified
            if step:
                # Quantize to step size
                quantized = round(value / step) * step
                value = max(min_val, min(max_val, quantized))

            return value
        else:
            # Linear scale sampling
            if step:
                # Discretized continuous
                num_steps = int((max_val - min_val) / step)
                random_step = random.randint(0, num_steps)
                return min_val + random_step * step
            else:
                return random.uniform(min_val, max_val)

    def _sample_log_uniform(
        self,
        min_value: float,
        max_value: float,
        base: float = 10.0,
    ) -> float:
        """
        Sample from log-uniform distribution.

        Args:
            min_value: Minimum value (positive)
            max_value: Maximum value (positive)
            base: Log base (default 10)

        Returns:
            Random value sampled log-uniformly
        """
        import math

        if min_value <= 0 or max_value <= 0:
            raise ValueError("Log scale requires positive values")

        log_min = math.log(min_value, base)
        log_max = math.log(max_value, base)

        log_value = random.uniform(log_min, log_max)

        return base**log_value

    def get_sampled_params(self) -> List[Dict[str, Any]]:
        """
        Get all sampled parameter combinations.

        Returns:
            List of parameter dictionaries
        """
        return self._sampled_params.copy()

    def get_unique_sample_count(self) -> int:
        """
        Get count of unique parameter combinations sampled.

        Returns:
            Number of unique combinations
        """
        return len(self._sampled_params)


class RandomSearchOptimizerCV(RandomSearchOptimizer):
    """
    Random Search with Cross-Validation.

    Extends RandomSearchOptimizer to use cross-validation for more robust
    parameter selection.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        cv_folds: int = 5,
        cv_metric: str = "mean",
    ):
        """
        Initialize random search with CV.

        Args:
            config: Optimization configuration
            cv_folds: Number of CV folds
            cv_metric: How to aggregate CV scores ('mean', 'min', 'median')
        """
        super().__init__(config)
        self.cv_folds = cv_folds
        self.cv_metric = cv_metric

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any], int], float],
        param_grid: ParameterGrid,
    ) -> OptimizationResult:
        """
        Run random search with cross-validation.

        The objective function should accept (params, fold_index) arguments.

        Args:
            objective: CV objective function
            param_grid: Parameter search space

        Returns:
            OptimizationResult with best parameters
        """
        self._start_time = datetime.now()
        self.history = TrialHistory()
        self._iteration_count = 0
        self._sampled_params = []

        best_params = {}
        best_cv_score = float("-inf") if self.config.maximize else float("inf")

        # Setup progress bar
        pbar = None
        if self.config.progress_bar and self.config.verbose >= 1:
            pbar = tqdm(total=self.config.max_iterations, desc="Random Search (CV)")

        try:
            for iteration in range(self.config.max_iterations):
                if self._check_timeout():
                    break

                # Sample random parameters
                params = self._sample_random_params(param_grid)

                if params in self._sampled_params:
                    continue

                self._sampled_params.append(params)

                # Run CV
                cv_scores = []
                for fold in range(self.cv_folds):
                    try:
                        score = objective(params, fold)
                        cv_scores.append(score)
                    except Exception as e:
                        logger.warning(f"CV fold {fold} failed: {e}")
                        cv_scores.append(float("-inf") if self.config.maximize else float("inf"))

                # Aggregate CV scores
                cv_score = self._aggregate_cv_scores(cv_scores)

                # Create trial result
                result = TrialResult(
                    trial_id=create_trial_id(),
                    params=params,
                    objective_value=cv_score,
                    status=TrialStatus.COMPLETED,
                    iteration=iteration,
                    metrics={
                        "cv_scores": cv_scores,
                        "cv_mean": np.mean(cv_scores) if cv_scores else 0.0,
                        "cv_std": self._std(cv_scores) if len(cv_scores) > 1 else 0.0,
                        "cv_min": min(cv_scores) if cv_scores else 0.0,
                        "cv_max": max(cv_scores) if cv_scores else 0.0,
                    },
                )

                self.history.add_trial(result)

                # Update best
                if self.config.maximize:
                    is_better = cv_score > best_cv_score
                else:
                    is_better = cv_score < best_cv_score

                if is_better:
                    best_cv_score = cv_score
                    best_params = params

                    if self.config.verbose >= 1:
                        logger.info(
                            f"Iteration {iteration}: New best CV score = {best_cv_score:.6f}"
                        )

                self._iteration_count += 1

                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({"best": f"{best_cv_score:.4f}"})

                if self._should_stop_early():
                    break

        finally:
            if pbar:
                pbar.close()

        self._end_time = datetime.now()
        return self._create_result(best_params, best_cv_score)

    def _aggregate_cv_scores(self, cv_scores: List[float]) -> float:
        """Aggregate cross-validation scores."""
        if not cv_scores:
            return float("-inf") if self.config.maximize else float("inf")

        if self.cv_metric == "mean":
            return np.mean(cv_scores)
        elif self.cv_metric == "min":
            return min(cv_scores)
        elif self.cv_metric == "median":
            sorted_scores = sorted(cv_scores)
            mid = len(sorted_scores) // 2
            if len(sorted_scores) % 2 == 1:
                return sorted_scores[mid]
            else:
                return (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
        else:
            return np.mean(cv_scores)

    def _std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        import statistics

        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)
