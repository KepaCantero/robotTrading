"""
SectorRotationDetector - Detector de rotación sectorial (simplificado).
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SectorRotationDetector:
    """Detector de rotación sectorial (simplificado)."""

    def detect_rotation(self, sector_returns: dict[str, list[float]]) -> dict[str, Any]:
        """Detectar rotación sectorial."""
        if not sector_returns:
            return {"rotation": "unknown"}

        # Calcular returns promedio por sector
        avg_returns = {
            sector: np.mean(returns) if returns else 0.0
            for sector, returns in sector_returns.items()
        }

        # Sector con mejor performance
        best_sector = max(avg_returns.items(), key=lambda x: x[1])

        return {
            "rotation": best_sector[0],
            "sector_returns": avg_returns,
            "best_sector": best_sector[0],
        }
