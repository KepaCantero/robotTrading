"""
Kelly Criterion Validator (R1)

Valida que el tamaño de la posición no exceda:
- Kelly Criterion calculado
- 2% máximo del capital
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class KellyResult:
    """Resultado del cálculo de Kelly"""

    kelly_fraction: Decimal  # Fracción de Kelly (0-1)
    max_position: Decimal  # Tamaño máximo de posición
    passes_kelly: bool  # Si pasa el criterio Kelly
    passes_2pct: bool  # Si pasa el límite del 2%
    passes: bool  # Si pasa TODAS las validaciones


class KellyCriterionValidator:
    """
    Validador de Kelly Criterion (R1)

    Kelly Criterion = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

    Máximo riesgo: 2% del capital
    """

    MAX_RISK_PCT = 0.02  # 2% máximo

    def __init__(
        self,
        win_rate: float = 0.55,
        avg_win: float = 0.03,
        avg_loss: float = 0.02,
    ):
        """
        Inicializar validador con parámetros históricos

        Args:
            win_rate: Tasa de victorias (0-1)
            avg_win: Ganancia promedio (% como decimal)
            avg_loss: Pérdida promedio (% como decimal)
        """
        self.win_rate = Decimal(str(win_rate))
        self.avg_win = Decimal(str(avg_win))
        self.avg_loss = Decimal(str(avg_loss))

    def calculate_kelly_fraction(self) -> Decimal:
        """
        Calcular fracción de Kelly

        Formula:
        kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        Returns:
            Fracción de Kelly (0-1)
        """
        loss_rate = Decimal("1") - self.win_rate

        numerator = (self.win_rate * self.avg_win) - (loss_rate * self.avg_loss)
        kelly = numerator / self.avg_win

        # Kelly no puede ser negativo
        return max(kelly, Decimal("0"))

    def validate(self, capital: Decimal, order_value: Decimal) -> KellyResult:
        """
        Validar posición según Kelly Criterion + 2%

        Args:
            capital: Capital total disponible
            order_value: Valor de la orden

        Returns:
            KellyResult con detalles de validación
        """
        kelly_fraction = self.calculate_kelly_fraction()

        # Limitar Kelly al 50% (fracción de Kelly)
        kelly_half = kelly_fraction * Decimal("0.5")

        # Calcular tamaños máximos
        max_by_kelly = capital * kelly_half
        max_by_2pct = capital * self.MAX_RISK_PCT

        # Usar el MÁS conservador
        max_position = min(max_by_kelly, max_by_2pct)

        # Validar
        passes_kelly = order_value <= max_by_kelly
        passes_2pct = order_value <= max_by_2pct
        passes = order_value <= max_position

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
        Actualizar parámetros con nuevos datos históricos

        Args:
            win_rate: Nueva tasa de victorias
            avg_win: Nueva ganancia promedio
            avg_loss: Nueva pérdida promedio
        """
        if win_rate is not None:
            self.win_rate = Decimal(str(win_rate))
        if avg_win is not None:
            self.avg_win = Decimal(str(avg_win))
        if avg_loss is not None:
            self.avg_loss = Decimal(str(avg_loss))
