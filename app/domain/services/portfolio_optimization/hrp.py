"""
Hierarchical Risk Parity (HRP) - López de Prado

Implements Hierarchical Risk Parity portfolio optimization using
hierarchical clustering and inverse variance allocation.

Reference: Rule 03-lopez-de-prado-advances-financial-ml.md
Paper: López de Prado, M. (2016). "Building Diversified Portfolios
       that Outperform Out of Sample"
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list, cophenet
from scipy.spatial.distance import squareform


@dataclass
class HRPResult:
    """Result of Hierarchical Risk Parity optimization."""

    weights: np.ndarray  # HRP weights
    hierarchy: np.ndarray  # Linkage matrix (hierarchical clustering)
    order: List[int]  # Order of assets in hierarchy
    clusters: Dict[str, List[int]]  # Cluster assignments
    symbols: List[str]  # Asset symbols

    # Quality metrics
    cophenetic_corr: float  # Quality of dendrogram preservation

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}

    def get_cluster_allocation(
        self,
        n_clusters: int,
    ) -> Dict[int, List[str]]:
        """
        Get cluster allocation for specified number of clusters.

        Args:
            n_clusters: Number of clusters to extract

        Returns:
            Dictionary of cluster_id -> list of symbols
        """
        from scipy.cluster.hierarchy import fcluster

        # Get cluster assignments
        assignments = fcluster(self.hierarchy, n_clusters, criterion="maxclust")

        # Group symbols by cluster
        cluster_map = {}
        for idx, cluster_id in enumerate(assignments):
            if cluster_id not in cluster_map:
                cluster_map[cluster_id] = []
            cluster_map[cluster_id].append(self.symbols[idx])

        return cluster_map


class HierarchicalRiskParity:
    """
    Hierarchical Risk Parity portfolio optimizer.

    HRP constructs portfolios by:
    1. Hierarchical clustering of assets based on correlation
    2. Bisectional allocation within clusters using inverse variance

    Advantages over MVO:
    - Does not require invertibility of covariance matrix
    - More robust out-of-sample
    - Naturally handles multicollinearity
    - No need to estimate expected returns

    Reference: López de Prado, M. (2016)
    """

    def __init__(
        self,
        linkage_method: str = "ward",  # ward, single, complete, average
        distance_metric: str = "euclidean",  # euclidean, correlation
    ):
        """
        Initialize HRP optimizer.

        Args:
            linkage_method: Linkage method for hierarchical clustering
            distance_metric: Distance metric for clustering
        """
        self._linkage_method = linkage_method
        self._distance_metric = distance_metric

    def optimize(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
    ) -> HRPResult:
        """
        Compute HRP portfolio weights.

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols

        Returns:
            HRPResult with optimal weights and hierarchy
        """
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Step 1: Compute distance matrix from correlation
        corr_matrix = self._cov_to_corr(cov_matrix)
        distance = self._correlation_to_distance(corr_matrix)

        # Step 2: Hierarchical clustering
        hierarchy = linkage(
            squareform(distance),
            method=self._linkage_method,
        )

        # Step 3: Get dendrogram order
        order = leaves_list(hierarchy)

        # Step 4: Compute HRP weights using bisectional allocation
        weights = self._hrp_weights(cov_matrix, hierarchy)

        # Step 5: Calculate quality metric
        cophenetic_corr = cophenet(hierarchy, squareform(distance))[0]

        # Step 6: Extract clusters (at 2-cluster level for simplicity)
        clusters = self._extract_clusters(hierarchy, symbols)

        return HRPResult(
            weights=weights,
            hierarchy=hierarchy,
            order=list(order),
            clusters=clusters,
            symbols=symbols,
            cophenetic_corr=float(cophenetic_corr),
        )

    def _cov_to_corr(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Convert covariance to correlation."""
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr = cov_matrix / np.outer(std_devs, std_devs)
        np.fill_diagonal(corr, 1.0)
        return corr

    def _correlation_to_distance(
        self,
        corr_matrix: np.ndarray,
    ) -> np.ndarray:
        """
        Convert correlation to distance.

        Distance = sqrt(0.5 * (1 - correlation))
        This ensures 0 <= distance <= sqrt(2)
        """
        # Handle any numerical issues
        corr = np.clip(corr_matrix, -1.0, 1.0)
        distance = np.sqrt(0.5 * (1 - corr))
        return distance

    def _hrp_weights(
        self,
        cov_matrix: np.ndarray,
        hierarchy: np.ndarray,
    ) -> np.ndarray:
        """
        Compute HRP weights using bisectional allocation.

        Recursive algorithm:
        1. Split cluster into two sub-clusters
        2. Allocate weight based on inverse variance
        3. Recurse into sub-clusters

        Args:
            cov_matrix: Covariance matrix
            hierarchy: Linkage matrix from scipy

        Returns:
            HRP weights
        """
        n_assets = cov_matrix.shape[0]

        # Initialize equal weights
        weights = np.ones(n_assets) / n_assets

        # Get cluster indices for bisection
        cluster_indices = self._get_cluster_items(hierarchy, n_assets)

        # Allocate weights through bisection
        weights = self._bisect_cluster_weights(
            cov_matrix,
            cluster_indices,
            weights,
        )

        return weights

    def _get_cluster_items(
        self,
        hierarchy: np.ndarray,
        n_assets: int,
    ) -> Dict[int, List[int]]:
        """
        Get all clusters from hierarchy.

        Returns dictionary mapping cluster_id to list of asset indices.
        """
        from scipy.cluster.hierarchy import fcluster

        # Get clusters at various levels
        clusters = {}
        n_clusters = n_assets

        for n in range(2, n_clusters + 1):
            assignments = fcluster(hierarchy, n, criterion="maxclust")
            for cluster_id in np.unique(assignments):
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].extend(
                    np.where(assignments == cluster_id)[0].tolist()
                )

        return clusters

    def _bisect_cluster_weights(
        self,
        cov_matrix: np.ndarray,
        clusters: Dict[int, List[int]],
        initial_weights: np.ndarray,
    ) -> np.ndarray:
        """
        Bisect clusters and allocate weights based on inverse variance.

        Args:
            cov_matrix: Covariance matrix
            clusters: Dictionary of cluster_id -> asset indices
            initial_weights: Initial equal weights

        Returns:
            Final HRP weights
        """
        weights = initial_weights.copy()

        # For each cluster split, reallocate weights
        # This is a simplified version - full implementation would
        # traverse the dendrogram recursively
        n_assets = cov_matrix.shape[0]

        # Single bisection (can be extended for full recursive)
        mid = n_assets // 2

        # Calculate variances of two halves
        left_indices = list(range(mid))
        right_indices = list(range(mid, n_assets))

        var_left = self._get_cluster_variance(cov_matrix, left_indices, weights[left_indices])
        var_right = self._get_cluster_variance(cov_matrix, right_indices, weights[right_indices])

        # Allocate based on inverse variance
        total_inv_var = 1.0 / var_left + 1.0 / var_right

        weights[left_indices] *= (1.0 / var_left) / total_inv_var / np.sum(weights[left_indices])
        weights[right_indices] *= (1.0 / var_right) / total_inv_var / np.sum(weights[right_indices])

        return weights

    def _get_cluster_variance(
        self,
        cov_matrix: np.ndarray,
        indices: List[int],
        weights: np.ndarray,
    ) -> float:
        """Calculate variance of a cluster."""
        if len(indices) == 0:
            return 1.0

        # Extract sub-covariance and weights
        sub_cov = cov_matrix[np.ix_(indices, indices)]
        sub_weights = weights[indices]

        # Normalize weights
        sub_weights = sub_weights / sub_weights.sum()

        # Calculate variance
        variance = float(sub_weights @ sub_cov @ sub_weights)

        return variance

    def _extract_clusters(
        self,
        hierarchy: np.ndarray,
        symbols: List[str],
    ) -> Dict[str, List[int]]:
        """
        Extract cluster assignments from hierarchy.

        Args:
            hierarchy: Linkage matrix
            symbols: Asset symbols

        Returns:
            Dictionary with cluster information
        """
        from scipy.cluster.hierarchy import fcluster

        # Get 2-cluster split (main bisection)
        assignments = fcluster(hierarchy, 2, criterion="maxclust")

        cluster_0 = [i for i, c in enumerate(assignments) if c == 1]
        cluster_1 = [i for i, c in enumerate(assignments) if c == 2]

        return {
            "cluster_0": cluster_0,
            "cluster_1": cluster_1,
        }

    def get_dendrogram_data(
        self,
        cov_matrix: np.ndarray,
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for plotting dendrogram.

        Args:
            cov_matrix: Covariance matrix

        Returns:
            Tuple of (linkage_matrix, leaf_order)
        """
        # Compute correlation distance
        corr = self._cov_to_corr(cov_matrix)
        distance = self._correlation_to_distance(corr)

        # Hierarchical clustering
        hierarchy = linkage(
            squareform(distance),
            method=self._linkage_method,
        )

        # Leaf order
        order = leaves_list(hierarchy)

        return hierarchy, list(order)


def inverse_variance_weights(cov_matrix: np.ndarray) -> np.ndarray:
    """
    Compute inverse variance weights (IVP).

    Simple baseline: w_i ∝ 1/σ_i²

    Args:
        cov_matrix: Covariance matrix

    Returns:
        Inverse variance weights
    """
    variances = np.diag(cov_matrix)
    inv_var = 1.0 / variances
    weights = inv_var / inv_var.sum()
    return weights
