"""
Kelly Criterion Validator (R1)

Valida que el tamano de la posicion no exceda:
- Kelly Criterion calculado
- 2% maximo del capital
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class KellyResult:
    """Resultado del calculo de Kelly"""

    kelly_fraction: Decimal  # Fraccion de Kelly (0-1)
    max_position: Decimal  # Tamano maximo de posicion
    passes_kelly: bool  # Si pasa el criterio Kelly
    passes_2pct: bool  # Si pasa el limite del 2%
    passes: bool  # Si pasa TODAS las validaciones


class KellyCriterionValidator:
    """
    Validador de Kelly Criterion (R1)

    Kelly Criterion = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

    Maximo riesgo: 2% del capital
    """

    MAX_RISK_PCT = 0.02  # 2% maximo

    def __init__(
        self,
        win_rate: float = 0.55,
        avg_win: float = 0.03,
        avg_loss: float = 0.02,
    ):
        """
        Inicializar validador con parametros historicos

        Args:
            win_rate: Tasa de victorias (0-1)
            avg_win: Ganancia promedio (% como decimal)
            avg_loss: Perdida promedio (% como decimal)
        """
        self.win_rate = Decimal(str(win_rate))
        self.avg_win = Decimal(str(avg_win))
        self.avg_loss = Decimal(str(avg_loss))

        logger.info(
            "KellyCriterionValidator initialized",
            extra={
                "component": "kelly_criterion_validator",
                "operation": "init",
                "win_rate": str(self.win_rate),
                "avg_win": str(self.avg_win),
                "avg_loss": str(self.avg_loss),
                "max_risk_pct": self.MAX_RISK_PCT,
            },
        )

    def calculate_kelly_fraction(self) -> Decimal:
        """
        Calcular fraccion de Kelly

        Formula:
        kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        Returns:
            Fraccion de Kelly (0-1)
        """
        loss_rate = Decimal("1") - self.win_rate

        numerator = (self.win_rate * self.avg_win) - (loss_rate * self.avg_loss)
        kelly = numerator / self.avg_win

        # Kelly no puede ser negativo
        kelly_fraction = max(kelly, Decimal("0"))

        logger.debug(
            "Kelly fraction calculated",
            extra={
                "component": "kelly_criterion_validator",
                "operation": "calculate_kelly_fraction",
                "win_rate": str(self.win_rate),
                "loss_rate": str(loss_rate),
                "numerator": str(numerator),
                "kelly_fraction": str(kelly_fraction),
            },
        )

        return kelly_fraction

    def validate(self, capital: Decimal, order_value: Decimal) -> KellyResult:
        """
        Validar posicion segun Kelly Criterion + 2%

        Args:
            capital: Capital total disponible
            order_value: Valor de la orden

        Returns:
            KellyResult con detalles de validacion
        """
        kelly_fraction = self.calculate_kelly_fraction()

        # Limitar Kelly al 50% (fraccion de Kelly)
        kelly_half = kelly_fraction * Decimal("0.5")

        # Calcular tamanos maximos
        max_by_kelly = capital * kelly_half
        max_by_2pct = capital * Decimal(str(self.MAX_RISK_PCT))

        # Usar el MAS conservador
        max_position = min(max_by_kelly, max_by_2pct)

        # Validar
        passes_kelly = order_value <= max_by_kelly
        passes_2pct = order_value <= max_by_2pct
        passes = order_value <= max_position

        logger.info(
            "Position validation completed",
            extra={
                "component": "kelly_criterion_validator",
                "operation": "validate",
                "capital": str(capital),
                "order_value": str(order_value),
                "kelly_fraction": str(kelly_fraction),
                "kelly_half": str(kelly_half),
                "max_by_kelly": str(max_by_kelly),
                "max_by_2pct": str(max_by_2pct),
                "max_position": str(max_position),
                "passes_kelly": passes_kelly,
                "passes_2pct": passes_2pct,
                "passes": passes,
            },
        )

        if not passes:
            logger.warning(
                "Position validation FAILED - exceeds allowed size",
                extra={
                    "component": "kelly_criterion_validator",
                    "operation": "validate",
                    "order_value": str(order_value),
                    "max_allowed": str(max_position),
                    "excess_amount": str(order_value - max_position),
                },
            )

        return KellyResult(
            kelly_fraction=kelly_fraction,
            max_position=max_position,
            passes_kelly=passes_kelly,
            passes_2pct=passes_2pct,
            passes=passes,
        )

    def update_parameters(
        self,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
    ) -> None:
        """
        Actualizar parametros con nuevos datos historicos

        Args:
            win_rate: Nueva tasa de victorias
            avg_win: Nueva ganancia promedio
            avg_loss: Nueva perdida promedio
        """
        old_win_rate = self.win_rate
        old_avg_win = self.avg_win
        old_avg_loss = self.avg_loss

        if win_rate is not None:
            self.win_rate = Decimal(str(win_rate))
        if avg_win is not None:
            self.avg_win = Decimal(str(avg_win))
        if avg_loss is not None:
            self.avg_loss = Decimal(str(avg_loss))

        logger.info(
            "Kelly parameters updated",
            extra={
                "component": "kelly_criterion_validator",
                "operation": "update_parameters",
                "old_win_rate": str(old_win_rate),
                "new_win_rate": str(self.win_rate),
                "old_avg_win": str(old_avg_win),
                "new_avg_win": str(self.avg_win),
                "old_avg_loss": str(old_avg_loss),
                "new_avg_loss": str(self.avg_loss),
            },
        )
