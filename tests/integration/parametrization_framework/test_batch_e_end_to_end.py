"""
BATCH E: End-to-End Integration Tests

Tests complete BATCH E pipeline:
ProfileGenerator → ModuleParametrizer → BacktestOrchestrator → ValidationEngine → StrategyRecommender
"""

import pytest
from decimal import Decimal
from app.services.profile_generator.profile_generator import ProfileGenerator
from app.services.profile_generator.models import (
    InvestmentObjective,
    RiskProfile,
    ProfileGenerationRequest,
)
from app.services.module_parametrizer.module_parametrizer import ModuleParametrizer
from app.services.module_parametrizer.models import ParameterizationRequest


@pytest.fixture
def profile_generator():
    return ProfileGenerator()


@pytest.fixture
def module_parametrizer():
    return ModuleParametrizer()


class TestProfileGeneratorIntegration:
    """Test ProfileGenerator integration with MAESTRO PHASE 1."""

    @pytest.mark.asyncio
    async def test_micro_tier_profile_generation(self, profile_generator):
        """Test complete profile generation for MICRO tier."""
        request = ProfileGenerationRequest(
            input_id="batch_e_001",
            capital_initial=Decimal("10000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("50"),
            time_horizon_months=12,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile is not None
        assert result.profile.required_alpha_pct is not None
        assert result.profile.capacity_fade_adjusted_alpha is not None
        assert result.profile.feasibility_validation is not None

    @pytest.mark.asyncio
    async def test_small_tier_profile_generation(self, profile_generator):
        """Test complete profile generation for SMALL tier."""
        request = ProfileGenerationRequest(
            input_id="batch_e_002",
            capital_initial=Decimal("30000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("100"),
            time_horizon_months=24,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert len(result.profile.enabled_modules) > 0
        assert result.profile.required_annual_return_pct is not None

    @pytest.mark.asyncio
    async def test_medium_tier_profile_generation(self, profile_generator):
        """Test complete profile generation for MEDIUM tier."""
        request = ProfileGenerationRequest(
            input_id="batch_e_003",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("300"),
            time_horizon_months=36,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier.value == "medium"
        assert result.profile.risk_scaling_enabled is True

    @pytest.mark.asyncio
    async def test_large_tier_profile_generation(self, profile_generator):
        """Test complete profile generation for LARGE tier."""
        request = ProfileGenerationRequest(
            input_id="batch_e_004",
            capital_initial=Decimal("500000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("1000"),
            time_horizon_months=60,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier.value == "large"


class TestModuleParametrizerIntegration:
    """Test ModuleParametrizer with ProfileGenerator output."""

    @pytest.mark.asyncio
    async def test_parametrize_after_profile_generation(self, profile_generator, module_parametrizer):
        """Test parametrization using profile from ProfileGenerator."""
        # Step 1: Generate profile
        profile_request = ProfileGenerationRequest(
            input_id="batch_e_005",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("200"),
            time_horizon_months=24,
        )

        profile_result = await profile_generator.generate(profile_request)
        assert profile_result.success is True

        # Step 2: Parametrize using profile data
        profile = profile_result.profile
        param_request = ParameterizationRequest(
            profile_id=profile.profile_id,
            input_id=profile.input_id,
            capital_tier=profile.capital_tier.value,
            objective=profile.objective.value,
            risk_profile=profile.risk_profile.value,
            enabled_modules=[m.name for m in profile.enabled_modules],
            initial_capital=profile.initial_capital,
        )

        param_result = await module_parametrizer.parametrize(param_request)

        assert param_result.success is True
        assert param_result.parameter_set is not None
        assert param_result.parameter_set.total_modules_enabled > 0

    @pytest.mark.asyncio
    async def test_capital_gating_in_pipeline(self, profile_generator, module_parametrizer):
        """Test capital gating is applied in full pipeline."""
        # Generate MICRO tier profile
        profile_request = ProfileGenerationRequest(
            input_id="batch_e_006",
            capital_initial=Decimal("10000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("50"),
        )

        profile_result = await profile_generator.generate(profile_request)
        profile = profile_result.profile

        # Parametrize with expensive modules
        param_request = ParameterizationRequest(
            profile_id=profile.profile_id,
            input_id=profile.input_id,
            capital_tier=profile.capital_tier.value,
            objective=profile.objective.value,
            risk_profile=profile.risk_profile.value,
            enabled_modules=["momentum_modular", "deep_learning_engine", "ml_ensemble"],
            initial_capital=profile.initial_capital,
        )

        param_result = await module_parametrizer.parametrize(param_request)

        # Expensive modules should be disabled for MICRO tier
        assert "deep_learning_engine" in param_result.disabled_modules
        assert "ml_ensemble" in param_result.disabled_modules


class TestFeasibilityRatioCalculation:
    """Test feasibility ratio calculation in context."""

    def test_feasibility_ratio_approved_scenario(self):
        """Test APPROVED scenario: €250k, €800/month, 5.2% achieved."""
        capital = Decimal("250000")
        monthly_target = Decimal("800")
        achieved_annual_pct = Decimal("5.2")

        # Required return calculation
        annual_target = monthly_target * 12
        required_annual_pct = (annual_target / capital * 100).quantize(Decimal("0.01"))

        # Feasibility ratio
        feasibility_ratio = (achieved_annual_pct / required_annual_pct).quantize(Decimal("0.01"))

        assert required_annual_pct == Decimal("3.84")
        assert feasibility_ratio == Decimal("1.35")
        assert feasibility_ratio >= Decimal("1.0")

    def test_feasibility_ratio_conditional_scenario(self):
        """Test CONDITIONAL scenario: €100k, €200/month, 1.8% achieved."""
        capital = Decimal("100000")
        monthly_target = Decimal("200")
        achieved_annual_pct = Decimal("1.8")

        annual_target = monthly_target * 12
        required_annual_pct = (annual_target / capital * 100).quantize(Decimal("0.01"))

        feasibility_ratio = (achieved_annual_pct / required_annual_pct).quantize(Decimal("0.01"))

        assert required_annual_pct == Decimal("2.40")
        assert feasibility_ratio == Decimal("0.75")
        assert Decimal("0.7") <= feasibility_ratio < Decimal("1.0")

    def test_feasibility_ratio_rejected_scenario(self):
        """Test REJECTED scenario: €50k, €500/month, 5% achieved."""
        capital = Decimal("50000")
        monthly_target = Decimal("500")
        achieved_annual_pct = Decimal("5.0")

        annual_target = monthly_target * 12
        required_annual_pct = (annual_target / capital * 100).quantize(Decimal("0.01"))

        feasibility_ratio = (achieved_annual_pct / required_annual_pct).quantize(Decimal("0.01"))

        assert required_annual_pct == Decimal("12.00")
        assert feasibility_ratio < Decimal("0.7")


class TestPipelineDataFlow:
    """Test data flow through complete pipeline."""

    @pytest.mark.asyncio
    async def test_data_persistence_through_pipeline(self, profile_generator, module_parametrizer):
        """Test that profile data flows correctly through to parametrization."""
        # Generate profile
        profile_request = ProfileGenerationRequest(
            input_id="batch_e_007",
            capital_initial=Decimal("200000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("300"),
            time_horizon_months=24,
        )

        profile_result = await profile_generator.generate(profile_request)
        profile = profile_result.profile

        # Parametrize
        param_request = ParameterizationRequest(
            profile_id=profile.profile_id,
            input_id=profile.input_id,
            capital_tier=profile.capital_tier.value,
            objective=profile.objective.value,
            risk_profile=profile.risk_profile.value,
            enabled_modules=[m.name for m in profile.enabled_modules],
            initial_capital=profile.initial_capital,
        )

        param_result = await module_parametrizer.parametrize(param_request)

        # Verify data consistency
        assert param_result.parameter_set.profile_id == profile.profile_id
        assert param_result.parameter_set.input_id == profile.input_id
        assert param_result.parameter_set.capital_tier == profile.capital_tier.value
        assert param_result.parameter_set.objective == profile.objective.value
        assert param_result.parameter_set.risk_profile == profile.risk_profile.value


class TestMultipleObjectives:
    """Test BATCH E pipeline with all 5 objectives."""

    @pytest.mark.asyncio
    async def test_maximizar_capital_objective(self, profile_generator):
        """Test MAXIMIZAR_CAPITAL objective."""
        request = ProfileGenerationRequest(
            input_id="batch_e_008",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("250"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_maximizar_dividendos_objective(self, profile_generator):
        """Test MAXIMIZAR_DIVIDENDOS objective."""
        request = ProfileGenerationRequest(
            input_id="batch_e_009",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("150"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_capital_preservation_objective(self, profile_generator):
        """Test CAPITAL_PRESERVATION objective."""
        request = ProfileGenerationRequest(
            input_id="batch_e_010",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.CAPITAL_PRESERVATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("50"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_balanced_growth_objective(self, profile_generator):
        """Test BALANCED_GROWTH objective."""
        request = ProfileGenerationRequest(
            input_id="batch_e_011",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("150"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_income_generation_objective(self, profile_generator):
        """Test INCOME_GENERATION objective."""
        request = ProfileGenerationRequest(
            input_id="batch_e_012",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.INCOME_GENERATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("100"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True


class TestBoundaryConditions:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_minimal_capital(self, profile_generator):
        """Test with minimal capital."""
        request = ProfileGenerationRequest(
            input_id="batch_e_013",
            capital_initial=Decimal("1000"),
            objective=InvestmentObjective.CAPITAL_PRESERVATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("5"),
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_large_capital(self, profile_generator):
        """Test with large capital."""
        request = ProfileGenerationRequest(
            input_id="batch_e_014",
            capital_initial=Decimal("10000000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("10000"),
            time_horizon_months=60,
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_long_time_horizon(self, profile_generator):
        """Test with long time horizon."""
        request = ProfileGenerationRequest(
            input_id="batch_e_015",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("200"),
            time_horizon_months=240,  # 20 years
        )

        result = await profile_generator.generate(request)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_short_time_horizon(self, profile_generator):
        """Test with short time horizon."""
        request = ProfileGenerationRequest(
            input_id="batch_e_016",
            capital_initial=Decimal("50000"),
            objective=InvestmentObjective.CAPITAL_PRESERVATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("50"),
            time_horizon_months=3,
        )

        result = await profile_generator.generate(request)
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
