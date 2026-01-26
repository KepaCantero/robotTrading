"""
RSIFilter - Filtro de momentum relativo usando RSI.
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class RSIFilter(BaseFilter):
    """
    Filtro RSI con thresholds adaptativos según contexto de mercado.

    Evalúa condiciones de sobrecompra/sobreventa según el régimen detectado.
    """

    def __init__(
        self, config: Dict = None, preset: str = "balanced", tier: str = None, use_yaml: bool = True
    ):
        """Inicializar filtro RSI."""
        super().__init__("rsi_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.period = settings.get("period", 14)
        self.adaptive = settings.get("adaptive", True)

        # Thresholds adaptativos por contexto (desde YAML)
        self.adaptive_thresholds = self.config.get("adaptive_thresholds", {})
        if not self.adaptive_thresholds:
            # Fallback a defaults si no están en YAML
            self.adaptive_thresholds = {
                "balanced": {"buy_min": 30, "buy_max": 70, "sell_min": 50, "sell_max": 80},
                "volatile": {"buy_min": 25, "buy_max": 75, "sell_min": 45, "sell_max": 85},
                "trending": {"buy_min": 40, "buy_max": 65, "sell_min": 55, "sell_max": 75},
            }

    def _get_thresholds_for_context(self, market_context: Dict) -> Dict:
        """Obtener thresholds según el contexto de mercado."""
        market_type = market_context.get("type", "unknown")

        # Intentar obtener thresholds específicos para este contexto
        if market_type in self.adaptive_thresholds:
            return self.adaptive_thresholds[market_type]

        # Fallback a preset genérico
        return self.adaptive_thresholds.get(
            "balanced", {"buy_min": 30, "buy_max": 70, "sell_min": 50, "sell_max": 80}
        )

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """Aplicar lógica del filtro RSI."""
        rsi = indicators.get("rsi")

        if rsi is None:
            return {
                'passed': False,
                'confidence': 0.0,
                'reason': 'RSI indicator missing',
                'metadata': {},
            }

        # Obtener thresholds adaptativos
        thresholds = (
            self._get_thresholds_for_context(market_context) if self.adaptive else self.thresholds
        )

        if signal_type == "BUY":
            buy_min = thresholds.get("buy_min", 30)
            buy_max = thresholds.get("buy_max", 70)

            if buy_min <= rsi <= buy_max:
                # Calcular confianza: más cerca del centro = mayor confianza
                center = (buy_min + buy_max) / 2
                distance_from_center = abs(rsi - center)
                max_distance = (buy_max - buy_min) / 2
                confidence = 1.0 - (distance_from_center / max_distance) * 0.5

                return {
                    'passed': True,
                    'confidence': max(0.5, confidence),
                    'reason': f'RSI {rsi:.2f} in buy range [{buy_min}-{buy_max}]',
                    'metadata': {
                        'rsi': rsi,
                        'thresholds': thresholds,
                        'context': market_context.get('type'),
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'RSI {rsi:.2f} outside buy range [{buy_min}-{buy_max}]',
                    'metadata': {'rsi': rsi},
                }

        elif signal_type == "SELL":
            sell_min = thresholds.get("sell_min", 50)
            sell_max = thresholds.get("sell_max", 80)

            if sell_min <= rsi <= sell_max:
                center = (sell_min + sell_max) / 2
                distance_from_center = abs(rsi - center)
                max_distance = (sell_max - sell_min) / 2
                confidence = 1.0 - (distance_from_center / max_distance) * 0.5

                return {
                    'passed': True,
                    'confidence': max(0.5, confidence),
                    'reason': f'RSI {rsi:.2f} in sell range [{sell_min}-{sell_max}]',
                    'metadata': {'rsi': rsi, 'thresholds': thresholds},
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'RSI {rsi:.2f} outside sell range [{sell_min}-{sell_max}]',
                    'metadata': {'rsi': rsi},
                }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
