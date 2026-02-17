"""
MomentumFilter - Filtro de momentum usando Rate of Change (ROC).
"""

import logging
from typing import Dict

from ..base_filter import BaseFilter

logger = logging.getLogger(__name__)


class MomentumFilter(BaseFilter):
    """
    Filtro de momentum basado en Rate of Change.

    Evalúa si hay suficiente momentum positivo (para compra) o negativo (para venta).
    """

    def __init__(
        self, config: Dict = None, preset: str = "balanced", tier: str = None, use_yaml: bool = True
    ):
        """Inicializar filtro de momentum."""
        super().__init__("momentum_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.period = settings.get("period", 12)
        self.method = settings.get("method", "roc")

        # Thresholds del preset (usar thresholds cargados desde YAML)
        # FIX: Lowered from 0.015 (1.5%) - too restrictive, missing valid signals
        self.min_positive_momentum = self.thresholds.get("min_positive_momentum", 0.005)
        # FIX: Raised from -0.015 - allow earlier SELL signals on weakening momentum
        self.min_negative_momentum = self.thresholds.get("min_negative_momentum", -0.005)

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """Aplicar lógica del filtro de momentum."""
        momentum = indicators.get("momentum_roc")
        if momentum is None:
            # Intentar con otros nombres posibles
            momentum = indicators.get("roc") or indicators.get("momentum")

        if momentum is None:
            return {
                'passed': False,
                'confidence': 0.0,
                'reason': 'Momentum indicator missing',
                'metadata': {},
            }

        if signal_type == "BUY":
            if momentum >= self.min_positive_momentum:
                # Calcular confianza basada en fuerza del momentum
                # Momentum más fuerte = mayor confianza (hasta 2x el mínimo)
                max_momentum = self.min_positive_momentum * 2
                normalized_momentum = min(1.0, momentum / max_momentum)
                confidence = 0.6 + (normalized_momentum * 0.4)

                return {
                    'passed': True,
                    'confidence': confidence,
                    'reason': f'Positive momentum {momentum:.4f} >= threshold {self.min_positive_momentum:.4f}',
                    'metadata': {
                        'momentum': momentum,
                        'threshold': self.min_positive_momentum,
                        'normalized': normalized_momentum,
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'Momentum {momentum:.4f} below threshold {self.min_positive_momentum:.4f}',
                    'metadata': {'momentum': momentum},
                }

        elif signal_type == "SELL":
            if momentum <= self.min_negative_momentum:
                max_momentum = abs(self.min_negative_momentum) * 2
                normalized_momentum = min(1.0, abs(momentum) / max_momentum)
                confidence = 0.6 + (normalized_momentum * 0.4)

                return {
                    'passed': True,
                    'confidence': confidence,
                    'reason': f'Negative momentum {momentum:.4f} <= threshold {self.min_negative_momentum:.4f}',
                    'metadata': {
                        'momentum': momentum,
                        'threshold': self.min_negative_momentum,
                        'normalized': normalized_momentum,
                    },
                }
            else:
                return {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f'Momentum {momentum:.4f} above threshold {self.min_negative_momentum:.4f}',
                    'metadata': {'momentum': momentum},
                }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
