"""
Grid Search Optimizer - Consolidated Implementation.

This module provides a unified grid search implementation that combines
the best features from:
- app/domain/optimization/parameter/grid_search.py (parameter optimization)
- app/domain/optimization/grid_search_optimizer.py (walk-forward validation)

Features:
- Exhaustive grid search over parameter space
- Parallel execution support
- Early stopping on convergence
- Progress tracking
- Cross-validation support
- Walk-forward validation integration

Usage:
    ```python
    from app.domain.optimization.grid_search_optimizer import GridSearchOptimizer
    from app.domain.optimization.base_optimizer import OptimizationConfig

    config = OptimizationConfig(
        max_iterations=1000,
        n_jobs=4,
        early_stopping=True,
    )

    optimizer = GridSearchOptimizer(config)

    # Define search space
    space = SearchSpace()
    space.add_integer("lookback", 5, 20, step=5)
    space.add_continuous("threshold", 0.1, 0.5, step=0.1)

    result = await optimizer.optimize(objective_func, space)
    ```
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from itertools import product
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from .base_optimizer import (
    BaseOptimizer,
    OptimizationConfig,
    OptimizationResult,
    OptimizationStatus,
    OptimizerType,
    TrialResult,
)
from .bayesian_optimizer import ParameterType, SearchSpace

logger = logging.getLogger(__name__)


class GridSearchOptimizer(BaseOptimizer[SearchSpace]):
    """
    Exhaustive grid search over parameter space.

    Evaluates all combinations of parameter values systematically.
    Good for small parameter spaces where exhaustive evaluation is feasible.

    Features:
    - Systematic evaluation of all combinations
    - Parallel execution support
    - Early stopping based on convergence
    - Progress tracking with optional progress bar

    Example:
        ```python
        config = OptimizationConfig(
            max_iterations=1000,
            n_jobs=4,
            early_stopping=True,
            early_stopping_patience=20,
        )

        optimizer = GridSearchOptimizer(config)

        space = SearchSpace()
        space.add_integer("lookback", 5, 20, step=5)
        space.add_continuous("threshold", 0.1, 0.5)

        def objective(params):
            return backtest_strategy(params)["sharpe_ratio"]

        result = await optimizer.optimize(objective, space)
        ```
    """

    def __init__(self, config: OptimizationConfig) -> None:
        """
        Initialize grid search optimizer.

        Args:
            config: Optimization configuration
        """
        super().__init__(config)
        self._total_combinations: Optional[int] = None
        self._evaluated_combinations: int = 0
        self._search_space: Optional[SearchSpace] = None
        self._best_params: Dict[str, Any] = {}

    @classmethod
    def get_optimizer_type(cls) -> OptimizerType:
        """Get the type of this optimizer."""
        return OptimizerType.GRID_SEARCH

    def get_best_params(self) -> Dict[str, Any]:
        """Get the best parameters found."""
        return self._best_params

    def get_history(self) -> List[TrialResult]:
        """Get optimization history."""
        return self._history

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """
        Run grid search optimization.

        Process:
        1. Generate all parameter combinations
        2. Evaluate each combination (optionally in parallel)
        3. Track best parameters throughout
        4. Apply early stopping if enabled
        5. Return best parameters found

        Args:
            objective: Function to maximize/minimize
            search_space: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        self._start_time = datetime.now()
        self._history: List[TrialResult] = []
        self._iteration_count = 0
        self._search_space = search_space

        if self.config.verbose >= 1:
            logger.info("Starting grid search optimization")

        # Generate all combinations
        combinations = self._generate_combinations(search_space)
        self._total_combinations = len(combinations)

        if self.config.verbose >= 1:
            logger.info(f"Generated {len(combinations)} parameter combinations")

        if not combinations:
            logger.warning("No valid parameter combinations generated")
            return self._create_empty_result()

        # Limit by max_iterations if needed
        if self.config.max_iterations < len(combinations):
            combinations = combinations[: self.config.max_iterations]
            if self.config.verbose >= 1:
                logger.info(
                    f"Limited to first {len(combinations)} combinations "
                    f"(max_iterations={self.config.max_iterations})"
                )

        # Evaluate combinations
        best_params, best_score = await self._evaluate_combinations(
            combinations=combinations,
            objective=objective,
        )

        self._best_params = best_params
        self._end_time = datetime.now()

        result = self._create_result(best_params, best_score)

        if self.config.verbose >= 1:
            logger.info(f"Grid search completed in {result.optimization_time:.2f}s")
            logger.info(f"Best score: {result.best_score:.6f}")
            logger.info(f"Evaluated {len(result.all_trials)} combinations")

        return result

    def _generate_combinations(self, search_space: SearchSpace) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations.

        Args:
            search_space: Search space definition

        Returns:
            List of parameter dictionaries
        """
        combinations = []

        # Get grid values for each parameter
        param_names = search_space.get_parameter_names()
        grid_values = []

        for name in param_names:
            defn = search_space.get_parameter_def(name)
            param_type = defn.get("type", ParameterType.CONTINUOUS)

            if param_type == ParameterType.CATEGORICAL:
                values = defn.get("choices", [])
            elif param_type == ParameterType.DISCRETE:
                values = defn.get("values", [])
            elif param_type == ParameterType.INTEGER:
                min_val = int(defn.get("min", 0))
                max_val = int(defn.get("max", 100))
                step = int(defn.get("step", 1))
                values = list(range(min_val, max_val + 1, step))
            elif param_type == ParameterType.CONTINUOUS:
                min_val_float = float(defn.get("min", 0.0))
                max_val_float = float(defn.get("max", 1.0))
                step_float = float(defn.get("step", (max_val_float - min_val_float) / 10))

                if step_float > 0:
                    num_steps = int((max_val_float - min_val_float) / step_float) + 1
                    values = [min_val_float + i * step_float for i in range(num_steps)]
                    # Ensure max is included
                    if values[-1] < max_val_float:
                        values.append(max_val_float)
                else:
                    # Default to 10 steps
                    values = [
                        min_val_float + (max_val_float - min_val_float) * i / 10 for i in range(11)
                    ]
            else:
                values = []

            grid_values.append(values)

        # Generate all combinations
        for values in product(*grid_values):
            params = dict(zip(param_names, values))
            combinations.append(params)

        return combinations

    async def _evaluate_combinations(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
    ) -> Tuple[Dict[str, Any], float]:
        """
        Evaluate all parameter combinations.

        Args:
            combinations: List of parameter dictionaries
            objective: Objective function

        Returns:
            Tuple of (best_params, best_score)
        """
        best_params: Dict[str, Any] = {}
        best_score = float("-inf") if self.config.maximize else float("inf")

        # Setup progress bar
        pbar = None
        try:
            from tqdm import tqdm

            if self.config.progress_bar and self.config.verbose >= 1:
                pbar = tqdm(total=len(combinations), desc="Grid Search", unit="eval")
        except ImportError:
            pass

        try:
            # Sequential evaluation
            if self.config.n_jobs == 1:
                for i, params in enumerate(combinations):
                    if self._check_timeout():
                        logger.warning("Timeout reached, stopping optimization")
                        break

                    result = await self._evaluate_single(params, objective, i)
                    self._history.append(result)

                    if result.is_success:
                        if self.config.maximize:
                            is_better = result.objective_value > best_score
                        else:
                            is_better = result.objective_value < best_score

                        if is_better:
                            best_score = result.objective_value
                            best_params = result.params.copy()

                            if self.config.verbose >= 2:
                                logger.info(f"New best: {best_score:.6f} at iteration {i}")

                    self._iteration_count += 1

                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix({"best": f"{best_score:.4f}"})

                    self._log_progress(i, best_score, best_params)

                    # Check early stopping
                    if self._should_stop_early():
                        if self.config.verbose >= 1:
                            logger.info("Early stopping triggered")
                        break

            # Parallel evaluation
            else:
                results = await self._evaluate_parallel_async(combinations, objective)

                for result in results:
                    self._history.append(result)

                    if result.is_success:
                        if self.config.maximize:
                            is_better = result.objective_value > best_score
                        else:
                            is_better = result.objective_value < best_score

                        if is_better:
                            best_score = result.objective_value
                            best_params = result.params.copy()

                    self._iteration_count += 1

                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix({"best": f"{best_score:.4f}"})

        finally:
            if pbar:
                pbar.close()

        return best_params, best_score

    async def _evaluate_single(
        self,
        params: Dict[str, Any],
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
        iteration: int,
    ) -> TrialResult:
        """
        Evaluate a single parameter combination.

        Args:
            params: Parameter dictionary
            objective: Objective function
            iteration: Iteration number

        Returns:
            TrialResult with evaluation results
        """
        trial_id = f"grid_{iteration}"
        start_time = datetime.now()

        try:
            if asyncio.iscoroutinefunction(objective):
                value = await objective(params)
            else:
                value = objective(params)

            end_time = datetime.now()

            return TrialResult(
                trial_id=trial_id,
                params=params.copy(),
                objective_value=float(value),
                status=OptimizationStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                iteration=iteration,
            )

        except Exception as e:
            end_time = datetime.now()
            logger.warning(f"Trial {iteration} failed: {e}")

            return TrialResult(
                trial_id=trial_id,
                params=params.copy(),
                objective_value=float("-inf") if self.config.maximize else float("inf"),
                status=OptimizationStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                iteration=iteration,
                error_message=str(e),
            )

    async def _evaluate_parallel_async(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
    ) -> List[TrialResult]:
        """
        Evaluate combinations in parallel asynchronously.

        Args:
            combinations: List of parameter dictionaries
            objective: Objective function

        Returns:
            List of trial results
        """
        # Create async tasks
        tasks = [
            self._evaluate_single(params, objective, i) for i, params in enumerate(combinations)
        ]

        # Execute in parallel batches
        batch_size = self.config.n_parallel_jobs
        results: List[TrialResult] = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]

            # Check timeout before each batch
            if self._check_timeout():
                logger.warning("Timeout reached during parallel evaluation")
                break

            # Execute batch
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    # Create failed trial result
                    results.append(
                        TrialResult(
                            trial_id=f"failed_{len(results)}",
                            params={},
                            objective_value=float("-inf") if self.config.maximize else float("inf"),
                            status=OptimizationStatus.FAILED,
                            error_message=str(result),
                        )
                    )
                else:
                    results.append(result)

        return results

    def _create_empty_result(self) -> OptimizationResult:
        """Create result for failed optimization."""
        return OptimizationResult(
            best_params={},
            best_score=float("-inf") if self.config.maximize else float("inf"),
            all_trials=[],
            optimization_time=0.0,
            n_iterations=0,
            converged=False,
            config=self.config,
        )


class GridSearchOptimizerCV(GridSearchOptimizer):
    """
    Grid Search with Cross-Validation.

    Extends GridSearchOptimizer to use cross-validation for more robust
    parameter selection.

    Example:
        ```python
        config = OptimizationConfig(max_iterations=100)

        optimizer = GridSearchOptimizerCV(
            config,
            cv_folds=5,
            cv_metric="mean",  # or "min", "median"
        )

        def cv_objective(params, fold_index):
            train_data, val_data = get_cv_split(fold_index)
            return evaluate_on_fold(params, train_data, val_data)

        result = await optimizer.optimize_cv(cv_objective, space)
        ```
    """

    def __init__(
        self,
        config: OptimizationConfig,
        cv_folds: int = 5,
        cv_metric: str = "mean",
    ) -> None:
        """
        Initialize grid search with CV.

        Args:
            config: Optimization configuration
            cv_folds: Number of CV folds
            cv_metric: How to aggregate CV scores ('mean', 'min', 'median')
        """
        super().__init__(config)
        self.cv_folds = cv_folds
        self.cv_metric = cv_metric

    async def optimize_cv(
        self,
        cv_objective: Callable[[Dict[str, Any], int], Union[float, "Awaitable[float]"]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """
        Run grid search with cross-validation.

        The cv_objective function should accept (params, fold_index) arguments.

        Args:
            cv_objective: CV objective function
            search_space: Parameter search space

        Returns:
            OptimizationResult with best parameters
        """
        self._start_time = datetime.now()
        self._history = []
        self._iteration_count = 0
        self._search_space = search_space

        combinations = self._generate_combinations(search_space)

        if self.config.verbose >= 1:
            logger.info(f"Starting grid search with {self.cv_folds}-fold CV")
            logger.info(f"Total evaluations: {len(combinations) * self.cv_folds}")

        best_params: Dict[str, Any] = {}
        best_cv_score = float("-inf") if self.config.maximize else float("inf")

        for i, params in enumerate(combinations):
            if self._check_timeout():
                break

            trial_id = f"cv_{i}"
            start_time = datetime.now()

            # Run CV
            cv_scores = []
            for fold in range(self.cv_folds):
                try:
                    if asyncio.iscoroutinefunction(cv_objective):
                        score = await cv_objective(params, fold)
                    else:
                        score = cv_objective(params, fold)
                    cv_scores.append(float(score))
                except Exception as e:
                    logger.warning(f"CV fold {fold} failed: {e}")
                    cv_scores.append(float("-inf") if self.config.maximize else float("inf"))

            # Aggregate CV scores
            if self.cv_metric == "mean":
                cv_score = float(np.mean(cv_scores))
            elif self.cv_metric == "min":
                cv_score = float(min(cv_scores))
            elif self.cv_metric == "median":
                sorted_scores = sorted(cv_scores)
                mid = len(sorted_scores) // 2
                cv_score = (
                    sorted_scores[mid]
                    if len(sorted_scores) % 2
                    else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
                )
            else:
                cv_score = float(np.mean(cv_scores))

            end_time = datetime.now()

            # Create trial result
            result = TrialResult(
                trial_id=trial_id,
                params=params.copy(),
                objective_value=cv_score,
                status=OptimizationStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                iteration=i,
                metrics={
                    "cv_scores": cv_scores,
                    "cv_mean": float(np.mean(cv_scores)),
                    "cv_std": float(np.std(cv_scores)) if len(cv_scores) > 1 else 0.0,
                },
            )

            self._history.append(result)

            # Update best
            if self.config.maximize:
                is_better = cv_score > best_cv_score
            else:
                is_better = cv_score < best_cv_score

            if is_better:
                best_cv_score = cv_score
                best_params = params.copy()

            self._iteration_count += 1

            if self._should_stop_early():
                break

        self._best_params = best_params
        self._end_time = datetime.now()

        return self._create_result(best_params, best_cv_score)

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """
        Run standard grid search (non-CV).

        For CV support, use optimize_cv() instead.
        """
        return await super().optimize(objective, search_space)
