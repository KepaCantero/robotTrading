"""
Unit tests for Order Flow module

Tests for order flow analysis and information asymmetry measurement
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.microstructure.order_flow import (
    Order,
    OrderFlowAnalyzer,
    OrderFlowSimulator,
    OrderFlowSnapshot,
    OrderSide,
    OrderType,
    TraderType,
    get_order_flow_analyzer,
    get_order_flow_simulator,
)


class TestOrder:
    """Test Order dataclass"""

    def test_order_creation(self):
        """Test creating an order"""
        order = Order(
            order_id="test_001",
            timestamp=datetime.now(),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            size=Decimal("1000"),
        )

        assert order.order_id == "test_001"
        assert order.side == OrderSide.BUY
        assert order.size == Decimal("1000")
        assert order.price is None


class TestOrderFlowSnapshot:
    """Test OrderFlowSnapshot dataclass"""

    def test_snapshot_imbalance_calculation(self):
        """Test order imbalance calculation"""
        snapshot = OrderFlowSnapshot(
            timestamp=datetime.now(),
            buy_volume=Decimal("6000"),
            sell_volume=Decimal("4000"),
            buy_count=60,
            sell_count=40,
        )

        # Imbalance = (6000 - 4000) / (6000 + 4000) = 0.2
        assert abs(float(snapshot.order_imbalance) - 0.2) < 0.01


class TestOrderFlowAnalyzer:
    """Test OrderFlowAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return OrderFlowAnalyzer(lookback_seconds=300, alpha_threshold=0.3)

    @pytest.fixture
    def sample_orders(self):
        """Create sample orders"""
        now = datetime.now()
        return [
            Order(
                order_id=f"order_{i}",
                timestamp=now + timedelta(seconds=i),
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                price=Decimal("100") if i % 2 == 0 else None,
                size=Decimal(str(1000 + i * 100)),
                trader_type=TraderType.INFORMED if i % 3 == 0 else TraderType.UNINFORMED,
            )
            for i in range(20)
        ]

    def test_add_order(self, analyzer, sample_orders):
        """Test adding orders to history"""
        initial_count = len(analyzer._order_history)

        for order in sample_orders:
            analyzer.add_order(order)

        assert len(analyzer._order_history) >= initial_count

    def test_calculate_order_imbalance(self, analyzer, sample_orders):
        """Test order imbalance calculation"""
        for order in sample_orders:
            analyzer.add_order(order)

        imbalance = analyzer.calculate_order_imbalance()

        # Should be between -1 and 1
        assert -1 <= imbalance <= 1

    def test_calculate_order_imbalance_no_orders(self, analyzer):
        """Test imbalance with no orders"""
        imbalance = analyzer.calculate_order_imbalance()

        # Should return 0 for no orders
        assert imbalance == 0

    def test_estimate_order_flow_toxicity(self, analyzer):
        """Test toxicity estimation"""
        # Create sample trade data
        trades_df = pd.DataFrame(
            {
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1s'),
                'side': np.random.choice(['BUY', 'SELL'], 100),
                'size': np.random.randint(100, 1000, 100),
                'price': 100 + np.random.randn(100).cumsum() * 0.1,
            }
        )

        price_changes = pd.Series(np.random.randn(100) * 0.01)

        toxicity = analyzer.estimate_order_flow_toxicity(trades_df, price_changes)

        # Toxicity should be between 0 and 1
        assert 0 <= toxicity <= 1

    def test_calculate_probability_of_informed_trading(self, analyzer):
        """Test PIN calculation"""
        now = datetime.now()
        snapshots = [
            OrderFlowSnapshot(
                timestamp=now + timedelta(seconds=i),
                buy_volume=Decimal(str(5000 + i * 100)),
                sell_volume=Decimal(str(4000 + i * 100)),
                buy_count=50 + i,
                sell_count=40 + i,
            )
            for i in range(20)
        ]

        pin = analyzer.calculate_probability_of_informed_trading(
            snapshots,
            price_volatility=0.02,
        )

        # PIN should be between 0 and 1
        assert 0 <= pin <= 1

    def test_detect_informed_trading(self, analyzer):
        """Test informed trading detection"""
        now = datetime.now()
        orders = [
            Order(
                order_id=f"inf_{i}",
                timestamp=now + timedelta(seconds=i),
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                price=None,
                size=Decimal("10000"),  # Large orders
            )
            for i in range(10)
        ]

        price_history = pd.DataFrame(
            {
                'close': [100 + i * 0.1 for i in range(100)],
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1s'),
        )

        detected, confidence, explanation = analyzer.detect_informed_trading(orders, price_history)

        # Should return valid results
        assert isinstance(detected, bool)
        assert 0 <= confidence <= 1
        assert isinstance(explanation, str)

    def test_measure_adverse_selection_cost(self, analyzer):
        """Test adverse selection cost measurement"""
        executions = pd.DataFrame(
            {
                'timestamp': pd.date_range('2024-01-01', periods=50, freq='1s'),
                'side': np.random.choice(['BUY', 'SELL'], 50),
                'price': 100 + np.random.randn(50) * 0.5,
                'size': np.random.randint(100, 1000, 50),
            }
        )

        subsequent_prices = pd.Series(100 + np.random.randn(50) * 0.5)

        cost_metrics = analyzer.measure_adverse_selection_cost(executions, subsequent_prices)

        # Should return all required metrics
        assert 'avg_adverse_cost_bps' in cost_metrics
        assert 'adverse_selection_rate' in cost_metrics
        assert 'total_adverse_cost_usd' in cost_metrics

    def test_forecast_order_flow(self, analyzer, sample_orders):
        """Test order flow forecasting"""
        for order in sample_orders:
            analyzer.add_order(order)

        forecast = analyzer.forecast_order_flow(
            forecast_horizon_seconds=60,
            method="exponential_smoothing",
        )

        # Should return valid forecast
        assert forecast.forecast_time > datetime.now()
        assert -1 <= float(forecast.expected_imbalance) <= 1

    def test_calculate_information_content(self, analyzer):
        """Test information content calculation"""
        now = datetime.now()
        orders = [
            Order(
                order_id=f"info_{i}",
                timestamp=now + timedelta(seconds=i),
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET if i % 3 == 0 else OrderType.LIMIT,
                price=Decimal("100") if i % 3 != 0 else None,
                size=Decimal("1000"),
            )
            for i in range(20)
        ]

        metrics = analyzer.calculate_information_content(
            orders,
            market_price=Decimal("100"),
        )

        # Should return valid metrics
        assert 0 <= metrics['information_content'] <= 1
        assert 0 <= metrics['signal_to_noise_ratio'] <= 1
        assert metrics['information_quality'] in ['LOW', 'MEDIUM', 'HIGH']

    def test_generate_order_flow_report(self, analyzer, sample_orders):
        """Test comprehensive report generation"""
        price_history = pd.DataFrame(
            {
                'close': [100 + i * 0.1 for i in range(100)],
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1s'),
        )

        report = analyzer.generate_order_flow_report(
            current_orders=sample_orders,
            price_history=price_history,
        )

        # Should contain all required fields
        assert 'order_imbalance' in report
        assert 'informed_trading_detected' in report
        assert 'information_content' in report
        assert 'adverse_selection_risk' in report
        assert 'recommendations' in report


class TestOrderFlowSimulator:
    """Test OrderFlowSimulator"""

    @pytest.fixture
    def simulator(self):
        """Create simulator instance"""
        return OrderFlowSimulator(
            informed_trader_probability=0.2,
            information_event_probability=0.05,
        )

    def test_generate_order_flow(self, simulator):
        """Test order flow generation"""
        orders = simulator.generate_order_flow(
            num_orders=100,
            base_price=100.0,
            price_impact=0.001,
            spread_bps=5.0,
        )

        # Should generate correct number of orders
        assert len(orders) == 100

        # All orders should have valid fields
        for order in orders:
            assert order.order_id.startswith('sim_')
            assert order.side in [OrderSide.BUY, OrderSide.SELL]
            assert order.size > 0
            assert order.trader_type in [TraderType.INFORMED, TraderType.UNINFORMED]

    def test_informed_trader_ratio(self, simulator):
        """Test informed trader ratio in simulation"""
        orders = simulator.generate_order_flow(
            num_orders=1000,
            base_price=100.0,
        )

        informed_count = sum(1 for o in orders if o.trader_type == TraderType.INFORMED)

        # Ratio should be close to target (allow 10% tolerance)
        actual_ratio = informed_count / len(orders)
        target_ratio = simulator.informed_trader_probability

        assert abs(actual_ratio - target_ratio) < 0.1


class TestSingletonFunctions:
    """Test singleton instance functions"""

    def test_get_order_flow_analyzer(self):
        """Test singleton analyzer"""
        analyzer1 = get_order_flow_analyzer()
        analyzer2 = get_order_flow_analyzer()

        # Should return same instance
        assert analyzer1 is analyzer2

    def test_get_order_flow_simulator(self):
        """Test singleton simulator"""
        sim1 = get_order_flow_simulator()
        sim2 = get_order_flow_simulator()

        # Should return same instance
        assert sim1 is sim2


@pytest.mark.integration
class TestOrderFlowIntegration:
    """Integration tests for order flow module"""

    def test_full_order_flow_analysis(self):
        """Test complete order flow analysis workflow"""
        analyzer = get_order_flow_analyzer()

        # Create realistic order flow
        now = datetime.now()
        orders = []
        for i in range(50):
            orders.append(
                Order(
                    order_id=f"order_{i}",
                    timestamp=now + timedelta(milliseconds=i * 100),
                    side=OrderSide.BUY if i % 3 == 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET if i % 2 == 0 else OrderType.LIMIT,
                    price=Decimal("100.00") if i % 2 != 0 else None,
                    size=Decimal(str(1000 + i * 50)),
                    trader_type=TraderType.INFORMED if i % 5 == 0 else TraderType.UNINFORMED,
                )
            )

        # Create price history
        price_history = pd.DataFrame(
            {
                'close': [100 + i * 0.05 + np.random.randn() * 0.1 for i in range(100)],
            },
            index=pd.date_range('2024-01-01', periods=100, freq='1s'),
        )

        # Generate report
        report = analyzer.generate_order_flow_report(
            current_orders=orders,
            price_history=price_history,
        )

        # Validate report structure
        assert 'timestamp' in report
        assert 'order_imbalance' in report
        assert 'information_content' in report
        assert 'forecast_imbalance' in report
        assert len(report['recommendations']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
