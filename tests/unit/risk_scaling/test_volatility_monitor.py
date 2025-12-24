"""
Unit tests for VolatilityMonitor (PHASE 3)

Tests ATR calculation, volatility scaling, and spike detection.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.services.risk_scaling.volatility_monitor import VolatilityMonitor, PriceData


class TestVolatilityMonitor:
    """Test suite for VolatilityMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance."""
        return VolatilityMonitor(atr_period=14)

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        prices = []
        base_time = datetime.now()
        base_price = Decimal("100")

        for i in range(30):
            prices.append(
                PriceData(
                    timestamp=base_time,
                    open=base_price + Decimal(str(i * 0.1)),
                    high=base_price + Decimal(str(i * 0.15)),
                    low=base_price + Decimal(str(i * 0.05)),
                    close=base_price + Decimal(str(i * 0.12)),
                )
            )

        return prices

    def test_initialization(self, monitor):
        """Test monitor initializes correctly."""
        assert monitor.atr_period == 14
        assert monitor.atr_history == {}
        assert monitor.volatility_spikes == {}

    def test_calculate_atr(self, monitor, sample_prices):
        """Test ATR calculation."""
        atr = monitor.calculate_atr(sample_prices)
        assert isinstance(atr, Decimal)
        assert atr > Decimal("0")

    def test_calculate_atr_insufficient_data(self, monitor):
        """Test ATR raises error with insufficient data."""
        prices = [
            PriceData(
                timestamp=datetime.now(),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
            )
        ]

        with pytest.raises(ValueError, match="Need at least 14"):
            monitor.calculate_atr(prices, period=14)

    def test_calculate_volatility_scale_low_vol(self, monitor):
        """Test scaling with low volatility."""
        current_atr = Decimal("0.5")
        average_atr = Decimal("1.0")

        scale = monitor.calculate_volatility_scale("TEST", current_atr, average_atr)
        # Scale should be > 1.0 (increased positions in low vol)
        assert scale > Decimal("1.0")
        assert scale <= Decimal("1.5")

    def test_calculate_volatility_scale_high_vol(self, monitor):
        """Test scaling with high volatility."""
        current_atr = Decimal("2.0")
        average_atr = Decimal("1.0")

        scale = monitor.calculate_volatility_scale("TEST", current_atr, average_atr)
        # Scale should be < 1.0 (reduced positions in high vol)
        assert scale < Decimal("1.0")
        assert scale >= Decimal("0.5")

    def test_calculate_volatility_scale_normal(self, monitor):
        """Test scaling with normal volatility."""
        current_atr = Decimal("1.0")
        average_atr = Decimal("1.0")

        scale = monitor.calculate_volatility_scale("TEST", current_atr, average_atr)
        # Scale should be 1.0 (baseline)
        assert scale == Decimal("1.0")

    def test_calculate_volatility_scale_bounds(self, monitor):
        """Test scaling respects bounds (0.5 to 1.5)."""
        # Test with extreme low
        scale = monitor.calculate_volatility_scale("TEST", Decimal("0.1"), Decimal("1.0"))
        assert scale == Decimal("1.5")  # capped at max

        # Test with extreme high
        scale = monitor.calculate_volatility_scale("TEST", Decimal("10.0"), Decimal("1.0"))
        assert scale == Decimal("0.5")  # capped at min

    def test_is_volatility_spike_true(self, monitor):
        """Test spike detection returns True for spike."""
        current_atr = Decimal("2.5")
        average_atr = Decimal("1.0")

        is_spike = monitor.is_volatility_spike("TEST", current_atr, average_atr)
        assert is_spike is True

    def test_is_volatility_spike_false(self, monitor):
        """Test spike detection returns False for normal vol."""
        current_atr = Decimal("1.0")
        average_atr = Decimal("1.0")

        is_spike = monitor.is_volatility_spike("TEST", current_atr, average_atr)
        assert is_spike is False

    def test_get_volatility_regime_very_low(self, monitor):
        """Test regime classification for very low volatility."""
        regime = monitor.get_volatility_regime(Decimal("0.5"), Decimal("1.0"))
        assert regime == "very_low"

    def test_get_volatility_regime_low(self, monitor):
        """Test regime classification for low volatility."""
        regime = monitor.get_volatility_regime(Decimal("0.85"), Decimal("1.0"))
        assert regime == "low"

    def test_get_volatility_regime_normal(self, monitor):
        """Test regime classification for normal volatility."""
        regime = monitor.get_volatility_regime(Decimal("1.0"), Decimal("1.0"))
        assert regime == "normal"

    def test_get_volatility_regime_high(self, monitor):
        """Test regime classification for high volatility."""
        regime = monitor.get_volatility_regime(Decimal("1.3"), Decimal("1.0"))
        assert regime == "high"

    def test_get_volatility_regime_very_high(self, monitor):
        """Test regime classification for very high volatility."""
        regime = monitor.get_volatility_regime(Decimal("2.0"), Decimal("1.0"))
        assert regime == "very_high"

    def test_get_recent_volatility_spikes_empty(self, monitor):
        """Test getting spikes when none exist."""
        spikes = monitor.get_recent_volatility_spikes("TEST")
        assert spikes == []

    def test_get_recent_volatility_spikes_filtered(self, monitor):
        """Test spike filtering by lookback window."""
        # Record some spikes
        monitor.is_volatility_spike("TEST", Decimal("2.5"), Decimal("1.0"))

        # All spikes should be within recent window
        spikes = monitor.get_recent_volatility_spikes("TEST", lookback_minutes=60)
        assert len(spikes) > 0

    def test_calculate_atr_std_dev(self, monitor, sample_prices):
        """Test standard deviation calculation."""
        # Calculate average ATR to populate history
        monitor.calculate_average_atr("TEST", prices=sample_prices)

        std_dev = monitor.calculate_atr_std_dev("TEST")
        assert isinstance(std_dev, Decimal)

    def test_calculate_average_atr(self, monitor, sample_prices):
        """Test average ATR calculation."""
        avg_atr = monitor.calculate_average_atr("TEST", prices=sample_prices)
        assert isinstance(avg_atr, Decimal)
        assert avg_atr > Decimal("0")

    def test_calculate_average_atr_no_history(self, monitor):
        """Test average ATR raises error with no history."""
        with pytest.raises(ValueError, match="No ATR"):
            monitor.calculate_average_atr("UNKNOWN")

    def test_true_range_calculation(self):
        """Test true range calculation for price data."""
        current = PriceData(
            timestamp=datetime.now(),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
        )

        # Without previous close
        tr = current.true_range()
        assert tr == Decimal("3")  # high - low = 102 - 99

        # With previous close
        prev_close = Decimal("98")
        tr = current.true_range(prev_close)
        # Max(102-99, |102-98|, |99-98|) = Max(3, 4, 1) = 4
        assert tr == Decimal("4")

    def test_multiple_symbols_tracked(self, monitor, sample_prices):
        """Test monitor tracks multiple symbols independently."""
        monitor.calculate_atr(sample_prices)
        scale1 = monitor.calculate_volatility_scale("AAPL", Decimal("1.0"), Decimal("1.0"))

        # Different ATR for different symbol
        scale2 = monitor.calculate_volatility_scale("MSFT", Decimal("2.0"), Decimal("1.0"))

        assert scale1 == Decimal("1.0")
        assert scale2 < Decimal("1.0")
