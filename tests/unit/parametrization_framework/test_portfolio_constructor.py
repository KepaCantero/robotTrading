"""
T7.1: PortfolioConstructor Tests

Tests for portfolio construction and optimization across trading modules.
"""

import pytest
from decimal import Decimal
from app.services.portfolio_constructor import (
    PortfolioConstructor,
    get_portfolio_constructor,
    PortfolioConstructionRequest,
)


# PORTFOLIO CONSTRUCTOR INITIALIZATION TESTS
class TestPortfolioConstructorInitialization:
    def test_constructor_init(self):
        """Test constructor initialization."""
        constructor = PortfolioConstructor()
        assert len(constructor.construction_history) == 0

    def test_constructor_singleton(self):
        """Test constructor singleton pattern."""
        c1 = get_portfolio_constructor()
        c2 = get_portfolio_constructor()
        assert c1 is c2

    def test_constructor_status(self):
        """Test constructor status reporting."""
        constructor = PortfolioConstructor()
        status = constructor.get_constructor_status()

        assert "total_constructions" in status
        assert "successful_constructions" in status
        assert "average_sharpe" in status


# EFFICIENT FRONTIER PORTFOLIO TESTS
class TestEfficientFrontierPortfolio:
    @pytest.mark.asyncio
    async def test_construct_efficient_frontier(self):
        """Test efficient frontier portfolio construction."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_efficient",
            input_id="user_001",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion", "machine_learning_basic"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert result.allocation_method == "efficient_frontier"
        assert len(result.allocations) == 3
        assert sum(a.weight_pct for a in result.allocations) == pytest.approx(Decimal("100"), abs=Decimal("0.01"))

    @pytest.mark.asyncio
    async def test_efficient_frontier_aggressive_profile(self):
        """Test efficient frontier with aggressive risk profile."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_eff_aggressive",
            input_id="user_002",
            capital_eur=Decimal("50000"),
            risk_profile="aggressive",
            investment_objective="maximizar_capital",
            enabled_modules=[
                "momentum",
                "machine_learning_basic",
                "transformer_engine",
                "deep_learning_engine",
            ],
            target_annual_return_pct=Decimal("20"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        # Aggressive should favor higher-return, higher-volatility modules
        high_return_weight = sum(
            a.weight_pct for a in result.allocations
            if a.module_name in ["transformer_engine", "deep_learning_engine"]
        )
        assert high_return_weight > Decimal("10")  # Should have meaningful allocation

    @pytest.mark.asyncio
    async def test_efficient_frontier_conservative_profile(self):
        """Test efficient frontier with conservative risk profile."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_eff_conservative",
            input_id="user_003",
            capital_eur=Decimal("100000"),
            risk_profile="conservative",
            investment_objective="capital_preservation",
            enabled_modules=["mean_reversion", "pairs_trading", "ensemble_strategy"],
            target_annual_return_pct=Decimal("6"),
            max_acceptable_drawdown_pct=Decimal("8"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        # Conservative should favor lower-volatility modules
        low_vol_weight = sum(
            a.weight_pct for a in result.allocations
            if a.module_name in ["pairs_trading", "mean_reversion"]
        )
        assert low_vol_weight > Decimal("30")


# RISK PARITY PORTFOLIO TESTS
class TestRiskParityPortfolio:
    @pytest.mark.asyncio
    async def test_construct_risk_parity(self):
        """Test risk-parity portfolio construction."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_risk_parity",
            input_id="user_004",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        # Should use efficient frontier or risk parity (either is valid)
        assert result.success
        assert len(result.allocations) == 2
        assert sum(a.weight_pct for a in result.allocations) == pytest.approx(Decimal("100"), abs=Decimal("0.01"))


# EQUAL WEIGHT PORTFOLIO TESTS
class TestEqualWeightPortfolio:
    @pytest.mark.asyncio
    async def test_construct_equal_weight(self):
        """Test equal-weight portfolio construction."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_equal_weight",
            input_id="user_005",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion", "pairs_trading"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert len(result.allocations) == 3
        # All weights should be positive and sum to 100%
        total_weight = sum(a.weight_pct for a in result.allocations)
        assert total_weight == pytest.approx(Decimal("100"), abs=Decimal("0.1"))

    @pytest.mark.asyncio
    async def test_equal_weight_two_modules(self):
        """Test portfolio with two modules."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_equal_two",
            input_id="user_006",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert len(result.allocations) == 2
        # Weights should sum to 100%
        total_weight = sum(a.weight_pct for a in result.allocations)
        assert total_weight == pytest.approx(Decimal("100"), abs=Decimal("0.1"))
        # Total capital allocated should equal input capital
        total_capital = sum(a.capital_allocation_eur for a in result.allocations)
        assert total_capital == pytest.approx(Decimal("100000"), abs=Decimal("1"))


# CAPITAL ALLOCATION TESTS
class TestCapitalAllocation:
    @pytest.mark.asyncio
    async def test_capital_properly_allocated(self):
        """Test that total capital is properly allocated."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_capital_alloc",
            input_id="user_007",
            capital_eur=Decimal("250000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion", "machine_learning_basic"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        total_allocated = sum(a.capital_allocation_eur for a in result.allocations)
        assert total_allocated == pytest.approx(request.capital_eur, abs=Decimal("1"))

    @pytest.mark.asyncio
    async def test_large_capital_allocation(self):
        """Test allocation with large capital amount."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_large_capital",
            input_id="user_008",
            capital_eur=Decimal("1000000"),
            risk_profile="aggressive",
            investment_objective="maximizar_capital",
            enabled_modules=["momentum", "machine_learning_basic", "transformer_engine"],
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        total_allocated = sum(a.capital_allocation_eur for a in result.allocations)
        assert total_allocated == pytest.approx(Decimal("1000000"), abs=Decimal("10"))


# PORTFOLIO METRICS TESTS
class TestPortfolioMetrics:
    @pytest.mark.asyncio
    async def test_portfolio_metrics_calculated(self):
        """Test that portfolio metrics are properly calculated."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_metrics",
            input_id="user_009",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert result.expected_portfolio_return_pct > Decimal("0")
        assert result.expected_portfolio_sharpe >= Decimal("0")
        assert result.expected_portfolio_drawdown_pct > Decimal("0")
        assert result.diversification_ratio >= Decimal("1")  # Should be >= 1 for diversified portfolios

    @pytest.mark.asyncio
    async def test_aggressive_portfolio_higher_return(self):
        """Test that aggressive portfolios have higher expected returns."""
        constructor = PortfolioConstructor()
        request_agg = PortfolioConstructionRequest(
            profile_id="test_agg_return",
            input_id="user_010",
            capital_eur=Decimal("100000"),
            risk_profile="aggressive",
            investment_objective="maximizar_capital",
            enabled_modules=["transformer_engine", "deep_learning_engine", "reinforcement_learning"],
            target_annual_return_pct=Decimal("20"),
            max_acceptable_drawdown_pct=Decimal("25"),
        )

        request_cons = PortfolioConstructionRequest(
            profile_id="test_cons_return",
            input_id="user_011",
            capital_eur=Decimal("100000"),
            risk_profile="conservative",
            investment_objective="capital_preservation",
            enabled_modules=["pairs_trading", "mean_reversion"],
            target_annual_return_pct=Decimal("6"),
            max_acceptable_drawdown_pct=Decimal("8"),
        )

        result_agg = await constructor.construct_portfolio(request_agg)
        result_cons = await constructor.construct_portfolio(request_cons)

        assert result_agg.success
        assert result_cons.success
        # Aggressive should have higher expected return
        assert result_agg.expected_portfolio_return_pct > result_cons.expected_portfolio_return_pct


# ALLOCATION RATIONALE TESTS
class TestAllocationRationale:
    @pytest.mark.asyncio
    async def test_allocation_has_rationale(self):
        """Test that each allocation has a rationale."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_rationale",
            input_id="user_012",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        for allocation in result.allocations:
            assert allocation.rationale != ""
            assert allocation.rationale is not None


# SINGLE MODULE PORTFOLIO TESTS
class TestSingleModulePortfolio:
    @pytest.mark.asyncio
    async def test_single_module_allocation(self):
        """Test portfolio with single module (fallback to 100%)."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_single_module",
            input_id="user_013",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert len(result.allocations) == 1
        assert result.allocations[0].weight_pct == Decimal("100")
        assert result.allocations[0].capital_allocation_eur == Decimal("100000")


# NO MODULES EDGE CASE TEST
class TestNoModulesEdgeCase:
    @pytest.mark.asyncio
    async def test_no_modules_enabled(self):
        """Test behavior when no modules are enabled."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_no_modules",
            input_id="user_014",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        # Should fail gracefully
        assert result.success is False


# CONSTRUCTION HISTORY TESTS
class TestConstructionHistory:
    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test that construction history is tracked."""
        constructor = PortfolioConstructor()

        for i in range(3):
            request = PortfolioConstructionRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                capital_eur=Decimal("100000"),
                risk_profile="balanced",
                investment_objective="balanced_growth",
                enabled_modules=["momentum", "mean_reversion"],
                target_annual_return_pct=Decimal("10"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )
            await constructor.construct_portfolio(request)

        history = await constructor.get_construction_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history retrieval with limit."""
        constructor = PortfolioConstructor()

        for i in range(5):
            request = PortfolioConstructionRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                capital_eur=Decimal("100000"),
                risk_profile="balanced",
                investment_objective="balanced_growth",
                enabled_modules=["momentum", "mean_reversion"],
                target_annual_return_pct=Decimal("10"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )
            await constructor.construct_portfolio(request)

        history = await constructor.get_construction_history(limit=2)
        assert len(history) == 2


# DIVERSIFICATION RATIO TESTS
class TestDiversificationRatio:
    @pytest.mark.asyncio
    async def test_diversification_ratio_calculated(self):
        """Test that diversification ratio is properly calculated."""
        constructor = PortfolioConstructor()
        request = PortfolioConstructionRequest(
            profile_id="test_diversification",
            input_id="user_015",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[
                "momentum",
                "mean_reversion",
                "pairs_trading",
                "ensemble_strategy",
            ],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await constructor.construct_portfolio(request)

        assert result.success
        assert result.diversification_ratio > Decimal("0")
        # More modules should generally have better diversification
        assert result.diversification_ratio > Decimal("1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
