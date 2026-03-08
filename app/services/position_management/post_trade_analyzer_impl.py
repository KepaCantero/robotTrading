"""
Post Trade Analyzer Implementation - Implements IPostTradeAnalyzer Protocol

Implementa el Protocol IPostTradeAnalyzer con gestión de trailing stops,
take profits parciales, y pyramiding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from app.core.protocols.i_post_trade_analyzer import IPostTradeAnalyzer

if TYPE_CHECKING:
    from app.domain.entities.position import Position

from app.services.position_management.partial_take_profit import PartialTakeProfit
from app.services.position_management.pyramiding_manager import PyramidingManager
from app.services.position_management.trailing_stop_manager import TrailingStopManager

logger = logging.getLogger(__name__)


@dataclass
class PositionState:
    """Estado de gestión de una posición."""

    position_id: str
    trailing_stop_manager: TrailingStopManager
    partial_take_profit: PartialTakeProfit
    pyramiding_manager: Optional[PyramidingManager] = None
    entry_price: Decimal = Decimal("0")
    initial_stop: Decimal = Decimal("0")
    quantity: Decimal = Decimal("0")


@dataclass
class TradeSignal:
    """Señal de trading generada."""

    signal_type: str  # "exit", "partial_exit", "add", "none"
    reason: str
    size: Optional[Decimal] = None
    price: Optional[Decimal] = None


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
    ) -> Optional[Decimal]:
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
        position = self._get_position_entity(position_id)
        if position is None:
            return None

        # Calcular P&L no realizado
        unrealized_pnl = position.get_unrealized_pnl_amount()

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

        state = self.positions[position_id]
        position = self._get_position_entity(position_id)
        if position is None:
            return False

        # Verificar targets
        action = state.partial_take_profit.check_targets(
            current_price=position.current_price,
            position_size=position.quantity,
        )

        if action is not None:
            logger.info(
                f"Take profit action for {position_id}: "
                f"close {action.size_to_close} shares ({action.action})"
            )
            return True

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
        position = self._get_position_entity(position_id)
        if position is None:
            return {}

        state = self.positions.get(position_id)

        # Calcular riesgo inicial
        if state and state.initial_stop > 0:
            initial_risk = abs(state.entry_price - state.initial_stop)
        else:
            initial_risk = Decimal("0")

        # Calcular R-múltiplo actual
        if initial_risk > 0:
            unrealized_pnl = position.get_unrealized_pnl_amount()
            r_multiple = float(unrealized_pnl / initial_risk)
        else:
            r_multiple = 0.0

        return {
            "position_id": position_id,
            "symbol": position.symbol,
            "side": position.side.value,
            "quantity": str(position.quantity),
            "entry_price": str(position.avg_entry_price),
            "current_price": str(position.current_price),
            "unrealized_pnl": str(position.get_unrealized_pnl_amount()),
            "unrealized_pnl_percent": str(position.get_pnl_percent()),
            "initial_stop": str(state.initial_stop) if state else None,
            "current_stop": str(state.trailing_stop_manager.get_current_stop()) if state else None,
            "r_multiple": r_multiple,
            "max_price": str(position.max_price),
            "min_price": str(position.min_price),
            "age_days": position.get_age_days(),
            "is_open": position.is_open(),
            "is_profitable": position.is_profitable(),
        }

    async def generate_exit_signal(self, position_id: str) -> Optional[TradeSignal]:
        """
        Generar señal de salida.

        Evalúa todas las condiciones y genera una señal si es necesario.

        Args:
            position_id: ID de la posición

        Returns:
            TradeSignal si hay acción requerida, None si no
        """
        position = self._get_position_entity(position_id)
        if position is None or not position.is_open():
            return None

        state = self.positions.get(position_id)
        if state is None:
            return None

        # 1. Verificar stop loss
        if position.is_stop_loss_hit():
            return TradeSignal(
                signal_type="exit",
                reason=f"Stop loss hit at {position.stop_loss}",
                size=position.quantity,
                price=position.stop_loss,
            )

        # 2. Verificar take profit
        if position.is_take_profit_hit():
            return TradeSignal(
                signal_type="exit",
                reason=f"Take profit hit at {position.take_profit}",
                size=position.quantity,
                price=position.take_profit,
            )

        # 3. Verificar take profit parcial
        unrealized_pnl = position.get_unrealized_pnl_amount()
        partial_tp_action = state.partial_take_profit.check_targets(
            current_price=position.current_price,
            position_size=position.quantity,
        )
        if partial_tp_action is not None:
            return TradeSignal(
                signal_type="partial_exit",
                reason=partial_tp_action.reason,
                size=partial_tp_action.size_to_close,
                price=position.current_price,
            )

        # 4. Verificar trailing stop
        current_stop = state.trailing_stop_manager.get_current_stop()
        if position.side.value == "long" and position.current_price <= current_stop:
            return TradeSignal(
                signal_type="exit",
                reason=f"Trailing stop hit at {current_stop}",
                size=position.quantity,
                price=current_stop,
            )
        elif position.side.value == "short" and position.current_price >= current_stop:
            return TradeSignal(
                signal_type="exit",
                reason=f"Trailing stop hit at {current_stop}",
                size=position.quantity,
                price=current_stop,
            )

        # 5. Evaluar pyramiding (señal de añadir, no salida)
        if state.pyramiding_manager is not None:
            pyramiding_result = state.pyramiding_manager.can_add_position(unrealized_pnl)
            if pyramiding_result.can_add:
                return TradeSignal(
                    signal_type="add",
                    reason=pyramiding_result.reason,
                    size=pyramiding_result.size_to_add,
                    price=position.current_price,
                )

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

    def _get_position_entity(self, position_id: str) -> Optional["Position"]:
        """
        Obtener la entidad Position desde el repositorio.

        @todo Implementar búsqueda real desde PositionRepository.

        Args:
            position_id: ID de la posición

        Returns:
            Position entity o None si no existe
        """
        # @todo Implementar búsqueda desde PositionRepository
        # Por ahora retornar None para que los métodos manejen el caso
        return None

    def get_position_state(self, position_id: str) -> Optional[PositionState]:
        """
        Obtener el estado de gestión de una posición.

        Args:
            position_id: ID de la posición

        Returns:
            PositionState o None si no existe
        """
        return self.positions.get(position_id)
