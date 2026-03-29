"""
Risk Parameters Value Object - Risk management constraints

Risk parameters define the risk limits and constraints for
portfolio and position management.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskParameters:
    """
    Risk parameters value object.

    Defines risk management constraints including position sizing,
    stop loss, take profit, and portfolio-level limits.
    """

    max_position_size: Decimal
    max_portfolio_exposure: Decimal
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    risk_reward_ratio: Decimal = Decimal("2")
    max_daily_loss_pct: Decimal = Decimal("0.05")
    max_drawdown_pct: Decimal = Decimal("0.15")

    def __post_init__(self):
        """Validate risk parameter invariants."""
        if self.max_position_size <= 0:
            raise ValueError("Max position size must be positive")
        if self.max_portfolio_exposure <= 0:
            raise ValueError("Max portfolio exposure must be positive")
        if self.stop_loss_pct <= 0 or self.stop_loss_pct > 1:
            raise ValueError("Stop loss must be between 0 and 1")
        if self.take_profit_pct <= 0:
            raise ValueError("Take profit must be positive")
        if self.risk_reward_ratio <= 0:
            raise ValueError("Risk/reward ratio must be positive")
        if self.max_daily_loss_pct < 0 or self.max_daily_loss_pct > 1:
            raise ValueError("Max daily loss must be between 0 and 1")
        if self.max_drawdown_pct < 0 or self.max_drawdown_pct > 1:
            raise ValueError("Max drawdown must be between 0 and 1")

    def get_stop_loss_price(self, entry_price: Decimal, side: str = "long") -> Decimal:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            side: Position side ('long' or 'short')

        Returns:
            Stop loss price
        """
        if side == "long":
            return entry_price * (1 - self.stop_loss_pct)
        else:
            return entry_price * (1 + self.stop_loss_pct)

    def get_take_profit_price(self, entry_price: Decimal, side: str = "long") -> Decimal:
        """
        Calculate take profit price.

        Args:
            entry_price: Entry price
            side: Position side ('long' or 'short')

        Returns:
            Take profit price
        """
        if side == "long":
            return entry_price * (1 + self.take_profit_pct)
        else:
            return entry_price * (1 - self.take_profit_pct)

    def validate_risk_reward(
        self, entry_price: Decimal, target_price: Decimal, stop_price: Decimal, side: str = "long"
    ) -> bool:
        """
        Validate if trade meets minimum risk/reward ratio.

        Args:
            entry_price: Entry price
            target_price: Target price
            stop_price: Stop loss price
            side: Position side

        Returns:
            True if risk/reward ratio meets minimum
        """
        if side == "long":
            potential_profit = abs(target_price - entry_price)
            potential_loss = abs(entry_price - stop_price)
        else:
            potential_profit = abs(entry_price - target_price)
            potential_loss = abs(stop_price - entry_price)

        if potential_loss == 0:
            return False

        actual_ratio = potential_profit / potential_loss
        return actual_ratio >= self.risk_reward_ratio

    @classmethod
    def for_tier(cls, tier: str) -> RiskParameters:
        """
        Create risk parameters for a capital tier.

        Args:
            tier: Capital tier (micro, small, medium, large, institutional)

        Returns:
            RiskParameters instance with tier-appropriate values
        """
        # Tier-specific risk parameters
        if tier == "micro":
            return cls(
                max_position_size=Decimal("0.20"),  # 20% max per position
                max_portfolio_exposure=Decimal("1.0"),  # 100% max exposure
                stop_loss_pct=Decimal("0.05"),  # 5% stop loss
                take_profit_pct=Decimal("0.10"),  # 10% take profit
            )
        elif tier == "small":
            return cls(
                max_position_size=Decimal("0.15"),
                max_portfolio_exposure=Decimal("1.2"),
                stop_loss_pct=Decimal("0.04"),
                take_profit_pct=Decimal("0.08"),
            )
        elif tier == "medium":
            return cls(
                max_position_size=Decimal("0.10"),
                max_portfolio_exposure=Decimal("1.5"),
                stop_loss_pct=Decimal("0.03"),
                take_profit_pct=Decimal("0.06"),
            )
        elif tier == "large":
            return cls(
                max_position_size=Decimal("0.08"),
                max_portfolio_exposure=Decimal("1.8"),
                stop_loss_pct=Decimal("0.02"),  # 2% stop loss for large tier
                take_profit_pct=Decimal("0.05"),
            )
        else:  # institutional
            return cls(
                max_position_size=Decimal("0.05"),
                max_portfolio_exposure=Decimal("2.0"),
                stop_loss_pct=Decimal("0.02"),  # 2% stop loss for institutional
                take_profit_pct=Decimal("0.04"),
            )
