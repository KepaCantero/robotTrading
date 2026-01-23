"""
OutlierDetector - Detección de outliers en datos de mercado.

Métodos soportados:
- IQR (Interquartile Range)
- Z-score
- Isolation Forest
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Importaciones opcionales
try:
    from sklearn.ensemble import IsolationForest

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn no disponible. Isolation Forest no funcionará.")


class OutlierDetector:
    """
    Detector de outliers en datos de mercado.

    Detecta valores anómalos que pueden indicar errores de datos.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar detector.

        Args:
            config: Configuración
        """
        config = config or {}
        self.method = config.get('method', 'iqr')  # iqr, zscore, isolation_forest
        self.iqr_multiplier = config.get('iqr_multiplier', 1.5)
        self.zscore_threshold = config.get('zscore_threshold', 3.0)
        self.isolation_contamination = config.get('isolation_contamination', 0.1)

    def detect(self, values: List[Any], method: Optional[str] = None) -> Dict[str, Any]:
        """
        Detectar outliers en una lista de valores.

        Args:
            values: Lista de valores (precios, volúmenes, etc.)
            method: Método a usar (opcional, usa self.method si None)

        Returns:
            Dict con:
                - outliers: List[int] - Índices de outliers
                - outlier_values: List[Any] - Valores de outliers
                - is_outlier: List[bool] - Máscara booleana
                - method_used: str
        """
        method = method or self.method

        # Convertir a numpy array
        try:
            if isinstance(values[0], Decimal):
                values_array = np.array([float(v) for v in values])
            else:
                values_array = np.array(values)
        except Exception:
            logger.error("Error convirtiendo valores a array")
            return {
                'outliers': [],
                'outlier_values': [],
                'is_outlier': [False] * len(values),
                'method_used': method,
            }

        if method == 'iqr':
            return self._detect_iqr(values_array, values)
        elif method == 'zscore':
            return self._detect_zscore(values_array, values)
        elif method == 'isolation_forest':
            return self._detect_isolation_forest(values_array, values)
        else:
            logger.warning(f"Método {method} no reconocido, usando IQR")
            return self._detect_iqr(values_array, values)

    def _detect_iqr(self, values_array: np.ndarray, original_values: List[Any]) -> Dict[str, Any]:
        """Detección usando IQR (Interquartile Range)."""
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1

        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        is_outlier = (values_array < lower_bound) | (values_array > upper_bound)
        outlier_indices = np.where(is_outlier)[0].tolist()
        outlier_values = [original_values[i] for i in outlier_indices]

        return {
            'outliers': outlier_indices,
            'outlier_values': outlier_values,
            'is_outlier': is_outlier.tolist(),
            'method_used': 'iqr',
            'lower_bound': float(lower_bound),
            'upper_bound': float(upper_bound),
        }

    def _detect_zscore(
        self, values_array: np.ndarray, original_values: List[Any]
    ) -> Dict[str, Any]:
        """Detección usando Z-score."""
        mean = np.mean(values_array)
        std = np.std(values_array)

        if std == 0:
            # Sin variación, no hay outliers
            return {
                'outliers': [],
                'outlier_values': [],
                'is_outlier': [False] * len(values_array),
                'method_used': 'zscore',
            }

        z_scores = np.abs((values_array - mean) / std)
        is_outlier = z_scores > self.zscore_threshold
        outlier_indices = np.where(is_outlier)[0].tolist()
        outlier_values = [original_values[i] for i in outlier_indices]

        return {
            'outliers': outlier_indices,
            'outlier_values': outlier_values,
            'is_outlier': is_outlier.tolist(),
            'method_used': 'zscore',
            'z_scores': z_scores.tolist(),
        }

    def _detect_isolation_forest(
        self, values_array: np.ndarray, original_values: List[Any]
    ) -> Dict[str, Any]:
        """Detección usando Isolation Forest."""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn no disponible, usando Z-score como fallback")
            return self._detect_zscore(values_array, original_values)

        try:
            # Reshape para sklearn
            X = values_array.reshape(-1, 1)

            # Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.isolation_contamination, random_state=42
            )
            predictions = iso_forest.fit_predict(X)

            # -1 = outlier, 1 = inlier
            is_outlier = predictions == -1
            outlier_indices = np.where(is_outlier)[0].tolist()
            outlier_values = [original_values[i] for i in outlier_indices]

            return {
                'outliers': outlier_indices,
                'outlier_values': outlier_values,
                'is_outlier': is_outlier.tolist(),
                'method_used': 'isolation_forest',
            }

        except Exception as e:
            logger.error(f"Error en Isolation Forest: {e}")
            return self._detect_zscore(values_array, original_values)

    def detect_in_ohlcv(
        self, ohlcv_data: List[Dict[str, Any]], check_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Detectar outliers en datos OHLCV.

        Args:
            ohlcv_data: Lista de dicts con datos OHLCV
            check_fields: Campos a verificar (default: ['open', 'high', 'low', 'close', 'volume'])

        Returns:
            Dict con outliers por campo
        """
        if check_fields is None:
            check_fields = ['open', 'high', 'low', 'close', 'volume']

        results = {}

        for field in check_fields:
            values = [item.get(field) for item in ohlcv_data]
            if values:
                results[field] = self.detect(values)

        # Combinar resultados
        all_outlier_indices = set()
        for field_result in results.values():
            all_outlier_indices.update(field_result.get('outliers', []))

        return {
            'field_results': results,
            'combined_outliers': sorted(list(all_outlier_indices)),
            'total_outliers': len(all_outlier_indices),
        }
