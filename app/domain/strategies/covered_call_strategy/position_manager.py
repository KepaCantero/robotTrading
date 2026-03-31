"""
Position Manager - Gestión de Posiciones Covered Call

Implementa gestión completa de posiciones covered call:
- Apertura de nuevas posiciones
- Monitoreo de posiciones existentes
- Cierre de posiciones
- Cálculo de P&L
- Evaluación de probabilidad de assignment

SOLID Principles:
- Single Responsibility: Solo gestión de posiciones, no análisis
- Open/Closed: Extensible con nuevos tipos de gestión
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from .greeks_calculator import GreeksCalculator
from .models import (
    AssignmentProbability,
    CallOption,
    CoveredCallConfig,
    CoveredCallPosition,
    RollDecision,
    RollType,
)

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Gestor de posiciones covered call.

    Maneja el ciclo de vida completo de posiciones covered call:
    - Apertura
    - Monitoreo
    - Decisión de rolling
    - Cierre/Assignment

    Attributes:
        config: Configuración de la estrategia
        greeks_calculator: Calculador de Greeks
        positions: Posiciones activas
        closed_positions: Posiciones cerradas
    """

    def __init__(
        self,
        config: CoveredCallConfig,
        greeks_calculator: GreeksCalculator | None = None,
    ):
        """
        Inicializar gestor de posiciones.

        Args:
            config: Configuración de la estrategia
            greeks_calculator: Calculador de Greeks
        """
        self.config = config
        self.greeks_calculator = greeks_calculator or GreeksCalculator()

        # Almacenamiento de posiciones
        self.positions: dict[str, CoveredCallPosition] = {}
        self.closed_positions: list[CoveredCallPosition] = []

        # Estadísticas
        self.total_premium_collected = Decimal("0")
        self.total_assignments = 0
        self.positions_opened = 0
        self.positions_closed = 0

        logger.info(
            f"PositionManager inicializado: "
            f"max_position={config.max_position_size}, "
            f"target_DTE={config.target_dte}, "
            f"target_OTM={config.target_otm_pct}"
        )

    def open_position(
        self,
        symbol: str,
        shares_owned: int,
        average_cost: Decimal,
        current_price: Decimal,
        call_option: CallOption,
        contracts_to_sell: int,
        premium_received: Decimal,
    ) -> CoveredCallPosition:
        """
        Abrir una posición covered call.

        Args:
            symbol: Símbolo del activo
            shares_owned: Acciones poseídas
            average_cost: Costo promedio por acción
            current_price: Precio actual
            call_option: Opción a vender
            contracts_to_sell: Contratos a vender
            premium_received: Prima recibida (por contrato)

        Returns:
            Posición creada

        Raises:
            ValueError: Si la posición es inválida
        """
        # Validaciones
        if shares_owned < self.config.min_shares_required:
            raise ValueError(
                f"Acciones insuficientes: {shares_owned} < {self.config.min_shares_required}"
            )

        max_contracts = shares_owned // 100
        if contracts_to_sell > max_contracts:
            raise ValueError(f"Contratos exceden acciones: {contracts_to_sell} > {max_contracts}")

        if contracts_to_sell > self.config.max_contracts_per_position:
            raise ValueError(
                f"Contratos exceden máximo: {contracts_to_sell} > {self.config.max_contracts_per_position}"
            )

        # Calcular probabilidad de assignment
        assignment_prob_str = self.greeks_calculator.estimate_probability(
            call_option, current_price
        )
        assignment_prob = AssignmentProbability(assignment_prob_str)

        # Calcular prima total
        total_premium = premium_received * contracts_to_sell * 100

        # Crear posición
        position = CoveredCallPosition(
            symbol=symbol,
            shares_owned=shares_owned,
            average_cost=average_cost,
            call_option=call_option,
            contracts_sold=contracts_to_sell,
            premium_received=premium_received,
            total_premium=total_premium,
            opened_at=date.today(),
            current_price=current_price,
            assignment_probability=assignment_prob,
        )

        # Calcular retornos esperados
        position.expected_return = position.return_if_unchanged

        # Almacenar
        key = f"{symbol}_{call_option.expiry_date}_{call_option.strike}"
        self.positions[key] = position

        # Actualizar estadísticas
        self.total_premium_collected += position.total_premium
        self.positions_opened += 1

        logger.info(
            f"✅ Posición abierta: {symbol} {contracts_to_sell} contratos, "
            f"strike=${call_option.strike}, expiry={call_option.expiry_date}, "
            f"premium=${position.total_premium:.2f}"
        )

        return position

    def update_position(
        self,
        symbol: str,
        expiry_date: date,
        strike: Decimal,
        current_price: Decimal,
        current_option_price: Decimal | None = None,
    ) -> CoveredCallPosition | None:
        """
        Actualizar una posición existente.

        Args:
            symbol: Símbolo del activo
            expiry_date: Fecha de vencimiento
            strike: Strike de la opción
            current_price: Precio actual del subyacente
            current_option_price: Precio actual de la opción

        Returns:
            Posición actualizada o None si no existe
        """
        key = f"{symbol}_{expiry_date}_{strike}"
        position = self.positions.get(key)

        if position is None:
            logger.warning(f"Posición no encontrada: {key}")
            return None

        # Actualizar precios
        position.current_price = current_price
        position.current_option_price = current_option_price

        # Recalcular probabilidad de assignment
        prob_str = self.greeks_calculator.estimate_probability(position.call_option, current_price)
        position.assignment_probability = AssignmentProbability(prob_str)

        logger.debug(
            f"Posición actualizada: {symbol} P=${current_price:.2f}, "
            f"prob={position.assignment_probability}"
        )

        return position

    def close_position(
        self,
        symbol: str,
        expiry_date: date,
        strike: Decimal,
        close_price: Decimal | None = None,
        reason: str = "manual",
    ) -> CoveredCallPosition | None:
        """
        Cerrar una posición.

        Args:
            symbol: Símbolo del activo
            expiry_date: Fecha de vencimiento
            strike: Strike de la opción
            close_price: Precio de cierre de la opción (para buy-to-close)
            reason: Razón del cierre

        Returns:
            Posición cerrada o None si no existe
        """
        key = f"{symbol}_{expiry_date}_{strike}"
        position = self.positions.pop(key, None)

        if position is None:
            logger.warning(f"Posición no encontrada: {key}")
            return None

        # Calcular P&L si se proporciona precio de cierre
        if close_price is not None:
            # P&L = premium_recibida - coste_cierre
            close_cost = close_price * position.contracts_sold * 100
            profit = position.total_premium - close_cost

            # Agregar a metadata
            position.metadata["close_price"] = str(close_price)
            position.metadata["close_profit"] = str(profit)
            position.metadata["close_reason"] = reason

        # Mover a cerradas
        self.closed_positions.append(position)
        self.positions_closed += 1

        logger.info(f"📊 Posición cerrada: {symbol} strike=${strike}, razón={reason}")

        return position

    def should_roll_position(
        self,
        symbol: str,
        expiry_date: date,
        strike: Decimal,
        current_price: Decimal,
    ) -> RollDecision:
        """
        Determinar si se debe hacer roll de una posición.

        Razones para hacer roll:
        1. Días al vencimiento bajo (time decay management)
        2. Opción ITM con alta probabilidad de assignment
        3. Opción profundamente OTM (opportunidad de bajar strike y recibir más prima)

        Args:
            symbol: Símbolo del activo
            expiry_date: Fecha de vencimiento
            strike: Strike de la opción
            current_price: Precio actual

        Returns:
            Decisión de rolling
        """
        key = f"{symbol}_{expiry_date}_{strike}"
        position = self.positions.get(key)

        if position is None:
            return RollDecision(
                should_roll=False,
                roll_type=None,
                new_strike=None,
                new_expiry=None,
                reason="Posición no encontrada",
                confidence=Decimal("0"),
            )

        dte = position.call_option.days_to_expiry
        otm_pct = self._calculate_otm_pct(position, current_price)

        # Resolve optional expiry_date for the call option
        option_expiry = position.call_option.expiry_date or position.call_option.expiry

        # 1. Roll por DTE bajo
        if dte <= self.config.roll_threshold_days:
            if otm_pct < 0:  # ITM
                # Roll up and out
                new_strike = current_price * (1 + self.config.target_otm_pct)
                new_expiry = self._calculate_next_expiry(option_expiry)

                return RollDecision(
                    should_roll=True,
                    roll_type=RollType.ROLL_OUT_UP,
                    new_strike=new_strike,
                    new_expiry=new_expiry,
                    reason=f"DTE bajo ({dte}d) y ITM, roll up&out",
                    confidence=Decimal("80"),
                )
            else:
                # Roll out (mismo strike, más tiempo)
                new_expiry = self._calculate_next_expiry(option_expiry)

                return RollDecision(
                    should_roll=True,
                    roll_type=RollType.ROLL_OUT,
                    new_strike=strike,
                    new_expiry=new_expiry,
                    reason=f"DTE bajo ({dte}d) y OTM, roll out",
                    confidence=Decimal("70"),
                )

        # 2. Roll si está ITM con alta probabilidad de assignment
        if position.assignment_probability in [
            AssignmentProbability.HIGH,
            AssignmentProbability.VERY_HIGH,
        ]:
            new_strike = current_price * (1 + self.config.target_otm_pct)
            new_expiry = self._calculate_next_expiry(option_expiry)

            return RollDecision(
                should_roll=True,
                roll_type=RollType.ROLL_OUT_UP,
                new_strike=new_strike,
                new_expiry=new_expiry,
                reason=f"Alta probabilidad de assignment ({position.assignment_probability})",
                confidence=Decimal("85"),
            )

        # 3. Roll si está muy OTM (bajar strike, recibir más prima)
        if otm_pct > float(self.config.roll_threshold_otm):
            new_strike = current_price * (1 + self.config.target_otm_pct)
            new_expiry = self._calculate_next_expiry(option_expiry)

            return RollDecision(
                should_roll=True,
                roll_type=RollType.ROLL_OUT_DOWN,
                new_strike=new_strike,
                new_expiry=new_expiry,
                reason=f"Muy OTM ({otm_pct:.1%}), oportunidad de bajar strike",
                confidence=Decimal("60"),
            )

        # No hacer roll
        return RollDecision(
            should_roll=False,
            roll_type=None,
            new_strike=None,
            new_expiry=None,
            reason="No se justifica roll",
            confidence=Decimal("90"),
        )

    def get_position(
        self,
        symbol: str,
        expiry_date: date,
        strike: Decimal,
    ) -> CoveredCallPosition | None:
        """
        Obtener una posición específica.

        Args:
            symbol: Símbolo del activo
            expiry_date: Fecha de vencimiento
            strike: Strike de la opción

        Returns:
            Posición o None si no existe
        """
        key = f"{symbol}_{expiry_date}_{strike}"
        return self.positions.get(key)

    def get_all_positions(self) -> list[CoveredCallPosition]:
        """Obtener todas las posiciones activas."""
        return list(self.positions.values())

    def get_positions_by_symbol(self, symbol: str) -> list[CoveredCallPosition]:
        """Obtener posiciones por símbolo."""
        return [pos for pos in self.positions.values() if pos.symbol == symbol]

    def get_expiring_positions(self, days: int = 7) -> list[CoveredCallPosition]:
        """
        Obtener posiciones que vencen pronto.

        Args:
            days: Días de umbral

        Returns:
            Lista de posiciones próximas a vencer
        """
        threshold = date.today() + timedelta(days=days)

        return [
            pos
            for pos in self.positions.values()
            if pos.call_option.expiry_date is not None and pos.call_option.expiry_date <= threshold
        ]

    def get_itm_positions(self, current_prices: dict[str, Decimal]) -> list[CoveredCallPosition]:
        """
        Obtener posiciones ITM.

        Args:
            current_prices: Precios actuales por símbolo

        Returns:
            Lista de posiciones ITM
        """
        itm_positions = []

        for position in self.positions.values():
            current_price = current_prices.get(position.symbol)
            if current_price is None:
                continue

            position.current_price = current_price

            if position.call_option.is_itm:
                itm_positions.append(position)

        return itm_positions

    def calculate_portfolio_pnl(
        self, current_prices: dict[str, Decimal]
    ) -> dict[str, Decimal | dict[str, Decimal]]:
        """
        Calcular P&L del portfolio.

        Args:
            current_prices: Precios actuales por símbolo

        Returns:
            Dict con P&L total y por posición
        """
        total_pnl = Decimal("0")
        pnl_by_position: dict[str, Decimal] = {}

        for key, position in self.positions.items():
            current_price = current_prices.get(position.symbol)
            if current_price is None:
                continue

            # P&L sin realizar = valor_actual - costo_net
            if position.total_value is not None:
                unrealized_pnl = position.total_value - position.net_cost
                pnl_by_position[key] = unrealized_pnl
                total_pnl += unrealized_pnl

        total_realized_pnl = Decimal("0")
        for pos in self.closed_positions:
            close_profit_str = pos.metadata.get("close_profit", "0")
            total_realized_pnl += Decimal(close_profit_str)

        return {
            "total_unrealized_pnl": total_pnl,
            "by_position": pnl_by_position,
            "total_premium_collected": self.total_premium_collected,
            "total_realized_pnl": total_realized_pnl,
        }

    def get_position_metrics(
        self,
    ) -> dict[str, Decimal | int | float]:
        """
        Obtener métricas agregadas del portfolio.

        Returns:
            Dict con métricas
        """
        if not self.positions:
            return {
                "total_positions": 0,
                "total_contracts": 0,
                "total_premium": Decimal("0"),
                "weighted_dte": 0,
                "weighted_otm_pct": 0,
                "high_probability_count": 0,
            }

        total_contracts = sum(pos.contracts_sold for pos in self.positions.values())
        weighted_dte = (
            sum(
                pos.call_option.days_to_expiry * pos.contracts_sold
                for pos in self.positions.values()
            )
            / total_contracts
            if total_contracts > 0
            else 0
        )

        otm_pcts = []
        high_prob_count = 0

        for pos in self.positions.values():
            if pos.current_price is not None:
                otm_pct = self._calculate_otm_pct(pos, pos.current_price)
                otm_pcts.append(otm_pct * pos.contracts_sold)

            if pos.assignment_probability in [
                AssignmentProbability.HIGH,
                AssignmentProbability.VERY_HIGH,
            ]:
                high_prob_count += pos.contracts_sold

        weighted_otm_pct = (
            sum(otm_pcts) / total_contracts if total_contracts > 0 and otm_pcts else 0
        )

        return {
            "total_positions": len(self.positions),
            "total_contracts": total_contracts,
            "total_premium": self.total_premium_collected,
            "weighted_dte": round(weighted_dte, 1),
            "weighted_otm_pct": round(weighted_otm_pct * 100, 2),  # Como %
            "high_probability_count": high_prob_count,
            "positions_opened": self.positions_opened,
            "positions_closed": self.positions_closed,
            "total_assignments": self.total_assignments,
        }

    def _calculate_otm_pct(self, position: CoveredCallPosition, current_price: Decimal) -> float:
        """Calcular porcentaje OTM."""
        return float((position.call_option.strike - current_price) / current_price)

    def _calculate_next_expiry(self, current_expiry: date) -> date:
        """
        Calcular próxima fecha de vencimiento.

        Busca el ciclo de opciones siguiente (generalmente +30 días).
        """
        # Ciclos típicos: 30, 60, 90 días
        for days in [30, 60, 90]:
            next_expiry = current_expiry + timedelta(days=days)
            # Evitar fines de semana
            if next_expiry.weekday() < 5:
                return next_expiry

        # Fallback: +30 días
        return current_expiry + timedelta(days=30)

    def record_assignment(self, position: CoveredCallPosition) -> None:
        """
        Registrar assignment de una posición.

        Args:
            position: Posición que fue asignada
        """
        key = f"{position.symbol}_{position.call_option.expiry_date}_{position.call_option.strike}"

        if key in self.positions:
            del self.positions[key]

        position.metadata["assigned"] = "True"
        position.metadata["assignment_date"] = date.today().isoformat()

        self.closed_positions.append(position)
        self.total_assignments += 1

        logger.warning(
            f"🔔 Assignment registrado: {position.symbol} strike=${position.call_option.strike}"
        )
