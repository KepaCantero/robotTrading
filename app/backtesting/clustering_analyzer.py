"""
Advanced Clustering Analyzer - PHASE 4 MODULE 7 PHASE 3

Advanced clustering and dimensionality reduction techniques:
- Hierarchical clustering with dendrograms
- DBSCAN density-based clustering
- PCA (Principal Component Analysis)
- ICA (Independent Component Analysis)
- t-SNE (t-Distributed Stochastic Neighbor Embedding)
- Silhouette analysis for cluster quality
- Automatic optimal cluster detection
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA, FastICA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class AdvancedClusteringAnalyzer:
    """Advanced clustering and dimensionality reduction analyzer."""

    def __init__(self, random_state: int = 42, n_jobs: int = -1):
        """
        Initialize clustering analyzer.

        Args:
            random_state: Random state for reproducibility
            n_jobs: Number of jobs for parallel processing
        """
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.scaler = StandardScaler()

    def hierarchical_clustering(
        self, data: List[List[float]], n_clusters: int = 3, linkage_method: str = 'ward'
    ) -> Dict:
        """
        Perform hierarchical clustering with dendrogram.

        Args:
            data: 2D array of features
            n_clusters: Number of clusters
            linkage_method: Linkage method ('ward', 'complete', 'average', 'single')

        Returns:
            Dictionary with clustering results and dendrogram data
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for hierarchical clustering")
                return None

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Perform hierarchical clustering
            clusterer = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage_method)
            labels = clusterer.fit_predict(X_scaled)

            # Calculate linkage matrix for dendrogram
            from scipy.cluster.hierarchy import linkage as scipy_linkage

            linkage_matrix = scipy_linkage(X_scaled, method=linkage_method)

            # Calculate silhouette score
            if len(set(labels)) > 1:
                sil_score = float(silhouette_score(X_scaled, labels))
            else:
                sil_score = 0.0

            return {
                'labels': [int(var_l) for var_l in labels],
                'n_clusters': n_clusters,
                'linkage_method': linkage_method,
                'linkage_matrix': linkage_matrix.tolist(),
                'silhouette_score': sil_score,
                'cluster_sizes': self._get_cluster_sizes(labels),
            }

        except Exception as e:
            logger.error(f"Error in hierarchical clustering: {e}")
            return None

    def dbscan_clustering(
        self, data: List[List[float]], eps: float = 0.5, min_samples: int = 5
    ) -> Dict:
        """
        Perform DBSCAN density-based clustering.

        Args:
            data: 2D array of features
            eps: Maximum distance between samples
            min_samples: Minimum samples in a neighborhood

        Returns:
            Dictionary with clustering results
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for DBSCAN clustering")
                return None

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Perform DBSCAN
            clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            labels = clusterer.fit_predict(X_scaled)

            # Count clusters and noise points
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)

            # Calculate silhouette score (excluding noise points)
            if n_clusters > 1 and n_noise < len(labels) - 1:
                # Use only non-noise points for silhouette
                non_noise_mask = labels != -1
                if sum(non_noise_mask) > 1:
                    X_no_noise = X_scaled[non_noise_mask]
                    labels_no_noise = labels[non_noise_mask]
                    sil_score = float(silhouette_score(X_no_noise, labels_no_noise))
                else:
                    sil_score = 0.0
            else:
                sil_score = 0.0

            return {
                'labels': [int(var_l) for var_l in labels],
                'n_clusters': n_clusters,
                'n_noise_points': n_noise,
                'eps': eps,
                'min_samples': min_samples,
                'silhouette_score': sil_score,
                'cluster_sizes': self._get_cluster_sizes(labels),
            }

        except Exception as e:
            logger.error(f"Error in DBSCAN clustering: {e}")
            return None

    def pca_analysis(
        self,
        data: List[List[float]],
        n_components: Optional[int] = None,
        variance_threshold: float = 0.95,
    ) -> Dict:
        """
        Perform Principal Component Analysis.

        Args:
            data: 2D array of features
            n_components: Number of components (if None, use variance_threshold)
            variance_threshold: Variance to explain (default 95%)

        Returns:
            Dictionary with PCA results
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for PCA")
                return None

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Determine number of components
            if n_components is None:
                pca_temp = PCA()
                pca_temp.fit(X_scaled)
                cumsum = np.cumsum(pca_temp.explained_variance_ratio_)
                n_components = np.argmax(cumsum >= variance_threshold) + 1
                n_components = max(1, min(n_components, X_scaled.shape[1] - 1))

            # Perform PCA
            pca = PCA(n_components=n_components)
            X_pca = pca.fit_transform(X_scaled)

            # Calculate explained variance
            explained_var = pca.explained_variance_ratio_
            cumulative_var = np.cumsum(explained_var)

            return {
                'n_components': n_components,
                'explained_variance': [float(v) for v in explained_var],
                'cumulative_variance': [float(v) for v in cumulative_var],
                'total_variance_explained': float(cumulative_var[-1]),
                'components': pca.components_.tolist(),
                'transformed_data': X_pca.tolist(),
                'mean': pca.mean_.tolist(),
            }

        except Exception as e:
            logger.error(f"Error in PCA analysis: {e}")
            return None

    def ica_analysis(
        self,
        data: List[List[float]],
        n_components: Optional[int] = None,
        algorithm: str = 'parallel',
    ) -> Dict:
        """
        Perform Independent Component Analysis.

        Args:
            data: 2D array of features
            n_components: Number of independent components
            algorithm: 'parallel' or 'deflation'

        Returns:
            Dictionary with ICA results
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for ICA")
                return None

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Set default components
            if n_components is None:
                n_components = min(X_scaled.shape[1] - 1, X_scaled.shape[0] - 1)
                n_components = max(1, n_components)

            # Perform ICA
            ica = FastICA(
                n_components=n_components,
                algorithm=algorithm,
                random_state=self.random_state,
                max_iter=1000,
            )
            S = ica.fit_transform(X_scaled)

            # Get mixing matrix (A) and unmixing matrix (W)
            A = ica.mixing_  # Shape: (n_features, n_components)
            W = np.linalg.pinv(A)  # Unmixing matrix

            return {
                'n_components': n_components,
                'algorithm': algorithm,
                'independent_components': [float(v) for v in S[0]] if len(S) > 0 else [],
                'mixing_matrix': A.tolist(),
                'unmixing_matrix': W.tolist(),
                'transformed_data': S.tolist(),
            }

        except Exception as e:
            logger.error(f"Error in ICA analysis: {e}")
            return None

    def tsne_visualization(
        self,
        data: List[List[float]],
        n_components: int = 2,
        perplexity: int = 30,
        n_iter: int = 1000,
    ) -> Optional[Dict]:
        """
        Perform t-SNE dimensionality reduction for visualization.

        Args:
            data: 2D array of features
            n_components: Number of dimensions (2 or 3)
            perplexity: Perplexity parameter
            n_iter: Number of iterations (named max_iter in newer sklearn)

        Returns:
            Dictionary with t-SNE results or None if error
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for t-SNE")
                return None

            # Validate n_components
            if n_components not in [2, 3]:
                logger.warning(f"Invalid n_components {n_components}, using 2")
                n_components = 2

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Adjust perplexity if needed
            n_samples = X_scaled.shape[0]
            if perplexity >= n_samples / 3:
                perplexity = max(5, n_samples // 3)
                logger.warning(f"Adjusted perplexity to {perplexity}")

            # Perform t-SNE
            # Use 'max_iter' parameter name for compatibility with newer sklearn versions
            # but also accept 'n_iter' for backwards compatibility
            try:
                tsne = TSNE(
                    n_components=n_components,
                    perplexity=perplexity,
                    max_iter=n_iter,
                    random_state=self.random_state,
                    verbose=0,
                )
            except TypeError:
                # Fall back to older sklearn API
                tsne = TSNE(
                    n_components=n_components,
                    perplexity=perplexity,
                    n_iter=n_iter,
                    random_state=self.random_state,
                    verbose=0,
                )

            X_tsne = tsne.fit_transform(X_scaled)

            # Get KL divergence - handle both kl_divergence_ (newer) and accessing from result
            kl_div = 0.0
            if hasattr(tsne, 'kl_divergence_'):
                kl_div = float(tsne.kl_divergence_)

            result = {
                'n_components': n_components,
                'perplexity': perplexity,
                'n_iterations': n_iter,
                'max_iter': n_iter,  # Also provide max_iter for newer sklearn
                'transformed_data': X_tsne.tolist(),
                'kl_divergence': kl_div,
            }
            return result

        except Exception as e:
            logger.error(f"Error in t-SNE analysis: {e}")
            return None

    def silhouette_analysis(self, data: List[List[float]], labels: List[int]) -> Dict:
        """
        Analyze cluster quality using silhouette scores.

        Args:
            data: 2D array of features
            labels: Cluster labels for each sample

        Returns:
            Dictionary with silhouette analysis results
        """
        try:
            if not data or len(data) < 2 or not labels:
                logger.warning("Insufficient data for silhouette analysis")
                return None

            # Convert to numpy array
            X = np.array(data)
            y = np.array(labels)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Check if multiple clusters exist
            unique_labels = set(y)
            if len(unique_labels) < 2:
                logger.warning("Need at least 2 clusters for silhouette analysis")
                return None

            # Calculate overall silhouette score
            overall_score = float(silhouette_score(X_scaled, y))

            # Calculate per-sample silhouette scores
            sample_scores = silhouette_samples(X_scaled, y)

            # Calculate per-cluster averages
            cluster_scores = {}
            for label in unique_labels:
                cluster_mask = y == label
                if sum(cluster_mask) > 0:
                    cluster_scores[int(label)] = float(np.mean(sample_scores[cluster_mask]))

            return {
                'overall_score': overall_score,
                'cluster_scores': cluster_scores,
                'sample_scores': [float(s) for s in sample_scores],
                'n_clusters': len(unique_labels),
                'interpretation': self._interpret_silhouette(overall_score),
            }

        except Exception as e:
            logger.error(f"Error in silhouette analysis: {e}")
            return None

    def optimal_clusters(
        self,
        data: List[List[float]],
        k_range: Tuple[int, int] = (2, 10),
        method: str = 'silhouette',
    ) -> Dict:
        """
        Find optimal number of clusters using silhouette or elbow method.

        Args:
            data: 2D array of features
            k_range: Range of k values to test (min, max)
            method: 'silhouette' or 'elbow'

        Returns:
            Dictionary with optimal k and scores for each k
        """
        try:
            if not data or len(data) < 2:
                logger.warning("Insufficient data for optimal clusters")
                return None

            # Convert to numpy array
            X = np.array(data)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Ensure k_range is valid
            min_k, max_k = k_range
            max_k = min(max_k, len(X_scaled) - 1)
            min_k = max(2, min_k)

            scores = {}
            best_k = min_k
            best_score = -1

            if method == 'silhouette':
                # Silhouette analysis
                from sklearn.cluster import KMeans

                for k in range(min_k, max_k + 1):
                    try:
                        kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                        labels = kmeans.fit_predict(X_scaled)
                        score = float(silhouette_score(X_scaled, labels))
                        scores[k] = score

                        if score > best_score:
                            best_score = score
                            best_k = k
                    except Exception as e:
                        logger.warning(f"Error for k={k}: {e}")
                        continue

            elif method == 'elbow':
                # Elbow method (inertia)
                from sklearn.cluster import KMeans

                for k in range(min_k, max_k + 1):
                    try:
                        kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
                        kmeans.fit(X_scaled)
                        scores[k] = float(kmeans.inertia_)
                    except Exception as e:
                        logger.warning(f"Error for k={k}: {e}")
                        continue

                # For elbow, find the point with maximum curvature
                if len(scores) > 2:
                    ks = sorted(scores.keys())
                    inertias = [scores[k] for k in ks]
                    differences = np.diff(inertias)
                    second_diff = np.diff(differences)
                    if len(second_diff) > 0:
                        best_k = ks[np.argmax(second_diff) + 1]
                    else:
                        best_k = ks[0]

            return {
                'method': method,
                'optimal_k': best_k,
                'scores': scores,
                'k_range': [min_k, max_k],
            }

        except Exception as e:
            logger.error(f"Error finding optimal clusters: {e}")
            return None

    @staticmethod
    def _get_cluster_sizes(labels: List[int]) -> Dict[int, int]:
        """Get size of each cluster."""
        sizes = {}
        for label in set(labels):
            sizes[int(label)] = int(sum(1 for var_l in labels if var_l == label))
        return sizes

    @staticmethod
    def _interpret_silhouette(score: float) -> str:
        """Interpret silhouette score."""
        if score > 0.7:
            return "Strong structure"
        elif score > 0.5:
            return "Reasonable structure"
        elif score > 0.25:
            return "Weak structure"
        else:
            return "No substantial structure"
