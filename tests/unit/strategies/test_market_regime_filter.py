"""
Unit tests for Market Regime Filter in ModularMomentumStrategy.

Tests the critical safety filter that prevents trading during adverse market conditions:
- Bear market crashes (DOWN trend + HIGH volatility)
- Dead markets (sideways/range + LOW volatility)
- Extreme volatility crises
"""

from unittest.mock import Mock

import pytest

from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy


class TestMarketRegimeFilter:
    """Test suite for market regime filtering logic."""

    @pytest.fixture
    def strategy(self):
        """Create a strategy instance for testing."""
        config = {
            "name": "test_strategy",
            "preset": "balanced",
            "presets": {"balanced": {"min_confidence": 0.6, "combination_mode": "MAJORITY"}},
            "market_analyzer": {
                "enabled": True,
                "trend_detection": {"enabled": True},
                "volatility_detection": {"enabled": True},
                "range_detection": {"enabled": True},
            },
            "modules": {
                "ema_filter": {"enabled": True},
                "rsi_filter": {"enabled": True},
                "momentum_filter": {"enabled": True},
            },
        }
        return ModularMomentumStrategy(config)

    @pytest.fixture
    def mock_market_data(self):
        """Create mock market data."""
        mock_data = Mock()
        mock_data.symbol = "AAPL"
        mock_data.close = 150.0
        mock_data.high = 152.0
        mock_data.low = 148.0
        mock_data.volume = 1000000
        mock_data.timestamp = None
        mock_data.bid = 150.0
        mock_data.last = 150.0
        return mock_data

    # ===== BAD REGIME TESTS (should return False) =====

    def test_bear_market_crash_high_strength(self, strategy):
        """Test that bear market with high strength is blocked."""
        market_context = {
            'type': 'trend_down',
            'trend_strength': 0.8,  # > 0.6
            'volatility_regime': 'high',
            'volatility_percentile': 80,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block trading during bear market crash"

    def test_bear_market_exactly_at_threshold(self, strategy):
        """Test bear market exactly at threshold (0.6)."""
        market_context = {
            'type': 'trend_down',
            'trend_strength': 0.61,  # Just above 0.6
            'volatility_regime': 'normal',
            'volatility_percentile': 60,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block when strength > 0.6"

    def test_dead_market_range_low_volatility(self, strategy):
        """Test that dead market (range + low vol) is blocked."""
        market_context = {
            'type': 'range',
            'trend_strength': 0.2,
            'volatility_regime': 'low',  # KEY: low volatility
            'volatility_percentile': 15,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block trading in dead market (no opportunity)"

    def test_dead_market_sideways_low_volatility(self, strategy):
        """Test that sideways market with low volatility is blocked."""
        market_context = {
            'type': 'sideways',
            'trend_strength': 0.1,
            'volatility_regime': 'low',
            'volatility_percentile': 10,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block sideways with low volatility"

    def test_extreme_volatility_crisis(self, strategy):
        """Test that extreme volatility (>75 percentile) is blocked."""
        market_context = {
            'type': 'trend_up',  # Even with uptrend
            'trend_strength': 0.7,
            'volatility_regime': 'high',
            'volatility_percentile': 85,  # > 75
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block during extreme volatility crisis"

    def test_extreme_volatility_at_threshold(self, strategy):
        """Test extreme volatility exactly at threshold (75)."""
        market_context = {
            'type': 'unknown',
            'trend_strength': 0.5,
            'volatility_regime': 'high',
            'volatility_percentile': 76,  # Just above 75
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is False, "Should block when percentile > 75"

    # ===== GOOD REGIME TESTS (should return True) =====

    def test_bull_market_always_allowed(self, strategy):
        """Test that bull market (trend_up) is always allowed."""
        market_context = {
            'type': 'trend_up',  # KEY: uptrend
            'trend_strength': 0.9,
            'volatility_regime': 'normal',
            'volatility_percentile': 60,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Bull market should always be allowed"

    def test_bull_market_weak_strength(self, strategy):
        """Test bull market even with weak strength."""
        market_context = {
            'type': 'trend_up',
            'trend_strength': 0.3,  # Weak but still up
            'volatility_regime': 'low',
            'volatility_percentile': 30,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Bull market allowed regardless of strength"

    def test_normal_volatility_safe_range(self, strategy):
        """Test that normal volatility (40-70 percentile) is allowed."""
        market_context = {
            'type': 'range',
            'trend_strength': 0.0,
            'volatility_regime': 'normal',
            'volatility_percentile': 55,  # In 40-70 range
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Normal volatility should be allowed"

    def test_normal_volatility_at_lower_bound(self, strategy):
        """Test normal volatility at lower bound (40)."""
        market_context = {
            'type': 'no_trend',
            'trend_strength': 0.0,
            'volatility_regime': 'normal',
            'volatility_percentile': 40,  # Exactly at lower bound
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Should allow at percentile = 40"

    def test_normal_volatility_at_upper_bound(self, strategy):
        """Test normal volatility at upper bound (70)."""
        market_context = {
            'type': 'unknown',
            'trend_strength': 0.4,
            'volatility_regime': 'normal',
            'volatility_percentile': 70,  # Exactly at upper bound
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Should allow at percentile = 70"

    def test_range_market_normal_volatility(self, strategy):
        """Test that range market with normal volatility is allowed."""
        market_context = {
            'type': 'range',
            'trend_strength': 0.1,
            'volatility_regime': 'normal',  # KEY: normal, not low
            'volatility_percentile': 50,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Range market with normal vol should be allowed"

    def test_no_trend_normal_volatility(self, strategy):
        """Test that no_trend with normal volatility is allowed."""
        market_context = {
            'type': 'no_trend',
            'trend_strength': 0.0,
            'volatility_regime': 'normal',
            'volatility_percentile': 45,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "No trend with normal vol should be allowed"

    # ===== EDGE CASES =====

    def test_weak_downtrend_normal_volatility(self, strategy):
        """Test weak downtrend (<= 0.5) with normal volatility."""
        market_context = {
            'type': 'trend_down',
            'trend_strength': 0.4,  # Weak, <= 0.5
            'volatility_regime': 'normal',
            'volatility_percentile': 50,
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Weak downtrend with normal vol should be allowed"

    def test_weak_downtrend_in_normal_vol_range(self, strategy):
        """Test weak downtrend within 40-70 percentile range."""
        market_context = {
            'type': 'trend_down',
            'trend_strength': 0.5,
            'volatility_regime': 'normal',
            'volatility_percentile': 60,  # In 40-70 range
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Should allow weak downtrend in normal vol range"

    def test_missing_context_fields_defaults_safe(self, strategy):
        """Test that missing context uses safe defaults (percentile=50, regime='normal')."""
        market_context = {
            'type': 'unknown',
            # Missing trend_strength, volatility_regime, volatility_percentile
        }

        result = strategy._is_market_regime_safe(market_context)

        # With defaults: percentile=50 (in 40-70 range), regime='normal'
        # This passes the "normal volatility" check
        assert result is True, "Unknown market with safe defaults should allow trading"

    def test_high_volatility_below_threshold(self, strategy):
        """Test high volatility but below crisis threshold (75)."""
        market_context = {
            'type': 'trend_up',
            'trend_strength': 0.7,
            'volatility_regime': 'high',
            'volatility_percentile': 72,  # High but < 75
        }

        result = strategy._is_market_regime_safe(market_context)

        # This should be allowed because it's bull market
        assert result is True, "Bull market with vol < 75 should be allowed"

    def test_range_market_with_high_but_safe_volatility(self, strategy):
        """Test range market with high but safe volatility."""
        market_context = {
            'type': 'range',
            'trend_strength': 0.0,
            'volatility_regime': 'normal',
            'volatility_percentile': 65,  # In normal range
        }

        result = strategy._is_market_regime_safe(market_context)

        assert result is True, "Range market in normal vol range should be allowed"

    # ===== INTEGRATION TESTS =====

    def test_generate_signals_blocked_by_bad_regime(self, strategy, mock_market_data, monkeypatch):
        """Test that generate_signals returns empty list when regime is bad."""
        # Build up enough price history
        for i in range(100):
            strategy.price_history.append(150.0 + i * 0.1)
            strategy.high_history.append(152.0 + i * 0.1)
            strategy.low_history.append(148.0 + i * 0.1)
            strategy.volume_history.append(1000000)

        # Mock market_analyzer to return bear market crash
        bear_market_context = {
            'type': 'trend_down',
            'trend_strength': 0.8,
            'volatility_regime': 'high',
            'volatility_percentile': 80,
        }

        def mock_analyze(*args, **kwargs):
            return bear_market_context

        strategy.market_analyzer.analyze = mock_analyze

        # Generate signals
        signals = strategy.generate_signals(mock_market_data)

        # Should return empty list due to regime filter
        assert signals == [], "Should return no signals during bear market crash"

    def test_generate_signals_allowed_in_good_regime(self, strategy, mock_market_data, monkeypatch):
        """Test that generate_signals works when regime is good."""
        # Build up enough price history
        for i in range(100):
            strategy.price_history.append(150.0 + i * 0.1)
            strategy.high_history.append(152.0 + i * 0.1)
            strategy.low_history.append(148.0 + i * 0.1)
            strategy.volume_history.append(1000000)

        # Mock market_analyzer to return bull market
        bull_market_context = {
            'type': 'trend_up',
            'trend_strength': 0.7,
            'volatility_regime': 'normal',
            'volatility_percentile': 60,
        }

        def mock_analyze(*args, **kwargs):
            return bull_market_context

        strategy.market_analyzer.analyze = mock_analyze

        # Generate signals - we don't care about the actual signal,
        # just that it's not immediately blocked by regime filter
        signals = strategy.generate_signals(mock_market_data)

        # Should not be immediately blocked by regime filter
        # (may still return [] due to filters, but not because of regime)
        # We just verify it doesn't crash and returns a list
        assert isinstance(signals, list), "Should return a list"

    # ===== REGRESSION TESTS =====

    def test_regression_dont_trade_in_crash_scenarios(self, strategy):
        """Regression test: Ensure we don't trade in crash scenarios."""
        crash_scenarios = [
            # 2008-style crash
            {
                'type': 'trend_down',
                'trend_strength': 0.9,
                'volatility_regime': 'high',
                'volatility_percentile': 90,
            },
            # COVID crash
            {
                'type': 'trend_down',
                'trend_strength': 0.85,
                'volatility_regime': 'high',
                'volatility_percentile': 95,
            },
            # Flash crash
            {
                'type': 'trend_down',
                'trend_strength': 0.7,
                'volatility_regime': 'high',
                'volatility_percentile': 85,
            },
        ]

        for context in crash_scenarios:
            result = strategy._is_market_regime_safe(context)
            assert result is False, f"Should block crash scenario: {context}"

    def test_regression_allow_normal_trading_conditions(self, strategy):
        """Regression test: Ensure we allow normal trading conditions."""
        normal_scenarios = [
            # Healthy bull market
            {
                'type': 'trend_up',
                'trend_strength': 0.6,
                'volatility_regime': 'normal',
                'volatility_percentile': 55,
            },
            # Mild volatility with uptrend
            {
                'type': 'trend_up',
                'trend_strength': 0.4,
                'volatility_regime': 'normal',
                'volatility_percentile': 45,
            },
            # Normal range-bound market
            {
                'type': 'range',
                'trend_strength': 0.0,
                'volatility_regime': 'normal',
                'volatility_percentile': 50,
            },
        ]

        for context in normal_scenarios:
            result = strategy._is_market_regime_safe(context)
            assert result is True, f"Should allow normal scenario: {context}"


class TestMarketRegimeFilterLogging:
    """Test that appropriate logging occurs for different regimes."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        config = {
            "name": "test_strategy",
            "preset": "balanced",
            "presets": {"balanced": {"min_confidence": 0.6, "combination_mode": "MAJORITY"}},
            "market_analyzer": {"enabled": True},
            "modules": {},
        }
        return ModularMomentumStrategy(config)

    @pytest.fixture(autouse=True)
    def reset_rate_limited_logger(self):
        """Reset the rate-limited logger counters before each logging test."""
        from app.domain.strategies.momentum_modular.strategy import _rate_limited_logger

        # Reset counters to ensure logs appear in tests
        _rate_limited_logger.counters.clear()

    def test_bear_market_logs_warning(self, strategy, caplog):
        """Test that bear market logs a warning."""
        import logging

        caplog.set_level(logging.WARNING)

        market_context = {
            'type': 'trend_down',
            'trend_strength': 0.8,
            'volatility_regime': 'high',
            'volatility_percentile': 80,
        }

        strategy._is_market_regime_safe(market_context)

        assert "BEAR MARKET CRASH" in caplog.text
        assert "STOPPING TRADING" in caplog.text

    def test_extreme_volatility_logs_warning(self, strategy, caplog):
        """Test that extreme volatility logs a warning."""
        import logging

        caplog.set_level(logging.WARNING)

        market_context = {
            'type': 'trend_up',
            'trend_strength': 0.5,
            'volatility_regime': 'high',
            'volatility_percentile': 85,
        }

        strategy._is_market_regime_safe(market_context)

        assert "EXTREME VOLATILITY CRISIS" in caplog.text
        assert "STOPPING TRADING" in caplog.text

    def test_bull_market_logs_debug(self, strategy, caplog):
        """Test that bull market logs debug message."""
        import logging

        caplog.set_level(logging.DEBUG)

        market_context = {
            'type': 'trend_up',
            'trend_strength': 0.7,
            'volatility_regime': 'normal',
            'volatility_percentile': 60,
        }

        strategy._is_market_regime_safe(market_context)

        assert "BULL MARKET" in caplog.text
        assert "Trading ALLOWED" in caplog.text
