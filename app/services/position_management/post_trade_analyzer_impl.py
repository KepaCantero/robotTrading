"""
Post Trade Analyzer Implementation - Implements IPostTradeAnalyzer Protocol

Implementa el Protocol IPostTradeAnalyzer con gestión de trailing stops,
take profits parciales, y pyramiding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from app.services.position_management.partial_take_profit import PartialTakeProfit
from app.services.position_management.pyramiding_manager import PyramidingManager
from app.services.position_management.trailing_stop_manager import TrailingStopManager
from app.shared.protocols.i_post_trade_analyzer import IPostTradeAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class PositionState:
    """Estado de gestión de una posición."""

    position_id: str
    trailing_stop_manager: TrailingStopManager
    partial_take_profit: PartialTakeProfit
    pyramiding_manager: PyramidingManager | None = None
    entry_price: Decimal = Decimal("0")
    initial_stop: Decimal = Decimal("0")
    quantity: Decimal = Decimal("0")


@dataclass
class TradeSignal:
    """Señal de trading generada."""

    signal_type: str  # "exit", "partial_exit", "add", "none"
    reason: str
    size: Decimal | None = None
    price: Decimal | None = None


class PostTradeAnalyzerImpl(IPostTradeAnalyzer):
    """
    Implementación de IPostTradeAnalyzer Protocol.

    Gestiona:
    - R11: Trailing Stop Dinámico
    - R12: Take Profit Parcial
    - R13: Pyramiding (solo ganadores)

    Esta clase tiene máximo 5 métodos públicos (ISP-001).
    """

    def __init__(self):
        """Inicializar PostTradeAnalyzerImpl."""
        self.positions: dict[str, PositionState] = {}

    async def update_trailing_stop(
        self, position_id: str, current_price: Decimal
    ) -> Decimal | None:
        """
        R11: Trailing Stop Dinámico.

        Actualiza el trailing stop según el precio actual.

        Args:
            position_id: ID de la posición
            current_price: Precio actual del activo

        Returns:
            Nuevo stop si cambió, None si igual
        """
        if position_id not in self.positions:
            logger.warning(f"Position {position_id} not found for trailing stop update")
            return None

        state = self.positions[position_id]

        # TODO: Implementar obtención de Position entity desde repositorio
        # Por ahora, usamos los datos almacenados en PositionState
        unrealized_pnl = state.entry_price - state.initial_stop  # Placeholder

        # Actualizar trailing stop
        result = state.trailing_stop_manager.update(current_price, unrealized_pnl)

        if result.new_stop is not None:
            logger.info(
                f"Trailing stop updated for {position_id}: "
                f"{result.previous_stop} -> {result.new_stop} ({result.action})"
            )

        return result.new_stop

    async def check_partial_take_profit(self, position_id: str, current_pnl: Decimal) -> bool:
        """
        R12: Take Profit Parcial.

        Verifica si se debe cerrar parcialmente la posición.

        Args:
            position_id: ID de la posición
            current_pnl: P&L actual de la posición

        Returns:
            True si se debe cerrar parcialmente, False si no
        """
        if position_id not in self.positions:
            logger.warning(f"Position {position_id} not found for take profit check")
            return False

        # TODO: Implementar obtención de Position entity desde repositorio
        # Por ahora, no podemos verificar targets sin datos reales de posición
        logger.warning("check_partial_take_profit requires Position entity - not implemented")
        return False

    async def evaluate_pyramiding(self, position_id: str, unrealized_pnl: Decimal) -> bool:
        """
        R13: Pyramiding (solo ganadores).

        Evalúa si se puede añadir a la posición.

        Args:
            position_id: ID de la posición
            unrealized_pnl: P&L no realizado de la posición

        Returns:
            True si se puede añadir, False si no
        """
        if position_id not in self.positions:
            logger.warning(f"Position {position_id} not found for pyramiding evaluation")
            return False

        state = self.positions[position_id]

        # Si no hay pyramiding manager, no se puede añadir
        if state.pyramiding_manager is None:
            return False

        # Evaluar si se puede añadir
        result = state.pyramiding_manager.can_add_position(unrealized_pnl)

        if result.can_add:
            logger.info(
                f"Pyramiding possible for {position_id}: "
                f"add {result.size_to_add} shares ({result.reason})"
            )
            return True

        return False

    async def calculate_position_metrics(self, position_id: str) -> dict:
        """
        Calcular métricas de posición.

        Args:
            position_id: ID de la posición

        Returns:
            Diccionario con métricas de la posición
        """
        # TODO: Implementar obtención de Position entity desde repositorio
        logger.warning("calculate_position_metrics requires Position entity - not implemented")
        return {}

    async def generate_exit_signal(self, position_id: str) -> TradeSignal | None:
        """
        Generar señal de salida.

        Evalúa todas las condiciones y genera una señal si es necesario.

        Args:
            position_id: ID de la posición

        Returns:
            TradeSignal si hay acción requerida, None si no
        """
        # TODO: Implementar obtención de Position entity desde repositorio
        logger.warning("generate_exit_signal requires Position entity - not implemented")
        return None

    def register_position(
        self,
        position_id: str,
        entry_price: Decimal,
        initial_stop: Decimal,
        quantity: Decimal,
        enable_pyramiding: bool = False,
    ) -> None:
        """
        Registrar una posición para gestión.

        Args:
            position_id: ID único de la posición
            entry_price: Precio de entrada
            initial_stop: Stop loss inicial
            quantity: Tamaño de la posición
            enable_pyramiding: Si se permite pyramiding
        """
        trailing_stop_manager = TrailingStopManager(
            entry_price=entry_price,
            initial_stop=initial_stop,
        )

        partial_take_profit = PartialTakeProfit(
            entry_price=entry_price,
            initial_stop=initial_stop,
        )

        pyramiding_manager = None
        if enable_pyramiding:
            pyramiding_manager = PyramidingManager(initial_size=quantity)

        self.positions[position_id] = PositionState(
            position_id=position_id,
            trailing_stop_manager=trailing_stop_manager,
            partial_take_profit=partial_take_profit,
            pyramiding_manager=pyramiding_manager,
            entry_price=entry_price,
            initial_stop=initial_stop,
            quantity=quantity,
        )

        logger.info(f"Position {position_id} registered for post-trade management")

    def unregister_position(self, position_id: str) -> None:
        """
        Desregistrar una posición (cerrada).

        Args:
            position_id: ID de la posición a desregistrar
        """
        if position_id in self.positions:
            del self.positions[position_id]
            logger.info(f"Position {position_id} unregistered from post-trade management")

    def get_position_state(self, position_id: str) -> PositionState | None:
        """
        Obtener el estado de gestión de una posición.

        Args:
            position_id: ID de la posición

        Returns:
            PositionState o None si no existe
        """
        return self.positions.get(position_id)
