"""Example usage of InputProfileRouter.

This example demonstrates how to use the InputProfileRouter to automatically
select strategies and configure risk parameters based on user input.
"""

from decimal import Decimal

from app.application.routers.input_profile_router import InputProfileRouter
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)


def main() -> None:
    """Demonstrate InputProfileRouter usage."""
    # Example 1: Aggressive growth investor
    print("Example 1: Aggressive Growth Investor")
    print("-" * 50)

    profile1 = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.ALTO,
        investment_horizon=36,
    )

    router = InputProfileRouter()
    config1 = router(profile1)

    print(f"Objective: {profile1.objetivo_inversion.value}")
    print(f"Strategy: {config1.strategy_type.value}")
    print(f"Description: {config1.strategy_type.description}")
    print(f"Max Drawdown: {config1.risk_config.max_drawdown:.1%}")
    print(f"Leverage Allowed: {config1.risk_config.leverage_allowed}")
    print(f"Max Leverage: {config1.risk_config.max_leverage}x")
    print(f"Expected Volatility: {config1.expected_volatility:.1%}")
    print()

    # Example 2: Conservative dividend investor
    print("Example 2: Conservative Dividend Investor")
    print("-" * 50)

    profile2 = InputProfile(
        capital_initial=Decimal("50000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
        risk_tolerance=RiskTolerance.BAJO,
        investment_horizon=60,
        tax_residence=TaxResidence(
            country_code="ES",
            base_currency="EUR",
            capital_gains_rate_short=Decimal("0.19"),
            capital_gains_rate_long=Decimal("0.19"),
            dividend_tax_rate=Decimal("0.19"),
        ),
    )

    config2 = router(profile2)

    print(f"Objective: {profile2.objetivo_inversion.value}")
    print(f"Strategy: {config2.strategy_type.value}")
    print(f"Description: {config2.strategy_type.description}")
    print(f"Max Drawdown: {config2.risk_config.max_drawdown:.1%}")
    print(f"Leverage Allowed: {config2.risk_config.leverage_allowed}")
    print(f"Is Defensive: {config2.strategy_type.is_defensive}")
    print(f"Tax Optimization: {config2.tax_config is not None}")
    print(f"Tax Country: {config2.tax_config.country_code if config2.tax_config else 'N/A'}")
    print()

    # Example 3: Balanced investor with US tax residence
    print("Example 3: Balanced Investor with US Tax Residence")
    print("-" * 50)

    profile3 = InputProfile(
        capital_initial=Decimal("250000"),
        objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=48,
        tax_residence=TaxResidence(
            country_code="US",
            base_currency="USD",
            capital_gains_rate_short=Decimal("0.35"),
            capital_gains_rate_long=Decimal("0.15"),
            dividend_tax_rate=Decimal("0.20"),
            applies_wash_sale_rule=True,
        ),
    )

    config3 = router(profile3)

    print(f"Objective: {profile3.objetivo_inversion.value}")
    print(f"Strategy: {config3.strategy_type.value}")
    print(f"Description: {config3.strategy_type.description}")
    print(f"Max Drawdown: {config3.risk_config.max_drawdown:.1%}")
    print(f"Max Position Size: {config3.risk_config.max_position_size:.1%}")
    print(f"Leverage Allowed: {config3.risk_config.leverage_allowed}")
    print(f"Tax Long-term Advantage: {config3.tax_config.has_long_term_advantage if config3.tax_config else False}")
    print(f"Tax Advantage: {config3.tax_config.long_term_advantage:.1%}" if config3.tax_config else "")
    print(f"Requires Long-term Focus: {config3.requires_long_term_focus}")
    print()

    # Example 4: Capital preservation
    print("Example 4: Capital Preservation Investor")
    print("-" * 50)

    profile4 = InputProfile(
        capital_initial=Decimal("1000000"),
        objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
        risk_tolerance=RiskTolerance.BAJO,
        investment_horizon=120,
    )

    config4 = router(profile4)

    print(f"Objective: {profile4.objetivo_inversion.value}")
    print(f"Strategy: {config4.strategy_type.value}")
    print(f"Description: {config4.strategy_type.description}")
    print(f"Max Drawdown: {config4.risk_config.max_drawdown:.1%}")
    print(f"Max Portfolio Volatility: {config4.risk_config.max_portfolio_volatility:.1%}")
    print(f"Volatility Target: {config4.risk_config.volatility_target:.1%}" if config4.risk_config.volatility_target else "Volatility Target: None")
    print(f"Rebalance Frequency: {config4.rebalance_frequency_days} days")
    print(f"Is Conservative: {config4.risk_config.is_conservative}")
    print()

    # Example 5: Income generation
    print("Example 5: Income Generation Investor")
    print("-" * 50)

    profile5 = InputProfile(
        capital_initial=Decimal("150000"),
        objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
        risk_tolerance=RiskTolerance.BAJO,
        investment_horizon=24,
    )

    config5 = router(profile5)

    print(f"Objective: {profile5.objetivo_inversion.value}")
    print(f"Strategy: {config5.strategy_type.value}")
    print(f"Description: {config5.strategy_type.description}")
    print(f"Max Drawdown: {config5.risk_config.max_drawdown:.1%}")
    print(f"Is Complex Strategy: {config5.is_complex_strategy}")
    print(f"Deployable Capital: {config5.deployable_capital:,.2f}")
    print()

    # Show configuration validation
    print("Configuration Validation Example")
    print("-" * 50)

    # This configuration will generate a warning
    profile_warning = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
        risk_tolerance=RiskTolerance.ALTO,  # Contradictory!
        investment_horizon=12,
    )

    config_warning = router(profile_warning)
    is_valid, warnings = router.validate_configuration(profile_warning, config_warning)

    print(f"Valid: {is_valid}")
    print(f"Warnings:")
    for warning in warnings:
        print(f"  - {warning}")


if __name__ == "__main__":
    main()
