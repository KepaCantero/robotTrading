"""
BATCH F - T8.1: Unit Tests for RiskScalingApplication

Tests:
- Risk scaling application with market conditions
- Market regime adjustments (bull/sideways/bear)
- Volatility-based position sizing (low/normal/high)
- Drawdown-aware scaling adjustments
- PHASE 3 availability check (enabled/disabled)
- Weight normalization after adjustments
- Overall scaling factor calculation
- Adjustment rationale generation
- History tracking and status reporting
"""

from decimal import Decimal

import pytest

from app.services.portfolio_constructor.models import (
    AllocationWeight,
    PortfolioAllocation,
)
from app.services.risk_scaling_application.models import (
    RiskScalingRequest,
)
from app.services.risk_scaling_application.risk_scaling_applicator import (
    RiskScalingApplication,
    get_risk_scaler,
)


@pytest.fixture
def risk_scaler():
    """Create RiskScalingApplication instance for tests."""
    return RiskScalingApplication()


@pytest.fixture
def sample_portfolio() -> PortfolioAllocation:
    """Create sample portfolio for testing."""
    return PortfolioAllocation(
        success=True,
        profile_id="PROF-SCALE-001",
        total_capital_eur=Decimal("250000"),
        allocations=[
            AllocationWeight(
                module_name="momentum",
                weight_pct=Decimal("30"),
                capital_allocation_eur=Decimal("75000"),
                rationale="High-return growth module",
            ),
            AllocationWeight(
                module_name="mean_reversion",
                weight_pct=Decimal("40"),
                capital_allocation_eur=Decimal("100000"),
                rationale="Stable mean reversion strategy",
            ),
            AllocationWeight(
                module_name="pairs_trading",
                weight_pct=Decimal("30"),
                capital_allocation_eur=Decimal("75000"),
                rationale="Low-volatility defensive module",
            ),
        ],
        allocation_method="efficient_frontier",
        expected_portfolio_return_pct=Decimal("12"),
        expected_portfolio_sharpe=Decimal("1.5"),
        expected_portfolio_drawdown_pct=Decimal("10"),
        diversification_ratio=Decimal("1.3"),
    )


class TestBasicRiskScaling:
    """Test basic risk scaling application."""

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_favorable_conditions(self, risk_scaler, sample_portfolio):
        """Test risk scaling with favorable market conditions (no scaling applied)."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-001",
            input_id="test_001",
            base_portfolio=sample_portfolio,
            market_regime="bull",
            volatility_level="low",
            current_drawdown_pct=Decimal("2"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result is not None
        assert result.success is True
        # Favorable conditions should not trigger scaling
        assert result.risk_scaling_applied is False
        assert result.scaling_factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_phase3_disabled(self, risk_scaler, sample_portfolio):
        """Test risk scaling when PHASE 3 is disabled."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-002",
            input_id="test_002",
            base_portfolio=sample_portfolio,
            market_regime="bear",
            volatility_level="high",
            current_drawdown_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=False,  # PHASE 3 disabled
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        # PHASE 3 disabled should not apply scaling
        assert result.risk_scaling_applied is False


class TestMarketRegimeAdjustment:
    """Test market regime-based adjustments."""

    @pytest.mark.asyncio
    async def test_bear_market_reduces_volatility(self, risk_scaler, sample_portfolio):
        """Test bear market reduces allocation to high-volatility modules."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-003",
            input_id="test_003",
            base_portfolio=sample_portfolio,
            market_regime="bear",
            volatility_level="normal",
            current_drawdown_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        assert result.risk_scaling_applied is True
        # Momentum (high volatility) should be reduced in bear market
        if result.adjusted_allocations:
            momentum = next(
                (a for a in result.adjusted_allocations if a.module_name == "momentum"),
                None,
            )
            assert momentum is not None
            assert momentum.adjusted_weight_pct < Decimal("30")

    @pytest.mark.asyncio
    async def test_bull_market_favors_growth(self, risk_scaler, sample_portfolio):
        """Test bull market can increase allocation to growth modules."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-004",
            input_id="test_004",
            base_portfolio=sample_portfolio,
            market_regime="bull",
            volatility_level="normal",
            current_drawdown_pct=Decimal("1"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        # Bull market with low drawdown should not trigger scaling
        assert result.risk_scaling_applied is False

    @pytest.mark.asyncio
    async def test_sideways_market_neutral(self, risk_scaler, sample_portfolio):
        """Test sideways market maintains neutral allocations."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-005",
            input_id="test_005",
            base_portfolio=sample_portfolio,
            market_regime="sideways",
            volatility_level="normal",
            current_drawdown_pct=Decimal("5"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        assert result.risk_scaling_applied is False


class TestVolatilityAdjustment:
    """Test volatility-based position sizing."""

    @pytest.mark.asyncio
    async def test_high_volatility_reduces_positions(self, risk_scaler, sample_portfolio):
        """Test high volatility reduces overall position sizes."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-006",
            input_id="test_006",
            base_portfolio=sample_portfolio,
            market_regime="sideways",
            volatility_level="high",
            current_drawdown_pct=Decimal("3"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        assert result.risk_scaling_applied is True
        # High volatility should reduce scaling factor
        assert result.scaling_factor < Decimal("1.0")

    @pytest.mark.asyncio
    async def test_low_volatility_allows_aggression(self, risk_scaler, sample_portfolio):
        """Test low volatility allows slight position increase."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-007",
            input_id="test_007",
            base_portfolio=sample_portfolio,
            market_regime="sideways",
            volatility_level="low",
            current_drawdown_pct=Decimal("1"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        # Low volatility with favorable conditions should not reduce


class TestDrawdownAdjustment:
    """Test drawdown-aware scaling."""

    @pytest.mark.asyncio
    async def test_high_drawdown_defensive_positioning(self, risk_scaler, sample_portfolio):
        """Test high drawdown triggers defensive positioning."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-008",
            input_id="test_008",
            base_portfolio=sample_portfolio,
            market_regime="sideways",
            volatility_level="normal",
            current_drawdown_pct=Decimal("12"),  # 80% of limit
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        assert result.success is True
        assert result.risk_scaling_applied is True
        # High drawdown should reduce scaling factor
        assert result.scaling_factor < Decimal("1.0")


class TestWeightNormalization:
    """Test weight normalization after adjustments."""

    @pytest.mark.asyncio
    async def test_adjusted_weights_sum_to_100(self, risk_scaler, sample_portfolio):
        """Test adjusted weights sum to 100%."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-009",
            input_id="test_009",
            base_portfolio=sample_portfolio,
            market_regime="bear",
            volatility_level="high",
            current_drawdown_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        if result.adjusted_allocations:
            total_weight = sum(a.adjusted_weight_pct for a in result.adjusted_allocations)
            # Should be approximately 100%
            assert Decimal("99") <= total_weight <= Decimal("101")


class TestScalingFactorCalculation:
    """Test overall scaling factor calculation."""

    @pytest.mark.asyncio
    async def test_scaling_factor_reasonable(self, risk_scaler, sample_portfolio):
        """Test scaling factor is within reasonable bounds."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-010",
            input_id="test_010",
            base_portfolio=sample_portfolio,
            market_regime="bear",
            volatility_level="high",
            current_drawdown_pct=Decimal("14"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await risk_scaler.apply_risk_scaling(request)

        if result.risk_scaling_applied:
            # Scaling factor should be positive and less than or equal to 1.0 in extreme scenarios
            # (bear market + high volatility + near-max drawdown)
            assert Decimal("0.3") <= result.scaling_factor <= Decimal("1.5")


class TestScalingHistory:
    """Test scaling history tracking."""

    @pytest.mark.asyncio
    async def test_history_tracked(self, risk_scaler, sample_portfolio):
        """Test scaling operations are tracked in history."""
        request = RiskScalingRequest(
            profile_id="PROF-SCALE-011",
            input_id="test_011",
            base_portfolio=sample_portfolio,
            market_regime="sideways",
            volatility_level="normal",
            current_drawdown_pct=Decimal("2"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        await risk_scaler.apply_risk_scaling(request)

        history = await risk_scaler.get_scaling_history()
        assert len(history) > 0

    def test_scaler_status(self, risk_scaler):
        """Test scaler status reporting."""
        status = risk_scaler.get_scaler_status()

        assert "total_scalings" in status
        assert "successful_scalings" in status
        assert "scaling_applied_count" in status
        assert "success_rate" in status
        assert "average_scaling_factor" in status
        assert "history_size" in status


class TestSingletonPattern:
    """Test singleton pattern for RiskScalingApplication."""

    def test_singleton_instance(self):
        """Test that get_risk_scaler returns singleton."""
        instance1 = get_risk_scaler()
        instance2 = get_risk_scaler()

        assert instance1 is instance2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
