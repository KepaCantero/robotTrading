"""
Optimization Module - Unified Interface.

This module provides a unified interface for all optimization algorithms
in the trading system, including:

1. Parameter Optimizers:
   - BayesianOptimizer: Bayesian optimization using Optuna (TPE sampler)
   - GridSearchOptimizer: Exhaustive grid search
   - GridSearchOptimizerCV: Grid search with cross-validation

2. Portfolio Optimizers:
   - MeanVarianceOptimizer: Markowitz mean-variance optimization

3. Factory:
   - OptimizerFactory: Creates optimizers by type

Quick Start:
    ```python
    from app.domain.optimization import (
        OptimizerFactory,
        OptimizationConfig,
        BayesianOptimizer,
        GridSearchOptimizer,
        MeanVarianceOptimizer,
        SearchSpace,
    )

    # Create using factory
    optimizer = OptimizerFactory.create("bayesian", n_trials=100)

    # Or create directly
    config = OptimizationConfig(maximize=True, metric="sharpe_ratio")
    optimizer = BayesianOptimizer(config, n_trials=100)

    # Define search space
    space = SearchSpace()
    space.add_integer("lookback", 5, 50, step=5)
    space.add_continuous("threshold", 0.01, 0.1, log=True)

    # Run optimization
    result = await optimizer.optimize(objective_func, space)
    print(f"Best params: {result.best_params}")
    print(f"Best score: {result.best_score}")
    ```

Portfolio Optimization:
    ```python
    from app.domain.optimization import MeanVarianceOptimizer

    optimizer = MeanVarianceOptimizer(
        risk_free_rate=0.02,  # or use CentralizedConfig.backtesting.default_risk_free_rate
        max_position=0.20,
    )

    # Optimize for max Sharpe
    result = optimizer.optimize_portfolio(returns, method="max_sharpe")
    print(f"Optimal weights: {result.weights_dict}")
    print(f"Expected Sharpe: {result.sharpe_ratio:.2f}")

    # Get efficient frontier
    frontier = optimizer.compute_efficient_frontier(returns)
    ```
"""

# Base classes and types
from .base_optimizer import (
    BaseOptimizer,
    OptimizationConfig,
    OptimizationResult,
    OptimizationStatus,
    OptimizerType,
    TrialResult,
)

# Parameter optimizers
from .bayesian_optimizer import (
    BayesianOptimizer,
    MultiObjectiveBayesianOptimizer,
    SearchSpace,
)

from .grid_search_optimizer import (
    GridSearchOptimizer,
    GridSearchOptimizerCV,
)

# Portfolio optimizers
from .mean_variance_optimizer import (
    MeanVarianceOptimizer,
    EfficientFrontier,
    EfficientFrontierPoint,
    PortfolioOptimizationResult,
    OptimizationMethod,
    ShrinkageMethod,
    InputValidationError,
    OptimizationError,
)

# Factory
from .factory import (
    OptimizerFactory,
    create_optimizer,
    create_portfolio_optimizer,
    create_backtest_optimizer,
)


__all__ = [
    # Base
    "BaseOptimizer",
    "OptimizationConfig",
    "OptimizationResult",
    "OptimizationStatus",
    "OptimizerType",
    "TrialResult",
    # Parameter optimizers
    "BayesianOptimizer",
    "MultiObjectiveBayesianOptimizer",
    "GridSearchOptimizer",
    "GridSearchOptimizerCV",
    "SearchSpace",
    # Portfolio optimizers
    "MeanVarianceOptimizer",
    "EfficientFrontier",
    "EfficientFrontierPoint",
    "PortfolioOptimizationResult",
    "OptimizationMethod",
    "ShrinkageMethod",
    "InputValidationError",
    "OptimizationError",
    # Factory
    "OptimizerFactory",
    "create_optimizer",
    "create_portfolio_optimizer",
    "create_backtest_optimizer",
]

# Version
__version__ = "2.0.0"
