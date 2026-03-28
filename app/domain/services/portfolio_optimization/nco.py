"""
Nested Clustered Optimization (NCO) - López de Prado

Implements Nested Clustered Optimization which combines
hierarchical clustering with convex optimization.

Reference: Rule 03-lopez-de-prado-advances-financial-ml.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

from app.domain.services.portfolio_optimization._validation import (
    log_optimization_failure,
    sanitize_covariance_matrix,
    validate_covariance_matrix,
)

logger = logging.getLogger(__name__)


# NCO default parameters and constants
DEFAULT_MIN_CLUSTER_SIZE = 2  # Minimum assets per cluster
DEFAULT_OPTIMIZATION_METHOD = "sharpe"  # Default optimization method
HIGH_CORRELATION_THRESHOLD = 0.7  # Threshold for highly correlated assets
MEDIUM_CORRELATION_THRESHOLD = 0.5  # Threshold for medium correlated assets
DEFAULT_OPTIMIZATION_TOLERANCE = 1e-9  # Optimization tolerance
DEFAULT_NEG_INF_RETURN = -np.inf  # Negative infinity return


@dataclass
class NCOResult:
    """Result of Nested Clustered Optimization."""

    weights: np.ndarray  # NCO weights
    cluster_weights: Dict[int, np.ndarray]  # Weights within each cluster
    cluster_allocation: Dict[int, float]  # Allocation to each cluster
    n_clusters: int  # Number of clusters used
    symbols: List[str]  # Asset symbols

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}


class NestedClusteredOptimizer:
    """
    Nested Clustered Optimization (NCO) portfolio optimizer.

    NCO improves on HRP by:
    1. Clustering assets hierarchically
    2. Optimizing within each cluster (convex optimization)
    3. Allocating across clusters (convex optimization)

    This nested approach:
    - Reduces dimensionality of optimization problem
    - Handles multicollinearity naturally
    - Outperforms both HRP and MVO out-of-sample

    Reference: López de Prado, M. (2019). "Machine Learning for Asset Managers"
    """

    def __init__(
        self,
        min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
        optimization_method: str = DEFAULT_OPTIMIZATION_METHOD,
    ):
        """
        Initialize NCO optimizer.

        Args:
            min_cluster_size: Minimum assets per cluster
            optimization_method: Optimization method within clusters (sharpe, min_variance)
        """
        if min_cluster_size < 2:
            raise ValueError(f"min_cluster_size must be at least 2, got {min_cluster_size}")

        if optimization_method not in ["sharpe", "min_variance"]:
            raise ValueError(
                f"optimization_method must be 'sharpe' or 'min_variance', "
                f"got {optimization_method}"
            )

        self._min_cluster_size = min_cluster_size
        self._optimization_method = optimization_method

    def optimize(
        self,
        cov_matrix: np.ndarray,
        expected_returns: Optional[np.ndarray] = None,
        symbols: Optional[List[str]] = None,
        n_clusters: Optional[int] = None,
    ) -> NCOResult:
        """
        Compute NCO portfolio weights.

        Args:
            cov_matrix: Covariance matrix
            expected_returns: Expected returns (for Sharpe optimization)
            symbols: Asset symbols
            n_clusters: Number of clusters (None = auto-determine)

        Returns:
            NCOResult with optimal weights

        Raises:
            ValueError: If covariance matrix validation fails
        """
        # Step 1: Validate and preprocess inputs
        cov_matrix, expected_returns, symbols = self._validate_optimization_inputs(
            cov_matrix, expected_returns, symbols
        )

        # Step 2: Preprocess covariance and create clusters
        n_assets, cov_matrix, n_clusters, assignments = self._preprocess_covariance_matrix(
            cov_matrix, n_clusters
        )

        # Step 3: Optimize within each cluster
        cluster_weights, cluster_vars = self._optimize_within_clusters(
            cov_matrix, expected_returns, n_clusters, assignments
        )

        # Step 4: Allocate across clusters and combine weights
        return self._postprocess_optimization_results(
            cluster_weights, cluster_vars, n_clusters, assignments, n_assets, symbols
        )

    def _validate_optimization_inputs(
        self,
        cov_matrix: np.ndarray,
        expected_returns: Optional[np.ndarray],
        symbols: Optional[List[str]],
    ) -> Tuple[np.ndarray, Optional[np.ndarray], List[str]]:
        """Validate and sanitize optimization inputs."""
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
                enforce_psd=False,
            )
        except ValueError as e:
            log_optimization_failure(
                "nco.sanitize_covariance",
                e,
                {"original_shape": cov_matrix.shape},
            )
            raise

        n_assets = sanitized_cov.shape[0]

        if symbols is not None:
            symbols = [symbols[i] for i in valid_indices]
        else:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        if expected_returns is not None:
            expected_returns = expected_returns[valid_indices]

        return sanitized_cov, expected_returns, symbols

    def _preprocess_covariance_matrix(
        self,
        cov_matrix: np.ndarray,
        n_clusters: Optional[int],
    ) -> Tuple[int, np.ndarray, int, np.ndarray]:
        """Preprocess covariance matrix and create hierarchical clusters."""
        n_assets = cov_matrix.shape[0]

        corr_matrix = self._cov_to_corr(cov_matrix)
        distance = self._correlation_to_distance(corr_matrix)
        hierarchy = linkage(squareform(distance), method="ward")

        if n_clusters is None:
            n_clusters = self._optimal_n_clusters(n_assets, cov_matrix)

        n_clusters = max(2, min(n_clusters, n_assets // self._min_cluster_size))
        assignments = fcluster(hierarchy, n_clusters, criterion="maxclust")

        return n_assets, cov_matrix, n_clusters, assignments

    def _optimize_within_clusters(
        self,
        cov_matrix: np.ndarray,
        expected_returns: Optional[np.ndarray],
        n_clusters: int,
        assignments: np.ndarray,
    ) -> Tuple[Dict[int, np.ndarray], Dict[int, float]]:
        """Optimize weights within each cluster."""
        cluster_weights = {}
        cluster_vars = {}

        for cluster_id in range(1, n_clusters + 1):
            indices = np.where(assignments == cluster_id)[0]

            if len(indices) < self._min_cluster_size:
                cluster_weights[cluster_id] = np.ones(len(indices)) / len(indices)
            else:
                cluster_cov = cov_matrix[np.ix_(indices, indices)]
                cluster_ret = expected_returns[indices] if expected_returns is not None else None

                try:
                    if self._optimization_method == "sharpe" and cluster_ret is not None:
                        w = self._maximize_sharpe(cluster_cov, cluster_ret)
                    else:
                        w = self._minimize_variance(cluster_cov)
                    cluster_weights[cluster_id] = w
                except Exception as e:
                    log_optimization_failure(
                        f"nco.cluster_{cluster_id}_optimization",
                        e,
                        {"cluster_size": len(indices), "method": self._optimization_method},
                    )
                    cluster_weights[cluster_id] = np.ones(len(indices)) / len(indices)

            cluster_vars[cluster_id] = self._calculate_cluster_variance(
                cov_matrix, indices, cluster_weights[cluster_id]
            )

        return cluster_weights, cluster_vars

    def _postprocess_optimization_results(
        self,
        cluster_weights: Dict[int, np.ndarray],
        cluster_vars: Dict[int, float],
        n_clusters: int,
        assignments: np.ndarray,
        n_assets: int,
        symbols: List[str],
    ) -> NCOResult:
        """Allocate across clusters and combine with intra-cluster weights."""
        cluster_allocation = self._allocate_across_clusters(cluster_vars)
        final_weights = np.zeros(n_assets)

        for cluster_id in range(1, n_clusters + 1):
            indices = np.where(assignments == cluster_id)[0]
            intra_weights = cluster_weights[cluster_id]
            inter_weight = cluster_allocation[cluster_id]
            final_weights[indices] = intra_weights * inter_weight

        return NCOResult(
            weights=final_weights,
            cluster_weights=cluster_weights,
            cluster_allocation=cluster_allocation,
            n_clusters=n_clusters,
            symbols=symbols,
        )

    def _cov_to_corr(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Convert covariance to correlation."""
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr = cov_matrix / np.outer(std_devs, std_devs)
        np.fill_diagonal(corr, 1.0)
        return corr

    def _correlation_to_distance(self, corr_matrix: np.ndarray) -> np.ndarray:
        """Convert correlation to distance."""
        corr = np.clip(corr_matrix, -1.0, 1.0)
        return np.sqrt(0.5 * (1 - corr))

    def _optimal_n_clusters(
        self,
        n_assets: int,
        cov_matrix: np.ndarray,
    ) -> int:
        """
        Determine optimal number of clusters.

        Heuristic: cluster size between 2 and sqrt(n)

        Uses correlation-based heuristic:
        - High correlation (>0.7): fewer clusters (n/10)
        - Medium correlation (>0.5): moderate clusters (n/5)
        - Low correlation: more clusters (n/3)
        """
        n_assets // self._min_cluster_size
        min_clusters = 2

        # Use correlation-based heuristic
        # More correlated assets = fewer clusters
        avg_corr = np.mean(self._cov_to_corr(cov_matrix)[np.triu_indices(n_assets, k=1)])

        if avg_corr > HIGH_CORRELATION_THRESHOLD:
            return max(min_clusters, int(n_assets / 10))
        elif avg_corr > MEDIUM_CORRELATION_THRESHOLD:
            return max(min_clusters, int(n_assets / 5))
        else:
            return max(min_clusters, int(n_assets / 3))

    def _maximize_sharpe(
        self,
        cov_matrix: np.ndarray,
        expected_returns: np.ndarray,
        risk_free_rate: float = 0.0,
    ) -> np.ndarray:
        """
        Maximize Sharpe ratio within cluster.

        Args:
            cov_matrix: Cluster covariance matrix
            expected_returns: Cluster expected returns
            risk_free_rate: Risk-free rate

        Returns:
            Optimal weights
        """
        n_assets = len(expected_returns)
        objective = self._setup_sharpe_objective(cov_matrix, expected_returns, risk_free_rate)
        constraints, bounds, x0 = self._setup_optimization_constraints(n_assets)

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result.x if result.success else x0

    def _setup_sharpe_objective(
        self,
        cov_matrix: np.ndarray,
        expected_returns: np.ndarray,
        risk_free_rate: float,
    ):
        """Setup objective function for Sharpe maximization."""

        def objective(weights: np.ndarray) -> float:
            portfolio_return = float(weights @ expected_returns)
            portfolio_var = float(weights @ cov_matrix @ weights)
            portfolio_std = np.sqrt(portfolio_var)

            if portfolio_std == 0:
                return DEFAULT_NEG_INF_RETURN

            sharpe = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe

        return objective

    def _setup_optimization_constraints(
        self,
        n_assets: int,
    ) -> Tuple[list, list, np.ndarray]:
        """Setup constraints, bounds, and initial guess for optimization."""
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets
        return constraints, bounds, x0

    def _minimize_variance(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Minimize variance within cluster.

        Args:
            cov_matrix: Cluster covariance matrix

        Returns:
            Minimum variance weights
        """
        n_assets = cov_matrix.shape[0]

        def objective(weights: np.ndarray) -> float:
            return float(weights @ cov_matrix @ weights)

        constraints, bounds, x0 = self._setup_optimization_constraints(n_assets)

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result.x if result.success else x0

    def _calculate_cluster_variance(
        self,
        cov_matrix: np.ndarray,
        indices: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        """Calculate variance of a cluster."""
        sub_cov = cov_matrix[np.ix_(indices, indices)]
        return float(weights @ sub_cov @ weights)

    def _allocate_across_clusters(
        self,
        cluster_vars: Dict[int, float],
    ) -> Dict[int, float]:
        """
        Allocate weight across clusters using inverse variance.

        Args:
            cluster_vars: Dictionary of cluster_id -> variance

        Returns:
            Dictionary of cluster_id -> allocation weight
        """
        # Inverse variance allocation
        inv_var = {k: 1.0 / v for k, v in cluster_vars.items() if v > 0}

        if not inv_var:
            # All clusters have zero variance, use equal allocation
            n_clusters = len(cluster_vars)
            return dict.fromkeys(cluster_vars.keys(), 1.0 / n_clusters)

        total_inv_var = sum(inv_var.values())

        allocation = {k: v / total_inv_var for k, v in inv_var.items()}

        return allocation


def get_nco_with_multiple_n(
    cov_matrix: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
    symbols: Optional[List[str]] = None,
    n_clusters_range: Optional[List[int]] = None,
) -> Dict[int, NCOResult]:
    """
    Run NCO for multiple cluster numbers and return all results.

    Useful for selecting optimal number of clusters via cross-validation.

    Args:
        cov_matrix: Covariance matrix
        expected_returns: Expected returns
        symbols: Asset symbols
        n_clusters_range: List of n to try (None = auto-generate)

    Returns:
        Dictionary mapping n_clusters to NCOResult
    """
    # Validate covariance matrix
    is_valid, validated_cov, error_msg = validate_covariance_matrix(
        cov_matrix,
        check_psd=True,
        check_symmetry=True,
        enforce_psd=True,
    )

    if not is_valid:
        logger.error(f"Invalid covariance matrix: {error_msg}")
        return {}

    n_assets = validated_cov.shape[0]

    if n_clusters_range is None:
        # Try range from 2 to n/2
        n_clusters_range = list(range(2, max(3, n_assets // 2 + 1)))

    results = {}
    nco = NestedClusteredOptimizer()

    for n in n_clusters_range:
        try:
            result = nco.optimize(
                cov_matrix=validated_cov,
                expected_returns=expected_returns,
                symbols=symbols,
                n_clusters=n,
            )
            results[n] = result
        except Exception as e:
            log_optimization_failure(
                f"get_nco_with_multiple_n.n_clusters_{n}",
                e,
                {"n_clusters": n, "n_assets": n_assets},
            )
            # Continue with next n
            continue

    return results
