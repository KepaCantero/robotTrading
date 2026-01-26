"""
RSIFilter - Filtro de momentum relativo usando RSI.

Standard RSI Strategy:
- BUY when RSI <= buy_threshold (oversold condition, typically <= 30)
- SELL when RSI >= sell_threshold (overbought condition, typically >= 70)
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class RSIFilter(BaseFilter):
    """
    Filtro RSI con thresholds adaptativos según contexto de mercado.

    Evalúa condiciones de sobrecompra/sobreventa según el régimen detectado.
    
    Standard RSI interpretation:
    - RSI < 30: Oversold (potential buy signal)
    - RSI > 70: Overbought (potential sell signal)
    - 30 <= RSI <= 70: Neutral zone (no clear signal)
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
        # Using NEW correct format: buy_threshold and sell_threshold (single values)
        self.adaptive_thresholds = self.config.get("adaptive_thresholds", {})
        if not self.adaptive_thresholds:
            # Fallback a defaults si no están en YAML - FIXED LOGIC
            self.adaptive_thresholds = {
                "balanced": {"buy_threshold": 30, "sell_threshold": 70},
                "volatile": {"buy_threshold": 25, "sell_threshold": 75},
                "trending": {"buy_threshold": 40, "sell_threshold": 65},
                "trend_up": {"buy_threshold": 45, "sell_threshold": 70},
                "trend_down": {"buy_threshold": 30, "sell_threshold": 50},
                "range": {"buy_threshold": 30, "sell_threshold": 70},
                "high_vol": {"buy_threshold": 35, "sell_threshold": 65},
                "unknown": {"buy_threshold": 30, "sell_threshold": 70},
            }

    def _get_thresholds_for_context(self, market_context: Dict) -> Dict:
        """Obtener thresholds según el contexto de mercado."""
        market_type = market_context.get("type", "unknown")

        # Intentar obtener thresholds específicos para este contexto
        if market_type in self.adaptive_thresholds:
            return self.adaptive_thresholds[market_type]

        # Fallback a preset genérico
        return self.adaptive_thresholds.get(
            "unknown", {"buy_threshold": 30, "sell_threshold": 70}
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

        # Support both old and new config formats for backward compatibility
        if "buy_threshold" in thresholds:
            buy_threshold = thresholds.get("buy_threshold", 30)
            sell_threshold = thresholds.get("sell_threshold", 70)
        else:
            # Legacy format fallback - convert old range to single threshold
            buy_threshold = thresholds.get("buy_min", 30)
            sell_threshold = thresholds.get("sell_max", 70)
            logger.warning(
                f"Using legacy RSI threshold format (buy_min/buy_max). "
                f"Please update to use buy_threshold/sell_threshold. "
                f"Derived: buy_threshold={buy_threshold}, sell_threshold={sell_threshold}"
            )

        if signal_type == "BUY":
            # BUY when RSI is at or below buy_threshold (oversold condition)
            if rsi <= buy_threshold:
                # Calculate confidence: lower RSI = higher confidence (more oversold)
                # RSI of 0 = max confidence, RSI at threshold = min confidence
                confidence = 1.0 - ((rsi / buy_threshold) * 0.5) if buy_threshold > 0 else 0.5
                
                return {
                    'passed': True,
                    'confidence': max(0.5, min(1.0, confidence)),
                    'reason': f'RSI {rsi:.2f} <= {buy_threshold} (oversold)',
                    'metadata': {
                        'rsi': rsi,
                        'buy_threshold': buy_threshold,
                        'context': market_context.get('type'),
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'RSI {rsi:.2f} > {buy_threshold} (not oversold enough)',
                    'metadata': {'rsi': rsi, 'buy_threshold': buy_threshold},
                }

        elif signal_type == "SELL":
            # SELL when RSI is at or above sell_threshold (overbought condition)
            if rsi >= sell_threshold:
                # Calculate confidence: higher RSI = higher confidence (more overbought)
                # RSI at threshold = min confidence, RSI of 100 = max confidence
                distance_from_threshold = (rsi - sell_threshold) / (100 - sell_threshold) if sell_threshold < 100 else 0
                confidence = 0.5 + (distance_from_threshold * 0.5)
                
                return {
                    'passed': True,
                    'confidence': max(0.5, min(1.0, confidence)),
                    'reason': f'RSI {rsi:.2f} >= {sell_threshold} (overbought)',
                    'metadata': {
                        'rsi': rsi,
                        'sell_threshold': sell_threshold,
                        'context': market_context.get('type'),
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'RSI {rsi:.2f} < {sell_threshold} (not overbought enough)',
                    'metadata': {'rsi': rsi, 'sell_threshold': sell_threshold},
                }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
