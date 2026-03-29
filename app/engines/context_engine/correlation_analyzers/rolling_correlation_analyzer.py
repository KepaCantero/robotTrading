"""
RollingCorrelationAnalyzer - Analizador de correlaciones rolling window.

Calcula matrices de correlación en ventanas móviles.
"""

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RollingCorrelationAnalyzer:
    """Analizador de correlaciones con ventana móvil."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        config = config or {}
        self.window_size = config.get("window_size", 60)

    def calculate_rolling_correlation(
        self, returns_data: dict[str, list[float]], window: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Calcular correlación rolling.

        Args:
            returns_data: Dict con símbolos y returns
            window: Tamaño de ventana (opcional)

        Returns:
            Dict con matriz de correlación y estadísticas
        """
        window = window or self.window_size

        if len(returns_data) < 2:
            return {
                "correlation_matrix": None,
                "average_correlation": 0.0,
                "correlation_trend": "stable",
            }

        try:
            # Crear DataFrame
            df = pd.DataFrame(returns_data)

            # Calcular correlación rolling
            rolling_corr = df.rolling(window=window).corr()

            # Última matriz de correlación
            if len(rolling_corr) > 0:
                last_corr = rolling_corr.iloc[-len(returns_data) :].values
                avg_corr = float(np.mean(np.triu(last_corr, k=1)[np.triu(last_corr, k=1) != 0]))
            else:
                last_corr = df.corr().values
                avg_corr = float(np.mean(np.triu(last_corr, k=1)[np.triu(last_corr, k=1) != 0]))

            return {
                "correlation_matrix": (
                    last_corr.tolist() if isinstance(last_corr, np.ndarray) else None
                ),
                "average_correlation": avg_corr,
                "correlation_trend": "stable",
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculando correlación rolling: {e}")
            return {
                "correlation_matrix": None,
                "average_correlation": 0.0,
                "correlation_trend": "stable",
            }
