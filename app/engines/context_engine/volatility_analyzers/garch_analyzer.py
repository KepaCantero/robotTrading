"""
GARCHAnalyzer - Analizador de volatilidad usando modelos GARCH.

Detecta volatility clustering usando modelos GARCH.
"""

import logging
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)

# Importaciones opcionales
try:
    from arch import arch_model

    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    logger.warning("arch no disponible. GARCHAnalyzer limitado.")


class GARCHAnalyzer:
    """
    Analizador de volatilidad usando modelos GARCH.

    Detecta volatility clustering y predice volatilidad futura.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar analizador GARCH.

        Args:
            config: Configuración
        """
        config = config or {}
        self.model_type = config.get('model_type', 'GARCH')  # GARCH, EGARCH, GJR-GARCH
        self.p = config.get('p', 1)  # ARCH order
        self.q = config.get('q', 1)  # GARCH order
        self.dist = config.get('dist', 'normal')  # normal, t, skewt

        self.model = None
        self.fitted_model = None

    def fit(self, returns: List[float]) -> bool:
        """
        Entrenar modelo GARCH.

        Args:
            returns: Lista de returns

        Returns:
            True si el entrenamiento fue exitoso
        """
        if not ARCH_AVAILABLE:
            logger.warning("arch no disponible. GARCH no puede entrenarse.")
            return False

        if len(returns) < 100:
            logger.warning("No hay suficientes datos para entrenar GARCH")
            return False

        try:
            returns_array = np.array(returns)

            # Crear modelo
            if self.model_type == 'GARCH':
                self.model = arch_model(
                    returns_array, vol='Garch', p=self.p, q=self.q, dist=self.dist
                )
            elif self.model_type == 'EGARCH':
                self.model = arch_model(
                    returns_array, vol='EGARCH', p=self.p, q=self.q, dist=self.dist
                )
            elif self.model_type == 'GJR-GARCH':
                self.model = arch_model(
                    returns_array, vol='GARCH', p=self.p, o=1, q=self.q, dist=self.dist
                )
            else:
                logger.warning(f"Tipo de modelo desconocido: {self.model_type}, usando GARCH")
                self.model = arch_model(
                    returns_array, vol='Garch', p=self.p, q=self.q, dist=self.dist
                )

            # Entrenar
            self.fitted_model = self.model.fit(disp='of')

            logger.info("GARCH model entrenado exitosamente")
            return True

        except Exception as e:
            logger.error(f"Error entrenando GARCH: {e}")
            return False

    def predict_volatility(self, horizon: int = 1) -> Dict[str, Any]:
        """
        Predecir volatilidad futura.

        Args:
            horizon: Horizonte de predicción

        Returns:
            Dict con predicciones de volatilidad
        """
        if not self.fitted_model:
            return {'volatility': None, 'forecast': None, 'confidence': 0.0}

        try:
            forecast = self.fitted_model.forecast(horizon=horizon)
            volatility = float(np.sqrt(forecast.variance.values[-1, 0]))

            return {
                'volatility': volatility,
                'forecast': forecast.variance.values.tolist(),
                'confidence': 0.8,  # Confianza alta para modelos GARCH bien ajustados
            }

        except Exception as e:
            logger.error(f"Error prediciendo volatilidad: {e}")
            return {'volatility': None, 'forecast': None, 'confidence': 0.0}

    def detect_clustering(self, returns: List[float]) -> Dict[str, Any]:
        """
        Detectar volatility clustering.

        Args:
            returns: Lista de returns

        Returns:
            Dict con información de clustering
        """
        if not self.fitted_model:
            if not self.fit(returns):
                return {'clustering_detected': False, 'persistence': None, 'confidence': 0.0}

        try:
            # Obtener parámetros del modelo
            params = self.fitted_model.params

            # Calcular persistencia (suma de parámetros ARCH y GARCH)
            # Persistencia alta indica clustering fuerte
            persistence = float(params.get('alpha[1]', 0) + params.get('beta[1]', 0))

            # Persistencia > 0.9 indica clustering fuerte
            clustering_detected = persistence > 0.9

            return {
                'clustering_detected': clustering_detected,
                'persistence': persistence,
                'confidence': min(1.0, persistence),
                'parameters': params.to_dict(),
            }

        except Exception as e:
            logger.error(f"Error detectando clustering: {e}")
            return {'clustering_detected': False, 'persistence': None, 'confidence': 0.0}
