"""
Tests for momentum strategy models.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.models.momentum import MomentumSignal, MomentumType


class TestMomentumModels:
    """Test momentum model functionality."""

    def test_momentum_signal_creation(self):
        """Test basic momentum signal creation."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            strength=75.0,
            direction="BUY",
            confidence=85.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("50000"),
            volume_change_pct=5.26,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        assert signal.symbol == "AAPL"
        assert signal.direction == "BUY"
        assert signal.strength == 75.0

    def test_momentum_signal_properties(self):
        """Test momentum signal properties."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            strength=75.0,
            direction="BUY",
            confidence=85.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("50000"),
            volume_change_pct=5.26,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        assert signal.is_expired is False
        assert signal.momentum_score > 0
