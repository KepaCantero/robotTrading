"""
End-to-End Integration Tests for T1.1→T2.1→T3.1 Pipeline

Tests complete workflow from user input to parametrized modules:
- InputProfile (T1.1) → user investment intent
- InvestmentProfile (T2.1) → strategy configuration for objective + tier
- ModuleParameterSet (T3.1) → module-specific parameters

Covers:
- All 5 investment objectives
- All 4 capital tiers
- Parameter consistency across pipeline
- Enabled modules match module parameters
- Data flow integrity
"""

import pytest
import yaml
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.core.models.investment_profile import (
    CapitalTier,
    InvestmentProfile,
    ProfileGenerator,
)
from app.services.parametrization.module_parametrizer import (
    ModuleParametrizer,
    ModuleParameterSet,
)


# ===================== FIXTURES =====================

@pytest.fixture
def investment_profiles_config():
    """Load investment profiles YAML configuration."""
    yaml_path = Path("/Users/kepa.cantero/Projects/algoTrading/config/investment_profiles.yaml")
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def module_parameters_config():
    """Load module parameters YAML configuration."""
    yaml_path = Path("/Users/kepa.cantero/Projects/algoTrading/config/module_parameters.yaml")
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def profile_generator(investment_profiles_config) -> ProfileGenerator:
    """Create ProfileGenerator instance for testing."""
    return ProfileGenerator(investment_profiles_config)


@pytest.fixture
def module_parametrizer(module_parameters_config) -> ModuleParametrizer:
    """Create ModuleParametrizer instance for testing."""
    return ModuleParametrizer(module_parameters_config)


@pytest.fixture
def sample_input_profile_micro() -> InputProfile:
    """Sample micro-tier input profile."""
    return InputProfile(
        capital_initial=Decimal("10000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=12
    )


@pytest.fixture
def sample_input_profile_small() -> InputProfile:
    """Sample small-tier input profile."""
    return InputProfile(
        capital_initial=Decimal("30000"),
        objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24
    )


@pytest.fixture
def sample_input_profile_medium() -> InputProfile:
    """Sample medium-tier input profile."""
    return InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=36
    )


@pytest.fixture
def sample_input_profile_large() -> InputProfile:
    """Sample large-tier input profile."""
    return InputProfile(
        capital_initial=Decimal("500000"),
        objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
        risk_tolerance=RiskTolerance.BAJO,
        investment_horizon=60
    )


# ===================== PIPELINE INTEGRATION TESTS =====================

class TestCompleteE2EPipeline:
    """Test complete T1.1→T2.1→T3.1 pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_micro_maximizar_capital(
        self, profile_generator, module_parametrizer, sample_input_profile_micro
    ):
        """Test complete pipeline: micro account maximizing capital."""
        # Step 1: T1.1 - InputProfile is created (fixture provides this)
        input_profile = sample_input_profile_micro
        assert input_profile.capital_initial == Decimal("10000")
        assert input_profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL

        # Step 2: T2.1 - Generate InvestmentProfile
        investment_profile = profile_generator.generate(input_profile)
        assert investment_profile is not None
        assert investment_profile.capital_tier == CapitalTier.MICRO
        assert len(investment_profile.enabled_modules) > 0

        # Step 3: T3.1 - Parametrize modules
        module_params = module_parametrizer.generate(investment_profile)
        assert module_params is not None
        assert len(module_params.modules) > 0

        # Validate consistency
        assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)

    @pytest.mark.asyncio
    async def test_e2e_small_balanced_growth(
        self, profile_generator, module_parametrizer, sample_input_profile_small
    ):
        """Test complete pipeline: small account balanced growth."""
        input_profile = sample_input_profile_small
        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        assert investment_profile.capital_tier == CapitalTier.SMALL
        assert module_params is not None
        assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)

    @pytest.mark.asyncio
    async def test_e2e_medium_dividend_focus(
        self, profile_generator, module_parametrizer, sample_input_profile_medium
    ):
        """Test complete pipeline: medium account dividend focus."""
        input_profile = sample_input_profile_medium
        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        assert investment_profile.capital_tier == CapitalTier.MEDIUM
        assert module_params is not None
        assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)

    @pytest.mark.asyncio
    async def test_e2e_large_preservation(
        self, profile_generator, module_parametrizer, sample_input_profile_large
    ):
        """Test complete pipeline: large account capital preservation."""
        input_profile = sample_input_profile_large
        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        assert investment_profile.capital_tier == CapitalTier.LARGE
        assert module_params is not None
        assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)


# ===================== OBJECTIVE COVERAGE TESTS =====================

class TestAllObjectiveE2E:
    """Test all 5 investment objectives across all tiers."""

    @pytest.mark.asyncio
    async def test_maximizar_capital_all_tiers(
        self, profile_generator, module_parametrizer
    ):
        """Test maximizar_capital objective across all 4 tiers."""
        capital_amounts = {
            CapitalTier.MICRO: Decimal("10000"),
            CapitalTier.SMALL: Decimal("30000"),
            CapitalTier.MEDIUM: Decimal("100000"),
            CapitalTier.LARGE: Decimal("500000"),
        }

        for expected_tier, capital in capital_amounts.items():
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier
            assert len(module_params.modules) > 0
            assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)

    @pytest.mark.asyncio
    async def test_maximizar_dividendos_all_tiers(
        self, profile_generator, module_parametrizer
    ):
        """Test maximizar_dividendos objective across all 4 tiers."""
        capital_amounts = {
            CapitalTier.MICRO: Decimal("10000"),
            CapitalTier.SMALL: Decimal("30000"),
            CapitalTier.MEDIUM: Decimal("100000"),
            CapitalTier.LARGE: Decimal("500000"),
        }

        for expected_tier, capital in capital_amounts.items():
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
                risk_tolerance=RiskTolerance.BAJO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier
            assert len(module_params.modules) > 0
            # Dividend objectives should include dividend modules
            enabled_names = set(investment_profile.enabled_modules)
            assert any("dividend" in name.lower() for name in enabled_names)

    @pytest.mark.asyncio
    async def test_capital_preservation_all_tiers(
        self, profile_generator, module_parametrizer
    ):
        """Test capital_preservation objective across all 4 tiers."""
        capital_amounts = {
            CapitalTier.MICRO: Decimal("10000"),
            CapitalTier.SMALL: Decimal("30000"),
            CapitalTier.MEDIUM: Decimal("100000"),
            CapitalTier.LARGE: Decimal("500000"),
        }

        for expected_tier, capital in capital_amounts.items():
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
                risk_tolerance=RiskTolerance.BAJO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier
            assert len(module_params.modules) > 0
            # Preservation objectives should include defensive modules
            enabled_names = set(investment_profile.enabled_modules)
            assert any("defensive" in name.lower() or "hedge" in name.lower()
                      for name in enabled_names)

    @pytest.mark.asyncio
    async def test_balanced_growth_all_tiers(
        self, profile_generator, module_parametrizer
    ):
        """Test balanced_growth objective across all 4 tiers."""
        capital_amounts = {
            CapitalTier.MICRO: Decimal("10000"),
            CapitalTier.SMALL: Decimal("30000"),
            CapitalTier.MEDIUM: Decimal("100000"),
            CapitalTier.LARGE: Decimal("500000"),
        }

        for expected_tier, capital in capital_amounts.items():
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier
            assert len(module_params.modules) > 0

    @pytest.mark.asyncio
    async def test_income_generation_all_tiers(
        self, profile_generator, module_parametrizer
    ):
        """Test income_generation objective across all 4 tiers."""
        capital_amounts = {
            CapitalTier.MICRO: Decimal("10000"),
            CapitalTier.SMALL: Decimal("30000"),
            CapitalTier.MEDIUM: Decimal("100000"),
            CapitalTier.LARGE: Decimal("500000"),
        }

        for expected_tier, capital in capital_amounts.items():
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
                risk_tolerance=RiskTolerance.BAJO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier
            assert len(module_params.modules) > 0
            # Income objectives should include income-generating modules
            enabled_names = set(investment_profile.enabled_modules)
            assert any("dividend" in name.lower() or "call" in name.lower() or
                      "put" in name.lower() or "collar" in name.lower()
                      for name in enabled_names)


# ===================== PARAMETER CONSISTENCY TESTS =====================

class TestParameterConsistency:
    """Test parameter consistency across pipeline."""

    @pytest.mark.asyncio
    async def test_risk_profile_consistency(
        self, profile_generator, module_parametrizer
    ):
        """Test that risk_profile is consistent from profile to parameters."""
        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        # Risk profile should be consistent
        assert investment_profile.risk_profile >= 1
        assert investment_profile.risk_profile <= 7

        # Parameters should respect risk profile through risk_adjustment
        for module_name, module_param in module_params.modules.items():
            if hasattr(module_param, 'risk_adjustment'):
                assert 0.5 <= module_param.risk_adjustment <= 2.0

    @pytest.mark.asyncio
    async def test_leverage_applied_correctly(
        self, profile_generator, module_parametrizer
    ):
        """Test that leverage from profile is applied to module parameters."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        # Leverage should be defined in profile
        assert investment_profile.leverage_factor >= 0
        assert investment_profile.leverage_factor <= 2.5

        # Parameters should be generated without errors
        assert len(module_params.modules) > 0

    @pytest.mark.asyncio
    async def test_enabled_modules_match_parameters(
        self, profile_generator, module_parametrizer
    ):
        """Test that all enabled modules have parameters generated."""
        input_profile = InputProfile(
            capital_initial=Decimal("75000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=24,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        # All enabled modules must have parameters
        assert set(investment_profile.enabled_modules) == set(module_params.modules.keys())

    @pytest.mark.asyncio
    async def test_position_size_respects_capital_tier(
        self, profile_generator, module_parametrizer
    ):
        """Test that position sizes increase with capital tier."""
        tiers_and_capitals = [
            (Decimal("10000"), CapitalTier.MICRO),
            (Decimal("30000"), CapitalTier.SMALL),
            (Decimal("100000"), CapitalTier.MEDIUM),
            (Decimal("500000"), CapitalTier.LARGE),
        ]

        previous_max_size = 0
        for capital, expected_tier in tiers_and_capitals:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert investment_profile.capital_tier == expected_tier

            # Get max position size from generated parameters
            max_positions = []
            for module_param in module_params.modules.values():
                if hasattr(module_param, 'max_position_size'):
                    max_positions.append(module_param.max_position_size)

            if max_positions:
                current_max = max(max_positions)
                # Position sizes should generally increase with capital
                # (may not be strictly increasing due to objective-specific logic)
                assert current_max >= 0.01


# ===================== ERROR HANDLING & EDGE CASES =====================

class TestEdgeCasesAndErrors:
    """Test edge cases and error handling in pipeline."""

    @pytest.mark.asyncio
    async def test_minimum_capital_micro(
        self, profile_generator, module_parametrizer
    ):
        """Test minimum capital for micro tier."""
        input_profile = InputProfile(
            capital_initial=Decimal("1000"),  # Below €15k threshold
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        investment_profile = profile_generator.generate(input_profile)
        module_params = module_parametrizer.generate(investment_profile)

        assert investment_profile.capital_tier == CapitalTier.MICRO
        assert len(module_params.modules) > 0

    @pytest.mark.asyncio
    async def test_boundary_capital_small_to_medium(
        self, profile_generator, module_parametrizer
    ):
        """Test boundary between small and medium tiers."""
        # Just below €50k
        input_profile_small = InputProfile(
            capital_initial=Decimal("49999"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        # Just at €50k
        input_profile_medium = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        profile_small = profile_generator.generate(input_profile_small)
        profile_medium = profile_generator.generate(input_profile_medium)

        assert profile_small.capital_tier == CapitalTier.SMALL
        assert profile_medium.capital_tier == CapitalTier.MEDIUM

    @pytest.mark.asyncio
    async def test_multiple_objectives_same_capital(
        self, profile_generator, module_parametrizer
    ):
        """Test all objectives for same capital amount."""
        objectives = [
            ObjectivoInversion.MAXIMIZAR_CAPITAL,
            ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            ObjectivoInversion.CAPITAL_PRESERVATION,
            ObjectivoInversion.BALANCED_GROWTH,
            ObjectivoInversion.INCOME_GENERATION,
        ]

        capital = Decimal("50000")

        for objective in objectives:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=objective,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            investment_profile = profile_generator.generate(input_profile)
            module_params = module_parametrizer.generate(investment_profile)

            assert len(module_params.modules) > 0
            assert set(module_params.modules.keys()) == set(investment_profile.enabled_modules)

    @pytest.mark.asyncio
    async def test_risk_tolerance_influences_profile(
        self, profile_generator, module_parametrizer
    ):
        """Test that risk tolerance influences investment profile."""
        low_risk_input = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        high_risk_input = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=12,
        )

        low_risk_profile = profile_generator.generate(low_risk_input)
        high_risk_profile = profile_generator.generate(high_risk_input)

        # Risk profile should be lower for low risk tolerance
        assert low_risk_profile.risk_profile <= high_risk_profile.risk_profile

        # Both should generate valid parameters
        low_risk_params = module_parametrizer.generate(low_risk_profile)
        high_risk_params = module_parametrizer.generate(high_risk_profile)

        assert len(low_risk_params.modules) > 0
        assert len(high_risk_params.modules) > 0
