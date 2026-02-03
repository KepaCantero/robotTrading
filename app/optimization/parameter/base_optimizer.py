"""
Base optimizer class and common utilities.

Provides the abstract base class for all optimizers and shared functionality.
"""

import logging
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import ParameterGrid
from .trial import TrialContext, TrialHistory, TrialResult, TrialStatus, create_trial_id

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """
    Configuration for optimization algorithms.

    Attributes:
        max_iterations: Maximum number of optimization iterations
        timeout_seconds: Maximum time to run optimization (None = no limit)
        n_jobs: Number of parallel jobs (1 = sequential, -1 = all CPUs)
        early_stopping: Enable early stopping on convergence
        early_stopping_patience: Iterations without improvement before stopping
        early_stopping_min_improvement: Minimum improvement to reset patience
        metric: Name of metric to optimize
        maximize: True to maximize, False to minimize
        minimize: Alias for maximize (for backwards compatibility)
        random_seed: Random seed for reproducibility
        verbose: Logging verbosity (0 = silent, 1 = normal, 2 = debug)
        progress_bar: Show progress bar during optimization
        checkpoint_interval: Save checkpoint every N iterations (0 = disabled)
        checkpoint_path: Path to save checkpoints
        validation_split: Fraction of data to use for validation (0-1)
        cv_folds: Number of cross-validation folds (1 = no CV)
    """

    max_iterations: int = 100
    timeout_seconds: Optional[int] = None
    n_jobs: int = 1
    early_stopping: bool = True
    early_stopping_patience: int = 10
    early_stopping_min_improvement: float = 0.001
    metric: str = "sharpe_ratio"
    maximize: bool = True
    minimize: bool = False
    random_seed: Optional[int] = None
    verbose: int = 1
    progress_bar: bool = True
    checkpoint_interval: int = 0
    checkpoint_path: Optional[str] = None
    validation_split: float = 0.0
    cv_folds: int = 1

    def __post_init__(self):
        """Validate and post-process configuration."""
        # Handle minimize alias
        if self.minimize:
            self.maximize = False

        # Validate ranges
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive or None")

        if self.early_stopping_patience <= 0:
            raise ValueError("early_stopping_patience must be positive")

        if not 0 <= self.validation_split < 1:
            raise ValueError("validation_split must be in [0, 1)")

        if self.cv_folds < 1:
            raise ValueError("cv_folds must be >= 1")

    @property
    def n_parallel_jobs(self) -> int:
        """Get actual number of parallel jobs."""
        import os

        if self.n_jobs == -1:
            return os.cpu_count() or 1
        return max(1, self.n_jobs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "n_jobs": self.n_jobs,
            "early_stopping": self.early_stopping,
            "early_stopping_patience": self.early_stopping_patience,
            "early_stopping_min_improvement": self.early_stopping_min_improvement,
            "metric": self.metric,
            "maximize": self.maximize,
            "random_seed": self.random_seed,
            "verbose": self.verbose,
            "progress_bar": self.progress_bar,
            "checkpoint_interval": self.checkpoint_interval,
            "checkpoint_path": self.checkpoint_path,
            "validation_split": self.validation_split,
            "cv_folds": self.cv_folds,
        }


@dataclass
class OptimizationResult:
    """
    Result of optimization run.

    Contains best parameters, all trial history, and metadata.
    """

    best_params: Dict[str, Any]
    best_score: float
    all_trials: List[TrialResult]
    optimization_time: float
    n_iterations: int
    converged: bool
    convergence_iteration: Optional[int] = None
    config: Optional[OptimizationConfig] = None
    best_metrics: Dict[str, float] = field(default_factory=dict)
    additional_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def best_trial(self) -> Optional[TrialResult]:
        """Get the best trial result."""
        if not self.all_trials:
            return None
        successful = [t for t in self.all_trials if t.is_success]
        if not successful:
            return None
        return max(successful, key=lambda t: t.objective_value)

    @property
    def success_rate(self) -> float:
        """Get fraction of successful trials."""
        if not self.all_trials:
            return 0.0
        return sum(1 for t in self.all_trials if t.is_success) / len(self.all_trials)

    @property
    def mean_score(self) -> float:
        """Get mean score across successful trials."""
        successful = [t for t in self.all_trials if t.is_success]
        if not successful:
            return 0.0
        return sum(t.objective_value for t in successful) / len(successful)

    @property
    def std_score(self) -> float:
        """Get standard deviation of scores."""
        import statistics

        successful = [t for t in self.all_trials if t.is_success]
        if len(successful) < 2:
            return 0.0
        return statistics.stdev(t.objective_value for t in successful)

    def get_score_ranking(self) -> List[Tuple[int, Dict[str, Any], float]]:
        """
        Get trials ranked by score.

        Returns:
            List of (rank, params, score) tuples
        """
        ranked = sorted(
            [(t.params, t.objective_value) for t in self.all_trials if t.is_success],
            key=lambda x: x[1],
            reverse=True,
        )
        return [(i + 1, params, score) for i, (params, score) in enumerate(ranked)]

    def get_top_n(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get top N parameter sets.

        Args:
            n: Number of top results to return

        Returns:
            List of parameter dictionaries
        """
        ranked = self.get_score_ranking()
        return [params for _, params, _ in ranked[:n]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "best_metrics": self.best_metrics,
            "optimization_time_seconds": self.optimization_time,
            "n_iterations": self.n_iterations,
            "converged": self.converged,
            "convergence_iteration": self.convergence_iteration,
            "success_rate": self.success_rate,
            "mean_score": self.mean_score,
            "std_score": self.std_score,
            "total_trials": len(self.all_trials),
            "successful_trials": sum(1 for t in self.all_trials if t.is_success),
            "config": self.config.to_dict() if self.config else None,
            "additional_info": self.additional_info,
        }

    def save(self, filepath: str) -> None:
        """Save result to file."""
        import json

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, filepath: str) -> "OptimizationResult":
        """Load result from file."""
        import json

        with open(filepath, "r") as f:
            data = json.load(f)

        # Reconstruct trial results
        trials = [TrialResult.from_dict(t) for t in data.get("trials", [])]

        return cls(
            best_params=data["best_params"],
            best_score=data["best_score"],
            all_trials=trials,
            optimization_time=data.get("optimization_time_seconds", 0.0),
            n_iterations=data.get("n_iterations", 0),
            converged=data.get("converged", False),
            convergence_iteration=data.get("convergence_iteration"),
            best_metrics=data.get("best_metrics", {}),
            additional_info=data.get("additional_info", {}),
        )


class BaseOptimizer(ABC):
    """
    Abstract base class for parameter optimizers.

    All optimizers should inherit from this class and implement
    the optimize() method.

    Example:
        ```python
        class MyOptimizer(BaseOptimizer):
            async def optimize(self, objective, param_grid):
                # Implementation here
                pass
        ```
    """

    def __init__(self, config: OptimizationConfig):
        """
        Initialize optimizer.

        Args:
            config: Optimization configuration
        """
        self.config = config
        self.history = TrialHistory()
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._best_score = float("-inf") if config.maximize else float("inf")
        self._iteration_count = 0

        # Set random seed if specified
        if config.random_seed is not None:
            import random

            random.seed(config.random_seed)

    @abstractmethod
    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        param_grid: ParameterGrid,
    ) -> OptimizationResult:
        """
        Run optimization.

        Args:
            objective: Function to optimize, takes params dict, returns score
            param_grid: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        pass

    def _evaluate_params(
        self,
        params: Dict[str, Any],
        objective: Callable[[Dict[str, Any]], float],
        iteration: int = 0,
    ) -> TrialResult:
        """
        Evaluate a single parameter set.

        Args:
            params: Parameter dictionary
            objective: Objective function
            iteration: Current iteration number

        Returns:
            TrialResult with evaluation results
        """
        trial_id = create_trial_id()

        with TrialContext(trial_id, params, iteration) as ctx:
            objective_value = objective(params)

        # Apply maximize/minimize
        if not self.config.maximize:
            objective_value = -objective_value

        result = ctx.create_result(objective_value)
        return result

    async def _evaluate_params_async(
        self,
        params: Dict[str, Any],
        objective: Callable[[Dict[str, Any]], float],
        iteration: int = 0,
    ) -> TrialResult:
        """
        Evaluate parameters asynchronously.

        Args:
            params: Parameter dictionary
            objective: Objective function
            iteration: Current iteration number

        Returns:
            TrialResult with evaluation results
        """
        trial_id = create_trial_id()

        try:
            start_time = datetime.now()

            # Check if objective is async
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(objective):
                objective_value = await objective(params)
            else:
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                objective_value = await loop.run_in_executor(None, objective, params)

            end_time = datetime.now()

            # Don't apply maximize/minimize here - store raw value
            # The optimizer will handle the comparison logic

            result = TrialResult(
                trial_id=trial_id,
                params=params,
                objective_value=objective_value,
                status=TrialStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                iteration=iteration,
            )

        except Exception as e:
            result = TrialResult(
                trial_id=trial_id,
                params=params,
                objective_value=float("-inf") if self.config.maximize else float("inf"),
                status=TrialStatus.FAILED,
                error_message=str(e),
                iteration=iteration,
            )

        return result

    def _evaluate_parallel(
        self,
        param_list: List[Dict[str, Any]],
        objective: Callable[[Dict[str, Any]], float],
    ) -> List[TrialResult]:
        """
        Evaluate multiple parameter sets in parallel.

        Args:
            param_list: List of parameter dictionaries
            objective: Objective function

        Returns:
            List of TrialResults
        """
        if self.config.n_jobs == 1 or len(param_list) == 1:
            # Sequential evaluation
            return [
                self._evaluate_params(params, objective, i) for i, params in enumerate(param_list)
            ]

        # Parallel evaluation
        results = []

        with ProcessPoolExecutor(max_workers=self.config.n_parallel_jobs) as executor:
            futures = {
                executor.submit(self._evaluate_params, params, objective, i): params
                for i, params in enumerate(param_list)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    params = futures[future]
                    results.append(
                        TrialResult(
                            trial_id=create_trial_id(),
                            params=params,
                            objective_value=float("-inf") if self.config.maximize else float("inf"),
                            status=TrialStatus.FAILED,
                            error_message=str(e),
                        )
                    )

        return results

    def _should_stop_early(self) -> bool:
        """
        Check if optimization should stop early.

        Returns:
            True if early stopping criteria met
        """
        if not self.config.early_stopping:
            return False

        converged = self.history.check_convergence(
            patience=self.config.early_stopping_patience,
            min_improvement=self.config.early_stopping_min_improvement,
        )

        return converged

    def _check_timeout(self) -> bool:
        """
        Check if timeout has been reached.

        Returns:
            True if timeout exceeded
        """
        if self.config.timeout_seconds is None:
            return False

        if self._start_time is None:
            return False

        elapsed = (datetime.now() - self._start_time).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def _log_progress(self, iteration: int, score: float, params: Dict[str, Any]) -> None:
        """Log optimization progress."""
        if self.config.verbose == 0:
            return

        if self.config.verbose >= 2:
            logger.debug(f"Iteration {iteration}: score={score:.6f}, params={params}")
        else:
            logger.info(f"Iteration {iteration}: score={score:.6f}")

    def _create_result(
        self,
        best_params: Dict[str, Any],
        best_score: float,
    ) -> OptimizationResult:
        """
        Create OptimizationResult from current state.

        Args:
            best_params: Best parameter dictionary
            best_score: Best score achieved

        Returns:
            OptimizationResult populated with current state
        """
        optimization_time = 0.0
        if self._start_time and self._end_time:
            optimization_time = (self._end_time - self._start_time).total_seconds()
        elif self._start_time:
            optimization_time = (datetime.now() - self._start_time).total_seconds()

        converged = self.history.check_convergence(
            patience=self.config.early_stopping_patience,
            min_improvement=self.config.early_stopping_min_improvement,
        )

        convergence_iteration = self.history.get_convergence_iteration(
            patience=self.config.early_stopping_patience,
            min_improvement=self.config.early_stopping_min_improvement,
        )

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_trials=self.history.trials,
            optimization_time=optimization_time,
            n_iterations=self._iteration_count,
            converged=converged,
            convergence_iteration=convergence_iteration,
            config=self.config,
        )

    def _save_checkpoint(self, iteration: int) -> None:
        """Save checkpoint if configured."""
        if (
            self.config.checkpoint_interval > 0
            and iteration % self.config.checkpoint_interval == 0
            and self.config.checkpoint_path
        ):
            import os

            os.makedirs(os.path.dirname(self.config.checkpoint_path), exist_ok=True)

            checkpoint_data = {
                "iteration": iteration,
                "history": self.history.to_dict(),
                "config": self.config.to_dict(),
            }

            import json

            with open(self.config.checkpoint_path, "w") as f:
                json.dump(checkpoint_data, f, indent=2, default=str)

            if self.config.verbose >= 1:
                logger.info(f"Saved checkpoint at iteration {iteration}")

    def _load_checkpoint(self) -> Optional[int]:
        """
        Load checkpoint if available.

        Returns:
            Iteration number to resume from, or None
        """
        if not self.config.checkpoint_path:
            return None

        import os

        if not os.path.exists(self.config.checkpoint_path):
            return None

        try:
            import json

            with open(self.config.checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)

            self.history = TrialHistory.load(
                self.config.checkpoint_path.replace(".json", "_history.json")
            )

            if self.config.verbose >= 1:
                logger.info(f"Loaded checkpoint from iteration {checkpoint_data['iteration']}")

            return checkpoint_data["iteration"]

        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return None
