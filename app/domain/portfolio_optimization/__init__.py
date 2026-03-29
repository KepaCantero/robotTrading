"""Portfolio Optimization Module.

This module implements modern portfolio optimization methods including:

1. Mean-Variance Optimization (MVO) - Markowitz (1952)
2. Nested Clustered Optimization (NCO) - López de Prado (2019)
3. Black-Litterman Model - Black & Litterman (1992)

Key Classes:
    MeanVarianceOptimizer: Markowitz MVO with efficient frontier
    NestedClusteredOptimization: Hierarchical risk parity via clustering
    BlackLittermanOptimizer: Combine equilibrium with investor views
    OptimizationResult: Result dataclass for optimization output
    NCOResult: Result from NCO optimization
    BlackLittermanResult: Result from BL optimization

Enums:
    OptimizationMethod: Available optimization methods (MAX_SHARPE, MIN_VARIANCE, etc.)
    ShrinkageMethod: Covariance shrinkage methods (LEDOIT_WOLF, OAS, SAMPLE)
    ViewType: Type of investor view (ABSOLUTE, RELATIVE)
    ClusteringMethod: Clustering methods for NCO (KMEANS, DBSCAN)

Exceptions:
    InputValidationError: Raised when input validation fails
    OptimizationError: Raised when optimization fails

Example (MVO):
    >>> from app.domain.portfolio_optimization import MeanVarianceOptimizer
    >>> import numpy as np
    >>>
    >>> optimizer = MeanVarianceOptimizer(lookback_days=252, max_position=0.20)
    >>> returns = np.random.randn(252, 10) * 0.01
    >>> result = optimizer.optimize(returns)

Example (Black-Litterman):
    >>> from app.domain.portfolio_optimization import (
    ...     BlackLittermanOptimizer, InvestorView, ViewType
    ... )
    >>>
    >>> optimizer = BlackLittermanOptimizer()
    >>> views = [
    ...     InvestorView(ViewType.ABSOLUTE, [0], np.array([1,0,0,0,0]), 0.08, 0.7),
    ... ]
    >>> result = optimizer.optimize(returns, market_caps=caps, views=views)

References:
    Rule 66: Covariance with 252-day lookback
    Rule 67: Mean-Variance Optimization
    Rule 68: Long-only constraints (0 <= weight <= 1)
    Rule 69: Sum constraint (sum(weights) = 1.0)
    Rule 70: Diversification (max 20% per asset)
    Rule 71: Efficient frontier (20+ points)
    Rule 72: Max Sharpe portfolio (default)
    Rule 73: L2 regularization (gamma=0.01)
    Rule 74: Ledoit-Wolf shrinkage
    Brecha #7: Black-Litterman portfolio optimization
"""

from app.domain.portfolio_optimization.black_litterman_optimizer import (
    BlackLittermanConfig,
    BlackLittermanOptimizer,
    BlackLittermanResult,
    EquilibriumReturns,
    InvestorView,
    ViewType,
    compute_black_litterman_weights,
)
from app.domain.portfolio_optimization.mean_variance_optimizer import (
    EfficientFrontier,
    EfficientFrontierPoint,
    InputValidationError,
    MeanVarianceOptimizer,
    OptimizationError,
    OptimizationMethod,
    OptimizationResult,
    ShrinkageMethod,
)
from app.domain.portfolio_optimization.nested_clustered_optimization import (
    ClusteringMethod,
    NCOConfig,
    NCOResult,
    NestedClusteredOptimization,
    compute_nco_weights,
)

__all__ = [
    "BlackLittermanConfig",
    # Black-Litterman Optimizer
    "BlackLittermanOptimizer",
    "BlackLittermanResult",
    "ClusteringMethod",
    "EfficientFrontier",
    "EfficientFrontierPoint",
    "EquilibriumReturns",
    # Exceptions
    "InputValidationError",
    "InvestorView",
    # Mean-Variance Optimizer
    "MeanVarianceOptimizer",
    "NCOConfig",
    "NCOResult",
    # Nested Clustered Optimization
    "NestedClusteredOptimization",
    "OptimizationError",
    # Enums
    "OptimizationMethod",
    "OptimizationResult",
    "ShrinkageMethod",
    "ViewType",
    "compute_black_litterman_weights",
    "compute_nco_weights",
]

__version__ = "2.0.0"
__author__ = "Algorithmic Trading System"
