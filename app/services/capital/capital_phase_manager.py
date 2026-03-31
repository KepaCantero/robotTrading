"""
Capital Phase Manager (R25, R26, R27)

This module manages dynamic risk adjustment based on capital phases.
As the account grows, risk parameters are automatically adjusted.

Rules:
- R25: Survival phase (1k-10k EUR) - Conservative risk
- R26: Growth phase (10k-50k EUR) - Moderate risk
- R27: Optimization phase (50k+ EUR) - Aggressive risk with leverage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.capital.phase_config import (
    PHASE_CONFIGS,
    PHASE_THRESHOLDS,
    CapitalPhase,
    PhaseRiskParameters,
)

logger = logging.getLogger(__name__)


@dataclass
class CapitalPhaseEvent:
    """Evento de cambio de fase."""

    timestamp: datetime
    old_phase: CapitalPhase
    new_phase: CapitalPhase
    capital_at_transition: Decimal


class CapitalPhaseManager:
    """
    Gestiona fases de capital (R25, R26, R27).

    Ajusta parametros de riesgo dinamicamente segun
    el nivel de capital actual. Implementa reglas de trading realistas
    para traders minoristas.

    Example:
        >>> manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        >>> manager.get_current_phase()
        <CapitalPhase.SURVIVAL: 'survival'>
        >>> params = manager.get_risk_parameters()
        >>> params.max_risk_per_trade_pct
        Decimal('0.01')
        >>> manager.update_capital(Decimal("15000"))
        <CapitalPhase.GROWTH: 'growth'>
    """

    def __init__(self, initial_capital: Decimal) -> None:
        """
        Initialize the capital phase manager.

        Args:
            initial_capital: Capital inicial en EUR

        Raises:
            ValueError: Si initial_capital < 1000 EUR
        """
        logger.debug(
            "Initializing CapitalPhaseManager",
            extra={"initial_capital": str(initial_capital)},
        )

        if initial_capital < Decimal("1000"):
            logger.error(
                "CapitalPhaseManager initialization failed: capital below minimum",
                extra={"initial_capital": str(initial_capital), "minimum_required": "1000"},
            )
            raise ValueError("Initial capital must be at least 1,000 EUR")

        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._current_phase = self._determine_phase(initial_capital)
        self._phase_history: list[tuple[datetime, CapitalPhase]] = [
            (datetime.utcnow(), self._current_phase)
        ]
        self._phase_transitions: list[CapitalPhaseEvent] = []

        logger.info(
            "CapitalPhaseManager initialized",
            extra={
                "initial_capital": str(initial_capital),
                "initial_phase": self._current_phase.value,
            },
        )

    def update_capital(self, new_capital: Decimal) -> CapitalPhase:
        """
        Actualiza capital y determina si cambio de fase.

        Args:
            new_capital: Nuevo capital actual en EUR

        Returns:
            Nueva fase (puede ser igual que anterior)

        Raises:
            ValueError: Si new_capital < 1000 EUR
        """
        logger.debug(
            "Updating capital",
            extra={
                "current_capital": str(self._current_capital),
                "new_capital": str(new_capital),
            },
        )

        if new_capital < Decimal("1000"):
            logger.error(
                "Capital update failed: capital below minimum",
                extra={"new_capital": str(new_capital), "minimum_required": "1000"},
            )
            raise ValueError("Capital cannot fall below 1,000 EUR")

        old_phase = self._current_phase
        self._current_capital = new_capital
        new_phase = self._determine_phase(new_capital)

        # Si cambio de fase, registrar en historia
        if new_phase != old_phase:
            self._current_phase = new_phase
            self._phase_history.append((datetime.utcnow(), new_phase))

            # Registrar evento de transicion
            event = CapitalPhaseEvent(
                timestamp=datetime.utcnow(),
                old_phase=old_phase,
                new_phase=new_phase,
                capital_at_transition=new_capital,
            )
            self._phase_transitions.append(event)

            logger.info(
                "Capital phase transition",
                extra={
                    "old_phase": old_phase.value,
                    "new_phase": new_phase.value,
                    "capital_at_transition": str(new_capital),
                },
            )
        else:
            logger.debug(
                "Capital updated, phase unchanged",
                extra={
                    "current_phase": self._current_phase.value,
                    "new_capital": str(new_capital),
                },
            )

        return new_phase

    def get_current_phase(self) -> CapitalPhase:
        """
        Retorna fase actual.

        Returns:
            CapitalPhase actual
        """
        logger.debug(
            "Getting current phase",
            extra={"current_phase": self._current_phase.value},
        )
        return self._current_phase

    def get_current_capital(self) -> Decimal:
        """
        Retorna capital actual.

        Returns:
            Capital actual en EUR
        """
        return self._current_capital

    def get_risk_parameters(self) -> PhaseRiskParameters:
        """
        Retorna parametros de riesgo para fase actual.

        Returns:
            PhaseRiskParameters con configuracion actual

        Example:
            >>> manager = CapitalPhaseManager(Decimal("5000"))
            >>> params = manager.get_risk_parameters()
            >>> params.max_risk_per_trade_pct
            Decimal('0.01')
            >>> params.leverage_allowed
            False
        """
        params = PHASE_CONFIGS[self._current_phase]
        logger.debug(
            "Retrieved risk parameters",
            extra={
                "current_phase": self._current_phase.value,
                "max_risk_per_trade_pct": str(params.max_risk_per_trade_pct),
                "max_portfolio_risk_pct": str(params.max_portfolio_risk_pct),
                "leverage_allowed": params.leverage_allowed,
            },
        )
        return params

    def can_increase_position_size(
        self,
        current_risk_pct: Decimal,
        proposed_risk_pct: Decimal,
    ) -> tuple[bool, str]:
        """
        Valida si se puede incrementar tamano de posicion.

        Verifica que el riesgo propuesto no exceda los limites
        de la fase actual. Usa comparacion estricta (>=) para
        rechazar valores que estan exactamente en el limite.

        Args:
            current_risk_pct: Riesgo actual como % del capital
            proposed_risk_pct: Riesgo propuesto como %

        Returns:
            (puede_incrementar, razon)

        Example:
            >>> manager = CapitalPhaseManager(Decimal("5000"))
            >>> can, reason = manager.can_increase_position_size(
            ...     Decimal("0.02"), Decimal("0.01")
            ... )
            >>> can
            False
            >>> 'would exceed' in reason
            True
        """
        logger.debug(
            "Checking position size increase",
            extra={
                "current_risk_pct": str(current_risk_pct),
                "proposed_risk_pct": str(proposed_risk_pct),
            },
        )

        params = self.get_risk_parameters()

        # Verificar que no excede maximo por trade (>= para rechazar igual al limite)
        if proposed_risk_pct >= params.max_risk_per_trade_pct:
            reason = (
                f"Proposed risk {proposed_risk_pct:.1%} exceeds "
                f"max {params.max_risk_per_trade_pct:.1%} for {self._current_phase.value} phase"
            )
            logger.warning(
                "Position size increase rejected: exceeds max risk per trade",
                extra={
                    "proposed_risk_pct": str(proposed_risk_pct),
                    "max_allowed": str(params.max_risk_per_trade_pct),
                    "current_phase": self._current_phase.value,
                    "reason": reason,
                },
            )
            return False, reason

        # Verificar que no excede riesgo total de portfolio (>= para rechazar igual al limite)
        total_risk = current_risk_pct + proposed_risk_pct
        if total_risk >= params.max_portfolio_risk_pct:
            reason = (
                f"Total risk {total_risk:.1%} would exceed "
                f"max {params.max_portfolio_risk_pct:.1%} for {self._current_phase.value} phase"
            )
            logger.warning(
                "Position size increase rejected: exceeds max portfolio risk",
                extra={
                    "total_risk_pct": str(total_risk),
                    "max_allowed": str(params.max_portfolio_risk_pct),
                    "current_phase": self._current_phase.value,
                    "reason": reason,
                },
            )
            return False, reason

        logger.debug(
            "Position size increase approved",
            extra={
                "proposed_risk_pct": str(proposed_risk_pct),
                "total_risk_pct": str(total_risk),
            },
        )
        return True, "OK"

    def get_phase_summary(self) -> dict:
        """
        Retorna resumen de fase actual.

        Returns:
            Diccionario con informacion de fase

        Example:
            >>> manager = CapitalPhaseManager(Decimal("5000"))
            >>> summary = manager.get_phase_summary()
            >>> summary['current_phase']
            'survival'
            >>> summary['max_risk_per_trade']
            '1.0%'
        """
        params = self.get_risk_parameters()
        min_capital, max_capital = PHASE_THRESHOLDS[self._current_phase]

        summary = {
            "current_phase": self._current_phase.value,
            "capital_range": f"{min_capital:,.0f} - {max_capital:,.0f} EUR",
            "current_capital": f"{self._current_capital:,.2f} EUR",
            "max_risk_per_trade": f"{params.max_risk_per_trade_pct:.1%}",
            "max_portfolio_risk": f"{params.max_portfolio_risk_pct:.1%}",
            "max_positions": params.max_positions,
            "leverage_allowed": params.leverage_allowed,
            "position_sizing": params.position_sizing_method,
            "phase_duration_days": self._calculate_phase_duration(),
        }

        logger.debug(
            "Generated phase summary",
            extra={"summary": summary},
        )
        return summary

    def get_phase_history(self) -> list[dict]:
        """
        Retorna historia de transiciones de fase.

        Returns:
            Lista de diccionarios con transiciones de fase
        """
        history = [
            {
                "timestamp": event.timestamp.isoformat(),
                "old_phase": event.old_phase.value,
                "new_phase": event.new_phase.value,
                "capital_at_transition": f"{event.capital_at_transition:,.2f} EUR",
            }
            for event in self._phase_transitions
        ]

        logger.debug(
            "Retrieved phase history",
            extra={"num_transitions": len(history)},
        )
        return history

    def get_capital_progress(self) -> dict:
        """
        Retorna progreso de capital hacia siguiente fase.

        Returns:
            Diccionario con progreso hacia siguiente fase

        Example:
            >>> manager = CapitalPhaseManager(Decimal("7500"))
            >>> progress = manager.get_capital_progress()
            >>> progress['current_phase']
            'survival'
            >>> progress['next_phase']
            'growth'
        """
        current_phase = self._current_phase
        current_capital = self._current_capital

        if current_phase == CapitalPhase.OPTIMIZATION:
            # Ya estamos en la ultima fase
            progress = {
                "current_phase": current_phase.value,
                "next_phase": None,
                "progress_pct": 100.0,
                "remaining": Decimal("0"),
            }
            logger.debug(
                "Capital progress: at final phase",
                extra=progress,
            )
            return progress

        # Calcular progreso hacia siguiente fase
        min_capital, max_capital = PHASE_THRESHOLDS[current_phase]

        # Determinar siguiente fase
        if current_phase == CapitalPhase.SURVIVAL:
            next_phase = CapitalPhase.GROWTH
        else:  # GROWTH
            next_phase = CapitalPhase.OPTIMIZATION

        # Calcular progreso
        phase_range = max_capital - min_capital
        progress = current_capital - min_capital
        remaining = max_capital - current_capital
        progress_pct = float((progress / phase_range) * 100) if phase_range > 0 else 100.0

        result = {
            "current_phase": current_phase.value,
            "next_phase": next_phase.value,
            "progress_pct": min(progress_pct, 100.0),
            "remaining": max(remaining, Decimal("0")),
        }

        logger.debug(
            "Capital progress calculated",
            extra=result,
        )
        return result

    def _determine_phase(self, capital: Decimal) -> CapitalPhase:
        """
        Determina fase basado en capital.

        Args:
            capital: Capital actual

        Returns:
            CapitalPhase correspondiente

        Example:
            >>> manager = CapitalPhaseManager(Decimal("5000"))
            >>> manager._determine_phase(Decimal("5000"))
            <CapitalPhase.SURVIVAL: 'survival'>
            >>> manager._determine_phase(Decimal("15000"))
            <CapitalPhase.GROWTH: 'growth'>
            >>> manager._determine_phase(Decimal("75000"))
            <CapitalPhase.OPTIMIZATION: 'optimization'>
        """
        if capital < Decimal("10000"):
            phase = CapitalPhase.SURVIVAL
        elif capital < Decimal("50000"):
            phase = CapitalPhase.GROWTH
        else:
            phase = CapitalPhase.OPTIMIZATION

        logger.debug(
            "Determined phase from capital",
            extra={"capital": str(capital), "phase": phase.value},
        )
        return phase

    def _calculate_phase_duration(self) -> int:
        """Calcula dias en fase actual."""
        if len(self._phase_history) < 2:
            return 0

        # Encontrar cuando empezo fase actual
        current_phase = self._current_phase
        for timestamp, phase in reversed(self._phase_history):
            if phase == current_phase:
                phase_start = timestamp
                break
        else:
            # No deberia pasar, pero fallback
            phase_start = self._phase_history[0][0]

        duration = datetime.utcnow() - phase_start
        duration_days = duration.days

        logger.debug(
            "Calculated phase duration",
            extra={
                "current_phase": current_phase.value,
                "duration_days": duration_days,
            },
        )
        return duration_days
