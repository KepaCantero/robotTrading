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
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

from app.domain.services.portfolio_optimization.hrp import HierarchicalRiskParity
from app.domain.services.portfolio_optimization._validation import (
    validate_covariance_matrix,
    sanitize_covariance_matrix,
    log_optimization_failure,
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
                enforce_psd=False,  # Already enforced
            )
        except ValueError as e:
            log_optimization_failure(
                "nco.sanitize_covariance",
                e,
                {"original_shape": cov_matrix.shape},
            )
            raise

        cov_matrix = sanitized_cov
        n_assets = cov_matrix.shape[0]

        # Filter symbols and expected returns
        if symbols is not None:
            symbols = [symbols[i] for i in valid_indices]
        else:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        if expected_returns is not None:
            expected_returns = expected_returns[valid_indices]

        # Step 1: Hierarchical clustering
        corr_matrix = self._cov_to_corr(cov_matrix)
        distance = self._correlation_to_distance(corr_matrix)
        hierarchy = linkage(squareform(distance), method="ward")

        # Determine number of clusters
        if n_clusters is None:
            n_clusters = self._optimal_n_clusters(n_assets, cov_matrix)

        n_clusters = max(2, min(n_clusters, n_assets // self._min_cluster_size))

        # Get cluster assignments
        assignments = fcluster(hierarchy, n_clusters, criterion="maxclust")

        # Step 2: Optimize within each cluster
        cluster_weights = {}
        cluster_vars = {}

        for cluster_id in range(1, n_clusters + 1):
            indices = np.where(assignments == cluster_id)[0]

            if len(indices) < self._min_cluster_size:
                # Small cluster: use equal weight
                cluster_weights[cluster_id] = np.ones(len(indices)) / len(indices)
            else:
                # Extract cluster covariance
                cluster_cov = cov_matrix[np.ix_(indices, indices)]
                cluster_ret = expected_returns[indices] if expected_returns is not None else None

                try:
                    # Optimize within cluster
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
                    # Fallback to equal weights
                    cluster_weights[cluster_id] = np.ones(len(indices)) / len(indices)

            # Calculate cluster variance for allocation
            cluster_vars[cluster_id] = self._calculate_cluster_variance(
                cov_matrix, indices, cluster_weights[cluster_id]
            )

        # Step 3: Allocate across clusters (inverse variance)
        cluster_allocation = self._allocate_across_clusters(cluster_vars)

        # Step 4: Combine intra-cluster and inter-cluster weights
        final_weights = np.zeros(n_assets)

        for cluster_id in range(1, n_clusters + 1):
            indices = np.where(assignments == cluster_id)[0]
            intra_weights = cluster_weights[cluster_id]
            inter_weight = cluster_allocation[cluster_id]

            # Combine: final = inter_allocation * intra_weights
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
        max_clusters = n_assets // self._min_cluster_size
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

        # Objective: negative Sharpe
        def objective(weights: np.ndarray) -> float:
            portfolio_return = float(weights @ expected_returns)
            portfolio_var = float(weights @ cov_matrix @ weights)
            portfolio_std = np.sqrt(portfolio_var)

            if portfolio_std == 0:
                return DEFAULT_NEG_INF_RETURN

            sharpe = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds (no short selling within cluster)
        bounds = [(0.0, 1.0) for _ in range(n_assets)]

        # Initial guess (equal weight)
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result.x if result.success else x0

    def _minimize_variance(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Minimize variance within cluster.

        Args:
            cov_matrix: Cluster covariance matrix

        Returns:
            Minimum variance weights
        """
        n_assets = cov_matrix.shape[0]

        # Objective: portfolio variance
        def objective(weights: np.ndarray) -> float:
            return float(weights @ cov_matrix @ weights)

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(0.0, 1.0) for _ in range(n_assets)]

        # Initial guess
        x0 = np.ones(n_assets) / n_assets

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
            return {k: 1.0 / n_clusters for k in cluster_vars.keys()}

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
