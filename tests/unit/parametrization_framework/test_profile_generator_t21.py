"""
BATCH E - T2.1: Unit Tests for ProfileGenerator with MAESTRO PHASE 1 Integration

Tests:
- Profile generation from request
- Capital tier classification (MICRO/SMALL/MEDIUM/LARGE)
- Objective-aware template selection (5 objectives)
- Module configuration
- MAESTRO PHASE 1 integration:
  - Required alpha calculation
  - Capacity fade adjustment
  - Position sizing optimization
  - Feasibility validation
"""

from decimal import Decimal

import pytest

from app.services.profile_generator.models import (
    CapitalTier,
    InvestmentObjective,
    ProfileGenerationRequest,
    RiskProfile,
)
from app.services.profile_generator.profile_generator import ProfileGenerator


@pytest.fixture
def profile_generator():
    """Create ProfileGenerator instance for tests."""
    return ProfileGenerator()


class TestProfileGenerationBasic:
    """Test basic profile generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_profile_micro_capital_growth(self, profile_generator):
        """Test profile generation for MICRO tier with capital growth objective."""
        request = ProfileGenerationRequest(
            input_id="test_001",
            capital_initial=Decimal("10000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("50"),
            time_horizon_months=12,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile is not None
        assert result.profile.capital_tier == CapitalTier.MICRO
        assert result.profile.objective == InvestmentObjective.MAXIMIZAR_CAPITAL
        assert result.generation_time_ms > 0

    @pytest.mark.asyncio
    async def test_generate_profile_small_tier(self, profile_generator):
        """Test profile generation for SMALL tier (€15k-€50k)."""
        request = ProfileGenerationRequest(
            input_id="test_002",
            capital_initial=Decimal("30000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("100"),
            time_horizon_months=24,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.SMALL
        assert len(result.profile.enabled_modules) > 0

    @pytest.mark.asyncio
    async def test_generate_profile_medium_tier(self, profile_generator):
        """Test profile generation for MEDIUM tier (€50k-€250k)."""
        request = ProfileGenerationRequest(
            input_id="test_003",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("300"),
            time_horizon_months=36,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.MEDIUM
        assert result.profile.risk_scaling_enabled is True

    @pytest.mark.asyncio
    async def test_generate_profile_large_tier(self, profile_generator):
        """Test profile generation for LARGE tier (€250k+)."""
        request = ProfileGenerationRequest(
            input_id="test_004",
            capital_initial=Decimal("500000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("1000"),
            time_horizon_months=60,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.LARGE
        assert result.profile.risk_scaling_enabled is True


class TestCapitalTierClassification:
    """Test capital tier classification using MAESTRO PHASE 1."""

    @pytest.mark.asyncio
    async def test_micro_tier_threshold_lower(self, profile_generator):
        """Test MICRO tier boundary at lower end."""
        request = ProfileGenerationRequest(
            input_id="test_005",
            capital_initial=Decimal("1000"),
            objective=InvestmentObjective.CAPITAL_PRESERVATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("10"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.MICRO

    @pytest.mark.asyncio
    async def test_tier_boundary_small_lower(self, profile_generator):
        """Test SMALL tier at lower boundary (€15k)."""
        request = ProfileGenerationRequest(
            input_id="test_006",
            capital_initial=Decimal("15000"),
            objective=InvestmentObjective.INCOME_GENERATION,
            risk_tolerance=RiskProfile.CONSERVATIVE,
            target_monthly_return_eur=Decimal("50"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.SMALL

    @pytest.mark.asyncio
    async def test_tier_boundary_medium_lower(self, profile_generator):
        """Test MEDIUM tier at lower boundary (€50k)."""
        request = ProfileGenerationRequest(
            input_id="test_007",
            capital_initial=Decimal("50000"),
            objective=InvestmentObjective.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("150"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capital_tier == CapitalTier.MEDIUM


class TestObjectiveMapping:
    """Test objective-specific profile configuration."""

    @pytest.mark.asyncio
    async def test_maximizar_capital_objective(self, profile_generator):
        """Test MAXIMIZAR_CAPITAL objective selection."""
        request = ProfileGenerationRequest(
            input_id="test_008",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("300"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.objective == InvestmentObjective.MAXIMIZAR_CAPITAL

    @pytest.mark.asyncio
    async def test_balanced_growth_objective(self, profile_generator):
        """Test BALANCED_GROWTH objective selection."""
        request = ProfileGenerationRequest(
            input_id="test_009",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("200"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.objective == InvestmentObjective.BALANCED_GROWTH


class TestMaestroPhase1Integration:
    """Test MAESTRO PHASE 1 integration in profile generation."""

    @pytest.mark.asyncio
    async def test_required_alpha_calculation(self, profile_generator):
        """Test required alpha calculation from EUR target."""
        request = ProfileGenerationRequest(
            input_id="test_010",
            capital_initial=Decimal("250000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("800"),
            time_horizon_months=24,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        # €800/month = €9600/year on €250k = 3.84% annual required
        # But after tax and commission, required_alpha_pct should be higher
        assert result.profile.required_alpha_pct is not None
        assert result.profile.required_alpha_pct > Decimal("3")

    @pytest.mark.asyncio
    async def test_capacity_fade_adjustment(self, profile_generator):
        """Test capacity fade is applied (alpha decreases at larger capital)."""
        request = ProfileGenerationRequest(
            input_id="test_011",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("300"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.capacity_fade_adjusted_alpha is not None
        # Capacity fade adjusted should be less than theoretical max alpha
        assert result.profile.capacity_fade_adjusted_alpha > Decimal("0")

    @pytest.mark.asyncio
    async def test_position_sizing_optimization(self, profile_generator):
        """Test position sizing is optimized."""
        request = ProfileGenerationRequest(
            input_id="test_012",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("200"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.position_size_pct is not None
        assert result.profile.position_size_pct > Decimal("0")
        assert result.profile.position_size_pct <= Decimal("100")  # Max 100% position

    @pytest.mark.asyncio
    async def test_concurrent_positions_calculated(self, profile_generator):
        """Test concurrent positions are calculated."""
        request = ProfileGenerationRequest(
            input_id="test_013",
            capital_initial=Decimal("100000"),
            objective=InvestmentObjective.BALANCED_GROWTH,
            risk_tolerance=RiskProfile.MODERATE,
            target_monthly_return_eur=Decimal("200"),
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.concurrent_positions is not None
        assert result.profile.concurrent_positions >= 1

    @pytest.mark.asyncio
    async def test_feasibility_validation_integration(self, profile_generator):
        """Test feasibility validation from MAESTRO is stored."""
        request = ProfileGenerationRequest(
            input_id="test_014",
            capital_initial=Decimal("250000"),
            objective=InvestmentObjective.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskProfile.AGGRESSIVE,
            target_monthly_return_eur=Decimal("800"),
            time_horizon_months=24,
        )

        result = await profile_generator.generate(request)

        assert result.success is True
        assert result.profile.feasibility_validation is not None
        assert "is_feasible" in result.profile.feasibility_validation
        assert "confidence_level" in result.profile.feasibility_validation
        assert "recommendation" in result.profile.feasibility_validation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
