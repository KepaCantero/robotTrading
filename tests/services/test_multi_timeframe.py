"""
Tests for multi-timeframe confirmation (TASK-MET-MULTI-1).
"""

import pytest
from decimal import Decimal

from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.multi_timeframe_service import (
    MultiTimeframeConfirmation,
    TimeframeSignal,
)


class TestTimeframeSignal:
    """Tests for TimeframeSignal class."""

    @pytest.fixture
    def sample_signal(self):
        """Create a sample signal."""
        from datetime import datetime
        
        return Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=90.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )

    def test_timeframe_signal_creation(self, sample_signal):
        """Test TimeframeSignal creation."""
        from datetime import datetime

        timeframe_signal = TimeframeSignal(sample_signal, "1h", datetime.utcnow())

        assert timeframe_signal.signal == sample_signal
        assert timeframe_signal.timeframe == "1h"
        assert timeframe_signal.timestamp is not None


class TestMultiTimeframeConfirmation:
    """Tests for MultiTimeframeConfirmation class."""

    @pytest.fixture
    def sample_signal(self):
        """Create a sample signal."""
        from datetime import datetime
        
        return Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=90.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )

    def test_service_initialization(self):
        """Test MultiTimeframeConfirmation initialization."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h", "1d"], min_confirmations=2)

        assert service.timeframes == ["15m", "1h", "4h", "1d"]
        assert service.min_confirmations == 2
        assert len(service.signal_history) == 0
        assert len(service.confirmed_signals) == 0

    def test_add_signal_invalid_timeframe(self, sample_signal):
        """Test adding signal with invalid timeframe."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        confirmed = service.add_signal(sample_signal, "invalid")

        assert confirmed is False

    def test_add_signal_insufficient_confirmations(self, sample_signal):
        """Test adding signal without enough confirmations."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        confirmed = service.add_signal(sample_signal, "15m")

        assert confirmed is False  # Not enough confirmations yet

    def test_add_signal_with_confirmations(self, sample_signal):
        """Test adding signal with sufficient confirmations."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        # Add first signal
        confirmed1 = service.add_signal(sample_signal, "15m")
        assert confirmed1 is False

        # Add second signal from different timeframe
        from datetime import datetime
        
        signal2 = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=85.0,
            priority_score=70.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        confirmed2 = service.add_signal(signal2, "1h")

        assert confirmed2 is True  # Should be confirmed now

    def test_get_confirmed_signals(self, sample_signal):
        """Test getting confirmed signals."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        # Add signals to trigger confirmation
        service.add_signal(sample_signal, "15m")
        service.add_signal(sample_signal, "1h")

        confirmed = service.get_confirmed_signals()

        assert len(confirmed) > 0
        assert confirmed[0]["symbol"] == "AAPL"
        assert SignalType.BUY in confirmed[0]["signal_type"]

    def test_get_confirmed_signals_by_symbol(self, sample_signal):
        """Test getting confirmed signals filtered by symbol."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        service.add_signal(sample_signal, "15m")
        service.add_signal(sample_signal, "1h")

        # Add signal for different symbol
        from datetime import datetime
        
        signal2 = Signal(
            symbol="MSFT",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=85.0,
            priority_score=70.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("200.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        service.add_signal(signal2, "15m")
        service.add_signal(signal2, "1h")

        confirmed_aapl = service.get_confirmed_signals(symbol="AAPL")
        confirmed_msft = service.get_confirmed_signals(symbol="MSFT")

        assert len(confirmed_aapl) > 0
        assert len(confirmed_msft) > 0

    def test_get_confirmation_stats(self, sample_signal):
        """Test getting confirmation statistics."""
        service = MultiTimeframeConfirmation(timeframes=["15m", "1h", "4h"], min_confirmations=2)

        # Add some signals - need to create new signals to avoid timestamp collision
        from datetime import datetime
        
        signal1 = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=90.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        
        signal2 = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=85.0,
            priority_score=70.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.50"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        
        service.add_signal(signal1, "15m")
        service.add_signal(signal2, "1h")

        stats = service.get_confirmation_stats()

        assert "total_confirmations" in stats
        assert "confirmed_by_type" in stats
        assert "unique_symbols" in stats
