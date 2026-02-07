"""
Unit tests for Liquidity module

Tests for market depth and liquidity analysis
"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.microstructure.liquidity import (
    DepthProfile,
    LiquidityAnalyzer,
    LiquidityMonitor,
    SpreadComponent,
    SpreadDecomposition,
    get_liquidity_analyzer,
    get_liquidity_monitor,
)


class TestLiquidityAnalyzer:
    """Test LiquidityAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return LiquidityAnalyzer(lookback_periods=20, depth_levels=5)

    @pytest.fixture
    def sample_order_book(self):
        """Create sample order book"""
        return {
            'bids': [
                (Decimal("99.99"), Decimal("1000")),
                (Decimal("99.98"), Decimal("2000")),
                (Decimal("99.97"), Decimal("3000")),
                (Decimal("99.96"), Decimal("4000")),
                (Decimal("99.95"), Decimal("5000")),
            ],
            'asks': [
                (Decimal("100.01"), Decimal("1000")),
                (Decimal("100.02"), Decimal("2000")),
                (Decimal("100.03"), Decimal("3000")),
                (Decimal("100.04"), Decimal("4000")),
                (Decimal("100.05"), Decimal("5000")),
            ],
        }

    @pytest.fixture
    def sample_price_history(self):
        """Create sample price history"""
        return pd.DataFrame(
            {
                'close': [100 + i * 0.01 + np.random.randn() * 0.05 for i in range(100)],
                'volume': [1000000 + np.random.randint(-100000, 100000) for _ in range(100)],
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1min'),
        )

    def test_measure_market_depth(self, analyzer, sample_order_book):
        """Test market depth measurement"""
        depth_profile = analyzer.measure_market_depth(
            sample_order_book,
            target_size=Decimal("5000"),
        )

        # Should return valid depth profile
        assert len(depth_profile.bid_levels) > 0
        assert len(depth_profile.ask_levels) > 0
        assert depth_profile.total_bid_depth > 0
        assert depth_profile.total_ask_depth > 0
        assert -1 <= depth_profile.imbalance_ratio <= 1

    def test_calculate_liquidity_score(self, analyzer):
        """Test liquidity score calculation"""
        score = analyzer.calculate_liquidity_score(
            spread_bps=5.0,
            depth=Decimal("100000"),
            volatility=0.02,
            volume=5_000_000,
        )

        # Score should be between 0 and 100
        assert 0 <= score <= 100

    def test_liquidity_score_extreme_cases(self, analyzer):
        """Test liquidity score at extremes"""
        # Very illiquid (wide spread, low depth, high volatility)
        poor_score = analyzer.calculate_liquidity_score(
            spread_bps=100.0,
            depth=Decimal("100"),
            volatility=0.10,
            volume=10000,
        )

        # Very liquid (tight spread, high depth, low volatility)
        good_score = analyzer.calculate_liquidity_score(
            spread_bps=1.0,
            depth=Decimal("10000000"),
            volatility=0.005,
            volume=50_000_000,
        )

        # Good score should be higher than poor score
        assert good_score > poor_score

    def test_classify_liquidity_regime(self, analyzer):
        """Test liquidity regime classification"""
        assert analyzer.classify_liquidity_regime(90) == 'HIGH'
        assert analyzer.classify_liquidity_regime(70) == 'NORMAL'
        assert analyzer.classify_liquidity_regime(50) == 'LOW'
        assert analyzer.classify_liquidity_regime(30) == 'POOR'

    def test_decompose_spread(self, analyzer):
        """Test spread decomposition"""
        decomposition = analyzer.decompose_spread(
            spread_bps=10.0,
            price_variance=0.0001,
            order_flow_imbalance=0.2,
            volume=5_000_000,
            volatility=0.02,
        )

        # Should decompose into components
        assert abs(decomposition.total_spread_bps - 10.0) < 0.1
        assert decomposition.order_processing_bps >= 0
        assert decomposition.inventory_holding_bps >= 0
        assert decomposition.adverse_selection_bps >= 0
        assert decomposition.dominant_component in SpreadComponent

    def test_calculate_effective_spread(self, analyzer):
        """Test effective spread calculation"""
        effective_spread = analyzer.calculate_effective_spread(
            execution_price=100.05,
            bid_price=99.98,
            ask_price=100.02,
            side='BUY',
        )

        # Should be positive for buy above midpoint
        assert effective_spread >= 0

    def test_measure_market_resilience(self, analyzer):
        """Test market resilience measurement"""
        # Create price history with shock
        prices = [100.0] * 50 + [102.0] * 50  # Shock at period 50
        price_history = pd.DataFrame(
            {
                'close': prices,
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1s'),
        )

        shock_times = [price_history.index[50]]

        resilience = analyzer.measure_market_resilience(
            price_history,
            shock_times,
            recovery_window_seconds=30,
        )

        # Should return non-negative resilience score
        assert resilience >= 0

    def test_assess_liquidity_risk(self, analyzer):
        """Test liquidity risk assessment"""
        risk = analyzer.assess_liquidity_risk(
            required_size=Decimal("100000"),
            available_depth=Decimal("50000"),
            volatility=0.03,
            average_daily_volume=5_000_000,
            urgency='HIGH',
        )

        # Should return valid risk assessment
        assert risk.liquidity_gap >= 0
        assert 0 <= risk.execution_shortfall_risk <= 1
        assert risk.risk_level in ['LOW', 'MEDIUM', 'HIGH']
        assert isinstance(risk.recommendations, list)

    def test_calculate_liquidity_metrics(self, analyzer, sample_order_book, sample_price_history):
        """Test comprehensive liquidity metrics calculation"""
        metrics = analyzer.calculate_liquidity_metrics(
            symbol='AAPL',
            order_book=sample_order_book,
            price_history=sample_price_history,
            volume=5_000_000,
            target_size=Decimal("10000"),
        )

        # Should return valid metrics
        assert metrics.bid_ask_spread_bps >= 0
        assert metrics.quoted_depth > 0
        assert 0 <= metrics.liquidity_score <= 100
        assert metrics.liquidity_regime in ['HIGH', 'NORMAL', 'LOW', 'POOR']

    def test_get_liquidity_trend(self, analyzer, sample_order_book, sample_price_history):
        """Test liquidity trend calculation"""
        # Add some historical metrics
        for i in range(10):
            analyzer.calculate_liquidity_metrics(
                symbol='AAPL',
                order_book=sample_order_book,
                price_history=sample_price_history,
                volume=5_000_000,
            )

        trend = analyzer.get_liquidity_trend()

        # Should return valid trend
        assert trend in ['IMPROVING', 'STABLE', 'DETERIORATING', 'UNKNOWN']

    def test_generate_liquidity_report(self, analyzer, sample_order_book, sample_price_history):
        """Test comprehensive liquidity report generation"""
        report = analyzer.generate_liquidity_report(
            symbol='AAPL',
            order_book=sample_order_book,
            price_history=sample_price_history,
            volume=5_000_000,
            required_size=Decimal("10000"),
        )

        # Should contain all required sections
        assert 'symbol' in report
        assert 'metrics' in report
        assert 'depth_profile' in report
        assert 'spread_decomposition' in report
        assert 'liquidity_risk' in report
        assert 'trend' in report
        assert 'recommendations' in report


class TestLiquidityMonitor:
    """Test LiquidityMonitor"""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance"""
        return LiquidityMonitor(
            liquidity_threshold=50.0,
            alert_window_minutes=5,
        )

    def test_check_liquidity_alert_low_score(self, monitor):
        """Test alert for low liquidity score"""
        from app.microstructure.liquidity import LiquidityMetrics

        low_metrics = LiquidityMetrics(
            timestamp=datetime.now(),
            bid_ask_spread_bps=50.0,
            quoted_depth=Decimal("100"),
            effective_spread_bps=50.0,
            depth_slope=0.1,
            liquidity_score=30.0,  # Below threshold
            liquidity_regime='POOR',
        )

        alert = monitor.check_liquidity_alert(low_metrics)

        # Should trigger alert
        assert alert is not None
        assert alert['type'] == 'LOW_LIQUIDITY'

    def test_check_liquidity_alert_no_alert(self, monitor):
        """Test no alert for good liquidity"""
        from app.microstructure.liquidity import LiquidityMetrics

        good_metrics = LiquidityMetrics(
            timestamp=datetime.now(),
            bid_ask_spread_bps=2.0,
            quoted_depth=Decimal("1000000"),
            effective_spread_bps=2.0,
            depth_slope=0.5,
            liquidity_score=80.0,  # Above threshold
            liquidity_regime='HIGH',
        )

        alert = monitor.check_liquidity_alert(good_metrics)

        # Should not trigger alert
        assert alert is None


class TestSpreadDecomposition:
    """Test spread decomposition"""

    def test_spread_components_sum_to_total(self):
        """Test that components sum to total spread"""
        decomposition = SpreadDecomposition(
            timestamp=datetime.now(),
            total_spread_bps=10.0,
            order_processing_bps=3.0,
            inventory_holding_bps=3.5,
            adverse_selection_bps=3.5,
            dominant_component=SpreadComponent.ADVERSE_SELECTION,
        )

        # Components should sum to approximately total
        component_sum = (
            decomposition.order_processing_bps
            + decomposition.inventory_holding_bps
            + decomposition.adverse_selection_bps
        )

        assert abs(component_sum - decomposition.total_spread_bps) < 0.1


class TestDepthProfile:
    """Test depth profile"""

    def test_depth_profile_calculation(self):
        """Test depth profile creation"""
        profile = DepthProfile(
            timestamp=datetime.now(),
            bid_levels=[
                (Decimal("99.99"), Decimal("1000")),
                (Decimal("99.98"), Decimal("3000")),
            ],
            ask_levels=[
                (Decimal("100.01"), Decimal("1000")),
                (Decimal("100.02"), Decimal("3000")),
            ],
            total_bid_depth=Decimal("3000"),
            total_ask_depth=Decimal("3000"),
            imbalance_ratio=0.0,
        )

        # Bid levels should be in descending price order
        assert profile.bid_levels[0][0] > profile.bid_levels[1][0]

        # Ask levels should be in ascending price order
        assert profile.ask_levels[0][0] < profile.ask_levels[1][0]


class TestSingletonFunctions:
    """Test singleton instance functions"""

    def test_get_liquidity_analyzer(self):
        """Test singleton analyzer"""
        analyzer1 = get_liquidity_analyzer()
        analyzer2 = get_liquidity_analyzer()

        # Should return same instance
        assert analyzer1 is analyzer2

    def test_get_liquidity_monitor(self):
        """Test singleton monitor"""
        monitor1 = get_liquidity_monitor()
        monitor2 = get_liquidity_monitor()

        # Should return same instance
        assert monitor1 is monitor2


@pytest.mark.integration
class TestLiquidityIntegration:
    """Integration tests for liquidity module"""

    def test_full_liquidity_analysis(self):
        """Test complete liquidity analysis workflow"""
        analyzer = get_liquidity_analyzer()

        # Create realistic order book
        order_book = {
            'bids': [
                (Decimal(f"{100 - i*0.01:.2f}"), Decimal(str((i + 1) * 1000))) for i in range(10)
            ],
            'asks': [
                (Decimal(f"{100 + i*0.01:.2f}"), Decimal(str((i + 1) * 1000))) for i in range(10)
            ],
        }

        # Create price history
        price_history = pd.DataFrame(
            {
                'close': [100 + np.random.randn() * 0.1 for _ in range(100)],
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1min'),
        )

        # Generate report
        report = analyzer.generate_liquidity_report(
            symbol='AAPL',
            order_book=order_book,
            price_history=price_history,
            volume=5_000_000,
            required_size=Decimal("50000"),
        )

        # Validate report structure
        assert report['symbol'] == 'AAPL'
        assert 'metrics' in report
        assert report['metrics']['liquidity_score'] >= 0
        assert len(report['recommendations']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
