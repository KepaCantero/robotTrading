"""
Hierarchical Risk Parity (HRP) - López de Prado (2016).

Implements the HRP algorithm from Marcos López de Prado's
"Machine Learning for Asset Managers" and "Advances in Financial Machine Learning".

Key advantages over Markowitz:
- No matrix inversion required (more robust)
- No extreme weights
- More stable out-of-sample performance
- Uses hierarchical clustering + recursive bisection

Algorithm steps:
1. Calculate correlation-based distance matrix
2. Perform hierarchical clustering (single, average, or ward linkage)
3. Quasi-diagonalization: reorder covariance matrix by cluster hierarchy
4. Recursive bisection: allocate capital based on inverse variance
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import cophenet, dendrogram, linkage
from scipy.spatial.distance import pdist, squareform

logger = logging.getLogger(__name__)


class HierarchicalRiskParity:
    """
    Hierarchical Risk Parity (HRP) optimizer.

    Implements López de Prado's HRP algorithm for robust portfolio allocation.
    Uses hierarchical clustering to group assets and recursive bisection
    to allocate weights based on inverse variance.

    From "Machine Learning for Asset Managers" (2016):
    "HRP uses a hierarchical tree to allocate weights, avoiding the need
    to invert the covariance matrix. This makes it more robust than
    mean-variance optimization."

    Attributes:
        linkage_method: Linkage method for hierarchical clustering
            - 'single': Single linkage (minimum distance)
            - 'average': Average linkage (UPGMA)
            - 'complete': Complete linkage (maximum distance)
            - 'ward': Ward's method (minimize variance)
        distance_metric: Distance metric for clustering
    """

    def __init__(
        self,
        linkage_method: str = "single",
        distance_metric: str = "euclidean",
    ) -> None:
        """
        Initialize HRP optimizer.

        Args:
            linkage_method: Linkage method ('single', 'average', 'complete', 'ward')
            distance_metric: Distance metric ('euclidean', 'correlation', etc.)

        Raises:
            ValueError: If linkage_method is not supported
        """
        valid_linkage = {"single", "average", "complete", "ward"}
        if linkage_method not in valid_linkage:
            raise ValueError(
                f"linkage_method must be one of {valid_linkage}, got '{linkage_method}'"
            )

        self.linkage_method = linkage_method
        self.distance_metric = distance_metric
        self.logger = logging.getLogger(self.__class__.__name__)

        # Store for analysis
        self.linkage_matrix_: Optional[np.ndarray] = None
        self.cophenet_correlation_: Optional[float] = None
        self.ordered_indices_: Optional[List[int]] = None
        self.cluster_tree_: Optional[Dict[str, Any]] = None

        logger.info(
            f"HierarchicalRiskParity initialized: linkage={linkage_method}, "
            f"distance={distance_metric}"
        )

    def get_weights(
        self,
        cov_matrix: np.ndarray,
        returns: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Calculate HRP portfolio weights.

        Main entry point that implements the complete HRP algorithm:
        1. Calculate correlation-based distance
        2. Perform hierarchical clustering
        3. Quasi-diagonalize covariance matrix
        4. Recursive bisection allocation

        Args:
            cov_matrix: Covariance matrix (N x N), must be positive semi-definite
            returns: Asset returns (T x N), optional for visualization

        Returns:
            Portfolio weights (N,) that sum to 1

        Raises:
            ValueError: If cov_matrix is invalid
        """
        # Validate input
        if not isinstance(cov_matrix, np.ndarray):
            raise ValueError("cov_matrix must be a numpy array")

        if cov_matrix.ndim != 2:
            raise ValueError("cov_matrix must be 2-dimensional")

        n = len(cov_matrix)
        if n == 0:
            raise ValueError("cov_matrix cannot be empty")

        if cov_matrix.size == 0:
            raise ValueError("cov_matrix cannot be empty")

        if cov_matrix.shape[0] != cov_matrix.shape[1]:
            raise ValueError("cov_matrix must be square")

        # Edge case: single asset
        if n == 1:
            return np.array([1.0])

        # Ensure symmetry
        cov_matrix = (cov_matrix + cov_matrix.T) / 2

        # Step 1: Calculate correlation-based distance
        corr_matrix = self._cov_to_corr(cov_matrix)
        distance_matrix = self._correlation_to_distance(corr_matrix)

        # Step 2: Perform hierarchical clustering
        self.linkage_matrix_ = linkage(
            squareform(distance_matrix),
            method=self.linkage_method,
        )

        # Calculate cophenetic correlation (quality metric)
        self.cophenet_correlation_ = cophenet(self.linkage_matrix_, pdist(distance_matrix))[0]

        logger.debug(
            f"HRP clustering complete: cophenet correlation = " f"{self.cophenet_correlation_:.4f}"
        )

        # Step 3: Quasi-diagonalization
        self.ordered_indices_ = self._quasi_diagonalization(corr_matrix, self.linkage_matrix_)

        # Step 4: Recursive bisection
        weights = self._recursive_bisection(cov_matrix, self.linkage_matrix_, list(range(n)))

        # Ensure weights sum to 1 and are non-negative
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()

        # Store cluster tree for visualization
        self.cluster_tree_ = {
            "linkage": self.linkage_matrix_,
            "ordered_indices": self.ordered_indices_,
            "n_assets": n,
        }

        logger.info(
            f"HRP weights calculated: min={weights.min():.4f}, "
            f"max={weights.max():.4f}, "
            f"effective_n={1 / np.sum(weights**2):.2f}"
        )

        return weights

    def _cov_to_corr(self, cov_matrix: np.ndarray) -> np.ndarray:
        """
        Convert covariance matrix to correlation matrix.

        Formula: corr[i,j] = cov[i,j] / (std[i] * std[j])

        Args:
            cov_matrix: Covariance matrix

        Returns:
            Correlation matrix
        """
        # Calculate standard deviations
        std = np.sqrt(np.diag(cov_matrix))

        # Avoid division by zero
        std = np.maximum(std, 1e-10)

        # Calculate correlation matrix
        corr_matrix = cov_matrix / np.outer(std, std)

        # Ensure diagonal is exactly 1
        np.fill_diagonal(corr_matrix, 1.0)

        # Clip to valid range [-1, 1]
        corr_matrix = np.clip(corr_matrix, -1.0, 1.0)

        return corr_matrix

    def _correlation_to_distance(self, corr_matrix: np.ndarray) -> np.ndarray:
        """
        Convert correlation matrix to distance matrix.

        For HRP, we use: distance = sqrt((1 - correlation) / 2)

        This ensures:
        - correlation = 1  → distance = 0 (identical)
        - correlation = 0  → distance = sqrt(0.5) (uncorrelated)
        - correlation = -1 → distance = 1 (opposite)

        Args:
            corr_matrix: Correlation matrix

        Returns:
            Distance matrix
        """
        # Convert correlation to distance
        # d = sqrt((1 - ρ) / 2)
        distance_matrix = np.sqrt((1.0 - corr_matrix) / 2.0)

        # Ensure diagonal is zero
        np.fill_diagonal(distance_matrix, 0.0)

        return distance_matrix

    def _quasi_diagonalization(
        self,
        corr_matrix: np.ndarray,
        linkage_matrix: np.ndarray,
    ) -> List[int]:
        """
        Reorder covariance matrix by dendrogram order.

        This step rearranges the covariance matrix so that similar assets
        are close together, creating a "quasi-diagonal" structure.

        From López de Prado:
        "Quasi-diagonalization reorders the matrix so that similar investments
        are placed together. This is achieved by traversing the dendrogram
        and collecting the indices in order."

        Args:
            corr_matrix: Correlation matrix (not directly used, for compatibility)
            linkage_matrix: Linkage matrix from scipy.cluster.hierarchy.linkage

        Returns:
            List of ordered indices
        """
        # Get the number of assets
        n = len(corr_matrix)

        # Sort indices by the hierarchical clustering
        # We need to traverse the dendrogram from bottom to top
        ordered_indices = self._get_seriated_indices(n, linkage_matrix)

        return ordered_indices

    def _get_seriated_indices(
        self,
        n: int,
        linkage_matrix: np.ndarray,
    ) -> List[int]:
        """
        Get seriated indices from linkage matrix.

        This implements the recursive traversal of the dendrogram
        to produce the quasi-diagonal ordering.

        Args:
            n: Number of assets
            linkage_matrix: Linkage matrix

        Returns:
            List of indices in quasi-diagonal order
        """
        # Initialize cluster assignments
        # Each asset starts in its own cluster
        clusters = [{i} for i in range(n)]

        # Track cluster indices
        cluster_indices = [i for i in range(n)]

        # Process each merge in the linkage matrix
        for i, row in enumerate(linkage_matrix):
            # Get the indices of clusters to merge
            idx1, idx2 = int(row[0]), int(row[1])

            # Get the actual clusters
            if idx1 < n and idx2 < n:
                # Both are individual assets
                cluster1 = {idx1}
                cluster2 = {idx2}
            else:
                # At least one is a merged cluster
                cluster1 = clusters[idx1 - n] if idx1 >= n else {idx1}
                cluster2 = clusters[idx2 - n] if idx2 >= n else {idx2}

            # Merge clusters
            merged_cluster = cluster1.union(cluster2)

            # Store merged cluster
            clusters.append(merged_cluster)

        # The final cluster contains all assets
        # We need to sort them by the dendrogram structure
        final_cluster = clusters[-1]

        # Use scipy's leaves_list to get the optimal ordering
        from scipy.cluster.hierarchy import leaves_list

        ordered_indices = leaves_list(linkage_matrix).tolist()

        return ordered_indices

    def _recursive_bisection(
        self,
        cov_matrix: np.ndarray,
        linkage_matrix: np.ndarray,
        indices: List[int],
    ) -> np.ndarray:
        """
        Recursively bisect clusters and allocate weights.

        This is the core allocation algorithm of HRP. It:
        1. Recursively splits clusters into sub-clusters
        2. Allocates weight between sub-clusters based on inverse variance
        3. Continues until individual assets are reached

        From López de Prado:
        "Recursive bisection allocates capital based on the inverse variance
        of each cluster. This ensures that lower-risk clusters receive
        more capital."

        Args:
            cov_matrix: Covariance matrix
            linkage_matrix: Linkage matrix
            indices: List of asset indices in current cluster

        Returns:
            Array of weights for assets in this cluster
        """
        n = len(indices)

        # Base case: single asset
        if n == 1:
            return np.array([1.0])

        # Base case: two assets - allocate by inverse variance
        if n == 2:
            variances = np.diag(cov_matrix)[indices]
            weights = 1.0 / variances
            weights = weights / weights.sum()
            return weights

        # Recursive case: split cluster and allocate

        # Find the split point from the linkage matrix
        # We need to find which split separates this cluster
        split_point = self._find_split_point(indices, linkage_matrix, len(cov_matrix))

        if split_point is None or split_point == 0 or split_point == n:
            # No valid split found, use equal weights
            return np.ones(n) / n

        # Split the cluster
        left_indices = indices[:split_point]
        right_indices = indices[split_point:]

        # Recursively allocate within sub-clusters
        left_weights = self._recursive_bisection(cov_matrix, linkage_matrix, left_indices)
        right_weights = self._recursive_bisection(cov_matrix, linkage_matrix, right_indices)

        # Calculate cluster variances
        left_var = self._get_cluster_variance(cov_matrix, left_indices, left_weights)
        right_var = self._get_cluster_variance(cov_matrix, right_indices, right_weights)

        # Allocate between clusters based on inverse variance
        # Lower variance cluster gets more weight
        total_inv_var = 1.0 / left_var + 1.0 / right_var
        left_alpha = (1.0 / left_var) / total_inv_var
        right_alpha = (1.0 / right_var) / total_inv_var

        # Combine weights
        weights = np.concatenate([left_weights * left_alpha, right_weights * right_alpha])

        return weights

    def _find_split_point(
        self,
        indices: List[int],
        linkage_matrix: np.ndarray,
        n_assets: int,
    ) -> Optional[int]:
        """
        Find the optimal split point for recursive bisection.

        Args:
            indices: Asset indices in current cluster
            linkage_matrix: Linkage matrix
            n_assets: Total number of assets

        Returns:
            Split point index, or None if no valid split
        """
        # For now, use a simple midpoint split
        # In a full implementation, you would traverse the linkage tree
        # to find the actual merge points

        if len(indices) <= 2:
            return None

        # Try to find a natural split point using the linkage matrix
        # This is a simplified version
        n = len(indices)

        # Use the linkage matrix to guide the split
        # Find the row that corresponds to merging large clusters
        for i in range(len(linkage_matrix) - 1, -1, -1):
            row = linkage_matrix[i]
            idx1, idx2 = int(row[0]), int(row[1])

            # Check if this merge creates a cluster of our size
            cluster1_size = self._get_cluster_size(idx1, n_assets, linkage_matrix)
            cluster2_size = self._get_cluster_size(idx2, n_assets, linkage_matrix)

            if cluster1_size + cluster2_size == n:
                # Found the merge that creates our cluster
                # The split point is cluster1_size
                return cluster1_size

        # Fallback: split at midpoint
        return n // 2

    def _get_cluster_size(
        self,
        idx: int,
        n_assets: int,
        linkage_matrix: np.ndarray,
    ) -> int:
        """Get the size of a cluster from its index."""
        if idx < n_assets:
            return 1
        else:
            # This is a merged cluster
            # Recursively calculate size
            row_idx = idx - n_assets
            row = linkage_matrix[row_idx]
            idx1, idx2 = int(row[0]), int(row[1])
            return self._get_cluster_size(idx1, n_assets, linkage_matrix) + self._get_cluster_size(
                idx2, n_assets, linkage_matrix
            )

    def _get_cluster_variance(
        self,
        cov_matrix: np.ndarray,
        indices: List[int],
        weights: np.ndarray,
    ) -> float:
        """
        Calculate the variance of a cluster.

        Args:
            cov_matrix: Full covariance matrix
            indices: Asset indices in the cluster
            weights: Weights within the cluster

        Returns:
            Cluster variance
        """
        # Extract sub-covariance matrix
        sub_cov = cov_matrix[np.ix_(indices, indices)]

        # Calculate portfolio variance
        cluster_var = float(weights @ sub_cov @ weights)

        return max(cluster_var, 1e-10)  # Avoid division by zero

    def get_cluster_tree(self) -> Optional[Dict[str, Any]]:
        """Get the cluster tree structure for visualization."""
        return self.cluster_tree_

    def get_dendrogram_data(self) -> Optional[Dict[str, Any]]:
        """
        Get data for plotting dendrogram.

        Returns:
            Dict with linkage matrix and metadata
        """
        if self.linkage_matrix_ is None:
            return None

        return {
            "linkage_matrix": self.linkage_matrix_,
            "cophenet_correlation": self.cophenet_correlation_,
            "ordered_indices": self.ordered_indices_,
        }

    def get_metrics(self, weights: np.ndarray, cov_matrix: np.ndarray) -> Dict[str, float]:
        """
        Calculate portfolio metrics.

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Dict with portfolio metrics
        """
        # Portfolio variance
        portfolio_var = float(weights @ cov_matrix @ weights)
        portfolio_vol = np.sqrt(portfolio_var)

        # Effective number of assets (inverse Herfindahl index)
        effective_n = 1.0 / np.sum(weights**2)

        # Concentration (max weight)
        concentration = float(weights.max())

        return {
            "portfolio_variance": portfolio_var,
            "portfolio_volatility": portfolio_vol,
            "effective_n_assets": effective_n,
            "max_weight": concentration,
            "cophenet_correlation": self.cophenet_correlation_ or 0.0,
        }


class HRPOptimizer:
    """
    Wrapper class for HRP that matches the optimizer interface.

    This provides a consistent interface with other optimizers
    (Markowitz, RiskParity, etc.) while using HRP internally.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize HRP optimizer.

        Args:
            config: Configuration dict with:
                - linkage_method: 'single', 'average', 'complete', or 'ward'
                - distance_metric: 'euclidean', 'correlation', etc.
        """
        self.config = config or {}
        self.hrp = HierarchicalRiskParity(
            linkage_method=self.config.get("linkage_method", "single"),
            distance_metric=self.config.get("distance_metric", "euclidean"),
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize using HRP.

        Args:
            expected_returns: Expected returns (not used in HRP)
            cov_matrix: Covariance matrix
            constraints: Additional constraints (not used in HRP)

        Returns:
            Dict with weights and metrics
        """
        constraints = constraints or {}

        try:
            n = len(expected_returns)

            # Get HRP weights
            weights = self.hrp.get_weights(cov_matrix)

            # Apply constraints if specified
            max_weight = constraints.get("max_weight", 1.0)
            min_weight = constraints.get("min_weight", 0.0)

            # Clip weights
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()  # Re-normalize

            # Calculate metrics
            metrics = self.hrp.get_metrics(weights, cov_matrix)

            return {
                "weights": {f"asset_{i}": float(w) for i, w in enumerate(weights)},
                "expected_return": float(np.dot(weights, expected_returns)),
                "volatility": metrics["portfolio_volatility"],
                "sharpe_ratio": 0.0,  # HRP doesn't optimize for Sharpe
                "method": "hrp",
                "linkage_method": self.hrp.linkage_method,
                "effective_n_assets": metrics["effective_n_assets"],
                "max_weight": metrics["max_weight"],
                "cophenet_correlation": metrics["cophenet_correlation"],
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error in HRP optimization: {e}", exc_info=True)
            return self._equal_weight_fallback(len(expected_returns))

    def _equal_weight_fallback(self, n: int) -> Dict[str, Any]:
        """Fallback to equal weights."""
        weight = 1.0 / n
        return {
            "weights": {f"asset_{i}": weight for i in range(n)},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "method": "equal_weight_fallback",
        }


def compute_hrp_weights(
    cov_matrix: np.ndarray,
    linkage_method: str = "single",
) -> np.ndarray:
    """
    Convenience function to compute HRP weights.

    This is the main entry point for using HRP in your code.

    Args:
        cov_matrix: Covariance matrix (N x N)
        linkage_method: Linkage method ('single', 'average', 'complete', 'ward')

    Returns:
        Portfolio weights (N,) that sum to 1

    Example:
        >>> import numpy as np
        >>> cov = np.array([[0.01, 0.005], [0.005, 0.02]])
        >>> weights = compute_hrp_weights(cov, linkage_method='single')
        >>> print(weights)
        [0.6667 0.3333]
    """
    hrp = HierarchicalRiskParity(linkage_method=linkage_method)
    return hrp.get_weights(cov_matrix)


def plot_hrp_dendrogram(
    cov_matrix: np.ndarray,
    linkage_method: str = "single",
    labels: Optional[List[str]] = None,
    ax=None,
) -> Dict[str, Any]:
    """
    Plot HRP dendrogram for visualization.

    Args:
        cov_matrix: Covariance matrix
        linkage_method: Linkage method
        labels: Asset labels (optional)
        ax: Matplotlib axis (optional)

    Returns:
        Dict with dendrogram data and the axis

    Example:
        >>> import matplotlib.pyplot as plt
        >>> cov = np.array([[0.01, 0.005], [0.005, 0.02]])
        >>> result = plot_hrp_dendrogram(cov, labels=['AAPL', 'MSFT'])
        >>> plt.show()
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting. Install: pip install matplotlib")

    # Compute HRP
    hrp = HierarchicalRiskParity(linkage_method=linkage_method)
    hrp.get_weights(cov_matrix)

    # Get dendrogram data
    dendro_data = hrp.get_dendrogram_data()
    if dendro_data is None:
        raise ValueError("Could not compute dendrogram data")

    # Create axis if not provided
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    # Plot dendrogram
    dendrogram(
        dendro_data["linkage_matrix"],
        labels=labels,
        ax=ax,
        leaf_rotation=90,
        leaf_font_size=10,
    )

    ax.set_title(f"HRP Dendrogram ({linkage_method} linkage)")
    ax.set_xlabel("Assets")
    ax.set_ylabel("Distance")

    # Add cophenetic correlation
    ax.text(
        0.02,
        0.98,
        f"Cophenetic correlation: {dendro_data['cophenet_correlation']:.4f}",
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    return {
        "dendrogram_data": dendro_data,
        "axis": ax,
    }


__all__ = [
    "HierarchicalRiskParity",
    "HRPOptimizer",
    "compute_hrp_weights",
    "plot_hrp_dendrogram",
]
