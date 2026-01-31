"""
Tests for Transaction Cost Models - Narang "Inside the Black Box" Chapter 5
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.services.transaction_costs import (
    CostComponent,
    MarketImpactModel,
    ExecutionAlgorithm,
    MarketData,
    OrderSpecification,
    CostBreakdown,
    TransactionCostModel,
    CommissionModel,
    AlmgrenChrissModel,
    get_transaction_cost_model,
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
        average_daily_volume=Decimal("50000000"),  # 50M shares daily
        volatility=0.25,  # 25% annualized
        timestamp=datetime.now(),
    )


@pytest.fixture
def small_buy_order():
    """Create a small buy order (0.5% of ADV)."""
    return OrderSpecification(
        symbol="AAPL",
        side="buy",
        quantity=Decimal("250000"),  # 250K shares = 0.5% of 50M ADV
        order_type="market",
        execution_algorithm=ExecutionAlgorithm.MARKET,
        urgency=0.5,
    )


@pytest.fixture
def large_buy_order():
    """Create a large buy order (5% of ADV)."""
    return OrderSpecification(
        symbol="AAPL",
        side="buy",
        quantity=Decimal("2500000"),  # 2.5M shares = 5% of 50M ADV
        order_type="market",
        execution_algorithm=ExecutionAlgorithm.VWAP,
        urgency=0.3,
    )


class TestMarketData:
    """Tests for MarketData class."""

    def test_market_data_properties(self, sample_market_data):
        """Test market data calculated properties."""
        assert sample_market_data.spread == Decimal("1.00")  # 150.50 - 149.50
        assert sample_market_data.mid_price == Decimal("150.00")  # (149.50 + 150.50) / 2


class TestTransactionCostModel:
    """Tests for base TransactionCostModel."""

    def test_initialization(self):
        """Test transaction cost model initialization."""
        config = {
            "commission_per_share": 0.005,
            "impact_coefficient": 0.1,
            "max_participation_rate": 0.01,
        }
        model = TransactionCostModel(config)

        assert model.commission_per_share == Decimal("0.005")
        assert model.impact_coefficient == 0.1
        assert model.max_participation_rate == 0.01

    def test_calculate_commission(self, sample_market_data):
        """Test commission calculation."""
        model = TransactionCostModel({})

        commission = model._calculate_commission(Decimal("1000"), "buy")

        # Commission = quantity * commission_per_share
        # Min commission applies
        assert commission >= model.min_commission

    def test_calculate_spread_cost(self, sample_market_data, small_buy_order):
        """Test spread cost calculation."""
        model = TransactionCostModel({})

        spread_cost = model._calculate_spread_cost(small_buy_order, sample_market_data)

        # Spread cost = (spread / 2) * quantity
        # = (1.00 / 2) * 250000 = 125000
        expected = (sample_market_data.spread / 2) * small_buy_order.quantity
        assert spread_cost == expected

    def test_calculate_market_impact_square_root(self, sample_market_data, small_buy_order):
        """Test market impact calculation with square root model."""
        config = {"impact_model": "square_root", "impact_coefficient": 0.1}
        model = TransactionCostModel(config)

        impact, participation_rate = model._calculate_market_impact(
            small_buy_order, sample_market_data
        )

        assert impact >= 0
        assert participation_rate == 0.005  # 250K / 50M
        assert model.impact_model == MarketImpactModel.SQUARE_ROOT

    def test_calculate_market_impact_linear(self, sample_market_data, small_buy_order):
        """Test market impact calculation with linear model."""
        config = {"impact_model": "linear", "impact_coefficient": 0.1}
        model = TransactionCostModel(config)

        impact, participation_rate = model._calculate_market_impact(
            small_buy_order, sample_market_data
        )

        assert impact >= 0
        assert participation_rate == 0.005

    def test_calculate_timing_risk(self, sample_market_data, small_buy_order):
        """Test timing risk calculation."""
        model = TransactionCostModel({})

        timing_risk = model._calculate_timing_risk(
            small_buy_order,
            sample_market_data,
            participation_rate=0.005,
        )

        assert timing_risk >= 0

    def test_calculate_transaction_costs(self, sample_market_data, small_buy_order):
        """Test complete transaction cost calculation."""
        model = TransactionCostModel({})

        cost_breakdown = model.calculate_transaction_costs(
            small_buy_order, sample_market_data, "order_123"
        )

        assert isinstance(cost_breakdown, CostBreakdown)
        assert cost_breakdown.symbol == "AAPL"
        assert cost_breakdown.side == "buy"
        assert cost_breakdown.quantity == Decimal("250000")

        # Check that all cost components are non-negative
        assert cost_breakdown.commission >= 0
        assert cost_breakdown.spread_cost >= 0
        assert cost_breakdown.market_impact >= 0
        assert cost_breakdown.timing_risk >= 0
        assert cost_breakdown.total_cost >= 0

        # Total should equal sum of components
        expected_total = (
            cost_breakdown.commission
            + cost_breakdown.spread_cost
            + cost_breakdown.market_impact
            + cost_breakdown.timing_risk
            + cost_breakdown.fees
            + cost_breakdown.taxes
        )
        assert cost_breakdown.total_cost == expected_total

    def test_validate_order_type_small(self, sample_market_data, small_buy_order):
        """Test order type validation for small orders."""
        model = TransactionCostModel({})

        is_valid, message = model.validate_order_type(small_buy_order, sample_market_data)

        # Small order with market type should be valid
        assert is_valid is True
        assert message is None

    def test_validate_order_type_large(self, sample_market_data, large_buy_order):
        """Test order type validation for large orders."""
        model = TransactionCostModel({})

        # Large order with market execution should fail validation
        large_buy_order.execution_algorithm = ExecutionAlgorithm.MARKET
        is_valid, message = model.validate_order_type(large_buy_order, sample_market_data)

        assert is_valid is False
        assert message is not None
        assert "VWAP" in message or "TWAP" in message

    def test_recommend_execution_algorithm(self, sample_market_data):
        """Test execution algorithm recommendation."""
        model = TransactionCostModel({})

        # Very small order
        tiny_order = OrderSpecification(
            symbol="AAPL",
            side="buy",
            quantity=Decimal("10000"),  # 0.02% of ADV
            order_type="market",
            urgency=0.5,
        )

        algo = model.recommend_execution_algorithm(tiny_order, sample_market_data)
        assert algo == ExecutionAlgorithm.MARKET

        # Large order
        large_order = OrderSpecification(
            symbol="AAPL",
            side="buy",
            quantity=Decimal("5000000"),  # 10% of ADV
            order_type="market",
            urgency=0.3,
        )

        algo = model.recommend_execution_algorithm(large_order, sample_market_data)
        assert algo in [ExecutionAlgorithm.VWAP, ExecutionAlgorithm.POV]


class TestAlmgrenChrissModel:
    """Tests for Almgren-Chriss market impact model."""

    def test_initialization(self):
        """Test Almgren-Chriss model initialization."""
        config = {
            "permanent_impact_coef": 0.1,
            "temporary_impact_coef": 0.5,
            "liquidity_parameter": 0.01,
        }
        model = AlmgrenChrissModel(config)

        assert model.permanent_impact_coef == 0.1
        assert model.temporary_impact_coef == 0.5
        assert model.impact_model == MarketImpactModel.SQUARE_ROOT

    def test_calculate_market_impact_almgren_chriss(self, sample_market_data, large_buy_order):
        """Test Almgren-Chriss market impact calculation."""
        model = AlmgrenChrissModel({})

        impact, participation_rate = model._calculate_market_impact(
            large_buy_order, sample_market_data
        )

        assert impact >= 0
        # Large order should have significant impact
        assert participation_rate == 0.05  # 2.5M / 50M


class TestCommissionModel:
    """Tests for commission-only cost model."""

    def test_only_commission_charged(self, sample_market_data, small_buy_order):
        """Test that only commission is charged."""
        model = CommissionModel({})

        cost_breakdown = model.calculate_transaction_costs(small_buy_order, sample_market_data)

        # Market impact should be zero for commission-only model
        assert cost_breakdown.market_impact == 0

        # Commission should still be charged
        assert cost_breakdown.commission > 0


class TestCostModelFactory:
    """Tests for the transaction cost model factory function."""

    def test_get_commission_model(self):
        """Test factory creates commission model."""
        config = {"model_type": "commission"}
        model = get_transaction_cost_model(config)

        assert isinstance(model, CommissionModel)

    def test_get_almgren_chriss_model(self):
        """Test factory creates Almgren-Chriss model."""
        config = {"model_type": "almgren_chriss"}
        model = get_transaction_cost_model(config)

        assert isinstance(model, AlmgrenChrissModel)

    def test_default_model(self):
        """Test factory returns default model."""
        config = {}
        model = get_transaction_cost_model(config)

        assert isinstance(model, TransactionCostModel)


class TestCostBreakdown:
    """Tests for CostBreakdown dataclass."""

    def test_cost_breakdown_properties(self):
        """Test cost breakdown calculated properties."""
        breakdown = CostBreakdown(
            order_id="test_123",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("1000"),
            execution_price=Decimal("150.00"),
            commission=Decimal("5.00"),
            spread_cost=Decimal("0.50"),
            market_impact=Decimal("2.00"),
            timing_risk=Decimal("1.00"),
            slippage=Decimal("0.50"),
            fees=Decimal("0.25"),
            taxes=Decimal("0.00"),
            total_cost=Decimal("9.25"),
            cost_per_share=Decimal("0.00925"),
            cost_as_bps=0.62,
            participation_rate=0.01,
            impact_model=MarketImpactModel.SQUARE_ROOT,
            execution_algorithm=ExecutionAlgorithm.MARKET,
            expected_duration_seconds=1.0,
        )

        assert breakdown.cost_per_share == Decimal("0.00925")
        assert breakdown.cost_as_bps == 0.62
        assert breakdown.participation_rate == 0.01


class TestOrderSpecification:
    """Tests for OrderSpecification dataclass."""

    def test_order_creation(self):
        """Test creating an order specification."""
        order = OrderSpecification(
            symbol="AAPL",
            side="sell",
            quantity=Decimal("5000"),
            order_type="limit",
            limit_price=Decimal("155.00"),
            time_in_force="DAY",
            execution_algorithm=ExecutionAlgorithm.LIMIT,
            urgency=0.7,
        )

        assert order.symbol == "AAPL"
        assert order.side == "sell"
        assert order.order_type == "limit"
        assert order.limit_price == Decimal("155.00")
        assert order.execution_algorithm == ExecutionAlgorithm.LIMIT
