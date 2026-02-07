"""Input Profile Router - Maps InputProfile to strategies and configurations.

This module implements Brecha #1 from AUDIT_PLAN_COMPLETO.md section 4.1:
Automatic strategy selection based on investment objective.

The router maps:
- objetivo_inversion -> StrategyType (momentum, dividend, low_volatility, etc.)
- risk_tolerance -> RiskConfig (drawdown limits, position sizing, leverage)
- tax_residence -> TaxConfig (tax rates, optimization preferences)

Reference papers:
- Gray & Vogel: Quantitative Momentum (11-gray-vogel)
- Berkin & Swedroe: Factor-Based Investing (30-berkin-swedroe)
- Markowitz: Portfolio Selection (48-papers-markowitz)
- Fama-French: Factor Models (43-papers-fama-french)
- Kissell: Portfolio Management (42-kissell)
"""

from decimal import Decimal
from typing import Optional

import structlog

from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)
from app.domain.models.risk_config import RiskConfig
from app.domain.models.strategy_type import StrategyType
from app.domain.models.system_configuration import SystemConfiguration
from app.domain.models.tax_config import TaxConfig

logger = structlog.get_logger(__name__)


class InputProfileRouter:
    """Route InputProfile to appropriate strategies and risk configurations.

    This router implements the critical mapping from user inputs to system
    configuration, addressing Brecha #1: NO hay routing InputProfile -> Estrategia.

    The router follows SOLID principles:
    - SRP: Only responsible for routing/profile mapping
    - OCP: Can be extended with new strategies without modification
    - DIP: Depends on abstractions (domain models), not concrete implementations
    """

    def __init__(self) -> None:
        """Initialize the router with structured logging."""
        self._logger = structlog.get_logger(__name__)

    def __call__(self, profile: InputProfile) -> SystemConfiguration:
        """Generate complete system config from InputProfile.

        Args:
            profile: Validated InputProfile from user input

        Returns:
            SystemConfiguration: Complete configuration for the trading system

        Raises:
            ValueError: If profile validation fails
        """
        if profile is None:
            raise ValueError("profile cannot be None")

        self._logger.info(
            "Routing profile",
            objetivo=profile.objetivo_inversion.value,
            risk=profile.risk_tolerance.value,
            capital=str(profile.capital_initial),
        )

        # Select strategy type based on investment objective
        strategy_type = self._select_strategy_type(profile.objetivo_inversion)

        # Select risk configuration based on risk tolerance
        risk_config = self._select_risk_config(profile.risk_tolerance)

        # Create tax configuration if tax residence provided
        tax_config = self._create_tax_config(profile.tax_residence)

        # Calculate rebalancing frequency based on horizon
        rebalance_days = self._calculate_rebalance_frequency(profile.investment_horizon)

        # Build complete configuration
        config = SystemConfiguration(
            strategy_type=strategy_type,
            risk_config=risk_config,
            tax_config=tax_config,
            initial_capital=profile.capital_initial,
            investment_horizon_months=profile.investment_horizon,
            rebalance_frequency_days=rebalance_days,
        )

        self._logger.info(
            "Generated configuration",
            strategy=strategy_type.value,
            max_drawdown=str(risk_config.max_drawdown),
            leverage="allowed" if risk_config.leverage_allowed else "not allowed",
        )

        return config

    def _select_strategy_type(self, objetivo: ObjectivoInversion) -> StrategyType:
        """Select strategy type from investment objective.

        Maps investment objectives to strategy types based on academic research:

        | objetivo_inversion | Strategy Required | Reference Paper |
        |-------------------|-------------------|-----------------|
        | MAXIMIZAR_CAPITAL | Momentum/Trend Following | 11-gray-vogel |
        | MAXIMIZAR_DIVIDENDOS | Dividend Strategy | 30-berkin-swedroe |
        | CAPITAL_PRESERVATION | Low Volatility + Risk Parity | 48-papers-markowitz |
        | BALANCED_GROWTH | Multi-Factor | 43-papers-fama-french |
        | INCOME_GENERATION | Covered Calls | 42-kissell |

        Args:
            objetivo: User's investment objective

        Returns:
            StrategyType: Appropriate strategy for the objective

        Raises:
            ValueError: If objective is not recognized
        """
        strategies = {
            ObjectivoInversion.MAXIMIZAR_CAPITAL: StrategyType.MOMENTUM,
            ObjectivoInversion.MAXIMIZAR_DIVIDENDOS: StrategyType.DIVIDEND,
            ObjectivoInversion.CAPITAL_PRESERVATION: StrategyType.LOW_VOLATILITY,
            ObjectivoInversion.BALANCED_GROWTH: StrategyType.MULTI_FACTOR,
            ObjectivoInversion.INCOME_GENERATION: StrategyType.COVERED_CALL,
        }

        if objetivo not in strategies:
            raise ValueError(
                f"Unknown investment objective: {objetivo}. "
                f"Must be one of: {list(strategies.keys())}"
            )

        strategy = strategies[objetivo]
        self._logger.debug(
            "Mapped objetivo to strategy",
            objetivo=objetivo.value,
            strategy=strategy.value,
        )

        return strategy

    def _select_risk_config(self, tolerance: RiskTolerance) -> RiskConfig:
        """Select risk parameters from risk tolerance.

        Based on John Hull's risk management principles:
        - VaR limits based on tolerance
        - Position sizing to control concentration
        - Leverage constraints based on risk appetite

        Mapping:
        | RiskTolerance | Max Drawdown | Max Position | Leverage |
        |---------------|--------------|--------------|----------|
        | BAJO          | 15%          | 5%           | No       |
        | MEDIO         | 25%          | 10%          | 1.5x     |
        | ALTO          | 40%          | 20%          | 2.0x     |

        Args:
            tolerance: User's risk tolerance level

        Returns:
            RiskConfig: Risk configuration parameters

        Raises:
            ValueError: If tolerance is not recognized
        """
        configs = {
            RiskTolerance.BAJO: RiskConfig(
                max_drawdown=Decimal("0.15"),  # 15%
                var_confidence=Decimal("0.95"),
                max_position_size=Decimal("0.05"),  # 5%
                max_sector_exposure=Decimal("0.25"),
                leverage_allowed=False,
                max_leverage=Decimal("1.0"),
                min_positions=10,
                max_positions=50,
                stop_loss_enabled=True,
                stop_loss_atr_multiplier=Decimal("1.5"),
                trailing_stop_enabled=True,
                max_portfolio_volatility=Decimal("0.12"),
                volatility_target=Decimal("0.10"),
            ),
            RiskTolerance.MEDIO: RiskConfig(
                max_drawdown=Decimal("0.25"),  # 25%
                var_confidence=Decimal("0.95"),
                max_position_size=Decimal("0.10"),  # 10%
                max_sector_exposure=Decimal("0.30"),
                leverage_allowed=True,
                max_leverage=Decimal("1.5"),
                min_positions=5,
                max_positions=40,
                stop_loss_enabled=True,
                stop_loss_atr_multiplier=Decimal("2.0"),
                trailing_stop_enabled=False,
                max_portfolio_volatility=Decimal("0.18"),
                volatility_target=None,
            ),
            RiskTolerance.ALTO: RiskConfig(
                max_drawdown=Decimal("0.40"),  # 40%
                var_confidence=Decimal("0.95"),
                max_position_size=Decimal("0.20"),  # 20%
                max_sector_exposure=Decimal("0.40"),
                leverage_allowed=True,
                max_leverage=Decimal("2.0"),
                min_positions=3,
                max_positions=30,
                stop_loss_enabled=True,
                stop_loss_atr_multiplier=Decimal("2.5"),
                trailing_stop_enabled=False,
                max_portfolio_volatility=Decimal("0.25"),
                volatility_target=None,
            ),
        }

        if tolerance not in configs:
            raise ValueError(
                f"Unknown risk tolerance: {tolerance}. " f"Must be one of: {list(configs.keys())}"
            )

        config = configs[tolerance]
        self._logger.debug(
            "Mapped risk tolerance",
            tolerance=tolerance.value,
            max_dd=str(config.max_drawdown),
            leverage=config.leverage_allowed,
        )

        return config

    def _create_tax_config(self, tax_residence: Optional[TaxResidence]) -> Optional[TaxConfig]:
        """Create tax configuration from tax residence.

        Extracts tax optimization parameters from TaxResidence model.
        Returns None if no tax residence is provided.

        Args:
            tax_residence: User's tax residence configuration

        Returns:
            TaxConfig: Tax optimization parameters, or None if not provided
        """
        if tax_residence is None:
            self._logger.debug("No tax residence provided, tax optimization disabled")
            return None

        config = TaxConfig(
            country_code=tax_residence.country_code,
            base_currency=tax_residence.base_currency,
            capital_gains_rate_short=tax_residence.capital_gains_rate_short,
            capital_gains_rate_long=tax_residence.capital_gains_rate_long,
            dividend_tax_rate=tax_residence.dividend_tax_rate,
            withholding_tax_domestic=tax_residence.withholding_tax_domestic,
            withholding_tax_eu=tax_residence.withholding_tax_eu,
            withholding_tax_us=tax_residence.withholding_tax_us,
            applies_wash_sale_rule=tax_residence.applies_wash_sale_rule,
            allows_loss_carryforward=tax_residence.allows_loss_carryforward,
            loss_carryforward_years=tax_residence.loss_carryforward_years,
            prefer_long_term=(
                tax_residence.capital_gains_rate_long < tax_residence.capital_gains_rate_short
            ),
            min_holding_period_days=365,  # Standard 1 year for long-term
            requires_currency_hedging=tax_residence.requires_currency_hedging,
            hedging_instruments=["FX_FORWARDS", "CURRENCY_FUTURES"],
        )

        self._logger.debug(
            "Created tax config",
            country=tax_residence.country_code,
            prefer_long_term=config.prefer_long_term,
        )

        return config

    def _calculate_rebalance_frequency(self, horizon_months: int) -> int:
        """Calculate optimal rebalancing frequency based on investment horizon.

        Based on Grinold & Kahn's active portfolio management principles:
        - Longer horizons -> less frequent rebalancing
        - Shorter horizons -> more frequent rebalancing

        Args:
            horizon_months: Investment horizon in months

        Returns:
            int: Rebalancing frequency in days
        """
        if horizon_months < 6:
            # Short-term: rebalance weekly
            return 7
        elif horizon_months < 24:
            # Medium-term: rebalance bi-weekly
            return 14
        elif horizon_months < 60:
            # Long-term: rebalance monthly
            return 30
        else:
            # Very long-term: rebalance quarterly
            return 90

    def validate_configuration(
        self,
        profile: InputProfile,
        config: SystemConfiguration,
    ) -> tuple[bool, list[str]]:
        """Validate that configuration is appropriate for the profile.

        Performs consistency checks between InputProfile and generated
        SystemConfiguration to detect potential issues.

        Args:
            profile: Original InputProfile
            config: Generated SystemConfiguration

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check objective vs risk consistency
        if (
            profile.objetivo_inversion == ObjectivoInversion.CAPITAL_PRESERVATION
            and profile.risk_tolerance == RiskTolerance.ALTO
        ):
            warnings.append(
                "CAPITAL_PRESERVATION objective with ALTO risk tolerance may be contradictory"
            )

        # Check leverage vs objective
        if (
            profile.objetivo_inversion == ObjectivoInversion.CAPITAL_PRESERVATION
            and config.risk_config.leverage_allowed
        ):
            warnings.append(
                "CAPITAL_PRESERVATION objective with leverage allowed may not be optimal"
            )

        # Check horizon vs rebalancing
        if profile.investment_horizon < 12 and config.rebalance_frequency_days < 7:
            warnings.append(
                "Short investment horizon with frequent rebalancing "
                "may generate excessive transaction costs"
            )

        # Check capital vs diversification
        if profile.capital_initial < Decimal("50000") and config.risk_config.min_positions > 20:
            warnings.append("Small capital with high position minimum may cause over-fragmentation")

        is_valid = len(warnings) == 0

        if not is_valid:
            self._logger.warning("Configuration validation warnings", warnings=warnings)

        return is_valid, warnings
