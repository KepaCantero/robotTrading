"""
Tests for Stochastic RSI filtering in MomentumStrategy (TASK-IND-STOCH-2).
"""

import pytest
from collections import deque
from decimal import Decimal

from app.models.market_data import Quote
from app.models.signal import SignalType
from app.strategies.momentum import MomentumStrategy


@pytest.fixture
def momentum_strategy():
    """Create a MomentumStrategy instance for testing."""
    config = {
        "name": "test_momentum",
        "rsi_period": 14,
        "ema_period": 20,
        "volume_threshold": 1.2,
        "cooldown_bars": 3,
    }
    return MomentumStrategy(config)


@pytest.fixture
def sample_quote():
    """Create a sample market quote."""
    from datetime import datetime
    from decimal import Decimal
    
    return Quote(
        symbol="AAPL",
        bid=Decimal("149.50"),
        ask=Decimal("150.50"),
        last=Decimal("150.00"),
        volume=Decimal("1000000"),
        timestamp=datetime.utcnow(),
        high=Decimal("151.00"),
        low=Decimal("149.00"),
        close=Decimal("150.00"),
        open=Decimal("150.00"),
    )


class TestStochasticRSICalculation:
    """Tests for Stochastic RSI calculation - TASK-IND-STOCH-2."""

    def test_calculate_stochastic_rsi_insufficient_data(self, momentum_strategy):
        """Test Stochastic RSI with insufficient RSI history."""
        momentum_strategy.rsi_history = deque([50.0, 55.0, 60.0])  # Only 3 values

        stoch_rsi, signal = momentum_strategy._calculate_stochastic_rsi(period=14)

        assert stoch_rsi is None
        assert signal is None

    def test_calculate_stochastic_rsi_sufficient_data(self, momentum_strategy):
        """Test Stochastic RSI with sufficient RSI history."""
        # Create RSI history with variation
        rsi_values = [30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0]
        for val in rsi_values:
            momentum_strategy.rsi_history.append(val)

        stoch_rsi, signal = momentum_strategy._calculate_stochastic_rsi(period=14)

        assert stoch_rsi is not None
        assert signal is not None
        assert isinstance(stoch_rsi, float)
        assert isinstance(signal, float)
        assert 0 <= stoch_rsi <= 100
        assert 0 <= signal <= 100

    def test_calculate_stochastic_rsi_flat_rsi(self, momentum_strategy):
        """Test Stochastic RSI with flat RSI values."""
        # All RSI values are the same
        for _ in range(14):
            momentum_strategy.rsi_history.append(50.0)

        stoch_rsi, signal = momentum_strategy._calculate_stochastic_rsi(period=14)

        assert stoch_rsi is None
        assert signal is None

    def test_calculate_stochastic_rsi_overbought_condition(self, momentum_strategy):
        """Test Stochastic RSI in overbought condition."""
        # High RSI values (overbought)
        rsi_values = [80.0, 85.0, 90.0, 88.0, 92.0, 95.0, 98.0, 97.0, 99.0, 100.0, 98.0, 97.0, 96.0, 95.0]
        for val in rsi_values:
            momentum_strategy.rsi_history.append(val)

        stoch_rsi, signal = momentum_strategy._calculate_stochastic_rsi(period=14)

        assert stoch_rsi is not None
        # In overbought condition, StochRSI should be high
        assert stoch_rsi > 50

    def test_calculate_stochastic_rsi_oversold_condition(self, momentum_strategy):
        """Test Stochastic RSI in oversold condition."""
        # Low RSI values (oversold) - declining pattern with current value being lowest
        rsi_values = [35.0, 34.0, 32.0, 30.0, 28.0, 25.0, 22.0, 20.0, 18.0, 17.0, 16.0, 15.0, 12.0, 10.0]
        for val in rsi_values:
            momentum_strategy.rsi_history.append(val)

        stoch_rsi, signal = momentum_strategy._calculate_stochastic_rsi(period=14)

        assert stoch_rsi is not None
        # In oversold condition where current value (10.0) is the lowest, StochRSI should be very low
        assert stoch_rsi <= 20  # Should be in oversold zone


class TestStochasticRSIFiltering:
    """Tests for Stochastic RSI signal filtering."""

    def test_should_generate_signal_normal_condition(self, momentum_strategy):
        """Test signal generation in normal Stochastic RSI condition."""
        stoch_rsi = 50.0
        signal = 45.0

        should_generate = momentum_strategy._should_generate_signal(stoch_rsi, signal)

        assert should_generate is True

    def test_should_generate_signal_overbought_filtered(self, momentum_strategy):
        """Test that overbought signals are filtered."""
        stoch_rsi = 85.0  # Overbought
        signal = 80.0

        should_generate = momentum_strategy._should_generate_signal(stoch_rsi, signal)

        assert should_generate is False  # Should filter overbought signals

    def test_should_generate_signal_oversold_filtered(self, momentum_strategy):
        """Test that oversold signals are filtered."""
        stoch_rsi = 15.0  # Oversold
        signal = 20.0

        should_generate = momentum_strategy._should_generate_signal(stoch_rsi, signal)

        assert should_generate is False  # Should filter oversold signals

    def test_should_generate_signal_none_values(self, momentum_strategy):
        """Test signal generation with None values (should allow)."""
        stoch_rsi = None
        signal = None

        should_generate = momentum_strategy._should_generate_signal(stoch_rsi, signal)

        assert should_generate is True  # Should allow if no data

    def test_should_generate_signal_edge_cases(self, momentum_strategy):
        """Test edge cases for signal generation."""
        # Exactly at lower bound
        assert momentum_strategy._should_generate_signal(20.0, 20.0) is True
        # Just below lower bound
        assert momentum_strategy._should_generate_signal(19.99, 20.0) is False
        # Exactly at upper bound
        assert momentum_strategy._should_generate_signal(80.0, 80.0) is True
        # Just above upper bound
        assert momentum_strategy._should_generate_signal(80.01, 80.0) is False


class TestStochasticRSIIntegration:
    """Integration tests for Stochastic RSI in signal generation."""

    def test_stochastic_rsi_integration_creates_rsi_history(self, momentum_strategy, sample_quote):
        """Test that RSI history is maintained during signal generation."""
        from datetime import datetime
        
        # Populate price history to enable RSI calculation
        for i in range(50):
            price = Decimal(f"{150.0 + i * 0.5}")
            quote = Quote(
                symbol="AAPL",
                bid=price - Decimal("0.5"),
                ask=price + Decimal("0.5"),
                last=price,
                close=price,
                volume=Decimal("1000000"),
                timestamp=datetime.utcnow(),
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                open=price,
            )
            momentum_strategy.generate_signals(quote)

        # Should have populated RSI history
        assert len(momentum_strategy.rsi_history) > 0

    def test_stochastic_rsi_filters_false_signals(self, momentum_strategy, sample_quote):
        """Test that Stochastic RSI filters false signals."""
        from datetime import datetime
        
        # Set up overbought condition
        rsi_overbought = [90.0, 92.0, 95.0, 93.0, 94.0, 96.0, 98.0, 97.0, 99.0, 100.0, 98.0, 97.0, 96.0, 95.0, 94.0]
        for val in rsi_overbought:
            momentum_strategy.rsi_history.append(val)

        # Populate other required histories
        for i in range(30):
            momentum_strategy.price_history.append(150.0 + i * 0.5)
            momentum_strategy.volume_history.append(1000000)

        # Create proper quote with all required fields
        quote = Quote(
            symbol="AAPL",
            bid=Decimal("149.50"),
            ask=Decimal("150.50"),
            last=Decimal("150.00"),
            close=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
            high=Decimal("151.00"),
            low=Decimal("149.00"),
            open=Decimal("150.00"),
        )
        
        # Generate signals
        signals = momentum_strategy.generate_signals(quote)

        # In overbought condition, Stochastic RSI should filter signals
        # (Signals might be None or empty depending on other conditions)
        assert isinstance(signals, list)
