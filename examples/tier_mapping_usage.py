"""
Tier Mapping Usage Examples

This file contains practical examples demonstrating how to use the TierMapper
system throughout the algorithmic trading codebase.

Run examples:
    python -m examples.tier_mapping_usage
"""

from decimal import Decimal
from app.core.models.input_profile import InputProfile
from app.core.tier_mapper import (
    TierMapper,
    TierSystem,
    get_tier,
    normalize_tier,
    map_profile_tier_to_config,
    validate_tier_mapping,
)


def example_1_basic_conversions():
    """Example 1: Basic tier conversions between systems."""
    print("=" * 70)
    print("Example 1: Basic Tier Conversions")
    print("=" * 70)

    # Convert between systems
    print("\n1. Convert Spanish to YAML:")
    spanish_tier = "bajo"
    yaml_tier = TierMapper.to_spanish(spanish_tier, TierSystem.YAML)
    print(f"  {spanish_tier} -> {yaml_tier}")

    print("\n2. Convert YAML to Spanish:")
    yaml_tier = "large"
    spanish_tier = TierMapper.to_spanish(yaml_tier)
    print(f"  {yaml_tier} -> {spanish_tier}")

    print("\n3. Convert capital_flag to YAML:")
    capital_flag = "medium"
    yaml_tier = TierMapper.to_yaml_tier(capital_flag, TierSystem.CAPITAL_FLAG)
    print(f"  {capital_flag} -> {yaml_tier}")

    print("\n4. Detect tier system:")
    for tier in ["bajo", "micro", "small"]:
        system = TierMapper.detect_system(tier)
        print(f"  '{tier}' belongs to: {system.value}")


def example_2_capital_to_tier():
    """Example 2: Determine tier from capital amount."""
    print("\n" + "=" * 70)
    print("Example 2: Capital to Tier Conversion")
    print("=" * 70)

    capitals = [
        Decimal("10000"),  # €10k
        Decimal("30000"),  # €30k
        Decimal("75000"),  # €75k
        Decimal("300000"),  # €300k
    ]

    print(f"\n{'Capital (EUR)':<20} {'YAML Tier':<12} {'Capital Flag':<15} {'Spanish'}")
    print("-" * 70)

    for capital in capitals:
        yaml_tier = get_tier(capital, TierSystem.YAML)
        capital_flag = get_tier(capital, TierSystem.CAPITAL_FLAG)
        spanish_tier = get_tier(capital, TierSystem.SPANISH)

        print(f"€{str(capital):>17,}  {yaml_tier:<12} {capital_flag:<15} {spanish_tier}")


def example_3_profile_workflow():
    """Example 3: Complete profile processing workflow."""
    print("\n" + "=" * 70)
    print("Example 3: Profile Processing Workflow")
    print("=" * 70)

    # Step 1: Create InputProfile from user input
    print("\n1. Create InputProfile:")
    profile = InputProfile(
        capital_initial=Decimal("75000"),
        objetivo_inversion="maximizar_capital",
        risk_tolerance="medio",
        investment_horizon=24,
    )
    print(f"  Capital: €{profile.capital_initial:,}")
    print(f"  Capital flag: {profile.capital_flag}")

    # Step 2: Convert to YAML tier for config lookup
    print("\n2. Convert to YAML tier:")
    yaml_tier = map_profile_tier_to_config(profile.capital_flag, "yaml")
    print(f"  YAML tier: {yaml_tier}")

    # Step 3: Convert to Spanish for tax config
    print("\n3. Convert to Spanish tier:")
    spanish_tier = map_profile_tier_to_config(profile.capital_flag, "spanish")
    print(f"  Spanish tier: {spanish_tier}")

    # Step 4: Show all equivalent tiers
    print("\n4. All equivalent tiers:")
    print(f"  Capital flag: {profile.capital_flag}")
    print(f"  YAML tier: {yaml_tier}")
    print(f"  Spanish tier: {spanish_tier}")


def example_4_validation():
    """Example 4: Tier validation and consistency checking."""
    print("\n" + "=" * 70)
    print("Example 4: Validation and Consistency Checking")
    print("=" * 70)

    # Check tier validity
    print("\n1. Check tier validity:")
    test_tiers = ["small", "micro", "bajo", "invalid", "tiny"]
    for tier in test_tiers:
        is_valid = TierMapper.is_valid_tier(tier)
        if is_valid:
            system = TierMapper.detect_system(tier)
            print(f"  '{tier}': Valid (system: {system.value})")
        else:
            print(f"  '{tier}': Invalid")

    # Check mapping consistency
    print("\n2. Check mapping consistency:")
    is_valid, warnings = validate_tier_mapping()
    if is_valid:
        print("  ✅ All tier mappings are consistent")
    else:
        print(f"  ⚠️  Found {len(warnings)} issues:")
        for warning in warnings:
            print(f"     - {warning}")

    # List all valid tiers
    print("\n3. All valid tiers by system:")
    valid_tiers = TierMapper.list_all_valid_tiers()
    for system, tiers in valid_tiers.items():
        print(f"  {system}: {', '.join(tiers)}")


def example_5_normalization():
    """Example 5: Normalize tiers to a standard system."""
    print("\n" + "=" * 70)
    print("Example 5: Tier Normalization")
    print("=" * 70)

    # Various tier names from different contexts
    tier_names = ["small", "micro", "bajo", "medium", "medio", "large", "alto"]

    print("\n1. Normalize all to YAML system:")
    print(f"{'Original':<12} {'Normalized (YAML)':<20} {'System'}")
    print("-" * 50)
    for tier in tier_names:
        normalized = normalize_tier(tier, TierSystem.YAML)
        system = TierMapper.detect_system(tier)
        print(f"{tier:<12} {normalized:<20} {system.value}")

    print("\n2. Normalize all to Spanish system:")
    print(f"{'Original':<12} {'Normalized (Spanish)':<20} {'System'}")
    print("-" * 50)
    for tier in tier_names:
        normalized = normalize_tier(tier, TierSystem.SPANISH)
        system = TierMapper.detect_system(tier)
        print(f"{tier:<12} {normalized:<20} {system.value}")


def example_6_error_handling():
    """Example 6: Error handling for invalid tiers."""
    print("\n" + "=" * 70)
    print("Example 6: Error Handling")
    print("=" * 70)

    invalid_tiers = ["invalid", "tiny", "huge", "pequeño", "grand"]

    print("\n1. Detecting invalid tiers:")
    for tier in invalid_tiers:
        try:
            system = TierMapper.detect_system(tier)
            print(f"  '{tier}': {system.value}")
        except ValueError as e:
            print(f"  '{tier}': Error - {str(e)[:60]}...")

    print("\n2. Graceful handling with validation:")
    for tier in invalid_tiers:
        if TierMapper.is_valid_tier(tier):
            normalized = normalize_tier(tier, TierSystem.YAML)
            print(f"  '{tier}': Valid -> {normalized}")
        else:
            print(f"  '{tier}': Invalid (skipped)")


def example_7_mapping_table():
    """Example 7: Display complete mapping table."""
    print("\n" + "=" * 70)
    print("Example 7: Complete Mapping Table")
    print("=" * 70)

    # Get all unique tiers
    yaml_tiers = ["micro", "small", "medium", "large"]
    capital_flags = ["small", "medium", "large"]

    print("\nCapital Ranges and Tier Mappings:")
    print(f"\n{'Capital Range':<25} {'YAML':<10} {'Cap Flag':<10} {'Spanish':<10}")
    print("-" * 70)

    ranges = [
        ("< €15,000", "micro", "small", "bajo"),
        ("€15,000 - €50,000", "small", "small", "bajo"),
        ("€50,000 - €250,000", "medium", "medium", "medio"),
        (">= €250,000", "large", "large", "alto"),
    ]

    for range_str, yaml_t, cf_t, sp_t in ranges:
        print(f"{range_str:<25} {yaml_t:<10} {cf_t:<10} {sp_t:<10}")

    print("\nConversion Mappings:")
    print(f"\n{'From':<12} {'To YAML':<10} {'To Cap Flag':<12} {'To Spanish':<10}")
    print("-" * 70)

    for tier in capital_flags:
        to_yaml = TierMapper.to_yaml_tier(tier, TierSystem.CAPITAL_FLAG)
        to_spanish = TierMapper.to_spanish(tier, TierSystem.CAPITAL_FLAG)
        print(f"{tier:<12} {to_yaml:<10} {tier:<12} {to_spanish:<10}")

    for tier in yaml_tiers:
        to_cap_flag = TierMapper.to_capital_flag(tier, TierSystem.YAML)
        to_spanish = TierMapper.to_spanish(tier, TierSystem.YAML)
        print(f"{tier:<12} {tier:<10} {to_cap_flag:<12} {to_spanish:<10}")


def example_8_practical_use_case():
    """Example 8: Practical use case - Module gating."""
    print("\n" + "=" * 70)
    print("Example 8: Practical Use Case - Module Gating")
    print("=" * 70)

    # Simulate module gating logic
    expensive_modules = {
        "deep_learning_engine": Decimal("50000"),
        "transformer_engine": Decimal("100000"),
        "reinforcement_learning_engine": Decimal("50000"),
    }

    capitals = [
        Decimal("30000"),  # Small account
        Decimal("75000"),  # Medium account
        Decimal("300000"),  # Large account
    ]

    for capital in capitals:
        tier = get_tier(capital, TierSystem.YAML)
        print(f"\nCapital: €{capital:,} (tier: {tier})")

        enabled = []
        disabled = []

        for module, min_capital in expensive_modules.items():
            if capital >= min_capital:
                enabled.append(module)
            else:
                disabled.append(module)

        print("  Enabled modules:")
        for module in enabled:
            print(f"    ✅ {module}")
        print("  Disabled modules (insufficient capital):")
        for module in disabled:
            print(f"    ❌ {module} (requires €{min_capital:,}+)")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("TIER MAPPING USAGE EXAMPLES")
    print("=" * 70)

    example_1_basic_conversions()
    example_2_capital_to_tier()
    example_3_profile_workflow()
    example_4_validation()
    example_5_normalization()
    example_6_error_handling()
    example_7_mapping_table()
    example_8_practical_use_case()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
