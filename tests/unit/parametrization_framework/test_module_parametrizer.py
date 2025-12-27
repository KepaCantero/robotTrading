"""
T3.1: ModuleParametrizer Tests

Tests for ModuleParametrizer, module parameter generation, and capital-tier gating.
"""

from decimal import Decimal

import pytest

from app.services.module_parametrizer import (
    ModuleParametrizer,
    ParameterizationRequest,
    get_module_parametrizer,
)


# MODULE PARAMETRIZER INITIALIZATION TESTS
class TestModuleParametrizerInitialization:
    def test_parametrizer_init(self):
        """Test module parametrizer initialization."""
        parametrizer = ModuleParametrizer()
        assert len(parametrizer.parametrization_history) == 0
        assert len(parametrizer.module_templates) > 0

    def test_parametrizer_singleton(self):
        """Test module parametrizer singleton pattern."""
        p1 = get_module_parametrizer()
        p2 = get_module_parametrizer()
        assert p1 is p2

    def test_template_loading(self):
        """Test that module templates are loaded."""
        parametrizer = ModuleParametrizer()
        assert "modules" in parametrizer.module_templates
        modules = parametrizer.module_templates.get("modules", {})
        assert len(modules) > 0
        # Verify some known modules are present
        module_names = list(modules.keys())
        assert "momentum_modular" in module_names
        assert "mean_reversion_modular" in module_names


# CAPITAL GATING TESTS
class TestCapitalGating:
    def test_capital_gating_micro_tier(self):
        """Test capital gating for micro tier (€15k)."""
        parametrizer = ModuleParametrizer()
        enabled_modules = ["momentum_modular", "ml_ensemble"]
        capital = Decimal("15000")

        gated_modules, disabled_modules = parametrizer._apply_capital_gating(
            enabled_modules, capital
        )

        # ml_ensemble requires €500k, so should be disabled for micro
        assert "momentum_modular" in gated_modules
        assert "ml_ensemble" in disabled_modules
        assert len(gated_modules) == 1
        assert len(disabled_modules) == 1

    def test_capital_gating_small_tier(self):
        """Test capital gating for small tier (€50k)."""
        parametrizer = ModuleParametrizer()
        enabled_modules = ["momentum_modular", "mean_reversion_modular"]
        capital = Decimal("50000")

        gated_modules, disabled_modules = parametrizer._apply_capital_gating(
            enabled_modules, capital
        )

        # Both should be allowed for small tier
        assert len(gated_modules) == 2
        assert len(disabled_modules) == 0

    def test_capital_gating_medium_tier(self):
        """Test capital gating for medium tier (€250k)."""
        parametrizer = ModuleParametrizer()
        enabled_modules = [
            "momentum_modular",
            "pairs_trading_modular",
            "ml_ensemble",  # Requires €500k
        ]
        capital = Decimal("250000")

        gated_modules, disabled_modules = parametrizer._apply_capital_gating(
            enabled_modules, capital
        )

        # ml_ensemble should be disabled
        assert len(gated_modules) == 2
        assert len(disabled_modules) == 1
        assert "ml_ensemble" in disabled_modules

    def test_capital_gating_large_tier(self):
        """Test capital gating for large tier (€1M)."""
        parametrizer = ModuleParametrizer()
        enabled_modules = [
            "momentum_modular",
            "mean_reversion_modular",
            "ml_ensemble",
        ]
        capital = Decimal("1000000")

        gated_modules, disabled_modules = parametrizer._apply_capital_gating(
            enabled_modules, capital
        )

        # All should be allowed
        assert len(gated_modules) == 3
        assert len(disabled_modules) == 0

    def test_capital_gating_edge_case(self):
        """Test capital gating at exact threshold."""
        parametrizer = ModuleParametrizer()
        # Test at the exact minimum capital for ml_ensemble (€500k)
        enabled_modules = ["ml_ensemble"]
        capital = Decimal("500000")

        gated_modules, disabled_modules = parametrizer._apply_capital_gating(
            enabled_modules, capital
        )

        # Should be allowed at exact threshold
        assert "ml_ensemble" in gated_modules
        assert len(disabled_modules) == 0


# MODULE PARAMETRIZATION TESTS
class TestModuleParametrization:
    @pytest.mark.asyncio
    async def test_parametrize_momentum_micro(self):
        """Test parametrization for momentum module on micro tier."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_mom_micro",
            input_id="user_001",
            capital_tier="micro",
            objective="maximizar_capital",
            risk_profile="moderate",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("15000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        assert result.parameter_set is not None
        assert "momentum_modular" in result.parameter_set.module_parameters
        config = result.parameter_set.module_parameters["momentum_modular"]
        assert config.enabled
        assert config.priority == 0
        assert config.max_position_size == Decimal("0.08")  # Micro tier is conservative

    @pytest.mark.asyncio
    async def test_parametrize_momentum_large(self):
        """Test parametrization for momentum module on large tier."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_mom_large",
            input_id="user_002",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("1000000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        assert result.parameter_set is not None
        config = result.parameter_set.module_parameters["momentum_modular"]
        assert config.max_position_size == Decimal("0.15")  # Large tier is more aggressive

    @pytest.mark.asyncio
    async def test_parametrize_multiple_modules(self):
        """Test parametrization for multiple modules."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_multi",
            input_id="user_003",
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=[
                "momentum_modular",
                "mean_reversion_modular",
                "pairs_trading_modular",
            ],
            initial_capital=Decimal("250000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        assert result.parameter_set.total_modules_enabled == 3
        assert len(result.parameter_set.module_parameters) == 3
        assert all(c.enabled for c in result.parameter_set.module_parameters.values())

    @pytest.mark.asyncio
    async def test_parametrize_with_capital_gating(self):
        """Test parametrization with capital gating applied."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_gate",
            input_id="user_004",
            capital_tier="micro",
            objective="maximizar_capital",
            risk_profile="moderate",
            enabled_modules=["momentum_modular", "ml_ensemble"],  # ml_ensemble requires €500k
            initial_capital=Decimal("20000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        assert result.parameter_set.total_modules_enabled == 1
        assert "momentum_modular" in result.parameter_set.module_parameters
        assert "ml_ensemble" not in result.parameter_set.module_parameters
        assert "ml_ensemble" in result.disabled_modules

    @pytest.mark.asyncio
    async def test_parametrize_all_tiers(self):
        """Test parametrization for all capital tiers."""
        parametrizer = ModuleParametrizer()

        tiers_and_capitals = [
            ("micro", Decimal("15000")),
            ("small", Decimal("50000")),
            ("medium", Decimal("250000")),
            ("large", Decimal("1000000")),
        ]

        for tier, capital in tiers_and_capitals:
            request = ParameterizationRequest(
                profile_id=f"test_{tier}",
                input_id=f"user_{tier}",
                capital_tier=tier,
                objective="balanced_growth",
                risk_profile="moderate",
                enabled_modules=["momentum_modular"],
                initial_capital=capital,
            )

            result = await parametrizer.parametrize(request)
            assert result.success
            assert result.parameter_set.total_modules_enabled >= 1


# PARAMETER SET VALIDATION TESTS
class TestParameterSetValidation:
    @pytest.mark.asyncio
    async def test_parameter_set_structure(self):
        """Test parameter set structure and aggregates."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_struct",
            input_id="user_005",
            capital_tier="medium",
            objective="income_generation",
            risk_profile="conservative",
            enabled_modules=["dividend_screener", "covered_call_writer"],
            initial_capital=Decimal("250000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        param_set = result.parameter_set
        assert param_set.profile_id == "test_struct"
        assert param_set.input_id == "user_005"
        assert param_set.capital_tier == "medium"
        assert param_set.objective == "income_generation"
        assert param_set.total_modules_enabled >= 1
        assert param_set.total_max_exposure > Decimal("0")

    @pytest.mark.asyncio
    async def test_module_priorities(self):
        """Test module priority assignment."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_priority",
            input_id="user_006",
            capital_tier="large",
            objective="maximizar_capital",
            risk_profile="aggressive",
            enabled_modules=[
                "momentum_modular",
                "mean_reversion_modular",
                "pairs_trading_modular",
            ],
            initial_capital=Decimal("1000000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        param_set = result.parameter_set
        # Check that priorities are assigned sequentially
        priorities = [c.priority for c in param_set.module_parameters.values()]
        assert 0 in priorities  # First module should have priority 0

    @pytest.mark.asyncio
    async def test_parameter_set_to_dict(self):
        """Test converting parameter set to dictionary."""
        parametrizer = ModuleParametrizer()
        request = ParameterizationRequest(
            profile_id="test_dict",
            input_id="user_007",
            capital_tier="small",
            objective="balanced_growth",
            risk_profile="moderate",
            enabled_modules=["momentum_modular"],
            initial_capital=Decimal("50000"),
        )

        result = await parametrizer.parametrize(request)

        assert result.success
        param_dict = result.parameter_set.to_dict()
        assert param_dict["profile_id"] == "test_dict"
        assert "module_parameters" in param_dict
        assert len(param_dict["module_parameters"]) >= 1


# HISTORY & STATUS TESTS
class TestParametrizationHistory:
    @pytest.mark.asyncio
    async def test_parametrization_history_tracking(self):
        """Test that parametrization history is tracked."""
        parametrizer = ModuleParametrizer()

        for i in range(3):
            request = ParameterizationRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                capital_tier="medium",
                objective="balanced_growth",
                risk_profile="moderate",
                enabled_modules=["momentum_modular"],
                initial_capital=Decimal("250000"),
            )
            await parametrizer.parametrize(request)

        history = await parametrizer.get_parametrization_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_parametrization_history_limit(self):
        """Test parametrization history with limit."""
        parametrizer = ModuleParametrizer()

        for i in range(5):
            request = ParameterizationRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                capital_tier="medium",
                objective="balanced_growth",
                risk_profile="moderate",
                enabled_modules=["momentum_modular"],
                initial_capital=Decimal("250000"),
            )
            await parametrizer.parametrize(request)

        history = await parametrizer.get_parametrization_history(limit=2)
        assert len(history) == 2

    def test_parametrizer_status(self):
        """Test parametrizer status reporting."""
        parametrizer = ModuleParametrizer()
        status = parametrizer.get_parametrizer_status()

        assert "total_parametrizations" in status
        assert "successful_parametrizations" in status
        assert "success_rate" in status
        assert "total_modules_available" in status
        assert status["total_modules_available"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
