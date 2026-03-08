"""
Pyramiding Manager - R13: Pyramiding - Añadir a Ganadores

Implementa añadir posiciones solo a trades ganadores, nunca a perdedoras.

R13 Rules:
- Solo añadir si P&L > 0 (posición ganadora)
- Máximo 2 adiciones
- Primera adición: 50% del tamaño inicial
- Segunda adición: 25% del tamaño inicial
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PyramidingAddition:
    """Registro de una adición de posición."""

    addition_number: int
    size: Decimal
    price: Decimal
    timestamp: str
    pnl_at_addition: Decimal


@dataclass
class PyramidingResult:
    """Resultado de evaluar pyramiding."""

    can_add: bool
    size_to_add: Optional[Decimal]
    reason: str
    additions_remaining: int


class PyramidingManager:
    """
    Gestiona añadir posiciones a trades ganadores.

    Rules:
    - Solo añadir si la posición está en beneficio (P&L > 0)
    - No añadir a perdedoras
    - Máximo número de adiciones configurables
    - Tamaños de adición decrecientes

    Attributes:
        initial_size: Tamaño inicial de la posición
        max_additions: Número máximo de adiciones
        additions: Lista de porcentajes de adición
    """

    DEFAULT_ADDITIONS = [
        Decimal("0.5"),  # 50% del tamaño inicial
        Decimal("0.25"),  # 25% del tamaño inicial
    ]

    def __init__(
        self,
        initial_size: Decimal,
        max_additions: int = 2,
        first_addition_pct: Optional[Decimal] = None,
        second_addition_pct: Optional[Decimal] = None,
    ):
        """
        Inicializar PyramidingManager.

        Args:
            initial_size: Tamaño inicial de la posición
            max_additions: Número máximo de adiciones (default 2)
            first_addition_pct: Porcentaje de la primera adición (default 50%)
            second_addition_pct: Porcentaje de la segunda adición (default 25%)
        """
        if initial_size <= 0:
            raise ValueError("initial_size must be positive")
        if max_additions <= 0:
            raise ValueError("max_additions must be positive")

        self.initial_size = initial_size
        self.max_additions = max_additions

        # Configurar adiciones
        if first_addition_pct is not None and second_addition_pct is not None:
            self.additions = [first_addition_pct, second_addition_pct]
        else:
            self.additions = self.DEFAULT_ADDITIONS[:max_additions]

        self.current_additions = 0
        self.addition_history: List[PyramidingAddition] = []

    def can_add_position(self, current_pnl: Decimal) -> PyramidingResult:
        """
        Verificar si se puede añadir a la posición.

        Args:
            current_pnl: P&L actual de la posición

        Returns:
            PyramidingResult con la decisión
        """
        # Verificar si hay beneficio
        if current_pnl <= 0:
            logger.info("❌ No pyramiding: position in loss")
            return PyramidingResult(
                can_add=False,
                size_to_add=None,
                reason="Position is not profitable (P&L <= 0)",
                additions_remaining=self.max_additions - self.current_additions,
            )

        # Verificar máximo de adiciones
        if self.current_additions >= self.max_additions:
            logger.info(f"❌ No pyramiding: maximum {self.max_additions} additions reached")
            return PyramidingResult(
                can_add=False,
                size_to_add=None,
                reason=f"Maximum additions ({self.max_additions}) reached",
                additions_remaining=0,
            )

        # Calcular tamaño de adición
        addition_pct = self.additions[self.current_additions]
        size_to_add = self.initial_size * addition_pct

        return PyramidingResult(
            can_add=True,
            size_to_add=size_to_add,
            reason=f"Can add {addition_pct:.1%} of initial size ({size_to_add} shares)",
            additions_remaining=self.max_additions - self.current_additions - 1,
        )

    def get_addition_size(self) -> Optional[Decimal]:
        """
        Calcular tamaño de siguiente adición.

        Returns:
            Tamaño de la adición, o None si no hay más adiciones posibles
        """
        if self.current_additions >= len(self.additions):
            return None

        addition_pct = self.additions[self.current_additions]
        return self.initial_size * addition_pct

    def add_position(self, price: Decimal, current_pnl: Decimal) -> PyramidingResult:
        """
        Añadir a la posición (registra la adición).

        Args:
            price: Precio de la adición
            current_pnl: P&L actual en el momento de la adición

        Returns:
            PyramidingResult con el resultado de la adición
        """
        result = self.can_add_position(current_pnl)

        if not result.can_add:
            return result

        # Registrar adición
        from datetime import datetime

        addition = PyramidingAddition(
            addition_number=self.current_additions + 1,
            size=result.size_to_add,
            price=price,
            timestamp=datetime.utcnow().isoformat(),
            pnl_at_addition=current_pnl,
        )
        self.addition_history.append(addition)
        self.current_additions += 1

        logger.info(
            f"✅ Pyramiding addition #{addition.addition_number}: "
            f"{addition.size} shares @ {addition.price} "
            f"(P&L: {current_pnl})"
        )

        return result

    def get_addition_history(self) -> List[PyramidingAddition]:
        """Obtener historial de adiciones."""
        return self.addition_history.copy()

    def get_total_added(self) -> Decimal:
        """Obtener total de acciones añadidas."""
        return sum(a.size for a in self.addition_history)

    def reset(self, initial_size: Decimal) -> None:
        """
        Reiniciar el manager para una nueva posición.

        Args:
            initial_size: Nuevo tamaño inicial
        """
        self.initial_size = initial_size
        self.current_additions = 0
        self.addition_history.clear()

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "initial_size": str(self.initial_size),
            "max_additions": self.max_additions,
            "additions": [str(pct) for pct in self.additions],
            "current_additions": self.current_additions,
            "addition_history": [
                {
                    "addition_number": a.addition_number,
                    "size": str(a.size),
                    "price": str(a.price),
                    "timestamp": a.timestamp,
                    "pnl_at_addition": str(a.pnl_at_addition),
                }
                for a in self.addition_history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PyramidingManager":
        """Crear instancia desde diccionario."""
        initial_size = Decimal(data["initial_size"])
        max_additions = data["max_additions"]
        additions = [Decimal(pct) for pct in data["additions"]]

        instance = cls(
            initial_size=initial_size,
            max_additions=max_additions,
        )
        instance.additions = additions
        instance.current_additions = data["current_additions"]


        for a_data in data["addition_history"]:
            addition = PyramidingAddition(
                addition_number=a_data["addition_number"],
                size=Decimal(a_data["size"]),
                price=Decimal(a_data["price"]),
                timestamp=a_data["timestamp"],
                pnl_at_addition=Decimal(a_data["pnl_at_addition"]),
            )
            instance.addition_history.append(addition)

        return instance
