"""
Comprehensive Tests for Execution Model (FASE 5.2)

This test suite covers:
- TransactionCostCalculator
- SlippageModel
- MarketImpactModel (Almgren-Chriss)
- OrderFillSimulator
- RealisticExecutionModel

Total: 60+ tests
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.execution import (
    CostConfig,
    ExecutionConfig,
    ImpactConfig,
    MarketImpactModel,
    OrderFillSimulator,
    RealisticExecutionModel,
    SlippageConfig,
    SlippageModel,
    TransactionCostCalculator,
)
from app.backtesting.execution.models import (
    FillReason,
    MarketSnapshot,
    Order,
    OrderSide,
    OrderType,
    TimeOfDay,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def cost_config() -> CostConfig:
    """Default cost configuration."""
    return CostConfig(
        commission_per_share=Decimal("0.005"),
        min_commission=Decimal("1.0"),
        use_sec_fee=True,
        use_finra_taf=True,
        use_exchange_fees=True,
    )


@pytest.fixture
def slippage_config() -> SlippageConfig:
    """Default slippage configuration."""
    return SlippageConfig(
        base_slippage_bps=Decimal("5"),
        vol_multiplier=Decimal("2"),
        spread_impact=True,
        time_of_day_impact=True,
    )


@pytest.fixture
def impact_config() -> ImpactConfig:
    """Default market impact configuration."""
    return ImpactConfig(
        temporary_coef=Decimal("0.1"),
        permanent_coef=Decimal("0.05"),
        max_impact_bps=Decimal("100"),
    )


@pytest.fixture
def execution_config(
    cost_config: CostConfig,
    slippage_config: SlippageConfig,
    impact_config: ImpactConfig,
) -> ExecutionConfig:
    """Default execution configuration."""
    return ExecutionConfig(
        cost_config=cost_config,
        slippage_config=slippage_config,
        impact_config=impact_config,
        max_participation_rate=Decimal("0.10"),
        allow_partial_fills=True,
    )


@pytest.fixture
def sample_order() -> Order:
    """Sample buy order."""
    return Order(
        order_id="TEST001",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1000,
        created_at=datetime(2024, 1, 15, 10, 30),
    )


@pytest.fixture
def sample_sell_order() -> Order:
    """Sample sell order."""
    return Order(
        order_id="TEST002",
        symbol="AAPL",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=1000,
        created_at=datetime(2024, 1, 15, 10, 30),
    )


@pytest.fixture
def liquid_market_snapshot() -> MarketSnapshot:
    """Liquid market snapshot (large cap)."""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 15, 10, 30),
        symbol="AAPL",
        bid=Decimal("149.98"),
        ask=Decimal("150.02"),
        last_price=Decimal("150.00"),
        open_price=Decimal("149.50"),
        high_price=Decimal("150.50"),
        low_price=Decimal("149.40"),
        close_price=Decimal("150.00"),
        bid_size=10000,
        ask_size=10000,
        volume=5000000,
        average_daily_volume=Decimal("50000000"),  # 50M shares
        historical_volatility_20d=Decimal("0.20"),  # 20% annual vol
        vix=Decimal("15"),
        is_market_open=True,
    )


@pytest.fixture
def illiquid_market_snapshot() -> MarketSnapshot:
    """Illiquid market snapshot (small cap)."""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 15, 10, 30),
        symbol="SMALL",
        bid=Decimal("9.98"),
        ask=Decimal("10.05"),
        last_price=Decimal("10.00"),
        volume=50000,
        average_daily_volume=Decimal("100000"),  # 100K shares
        historical_volatility_20d=Decimal("0.35"),  # 35% annual vol
        vix=Decimal("25"),
        is_market_open=True,
    )


@pytest.fixture
def high_volatility_snapshot() -> MarketSnapshot:
    """High volatility market snapshot."""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 15, 10, 30),
        symbol="VOLAT",
        bid=Decimal("49.90"),
        ask=Decimal("50.15"),
        last_price=Decimal("50.00"),
        volume=1000000,
        average_daily_volume=Decimal("10000000"),  # 10M shares
        historical_volatility_20d=Decimal("0.50"),  # 50% annual vol
        vix=Decimal("35"),  # High VIX
        is_market_open=True,
    )


# ============================================================================
# TRANSACTION COST CALCULATOR TESTS
# ============================================================================


class TestTransactionCostCalculator:
    """Tests for TransactionCostCalculator."""

    def test_initialization(self, cost_config: CostConfig):
        """Test calculator initialization."""
        calculator = TransactionCostCalculator(cost_config)
        assert calculator.config == cost_config

    def test_calculate_commission_buy(self, cost_config: CostConfig):
        """Test commission calculation for buy order."""
        calculator = TransactionCostCalculator(cost_config)
        commission = calculator.calculate_commission(shares=1000, price=Decimal("150.00"))

        # 1000 shares * $0.005/share = $5.00
        expected = Decimal("5.00")
        assert commission == expected

    def test_calculate_commission_sell(self, cost_config: CostConfig):
        """Test commission calculation for sell order."""
        calculator = TransactionCostCalculator(cost_config)
        commission = calculator.calculate_commission(shares=500, price=Decimal("100.00"))

        # 500 shares * $0.005/share = $2.50
        expected = Decimal("2.50")
        assert commission == expected

    def test_calculate_commission_minimum(self, cost_config: CostConfig):
        """Test minimum commission is applied."""
        calculator = TransactionCostCalculator(cost_config)
        commission = calculator.calculate_commission(shares=10, price=Decimal("10.00"))

        # 10 shares * $0.005 = $0.05, but min is $1.00
        assert commission >= cost_config.min_commission
        assert commission == Decimal("1.00")

    def test_calculate_sec_fee_calculation(self, cost_config: CostConfig):
        """Test SEC fee calculation."""
        calculator = TransactionCostCalculator(cost_config)
        sec_fee = calculator.calculate_sec_fee(shares=1000, price=Decimal("150.00"))

        # $150,000 * $0.0000078 = $1.17
        assert sec_fee > Decimal("0")
        assert sec_fee <= Decimal("5.95")  # Cap at $5.95

    def test_sec_fee_only_applied_to_sells(self, cost_config: CostConfig):
        """Test that SEC fee is only applied to sells in calculate_cost."""
        calculator = TransactionCostCalculator(cost_config)

        # Buy should have no SEC fee
        buy_cost = calculator.calculate_cost(
            symbol="AAPL",
            side="buy",
            shares=1000,
            price=Decimal("150.00"),
        )
        assert buy_cost.sec_fee == Decimal("0")

        # Sell should have SEC fee
        sell_cost = calculator.calculate_cost(
            symbol="AAPL",
            side="sell",
            shares=1000,
            price=Decimal("150.00"),
        )
        assert sell_cost.sec_fee > Decimal("0")

    def test_calculate_sec_fee_cap(self, cost_config: CostConfig):
        """Test SEC fee cap at $5.95."""
        calculator = TransactionCostCalculator(cost_config)
        # Large sell order
        sec_fee = calculator.calculate_sec_fee(shares=100000, price=Decimal("1000.00"))

        # Should be capped at $5.95
        assert sec_fee == Decimal("5.95")

    def test_calculate_finra_taf(self, cost_config: CostConfig):
        """Test FINRA TAF calculation."""
        calculator = TransactionCostCalculator(cost_config)
        taf = calculator.calculate_finra_taf(shares=1000)

        # 1000 shares * $0.000145 = $0.145
        expected = Decimal("0.15")  # Rounded to 2 decimals
        assert taf == expected

    def test_calculate_exchange_fee(self, cost_config: CostConfig):
        """Test exchange fee calculation."""
        calculator = TransactionCostCalculator(cost_config)
        exchange_fee = calculator.calculate_exchange_fee(shares=1000)

        # 1000 shares * $0.003 = $3.00
        expected = Decimal("3.00")
        assert exchange_fee == expected

    def test_calculate_total_cost_buy(self, cost_config: CostConfig):
        """Test total cost calculation for buy."""
        calculator = TransactionCostCalculator(cost_config)
        cost = calculator.calculate_cost(
            symbol="AAPL",
            side="buy",
            shares=1000,
            price=Decimal("150.00"),
        )

        # Should include commission, FINRA TAF, exchange fee
        # No SEC fee for buys
        assert cost.commission > Decimal("0")
        assert cost.sec_fee == Decimal("0")
        assert cost.finra_taf > Decimal("0")
        assert cost.exchange_fee > Decimal("0")
        assert cost.total_cost == (
            cost.commission + cost.finra_taf + cost.exchange_fee + cost.platform_fee
        )

    def test_calculate_total_cost_sell(self, cost_config: CostConfig):
        """Test total cost calculation for sell."""
        calculator = TransactionCostCalculator(cost_config)
        cost = calculator.calculate_cost(
            symbol="AAPL",
            side="sell",
            shares=1000,
            price=Decimal("150.00"),
        )

        # Should include all fees including SEC fee
        assert cost.commission > Decimal("0")
        assert cost.sec_fee > Decimal("0")
        assert cost.finra_taf > Decimal("0")
        assert cost.exchange_fee > Decimal("0")
        assert cost.total_cost == (
            cost.commission + cost.sec_fee + cost.finra_taf + cost.exchange_fee + cost.platform_fee
        )

    def test_invalid_shares(self, cost_config: CostConfig):
        """Test error handling for invalid shares."""
        calculator = TransactionCostCalculator(cost_config)

        with pytest.raises(ValueError):
            calculator.calculate_commission(shares=0, price=Decimal("100"))

        with pytest.raises(ValueError):
            calculator.calculate_commission(shares=-100, price=Decimal("100"))

    def test_invalid_price(self, cost_config: CostConfig):
        """Test error handling for invalid price."""
        calculator = TransactionCostCalculator(cost_config)

        with pytest.raises(ValueError):
            calculator.calculate_commission(shares=100, price=Decimal("0"))

        with pytest.raises(ValueError):
            calculator.calculate_commission(shares=100, price=Decimal("-100"))

    def test_invalid_side(self, cost_config: CostConfig):
        """Test error handling for invalid side."""
        calculator = TransactionCostCalculator(cost_config)

        with pytest.raises(ValueError):
            calculator.calculate_cost(
                symbol="AAPL",
                side="invalid",
                shares=1000,
                price=Decimal("150"),
            )


# ============================================================================
# SLIPPAGE MODEL TESTS
# ============================================================================


class TestSlippageModel:
    """Tests for SlippageModel."""

    def test_initialization(self, slippage_config: SlippageConfig):
        """Test slippage model initialization."""
        model = SlippageModel(slippage_config)
        assert model.config == slippage_config

    def test_classify_large_cap(self, slippage_config: SlippageConfig):
        """Test market cap classification for large cap."""
        model = SlippageModel(slippage_config)

        # $1B+ daily volume = large cap
        category = model.classify_market_cap(Decimal("1000000000"))
        assert category.name == "LARGE_CAP"

    def test_classify_mid_cap(self, slippage_config: SlippageConfig):
        """Test market cap classification for mid cap."""
        model = SlippageModel(slippage_config)

        # $100M-$1B daily volume = mid cap
        category = model.classify_market_cap(Decimal("500000000"))
        assert category.name == "MID_CAP"

    def test_classify_small_cap(self, slippage_config: SlippageConfig):
        """Test market cap classification for small cap."""
        model = SlippageModel(slippage_config)

        # $10M-$100M daily volume = small cap
        category = model.classify_market_cap(Decimal("50000000"))
        assert category.name == "SMALL_CAP"

    def test_base_slippage_large_cap(self, slippage_config: SlippageConfig):
        """Test base slippage for large cap stocks."""
        model = SlippageModel(slippage_config)

        # Use large daily dollar volume (>$1B)
        # Assuming $150 stock, need at least ~6.7M shares
        base_slippage = model.calculate_base_slippage(
            adv=Decimal("100000000"),  # 100M shares * $150 = $15B daily
        )

        # Large caps should have low slippage (2-5 bps)
        assert Decimal("2") <= base_slippage <= Decimal("10")

    def test_base_slippage_small_cap(self, slippage_config: SlippageConfig):
        """Test base slippage for small cap stocks."""
        model = SlippageModel(slippage_config)

        base_slippage = model.calculate_base_slippage(
            adv=Decimal("5000000"),  # 5M shares
        )

        # Small caps should have higher slippage (10-25 bps)
        assert Decimal("10") <= base_slippage

    def test_adv_impact_small_order(self, slippage_config: SlippageConfig):
        """Test ADV impact for small order."""
        model = SlippageModel(slippage_config)

        # $150K order vs $50M daily = 0.3% of ADV
        impact = model.calculate_adv_impact(
            order_value=Decimal("150000"),
            adv=Decimal("75000000"),  # $50M shares * $150
        )

        # Small order should have minimal ADV impact
        assert impact < Decimal("1")  # < 1 bps

    def test_adv_impact_large_order(self, slippage_config: SlippageConfig):
        """Test ADV impact for large order."""
        model = SlippageModel(slippage_config)

        # $7.5M order vs $50M daily = 10% of ADV
        impact = model.calculate_adv_impact(
            order_value=Decimal("7500000"),
            adv=Decimal("75000000"),
        )

        # Large order should have significant ADV impact
        assert impact > Decimal("0")

    def test_volatility_impact_low(self, slippage_config: SlippageConfig):
        """Test volatility impact for low volatility."""
        model = SlippageModel(slippage_config)

        multiplier = model.calculate_volatility_impact(
            volatility=Decimal("0.15"),  # 15% vol
            vix=Decimal("15"),
        )

        # Low vol should have multiplier close to 1.0
        assert multiplier == Decimal("1.0")

    def test_volatility_impact_high(self, slippage_config: SlippageConfig):
        """Test volatility impact for high volatility."""
        model = SlippageModel(slippage_config)

        multiplier = model.calculate_volatility_impact(
            volatility=Decimal("0.35"),  # 35% vol
            vix=Decimal("35"),  # High VIX
        )

        # High vol should have 2x multiplier
        assert multiplier == Decimal("2.0")

    def test_volatility_impact_extreme(self, slippage_config: SlippageConfig):
        """Test volatility impact for extreme volatility."""
        model = SlippageModel(slippage_config)

        multiplier = model.calculate_volatility_impact(
            volatility=Decimal("0.55"),  # 55% vol
            vix=Decimal("55"),  # Extreme VIX
        )

        # Extreme vol should have 3x multiplier
        assert multiplier == Decimal("3.0")

    def test_time_of_day_impact_open(self, slippage_config: SlippageConfig):
        """Test time-of-day impact at open."""
        model = SlippageModel(slippage_config)

        multiplier = model.calculate_time_of_day_impact(TimeOfDay.OPEN)

        # Open should have 1.5x multiplier
        assert multiplier == Decimal("1.5")

    def test_time_of_day_impact_lunch(self, slippage_config: SlippageConfig):
        """Test time-of-day impact at lunch."""
        model = SlippageModel(slippage_config)

        multiplier = model.calculate_time_of_day_impact(TimeOfDay.LUNCH)

        # Lunch should have 0.8x multiplier (best time)
        assert multiplier == Decimal("0.8")

    def test_spread_impact(self, slippage_config: SlippageConfig):
        """Test spread impact calculation."""
        model = SlippageModel(slippage_config)

        spread_bps = model.calculate_spread_impact(
            bid=Decimal("149.98"),
            ask=Decimal("150.02"),
            current_price=Decimal("150.00"),
        )

        # Spread is $0.04, half is $0.02
        # $0.02 / $150 = 0.013% = 1.3 bps
        assert spread_bps > Decimal("0")
        assert spread_bps < Decimal("5")

    def test_estimate_slippage_buy_liquid(
        self,
        slippage_config: SlippageConfig,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test slippage estimation for liquid stock buy."""
        model = SlippageModel(slippage_config)

        estimate = model.estimate_slippage(
            symbol="AAPL",
            side="buy",
            shares=1000,
            current_price=Decimal("150.00"),
            bid=Decimal("149.98"),
            ask=Decimal("150.02"),
            adv=Decimal("50000000"),
            volatility=Decimal("0.20"),
            vix=Decimal("15"),
            timestamp=liquid_market_snapshot.timestamp,
        )

        # Liquid stock should have low slippage
        assert estimate.basis_points < Decimal("20")  # < 20 bps
        assert estimate.estimated_fill_price > Decimal("150.00")  # Buy pays more
        assert estimate.fill_probability > 0.9  # High fill probability

    def test_estimate_slippage_sell_liquid(
        self,
        slippage_config: SlippageConfig,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test slippage estimation for liquid stock sell."""
        model = SlippageModel(slippage_config)

        estimate = model.estimate_slippage(
            symbol="AAPL",
            side="sell",
            shares=1000,
            current_price=Decimal("150.00"),
            bid=Decimal("149.98"),
            ask=Decimal("150.02"),
            adv=Decimal("50000000"),
            volatility=Decimal("0.20"),
            vix=Decimal("15"),
        )

        # Liquid stock should have low slippage
        assert estimate.basis_points < Decimal("20")  # < 20 bps
        assert estimate.estimated_fill_price < Decimal("150.00")  # Sell receives less
        assert estimate.fill_probability > 0.9  # High fill probability

    def test_estimate_slippage_illiquid(
        self,
        slippage_config: SlippageConfig,
        illiquid_market_snapshot: MarketSnapshot,
    ):
        """Test slippage estimation for illiquid stock."""
        model = SlippageModel(slippage_config)

        estimate = model.estimate_slippage(
            symbol="SMALL",
            side="buy",
            shares=1000,
            current_price=Decimal("10.00"),
            bid=Decimal("9.98"),
            ask=Decimal("10.05"),
            adv=Decimal("100000"),  # Low ADV
            volatility=Decimal("0.35"),
            vix=Decimal("25"),
        )

        # Illiquid stock should have higher slippage
        assert estimate.basis_points > Decimal("10")  # Higher slippage
        assert estimate.fill_probability < 1.0  # Lower fill probability

    def test_estimate_slippage_high_volatility(
        self,
        slippage_config: SlippageConfig,
        high_volatility_snapshot: MarketSnapshot,
    ):
        """Test slippage estimation in high volatility."""
        model = SlippageModel(slippage_config)

        estimate = model.estimate_slippage(
            symbol="VOLAT",
            side="buy",
            shares=1000,
            current_price=Decimal("50.00"),
            bid=Decimal("49.90"),
            ask=Decimal("50.15"),
            adv=Decimal("10000000"),
            volatility=Decimal("0.50"),
            vix=Decimal("35"),  # High VIX
        )

        # High volatility should increase slippage
        assert estimate.volatility_impact >= Decimal("2.0")  # At least 2x

    def test_invalid_shares_slippage(self, slippage_config: SlippageConfig):
        """Test error handling for invalid shares."""
        model = SlippageModel(slippage_config)

        with pytest.raises(ValueError):
            model.estimate_slippage(
                symbol="AAPL",
                side="buy",
                shares=0,
                current_price=Decimal("150"),
                bid=Decimal("149"),
                ask=Decimal("151"),
                adv=Decimal("1000000"),
            )

    def test_invalid_side_slippage(self, slippage_config: SlippageConfig):
        """Test error handling for invalid side."""
        model = SlippageModel(slippage_config)

        with pytest.raises(ValueError):
            model.estimate_slippage(
                symbol="AAPL",
                side="invalid",
                shares=1000,
                current_price=Decimal("150"),
                bid=Decimal("149"),
                ask=Decimal("151"),
                adv=Decimal("1000000"),
            )


# ============================================================================
# MARKET IMPACT MODEL TESTS
# ============================================================================


class TestMarketImpactModel:
    """Tests for MarketImpactModel (Almgren-Chriss)."""

    def test_initialization(self, impact_config: ImpactConfig):
        """Test market impact model initialization."""
        model = MarketImpactModel(impact_config)
        assert model.config == impact_config

    def test_permanent_impact_small_order(self, impact_config: ImpactConfig):
        """Test permanent impact for small order."""
        model = MarketImpactModel(impact_config)

        impact_bps = model.calculate_permanent_impact(
            order_size=Decimal("150000"),  # $150K
            adv=Decimal("75000000"),  # $75M daily
            side="buy",
        )

        # Small order (0.2% ADV) should have minimal permanent impact
        assert impact_bps <= Decimal("1")  # <= 1 bps

    def test_permanent_impact_large_order(self, impact_config: ImpactConfig):
        """Test permanent impact for large order."""
        model = MarketImpactModel(impact_config)

        impact_bps = model.calculate_permanent_impact(
            order_size=Decimal("7500000"),  # $7.5M
            adv=Decimal("75000000"),  # $75M daily
            side="buy",
        )

        # Large order (10% ADV) should have significant permanent impact
        assert impact_bps > Decimal("0")
        # 10% * 0.05 coef * 10000 = 50 bps
        assert impact_bps >= Decimal("40")  # Approximately

    def test_temporary_impact_low_volatility(self, impact_config: ImpactConfig):
        """Test temporary impact with low volatility."""
        model = MarketImpactModel(impact_config)

        impact_bps = model.calculate_temporary_impact(
            order_size=Decimal("150000"),
            adv=Decimal("75000000"),
            volatility=Decimal("0.15"),  # 15% vol
            side="buy",
        )

        # Low vol should have minimal temporary impact
        assert impact_bps >= Decimal("0")

    def test_temporary_impact_high_volatility(self, impact_config: ImpactConfig):
        """Test temporary impact with high volatility."""
        model = MarketImpactModel(impact_config)

        impact_bps = model.calculate_temporary_impact(
            order_size=Decimal("150000"),
            adv=Decimal("75000000"),
            volatility=Decimal("0.50"),  # 50% vol
            side="buy",
        )

        # High vol should increase temporary impact
        # We just verify it's positive
        assert impact_bps >= Decimal("0")

    def test_total_impact_buy(self, impact_config: ImpactConfig):
        """Test total impact for buy order."""
        model = MarketImpactModel(impact_config)

        impact = model.calculate_impact(
            order_size=Decimal("150000"),
            adv=Decimal("75000000"),
            volatility=Decimal("0.20"),
            side="buy",
            base_price=Decimal("150.00"),
        )

        # Buy should increase price
        assert impact.estimated_price > Decimal("150.00")
        assert impact.permanent_impact_bps >= Decimal("0")
        assert impact.temporary_impact_bps >= Decimal("0")
        assert impact.total_impact_bps == (
            impact.permanent_impact_bps + impact.temporary_impact_bps
        )

    def test_total_impact_sell(self, impact_config: ImpactConfig):
        """Test total impact for sell order."""
        model = MarketImpactModel(impact_config)

        impact = model.calculate_impact(
            order_size=Decimal("150000"),
            adv=Decimal("75000000"),
            volatility=Decimal("0.20"),
            side="sell",
            base_price=Decimal("150.00"),
        )

        # Sell should decrease price
        assert impact.estimated_price < Decimal("150.00")

    def test_impact_max_limit(self, impact_config: ImpactConfig):
        """Test that impact is capped at maximum."""
        model = MarketImpactModel(impact_config)

        # Very large order
        impact = model.calculate_impact(
            order_size=Decimal("50000000"),  # $50M - huge order
            adv=Decimal("75000000"),
            volatility=Decimal("0.50"),
            side="buy",
            base_price=Decimal("150.00"),
        )

        # Should be capped at max_impact_bps
        assert impact.total_impact_bps <= impact_config.max_impact_bps

    def test_invalid_order_size(self, impact_config: ImpactConfig):
        """Test error handling for invalid order size."""
        model = MarketImpactModel(impact_config)

        with pytest.raises(ValueError):
            model.calculate_permanent_impact(
                order_size=Decimal("0"),
                adv=Decimal("1000000"),
                side="buy",
            )

    def test_invalid_adv(self, impact_config: ImpactConfig):
        """Test error handling for invalid ADV."""
        model = MarketImpactModel(impact_config)

        with pytest.raises(ValueError):
            model.calculate_permanent_impact(
                order_size=Decimal("100000"),
                adv=Decimal("0"),
                side="buy",
            )

    def test_get_participation_rate_limit(self, impact_config: ImpactConfig):
        """Test calculation of participation rate limit."""
        model = MarketImpactModel(impact_config)

        limit = model.get_participation_rate_limit(
            max_impact_bps=Decimal("50"),  # 50 bps max impact
            volatility=Decimal("0.20"),
        )

        # Should return a reasonable participation rate
        assert Decimal("0") < limit <= Decimal("0.20")  # Max 20%


# ============================================================================
# ORDER FILL SIMULATOR TESTS
# ============================================================================


class TestOrderFillSimulator:
    """Tests for OrderFillSimulator."""

    @pytest.fixture
    def simulator(self, execution_config: ExecutionConfig) -> OrderFillSimulator:
        """Create order fill simulator."""
        return OrderFillSimulator(config=execution_config.to_simulator_config())

    def test_simulate_fill_liquid_stock(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test fill simulation for liquid stock."""

        result = asyncio.run(simulator.simulate_fill(sample_order, liquid_market_snapshot))

        assert result.filled is True
        assert result.filled_shares > 0
        assert result.fill_price > Decimal("0")
        assert result.commission > Decimal("0")
        assert result.total_cost > Decimal("0")
        assert result.fill_reason == FillReason.FULL_FILL

    def test_simulate_fill_illiquid_stock(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        illiquid_market_snapshot: MarketSnapshot,
    ):
        """Test fill simulation for illiquid stock."""

        result = asyncio.run(simulator.simulate_fill(sample_order, illiquid_market_snapshot))

        # Illiquid stock may partially fill or reject
        assert result.fill_reason in (
            FillReason.FULL_FILL,
            FillReason.PARTIAL_FILL,
            FillReason.EXCEEDS_ADV,
        )

    def test_simulate_fill_market_closed(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test fill simulation when market is closed."""

        # Create closed market snapshot
        from dataclasses import replace

        closed_snapshot = replace(liquid_market_snapshot, is_market_open=False)

        result = asyncio.run(simulator.simulate_fill(sample_order, closed_snapshot))

        assert result.filled is False
        assert result.fill_reason == FillReason.MARKET_CLOSED

    def test_simulate_fill_trading_halt(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test fill simulation during trading halt."""

        # Create halted market snapshot
        from dataclasses import replace

        halted_snapshot = replace(liquid_market_snapshot, is_trading_halt=True)

        result = asyncio.run(simulator.simulate_fill(sample_order, halted_snapshot))

        assert result.filled is False
        assert result.fill_reason == FillReason.MARKET_CLOSED

    def test_cost_breakdown(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test detailed cost breakdown."""
        breakdown = simulator.get_cost_breakdown(sample_order, liquid_market_snapshot)

        assert "commission" in breakdown
        assert "sec_fee" in breakdown
        assert "finra_taf" in breakdown
        assert "exchange_fee" in breakdown
        assert "slippage_cost" in breakdown
        assert "market_impact_cost" in breakdown
        assert "total_cost" in breakdown
        assert "cost_as_bps" in breakdown

        # Verify costs are positive
        for key, value in breakdown.items():
            if key != "cost_as_bps":  # Can be zero
                assert value >= Decimal("0")

    def test_estimate_fill_probability(
        self,
        simulator: OrderFillSimulator,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test fill probability estimation."""
        prob = simulator.estimate_fill_probability(sample_order, liquid_market_snapshot)

        assert 0 <= prob <= 1

        # Liquid stock with reasonable order size should have high probability
        assert prob > 0.5


# ============================================================================
# REALISTIC EXECUTION MODEL TESTS
# ============================================================================


class TestRealisticExecutionModel:
    """Tests for RealisticExecutionModel."""

    def test_initialization(self, execution_config: ExecutionConfig):
        """Test execution model initialization."""
        model = RealisticExecutionModel(execution_config)

        assert model.config == execution_config
        assert model.cost_calculator is not None
        assert model.slippage_model is not None
        assert model.impact_model is not None
        assert model.fill_simulator is not None

    def test_execute_order_liquid(
        self,
        execution_config: ExecutionConfig,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test order execution for liquid stock."""

        model = RealisticExecutionModel(execution_config)
        result = asyncio.run(model.execute_order(sample_order, liquid_market_snapshot))

        assert result.is_fully_filled is True
        assert result.total_filled_shares == sample_order.quantity
        assert result.avg_fill_price > Decimal("0")
        assert result.total_cost > Decimal("0")
        assert len(result.warnings) == 0  # No warnings for liquid orders

    def test_execute_order_illiquid(
        self,
        execution_config: ExecutionConfig,
        sample_order: Order,
        illiquid_market_snapshot: MarketSnapshot,
    ):
        """Test order execution for illiquid stock."""

        model = RealisticExecutionModel(execution_config)
        result = asyncio.run(model.execute_order(sample_order, illiquid_market_snapshot))

        # May fully fill, partially fill, or reject
        assert result.is_fully_filled in (True, False)

        if not result.is_fully_filled:
            # Should have warnings about liquidity
            assert len(result.warnings) > 0 or result.is_rejected

    def test_execute_sell_order(
        self,
        execution_config: ExecutionConfig,
        sample_sell_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test sell order execution."""

        model = RealisticExecutionModel(execution_config)
        result = asyncio.run(model.execute_order(sample_sell_order, liquid_market_snapshot))

        assert result.total_filled_shares > 0

        # SEC fee should be included for sells
        assert result.cost_breakdown.sec_fee >= Decimal("0")

    def test_estimate_execution_cost(
        self,
        execution_config: ExecutionConfig,
    ):
        """Test quick cost estimation."""
        model = RealisticExecutionModel(execution_config)

        estimate = model.estimate_execution_cost(
            symbol="AAPL",
            side="buy",
            shares=1000,
            price=Decimal("150.00"),
            adv=Decimal("50000000"),
            volatility=Decimal("0.20"),
        )

        assert "commission" in estimate
        assert "regulatory_fees" in estimate
        assert "slippage_cost" in estimate
        assert "market_impact_cost" in estimate
        assert "total_cost" in estimate
        assert "total_cost_bps" in estimate

        # Total cost should be positive
        assert estimate["total_cost"] > Decimal("0")

    def test_validate_order_feasibility(
        self,
        execution_config: ExecutionConfig,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test order feasibility validation."""
        model = RealisticExecutionModel(execution_config)

        is_feasible, warnings = model.validate_order_feasibility(
            sample_order, liquid_market_snapshot
        )

        # Liquid order should be feasible
        assert is_feasible is True

    def test_get_execution_summary(
        self,
        execution_config: ExecutionConfig,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test execution summary tracking."""

        model = RealisticExecutionModel(execution_config)

        # Execute a few orders
        asyncio.run(model.execute_order(sample_order, liquid_market_snapshot))
        asyncio.run(model.execute_order(sample_order, liquid_market_snapshot))

        summary = model.get_execution_summary()

        assert summary.total_orders == 2
        assert summary.filled_orders > 0
        assert summary.total_shares_requested > 0
        assert summary.total_shares_filled > 0

    def test_reset_summary(
        self,
        execution_config: ExecutionConfig,
        sample_order: Order,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test summary reset."""

        model = RealisticExecutionModel(execution_config)

        # Execute an order
        asyncio.run(model.execute_order(sample_order, liquid_market_snapshot))

        # Reset
        model.reset_summary()

        summary = model.get_execution_summary()
        assert summary.total_orders == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestExecutionModelIntegration:
    """Integration tests for the complete execution model."""

    def test_full_execution_cycle(
        self,
        execution_config: ExecutionConfig,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test complete execution cycle from order to result."""

        model = RealisticExecutionModel(execution_config)

        # Create buy order
        buy_order = Order(
            order_id="INT001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000,
        )

        # Execute buy
        buy_result = asyncio.run(model.execute_order(buy_order, liquid_market_snapshot))

        assert buy_result.is_fully_filled
        assert buy_result.total_filled_shares == 1000

        # Create sell order (to close position)
        sell_order = Order(
            order_id="INT002",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1000,
        )

        # Execute sell
        sell_result = asyncio.run(model.execute_order(sell_order, liquid_market_snapshot))

        assert sell_result.is_fully_filled

        # Check round-trip cost
        round_trip_cost = buy_result.total_cost + sell_result.total_cost
        round_trip_value = buy_result.total_fill_value + sell_result.total_fill_value
        round_trip_bps = (round_trip_cost / round_trip_value) * Decimal("10000")

        # Round-trip should be reasonable (typically 10-30 bps for liquid stocks)
        assert Decimal("5") <= round_trip_bps <= Decimal("50")

    def test_cost_comparison_liquid_vs_illiquid(
        self,
        execution_config: ExecutionConfig,
        liquid_market_snapshot: MarketSnapshot,
        illiquid_market_snapshot: MarketSnapshot,
    ):
        """Test that illiquid stocks have higher costs."""

        model = RealisticExecutionModel(execution_config)

        # Same order, different market conditions
        order = Order(
            order_id="COST001",
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000,
        )

        liquid_result = asyncio.run(model.execute_order(order, liquid_market_snapshot))
        illiquid_result = asyncio.run(model.execute_order(order, illiquid_market_snapshot))

        # Illiquid should have higher cost as % of value
        if illiquid_result.is_fully_filled:
            liquid_cost_bps = (
                liquid_result.total_cost / liquid_result.total_fill_value * Decimal("10000")
            )
            illiquid_cost_bps = (
                illiquid_result.total_cost / illiquid_result.total_fill_value * Decimal("10000")
            )

            assert illiquid_cost_bps >= liquid_cost_bps

    def test_batch_execution(
        self,
        execution_config: ExecutionConfig,
        liquid_market_snapshot: MarketSnapshot,
    ):
        """Test executing multiple orders in batch."""

        model = RealisticExecutionModel(execution_config)

        orders = [
            Order(
                order_id=f"BATCH{i:03d}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100 * (i + 1),  # Different sizes
            )
            for i in range(5)
        ]

        snapshots = {"AAPL": liquid_market_snapshot}

        results = asyncio.run(model.execute_orders_batch(orders, snapshots))

        assert len(results) == len(orders)

        # All should be filled (liquid market)
        for result in results:
            assert result.is_fully_filled


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
