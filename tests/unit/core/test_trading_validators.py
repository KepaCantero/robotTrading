"""
Tests for TradingValidator - CRITICAL for financial safety.

This module tests the validation logic that prevents catastrophic trading errors.
These tests are essential for ensuring the safety of the trading system.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.core.trading_validators import TradingValidator


class TestTradingValidator:
    """Test trading validation logic."""

    def test_validate_position_size_accepts_valid(self):
        """Validator accepts valid position sizes."""
        validator = TradingValidator()

        # 10% of capital - should pass
        assert (
            validator.validate_position_size(
                capital=Decimal("100000"),
                position_size=Decimal("10000"),
                max_position_percent=Decimal("0.25"),
            )
            is True
        )

    def test_validate_position_size_rejects_too_large(self):
        """Validator rejects position exceeding maximum percentage."""
        validator = TradingValidator()

        # 30% exceeds 25% max
        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_position_size(
                capital=Decimal("100000"),
                position_size=Decimal("30000"),
                max_position_percent=Decimal("0.25"),
            )

    def test_validate_position_size_rejects_zero_capital(self):
        """Validator rejects zero or negative capital."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Capital must be positive"):
            validator.validate_position_size(capital=Decimal("0"), position_size=Decimal("1000"))

    def test_validate_position_size_rejects_zero_position(self):
        """Validator rejects zero or negative position size."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Position size must be positive"):
            validator.validate_position_size(capital=Decimal("100000"), position_size=Decimal("0"))

    def test_validate_position_size_default_max_percent(self):
        """Validator uses default 25% max when not specified."""
        validator = TradingValidator()

        # 25% should pass
        assert (
            validator.validate_position_size(
                capital=Decimal("100000"), position_size=Decimal("25000")
            )
            is True
        )

        # 26% should fail (exceeds default 25%)
        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_position_size(
                capital=Decimal("100000"), position_size=Decimal("26000")
            )

    def test_validate_position_size_invalid_max_percent(self):
        """Validator rejects invalid max_position_percent values."""
        validator = TradingValidator()

        # Too low (< 1%)
        with pytest.raises(ValueError, match="max_position_percent must be between"):
            validator.validate_position_size(
                capital=Decimal("100000"),
                position_size=Decimal("1000"),
                max_position_percent=Decimal("0.001"),
            )

        # Too high (> 100%)
        with pytest.raises(ValueError, match="max_position_percent must be between"):
            validator.validate_position_size(
                capital=Decimal("100000"),
                position_size=Decimal("1000"),
                max_position_percent=Decimal("1.5"),
            )

    def test_validate_stop_loss_requires_stop_loss(self):
        """Validator requires stop-loss to be defined."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Stop-loss is REQUIRED"):
            validator.validate_stop_loss(entry_price=Decimal("100"), stop_loss=None, side="long")

    def test_validate_stop_loss_long_position(self):
        """Validator validates long position stop-loss."""
        validator = TradingValidator()

        # Stop-loss below entry is valid for long
        assert (
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), side="long"
            )
            is True
        )

        # Stop-loss above entry is invalid for long
        with pytest.raises(ValueError, match="must be BELOW"):
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("105"), side="long"
            )

    def test_validate_stop_loss_short_position(self):
        """Validator validates short position stop-loss."""
        validator = TradingValidator()

        # Stop-loss above entry is valid for short
        assert (
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("105"), side="short"
            )
            is True
        )

        # Stop-loss below entry is invalid for short
        with pytest.raises(ValueError, match="must be ABOVE"):
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), side="short"
            )

    def test_validate_stop_loss_rejects_invalid_side(self):
        """Validator rejects invalid trade side."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Invalid trade side"):
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), side="invalid"
            )

    def test_validate_stop_loss_rejects_zero_entry_price(self):
        """Validator rejects zero or negative entry price."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Entry price must be positive"):
            validator.validate_stop_loss(
                entry_price=Decimal("0"), stop_loss=Decimal("95"), side="long"
            )

    def test_validate_stop_loss_rejects_zero_stop_loss(self):
        """Validator rejects zero or negative stop-loss price."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Stop-loss price must be positive"):
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("0"), side="long"
            )

    def test_validate_risk_reward_ratio(self):
        """Validator validates risk/reward ratio."""
        validator = TradingValidator()

        # 3:1 ratio is good (2:1 minimum)
        assert (
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("110")
            )
            is True
        )

        # 1:1 ratio fails (below 2:1 minimum)
        with pytest.raises(ValueError, match="Reward/risk ratio"):
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=Decimal("105")
            )

    def test_validate_risk_reward_no_take_profit(self):
        """Validator allows missing take-profit (skips validation)."""
        validator = TradingValidator()

        # Should pass without take-profit
        assert (
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), take_profit=None
            )
            is True
        )

    def test_validate_risk_reward_requires_stop_loss(self):
        """Validator requires stop-loss for risk/reward calculation."""
        validator = TradingValidator()

        with pytest.raises(ValueError, match="Stop-loss is required"):
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"), stop_loss=None, take_profit=Decimal("110")
            )

    def test_validate_risk_reward_custom_min_ratio(self):
        """Validator respects custom minimum reward/risk ratio."""
        validator = TradingValidator()

        # 1.5:1 ratio fails with default 2:1 minimum
        with pytest.raises(ValueError, match="Reward/risk ratio"):
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"),
                stop_loss=Decimal("95"),
                take_profit=Decimal("107.5"),
                min_reward_risk_ratio=Decimal("2.0"),
            )

        # But passes with 1.5:1 minimum
        assert (
            validator.validate_trade_risk_reward(
                entry_price=Decimal("100"),
                stop_loss=Decimal("95"),
                take_profit=Decimal("107.5"),
                min_reward_risk_ratio=Decimal("1.5"),
            )
            is True
        )

    def test_validate_trading_hours_default(self):
        """Validator uses default market hours (9 AM - 4 PM)."""
        validator = TradingValidator()

        # 10 AM - should pass
        assert validator.validate_trading_hours(current_time=datetime(2024, 1, 1, 10, 0)) is True

        # 8 AM - should fail
        with pytest.raises(ValueError, match="Trading is not allowed"):
            validator.validate_trading_hours(current_time=datetime(2024, 1, 1, 8, 0))

    def test_validate_trading_hours_custom(self):
        """Validator respects custom allowed hours."""
        validator = TradingValidator()

        # Allow extended hours (8 AM - 8 PM)
        allowed_hours = set(range(8, 21))

        assert (
            validator.validate_trading_hours(
                current_time=datetime(2024, 1, 1, 8, 0), allowed_hours=allowed_hours
            )
            is True
        )

        assert (
            validator.validate_trading_hours(
                current_time=datetime(2024, 1, 1, 20, 0), allowed_hours=allowed_hours
            )
            is True
        )

        # 7 AM should fail
        with pytest.raises(ValueError, match="Trading is not allowed"):
            validator.validate_trading_hours(
                current_time=datetime(2024, 1, 1, 7, 0), allowed_hours=allowed_hours
            )

    def test_validate_stop_loss_case_insensitive(self):
        """Validator handles case-insensitive side parameter."""
        validator = TradingValidator()

        # LONG (uppercase)
        assert (
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), side="LONG"
            )
            is True
        )

        # Long (mixed case)
        assert (
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("95"), side="Long"
            )
            is True
        )

        # SHORT (uppercase)
        assert (
            validator.validate_stop_loss(
                entry_price=Decimal("100"), stop_loss=Decimal("105"), side="SHORT"
            )
            is True
        )
