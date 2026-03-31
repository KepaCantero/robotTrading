"""
YieldCurveAnalyzer - Analizador de yield curve (simplificado).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class YieldCurveAnalyzer:
    """Analizador de yield curve (simplificado)."""

    def get_yield_curve(self) -> dict[str, Any]:
        """Obtener yield curve (placeholder)."""
        return {"yield_curve": None, "note": "Requiere integración con API de Treasury"}
