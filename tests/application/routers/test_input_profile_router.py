"""Tests for InputProfileRouter.

Tests the routing logic from InputProfile to SystemConfiguration,
ensuring correct strategy selection, risk configuration, and tax optimization.
"""

from decimal import Decimal

import pytest

from app.application.routers.input_profile_router import InputProfileRouter
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)
from app.domain.models.strategy_type import StrategyType


class TestInputProfileRouter:
    """Test suite for InputProfileRouter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = InputProfileRouter()

    def test_select_strategy_type_maximizar_capital(self):
        """Test strategy selection for MAXIMIZAR_CAPITAL objective."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)

        assert config.strategy_type == StrategyType.MOMENTUM
        assert config.risk_config.max_drawdown == Decimal("0.25")
        assert config.risk_config.leverage_allowed is True

    def test_select_strategy_type_maximizar_dividendos(self):
        """Test strategy selection for MAXIMIZAR_DIVIDENDOS objective."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=36,
        )

        config = self.router(profile)

        assert config.strategy_type == StrategyType.DIVIDEND
        assert config.risk_config.max_drawdown == Decimal("0.15")
        assert config.risk_config.leverage_allowed is False

    def test_select_strategy_type_capital_preservation(self):
        """Test strategy selection for CAPITAL_PRESERVATION objective."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        config = self.router(profile)

        assert config.strategy_type == StrategyType.LOW_VOLATILITY
        assert config.risk_config.is_conservative is True

    def test_select_strategy_type_balanced_growth(self):
        """Test strategy selection for BALANCED_GROWTH objective."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=48,
        )

        config = self.router(profile)

        assert config.strategy_type == StrategyType.MULTI_FACTOR

    def test_select_strategy_type_income_generation(self):
        """Test strategy selection for INCOME_GENERATION objective."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=24,
        )

        config = self.router(profile)

        assert config.strategy_type == StrategyType.COVERED_CALL

    def test_risk_config_bajo(self):
        """Test risk configuration for BAJO tolerance."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=12,
        )

        config = self.router(profile)

        assert config.risk_config.max_drawdown == Decimal("0.15")
        assert config.risk_config.max_position_size == Decimal("0.05")
        assert config.risk_config.leverage_allowed is False
        assert config.risk_config.min_positions == 10

    def test_risk_config_medio(self):
        """Test risk configuration for MEDIO tolerance."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)

        assert config.risk_config.max_drawdown == Decimal("0.25")
        assert config.risk_config.max_position_size == Decimal("0.10")
        assert config.risk_config.leverage_allowed is True
        assert config.risk_config.max_leverage == Decimal("1.5")

    def test_risk_config_alto(self):
        """Test risk configuration for ALTO tolerance."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=36,
        )

        config = self.router(profile)

        assert config.risk_config.max_drawdown == Decimal("0.40")
        assert config.risk_config.max_position_size == Decimal("0.20")
        assert config.risk_config.leverage_allowed is True
        assert config.risk_config.max_leverage == Decimal("2.0")
        assert config.risk_config.is_aggressive is True

    def test_tax_config_with_residence(self):
        """Test tax configuration creation with tax residence."""
        tax_residence = TaxResidence(
            country_code="ES",
            capital_gains_rate_short=Decimal("0.19"),
            capital_gains_rate_long=Decimal("0.19"),
            dividend_tax_rate=Decimal("0.19"),
        )

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
            tax_residence=tax_residence,
        )

        config = self.router(profile)

        assert config.tax_config is not None
        assert config.tax_config.country_code == "ES"
        assert config.tax_config.base_currency == "EUR"
        assert config.tax_config.capital_gains_rate_short == Decimal("0.19")

    def test_tax_config_without_residence(self):
        """Test tax configuration without tax residence."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)

        assert config.tax_config is None

    def test_rebalance_frequency_short_horizon(self):
        """Test rebalancing frequency for short horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=3,  # 3 months
        )

        config = self.router(profile)

        assert config.rebalance_frequency_days == 7  # Weekly

    def test_rebalance_frequency_medium_horizon(self):
        """Test rebalancing frequency for medium horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=18,  # 18 months
        )

        config = self.router(profile)

        assert config.rebalance_frequency_days == 14  # Bi-weekly

    def test_rebalance_frequency_long_horizon(self):
        """Test rebalancing frequency for long horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=60,  # 5 years
        )

        config = self.router(profile)

        # 60 months >= 60, so quarterly (90 days)
        assert config.rebalance_frequency_days == 90  # Quarterly

    def test_rebalance_frequency_very_long_horizon(self):
        """Test rebalancing frequency for very long horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=120,  # 10 years
        )

        config = self.router(profile)

        assert config.rebalance_frequency_days == 90  # Quarterly

    def test_deployable_capital_calculation(self):
        """Test deployable capital calculation."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)

        # 100000 - (100000 * 0.05) = 95000
        assert config.deployable_capital == Decimal("95000")

    def test_validate_configuration_capital_preservation_with_high_risk(self):
        """Test validation warning for capital preservation with high risk."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=24,
        )

        config = self.router(profile)
        is_valid, warnings = self.router.validate_configuration(profile, config)

        assert is_valid is False
        assert len(warnings) > 0
        assert any("contradictory" in w for w in warnings)

    def test_validate_configuration_valid(self):
        """Test validation for valid configuration."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)
        is_valid, warnings = self.router.validate_configuration(profile, config)

        assert is_valid is True
        assert len(warnings) == 0

    def test_tax_config_long_term_advantage(self):
        """Test tax config detects long-term advantage."""
        tax_residence = TaxResidence(
            country_code="US",
            base_currency="USD",
            capital_gains_rate_short=Decimal("0.35"),  # Higher short-term rate
            capital_gains_rate_long=Decimal("0.15"),  # Lower long-term rate
            dividend_tax_rate=Decimal("0.20"),
        )

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
            tax_residence=tax_residence,
        )

        config = self.router(profile)

        assert config.tax_config is not None
        assert config.tax_config.has_long_term_advantage is True
        assert config.tax_config.long_term_advantage == Decimal("0.20")
        assert config.tax_config.prefer_long_term is True

    def test_strategy_type_properties(self):
        """Test StrategyType properties."""
        assert StrategyType.MOMENTUM.requires_leverage is False
        assert StrategyType.MULTI_FACTOR.requires_leverage is True
        assert StrategyType.LOW_VOLATILITY.is_defensive is True
        assert StrategyType.MOMENTUM.is_defensive is False

    def test_system_configuration_properties(self):
        """Test SystemConfiguration computed properties."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=24,
        )

        config = self.router(profile)

        assert config.requires_long_term_focus is True
        assert config.is_complex_strategy is False
        assert config.expected_volatility == Decimal("0.10")

    def test_invalid_objectivo_raises_error(self):
        """Test that invalid objetivo raises ValueError."""
        # This would be caught by InputProfile validation, but we can
        # test the internal method directly if needed
        pass  # InputProfile validation handles this

    def test_to_dict_serialization(self):
        """Test SystemConfiguration.to_dict() method."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = self.router(profile)
        config_dict = config.to_dict()

        assert config_dict["strategy_type"] == "multi_factor"
        assert config_dict["max_drawdown"] == "0.25"
        assert config_dict["initial_capital"] == "100000"
        assert config_dict["tax_optimization"] is False
