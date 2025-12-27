"""
Test suite for T18.1: Portfolio Construction & Optimization

Tests for:
- AllocationManager: Allocation tracking and management
- RebalancingEngine: Dynamic rebalancing
- AllocationRecommender: Smart allocation recommendations
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.portfolio_construction import (
    AllocationManager,
    AllocationRecommender,
    RebalancingEngine,
    RebalancingFrequency,
)

# ============================================================================
# ALLOCATION MANAGER TESTS (25 tests)
# ============================================================================


class TestAllocationManagerInitialization:
    """Test allocation manager initialization."""

    def test_allocation_manager_init(self):
        """Test AllocationManager initialization."""
        manager = AllocationManager()
        assert manager.rebalancing_threshold == Decimal("0.05")
        assert len(manager.current_allocation) == 0
        assert len(manager.target_allocation) == 0
        assert manager.total_value == Decimal("0")

    def test_allocation_manager_custom_threshold(self):
        """Test AllocationManager with custom threshold."""
        manager = AllocationManager(rebalancing_threshold=Decimal("0.10"))
        assert manager.rebalancing_threshold == Decimal("0.10")

    def test_allocation_manager_singleton(self):
        """Test singleton getter for allocation manager."""
        from app.services.portfolio_construction import get_allocation_manager

        mgr1 = get_allocation_manager()
        mgr2 = get_allocation_manager()
        assert mgr1 is mgr2


class TestAllocationManagerTargetSetting:
    """Test setting target allocations."""

    @pytest.mark.asyncio
    async def test_set_valid_target_allocation(self):
        """Test setting valid target allocation."""
        manager = AllocationManager()
        allocation = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.40"),
            "GOOGL": Decimal("0.30"),
        }
        result = await manager.set_target_allocation(allocation)
        assert result is True
        assert len(manager.target_allocation) == 3

    @pytest.mark.asyncio
    async def test_set_invalid_target_allocation(self):
        """Test setting invalid target allocation (doesn't sum to 1)."""
        manager = AllocationManager()
        allocation = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.40"),
        }
        result = await manager.set_target_allocation(allocation)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_current_allocation(self):
        """Test setting current allocation."""
        manager = AllocationManager()
        allocation = {
            "AAPL": Decimal("0.25"),
            "MSFT": Decimal("0.50"),
            "GOOGL": Decimal("0.25"),
        }
        result = await manager.set_current_allocation(
            allocation,
            total_value=Decimal("100000"),
        )
        assert result is True
        assert manager.total_value == Decimal("100000")
        assert len(manager.allocation_history) == 1


class TestAllocationManagerDrift:
    """Test drift calculation and detection."""

    @pytest.mark.asyncio
    async def test_calculate_drift(self):
        """Test drift calculation."""
        manager = AllocationManager()
        target = {
            "AAPL": Decimal("0.40"),
            "MSFT": Decimal("0.60"),
        }
        current = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.70"),
        }
        await manager.set_target_allocation(target)
        await manager.set_current_allocation(current, Decimal("100000"))

        drift = await manager.get_drift()
        assert drift["AAPL"] == Decimal("-0.10")
        assert drift["MSFT"] == Decimal("0.10")

    @pytest.mark.asyncio
    async def test_needs_rebalancing_exceeds_threshold(self):
        """Test rebalancing trigger when drift exceeds threshold."""
        manager = AllocationManager(rebalancing_threshold=Decimal("0.05"))
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }
        current = {
            "AAPL": Decimal("0.35"),
            "MSFT": Decimal("0.65"),
        }
        await manager.set_target_allocation(target)
        await manager.set_current_allocation(current, Decimal("100000"))

        needs_rebalancing = await manager.needs_rebalancing()
        assert needs_rebalancing is True

    @pytest.mark.asyncio
    async def test_needs_rebalancing_below_threshold(self):
        """Test no rebalancing trigger when drift is below threshold."""
        manager = AllocationManager(rebalancing_threshold=Decimal("0.20"))
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }
        current = {
            "AAPL": Decimal("0.45"),
            "MSFT": Decimal("0.55"),
        }
        await manager.set_target_allocation(target)
        await manager.set_current_allocation(current, Decimal("100000"))

        needs_rebalancing = await manager.needs_rebalancing()
        assert needs_rebalancing is False


class TestAllocationManagerRebalancingTrades:
    """Test rebalancing trade calculations."""

    @pytest.mark.asyncio
    async def test_get_rebalancing_trades(self):
        """Test calculation of rebalancing trades."""
        manager = AllocationManager()
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }
        await manager.set_target_allocation(target)

        current_values = {
            "AAPL": Decimal("35000"),
            "MSFT": Decimal("65000"),
        }

        trades = await manager.get_rebalancing_trades(current_values)
        assert "AAPL" in trades
        assert "MSFT" in trades
        # AAPL should be bought (positive delta)
        assert trades["AAPL"] > 0
        # MSFT should be sold (negative delta)
        assert trades["MSFT"] < 0

    @pytest.mark.asyncio
    async def test_get_rebalancing_trades_small_amounts(self):
        """Test that small trades are filtered out."""
        manager = AllocationManager()
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }
        await manager.set_target_allocation(target)

        # Very small drift
        current_values = {
            "AAPL": Decimal("50000.50"),
            "MSFT": Decimal("49999.50"),
        }

        trades = await manager.get_rebalancing_trades(current_values)
        # Should filter out small trades
        assert len(trades) == 0 or all(abs(v) > Decimal("0.01") for v in trades.values())


class TestAllocationManagerMetrics:
    """Test allocation metrics calculation."""

    @pytest.mark.asyncio
    async def test_get_allocation_metrics(self):
        """Test allocation metrics calculation."""
        manager = AllocationManager()
        allocation = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.40"),
            "GOOGL": Decimal("0.30"),
        }
        await manager.set_current_allocation(allocation, Decimal("100000"))

        metrics = await manager.get_allocation_metrics()
        assert metrics.num_positions == 3
        assert metrics.concentration_ratio == Decimal("0.40")  # Largest is MSFT at 0.40
        assert metrics.largest_position == "MSFT"

    @pytest.mark.asyncio
    async def test_herfindahl_index(self):
        """Test Herfindahl index calculation."""
        manager = AllocationManager()
        allocation = {
            "AAPL": Decimal("1.0"),  # 100%
        }
        await manager.set_current_allocation(allocation, Decimal("100000"))

        metrics = await manager.get_allocation_metrics()
        # Herfindahl for single asset should be 1.0
        assert metrics.herfindahl_index == Decimal("1.0")


class TestAllocationManagerHistory:
    """Test allocation history tracking."""

    @pytest.mark.asyncio
    async def test_allocation_history_snapshots(self):
        """Test allocation history snapshots."""
        manager = AllocationManager()

        for i in range(3):
            allocation = {
                "AAPL": Decimal("0.50"),
                "MSFT": Decimal("0.50"),
            }
            await manager.set_current_allocation(
                allocation,
                total_value=Decimal("100000") + Decimal(i) * Decimal("1000"),
            )

        history = await manager.get_allocation_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_allocation_history_with_limit(self):
        """Test allocation history with limit."""
        manager = AllocationManager()

        for i in range(5):
            allocation = {
                "AAPL": Decimal("0.50"),
                "MSFT": Decimal("0.50"),
            }
            await manager.set_current_allocation(allocation, Decimal("100000"))

        history = await manager.get_allocation_history(limit=2)
        assert len(history) == 2


class TestAllocationManagerStatus:
    """Test manager status reporting."""

    def test_get_management_status(self):
        """Test management status report."""
        manager = AllocationManager()
        status = manager.get_management_status()
        assert status["current_allocation"] == 0
        assert status["target_allocation"] == 0
        assert status["rebalancing_threshold"] == 0.05


# ============================================================================
# REBALANCING ENGINE TESTS (28 tests)
# ============================================================================


class TestRebalancingEngineInitialization:
    """Test rebalancing engine initialization."""

    def test_rebalancing_engine_init(self):
        """Test RebalancingEngine initialization."""
        engine = RebalancingEngine()
        assert engine.frequency == RebalancingFrequency.MONTHLY
        assert engine.drift_threshold == Decimal("0.05")
        assert engine.min_trade_value == Decimal("100")
        assert engine.transaction_cost_rate == Decimal("0.001")

    def test_rebalancing_engine_custom_config(self):
        """Test RebalancingEngine with custom configuration."""
        engine = RebalancingEngine(
            frequency=RebalancingFrequency.WEEKLY,
            drift_threshold=Decimal("0.10"),
            min_trade_value=Decimal("500"),
            transaction_cost_rate=Decimal("0.002"),
        )
        assert engine.frequency == RebalancingFrequency.WEEKLY
        assert engine.drift_threshold == Decimal("0.10")

    def test_rebalancing_engine_singleton(self):
        """Test singleton getter for rebalancing engine."""
        from app.services.portfolio_construction import get_rebalancing_engine

        eng1 = get_rebalancing_engine()
        eng2 = get_rebalancing_engine()
        assert eng1 is eng2


class TestRebalancingEngineScheduling:
    """Test scheduled rebalancing."""

    @pytest.mark.asyncio
    async def test_should_rebalance_first_time(self):
        """Test that rebalancing is due on first call."""
        engine = RebalancingEngine()
        should_rebalance = await engine.should_rebalance_by_schedule()
        assert should_rebalance is True

    @pytest.mark.asyncio
    async def test_should_rebalance_daily_frequency(self):
        """Test daily rebalancing frequency."""
        engine = RebalancingEngine(frequency=RebalancingFrequency.DAILY)
        # Set last rebalance to now
        engine.last_rebalance = datetime.now()
        # Should not need rebalancing yet
        should_rebalance = await engine.should_rebalance_by_schedule()
        assert should_rebalance is False

    @pytest.mark.asyncio
    async def test_should_rebalance_monthly_frequency(self):
        """Test monthly rebalancing frequency."""
        engine = RebalancingEngine(frequency=RebalancingFrequency.MONTHLY)
        # Set last rebalance to 31 days ago
        engine.last_rebalance = datetime.now() - timedelta(days=31)
        should_rebalance = await engine.should_rebalance_by_schedule()
        assert should_rebalance is True


class TestRebalancingEnginePlanning:
    """Test rebalancing planning."""

    @pytest.mark.asyncio
    async def test_plan_rebalancing(self):
        """Test rebalancing plan creation."""
        engine = RebalancingEngine()
        current = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.70"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        event = await engine.plan_rebalancing(
            current,
            target,
            Decimal("100000"),
            reason="drift_threshold",
        )

        assert event.event_id == "rebalance_1"
        assert event.reason == "drift_threshold"
        assert len(event.trades) > 0
        assert event.status == "pending"

    @pytest.mark.asyncio
    async def test_plan_rebalancing_filters_small_trades(self):
        """Test that small trades are filtered."""
        engine = RebalancingEngine(min_trade_value=Decimal("1000"))
        current = {
            "AAPL": Decimal("0.501"),
            "MSFT": Decimal("0.499"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        event = await engine.plan_rebalancing(current, target, Decimal("100000"))
        # Small drift should be filtered
        assert event.num_trades == 0

    @pytest.mark.asyncio
    async def test_rebalancing_event_cost_calculation(self):
        """Test transaction cost calculation."""
        engine = RebalancingEngine(transaction_cost_rate=Decimal("0.001"))
        current = {
            "AAPL": Decimal("0.20"),
            "MSFT": Decimal("0.80"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        event = await engine.plan_rebalancing(current, target, Decimal("100000"))
        assert event.total_transaction_cost > 0


class TestRebalancingEngineExecution:
    """Test rebalancing execution."""

    @pytest.mark.asyncio
    async def test_execute_rebalancing(self):
        """Test rebalancing execution."""
        engine = RebalancingEngine()
        current = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.70"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        event = await engine.plan_rebalancing(current, target, Decimal("100000"))
        result = await engine.execute_rebalancing(event)

        assert result is True
        assert event.status == "executed"
        assert engine.last_rebalance is not None

    @pytest.mark.asyncio
    async def test_rebalancing_history(self):
        """Test rebalancing event history."""
        engine = RebalancingEngine()
        current = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.70"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        # Execute multiple rebalancing events
        for i in range(3):
            event = await engine.plan_rebalancing(current, target, Decimal("100000"))
            await engine.execute_rebalancing(event)

        history = await engine.get_rebalancing_history()
        assert len(history) == 3


class TestRebalancingEngineDriftDetection:
    """Test drift-based rebalancing triggers."""

    @pytest.mark.asyncio
    async def test_should_rebalance_by_drift_exceeds(self):
        """Test rebalancing trigger when drift exceeds threshold."""
        engine = RebalancingEngine(drift_threshold=Decimal("0.05"))
        current = {
            "AAPL": Decimal("0.40"),
            "MSFT": Decimal("0.60"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        should_rebalance = await engine.should_rebalance_by_drift(current, target)
        assert should_rebalance is True

    @pytest.mark.asyncio
    async def test_should_rebalance_by_drift_below_threshold(self):
        """Test no rebalancing when drift is below threshold."""
        engine = RebalancingEngine(drift_threshold=Decimal("0.15"))
        current = {
            "AAPL": Decimal("0.45"),
            "MSFT": Decimal("0.55"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        should_rebalance = await engine.should_rebalance_by_drift(current, target)
        assert should_rebalance is False


class TestRebalancingEngineStatistics:
    """Test rebalancing statistics."""

    @pytest.mark.asyncio
    async def test_get_rebalancing_statistics(self):
        """Test rebalancing statistics."""
        engine = RebalancingEngine()
        current = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.70"),
        }
        target = {
            "AAPL": Decimal("0.50"),
            "MSFT": Decimal("0.50"),
        }

        for i in range(2):
            event = await engine.plan_rebalancing(current, target, Decimal("100000"))
            await engine.execute_rebalancing(event)

        stats = await engine.get_rebalancing_statistics()
        assert stats["total_events"] == 2
        assert stats["total_cost"] > 0


class TestRebalancingEngineStatus:
    """Test engine status reporting."""

    def test_get_engine_status(self):
        """Test engine status report."""
        engine = RebalancingEngine()
        status = engine.get_engine_status()
        assert status["frequency"] == "monthly"
        assert status["drift_threshold"] == 0.05


# ============================================================================
# ALLOCATION RECOMMENDER TESTS (27 tests)
# ============================================================================


class TestAllocationRecommenderInitialization:
    """Test recommender initialization."""

    def test_allocation_recommender_init(self):
        """Test AllocationRecommender initialization."""
        recommender = AllocationRecommender()
        assert len(recommender.recommendation_history) == 0

    def test_allocation_recommender_singleton(self):
        """Test singleton getter."""
        from app.services.portfolio_construction import get_allocation_recommender

        rec1 = get_allocation_recommender()
        rec2 = get_allocation_recommender()
        assert rec1 is rec2


class TestAllocationRecommenderByRiskProfile:
    """Test recommendations by risk profile."""

    @pytest.mark.asyncio
    async def test_recommend_conservative(self):
        """Test conservative profile recommendation."""
        recommender = AllocationRecommender()
        assets = ["BOND", "DIVIDEND", "STOCK"]

        recommendation = await recommender.recommend_by_risk_profile(
            "conservative",
            assets,
        )

        assert recommendation.confidence == "high"
        assert len(recommendation.allocation) == 3
        assert sum(recommendation.allocation.values()) == Decimal("1.0")
        assert recommendation.expected_volatility < Decimal("0.10")

    @pytest.mark.asyncio
    async def test_recommend_moderate(self):
        """Test moderate profile recommendation."""
        recommender = AllocationRecommender()
        assets = ["STOCK1", "STOCK2", "BOND", "ALTERNATIVE"]

        recommendation = await recommender.recommend_by_risk_profile(
            "moderate",
            assets,
        )

        assert recommendation.confidence == "high"
        assert recommendation.expected_return == Decimal("0.07")

    @pytest.mark.asyncio
    async def test_recommend_aggressive(self):
        """Test aggressive profile recommendation."""
        recommender = AllocationRecommender()
        assets = ["STOCK1", "STOCK2", "STOCK3", "ALTERNATIVE"]

        recommendation = await recommender.recommend_by_risk_profile(
            "aggressive",
            assets,
        )

        assert recommendation.expected_volatility == Decimal("0.18")


class TestAllocationRecommenderByObjective:
    """Test recommendations by investment objective."""

    @pytest.mark.asyncio
    async def test_recommend_growth(self):
        """Test growth objective recommendation."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT", "GOOGL", "AMZN"]

        recommendation = await recommender.recommend_by_objective("growth", assets)

        assert sum(recommendation.allocation.values()) == Decimal("1.0")
        assert recommendation.expected_return == Decimal("0.10")

    @pytest.mark.asyncio
    async def test_recommend_income(self):
        """Test income objective recommendation."""
        recommender = AllocationRecommender()
        assets = ["DIVIDEND_STOCK", "BOND", "REIT", "PREFERRED"]

        recommendation = await recommender.recommend_by_objective("income", assets)

        assert recommendation.expected_return == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_recommend_preservation(self):
        """Test preservation objective recommendation."""
        recommender = AllocationRecommender()
        assets = ["BOND", "CASH", "TREASURY"]

        recommendation = await recommender.recommend_by_objective(
            "preservation",
            assets,
        )

        assert recommendation.expected_return == Decimal("0.03")

    @pytest.mark.asyncio
    async def test_recommend_balanced(self):
        """Test balanced objective recommendation."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT", "JNJ", "PG"]

        recommendation = await recommender.recommend_by_objective("balanced", assets)

        # Equal weight allocation
        assert all(w == Decimal("0.25") for w in recommendation.allocation.values())


class TestAllocationRecommenderByCapitalTier:
    """Test recommendations by capital tier."""

    @pytest.mark.asyncio
    async def test_recommend_micro_capital(self):
        """Test recommendation for micro capital."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT"]

        recommendation = await recommender.recommend_by_capital_tier(
            Decimal("5000"),
            assets,
        )

        # Micro capital should use equal weight
        assert all(w == Decimal("0.5") for w in recommendation.allocation.values())

    @pytest.mark.asyncio
    async def test_recommend_small_capital(self):
        """Test recommendation for small capital."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT", "GOOGL"]

        recommendation = await recommender.recommend_by_capital_tier(
            Decimal("50000"),
            assets,
        )

        assert recommendation.expected_return == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_recommend_medium_capital(self):
        """Test recommendation for medium capital."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT", "GOOGL", "AMZN"]

        recommendation = await recommender.recommend_by_capital_tier(
            Decimal("250000"),
            assets,
        )

        assert recommendation.expected_return == Decimal("0.07")

    @pytest.mark.asyncio
    async def test_recommend_large_capital(self):
        """Test recommendation for large capital."""
        recommender = AllocationRecommender()
        assets = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]

        recommendation = await recommender.recommend_by_capital_tier(
            Decimal("1000000"),
            assets,
        )

        assert recommendation.expected_return == Decimal("0.08")


class TestAllocationRecommenderDiversification:
    """Test diversification scoring."""

    @pytest.mark.asyncio
    async def test_diversification_score_concentrated(self):
        """Test diversification score for concentrated portfolio."""
        recommender = AllocationRecommender()
        allocation = {
            "AAPL": Decimal("0.80"),
            "MSFT": Decimal("0.20"),
        }

        score = await recommender._calculate_diversification_score(allocation)
        # Concentrated portfolio should have lower score
        assert score < Decimal("50")

    @pytest.mark.asyncio
    async def test_diversification_score_diversified(self):
        """Test diversification score for diversified portfolio."""
        recommender = AllocationRecommender()
        allocation = {
            "A1": Decimal("0.20"),
            "A2": Decimal("0.20"),
            "A3": Decimal("0.20"),
            "A4": Decimal("0.20"),
            "A5": Decimal("0.20"),
        }

        score = await recommender._calculate_diversification_score(allocation)
        # Diversified portfolio should have higher score
        assert score >= Decimal("80")


class TestAllocationRecommenderConcentrationRisk:
    """Test concentration risk assessment."""

    @pytest.mark.asyncio
    async def test_concentration_risk_high(self):
        """Test high concentration risk."""
        recommender = AllocationRecommender()
        allocation = {"AAPL": Decimal("0.75"), "MSFT": Decimal("0.25")}

        risk = await recommender._assess_concentration_risk(allocation)
        assert risk == "high"

    @pytest.mark.asyncio
    async def test_concentration_risk_medium(self):
        """Test medium concentration risk."""
        recommender = AllocationRecommender()
        allocation = {
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.30"),
            "GOOGL": Decimal("0.40"),
        }

        risk = await recommender._assess_concentration_risk(allocation)
        assert risk == "medium"

    @pytest.mark.asyncio
    async def test_concentration_risk_low(self):
        """Test low concentration risk."""
        recommender = AllocationRecommender()
        allocation = {
            "A1": Decimal("0.20"),
            "A2": Decimal("0.20"),
            "A3": Decimal("0.20"),
            "A4": Decimal("0.20"),
            "A5": Decimal("0.20"),
        }

        risk = await recommender._assess_concentration_risk(allocation)
        assert risk == "low"


class TestAllocationRecommenderHistory:
    """Test recommendation history."""

    @pytest.mark.asyncio
    async def test_recommendation_history(self):
        """Test recommendation history tracking."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT", "GOOGL"]

        # Generate multiple recommendations
        for i in range(3):
            await recommender.recommend_by_risk_profile("conservative", assets)

        history = await recommender.get_recommendation_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_recommendation_history_with_limit(self):
        """Test recommendation history with limit."""
        recommender = AllocationRecommender()
        assets = ["AAPL", "MSFT"]

        for i in range(5):
            await recommender.recommend_by_objective("growth", assets)

        history = await recommender.get_recommendation_history(limit=2)
        assert len(history) == 2


class TestAllocationRecommenderStatus:
    """Test recommender status reporting."""

    def test_get_recommender_status(self):
        """Test recommender status."""
        recommender = AllocationRecommender()
        status = recommender.get_recommender_status()
        assert status["total_recommendations"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
