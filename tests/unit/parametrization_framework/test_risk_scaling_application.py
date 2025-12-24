"""
T8.1: Unit Tests for RiskScalingApplication

Tests cover:
- Risk scaling factor calculation
- Portfolio allocation adjustment
- Rebalancing decisions
- Edge cases and error handling
"""

import pytest
from app.services.risk_scaling_application import (
    RiskScalingApplicator,
)


@pytest.fixture
def applicator():
    """Create RiskScalingApplicator instance."""
    return RiskScalingApplicator()


@pytest.fixture
def sample_allocation():
    """Sample portfolio allocation."""
    return {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}


# =============================================================================
# Test Risk Scaling Factor Calculation
# =============================================================================

class TestRiskScalingCalculation:
    """Test risk scaling factor calculation."""

    @pytest.mark.asyncio
    async def test_normal_volatility_no_scaling(self, applicator):
        """Test that normal volatility produces scale factor of ~1.0."""
        scale_factor = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.15, risk_tolerance=1.0,
            max_scaling=2.0, min_scaling=0.5
        )
        # Should be close to 1.0 when market vol equals base vol
        assert 0.95 < scale_factor < 1.05

    @pytest.mark.asyncio
    async def test_high_volatility_reduces_risk(self, applicator):
        """Test that high market volatility reduces risk (scale < 1.0)."""
        scale_factor = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.25, risk_tolerance=1.0,
            max_scaling=2.0, min_scaling=0.5
        )
        assert scale_factor < 1.0

    @pytest.mark.asyncio
    async def test_low_volatility_increases_risk(self, applicator):
        """Test that low market volatility increases risk (scale > 1.0)."""
        scale_factor = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.10, risk_tolerance=1.0,
            max_scaling=2.0, min_scaling=0.5
        )
        assert scale_factor > 1.0

    @pytest.mark.asyncio
    async def test_risk_tolerance_affects_scaling(self, applicator):
        """Test that risk tolerance multiplies scaling factor."""
        scale_low_risk = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.15, risk_tolerance=0.5,
            max_scaling=2.0, min_scaling=0.5
        )
        scale_high_risk = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.15, risk_tolerance=1.5,
            max_scaling=2.0, min_scaling=0.5
        )
        assert scale_low_risk < scale_high_risk

    @pytest.mark.asyncio
    async def test_scaling_respects_bounds(self, applicator):
        """Test that scaling respects min/max bounds."""
        # Very high volatility should still respect max_scaling
        scale_factor = await applicator._calculate_scale_factor(
            portfolio_vol=0.15, market_vol=0.50, risk_tolerance=1.0,
            max_scaling=2.0, min_scaling=0.5
        )
        assert scale_factor >= 0.5
        assert scale_factor <= 2.0


# =============================================================================
# Test Apply Risk Scaling
# =============================================================================

class TestApplyRiskScaling:
    """Test risk scaling application."""

    @pytest.mark.asyncio
    async def test_apply_scaling_normal_conditions(self, applicator, sample_allocation):
        """Test risk scaling in normal volatility conditions."""
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=0.15,
            market_volatility=0.15,
            risk_tolerance=1.0
        )

        assert result.is_scaled is False  # No scaling in normal conditions
        assert abs(sum(result.adjusted_allocation.values()) - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_apply_scaling_high_volatility(self, applicator, sample_allocation):
        """Test risk scaling reduces allocation in high volatility."""
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=0.15,
            market_volatility=0.30,
            risk_tolerance=1.0
        )

        assert result.is_scaled is True
        assert result.risk_scale_factor < 1.0
        # Scale factor should be less than 1.0 (reduced risk)
        assert result.risk_scale_factor < 1.0

    @pytest.mark.asyncio
    async def test_apply_scaling_low_volatility(self, applicator, sample_allocation):
        """Test risk scaling increases allocation in low volatility."""
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=0.15,
            market_volatility=0.08,
            risk_tolerance=1.0
        )

        assert result.is_scaled is True
        assert result.risk_scale_factor > 1.0
        # Scale factor should be greater than 1.0 (increased risk)
        assert result.risk_scale_factor > 1.0

    @pytest.mark.asyncio
    async def test_apply_scaling_allocation_sums_to_one(self, applicator, sample_allocation):
        """Test that adjusted allocation sums to 1.0."""
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=0.15,
            market_volatility=0.20,
            risk_tolerance=1.5
        )

        total = sum(result.adjusted_allocation.values())
        assert abs(total - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_apply_scaling_preserves_asset_order(self, applicator, sample_allocation):
        """Test that risk scaling preserves relative asset weights."""
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=0.15,
            market_volatility=0.20
        )

        # AAPL and MSFT both had 0.30 weight
        aapl_weight = result.adjusted_allocation["AAPL"]
        msft_weight = result.adjusted_allocation["MSFT"]
        assert abs(aapl_weight - msft_weight) < 0.01


# =============================================================================
# Test Scaling Reason Determination
# =============================================================================

class TestScalingReason:
    """Test scaling reason determination."""

    @pytest.mark.asyncio
    async def test_no_scaling_reason(self, applicator):
        """Test reason when scale factor is ~1.0."""
        reason = await applicator._determine_scaling_reason(
            scale_factor=1.0, portfolio_vol=0.15, market_vol=0.15
        )
        assert "No scaling" in reason

    @pytest.mark.asyncio
    async def test_increase_risk_reason(self, applicator):
        """Test reason when scale factor > 1.0."""
        reason = await applicator._determine_scaling_reason(
            scale_factor=1.5, portfolio_vol=0.15, market_vol=0.10
        )
        assert "Increase risk" in reason

    @pytest.mark.asyncio
    async def test_reduce_risk_reason(self, applicator):
        """Test reason when scale factor < 1.0."""
        reason = await applicator._determine_scaling_reason(
            scale_factor=0.7, portfolio_vol=0.15, market_vol=0.25
        )
        assert "Reduce risk" in reason


# =============================================================================
# Test Position Size Adjustment
# =============================================================================

class TestPositionSizeAdjustment:
    """Test position size adjustment."""

    def test_adjust_position_sizes_no_scaling(self, applicator, sample_allocation):
        """Test position size adjustment with scale factor 1.0."""
        position_sizes = applicator.adjust_position_sizes(
            sample_allocation,
            total_portfolio_value=100000,
            scale_factor=1.0
        )

        # Total should equal portfolio value
        assert abs(sum(position_sizes.values()) - 100000) < 1
        # AAPL should be 30% of 100k
        assert abs(position_sizes["AAPL"] - 30000) < 1

    def test_adjust_position_sizes_scaled_down(self, applicator, sample_allocation):
        """Test position size adjustment with scale down."""
        position_sizes = applicator.adjust_position_sizes(
            sample_allocation,
            total_portfolio_value=100000,
            scale_factor=0.8
        )

        # Total should equal scaled portfolio value
        assert abs(sum(position_sizes.values()) - 80000) < 1

    def test_adjust_position_sizes_scaled_up(self, applicator, sample_allocation):
        """Test position size adjustment with scale up."""
        position_sizes = applicator.adjust_position_sizes(
            sample_allocation,
            total_portfolio_value=100000,
            scale_factor=1.2
        )

        # Total should equal scaled portfolio value
        assert abs(sum(position_sizes.values()) - 120000) < 1


# =============================================================================
# Test Rebalancing Decisions
# =============================================================================

class TestRebalancingDecision:
    """Test rebalancing decision logic."""

    def test_should_not_rebalance_aligned(self, applicator):
        """Test that aligned portfolios don't need rebalancing."""
        current = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}
        target = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}

        should_rebalance = applicator.should_rebalance(current, target)
        assert should_rebalance is False

    def test_should_rebalance_drift_exceeds_threshold(self, applicator):
        """Test that drift exceeding threshold triggers rebalancing."""
        current = {"AAPL": 0.40, "MSFT": 0.25, "GOOGL": 0.20, "AMZN": 0.15}
        target = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}

        should_rebalance = applicator.should_rebalance(current, target, rebalance_threshold=0.05)
        assert should_rebalance is True

    def test_should_not_rebalance_drift_below_threshold(self, applicator):
        """Test that drift below threshold doesn't trigger rebalancing."""
        current = {"AAPL": 0.32, "MSFT": 0.29, "GOOGL": 0.20, "AMZN": 0.19}
        target = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}

        should_rebalance = applicator.should_rebalance(current, target, rebalance_threshold=0.05)
        assert should_rebalance is False

    def test_should_rebalance_custom_threshold(self, applicator):
        """Test rebalancing with custom threshold."""
        current = {"AAPL": 0.32, "MSFT": 0.29, "GOOGL": 0.20, "AMZN": 0.19}
        target = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20}

        # With tight threshold, should rebalance
        should_rebalance = applicator.should_rebalance(current, target, rebalance_threshold=0.01)
        assert should_rebalance is True


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_apply_scaling_with_error_fallback(self, applicator, sample_allocation):
        """Test that errors result in fallback (no scaling)."""
        # Pass None values to trigger error internally
        result = await applicator.apply_risk_scaling(
            sample_allocation,
            portfolio_volatility=None,  # Invalid
            market_volatility=0.15
        )

        assert result.is_scaled is False
        assert result.risk_scale_factor == 1.0
        # Allocation should be unchanged
        assert result.adjusted_allocation == sample_allocation
