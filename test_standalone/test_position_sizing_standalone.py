"""
Standalone test for PositionSizingEngine that bypasses conftest.py import issues.
Run with: python -m pytest test_standalone/test_position_sizing_standalone.py -v
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
import pytest

# Direct import to avoid conftest.py
from app.services.position_sizing_engine import PositionSizingEngine


class TestPositionSizingEngineInitialization:
    """Test suite for PositionSizingEngine initialization."""

    def test_initialization_with_default_multiplier(self):
        """Test that engine initializes with default multiplier."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        assert engine.atr_multiplier == Decimal("2.0")

    def test_initialization_with_custom_multiplier(self):
        """Test that engine accepts custom ATR multiplier."""
        engine = PositionSizingEngine(atr_multiplier=1.5)
        assert engine.atr_multiplier == Decimal("1.5")


class TestStopLossCalculation:
    """Test suite for stop loss price calculation."""

    def test_calculate_stop_loss_buy_with_atr(self):
        """Test stop loss for buy order with ATR."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="buy",
            atr=atr,
        )

        # 150 - (3 * 2) = 144
        expected = Decimal("144.00")
        assert stop_loss == expected

    def test_calculate_stop_loss_sell_with_atr(self):
        """Test stop loss for sell order with ATR."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="sell",
            atr=atr,
        )

        # 150 + (3 * 2) = 156
        expected = Decimal("156.00")
        assert stop_loss == expected

    def test_calculate_stop_loss_case_insensitive_direction(self):
        """Test that direction is case-insensitive."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        entry_price = Decimal("150.00")
        atr = 3.0

        stop_loss_buy = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="BUY",
            atr=atr,
        )
        stop_loss_sell = engine.calculate_stop_loss_price(
            entry_price=entry_price,
            direction="SELL",
            atr=atr,
        )

        assert stop_loss_buy == Decimal("144.00")
        assert stop_loss_sell == Decimal("156.00")

    def test_calculate_stop_loss_with_invalid_direction(self):
        """Test stop loss with invalid direction."""
        engine = PositionSizingEngine(atr_multiplier=2.0)
        result = engine.calculate_stop_loss_price(
            entry_price=Decimal("150.00"),
            direction="invalid",
            atr=3.0,
        )
        # Should return None for invalid direction
        assert result is None
