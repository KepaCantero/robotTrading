"""
Risk Configurator - Maps risk tolerance to concrete risk limits.

This module implements the RiskConfigurator class which is responsible
for translating a user's risk tolerance level into concrete risk parameters.

CRITICAL REQUIREMENT: Brecha #2 - NO hay routing InputProfile → Risk Config

The system MUST automatically configure risk limits based on risk_tolerance:

| risk_tolerance | Drawdown Limit | Position Limit | Leverage |
|---------------|---------------|----------------|----------|
| BAJO          | < 15%         | 5% max         | No       |
| MEDIO         | < 25%         | 10% max        | Yes (1.5x) |
| ALTO          | < 40%         | 20% max        | Yes (2.0x) |

Reference: AUDIT_PLAN_COMPLETO.md Section 4.2
Reference: rules/trading/papers/13-john-hull-risk-management.md
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.core.models.input_profile import RiskTolerance
from app.domain.configurators.risk_config import RiskConfig

logger = logging.getLogger(__name__)


class RiskConfigurator:
    """
    Configure risk parameters based on risk tolerance.

    This class implements the Single Responsibility Principle (SRP)
    by having only one job: mapping risk tolerance to risk configuration.

    It follows the Open/Closed Principle (OCP) by being open for extension
    (new risk levels can be added) but closed for modification.

    Usage:
        configurator = RiskConfigurator()
        config = configurator.configure(RiskTolerance.MEDIO)
        logger.debug(config.max_drawdown)  # Decimal('0.25')
    """

    def configure(self, tolerance: RiskTolerance) -> RiskConfig:
        """
        Select risk parameters from risk tolerance.

        This method implements the risk tolerance mapping as specified in
        AUDIT_PLAN_COMPLETO.md Section 4.2.

        Args:
            tolerance: User's risk tolerance level (BAJO, MEDIO, or ALTO)

        Returns:
            RiskConfig with concrete risk parameters

        Raises:
            ValueError: If risk tolerance is not recognized
        """
        if tolerance == RiskTolerance.BAJO:
            logger.debug("Configuring risk parameters for BAJO (low) tolerance")
            return RiskConfig(
                max_drawdown=Decimal("0.15"),  # 15% max drawdown
                max_daily_loss=Decimal("0.05"),  # 5% daily circuit breaker
                max_position_size=Decimal("0.05"),  # 5% per position
                portfolio_var_limit= getattr(config.trading, 'max_risk_per_trade', 0.02)"),  # 2% VaR limit
                leverage_allowed=False,
                max_leverage=Decimal("1.0"),
                stop_loss_atr_multiplier=Decimal("2.0"),
                trailing_stop_atr_multiplier=Decimal("3.0"),
            )
        elif tolerance == RiskTolerance.MEDIO:
            logger.debug("Configuring risk parameters for MEDIO (medium) tolerance")
            return RiskConfig(
                max_drawdown=Decimal("0.25"),  # 25% max drawdown
                max_daily_loss=Decimal("0.08"),  # 8% daily circuit breaker
                max_position_size=Decimal("0.10"),  # 10% per position
                portfolio_var_limit=Decimal("0.03"),  # 3% VaR limit
                leverage_allowed=True,
                max_leverage=Decimal("1.5"),  # 1.5x leverage
                stop_loss_atr_multiplier=Decimal("2.5"),
                trailing_stop_atr_multiplier=Decimal("3.5"),
            )
        elif tolerance == RiskTolerance.ALTO:
            logger.debug("Configuring risk parameters for ALTO (high) tolerance")
            return RiskConfig(
                max_drawdown=Decimal("0.40"),  # 40% max drawdown
                max_daily_loss=Decimal("0.12"),  # 12% daily circuit breaker
                max_position_size=Decimal("0.20"),  # 20% per position
                portfolio_var_limit=Decimal("0.05"),  # 5% VaR limit
                leverage_allowed=True,
                max_leverage=Decimal("2.0"),  # 2.0x leverage
                stop_loss_atr_multiplier=Decimal("3.0"),
                trailing_stop_atr_multiplier=Decimal("4.0"),
            )
        else:
            error_msg = f"Unrecognized risk tolerance: {tolerance}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def configure_for_profile(self, risk_tolerance: str | RiskTolerance) -> RiskConfig:
        """
        Configure risk from a string or enum risk tolerance.

        Convenience method that accepts both string and enum types.

        Args:
            risk_tolerance: Risk tolerance as string or RiskTolerance enum

        Returns:
            RiskConfig with concrete risk parameters

        Raises:
            ValueError: If risk tolerance string is not recognized
        """
        if isinstance(risk_tolerance, str):
            try:
                tolerance_enum = RiskTolerance(risk_tolerance.lower())
            except ValueError as e:
                valid_values = [t.value for t in RiskTolerance]
                raise ValueError(
                    f"Invalid risk_tolerance: {risk_tolerance}. "
                    f"Must be one of: {', '.join(valid_values)}"
                ) from e
        else:
            tolerance_enum = risk_tolerance

        return self.configure(tolerance_enum)

    def get_all_configs(self) -> dict[RiskTolerance, RiskConfig]:
        """
        Get all available risk configurations.

        Useful for UI display or configuration validation.

        Returns:
            Dictionary mapping risk tolerance levels to their configurations
        """
        return {
            RiskTolerance.BAJO: self.configure(RiskTolerance.BAJO),
            RiskTolerance.MEDIO: self.configure(RiskTolerance.MEDIO),
            RiskTolerance.ALTO: self.configure(RiskTolerance.ALTO),
        }

    def compare_configs(
        self, tolerance1: RiskTolerance, tolerance2: RiskTolerance
    ) -> dict[str, dict[str, Decimal | bool | str]]:
        """
        Compare risk configurations between two tolerance levels.

        Useful for demonstrating the impact of changing risk tolerance.

        Args:
            tolerance1: First risk tolerance level
            tolerance2: Second risk tolerance level

        Returns:
            Dictionary with parameter comparisons
        """
        config1 = self.configure(tolerance1)
        config2 = self.configure(tolerance2)

        return {
            "tolerance1": {
                "level": tolerance1.value,
                "max_drawdown": config1.max_drawdown,
                "max_position_size": config1.max_position_size,
                "leverage_allowed": config1.leverage_allowed,
                "max_leverage": config1.max_leverage,
            },
            "tolerance2": {
                "level": tolerance2.value,
                "max_drawdown": config2.max_drawdown,
                "max_position_size": config2.max_position_size,
                "leverage_allowed": config2.leverage_allowed,
                "max_leverage": config2.max_leverage,
            },
        }
