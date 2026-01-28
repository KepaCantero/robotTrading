"""
Nested Clustered Optimization (NCO) - López de Prado

Implements Nested Clustered Optimization which combines
hierarchical clustering with convex optimization.

Reference: Rule 03-lopez-de-prado-advances-financial-ml.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

from app.domain.services.portfolio_optimization.hrp import HierarchicalRiskParity


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
        min_cluster_size: int = 2,
        optimization_method: str = "sharpe",  # sharpe, min_variance
    ):
        """
        Initialize NCO optimizer.

        Args:
            min_cluster_size: Minimum assets per cluster
            optimization_method: Optimization method within clusters
        """
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
        """
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Step 1: Hierarchical clustering
        corr_matrix = self._cov_to_corr(cov_matrix)
        distance = self._correlation_to_distance(corr_matrix)
        hierarchy = linkage(squareform(distance), method="ward")

        # Determine number of clusters
        if n_clusters is None:
            n_clusters = self._optimal_n_clusters(n_assets, cov_matrix)

        # Get cluster assignments
        assignments = fcluster(hierarchy, n_clusters, criterion="maxclust")

        # Step 2: Optimize within each cluster
        cluster_weights = {}
        cluster_vars = {}

        for cluster_id in range(1, n_clusters + 1):
            indices = np.where(assignments == cluster_id)[0]

            if len(indices) < self._min_cluster_size:
                # Skip small clusters or use equal weight
                cluster_weights[cluster_id] = np.ones(len(indices)) / len(indices)
            else:
                # Extract cluster covariance
                cluster_cov = cov_matrix[np.ix_(indices, indices)]
                cluster_ret = expected_returns[indices] if expected_returns is not None else None

                # Optimize within cluster
                if self._optimization_method == "sharpe" and cluster_ret is not None:
                    w = self._maximize_sharpe(cluster_cov, cluster_ret)
                else:
                    w = self._minimize_variance(cluster_cov)

                cluster_weights[cluster_id] = w

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
        """
        max_clusters = n_assets // self._min_cluster_size
        min_clusters = 2

        # Use correlation-based heuristic
        # More correlated assets = fewer clusters
        avg_corr = np.mean(self._cov_to_corr(cov_matrix)[np.triu_indices(n_assets, k=1)])

        if avg_corr > 0.7:
            return max(min_clusters, int(n_assets / 10))
        elif avg_corr > 0.5:
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
                return -np.inf

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
        inv_var = {k: 1.0 / v for k, v in cluster_vars.items()}
        total_inv_var = sum(inv_var.values())

        allocation = {
            k: v / total_inv_var
            for k, v in inv_var.items()
        }

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
    n_assets = cov_matrix.shape[0]

    if n_clusters_range is None:
        # Try range from 2 to n/2
        n_clusters_range = list(range(2, max(3, n_assets // 2 + 1)))

    results = {}
    nco = NestedClusteredOptimizer()

    for n in n_clusters_range:
        try:
            result = nco.optimize(
                cov_matrix=cov_matrix,
                expected_returns=expected_returns,
                symbols=symbols,
                n_clusters=n,
            )
            results[n] = result
        except Exception:
            # Skip failed optimizations
            continue

    return results
