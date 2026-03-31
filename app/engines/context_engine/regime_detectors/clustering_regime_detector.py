"""
ClusteringRegimeDetector - Detección de régimen usando clustering.

Usa KMeans y DBSCAN para identificar regímenes basados en features de mercado.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# REQUIRED: sklearn is REQUIRED - NO FALLBACKS
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

if TYPE_CHECKING:
    from sklearn.base import ClusterMixin


class ClusteringRegimeDetector:
    """
    Detector de régimen usando clustering.

    Usa KMeans o DBSCAN para identificar regímenes basados en features de mercado.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar detector de clustering.

        Args:
            config: Configuración
        """
        config = config or {}
        self.method = config.get("method", "kmeans")  # kmeans, dbscan
        self.n_clusters = config.get("n_clusters", 3)
        self.window_size = config.get("window_size", 100)
        self.min_samples = config.get("min_samples", 50)
        self.use_pca = config.get("use_pca", False)
        self.n_components_pca = config.get("n_components_pca", 2)

        self.model: Optional[ClusterMixin] = None
        self.scaler = StandardScaler()
        self.pca: Optional[PCA] = PCA(n_components=self.n_components_pca) if self.use_pca else None
        self.regime_labels = (
            ["bear", "sideways", "bull"]
            if self.n_clusters == 3
            else [f"regime_{i}" for i in range(self.n_clusters)]
        )

    def _extract_features(self, prices: list[float]) -> np.ndarray:
        """
        Extraer features de precios.

        Features:
        - Returns (múltiples períodos)
        - Volatilidad
        - Momentum
        - RSI-like indicator
        """
        if len(prices) < 20:
            return np.zeros(0)

        returns = np.diff(prices) / prices[:-1]

        features: list[float] = []

        # Returns de diferentes períodos
        for period in [1, 5, 10, 20]:
            if len(returns) >= period:
                features.append(float(np.mean(returns[-period:])))
            else:
                features.append(float(np.mean(returns)))

        # Volatilidad
        if len(returns) >= 20:
            features.append(float(np.std(returns[-20:])))
        else:
            features.append(float(np.std(returns)))

        # Momentum (tasa de cambio)
        if len(prices) >= 20:
            momentum = (prices[-1] - prices[-20]) / prices[-20]
            features.append(float(momentum))
        else:
            features.append(0.0)

        # RSI-like (proporción de movimientos positivos)
        if len(returns) >= 14:
            positive_moves = float(np.sum(returns[-14:] > 0)) / 14.0
            features.append(positive_moves)
        else:
            features.append(0.5)

        return np.array(features, dtype=np.float64)

    def fit(self, prices: list[float]) -> bool:
        """
        Entrenar modelo de clustering.

        Args:
            prices: Lista de precios históricos

        Returns:
            True si el entrenamiento fue exitoso
        """
        # sklearn es REQUIRED - ya importado al inicio del módulo

        if len(prices) < self.min_samples:
            logger.warning(f"No hay suficientes datos: {len(prices)} < {self.min_samples}")
            return False

        try:
            # Extraer features para cada ventana
            feature_matrix: list[np.ndarray] = []
            window_size = min(self.window_size, len(prices) - 20)

            for i in range(20, len(prices)):
                window_prices = (
                    prices[i - window_size : i + 1] if i >= window_size else prices[: i + 1]
                )
                features = self._extract_features(window_prices)
                if len(features) > 0:
                    feature_matrix.append(features)

            if len(feature_matrix) < self.min_samples:
                logger.warning("No hay suficientes ventanas para clustering")
                return False

            X = np.array(feature_matrix)

            # Estandarizar
            X = self.scaler.fit_transform(X)

            # Aplicar PCA si está configurado
            if self.pca is not None:
                X = self.pca.fit_transform(X)

            # Entrenar clustering
            if self.method == "kmeans":
                kmeans_model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
                kmeans_model.fit(X)
                self.model = kmeans_model
            elif self.method == "dbscan":
                dbscan_model = DBSCAN(eps=0.5, min_samples=5)
                dbscan_model.fit(X)
                self.model = dbscan_model
            else:
                logger.error(f"Método desconocido: {self.method}")
                return False

            logger.info(f"Clustering entrenado con {len(X)} muestras")
            return True

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error entrenando clustering: {e}")
            return False

    def detect(self, prices: list[float]) -> dict[str, Any]:
        """
        Detectar régimen actual usando clustering.

        Args:
            prices: Lista de precios históricos

        Returns:
            Dict con régimen detectado
        """
        if self.model is None and not self.fit(prices):
            return {"regime": "unknown", "cluster": -1, "confidence": 0.0}

        # After fit check, model should be set
        if self.model is None:
            return {"regime": "unknown", "cluster": -1, "confidence": 0.0}

        try:
            # Extraer features recientes
            features = self._extract_features(prices)

            if len(features) == 0:
                return {"regime": "unknown", "cluster": -1, "confidence": 0.0}

            X = features.reshape(1, -1)

            # Estandarizar
            X = self.scaler.transform(X)

            # Aplicar PCA
            if self.pca is not None:
                X = self.pca.transform(X)

            # Predecir cluster
            cluster = int(self.model.predict(X)[0])

            # Para DBSCAN, -1 significa outlier
            if cluster == -1:
                return {"regime": "outlier", "cluster": -1, "confidence": 0.0}

            # Mapear cluster a régimen
            regime = (
                self.regime_labels[cluster]
                if cluster < len(self.regime_labels)
                else f"regime_{cluster}"
            )

            # Calcular distancia al centroide (confianza)
            if hasattr(self.model, "cluster_centers_"):
                centers = self.model.cluster_centers_
                center = centers[cluster]
                distance = float(np.linalg.norm(X[0] - center))
                # Normalizar distancia (confianza inversa)
                max_distance: float = float(np.max([np.linalg.norm(X[0] - c) for c in centers]))
                confidence = 1.0 - (distance / max_distance) if max_distance > 0 else 0.5
            else:
                confidence = 0.5

            return {"regime": regime, "cluster": int(cluster), "confidence": float(confidence)}

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error detectando régimen con clustering: {e}")
            return {"regime": "unknown", "cluster": -1, "confidence": 0.0}
