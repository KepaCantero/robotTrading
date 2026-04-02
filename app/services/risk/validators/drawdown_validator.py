"""
Drawdown Validator (R2)

Valida que el drawdown no exceda 15% (kill switch)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class DrawdownResult:
    """Resultado de validacion de drawdown"""

    current_drawdown: Decimal  # Drawdown actual (%)
    peak_equity: Decimal  # Equity maximo
    current_equity: Decimal  # Equity actual
    passes: bool  # Si pasa (< 15%)
    kill_switch_active: bool  # Si kill switch esta activo


class DrawdownValidator:
    """
    Validador de Drawdown (R2)

    Si drawdown >= 15% -> halt trading (kill switch)
    """

    MAX_DRAWDOWN_PCT = Decimal("0.15")  # 15% maximo

    def __init__(self):
        self._peak_equity: Decimal | None = None
        self._current_equity: Decimal | None = None
        self._kill_switch_active = False
        self._kill_switch_activated_at: datetime | None = None

        logger.info(
            "DrawdownValidator initialized",
            extra={
                "component": "drawdown_validator",
                "operation": "init",
                "max_drawdown_pct": str(self.MAX_DRAWDOWN_PCT),
            },
        )

    def update_equity(self, current_equity: Decimal) -> None:
        """
        Actualizar equity y recalcular peak

        Args:
            current_equity: Equity actual
        """
        self._current_equity = current_equity
        old_peak = self._peak_equity

        if self._peak_equity is None or current_equity > self._peak_equity:
            self._peak_equity = current_equity

            logger.debug(
                "New peak equity recorded",
                extra={
                    "component": "drawdown_validator",
                    "operation": "update_equity",
                    "current_equity": str(current_equity),
                    "old_peak": str(old_peak) if old_peak else None,
                    "new_peak": str(self._peak_equity),
                },
            )

        # Si hay nuevo peak, resetear kill switch
        if current_equity >= self._peak_equity:
            if self._kill_switch_active:
                logger.info(
                    "Kill switch reset due to new equity peak",
                    extra={
                        "component": "drawdown_validator",
                        "operation": "update_equity",
                        "peak_equity": str(self._peak_equity),
                    },
                )
            self._kill_switch_active = False
            self._kill_switch_activated_at = None

    def validate(self, current_equity: Decimal) -> DrawdownResult:
        """
        Validar drawdown actual

        Args:
            current_equity: Equity actual

        Returns:
            DrawdownResult con estado de validacion
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

            logger.warning(
                "KILL SWITCH ACTIVATED - Drawdown exceeded threshold",
                extra={
                    "component": "drawdown_validator",
                    "operation": "validate",
                    "current_drawdown_pct": str(current_drawdown * 100),
                    "max_drawdown_pct": str(self.MAX_DRAWDOWN_PCT * 100),
                    "peak_equity": str(self._peak_equity),
                    "current_equity": str(current_equity),
                    "kill_switch_activated_at": (
                        self._kill_switch_activated_at.isoformat()
                        if self._kill_switch_activated_at
                        else None
                    ),
                },
            )

        logger.debug(
            "Drawdown validation completed",
            extra={
                "component": "drawdown_validator",
                "operation": "validate",
                "current_drawdown_pct": str(current_drawdown * 100),
                "passes": passes,
                "kill_switch_active": self._kill_switch_active,
            },
        )

        return DrawdownResult(
            current_drawdown=current_drawdown * 100,  # Como %
            peak_equity=self._peak_equity or Decimal("0"),
            current_equity=current_equity,
            passes=passes,
            kill_switch_active=self._kill_switch_active,
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
            reason: Razon de activacion
        """
        self._kill_switch_active = True
        self._kill_switch_activated_at = datetime.utcnow()

        logger.warning(
            "Kill switch manually activated",
            extra={
                "component": "drawdown_validator",
                "operation": "activate_kill_switch",
                "reason": reason,
                "activated_at": (
                    self._kill_switch_activated_at.isoformat()
                    if self._kill_switch_activated_at
                    else None
                ),
            },
        )

    def deactivate_kill_switch(self) -> bool:
        """
        Desactivar kill switch

        Returns:
            True si se desactivo correctamente
        """
        if not self._kill_switch_active:
            logger.debug(
                "Kill switch deactivation skipped - not active",
                extra={
                    "component": "drawdown_validator",
                    "operation": "deactivate_kill_switch",
                },
            )
            return False

        self._kill_switch_active = False
        self._kill_switch_activated_at = None

        logger.info(
            "Kill switch deactivated",
            extra={
                "component": "drawdown_validator",
                "operation": "deactivate_kill_switch",
            },
        )

        return True

    def is_kill_switch_active(self) -> bool:
        """Verificar si kill switch esta activo"""
        return self._kill_switch_active
