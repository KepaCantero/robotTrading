"""
StochRSIFilter - Filtro de Stochastic RSI.
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class StochRSIFilter(BaseFilter):
    """
    Filtro Stochastic RSI para detectar condiciones de sobrecompra/sobreventa más precisas.
    """

    def __init__(
        self, config: Dict = None, preset: str = "balanced", tier: str = None, use_yaml: bool = True
    ):
        """Inicializar filtro Stochastic RSI."""
        super().__init__("stoch_rsi_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.rsi_period = settings.get("stoch_rsi_period", settings.get("rsi_period", 14))
        self.stoch_period = settings.get("k_period", 14)
        self.k_period = settings.get("smooth_k", settings.get("k_period", 3))
        self.d_period = settings.get("d_period", 3)

        # Thresholds del preset (usar thresholds cargados desde YAML)
        self.buy_min = self.thresholds.get("buy_min", 15)
        self.buy_max = self.thresholds.get("buy_max", 85)
        self.sell_min = self.thresholds.get("sell_min", 15)
        self.sell_max = self.thresholds.get("sell_max", 85)

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """Aplicar lógica del filtro Stochastic RSI."""
        stoch_rsi_k = indicators.get("stoch_rsi_k")
        stoch_rsi_d = indicators.get("stoch_rsi_d")

        if stoch_rsi_k is None:
            return {
                'passed': False,
                'confidence': 0.0,
                'reason': 'StochRSI K indicator missing',
                'metadata': {},
            }

        if signal_type == "BUY":
            # Comprar cuando StochRSI está en rango y K cruza por encima de D (opcional)
            if self.buy_min <= stoch_rsi_k <= self.buy_max:
                # Bonificación si K cruza arriba de D
                crossover_bonus = 0.1 if stoch_rsi_d and stoch_rsi_k > stoch_rsi_d else 0.0

                # Calcular confianza
                center = (self.buy_min + self.buy_max) / 2
                distance = abs(stoch_rsi_k - center)
                max_distance = (self.buy_max - self.buy_min) / 2
                confidence = 1.0 - (distance / max_distance) * 0.4 + crossover_bonus

                return {
                    'passed': True,
                    'confidence': min(1.0, max(0.5, confidence)),
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} in buy range [{self.buy_min}-{self.buy_max}]',
                    'metadata': {
                        'stoch_rsi_k': stoch_rsi_k,
                        'stoch_rsi_d': stoch_rsi_d,
                        'crossover': stoch_rsi_d and stoch_rsi_k > stoch_rsi_d,
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} outside buy range [{self.buy_min}-{self.buy_max}]',
                    'metadata': {'stoch_rsi_k': stoch_rsi_k},
                }

        elif signal_type == "SELL":
            if self.sell_min <= stoch_rsi_k <= self.sell_max:
                crossover_bonus = 0.1 if stoch_rsi_d and stoch_rsi_k < stoch_rsi_d else 0.0

                center = (self.sell_min + self.sell_max) / 2
                distance = abs(stoch_rsi_k - center)
                max_distance = (self.sell_max - self.sell_min) / 2
                confidence = 1.0 - (distance / max_distance) * 0.4 + crossover_bonus

                return {
                    'passed': True,
                    'confidence': min(1.0, max(0.5, confidence)),
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} in sell range [{self.sell_min}-{self.sell_max}]',
                    'metadata': {'stoch_rsi_k': stoch_rsi_k, 'stoch_rsi_d': stoch_rsi_d},
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} outside sell range',
                    'metadata': {'stoch_rsi_k': stoch_rsi_k},
                }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
