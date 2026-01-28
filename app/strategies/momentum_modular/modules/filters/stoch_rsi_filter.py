"""
StochRSIFilter - Filtro de Stochastic RSI.

Standard Stochastic RSI Strategy:
- BUY when StochRSI K <= oversold_threshold (typically <= 20)
- SELL when StochRSI K >= overbought_threshold (typically >= 80)
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class StochRSIFilter(BaseFilter):
    """
    Filtro Stochastic RSI para detectar condiciones de sobrecompra/sobreventa más precisas.

    Standard StochRSI interpretation:
    - StochRSI < 20: Oversold (potential buy signal)
    - StochRSI > 80: Overbought (potential sell signal)
    - 20 <= StochRSI <= 80: Neutral zone (no clear signal)
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

        # NEW CORRECT FORMAT: Single thresholds for oversold/overbought
        # Support both old and new config formats
        if "oversold_threshold" in self.thresholds:
            self.oversold_threshold = self.thresholds.get("oversold_threshold", 20)
            self.overbought_threshold = self.thresholds.get("overbought_threshold", 80)
        else:
            # Legacy format - convert old range to single threshold
            self.oversold_threshold = self.thresholds.get("buy_min", 20)
            self.overbought_threshold = self.thresholds.get("sell_max", 80)
            if self.oversold_threshold == self.overbought_threshold:
                # Fix legacy config where both were the same
                self.oversold_threshold = 20
                self.overbought_threshold = 80
            logger.warning(
                f"Using legacy StochRSI threshold format. "
                f"Updated to: oversold_threshold={self.oversold_threshold}, "
                f"overbought_threshold={self.overbought_threshold}"
            )

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
            # BUY when StochRSI K is at or below oversold_threshold (oversold condition)
            if stoch_rsi_k <= self.oversold_threshold:
                # Bonus if K crosses above D (bullish crossover signal)
                crossover_bonus = 0.1 if stoch_rsi_d and stoch_rsi_k > stoch_rsi_d else 0.0

                # Calculate confidence: lower StochRSI = higher confidence (more oversold)
                confidence = (
                    1.0 - ((stoch_rsi_k / self.oversold_threshold) * 0.4)
                    if self.oversold_threshold > 0
                    else 0.6
                )

                return {
                    'passed': True,
                    'confidence': min(1.0, max(0.5, confidence + crossover_bonus)),
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} <= {self.oversold_threshold} (oversold)',
                    'metadata': {
                        'stoch_rsi_k': stoch_rsi_k,
                        'stoch_rsi_d': stoch_rsi_d,
                        'oversold_threshold': self.oversold_threshold,
                        'crossover': stoch_rsi_d and stoch_rsi_k > stoch_rsi_d,
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} > {self.oversold_threshold} (not oversold enough)',
                    'metadata': {
                        'stoch_rsi_k': stoch_rsi_k,
                        'oversold_threshold': self.oversold_threshold,
                    },
                }

        elif signal_type == "SELL":
            # SELL when StochRSI K is at or above overbought_threshold (overbought condition)
            if stoch_rsi_k >= self.overbought_threshold:
                # Bonus if K crosses below D (bearish crossover signal)
                crossover_bonus = 0.1 if stoch_rsi_d and stoch_rsi_k < stoch_rsi_d else 0.0

                # Calculate confidence: higher StochRSI = higher confidence (more overbought)
                distance_from_threshold = (
                    (stoch_rsi_k - self.overbought_threshold) / (100 - self.overbought_threshold)
                    if self.overbought_threshold < 100
                    else 0
                )
                confidence = 0.5 + (distance_from_threshold * 0.4)

                return {
                    'passed': True,
                    'confidence': min(1.0, max(0.5, confidence + crossover_bonus)),
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} >= {self.overbought_threshold} (overbought)',
                    'metadata': {
                        'stoch_rsi_k': stoch_rsi_k,
                        'stoch_rsi_d': stoch_rsi_d,
                        'overbought_threshold': self.overbought_threshold,
                        'crossover': stoch_rsi_d and stoch_rsi_k < stoch_rsi_d,
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'StochRSI K {stoch_rsi_k:.2f} < {self.overbought_threshold} (not overbought enough)',
                    'metadata': {
                        'stoch_rsi_k': stoch_rsi_k,
                        'overbought_threshold': self.overbought_threshold,
                    },
                }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
