"""
Mean-Variance Optimizer - Markowitz Portfolio Optimization

Implements Markowitz Mean-Variance Optimization for portfolio construction.

Reference: Rule 48-papers-markowitz (Markowitz Portfolio Selection)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize, OptimizeResult

from app.domain.services.portfolio_optimization.covariance_calculator import (
    CovarianceCalculator,
    CovarianceResult,
)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    weights: np.ndarray  # Optimal weights
    expected_return: float  # Expected portfolio return
    expected_risk: float  # Expected portfolio risk (std dev)
    sharpe_ratio: float  # Sharpe ratio
    symbols: List[str]  # Asset symbols

    # Optimization metadata
    converged: bool  # Whether optimization converged
    message: str  # Optimizer message

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}

    def get_allocation(self, total_capital: Decimal) -> Dict[str, Decimal]:
        """
        Get dollar allocation for each asset.

        Args:
            total_capital: Total capital to allocate

        Returns:
            Dictionary of symbol -> allocation amount
        """
        return {
            symbol: Decimal(str(weight)) * total_capital
            for symbol, weight in zip(self.symbols, self.weights)
        }


@dataclass
class EfficientFrontier:
    """Efficient frontier points."""

    returns: np.ndarray  # Portfolio returns
    risks: np.ndarray  # Portfolio risks (std dev)
    weights_list: List[np.ndarray]  # Weight sets for each point
    sharpe_ratios: np.ndarray  # Sharpe ratios

    def get_max_sharpe_point(self) -> Tuple[int, float, float]:
        """Get index, return, and risk of max Sharpe point."""
        idx = np.argmax(self.sharpe_ratios)
        return int(idx), float(self.returns[idx]), float(self.risks[idx])

    def get_min_variance_point(self) -> Tuple[int, float, float]:
        """Get index, return, and risk of min variance point."""
        idx = np.argmin(self.risks)
        return int(idx), float(self.returns[idx]), float(self.risks[idx])


class MeanVarianceOptimizer:
    """
    Mean-variance portfolio optimizer (Markowitz).

    Implements classic Markowitz optimization:
    - Maximize Sharpe ratio
    - Minimize variance
    - Target return optimization
    - Efficient frontier computation

    Reference: Markowitz, H. (1952). "Portfolio Selection"
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        allow_short: bool = False,
    ):
        """
        Initialize optimizer.

        Args:
            risk_free_rate: Annual risk-free rate
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
            allow_short: Whether to allow short positions
        """
        self._risk_free_rate = risk_free_rate
        self._min_weight = -1.0 if allow_short else 0.0
        self._max_weight = max_weight
        self._allow_short = allow_short

    def maximize_sharpe(
        self,
        cov_result: CovarianceResult,
    ) -> OptimizationResult:
        """
        Find portfolio that maximizes Sharpe ratio.

        Maximize: (μ'w - r_f) / sqrt(w'Σw)

        Args:
            cov_result: Covariance calculation result

        Returns:
            OptimizationResult with optimal weights
        """
        n_assets = len(cov_result.symbols)

        # Objective: negative Sharpe ratio (for minimization)
        def objective(weights: np.ndarray) -> float:
            portfolio_return = float(weights @ cov_result.means)
            portfolio_var = float(weights @ cov_result.covariance_matrix @ weights)
            portfolio_std = np.sqrt(portfolio_var)

            # Annualize (assuming daily returns)
            annual_return = portfolio_return * 252
            annual_std = portfolio_std * np.sqrt(252)

            sharpe = (annual_return - self._risk_free_rate) / annual_std
            return -sharpe  # Minimize negative Sharpe = maximize Sharpe

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # Weights sum to 1
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Initial guess (equal weight)
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9},
        )

        # Extract results
        weights = result.x
        expected_return = float(weights @ cov_result.means)
        expected_var = float(weights @ cov_result.covariance_matrix @ weights)
        expected_risk = np.sqrt(expected_var)

        # Annualize
        annual_return = expected_return * 252
        annual_risk = expected_risk * np.sqrt(252)
        sharpe = (annual_return - self._risk_free_rate) / annual_risk

        return OptimizationResult(
            weights=weights,
            expected_return=annual_return,
            expected_risk=annual_risk,
            sharpe_ratio=sharpe,
            symbols=cov_result.symbols,
            converged=result.success,
            message=result.message,
        )

    def minimize_variance(
        self,
        cov_result: CovarianceResult,
    ) -> OptimizationResult:
        """
        Find minimum variance portfolio.

        Minimize: w'Σw
        Subject to: Σw = 1

        Args:
            cov_result: Covariance calculation result

        Returns:
            OptimizationResult with minimum variance weights
        """
        n_assets = len(cov_result.symbols)

        # Objective: portfolio variance
        def objective(weights: np.ndarray) -> float:
            return float(weights @ cov_result.covariance_matrix @ weights)

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Initial guess
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        # Extract results
        weights = result.x
        expected_return = float(weights @ cov_result.means)
        expected_var = float(weights @ cov_result.covariance_matrix @ weights)
        expected_risk = np.sqrt(expected_var)

        # Annualize
        annual_return = expected_return * 252
        annual_risk = expected_risk * np.sqrt(252)
        sharpe = (annual_return - self._risk_free_rate) / annual_risk

        return OptimizationResult(
            weights=weights,
            expected_return=annual_return,
            expected_risk=annual_risk,
            sharpe_ratio=sharpe,
            symbols=cov_result.symbols,
            converged=result.success,
            message=result.message,
        )

    def target_return(
        self,
        cov_result: CovarianceResult,
        target_return: float,
    ) -> OptimizationResult:
        """
        Find minimum variance portfolio for target return.

        Minimize: w'Σw
        Subject to: Σw = 1, μ'w = target_return

        Args:
            cov_result: Covariance calculation result
            target_return: Target annualized return

        Returns:
            OptimizationResult with optimal weights
        """
        n_assets = len(cov_result.symbols)
        target_daily = target_return / 252  # Convert to daily

        # Objective: portfolio variance
        def objective(weights: np.ndarray) -> float:
            return float(weights @ cov_result.covariance_matrix @ weights)

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # Weights sum to 1
            {
                "type": "eq",
                "fun": lambda w: float(w @ cov_result.means) - target_daily,
            },  # Target return
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Initial guess
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        # Extract results
        weights = result.x
        expected_return = float(weights @ cov_result.means)
        expected_var = float(weights @ cov_result.covariance_matrix @ weights)
        expected_risk = np.sqrt(expected_var)

        # Annualize
        annual_return = expected_return * 252
        annual_risk = expected_risk * np.sqrt(252)
        sharpe = (annual_return - self._risk_free_rate) / annual_risk

        return OptimizationResult(
            weights=weights,
            expected_return=annual_return,
            expected_risk=annual_risk,
            sharpe_ratio=sharpe,
            symbols=cov_result.symbols,
            converged=result.success,
            message=result.message,
        )

    def compute_efficient_frontier(
        self,
        cov_result: CovarianceResult,
        n_points: int = 20,
    ) -> EfficientFrontier:
        """
        Compute efficient frontier.

        Calculates optimal portfolios at various return levels.

        Args:
            cov_result: Covariance calculation result
            n_points: Number of points on frontier

        Returns:
            EfficientFrontier with return/risk points
        """
        # Get return bounds
        min_var_result = self.minimize_variance(cov_result)
        min_return = min_var_result.expected_return

        # Find max return (max weight in highest-return asset)
        max_return_idx = np.argmax(cov_result.means)
        max_return = float(cov_result.means[max_return_idx]) * 252

        # Generate target returns
        target_returns = np.linspace(min_return, max_return, n_points)

        returns = []
        risks = []
        weights_list = []
        sharpe_ratios = []

        for target in target_returns:
            try:
                result = self.target_return(cov_result, target)
                if result.converged:
                    returns.append(result.expected_return)
                    risks.append(result.expected_risk)
                    weights_list.append(result.weights)
                    sharpe_ratios.append(result.sharpe_ratio)
            except Exception:
                # Skip infeasible targets
                pass

        return EfficientFrontier(
            returns=np.array(returns),
            risks=np.array(risks),
            weights_list=weights_list,
            sharpe_ratios=np.array(sharpe_ratios),
        )

    def get_global_minimum_variance(
        self,
        cov_result: CovarianceResult,
    ) -> OptimizationResult:
        """
        Get global minimum variance portfolio (no constraints).

        Analytical solution: w = Σ^(-1) * 1 / (1' * Σ^(-1) * 1)

        Args:
            cov_result: Covariance calculation result

        Returns:
            OptimizationResult with GMV weights
        """
        cov_matrix = cov_result.covariance_matrix
        n_assets = len(cov_result.symbols)

        # Inverse covariance
        inv_cov = np.linalg.inv(cov_matrix)

        # GMV weights (analytical)
        ones = np.ones(n_assets)
        weights = inv_cov @ ones / (ones @ inv_cov @ ones)

        # Calculate metrics
        expected_return = float(weights @ cov_result.means)
        expected_var = float(weights @ cov_result.covariance_matrix @ weights)
        expected_risk = np.sqrt(expected_var)

        # Annualize
        annual_return = expected_return * 252
        annual_risk = expected_risk * np.sqrt(252)
        sharpe = (annual_return - self._risk_free_rate) / annual_risk

        return OptimizationResult(
            weights=weights,
            expected_return=annual_return,
            expected_risk=annual_risk,
            sharpe_ratio=sharpe,
            symbols=cov_result.symbols,
            converged=True,
            message="Analytical solution",
        )
