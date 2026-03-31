"""
VolumeFilter - Filtro de volumen para confirmar señales.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class VolumeFilter(BaseFilter):
    """
    Filtro de volumen que valida que haya suficiente actividad de trading.

    Compara volumen actual vs promedio histórico.
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        preset: str = "balanced",
        tier: Optional[str] = None,
        use_yaml: bool = True,
    ):
        """Inicializar filtro de volumen."""
        super().__init__("volume_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.lookback_period = settings.get("lookback_period", 20)
        self.method = settings.get("method", "ratio")

        # Thresholds del preset (usar thresholds cargados desde YAML)
        # FIX: Lowered from 1.1 - requiring above-average volume is too restrictive
        self.min_volume_ratio = self.thresholds.get("min_volume_ratio", 0.9)

    def _apply_filter_logic(self, indicators: dict, market_context: dict, signal_type: str) -> dict:
        """Aplicar lógica del filtro de volumen."""
        volume_ratio = indicators.get("volume_ratio")

        if volume_ratio is None:
            # Intentar calcular desde volumen actual y promedio
            current_volume = indicators.get("volume")
            avg_volume = indicators.get("avg_volume")

            if current_volume and avg_volume and avg_volume > 0:
                volume_ratio = current_volume / avg_volume
            else:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": "Volume indicators missing",
                    "metadata": {},
                }

        if volume_ratio >= self.min_volume_ratio:
            # Calcular confianza: más volumen = mayor confianza (hasta 2x el threshold)
            max_ratio = self.min_volume_ratio * 2
            normalized_ratio = min(1.0, volume_ratio / max_ratio)
            confidence = 0.6 + (normalized_ratio * 0.4)

            return {
                "passed": True,
                "confidence": confidence,
                "reason": f"Volume ratio {volume_ratio:.2f} >= threshold {self.min_volume_ratio:.2f}",
                "metadata": {
                    "volume_ratio": volume_ratio,
                    "threshold": self.min_volume_ratio,
                    "normalized": normalized_ratio,
                },
            }
        else:
            return {
                "passed": False,
                "confidence": 0.0,
                "reason": f"Volume ratio {volume_ratio:.2f} below threshold {self.min_volume_ratio:.2f}",
                "metadata": {"volume_ratio": volume_ratio},
            }
