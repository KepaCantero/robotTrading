"""
Mean-Variance Optimizer - Consolidated Implementation.

This module provides a unified Mean-Variance (Markowitz) portfolio optimization
implementation that combines the best features from:
- app/domain/services/portfolio_optimization/mean_variance_optimizer.py
- app/domain/portfolio_optimization/mean_variance_optimizer.py

Reference: Markowitz, H. (1952). "Portfolio Selection". Journal of Finance.

Features:
- Maximize Sharpe ratio optimization
- Minimize variance optimization
- Target return optimization
- Efficient frontier computation
- L2 regularization for stability
- Ledoit-Wolf shrinkage for covariance estimation
- Risk parity fallback
- Diversification constraints

Usage:
    ```python
    from app.domain.optimization.mean_variance_optimizer import MeanVarianceOptimizer
    from app.domain.optimization.base_optimizer import OptimizationConfig

    optimizer = MeanVarianceOptimizer(
        risk_free_rate=0.02,  # or use get_config().backtesting.default_risk_free_rate
        max_position=0.20,
    )

    # Optimize for max Sharpe
    result = optimizer.optimize(returns, method="max_sharpe")

    # Get efficient frontier
    frontier = optimizer.compute_efficient_frontier(returns)
    ```
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from app.shared.config.centralized_config import get_config

from .base_optimizer import (
    BaseOptimizer,
    OptimizationConfig,
    OptimizationResult,
    OptimizationStatus,
    OptimizerType,
    TrialResult,
)

logger = logging.getLogger(__name__)

# Trading days per year for annualization - get from CentralizedConfig
_config = get_config()
TRADING_DAYS = _config.backtesting.annual_trading_days


class OptimizationMethod(str, Enum):
    """Available optimization methods for MVO."""

    MAX_SHARPE = "max_sharpe"
    MIN_VARIANCE = "min_variance"
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    TARGET_RETURN = "target_return"


class ShrinkageMethod(str, Enum):
    """Available shrinkage methods for covariance estimation."""

    LEDOIT_WOLF = "ledoit_wolf"
    ORACLE_APPROXIMATING = "oracle_approximating"
    SAMPLE = "sample"


@dataclass
class PortfolioOptimizationResult:
    """
    Result of portfolio optimization.

    Contains optimal weights and portfolio metrics.
    """

    weights: NDArray[np.float64]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    success: bool
    message: str
    method: OptimizationMethod
    symbols: List[str] = field(default_factory=list)

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Convert weights array to dictionary format."""
        if self.symbols:
            return {sym: float(w) for sym, w in zip(self.symbols, self.weights)}
        return {f"asset_{i}": float(w) for i, w in enumerate(self.weights)}

    def get_allocation(self, total_capital: Decimal) -> Dict[str, Decimal]:
        """
        Get dollar allocation for each asset.

        Args:
            total_capital: Total capital to allocate

        Returns:
            Dictionary of symbol -> allocation amount
        """
        return {
            sym: Decimal(str(weight)) * total_capital
            for sym, weight in zip(self.symbols, self.weights)
        }


@dataclass
class EfficientFrontierPoint:
    """Single point on the efficient frontier."""

    weights: NDArray[np.float64]
    portfolio_return: float
    portfolio_risk: float
    sharpe_ratio: float


@dataclass
class EfficientFrontier:
    """Efficient frontier with multiple optimal portfolios."""

    points: List[EfficientFrontierPoint]
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

    def to_arrays(self) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Convert frontier points to arrays for plotting."""
        returns = np.array([p.portfolio_return for p in self.points])
        risks = np.array([p.portfolio_risk for p in self.points])
        sharpes = np.array([p.sharpe_ratio for p in self.points])
        return returns, risks, sharpes


@dataclass
class CovarianceResult:
    """Result of covariance calculation."""

    covariance_matrix: NDArray[np.float64]
    means: NDArray[np.float64]
    symbols: List[str]


class InputValidationError(ValueError):
    """Raised when input validation fails."""

    pass


class OptimizationError(RuntimeError):
    """Raised when optimization fails."""

    pass


class MeanVarianceOptimizer(BaseOptimizer[NDArray[np.float64]]):
    """
    Markowitz Mean-Variance Portfolio Optimization (1952).

    This class implements Modern Portfolio Theory for optimal portfolio construction.
    It follows SOLID principles by separating concerns:
    - Covariance estimation (separate shrinkage methods)
    - Constraint validation (separate validators)
    - Optimization algorithms (separate methods)

    Attributes:
        lookback_days: Number of days for covariance calculation (default: 252)
        max_position: Maximum weight per asset (default: 0.20 for diversification)
        risk_free_rate: Risk-free rate for Sharpe ratio calculation (default: from CentralizedConfig)
        regularization_gamma: L2 regularization parameter (default: 0.01)
        sum_tolerance: Tolerance for sum constraint validation (default: 1e-6)

    Example:
        >>> optimizer = MeanVarianceOptimizer()
        >>> returns = np.random.randn(252, 10) * 0.01  # 252 days, 10 assets
        >>> result = optimizer.optimize(returns)
        >>> print(f"Weights: {result.weights}")
        >>> print(f"Expected Sharpe: {result.sharpe_ratio:.2f}")
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        lookback_days: int = 252,
        max_position: float = 0.20,
        risk_free_rate: float = None,
        regularization_gamma: float = 0.01,
        sum_tolerance: float = 1e-6,
        allow_short: bool = False,
    ) -> None:
        """
        Initialize the Mean-Variance Optimizer.

        Args:
            config: Optimization configuration (optional)
            lookback_days: Minimum days for covariance calculation.
                Must be >= 252 for statistical significance.
            max_position: Maximum weight per asset.
                Default 0.20 forces diversification.
            risk_free_rate: Annual risk-free rate for Sharpe calculation.
                Default: from get_config().backtesting.default_risk_free_rate.
            regularization_gamma: L2 regularization strength.
                Default 0.01 prevents corner solutions.
            sum_tolerance: Tolerance for sum constraint validation.
                Default 1e-6 for numerical precision.
            allow_short: Whether to allow short positions.

        Raises:
            ValueError: If parameters are out of valid range.
        """
        if config is None:
            config = OptimizationConfig(maximize=True, metric="sharpe_ratio")

        # Use CentralizedConfig default if not provided
        if risk_free_rate is None:
            risk_free_rate = float(get_config().backtesting.default_risk_free_rate)

        super().__init__(config)

        self._validate_initialization_params(
            lookback_days, max_position, risk_free_rate, regularization_gamma, sum_tolerance
        )

        self._lookback_days = lookback_days
        self._max_position = max_position
        self._risk_free_rate = risk_free_rate
        self._regularization_gamma = regularization_gamma
        self._sum_tolerance = sum_tolerance
        self._allow_short = allow_short

        self._min_weight = -1.0 if allow_short else 0.0

        # Results storage
        self._last_result: Optional[PortfolioOptimizationResult] = None
        self._symbols: List[str] = []

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
                "Covariance requires minimum 252 days for statistical significance."
            )
        if not 0.0 < max_position <= 1.0:
            raise ValueError(
                f"max_position must be in (0, 1], got {max_position}. "
                "Max position must be positive and not exceed 100%."
            )
        if not 0.0 <= risk_free_rate <= 1.0:
            raise ValueError(
                f"risk_free_rate must be in [0, 1], got {risk_free_rate}. "
                "Risk-free rate should be an annual decimal rate."
            )
        if regularization_gamma < 0.0:
            raise ValueError(
                f"regularization_gamma must be >= 0, got {regularization_gamma}. "
                "L2 regularization must be non-negative."
            )
        if not 0.0 < sum_tolerance < 1e-3:
            raise ValueError(
                f"sum_tolerance must be in (0, 1e-3), got {sum_tolerance}. "
                "Sum constraint tolerance requires reasonable precision."
            )

    @classmethod
    def get_optimizer_type(cls) -> OptimizerType:
        """Get the type of this optimizer."""
        return OptimizerType.MEAN_VARIANCE

    def get_best_params(self) -> Dict[str, Any]:
        """Get the best parameters found (optimal weights)."""
        if self._last_result is not None:
            return self._last_result.weights_dict
        return {}

    def get_history(self) -> List[TrialResult]:
        """Get optimization history."""
        return self._history

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

    async def optimize(
        self,
        objective: object,  # Not used for portfolio optimization
        search_space: NDArray[np.float64],  # Returns matrix (T, N)
    ) -> OptimizationResult:
        """
        Main entry point for portfolio optimization.

        Args:
            objective: Not used for portfolio optimization
            search_space: Historical returns array of shape (T, N)

        Returns:
            OptimizationResult with optimal weights and metrics
        """
        returns = search_space
        result = self.optimize_portfolio(returns)

        return OptimizationResult(
            best_params=result.weights_dict,
            best_weights=result.weights,
            best_score=result.sharpe_ratio,
            all_trials=[],
            optimization_time=0.0,
            n_iterations=1,
            converged=result.success,
            status=OptimizationStatus.COMPLETED if result.success else OptimizationStatus.FAILED,
            config=self.config,
            additional_info={
                "expected_return": result.expected_return,
                "expected_risk": result.expected_risk,
                "method": result.method.value,
                "message": result.message,
            },
        )

    def optimize_portfolio(
        self,
        returns: NDArray[np.float64],
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        use_shrinkage: bool = True,
        shrinkage_method: ShrinkageMethod = ShrinkageMethod.LEDOIT_WOLF,
        target_return: Optional[float] = None,
        symbols: Optional[List[str]] = None,
    ) -> PortfolioOptimizationResult:
        """
        Main entry point for portfolio optimization.

        Performs complete optimization pipeline:
        1. Input sanitization
        2. Covariance calculation with shrinkage
        3. Expected returns calculation
        4. Optimization using specified method
        5. Diversification check
        6. Fallback to risk parity if needed

        Args:
            returns: Historical returns array of shape (T, N).
            method: Optimization method (default: MAX_SHARPE).
            use_shrinkage: Whether to use shrinkage estimation (default: True).
            shrinkage_method: Shrinkage method to use.
            target_return: Target return for TARGET_RETURN method.
            symbols: Asset symbols (optional).

        Returns:
            PortfolioOptimizationResult with optimal weights and metrics.
        """
        try:
            # Step 1: Sanitize inputs
            returns_clean = self.sanitize_inputs(returns)

            # Step 2: Calculate covariance matrix
            cov_matrix = self.calculate_covariance_matrix(
                returns_clean, use_shrinkage=use_shrinkage, shrinkage_method=shrinkage_method
            )

            # Step 3: Calculate expected returns
            expected_returns = self.calculate_expected_returns(returns_clean)

            # Step 4: Check diversification
            self.check_false_diversification(cov_matrix)

            # Store symbols
            self._symbols = symbols or [f"asset_{i}" for i in range(returns_clean.shape[1])]

            # Step 5: Optimize
            if method == OptimizationMethod.MAX_SHARPE:
                result = self._maximize_sharpe(expected_returns, cov_matrix)
            elif method == OptimizationMethod.MIN_VARIANCE:
                result = self._minimize_variance(expected_returns, cov_matrix)
            elif method == OptimizationMethod.RISK_PARITY:
                result = self._risk_parity_fallback(expected_returns, cov_matrix)
            elif method == OptimizationMethod.TARGET_RETURN:
                if target_return is None:
                    raise ValueError("target_return required for TARGET_RETURN method")
                result = self._target_return_optimization(
                    expected_returns, cov_matrix, target_return
                )
            elif method == OptimizationMethod.EQUAL_WEIGHT:
                result = self._equal_weights(expected_returns, cov_matrix)
            else:
                result = self._maximize_sharpe(expected_returns, cov_matrix)

            # Add symbols to result
            result.symbols = self._symbols

            # Step 6: Fallback if optimization failed
            if not result.success and method != OptimizationMethod.RISK_PARITY:
                logger.warning("Optimization failed, using risk parity fallback")
                result = self._risk_parity_fallback(expected_returns, cov_matrix)
                result.symbols = self._symbols

            self._last_result = result
            return result

        except Exception as e:
            logger.error(f"Optimization pipeline failed: {e}", exc_info=True)

            # Return equal weights as last resort
            n_assets = returns.shape[1] if len(returns.shape) > 1 else 1
            equal_weights = np.ones(n_assets) / n_assets

            return PortfolioOptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=0.0,
                success=False,
                message=f"Optimization failed: {str(e)}",
                method=method,
                symbols=symbols or [f"asset_{i}" for i in range(n_assets)],
            )

    def sanitize_inputs(self, returns: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Validate and sanitize input returns data.

        Args:
            returns: Returns array of shape (T, N).

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
                f"Covariance calculation requires minimum {self._lookback_days} days."
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
                f"Dropping {n_nan_assets} assets with NaN values "
                f"({n_nan_assets / n_assets:.1%} of universe)"
            )
            returns = returns[:, ~nan_mask]

        # Check for zero/near-zero volatility
        volatilities = returns.std(axis=0)
        zero_vol_mask = volatilities < 1e-10
        n_zero_vol = zero_vol_mask.sum()

        if n_zero_vol > 0:
            logger.warning(
                f"Dropping {n_zero_vol} assets with ~0 volatility "
                f"({n_zero_vol / n_assets:.1%} of universe)"
            )
            returns = returns[:, ~zero_vol_mask]

        # Validate sufficient assets remain
        if returns.shape[1] < 2:
            raise InputValidationError(
                f"Insufficient assets after sanitization: {returns.shape[1]} < 2. "
                "Need at least 2 valid assets for optimization."
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
        """
        Calculate expected returns from historical data.

        Args:
            returns: Returns array of shape (T, N).
            annualize: Whether to annualize returns (default: True).

        Returns:
            Expected returns array of shape (N,).
        """
        expected_returns = returns.mean(axis=0)

        if annualize:
            expected_returns = expected_returns * TRADING_DAYS

        return expected_returns

    def calculate_covariance_matrix(
        self,
        returns: NDArray[np.float64],
        use_shrinkage: bool = True,
        shrinkage_method: ShrinkageMethod = ShrinkageMethod.LEDOIT_WOLF,
    ) -> NDArray[np.float64]:
        """
        Calculate covariance matrix with 252-day lookback.

        Uses the most recent lookback_days periods for calculation.
        Applies Ledoit-Wolf shrinkage by default for robustness.

        Args:
            returns: Returns array of shape (T, N) where T >= lookback_days.
            use_shrinkage: Whether to apply shrinkage estimation (default: True).
            shrinkage_method: Shrinkage method to use (default: LEDOIT_WOLF).

        Returns:
            Covariance matrix of shape (N, N), annualized.

        Raises:
            OptimizationError: If covariance calculation fails.
        """
        # Use only the most recent lookback_days
        recent_returns = returns[-self._lookback_days :, :]

        if use_shrinkage:
            cov_matrix = self._shrink_covariance_matrix(recent_returns, shrinkage_method)
        else:
            # Sample covariance
            cov_matrix = np.asarray(
                np.cov(recent_returns, rowvar=False) * TRADING_DAYS, dtype=np.float64
            )

        # Validate covariance matrix is positive semi-definite
        if not self._is_positive_semi_definite(cov_matrix):
            logger.warning(
                "Covariance matrix is not positive semi-definite. "
                "Applying nearest PSD correction."
            )
            cov_matrix = self._nearest_positive_semi_definite(cov_matrix)

        logger.info(
            f"Covariance matrix: {cov_matrix.shape[0]} assets, "
            f"{self._lookback_days} days lookback, shrinkage={use_shrinkage}"
        )

        return cov_matrix

    def _shrink_covariance_matrix(
        self,
        returns: NDArray[np.float64],
        method: ShrinkageMethod = ShrinkageMethod.LEDOIT_WOLF,
    ) -> NDArray[np.float64]:
        """Apply shrinkage to covariance matrix."""
        try:
            if method == ShrinkageMethod.LEDOIT_WOLF:
                from sklearn.covariance import LedoitWolf

                lw = LedoitWolf()
                shrunk_cov = lw.fit(returns).covariance_ * TRADING_DAYS
                shrinkage = lw.shrinkage_

                logger.info(f"Ledoit-Wolf shrinkage applied: {shrinkage:.2%}")

            elif method == ShrinkageMethod.ORACLE_APPROXIMATING:
                from sklearn.covariance import OAS

                oas = OAS()
                shrunk_cov = oas.fit(returns).covariance_ * TRADING_DAYS
                shrinkage = oas.shrinkage_

                logger.info(f"OAS shrinkage applied: {shrinkage:.2%}")

            else:
                # Sample covariance (no shrinkage)
                shrunk_cov = np.cov(returns, rowvar=False) * TRADING_DAYS
                logger.warning("Using sample covariance (no shrinkage).")

            return shrunk_cov

        except ImportError as e:
            logger.error(f"scikit-learn not available for shrinkage: {e}. Using sample covariance.")
            return np.cov(returns, rowvar=False) * TRADING_DAYS

    @staticmethod
    def _is_positive_semi_definite(matrix: NDArray[np.float64]) -> bool:
        """Check if matrix is positive semi-definite."""
        try:
            np.linalg.cholesky(matrix)
            return True
        except np.linalg.LinAlgError:
            return False

    @staticmethod
    def _nearest_positive_semi_definite(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
        """Find nearest positive semi-definite matrix using Higham's method."""
        # Symmetrize
        sym_matrix = (matrix + matrix.T) / 2

        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(sym_matrix)

        # Clip negative eigenvalues
        eigenvalues = np.maximum(eigenvalues, 0)

        # Reconstruct
        return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    def _maximize_sharpe(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> PortfolioOptimizationResult:
        """Calculate maximum Sharpe ratio portfolio."""
        n_assets = len(expected_returns)

        def negative_sharpe(weights: NDArray[np.float64]) -> float:
            portfolio_return = float(weights @ expected_returns)
            portfolio_variance = float(weights @ cov_matrix @ weights)
            portfolio_risk = float(np.sqrt(portfolio_variance))

            if portfolio_risk < 1e-10:
                return float(-np.inf)

            excess_return = portfolio_return - self._risk_free_rate
            return float(-(excess_return / portfolio_risk))

        # Constraints: sum(w) = 1
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        # Bounds
        bounds = [(self._min_weight, self._max_position) for _ in range(n_assets)]

        # Initial guess: equal weight
        x0 = np.ones(n_assets) / n_assets

        # Optimize
        result = minimize(
            negative_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if not result.success:
            logger.error(f"Max Sharpe optimization failed: {result.message}")

        weights = result.x
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else float(-np.inf)
        )

        return PortfolioOptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=result.success,
            message=result.message,
            method=OptimizationMethod.MAX_SHARPE,
        )

    def _minimize_variance(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> PortfolioOptimizationResult:
        """Calculate minimum variance portfolio."""
        n_assets = len(expected_returns)

        def portfolio_variance(weights: NDArray[np.float64]) -> float:
            return float(weights @ cov_matrix @ weights)

        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        bounds = [(self._min_weight, self._max_position) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        weights = result.x
        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else float(-np.inf)
        )

        return PortfolioOptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=result.success,
            message=result.message,
            method=OptimizationMethod.MIN_VARIANCE,
        )

    def _target_return_optimization(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        target_return: float,
    ) -> PortfolioOptimizationResult:
        """Find minimum variance portfolio for target return."""
        n_assets = len(expected_returns)
        target_return / TRADING_DAYS

        def portfolio_variance(weights: NDArray[np.float64]) -> float:
            return float(weights @ cov_matrix @ weights)

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: float(w @ expected_returns) - target_return},
        ]

        bounds = [(self._min_weight, self._max_position) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        weights = result.x
        actual_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (actual_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else float(-np.inf)
        )

        return PortfolioOptimizationResult(
            weights=weights,
            expected_return=actual_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=result.success,
            message=result.message,
            method=OptimizationMethod.TARGET_RETURN,
        )

    def _risk_parity_fallback(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> PortfolioOptimizationResult:
        """Fallback to risk parity if MVO fails."""
        volatilities = np.sqrt(np.diag(cov_matrix))
        inv_vols = 1.0 / volatilities
        weights = inv_vols / inv_vols.sum()

        # Apply max position constraint
        weights = self._apply_diversification_constraint(weights)

        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else float(-np.inf)
        )

        return PortfolioOptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Risk parity fallback successful",
            method=OptimizationMethod.RISK_PARITY,
        )

    def _equal_weights(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> PortfolioOptimizationResult:
        """Generate equal weight portfolio."""
        n_assets = len(expected_returns)
        weights = np.ones(n_assets) / n_assets

        expected_return = float(weights @ expected_returns)
        expected_risk = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe_ratio = (
            (expected_return - self._risk_free_rate) / expected_risk
            if expected_risk > 0
            else float(-np.inf)
        )

        return PortfolioOptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe_ratio,
            success=True,
            message="Equal weight allocation",
            method=OptimizationMethod.EQUAL_WEIGHT,
        )

    def _apply_diversification_constraint(
        self,
        weights: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Limit concentration: max position per asset."""
        max_iterations = 100

        for _ in range(max_iterations):
            violations = weights > self._max_position
            n_violations = violations.sum()

            if n_violations == 0:
                break

            # Cap violating weights
            weights[violations] = self._max_position

            # Calculate excess to redistribute
            current_sum = weights.sum()
            excess = 1.0 - current_sum

            # Find assets below max that can receive excess
            below_max = weights < self._max_position
            n_below_max = below_max.sum()

            if n_below_max == 0:
                weights = np.full_like(weights, self._max_position)
                break

            if excess > 0:
                headroom = self._max_position - weights[below_max]
                total_headroom = headroom.sum()

                if total_headroom > 0:
                    weights[below_max] += excess * (headroom / total_headroom)
            else:
                break

        # Final normalization
        weights = weights / weights.sum()
        return weights

    def compute_efficient_frontier(
        self,
        returns: NDArray[np.float64],
        n_points: int = 20,
        use_shrinkage: bool = True,
    ) -> EfficientFrontier:
        """
        Compute efficient frontier with 20+ points.

        Args:
            returns: Historical returns array of shape (T, N).
            n_points: Number of frontier points (default: 20).
            use_shrinkage: Whether to use shrinkage estimation.

        Returns:
            EfficientFrontier with all frontier points and optimal portfolios.
        """
        returns_clean = self.sanitize_inputs(returns)
        cov_matrix = self.calculate_covariance_matrix(returns_clean, use_shrinkage=use_shrinkage)
        expected_returns = self.calculate_expected_returns(returns_clean)

        n_assets = len(expected_returns)

        # Get return bounds
        min_var_result = self._minimize_variance(expected_returns, cov_matrix)
        min_return = min_var_result.expected_return

        # Find max return
        sorted_indices = np.argsort(expected_returns)
        n_assets_max = min(5, n_assets)
        max_feasible_return = expected_returns[sorted_indices[-n_assets_max:]].mean()

        # Generate target returns
        return_range = max_feasible_return - min_return
        min_target = min_return - 0.1 * return_range
        max_target = max_feasible_return + 0.1 * return_range

        target_returns = np.linspace(min_target, max_target, n_points)

        points: List[EfficientFrontierPoint] = []

        for target in target_returns:
            try:
                result = self._target_return_optimization(expected_returns, cov_matrix, target)
                if result.success:
                    points.append(
                        EfficientFrontierPoint(
                            weights=result.weights,
                            portfolio_return=result.expected_return,
                            portfolio_risk=result.expected_risk,
                            sharpe_ratio=result.sharpe_ratio,
                        )
                    )
            except Exception:
                continue

        if not points and min_var_result.success:
            points.append(
                EfficientFrontierPoint(
                    weights=min_var_result.weights,
                    portfolio_return=min_var_result.expected_return,
                    portfolio_risk=min_var_result.expected_risk,
                    sharpe_ratio=min_var_result.sharpe_ratio,
                )
            )

        if not points:
            raise OptimizationError("Failed to calculate any efficient frontier points")

        # Find max Sharpe and min variance
        sharpes = np.array([p.sharpe_ratio for p in points])
        risks = np.array([p.portfolio_risk for p in points])

        max_sharpe_idx = int(np.argmax(sharpes))
        min_variance_idx = int(np.argmin(risks))

        return EfficientFrontier(
            points=points,
            max_sharpe_index=max_sharpe_idx,
            min_variance_index=min_variance_idx,
        )

    def check_false_diversification(
        self,
        cov_matrix: NDArray[np.float64],
        threshold: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Detect false diversification.

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

        result: Dict[str, Any] = {
            "false_diversification": False,
            "avg_correlation": avg_correlation,
            "threshold": threshold,
            "warning": "",
        }

        if avg_correlation > threshold:
            logger.warning(
                f"FALSE DIVERSIFICATION detected - "
                f"Avg correlation={avg_correlation:.2f} > {threshold:.2f}. "
                f"Portfolio not truly diversified."
            )
            result["false_diversification"] = True
            result["warning"] = (
                "Reduce number of assets or add uncorrelated assets. "
                "High correlation reduces diversification benefits."
            )
        else:
            logger.info(f"Diversification check passed - Avg correlation={avg_correlation:.2f}")

        return result

    def check_rebalance_trigger(
        self,
        current_weights: NDArray[np.float64],
        target_weights: NDArray[np.float64],
        threshold: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Check if rebalancing is needed due to drift.

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

        # Relative deviation
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
                f"Rebalance trigger - {len(rebalance_assets)} assets "
                f"deviated > {threshold:.0%}, max deviation={max_deviation:.2%}"
            )
            return {
                "rebalance": True,
                "assets": rebalance_assets,
                "max_deviation": max_deviation,
                "n_assets": len(rebalance_assets),
            }

        return {
            "rebalance": False,
            "assets": [],
            "max_deviation": max_deviation,
            "n_assets": 0,
        }
