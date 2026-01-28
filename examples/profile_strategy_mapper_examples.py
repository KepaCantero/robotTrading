"""
Examples of using ProfileStrategyMapper

This file demonstrates how to use the ProfileStrategyMapper to convert
user investment profiles into trading configurations.
"""

import logging
from decimal import Decimal

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading.profile_strategy_mapper import (
    ProfileStrategyMapper,
    create_profile_mapper,
    map_profile_to_strategies,
    get_capital_tier,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_mapping():
    """
    Example 1: Basic profile to strategy mapping.

    Shows how to map a simple investment profile to strategies.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Profile to Strategy Mapping")
    print("=" * 80)

    # Create mapper
    mapper = create_profile_mapper()

    # Create user profile
    profile = InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,  # 2 years
    )

    print(f"\nUser Profile:")
    print(f"  Capital: €{profile.capital_initial:,.2f}")
    print(f"  Objective: {profile.objetivo_inversion.value}")
    print(f"  Risk Tolerance: {profile.risk_tolerance.value}")
    print(f"  Horizon: {profile.investment_horizon} months")
    print(f"  Capital Tier: {get_capital_tier(profile.capital_initial)}")

    # Map to strategies
    strategy_config = mapper.map_profile_to_strategies(profile)

    print(f"\nStrategy Configuration:")
    print(f"  Enabled Strategies: {', '.join(strategy_config['enabled_strategies'])}")
    print(f"  Risk Profile: {strategy_config['risk_params']['risk_profile']}")
    print(f"  Leverage: {strategy_config['risk_params']['leverage']}x")
    print(f"  Max Position Size: {strategy_config['risk_params']['max_position_size']:.1%}")
    print(f"  Order Splitting: {strategy_config['trading_params']['order_splitting_strategy']}")

    print(f"\nLearning Engines:")
    print(f"  {', '.join(strategy_config['learning_engines']) or 'None'}")

    print(f"\nEnsemble Configuration:")
    ensemble = strategy_config['ensemble_config']
    print(f"  Mode: {ensemble['mode']}")
    print(f"  Min Strategies: {ensemble['min_strategies']}")
    print(f"  Min Confidence: {ensemble['min_confidence']:.1%}")


def example_capital_allocation():
    """
    Example 2: Capital allocation across strategies.

    Shows how capital is distributed across multiple strategies.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Capital Allocation")
    print("=" * 80)

    mapper = create_profile_mapper()

    # Test different capital tiers
    test_cases = [
        (Decimal("10000"), "Micro account (< €15k)"),
        (Decimal("30000"), "Small account (€15k-€50k)"),
        (Decimal("100000"), "Medium account (€50k-€250k)"),
        (Decimal("500000"), "Large account (>= €250k)"),
    ]

    for capital, description in test_cases:
        print(f"\n{description}: €{capital:,.2f}")

        profile = InputProfile(
            capital_initial=capital,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=36,
        )

        # Get capital allocation
        allocation_manager = mapper.get_capital_allocation(profile)
        allocations = allocation_manager.allocate_capital()

        print(f"  Tier: {get_capital_tier(capital)}")
        print(f"  Strategies: {len(allocations)}")
        for strategy, amount in allocations.items():
            weight = allocation_manager.strategy_allocations[strategy].current_weight
            print(f"    {strategy}: €{amount:,.2f} ({weight:.1%})")


def example_risk_tolerance_comparison():
    """
    Example 3: Comparing different risk tolerance levels.

    Shows how risk tolerance affects strategy selection and ensemble configuration.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Risk Tolerance Comparison")
    print("=" * 80)

    mapper = create_profile_mapper()

    capital = Decimal("100000")

    for risk_tolerance in [RiskTolerance.BAJO, RiskTolerance.MEDIO, RiskTolerance.ALTO]:
        print(f"\nRisk Tolerance: {risk_tolerance.value}")

        profile = InputProfile(
            capital_initial=capital,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=risk_tolerance,
            investment_horizon=24,
        )

        # Get ensemble configuration
        ensemble_config = mapper.get_ensemble_config(profile)

        print(f"  Ensemble Mode: {ensemble_config['mode']}")
        print(f"  Min Strategies Required: {ensemble_config['min_strategies']}")
        print(f"  Min Confidence: {ensemble_config['min_confidence']:.1%}")
        print(f"  Require Majority: {ensemble_config.get('require_majority', False)}")


def example_investment_objectives():
    """
    Example 4: Different investment objectives.

    Shows how different objectives map to different strategies.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Investment Objectives")
    print("=" * 80)

    mapper = create_profile_mapper()

    objectives = [
        (ObjectivoInversion.MAXIMIZAR_CAPITAL, "Maximize Capital Growth"),
        (ObjectivoInversion.MAXIMIZAR_DIVIDENDOS, "Maximize Dividend Income"),
        (ObjectivoInversion.CAPITAL_PRESERVATION, "Capital Preservation"),
        (ObjectivoInversion.BALANCED_GROWTH, "Balanced Growth"),
        (ObjectivoInversion.INCOME_GENERATION, "Income Generation"),
    ]

    capital = Decimal("75000")  # Small tier

    for objective, description in objectives:
        print(f"\n{description} ({objective.value})")

        profile = InputProfile(
            capital_initial=capital,
            objetivo_inversion=objective,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=36,
        )

        # Map to strategies
        strategy_config = mapper.map_profile_to_strategies(profile)

        print(f"  Enabled Strategies: {', '.join(strategy_config['enabled_strategies'])}")
        print(f"  Risk Profile: {strategy_config['risk_params']['risk_profile']}/6")
        print(f"  Leverage: {strategy_config['risk_params']['leverage']}x")


def example_complete_mapping():
    """
    Example 5: Complete strategy mapping.

    Shows the full StrategyMapping object with all configurations.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Complete Strategy Mapping")
    print("=" * 80)

    mapper = create_profile_mapper()

    # Create a comprehensive profile
    profile = InputProfile(
        capital_initial=Decimal("300000"),  # Large tier
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.ALTO,
        investment_horizon=48,  # 4 years
    )

    # Create complete mapping
    mapping = mapper.create_strategy_mapping(profile)

    print(f"\nComplete Strategy Mapping:")
    print(f"  Objective: {mapping.objective.value}")
    print(f"  Capital Tier: {mapping.capital_tier}")
    print(f"  Risk Tolerance: {mapping.risk_tolerance.value}")

    print(f"\nStrategies ({len(mapping.enabled_strategies)}):")
    for strategy in mapping.enabled_strategies:
        weight = mapping.strategy_weights.get(strategy, 0)
        capital = mapping.capital_allocation.get(strategy, Decimal("0"))
        print(f"  - {strategy}")
        print(f"      Weight: {weight:.1%}")
        print(f"      Capital: €{capital:,.2f}")

    print(f"\nRisk Parameters:")
    print(f"  Risk Profile: {mapping.risk_profile}/6")
    print(f"  Leverage: {mapping.leverage}x")
    print(f"  Max Position: {mapping.max_position_size:.1%}")
    print(f"  Max Sector: {mapping.max_sector_allocation:.1%}")

    print(f"\nTrading Configuration:")
    print(f"  Order Splitting: {mapping.order_splitting_strategy}")
    print(f"  Commission Negotiation: {mapping.commission_negotiation}")

    print(f"\nLearning:")
    print(f"  Engines: {', '.join(mapping.enabled_learning_engines) or 'None'}")

    print(f"\nEnsemble:")
    print(f"  Mode: {mapping.ensemble_mode}")
    print(f"  Min Strategies: {mapping.ensemble_min_strategies}")
    print(f"  Confidence Threshold: {mapping.ensemble_confidence_threshold:.1%}")


def example_learning_parameters():
    """
    Example 6: Learning engine parameters.

    Shows how to get learning parameters for different engines.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Learning Engine Parameters")
    print("=" * 80)

    mapper = create_profile_mapper()

    profile = InputProfile(
        capital_initial=Decimal("300000"),  # Large tier for all engines
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=36,
    )

    # Get parameters for different engine types
    for engine_type in ["supervised", "reinforcement", "deep"]:
        print(f"\n{engine_type.upper()} Learning Parameters:")
        params = mapper.get_learning_parameters(profile, engine_type)

        if params:
            # Print top-level parameters
            for key, value in list(params.items())[:5]:
                print(f"  {key}: {value}")
            if len(params) > 5:
                print(f"  ... and {len(params) - 5} more parameters")
        else:
            print(f"  No parameters found for {engine_type}")


def example_convenience_function():
    """
    Example 7: Using the convenience function.

    Shows the simplest way to map a profile to strategies.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Convenience Function")
    print("=" * 80)

    # Create profile
    profile = InputProfile(
        capital_initial=Decimal("50000"),
        objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,
    )

    # Use convenience function
    mapping = map_profile_to_strategies(profile)

    print(f"\nQuick Mapping Result:")
    print(f"  Strategies: {', '.join(mapping.enabled_strategies)}")
    print(f"  Ensemble: {mapping.ensemble_mode}")
    print(f"  Risk Level: {mapping.risk_profile}/6")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ProfileStrategyMapper Usage Examples")
    print("=" * 80)

    try:
        example_basic_mapping()
        example_capital_allocation()
        example_risk_tolerance_comparison()
        example_investment_objectives()
        example_complete_mapping()
        example_learning_parameters()
        example_convenience_function()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("Make sure configuration files exist in config/")


if __name__ == "__main__":
    main()
