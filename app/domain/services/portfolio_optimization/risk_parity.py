"""
Risk Parity Portfolio Optimization

Implements Risk Parity and related allocation methods that equalize
risk contribution across assets.

Reference: Rule 48-papers-markowitz (Related methods)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import minimize

from app.domain.services.portfolio_optimization._validation import (
    validate_covariance_matrix,
    sanitize_covariance_matrix,
    log_optimization_failure,
    MIN_VARIANCE_THRESHOLD,
)


logger = logging.getLogger(__name__)


# Risk Parity default parameters
DEFAULT_RISK_FREE_RATE = 0.02  # Annual risk-free rate
DEFAULT_MIN_WEIGHT = 0.0  # Minimum weight per asset (no short)
DEFAULT_MAX_WEIGHT = 1.0  # Maximum weight per asset
DEFAULT_OPTIMIZATION_TOLERANCE = 1e-9  # Optimization tolerance
DEFAULT_DIVERSE_RISK_PARITY_KAPPA = 1.0  # Diversification parameter
DEFAULT_DIV_RETURN_THRESHOLD = 1.0  # Default return if portfolio_vol == 0


@dataclass
class RiskParityResult:
    """Result of Risk Parity optimization."""

    weights: np.ndarray  # Risk parity weights
    risk_contributions: np.ndarray  # Risk contribution of each asset
    risk_budget: np.ndarray  # Target risk budget (usually equal)
    symbols: List[str]  # Asset symbols
    converged: bool  # Whether optimization converged

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}

    @property
    def risk_parity_error(self) -> float:
        """Get error in risk parity (std dev of risk contributions)."""
        return float(np.std(self.risk_contributions))


class RiskParityOptimizer:
    """
    Risk Parity portfolio optimizer.

    Risk Parity allocates weights such that each asset contributes
    equal risk to the portfolio:

    RC_i = w_i * (Σw)_i / σ_p = constant

    Methods:
    - Risk Parity (equal risk contribution)
    - Inverse Volatility
    - Equal Weight (benchmark)
    - Diversified Risk Parity

    Reference:
    - Qian, E., & Maas, K. (2010). "Risk Parity Portfolios"
    """

    def __init__(
        self,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        min_weight: float = DEFAULT_MIN_WEIGHT,
        max_weight: float = DEFAULT_MAX_WEIGHT,
    ):
        """
        Initialize Risk Parity optimizer.

        Args:
            risk_free_rate: Annual risk-free rate
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
        """
        if min_weight < 0:
            raise ValueError(f"Min weight cannot be negative, got {min_weight}")
        if max_weight > 1.0:
            raise ValueError(f"Max weight cannot exceed 1.0, got {max_weight}")
        if min_weight > max_weight:
            raise ValueError(f"Min weight {min_weight} > max weight {max_weight}")

        self._risk_free_rate = risk_free_rate
        self._min_weight = min_weight
        self._max_weight = max_weight

    def optimize(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
        risk_budget: Optional[np.ndarray] = None,
    ) -> RiskParityResult:
        """
        Compute Risk Parity weights.

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols
            risk_budget: Target risk budget (None = equal risk)

        Returns:
            RiskParityResult with optimal weights

        Raises:
            ValueError: If covariance matrix validation fails
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

        # Sanitize: remove zero variance assets
        try:
            sanitized_cov, valid_indices = sanitize_covariance_matrix(
                validated_cov,
                min_variance_threshold=MIN_VARIANCE_THRESHOLD,
                enforce_psd=False,  # Already enforced above
            )
        except ValueError as e:
            log_optimization_failure(
                "risk_parity.sanitize_covariance",
                e,
                {"original_shape": cov_matrix.shape},
            )
            raise

        cov_matrix = sanitized_cov
        n_assets = cov_matrix.shape[0]

        # Filter symbols to valid assets
        if symbols is not None:
            symbols = [symbols[i] for i in valid_indices]
        else:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        # Default to equal risk budget
        if risk_budget is None:
            risk_budget = np.ones(n_assets) / n_assets
        else:
            # Filter risk budget to valid assets
            risk_budget = risk_budget[valid_indices]
            # Normalize
            risk_budget = risk_budget / risk_budget.sum()

        # Initial guess (inverse volatility)
        try:
            inv_vol = 1.0 / np.sqrt(np.diag(cov_matrix))
        except (ZeroDivisionError, FloatingPointError):
            logger.warning("Zero variance in covariance matrix, using equal weights")
            inv_vol = np.ones(n_assets)

        x0 = inv_vol / inv_vol.sum()

        # Objective: minimize sum of squared differences from risk budget
        def objective(weights: np.ndarray) -> float:
            # Calculate risk contributions
            portfolio_var = weights @ cov_matrix @ weights
            portfolio_std = np.sqrt(portfolio_var)

            if portfolio_std == 0:
                return 1e6

            marginal_contrib = cov_matrix @ weights
            contrib = weights * marginal_contrib / portfolio_std

            # Normalize to sum to 1
            contrib_sum = contrib.sum()
            if contrib_sum == 0:
                return 1e6
            contrib = contrib / contrib_sum

            # Squared error from risk budget
            return float(np.sum((contrib - risk_budget) ** 2))

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": DEFAULT_OPTIMIZATION_TOLERANCE},
        )

        weights = result.x if result.success else x0

        # Calculate final risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=risk_budget,
            symbols=symbols,
            converged=result.success,
        )

    def inverse_volatility(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
    ) -> RiskParityResult:
        """
        Compute inverse volatility weights (simple risk parity).

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols

        Returns:
            RiskParityResult with inverse volatility weights

        Raises:
            ValueError: If all assets have zero variance
        """
        # Sanitize covariance matrix
        try:
            sanitized_cov, valid_indices = sanitize_covariance_matrix(
                cov_matrix,
                min_variance_threshold=MIN_VARIANCE_THRESHOLD,
                enforce_psd=True,
            )
        except ValueError as e:
            log_optimization_failure(
                "inverse_volatility",
                e,
                {"shape": cov_matrix.shape},
            )
            raise

        volatilities = np.sqrt(np.diag(sanitized_cov))
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()

        n_assets = len(volatilities)

        # Filter symbols
        if symbols is not None:
            symbols = [symbols[i] for i in valid_indices]
        else:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        # Calculate risk contributions
        portfolio_var = weights @ sanitized_cov @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = sanitized_cov @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=np.ones(n_assets) / n_assets,
            symbols=symbols,
            converged=True,
        )

    def equal_weight(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
    ) -> RiskParityResult:
        """
        Compute equal weights (benchmark).

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols

        Returns:
            RiskParityResult with equal weights
        """
        # Basic validation only
        if cov_matrix.ndim != 2 or cov_matrix.shape[0] != cov_matrix.shape[1]:
            raise ValueError(f"Covariance matrix must be square, got shape {cov_matrix.shape}")

        n_assets = cov_matrix.shape[0]

        if n_assets == 0:
            raise ValueError("Covariance matrix has zero assets")

        weights = np.ones(n_assets) / n_assets
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Calculate risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=np.ones(n_assets) / n_assets,
            symbols=symbols,
            converged=True,
        )

    def diversified_risk_parity(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
        kappa: float = DEFAULT_DIVERSE_RISK_PARITY_KAPPA,
    ) -> RiskParityResult:
        """
        Compute Diversified Risk Parity weights.

        Adds diversification term to objective function.

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols
            kappa: Diversification parameter

        Returns:
            RiskParityResult with DRP weights

        Raises:
            ValueError: If covariance matrix validation fails
        """
        # Validate and sanitize
        is_valid, validated_cov, error_msg = validate_covariance_matrix(
            cov_matrix,
            check_psd=True,
            check_symmetry=True,
            enforce_psd=True,
        )

        if not is_valid:
            raise ValueError(f"Invalid covariance matrix: {error_msg}")

        try:
            sanitized_cov, valid_indices = sanitize_covariance_matrix(
                validated_cov,
                min_variance_threshold=MIN_VARIANCE_THRESHOLD,
                enforce_psd=False,
            )
        except ValueError as e:
            log_optimization_failure(
                "diversified_risk_parity",
                e,
                {"shape": cov_matrix.shape},
            )
            raise

        cov_matrix = sanitized_cov
        n_assets = cov_matrix.shape[0]

        # Filter symbols
        if symbols is not None:
            symbols = [symbols[i] for i in valid_indices]
        else:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        # Risk budget (equal)
        risk_budget = np.ones(n_assets) / n_assets

        # Initial guess
        inv_vol = 1.0 / np.sqrt(np.diag(cov_matrix))
        x0 = inv_vol / inv_vol.sum()

        def objective(weights: np.ndarray) -> float:
            # Risk parity term
            portfolio_var = weights @ cov_matrix @ weights
            portfolio_std = np.sqrt(portfolio_var)
            marginal_contrib = cov_matrix @ weights
            contrib = weights * marginal_contrib / portfolio_std
            contrib = contrib / contrib.sum()

            rp_term = np.sum((contrib - risk_budget) ** 2)

            # Diversification term (negative entropy)
            # Add small epsilon to avoid log(0)
            div_term = -kappa * np.sum(weights * np.log(weights + 1e-10))

            return rp_term + div_term

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        weights = result.x if result.success else x0

        # Calculate risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=risk_budget,
            symbols=symbols,
            converged=result.success,
        )

    def get_diversification_ratio(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> float:
        """
        Calculate diversification ratio.

        DR = (Σ w_i σ_i) / σ_p

        Where DR > 1 indicates diversification benefit.

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Diversification ratio
        """
        # Weighted average volatility
        volatilities = np.sqrt(np.diag(cov_matrix))
        avg_vol = float(weights @ volatilities)

        # Portfolio volatility
        portfolio_vol = float(np.sqrt(weights @ cov_matrix @ weights))

        if portfolio_vol == 0:
            return DEFAULT_DIV_RETURN_THRESHOLD

        return avg_vol / portfolio_vol


def cluster_based_risk_parity(
    cov_matrix: np.ndarray,
    cluster_labels: np.ndarray,
    symbols: Optional[List[str]] = None,
) -> np.ndarray:
    """
    Compute Cluster-Based Risk Parity (CBRP) weights.

    Combines clustering with risk parity:
    1. Allocate to clusters using risk parity
    2. Allocate within clusters using risk parity

    Args:
        cov_matrix: Covariance matrix
        cluster_labels: Cluster assignment for each asset
        symbols: Asset symbols

    Returns:
        CBRP weights

    Raises:
        ValueError: If inputs are invalid
    """
    # Basic validation
    if cov_matrix.ndim != 2 or cov_matrix.shape[0] != cov_matrix.shape[1]:
        raise ValueError(f"Covariance matrix must be square, got shape {cov_matrix.shape}")

    n_assets = cov_matrix.shape[0]

    if len(cluster_labels) != n_assets:
        raise ValueError(
            f"Cluster labels length {len(cluster_labels)} "
            f"must match n_assets {n_assets}"
        )

    symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

    unique_clusters = np.unique(cluster_labels)
    final_weights = np.zeros(n_assets)

    # Calculate cluster covariances and weights
    cluster_variances = {}

    for cluster_id in unique_clusters:
        indices = np.where(cluster_labels == cluster_id)[0]

        if len(indices) == 0:
            logger.warning(f"Cluster {cluster_id} has no assets, skipping")
            continue

        if len(indices) == 1:
            # Single asset cluster
            cluster_weights = np.array([1.0])
        else:
            # Inverse volatility within cluster
            cluster_cov = cov_matrix[np.ix_(indices, indices)]
            cluster_vols = np.sqrt(np.diag(cluster_cov))

            # Check for zero variance
            if np.any(cluster_vols < MIN_VARIANCE_THRESHOLD):
                logger.warning(
                    f"Cluster {cluster_id} has zero variance assets, "
                    "using equal weights within cluster"
                )
                cluster_weights = np.ones(len(indices)) / len(indices)
            else:
                cluster_weights = 1.0 / cluster_vols
                cluster_weights = cluster_weights / cluster_weights.sum()

        # Calculate cluster variance
        cluster_cov = cov_matrix[np.ix_(indices, indices)]
        cluster_var = float(cluster_weights @ cluster_cov @ cluster_weights)
        cluster_variances[cluster_id] = cluster_var

        # Store intra-cluster weights
        final_weights[indices] = cluster_weights

    # Allocate across clusters (inverse variance)
    inv_var_list = []
    valid_clusters = []

    for cluster_id in unique_clusters:
        if cluster_id in cluster_variances and cluster_variances[cluster_id] > 0:
            inv_var_list.append(1.0 / cluster_variances[cluster_id])
            valid_clusters.append(cluster_id)

    if len(inv_var_list) == 0:
        logger.warning("All clusters have zero variance, using equal weights")
        return np.ones(n_assets) / n_assets

    inv_var_array = np.array(inv_var_list)
    cluster_allocation = inv_var_array / inv_var_array.sum()

    # Combine intra and inter cluster weights
    for i, cluster_id in enumerate(valid_clusters):
        indices = np.where(cluster_labels == cluster_id)[0]
        final_weights[indices] *= cluster_allocation[i]

    return final_weights
