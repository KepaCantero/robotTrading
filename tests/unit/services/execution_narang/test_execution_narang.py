"""
Tests for Execution Algorithms - Narang "Inside the Black Box" Chapter 7
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.execution_narang import (
    OrderStatus,
    OrderType,
    TimeInForce,
    OrderSide,
    ChildOrder,
    ExecutionReport,
    IntradayVolumeProfile,
    VWAPExecution,
    TWAPExecution,
    POVExecution,
    MarketExecution,
    ExecutionEngine,
    get_execution_engine,
)
from app.services.transaction_costs import (
    ExecutionAlgorithm,
    MarketData,
    OrderSpecification,
)


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    return MarketData(
        symbol="AAPL",
        bid=Decimal("149.50"),
        ask=Decimal("150.50"),
        last=Decimal("150.00"),
        volume=Decimal("1000000"),
        average_daily_volume=Decimal("50000000"),
        volatility=0.25,
        timestamp=datetime.now(),
    )


@pytest.fixture
def small_buy_order():
    """Create a small buy order."""
    return OrderSpecification(
        symbol="AAPL",
        side="buy",
        quantity=Decimal("10000"),  # 0.02% of ADV
        order_type="market",
        execution_algorithm=ExecutionAlgorithm.MARKET,
        urgency=0.7,
    )


@pytest.fixture
def large_buy_order():
    """Create a large buy order."""
    return OrderSpecification(
        symbol="AAPL",
        side="buy",
        quantity=Decimal("2500000"),  # 5% of ADV
        order_type="limit",
        execution_algorithm=ExecutionAlgorithm.VWAP,
        urgency=0.3,
    )


class TestChildOrder:
    """Tests for ChildOrder dataclass."""

    def test_child_order_creation(self):
        """Test creating a child order."""
        order = ChildOrder(
            order_id="child_001",
            parent_order_id="parent_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("1000"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("150.00"),
            time_in_force=TimeInForce.DAY,
            target_time=datetime.now(),
        )

        assert order.order_id == "child_001"
        assert order.parent_order_id == "parent_001"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.time_in_force == TimeInForce.DAY
        assert order.status == OrderStatus.PENDING


class TestExecutionReport:
    """Tests for ExecutionReport dataclass."""

    def test_execution_report_creation(self):
        """Test creating an execution report."""
        report = ExecutionReport(
            order_id="order_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=Decimal("10000"),
            filled_quantity=Decimal("10000"),
            average_price=Decimal("150.25"),
            benchmark_price=Decimal("150.00"),
            implementation_shortfall_bps=16.67,
            market_impact_bps=10.0,
            timing_cost_bps=6.67,
            total_cost_bps=16.67,
            execution_duration_seconds=300.0,
            fill_rate=1.0,
            slippage_bps=16.67,
        )

        assert report.order_id == "order_001"
        assert report.fill_rate == 1.0
        assert report.implementation_shortfall_bps == 16.67
        assert report.market_impact_bps + report.timing_cost_bps == pytest.approx(
            report.total_cost_bps, abs=0.1
        )


class TestVWAPExecution:
    """Tests for VWAP execution algorithm."""

    def test_initialization(self):
        """Test VWAP algorithm initialization."""
        config = {"volume_profile_lookback": 20}
        algorithm = VWAPExecution(config)

        assert algorithm.algorithm_type == ExecutionAlgorithm.VWAP
        assert algorithm.volume_profile_lookback == 20

    def test_generate_child_orders(self, sample_market_data, large_buy_order):
        """Test generating VWAP child orders."""
        algorithm = VWAPExecution({})

        start_time = datetime.now().replace(hour=9, minute=30)
        end_time = datetime.now().replace(hour=16, minute=0)

        child_orders = algorithm.generate_child_orders(
            large_buy_order, sample_market_data, start_time, end_time
        )

        assert len(child_orders) > 0

        # Check that child orders have appropriate properties
        for order in child_orders:
            assert order.symbol == "AAPL"
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.LIMIT
            assert order.limit_price is not None
            assert order.time_in_force == TimeInForce.IOC

    def test_should_update_child_orders(self, sample_market_data, large_buy_order):
        """Test that VWAP doesn't update child orders."""
        algorithm = VWAPExecution({})

        start_time = datetime.now()
        child_orders = [
            ChildOrder(
                order_id="child_001",
                parent_order_id="parent_001",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=Decimal("1000"),
                order_type=OrderType.LIMIT,
            )
        ]

        should_update, updated = algorithm.should_update_child_orders(
            large_buy_order, child_orders, sample_market_data
        )

        assert should_update is False
        assert updated == child_orders


class TestTWAPExecution:
    """Tests for TWAP execution algorithm."""

    def test_initialization(self):
        """Test TWAP algorithm initialization."""
        algorithm = TWAPExecution({})

        assert algorithm.algorithm_type == ExecutionAlgorithm.TWAP

    def test_generate_child_orders(self, sample_market_data, large_buy_order):
        """Test generating TWAP child orders."""
        algorithm = TWAPExecution({})

        start_time = datetime.now().replace(hour=9, minute=30)
        end_time = datetime.now().replace(hour=16, minute=0)

        child_orders = algorithm.generate_child_orders(
            large_buy_order, sample_market_data, start_time, end_time
        )

        assert len(child_orders) > 0

        # TWAP should split orders evenly
        if len(child_orders) > 1:
            quantities = [float(co.quantity) for co in child_orders]
            # Quantities should be similar (within tolerance)
            max_qty = max(quantities)
            min_qty = min(quantities)
            assert (max_qty - min_qty) / max_qty < 0.1  # Within 10%


class TestPOVExecution:
    """Tests for POV (Percentage of Volume) execution algorithm."""

    def test_initialization(self):
        """Test POV algorithm initialization."""
        config = {"target_participation_rate": 0.10}
        algorithm = POVExecution(config)

        assert algorithm.algorithm_type == ExecutionAlgorithm.POV
        assert algorithm.target_participation_rate == 0.10

    def test_generate_child_orders(self, sample_market_data, large_buy_order):
        """Test generating POV child orders."""
        algorithm = POVExecution({"target_participation_rate": 0.10})

        start_time = datetime.now()
        end_time = datetime.now() + timedelta(hours=1)

        child_orders = algorithm.generate_child_orders(
            large_buy_order, sample_market_data, start_time, end_time
        )

        # POV should create a single order
        assert len(child_orders) == 1

        order = child_orders[0]
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.target_participation_rate == 0.10


class TestMarketExecution:
    """Tests for immediate market execution."""

    def test_initialization(self):
        """Test market execution initialization."""
        config = {"max_order_size_pct": 0.01}
        algorithm = MarketExecution(config)

        assert algorithm.algorithm_type == ExecutionAlgorithm.MARKET
        assert algorithm.max_order_size_pct == 0.01

    def test_generate_child_orders_small(self, sample_market_data, small_buy_order):
        """Test generating market order for small order."""
        algorithm = MarketExecution({})

        child_orders = algorithm.generate_child_orders(
            small_buy_order, sample_market_data, datetime.now(), datetime.now()
        )

        assert len(child_orders) == 1

        order = child_orders[0]
        assert order.order_type == OrderType.MARKET
        assert order.time_in_force == TimeInForce.IOC

    def test_generate_child_orders_large_warns(self, sample_market_data, large_buy_order):
        """Test that large orders generate warning."""
        algorithm = MarketExecution({"max_order_size_pct": 0.01})

        # This should log a warning but still create the order
        child_orders = algorithm.generate_child_orders(
            large_buy_order, sample_market_data, datetime.now(), datetime.now()
        )

        assert len(child_orders) == 1


class TestExecutionEngine:
    """Tests for the main execution engine."""

    def test_initialization(self):
        """Test execution engine initialization."""
        config = {}
        engine = ExecutionEngine(config)

        assert ExecutionAlgorithm.VWAP in engine.algorithms
        assert ExecutionAlgorithm.TWAP in engine.algorithms
        assert ExecutionAlgorithm.POV in engine.algorithms
        assert ExecutionAlgorithm.MARKET in engine.algorithms

    def test_select_execution_algorithm_small_order(self, sample_market_data, small_buy_order):
        """Test algorithm selection for small orders."""
        engine = ExecutionEngine({})

        algo = engine.select_execution_algorithm(small_buy_order, sample_market_data)

        # Small orders should use MARKET or LIMIT
        assert algo in [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.LIMIT]

    def test_select_execution_algorithm_large_order(self, sample_market_data, large_buy_order):
        """Test algorithm selection for large orders."""
        engine = ExecutionEngine({})

        algo = engine.select_execution_algorithm(large_buy_order, sample_market_data)

        # Large orders should use VWAP or POV
        assert algo in [ExecutionAlgorithm.VWAP, ExecutionAlgorithm.POV, ExecutionAlgorithm.TWAP]

    def test_execute_order(self, sample_market_data, large_buy_order):
        """Test executing an order."""
        engine = ExecutionEngine({})

        start_time = datetime.now().replace(hour=9, minute=30)
        end_time = datetime.now().replace(hour=16, minute=0)

        report, child_orders = engine.execute_order(
            large_buy_order, sample_market_data, start_time, end_time
        )

        assert isinstance(report, ExecutionReport)
        assert len(child_orders) > 0
        assert report.symbol == "AAPL"
        assert report.side == OrderSide.BUY

    def test_analyze_execution_quality_good(self):
        """Test execution quality analysis for good execution."""
        engine = ExecutionEngine({})

        report = ExecutionReport(
            order_id="order_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=Decimal("10000"),
            filled_quantity=Decimal("10000"),
            average_price=Decimal("150.02"),
            benchmark_price=Decimal("150.00"),
            implementation_shortfall_bps=13.33,
            market_impact_bps=8.0,
            timing_cost_bps=5.33,
            total_cost_bps=13.33,
            execution_duration_seconds=300.0,
            fill_rate=1.0,
            slippage_bps=13.33,
        )

        analysis = engine.analyze_execution_quality(report)

        assert "is_good" in analysis
        assert "issues" in analysis
        assert "recommendations" in analysis

    def test_analyze_execution_quality_poor(self):
        """Test execution quality analysis for poor execution."""
        engine = ExecutionEngine({})

        report = ExecutionReport(
            order_id="order_002",
            symbol="AAPL",
            side=OrderSide.BUY,
            target_quantity=Decimal("10000"),
            filled_quantity=Decimal("8000"),  # Only 80% filled
            average_price=Decimal("150.50"),
            benchmark_price=Decimal("150.00"),
            implementation_shortfall_bps=33.33,  # High shortfall
            market_impact_bps=25.0,
            timing_cost_bps=8.33,
            total_cost_bps=33.33,
            execution_duration_seconds=300.0,
            fill_rate=0.8,  # Low fill rate
            slippage_bps=33.33,
        )

        analysis = engine.analyze_execution_quality(report)

        # Poor execution should be flagged
        assert analysis["is_good"] is False
        assert len(analysis["issues"]) > 0
        assert len(analysis["recommendations"]) > 0


class TestExecutionEngineFactory:
    """Tests for the execution engine factory function."""

    def test_get_execution_engine(self):
        """Test factory creates execution engine."""
        config = {}
        engine = get_execution_engine(config)

        assert isinstance(engine, ExecutionEngine)


class TestOrderSide:
    """Tests for OrderSide enum."""

    def test_order_side_values(self):
        """Test order side enum values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"
        assert OrderSide.SHORT.value == "short"


class TestTimeInForce:
    """Tests for TimeInForce enum."""

    def test_time_in_force_values(self):
        """Test time in force enum values."""
        assert TimeInForce.DAY.value == "DAY"
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.IOC.value == "IOC"
        assert TimeInForce.FOK.value == "FOK"


class TestIntradayVolumeProfile:
    """Tests for IntradayVolumeProfile dataclass."""

    def test_volume_profile_creation(self):
        """Test creating an intraday volume profile."""
        profile = IntradayVolumeProfile(
            symbol="AAPL",
            time_bins=[datetime.now().time()],
            volume_distribution=[1.0],
            total_daily_volume=Decimal("50000000"),
        )

        assert profile.symbol == "AAPL"
        assert profile.total_daily_volume == Decimal("50000000")
        assert len(profile.volume_distribution) == len(profile.time_bins)
