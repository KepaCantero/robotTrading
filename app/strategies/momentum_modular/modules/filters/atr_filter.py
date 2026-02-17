"""
ATRFilter - Filtro de volatilidad usando Average True Range.
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class ATRFilter(BaseFilter):
    """
    Filtro ATR que valida que haya suficiente volatilidad para operar.

    Puede usar ATR absoluto, relativo (% del precio) o percentil.
    """

    def __init__(
        self, config: Dict = None, preset: str = "balanced", tier: str = None, use_yaml: bool = True
    ):
        """Inicializar filtro ATR."""
        super().__init__("atr_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.period = settings.get("period", 14)
        self.method = settings.get("method", "relative_percentile")
        self.use_relative_atr = settings.get("use_relative_atr", True)

        # Thresholds adaptativos según volatilidad (desde YAML)
        volatility_thresholds = self.config.get("regimes", {})
        self.high_vol_thresholds = volatility_thresholds.get("high", {})
        self.normal_vol_thresholds = volatility_thresholds.get("medium", {})
        self.low_vol_thresholds = volatility_thresholds.get("low", {})

        # Thresholds del preset (usar thresholds cargados desde YAML)
        # FIX: Lowered thresholds - 60th percentile is too restrictive
        self.min_atr_percentile = self.thresholds.get(
            "min_percentile", self.thresholds.get("min_atr_percentile", 40)  # Lowered from 60
        )
        self.min_relative_atr = self.thresholds.get("min_relative_atr", 0.004)  # Lowered from 0.006

    def _get_thresholds_for_volatility(self, market_context: Dict) -> Dict:
        """Obtener thresholds según régimen de volatilidad."""
        vol_regime = market_context.get("volatility_regime", "normal")

        if vol_regime == "high":
            return self.high_vol_thresholds or self.thresholds
        elif vol_regime == "low":
            return self.low_vol_thresholds or self.thresholds
        else:
            return self.normal_vol_thresholds or self.thresholds

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """Aplicar lógica del filtro ATR."""
        # Obtener thresholds según volatilidad
        thresholds = self._get_thresholds_for_volatility(market_context)

        min_atr_percentile = thresholds.get("min_atr_percentile", self.min_atr_percentile)
        min_relative_atr = thresholds.get("min_relative_atr", self.min_relative_atr)

        atr_percentile = indicators.get("atr_percentile")
        relative_atr = indicators.get("relative_atr")
        atr = indicators.get("atr")
        current_price = indicators.get("price")

        # Calcular ATR relativo si no está disponible
        if relative_atr is None and atr and current_price:
            relative_atr = atr / current_price

        if self.method == "relative_percentile":
            # FIX: Use OR logic instead of AND - either condition passing is sufficient
            if atr_percentile is None or relative_atr is None:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': 'ATR percentile or relative ATR missing',
                    'metadata': {},
                }

            percentile_pass = atr_percentile >= min_atr_percentile
            relative_pass = relative_atr >= min_relative_atr

            # FIX: OR logic - either condition is sufficient
            if percentile_pass or relative_pass:
                # Calcular confianza basada en qué tan por encima está
                confidence = 0.5
                if percentile_pass:
                    confidence += min(0.3, (atr_percentile - min_atr_percentile) / 100)
                if relative_pass:
                    confidence += min(0.2, (relative_atr - min_relative_atr) / min_relative_atr * 0.2)

                passed_type = []
                if percentile_pass:
                    passed_type.append(f'percentile {atr_percentile:.1f}>={min_atr_percentile}')
                if relative_pass:
                    passed_type.append(f'relative {relative_atr:.4f}>={min_relative_atr:.4f}')

                return {
                    'passed': True,
                    'confidence': min(1.0, confidence),
                    'reason': f'ATR passed: {" OR ".join(passed_type)}',
                    'metadata': {
                        'atr_percentile': atr_percentile,
                        'relative_atr': relative_atr,
                        'volatility_regime': market_context.get('volatility_regime'),
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'ATR conditions not met: percentile {atr_percentile:.1f} < {min_atr_percentile} AND relative {relative_atr:.4f} < {min_relative_atr:.4f}',
                    'metadata': {'atr_percentile': atr_percentile, 'relative_atr': relative_atr},
                }

        elif self.method == "relative":
            # Solo requiere ATR relativo
            if relative_atr is None:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': 'Relative ATR missing',
                    'metadata': {},
                }

            if relative_atr >= min_relative_atr:
                confidence = min(1.0, (relative_atr / min_relative_atr) * 0.8)
                return {
                    'passed': True,
                    'confidence': confidence,
                    'reason': f'Relative ATR {relative_atr:.4f} >= {min_relative_atr:.4f}',
                    'metadata': {'relative_atr': relative_atr},
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'Relative ATR {relative_atr:.4f} below threshold',
                    'metadata': {'relative_atr': relative_atr},
                }

        return {
            'passed': False,
            'confidence': 0.0,
            'reason': f'Unknown ATR method: {self.method}',
            'metadata': {},
        }
