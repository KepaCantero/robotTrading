"""
HMMRegimeDetector - Detección de régimen usando Hidden Markov Models.

Usa HMM para detectar regímenes de mercado (bull, bear, sideways).
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Importaciones opcionales
try:
    from hmmlearn import hmm
    HMMLEARN_AVAILABLE = True
except ImportError:
    HMMLEARN_AVAILABLE = False
    logger.warning("hmmlearn no disponible. HMMRegimeDetector limitado.")

try:
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn no disponible. HMMRegimeDetector limitado.")


class HMMRegimeDetector:
    """
    Detector de régimen usando Hidden Markov Models.
    
    Detecta regímenes ocultos basados en observaciones de precios y volatilidad.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar detector HMM.
        
        Args:
            config: Configuración
        """
        config = config or {}
        self.n_regimes = config.get('n_regimes', 3)  # Bull, Bear, Sideways
        self.n_features = config.get('n_features', 2)  # Returns, Volatility
        self.window_size = config.get('window_size', 100)
        self.min_samples = config.get('min_samples', 50)
        
        self.model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.regime_labels = ['bear', 'sideways', 'bull'] if self.n_regimes == 3 else [f'regime_{i}' for i in range(self.n_regimes)]
    
    def fit(self, prices: List[float]) -> bool:
        """
        Entrenar modelo HMM con datos históricos.
        
        Args:
            prices: Lista de precios históricos
        
        Returns:
            True si el entrenamiento fue exitoso
        """
        if not HMMLEARN_AVAILABLE:
            logger.warning("hmmlearn no disponible. HMM no puede entrenarse.")
            return False
        
        if len(prices) < self.min_samples:
            logger.warning(f"No hay suficientes datos para entrenar HMM: {len(prices)} < {self.min_samples}")
            return False
        
        try:
            # Calcular features: returns y volatilidad
            returns = np.diff(prices) / prices[:-1]
            volatility = self._calculate_rolling_volatility(returns)
            
            # Crear matriz de observaciones
            observations = np.column_stack([returns[-self.window_size:], volatility[-self.window_size:]])
            
            if self.scaler:
                observations = self.scaler.fit_transform(observations)
            
            # Entrenar HMM
            self.model = hmm.GaussianHMM(n_components=self.n_regimes, covariance_type="full", n_iter=100)
            self.model.fit(observations)
            
            logger.info(f"HMM entrenado con {len(observations)} observaciones")
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando HMM: {e}")
            return False
    
    def detect(self, prices: List[float]) -> Dict[str, Any]:
        """
        Detectar régimen actual.
        
        Args:
            prices: Lista de precios históricos
        
        Returns:
            Dict con:
                - regime: str - Régimen detectado
                - probability: float - Probabilidad del régimen
                - regime_probabilities: Dict[str, float] - Probabilidades por régimen
                - confidence: float - Confianza en la detección
        """
        if not self.model:
            # Intentar entrenar si no está entrenado
            if not self.fit(prices):
                return {
                    'regime': 'unknown',
                    'probability': 0.0,
                    'regime_probabilities': {},
                    'confidence': 0.0
                }
        
        try:
            # Calcular features recientes
            returns = np.diff(prices) / prices[:-1]
            volatility = self._calculate_rolling_volatility(returns)
            
            # Usar ventana reciente
            recent_returns = returns[-self.window_size:]
            recent_volatility = volatility[-self.window_size:]
            
            observations = np.column_stack([recent_returns, recent_volatility])
            
            if self.scaler:
                observations = self.scaler.transform(observations)
            
            # Predecir régimen
            states = self.model.predict(observations)
            current_state = states[-1]
            
            # Calcular probabilidades
            log_probs = self.model.score_samples(observations[-1:])
            probs = np.exp(log_probs[0])
            
            # Normalizar probabilidades
            probs = probs / probs.sum() if probs.sum() > 0 else probs
            
            regime = self.regime_labels[current_state]
            probability = float(probs[current_state])
            
            # Crear dict de probabilidades por régimen
            regime_probs = {
                self.regime_labels[i]: float(probs[i])
                for i in range(len(self.regime_labels))
            }
            
            # Calcular confianza (máxima probabilidad)
            confidence = float(max(probs))
            
            return {
                'regime': regime,
                'probability': probability,
                'regime_probabilities': regime_probs,
                'confidence': confidence,
                'state': int(current_state)
            }
            
        except Exception as e:
            logger.error(f"Error detectando régimen con HMM: {e}")
            return {
                'regime': 'unknown',
                'probability': 0.0,
                'regime_probabilities': {},
                'confidence': 0.0
            }
    
    def _calculate_rolling_volatility(self, returns: np.ndarray, window: int = 20) -> np.ndarray:
        """Calcular volatilidad rolling."""
        if len(returns) < window:
            # Si no hay suficientes datos, usar volatilidad completa
            volatility = np.full(len(returns), np.std(returns))
        else:
            # Rolling std
            volatility = np.zeros(len(returns))
            for i in range(window, len(returns)):
                volatility[i] = np.std(returns[i-window:i])
            # Llenar primeros valores con el primer valor calculado
            volatility[:window] = volatility[window] if len(returns) > window else np.std(returns)
        
        return volatility
    
    def get_transition_matrix(self) -> Optional[np.ndarray]:
        """Obtener matriz de transición entre regímenes."""
        if self.model:
            return self.model.transmat_
        return None
    
    def get_regime_means(self) -> Optional[np.ndarray]:
        """Obtener medias de cada régimen."""
        if self.model:
            return self.model.means_
        return None

