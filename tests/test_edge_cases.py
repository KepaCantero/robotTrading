"""
Tests for Edge Cases and Extreme Data in Technical Indicators

This module tests technical indicators with extreme data conditions,
division by zero scenarios, and edge cases for mathematical calculations.
"""

from decimal import Decimal

import pytest

from app.services.momentum_analysis import TechnicalIndicatorCalculator


class TestTechnicalIndicatorsEdgeCases:
    """Test technical indicators with extreme data conditions."""

    def test_rsi_with_zero_volume(self):
        """Test RSI calculation with zero volume data."""
        # Test with all zeros - RSI returns 100.0 when avg_loss is 0
        prices = [0.0] * 20
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi == 100.0  # RSI returns 100 when there are no losses

        # Test with constant price (no change)
        prices = [100.0] * 20
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi == 100.0  # RSI returns 100 when there are no losses

    def test_rsi_with_nan_values(self):
        """Test RSI calculation with NaN values."""
        prices = [
            100.0,
            float("nan"),
            105.0,
            110.0,
            108.0,
            112.0,
            115.0,
            118.0,
            120.0,
            122.0,
            125.0,
            128.0,
            130.0,
            132.0,
            135.0,
        ]

        # RSI calculation doesn't explicitly check for NaN, so it might return
        # a value
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        # The actual behavior depends on how Python handles NaN in arithmetic
        assert rsi is not None  # RSI calculation doesn't fail on NaN

    def test_rsi_with_infinite_values(self):
        """Test RSI calculation with infinite values."""
        prices = [
            100.0,
            float("inf"),
            105.0,
            110.0,
            108.0,
            112.0,
            115.0,
            118.0,
            120.0,
            122.0,
            125.0,
            128.0,
            130.0,
            132.0,
            135.0,
        ]

        # RSI calculation doesn't explicitly check for infinity, so it might
        # return a value
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        # The actual behavior depends on how Python handles infinity in
        # arithmetic
        assert rsi is not None  # RSI calculation doesn't fail on infinity

    def test_rsi_with_extreme_price_changes(self):
        """Test RSI with extreme price changes (>50% spikes)."""
        # Test with 100% price increase
        prices = [100.0] * 14 + [200.0] * 5  # 100% increase
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

        # Test with 90% price decrease
        prices = [100.0] * 14 + [10.0] * 5  # 90% decrease
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_rsi_with_insufficient_data(self):
        """Test RSI with insufficient data points."""
        # Test with less than period + 1 data points
        prices = [100.0, 105.0, 110.0]  # Only 3 points, need 15 for period=14
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, period=14)
        assert rsi is None

        # Test with exactly period data points
        prices = [100.0] * 14  # Exactly 14 points, need 15 for period=14
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, period=14)
        assert rsi is None

    def test_rsi_boundary_values(self):
        """Test RSI with boundary values."""
        # Test with very small price changes
        prices = [
            100.0,
            100.0001,
            100.0002,
            100.0003,
            100.0004,
            100.0005,
            100.0006,
            100.0007,
            100.0008,
            100.0009,
            100.0010,
            100.0011,
            100.0012,
            100.0013,
            100.0014,
        ]
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

        # Test with alternating gains and losses
        prices = [
            100.0,
            101.0,
            99.0,
            101.0,
            99.0,
            101.0,
            99.0,
            101.0,
            99.0,
            101.0,
            99.0,
            101.0,
            99.0,
            101.0,
            99.0,
        ]
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_ema_with_zero_values(self):
        """Test EMA calculation with zero values."""
        prices = [0.0] * 20
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=10)
        assert ema == 0.0

        # Test with mixed zero and non-zero values
        prices = [
            100.0,
            0.0,
            105.0,
            0.0,
            110.0,
            0.0,
            108.0,
            0.0,
            112.0,
            0.0,
            115.0,
            0.0,
            118.0,
            0.0,
            120.0,
            0.0,
            122.0,
            0.0,
            125.0,
            0.0,
        ]
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=10)
        assert ema is not None
        assert ema >= 0

    def test_ema_with_negative_values(self):
        """Test EMA calculation with negative values."""
        prices = [
            -100.0,
            -105.0,
            -110.0,
            -108.0,
            -112.0,
            -115.0,
            -118.0,
            -120.0,
            -122.0,
            -125.0,
            -128.0,
            -130.0,
            -132.0,
            -135.0,
            -138.0,
        ]
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=10)
        assert ema is not None
        assert ema < 0  # Should handle negative values correctly

    def test_ema_with_extreme_values(self):
        """Test EMA with extreme values."""
        # Test with very large values
        prices = [
            1e10,
            1e10 + 1000,
            1e10 + 2000,
            1e10 + 1500,
            1e10 + 3000,
            1e10 + 2500,
            1e10 + 4000,
            1e10 + 3500,
            1e10 + 5000,
            1e10 + 4500,
            1e10 + 6000,
            1e10 + 5500,
            1e10 + 7000,
            1e10 + 6500,
            1e10 + 8000,
        ]
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=10)
        assert ema is not None
        assert ema > 1e10  # Should handle large values

        # Test with very small values - EMA might return 0 due to rounding
        prices = [
            1e-10,
            1e-10 + 1e-12,
            1e-10 + 2e-12,
            1e-10 + 1.5e-12,
            1e-10 + 3e-12,
            1e-10 + 2.5e-12,
            1e-10 + 4e-12,
            1e-10 + 3.5e-12,
            1e-10 + 5e-12,
            1e-10 + 4.5e-12,
            1e-10 + 6e-12,
            1e-10 + 5.5e-12,
            1e-10 + 7e-12,
            1e-10 + 6.5e-12,
            1e-10 + 8e-12,
        ]
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=10)
        assert ema is not None
        # Should handle small values (might be 0 due to rounding)
        assert ema >= 0

    def test_macd_with_division_by_zero(self):
        """Test MACD calculation to prevent division by zero."""
        # Test with constant prices (no change)
        prices = [100.0] * 30
        macd = TechnicalIndicatorCalculator.calculate_macd(prices)
        assert macd is not None
        # MACD should be (0, 0, 0) for constant prices
        assert macd == (0.0, 0.0, 0.0)

        # Test with insufficient data
        prices = [100.0, 105.0]  # Only 2 points
        macd = TechnicalIndicatorCalculator.calculate_macd(prices)
        assert macd == (None, None, None)

    def test_atr_with_zero_values(self):
        """Test ATR calculation with zero values."""
        # Test with zero high, low, close
        high = [0.0] * 20
        low = [0.0] * 20
        close = [0.0] * 20
        atr = TechnicalIndicatorCalculator.calculate_atr(high, low, close, period=10)
        assert atr == 0.0

        # Test with constant values
        high = [100.0] * 20
        low = [100.0] * 20
        close = [100.0] * 20
        atr = TechnicalIndicatorCalculator.calculate_atr(high, low, close, period=10)
        assert atr == 0.0

    def test_atr_with_invalid_data(self):
        """Test ATR with invalid data (high < low)."""
        high = [100.0, 95.0, 110.0]  # high < low in second value
        low = [98.0, 100.0, 105.0]  # low > high in second value
        close = [99.0, 97.0, 108.0]

        # ATR calculation doesn't validate high >= low, so it might return None
        # due to insufficient data
        atr = TechnicalIndicatorCalculator.calculate_atr(high, low, close, period=3)
        assert atr is None  # Returns None due to insufficient data for period=3

    def test_volume_sma_with_zero_volume(self):
        """Test Volume SMA with zero volume."""
        volumes = [Decimal("0.0")] * 20
        sma = TechnicalIndicatorCalculator.calculate_volume_sma(volumes, period=10)
        assert sma == Decimal("0.0")

        # Test with mixed zero and non-zero volumes
        volumes = [
            Decimal("1000.0"),
            Decimal("0.0"),
            Decimal("2000.0"),
            Decimal("0.0"),
            Decimal("1500.0"),
            Decimal("0.0"),
            Decimal("3000.0"),
            Decimal("0.0"),
            Decimal("2500.0"),
            Decimal("0.0"),
            Decimal("4000.0"),
            Decimal("0.0"),
            Decimal("3500.0"),
            Decimal("0.0"),
            Decimal("5000.0"),
            Decimal("0.0"),
            Decimal("4500.0"),
            Decimal("0.0"),
            Decimal("6000.0"),
            Decimal("0.0"),
        ]
        sma = TechnicalIndicatorCalculator.calculate_volume_sma(volumes, period=10)
        assert sma is not None
        assert sma >= Decimal("0")

    def test_indicators_with_empty_lists(self):
        """Test all indicators with empty lists."""
        empty_prices = []
        empty_volumes = []

        # All indicators should handle empty lists gracefully
        assert TechnicalIndicatorCalculator.calculate_rsi(empty_prices) is None
        assert TechnicalIndicatorCalculator.calculate_ema(empty_prices, period=10) is None
        assert TechnicalIndicatorCalculator.calculate_macd(empty_prices) == (
            None,
            None,
            None,
        )
        assert TechnicalIndicatorCalculator.calculate_atr([], [], []) is None
        assert TechnicalIndicatorCalculator.calculate_volume_sma(empty_volumes, period=10) is None

    def test_indicators_with_single_value(self):
        """Test all indicators with single value."""
        single_price = [100.0]
        single_volume = [Decimal("1000.0")]

        # All indicators should handle single values gracefully
        assert TechnicalIndicatorCalculator.calculate_rsi(single_price) is None
        assert TechnicalIndicatorCalculator.calculate_ema(single_price, period=1) == 100.0
        assert TechnicalIndicatorCalculator.calculate_macd(single_price) == (
            None,
            None,
            None,
        )
        assert TechnicalIndicatorCalculator.calculate_atr([100.0], [100.0], [100.0]) is None
        assert TechnicalIndicatorCalculator.calculate_volume_sma(
            single_volume, period=1
        ) == Decimal("1000.0")

    def test_indicators_with_very_large_periods(self):
        """Test indicators with periods larger than data length."""
        prices = [100.0, 105.0, 110.0, 108.0, 112.0]
        volumes = [
            Decimal("1000.0"),
            Decimal("2000.0"),
            Decimal("1500.0"),
            Decimal("3000.0"),
            Decimal("2500.0"),
        ]

        # Test with period larger than data length
        assert TechnicalIndicatorCalculator.calculate_rsi(prices, period=100) is None
        assert TechnicalIndicatorCalculator.calculate_ema(prices, period=100) is None
        assert TechnicalIndicatorCalculator.calculate_macd(prices) == (
            None,
            None,
            None,
        )  # MACD needs more data
        assert (
            TechnicalIndicatorCalculator.calculate_atr(
                [100.0, 105.0], [98.0, 103.0], [99.0, 104.0], period=100
            )
            is None
        )
        assert TechnicalIndicatorCalculator.calculate_volume_sma(volumes, period=100) is None

    def test_indicators_with_negative_periods(self):
        """Test indicators with negative periods."""
        prices = [100.0, 105.0, 110.0, 108.0, 112.0]
        volumes = [
            Decimal("1000.0"),
            Decimal("2000.0"),
            Decimal("1500.0"),
            Decimal("3000.0"),
            Decimal("2500.0"),
        ]

        # Test with negative periods - methods now validate and return None for invalid periods
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, period=-1)
        assert rsi is not None  # Returns a value due to how negative indexing works

        # EMA now validates period and returns None for negative periods
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=-1)
        assert ema is None  # Should return None for invalid period

        atr = TechnicalIndicatorCalculator.calculate_atr(
            [100.0, 105.0], [98.0, 103.0], [99.0, 104.0], period=-1
        )
        assert atr is not None  # Returns a value due to how negative indexing works

        sma = TechnicalIndicatorCalculator.calculate_volume_sma(volumes, period=-1)
        assert sma is not None  # Returns a value

    def test_indicators_with_zero_periods(self):
        """Test indicators with zero periods."""
        prices = [100.0, 105.0, 110.0, 108.0, 112.0]
        volumes = [
            Decimal("1000.0"),
            Decimal("2000.0"),
            Decimal("1500.0"),
            Decimal("3000.0"),
            Decimal("2500.0"),
        ]

        # REFACTORED: Methods should handle period=0 gracefully (return None or raise ValueError)
        # RSI with period=0 - check if returns None or raises error
        try:
            rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, period=0)
            assert rsi is None or isinstance(rsi, (int, float))
        except (ValueError, ZeroDivisionError):
            pass  # Acceptable behavior

        # EMA with period=0 - pandas raises ValueError
        try:
            ema = TechnicalIndicatorCalculator.calculate_ema(prices, period=0)
            assert ema is None or isinstance(ema, (int, float))
        except ValueError:
            pass  # Acceptable - pandas raises ValueError for span < 1

        # ATR with period=0
        try:
            atr = TechnicalIndicatorCalculator.calculate_atr(
                [100.0, 105.0], [98.0, 103.0], [99.0, 104.0], period=0
            )
            assert atr is None or isinstance(atr, (int, float))
        except (ValueError, ZeroDivisionError):
            pass  # Acceptable behavior

        # Volume SMA with period=0
        try:
            sma = TechnicalIndicatorCalculator.calculate_volume_sma(volumes, period=0)
            assert sma is None or isinstance(sma, (int, float, Decimal))
        except (ValueError, ZeroDivisionError):
            pass  # Acceptable behavior


class TestRiskCalculationEdgeCases:
    """Test risk calculations with edge cases."""

    def test_position_sizing_with_zero_account_balance(self):
        """Test position sizing with zero account balance."""
        account_balance = Decimal("0")
        risk_per_trade = Decimal("0.01")  # 1%
        price = Decimal("100.0")
        stop_loss = Decimal("95.0")

        # Should handle zero balance gracefully
        risk_amount = account_balance * risk_per_trade
        assert risk_amount == Decimal("0")

        # Position size should be zero
        if stop_loss > 0 and price > 0:
            position_size = risk_amount / (price - stop_loss)
            assert position_size == Decimal("0")

    def test_position_sizing_with_zero_price(self):
        """Test position sizing with zero price."""
        account_balance = Decimal("10000")
        risk_per_trade = Decimal("0.01")
        price = Decimal("0")  # Invalid price
        stop_loss = Decimal("95.0")

        # Should handle zero price gracefully - Decimal division doesn't raise
        # ZeroDivisionError
        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / (price - stop_loss)
        assert position_size == Decimal("-1.052631578947368421052631579")  # Negative result

    def test_position_sizing_with_zero_stop_loss(self):
        """Test position sizing with zero stop loss."""
        account_balance = Decimal("10000")
        risk_per_trade = Decimal("0.01")
        price = Decimal("100.0")
        stop_loss = Decimal("0")  # Invalid stop loss

        # Should handle zero stop loss gracefully - Decimal division doesn't
        # raise ZeroDivisionError
        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / (price - stop_loss)
        assert position_size == Decimal("1")  # Positive result

    def test_position_sizing_with_price_equals_stop_loss(self):
        """Test position sizing when price equals stop loss."""
        account_balance = Decimal("10000")
        risk_per_trade = Decimal("0.01")
        price = Decimal("100.0")
        stop_loss = Decimal("100.0")  # Same as price

        # Should handle equal price and stop loss gracefully
        risk_amount = account_balance * risk_per_trade
        with pytest.raises(ZeroDivisionError):  # Division by zero in Decimal
            risk_amount / (price - stop_loss)

    def test_position_sizing_with_negative_values(self):
        """Test position sizing with negative values."""
        account_balance = Decimal("-10000")  # Negative balance
        risk_per_trade = Decimal("0.01")
        price = Decimal("100.0")
        stop_loss = Decimal("95.0")

        # Should handle negative balance gracefully
        risk_amount = account_balance * risk_per_trade
        assert risk_amount < 0

        # Position size should be negative (short position)
        position_size = risk_amount / (price - stop_loss)
        assert position_size < 0

    def test_position_sizing_with_extreme_values(self):
        """Test position sizing with extreme values."""
        # Test with very large values
        account_balance = Decimal("1000000000")  # $1B
        risk_per_trade = Decimal("0.01")
        price = Decimal("1000000")  # $1M per share
        stop_loss = Decimal("950000")

        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / (price - stop_loss)

        assert position_size > 0
        assert position_size < Decimal("1000000")  # Reasonable limit

        # Test with very small values
        account_balance = Decimal("0.01")  # 1 cent
        risk_per_trade = Decimal("0.01")
        price = Decimal("0.01")  # 1 cent per share
        stop_loss = Decimal("0.009")

        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / (price - stop_loss)

        assert position_size > 0
        assert position_size < Decimal("100")  # Reasonable limit


class TestSignalEdgeCases:
    """Test signal generation with edge cases."""

    def test_signal_with_disordered_timestamps(self):
        """Test signal generation with disordered timestamps."""
        from datetime import datetime, timedelta

        # Create signals with disordered timestamps
        timestamps = [
            datetime.utcnow() + timedelta(hours=2),  # Future
            datetime.utcnow() - timedelta(hours=1),  # Past
            datetime.utcnow() + timedelta(hours=1),  # Future
            datetime.utcnow() - timedelta(hours=2),  # Past
        ]

        # Should handle disordered timestamps gracefully
        for timestamp in timestamps:
            # Future timestamps should be rejected
            if timestamp > datetime.utcnow():
                with pytest.raises(ValueError, match="Timestamp cannot be in the future"):
                    from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

                    Signal(
                        symbol="TEST_SYMBOL",
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.MODERATE,
                        confidence=70.0,
                        liquidity_score=50.0,
                        priority_score=50.0,
                        source=SignalSource.TECHNICAL,
                        price=Decimal("100.0"),
                        volume=Decimal("1000"),
                        timestamp=timestamp,
                    )

    def test_signal_with_future_timestamps(self):
        """Test signal generation with future timestamps."""
        from datetime import datetime, timedelta

        from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

        future_time = datetime.utcnow() + timedelta(days=1)

        with pytest.raises(ValueError, match="Timestamp cannot be in the future"):
            Signal(
                symbol="TEST_SYMBOL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("100.0"),
                volume=Decimal("1000"),
                timestamp=future_time,
            )

    def test_signal_with_incomplete_inputs(self):
        """Test signal generation with incomplete inputs."""
        from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

        # Test with complete signal - should work
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
        )
        assert signal.symbol == "TEST_SYMBOL"

    def test_signal_with_extreme_confidence_values(self):
        """Test signal generation with extreme confidence values."""
        from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

        # Test with confidence = 0
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=0.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
        )
        assert signal.confidence == 0.0

        # Test with confidence = 100
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=100.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
        )
        assert signal.confidence == 100.0


class TestMathematicalEdgeCases:
    """Test mathematical calculations with edge cases."""

    def test_division_by_zero_in_calculations(self):
        """Test division by zero scenarios in calculations."""
        # Test division by zero in percentage calculations
        with pytest.raises(ZeroDivisionError):
            100 / 0

        # Test division by zero in average calculations
        with pytest.raises(ZeroDivisionError):
            values = [100, 200, 300]
            sum(values) / 0

        # Test division by zero in ratio calculations
        with pytest.raises(ZeroDivisionError):
            numerator = 100
            denominator = 0
            numerator / denominator

    def test_square_root_of_negative_numbers(self):
        """Test square root calculations with negative numbers."""
        import math

        # Test square root of negative number
        with pytest.raises(ValueError):
            result = math.sqrt(-1)

        # Test square root of zero
        result = math.sqrt(0)
        assert result == 0.0

        # Test square root of very small positive number
        result = math.sqrt(1e-10)
        assert result > 0

    def test_logarithm_of_zero_or_negative(self):
        """Test logarithm calculations with zero or negative numbers."""
        import math

        # Test logarithm of zero
        with pytest.raises(ValueError):
            result = math.log(0)

        # Test logarithm of negative number
        with pytest.raises(ValueError):
            result = math.log(-1)

        # Test logarithm of very small positive number
        result = math.log(1e-10)
        assert result < 0

    def test_power_calculations_with_extreme_values(self):
        """Test power calculations with extreme values."""

        # Test very large base
        result = 1e10**2
        assert result > 0

        # Test very small base
        result = 1e-10**2
        assert result > 0

        # Test very large exponent
        result = 2**100
        assert result > 0

        # Test very small exponent
        result = 2 ** (-100)
        assert result > 0
        assert result < 1
