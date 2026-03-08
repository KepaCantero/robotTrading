"""
Bayesian Optimizer - Consolidated Implementation.

This module provides a unified Bayesian optimization implementation that combines
the best features from:
- app/domain/optimization/parameter/bayesian_optimizer.py (parameter optimization)
- app/backtesting/profile_batch/bayesian_optimizer.py (profile-based optimization)

Features:
- TPE (Tree-structured Parzen Estimator) sampler via Optuna
- Multiple pruner options (median, hyperband, successive halving)
- Multi-objective optimization support
- Efficient for expensive evaluations
- Trial pruning for efficiency
- Automatic hyperparameter suggestion based on type

Usage:
    ```python
    from app.domain.optimization.bayesian_optimizer import BayesianOptimizer
    from app.domain.optimization.base_optimizer import OptimizationConfig

    config = OptimizationConfig(
        max_iterations=100,
        metric="sharpe_ratio",
        maximize=True,
    )

    optimizer = BayesianOptimizer(
        config,
        n_trials=100,
        pruner="median",
        sampler="tpe",
    )

    result = await optimizer.optimize(objective_func, param_grid)
    ```
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


from .base_optimizer import (
    BaseOptimizer,
    OptimizationConfig,
    OptimizationResult,
    OptimizationStatus,
    OptimizerType,
    TrialResult,
)

logger = logging.getLogger(__name__)

# Try to import Optuna (optional dependency)
try:
    import optuna
    from optuna.pruners import HyperbandPruner, MedianPruner, SuccessiveHalvingPruner
    from optuna.samplers import CmaEsSampler, RandomSampler, TPESampler

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None  # type: ignore

    logger.warning(
        "Optuna not installed. Bayesian optimizer will fall back to random search. "
        "Install with: pip install optuna"
    )


class ParameterType:
    """Parameter type constants for search space definition."""

    CONTINUOUS = "continuous"
    INTEGER = "integer"
    CATEGORICAL = "categorical"
    DISCRETE = "discrete"


class SearchSpace:
    """
    Unified search space definition.

    Supports both the ParameterGrid style and the profile-based style.
    """

    def __init__(self) -> None:
        self._parameters: Dict[str, Dict[str, Any]] = {}

    def add_continuous(
        self,
        name: str,
        min_value: float,
        max_value: float,
        log: bool = False,
    ) -> "SearchSpace":
        """Add a continuous parameter."""
        self._parameters[name] = {
            "type": ParameterType.CONTINUOUS,
            "min": min_value,
            "max": max_value,
            "log": log,
        }
        return self

    def add_integer(
        self,
        name: str,
        min_value: int,
        max_value: int,
        step: int = 1,
    ) -> "SearchSpace":
        """Add an integer parameter."""
        self._parameters[name] = {
            "type": ParameterType.INTEGER,
            "min": min_value,
            "max": max_value,
            "step": step,
        }
        return self

    def add_categorical(
        self,
        name: str,
        choices: List[Any],
    ) -> "SearchSpace":
        """Add a categorical parameter."""
        self._parameters[name] = {
            "type": ParameterType.CATEGORICAL,
            "choices": choices,
        }
        return self

    def add_discrete(
        self,
        name: str,
        values: List[Any],
    ) -> "SearchSpace":
        """Add a discrete parameter (same as categorical for Optuna)."""
        self._parameters[name] = {
            "type": ParameterType.DISCRETE,
            "values": values,
        }
        return self

    def get_parameter_names(self) -> List[str]:
        """Get all parameter names."""
        return list(self._parameters.keys())

    def get_parameter_def(self, name: str) -> Dict[str, Any]:
        """Get parameter definition."""
        return self._parameters.get(name, {})

    @classmethod
    def from_dict(cls, params_dict: Dict[str, Dict[str, Any]]) -> "SearchSpace":
        """Create SearchSpace from dictionary."""
        space = cls()
        for name, defn in params_dict.items():
            space._parameters[name] = defn
        return space

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to dictionary."""
        return self._parameters.copy()


class BayesianOptimizer(BaseOptimizer[SearchSpace]):
    """
    Bayesian optimization using Optuna.

    Uses TPE (Tree-structured Parzen Estimator) for efficient hyperparameter
    optimization. More efficient than grid/random search for expensive evaluations.

    Features:
    - TPE sampler for efficient search
    - Multiple pruner options for early stopping of bad trials
    - Multi-objective optimization support
    - Trial pruning for efficiency
    - Automatic hyperparameter suggestion based on type

    Requires optuna to be installed. Falls back to random search if not available.

    Example:
        ```python
        config = OptimizationConfig(max_iterations=100, maximize=True)

        optimizer = BayesianOptimizer(config, n_trials=100)

        # Define search space
        space = SearchSpace()
        space.add_integer("lookback", 5, 50, step=5)
        space.add_continuous("threshold", 0.01, 0.1, log=True)
        space.add_categorical("method", ["ema", "sma"])

        # Define objective
        def objective(params):
            return backtest_strategy(params)["sharpe_ratio"]

        result = await optimizer.optimize(objective, space)
        print(f"Best params: {result.best_params}")
        ```
    """

    def __init__(
        self,
        config: OptimizationConfig,
        n_trials: Optional[int] = None,
        pruner: Optional[str] = "median",
        sampler: Optional[str] = "tpe",
        multivariate: bool = True,
        n_startup_trials: int = 10,
    ) -> None:
        """
        Initialize Bayesian optimizer.

        Args:
            config: Optimization configuration
            n_trials: Number of optimization trials (default: max_iterations from config)
            pruner: Pruner type ('median', 'successive_halving', 'hyperband', None)
            sampler: Sampler type ('tpe', 'cmaes', 'random')
            multivariate: Whether to use multivariate TPE
            n_startup_trials: Number of random trials before TPE
        """
        super().__init__(config)

        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, will use random search fallback")

        self.n_trials = n_trials or config.max_iterations
        self.pruner_type = pruner
        self.sampler_type = sampler
        self.multivariate = multivariate
        self.n_startup_trials = n_startup_trials

        self._study: Optional[Any] = None
        self._search_space: Optional[SearchSpace] = None

    @classmethod
    def get_optimizer_type(cls) -> OptimizerType:
        """Get the type of this optimizer."""
        return OptimizerType.BAYESIAN

    def get_best_params(self) -> Dict[str, Any]:
        """Get the best parameters found."""
        if self._study is not None and hasattr(self._study, 'best_params'):
            return self._study.best_params
        return {}

    def get_history(self) -> List[TrialResult]:
        """Get optimization history."""
        return self._history

    async def optimize(
        self,
        objective: Callable[[Dict[str, Any]], Union[float, Awaitable[float]]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """
        Run Bayesian optimization with Optuna.

        Process:
        1. Create Optuna study with TPE sampler
        2. Define search space from search_space parameter
        3. Run optimization trials
        4. Prune unpromising trials
        5. Return best parameters

        Args:
            objective: Function to maximize/minimize
            search_space: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        # Fallback to random search if Optuna not available
        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, falling back to random search")
            return await self._random_search_fallback(objective, search_space)

        self._start_time = datetime.now()
        self._history = []
        self._iteration_count = 0
        self._search_space = search_space

        if self.config.verbose >= 1:
            logger.info("Starting Bayesian optimization with Optuna")
            logger.info(f"Number of trials: {self.n_trials}")

        # Create Optuna study
        self._study = self._create_study()

        # Define objective wrapper for Optuna
        def optuna_objective(trial: Any) -> float:
            return self._run_trial(trial, objective)

        # Run optimization
        try:
            from tqdm import tqdm

            pbar = None
            if self.config.progress_bar and self.config.verbose >= 1:
                pbar = tqdm(total=self.n_trials, desc="Bayesian Optimization")

            def callback(study: Any, trial: Any) -> None:
                self._iteration_count = len(study.trials)

                if pbar:
                    best_value = study.best_value
                    pbar.update(1)
                    pbar.set_postfix({"best": f"{best_value:.4f}"})

                # Check timeout
                if self._check_timeout():
                    study.stop()

            # Run optimization
            self._study.optimize(
                optuna_objective,
                n_trials=self.n_trials,
                callbacks=[callback] if self.config.progress_bar else None,
                show_progress_bar=False,
            )

            if pbar:
                pbar.close()

        except Exception as e:
            logger.error(f"Optuna optimization failed: {e}")

        # Extract results
        self._extract_results_from_study(self._study)

        self._end_time = datetime.now()

        best_params = dict(self._study.best_params)
        best_score = self._study.best_value

        # Apply maximize/minimize correction
        if not self.config.maximize:
            best_score = -best_score

        result = self._create_result(best_params, best_score)

        if self.config.verbose >= 1:
            logger.info(f"Bayesian optimization completed in {result.optimization_time:.2f}s")
            logger.info(f"Best score: {result.best_score:.6f}")
            logger.info(f"Evaluated {len(result.all_trials)} trials")

        return result

    def _create_study(self) -> Any:
        """Create Optuna study with appropriate sampler and pruner."""
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna not available")

        # Create sampler
        sampler = self._create_sampler()

        # Create pruner
        pruner = self._create_pruner()

        # Create study
        study = optuna.create_study(
            direction="maximize" if self.config.maximize else "minimize",
            sampler=sampler,
            pruner=pruner,
        )

        return study

    def _create_sampler(self) -> Any:
        """Create Optuna sampler."""
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna not available")

        if self.sampler_type == "tpe":
            return TPESampler(
                seed=self.config.random_seed,
                multivariate=self.multivariate,
                n_startup_trials=self.n_startup_trials,
            )
        elif self.sampler_type == "cmaes":
            return CmaEsSampler(seed=self.config.random_seed)
        elif self.sampler_type == "random":
            return RandomSampler(seed=self.config.random_seed)
        else:
            return TPESampler(
                seed=self.config.random_seed,
                multivariate=self.multivariate,
            )

    def _create_pruner(self) -> Optional[Any]:
        """Create Optuna pruner."""
        if not OPTUNA_AVAILABLE:
            return None

        if self.pruner_type == "median":
            return MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        elif self.pruner_type == "successive_halving":
            return SuccessiveHalvingPruner()
        elif self.pruner_type == "hyperband":
            return HyperbandPruner()
        elif self.pruner_type is None:
            return None
        else:
            return MedianPruner(n_startup_trials=5, n_warmup_steps=10)

    def _run_trial(
        self,
        trial: Any,
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
    ) -> float:
        """
        Run a single Optuna trial.

        Args:
            trial: Optuna trial object
            objective: User's objective function

        Returns:
            Objective value
        """
        trial_id = f"optuna_{trial.number}"
        start_time = datetime.now()

        try:
            # Sample parameters from search space
            params = self._sample_params(trial)

            # Evaluate objective
            if asyncio.iscoroutinefunction(objective):
                # Run async function in event loop
                loop = asyncio.get_event_loop()
                value = loop.run_until_complete(objective(params))
            else:
                value = objective(params)

            # Apply maximize/minimize
            if not self.config.maximize:
                value = -value

            end_time = datetime.now()

            # Record trial
            result = TrialResult(
                trial_id=trial_id,
                params=params,
                objective_value=value if self.config.maximize else -value,
                status=OptimizationStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                iteration=trial.number,
            )
            self._history.append(result)

            return value

        except Exception as e:
            logger.warning(f"Trial {trial.number} failed: {e}")
            end_time = datetime.now()

            # Record failed trial
            result = TrialResult(
                trial_id=trial_id,
                params={},
                objective_value=float("-inf") if self.config.maximize else float("inf"),
                status=OptimizationStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                iteration=trial.number,
                error_message=str(e),
            )
            self._history.append(result)

            return float("-inf") if self.config.maximize else float("inf")

    def _sample_params(self, trial: Any) -> Dict[str, Any]:
        """
        Sample parameters from search space using Optuna trial.

        Args:
            trial: Optuna trial object

        Returns:
            Sampled parameter dictionary
        """
        if self._search_space is None:
            return {}

        params = {}
        for name, defn in self._search_space.to_dict().items():
            param_type = defn.get("type", ParameterType.CONTINUOUS)

            if param_type == ParameterType.CATEGORICAL:
                params[name] = trial.suggest_categorical(name, defn["choices"])

            elif param_type == ParameterType.DISCRETE:
                params[name] = trial.suggest_categorical(name, defn["values"])

            elif param_type == ParameterType.INTEGER:
                min_val = int(defn["min"])
                max_val = int(defn["max"])
                step = int(defn.get("step", 1))

                if step == 1:
                    params[name] = trial.suggest_int(name, min_val, max_val)
                else:
                    values = list(range(min_val, max_val + 1, step))
                    params[name] = trial.suggest_categorical(name, values)

            elif param_type == ParameterType.CONTINUOUS:
                min_val = float(defn["min"])
                max_val = float(defn["max"])
                log = defn.get("log", False)

                params[name] = trial.suggest_float(name, min_val, max_val, log=log)

        return params

    def _extract_results_from_study(self, study: Any) -> None:
        """
        Extract trial results from Optuna study.

        Args:
            study: Completed Optuna study
        """
        if not OPTUNA_AVAILABLE:
            return

        self._iteration_count = len(study.trials)

        # Clear and rebuild history from study
        self._history = []

        for trial in study.trials:
            params = dict(trial.params)
            value = trial.value

            # Determine status
            if trial.state == optuna.trial.TrialState.COMPLETE:
                status = OptimizationStatus.COMPLETED
            elif trial.state == optuna.trial.TrialState.PRUNED:
                status = OptimizationStatus.FAILED  # Use FAILED for PRUNED
            elif trial.state == optuna.trial.TrialState.FAIL:
                status = OptimizationStatus.FAILED
            else:
                status = OptimizationStatus.FAILED

            # Create trial result
            result = TrialResult(
                trial_id=f"optuna_{trial.number}",
                params=params,
                objective_value=value if value is not None else 0.0,
                status=status,
                start_time=datetime.fromtimestamp(trial.datetime_start.timestamp())
                if trial.datetime_start
                else None,
                end_time=datetime.fromtimestamp(trial.datetime_complete.timestamp())
                if trial.datetime_complete
                else None,
                iteration=trial.number,
                additional_info={
                    "optuna_trial_number": trial.number,
                    "optuna_state": trial.state.name,
                },
            )

            self._history.append(result)

    async def _random_search_fallback(
        self,
        objective: Callable[[Dict[str, Any]], Union[float, "Awaitable[float]"]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """Fallback to random search if Optuna is not available."""
        import random

        self._start_time = datetime.now()
        self._history = []
        self._iteration_count = 0

        best_params = {}
        best_score = float("-inf") if self.config.maximize else float("inf")

        for i in range(self.n_trials):
            if self._check_timeout():
                break

            trial_id = f"random_{i}"
            start_time = datetime.now()

            # Random sample
            params = {}
            for name, defn in search_space.to_dict().items():
                param_type = defn.get("type", ParameterType.CONTINUOUS)

                if param_type == ParameterType.CATEGORICAL:
                    params[name] = random.choice(defn["choices"])
                elif param_type == ParameterType.INTEGER:
                    params[name] = random.randint(int(defn["min"]), int(defn["max"]))
                elif param_type == ParameterType.CONTINUOUS:
                    params[name] = random.uniform(float(defn["min"]), float(defn["max"]))

            try:
                if asyncio.iscoroutinefunction(objective):
                    value = await objective(params)
                else:
                    value = objective(params)

                end_time = datetime.now()

                result = TrialResult(
                    trial_id=trial_id,
                    params=params,
                    objective_value=value,
                    status=OptimizationStatus.COMPLETED,
                    start_time=start_time,
                    end_time=end_time,
                    iteration=i,
                )

                if self.config.maximize:
                    if value > best_score:
                        best_score = value
                        best_params = params
                else:
                    if value < best_score:
                        best_score = value
                        best_params = params

            except Exception as e:
                end_time = datetime.now()
                result = TrialResult(
                    trial_id=trial_id,
                    params=params,
                    objective_value=float("-inf") if self.config.maximize else float("inf"),
                    status=OptimizationStatus.FAILED,
                    start_time=start_time,
                    end_time=end_time,
                    iteration=i,
                    error_message=str(e),
                )

            self._history.append(result)
            self._iteration_count += 1

        self._end_time = datetime.now()
        return self._create_result(best_params, best_score)


class MultiObjectiveBayesianOptimizer(BaseOptimizer[SearchSpace]):
    """
    Multi-objective Bayesian optimizer using Optuna.

    Optimizes multiple objectives simultaneously and finds Pareto front.
    Useful for balancing competing objectives like return vs drawdown vs Sharpe.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        n_trials: int = 100,
        objectives: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize multi-objective Bayesian optimizer.

        Args:
            config: Optimization configuration
            n_trials: Number of optimization trials
            objectives: List of objective names to optimize
        """
        super().__init__(config)

        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna required for multi-objective optimization")

        self.n_trials = n_trials
        self.objectives = objectives or ["return", "sharpe_ratio"]

        self._pareto_front: List[Dict[str, Any]] = []

    @classmethod
    def get_optimizer_type(cls) -> OptimizerType:
        """Get the type of this optimizer."""
        return OptimizerType.BAYESIAN

    def get_best_params(self) -> Dict[str, Any]:
        """Get the best parameters found (first Pareto solution)."""
        if self._pareto_front:
            return self._pareto_front[0].get("params", {})
        return {}

    def get_history(self) -> List[TrialResult]:
        """Get optimization history."""
        return self._history

    async def optimize(
        self,
        objectives: List[Callable[[Dict[str, Any]], float]],
        search_space: SearchSpace,
    ) -> OptimizationResult:
        """
        Run multi-objective optimization.

        Args:
            objectives: List of objective functions to optimize
            search_space: Parameter search space

        Returns:
            OptimizationResult with Pareto front in additional_info
        """
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna required for multi-objective optimization")

        self._start_time = datetime.now()
        self._history = []
        self._search_space = search_space

        # Create multi-objective study
        study = optuna.create_study(
            directions=["maximize"] * len(objectives),
            sampler=TPESampler(seed=self.config.random_seed),
        )

        # Define objective wrapper
        def optuna_objective(trial: Any) -> Tuple[float, ...]:
            params = {}
            for name, defn in search_space.to_dict().items():
                param_type = defn.get("type", ParameterType.CONTINUOUS)

                if param_type == ParameterType.CATEGORICAL:
                    params[name] = trial.suggest_categorical(name, defn["choices"])
                elif param_type == ParameterType.INTEGER:
                    params[name] = trial.suggest_int(name, int(defn["min"]), int(defn["max"]))
                elif param_type == ParameterType.CONTINUOUS:
                    params[name] = trial.suggest_float(name, float(defn["min"]), float(defn["max"]))

            # Evaluate all objectives
            values = []
            for obj_func in objectives:
                try:
                    value = obj_func(params)
                    values.append(float(value))
                except Exception:
                    values.append(float("-inf"))

            return tuple(values)

        # Run optimization
        study.optimize(optuna_objective, n_trials=self.n_trials)

        # Extract Pareto front
        self._extract_pareto_front(study)

        self._end_time = datetime.now()

        # Return result with first Pareto solution as best
        best_params = self._pareto_front[0]["params"] if self._pareto_front else {}

        result = self._create_result(best_params, 0.0)  # Score is meaningless for multi-objective
        result.additional_info["pareto_front"] = self._pareto_front

        return result

    def _extract_pareto_front(self, study: Any) -> None:
        """Extract Pareto front from Optuna study."""
        self._pareto_front = []

        best_trials = study.best_trials

        for trial in best_trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                self._pareto_front.append(
                    {
                        "params": dict(trial.params),
                        "objectives": trial.values,
                        "trial_number": trial.number,
                    }
                )
