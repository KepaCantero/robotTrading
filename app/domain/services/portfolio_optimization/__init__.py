"""
Portfolio Optimization Domain Services

This module contains domain services for portfolio optimization
following modern portfolio theory and advanced methods.
"""

from .black_litterman import BlackLittermanOptimizer, BlackLittermanResult, View, create_relative_view
from .cla import CriticalLineAlgorithm, CornerPortfolio, EfficientFrontierCLA, compute_turnover
from .covariance_calculator import CovarianceCalculator, CovarianceResult
from .denoise_correlation import CorrelationDenoiser, DenoisedResult
from .hrp import HierarchicalRiskParity, HRPResult, inverse_variance_weights
from .mean_variance_optimizer import EfficientFrontier, MeanVarianceOptimizer, OptimizationResult
from .nco import NestedClusteredOptimizer, NCOResult, get_nco_with_multiple_n
from .risk_parity import ClusterBasedRiskParity, RiskParityOptimizer, RiskParityResult

__all__ = [
    # Covariance
    "CovarianceCalculator",
    "CovarianceResult",
    # Mean-Variance
    "MeanVarianceOptimizer",
    "OptimizationResult",
    "EfficientFrontier",
    # De-noising
    "CorrelationDenoiser",
    "DenoisedResult",
    # Hierarchical methods
    "HierarchicalRiskParity",
    "HRPResult",
    "inverse_variance_weights",
    # NCO
    "NestedClusteredOptimizer",
    "NCOResult",
    "get_nco_with_multiple_n",
    # Risk Parity
    "RiskParityOptimizer",
    "RiskParityResult",
    "ClusterBasedRiskParity",
    # Black-Litterman
    "BlackLittermanOptimizer",
    "BlackLittermanResult",
    "View",
    "create_relative_view",
    # CLA
    "CriticalLineAlgorithm",
    "CornerPortfolio",
    "EfficientFrontierCLA",
    "compute_turnover",
]
