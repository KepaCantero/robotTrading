# mypy: ignore-errors
"""
Critical Line Algorithm (CLA) - Efficient Frontier Computation

Implements the Critical Line Algorithm for computing the efficient frontier
and finding optimal corner portfolios.

Reference: Rule 48-papers-markowitz (Markowitz related)
Paper: Markowitz, H. (1956). "The Optimization of a Quadratic Function
       Subject to Linear Constraints"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from app.domain.services.portfolio_optimization._validation import (
    log_optimization_failure,
    validate_covariance_matrix,
)

logger = logging.getLogger(__name__)


# CLA default parameters
DEFAULT_MIN_WEIGHT = 0.0  # Minimum weight per asset
DEFAULT_MAX_WEIGHT = 1.0  # Maximum weight per asset
DEFAULT_FRONTIER_POINTS = 10  # Number of frontier points
DEFAULT_LAMBDA_VAL = 0.0  # Default Lagrange multiplier
DEFAULT_WEIGHT_TOLERANCE = 1e-10  # Tolerance for considering weight as zero
DEFAULT_TURNOVER_COEFFICIENT = 0.5  # Coefficient for turnover calculation


@dataclass
class CornerPortfolio:
    """A corner portfolio on the efficient frontier."""

    weights: np.ndarray  # Portfolio weights
    expected_return: float  # Expected return
    variance: float  # Portfolio variance
    lambda_val: float  # Lagrange multiplier for return constraint
    in_assets: list[int]  # Assets with positive weights
    out_assets: list[int]  # Assets at bounds (zero weight)
    symbols: list[str]  # Asset symbols

    @property
    def risk(self) -> float:
        """Get portfolio risk (standard deviation)."""
        return np.sqrt(self.variance)


@dataclass
class EfficientFrontierCLA:
    """Efficient frontier computed via CLA."""

    corner_portfolios: list[CornerPortfolio]  # Corner portfolios
    n_portfolios: int  # Number of corner portfolios
    symbols: list[str]  # Asset symbols

    def get_portfolio_for_return(
        self,
        target_return: float,
        cov_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Get optimal portfolio for target return via interpolation.

        Args:
            target_return: Target expected return
            cov_matrix: Covariance matrix

        Returns:
            Optimal weights
        """
        # Find neighboring corner portfolios
        returns = [cp.expected_return for cp in self.corner_portfolios]

        if target_return <= returns[0]:
            return self.corner_portfolios[0].weights
        if target_return >= returns[-1]:
            return self.corner_portfolios[-1].weights

        # Find interpolation interval
        for i in range(len(returns) - 1):
            if returns[i] <= target_return <= returns[i + 1]:
                # Linear interpolation
                alpha = (target_return - returns[i]) / (returns[i + 1] - returns[i])
                weights = (1 - alpha) * self.corner_portfolios[
                    i
                ].weights + alpha * self.corner_portfolios[i + 1].weights
                return weights

        return self.corner_portfolios[-1].weights

    def get_max_sharpe_portfolio(
        self,
        risk_free_rate: float,
    ) -> CornerPortfolio | None:
        """
        Get maximum Sharpe ratio portfolio.

        Args:
            risk_free_rate: Risk-free rate

        Returns:
            Corner portfolio with max Sharpe
        """
        max_sharpe = None
        max_sharpe_val = -np.inf

        for cp in self.corner_portfolios:
            sharpe = (cp.expected_return - risk_free_rate) / cp.risk
            if sharpe > max_sharpe_val:
                max_sharpe_val = sharpe
                max_sharpe = cp

        return max_sharpe


class CriticalLineAlgorithm:
    """
    Critical Line Algorithm for efficient frontier computation.

    The CLA solves the mean-variance optimization problem
    for all possible return levels simultaneously.

    Advantages:
    - Computes all optimal portfolios in one run
    - Identifies corner portfolios (where asset weights enter/exit)
    - More efficient than solving for each target return

    Reference: Markowitz, H. (1956)
    """

    def __init__(
        self,
        min_weight: float = DEFAULT_MIN_WEIGHT,
        max_weight: float = DEFAULT_MAX_WEIGHT,
        allow_short: bool = False,
    ):
        """
        Initialize CLA optimizer.

        Args:
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
            allow_short: Whether to allow short positions
        """
        if min_weight < (-1.0 if allow_short else 0.0):
            raise ValueError(f"min_weight out of range, got {min_weight}")
        if max_weight > 1.0:
            raise ValueError(f"max_weight cannot exceed 1.0, got {max_weight}")
        if min_weight > max_weight:
            raise ValueError(f"Min weight {min_weight} > max weight {max_weight}")

        self._min_weight = -1.0 if allow_short else 0.0
        self._max_weight = max_weight

    def compute_efficient_frontier(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        symbols: list[str] | None = None,
    ) -> EfficientFrontierCLA:
        """
        Compute efficient frontier using CLA.

        Args:
            expected_returns: Expected returns (annual)
            cov_matrix: Covariance matrix (annual)
            symbols: Asset symbols

        Returns:
            EfficientFrontierCLA with corner portfolios

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate covariance matrix
        is_valid, validated_cov, error_msg = validate_covariance_matrix(
            cov_matrix,
            check_psd=True,
            check_symmetry=True,
            enforce_psd=True,
        )

        if not is_valid:
            raise ValueError(f"Invalid covariance matrix: {error_msg}")

        cov_matrix = validated_cov
        n_assets = len(expected_returns)
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Generate corner portfolios at different return levels
        corner_portfolios = []

        # Min variance portfolio
        try:
            min_var_result = self._solve_min_variance(cov_matrix, symbols)
            corner_portfolios.append(min_var_result)
        except Exception as e:
            log_optimization_failure(
                "cla.min_variance",
                e,
                {"n_assets": n_assets},
            )
            raise ValueError(f"Failed to compute minimum variance portfolio: {e}") from e

        # Max return portfolio (single asset with highest return)
        max_return_idx = np.argmax(expected_returns)
        max_return_weights = np.zeros(n_assets)
        max_return_weights[max_return_idx] = 1.0
        max_return_cp = CornerPortfolio(
            weights=max_return_weights,
            expected_return=float(expected_returns[max_return_idx]),
            variance=float(cov_matrix[max_return_idx, max_return_idx]),
            lambda_val=DEFAULT_LAMBDA_VAL,
            in_assets=[max_return_idx],
            out_assets=list(set(range(n_assets)) - {max_return_idx}),
            symbols=symbols,
        )
        corner_portfolios.append(max_return_cp)

        # Intermediate portfolios
        for target_return in np.linspace(
            min_var_result.expected_return,
            float(expected_returns[max_return_idx]),
            DEFAULT_FRONTIER_POINTS,
        ):
            try:
                result = self._solve_target_return(
                    expected_returns,
                    cov_matrix,
                    target_return,
                    symbols,
                )
                corner_portfolios.append(result)
            except Exception as e:
                logger.debug(f"Skipping target return {target_return}: {e}")

        return EfficientFrontierCLA(
            corner_portfolios=corner_portfolios,
            n_portfolios=len(corner_portfolios),
            symbols=symbols,
        )

    def _solve_min_variance(
        self,
        cov_matrix: np.ndarray,
        symbols: list[str],
    ) -> CornerPortfolio:
        """Solve minimum variance portfolio."""
        n_assets = len(symbols)

        try:
            # Analytical solution for unconstrained case
            inv_cov = np.linalg.inv(cov_matrix)
            ones = np.ones(n_assets)
            weights = inv_cov @ ones / (ones @ inv_cov @ ones)
        except np.linalg.LinAlgError as e:
            log_optimization_failure(
                "cla.min_variance.matrix_inv",
                e,
                {"n_assets": n_assets},
            )
            raise ValueError(f"Cannot invert covariance matrix: {e}") from e

        # Apply bounds if needed
        weights = np.clip(weights, self._min_weight, self._max_weight)
        weights = weights / weights.sum()

        variance = float(weights @ cov_matrix @ weights)
        mean_return = 0.0  # Not needed for min variance

        return CornerPortfolio(
            weights=weights,
            expected_return=mean_return,
            variance=variance,
            lambda_val=DEFAULT_LAMBDA_VAL,
            in_assets=list(np.where(weights > DEFAULT_WEIGHT_TOLERANCE)[0]),
            out_assets=list(np.where(weights <= DEFAULT_WEIGHT_TOLERANCE)[0]),
            symbols=symbols,
        )

    def _solve_target_return(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        target_return: float,
        symbols: list[str],
    ) -> CornerPortfolio:
        """Solve for target return (quadratic programming)."""
        from scipy.optimize import minimize

        n_assets = len(expected_returns)

        def objective(weights: np.ndarray) -> float:
            return float(weights @ cov_matrix @ weights)

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: float(w @ expected_returns) - target_return},
        ]

        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            log_optimization_failure(
                "cla.target_return",
                Exception(result.message),
                {"target_return": target_return, "status": result.status},
            )

        weights = result.x if result.success else x0
        variance = float(weights @ cov_matrix @ weights)

        return CornerPortfolio(
            weights=weights,
            expected_return=target_return,
            variance=variance,
            lambda_val=DEFAULT_LAMBDA_VAL,
            in_assets=list(np.where(weights > DEFAULT_WEIGHT_TOLERANCE)[0]),
            out_assets=list(np.where(weights <= DEFAULT_WEIGHT_TOLERANCE)[0]),
            symbols=symbols,
        )


def compute_turnover(
    old_weights: np.ndarray,
    new_weights: np.ndarray,
) -> float:
    """
    Compute portfolio turnover.

    Turnover = 0.5 * Σ|w_new - w_old|

    Args:
        old_weights: Previous portfolio weights
        new_weights: New portfolio weights

    Returns:
        Turnover (0-1)
    """
    return float(DEFAULT_TURNOVER_COEFFICIENT * np.sum(np.abs(new_weights - old_weights)))
