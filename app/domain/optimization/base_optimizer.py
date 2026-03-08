"""
Base Optimizer - Abstract base class for all optimizers.

This module provides the unified interface for all optimization algorithms
in the system, including parameter optimizers and portfolio optimizers.

Hierarchy:
    BaseOptimizer (abstract)
    ├── ParameterOptimizer (abstract) - for strategy parameter optimization
    │   ├── BayesianOptimizer
    │   ├── GridSearchOptimizer
    │   └── RandomSearchOptimizer
    └── PortfolioOptimizer (abstract) - for portfolio weight optimization
        └── MeanVarianceOptimizer

Usage:
    from app.domain.optimization.base_optimizer import (
        BaseOptimizer,
        OptimizationConfig,
        OptimizationResult,
    )
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class OptimizerType(str, Enum):
    """Types of optimizers available."""

    # Parameter optimizers
    BAYESIAN = "bayesian"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    MULTI_STRATEGY = "multi_strategy"

    # Portfolio optimizers
    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    BLACK_LITTERMAN = "black_litterman"


class OptimizationStatus(str, Enum):
    """Status of an optimization run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CONVERGED = "converged"


@dataclass
class OptimizationConfig:
    """
    Configuration for optimization algorithms.

    This is the unified configuration that works for both parameter
    and portfolio optimization.

    Attributes:
        max_iterations: Maximum number of optimization iterations
        timeout_seconds: Maximum time to run optimization (None = no limit)
        n_jobs: Number of parallel jobs (1 = sequential, -1 = all CPUs)
        early_stopping: Enable early stopping on convergence
        early_stopping_patience: Iterations without improvement before stopping
        early_stopping_min_improvement: Minimum improvement to reset patience
        metric: Name of metric to optimize
        maximize: True to maximize, False to minimize
        random_seed: Random seed for reproducibility
        verbose: Logging verbosity (0 = silent, 1 = normal, 2 = debug)
        progress_bar: Show progress bar during optimization
        checkpoint_interval: Save checkpoint every N iterations (0 = disabled)
        checkpoint_path: Path to save checkpoints
    """

    max_iterations: int = 100
    timeout_seconds: Optional[int] = None
    n_jobs: int = 1
    early_stopping: bool = True
    early_stopping_patience: int = 10
    early_stopping_min_improvement: float = 0.001
    metric: str = "sharpe_ratio"
    maximize: bool = True
    random_seed: Optional[int] = None
    verbose: int = 1
    progress_bar: bool = True
    checkpoint_interval: int = 0
    checkpoint_path: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive or None")

        if self.early_stopping_patience <= 0:
            raise ValueError("early_stopping_patience must be positive")

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
        }


@dataclass
class TrialResult:
    """
    Result of a single optimization trial.

    Attributes:
        trial_id: Unique identifier for this trial
        params: Parameters used in this trial
        objective_value: Value of the objective function
        status: Status of the trial
        start_time: When the trial started
        end_time: When the trial ended
        iteration: Iteration number
        error_message: Error message if trial failed
        metrics: Additional metrics from the trial
    """

    trial_id: str
    params: Dict[str, Any]
    objective_value: float
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    iteration: int = 0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if trial was successful."""
        return self.status == OptimizationStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get trial duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "trial_id": self.trial_id,
            "params": self.params,
            "objective_value": self.objective_value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "iteration": self.iteration,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


@dataclass
class OptimizationResult:
    """
    Result of an optimization run.

    Contains best parameters/weights, all trial history, and metadata.
    Works for both parameter optimization and portfolio optimization.

    Attributes:
        best_params: Best parameters found (for parameter optimization)
        best_weights: Optimal portfolio weights (for portfolio optimization)
        best_score: Best objective value achieved
        all_trials: History of all trials
        optimization_time: Total optimization time in seconds
        n_iterations: Number of iterations performed
        converged: Whether optimization converged
        status: Final status of optimization
        config: Configuration used for optimization
        additional_info: Additional metadata
    """

    best_params: Dict[str, Any] = field(default_factory=dict)
    best_weights: Optional[NDArray[np.float64]] = None
    best_score: float = 0.0
    all_trials: List[TrialResult] = field(default_factory=list)
    optimization_time: float = 0.0
    n_iterations: int = 0
    converged: bool = False
    convergence_iteration: Optional[int] = None
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    config: Optional[OptimizationConfig] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Get fraction of successful trials."""
        if not self.all_trials:
            return 0.0
        return np.mean([1.0 for t in self.all_trials if t.is_success])

    @property
    def mean_score(self) -> float:
        """Get mean score across successful trials."""
        successful = [t for t in self.all_trials if t.is_success]
        if not successful:
            return 0.0
        return float(np.mean([t.objective_value for t in successful]))

    @property
    def std_score(self) -> float:
        """Get standard deviation of scores."""
        successful = [t for t in self.all_trials if t.is_success]
        if len(successful) < 2:
            return 0.0
        return float(np.std([t.objective_value for t in successful]))

    def get_top_n(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get top N parameter sets.

        Args:
            n: Number of top results to return

        Returns:
            List of parameter dictionaries
        """
        successful = [t for t in self.all_trials if t.is_success]
        sorted_trials = sorted(
            successful,
            key=lambda x: x.objective_value,
            reverse=self.config.maximize if self.config else True,
        )
        return [t.params for t in sorted_trials[:n]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "best_params": self.best_params,
            "best_weights": self.best_weights.tolist() if self.best_weights is not None else None,
            "best_score": self.best_score,
            "optimization_time_seconds": self.optimization_time,
            "n_iterations": self.n_iterations,
            "converged": self.converged,
            "convergence_iteration": self.convergence_iteration,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "mean_score": self.mean_score,
            "std_score": self.std_score,
            "total_trials": len(self.all_trials),
            "successful_trials": sum(1 for t in self.all_trials if t.is_success),
            "config": self.config.to_dict() if self.config else None,
            "additional_info": self.additional_info,
        }


T = TypeVar('T')


class BaseOptimizer(ABC, Generic[T]):
    """
    Abstract base class for all optimizers.

    This provides the unified interface that all optimizers must implement.
    Generic type T represents the search space type (ParameterGrid for parameter
    optimization, or returns/covariance data for portfolio optimization).

    Subclasses must implement:
        - optimize(): Run the optimization
        - get_best_params(): Get the best parameters found
        - get_history(): Get optimization history

    Example:
        ```python
        class MyOptimizer(BaseOptimizer[MySearchSpace]):
            async def optimize(self, objective, search_space):
                # Implementation
                pass

            def get_best_params(self) -> Dict[str, Any]:
                return self._best_params

            def get_history(self) -> List[TrialResult]:
                return self._history
        ```
    """

    def __init__(self, config: OptimizationConfig) -> None:
        """
        Initialize optimizer.

        Args:
            config: Optimization configuration
        """
        self.config = config
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._best_score = float("-inf") if config.maximize else float("inf")
        self._iteration_count = 0
        self._history: List[TrialResult] = []

        # Set random seed if specified
        if config.random_seed is not None:
            import random

            random.seed(config.random_seed)
            np.random.seed(config.random_seed)

    @abstractmethod
    async def optimize(
        self,
        objective: Any,
        search_space: T,
    ) -> OptimizationResult:
        """
        Run optimization.

        Args:
            objective: Objective function or data to optimize
            search_space: Search space definition

        Returns:
            OptimizationResult with best parameters and all trials
        """

    @abstractmethod
    def get_best_params(self) -> Dict[str, Any]:
        """
        Get the best parameters found.

        Returns:
            Dictionary of best parameter values
        """

    @abstractmethod
    def get_history(self) -> List[TrialResult]:
        """
        Get optimization history.

        Returns:
            List of all trial results
        """

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

    def _should_stop_early(self) -> bool:
        """
        Check if optimization should stop early.

        Returns:
            True if early stopping criteria met
        """
        if not self.config.early_stopping:
            return False

        if len(self._history) < self.config.early_stopping_patience:
            return False

        # Check if no improvement in last N trials
        recent_trials = self._history[-self.config.early_stopping_patience :]

        if self.config.maximize:
            best_recent = max(t.objective_value for t in recent_trials if t.is_success)
            improvement = best_recent - self._best_score
        else:
            best_recent = min(t.objective_value for t in recent_trials if t.is_success)
            improvement = self._best_score - best_recent

        return improvement < self.config.early_stopping_min_improvement

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
        best_weights: Optional[NDArray[np.float64]] = None,
    ) -> OptimizationResult:
        """
        Create OptimizationResult from current state.

        Args:
            best_params: Best parameter dictionary
            best_score: Best score achieved
            best_weights: Optimal weights (for portfolio optimization)

        Returns:
            OptimizationResult populated with current state
        """
        optimization_time = 0.0
        if self._start_time and self._end_time:
            optimization_time = (self._end_time - self._start_time).total_seconds()
        elif self._start_time:
            optimization_time = (datetime.now() - self._start_time).total_seconds()

        return OptimizationResult(
            best_params=best_params,
            best_weights=best_weights,
            best_score=best_score,
            all_trials=self._history,
            optimization_time=optimization_time,
            n_iterations=self._iteration_count,
            converged=self._should_stop_early(),
            convergence_iteration=self._iteration_count if self._should_stop_early() else None,
            config=self.config,
        )

    @classmethod
    @abstractmethod
    def get_optimizer_type(cls) -> OptimizerType:
        """
        Get the type of this optimizer.

        Returns:
            OptimizerType enum value
        """
