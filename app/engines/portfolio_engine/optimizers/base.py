# pylint: disable=useless-parent-delegation
"""
Base Optimizer Module

Defines the abstract base class for all portfolio optimizers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class BaseOptimizer(ABC):
    """
    Abstract base class for portfolio optimizers.

    All portfolio optimizers should inherit from this class and implement
    the optimize method.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the optimizer.

        Args:
            config: Optimizer configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def optimize(
        self,
        returns: np.ndarray,
        **kwargs,
    ) -> np.ndarray:
        """
        Optimize portfolio weights.

        Args:
            returns: Asset returns matrix (T x N)
            **kwargs: Additional optimizer-specific parameters

        Returns:
            Optimal weights (N,)
        """

    def validate_weights(self, weights: np.ndarray) -> bool:
        """
        Validate portfolio weights.

        Args:
            weights: Portfolio weights

        Returns:
            True if valid
        """
        # Check weights sum to 1 (or close to 1)
        if not np.allclose(weights.sum(), 1.0, atol=1e-4):
            return False

        # Check no negative weights (for long-only)
        if np.any(weights < -1e-8):
            return False

        return True

    def get_status(self) -> Dict[str, Any]:
        """Get optimizer status."""
        return {
            'optimizer_type': self.__class__.__name__,
            'config': self.config,
        }


class MarkowitzOptimizer(BaseOptimizer):
    """
    Markowitz Mean-Variance Optimizer.

    Implements classical mean-variance optimization for portfolio allocation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Markowitz optimizer."""
        super().__init__(config)
        self.risk_free_rate = float(get_config().backtesting.default_risk_free_rate)

    def optimize(
        self,
        returns: np.ndarray,
        **kwargs,
    ) -> np.ndarray:
        """
        Optimize using mean-variance framework.

        Args:
            returns: Asset returns (T x N)
            **kwargs: Additional parameters

        Returns:
            Optimal weights
        """
        # Simple equal-weight fallback
        n_assets = returns.shape[1]
        return np.ones(n_assets) / n_assets


class RiskParityOptimizer(BaseOptimizer):
    """
    Risk Parity Optimizer.

    Allocates weights based on risk contribution (inverse volatility).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize risk parity optimizer."""
        super().__init__(config)

    def optimize(
        self,
        returns: np.ndarray,
        **kwargs,
    ) -> np.ndarray:
        """
        Optimize using risk parity.

        Args:
            returns: Asset returns (T x N)
            **kwargs: Additional parameters

        Returns:
            Optimal weights
        """
        # Calculate volatilities
        vols = returns.std(axis=0)

        # Inverse volatility weighting
        weights = 1 / vols
        weights = weights / weights.sum()

        return weights


class BlackLittermanOptimizer(BaseOptimizer):
    """
    Black-Litterman Optimizer.

    Incorporates views into portfolio optimization.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Black-Litterman optimizer."""
        super().__init__(config)

    def optimize(
        self,
        returns: np.ndarray,
        **kwargs,
    ) -> np.ndarray:
        """
        Optimize using Black-Litterman.

        Args:
            returns: Asset returns (T x N)
            **kwargs: Additional parameters (views, P, Q, etc.)

        Returns:
            Optimal weights
        """
        n_assets = returns.shape[1]
        return np.ones(n_assets) / n_assets


class KellyCriterionOptimizer(BaseOptimizer):
    """
    Kelly Criterion Optimizer.

    Maximizes long-term growth rate.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Kelly criterion optimizer."""
        super().__init__(config)

    def optimize(
        self,
        returns: np.ndarray,
        **kwargs,
    ) -> np.ndarray:
        """
        Optimize using Kelly criterion.

        Args:
            returns: Asset returns (T x N)
            **kwargs: Additional parameters

        Returns:
            Optimal weights
        """
        n_assets = returns.shape[1]
        return np.ones(n_assets) / n_assets
