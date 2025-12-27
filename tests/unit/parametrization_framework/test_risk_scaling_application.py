"""
T8.1: RiskScalingApplication Tests

Tests for conditional risk scaling based on market regime and drawdown.
"""

from decimal import Decimal

import pytest

from app.services.portfolio_constructor import (
    PortfolioConstructionRequest,
    PortfolioConstructor,
)
from app.services.risk_scaling_application import (
    RiskScalingApplication,
    RiskScalingRequest,
    get_risk_scaler,
)


# RISK SCALING APPLICATION INITIALIZATION TESTS
class TestRiskScalingApplicationInitialization:
    def test_scaler_init(self):
        """Test scaler initialization."""
        scaler = RiskScalingApplication()
        assert len(scaler.scaling_history) == 0

    def test_scaler_singleton(self):
        """Test scaler singleton pattern."""
        s1 = get_risk_scaler()
        s2 = get_risk_scaler()
        assert s1 is s2

    def test_scaler_status(self):
        """Test scaler status reporting."""
        scaler = RiskScalingApplication()
        status = scaler.get_scaler_status()

        assert "total_scalings" in status
        assert "successful_scalings" in status
        assert "scaling_applied_count" in status


# BULL MARKET RISK SCALING TESTS
class TestBullMarketRiskScaling:
    @pytest.mark.asyncio
    async def test_bull_market_no_phase3(self):
        """Test no scaling applied in bull market without PHASE 3."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        # Create base portfolio
        profile_req = PortfolioConstructionRequest(
            profile_id="test_bull_no_phase3",
            input_id="user_001",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        # Apply risk scaling
        request = RiskScalingRequest(
            profile_id="test_bull_no_phase3",
            input_id="user_001",
            base_portfolio=base_portfolio,
            market_regime="bull",
            volatility_level="normal",
            current_drawdown_pct=Decimal("5"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=False,
        )

        result = await scaler.apply_risk_scaling(request)

        assert result.success
        assert result.risk_scaling_applied is False
        assert result.scaling_factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_bull_market_with_phase3(self):
        """Test minor scaling in bull market with PHASE 3."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        profile_req = PortfolioConstructionRequest(
            profile_id="test_bull_phase3",
            input_id="user_002",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        request = RiskScalingRequest(
            profile_id="test_bull_phase3",
            input_id="user_002",
            base_portfolio=base_portfolio,
            market_regime="bull",
            volatility_level="normal",
            current_drawdown_pct=Decimal("5"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,  # PHASE 3 available
        )

        result = await scaler.apply_risk_scaling(request)

        # Bull market with normal conditions and PHASE 3: should still not scale
        assert result.success
        assert result.risk_scaling_applied is False


# BEAR MARKET RISK SCALING TESTS
class TestBearMarketRiskScaling:
    @pytest.mark.asyncio
    async def test_bear_market_scales_down(self):
        """Test risk scaling in bear market."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        profile_req = PortfolioConstructionRequest(
            profile_id="test_bear_market",
            input_id="user_003",
            capital_eur=Decimal("100000"),
            risk_profile="aggressive",
            investment_objective="maximizar_capital",
            enabled_modules=["momentum", "transformer_engine", "mean_reversion"],
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        request = RiskScalingRequest(
            profile_id="test_bear_market",
            input_id="user_003",
            base_portfolio=base_portfolio,
            market_regime="bear",
            volatility_level="normal",
            current_drawdown_pct=Decimal("8"),
            max_acceptable_drawdown_pct=Decimal("20"),
            phase3_enabled=True,
        )

        result = await scaler.apply_risk_scaling(request)

        assert result.success
        assert result.risk_scaling_applied is True
        assert result.scaling_factor < Decimal("1.0")  # Reduced in bear market
        # Should favor low-volatility modules
        momentum_adj = next(
            (a for a in result.adjusted_allocations if a.module_name == "momentum"), None
        )
        mean_rev_adj = next(
            (a for a in result.adjusted_allocations if a.module_name == "mean_reversion"), None
        )
        if momentum_adj and mean_rev_adj:
            assert momentum_adj.adjusted_weight_pct < momentum_adj.original_weight_pct


# HIGH VOLATILITY RISK SCALING TESTS
class TestHighVolatilityRiskScaling:
    @pytest.mark.asyncio
    async def test_high_volatility_reduces_positions(self):
        """Test position reduction in high volatility."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        profile_req = PortfolioConstructionRequest(
            profile_id="test_high_vol",
            input_id="user_004",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion", "pairs_trading"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        request = RiskScalingRequest(
            profile_id="test_high_vol",
            input_id="user_004",
            base_portfolio=base_portfolio,
            market_regime="sideways",
            volatility_level="high",  # High volatility
            current_drawdown_pct=Decimal("5"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await scaler.apply_risk_scaling(request)

        assert result.success
        assert result.risk_scaling_applied is True
        # High volatility should significantly reduce scaling factor
        assert result.scaling_factor < Decimal("1.0")
        assert result.scaling_factor == pytest.approx(Decimal("0.75"), abs=Decimal("0.05"))


# HIGH DRAWDOWN RISK SCALING TESTS
class TestHighDrawdownRiskScaling:
    @pytest.mark.asyncio
    async def test_high_drawdown_triggers_scaling(self):
        """Test scaling triggered by high drawdown."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        profile_req = PortfolioConstructionRequest(
            profile_id="test_high_dd",
            input_id="user_005",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        request = RiskScalingRequest(
            profile_id="test_high_dd",
            input_id="user_005",
            base_portfolio=base_portfolio,
            market_regime="sideways",
            volatility_level="normal",
            current_drawdown_pct=Decimal("12"),  # 80% of max
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await scaler.apply_risk_scaling(request)

        assert result.success
        assert result.risk_scaling_applied is True
        # Should have reduced scaling factor due to drawdown
        assert result.scaling_factor < Decimal("1.0")


# SCALING HISTORY TESTS
class TestScalingHistory:
    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test that scaling history is tracked."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        for i in range(3):
            profile_req = PortfolioConstructionRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                capital_eur=Decimal("100000"),
                risk_profile="balanced",
                investment_objective="balanced_growth",
                enabled_modules=["momentum", "mean_reversion"],
                target_annual_return_pct=Decimal("10"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )
            base_portfolio = await constructor.construct_portfolio(profile_req)

            request = RiskScalingRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                base_portfolio=base_portfolio,
                market_regime="sideways",
                volatility_level="normal",
                current_drawdown_pct=Decimal("5"),
                max_acceptable_drawdown_pct=Decimal("15"),
                phase3_enabled=False,
            )
            await scaler.apply_risk_scaling(request)

        history = await scaler.get_scaling_history()
        assert len(history) == 3  # Should have exactly 3 items from this loop

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history retrieval with limit."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        for i in range(5):
            profile_req = PortfolioConstructionRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                capital_eur=Decimal("100000"),
                risk_profile="balanced",
                investment_objective="balanced_growth",
                enabled_modules=["momentum", "mean_reversion"],
                target_annual_return_pct=Decimal("10"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )
            base_portfolio = await constructor.construct_portfolio(profile_req)

            request = RiskScalingRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                base_portfolio=base_portfolio,
                market_regime="sideways",
                volatility_level="normal",
                current_drawdown_pct=Decimal("5"),
                max_acceptable_drawdown_pct=Decimal("15"),
                phase3_enabled=False,
            )
            await scaler.apply_risk_scaling(request)

        history = await scaler.get_scaling_history(limit=2)
        assert len(history) == 2


# ADJUSTMENT RATIONALE TESTS
class TestAdjustmentRationale:
    @pytest.mark.asyncio
    async def test_rationale_contains_reason(self):
        """Test that adjustment rationale explains the decision."""
        scaler = RiskScalingApplication()
        constructor = PortfolioConstructor()

        profile_req = PortfolioConstructionRequest(
            profile_id="test_rationale",
            input_id="user_006",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )
        base_portfolio = await constructor.construct_portfolio(profile_req)

        request = RiskScalingRequest(
            profile_id="test_rationale",
            input_id="user_006",
            base_portfolio=base_portfolio,
            market_regime="bear",
            volatility_level="normal",
            current_drawdown_pct=Decimal("8"),
            max_acceptable_drawdown_pct=Decimal("15"),
            phase3_enabled=True,
        )

        result = await scaler.apply_risk_scaling(request)

        assert result.success
        assert result.adjustment_rationale != ""
        assert (
            "Bear market" in result.adjustment_rationale
            or "scaling factor" in result.adjustment_rationale
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
