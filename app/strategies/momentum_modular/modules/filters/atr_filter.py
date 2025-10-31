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
    
    def __init__(self, config: Dict, preset: str = "balanced"):
        """Inicializar filtro ATR."""
        super().__init__("atr_filter", config, preset)
        
        params = config.get("parameters", {})
        self.period = params.get("period", 14)
        self.method = params.get("method", "relative_percentile")
        self.use_relative_atr = params.get("use_relative_atr", True)
        
        # Thresholds adaptativos según volatilidad
        volatility_thresholds = self.config.get("thresholds", {})
        self.high_vol_thresholds = volatility_thresholds.get("high_vol", {})
        self.normal_vol_thresholds = volatility_thresholds.get("normal_vol", {})
        self.low_vol_thresholds = volatility_thresholds.get("low_vol", {})
        
        # Thresholds del preset como fallback
        self.min_atr_percentile = self.thresholds.get("min_atr_percentile", 60)
        self.min_relative_atr = self.thresholds.get("min_relative_atr", 0.006)
    
    def _get_thresholds_for_volatility(self, market_context: Dict) -> Dict:
        """Obtener thresholds según régimen de volatilidad."""
        vol_regime = market_context.get("volatility_regime", "normal")
        
        if vol_regime == "high":
            return self.high_vol_thresholds or self.thresholds
        elif vol_regime == "low":
            return self.low_vol_thresholds or self.thresholds
        else:
            return self.normal_vol_thresholds or self.thresholds
    
    def _apply_filter_logic(
        self,
        indicators: Dict,
        market_context: Dict,
        signal_type: str
    ) -> Dict:
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
            # Requiere tanto percentil como ATR relativo
            if atr_percentile is None or relative_atr is None:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': 'ATR percentile or relative ATR missing',
                    'metadata': {}
                }
            
            percentile_pass = atr_percentile >= min_atr_percentile
            relative_pass = relative_atr >= min_relative_atr
            
            if percentile_pass and relative_pass:
                # Calcular confianza basada en qué tan por encima está
                percentile_confidence = min(1.0, (atr_percentile / 100) * 1.2)
                relative_confidence = min(1.0, (relative_atr / min_relative_atr) * 0.8)
                confidence = (percentile_confidence + relative_confidence) / 2
                
                return {
                    'passed': True,
                    'confidence': confidence,
                    'reason': f'ATR percentile {atr_percentile:.1f} >= {min_atr_percentile} and relative ATR {relative_atr:.4f} >= {min_relative_atr:.4f}',
                    'metadata': {
                        'atr_percentile': atr_percentile,
                        'relative_atr': relative_atr,
                        'volatility_regime': market_context.get('volatility_regime')
                    }
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'ATR conditions not met: percentile {atr_percentile or "N/A"} >= {min_atr_percentile}, relative {relative_atr or "N/A":.4f} >= {min_relative_atr:.4f}',
                    'metadata': {'atr_percentile': atr_percentile, 'relative_atr': relative_atr}
                }
        
        elif self.method == "relative":
            # Solo requiere ATR relativo
            if relative_atr is None:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': 'Relative ATR missing',
                    'metadata': {}
                }
            
            if relative_atr >= min_relative_atr:
                confidence = min(1.0, (relative_atr / min_relative_atr) * 0.8)
                return {
                    'passed': True,
                    'confidence': confidence,
                    'reason': f'Relative ATR {relative_atr:.4f} >= {min_relative_atr:.4f}',
                    'metadata': {'relative_atr': relative_atr}
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'Relative ATR {relative_atr:.4f} below threshold',
                    'metadata': {'relative_atr': relative_atr}
                }
        
        return {
            'passed': False,
            'confidence': 0.0,
            'reason': f'Unknown ATR method: {self.method}',
            'metadata': {}
        }

