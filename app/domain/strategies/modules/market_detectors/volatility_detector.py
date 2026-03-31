"""
VolatilityDetector - Módulo independiente para detectar régimen de volatilidad.
"""

from __future__ import annotations

import bisect
import logging
from typing import Optional

from .base_detector import BaseMarketDetector

logger = logging.getLogger(__name__)


class VolatilityDetector(BaseMarketDetector):
    """
    Detecta régimen de volatilidad: high, normal, low.

    Métodos soportados:
    - atr_percentile: Percentil de ATR histórico
    - std_dev: Desviación estándar de retornos
    """

    def __init__(
        self, config: Optional[dict] = None, tier: Optional[str] = None, use_yaml: bool = True
    ):
        """Inicializar detector de volatilidad."""
        super().__init__("volatility_detector", config, tier, use_yaml)

        # Get settings from YAML or config
        percentile_config = self.config.get("percentile", {})
        std_dev_config = self.config.get("std_dev", {})

        # Try to get method from config, default to atr_percentile
        self.method = self.config.get("method", "atr_percentile")
        self.percentile_window = percentile_config.get("window", 30)
        self.high_vol_threshold = percentile_config.get("high_threshold", 75)
        self.low_vol_threshold = percentile_config.get("low_threshold", 25)

        # Store std_dev thresholds for fallback
        self.std_dev_high_threshold = std_dev_config.get("high_threshold", 0.02)
        self.std_dev_low_threshold = std_dev_config.get("low_threshold", 0.005)
        self.std_dev_window = std_dev_config.get("window", 20)

    def detect(self, price_history: list[float], **kwargs) -> dict:
        """
        Detectar régimen de volatilidad.

        Args:
            atr_history: Histórico de ATR (si está disponible)

        Returns:
            {
                'regime': 'high' | 'normal' | 'low',
                'percentile': int,  # 0-100
                'confidence': float,
                'method': str
            }
        """
        if not self.enabled:
            return {"regime": "normal", "percentile": 50, "confidence": 0.5, "method": self.method}

        atr_history = kwargs.get("atr_history", [])

        if self.method == "atr_percentile":
            return self._detect_atr_percentile(atr_history)
        elif self.method == "std_dev":
            return self._detect_std_dev(price_history)
        else:
            logger.warning(f"Unknown volatility detection method: {self.method}")
            return self._detect_atr_percentile(atr_history)

    def _detect_atr_percentile(self, atr_history: list[float]) -> dict:
        """Detectar volatilidad usando percentil de ATR."""
        if len(atr_history) < self.percentile_window:
            return {
                "regime": "normal",
                "percentile": 50,
                "confidence": 0.5,
                "method": "atr_percentile",
            }

        # Calcular percentil del ATR actual usando bisect para mayor precisión
        current_atr = atr_history[-1]
        window = atr_history[-self.percentile_window :]
        sorted_atr = sorted(window)

        # Usar bisect para encontrar la posición correcta (evita problemas con floats)
        pos = bisect.bisect_left(sorted_atr, current_atr)
        percentile = (pos / len(sorted_atr)) * 100

        if percentile >= self.high_vol_threshold:
            regime = "high"
            confidence = min(1.0, (percentile - self.high_vol_threshold) / 25)
        elif percentile <= self.low_vol_threshold:
            regime = "low"
            confidence = min(1.0, (self.low_vol_threshold - percentile) / 25)
        else:
            regime = "normal"
            # Confianza basada en qué tan cerca del centro
            center = (self.high_vol_threshold + self.low_vol_threshold) / 2
            distance = abs(percentile - center)
            max_distance = (self.high_vol_threshold - self.low_vol_threshold) / 2
            confidence = 1.0 - (distance / max_distance) * 0.5

        return {
            "regime": regime,
            "percentile": int(percentile),
            "confidence": confidence,
            "method": "atr_percentile",
            "metadata": {"current_atr": current_atr, "atr_history_length": len(atr_history)},
        }

    def _detect_std_dev(self, price_history: list[float]) -> dict:
        """Detectar volatilidad usando desviación estándar de retornos."""
        if len(price_history) < self.std_dev_window:
            return {"regime": "normal", "percentile": 50, "confidence": 0.5, "method": "std_dev"}

        # Calcular retornos
        returns = []
        for i in range(1, len(price_history)):
            if price_history[i - 1] > 0:
                ret = (price_history[i] - price_history[i - 1]) / price_history[i - 1]
                returns.append(ret)

        if len(returns) < 2:
            return {"regime": "normal", "percentile": 50, "confidence": 0.5, "method": "std_dev"}

        import numpy as np

        std_dev = np.std(returns)

        # Calcular percentil basado en ventana histórica
        # Usar thresholds desde config YAML
        high_threshold = self.std_dev_high_threshold
        low_threshold = self.std_dev_low_threshold

        if std_dev >= high_threshold:
            regime = "high"
            percentile = 75 + min(25, (std_dev - high_threshold) / high_threshold * 25)
        elif std_dev <= low_threshold:
            regime = "low"
            percentile = 25 - min(25, (low_threshold - std_dev) / low_threshold * 25)
        else:
            regime = "normal"
            percentile = 50

        return {
            "regime": regime,
            "percentile": int(percentile),
            "confidence": 0.7,
            "method": "std_dev",
            "metadata": {"std_dev": float(std_dev)},
        }
