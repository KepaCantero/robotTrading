from __future__ import annotations

"""CorrelationRegimeDetector - Detección de régimen basada en correlaciones dinámicas.

Usa análisis de correlaciones para detectar cambios de régimen.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Optional sklearn import
try:
    from sklearn.decomposition import PCA

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    PCA = None


class CorrelationRegimeDetector:
    """
    Usa cambios en correlaciones entre activos para detectar cambios de régimen.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Inicializar detector de correlación.

        Args:
            config: Configuración
        """
        config = config or {}
        self.window_size = config.get("window_size", 60)
        self.correlation_threshold = config.get("correlation_threshold", 0.7)
        self.use_pca = config.get("use_pca", True)
        self.n_components_pca = config.get("n_components_pca", 3)

        self.pca = (
            PCA(n_components=self.n_components_pca) if SKLEARN_AVAILABLE and self.use_pca else None
        )
        self.baseline_correlation = None

    def _calculate_correlation_matrix(self, returns_matrix: np.ndarray) -> np.ndarray:
        """Calcular matriz de correlación."""
        if returns_matrix.shape[1] < 2:
            result: np.ndarray = np.array([[1.0]])
            return result

        df = pd.DataFrame(returns_matrix)
        corr_values: np.ndarray = np.array(df.corr().values)
        return corr_values

    def _calculate_pca_variance(self, returns_matrix: np.ndarray) -> float:
        """Calcular varianza explicada por PCA."""
        if not self.pca or returns_matrix.shape[1] < 2:
            return 0.0

        try:
            self.pca.fit(returns_matrix)
            explained_variance: float = float(np.sum(self.pca.explained_variance_ratio_))
            return explained_variance
        except (ValueError, TypeError, KeyError, AttributeError):
            return 0.0

    def detect(
        self, price_data: dict[str, list[float]], baseline_period: int | None = None
    ) -> dict[str, Any]:
        """
        Detectar régimen basado en correlaciones.

        Args:
            price_data: Dict con símbolos como keys y listas de precios como values
            baseline_period: Período baseline para comparar (opcional)

        Returns:
            Dict con información del régimen
        """
        if len(price_data) < 2:
            return {
                "regime": "unknown",
                "correlation_regime": "unknown",
                "average_correlation": 0.0,
                "pca_variance": 0.0,
                "confidence": 0.0,
            }

        try:
            # Convertir a DataFrame de returns
            symbols = list(price_data.keys())
            min_length = min(len(prices) for prices in price_data.values())

            if min_length < self.window_size:
                return {
                    "regime": "unknown",
                    "correlation_regime": "unknown",
                    "average_correlation": 0.0,
                    "pca_variance": 0.0,
                    "confidence": 0.0,
                }

            # Calcular returns
            returns_dict = {}
            for symbol, prices in price_data.items():
                returns = np.diff(prices[-min_length:]) / prices[-min_length:-1]
                returns_dict[symbol] = returns[-self.window_size :]

            # Crear matriz de returns
            returns_matrix = np.array([returns_dict[symbol] for symbol in symbols]).T

            # Calcular matriz de correlación
            corr_matrix = self._calculate_correlation_matrix(returns_matrix)

            # Extraer correlaciones (triángulo superior, sin diagonal)
            upper_triangle = np.triu(corr_matrix, k=1)
            correlations = upper_triangle[upper_triangle != 0]

            avg_correlation = float(np.mean(correlations)) if len(correlations) > 0 else 0.0

            # Determinar régimen basado en correlación promedio
            if avg_correlation > self.correlation_threshold:
                correlation_regime = "high_correlation"
            elif avg_correlation > 0.3:
                correlation_regime = "normal_correlation"
            else:
                correlation_regime = "low_correlation"

            # Calcular varianza explicada por PCA
            pca_variance = self._calculate_pca_variance(returns_matrix)

            # Calcular confianza
            confidence = min(1.0, len(correlations) / 10.0)  # Más correlaciones = más confianza

            # Comparar con baseline si está disponible
            baseline_comparison = None
            if self.baseline_correlation is not None:
                correlation_change = avg_correlation - self.baseline_correlation
                baseline_comparison = {
                    "baseline_correlation": float(self.baseline_correlation),
                    "correlation_change": float(correlation_change),
                    "regime_changed": abs(correlation_change) > 0.2,
                }

            return {
                "regime": correlation_regime,
                "correlation_regime": correlation_regime,
                "average_correlation": avg_correlation,
                "correlation_matrix": corr_matrix.tolist(),
                "pca_variance": pca_variance,
                "confidence": confidence,
                "baseline_comparison": baseline_comparison,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error detectando régimen de correlación: {e}")
            return {
                "regime": "unknown",
                "correlation_regime": "unknown",
                "average_correlation": 0.0,
                "pca_variance": 0.0,
                "confidence": 0.0,
            }

    def set_baseline(self, price_data: dict[str, list[float]]) -> None:
        """
        Establecer baseline de correlación.

        Args:
            price_data: Datos de precios para baseline
        """
        result = self.detect(price_data)
        self.baseline_correlation = result.get("average_correlation")
