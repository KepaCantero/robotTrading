"""
Unit tests for SmartOrderRouter

Tests order routing orchestration, cost estimation, and plan validation.
"""

import pytest
import asyncio
from decimal import Decimal

from app.services.smart_order_routing.smart_order_router import SmartOrderRouter


class TestSmartOrderRouter:
    """Test suite for SmartOrderRouter."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return SmartOrderRouter()

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    def test_initialization(self, router):
        """Test router initializes with all components."""
        assert router is not None
        assert router.market_impact_estimator is not None
        assert router.broker_negotiation is not None
        assert router.order_splitter is not None
        assert router.cost_monitor is not None

    def test_minimum_order_size(self, router):
        """Test minimum order size constant."""
        assert router.MIN_ORDER_SIZE_FOR_ROUTING == Decimal("25000")

    @pytest.mark.asyncio
    async def test_route_order_basic(self, router):
        """Test basic order routing."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            strategy="vwap",
        )

        assert plan is not None
        assert plan.symbol == "AAPL"
        assert plan.total_size == Decimal("50000")
        assert plan.strategy == "vwap"
        assert plan.cost_budget is not None
        assert len(plan.tranches) > 0

    @pytest.mark.asyncio
    async def test_route_order_rejects_small_order(self, router):
        """Test routing rejects orders below minimum size."""
        with pytest.raises(ValueError, match="below minimum"):
            await router.route_order(
                symbol="AAPL",
                total_size=Decimal("10000"),  # Too small
                daily_volume=Decimal("10000000"),
            )

    @pytest.mark.asyncio
    async def test_route_order_requires_daily_volume(self, router):
        """Test routing requires daily volume for impact estimation."""
        with pytest.raises(ValueError, match="daily_volume"):
            await router.route_order(
                symbol="AAPL",
                total_size=Decimal("50000"),
                daily_volume=Decimal("0"),  # Invalid
            )

    @pytest.mark.asyncio
    async def test_route_order_calculates_market_impact(self, router):
        """Test route_order estimates market impact."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Cost budget should be > 0
        assert plan.cost_budget > Decimal("0")

    @pytest.mark.asyncio
    async def test_route_order_negotiates_commission(self, router):
        """Test route_order negotiates commissions."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Cost budget should include commission
        assert plan.cost_budget > Decimal("0")

    @pytest.mark.asyncio
    async def test_route_order_all_strategies(self, router):
        """Test routing supports all splitting strategies."""
        strategies = ["vwap", "twap", "poi", "intraday_phased"]

        for strategy in strategies:
            plan = await router.route_order(
                symbol="AAPL",
                total_size=Decimal("50000"),
                daily_volume=Decimal("10000000"),
                strategy=strategy,
            )

            assert plan.strategy == strategy

    @pytest.mark.asyncio
    async def test_route_order_respects_cost_limit(self, router):
        """Test routing respects maximum cost limit."""
        # Very small max slippage might cause error
        with pytest.raises(ValueError, match="exceeds"):
            await router.route_order(
                symbol="AAPL",
                total_size=Decimal("500000"),  # Large order
                daily_volume=Decimal("1000000"),  # Small volume
                max_accepted_slippage_bps=Decimal("1"),  # Very tight
            )

    @pytest.mark.asyncio
    async def test_route_order_sets_up_monitoring(self, router):
        """Test routing sets up execution monitoring."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Should have execution ID
        assert plan.execution_id is not None

        # Should be monitored
        monitoring = router.cost_monitor.get_monitoring_status(plan.execution_id)
        assert monitoring is not None
        assert monitoring.execution_id == plan.execution_id

    @pytest.mark.asyncio
    async def test_route_order_with_target_price(self, router):
        """Test routing with target VWAP price."""
        target_price = Decimal("150.25")
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            target_vwap=target_price,
        )

        assert plan.estimated_avg_price == target_price

    @pytest.mark.asyncio
    async def test_route_order_with_custom_asset_class(self, router):
        """Test routing with different asset classes."""
        for asset_class in ["equity", "crypto", "forex", "commodity", "bond"]:
            plan = await router.route_order(
                symbol="TEST",
                total_size=Decimal("50000"),
                daily_volume=Decimal("10000000"),
                asset_class=asset_class,
            )

            assert plan is not None

    @pytest.mark.asyncio
    async def test_route_order_with_account_tier(self, router):
        """Test routing with explicit account tier."""
        plan_retail = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            account_tier="retail",
        )

        plan_pro = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            account_tier="pro",
        )

        # Pro tier should have lower cost budget (better commission)
        assert plan_pro.cost_budget < plan_retail.cost_budget

    @pytest.mark.asyncio
    async def test_route_order_with_custom_execution_time(self, router):
        """Test routing with custom execution time window."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            max_execution_time_ms=600_000,  # 10 minutes
        )

        assert plan.max_execution_time_ms == 600_000

    @pytest.mark.asyncio
    async def test_route_order_with_spread(self, router):
        """Test routing accounts for bid-ask spread."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            current_spread_bps=Decimal("2"),
        )

        # Cost should include spread impact
        assert plan.cost_budget > Decimal("0")

    @pytest.mark.asyncio
    async def test_route_order_with_volatility(self, router):
        """Test routing adjusts for market volatility."""
        plan_low_vol = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=10,
        )

        plan_high_vol = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            volatility_percentile=90,
        )

        # High volatility should result in higher cost
        assert plan_high_vol.cost_budget > plan_low_vol.cost_budget

    def test_get_cost_forecast(self, router):
        """Test cost forecasting across execution windows."""
        forecast = router.get_cost_forecast(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        assert forecast is not None
        assert "symbol" in forecast
        assert "commission_cost" in forecast
        assert "window_costs" in forecast

    def test_cost_forecast_multiple_windows(self, router):
        """Test cost forecast shows costs for multiple windows."""
        forecast = router.get_cost_forecast(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Should have multiple time windows
        assert len(forecast["window_costs"]) >= 3

    def test_cost_forecast_shows_tradeoffs(self, router):
        """Test cost forecast shows cost tradeoffs."""
        forecast = router.get_cost_forecast(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        # Faster execution should cost more
        costs = [d["total_cost_bps"] for d in forecast["window_costs"].values()]
        # Generally, first (1 min) > last (60 min)
        if len(costs) >= 2:
            assert costs[0] > costs[-1]

    def test_validate_execution_plan_valid(self, router):
        """Test validating a valid execution plan."""
        # Create a simple plan manually for testing
        from app.services.smart_order_routing.models import ExecutionPlan, OrderTranche

        plan = ExecutionPlan(
            symbol="AAPL",
            total_size=Decimal("50000"),
            tranches=[
                OrderTranche(
                    symbol="AAPL",
                    size=Decimal("50000"),
                    execution_time=router.cost_monitor.executions.get(
                        "dummy", None
                    ) or __import__("datetime").datetime.now(),
                ),
            ],
            strategy="vwap",
        )

        is_valid, message = router.validate_execution_plan(plan)
        assert is_valid is True

    def test_validate_execution_plan_no_tranches(self, router):
        """Test validation fails for plan with no tranches."""
        from app.services.smart_order_routing.models import ExecutionPlan

        plan = ExecutionPlan(
            symbol="AAPL",
            total_size=Decimal("50000"),
            tranches=[],  # Empty
            strategy="vwap",
        )

        is_valid, message = router.validate_execution_plan(plan)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_route_order_large_position(self, router):
        """Test routing large position (€500k)."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("500000"),
            daily_volume=Decimal("50000000"),
        )

        assert len(plan.tranches) >= 5

    @pytest.mark.asyncio
    async def test_route_order_institutional_volume(self, router):
        """Test routing with institutional volume (€1M+)."""
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("1000000"),
            daily_volume=Decimal("100000000"),
        )

        assert plan is not None
        # Institutional tier should give best commission rate

    @pytest.mark.asyncio
    async def test_route_order_creates_unique_execution_ids(self, router):
        """Test each routed order gets unique execution ID."""
        plan1 = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        plan2 = await router.route_order(
            symbol="MSFT",
            total_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
        )

        assert plan1.execution_id != plan2.execution_id

    @pytest.mark.asyncio
    async def test_route_order_comprehensive_scenario(self, router):
        """Test comprehensive routing scenario."""
        # Large order, high volatility, aggressive commission tier
        plan = await router.route_order(
            symbol="AAPL",
            total_size=Decimal("100000"),
            target_vwap=Decimal("150.50"),
            daily_volume=Decimal("20000000"),
            current_spread_bps=Decimal("1.5"),
            volatility_percentile=75,
            max_execution_time_ms=900_000,  # 15 minutes
            max_accepted_slippage_bps=Decimal("50"),
            asset_class="equity",
            account_tier="pro",
            strategy="vwap",
        )

        # Verify complete plan
        assert plan.symbol == "AAPL"
        assert plan.total_size == Decimal("100000")
        assert plan.strategy == "vwap"
        assert len(plan.tranches) > 0
        assert plan.cost_budget > Decimal("0")
        assert plan.max_execution_time_ms == 900_000
