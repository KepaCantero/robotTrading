"""
Parameter Optimization Module - FASE 6.1

This module provides comprehensive parameter optimization capabilities for trading strategies:
- Grid search: Exhaustive parameter search with parallel execution
- Random search: Efficient random sampling from parameter space
- Bayesian optimization: Smart hyperparameter optimization using Optuna
- Multi-objective optimization: Pareto front for balancing multiple metrics

Example usage:
    ```python
    from app.optimization.parameter import (
        GridSearchOptimizer,
        RandomSearchOptimizer,
        BayesianOptimizer,
        ParameterGrid,
        ParameterRange,
        OptimizationConfig,
    )

    # Define parameter space
    param_grid = ParameterGrid(parameters=[
        ParameterRange(name="lookback_period", min_value=5, max_value=50, step=5),
        ParameterRange(name="threshold", min_value=0.1, max_value=2.0, step=0.1),
        ParameterRange(name="strategy_type", values=["momentum", "mean_reversion"]),
    ])

    # Configure optimization
    config = OptimizationConfig(
        max_iterations=100,
        n_jobs=4,
        metric="sharpe_ratio",
        maximize=True,
        early_stopping=True,
        early_stopping_patience=10,
    )

    # Run grid search
    optimizer = GridSearchOptimizer(config)
    result = await optimizer.optimize(objective_function, param_grid)

    # Run Bayesian optimization
    bayesian_opt = BayesianOptimizer(config, n_trials=100)
    result = await bayesian_opt.optimize(objective_function, param_grid)
    ```
"""

from .base_optimizer import (
    BaseOptimizer,
    OptimizationConfig,
    OptimizationResult,
)
from .bayesian_optimizer import BayesianOptimizer
from .grid_search import GridSearchOptimizer
from .models import (
    ParameterConstraint,
    ParameterGrid,
    ParameterRange,
    ParameterScale,
    ParameterType,
)
from .multi_objective import (
    MultiObjectiveOptimizer,
    ParetoFront,
    ParetoSolution,
    ScalarizationOptimizer,
    calculate_hypervolume,
    find_non_dominated_solutions,
)
from .random_search import RandomSearchOptimizer
from .trial import (
    TrialHistory,
    TrialResult,
    TrialStatus,
)

__all__ = [
    # Base classes
    "BaseOptimizer",
    "OptimizationConfig",
    "OptimizationResult",
    # Optimizers
    "GridSearchOptimizer",
    "RandomSearchOptimizer",
    "BayesianOptimizer",
    # Multi-objective
    "MultiObjectiveOptimizer",
    "ParetoFront",
    "ParetoSolution",
    "ScalarizationOptimizer",
    "find_non_dominated_solutions",
    "calculate_hypervolume",
    # Models
    "ParameterRange",
    "ParameterGrid",
    "ParameterConstraint",
    "ParameterType",
    "ParameterScale",
    # Trial tracking
    "TrialResult",
    "TrialStatus",
    "TrialHistory",
]
