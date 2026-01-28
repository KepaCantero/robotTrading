#!/usr/bin/env python3
"""
Standalone test script for RiskConfigurator.

This script tests the RiskConfigurator implementation without requiring
the full pytest environment, which has numpy compatibility issues.
"""

from decimal import Decimal
import sys

# Add project root to path
sys.path.insert(0, '/Users/kepa.cantero/Projects/algoTrading')

from app.domain.configurators.risk_config import RiskConfig
from app.domain.configurators.risk_configurator import RiskConfigurator
from app.core.models.input_profile import RiskTolerance


def test_risk_config_bajo():
    """Test RiskConfig for BAJO risk level."""
    print("Testing RiskConfig for BAJO risk level...")

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
    assert config.is_conservative is True
    assert config.is_aggressive is False
    assert config.risk_level == "BAJO"

    # Test calculation methods
    assert config.get_position_limit_for_capital(Decimal("100000")) == Decimal("5000")
    assert config.get_var_limit_for_capital(Decimal("100000")) == Decimal("2000")
    assert config.get_daily_loss_limit_for_capital(Decimal("100000")) == Decimal("5000")

    print("  BAJO: OK")


def test_risk_config_medio():
    """Test RiskConfig for MEDIO risk level."""
    print("Testing RiskConfig for MEDIO risk level...")

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

    assert config.max_drawdown == Decimal("0.25")
    assert config.max_position_size == Decimal("0.10")
    assert config.leverage_allowed is True
    assert config.max_leverage == Decimal("1.5")
    assert config.is_conservative is False
    assert config.is_aggressive is False
    assert config.risk_level == "MEDIO"

    print("  MEDIO: OK")


def test_risk_config_alto():
    """Test RiskConfig for ALTO risk level."""
    print("Testing RiskConfig for ALTO risk level...")

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

    assert config.max_drawdown == Decimal("0.40")
    assert config.max_position_size == Decimal("0.20")
    assert config.leverage_allowed is True
    assert config.max_leverage == Decimal("2.0")
    assert config.is_conservative is False
    assert config.is_aggressive is True
    assert config.risk_level == "ALTO"

    print("  ALTO: OK")


def test_risk_config_validation():
    """Test RiskConfig validation."""
    print("Testing RiskConfig validation...")

    # Test leverage consistency validation
    try:
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
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "max_leverage must be 1.0" in str(e)
        print("  Leverage validation: OK")

    # Test trailing stop validation
    try:
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
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "trailing_stop_atr_multiplier" in str(e)
        print("  Trailing stop validation: OK")


def test_risk_configurator_bajo():
    """Test RiskConfigurator for BAJO tolerance."""
    print("Testing RiskConfigurator.configure(BAJO)...")

    configurator = RiskConfigurator()
    config = configurator.configure(RiskTolerance.BAJO)

    assert config.max_drawdown == Decimal("0.15")
    assert config.max_daily_loss == Decimal("0.05")
    assert config.max_position_size == Decimal("0.05")
    assert config.portfolio_var_limit == Decimal("0.02")
    assert config.leverage_allowed is False
    assert config.max_leverage == Decimal("1.0")
    assert config.stop_loss_atr_multiplier == Decimal("2.0")
    assert config.trailing_stop_atr_multiplier == Decimal("3.0")

    print("  configure(BAJO): OK")


def test_risk_configurator_medio():
    """Test RiskConfigurator for MEDIO tolerance."""
    print("Testing RiskConfigurator.configure(MEDIO)...")

    configurator = RiskConfigurator()
    config = configurator.configure(RiskTolerance.MEDIO)

    assert config.max_drawdown == Decimal("0.25")
    assert config.max_daily_loss == Decimal("0.08")
    assert config.max_position_size == Decimal("0.10")
    assert config.portfolio_var_limit == Decimal("0.03")
    assert config.leverage_allowed is True
    assert config.max_leverage == Decimal("1.5")
    assert config.stop_loss_atr_multiplier == Decimal("2.5")
    assert config.trailing_stop_atr_multiplier == Decimal("3.5")

    print("  configure(MEDIO): OK")


def test_risk_configurator_alto():
    """Test RiskConfigurator for ALTO tolerance."""
    print("Testing RiskConfigurator.configure(ALTO)...")

    configurator = RiskConfigurator()
    config = configurator.configure(RiskTolerance.ALTO)

    assert config.max_drawdown == Decimal("0.40")
    assert config.max_daily_loss == Decimal("0.12")
    assert config.max_position_size == Decimal("0.20")
    assert config.portfolio_var_limit == Decimal("0.05")
    assert config.leverage_allowed is True
    assert config.max_leverage == Decimal("2.0")
    assert config.stop_loss_atr_multiplier == Decimal("3.0")
    assert config.trailing_stop_atr_multiplier == Decimal("4.0")

    print("  configure(ALTO): OK")


def test_configure_for_profile():
    """Test configure_for_profile method."""
    print("Testing configure_for_profile...")

    configurator = RiskConfigurator()

    # Test with enum
    config = configurator.configure_for_profile(RiskTolerance.MEDIO)
    assert config.max_drawdown == Decimal("0.25")
    print("  configure_for_profile(enum): OK")

    # Test with string
    config = configurator.configure_for_profile("bajo")
    assert config.max_drawdown == Decimal("0.15")
    print("  configure_for_profile(string): OK")

    # Test with uppercase string
    config = configurator.configure_for_profile("ALTO")
    assert config.max_drawdown == Decimal("0.40")
    print("  configure_for_profile(uppercase): OK")


def test_get_all_configs():
    """Test get_all_configs method."""
    print("Testing get_all_configs...")

    configurator = RiskConfigurator()
    all_configs = configurator.get_all_configs()

    assert len(all_configs) == 3
    assert RiskTolerance.BAJO in all_configs
    assert RiskTolerance.MEDIO in all_configs
    assert RiskTolerance.ALTO in all_configs

    print("  get_all_configs: OK")


def test_compare_configs():
    """Test compare_configs method."""
    print("Testing compare_configs...")

    configurator = RiskConfigurator()
    comparison = configurator.compare_configs(RiskTolerance.BAJO, RiskTolerance.ALTO)

    assert "tolerance1" in comparison
    assert "tolerance2" in comparison
    assert comparison["tolerance1"]["level"] == "bajo"
    assert comparison["tolerance2"]["level"] == "alto"

    print("  compare_configs: OK")


def test_risk_parameter_progression():
    """Test that risk parameters increase with tolerance level."""
    print("Testing risk parameter progression...")

    configurator = RiskConfigurator()

    bajo = configurator.configure(RiskTolerance.BAJO)
    medio = configurator.configure(RiskTolerance.MEDIO)
    alto = configurator.configure(RiskTolerance.ALTO)

    # Drawdown should increase
    assert bajo.max_drawdown < medio.max_drawdown < alto.max_drawdown
    print("  Drawdown progression: OK")

    # Position size should increase
    assert bajo.max_position_size < medio.max_position_size < alto.max_position_size
    print("  Position size progression: OK")

    # Stop loss multiplier should increase
    assert (
        bajo.stop_loss_atr_multiplier
        < medio.stop_loss_atr_multiplier
        < alto.stop_loss_atr_multiplier
    )
    print("  Stop loss progression: OK")

    # Trailing stop multiplier should increase
    assert (
        bajo.trailing_stop_atr_multiplier
        < medio.trailing_stop_atr_multiplier
        < alto.trailing_stop_atr_multiplier
    )
    print("  Trailing stop progression: OK")


def main():
    """Run all tests."""
    print("=" * 60)
    print("RiskConfigurator Standalone Test Suite")
    print("=" * 60)
    print()

    # Test RiskConfig value object
    print("Testing RiskConfig value object:")
    print("-" * 40)
    test_risk_config_bajo()
    test_risk_config_medio()
    test_risk_config_alto()
    test_risk_config_validation()
    print()

    # Test RiskConfigurator
    print("Testing RiskConfigurator:")
    print("-" * 40)
    test_risk_configurator_bajo()
    test_risk_configurator_medio()
    test_risk_configurator_alto()
    test_configure_for_profile()
    test_get_all_configs()
    test_compare_configs()
    test_risk_parameter_progression()
    print()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
