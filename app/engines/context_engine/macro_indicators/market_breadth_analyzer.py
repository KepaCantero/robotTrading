"""
MarketBreadthAnalyzer - Analizador de market breadth (simplificado).
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MarketBreadthAnalyzer:
    """Analizador de market breadth (simplificado)."""

    def analyze_breadth(self, price_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """Analizar market breadth."""
        if not price_data:
            return {'breadth': 'unknown'}

        # Calcular % de activos en tendencia alcista
        up_count = 0
        total_count = len(price_data)

        for _symbol, prices in price_data.items():
            if len(prices) >= 20:
                recent_return = (prices[-1] - prices[-20]) / prices[-20]
                if recent_return > 0:
                    up_count += 1

        breadth_pct = (up_count / total_count) * 100 if total_count > 0 else 0.0

        return {
            'breadth': breadth_pct,
            'up_count': up_count,
            'total_count': total_count,
            'breadth_regime': (
                'bullish' if breadth_pct > 60 else 'bearish' if breadth_pct < 40 else 'neutral'
            ),
        }
