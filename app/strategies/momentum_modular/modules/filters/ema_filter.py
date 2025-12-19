"""
EMAFilter - Filtro de tendencia basado en cruces de EMA.
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class EMAFilter(BaseFilter):
    """
    Filtro de tendencia usando Exponential Moving Averages.

    Evalúa si el precio está en tendencia según:
    - EMA rápida vs EMA lenta
    - Precio vs EMAs
    - Distancia mínima entre EMAs
    """

    def __init__(self, config: Dict, preset: str = "balanced"):
        """Inicializar filtro EMA."""
        super().__init__("ema_filter", config, preset)

        params = config.get("parameters", {})
        self.fast_period = params.get("fast_period", 12)
        self.slow_period = params.get("slow_period", 26)
        self.confirmation_method = params.get("trend_confirmation", {}).get("method", "price_above")

        # Thresholds del preset
        self.min_distance_pct = self.thresholds.get("min_distance_pct", 0.005)
        self.require_crossover = self.thresholds.get("require_crossover", False)

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """
        Aplicar lógica del filtro EMA.

        Para BUY:
        - EMA rápida > EMA lenta (con distancia mínima)
        - Precio > EMA rápida (si método = price_above)
        """
        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")
        current_price = indicators.get("price")

        if not all([ema_fast, ema_slow, current_price]):
            return {
                'passed': False,
                'confidence': 0.0,
                'reason': 'EMA indicators missing',
                'metadata': {},
            }

        if signal_type == "BUY":
            # Verificar que EMA rápida esté por encima de EMA lenta
            fast_above_slow = ema_fast > ema_slow

            if not fast_above_slow:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'EMA fast ({ema_fast:.2f}) not above EMA slow ({ema_slow:.2f})',
                    'metadata': {'ema_fast': ema_fast, 'ema_slow': ema_slow},
                }

            # Verificar distancia mínima
            distance_pct = (ema_fast - ema_slow) / ema_slow
            if distance_pct < self.min_distance_pct:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'EMA distance {distance_pct:.4f} < threshold {self.min_distance_pct:.4f}',
                    'metadata': {'distance_pct': distance_pct},
                }

            # Verificar precio vs EMA según método
            if self.confirmation_method == "price_above":
                if current_price <= ema_fast:
                    return {
                        'passed': False,
                        'confidence': 0.0,
                        'reason': f'Price ({current_price:.2f}) not above EMA fast ({ema_fast:.2f})',
                        'metadata': {},
                    }

            # Calcular confianza basada en distancia
            confidence = min(1.0, (distance_pct / self.min_distance_pct) * 0.8)

            return {
                'passed': True,
                'confidence': confidence,
                'reason': f'EMA trend confirmed: distance {distance_pct:.4f}',
                'metadata': {
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'distance_pct': distance_pct,
                    'price_above_fast': current_price > ema_fast,
                },
            }

        elif signal_type == "SELL":
            # Lógica inversa para SELL
            slow_above_fast = ema_slow > ema_fast

            if not slow_above_fast:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'EMA slow ({ema_slow:.2f}) not above EMA fast ({ema_fast:.2f})',
                    'metadata': {},
                }

            distance_pct = (ema_slow - ema_fast) / ema_fast
            if distance_pct < self.min_distance_pct:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'EMA distance {distance_pct:.4f} < threshold',
                    'metadata': {},
                }

            if self.confirmation_method == "price_above":
                if current_price >= ema_slow:
                    return {
                        'passed': False,
                        'confidence': 0.0,
                        'reason': f'Price ({current_price:.2f}) not below EMA slow ({ema_slow:.2f})',
                        'metadata': {},
                    }

            confidence = min(1.0, (distance_pct / self.min_distance_pct) * 0.8)

            return {
                'passed': True,
                'confidence': confidence,
                'reason': 'EMA downtrend confirmed',
                'metadata': {'distance_pct': distance_pct},
            }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
