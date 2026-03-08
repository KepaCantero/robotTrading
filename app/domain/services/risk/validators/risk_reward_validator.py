"""
Risk:Reward Validator (R4)

Valida que la relación riesgo:retorno sea mínimo 2:1
Uses centralized configuration for minimum R:R ratio.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.shared.config.centralized_config import get_config


@dataclass
class RiskRewardResult:
    """Resultado de validación R:R"""

    rr_ratio: Decimal  # Relación R:R
    min_rr_ratio: Decimal  # R:R mínimo requerido
    potential_profit: Decimal
    potential_loss: Decimal
    passes: bool  # Si pasa (>= 2:1)


class RiskRewardValidator:
    """
    Validador de Risk:Reward (R4)

    Mínimo R:R = 2:1 (loaded from centralized config)
    """

    def __init__(self):
        """Initialize validator with config values."""
        config = get_config()
        self.MIN_RR_RATIO = Decimal(str(getattr(config.trading, 'min_rr_ratio', 2.0)))

    def validate(
        self, entry_price: Decimal, target_price: Decimal, stop_loss: Decimal
    ) -> RiskRewardResult:
        """
        Validar relación riesgo:retorno

        Args:
            entry_price: Precio de entrada
            target_price: Precio objetivo (take profit)
            stop_loss: Precio de stop loss

        Returns:
            RiskRewardResult con detalles
        """
        # Calcular potencial de ganancia y pérdida
        potential_profit = abs(target_price - entry_price)
        potential_loss = abs(entry_price - stop_loss)

        # Evitar división por cero
        if potential_loss == 0:
            return RiskRewardResult(
                rr_ratio=Decimal("0"),
                min_rr_ratio=self.MIN_RR_RATIO,
                potential_profit=potential_profit,
                potential_loss=potential_loss,
                passes=False,
            )

        # Calcular R:R
        rr_ratio = potential_profit / potential_loss

        # Validar
        passes = rr_ratio >= self.MIN_RR_RATIO

        return RiskRewardResult(
            rr_ratio=rr_ratio,
            min_rr_ratio=self.MIN_RR_RATIO,
            potential_profit=potential_profit,
            potential_loss=potential_loss,
            passes=passes,
        )

    def calculate_minimum_stop(self, entry_price: Decimal, target_price: Decimal) -> Decimal:
        """
        Calcular stop loss mínimo para cumplir R:R 2:1

        Args:
            entry_price: Precio de entrada
            target_price: Precio objetivo

        Returns:
            Stop loss mínimo aceptable
        """
        potential_profit = abs(target_price - entry_price)
        max_loss = potential_profit / self.MIN_RR_RATIO

        if target_price > entry_price:
            # Long
            return entry_price - max_loss
        else:
            # Short
            return entry_price + max_loss
