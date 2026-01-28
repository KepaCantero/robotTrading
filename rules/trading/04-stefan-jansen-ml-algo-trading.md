# 📙 4. "Machine Learning for Asset Managers" - Marcos López de Prado

## REGLAS DE PORTFOLIO CONSTRUCTION CON ML

**Hierarchical Risk Parity (HRP): Mejor que Markowitz**

```python
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

def hierarchical_risk_parity(
    self,
    returns: pd.DataFrame
) -> pd.Series:
    """
    HRP: Portfolio allocation usando clustering jerárquico.

    Ventajas vs Markowitz:
    - No requiere invertir matriz de correlación (más estable)
    - No produce pesos extremos
    - Más robusto a estimation error
    """
    # 1. Calcular matriz de correlación
    corr = returns.corr()

    # 2. Convertir correlación a distancia
    dist = np.sqrt(0.5 * (1 - corr))

    # 3. Clustering jerárquico
    link = linkage(squareform(dist.values), method='single')

    # 4. Ordenar assets por similaridad
    sorted_idx = self._quasi_diagonalization(link, corr.shape[0])

    # 5. Recursive bisection para asignar pesos
    weights = self._recursive_bisection(corr.iloc[sorted_idx, sorted_idx], returns.iloc[:, sorted_idx])

    return pd.Series(weights, index=returns.columns[sorted_idx])

def _recursive_bisection(self, corr: pd.DataFrame, returns: pd.DataFrame) -> np.array:
    """Dividir cluster recursivamente y asignar pesos."""
    weights = pd.Series(1.0, index=corr.index)
    clusters = [corr.index]

    while len(clusters) > 0:
        clusters = [
            cluster[start:end]
            for cluster in clusters
            for start, end in [(0, len(cluster) // 2), (len(cluster) // 2, len(cluster))]
            if len(cluster) > 1
        ]

        for i in range(0, len(clusters), 2):
            cluster0 = clusters[i]
            cluster1 = clusters[i + 1]

            # Calcular variance de cada cluster
            var0 = self._cluster_variance(returns[cluster0])
            var1 = self._cluster_variance(returns[cluster1])

            # Asignar peso inversamente proporcional a variance
            alpha = 1 - var0 / (var0 + var1)

            weights[cluster0] *= alpha
            weights[cluster1] *= (1 - alpha)

    return weights.values
```

**De-noising Correlation Matrix con Random Matrix Theory**

```python
def denoise_correlation_matrix(
    self,
    corr: pd.DataFrame,
    n_samples: int,
    n_features: int
) -> pd.DataFrame:
    """
    Eliminar eigenvalues ruidosos usando Marchenko-Pastur distribution.

    Correlaciones estimadas tienen noise - RMT lo elimina.
    """
    # 1. Eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eigh(corr.values)

    # 2. Marchenko-Pastur threshold
    q = n_features / n_samples
    lambda_max = (1 + np.sqrt(q)) ** 2

    # 3. Shrink eigenvalues ruidosos
    eigenvalues_denoised = eigenvalues.copy()

    for i, eigenvalue in enumerate(eigenvalues):
        if eigenvalue < lambda_max:
            # Eigenvalue ruidoso - shrink a promedio
            eigenvalues_denoised[i] = eigenvalues[eigenvalues < lambda_max].mean()

    # 4. Reconstruir matriz
    corr_denoised = eigenvectors @ np.diag(eigenvalues_denoised) @ eigenvectors.T

    # 5. Rescale a correlación (diagonal = 1)
    corr_denoised = pd.DataFrame(
        corr_denoised / np.sqrt(np.outer(np.diag(corr_denoised), np.diag(corr_denoised))),
        index=corr.index,
        columns=corr.columns
    )

    return corr_denoised
```

**Detoning: Eliminar market factor de correlación**

```python
def detone_correlation_matrix(
    self,
    corr: pd.DataFrame,
    n_factors: int = 1
) -> pd.DataFrame:
    """
    Eliminar N factores principales (market beta) de matriz de correlación.

    Útil para strategies market-neutral.
    """
    # 1. Eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eigh(corr.values)

    # 2. Eliminar top N eigenvalues (market factor)
    eigenvalues_detoned = eigenvalues.copy()
    eigenvalues_detoned[-n_factors:] = 0  # Set market factor a 0

    # 3. Reconstruir matriz sin market factor
    corr_detoned = eigenvectors @ np.diag(eigenvalues_detoned) @ eigenvectors.T

    # 4. Rescale
    corr_detoned = pd.DataFrame(
        corr_detoned / np.sqrt(np.outer(np.diag(corr_detoned), np.diag(corr_detoned))),
        index=corr.index,
        columns=corr.columns
    )

    return corr_detoned
```

**Feature Clustering: Reduce dimensionalidad preservando información**

```python
from sklearn.cluster import KMeans

def cluster_features(
    self,
    features: pd.DataFrame,
    n_clusters: int = 10
) -> pd.DataFrame:
    """
    Agrupar features correlacionados y usar centroid.

    Si tienes 100 features → reduce a 10 clusters.
    """
    # 1. Calcular correlación entre features
    corr = features.corr()

    # 2. Clustering basado en correlación
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(corr.values)

    # 3. Para cada cluster, usar PCA component 1
    clustered_features = pd.DataFrame(index=features.index)

    for cluster_id in range(n_clusters):
        cluster_cols = features.columns[cluster_labels == cluster_id]

        if len(cluster_cols) == 1:
            clustered_features[f'cluster_{cluster_id}'] = features[cluster_cols[0]]
        else:
            # PCA - usar first component
            from sklearn.decomposition import PCA
            pca = PCA(n_components=1)
            clustered_features[f'cluster_{cluster_id}'] = pca.fit_transform(
                features[cluster_cols]
            ).flatten()

    return clustered_features
```

**SIEMPRE valida stability de portfolio weights**

```python
def portfolio_turnover(
    self,
    weights_t0: pd.Series,
    weights_t1: pd.Series
) -> float:
    """
    Turnover = suma de cambios absolutos en weights.

    High turnover (>50%) = unstable portfolio = high transaction costs.
    """
    turnover = (weights_t1 - weights_t0).abs().sum()

    if turnover > 0.5:
        logger.warning(f"⚠️ Portfolio turnover {turnover:.1%} > 50% threshold")

    return turnover
```

**NUNCA uses Sharpe ratio solo** - Combínalo con otros

```python
def probabilistic_sharpe_ratio(
    self,
    observed_sharpe: float,
    n_samples: int,
    benchmark_sharpe: float = 0.0,
    skewness: float = 0.0,
    kurtosis: float = 3.0
) -> float:
    """
    PSR = P(Sharpe > benchmark | observaciones).

    Ajusta por skewness y kurtosis (Sharpe solo asume normal).
    """
    from scipy.stats import norm

    # Adjust for higher moments
    adjustment = (1 - skewness * observed_sharpe +
                 (kurtosis - 1) / 4 * observed_sharpe ** 2)

    # Standard error
    se = np.sqrt(adjustment / n_samples)

    # Z-score
    z_score = (observed_sharpe - benchmark_sharpe) / se

    # PSR = P(Z > z_score)
    psr = norm.cdf(z_score)

    return psr
```
