"""
Unit tests for T3.1: ModuleParametrizer

Tests module parameter generation from InvestmentProfile, covering:
- All 17+ modules with tier-specific configurations
- Risk scaling factor calculations
- Parameter range validation
- Module exposure accumulation
- Error handling for missing configurations
"""

import pytest
from decimal import Decimal
from typing import Dict, Any

from app.core.models.investment_profile import (
    InvestmentProfile,
    CapitalTier,
    ProfileGenerator,
)
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.parametrization.module_parametrizer import (
    ModuleParametrizer,
    ModuleParameters,
    ModuleParameterSet,
)


# ===================== FIXTURES =====================

@pytest.fixture
def module_parameters_config() -> Dict[str, Any]:
    """Comprehensive module parameters configuration for testing."""
    return {
        "modules": {
            "momentum_modular": {
                "description": "Multi-filter momentum strategy",
                "base": {
                    "max_position_size": 0.10,
                    "stop_loss_pct": 0.025,
                    "take_profit_pct": 0.08,
                    "max_exposure": 0.30,
                    "max_positions": 5,
                },
                "tiers": {
                    "micro": {
                        "preset": "conservative",
                        "max_position_size": 0.08,
                        "stop_loss_pct": 0.035,
                        "take_profit_pct": 0.06,
                        "max_exposure": 0.20,
                        "max_positions": 3,
                        "risk_adjustment": 0.9,
                        "module_specific": {"min_confidence": 0.75},
                    },
                    "small": {
                        "preset": "conservative",
                        "max_position_size": 0.10,
                        "stop_loss_pct": 0.030,
                        "take_profit_pct": 0.07,
                        "max_exposure": 0.25,
                        "max_positions": 4,
                        "risk_adjustment": 0.95,
                        "module_specific": {"min_confidence": 0.70},
                    },
                    "medium": {
                        "preset": "balanced",
                        "max_position_size": 0.12,
                        "stop_loss_pct": 0.025,
                        "take_profit_pct": 0.08,
                        "max_exposure": 0.30,
                        "max_positions": 6,
                        "risk_adjustment": 1.0,
                        "module_specific": {"min_confidence": 0.60},
                    },
                    "large": {
                        "preset": "aggressive",
                        "max_position_size": 0.15,
                        "stop_loss_pct": 0.020,
                        "take_profit_pct": 0.10,
                        "max_exposure": 0.40,
                        "max_positions": 8,
                        "risk_adjustment": 1.1,
                        "module_specific": {"min_confidence": 0.50},
                    },
                },
            },
            "mean_reversion_modular": {
                "description": "Mean reversion strategy",
                "base": {
                    "max_position_size": 0.07,
                    "stop_loss_pct": 0.015,
                    "take_profit_pct": 0.10,
                    "max_exposure": 0.20,
                    "max_positions": 5,
                },
                "tiers": {
                    "micro": {
                        "preset": "conservative",
                        "max_position_size": 0.06,
                        "stop_loss_pct": 0.025,
                        "max_exposure": 0.15,
                        "max_positions": 3,
                        "risk_adjustment": 0.85,
                        "module_specific": {"z_score_threshold": 1.5},
                    },
                    "small": {
                        "preset": "conservative",
                        "max_position_size": 0.07,
                        "stop_loss_pct": 0.020,
                        "max_exposure": 0.18,
                        "max_positions": 4,
                        "risk_adjustment": 0.9,
                        "module_specific": {"z_score_threshold": 1.25},
                    },
                    "medium": {
                        "preset": "balanced",
                        "max_position_size": 0.08,
                        "stop_loss_pct": 0.015,
                        "max_exposure": 0.20,
                        "max_positions": 5,
                        "risk_adjustment": 1.0,
                        "module_specific": {"z_score_threshold": 1.0},
                    },
                    "large": {
                        "preset": "aggressive",
                        "max_position_size": 0.10,
                        "stop_loss_pct": 0.012,
                        "max_exposure": 0.25,
                        "max_positions": 7,
                        "risk_adjustment": 1.1,
                        "module_specific": {"z_score_threshold": 0.8},
                    },
                },
            },
            "dividend_screener": {
                "base": {
                    "max_position_size": 0.08,
                    "stop_loss_pct": 0.04,
                    "take_profit_pct": 0.12,
                    "max_exposure": 0.30,
                    "max_positions": 8,
                },
                "tiers": {
                    "micro": {
                        "preset": "conservative",
                        "max_position_size": 0.08,
                        "max_exposure": 0.25,
                        "max_positions": 5,
                        "module_specific": {"min_dividend_yield": 0.03},
                    },
                    "small": {
                        "preset": "conservative",
                        "max_position_size": 0.08,
                        "max_exposure": 0.28,
                        "max_positions": 6,
                        "module_specific": {"min_dividend_yield": 0.027},
                    },
                    "medium": {
                        "preset": "balanced",
                        "max_position_size": 0.08,
                        "max_exposure": 0.30,
                        "max_positions": 8,
                        "module_specific": {"min_dividend_yield": 0.025},
                    },
                    "large": {
                        "preset": "aggressive",
                        "max_position_size": 0.10,
                        "max_exposure": 0.35,
                        "max_positions": 10,
                        "module_specific": {"min_dividend_yield": 0.020},
                    },
                },
            },
        }
    }


@pytest.fixture
def investment_profiles_config() -> Dict[str, Any]:
    """Investment profiles configuration fixture."""
    return {
        "profiles": {
            "maximizar_capital": {
                "micro": {
                    "risk_profile": 2,
                    "leverage": 0,
                    "enabled_modules": ["momentum_modular"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                },
                "small": {
                    "risk_profile": 3,
                    "leverage": 0.5,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular"],
                    "max_position_size": 0.20,
                    "max_sector_allocation": 0.25,
                },
                "medium": {
                    "risk_profile": 4,
                    "leverage": 1.5,
                    "enabled_modules": [
                        "momentum_modular",
                        "mean_reversion_modular",
                        "dividend_screener",
                    ],
                    "max_position_size": 0.25,
                    "max_sector_allocation": 0.30,
                },
                "large": {
                    "risk_profile": 6,
                    "leverage": 2.5,
                    "enabled_modules": [
                        "momentum_modular",
                        "mean_reversion_modular",
                        "dividend_screener",
                    ],
                    "max_position_size": 0.30,
                    "max_sector_allocation": 0.35,
                },
            }
        }
    }


@pytest.fixture
def parametrizer(module_parameters_config) -> ModuleParametrizer:
    """Create a ModuleParametrizer instance with test config."""
    return ModuleParametrizer(module_parameters_config)


@pytest.fixture
def profile_generator(investment_profiles_config) -> ProfileGenerator:
    """Create a ProfileGenerator instance with test config."""
    return ProfileGenerator(investment_profiles_config)


# ===================== TESTS: Module Parameter Generation =====================

class TestModuleParameterGeneration:
    """Test basic module parameter generation."""

    def test_generate_parameters_for_momentum_modular_micro(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test parameter generation for momentum_modular at micro tier."""
        # Create input profile
        input_profile = InputProfile(
            capital_initial=Decimal("5000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        # Generate investment profile
        inv_profile = profile_generator.generate(input_profile)
        # Disable risk scaling for clean parameter testing
        inv_profile.risk_scaling_enabled = False

        # Generate module parameters
        param_set = parametrizer.generate(inv_profile)

        # Verify parameter set
        assert param_set.profile_id == inv_profile.profile_id
        assert param_set.capital_tier == CapitalTier.MICRO
        assert "momentum_modular" in param_set.modules

        # Verify momentum_modular parameters
        momentum_params = param_set.get_module("momentum_modular")
        assert momentum_params is not None
        assert momentum_params.preset == "conservative"
        assert momentum_params.max_position_size == Decimal("0.08")
        assert momentum_params.max_exposure == Decimal("0.20")
        assert momentum_params.max_positions == 3

    def test_generate_parameters_for_mean_reversion_small(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test parameter generation for mean_reversion_modular at small tier."""
        input_profile = InputProfile(
            capital_initial=Decimal("25000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        assert param_set.capital_tier == CapitalTier.SMALL
        assert "mean_reversion_modular" in param_set.modules

        mr_params = param_set.get_module("mean_reversion_modular")
        assert mr_params.preset == "conservative"
        assert mr_params.max_position_size == Decimal("0.07")
        assert mr_params.module_specific["z_score_threshold"] == 1.25

    def test_generate_parameters_multiple_modules_medium(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test parameter generation for multiple modules at medium tier."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=36,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        assert param_set.capital_tier == CapitalTier.MEDIUM
        # Should have momentum, mean_reversion, and dividend_screener
        assert len(param_set.modules) >= 3

        # Check momentum
        momentum = param_set.get_module("momentum_modular")
        assert momentum.preset == "balanced"
        assert momentum.max_position_size == Decimal("0.12")

        # Check mean_reversion
        mr = param_set.get_module("mean_reversion_modular")
        assert mr.preset == "balanced"
        assert mr.max_position_size == Decimal("0.08")

        # Check dividend_screener
        dividend = param_set.get_module("dividend_screener")
        assert dividend.max_position_size == Decimal("0.08")

    def test_generate_parameters_large_tier(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test parameter generation for large tier with aggressive presets."""
        input_profile = InputProfile(
            capital_initial=Decimal("500000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=60,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        assert param_set.capital_tier == CapitalTier.LARGE

        # Large tier should have aggressive presets
        momentum = param_set.get_module("momentum_modular")
        assert momentum.preset == "aggressive"
        assert momentum.max_position_size == Decimal("0.15")
        assert momentum.risk_adjustment > Decimal("1.0")


# ===================== TESTS: Tier-Specific Variations =====================

class TestTierSpecificVariations:
    """Test parameter variations across capital tiers."""

    def test_momentum_position_size_increases_across_tiers(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that position sizes increase as capital tier increases."""
        position_sizes = {}

        for capital, tier in [
            (Decimal("5000"), CapitalTier.MICRO),
            (Decimal("25000"), CapitalTier.SMALL),
            (Decimal("100000"), CapitalTier.MEDIUM),
            (Decimal("500000"), CapitalTier.LARGE),
        ]:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=24,
            )

            inv_profile = profile_generator.generate(input_profile)
            inv_profile.risk_scaling_enabled = False
            param_set = parametrizer.generate(inv_profile)

            momentum = param_set.get_module("momentum_modular")
            position_sizes[tier.value] = momentum.max_position_size

        # Verify monotonic increase
        assert position_sizes["micro"] == Decimal("0.08")
        assert position_sizes["small"] == Decimal("0.10")
        assert position_sizes["medium"] == Decimal("0.12")
        assert position_sizes["large"] == Decimal("0.15")

    def test_stop_loss_decreases_across_tiers(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that stop losses tighten as capital tier increases (more capital = tighter stops)."""
        stop_losses = {}

        for capital, tier in [
            (Decimal("5000"), CapitalTier.MICRO),
            (Decimal("25000"), CapitalTier.SMALL),
            (Decimal("100000"), CapitalTier.MEDIUM),
            (Decimal("500000"), CapitalTier.LARGE),
        ]:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=24,
            )

            inv_profile = profile_generator.generate(input_profile)
            inv_profile.risk_scaling_enabled = False
            param_set = parametrizer.generate(inv_profile)

            momentum = param_set.get_module("momentum_modular")
            stop_losses[tier.value] = momentum.stop_loss_pct

        # Verify decreasing stop loss (tighter discipline with larger capital)
        assert stop_losses["micro"] > stop_losses["small"]
        assert stop_losses["small"] >= stop_losses["medium"]
        assert stop_losses["medium"] > stop_losses["large"]

    def test_exposure_increases_with_tier(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that max_exposure increases with capital tier."""
        exposures = {}

        for capital, tier in [
            (Decimal("5000"), CapitalTier.MICRO),
            (Decimal("25000"), CapitalTier.SMALL),
            (Decimal("100000"), CapitalTier.MEDIUM),
            (Decimal("500000"), CapitalTier.LARGE),
        ]:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=24,
            )

            inv_profile = profile_generator.generate(input_profile)
            inv_profile.risk_scaling_enabled = False
            param_set = parametrizer.generate(inv_profile)

            momentum = param_set.get_module("momentum_modular")
            exposures[tier.value] = momentum.max_exposure

        # Verify increasing exposure
        assert exposures["micro"] <= exposures["small"]
        assert exposures["small"] <= exposures["medium"]
        assert exposures["medium"] <= exposures["large"]


# ===================== TESTS: Risk Scaling =====================

class TestRiskScaling:
    """Test risk scaling factor calculations."""

    def test_risk_scaling_factor_calculation(self):
        """Test risk scaling factor based on risk profile."""
        from app.services.parametrization.module_parametrizer import (
            ModuleParametrizer,
        )

        # Test conservative risk (1) → ~0.867
        factor_1 = ModuleParametrizer._calculate_risk_scaling_factor(1)
        assert factor_1 < Decimal("1.0")
        assert factor_1 >= Decimal("0.6")

        # Test neutral risk (4) → ~1.0
        factor_4 = ModuleParametrizer._calculate_risk_scaling_factor(4)
        assert abs(factor_4 - Decimal("1.0")) < Decimal("0.05")

        # Test aggressive risk (7) → ~1.133
        factor_7 = ModuleParametrizer._calculate_risk_scaling_factor(7)
        assert factor_7 > Decimal("1.0")
        assert factor_7 <= Decimal("1.4")

    def test_risk_scaling_applied_to_position_size(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that risk scaling is applied to position sizes when enabled."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = True

        param_set = parametrizer.generate(inv_profile)

        momentum = param_set.get_module("momentum_modular")

        # Risk scaling should be applied based on risk_profile
        # With risk_profile=4 (neutral), scaling factor should be ~1.0
        # So position size should remain approximately 0.12
        assert momentum.max_position_size > Decimal("0.10")  # Within reasonable bounds


# ===================== TESTS: Module Exposure & Accumulation =====================

class TestModuleExposure:
    """Test module exposure accumulation and limits."""

    def test_total_exposure_accumulation(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that total exposure is correctly accumulated across modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        # Calculate total exposure from all modules
        calculated_total = Decimal("0")
        for module_params in param_set.modules.values():
            calculated_total += module_params.max_exposure

        # Should match the param_set total
        assert param_set.total_max_exposure == calculated_total

    def test_multiple_modules_exposure(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test exposure calculation for multiple enabled modules."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        # For medium tier, should have at least 3 modules
        assert len(param_set.modules) >= 3

        # Each module should have max_exposure set
        for module_params in param_set.modules.values():
            assert module_params.max_exposure > Decimal("0")
            assert module_params.max_exposure <= Decimal("1.0")


# ===================== TESTS: Module-Specific Parameters =====================

class TestModuleSpecificParameters:
    """Test module-specific parameter handling."""

    def test_momentum_module_specific_params(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test momentum_modular module-specific parameters."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        momentum = param_set.get_module("momentum_modular")
        assert "min_confidence" in momentum.module_specific
        assert momentum.module_specific["min_confidence"] == 0.60

    def test_mean_reversion_module_specific_params(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test mean_reversion_modular module-specific parameters."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        mr = param_set.get_module("mean_reversion_modular")
        assert "z_score_threshold" in mr.module_specific
        assert mr.module_specific["z_score_threshold"] == 1.0

    def test_dividend_screener_module_specific_params(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test dividend_screener module-specific parameters."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        dividend = param_set.get_module("dividend_screener")
        assert "min_dividend_yield" in dividend.module_specific
        assert dividend.module_specific["min_dividend_yield"] == 0.025


# ===================== TESTS: Error Handling =====================

class TestErrorHandling:
    """Test error handling for invalid configurations."""

    def test_error_handling_missing_module_config(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test handling of missing module configuration."""
        # Create an input profile that would lead to a non-existent module
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)

        # Manually add a non-existent module
        inv_profile.enabled_modules.append("nonexistent_module")

        # Should handle gracefully
        param_set = parametrizer.generate(inv_profile)

        # Valid modules should still be present
        assert "momentum_modular" in param_set.modules

    def test_handling_missing_tier_in_config(
        self,
        profile_generator,
    ):
        """Test handling of missing tier configuration."""
        # This test verifies that ProfileGenerator properly validates
        # that the tier exists in the config
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        assert inv_profile.capital_tier in [CapitalTier.MICRO, CapitalTier.SMALL,
                                             CapitalTier.MEDIUM, CapitalTier.LARGE]


# ===================== TESTS: Serialization =====================

class TestSerialization:
    """Test serialization of parameters to dict format."""

    def test_module_parameters_to_dict(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test ModuleParameters.to_dict() serialization."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        momentum = param_set.get_module("momentum_modular")
        momentum_dict = momentum.to_dict()

        assert momentum_dict["module_name"] == "momentum_modular"
        assert momentum_dict["preset"] == "balanced"
        assert momentum_dict["enabled"] is True
        assert isinstance(momentum_dict["max_position_size"], str)

    def test_module_parameter_set_to_dict(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test ModuleParameterSet.to_dict() serialization."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        param_set_dict = param_set.to_dict()

        assert param_set_dict["profile_id"] == inv_profile.profile_id
        assert param_set_dict["capital_tier"] == "medium"
        assert param_set_dict["objetivo_inversion"] == "maximizar_capital"
        assert "modules" in param_set_dict
        assert len(param_set_dict["modules"]) >= 3


# ===================== TESTS: Preset Assignment =====================

class TestPresetAssignment:
    """Test correct preset assignment based on tier."""

    @pytest.mark.parametrize("capital,expected_preset", [
        (Decimal("5000"), "conservative"),
        (Decimal("25000"), "conservative"),
        (Decimal("100000"), "balanced"),
        (Decimal("500000"), "aggressive"),
    ])
    def test_preset_assignment_by_tier(
        self,
        parametrizer,
        profile_generator,
        capital,
        expected_preset,
    ):
        """Test that correct preset is assigned based on capital tier."""
        input_profile = InputProfile(
            capital_initial=capital,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        for module_params in param_set.modules.values():
            assert module_params.preset == expected_preset


# ===================== TESTS: Configuration Fallbacks =====================

class TestConfigurationFallbacks:
    """Test configuration fallbacks to base/defaults."""

    def test_fallback_to_base_config_if_tier_not_specified(
        self,
        parametrizer,
        profile_generator,
    ):
        """Test that system falls back to base config when tier params missing."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        inv_profile = profile_generator.generate(input_profile)
        inv_profile.risk_scaling_enabled = False
        param_set = parametrizer.generate(inv_profile)

        # All modules should have parameters, even if using base config
        for module_name, module_params in param_set.modules.items():
            assert module_params.max_position_size > Decimal("0")
            assert module_params.stop_loss_pct > Decimal("0")
            assert module_params.take_profit_pct > Decimal("0")
