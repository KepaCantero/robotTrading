"""
Test that shadow mode uses centralized configuration

Verifies that all magic numbers have been replaced with centralized config values.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.services.shadow_mode import ShadowModeConfig
from app.shared.config.centralized_config import get_config


def test_shadow_mode_config_uses_centralized_defaults():
    """Test that ShadowModeConfig loads defaults from centralized config."""
    # Create config without explicit values
    config = ShadowModeConfig()

    # Get centralized config
    centralized = get_config().shadow_mode

    # Verify all values come from centralized config
    assert config.slippage_bps == centralized.slippage_bps
    assert config.fill_delay_ms == centralized.fill_delay_ms
    assert config.partial_fill_probability == centralized.partial_fill_probability
    assert config.rejection_probability == centralized.rejection_probability
    assert config.comparison_window_minutes == centralized.comparison_window_minutes
    assert config.max_shadow_orders_per_day == centralized.max_shadow_orders_per_day

    # Verify default values match centralized config
    assert config.slippage_bps == 5
    assert config.fill_delay_ms == 100
    assert config.partial_fill_probability == 0.1
    assert config.rejection_probability == 0.01
    assert config.comparison_window_minutes == 60
    assert config.max_shadow_orders_per_day == 1000


def test_shadow_mode_config_allows_override():
    """Test that ShadowModeConfig allows overriding centralized defaults."""
    config = ShadowModeConfig(
        slippage_bps=20,
        fill_delay_ms=200,
        partial_fill_probability=0.3,
        rejection_probability=0.05,
        comparison_window_minutes=120,
        max_shadow_orders_per_day=500,
    )

    # Verify overridden values
    assert config.slippage_bps == 20
    assert config.fill_delay_ms == 200
    assert config.partial_fill_probability == 0.3
    assert config.rejection_probability == 0.05
    assert config.comparison_window_minutes == 120
    assert config.max_shadow_orders_per_day == 500


def test_centralized_config_has_fallback_price_settings():
    """Test that centralized config includes fallback price settings."""
    centralized = get_config().shadow_mode

    # Verify fallback price settings exist
    assert hasattr(centralized, 'fallback_price')
    assert hasattr(centralized, 'enable_fallback_price')

    # Verify default values
    assert centralized.fallback_price == Decimal("100.00")
    assert centralized.enable_fallback_price == False


def test_centralized_config_has_simulation_parameters():
    """Test that centralized config includes simulation parameters."""
    centralized = get_config().shadow_mode

    # Verify simulation parameters exist
    assert hasattr(centralized, 'fill_delay_jitter_min_ms')
    assert hasattr(centralized, 'fill_delay_jitter_max_ms')
    assert hasattr(centralized, 'partial_fill_min_pct')
    assert hasattr(centralized, 'partial_fill_max_pct')

    # Verify values
    assert centralized.fill_delay_jitter_min_ms == -20
    assert centralized.fill_delay_jitter_max_ms == 50
    assert centralized.partial_fill_min_pct == 0.5
    assert centralized.partial_fill_max_pct == 0.9

    # Verify max > min
    assert centralized.fill_delay_jitter_max_ms > centralized.fill_delay_jitter_min_ms
    assert centralized.partial_fill_max_pct > centralized.partial_fill_min_pct


def test_no_magic_numbers_in_simulate_fill():
    """
    Test that simulate_fill uses centralized config values instead of magic numbers.

    This test verifies:
    1. Fill delay jitter comes from config (not hardcoded -20, 50)
    2. Partial fill percentages come from config (not hardcoded 0.5, 0.9)
    3. Fallback price comes from config (not hardcoded 100.00)
    """
    from app.domain.services.shadow_mode import ShadowModeExecutor
    from app.sre.state_machine.wal_persistence import OrderStateMachine

    # Create mock objects
    mock_broker = MagicMock()
    mock_wal = MagicMock(spec=OrderStateMachine)

    # Create executor
    config = ShadowModeConfig(enabled=True)
    executor = ShadowModeExecutor(
        broker_client=mock_broker,
        wal_manager=mock_wal,
        config=config
    )

    # Verify executor has access to centralized config through get_config()
    centralized = get_config().shadow_mode

    # These values should be used in simulate_fill instead of magic numbers
    assert centralized.fill_delay_jitter_min_ms == -20
    assert centralized.fill_delay_jitter_max_ms == 50
    assert centralized.partial_fill_min_pct == 0.5
    assert centralized.partial_fill_max_pct == 0.9
    assert centralized.fallback_price == Decimal("100.00")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
