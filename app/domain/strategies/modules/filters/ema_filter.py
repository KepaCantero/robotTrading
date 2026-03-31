"""
EMAFilter - Filtro de tendencia basado en cruces de EMA.
"""

from __future__ import annotations

import logging
from typing import Optional

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

    def __init__(
        self,
        config: Optional[dict] = None,
        preset: str = "balanced",
        tier: Optional[str] = None,
        use_yaml: bool = True,
    ):
        """Inicializar filtro EMA."""
        super().__init__("ema_filter", config, preset, tier, use_yaml)

        # Get settings from YAML or config
        periods = self.config.get("periods", self.config)
        self.fast_period = periods.get("fast_ema", 12)
        self.slow_period = periods.get("slow_ema", 26)
        self.confirmation_method = self.config.get("confirmation", {}).get("price_above_ema", True)

        # Thresholds del preset (usar thresholds cargados desde YAML)
        # FIX: Lowered from 0.005 (0.5%) - too restrictive for trend confirmation
        self.min_distance_pct = self.thresholds.get("min_distance_pct", 0.002)
        self.require_crossover = self.thresholds.get("require_crossover", False)
        # FIX: Allow dip buying even if price slightly below EMA fast during pullbacks
        self.allow_dip_buy = self.thresholds.get("allow_dip_buy", True)

    def _apply_filter_logic(self, indicators: dict, market_context: dict, signal_type: str) -> dict:
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
                "passed": False,
                "confidence": 0.0,
                "reason": "EMA indicators missing",
                "metadata": {},
            }

        # DEBUG: Log EMA values to understand why SELL passes but BUY doesn't
        logger.debug(
            f"EMA_FILTER: price={current_price:.2f}, fast={ema_fast:.2f}, slow={ema_slow:.2f}, "
            f"fast>slow={ema_fast > ema_slow}, price>fast={current_price > ema_fast}"
        )

        if signal_type == "BUY":
            # Verificar que EMA rápida esté por encima de EMA lenta
            fast_above_slow = ema_fast > ema_slow

            if not fast_above_slow:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"EMA fast ({ema_fast:.2f}) not above EMA slow ({ema_slow:.2f})",
                    "metadata": {"ema_fast": ema_fast, "ema_slow": ema_slow},
                }

            # Verificar distancia mínima
            distance_pct = (ema_fast - ema_slow) / ema_slow
            if distance_pct < self.min_distance_pct:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"EMA distance {distance_pct:.4f} < threshold {self.min_distance_pct:.4f}",
                    "metadata": {"distance_pct": distance_pct},
                }

            # Verificar precio vs EMA según método
            # FIX: Allow dip buying during pullbacks (price can be slightly below EMA fast)
            if self.confirmation_method == "price_above" and not self.allow_dip_buy:
                if current_price <= ema_fast:
                    return {
                        "passed": False,
                        "confidence": 0.0,
                        "reason": f"Price ({current_price:.2f}) not above EMA fast ({ema_fast:.2f})",
                        "metadata": {},
                    }
            elif self.confirmation_method == "price_above" and self.allow_dip_buy:
                # Allow price to be up to 2% below EMA fast (dip opportunity)
                max_dip_pct = 0.02
                dip_pct = (ema_fast - current_price) / ema_fast if current_price < ema_fast else 0
                if dip_pct > max_dip_pct:
                    return {
                        "passed": False,
                        "confidence": 0.0,
                        "reason": f"Price ({current_price:.2f}) too far below EMA fast ({ema_fast:.2f}): dip {dip_pct:.2%} > {max_dip_pct:.2%}",
                        "metadata": {},
                    }

            # Calcular confianza basada en distancia
            confidence = min(1.0, (distance_pct / self.min_distance_pct) * 0.8)

            return {
                "passed": True,
                "confidence": confidence,
                "reason": f"EMA trend confirmed: distance {distance_pct:.4f}",
                "metadata": {
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "distance_pct": distance_pct,
                    "price_above_fast": current_price > ema_fast,
                },
            }

        elif signal_type == "SELL":
            # Lógica inversa para SELL
            slow_above_fast = ema_slow > ema_fast

            if not slow_above_fast:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"EMA slow ({ema_slow:.2f}) not above EMA fast ({ema_fast:.2f})",
                    "metadata": {},
                }

            distance_pct = (ema_slow - ema_fast) / ema_fast
            if distance_pct < self.min_distance_pct:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"EMA distance {distance_pct:.4f} < threshold",
                    "metadata": {},
                }

            if self.confirmation_method == "price_above" and current_price >= ema_slow:
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"Price ({current_price:.2f}) not below EMA slow ({ema_slow:.2f})",
                    "metadata": {},
                }

            confidence = min(1.0, (distance_pct / self.min_distance_pct) * 0.8)

            return {
                "passed": True,
                "confidence": confidence,
                "reason": "EMA downtrend confirmed",
                "metadata": {"distance_pct": distance_pct},
            }

        return {"passed": False, "confidence": 0.0, "reason": "Unknown signal type", "metadata": {}}
