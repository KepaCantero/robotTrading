"""Markowitz Mean-Variance Portfolio Optimization Implementation.

This module implements the Modern Portfolio Theory (MPT) by Harry Markowitz (1952),
providing mean-variance optimization for portfolio construction.

Key Features:
- Covariance matrix calculation with 252-day lookback (Rule 66)
- Mean-Variance Optimization (Rule 67)
- Long-only constraints (Rule 68): 0 <= weight <= 1
- Sum constraint validation (Rule 69): sum(weights) = 1.0
- Diversification enforcement (Rule 70): Max 20% per asset
- Efficient frontier calculation (Rule 71): 20+ points
- Max Sharpe Portfolio (Rule 72): Default optimization target
- L2 Regularization (Rule 73): gamma=0.01
- Ledoit-Wolf shrinkage (Rule 74): Robust covariance estimation

Reference:
    Markowitz, H. (1952). "Portfolio Selection". Journal of Finance.
    https://doi.org/10.1111/j.1540-6261.1952.tb01525.x
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize

from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Available optimization methods for MVO."""

    MAX_SHARPE = "max_sharpe"
    MIN_VARIANCE = "min_variance"
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"


class ShrinkageMethod(str, Enum):
    """Available shrinkage methods for covariance estimation."""

    LEDOIT_WOLF = "ledoit_wolf"
    ORACLE_APPROXIMATING = "oracle_approximating"
    SAMPLE = "sample"


@dataclass(frozen=True)
class OptimizationResult:
    """Result of portfolio optimization."""

    weights: NDArray[np.float64]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    success: bool
    message: str
    method: OptimizationMethod

    @property
    def weights_dict(self) -> dict[str, float]:
        """Convert weights array to dictionary format."""
        return {f"asset_{i}": float(w) for i, w in enumerate(self.weights)}


@dataclass(frozen=True)
class EfficientFrontierPoint:
    """Single point on the efficient frontier."""

    weights: NDArray[np.float64]
    portfolio_return: float
    portfolio_risk: float
    sharpe_ratio: float


@dataclass(frozen=True)
class EfficientFrontier:
    """Efficient frontier with multiple optimal portfolios."""

    points: list[EfficientFrontierPoint]
    max_sharpe_index: int
    min_variance_index: int

    @property
    def max_sharpe_portfolio(self) -> EfficientFrontierPoint:
        """Get the maximum Sharpe ratio portfolio."""
        return self.points[self.max_sharpe_index]

    @property
    def min_variance_portfolio(self) -> EfficientFrontierPoint:
        """Get the minimum variance portfolio."""
        return self.points[self.min_variance_index]

    def to_arrays(self) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Convert frontier points to arrays for plotting."""
        returns = np.array([p.portfolio_return for p in self.points])
        risks = np.array([p.portfolio_risk for p in self.points])
        sharpes = np.array([p.sharpe_ratio for p in self.points])
        return returns, risks, sharpes


class InputValidationError(ValueError):
    """Raised when input validation fails."""


class OptimizationError(RuntimeError):
    """Raised when optimization fails."""


class MeanVarianceOptimizer:
    """Markowitz Mean-Variance Portfolio Optimization (1952).

    This class implements Modern Portfolio Theory for optimal portfolio construction.
    It follows SOLID principles by separating concerns:
    - Covariance estimation (separate shrinkage methods)
    - Constraint validation (separate validators)
    - Optimization algorithms (separate methods)

    Attributes:
        lookback_days: Number of days for covariance calculation (default: 252)
        max_position: Maximum weight per asset (default: 0.20 for diversification)
        risk_free_rate: Risk-free rate for Sharpe ratio calculation (default: 0.02)
        regularization_gamma: L2 regularization parameter (default: 0.01)
        sum_tolerance: Tolerance for sum constraint validation (default: 1e-6)

    Example:
        >>> optimizer = MeanVarianceOptimizer()
        >>> returns = np.random.randn(252, 10) * 0.01  # 252 days, 10 assets
        >>> result = optimizer.optimize(returns)
        >>> print(f"Weights: {result.weights}")
        >>> print(f"Expected Sharpe: {result.sharpe_ratio:.2f}")
    """

    __slots__ = (
        "_lookback_days",
        "_max_position",
        "_regularization_gamma",
        "_risk_free_rate",
        "_sum_tolerance",
    )

    def __init__(
        self,
        lookback_days: int = 252,
        max_position: float = 0.20,
        risk_free_rate: float | None = None,
        regularization_gamma: float = 0.01,
        sum_tolerance: float = 1e-6,
    ) -> None:
        """Initialize the Mean-Variance Optimizer.

        Args:
            lookback_days: Minimum days for covariance calculation (Rule 66).
                Must be >= 252 for statistical significance.
            max_position: Maximum weight per asset (Rule 70).
                Default 0.20 forces diversification.
            risk_free_rate: Annual risk-free rate for Sharpe calculation (Rule 72).
                Default: from get_config().backtesting.default_risk_free_rate.
            regularization_gamma: L2 regularization strength (Rule 73).
                Default 0.01 prevents corner solutions.
            sum_tolerance: Tolerance for sum constraint validation (Rule 69).
                Default 1e-6 for numerical precision.

        Raises:
            ValueError: If parameters are out of valid range.
        """
        # Use CentralizedConfig default if not provided
        if risk_free_rate is None:
            risk_free_rate = float(get_config().backtesting.default_risk_free_rate)

        self._validate_initialization_params(
            lookback_days, max_position, risk_free_rate, regularization_gamma, sum_tolerance
        )

        self._lookback_days = lookback_days
        self._max_position = max_position
        self._risk_free_rate = risk_free_rate
        self._regularization_gamma = regularization_gamma
        self._sum_tolerance = sum_tolerance

        logger.info(
            f"Initialized MeanVarianceOptimizer: lookback={lookback_days}, "
            f"max_position={max_position:.2%}, rf_rate={risk_free_rate:.2%}"
        )

    def _validate_initialization_params(
        self,
        lookback_days: int,
        max_position: float,
        risk_free_rate: float,
        regularization_gamma: float,
        sum_tolerance: float,
    ) -> None:
        """Validate initialization parameters."""
        if lookback_days < 252:
            raise ValueError(
                f"lookback_days must be >= 252 (1 year), got {lookback_days}. "
                "Rule 66: Covariance requires minimum 252 days for statistical significance."
            )
        if not 0.0 < max_position <= 1.0:
            raise ValueError(
                f"max_position must be in (0, 1], got {max_position}. "
                "Rule 70: Max position must be positive and not exceed 100%."
            )
        if not 0.0 <= risk_free_rate <= 1.0:
            raise ValueError(
                f"risk_free_rate must be in [0, 1], got {risk_free_rate}. "
                "Risk-free rate should be an annual decimal rate."
            )
        if regularization_gamma < 0.0:
            raise ValueError(
                f"regularization_gamma must be >= 0, got {regularization_gamma}. "
                "Rule 73: L2 regularization must be non-negative."
            )
        if not 0.0 < sum_tolerance < 1e-3:
            raise ValueError(
                f"sum_tolerance must be in (0, 1e-3), got {sum_tolerance}. "
                "Rule 69: Sum constraint tolerance requires reasonable precision."
            )

    @property
    def lookback_days(self) -> int:
        """Get the lookback period for covariance calculation."""
        return self._lookback_days

    @property
    def max_position(self) -> float:
        """Get the maximum position size constraint."""
        return self._max_position

    @property
    def risk_free_rate(self) -> float:
        """Get the risk-free rate."""
        return self._risk_free_rate

    @property
    def regularization_gamma(self) -> float:
        """Get the L2 regularization parameter."""
        return self._regularization_gamma

    def sanitize_inputs(
        self,
        returns: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Validate and sanitize input returns data (Rule 15).

        Args:
            returns: Returns array of shape (T, N) where T is time periods, N is assets.
                T must be >= lookback_days.

        Returns:
            Cleaned returns array with NaN and zero-volatility assets removed.

        Raises:
            InputValidationError: If data is insufficient or invalid.
        """
        if returns.ndim != 2:
            raise InputValidationError(f"returns must be 2-dimensional, got shape {returns.shape}")

        n_periods, n_assets = returns.shape

        if n_periods < self._lookback_days:
            raise InputValidationError(
                f"Insufficient data: {n_periods} periods < {self._lookback_days} required. "
                f"Rule 66: Covariance calculation requires minimum {self._lookback_days} days."
            )

        if n_assets < 2:
            raise InputValidationError(
                f"Insufficient assets: {n_assets} < 2 required. "
                "Need at least 2 assets for portfolio optimization."
            )

        # Check for NaN values
        nan_mask = np.isnan(returns).any(axis=0)
        n_nan_assets = nan_mask.sum()

        if n_nan_assets > 0:
            logger.warning(
                f"Rule 15: Dropping {n_nan_assets} assets with NaN values "
                f"({n_nan_assets / n_assets:.1%} of universe)"
            )
            returns = returns[:, ~nan_mask]

        # Check for zero/near-zero volatility
        volatilities = returns.std(axis=0)
        zero_vol_mask = volatilities < 1e-10
        n_zero_vol = zero_vol_mask.sum()

        if n_zero_vol > 0:
            logger.warning(
                f"Rule 15: Dropping {n_zero_vol} assets with ~0 volatility "
                f"({n_zero_vol / n_assets:.1%} of universe)"
            )
            returns = returns[:, ~zero_vol_mask]

        # Validate sufficient assets remain
        if returns.shape[1] < 2:
            raise InputValidationError(
                f"Insufficient assets after sanitization: {returns.shape[1]} < 2. "
                "Rule 15: Need at least 2 valid assets for optimization."
            )

        logger.info(
            f"Input sanitization complete: {n_assets} -> {returns.shape[1]} assets, "
            f"{n_periods} periods"
        )

        return returns

    def calculate_expected_returns(
        self,
        returns: NDArray[np.float64],
        annualize: bool = True,
    ) -> NDArray[np.float64]:
        """Calculate expected returns from historical data.

        Args:
            returns: Returns array of shape (T, N).
            annualize: Whether to annualize returns (default: True).

        Returns:
            Expected returns array of shape (N,).
        """
        expected_returns = returns.mean(axis=0)

        if annualize:
            # Assuming daily returns, annualize by 252 trading days
            expected_returns = expected_returns * 252

        return expected_returns

    def calculate_covariance_matrix(
        self,
        returns: NDArray[np.float64],
        use_shrinkage: bool = True,
        shrinkage_method: ShrinkageMethod = ShrinkageMethod.LEDOIT_WOLF,
    ) -> NDArray[np.float64]:
        """Calculate covariance matrix with 252-day lookback (Rule 66).

        Uses the most recent lookback_days periods for calculation.
        Applies Ledoit-Wolf shrinkage by default for robustness (Rule 74).

        Args:
            returns: Returns array of shape (T, N) where T >= lookback_days.
            use_shrinkage: Whether to apply shrinkage estimation (default: True).
            shrinkage_method: Shrinkage method to use (default: LEDOIT_WOLF).

        Returns:
            Covariance matrix of shape (N, N), annualized.

        Raises:
            InputValidationError: If returns data is invalid.
            OptimizationError: If covariance calculation fails.
        """
        returns = self.sanitize_inputs(returns)

        # Use only the most recent lookback_days (Rule 66)
        recent_returns = returns[-self._lookback_days :, :]

        if use_shrinkage:
            cov_matrix = self._shrink_covariance_matrix(recent_returns, shrinkage_method)
        else:
            # Sample covariance (Rule 1 - fallback)
            cov_matrix = np.asarray(
                np.cov(recent_returns, rowvar=False) * 252, dtype=np.float64
            )  # Annualize

        # Validate covariance matrix is positive semi-definite
        if not self._is_positive_semi_definite(cov_matrix):
            logger.warning(
                "Covariance matrix is not positive semi-definite. Applying nearest PSD correction."
            )
            cov_matrix = self._nearest_positive_semi_definite(cov_matrix)

        logger.info(
            f"Covariance matrix: {cov_matrix.shape[0]} assets, "
            f"{self._lookback_days} days lookback, "
            f"shrinkage={use_shrinkage}"
        )

        return cov_matrix

    def _shrink_covariance_matrix(
        self,
        returns: NDArray[np.float64],
        method: ShrinkageMethod = ShrinkageMethod.LEDOIT_WOLF,
    ) -> NDArray[np.float64]:
        """Apply shrinkage to covariance matrix (Rule 74 - Ledoit-Wolf).

        Shrinkage reduces estimation error by combining sample covariance
        with a structured estimator (constant correlation).

        Args:
            returns: Returns array of shape (T, N).
            method: Shrinkage method (default: LEDOIT_WOLF).

        Returns:
            Shrunk covariance matrix, annualized.
        """
        try:
            if method == ShrinkageMethod.LEDOIT_WOLF:
                from sklearn.covariance import LedoitWolf

                lw = LedoitWolf()
                shrunk_cov = lw.fit(returns).covariance_ * 252  # Annualize
                shrinkage = lw.shrinkage_

                logger.info(f"Rule 74: Ledoit-Wolf shrinkage applied: {shrinkage:.2%}")

            elif method == ShrinkageMethod.ORACLE_APPROXIMATING:
                from sklearn.covariance import OAS

                oas = OAS()
                shrunk_cov = oas.fit(returns).covariance_ * 252
                shrinkage = oas.shrinkage_

                logger.info(f"Rule 74: OAS shrinkage applied: {shrinkage:.2%}")

            else:
                # Sample covariance (no shrinkage)
                shrunk_cov = np.cov(returns, rowvar=False) * 252
                logger.warning(
                    "Rule 74: Using sample covariance (no shrinkage). "
                    "Not recommended for noisy data."
                )

            return shrunk_cov

        except ImportError as e:
            logger.error(
                f"scikit-learn not available for shrinkage: {e}. "
                "Falling back to sample covariance.",
                exc_info=True,
            )
            return np.cov(returns, rowvar=False) * 252

    @staticmethod
    def _is_positive_semi_definite(
        matrix: NDArray[np.float64],
    ) -> bool:
        """Check if matrix is positive semi-definite."""
        try:
            np.linalg.cholesky(matrix)
            return True
        except np.linalg.LinAlgError:
            return False

    @staticmethod
    def _nearest_positive_semi_definite(
        matrix: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Find nearest positive semi-definite matrix using Higham's method."""
        # Symmetrize
        sym_matrix = (matrix + matrix.T) / 2

        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(sym_matrix)

        # Clip negative eigenvalues
        eigenvalues = np.maximum(eigenvalues, 0)

        # Reconstruct
        return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    def validate_sum_constraint(
        self,
        weights: NDArray[np.float64],
    ) -> bool:
        """Validate that sum of weights equals 1.0 (Rule 69).

        Args:
            weights: Portfolio weights array of shape (N,).

        Returns:
            True if sum constraint is satisfied within tolerance.
        """
        if weights.size == 0:
            logger.error("Rule 69: Cannot validate empty weights array")
            return False

        sum_weights = float(np.sum(weights))
        deviation = abs(sum_weights - 1.0)

        if deviation > self._sum_tolerance:
            logger.error(
                f"Rule 69: Sum constraint violated: {sum_weights:.6f} ≠ 1.0 "
                f"(deviation={deviation:.2e} > tolerance={self._sum_tolerance:.2e})"
            )
            return False

        logger.debug(f"Rule 69: Sum constraint validated: sum={sum_weights:.6f}")
        return True

    def apply_long_only_constraint(
        self,
        weights: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Force long-only constraint: 0 <= weight <= 1 (Rule 68).

        Args:
            weights: Portfolio weights array of shape (N,).

        Returns:
            Constrained weights array, normalized to sum to 1.0.
        """
        # Clip to [0, 1] (Rule 68)
        constrained_weights = np.clip(weights, 0.0, 1.0)

        # Count clipped assets
        n_clipped = (weights != constrained_weights).sum()

        if n_clipped > 0:
            logger.info(f"Rule 68: Long-only constraint clipped {n_clipped} positions")

        # Renormalize to ensure sum = 1 (Rule 69)
        constrained_weights = constrained_weights / constrained_weights.sum()

        return constrained_weights

    def apply_diversification_constraint(
        self,
        weights: NDArray[np.float64],
        max_weight: float | None = None,
    ) -> NDArray[np.float64]:
        """Limit concentration: max 20% per asset (Rule 70).

        Iteratively redistributes weight from assets exceeding max_weight
        to assets below max_weight until convergence.

        Args:
            weights: Portfolio weights array of shape (N,).
            max_weight: Maximum weight per asset (default: use self.max_position).

        Returns:
            Constrained weights with redistribution.
        """
        if max_weight is None:
            max_weight = self._max_position

        # Check for violations
        violations = weights > max_weight
        n_violations = violations.sum()

        if n_violations == 0:
            return weights

        logger.warning(
            f"Rule 70: {n_violations} assets exceed {max_weight:.0%} limit. "
            "Capping and redistributing."
        )

        # Start with copy of weights
        constrained_weights = weights.copy()
        max_iterations = 100

        for _ in range(max_iterations):
            # Cap weights at max_weight
            violations = constrained_weights > max_weight
            n_violations = violations.sum()

            if n_violations == 0:
                break

            # Cap violating weights
            constrained_weights[violations] = max_weight

            # Calculate excess to redistribute
            current_sum = constrained_weights.sum()
            excess = 1.0 - current_sum

            # Find assets below max that can receive excess
            below_max = constrained_weights < max_weight
            n_below_max = below_max.sum()

            if n_below_max == 0:
                # All at max, equal distribution
                constrained_weights = np.full_like(weights, max_weight)
                break

            if excess > 0:
                # Redistribute excess to assets below max
                # Distribute proportionally to current headroom
                headroom = max_weight - constrained_weights[below_max]
                total_headroom = headroom.sum()

                if total_headroom > 0:
                    constrained_weights[below_max] += excess * (headroom / total_headroom)
                else:
                    # Should not happen, but handle gracefully
                    constrained_weights[below_max] += excess / n_below_max
            else:
                # No excess, we're done
                break

        # Final normalization to ensure sum = 1
        constrained_weights = constrained_weights / constrained_weights.sum()

        logger.info(
            f"Rule 70: Weights capped at {max_weight:.0%} and redistributed, "
            f"max_weight={constrained_weights.max():.2%}"
        )

        return constrained_weights

    def max_sharpe_portfolio(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        risk_free_rate: float | None = None,
    ) -> OptimizationResult:
        """Calculate maximum Sharpe ratio portfolio (Rule 72).

        The tangency portfolio maximizes: (mu @ w - rf) / sqrt(w @ cov @ w)
        This is the optimal portfolio for all rational investors per CAPM.

        Args:
            expected_returns: Expected returns array of shape (N,).
            cov_matrix: Covariance matrix of shape (N, N).
            risk_free_rate: Risk-free rate (default: use self.risk_free_rate).

        Returns:
            OptimizationResult with optimal weights for maximum Sharpe ratio.
        """
        if risk_free_rate is None:
            risk_free_rate = self._risk_free_rate

        n_assets = len(expected_returns)

        # Negative Sharpe ratio (minimize negative = maximize positive)
        def negative_sharpe(weights: NDArray[np.float64]) -> float:
            """Calculate negative Sharpe ratio for minimization."""
            portfolio_return = float(weights @ expected_returns)
            portfolio_variance = float(weights @ cov_matrix @ weights)
            portfolio_risk: float = float(np.sqrt(portfolio_variance))

            if portfolio_risk < 1e-10:
                return -np.inf  # Penalize zero risk portfolios

            excess_return = portfolio_return - risk_free_rate
            return float(-(excess_return / portfolio_risk))

        # Constraints: sum(w) = 1 (Rule 69)
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        # Bounds: 0 <= w[i] <= max_position (Rules 68, 70)
        bounds = [(0.0, self._max_position) for _ in range(n_assets)]

        # Initial guess: equal weight
        x0 = np.ones(n_assets) / n_assets

        # Optimize using SLSQP
        result = minimize(
            negative_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if not result.success:
            logger.error(f"Rule 72: Max Sharpe optimization failed: {result.message}")
            return OptimizationResult(
                weights=x0,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=-np.inf,
                success=False,
                message=result.message,
                method=OptimizationMethod.MAX_SHARPE,
            )

        weights = result.x

        # Calculate portfolio metrics
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - risk_free_rate) / expected_risk if expected_risk > 0 else -np.inf
        )

        logger.info(
            f"Rule 72: Max Sharpe Portfolio - Return={expected_return:.2%}, "
            f"Risk={expected_risk:.2%}, Sharpe={sharpe_ratio:.2f}"
        )

        return OptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Optimization successful",
            method=OptimizationMethod.MAX_SHARPE,
        )

    def min_variance_portfolio(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> OptimizationResult:
        """Calculate minimum variance portfolio.

        Minimizes portfolio variance: w @ cov @ w
        Subject to: sum(w) = 1, 0 <= w[i] <= max_position

        Args:
            expected_returns: Expected returns array of shape (N,).
            cov_matrix: Covariance matrix of shape (N, N).

        Returns:
            OptimizationResult with minimum variance weights.
        """
        n_assets = len(expected_returns)

        # Portfolio variance
        def portfolio_variance(weights: NDArray[np.float64]) -> float:
            return float(weights @ cov_matrix @ weights)

        # Constraints: sum(w) = 1 (Rule 69)
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        # Bounds: 0 <= w[i] <= max_position (Rules 68, 70)
        bounds = [(0.0, self._max_position) for _ in range(n_assets)]

        # Initial guess: equal weight
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if not result.success:
            logger.error(f"Min variance optimization failed: {result.message}")
            return OptimizationResult(
                weights=x0,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=-np.inf,
                success=False,
                message=result.message,
                method=OptimizationMethod.MIN_VARIANCE,
            )

        weights = result.x

        # Calculate portfolio metrics
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else -np.inf
        )

        logger.info(
            f"Min Variance Portfolio - Return={expected_return:.2%}, "
            f"Risk={expected_risk:.2%}, Sharpe={sharpe_ratio:.2f}"
        )

        return OptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Optimization successful",
            method=OptimizationMethod.MIN_VARIANCE,
        )

    def regularized_mvo(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        gamma: float | None = None,
    ) -> OptimizationResult:
        """Mean-Variance Optimization with L2 regularization (Rule 73).

        Adds L2 penalty to prevent corner solutions: variance + gamma * ||w||^2
        Regularization discourages extreme weights and improves stability.

        Args:
            expected_returns: Expected returns array of shape (N,).
            cov_matrix: Covariance matrix of shape (N, N).
            gamma: L2 regularization parameter (default: self.regularization_gamma).

        Returns:
            OptimizationResult with regularized optimal weights.
        """
        if gamma is None:
            gamma = self._regularization_gamma

        n_assets = len(expected_returns)

        # Regularized variance: variance + gamma * L2_penalty
        def regularized_variance(weights: NDArray[np.float64]) -> float:
            variance = float(weights @ cov_matrix @ weights)
            penalty = gamma * float(np.sum(weights**2))
            return variance + penalty

        # Constraints: sum(w) = 1 (Rule 69)
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        # Bounds: 0 <= w[i] <= max_position (Rules 68, 70)
        bounds = [(0.0, self._max_position) for _ in range(n_assets)]

        # Initial guess: equal weight
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            regularized_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if not result.success:
            logger.error(f"Rule 73: Regularized MVO failed: {result.message}")
            return OptimizationResult(
                weights=x0,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=-np.inf,
                success=False,
                message=result.message,
                method=OptimizationMethod.MIN_VARIANCE,
            )

        weights = result.x

        # Calculate portfolio metrics (without penalty)
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else -np.inf
        )

        logger.info(
            f"Rule 73: Regularized MVO (gamma={gamma:.4f}) - "
            f"Return={expected_return:.2%}, Risk={expected_risk:.2%}, "
            f"Sharpe={sharpe_ratio:.2f}, max_weight={weights.max():.2%}"
        )

        return OptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Regularized optimization successful",
            method=OptimizationMethod.MIN_VARIANCE,
        )

    def calculate_efficient_frontier(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        n_points: int = 20,
    ) -> EfficientFrontier:
        """Calculate efficient frontier with 20+ points (Rule 71).

        The efficient frontier represents the optimal risk-return trade-off.
        Each point minimizes variance for a given return level.

        Args:
            expected_returns: Expected returns array of shape (N,).
            cov_matrix: Covariance matrix of shape (N, N).
            n_points: Number of frontier points (default: 20 per Rule 71).

        Returns:
            EfficientFrontier with all frontier points and optimal portfolios.

        Raises:
            OptimizationError: If unable to calculate any frontier points.
        """
        n_assets = len(expected_returns)

        # Calculate feasible return range with constraints
        # With max_position constraint, the feasible range is narrower
        # Get assets sorted by return
        sorted_indices = np.argsort(expected_returns)
        sorted_returns = expected_returns[sorted_indices]

        # Calculate min feasible return (use lowest returning assets)
        n_assets_min = min(5, n_assets)  # Use at least 5 assets
        min_feasible_return = sorted_returns[:n_assets_min].mean()

        # Calculate max feasible return (use highest returning assets)
        n_assets_max = min(5, n_assets)
        max_feasible_return = sorted_returns[-n_assets_max:].mean()

        # Add some buffer
        return_range = max_feasible_return - min_feasible_return
        min_return = min_feasible_return - 0.1 * return_range
        max_return = max_feasible_return + 0.1 * return_range

        # Generate target returns
        target_returns = np.linspace(min_return, max_return, n_points)

        points: list[EfficientFrontierPoint] = []

        for target_return in target_returns:
            # Optimize for this target return
            result = self._optimize_for_target_return(expected_returns, cov_matrix, target_return)

            if result is not None:
                points.append(result)

        # If still no points, try without return constraint (just min variance)
        if not points:
            logger.warning(
                "Rule 71: No frontier points with return constraint, "
                "falling back to variance-only optimization"
            )
            # Try just min variance portfolio
            min_var_result = self.min_variance_portfolio(expected_returns, cov_matrix)
            if min_var_result.success:
                points.append(
                    EfficientFrontierPoint(
                        weights=min_var_result.weights,
                        portfolio_return=min_var_result.expected_return,
                        portfolio_risk=min_var_result.expected_risk,
                        sharpe_ratio=min_var_result.sharpe_ratio,
                    )
                )

        if not points:
            raise OptimizationError("Rule 71: Failed to calculate any efficient frontier points")

        # Find max Sharpe and min variance
        sharpes = np.array([p.sharpe_ratio for p in points])
        risks = np.array([p.portfolio_risk for p in points])

        max_sharpe_idx = int(np.argmax(sharpes))
        min_variance_idx = int(np.argmin(risks))

        logger.info(
            f"Rule 71: Efficient Frontier - {len(points)} points, "
            f"Max Sharpe: return={points[max_sharpe_idx].portfolio_return:.2%}, "
            f"risk={points[max_sharpe_idx].portfolio_risk:.2%}, "
            f"sharpe={points[max_sharpe_idx].sharpe_ratio:.2f}"
        )

        return EfficientFrontier(
            points=points,
            max_sharpe_index=max_sharpe_idx,
            min_variance_index=min_variance_idx,
        )

    def _optimize_for_target_return(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        target_return: float,
    ) -> EfficientFrontierPoint | None:
        """Optimize portfolio for a specific target return."""
        n_assets = len(expected_returns)

        def portfolio_variance(weights: NDArray[np.float64]) -> float:
            return float(weights @ cov_matrix @ weights)

        # Constraints: sum(w) = 1, w @ mu = target_return
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: float(w @ expected_returns) - target_return},
        ]

        # Bounds: 0 <= w[i] <= max_position
        bounds = [(0.0, self._max_position) for _ in range(n_assets)]

        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if not result.success:
            logger.debug(f"Failed to optimize for target return {target_return:.4f}")
            return None

        weights = result.x
        portfolio_return = float(weights @ expected_returns)
        portfolio_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (portfolio_return - self._risk_free_rate) / portfolio_risk
            if portfolio_risk > 0
            else -np.inf
        )

        return EfficientFrontierPoint(
            weights=weights,
            portfolio_return=portfolio_return,
            portfolio_risk=portfolio_risk,
            sharpe_ratio=sharpe_ratio,
        )

    def check_false_diversification(
        self,
        cov_matrix: NDArray[np.float64],
        threshold: float = 0.85,
    ) -> dict[str, float | bool | str]:
        """Detect false diversification (Rule 14).

        High average correlation indicates assets move together,
        providing little real diversification benefit.

        Args:
            cov_matrix: Covariance matrix of shape (N, N).
            threshold: Correlation threshold for warning (default: 0.85).

        Returns:
            Dictionary with diversification metrics and warnings.
        """
        # Convert covariance to correlation
        vols = np.sqrt(np.diag(cov_matrix))
        correlation_matrix = cov_matrix / np.outer(vols, vols)

        # Average correlation (excluding diagonal)
        mask = ~np.eye(correlation_matrix.shape[0], dtype=bool)
        avg_correlation = float(correlation_matrix[mask].mean())

        result: dict[str, float | bool | str] = {
            "false_diversification": False,
            "avg_correlation": avg_correlation,
            "threshold": threshold,
            "warning": "",
        }

        if avg_correlation > threshold:
            logger.error(
                f"Rule 14: FALSE DIVERSIFICATION detected - "
                f"Avg correlation={avg_correlation:.2f} > {threshold:.2f}. "
                f"Portfolio not truly diversified."
            )
            result["false_diversification"] = True
            result["warning"] = (
                "Reduce number of assets or add uncorrelated assets. "
                "High correlation reduces diversification benefits."
            )
        else:
            logger.info(
                f"Rule 14: Diversification check passed - Avg correlation={avg_correlation:.2f}"
            )

        return result

    def risk_parity_fallback(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> OptimizationResult:
        """Fallback to risk parity if MVO fails (Rule 13).

        Risk parity allocates weights inversely proportional to volatility:
        w_i = (1 / sigma_i) / sum(1 / sigma_j)

        Args:
            expected_returns: Expected returns array of shape (N,).
            cov_matrix: Covariance matrix of shape (N, N).

        Returns:
            OptimizationResult with risk parity weights.
        """
        # Calculate volatilities from diagonal
        volatilities = np.sqrt(np.diag(cov_matrix))

        # Inverse volatility weights
        inv_vols = 1.0 / volatilities
        weights = inv_vols / inv_vols.sum()

        # Apply max position constraint
        weights = self.apply_diversification_constraint(weights)

        # Calculate metrics
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else -np.inf
        )

        logger.info(
            f"Rule 13: Risk Parity fallback - Return={expected_return:.2%}, "
            f"Risk={expected_risk:.2%}, Sharpe={sharpe_ratio:.2f}"
        )

        return OptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Risk parity fallback successful",
            method=OptimizationMethod.RISK_PARITY,
        )

    def optimize(
        self,
        returns: NDArray[np.float64],
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        use_shrinkage: bool = True,
    ) -> OptimizationResult:
        """Main entry point for portfolio optimization.

        Performs complete optimization pipeline:
        1. Input sanitization (Rule 15)
        2. Covariance calculation with shrinkage (Rule 74)
        3. Expected returns calculation
        4. Optimization using specified method
        5. Diversification check (Rule 14)
        6. Fallback to risk parity if needed (Rule 13)

        Args:
            returns: Historical returns array of shape (T, N).
            method: Optimization method (default: MAX_SHARPE per Rule 72).
            use_shrinkage: Whether to use shrinkage estimation (default: True).

        Returns:
            OptimizationResult with optimal weights and metrics.
        """
        try:
            # Step 1: Sanitize inputs
            returns_clean = self.sanitize_inputs(returns)

            # Step 2: Calculate covariance matrix
            cov_matrix = self.calculate_covariance_matrix(
                returns_clean, use_shrinkage=use_shrinkage
            )

            # Step 3: Calculate expected returns
            expected_returns = self.calculate_expected_returns(returns_clean)

            # Step 4: Check diversification
            self.check_false_diversification(cov_matrix)

            # Step 5: Optimize
            if method == OptimizationMethod.MAX_SHARPE:
                result = self.max_sharpe_portfolio(expected_returns, cov_matrix)
            elif method == OptimizationMethod.MIN_VARIANCE:
                result = self.min_variance_portfolio(expected_returns, cov_matrix)
            elif method == OptimizationMethod.RISK_PARITY:
                result = self.risk_parity_fallback(expected_returns, cov_matrix)
            else:
                result = self.max_sharpe_portfolio(expected_returns, cov_matrix)

            # Step 6: Fallback if optimization failed
            if not result.success and method != OptimizationMethod.RISK_PARITY:
                logger.warning("Optimization failed, using risk parity fallback (Rule 13)")
                result = self.risk_parity_fallback(expected_returns, cov_matrix)

            return result

        except Exception as e:
            logger.error(
                f"Optimization pipeline failed: {e}",
                exc_info=True,
                extra={
                    "returns_shape": returns.shape if hasattr(returns, "shape") else None,
                    "method": method.value if isinstance(method, Enum) else str(method),
                },
            )
            # Return equal weights as last resort
            n_assets = returns.shape[1]
            equal_weights = np.ones(n_assets) / n_assets

            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=0.0,
                success=False,
                message=f"Optimization failed: {e!s}",
                method=method,
            )

    def check_rebalance_trigger(
        self,
        current_weights: NDArray[np.float64],
        target_weights: NDArray[np.float64],
        threshold: float = 0.20,
    ) -> dict[str, bool | list[int] | float]:
        """Check if rebalancing is needed due to drift (Rule 9).

        Triggers rebalancing when current weights deviate significantly
        from target optimal weights.

        Args:
            current_weights: Current portfolio weights.
            target_weights: Target optimal weights from optimization.
            threshold: Deviation threshold for triggering (default: 20%).

        Returns:
            Dictionary with rebalancing recommendation and details.
        """
        if current_weights.shape != target_weights.shape:
            raise ValueError(
                f"Weight shape mismatch: {current_weights.shape} vs {target_weights.shape}"
            )

        # Absolute deviation
        absolute_deviation = np.abs(current_weights - target_weights)

        # Relative deviation (avoid division by zero)
        relative_deviation = np.divide(
            absolute_deviation,
            np.abs(target_weights),
            out=np.zeros_like(absolute_deviation),
            where=np.abs(target_weights) > 1e-10,
        )

        # Find assets needing rebalance
        rebalance_mask = relative_deviation > threshold
        rebalance_assets = np.where(rebalance_mask)[0].tolist()

        max_deviation = float(relative_deviation.max())

        if len(rebalance_assets) > 0:
            logger.info(
                f"Rule 9: Rebalance trigger - {len(rebalance_assets)} assets "
                f"deviated > {threshold:.0%}, max deviation={max_deviation:.2%}"
            )
            return {
                "rebalance": True,
                "assets": rebalance_assets,
                "max_deviation": max_deviation,
                "n_assets": len(rebalance_assets),
            }

        logger.debug(f"Rule 9: No rebalance needed - max deviation={max_deviation:.2%}")
        return {
            "rebalance": False,
            "assets": [],
            "max_deviation": max_deviation,
            "n_assets": 0,
        }
