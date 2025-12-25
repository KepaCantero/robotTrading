"""
T2.1: ProfileGenerator Tests

Tests for ProfileGenerator, InvestmentProfile, and related models.
"""

import pytest
from decimal import Decimal
from app.services.profile_generator import (
    ProfileGenerator,
    get_profile_generator,
    InvestmentProfile,
    CapitalTier,
    InvestmentObjective,
    RiskProfile,
    ProfileGenerationRequest,
)


# PROFILE GENERATOR TESTS
class TestProfileGeneratorInitialization:
    def test_generator_init(self):
        """Test profile generator initialization."""
        generator = ProfileGenerator()
        assert len(generator.generation_history) == 0
        assert len(generator.profile_cache) == 0

    def test_generator_singleton(self):
        """Test profile generator singleton pattern."""
        g1 = get_profile_generator()
        g2 = get_profile_generator()
        assert g1 is g2

    def test_template_loading(self):
        """Test that profile templates are loaded."""
        generator = ProfileGenerator()
        assert len(generator.profile_templates) > 0
        # Check for either flat or nested structure
        has_profiles = ('profiles' in generator.profile_templates) or ('maximizar_capital' in generator.profile_templates)
        assert has_profiles


class TestCapitalTierDetermination:
    def test_determine_tier_micro(self):
        """Test capital tier determination for micro capital."""
        generator = ProfileGenerator()
        tier = generator._determine_capital_tier(Decimal("10000"))
        assert tier == CapitalTier.MICRO

    def test_determine_tier_small(self):
        """Test capital tier determination for small capital."""
        generator = ProfileGenerator()
        tier = generator._determine_capital_tier(Decimal("50000"))
        assert tier == CapitalTier.SMALL

    def test_determine_tier_medium(self):
        """Test capital tier determination for medium capital."""
        generator = ProfileGenerator()
        tier = generator._determine_capital_tier(Decimal("250000"))
        assert tier == CapitalTier.MEDIUM

    def test_determine_tier_large(self):
        """Test capital tier determination for large capital."""
        generator = ProfileGenerator()
        tier = generator._determine_capital_tier(Decimal("1000000"))
        assert tier == CapitalTier.LARGE


class TestProfileGeneration:
    @pytest.mark.asyncio
    async def test_generate_profile_capital_maximization(self):
        """Test profile generation for capital maximization objective."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_001",
            capital_initial=Decimal("250000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("1000"),
            time_horizon_months=12,
        )

        result = await generator.generate(request)

        assert result.success
        assert result.profile is not None
        assert result.profile.objective == InvestmentObjective.MAXIMIZAR_CAPITAL
        assert result.profile.capital_tier == CapitalTier.MEDIUM

    @pytest.mark.asyncio
    async def test_generate_profile_capital_preservation(self):
        """Test profile generation for capital preservation objective."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_002",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.CAPITAL_PRESERVATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("200"),
            time_horizon_months=24,
        )

        result = await generator.generate(request)

        assert result.success
        assert result.profile is not None
        assert result.profile.objective == InvestmentObjective.CAPITAL_PRESERVATION
        assert result.profile.risk_profile == RiskProfile.CONSERVATIVE
        assert result.profile.max_leverage == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_generate_profile_income_generation(self):
        """Test profile generation for income generation objective."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_003",
            capital_initial=Decimal("500000"),
            objective=InvestmentObjective.INCOME_GENERATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("1500"),
            time_horizon_months=36,
        )

        result = await generator.generate(request)

        assert result.success
        assert result.profile is not None
        assert result.profile.objective == InvestmentObjective.INCOME_GENERATION

    @pytest.mark.asyncio
    async def test_generate_profile_micro_capital(self):
        """Test profile generation with micro capital."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_004",
            capital_initial=Decimal("15000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("100"),
            time_horizon_months=12,
        )

        result = await generator.generate(request)

        assert result.success
        assert result.profile is not None
        assert result.profile.capital_tier == CapitalTier.MICRO

    @pytest.mark.asyncio
    async def test_generate_profile_large_capital(self):
        """Test profile generation with large capital."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_005",
            capital_initial=Decimal("2000000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("5000"),
            time_horizon_months=24,
        )

        result = await generator.generate(request)

        assert result.success
        assert result.profile is not None
        assert result.profile.capital_tier == CapitalTier.LARGE

    @pytest.mark.asyncio
    async def test_all_objectives_supported(self):
        """Test that all investment objectives are supported."""
        generator = ProfileGenerator()
        objectives = [
            InvestmentObjective.MAXIMIZAR_CAPITAL,
            InvestmentObjective.MAXIMIZAR_DIVIDENDOS,
            InvestmentObjective.CAPITAL_PRESERVATION,
            InvestmentObjective.BALANCED_GROWTH,
            InvestmentObjective.INCOME_GENERATION,
        ]

        for objective in objectives:
            request = ProfileGenerationRequest(
                input_id=f"test_{objective.value}",
                capital_initial=Decimal("200000"),
                objective=objective,
                risk_tolerance=RiskProfile.MODERATE,
                target_monthly_return_eur=Decimal("800"),
                time_horizon_months=12,
            )

            result = await generator.generate(request)
            assert result.success
            assert result.profile.objective == objective


class TestProfileValidation:
    def test_investment_profile_validation(self):
        """Test investment profile validation."""
        profile = InvestmentProfile(
            input_id="test",
            capital_tier=CapitalTier.MEDIUM,
            initial_capital=Decimal("250000"),
            min_monthly_return_eur=Decimal("1000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_profile=RiskProfile.MODERATE,
            time_horizon_months=12,
        )

        assert profile.initial_capital > Decimal("0")
        assert profile.max_leverage >= Decimal("1.0")
        assert profile.max_leverage <= Decimal("3.0")

    def test_investment_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = InvestmentProfile(
            input_id="test",
            capital_tier=CapitalTier.MEDIUM,
            initial_capital=Decimal("250000"),
            min_monthly_return_eur=Decimal("1000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_profile=RiskProfile.MODERATE,
            time_horizon_months=12,
        )

        profile_dict = profile.to_dict()
        assert profile_dict["input_id"] == "test"
        assert profile_dict["capital_tier"] == "medium"
        assert profile_dict["objective"] == "balanced_growth"

    def test_profile_with_invalid_capital(self):
        """Test profile validation with invalid capital."""
        with pytest.raises(ValueError):
            InvestmentProfile(
                input_id="test",
                capital_tier=CapitalTier.MEDIUM,
                initial_capital=Decimal("-100"),
                min_monthly_return_eur=Decimal("1000"),
                objective=InvestmentObjective.BALANCED_GROWTH,
                risk_profile=RiskProfile.MODERATE,
                time_horizon_months=12,
            )


class TestProfileHistory:
    @pytest.mark.asyncio
    async def test_generation_history_tracking(self):
        """Test that generation history is tracked."""
        generator = ProfileGenerator()

        for i in range(3):
            request = ProfileGenerationRequest(
                input_id=f"test_{i}",
                capital_initial=Decimal("200000"),
                objective=InvestmentObjective.BALANCED_GROWTH,
                risk_tolerance=RiskProfile.MODERATE,
                target_monthly_return_eur=Decimal("1000"),
                time_horizon_months=12,
            )
            await generator.generate(request)

        history = await generator.get_generation_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_profile_caching(self):
        """Test that generated profiles are cached."""
        generator = ProfileGenerator()
        request = ProfileGenerationRequest(
            input_id="test_cache",
            capital_initial=Decimal("200000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("1000"),
            time_horizon_months=12,
        )

        result = await generator.generate(request)
        if result.success and result.profile:
            profile_id = result.profile.profile_id

            cached_profile = await generator.get_profile(profile_id)
            assert cached_profile is not None
            assert cached_profile.profile_id == profile_id

    def test_generator_status(self):
        """Test generator status reporting."""
        generator = ProfileGenerator()
        status = generator.get_generator_status()

        assert "total_profiles_generated" in status
        assert "profiles_cached" in status
        assert "success_rate" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
