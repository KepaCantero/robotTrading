"""
Unit tests for RiskConfigurator.

Tests the mapping from risk tolerance to concrete risk parameters
as specified in AUDIT_PLAN_COMPLETO.md Section 4.2.

Test Coverage:
- RiskConfig value object validation
- RiskConfigurator.configure() for each tolerance level
- RiskConfigurator edge cases and error handling
"""

from decimal import Decimal

import pytest

from app.domain.models.input_profile import RiskTolerance
from app.domain.configurators.risk_config import RiskConfig
from app.domain.configurators.risk_configurator import RiskConfigurator


class TestRiskConfig:
    """Test RiskConfig value object."""

    def test_risk_config_creation_bajo(self) -> None:
        """Test RiskConfig creation for BAJO risk level."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        assert config.max_drawdown == Decimal("0.15")
        assert config.max_position_size == Decimal("0.05")
        assert config.leverage_allowed is False
        assert config.max_leverage == Decimal("1.0")

    def test_risk_config_is_conservative(self) -> None:
        """Test is_conservative property."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        assert config.is_conservative is True
        assert config.is_aggressive is False
        assert config.risk_level == "BAJO"

    def test_risk_config_is_aggressive(self) -> None:
        """Test is_aggressive property."""
        config = RiskConfig(
            max_drawdown=Decimal("0.40"),
            max_daily_loss=Decimal("0.12"),
            max_position_size=Decimal("0.20"),
            portfolio_var_limit=Decimal("0.05"),
            leverage_allowed=True,
            max_leverage=Decimal("2.0"),
            stop_loss_atr_multiplier=Decimal("3.0"),
            trailing_stop_atr_multiplier=Decimal("4.0"),
        )

        assert config.is_conservative is False
        assert config.is_aggressive is True
        assert config.risk_level == "ALTO"

    def test_risk_config_is_moderate(self) -> None:
        """Test moderate risk level detection."""
        config = RiskConfig(
            max_drawdown=Decimal("0.25"),
            max_daily_loss=Decimal("0.08"),
            max_position_size=Decimal("0.10"),
            portfolio_var_limit=Decimal("0.03"),
            leverage_allowed=True,
            max_leverage=Decimal("1.5"),
            stop_loss_atr_multiplier=Decimal("2.5"),
            trailing_stop_atr_multiplier=Decimal("3.5"),
        )

        assert config.is_conservative is False
        assert config.is_aggressive is False
        assert config.risk_level == "MEDIO"

    def test_risk_config_validation_leverage_consistency(self) -> None:
        """Test validation fails when leverage not allowed but max_leverage > 1.0."""
        with pytest.raises(ValueError, match="max_leverage must be 1.0"):
            RiskConfig(
                max_drawdown=Decimal("0.15"),
                max_daily_loss=Decimal("0.05"),
                max_position_size=Decimal("0.05"),
                portfolio_var_limit=Decimal("0.02"),
                leverage_allowed=False,
                max_leverage=Decimal("1.5"),  # Invalid!
                stop_loss_atr_multiplier=Decimal("2.0"),
                trailing_stop_atr_multiplier=Decimal("3.0"),
            )

    def test_risk_config_validation_trailing_stop_wider_than_stop_loss(self) -> None:
        """Test validation fails when trailing stop is not wider than stop loss."""
        with pytest.raises(ValueError, match="trailing_stop_atr_multiplier.*must be greater than"):
            RiskConfig(
                max_drawdown=Decimal("0.25"),
                max_daily_loss=Decimal("0.08"),
                max_position_size=Decimal("0.10"),
                portfolio_var_limit=Decimal("0.03"),
                leverage_allowed=True,
                max_leverage=Decimal("1.5"),
                stop_loss_atr_multiplier=Decimal("3.0"),
                trailing_stop_atr_multiplier=Decimal("2.0"),  # Invalid!
            )

    def test_risk_config_get_position_limit_for_capital(self) -> None:
        """Test position limit calculation."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        limit = config.get_position_limit_for_capital(Decimal("100000"))
        assert limit == Decimal("5000")

    def test_risk_config_get_var_limit_for_capital(self) -> None:
        """Test VaR limit calculation."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        var_limit = config.get_var_limit_for_capital(Decimal("100000"))
        assert var_limit == Decimal("2000")

    def test_risk_config_get_daily_loss_limit_for_capital(self) -> None:
        """Test daily loss limit calculation."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        daily_limit = config.get_daily_loss_limit_for_capital(Decimal("100000"))
        assert daily_limit == Decimal("5000")

    def test_risk_config_immutability(self) -> None:
        """Test that RiskConfig is immutable (frozen)."""
        config = RiskConfig(
            max_drawdown=Decimal("0.15"),
            max_daily_loss=Decimal("0.05"),
            max_position_size=Decimal("0.05"),
            portfolio_var_limit=Decimal("0.02"),
            leverage_allowed=False,
            max_leverage=Decimal("1.0"),
            stop_loss_atr_multiplier=Decimal("2.0"),
            trailing_stop_atr_multiplier=Decimal("3.0"),
        )

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # pydantic.FrozenInstanceError
            config.max_drawdown = Decimal("0.20")


class TestRiskConfigurator:
    """Test RiskConfigurator class."""

    def test_configure_bajo_risk(self) -> None:
        """Test configuration for BAJO (low) risk tolerance.

        Expected per AUDIT_PLAN_COMPLETO.md Section 4.2:
        - Drawdown < 15%
        - Position limit 5%
        - No leverage
        """
        configurator = RiskConfigurator()
        config = configurator.configure(RiskTolerance.BAJO)

        assert config.max_drawdown == Decimal("0.15")
        assert config.max_position_size == Decimal("0.05")
        assert config.leverage_allowed is False
        assert config.max_leverage == Decimal("1.0")
        assert config.max_daily_loss == Decimal("0.05")
        assert config.portfolio_var_limit == Decimal("0.02")

    def test_configure_medio_risk(self) -> None:
        """Test configuration for MEDIO (medium) risk tolerance.

        Expected per AUDIT_PLAN_COMPLETO.md Section 4.2:
        - Drawdown < 25%
        - Position limit 10%
        - Leverage 1.5x
        """
        configurator = RiskConfigurator()
        config = configurator.configure(RiskTolerance.MEDIO)

        assert config.max_drawdown == Decimal("0.25")
        assert config.max_position_size == Decimal("0.10")
        assert config.leverage_allowed is True
        assert config.max_leverage == Decimal("1.5")
        assert config.max_daily_loss == Decimal("0.08")
        assert config.portfolio_var_limit == Decimal("0.03")

    def test_configure_alto_risk(self) -> None:
        """Test configuration for ALTO (high) risk tolerance.

        Expected per AUDIT_PLAN_COMPLETO.md Section 4.2:
        - Drawdown < 40%
        - Position limit 20%
        - Leverage 2.0x
        """
        configurator = RiskConfigurator()
        config = configurator.configure(RiskTolerance.ALTO)

        assert config.max_drawdown == Decimal("0.40")
        assert config.max_position_size == Decimal("0.20")
        assert config.leverage_allowed is True
        assert config.max_leverage == Decimal("2.0")
        assert config.max_daily_loss == Decimal("0.12")
        assert config.portfolio_var_limit == Decimal("0.05")

    def test_configure_invalid_tolerance(self) -> None:
        """Test that invalid risk tolerance raises ValueError."""
        configurator = RiskConfigurator()

        # Create a mock invalid enum value
        class MockRiskTolerance(str):
            pass

        invalid_tolerance = MockRiskTolerance("invalid")

        with pytest.raises(ValueError):
            # if-elif-else chain will fall through to the else case
            configurator.configure(invalid_tolerance)

    def test_configure_for_profile_with_enum(self) -> None:
        """Test configure_for_profile with RiskTolerance enum."""
        configurator = RiskConfigurator()
        config = configurator.configure_for_profile(RiskTolerance.MEDIO)

        assert config.max_drawdown == Decimal("0.25")
        assert config.max_position_size == Decimal("0.10")

    def test_configure_for_profile_with_string(self) -> None:
        """Test configure_for_profile with string input."""
        configurator = RiskConfigurator()

        # Test lowercase
        config = configurator.configure_for_profile("bajo")
        assert config.max_drawdown == Decimal("0.15")

        # Test uppercase
        config = configurator.configure_for_profile("MEDIO")
        assert config.max_drawdown == Decimal("0.25")

        # Test mixed case
        config = configurator.configure_for_profile("AlTo")
        assert config.max_drawdown == Decimal("0.40")

    def test_configure_for_profile_invalid_string(self) -> None:
        """Test configure_for_profile with invalid string."""
        configurator = RiskConfigurator()

        with pytest.raises(ValueError, match="Invalid risk_tolerance"):
            configurator.configure_for_profile("invalid")

    def test_get_all_configs(self) -> None:
        """Test getting all available configurations."""
        configurator = RiskConfigurator()
        all_configs = configurator.get_all_configs()

        assert len(all_configs) == 3
        assert RiskTolerance.BAJO in all_configs
        assert RiskTolerance.MEDIO in all_configs
        assert RiskTolerance.ALTO in all_configs

        # Verify each config has correct values
        assert all_configs[RiskTolerance.BAJO].max_drawdown == Decimal("0.15")
        assert all_configs[RiskTolerance.MEDIO].max_drawdown == Decimal("0.25")
        assert all_configs[RiskTolerance.ALTO].max_drawdown == Decimal("0.40")

    def test_compare_configs(self) -> None:
        """Test comparing two risk configurations."""
        configurator = RiskConfigurator()
        comparison = configurator.compare_configs(RiskTolerance.BAJO, RiskTolerance.ALTO)

        assert "tolerance1" in comparison
        assert "tolerance2" in comparison

        # Check BAJO values
        assert comparison["tolerance1"]["level"] == "bajo"
        assert comparison["tolerance1"]["max_drawdown"] == Decimal("0.15")
        assert comparison["tolerance1"]["leverage_allowed"] is False

        # Check ALTO values
        assert comparison["tolerance2"]["level"] == "alto"
        assert comparison["tolerance2"]["max_drawdown"] == Decimal("0.40")
        assert comparison["tolerance2"]["leverage_allowed"] is True

    def test_stop_loss_atr_multiplier_increases_with_risk(self) -> None:
        """Test that stop loss multiplier increases with risk tolerance."""
        configurator = RiskConfigurator()

        bajo_config = configurator.configure(RiskTolerance.BAJO)
        medio_config = configurator.configure(RiskTolerance.MEDIO)
        alto_config = configurator.configure(RiskTolerance.ALTO)

        assert (
            bajo_config.stop_loss_atr_multiplier
            < medio_config.stop_loss_atr_multiplier
            < alto_config.stop_loss_atr_multiplier
        )

    def test_trailing_stop_atr_multiplier_increases_with_risk(self) -> None:
        """Test that trailing stop multiplier increases with risk tolerance."""
        configurator = RiskConfigurator()

        bajo_config = configurator.configure(RiskTolerance.BAJO)
        medio_config = configurator.configure(RiskTolerance.MEDIO)
        alto_config = configurator.configure(RiskTolerance.ALTO)

        assert (
            bajo_config.trailing_stop_atr_multiplier
            < medio_config.trailing_stop_atr_multiplier
            < alto_config.trailing_stop_atr_multiplier
        )

    def test_position_size_increases_with_risk(self) -> None:
        """Test that position size limit increases with risk tolerance."""
        configurator = RiskConfigurator()

        bajo_config = configurator.configure(RiskTolerance.BAJO)
        medio_config = configurator.configure(RiskTolerance.MEDIO)
        alto_config = configurator.configure(RiskTolerance.ALTO)

        assert (
            bajo_config.max_position_size
            < medio_config.max_position_size
            < alto_config.max_position_size
        )
