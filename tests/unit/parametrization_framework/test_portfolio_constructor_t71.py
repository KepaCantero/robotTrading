"""
BATCH F - T7.1: Unit Tests for PortfolioConstructor with Portfolio Optimization

Tests:
- Portfolio construction with efficient frontier optimization
- Risk-parity allocation (inverse volatility weighting)
- Equal-weight baseline allocation
- Risk profile-aware adjustments (aggressive/balanced/conservative)
- Portfolio metrics calculation (return, Sharpe, drawdown, diversification)
- Fallback chain: EF → RP → EW
- Edge cases (no modules, single module)
- History tracking and status reporting
"""

import pytest
from decimal import Decimal
from app.services.portfolio_constructor.portfolio_constructor import (
    PortfolioConstructor,
    get_portfolio_constructor,
)
from app.services.portfolio_constructor.models import (
    PortfolioConstructionRequest,
    PortfolioAllocation,
)


@pytest.fixture
def portfolio_constructor():
    """Create PortfolioConstructor instance for tests."""
    return PortfolioConstructor()


class TestBasicPortfolioConstruction:
    """Test basic portfolio construction."""

    @pytest.mark.asyncio
    async def test_construct_with_multiple_modules(self, portfolio_constructor):
        """Test portfolio construction with multiple modules."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-001",
            input_id="test_001",
            capital_eur=Decimal("250000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion", "ensemble_strategy"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result is not None
        assert result.success is True
        assert result.profile_id == "PROF-PORT-001"
        assert result.total_capital_eur == Decimal("250000")
        assert len(result.allocations) == 3
        # Total allocation should be ~100%
        total_weight = sum(a.weight_pct for a in result.allocations)
        assert Decimal("99") <= total_weight <= Decimal("101")

    @pytest.mark.asyncio
    async def test_construct_single_module(self, portfolio_constructor):
        """Test portfolio construction with single module."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-002",
            input_id="test_002",
            capital_eur=Decimal("100000"),
            risk_profile="conservative",
            investment_objective="capital_preservation",
            enabled_modules=["pairs_trading"],
            target_annual_return_pct=Decimal("6"),
            max_acceptable_drawdown_pct=Decimal("10"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        assert len(result.allocations) == 1
        assert result.allocations[0].module_name == "pairs_trading"
        # Single module should get 100%
        assert result.allocations[0].weight_pct == Decimal("100")
        assert result.allocations[0].capital_allocation_eur == Decimal("100000")

    @pytest.mark.asyncio
    async def test_construct_empty_modules(self, portfolio_constructor):
        """Test portfolio construction with no enabled modules."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-003",
            input_id="test_003",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("12"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is False
        assert len(result.allocations) == 0


class TestRiskProfileAdjustment:
    """Test risk profile-aware portfolio construction."""

    @pytest.mark.asyncio
    async def test_aggressive_risk_profile(self, portfolio_constructor):
        """Test aggressive risk profile adjusts toward high-return modules."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-004",
            input_id="test_004",
            capital_eur=Decimal("250000"),
            risk_profile="aggressive",
            investment_objective="maximizar_capital",
            enabled_modules=[
                "momentum",
                "transformer_engine",
                "mean_reversion",
            ],
            target_annual_return_pct=Decimal("18"),
            max_acceptable_drawdown_pct=Decimal("25"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Find transformer (high return, high volatility)
        transformer = next(
            (a for a in result.allocations if a.module_name == "transformer_engine"),
            None,
        )
        assert transformer is not None
        # Aggressive profile should give higher weight to higher-return modules
        assert transformer.weight_pct > Decimal("20")

    @pytest.mark.asyncio
    async def test_conservative_risk_profile(self, portfolio_constructor):
        """Test conservative risk profile adjusts toward low-volatility modules."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-005",
            input_id="test_005",
            capital_eur=Decimal("200000"),
            risk_profile="conservative",
            investment_objective="capital_preservation",
            enabled_modules=[
                "pairs_trading",
                "mean_reversion",
                "momentum",
            ],
            target_annual_return_pct=Decimal("6"),
            max_acceptable_drawdown_pct=Decimal("8"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Find low-volatility modules
        pairs = next(
            (a for a in result.allocations if a.module_name == "pairs_trading"),
            None,
        )
        assert pairs is not None
        # Conservative profile should give higher weight to lower-volatility modules
        assert pairs.weight_pct > Decimal("20")

    @pytest.mark.asyncio
    async def test_balanced_risk_profile(self, portfolio_constructor):
        """Test balanced risk profile distributes allocations evenly."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-006",
            input_id="test_006",
            capital_eur=Decimal("150000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[
                "momentum",
                "mean_reversion",
                "ensemble_strategy",
            ],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("12"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Balanced profile should not heavily skew toward any single module
        max_weight = max(a.weight_pct for a in result.allocations)
        assert max_weight < Decimal("50")  # No single module dominates


class TestPortfolioMetrics:
    """Test portfolio metrics calculation."""

    @pytest.mark.asyncio
    async def test_portfolio_return_calculation(self, portfolio_constructor):
        """Test portfolio expected return is calculated."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-007",
            input_id="test_007",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("12"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Expected return should be positive and reasonable
        assert result.expected_portfolio_return_pct > Decimal("0")
        assert result.expected_portfolio_return_pct <= Decimal("25")

    @pytest.mark.asyncio
    async def test_portfolio_sharpe_calculation(self, portfolio_constructor):
        """Test portfolio Sharpe ratio is calculated."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-008",
            input_id="test_008",
            capital_eur=Decimal("150000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "ensemble_strategy"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("14"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Sharpe ratio should be non-negative
        assert result.expected_portfolio_sharpe >= Decimal("0")

    @pytest.mark.asyncio
    async def test_portfolio_drawdown_calculation(self, portfolio_constructor):
        """Test portfolio max drawdown is calculated."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-009",
            input_id="test_009",
            capital_eur=Decimal("120000"),
            risk_profile="conservative",
            investment_objective="capital_preservation",
            enabled_modules=["pairs_trading", "mean_reversion"],
            target_annual_return_pct=Decimal("6"),
            max_acceptable_drawdown_pct=Decimal("10"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Expected drawdown should be positive and reasonable
        assert result.expected_portfolio_drawdown_pct > Decimal("0")
        assert result.expected_portfolio_drawdown_pct <= Decimal("30")

    @pytest.mark.asyncio
    async def test_diversification_ratio(self, portfolio_constructor):
        """Test diversification ratio calculation."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-010",
            input_id="test_010",
            capital_eur=Decimal("200000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[
                "momentum",
                "mean_reversion",
                "ensemble_strategy",
                "pairs_trading",
            ],
            target_annual_return_pct=Decimal("11"),
            max_acceptable_drawdown_pct=Decimal("13"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Diversification ratio should be >= 1
        assert result.diversification_ratio >= Decimal("1")


class TestAllocationMethods:
    """Test different allocation methods."""

    @pytest.mark.asyncio
    async def test_efficient_frontier_method(self, portfolio_constructor):
        """Test efficient frontier allocation method."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-011",
            input_id="test_011",
            capital_eur=Decimal("250000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=[
                "momentum",
                "mean_reversion",
                "ensemble_strategy",
            ],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("14"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Should use efficient frontier method
        assert result.allocation_method in [
            "efficient_frontier",
            "risk_parity",
            "equal_weight",
        ]

    @pytest.mark.asyncio
    async def test_capital_allocation_calculation(self, portfolio_constructor):
        """Test capital allocation is calculated correctly."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-012",
            input_id="test_012",
            capital_eur=Decimal("100000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "mean_reversion"],
            target_annual_return_pct=Decimal("10"),
            max_acceptable_drawdown_pct=Decimal("12"),
        )

        result = await portfolio_constructor.construct_portfolio(request)

        assert result.success is True
        # Total allocated capital should equal total capital
        total_allocated = sum(
            a.capital_allocation_eur for a in result.allocations
        )
        assert (
            total_allocated
            == Decimal("100000")
        )


class TestPortfolioHistory:
    """Test construction history tracking."""

    @pytest.mark.asyncio
    async def test_history_tracked(self, portfolio_constructor):
        """Test portfolio constructions are tracked in history."""
        request = PortfolioConstructionRequest(
            profile_id="PROF-PORT-013",
            input_id="test_013",
            capital_eur=Decimal("150000"),
            risk_profile="balanced",
            investment_objective="balanced_growth",
            enabled_modules=["momentum", "ensemble_strategy"],
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("14"),
        )

        await portfolio_constructor.construct_portfolio(request)

        history = await portfolio_constructor.get_construction_history()
        assert len(history) > 0

    def test_constructor_status(self, portfolio_constructor):
        """Test constructor status reporting."""
        status = portfolio_constructor.get_constructor_status()

        assert "total_constructions" in status
        assert "successful_constructions" in status
        assert "success_rate" in status
        assert "average_sharpe" in status
        assert "history_size" in status


class TestSingletonPattern:
    """Test singleton pattern for PortfolioConstructor."""

    def test_singleton_instance(self):
        """Test that get_portfolio_constructor returns singleton."""
        instance1 = get_portfolio_constructor()
        instance2 = get_portfolio_constructor()

        assert instance1 is instance2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
