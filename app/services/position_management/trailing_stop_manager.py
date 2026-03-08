"""
Trailing Stop Manager - R11: Trailing Stop Dinámico

Implementa trailing stops dinámicos que se ajustan con el beneficio
según R-múltiplos.

R11 Rules:
- Mover a break-even en 2R
- Trailing stop 50% del beneficio en 3R
- Trailing stop 1.5% desde máximo en 1R

Uses centralized configuration for default trailing percentage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from app.shared.config.centralized_config import get_config

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class TrailingStopResult:
    """Resultado del cálculo de trailing stop."""

    new_stop: Optional[Decimal]
    previous_stop: Decimal
    r_multiple: float
    action: str  # "break_even", "trailing_50pct", "trailing_1.5pct", "none"
    reason: str


class TrailingStopManager:
    """
    Gestiona trailing stops dinámicos.

    El trailing stop se ajusta según el beneficio en R-múltiplos:
    - >= 2R: Mover a break-even
    - >= 3R: Trailing stop al 50% del beneficio
    - >= 1R: Trailing stop del 1.5% desde el máximo

    Attributes:
        entry_price: Precio de entrada de la posición
        initial_stop: Stop loss inicial
        trailing_pct: Porcentaje de trailing (uses centralized config)

    Uses centralized configuration for default trailing percentage.
    """

    def __init__(
        self,
        entry_price: Decimal,
        initial_stop: Decimal,
        trailing_pct: Optional[Decimal] = None,
    ):
        """
        Inicializar TrailingStopManager.

        Args:
            entry_price: Precio de entrada de la posición
            initial_stop: Stop loss inicial
            trailing_pct: Porcentaje de trailing (uses centralized config for default)
        """
        if entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if initial_stop <= 0:
            raise ValueError("initial_stop must be positive")

        # Store config reference for centralized access
        tt = get_config().trading_thresholds
        self._tt = tt

        self.entry_price = entry_price
        self.initial_stop = initial_stop
        # Use centralized config directly - no helper function, no fallback
        self.trailing_pct = trailing_pct or Decimal(str(tt.trailing_stop_default_pct))
        self.highest_price = entry_price
        self.current_stop = initial_stop

    def update(self, current_price: Decimal, unrealized_pnl: Decimal) -> TrailingStopResult:
        """
        Actualizar trailing stop según precio actual y P&L.

        Args:
            current_price: Precio actual del activo
            unrealized_pnl: P&L no realizado de la posición

        Returns:
            TrailingStopResult con el nuevo stop y acción tomada
        """
        # Actualizar máximo
        if current_price > self.highest_price:
            self.highest_price = current_price

        # Calcular riesgo inicial
        initial_risk = abs(self.entry_price - self.initial_stop)

        # Beneficio en R-múltiplos
        r_multiple = float(unrealized_pnl / initial_risk) if initial_risk > 0 else 0.0

        # Get R-multiple thresholds from centralized config
        r1_threshold = self._tt.trailing_stop_r1_threshold
        r2_threshold = self._tt.trailing_stop_r2_threshold
        r3_threshold = self._tt.trailing_stop_r3_threshold
        r3_trailing_pct = Decimal(str(self._tt.trailing_stop_r3_trailing_pct))

        previous_stop = self.current_stop
        new_stop = self.current_stop
        action = "none"
        reason = "No change"

        # Aplicar reglas según R-múltiplos (en orden descendente)
        if r_multiple >= r3_threshold:
            # Trailing stop al porcentaje configurado del beneficio actual
            profit = current_price - self.entry_price
            new_stop = current_price - (profit * r3_trailing_pct)
            action = "trailing_50pct"
            reason = f"R={r_multiple:.1f}: Trailing stop at {r3_trailing_pct:.0%} of profit"

        elif r_multiple >= r2_threshold:
            # Mover a break-even
            new_stop = self.entry_price
            action = "break_even"
            reason = f"R={r_multiple:.1f}: Moved to break-even"

        elif r_multiple >= r1_threshold:
            # Trailing stop del porcentaje configurado desde el precio actual
            # Esto permite que el stop suba con el precio pero no baje
            new_stop = current_price * (Decimal("1") - self.trailing_pct)
            action = "trailing_1.5pct"
            reason = (
                f"R={r_multiple:.1f}: Trailing stop at {self.trailing_pct:.2%} from current price"
            )

        # Solo actualizar si el nuevo stop es más alto (protege ganancias)
        # Para posiciones LONG, higher stop = mejor protección
        if new_stop > self.current_stop:
            self.current_stop = new_stop
            return TrailingStopResult(
                new_stop=new_stop,
                previous_stop=previous_stop,
                r_multiple=r_multiple,
                action=action,
                reason=reason,
            )

        # Sin cambios
        return TrailingStopResult(
            new_stop=None,
            previous_stop=previous_stop,
            r_multiple=r_multiple,
            action="none",
            reason=f"R={r_multiple:.1f}: No update needed (stop would move down)",
        )

    def get_current_stop(self) -> Decimal:
        """Obtener el stop actual."""
        return self.current_stop

    def reset(self, entry_price: Decimal, initial_stop: Decimal) -> None:
        """
        Reiniciar el manager para una nueva posición.

        Args:
            entry_price: Nuevo precio de entrada
            initial_stop: Nuevo stop inicial
        """
        self.entry_price = entry_price
        self.initial_stop = initial_stop
        self.highest_price = entry_price
        self.current_stop = initial_stop

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "entry_price": str(self.entry_price),
            "initial_stop": str(self.initial_stop),
            "trailing_pct": str(self.trailing_pct),
            "highest_price": str(self.highest_price),
            "current_stop": str(self.current_stop),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrailingStopManager":
        """Crear instancia desde diccionario."""
        instance = cls(
            entry_price=Decimal(data["entry_price"]),
            initial_stop=Decimal(data["initial_stop"]),
            trailing_pct=Decimal(data["trailing_pct"]),
        )
        instance.highest_price = Decimal(data["highest_price"])
        instance.current_stop = Decimal(data["current_stop"])
        return instance
