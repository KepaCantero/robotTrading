"""
Grid Search Optimizer - FASE 6.1

Implements exhaustive grid search over parameter space with:
- Parallel execution support
- Early stopping on poor performance
- Progress tracking
"""

# mypy: ignore-errors
import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Tuple

from tqdm import tqdm

from .base_optimizer import BaseOptimizer, OptimizationConfig, OptimizationResult
from .models import ParameterGrid
from .trial import TrialHistory, TrialResult, TrialStatus, create_trial_id

logger = logging.getLogger(__name__)


class GridSearchOptimizer(BaseOptimizer):
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
        from app.optimization.parameter import GridSearchOptimizer, ParameterGrid, ParameterRange

        param_grid = ParameterGrid(parameters=[
            ParameterRange(name="lookback", min_value=5, max_value=20, step=5),
            ParameterRange(name="threshold", min_value=0.1, max_value=0.5, step=0.1),
        ])

        config = OptimizationConfig(
            max_iterations=1000,
            n_jobs=4,
            early_stopping=True,
            early_stopping_patience=20,
        )

        optimizer = GridSearchOptimizer(config)

        def objective(params):
            # Evaluate strategy with these parameters
            return backtest_strategy(params)["sharpe_ratio"]

        result = await optimizer.optimize(objective, param_grid)
        logger.debug(f"Best params: {result.best_params}")
        logger.debug(f"Best score: {result.best_score}")
        ```
    """

    def __init__(self, config: OptimizationConfig):
        """
        Initialize grid search optimizer.

        Args:
            config: Optimization configuration
        """
        super().__init__(config)
        self._total_combinations: Optional[int] = None
        self._evaluated_combinations: int = 0

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        param_grid: ParameterGrid,
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
            param_grid: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        self._start_time = datetime.now()
        self.history = TrialHistory()
        self._iteration_count = 0

        if self.config.verbose >= 1:
            logger.info("Starting grid search optimization")
            logger.info(f"Parameter grid size: {param_grid.size()} combinations")

        # Generate all combinations
        combinations = self._generate_combinations(param_grid)
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

        self._end_time = datetime.now()
        self.history.finish()

        result = self._create_result(best_params, best_score)

        if self.config.verbose >= 1:
            logger.info(f"Grid search completed in {result.optimization_time:.2f}s")
            logger.info(f"Best score: {result.best_score:.6f}")
            logger.info(f"Evaluated {len(result.all_trials)} combinations")

        return result

    def _generate_combinations(self, param_grid: ParameterGrid) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations.

        Args:
            param_grid: Parameter grid defining search space

        Returns:
            List of parameter dictionaries
        """
        # Get grid values for each parameter
        param_names = [p.name for p in param_grid.parameters]
        grid_values = [p.get_grid_values() for p in param_grid.parameters]

        # Generate all combinations
        combinations = []
        for values in product(*grid_values):
            params = dict(zip(param_names, values))
            # Apply constraints
            if param_grid._check_constraints(params):
                combinations.append(params)

        return combinations

    async def _evaluate_combinations(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], float],
    ) -> Tuple[Dict[str, Any], float]:
        """
        Evaluate all parameter combinations.

        Args:
            combinations: List of parameter dictionaries
            objective: Objective function

        Returns:
            Tuple of (best_params, best_score)
        """
        best_params = {}
        best_score = float("-inf") if self.config.maximize else float("inf")

        # Setup progress bar
        pbar = None
        if self.config.progress_bar and self.config.verbose >= 1:
            pbar = tqdm(
                total=len(combinations),
                desc="Grid Search",
                unit="eval",
            )

        try:
            # Sequential evaluation
            if self.config.n_jobs == 1:
                for i, params in enumerate(combinations):
                    if self._check_timeout():
                        logger.warning("Timeout reached, stopping optimization")
                        break

                    result = await self._evaluate_params_async(params, objective, i)
                    self.history.add_trial(result)

                    if result.is_success:
                        if self.config.maximize:
                            is_better = result.objective_value > best_score
                        else:
                            is_better = result.objective_value < best_score

                        if is_better:
                            best_score = result.objective_value
                            best_params = result.params

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

                    # Save checkpoint
                    if self.config.checkpoint_interval > 0:
                        self._save_checkpoint(i)

            # Parallel evaluation
            else:
                results = await self._evaluate_parallel_async(combinations, objective)

                for result in results:
                    self.history.add_trial(result)

                    if result.is_success:
                        if self.config.maximize:
                            is_better = result.objective_value > best_score
                        else:
                            is_better = result.objective_value < best_score

                        if is_better:
                            best_score = result.objective_value
                            best_params = result.params

                    self._iteration_count += 1

                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix({"best": f"{best_score:.4f}"})

        finally:
            if pbar:
                pbar.close()

        return best_params, best_score

    async def _evaluate_parallel_async(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], float],
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
            self._evaluate_params_async(params, objective, i)
            for i, params in enumerate(combinations)
        ]

        # Execute in parallel batches
        batch_size = self.config.n_parallel_jobs
        results = []

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
                            trial_id=create_trial_id(),
                            params={},
                            objective_value=float("-inf") if self.config.maximize else float("inf"),
                            status=TrialStatus.FAILED,
                            error_message=str(result),
                        )
                    )
                else:
                    results.append(result)

        return results

    def _evaluate_sequential(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], float],
    ) -> Tuple[Dict[str, Any], float, List[TrialResult]]:
        """
        Evaluate combinations sequentially (synchronous version).

        Args:
            combinations: List of parameter dictionaries
            objective: Objective function

        Returns:
            Tuple of (best_params, best_score, results)
        """
        best_params = {}
        best_score = float("-inf") if self.config.maximize else float("inf")
        results = []

        pbar = None
        if self.config.progress_bar and self.config.verbose >= 1:
            pbar = tqdm(total=len(combinations), desc="Grid Search")

        try:
            for i, params in enumerate(combinations):
                result = self._evaluate_params(params, objective, i)
                results.append(result)

                if result.is_success:
                    if self.config.maximize:
                        is_better = result.objective_value > best_score
                    else:
                        is_better = result.objective_value < best_score

                    if is_better:
                        best_score = result.objective_value
                        best_params = result.params

                if pbar:
                    pbar.update(1)

        finally:
            if pbar:
                pbar.close()

        return best_params, best_score, results

    def _evaluate_parallel(
        self,
        combinations: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], float],
    ) -> Tuple[Dict[str, Any], float, List[TrialResult]]:
        """
        Evaluate combinations in parallel (synchronous version).

        Args:
            combinations: List of parameter dictionaries
            objective: Objective function

        Returns:
            Tuple of (best_params, best_score, results)
        """
        best_params = {}
        best_score = float("-inf") if self.config.maximize else float("inf")
        results = []

        pbar = None
        if self.config.progress_bar and self.config.verbose >= 1:
            pbar = tqdm(total=len(combinations), desc="Grid Search (Parallel)")

        try:
            with ProcessPoolExecutor(max_workers=self.config.n_parallel_jobs) as executor:
                futures = {
                    executor.submit(objective, params): (i, params)
                    for i, params in enumerate(combinations)
                }

                for future in as_completed(futures):
                    i, params = futures[future]

                    try:
                        score = future.result()

                        result = TrialResult(
                            trial_id=create_trial_id(),
                            params=params,
                            objective_value=score,
                            status=TrialStatus.COMPLETED,
                            iteration=i,
                        )

                        if self.config.maximize:
                            is_better = score > best_score
                        else:
                            is_better = score < best_score

                        if is_better:
                            best_score = score
                            best_params = params

                    except Exception as e:
                        result = TrialResult(
                            trial_id=create_trial_id(),
                            params=params,
                            objective_value=float("-inf") if self.config.maximize else float("inf"),
                            status=TrialStatus.FAILED,
                            error_message=str(e),
                            iteration=i,
                        )

                    results.append(result)

                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix({"best": f"{best_score:.4f}"})

        finally:
            if pbar:
                pbar.close()

        return best_params, best_score, results

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
    """

    def __init__(
        self,
        config: OptimizationConfig,
        cv_folds: int = 5,
        cv_metric: str = "mean",
    ):
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

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any], int], float],
        param_grid: ParameterGrid,
    ) -> OptimizationResult:
        """
        Run grid search with cross-validation.

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

        combinations = self._generate_combinations(param_grid)

        if self.config.verbose >= 1:
            logger.info(f"Starting grid search with {self.cv_folds}-fold CV")
            logger.info(f"Total evaluations: {len(combinations) * self.cv_folds}")

        best_params = {}
        best_cv_score = float("-inf") if self.config.maximize else float("inf")

        for i, params in enumerate(combinations):
            if self._check_timeout():
                break

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
            if self.cv_metric == "mean":
                cv_score = sum(cv_scores) / len(cv_scores)
            elif self.cv_metric == "min":
                cv_score = min(cv_scores)
            elif self.cv_metric == "median":
                sorted_scores = sorted(cv_scores)
                mid = len(sorted_scores) // 2
                cv_score = (
                    sorted_scores[mid]
                    if len(sorted_scores) % 2
                    else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
                )
            else:
                cv_score = sum(cv_scores) / len(cv_scores)

            # Create trial result
            result = TrialResult(
                trial_id=create_trial_id(),
                params=params,
                objective_value=cv_score,
                status=TrialStatus.COMPLETED,
                iteration=i,
                metrics={
                    "cv_scores": cv_scores,
                    "cv_mean": sum(cv_scores) / len(cv_scores),
                    "cv_std": self._std(cv_scores) if len(cv_scores) > 1 else 0.0,
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

            self._iteration_count += 1

            if self._should_stop_early():
                break

        self._end_time = datetime.now()
        return self._create_result(best_params, best_cv_score)

    def _std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        import statistics

        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)
