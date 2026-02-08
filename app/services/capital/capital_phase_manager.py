"""
Capital Phase Manager (R25, R26, R27)

This module manages dynamic risk adjustment based on capital phases.
As the account grows, risk parameters are automatically adjusted.

Rules:
- R25: Survival phase (€1k-€10k) - Conservative risk
- R26: Growth phase (€10k-€50k) - Moderate risk
- R27: Optimization phase (€50k+) - Aggressive risk with leverage
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.services.capital.phase_config import (
    PHASE_CONFIGS,
    PHASE_THRESHOLDS,
    CapitalPhase,
    PhaseRiskParameters,
)


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

    Ajusta parámetros de riesgo dinámicamente según
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
            ValueError: Si initial_capital < €1000
        """
        if initial_capital < Decimal("1000"):
            msg = "Initial capital must be at least €1,000"
            raise ValueError(msg)

        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._current_phase = self._determine_phase(initial_capital)
        self._phase_history: list[tuple[datetime, CapitalPhase]] = [
            (datetime.utcnow(), self._current_phase)
        ]
        self._phase_transitions: list[CapitalPhaseEvent] = []

    def update_capital(self, new_capital: Decimal) -> CapitalPhase:
        """
        Actualiza capital y determina si cambió de fase.

        Args:
            new_capital: Nuevo capital actual en EUR

        Returns:
            Nueva fase (puede ser igual que anterior)

        Raises:
            ValueError: Si new_capital < €1000
        """
        if new_capital < Decimal("1000"):
            msg = "Capital cannot fall below €1,000"
            raise ValueError(msg)

        old_phase = self._current_phase
        self._current_capital = new_capital
        new_phase = self._determine_phase(new_capital)

        # Si cambió de fase, registrar en historia
        if new_phase != old_phase:
            self._current_phase = new_phase
            self._phase_history.append((datetime.utcnow(), new_phase))

            # Registrar evento de transición
            event = CapitalPhaseEvent(
                timestamp=datetime.utcnow(),
                old_phase=old_phase,
                new_phase=new_phase,
                capital_at_transition=new_capital,
            )
            self._phase_transitions.append(event)

        return new_phase

    def get_current_phase(self) -> CapitalPhase:
        """
        Retorna fase actual.

        Returns:
            CapitalPhase actual
        """
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
        Retorna parámetros de riesgo para fase actual.

        Returns:
            PhaseRiskParameters con configuración actual

        Example:
            >>> manager = CapitalPhaseManager(Decimal("5000"))
            >>> params = manager.get_risk_parameters()
            >>> params.max_risk_per_trade_pct
            Decimal('0.01')
            >>> params.leverage_allowed
            False
        """
        return PHASE_CONFIGS[self._current_phase]

    def can_increase_position_size(
        self,
        current_risk_pct: Decimal,
        proposed_risk_pct: Decimal,
    ) -> tuple[bool, str]:
        """
        Valida si se puede incrementar tamaño de posición.

        Verifica que el riesgo propuesto no exceda los límites
        de la fase actual. Usa comparación estricta (>=) para
        rechazar valores que están exactamente en el límite.

        Args:
            current_risk_pct: Riesgo actual como % del capital
            proposed_risk_pct: Riesgo propuesto como %

        Returns:
            (puede_incrementar, razón)

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
        params = self.get_risk_parameters()

        # Verificar que no excede máximo por trade (>= para rechazar igual al límite)
        if proposed_risk_pct >= params.max_risk_per_trade_pct:
            return False, (
                f"Proposed risk {proposed_risk_pct:.1%} exceeds "
                f"max {params.max_risk_per_trade_pct:.1%} for {self._current_phase.value} phase"
            )

        # Verificar que no excede riesgo total de portfolio (>= para rechazar igual al límite)
        total_risk = current_risk_pct + proposed_risk_pct
        if total_risk >= params.max_portfolio_risk_pct:
            return False, (
                f"Total risk {total_risk:.1%} would exceed "
                f"max {params.max_portfolio_risk_pct:.1%} for {self._current_phase.value} phase"
            )

        return True, "OK"

    def get_phase_summary(self) -> dict:
        """
        Retorna resumen de fase actual.

        Returns:
            Diccionario con información de fase

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

        return {
            "current_phase": self._current_phase.value,
            "capital_range": f"€{min_capital:,.0f} - €{max_capital:,.0f}",
            "current_capital": f"€{self._current_capital:,.2f}",
            "max_risk_per_trade": f"{params.max_risk_per_trade_pct:.1%}",
            "max_portfolio_risk": f"{params.max_portfolio_risk_pct:.1%}",
            "max_positions": params.max_positions,
            "leverage_allowed": params.leverage_allowed,
            "position_sizing": params.position_sizing_method,
            "phase_duration_days": self._calculate_phase_duration(),
        }

    def get_phase_history(self) -> list[dict]:
        """
        Retorna historia de transiciones de fase.

        Returns:
            Lista de diccionarios con transiciones de fase
        """
        return [
            {
                "timestamp": event.timestamp.isoformat(),
                "old_phase": event.old_phase.value,
                "new_phase": event.new_phase.value,
                "capital_at_transition": f"€{event.capital_at_transition:,.2f}",
            }
            for event in self._phase_transitions
        ]

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
            # Ya estamos en la última fase
            return {
                "current_phase": current_phase.value,
                "next_phase": None,
                "progress_pct": 100.0,
                "remaining": Decimal("0"),
            }

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

        return {
            "current_phase": current_phase.value,
            "next_phase": next_phase.value,
            "progress_pct": min(progress_pct, 100.0),
            "remaining": max(remaining, Decimal("0")),
        }

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
            return CapitalPhase.SURVIVAL
        if capital < Decimal("50000"):
            return CapitalPhase.GROWTH
        return CapitalPhase.OPTIMIZATION

    def _calculate_phase_duration(self) -> int:
        """Calcula días en fase actual."""
        if len(self._phase_history) < 2:
            return 0

        # Encontrar cuándo empezó fase actual
        current_phase = self._current_phase
        for timestamp, phase in reversed(self._phase_history):
            if phase == current_phase:
                phase_start = timestamp
                break
        else:
            # No debería pasar, pero fallback
            phase_start = self._phase_history[0][0]

        duration = datetime.utcnow() - phase_start
        return duration.days
