"""
Unit tests for RSI Filter with Crossover Confirmation.

Tests the CORRECTED RSI logic:
- BUY when RSI crosses ABOVE buy_threshold (reversal confirmation)
- SELL when RSI crosses BELOW sell_threshold (reversal confirmation)
- FALLBACK mode when no history available
"""

import pytest

from app.domain.strategies.momentum_modular.modules.filters.rsi_filter import RSIFilter


@pytest.fixture(autouse=True)
def reset_rsi_history():
    """Reset RSI history before each test."""
    RSIFilter.clear_rsi_history()
    yield
    RSIFilter.clear_rsi_history()


class TestRSICrossoverLogic:
    """Test RSI crossover confirmation logic."""

    def test_buy_crossover_detection(self):
        """Test BUY signal when RSI crosses above 30."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # First call: RSI at 29 (oversold, uses fallback mode, no crossover yet)
        result1 = filter_instance.evaluate(
            indicators={"rsi": 29.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        # Fallback mode: RSI 29 > 28 (fallback threshold), so should not pass
        assert result1['passed'] is False, "Should not buy at 29 even with fallback threshold of 28"
        assert (
            "fallback" in result1['reason'].lower()
            or "not oversold enough" in result1['reason'].lower()
        )

        # Second call: RSI crosses to 32 (crossover detected!)
        result2 = filter_instance.evaluate(
            indicators={"rsi": 32.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result2['passed'] is True, "Should buy on crossover above 30"
        assert "crossover" in result2['reason'].lower()
        assert result2['metadata']['crossover'] is True
        assert result2['metadata']['previous_rsi'] == 29.0
        assert result2['metadata']['rsi'] == 32.0

    def test_sell_crossover_detection(self):
        """Test SELL signal when RSI crosses below 70."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # First call: RSI at 71 (overbought, uses fallback mode, no crossover yet)
        result1 = filter_instance.evaluate(
            indicators={"rsi": 71.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        # Fallback mode: RSI 71 < 72 (fallback threshold), so should not pass
        assert (
            result1['passed'] is False
        ), "Should not sell at 71 even with fallback threshold of 72"
        assert (
            "fallback" in result1['reason'].lower()
            or "not overbought enough" in result1['reason'].lower()
        )

        # Second call: RSI crosses to 68 (crossover detected!)
        result2 = filter_instance.evaluate(
            indicators={"rsi": 68.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result2['passed'] is True, "Should sell on crossover below 70"
        assert "crossover" in result2['reason'].lower()
        assert result2['metadata']['crossover'] is True
        assert result2['metadata']['previous_rsi'] == 71.0
        assert result2['metadata']['rsi'] == 68.0

    def test_no_buy_without_crossover(self):
        """Test that BUY signal is NOT generated when RSI stays below threshold."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # RSI goes from 28 to 29 (still below 30, no crossover)
        filter_instance.evaluate(
            indicators={"rsi": 28.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        result = filter_instance.evaluate(
            indicators={"rsi": 29.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result['passed'] is False, "Should not buy without crossing above threshold"
        assert "waiting for crossover" in result['reason']

    def test_no_sell_without_crossover(self):
        """Test that SELL signal is NOT generated when RSI stays above threshold."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # RSI goes from 72 to 74 (still above 70, no crossover)
        filter_instance.evaluate(
            indicators={"rsi": 72.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        result = filter_instance.evaluate(
            indicators={"rsi": 74.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result['passed'] is False, "Should not sell without crossing below threshold"
        assert "waiting for crossover" in result['reason']


class TestRSIFallbackMode:
    """Test RSI fallback mode when no history is available."""

    def test_fallback_buy_stricter_threshold(self):
        """Test fallback mode uses stricter threshold for BUY (30 - 2 = 28)."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Clear history to ensure fallback mode
        RSIFilter.clear_rsi_history()

        # First call with no history: RSI at 29
        # Should fail because fallback threshold is 28 (30 - 2)
        result = filter_instance.evaluate(
            indicators={"rsi": 29.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result['passed'] is False, "Should not buy at 29 with fallback threshold of 28"
        assert result['metadata']['fallback_mode'] is True
        assert result['metadata']['fallback_threshold'] == 28

        # Clear history again for the second test
        RSIFilter.clear_rsi_history()

        # RSI at 27 should pass with fallback
        result2 = filter_instance.evaluate(
            indicators={"rsi": 27.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result2['passed'] is True, "Should buy at 27 with fallback threshold of 28"

    def test_fallback_sell_stricter_threshold(self):
        """Test fallback mode uses stricter threshold for SELL (70 + 2 = 72)."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Clear history to ensure fallback mode
        RSIFilter.clear_rsi_history()

        # First call with no history: RSI at 71
        # Should fail because fallback threshold is 72 (70 + 2)
        result = filter_instance.evaluate(
            indicators={"rsi": 71.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result['passed'] is False, "Should not sell at 71 with fallback threshold of 72"
        assert result['metadata']['fallback_mode'] is True
        assert result['metadata']['fallback_threshold'] == 72

        # Clear history again for the second test
        RSIFilter.clear_rsi_history()

        # RSI at 73 should pass with fallback
        result2 = filter_instance.evaluate(
            indicators={"rsi": 73.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result2['passed'] is True, "Should sell at 73 with fallback threshold of 72"


class TestRSIAdaptiveThresholds:
    """Test RSI adaptive thresholds for different market contexts."""

    def test_volatile_market_thresholds(self):
        """Test that volatile market uses different thresholds."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Setup history
        filter_instance.evaluate(
            indicators={"rsi": 20.0, "symbol": symbol},
            market_context={"type": "volatile"},
            signal_type="BUY",
        )

        # In volatile market, buy_threshold is 25 (not 30)
        # Cross from 24 to 26 should trigger buy
        result = filter_instance.evaluate(
            indicators={"rsi": 26.0, "symbol": symbol},
            market_context={"type": "volatile"},
            signal_type="BUY",
        )

        assert result['passed'] is True, "Should buy on crossover above 25 in volatile market"
        assert result['metadata']['buy_threshold'] == 25

    def test_trending_market_thresholds(self):
        """Test that trending market uses different thresholds."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Setup history - need to be above 65 to then cross below
        filter_instance.evaluate(
            indicators={"rsi": 68.0, "symbol": symbol},
            market_context={"type": "trending"},
            signal_type="SELL",
        )

        # In trending market, sell_threshold is 65 (not 70)
        # Cross from 68 to 64 should trigger sell
        result = filter_instance.evaluate(
            indicators={"rsi": 64.0, "symbol": symbol},
            market_context={"type": "trending"},
            signal_type="SELL",
        )

        assert result['passed'] is True, "Should sell on crossover below 65 in trending market"
        assert result['metadata']['sell_threshold'] == 65


class TestRSICrossoverConfidence:
    """Test confidence calculation for crossovers."""

    def test_buy_confidence_deep_oversold(self):
        """Test that deeper oversold crossover gives higher confidence."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Cross from very deep oversold (15) to above 30
        filter_instance.evaluate(
            indicators={"rsi": 15.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        result = filter_instance.evaluate(
            indicators={"rsi": 32.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result['passed'] is True
        assert result['confidence'] > 0.7, "Deep reversal should have high confidence"

    def test_sell_confidence_deep_overbought(self):
        """Test that deeper overbought crossover gives higher confidence."""
        filter_instance = RSIFilter()
        symbol = "AAPL"

        # Cross from very deep overbought (85) to below 70
        filter_instance.evaluate(
            indicators={"rsi": 85.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        result = filter_instance.evaluate(
            indicators={"rsi": 68.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result['passed'] is True
        assert result['confidence'] > 0.7, "Deep reversal should have high confidence"


class TestRSIHistoryManagement:
    """Test RSI history tracking and management."""

    def test_history_per_symbol(self):
        """Test that history is tracked separately per symbol."""
        filter_instance = RSIFilter()

        # Set different RSI values for different symbols
        filter_instance.evaluate(
            indicators={"rsi": 25.0, "symbol": "AAPL"},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        filter_instance.evaluate(
            indicators={"rsi": 75.0, "symbol": "MSFT"},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        history = RSIFilter.get_rsi_history()

        assert history["AAPL"] == 25.0
        assert history["MSFT"] == 75.0

    def test_clear_history_symbol(self):
        """Test clearing history for specific symbol."""
        filter_instance = RSIFilter()

        filter_instance.evaluate(
            indicators={"rsi": 25.0, "symbol": "AAPL"},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        filter_instance.evaluate(
            indicators={"rsi": 75.0, "symbol": "MSFT"},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        RSIFilter.clear_rsi_history(symbol="AAPL")

        history = RSIFilter.get_rsi_history()

        assert "AAPL" not in history
        assert history["MSFT"] == 75.0

    def test_clear_all_history(self):
        """Test clearing all RSI history."""
        filter_instance = RSIFilter()

        filter_instance.evaluate(
            indicators={"rsi": 25.0, "symbol": "AAPL"},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        RSIFilter.clear_rsi_history()

        history = RSIFilter.get_rsi_history()

        assert len(history) == 0


class TestRSIDisableCrossover:
    """Test disabling crossover logic (legacy mode)."""

    def test_disable_crossover_buy(self):
        """Test BUY with crossover disabled uses threshold logic."""
        config = {"settings": {"use_crossover": False}}
        filter_instance = RSIFilter(config=config, use_yaml=False)
        symbol = "AAPL"

        # With crossover disabled, should buy at RSI <= 30
        result = filter_instance.evaluate(
            indicators={"rsi": 28.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert result['passed'] is True, "Should buy at 28 with crossover disabled"
        assert result['metadata'].get('crossover') is not True

    def test_disable_crossover_sell(self):
        """Test SELL with crossover disabled uses threshold logic."""
        config = {"settings": {"use_crossover": False}}
        filter_instance = RSIFilter(config=config, use_yaml=False)
        symbol = "AAPL"

        # With crossover disabled, should sell at RSI >= 70
        result = filter_instance.evaluate(
            indicators={"rsi": 72.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert result['passed'] is True, "Should sell at 72 with crossover disabled"
        assert result['metadata'].get('crossover') is not True


class TestRSILogging:
    """Test RSI crossover logging."""

    def test_buy_crossover_logged(self, caplog):
        """Test that BUY crossover is logged at INFO level."""
        import logging

        caplog.set_level(logging.INFO)

        filter_instance = RSIFilter()
        symbol = "AAPL"

        filter_instance.evaluate(
            indicators={"rsi": 25.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        filter_instance.evaluate(
            indicators={"rsi": 32.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="BUY",
        )

        assert "RSI BUY crossover detected" in caplog.text
        assert "AAPL" in caplog.text
        assert "32" in caplog.text

    def test_sell_crossover_logged(self, caplog):
        """Test that SELL crossover is logged at INFO level."""
        import logging

        caplog.set_level(logging.INFO)

        filter_instance = RSIFilter()
        symbol = "AAPL"

        filter_instance.evaluate(
            indicators={"rsi": 75.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        filter_instance.evaluate(
            indicators={"rsi": 68.0, "symbol": symbol},
            market_context={"type": "balanced"},
            signal_type="SELL",
        )

        assert "RSI SELL crossover detected" in caplog.text
        assert "AAPL" in caplog.text
        assert "68" in caplog.text
