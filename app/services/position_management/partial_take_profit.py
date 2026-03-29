"""
Partial Take Profit Manager - R12: Take Profit Parcial

Implementa take profit parcial en múltiples niveles de R-múltiplos.

R12 Rules:
- Cerrar 50% en 2R (move to breakeven)
- Cerrar 25% en 3R (trailing stop)
- Cerrar 25% en 5R (ninguna acción)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class ProfitTarget:
    """Objetivo de beneficio parcial."""

    r_multiple: float
    close_pct: float  # % de posición a cerrar
    action: str  # "move_to_breakeven", "trailing_stop", "none"

    def __post_init__(self):
        """Validar parámetros."""
        if self.r_multiple <= 0:
            raise ValueError("r_multiple must be positive")
        if not 0 < self.close_pct <= 1:
            raise ValueError("close_pct must be between 0 and 1")
        if self.close_pct > 1:
            raise ValueError("close_pct cannot exceed 1 (100%)")


@dataclass
class TakeProfitAction:
    """Acción de take profit a ejecutar."""

    size_to_close: Decimal
    action: str
    r_multiple: float
    reason: str


class PartialTakeProfit:
    """
    Gestiona take profit parcial en múltiples niveles.

    Los objetivos por defecto son:
    - 2R: Cerrar 50%, mover a breakeven
    - 3R: Cerrar 25%, activar trailing stop
    - 5R: Cerrar 25%, ninguna acción adicional

    Attributes:
        entry_price: Precio de entrada de la posición
        initial_stop: Stop loss inicial
        targets: Lista de objetivos de beneficio
    """

    DEFAULT_TARGETS: ClassVar[list] = [
        ProfitTarget(r_multiple=2.0, close_pct=0.50, action="move_to_breakeven"),
        ProfitTarget(r_multiple=3.0, close_pct=0.25, action="trailing_stop"),
        ProfitTarget(r_multiple=5.0, close_pct=0.25, action="none"),
    ]

    def __init__(
        self,
        entry_price: Decimal,
        initial_stop: Decimal,
        targets: list[ProfitTarget] | None = None,
    ):
        """
        Inicializar PartialTakeProfit.

        Args:
            entry_price: Precio de entrada de la posición
            initial_stop: Stop loss inicial
            targets: Lista de objetivos (usa default si None)
        """
        if entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if initial_stop <= 0:
            raise ValueError("initial_stop must be positive")

        self.entry_price = entry_price
        self.initial_stop = initial_stop
        self.targets = targets or self.DEFAULT_TARGETS
        self.executed_targets = set()

        # Validar que los targets sumen <= 100%
        total_close_pct = sum(t.close_pct for t in self.targets)
        if total_close_pct > 1.0:
            logger.warning(
                f"Total close_pct ({total_close_pct:.1%}) exceeds 100%. "
                "This will close more than the full position."
            )

    def check_targets(
        self, current_price: Decimal, position_size: Decimal
    ) -> TakeProfitAction | None:
        """
        Verificar si se alcanzó algún objetivo.

        Args:
            current_price: Precio actual del activo
            position_size: Tamaño actual de la posición

        Returns:
            TakeProfitAction si se alcanzó un objetivo, None si no
        """
        initial_risk = abs(self.entry_price - self.initial_stop)
        if initial_risk == 0:
            return None

        current_profit = current_price - self.entry_price
        r_multiple = float(current_profit / initial_risk)

        for target in self.targets:
            # Saltar targets ya ejecutados
            if target.r_multiple in self.executed_targets:
                continue

            # Verificar si se alcanzó este target
            if r_multiple >= target.r_multiple:
                self.executed_targets.add(target.r_multiple)
                size_to_close = position_size * Decimal(str(target.close_pct))

                logger.info(
                    f"Take profit target reached: {target.r_multiple}R, "
                    f"closing {target.close_pct:.1%} of position ({size_to_close} shares)"
                )

                return TakeProfitAction(
                    size_to_close=size_to_close,
                    action=target.action,
                    r_multiple=target.r_multiple,
                    reason=f"Target {target.r_multiple}R reached: {target.action}",
                )

        return None

    def reset(self, entry_price: Decimal, initial_stop: Decimal) -> None:
        """
        Reiniciar el manager para una nueva posición.

        Args:
            entry_price: Nuevo precio de entrada
            initial_stop: Nuevo stop inicial
        """
        self.entry_price = entry_price
        self.initial_stop = initial_stop
        self.executed_targets.clear()

    def get_executed_targets(self) -> list[float]:
        """Obtener lista de targets ya ejecutados."""
        return sorted(self.executed_targets)

    def get_remaining_targets(self) -> list[ProfitTarget]:
        """Obtener lista de targets pendientes."""
        return [t for t in self.targets if t.r_multiple not in self.executed_targets]

    def is_complete(self) -> bool:
        """Verificar si todos los targets han sido ejecutados."""
        return len(self.executed_targets) == len(self.targets)

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "entry_price": str(self.entry_price),
            "initial_stop": str(self.initial_stop),
            "targets": [
                {
                    "r_multiple": t.r_multiple,
                    "close_pct": t.close_pct,
                    "action": t.action,
                }
                for t in self.targets
            ],
            "executed_targets": sorted(self.executed_targets),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PartialTakeProfit:
        """Crear instancia desde diccionario."""
        targets = [
            ProfitTarget(
                r_multiple=t["r_multiple"],
                close_pct=t["close_pct"],
                action=t["action"],
            )
            for t in data["targets"]
        ]

        instance = cls(
            entry_price=Decimal(data["entry_price"]),
            initial_stop=Decimal(data["initial_stop"]),
            targets=targets,
        )
        instance.executed_targets = set(data["executed_targets"])
        return instance
