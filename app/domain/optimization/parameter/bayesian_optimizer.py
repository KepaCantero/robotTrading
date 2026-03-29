"""
Bayesian Optimizer using Optuna - FASE 6.1

Implements Bayesian optimization with:
- TPE (Tree-structured Parzen Estimator) sampler
- Median pruner for early stopping
- Multi-objective support
- Efficient for expensive evaluations
"""

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from tqdm import tqdm

from .base_optimizer import BaseOptimizer, OptimizationConfig, OptimizationResult
from .models import ParameterGrid, ParameterRange, ParameterScale, ParameterType
from .trial import TrialHistory, TrialResult, TrialStatus

# Try to import Optuna (optional dependency)
try:
    import optuna
    from optuna.pruners import HyperbandPruner, MedianPruner, SuccessiveHalvingPruner
    from optuna.samplers import CmaEsSampler, RandomSampler, TPESampler
    from optuna.study import Study

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None
    Study = None
    logger = logging.getLogger(__name__)
    logger.warning(
        "Optuna not installed. Bayesian optimizer will fall back to random search. "
        "Install with: pip install optuna"
    )


logger = logging.getLogger(__name__)


class BayesianOptimizer(BaseOptimizer):
    """
    Bayesian optimization using Optuna.

    Uses TPE (Tree-structured Parzen Estimator) for efficient hyperparameter
    optimization. More efficient than grid/random search for expensive evaluations.

    Features:
    - TPE sampler for efficient search
    - Median pruner for early stopping of bad trials
    - Multi-objective optimization support
    - Trial pruning for efficiency
    - Automatic hyperparameter suggestion based on type

    Requires optuna to be installed. Falls back to random search if not available.

    Example:
        ```python
        from app.domain.optimization.parameter import BayesianOptimizer, ParameterGrid, ParameterRange

        param_grid = ParameterGrid(parameters=[
            ParameterRange(name="learning_rate", min_value=1e-5, max_value=1e-1, scale="log"),
            ParameterRange(name="hidden_units", min_value=32, max_value=512, step=32),
            ParameterRange(name="dropout", min_value=0.0, max_value=0.5, step=0.05),
        ])

        config = OptimizationConfig(
            max_iterations=100,
            metric="validation_accuracy",
            maximize=True,
        )

        optimizer = BayesianOptimizer(config, n_trials=100)

        def objective(params):
            model = create_model(params)
            return train_and_evaluate(model)["accuracy"]

        result = await optimizer.optimize(objective, param_grid)
        logger.debug(f"Best params: {result.best_params}")
        ```
    """

    def __init__(
        self,
        config: OptimizationConfig,
        n_trials: int = 100,
        pruner: Optional[str] = "median",
        sampler: Optional[str] = "tpe",
        multivariate: bool = True,
        n_startup_trials: int = 10,
    ):
        """
        Initialize Bayesian optimizer.

        Args:
            config: Optimization configuration
            n_trials: Number of optimization trials
            pruner: Pruner type ('median', 'successive_halving', 'hyperband', None)
            sampler: Sampler type ('tpe', 'cmaes', 'random')
            multivariate: Whether to use multivariate TPE
            n_startup_trials: Number of random trials before TPE
        """
        super().__init__(config)

        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, will use random search fallback")

        self.n_trials = n_trials
        self.pruner_type = pruner
        self.sampler_type = sampler
        self.multivariate = multivariate
        self.n_startup_trials = n_startup_trials

    async def optimize(
        self,
        objective: Callable[[dict[str, Any]], float],
        param_grid: ParameterGrid,
    ) -> OptimizationResult:
        """
        Run Bayesian optimization with Optuna.

        Process:
        1. Create Optuna study with TPE sampler
        2. Define search space from param_grid
        3. Run optimization trials
        4. Prune unpromising trials
        5. Return best parameters

        Args:
            objective: Function to maximize/minimize
            param_grid: Parameter search space

        Returns:
            OptimizationResult with best parameters and all trials
        """
        # Fallback to random search if Optuna not available
        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, falling back to random search")
            from .random_search import RandomSearchOptimizer

            random_optimizer = RandomSearchOptimizer(self.config)
            random_optimizer.config.max_iterations = self.n_trials
            return await random_optimizer.optimize(objective, param_grid)

        self._start_time = datetime.now()
        self.history = TrialHistory()
        self._iteration_count = 0

        if self.config.verbose >= 1:
            logger.info("Starting Bayesian optimization with Optuna")
            logger.info(f"Number of trials: {self.n_trials}")

        # Create Optuna study
        study = self._create_study()

        # Define objective wrapper for Optuna
        def optuna_objective(trial):
            return self._objective_function(trial, objective, param_grid)

        # Run optimization
        try:
            # Setup progress bar
            pbar = None
            if self.config.progress_bar and self.config.verbose >= 1:
                pbar = tqdm(total=self.n_trials, desc="Bayesian Optimization")

            # Callback for progress tracking
            def callback(study, trial):
                self._iteration_count = len(study.trials)

                if pbar:
                    best_value = study.best_value
                    pbar.update(1)
                    pbar.set_postfix({"best": f"{best_value:.4f}"})

                # Check timeout
                if self._check_timeout():
                    study.stop()

            # Run optimization
            study.optimize(
                optuna_objective,
                n_trials=self.n_trials,
                callbacks=[callback] if pbar else None,
                show_progress_bar=False,
            )

            if pbar:
                pbar.close()

        except Exception as e:
            logger.error(f"Optuna optimization failed: {e}")
            # Return best found so far

        # Extract results
        self._extract_results_from_study(study)

        self._end_time = datetime.now()
        self.history.finish()

        best_params = study.best_params
        best_score = study.best_value

        # Apply maximize/minimize
        if not self.config.maximize:
            best_score = -best_score

        result = self._create_result(best_params, best_score)

        if self.config.verbose >= 1:
            logger.info(f"Bayesian optimization completed in {result.optimization_time:.2f}s")
            logger.info(f"Best score: {result.best_score:.6f}")
            logger.info(f"Evaluated {len(result.all_trials)} trials")

        return result

    def _create_study(self) -> "optuna.Study":
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

    def _create_sampler(self) -> "optuna.samplers.BaseSampler":
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

    def _create_pruner(self) -> Optional["optuna.pruners.BasePruner"]:
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

    def _objective_function(
        self,
        trial: "optuna.Trial",
        objective: Callable[[dict[str, Any]], float],
        param_grid: ParameterGrid,
    ) -> float:
        """
        Optuna objective function wrapper.

        Args:
            trial: Optuna trial object
            objective: User's objective function
            param_grid: Parameter search space

        Returns:
            Objective value (will be maximized/minimized by Optuna)
        """
        # Define search space and get params
        params = self._define_search_space(trial, param_grid)

        # Evaluate objective
        try:
            value = objective(params)

            # Apply maximize/minimize
            if not self.config.maximize:
                value = -value

            return value

        except Exception as e:
            logger.warning(f"Trial failed: {e}")
            # Return worst possible value
            return float("-inf") if self.config.maximize else float("inf")

    def _define_search_space(
        self,
        trial: "optuna.Trial",
        param_grid: ParameterGrid,
    ) -> dict[str, Any]:
        """
        Define Optuna search space from parameter grid.

        Args:
            trial: Optuna trial object
            param_grid: Parameter grid defining search space

        Returns:
            Parameter dictionary
        """
        params = {}

        for param_range in param_grid.parameters:
            params[param_range.name] = self._suggest_parameter(trial, param_range)

        return params

    def _suggest_parameter(
        self,
        trial: "optuna.Trial",
        param: ParameterRange,
    ) -> Any:
        """
        Suggest a parameter value using Optuna.

        Args:
            trial: Optuna trial object
            param: Parameter range definition

        Returns:
            Suggested parameter value

        Raises:
            ValueError: If parameter values are missing for categorical/discrete types
        """
        if param.parameter_type == ParameterType.CATEGORICAL:
            if param.values is None:
                raise ValueError(f"Categorical parameter '{param.name}' has no values")
            return trial.suggest_categorical(param.name, param.values)

        elif param.parameter_type == ParameterType.DISCRETE:
            if param.values is None:
                raise ValueError(f"Discrete parameter '{param.name}' has no values")
            return trial.suggest_categorical(param.name, param.values)

        elif param.parameter_type == ParameterType.INTEGER:
            if param.min_value is None or param.max_value is None:
                raise ValueError(f"Integer parameter '{param.name}' missing min/max values")
            int_min = int(param.min_value)
            int_max = int(param.max_value)
            step = int(param.step) if param.step is not None else 1

            if step == 1:
                return trial.suggest_int(param.name, int_min, int_max)
            else:
                # For integer with step > 1, use categorical
                values = list(range(int_min, int_max + 1, step))
                return trial.suggest_categorical(param.name, values)

        elif param.parameter_type == ParameterType.CONTINUOUS:
            if param.min_value is None or param.max_value is None:
                raise ValueError(f"Continuous parameter '{param.name}' missing min/max values")
            float_min = float(param.min_value)
            float_max = float(param.max_value)
            float_step = float(param.step) if param.step is not None else None

            if param.scale == ParameterScale.LOG:
                return trial.suggest_float(param.name, float_min, float_max, log=True)
            elif float_step is not None:
                # Linear with step
                return trial.suggest_float(param.name, float_min, float_max, step=float_step)
            else:
                return trial.suggest_float(param.name, float_min, float_max)

        raise ValueError(f"Unknown parameter type: {param.parameter_type}")

    def _extract_results_from_study(self, study: "optuna.Study") -> None:
        """
        Extract trial results from Optuna study.

        Args:
            study: Completed Optuna study
        """
        self._iteration_count = len(study.trials)

        for trial in study.trials:
            params = trial.params.copy()
            value = trial.value

            # Determine status
            if trial.state == optuna.trial.TrialState.COMPLETE:
                status = TrialStatus.COMPLETED
            elif trial.state == optuna.trial.TrialState.PRUNED:
                status = TrialStatus.PRUNED
            elif trial.state == optuna.trial.TrialState.FAIL:
                status = TrialStatus.FAILED
            else:
                status = TrialStatus.FAILED

            # Create trial result
            result = TrialResult(
                trial_id=f"optuna_{trial.number}",
                params=params,
                objective_value=(
                    value
                    if value is not None
                    else (float("-inf") if self.config.maximize else float("inf"))
                ),
                status=status,
                start_time=datetime.fromtimestamp(trial.datetime_start.timestamp()),
                end_time=(
                    datetime.fromtimestamp(trial.datetime_complete.timestamp())
                    if trial.datetime_complete
                    else None
                ),
                iteration=trial.number,
                additional_info={
                    "optuna_trial_number": trial.number,
                    "optuna_state": trial.state.name,
                    "intermediate_values": trial.intermediate_values,
                },
            )

            self.history.add_trial(result)


class MultiObjectiveBayesianOptimizer(BaseOptimizer):
    """
    Multi-objective Bayesian optimizer using Optuna.

    Optimizes multiple objectives simultaneously and finds Pareto front.
    Useful for balancing competing objectives like return vs drawdown vs Sharpe.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        n_trials: int = 100,
        objectives: Optional[list[str]] = None,
    ):
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

    async def optimize_multi_objective(
        self,
        objectives: list[Callable[[dict[str, Any]], float]],
        param_grid: ParameterGrid,
    ) -> "ParetoFront":
        """
        Run multi-objective optimization.

        Args:
            objectives: List of objective functions to optimize
            param_grid: Parameter search space

        Returns:
            ParetoFront with non-dominated solutions
        """
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna required for multi-objective optimization")

        self._start_time = datetime.now()

        # Create multi-objective study
        study = optuna.create_study(
            directions=["maximize"] * len(objectives),
            sampler=TPESampler(seed=self.config.random_seed),
        )

        # Define objective wrapper
        def optuna_objective(trial):
            params = {}
            for param_range in param_grid.parameters:
                params[param_range.name] = self._suggest_parameter(trial, param_range)

            # Evaluate all objectives
            values = []
            for obj_func in objectives:
                try:
                    value = obj_func(params)
                    values.append(value)
                except Exception:
                    values.append(float("-inf"))

            return tuple(values)

        # Run optimization
        study.optimize(optuna_objective, n_trials=self.n_trials)

        # Extract Pareto front
        pareto_front = self._extract_pareto_front(study, objectives)

        self._end_time = datetime.now()

        return pareto_front

    def _suggest_parameter(
        self,
        trial: "optuna.Trial",
        param: ParameterRange,
    ) -> Any:
        """Suggest parameter using Optuna."""
        if param.parameter_type == ParameterType.CATEGORICAL:
            if param.values is None:
                raise ValueError(f"Categorical parameter '{param.name}' has no values")
            return trial.suggest_categorical(param.name, param.values)
        elif param.parameter_type == ParameterType.INTEGER:
            if param.min_value is None or param.max_value is None:
                raise ValueError(f"Integer parameter '{param.name}' missing min/max values")
            int_min = int(param.min_value)
            int_max = int(param.max_value)
            return trial.suggest_int(param.name, int_min, int_max)
        elif param.parameter_type == ParameterType.CONTINUOUS:
            if param.min_value is None or param.max_value is None:
                raise ValueError(f"Continuous parameter '{param.name}' missing min/max values")
            float_min = float(param.min_value)
            float_max = float(param.max_value)
            if param.scale == ParameterScale.LOG:
                return trial.suggest_float(param.name, float_min, float_max, log=True)
            else:
                return trial.suggest_float(param.name, float_min, float_max)

        raise ValueError(f"Unknown parameter type: {param.parameter_type}")

    def _extract_pareto_front(
        self,
        study: "optuna.Study",
        objectives: list[Callable],
    ) -> "ParetoFront":
        """Extract Pareto front from Optuna study."""
        best_trials = study.best_trials

        solutions = []
        scores = []

        for trial in best_trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                solution = ParetoSolution(
                    params=trial.params,
                    objectives=trial.values,
                    trial_number=trial.number,
                )
                solutions.append(solution)
                scores.append(tuple(trial.values))

        return ParetoFront(
            solutions=solutions,
            scores=scores,
            n_trials=len(study.trials),
        )


class ParetoSolution:
    """A solution on the Pareto front."""

    def __init__(
        self,
        params: dict[str, Any],
        objectives: tuple[float, ...],
        trial_number: int,
    ):
        self.params = params
        self.objectives = objectives
        self.trial_number = trial_number


class ParetoFront:
    """Pareto front of non-dominated solutions."""

    def __init__(
        self,
        solutions: list[ParetoSolution],
        scores: list[tuple[float, ...]],
        n_trials: int = 0,
    ):
        self.solutions = solutions
        self.scores = scores
        self.n_trials = n_trials
        self.fronts: list[list[int]] = []

    def get_best_solution(self, objective_index: int = 0) -> Optional[ParetoSolution]:
        """Get best solution for a specific objective."""
        if not self.solutions:
            return None

        return max(self.solutions, key=lambda s: s.objectives[objective_index])

    def get_solution_by_criteria(
        self,
        weights: Optional[tuple[float, ...]] = None,
    ) -> Optional[ParetoSolution]:
        """
        Get solution by weighted criteria.

        Args:
            weights: Weights for each objective (defaults to equal weights)

        Returns:
            Best solution according to weighted criteria
        """
        if not self.solutions:
            return None

        if weights is None:
            weights = tuple(1.0 for _ in range(len(self.solutions[0].objectives)))

        # Normalize weights
        total = sum(weights)
        weights = tuple(w / total for w in weights)

        # Calculate weighted scores
        best_solution = None
        best_score = float("-inf")

        for solution in self.solutions:
            score = sum(w * o for w, o in zip(weights, solution.objectives))
            if score > best_score:
                best_score = score
                best_solution = solution

        return best_solution

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "solutions": [
                {
                    "params": s.params,
                    "objectives": s.objectives,
                    "trial_number": s.trial_number,
                }
                for s in self.solutions
            ],
            "scores": self.scores,
            "n_trials": self.n_trials,
            "n_solutions": len(self.solutions),
        }
