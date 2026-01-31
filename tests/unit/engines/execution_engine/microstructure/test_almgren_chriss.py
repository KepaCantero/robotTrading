"""
Unit tests for Almgren-Chriss Market Impact Model.
"""

import pytest
import pandas as pd
from decimal import Decimal

from app.engines.execution_engine.microstructure.almgren_chriss_model import (
    AlmgrenChrissModel,
    MarketImpactEstimate,
    OptimalExecutionSchedule,
    get_almgren_chriss_model,
)


@pytest.fixture
def impact_model():
    """Get Almgren-Chriss model instance."""
    return get_almgren_chriss_model(asset_class="equity")


class TestAlmgrenChrissModel:
    """Test AlmgrenChrissModel class."""

    def test_estimate_impact_basic(self, impact_model):
        """Test basic market impact estimation."""
        estimate = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
            execution_time_seconds=3600,
            price=Decimal("150"),
        )

        assert isinstance(estimate, MarketImpactEstimate)
        assert estimate.symbol == "AAPL"
        assert estimate.total_impact_bps > 0

    def test_permanent_vs_temporary_impact(self, impact_model):
        """Test permanent vs temporary impact decomposition."""
        estimate = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
        )

        # Both components should be positive
        assert estimate.permanent_impact_bps > 0
        assert estimate.temporary_impact_bps > 0
        # Permanent should be larger (usually)
        assert estimate.permanent_impact_bps >= estimate.temporary_impact_bps

    def test_participation_rate_impact(self, impact_model):
        """Test that higher participation rate = higher impact."""
        small_order = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("1000"),
            adv=Decimal("1000000"),
            volatility=0.02,
        )

        large_order = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("100000"),
            adv=Decimal("1000000"),
            volatility=0.02,
        )

        # Larger order should have higher impact
        assert large_order.total_impact_bps > small_order.total_impact_bps

    def test_volatility_impact(self, impact_model):
        """Test that higher volatility = higher impact."""
        low_vol = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.01,
        )

        high_vol = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.05,
        )

        # Higher volatility should have higher impact
        assert high_vol.total_impact_bps > low_vol.total_impact_bps

    def test_execution_time_impact(self, impact_model):
        """Test that longer execution time = lower temporary impact."""
        fast = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
            execution_time_seconds=300,  # 5 minutes
        )

        slow = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
            execution_time_seconds=3600,  # 1 hour
        )

        # Slower execution should have lower temporary impact
        assert slow.temporary_impact_bps < fast.temporary_impact_bps

    def test_cost_calculation(self, impact_model):
        """Test USD cost calculation."""
        estimate = impact_model.estimate_impact(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
            price=Decimal("150"),
        )

        # Cost should be positive
        assert estimate.total_cost_usd > 0

        # Cost should be approximately: size * price * impact
        expected_cost = float(
            estimate.order_size * Decimal("150") * estimate.total_impact_bps / Decimal("10000")
        )
        assert abs(float(estimate.total_cost_usd) - expected_cost) < 1.0


class TestAlmgrenChrissSchedules:
    """Test optimal execution schedule calculation."""

    def test_calculate_schedule(self, impact_model):
        """Test optimal execution schedule."""
        schedule = impact_model.calculate_optimal_schedule(
            symbol="AAPL",
            total_quantity=Decimal("10000"),
            time_horizon_seconds=3600,  # 1 hour
            adv=Decimal("1000000"),
            volatility=0.02,
            price=Decimal("150"),
        )

        assert isinstance(schedule, OptimalExecutionSchedule)
        assert schedule.symbol == "AAPL"
        assert schedule.n_tranches > 0
        assert len(schedule.schedule) == schedule.n_tranches

    def test_equal_sized_tranches(self, impact_model):
        """Test that tranches are roughly equal-sized."""
        schedule = impact_model.calculate_optimal_schedule(
            symbol="AAPL",
            total_quantity=Decimal("10000"),
            time_horizon_seconds=3600,
            adv=Decimal("1000000"),
            volatility=0.02,
            price=Decimal("150"),
            n_tranches=4,
        )

        sizes = [size for _, size in schedule.schedule]
        # All sizes should be similar
        avg_size = sum(sizes) / len(sizes)
        for size in sizes:
            assert abs(float(size - avg_size)) < 1.0

    def test_strategy_comparison(self, impact_model):
        """Test comparison of execution strategies."""
        comparison = impact_model.compare_execution_strategies(
            symbol="AAPL",
            order_size=Decimal("10000"),
            adv=Decimal("1000000"),
            volatility=0.02,
            price=Decimal("150"),
        )

        assert "urgent" in comparison
        assert "normal" in comparison
        assert "patient" in comparison

        # Urgent should have highest cost
        assert comparison["urgent"].total_cost_usd > comparison["patient"].total_cost_usd


class TestAlmgrenChrissAssetClasses:
    """Test different asset classes."""

    def test_equity_parameters(self):
        """Test equity asset class parameters."""
        model = get_almgren_chriss_model(asset_class="equity")
        assert model.gamma > 0
        assert model.eta > 0

    def test_crypto_parameters(self):
        """Test crypto asset class parameters."""
        model = get_almgren_chriss_model(asset_class="crypto")
        # Crypto should have higher impact parameters
        equity_model = get_almgren_chriss_model(asset_class="equity")
        assert model.gamma >= equity_model.gamma


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
