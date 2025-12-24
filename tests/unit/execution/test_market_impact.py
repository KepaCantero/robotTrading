"""
Unit tests for MarketImpactEstimator

Tests market impact calculation, volatility adjustments, and slippage estimation.
"""

import pytest
import asyncio
from decimal import Decimal

from app.services.smart_order_routing.market_impact_estimator import (
    MarketImpactEstimator,
)


class TestMarketImpactEstimator:
    """Test suite for MarketImpactEstimator."""

    @pytest.fixture
    def estimator(self):
        """Create estimator instance for testing."""
        return MarketImpactEstimator()

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    def test_initialization(self, estimator):
        """Test estimator initializes correctly."""
        assert estimator is not None
        assert estimator.BASE_IMPACT_BPS is not None
        assert estimator.VOLATILITY_MULTIPLIERS is not None

    @pytest.mark.asyncio
    async def test_estimate_basic(self, estimator):
        """Test basic market impact estimation."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,
        )

        assert result is not None
        assert result.symbol == "AAPL"
        assert result.estimated_slippage_bps > Decimal("0")
        assert result.estimated_slippage_usd > Decimal("0")

    @pytest.mark.asyncio
    async def test_participation_rate_calculation(self, estimator):
        """Test participation rate is calculated correctly."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("100000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,
        )

        expected_participation = Decimal("100000") / Decimal("10000000")
        assert result.participation_rate == expected_participation

    @pytest.mark.asyncio
    async def test_sqrt_impact_calculation(self, estimator):
        """Test square root market impact is calculated."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("100000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,
        )

        expected_sqrt = (Decimal("100000") / Decimal("10000000")).sqrt()
        assert result.sqrt_impact == expected_sqrt

    @pytest.mark.asyncio
    async def test_volatility_multiplier_low(self, estimator):
        """Test low volatility reduces impact."""
        result_low_vol = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=10,  # Low volatility
        )

        result_normal_vol = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,  # Normal volatility
        )

        # Low volatility should have lower impact
        assert result_low_vol.estimated_slippage_bps < result_normal_vol.estimated_slippage_bps

    @pytest.mark.asyncio
    async def test_volatility_multiplier_high(self, estimator):
        """Test high volatility increases impact."""
        result_normal_vol = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,  # Normal volatility
        )

        result_high_vol = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=90,  # High volatility
        )

        # High volatility should have higher impact
        assert result_high_vol.estimated_slippage_bps > result_normal_vol.estimated_slippage_bps

    @pytest.mark.asyncio
    async def test_time_window_effect(self, estimator):
        """Test longer time windows reduce per-unit impact."""
        result_1min = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            time_window_ms=60_000,  # 1 minute
            volatility_percentile=50,
        )

        result_10min = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            time_window_ms=600_000,  # 10 minutes
            volatility_percentile=50,
        )

        # Longer window should reduce impact
        assert result_10min.estimated_slippage_bps < result_1min.estimated_slippage_bps

    @pytest.mark.asyncio
    async def test_asset_class_equity(self, estimator):
        """Test equity asset class uses correct base impact."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            asset_class="equity",
        )

        assert result.estimated_slippage_bps > Decimal("0")

    @pytest.mark.asyncio
    async def test_asset_class_crypto(self, estimator):
        """Test crypto has higher base impact than equity."""
        result_equity = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            asset_class="equity",
        )

        result_crypto = await estimator.estimate(
            symbol="BTC",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            asset_class="crypto",
        )

        # Crypto should have higher impact due to higher base impact
        assert result_crypto.estimated_slippage_bps > result_equity.estimated_slippage_bps

    @pytest.mark.asyncio
    async def test_asset_class_forex(self, estimator):
        """Test forex has lower base impact than equity."""
        result_equity = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            asset_class="equity",
        )

        result_forex = await estimator.estimate(
            symbol="EURUSD",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            asset_class="forex",
        )

        # Forex should have lower impact (more liquid)
        assert result_forex.estimated_slippage_bps < result_equity.estimated_slippage_bps

    @pytest.mark.asyncio
    async def test_spread_impact_included(self, estimator):
        """Test spread impact is included in total slippage."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            current_spread_bps=Decimal("2"),
        )

        # Total should include spread impact
        assert result.spread_impact > Decimal("0")

    @pytest.mark.asyncio
    async def test_slippage_capped_at_500_bps(self, estimator):
        """Test slippage is capped at 500 bps (5%) maximum."""
        # Very large order relative to volume
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("5000000"),
            daily_volume=Decimal("1000000"),
            volatility_percentile=95,
        )

        # Should be capped at 500 bps
        assert result.estimated_slippage_bps <= Decimal("500")

    @pytest.mark.asyncio
    async def test_zero_volume_handling(self, estimator):
        """Test handling of zero daily volume."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("0"),
        )

        # Should handle gracefully with zero participation
        assert result.participation_rate == Decimal("0")

    @pytest.mark.asyncio
    async def test_slippage_to_usd_conversion(self, estimator):
        """Test slippage is correctly converted to USD."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Manual calculation: slippage_bps * order_size / 10000
        expected_usd = result.estimated_slippage_bps * Decimal("50000") / Decimal("10000")
        assert result.estimated_slippage_usd == expected_usd

    @pytest.mark.asyncio
    async def test_estimate_by_participation_rate(self, estimator):
        """Test estimation using pre-calculated participation rate."""
        participation = Decimal("0.005")  # 0.5%
        result = await estimator.estimate_by_participation_rate(
            symbol="AAPL",
            participation_rate=participation,
            daily_volume=Decimal("10000000"),
            order_size=Decimal("50000"),
        )

        assert result is not None
        assert result.participation_rate == participation

    def test_slippage_for_different_windows(self, estimator):
        """Test slippage comparison across time windows."""
        windows = estimator.estimate_slippage_for_different_windows(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=50,
        )

        assert len(windows) == 5
        assert 60_000 in windows
        assert 300_000 in windows
        assert 3_600_000 in windows

        # Slippage should decrease with longer windows
        slippage_1min = windows[60_000]["slippage_bps"]
        slippage_10min = windows[600_000]["slippage_bps"]
        slippage_1hr = windows[3_600_000]["slippage_bps"]

        assert slippage_1min > slippage_10min > slippage_1hr

    def test_window_comparison_structure(self, estimator):
        """Test window comparison returns proper structure."""
        windows = estimator.estimate_slippage_for_different_windows(
            symbol="AAPL",
            order_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        for time_ms, data in windows.items():
            assert "time_window_ms" in data
            assert "time_window_min" in data
            assert "slippage_bps" in data
            assert "slippage_usd" in data
            assert "time_decay" in data

    @pytest.mark.asyncio
    async def test_small_order_minimal_impact(self, estimator):
        """Test small orders have minimal market impact."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("1000"),  # Small
            daily_volume=Decimal("10000000"),
        )

        # Small orders should have very low impact
        assert result.estimated_slippage_bps < Decimal("10")

    @pytest.mark.asyncio
    async def test_large_order_significant_impact(self, estimator):
        """Test large orders have significant market impact."""
        result = await estimator.estimate(
            symbol="AAPL",
            order_size=Decimal("1000000"),  # Large
            daily_volume=Decimal("10000000"),
        )

        # Large orders should have more impact
        assert result.estimated_slippage_bps > Decimal("20")

    @pytest.mark.asyncio
    async def test_all_asset_classes(self, estimator):
        """Test all supported asset classes return results."""
        asset_classes = ["equity", "crypto", "forex", "commodity", "bond"]

        for asset_class in asset_classes:
            result = await estimator.estimate(
                symbol="TEST",
                order_size=Decimal("50000"),
                daily_volume=Decimal("10000000"),
                asset_class=asset_class,
            )
            assert result is not None
            assert result.estimated_slippage_bps > Decimal("0")
