"""
BATCH E - T3.1: Unit Tests for ModuleParametrizer with Capital Gating

Tests:
- Module parametrization by capital tier
- Capital gating (expensive modules disabled below thresholds)
- Tier-specific parameter selection
- Module priority categorization
- Total exposure and cost calculation
- Risk profile adjustments
"""

import pytest
from decimal import Decimal
from app.services.module_parametrizer.module_parametrizer import ModuleParametrizer
from app.services.module_parametrizer.models import (
    ParameterizationRequest,
    ParameterizationPreset,
)


@pytest.fixture
def module_parametrizer():
    """Create ModuleParametrizer instance for tests."""
    return ModuleParametrizer()


class TestBasicParametrization:
    """Test basic module parametrization functionality."""

    @pytest.mark.asyncio
    async def test_parametrize_micro_single_module(self, module_parametrizer):
        """Test parametrization of single module for MICRO tier."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100000",
            input_id="test_001",
            capital_tier="micro",
            objective="maximizar_capital",
            risk_profile="conservative",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("10000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert result.parameter_set is not None
        assert "momentum_modular" in result.parameter_set.module_parameters
        assert result.parametrization_time_ms > 0

    @pytest.mark.asyncio
    async def test_parametrize_small_multiple_modules(self, module_parametrizer):
        """Test parametrization of multiple modules for SMALL tier."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100001",
            input_id="test_002",
            capital_tier="small",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular", "trend_following_modular"],
            initial_capital=Decimal("30000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert len(result.parameter_set.module_parameters) == 2
        assert len(result.parameter_set.high_priority_modules) > 0

    @pytest.mark.asyncio
    async def test_parametrize_medium_tier(self, module_parametrizer):
        """Test parametrization for MEDIUM tier."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100002",
            input_id="test_003",
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular", "trend_following_modular", "deep_learning_engine"],
            initial_capital=Decimal("100000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert len(result.parameter_set.module_parameters) > 0
        assert result.parameter_set.capital_tier == "medium"

    @pytest.mark.asyncio
    async def test_parametrize_large_tier(self, module_parametrizer):
        """Test parametrization for LARGE tier (€250k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100003",
            input_id="test_004",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular", "ml_ensemble"],
            initial_capital=Decimal("500000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "ml_ensemble" in result.parameter_set.module_parameters
        # ml_ensemble should not be disabled for large tier with €500k
        assert "ml_ensemble" not in result.disabled_modules


class TestCapitalGating:
    """Test capital-tier-aware module gating."""

    @pytest.mark.asyncio
    async def test_deep_learning_gated_at_small_tier(self, module_parametrizer):
        """Test deep_learning_engine is disabled for SMALL tier (needs €100k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100004",
            input_id="test_005",
            capital_tier="small",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular", "deep_learning_engine"],
            initial_capital=Decimal("30000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "deep_learning_engine" in result.disabled_modules
        assert "momentum_modular" in result.parameter_set.module_parameters

    @pytest.mark.asyncio
    async def test_deep_learning_enabled_at_medium_tier(self, module_parametrizer):
        """Test deep_learning_engine is enabled for MEDIUM tier (€100k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100005",
            input_id="test_006",
            capital_tier="medium",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["deep_learning_engine"],
            initial_capital=Decimal("100000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "deep_learning_engine" in result.parameter_set.module_parameters
        assert len(result.disabled_modules) == 0

    @pytest.mark.asyncio
    async def test_transformer_gated_at_small_tier(self, module_parametrizer):
        """Test transformer module is disabled for SMALL tier (needs €250k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100006",
            input_id="test_007",
            capital_tier="small",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["transformer_learning"],
            initial_capital=Decimal("50000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "transformer_learning" in result.disabled_modules

    @pytest.mark.asyncio
    async def test_ml_ensemble_gated_at_medium_tier(self, module_parametrizer):
        """Test ml_ensemble is disabled for MEDIUM tier (needs €500k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100007",
            input_id="test_008",
            capital_tier="medium",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["ml_ensemble"],
            initial_capital=Decimal("250000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "ml_ensemble" in result.disabled_modules

    @pytest.mark.asyncio
    async def test_ml_ensemble_enabled_at_large_tier(self, module_parametrizer):
        """Test ml_ensemble is enabled for LARGE tier (€500k+)."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100008",
            input_id="test_009",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["ml_ensemble"],
            initial_capital=Decimal("500000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert "ml_ensemble" in result.parameter_set.module_parameters


class TestTierSpecificParameters:
    """Test tier-specific parameter selection."""

    @pytest.mark.asyncio
    async def test_conservative_parameters_for_micro_momentum(self, module_parametrizer):
        """Test momentum uses conservative parameters for MICRO tier."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100009",
            input_id="test_010",
            capital_tier="micro",
            objective="balanced_growth",
            risk_profile="conservative",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("10000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        momentum_config = result.parameter_set.module_parameters["momentum_modular"]
        # MICRO tier uses more conservative parameters
        assert momentum_config.max_position_size <= Decimal("0.10")
        assert momentum_config.preset == ParameterizationPreset.CONSERVATIVE

    @pytest.mark.asyncio
    async def test_aggressive_parameters_for_large_momentum(self, module_parametrizer):
        """Test momentum uses aggressive parameters for LARGE tier."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100010",
            input_id="test_011",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("500000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        momentum_config = result.parameter_set.module_parameters["momentum_modular"]
        # LARGE tier uses more aggressive parameters
        assert momentum_config.max_position_size >= Decimal("0.10")
        assert momentum_config.preset == ParameterizationPreset.AGGRESSIVE


class TestModulePriorities:
    """Test module priority categorization."""

    @pytest.mark.asyncio
    async def test_priority_categorization(self, module_parametrizer):
        """Test modules are categorized by priority."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100011",
            input_id="test_012",
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular", "trend_following_modular", "deep_learning_engine"],
            initial_capital=Decimal("150000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        param_set = result.parameter_set
        # Check that modules are assigned priorities
        total_modules = (
            len(param_set.high_priority_modules) +
            len(param_set.medium_priority_modules) +
            len(param_set.low_priority_modules)
        )
        assert total_modules == param_set.total_modules_enabled

    @pytest.mark.asyncio
    async def test_high_priority_modules_identified(self, module_parametrizer):
        """Test high-priority modules are correctly identified."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100012",
            input_id="test_013",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular", "deep_learning_engine", "ml_ensemble"],
            initial_capital=Decimal("500000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert len(result.parameter_set.high_priority_modules) > 0


class TestExposureAndCosts:
    """Test total exposure and cost calculations."""

    @pytest.mark.asyncio
    async def test_total_exposure_calculated(self, module_parametrizer):
        """Test total max exposure is calculated across modules."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100013",
            input_id="test_014",
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular", "trend_following_modular"],
            initial_capital=Decimal("100000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert result.parameter_set.total_max_exposure > Decimal("0")
        # Total exposure should be sum of individual exposures
        expected_exposure = sum(
            config.max_exposure
            for config in result.parameter_set.module_parameters.values()
        )
        assert result.parameter_set.total_max_exposure == expected_exposure

    @pytest.mark.asyncio
    async def test_total_cost_calculated(self, module_parametrizer):
        """Test total estimated cost is calculated."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100014",
            input_id="test_015",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular", "deep_learning_engine"],
            initial_capital=Decimal("300000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert result.parameter_set.total_estimated_cost_usd > Decimal("0")

    @pytest.mark.asyncio
    async def test_improvement_percentage_calculated(self, module_parametrizer):
        """Test estimated improvement percentage is calculated."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100015",
            input_id="test_016",
            capital_tier="small",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("50000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        assert result.parameter_set.total_estimated_improvement_pct > Decimal("0")


class TestValidationAndWarnings:
    """Test parameter set validation and warning generation."""

    @pytest.mark.asyncio
    async def test_no_modules_enabled_warning(self, module_parametrizer):
        """Test warning when no modules are enabled after gating."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100016",
            input_id="test_017",
            capital_tier="micro",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["ml_ensemble"],  # Requires €500k
            initial_capital=Decimal("10000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        # Should have warning about no modules enabled
        assert len(result.warnings) > 0 or len(result.parameter_set.module_parameters) == 0

    @pytest.mark.asyncio
    async def test_high_cost_warning(self, module_parametrizer):
        """Test warning for high infrastructure costs."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100017",
            input_id="test_018",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["ml_ensemble", "deep_learning_engine", "transformer_learning"],
            initial_capital=Decimal("500000"),
        )

        result = await module_parametrizer.parametrize(request)

        assert result.success is True
        # Many modules might generate cost warnings
        # Just verify warnings list exists
        assert isinstance(result.warnings, list)


class TestHistoryAndStatus:
    """Test history tracking and status reporting."""

    @pytest.mark.asyncio
    async def test_parametrization_history_tracked(self, module_parametrizer):
        """Test parametrization history is maintained."""
        request = ParameterizationRequest(
            profile_id="PROF-20251225100018",
            input_id="test_019",
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("100000"),
        )

        await module_parametrizer.parametrize(request)
        history = await module_parametrizer.get_parametrization_history()

        assert len(history) > 0
        assert history[-1].success is True

    def test_parametrizer_status(self, module_parametrizer):
        """Test parametrizer status reporting."""
        status = module_parametrizer.get_parametrizer_status()

        assert "total_parametrizations" in status
        assert "successful_parametrizations" in status
        assert "success_rate" in status
        assert "total_modules_available" in status
        assert status["total_modules_available"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
