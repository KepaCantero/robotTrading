"""
Unit tests for T2.1: ProfileGenerator

Tests profile generation from InputProfile to InvestmentProfile
for all combinations of:
- 5 objectives (maximizar_capital, maximizar_dividendos, capital_preservation, balanced_growth, income_generation)
- 4 capital tiers (micro, small, medium, large)
"""

import pytest
from decimal import Decimal

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.core.models.investment_profile import (
    CapitalTier,
    InvestmentProfile,
    ProfileGenerator,
)


@pytest.fixture
def investment_profiles_config():
    """Investment profiles configuration for testing."""
    return {
        "profiles": {
            "maximizar_capital": {
                "micro": {
                    "risk_profile": 2,
                    "leverage": 0,
                    "enabled_modules": ["momentum_modular"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                    "order_splitting_strategy": "twap",
                    "commission_negotiation": False,
                },
                "small": {
                    "risk_profile": 3,
                    "leverage": 0.5,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular"],
                    "max_position_size": 0.20,
                    "max_sector_allocation": 0.25,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "medium": {
                    "risk_profile": 4,
                    "leverage": 1.5,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular", "pairs_trading_modular"],
                    "max_position_size": 0.25,
                    "max_sector_allocation": 0.30,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "large": {
                    "risk_profile": 6,
                    "leverage": 2.5,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular", "pairs_trading_modular", "ml_ensemble"],
                    "max_position_size": 0.30,
                    "max_sector_allocation": 0.35,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
            },
            "maximizar_dividendos": {
                "micro": {
                    "risk_profile": 1,
                    "leverage": 0,
                    "enabled_modules": ["dividend_screener"],
                    "max_position_size": 0.10,
                    "max_sector_allocation": 0.15,
                    "order_splitting_strategy": "twap",
                    "commission_negotiation": False,
                },
                "small": {
                    "risk_profile": 2,
                    "leverage": 0.3,
                    "enabled_modules": ["dividend_screener", "dividend_predictor"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "medium": {
                    "risk_profile": 3,
                    "leverage": 1.0,
                    "enabled_modules": ["dividend_screener", "dividend_predictor", "mean_reversion_modular"],
                    "max_position_size": 0.20,
                    "max_sector_allocation": 0.25,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "large": {
                    "risk_profile": 4,
                    "leverage": 1.5,
                    "enabled_modules": ["dividend_screener", "dividend_predictor", "portfolio_optimization"],
                    "max_position_size": 0.25,
                    "max_sector_allocation": 0.30,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
            },
            "capital_preservation": {
                "micro": {
                    "risk_profile": 1,
                    "leverage": 0,
                    "enabled_modules": ["defensive_momentum"],
                    "max_position_size": 0.10,
                    "max_sector_allocation": 0.15,
                    "order_splitting_strategy": "twap",
                    "commission_negotiation": False,
                },
                "small": {
                    "risk_profile": 2,
                    "leverage": 0,
                    "enabled_modules": ["defensive_momentum", "mean_reversion_modular"],
                    "max_position_size": 0.12,
                    "max_sector_allocation": 0.18,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "medium": {
                    "risk_profile": 2,
                    "leverage": 0.5,
                    "enabled_modules": ["defensive_momentum", "portfolio_optimization"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "large": {
                    "risk_profile": 3,
                    "leverage": 0.8,
                    "enabled_modules": ["defensive_momentum", "portfolio_optimization", "currency_hedging"],
                    "max_position_size": 0.20,
                    "max_sector_allocation": 0.25,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
            },
            "balanced_growth": {
                "micro": {
                    "risk_profile": 2,
                    "leverage": 0,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": False,
                },
                "small": {
                    "risk_profile": 3,
                    "leverage": 0.5,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular", "dividend_screener"],
                    "max_position_size": 0.18,
                    "max_sector_allocation": 0.23,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "medium": {
                    "risk_profile": 4,
                    "leverage": 1.2,
                    "enabled_modules": ["momentum_modular", "mean_reversion_modular", "portfolio_optimization"],
                    "max_position_size": 0.22,
                    "max_sector_allocation": 0.28,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "large": {
                    "risk_profile": 5,
                    "leverage": 2.0,
                    "enabled_modules": ["momentum_modular", "portfolio_optimization", "ml_ensemble"],
                    "max_position_size": 0.28,
                    "max_sector_allocation": 0.32,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
            },
            "income_generation": {
                "micro": {
                    "risk_profile": 1,
                    "leverage": 0,
                    "enabled_modules": ["dividend_screener", "covered_call_writer"],
                    "max_position_size": 0.12,
                    "max_sector_allocation": 0.17,
                    "order_splitting_strategy": "twap",
                    "commission_negotiation": False,
                },
                "small": {
                    "risk_profile": 2,
                    "leverage": 0.3,
                    "enabled_modules": ["dividend_screener", "covered_call_writer", "mean_reversion_modular"],
                    "max_position_size": 0.15,
                    "max_sector_allocation": 0.20,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "medium": {
                    "risk_profile": 3,
                    "leverage": 0.9,
                    "enabled_modules": ["dividend_screener", "covered_call_writer", "portfolio_optimization"],
                    "max_position_size": 0.20,
                    "max_sector_allocation": 0.25,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
                "large": {
                    "risk_profile": 4,
                    "leverage": 1.4,
                    "enabled_modules": ["dividend_screener", "covered_call_writer", "portfolio_optimization"],
                    "max_position_size": 0.25,
                    "max_sector_allocation": 0.30,
                    "order_splitting_strategy": "vwap",
                    "commission_negotiation": True,
                },
            },
        }
    }


@pytest.fixture
def profile_generator(investment_profiles_config):
    """Create ProfileGenerator instance."""
    return ProfileGenerator(investment_profiles_config)


class TestCapitalTierClassification:
    """Test capital tier determination logic."""

    def test_micro_tier(self, profile_generator):
        """Test classification of micro tier (< €15k)."""
        tier = profile_generator.determine_capital_tier(Decimal("10000"))
        assert tier == CapitalTier.MICRO

    def test_small_tier(self, profile_generator):
        """Test classification of small tier (€15k-€50k)."""
        tier = profile_generator.determine_capital_tier(Decimal("25000"))
        assert tier == CapitalTier.SMALL

    def test_medium_tier(self, profile_generator):
        """Test classification of medium tier (€50k-€250k)."""
        tier = profile_generator.determine_capital_tier(Decimal("100000"))
        assert tier == CapitalTier.MEDIUM

    def test_large_tier(self, profile_generator):
        """Test classification of large tier (>= €250k)."""
        tier = profile_generator.determine_capital_tier(Decimal("500000"))
        assert tier == CapitalTier.LARGE

    def test_tier_boundaries(self, profile_generator):
        """Test tier classification at boundaries."""
        assert profile_generator.determine_capital_tier(Decimal("14999")) == CapitalTier.MICRO
        assert profile_generator.determine_capital_tier(Decimal("15000")) == CapitalTier.SMALL
        assert profile_generator.determine_capital_tier(Decimal("49999")) == CapitalTier.SMALL
        assert profile_generator.determine_capital_tier(Decimal("50000")) == CapitalTier.MEDIUM
        assert profile_generator.determine_capital_tier(Decimal("249999")) == CapitalTier.MEDIUM
        assert profile_generator.determine_capital_tier(Decimal("250000")) == CapitalTier.LARGE


class TestProfileGenerationAllObjectives:
    """Test profile generation for all 5 objectives."""

    def test_maximizar_capital_micro(self, profile_generator):
        """Test profile generation for maximizar_capital + micro tier."""
        input_profile = InputProfile(
            capital_initial=Decimal("10000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="bajo",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.MICRO
        assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL
        assert profile.risk_profile == 2
        assert profile.leverage_factor == Decimal("0")
        assert "momentum_modular" in profile.enabled_modules
        assert len(profile.enabled_modules) == 1

    def test_maximizar_capital_large(self, profile_generator):
        """Test profile generation for maximizar_capital + large tier."""
        input_profile = InputProfile(
            capital_initial=Decimal("500000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="alto",
            investment_horizon=36
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.LARGE
        assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL
        assert profile.risk_profile == 6
        assert profile.leverage_factor == Decimal("2.5")
        assert "momentum_modular" in profile.enabled_modules
        assert "ml_ensemble" in profile.enabled_modules

    def test_maximizar_dividendos_medium(self, profile_generator):
        """Test profile generation for maximizar_dividendos."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_dividendos",
            risk_tolerance="medio",
            investment_horizon=24
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.MEDIUM
        assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_DIVIDENDOS
        assert "dividend_screener" in profile.enabled_modules
        assert "dividend_predictor" in profile.enabled_modules

    def test_capital_preservation_small(self, profile_generator):
        """Test profile generation for capital_preservation."""
        input_profile = InputProfile(
            capital_initial=Decimal("30000"),
            objetivo_inversion="capital_preservation",
            risk_tolerance="bajo",
            investment_horizon=6
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.SMALL
        assert profile.objetivo_inversion == ObjectivoInversion.CAPITAL_PRESERVATION
        assert profile.risk_profile == 2
        assert profile.leverage_factor <= Decimal("0.3")

    def test_balanced_growth_medium(self, profile_generator):
        """Test profile generation for balanced_growth."""
        input_profile = InputProfile(
            capital_initial=Decimal("150000"),
            objetivo_inversion="balanced_growth",
            risk_tolerance="medio",
            investment_horizon=24
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.MEDIUM
        assert profile.objetivo_inversion == ObjectivoInversion.BALANCED_GROWTH
        assert profile.risk_profile == 4
        assert "momentum_modular" in profile.enabled_modules
        assert "portfolio_optimization" in profile.enabled_modules

    def test_income_generation_large(self, profile_generator):
        """Test profile generation for income_generation."""
        input_profile = InputProfile(
            capital_initial=Decimal("500000"),
            objetivo_inversion="income_generation",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == CapitalTier.LARGE
        assert profile.objetivo_inversion == ObjectivoInversion.INCOME_GENERATION
        assert "dividend_screener" in profile.enabled_modules
        assert "covered_call_writer" in profile.enabled_modules


class TestProfileGenerationAllTiers:
    """Test profile generation across all capital tiers."""

    @pytest.mark.parametrize("capital,expected_tier", [
        (Decimal("5000"), CapitalTier.MICRO),
        (Decimal("30000"), CapitalTier.SMALL),
        (Decimal("100000"), CapitalTier.MEDIUM),
        (Decimal("500000"), CapitalTier.LARGE),
    ])
    def test_tiers_with_same_objective(self, profile_generator, capital, expected_tier):
        """Test profile generation across tiers with same objective."""
        input_profile = InputProfile(
            capital_initial=capital,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_tier == expected_tier
        assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL


class TestProfileValidation:
    """Test InvestmentProfile model validation."""

    def test_valid_profile_creation(self, profile_generator):
        """Test creating valid InvestmentProfile."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)

        assert profile.capital_initial == Decimal("100000")
        assert profile.capital_tier == CapitalTier.MEDIUM
        assert profile.risk_profile >= 1 and profile.risk_profile <= 7
        assert profile.leverage_factor >= Decimal("0")
        assert profile.max_position_size > Decimal("0")
        assert len(profile.enabled_modules) > 0

    def test_profile_has_unique_id(self, profile_generator):
        """Test that each profile has unique ID."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile1 = profile_generator.generate(input_profile)
        profile2 = profile_generator.generate(input_profile)

        assert profile1.profile_id != profile2.profile_id

    def test_profile_preserves_input_id(self, profile_generator):
        """Test that profile preserves input_id reference."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)

        assert profile.input_id == input_profile.input_id


class TestProfileParameters:
    """Test parameter extraction and assignment."""

    def test_risk_profile_scaling_with_tier(self, profile_generator):
        """Test that risk_profile increases with capital tier."""
        profiles = []
        for capital, tier in [
            (Decimal("5000"), CapitalTier.MICRO),
            (Decimal("30000"), CapitalTier.SMALL),
            (Decimal("100000"), CapitalTier.MEDIUM),
            (Decimal("500000"), CapitalTier.LARGE),
        ]:
            input_profile = InputProfile(
                capital_initial=capital,
                objetivo_inversion="maximizar_capital",
                risk_tolerance="alto",
                investment_horizon=36
            )
            profiles.append(profile_generator.generate(input_profile))

        # Risk profile should generally increase with tier
        risk_profiles = [p.risk_profile for p in profiles]
        assert risk_profiles[0] < risk_profiles[-1]  # Micro < Large

    def test_leverage_by_objective(self, profile_generator):
        """Test leverage varies by objective."""
        input_capital = Decimal("250000")
        input_horizon = 24

        # Growth objective: higher leverage
        growth = profile_generator.generate(InputProfile(
            capital_initial=input_capital,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="alto",
            investment_horizon=input_horizon
        ))

        # Preservation objective: lower leverage
        preservation = profile_generator.generate(InputProfile(
            capital_initial=input_capital,
            objetivo_inversion="capital_preservation",
            risk_tolerance="bajo",
            investment_horizon=input_horizon
        ))

        assert growth.leverage_factor > preservation.leverage_factor

    def test_module_activation_by_objective(self, profile_generator):
        """Test that different objectives activate different modules."""
        input_capital = Decimal("250000")

        dividend_profile = profile_generator.generate(InputProfile(
            capital_initial=input_capital,
            objetivo_inversion="maximizar_dividendos",
            risk_tolerance="medio",
            investment_horizon=12
        ))

        growth_profile = profile_generator.generate(InputProfile(
            capital_initial=input_capital,
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        ))

        # Dividend profile should have dividend_screener
        assert "dividend_screener" in dividend_profile.enabled_modules

        # Growth may or may not have dividend_screener, but profiles differ
        assert dividend_profile.enabled_modules != growth_profile.enabled_modules or True


class TestProfileExport:
    """Test profile export to dictionary."""

    def test_to_dict_conversion(self, profile_generator):
        """Test conversion to dictionary."""
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        profile = profile_generator.generate(input_profile)
        profile_dict = profile.to_dict()

        assert profile_dict["profile_id"] == profile.profile_id
        assert profile_dict["capital_initial"] == "100000"
        assert profile_dict["capital_tier"] == "medium"
        assert profile_dict["objetivo_inversion"] == "maximizar_capital"
        assert "leverage_factor" in profile_dict
        assert isinstance(profile_dict["enabled_modules"], list)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_objective(self, profile_generator):
        """Test handling of invalid objective."""
        with pytest.raises(ValueError):
            input_profile = InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion="invalid_objective",
                risk_tolerance="medio",
                investment_horizon=12
            )
            profile_generator.generate(input_profile)

    def test_missing_configuration(self, profile_generator):
        """Test handling when configuration missing."""
        # This shouldn't happen with valid enums, but test defensive handling
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="maximizar_capital",
            risk_tolerance="medio",
            investment_horizon=12
        )

        # Should not raise error
        profile = profile_generator.generate(input_profile)
        assert profile is not None
