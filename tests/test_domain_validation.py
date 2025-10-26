"""
Tests for Domain Validation in Models
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestSignalDomainValidation:
    """Test domain validation for Signal model."""

    def test_valid_signal(self):
        """Test valid signal passes validation."""
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150.0"),
            volume=Decimal("1000"),
        )
        assert signal.confidence == 80.0
        assert signal.price == Decimal("150.0")

    def test_confidence_out_of_range(self):
        """Test confidence validation."""
        with pytest.raises(ValidationError):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=150.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("100.0"),
                volume=Decimal("1000"),
            )

    def test_negative_price(self):
        """Test price validation."""
        with pytest.raises(ValidationError):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("-100.0"),
                volume=Decimal("1000"),
            )

    def test_excessive_price(self):
        """Test price limit validation."""
        with pytest.raises(ValidationError):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("2000000.0"),
                volume=Decimal("1000"),
            )

    def test_strong_signal_low_confidence(self):
        """Test signal consistency validation."""
        with pytest.raises(ValueError, match="Strong signal"):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=50.0,  # Low for strong signal
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("100.0"),
                volume=Decimal("1000"),
            )

    def test_hold_signal_very_high_confidence(self):
        """Test HOLD signal consistency validation."""
        with pytest.raises(ValueError, match="HOLD signal"):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.HOLD,
                strength=SignalStrength.STRONG,
                confidence=95.0,  # Too high for HOLD
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("100.0"),
                volume=Decimal("1000"),
            )
