"""
Portfolio Optimization Domain Services

This module contains domain services for portfolio optimization
following modern portfolio theory and advanced methods.
"""

from .black_litterman import (
    BlackLittermanOptimizer,
    BlackLittermanResult,
    View,
    create_relative_view,
)
from .cla import CornerPortfolio, CriticalLineAlgorithm, EfficientFrontierCLA, compute_turnover
from .covariance_calculator import CovarianceCalculator, CovarianceResult
from .denoise_correlation import CorrelationDenoiser, DenoisedResult
from .hrp import HierarchicalRiskParity, HRPResult, inverse_variance_weights
from .mean_variance_optimizer import EfficientFrontier, MeanVarianceOptimizer, OptimizationResult
from .nco import NCOResult, NestedClusteredOptimizer, get_nco_with_multiple_n
from .risk_parity import RiskParityOptimizer, RiskParityResult

__all__ = [
    # Black-Litterman
    "BlackLittermanOptimizer",
    "BlackLittermanResult",
    "CornerPortfolio",
    # De-noising
    "CorrelationDenoiser",
    # Covariance
    "CovarianceCalculator",
    "CovarianceResult",
    # CLA
    "CriticalLineAlgorithm",
    "DenoisedResult",
    "EfficientFrontier",
    "EfficientFrontierCLA",
    "HRPResult",
    # Hierarchical methods
    "HierarchicalRiskParity",
    # Mean-Variance
    "MeanVarianceOptimizer",
    "NCOResult",
    # NCO
    "NestedClusteredOptimizer",
    "OptimizationResult",
    # Risk Parity
    "RiskParityOptimizer",
    "RiskParityResult",
    "View",
    "compute_turnover",
    "create_relative_view",
    "get_nco_with_multiple_n",
    "inverse_variance_weights",
]
