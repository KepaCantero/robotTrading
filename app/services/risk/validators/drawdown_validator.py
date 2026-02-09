"""
Drawdown Validator (R2)

Valida que el drawdown no exceda 15% (kill switch)
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DrawdownResult:
    """Resultado de validación de drawdown"""
    current_drawdown: Decimal  # Drawdown actual (%)
    peak_equity: Decimal       # Equity máximo
    current_equity: Decimal    # Equity actual
    passes: bool               # Si pasa (< 15%)
    kill_switch_active: bool   # Si kill switch está activo


class DrawdownValidator:
    """
    Validador de Drawdown (R2)

    Si drawdown >= 15% → halt trading (kill switch)
    """

    MAX_DRAWDOWN_PCT = Decimal("0.15")  # 15% máximo

    def __init__(self):
        self._peak_equity: Optional[Decimal] = None
        self._current_equity: Optional[Decimal] = None
        self._kill_switch_active = False
        self._kill_switch_activated_at: Optional[datetime] = None

    def update_equity(self, current_equity: Decimal) -> None:
        """
        Actualizar equity y recalcular peak

        Args:
            current_equity: Equity actual
        """
        self._current_equity = current_equity
        if self._peak_equity is None or current_equity > self._peak_equity:
            self._peak_equity = current_equity

        # Si hay nuevo peak, resetear kill switch
        if current_equity >= self._peak_equity:
            self._kill_switch_active = False
            self._kill_switch_activated_at = None

    def validate(self, current_equity: Decimal) -> DrawdownResult:
        """
        Validar drawdown actual

        Args:
            current_equity: Equity actual

        Returns:
            DrawdownResult con estado de validación
        """
        self.update_equity(current_equity)

        if self._peak_equity is None or self._peak_equity == 0:
            current_drawdown = Decimal("0")
        else:
            current_drawdown = (self._peak_equity - current_equity) / self._peak_equity

        # Validar
        passes = current_drawdown < self.MAX_DRAWDOWN_PCT

        # Activar kill switch si excede
        if not passes and not self._kill_switch_active:
            self._kill_switch_active = True
            self._kill_switch_activated_at = datetime.utcnow()

        return DrawdownResult(
            current_drawdown=current_drawdown * 100,  # Como %
            peak_equity=self._peak_equity or Decimal("0"),
            current_equity=current_equity,
            passes=passes,
            kill_switch_active=self._kill_switch_active
        )

    def get_current_drawdown(self) -> Decimal:
        """
        Obtener drawdown actual

        Returns:
            Drawdown actual (%)
        """
        if self._peak_equity is None or self._peak_equity == 0:
            return Decimal("0")

        if self._current_equity is None:
            return Decimal("0")

        current_drawdown = (self._peak_equity - self._current_equity) / self._peak_equity
        return current_drawdown * 100  # Como porcentaje

    def activate_kill_switch(self, reason: str) -> None:
        """
        Activar kill switch manualmente

        Args:
            reason: Razón de activación
        """
        self._kill_switch_active = True
        self._kill_switch_activated_at = datetime.utcnow()

    def deactivate_kill_switch(self) -> bool:
        """
        Desactivar kill switch

        Returns:
            True si se desactivó correctamente
        """
        if not self._kill_switch_active:
            return False

        self._kill_switch_active = False
        self._kill_switch_activated_at = None
        return True

    def is_kill_switch_active(self) -> bool:
        """Verificar si kill switch está activo"""
        return self._kill_switch_active
