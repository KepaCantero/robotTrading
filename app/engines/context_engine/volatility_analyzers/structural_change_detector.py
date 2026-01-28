"""
StructuralChangeDetector - Detección de cambios estructurales.

Implementa CUSUM y Chow test para detectar cambios estructurales en series temporales.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

# Try to import statsmodels with fallback
try:
    from statsmodels.stats.diagnostic import breaks_cusumolsresid

    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning(
        "statsmodels not available. CUSUM test will be disabled. "
        "Install with: pip install statsmodels"
    )


class StructuralChangeDetector:
    """
    Detector de cambios estructurales en series temporales.

    Implementa pruebas como CUSUM y Chow test para detectar cambios
    en la distribución de retornos.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializar detector.

        Args:
            config: Configuración del detector
        """
        config = config or {}
        self.method = config.get('method', 'cusum')  # cusum, chow
        self.significance_level = config.get('significance_level', 0.05)
        self.window_size = config.get('window_size', 100)

    def detect_cusum(self, prices: List[float]) -> Dict[str, Any]:
        """
        Detectar cambios estructurales usando CUSUM.

        Args:
            prices: Lista de precios

        Returns:
            Dict con información de cambios detectados
        """
        if len(prices) < self.window_size:
            return {
                'change_detected': False,
                'breakpoint': None,
                'p_value': None,
                'confidence': 0.0,
            }

        try:
            # Calcular returns
            returns = np.diff(prices[-self.window_size :]) / prices[-self.window_size : -1]

            # CUSUM test (requiere statsmodels)
            if not STATSMODELS_AVAILABLE:
                logger.warning("statsmodels no disponible. CUSUM test no puede ejecutarse.")
                return {
                    'change_detected': False,
                    'breakpoint': None,
                    'p_value': None,
                    'confidence': 0.0,
                    'note': 'statsmodels no disponible',
                }

            result = breaks_cusumolsresid(returns)

            # result es una tupla (test_statistic, p_value, critical_value)
            test_statistic = result[0] if isinstance(result, tuple) else result
            p_value = result[1] if isinstance(result, tuple) and len(result) > 1 else None

            change_detected = p_value is not None and p_value < self.significance_level

            return {
                'change_detected': change_detected,
                'breakpoint': None,  # CUSUM no detecta breakpoint específico
                'p_value': float(p_value) if p_value is not None else None,
                'test_statistic': float(test_statistic),
                'confidence': 1.0 - float(p_value) if p_value is not None else 0.0,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en CUSUM test: {e}")
            return {
                'change_detected': False,
                'breakpoint': None,
                'p_value': None,
                'confidence': 0.0,
            }

    def detect_chow_test(
        self, prices: List[float], breakpoint: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Detectar cambios estructurales usando Chow test.

        Args:
            prices: Lista de precios
            breakpoint: Punto de quiebre sospechado (opcional, usa el medio si None)

        Returns:
            Dict con información de cambios detectados
        """
        if len(prices) < self.window_size:
            return {
                'change_detected': False,
                'breakpoint': None,
                'p_value': None,
                'confidence': 0.0,
            }

        try:
            # Usar ventana reciente
            recent_prices = prices[-self.window_size :]

            # Calcular returns
            returns = np.diff(recent_prices) / recent_prices[:-1]

            # Determinar breakpoint
            if breakpoint is None:
                breakpoint = len(returns) // 2

            if breakpoint < 10 or breakpoint > len(returns) - 10:
                return {
                    'change_detected': False,
                    'breakpoint': None,
                    'p_value': None,
                    'confidence': 0.0,
                }

            # Dividir en dos períodos
            period1 = returns[:breakpoint]
            period2 = returns[breakpoint:]

            # Calcular estadísticas
            mean1 = np.mean(period1)
            mean2 = np.mean(period2)
            var1 = np.var(period1)
            var2 = np.var(period2)

            # Chow test simplificado (F-test)
            n1 = len(period1)
            n2 = len(period2)

            # Pooled variance
            pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)

            # F-statistic
            if pooled_var > 0:
                f_stat = ((mean1 - mean2) ** 2) / pooled_var
                # p-value usando F-distribution
                p_value = 1 - stats.f.cdf(f_stat, 1, n1 + n2 - 2)
            else:
                p_value = 1.0

            change_detected = p_value < self.significance_level

            return {
                'change_detected': change_detected,
                'breakpoint': breakpoint,
                'p_value': float(p_value),
                'f_statistic': float(f_stat) if pooled_var > 0 else 0.0,
                'mean_before': float(mean1),
                'mean_after': float(mean2),
                'confidence': 1.0 - float(p_value),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en Chow test: {e}")
            return {
                'change_detected': False,
                'breakpoint': None,
                'p_value': None,
                'confidence': 0.0,
            }

    def detect(self, prices: List[float], **kwargs) -> Dict[str, Any]:
        """
        Detectar cambios estructurales.

        Args:
            prices: Lista de precios
            **kwargs: Argumentos adicionales (breakpoint para Chow test)

        Returns:
            Dict con información de cambios
        """
        if self.method == 'cusum':
            return self.detect_cusum(prices)
        elif self.method == 'chow':
            breakpoint = kwargs.get('breakpoint')
            return self.detect_chow_test(prices, breakpoint)
        else:
            logger.warning(f"Método desconocido: {self.method}, usando CUSUM")
            return self.detect_cusum(prices)
