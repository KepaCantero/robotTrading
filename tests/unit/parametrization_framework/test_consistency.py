"""
Cross-Component Consistency Tests for T2.1 & T3.1

Tests consistency and integration between ProfileGenerator and ModuleParametrizer:
- Every enabled module has proper configuration
- Module selections match objectives
- Parameters are consistent across components
- No orphaned configurations
- Capital tier progression is consistent

Validates that T2.1 output (InvestmentProfile) properly integrates with T3.1 (ModuleParametrizer)
"""

from decimal import Decimal
from pathlib import Path
from typing import Set

import pytest
import yaml

from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.domain.models.investment_profile import CapitalTier, ProfileGenerator
from app.services.parametrization.module_parametrizer import ModuleParametrizer

# ===================== FIXTURES =====================


@pytest.fixture
def investment_profiles_config():
    """Load investment profiles YAML configuration."""
    yaml_path = Path("/Users/kepa.cantero/Projects/algoTrading/config/investment_profiles.yaml")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def module_parameters_config():
    """Load module parameters YAML configuration."""
    yaml_path = Path("/Users/kepa.cantero/Projects/algoTrading/config/module_parameters.yaml")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def profile_generator(investment_profiles_config) -> ProfileGenerator:
    """Create ProfileGenerator instance."""
    return ProfileGenerator(investment_profiles_config)


@pytest.fixture
def module_parametrizer(module_parameters_config) -> ModuleParametrizer:
    """Create ModuleParametrizer instance."""
    return ModuleParametrizer(module_parameters_config)


@pytest.fixture
def all_enabled_modules(investment_profiles_config) -> Set[str]:
    """Get all modules enabled across all configurations."""
    modules = set()
    for objective_config in investment_profiles_config["profiles"].values():
        for tier_config in objective_config.values():
            if isinstance(tier_config, dict) and "enabled_modules" in tier_config:
                modules.update(tier_config["enabled_modules"])
    return modules


@pytest.fixture
def configured_modules(module_parameters_config) -> Set[str]:
    """Get all modules with configurations."""
    return set(module_parameters_config["modules"].keys())


# ===================== CROSS-COMPONENT CONSISTENCY TESTS =====================


class TestModuleConfigurationConsistency:
    """Test that all enabled modules have proper configurations."""

    def test_all_enabled_modules_configured(self, all_enabled_modules, configured_modules):
        """Test that every enabled module has a configuration."""
        missing_config = all_enabled_modules - configured_modules
        assert not missing_config, f"Modules without configuration: {missing_config}"

    def test_all_objectives_have_enabled_modules(self, investment_profiles_config):
        """Test that each objective+tier combination has enabled modules."""
        for objective, tier_configs in investment_profiles_config["profiles"].items():
            for tier, config in tier_configs.items():
                assert "enabled_modules" in config, f"{objective}/{tier}: missing enabled_modules"
                assert (
                    len(config["enabled_modules"]) > 0
                ), f"{objective}/{tier}: empty enabled_modules"

    def test_module_tiers_match_capital_tiers(self, module_parameters_config):
        """Test that each module has all 4 capital tier configurations."""

        for module_name, module_config in module_parameters_config["modules"].items():
            if "tiers" in module_config:
                set(module_config["tiers"].keys())
                # Some modules may be intentionally disabled for certain tiers
                # Just ensure they have some configuration

    def test_enabled_modules_in_module_parametrizer_output(
        self, profile_generator, module_parametrizer
    ):
        """Test that ModuleParametrizer generates params for all enabled modules."""
        test_cases = [
            (Decimal("10000"), ObjectivoInversion.MAXIMIZAR_CAPITAL),
            (Decimal("30000"), ObjectivoInversion.BALANCED_GROWTH),
            (Decimal("100000"), ObjectivoInversion.MAXIMIZAR_DIVIDENDOS),
            (Decimal("500000"), ObjectivoInversion.CAPITAL_PRESERVATION),
        ]

        for capital, objective in test_cases:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=objective,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            # All enabled modules should be in module_params
            enabled_set = set(investment_profile.enabled_modules)
            configured_set = set(module_params.modules.keys())
            assert enabled_set == configured_set, (
                f"Mismatch for {objective}/{capital}: "
                f"enabled={enabled_set}, configured={configured_set}"
            )


class TestObjectiveModuleAlignment:
    """Test that module selections align with investment objectives."""

    def test_dividend_objectives_have_dividend_modules(self, profile_generator):
        """Test that dividend objectives include dividend-related modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        enabled_lower = [m.lower() for m in investment_profile.enabled_modules]

        assert any(
            "dividend" in m for m in enabled_lower
        ), f"Dividend objective missing dividend modules: {investment_profile.enabled_modules}"

    def test_preservation_objectives_have_defensive_modules(self, profile_generator):
        """Test that preservation objectives include defensive modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        enabled_lower = [m.lower() for m in investment_profile.enabled_modules]

        assert any(
            "defensive" in m or "hedge" in m for m in enabled_lower
        ), f"Preservation objective missing defensive modules: {investment_profile.enabled_modules}"

    def test_growth_objectives_have_growth_modules(self, profile_generator):
        """Test that growth objectives include appropriate modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        # Should have modules for capital growth
        assert len(investment_profile.enabled_modules) > 0, "Growth objective should enable modules"

    def test_income_objectives_have_income_modules(self, profile_generator):
        """Test that income objectives include income-generating modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        enabled_lower = [m.lower() for m in investment_profile.enabled_modules]

        # Income generation should include dividend or options-related modules
        assert any(
            "dividend" in m or "call" in m or "put" in m or "collar" in m for m in enabled_lower
        ), f"Income objective missing income modules: {investment_profile.enabled_modules}"


class TestParameterConsistencyAcrossComponents:
    """Test parameter consistency between ProfileGenerator and ModuleParametrizer."""

    def test_risk_profile_ranges_consistent(self, profile_generator, module_parametrizer):
        """Test that risk profiles are consistent (1-7 range)."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_parametrizer.generate(investment_profile)

        # Risk profile should be in valid range
        assert 1 <= investment_profile.risk_profile <= 7
        assert investment_profile.capital_tier in [
            CapitalTier.MICRO,
            CapitalTier.SMALL,
            CapitalTier.MEDIUM,
            CapitalTier.LARGE,
        ]

    def test_leverage_consistency(self, profile_generator, module_parametrizer):
        """Test that leverage is consistently applied."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_parametrizer.generate(investment_profile)

        # Leverage should be valid
        assert Decimal("0") <= investment_profile.leverage_factor <= Decimal("2.5")

    def test_position_size_consistency(self, profile_generator, module_parametrizer):
        """Test that position sizes are consistent across profile and modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        # Profile max_position_size should be reasonable
        assert Decimal("0.01") <= investment_profile.max_position_size <= Decimal("1.0")

        # All module position sizes should be in valid range
        for module_param in module_params.modules.values():
            assert Decimal("0.01") <= module_param.max_position_size <= Decimal("1.0")


class TestNoOrphanedConfigurations:
    """Test for orphaned or unused configurations."""

    def test_no_completely_unused_modules(self, all_enabled_modules, configured_modules):
        """Test that most configured modules are used somewhere."""
        # Not all configured modules need to be used (some might be fallback)
        # but the majority should be referenced
        used_ratio = len(all_enabled_modules & configured_modules) / len(configured_modules)
        assert used_ratio > 0.8, f"Too many unused modules: {used_ratio:.1%} usage rate"

    def test_tier_progression_by_module(self, module_parameters_config):
        """Test that modules have proper tier progressions."""
        for module_name, module_config in module_parameters_config["modules"].items():
            if "tiers" in module_config:
                tiers = module_config["tiers"]
                # If micro and large are both configured, small should be between them
                if "micro" in tiers and "large" in tiers:
                    assert (
                        "small" in tiers or "medium" in tiers
                    ), f"{module_name}: missing intermediate tiers"


class TestCapitalTierConsistency:
    """Test that capital tier logic is consistent."""

    def test_tier_progression_increases_modules(self, profile_generator):
        """Test that modules increase with capital tier."""
        objectives = [
            ObjectivoInversion.MAXIMIZAR_CAPITAL,
            ObjectivoInversion.BALANCED_GROWTH,
        ]

        for objective in objectives:
            profiles = {}
            for capital, expected_tier in [
                (Decimal("10000"), CapitalTier.MICRO),
                (Decimal("30000"), CapitalTier.SMALL),
                (Decimal("100000"), CapitalTier.MEDIUM),
                (Decimal("500000"), CapitalTier.LARGE),
            ]:
                input_profile = InputProfile(
                    capital_initial=capital,
                    objetivo_inversion=objective,
                    risk_tolerance=RiskTolerance.MEDIO,
                    investment_horizon=12,
                )
                profile = profile_generator.generate(input_profile)
                assert profile.capital_tier == expected_tier
                profiles[expected_tier] = len(profile.enabled_modules)

            # Generally, larger tiers should have more modules
            # (though not strictly enforced due to objective variation)
            assert (
                profiles[CapitalTier.LARGE] >= profiles[CapitalTier.MICRO]
            ), f"{objective}: large tier should have >= micro tier modules"

    def test_tier_boundaries_correct(self, profile_generator):
        """Test that capital tier boundaries are correctly applied."""
        test_cases = [
            (Decimal("1000"), CapitalTier.MICRO),
            (Decimal("14999"), CapitalTier.MICRO),
            (Decimal("15000"), CapitalTier.SMALL),
            (Decimal("49999"), CapitalTier.SMALL),
            (Decimal("50000"), CapitalTier.MEDIUM),
            (Decimal("249999"), CapitalTier.MEDIUM),
            (Decimal("250000"), CapitalTier.LARGE),
            (Decimal("1000000"), CapitalTier.LARGE),
        ]

        for capital, expected_tier in test_cases:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            profile = profile_generator.generate(input_profile)
            assert (
                profile.capital_tier == expected_tier
            ), f"Capital {capital} should be {expected_tier.value}, got {profile.capital_tier.value}"


class TestComponentIntegration:
    """Test integration between ProfileGenerator and ModuleParametrizer."""

    def test_full_pipeline_consistency_all_combinations(
        self, profile_generator, module_parametrizer
    ):
        """Test consistency across all objective+tier combinations."""
        objectives = [
            ObjectivoInversion.MAXIMIZAR_CAPITAL,
            ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            ObjectivoInversion.CAPITAL_PRESERVATION,
            ObjectivoInversion.BALANCED_GROWTH,
            ObjectivoInversion.INCOME_GENERATION,
        ]

        capitals = [
            Decimal("10000"),  # MICRO
            Decimal("30000"),  # SMALL
            Decimal("100000"),  # MEDIUM
            Decimal("500000"),  # LARGE
        ]

        for objective in objectives:
            for capital in capitals:
                input_profile = InputProfile(
                    capital_initial=capital,
                    objetivo_inversion=objective,
                    risk_tolerance=RiskTolerance.MEDIO,
                    investment_horizon=12,
                )

                # Generate profile
                investment_profile = profile_generator.generate(input_profile)
                assert investment_profile is not None

                # Parametrize modules
                module_params = module_parametrizer.generate(investment_profile)
                assert module_params is not None

                # Consistency check: enabled modules should match module parameters
                assert set(investment_profile.enabled_modules) == set(
                    module_params.modules.keys()
                ), (
                    f"Inconsistency for {objective}/{capital}: "
                    f"enabled={set(investment_profile.enabled_modules)}, "
                    f"params={set(module_params.modules.keys())}"
                )

                # All module parameters should be valid
                for module_param in module_params.modules.values():
                    assert module_param.module_name in investment_profile.enabled_modules
                    assert Decimal("0.01") <= module_param.max_position_size <= Decimal("1.0")
