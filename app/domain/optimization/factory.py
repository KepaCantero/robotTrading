"""
Optimizer Factory - Creates optimizers by type.

This module provides a factory for creating optimizers based on type,
configuration, and use case.

Usage:
    ```python
    from app.domain.optimization.factory import OptimizerFactory
    from app.domain.optimization.base_optimizer import OptimizationConfig

    # Create a Bayesian optimizer
    optimizer = OptimizerFactory.create("bayesian", max_iterations=100)

    # Create with full config
    config = OptimizationConfig(maximize=True, metric="sharpe_ratio")
    optimizer = OptimizerFactory.create("bayesian", config=config)

    # Create portfolio optimizer
    portfolio_optimizer = OptimizerFactory.create("mean_variance", risk_free_rate=0.02)
    ```
"""

from __future__ import annotations

import logging
from typing import Callable, ClassVar, Union

import numpy as np
from numpy.typing import NDArray

from app.shared.config.centralized_config import get_config

from .base_optimizer import BaseOptimizer, OptimizationConfig, OptimizerType
from .bayesian_optimizer import BayesianOptimizer, SearchSpace
from .grid_search_optimizer import GridSearchOptimizer, GridSearchOptimizerCV
from .mean_variance_optimizer import MeanVarianceOptimizer

logger = logging.getLogger(__name__)


# Type aliases for clarity
ObjectiveFunction = Callable[[dict[str, Union[str, int, float, bool]]], float]
SearchSpaceType = Union[SearchSpace, NDArray[np.float64]]


class OptimizerFactory:
    """
    Factory for creating optimizers.

    Provides a unified interface for creating different types of optimizers
    with sensible defaults and configuration validation.

    Supported optimizer types:
    - "bayesian": Bayesian optimization using Optuna (TPE sampler)
    - "grid_search": Exhaustive grid search
    - "random_search": Random search (available via Bayesian fallback)
    - "mean_variance": Markowitz mean-variance portfolio optimization
    - "multi_strategy": Multi-strategy optimization

    Example:
        ```python
        # Quick creation with defaults
        optimizer = OptimizerFactory.create("bayesian", n_trials=100)

        # Full configuration
        config = OptimizationConfig(
            max_iterations=100,
            maximize=True,
            metric="sharpe_ratio",
        )
        optimizer = OptimizerFactory.create("bayesian", config=config)

        # Portfolio optimizer
        optimizer = OptimizerFactory.create(
            "mean_variance",
            risk_free_rate=0.02,
            max_position=0.20,
        )
        ```
    """

    # Registry of available optimizers
    _registry: ClassVar[dict[OptimizerType, type[BaseOptimizer]]] = {}

    @classmethod
    def register(cls, optimizer_type: OptimizerType, optimizer_class: type[BaseOptimizer]) -> None:
        """
        Register an optimizer class.

        Args:
            optimizer_type: Type identifier for the optimizer
            optimizer_class: The optimizer class to register
        """
        cls._registry[optimizer_type] = optimizer_class
        logger.debug(f"Registered optimizer: {optimizer_type.value}")

    @classmethod
    def create(
        cls,
        optimizer_type: str | OptimizerType,
        config: OptimizationConfig | None = None,
        **kwargs: str | int | float | bool,
    ) -> BaseOptimizer:
        """
        Create an optimizer instance.

        Args:
            optimizer_type: Type of optimizer to create
            config: Optimization configuration (optional)
            **kwargs: Additional arguments passed to the optimizer constructor

        Returns:
            Configured optimizer instance

        Raises:
            ValueError: If optimizer type is not supported
        """
        # Convert string to enum if needed
        if isinstance(optimizer_type, str):
            optimizer_type = cls._parse_optimizer_type(optimizer_type)

        # Get default config if not provided
        if config is None:
            config = cls._get_default_config(optimizer_type)

        # Create optimizer based on type
        if optimizer_type == OptimizerType.BAYESIAN:
            return cls._create_bayesian(config, **kwargs)

        elif optimizer_type == OptimizerType.GRID_SEARCH:
            return cls._create_grid_search(config, **kwargs)

        elif optimizer_type == OptimizerType.MEAN_VARIANCE:
            return cls._create_mean_variance(config, **kwargs)

        elif optimizer_type == OptimizerType.MULTI_STRATEGY:
            return cls._create_multi_strategy(config, **kwargs)

        elif optimizer_type == OptimizerType.RANDOM_SEARCH:
            # Random search is a special case of Bayesian without Optuna
            return cls._create_bayesian(config, sampler="random", **kwargs)

        elif optimizer_type == OptimizerType.RISK_PARITY:
            # Risk parity is available via MeanVarianceOptimizer
            return cls._create_mean_variance(config, method="risk_parity", **kwargs)

        else:
            # Check registry for custom optimizers
            if optimizer_type in cls._registry:
                optimizer_class = cls._registry[optimizer_type]
                return optimizer_class(config, **kwargs)

            raise ValueError(f"Unsupported optimizer type: {optimizer_type}")

    @classmethod
    def _parse_optimizer_type(cls, type_str: str) -> OptimizerType:
        """Parse string to OptimizerType enum."""
        type_map = {
            "bayesian": OptimizerType.BAYESIAN,
            "bayes": OptimizerType.BAYESIAN,
            "optuna": OptimizerType.BAYESIAN,
            "tpe": OptimizerType.BAYESIAN,
            "grid_search": OptimizerType.GRID_SEARCH,
            "grid": OptimizerType.GRID_SEARCH,
            "exhaustive": OptimizerType.GRID_SEARCH,
            "random_search": OptimizerType.RANDOM_SEARCH,
            "random": OptimizerType.RANDOM_SEARCH,
            "mean_variance": OptimizerType.MEAN_VARIANCE,
            "markowitz": OptimizerType.MEAN_VARIANCE,
            "mvo": OptimizerType.MEAN_VARIANCE,
            "portfolio": OptimizerType.MEAN_VARIANCE,
            "risk_parity": OptimizerType.RISK_PARITY,
            "multi_strategy": OptimizerType.MULTI_STRATEGY,
            "multi": OptimizerType.MULTI_STRATEGY,
        }

        normalized = type_str.lower().strip()
        if normalized not in type_map:
            raise ValueError(
                f"Unknown optimizer type: '{type_str}'. Available types: {list(type_map.keys())}"
            )

        return type_map[normalized]

    @classmethod
    def _get_default_config(cls, optimizer_type: OptimizerType) -> OptimizationConfig:
        """Get default configuration for an optimizer type."""
        defaults = {
            OptimizerType.BAYESIAN: OptimizationConfig(
                max_iterations=100,
                maximize=True,
                metric="sharpe_ratio",
                early_stopping=True,
                early_stopping_patience=15,
            ),
            OptimizerType.GRID_SEARCH: OptimizationConfig(
                max_iterations=1000,
                maximize=True,
                metric="sharpe_ratio",
                n_jobs=1,
            ),
            OptimizerType.RANDOM_SEARCH: OptimizationConfig(
                max_iterations=100,
                maximize=True,
                metric="sharpe_ratio",
            ),
            OptimizerType.MEAN_VARIANCE: OptimizationConfig(
                maximize=True,
                metric="sharpe_ratio",
            ),
            OptimizerType.MULTI_STRATEGY: OptimizationConfig(
                max_iterations=50,
                maximize=True,
                metric="sharpe_ratio",
            ),
            OptimizerType.RISK_PARITY: OptimizationConfig(
                maximize=True,
                metric="sharpe_ratio",
            ),
        }

        return defaults.get(optimizer_type, OptimizationConfig())

    @classmethod
    def _create_bayesian(
        cls, config: OptimizationConfig, **kwargs: str | int | float | bool
    ) -> BayesianOptimizer:
        """Create a Bayesian optimizer."""
        return BayesianOptimizer(
            config=config,
            n_trials=kwargs.get("n_trials", config.max_iterations),
            pruner=kwargs.get("pruner", "median"),
            sampler=kwargs.get("sampler", "tpe"),
            multivariate=kwargs.get("multivariate", True),
            n_startup_trials=kwargs.get("n_startup_trials", 10),
        )

    @classmethod
    def _create_grid_search(
        cls, config: OptimizationConfig, **kwargs: str | int | float | bool
    ) -> GridSearchOptimizer:
        """Create a Grid Search optimizer."""
        use_cv = kwargs.get("use_cv", False)

        if use_cv:
            return GridSearchOptimizerCV(
                config=config,
                cv_folds=kwargs.get("cv_folds", 5),
                cv_metric=kwargs.get("cv_metric", "mean"),
            )

        return GridSearchOptimizer(config=config)

    @classmethod
    def _create_mean_variance(
        cls, config: OptimizationConfig, **kwargs: str | int | float | bool
    ) -> MeanVarianceOptimizer:
        """Create a Mean-Variance optimizer."""
        return MeanVarianceOptimizer(
            config=config,
            lookback_days=kwargs.get("lookback_days", 252),
            max_position=kwargs.get("max_position", 0.20),
            risk_free_rate=kwargs.get(
                "risk_free_rate", float(get_config().backtesting.default_risk_free_rate)
            ),
            regularization_gamma=kwargs.get("regularization_gamma", 0.01),
            sum_tolerance=kwargs.get("sum_tolerance", 1e-6),
            allow_short=kwargs.get("allow_short", False),
        )

    @classmethod
    def _create_multi_strategy(
        cls, config: OptimizationConfig, **kwargs: str | int | float | bool
    ) -> BayesianOptimizer:
        """
        Create a multi-strategy optimizer.

        Note: Multi-strategy optimization uses Bayesian optimization
        with a specialized objective function.
        """
        return BayesianOptimizer(
            config=config,
            n_trials=kwargs.get("n_trials", config.max_iterations),
            pruner=kwargs.get("pruner", "median"),
            sampler=kwargs.get("sampler", "tpe"),
        )

    @classmethod
    def get_available_types(cls) -> list[str]:
        """Get list of available optimizer types."""
        return [
            "bayesian",
            "grid_search",
            "random_search",
            "mean_variance",
            "risk_parity",
            "multi_strategy",
        ]

    @classmethod
    def get_recommended_type(
        cls,
        n_parameters: int,
        evaluation_cost: str = "medium",
        time_budget: str = "medium",
    ) -> OptimizerType:
        """
        Get recommended optimizer type based on problem characteristics.

        Args:
            n_parameters: Number of parameters to optimize
            evaluation_cost: Cost of evaluating the objective ("low", "medium", "high")
            time_budget: Available time for optimization ("low", "medium", "high")

        Returns:
            Recommended OptimizerType
        """
        # Grid search is good for small parameter spaces
        if n_parameters <= 3 and time_budget != "low":
            return OptimizerType.GRID_SEARCH

        # Bayesian is good for expensive evaluations and medium-large spaces
        if evaluation_cost in ("medium", "high") or n_parameters > 5:
            return OptimizerType.BAYESIAN

        # Default to Bayesian for most cases
        return OptimizerType.BAYESIAN

    @classmethod
    def create_for_portfolio(
        cls,
        method: str = "max_sharpe",
        risk_free_rate: float | None = None,
        max_position: float = 0.20,
        **kwargs: str | int | float | bool,
    ) -> MeanVarianceOptimizer:
        """
        Create an optimizer specifically configured for portfolio optimization.

        Args:
            method: Optimization method ("max_sharpe", "min_variance", "risk_parity")
            risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
            max_position: Maximum position per asset
            **kwargs: Additional arguments

        Returns:
            Configured MeanVarianceOptimizer
        """
        config = OptimizationConfig(
            maximize=True,
            metric="sharpe_ratio",
        )

        rf = (
            risk_free_rate
            if risk_free_rate is not None
            else float(get_config().backtesting.default_risk_free_rate)
        )

        return MeanVarianceOptimizer(
            config=config,
            risk_free_rate=rf,
            max_position=max_position,
            **kwargs,
        )

    @classmethod
    def create_for_backtest(
        cls,
        n_trials: int = 100,
        early_stopping: bool = True,
        n_jobs: int = 1,
        **kwargs: str | int | float | bool,
    ) -> BayesianOptimizer:
        """
        Create an optimizer specifically configured for backtest optimization.

        Args:
            n_trials: Number of optimization trials
            early_stopping: Enable early stopping
            n_jobs: Number of parallel jobs
            **kwargs: Additional arguments

        Returns:
            Configured BayesianOptimizer
        """
        config = OptimizationConfig(
            max_iterations=n_trials,
            maximize=True,
            metric="sharpe_ratio",
            early_stopping=early_stopping,
            early_stopping_patience=15,
            n_jobs=n_jobs,
            progress_bar=True,
        )

        return BayesianOptimizer(
            config=config,
            n_trials=n_trials,
            **kwargs,
        )


# Convenience functions
def create_optimizer(
    optimizer_type: str,
    config: OptimizationConfig | None = None,
    **kwargs: str | int | float | bool,
) -> BaseOptimizer:
    """
    Convenience function to create an optimizer.

    Args:
        optimizer_type: Type of optimizer to create
        config: Optimization configuration (optional)
        **kwargs: Additional arguments

    Returns:
        Configured optimizer instance
    """
    return OptimizerFactory.create(optimizer_type, config=config, **kwargs)


def create_portfolio_optimizer(
    method: str = "max_sharpe",
    **kwargs: str | int | float | bool,
) -> MeanVarianceOptimizer:
    """
    Convenience function to create a portfolio optimizer.

    Args:
        method: Optimization method
        **kwargs: Additional arguments

    Returns:
        Configured MeanVarianceOptimizer
    """
    return OptimizerFactory.create_for_portfolio(method=method, **kwargs)


def create_backtest_optimizer(
    n_trials: int = 100,
    **kwargs: str | int | float | bool,
) -> BayesianOptimizer:
    """
    Convenience function to create a backtest optimizer.

    Args:
        n_trials: Number of optimization trials
        **kwargs: Additional arguments

    Returns:
        Configured BayesianOptimizer
    """
    return OptimizerFactory.create_for_backtest(n_trials=n_trials, **kwargs)
