"""
Nested Clustered Optimization (NCO) - López de Prado (2019)

This module implements the Nested Clustered Optimization (NCO) methodology
developed by Marcos López de Prado. NCO addresses the limitations of
traditional mean-variance optimization by:

1. Clustering assets based on correlation distance
2. Optimizing within each cluster separately
3. Allocating capital across clusters based on risk contribution

Reference:
    López de Prado, M. (2019). "Machine Learning for Asset Managers"
    Chapter 16: Nested Clustered Optimization (NCO)

Key concepts:
    - Correlation distance: d[i,j] = sqrt(0.5 * (1 - corr[i,j]))
    - Within-cluster optimization: Optimize weights for assets in same cluster
    - Cross-cluster allocation: Allocate capital to clusters based on inverse volatility
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.optimize import minimize
from sklearn.cluster import DBSCAN, KMeans

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class ClusteringMethod(str, Enum):
    """Supported clustering methods for NCO."""

    KMEANS = "kmeans"
    DBSCAN = "dbscan"


@dataclass(frozen=True)
class NCOConfig:
    """
    Configuration for Nested Clustered Optimization.

    Attributes:
        n_clusters: Number of clusters for K-means (default: 5)
        clustering_method: Clustering algorithm to use ('kmeans' or 'dbscan')
        dbscan_eps: Maximum distance between samples for DBSCAN (default: 0.5)
        min_samples: Minimum samples in neighborhood for DBSCAN (default: 2)
        min_cluster_size: Minimum cluster size to consider valid (default: 2)
        max_weight_single_asset: Maximum weight for any single asset (default: 0.20)
        risk_free_rate: Risk-free rate for Sharpe ratio calculation (default: 0.02)
        random_state: Random seed for reproducibility (default: 42)
    """

    n_clusters: int = 5
    clustering_method: ClusteringMethod = ClusteringMethod.KMEANS
    dbscan_eps: float = 0.5
    min_samples: int = 2
    min_cluster_size: int = 2
    max_weight_single_asset: float = 0.20
    risk_free_rate: float = 0.02
    random_state: int = 42

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.n_clusters < 2:
            raise ValueError("n_clusters must be at least 2")
        if self.dbscan_eps <= 0:
            raise ValueError("dbscan_eps must be positive")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if self.min_cluster_size < 1:
            raise ValueError("min_cluster_size must be at least 1")
        if not 0 < self.max_weight_single_asset <= 1:
            raise ValueError("max_weight_single_asset must be in (0, 1]")


@dataclass
class NCOResult:
    """
    Result from Nested Clustered Optimization.

    Attributes:
        weights: Final optimized weights for each asset (N,)
        cluster_labels: Cluster assignment for each asset (N,)
        n_clusters: Number of clusters found/created
        expected_return: Portfolio expected return (annualized)
        expected_risk: Portfolio expected risk (annualized)
        sharpe_ratio: Portfolio Sharpe ratio
        cluster_weights: Weight allocated to each cluster (n_clusters,)
        within_cluster_weights: Dictionary of cluster_id -> asset weights
        converged: Whether optimization converged successfully
    """

    weights: NDArray[np.float64]
    cluster_labels: NDArray[np.int32]
    n_clusters: int
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    cluster_weights: NDArray[np.float64]
    within_cluster_weights: dict[int, NDArray[np.float64]]
    converged: bool = True

    def get_weight_dict(self, asset_names: list[str]) -> dict[str, float]:
        """
        Get weights as a dictionary mapping asset names to weights.

        Args:
            asset_names: List of asset names corresponding to weights

        Returns:
            Dictionary mapping asset names to their NCO weights

        Raises:
            ValueError: If length of asset_names doesn't match weights
        """
        if len(asset_names) != len(self.weights):
            raise ValueError(
                f"Number of asset names ({len(asset_names)}) must match "
                f"number of weights ({len(self.weights)})"
            )

        return {name: float(weight) for name, weight in zip(asset_names, self.weights)}

    def get_cluster_summary(self) -> dict[str, Any]:
        """
        Get a summary of clustering results.

        Returns:
            Dictionary with cluster information including sizes and allocations
        """
        unique_clusters, cluster_counts = np.unique(self.cluster_labels, return_counts=True)

        return {
            "n_clusters": self.n_clusters,
            "cluster_sizes": dict(zip(unique_clusters.tolist(), cluster_counts.tolist())),
            "cluster_weights": self.cluster_weights.tolist(),
            "largest_cluster": int(unique_clusters[np.argmax(cluster_counts)]),
            "largest_cluster_size": int(cluster_counts.max()),
        }

    def is_diversified(self, max_concentration: float = 0.30) -> bool:
        """
        Check if portfolio is adequately diversified.

        Args:
            max_concentration: Maximum allowed weight for any single asset

        Returns:
            True if no single asset exceeds max_concentration
        """
        return bool(np.all(self.weights <= max_concentration))


class NestedClusteredOptimization:
    """
    Nested Clustered Optimization (NCO) per López de Prado (2019).

    NCO improves upon traditional mean-variance optimization by:
    1. Grouping similar assets using clustering
    2. Optimizing within each cluster separately (reduces dimensionality)
    3. Allocating across clusters based on risk parity

    This approach reduces the impact of estimation errors in the covariance matrix
    and produces more stable, robust portfolios.

    Example:
        >>> import numpy as np
        >>> nco = NestedClusteredOptimization()
        >>> expected_returns = np.array([0.08, 0.10, 0.12, 0.09])
        >>> cov_matrix = np.array([[0.01, 0.005, 0.003, 0.004],
        ...                         [0.005, 0.02, 0.006, 0.005],
        ...                         [0.003, 0.006, 0.015, 0.007],
        ...                         [0.004, 0.005, 0.007, 0.018]])
        >>> result = nco.get_weights(expected_returns, cov_matrix)
        >>> print(result.weights)
        >>> print(result.cluster_labels)
    """

    def __init__(self, config: NCOConfig | None = None) -> None:
        """
        Initialize NCO optimizer.

        Args:
            config: NCO configuration. If None, uses default configuration.
        """
        self.config = config or NCOConfig()
        self._last_distance_matrix: NDArray[np.float64] | None = None

    def _correlation_to_distance(
        self, correlation_matrix: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """
        Convert correlation matrix to distance matrix.

        Distance metric: d[i,j] = sqrt(0.5 * (1 - corr[i,j]))

        This transforms correlation to a proper distance metric:
        - corr = 1  -> distance = 0 (identical)
        - corr = 0  -> distance = sqrt(0.5) ≈ 0.707
        - corr = -1 -> distance = 1 (opposite)

        Args:
            correlation_matrix: Correlation matrix (N, N)

        Returns:
            Distance matrix (N, N)

        Reference:
            López de Prado uses this metric to cluster assets with similar return patterns.
        """
        # Ensure correlation matrix is valid
        np.clip(correlation_matrix, -1.0, 1.0, out=correlation_matrix)

        # Compute distance: d = sqrt(0.5 * (1 - corr))
        distance = np.sqrt(0.5 * (1 - correlation_matrix))

        # Ensure diagonal is zero (self-distance)
        np.fill_diagonal(distance, 0.0)

        self._last_distance_matrix = distance

        return distance

    def _covariance_to_correlation(self, cov_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Convert covariance matrix to correlation matrix.

        Args:
            cov_matrix: Covariance matrix (N, N)

        Returns:
            Correlation matrix (N, N)
        """
        # Compute standard deviations
        std_devs = np.sqrt(np.diag(cov_matrix))

        # Handle zero standard deviations
        std_devs[std_devs == 0] = 1e-10

        # Compute correlation: corr[i,j] = cov[i,j] / (std[i] * std[j])
        correlation = cov_matrix / np.outer(std_devs, std_devs)

        # Ensure correlation matrix is valid
        np.clip(correlation, -1.0, 1.0, out=correlation)
        np.fill_diagonal(correlation, 1.0)

        return correlation

    def _cluster_assets(self, cov_matrix: NDArray[np.float64]) -> NDArray[np.int32]:
        """
        Cluster assets using correlation distance.

        This is the first step of NCO: group assets with similar return patterns.
        Clustering reduces the dimensionality of the optimization problem.

        Args:
            cov_matrix: Covariance matrix (N, N)

        Returns:
            Cluster labels for each asset (N,)
                - K-means: labels in range [0, n_clusters)
                - DBSCAN: labels >= 0 for clusters, -1 for noise
        """
        n_assets = cov_matrix.shape[0]

        # Convert covariance to correlation, then to distance
        corr_matrix = self._covariance_to_correlation(cov_matrix)
        distance_matrix = self._correlation_to_distance(corr_matrix)

        # Apply clustering
        if self.config.clustering_method == ClusteringMethod.KMEANS:
            labels = self._cluster_kmeans(distance_matrix, n_assets)
        elif self.config.clustering_method == ClusteringMethod.DBSCAN:
            labels = self._cluster_dbscan(distance_matrix)
        else:
            raise ValueError(f"Unsupported clustering method: {self.config.clustering_method}")

        # Validate clustering results
        unique_labels = np.unique(labels[labels >= 0])
        if len(unique_labels) < 2:
            logger.warning(
                f"Only {len(unique_labels)} cluster(s) found. "
                "Consider adjusting clustering parameters."
            )

        return labels.astype(np.int32)

    def _cluster_kmeans(
        self, distance_matrix: NDArray[np.float64], n_assets: int
    ) -> NDArray[np.int32]:
        """
        Cluster assets using K-means algorithm.

        K-means is used when we want a fixed number of clusters.
        It's deterministic given the same random_state.

        Args:
            distance_matrix: Distance matrix (N, N)
            n_assets: Number of assets

        Returns:
            Cluster labels (N,) with values in range [0, n_clusters)
        """
        # Use distance matrix directly as features
        # K-means will minimize within-cluster sum of distances
        kmeans = KMeans(
            n_clusters=min(self.config.n_clusters, n_assets),
            random_state=self.config.random_state,
            n_init=10,
            max_iter=300,
        )

        labels = kmeans.fit_predict(distance_matrix)

        logger.info(
            f"K-means clustering: {len(np.unique(labels))} clusters found "
            f"(requested: {self.config.n_clusters})"
        )

        return labels

    def _cluster_dbscan(self, distance_matrix: NDArray[np.float64]) -> NDArray[np.int32]:
        """
        Cluster assets using DBSCAN algorithm.

        DBSCAN automatically determines the number of clusters and can identify
        outliers (noise points). Good for datasets with unknown cluster structure.

        Args:
            distance_matrix: Pre-computed distance matrix (N, N)

        Returns:
            Cluster labels (N,) where:
                - labels >= 0: cluster assignment
                - labels == -1: noise/outlier
        """
        dbscan = DBSCAN(
            eps=self.config.dbscan_eps,
            min_samples=self.config.min_samples,
            metric="precomputed",
        )

        labels = dbscan.fit_predict(distance_matrix)

        n_clusters = len(np.unique(labels[labels >= 0]))
        n_noise: int = np.sum(labels == -1)

        logger.info(f"DBSCAN clustering: {n_clusters} clusters found, " f"{n_noise} noise points")

        return labels.astype(np.int32)

    def _optimize_within_cluster(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        cluster_mask: NDArray[np.bool_],
    ) -> NDArray[np.float64]:
        """
        Optimize weights within a single cluster.

        Uses mean-variance optimization to find optimal weights for assets
        within the cluster, subject to constraints:
        - Sum of weights = 1 (within cluster)
        - Long-only (weights >= 0)
        - Maximum weight constraint

        Args:
            expected_returns: Expected returns for all assets (N,)
            cov_matrix: Covariance matrix for all assets (N, N)
            cluster_mask: Boolean mask for assets in this cluster (N,)

        Returns:
            Optimal weights for assets in this cluster (N,)
                (zeros for assets not in cluster)
        """
        cluster_indices = np.where(cluster_mask)[0]
        n_cluster_assets = len(cluster_indices)

        # Skip small clusters
        if n_cluster_assets < self.config.min_cluster_size:
            logger.warning(
                f"Cluster has {n_cluster_assets} assets (< {self.config.min_cluster_size}), "
                "using equal weights"
            )
            weights = np.zeros_like(expected_returns)
            weights[cluster_indices] = 1.0 / n_cluster_assets
            return weights

        # Extract cluster-specific data
        expected_returns[cluster_indices]
        cluster_cov = cov_matrix[np.ix_(cluster_indices, cluster_indices)]

        # Objective function: minimize portfolio variance
        def portfolio_variance(weights_cluster: NDArray[np.float64]) -> float:
            """Calculate portfolio variance."""
            return float(weights_cluster @ cluster_cov @ weights_cluster)

        # Constraints
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]  # Sum = 1

        # Bounds: long-only with max weight constraint
        max_weight = min(self.config.max_weight_single_asset, 1.0)
        bounds = [(0.0, max_weight) for _ in range(n_cluster_assets)]

        # Initial guess: equal weight
        x0 = np.ones(n_cluster_assets) / n_cluster_assets

        # Optimize
        result = minimize(
            portfolio_variance,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        # Handle optimization failure
        if not result.success:
            logger.warning(
                f"Within-cluster optimization failed: {result.message}. "
                "Falling back to equal weights."
            )
            cluster_weights = np.ones(n_cluster_assets) / n_cluster_assets
        else:
            cluster_weights = result.x

        # Map back to full asset space
        weights = np.zeros_like(expected_returns)
        weights[cluster_indices] = cluster_weights

        return weights

    def _allocate_clusters(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        cluster_labels: NDArray[np.int32],
    ) -> NDArray[np.float64]:
        """
        Allocate capital across clusters using risk parity.

        Each cluster is treated as a "super-asset" and capital is allocated
        based on inverse volatility (risk parity).

        Args:
            expected_returns: Expected returns for all assets (N,)
            cov_matrix: Covariance matrix (N, N)
            cluster_labels: Cluster assignment for each asset (N,)

        Returns:
            Weight allocation to each cluster (n_clusters,)
        """
        # Handle DBSCAN noise points
        valid_clusters = cluster_labels[cluster_labels >= 0]
        if len(valid_clusters) == 0:
            logger.warning("No valid clusters found. Using equal weights.")
            return np.ones(1)

        unique_clusters = np.unique(valid_clusters)
        n_clusters = len(unique_clusters)

        # Compute cluster statistics
        cluster_volatilities = []
        cluster_returns = []

        for cluster_id in unique_clusters:
            cluster_mask = cluster_labels == cluster_id
            cluster_assets_mask = cluster_labels == cluster_id

            if not np.any(cluster_assets_mask):
                continue

            # Get cluster asset indices
            cluster_indices = np.where(cluster_assets_mask)[0]

            # Equal-weight within cluster for allocation purposes
            n_cluster_assets = len(cluster_indices)
            equal_weights = np.ones(n_cluster_assets) / n_cluster_assets

            # Cluster return: weighted average of asset returns
            cluster_return: float = np.sum(expected_returns[cluster_indices] * equal_weights)
            cluster_returns.append(cluster_return)

            # Cluster variance: w.T @ Sigma @ w
            cluster_cov = cov_matrix[np.ix_(cluster_indices, cluster_indices)]
            cluster_variance = equal_weights @ cluster_cov @ equal_weights
            cluster_volatility = np.sqrt(cluster_variance)
            cluster_volatilities.append(cluster_volatility)

        if not cluster_volatilities:
            logger.warning("No clusters with valid volatilities. Using equal weights.")
            return np.ones(n_clusters) / n_clusters

        cluster_volatilities = np.array(cluster_volatilities)

        # Risk parity allocation: weight proportional to 1/volatility
        inv_vols = 1.0 / cluster_volatilities
        cluster_weights = inv_vols / np.sum(inv_vols)

        logger.info(
            f"Cluster allocation (risk parity): "
            f"{n_clusters} clusters, "
            f"weights ranging from {cluster_weights.min():.4f} to {cluster_weights.max():.4f}"
        )

        return cluster_weights

    def get_weights(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> NCOResult:
        """
        Calculate NCO portfolio weights.

        This is the main entry point for NCO optimization. It follows
        the three-step process:
        1. Cluster assets based on correlation distance
        2. Optimize weights within each cluster
        3. Allocate capital across clusters (risk parity)

        Args:
            expected_returns: Expected returns for each asset (N,)
                Must be annualized and same order as cov_matrix
            cov_matrix: Covariance matrix (N, N)
                Must be symmetric and positive semi-definite

        Returns:
            NCOResult containing:
                - Final weights for each asset (N,)
                - Cluster assignments (N,)
                - Portfolio metrics (return, risk, Sharpe)
                - Cluster breakdown

        Raises:
            ValueError: If inputs are invalid or incompatible

        Example:
            >>> nco = NestedClusteredOptimization()
            >>> returns = np.array([0.08, 0.10, 0.12, 0.09])
            >>> cov = np.array([[0.01, 0.005, ...], ...])
            >>> result = nco.get_weights(returns, cov)
            >>> print(result.weights)
        """
        try:
            # Input validation
            expected_returns = np.asarray(expected_returns, dtype=np.float64)
            cov_matrix = np.asarray(cov_matrix, dtype=np.float64)

            if expected_returns.ndim != 1:
                raise ValueError(f"expected_returns must be 1D, got shape {expected_returns.shape}")

            if cov_matrix.ndim != 2:
                raise ValueError(f"cov_matrix must be 2D, got shape {cov_matrix.shape}")

            n_assets = len(expected_returns)

            if cov_matrix.shape != (n_assets, n_assets):
                raise ValueError(
                    f"cov_matrix shape {cov_matrix.shape} incompatible with "
                    f"expected_returns length {n_assets}"
                )

            if n_assets < 2:
                raise ValueError("Need at least 2 assets for optimization")

            # Step 1: Cluster assets
            logger.info("Step 1: Clustering assets...")
            cluster_labels = self._cluster_assets(cov_matrix)

            # Handle DBSCAN noise (label -1) - treat as separate clusters
            valid_labels = cluster_labels.copy()
            noise_mask = cluster_labels == -1

            if np.any(noise_mask):
                # Assign noise points to unique clusters
                n_noise: int = np.sum(noise_mask)
                max_label = cluster_labels.max()
                valid_labels[noise_mask] = np.arange(max_label + 1, max_label + 1 + n_noise)
                logger.info(f"Assigned {n_noise} noise points to separate clusters")

            unique_clusters = np.unique(valid_labels)
            n_clusters = len(unique_clusters)

            logger.info(f"Step 1 complete: {n_clusters} clusters identified")

            # Step 2: Optimize within each cluster
            logger.info("Step 2: Optimizing within clusters...")
            within_cluster_weights: dict[int, NDArray[np.float64]] = {}

            for cluster_id in unique_clusters:
                cluster_mask = valid_labels == cluster_id
                cluster_weights = self._optimize_within_cluster(
                    expected_returns, cov_matrix, cluster_mask
                )

                # Normalize weights within cluster
                cluster_sum = cluster_weights.sum()
                if cluster_sum > 0:
                    cluster_weights = cluster_weights / cluster_sum

                within_cluster_weights[int(cluster_id)] = cluster_weights[cluster_mask]

            logger.info("Step 2 complete: Within-cluster optimization finished")

            # Step 3: Allocate across clusters
            logger.info("Step 3: Allocating across clusters...")
            cluster_allocations = self._allocate_clusters(
                expected_returns, cov_matrix, valid_labels
            )

            # Combine within-cluster and cross-cluster weights
            final_weights = np.zeros(n_assets, dtype=np.float64)

            for i, cluster_id in enumerate(unique_clusters):
                cluster_mask = valid_labels == cluster_id
                cluster_allocation = cluster_allocations[i]

                # Get normalized within-cluster weights
                if int(cluster_id) in within_cluster_weights:
                    within_weights = within_cluster_weights[int(cluster_id)]
                    final_weights[cluster_mask] = within_weights * cluster_allocation

            # Ensure weights sum to 1
            total_weight = final_weights.sum()
            if total_weight > 0:
                final_weights = final_weights / total_weight
            else:
                logger.warning("Total weight is zero. Using equal weights.")
                final_weights = np.ones(n_assets) / n_assets

            logger.info("Step 3 complete: Final weights computed")

            # Compute portfolio metrics
            portfolio_return = float(final_weights @ expected_returns)
            portfolio_variance = float(final_weights @ cov_matrix @ final_weights)
            portfolio_risk = np.sqrt(portfolio_variance)

            if portfolio_risk > 0:
                sharpe_ratio = (portfolio_return - self.config.risk_free_rate) / portfolio_risk
            else:
                sharpe_ratio = 0.0
                logger.warning("Portfolio risk is zero. Setting Sharpe ratio to 0.")

            # Check convergence (basic check: all weights should be non-negative and sum to 1)
            converged = bool(
                np.all(final_weights >= 0) and np.abs(final_weights.sum() - 1.0) < 1e-6
            )

            logger.info(
                f"NCO complete: Return={portfolio_return:.4f}, "
                f"Risk={portfolio_risk:.4f}, Sharpe={sharpe_ratio:.4f}"
            )

            return NCOResult(
                weights=final_weights,
                cluster_labels=cluster_labels,
                n_clusters=n_clusters,
                expected_return=portfolio_return,
                expected_risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
                cluster_weights=cluster_allocations,
                within_cluster_weights=within_cluster_weights,
                converged=converged,
            )

        except Exception as e:
            logger.error(
                f"NCO optimization failed: {e}",
                exc_info=True,
                extra={
                    "n_assets": len(expected_returns)
                    if hasattr(expected_returns, "__len__")
                    else None,
                    "cov_shape": cov_matrix.shape if hasattr(cov_matrix, "shape") else None,
                },
            )
            raise

    def get_distance_matrix(self) -> NDArray[np.float64] | None:
        """
        Get the last computed distance matrix.

        Returns:
            Distance matrix from last clustering operation, or None if
            no clustering has been performed yet.
        """
        return self._last_distance_matrix


def compute_nco_weights(
    expected_returns: NDArray[np.float64],
    cov_matrix: NDArray[np.float64],
    n_clusters: int = 5,
    clustering_method: str = "kmeans",
    max_weight: float = 0.20,
) -> NDArray[np.float64]:
    """
    Convenience function to compute NCO weights with default settings.

    This is a simplified interface for quick NCO computations.

    Args:
        expected_returns: Expected returns for each asset (N,)
        cov_matrix: Covariance matrix (N, N)
        n_clusters: Number of clusters (for K-means)
        clustering_method: 'kmeans' or 'dbscan'
        max_weight: Maximum weight for any single asset

    Returns:
        Optimal weights (N,)

    Example:
        >>> weights = compute_nco_weights(returns, cov_matrix, n_clusters=5)
        >>> print(weights)
    """
    config = NCOConfig(
        n_clusters=n_clusters,
        clustering_method=ClusteringMethod(clustering_method),
        max_weight_single_asset=max_weight,
    )

    nco = NestedClusteredOptimization(config)
    result = nco.get_weights(expected_returns, cov_matrix)

    return result.weights
