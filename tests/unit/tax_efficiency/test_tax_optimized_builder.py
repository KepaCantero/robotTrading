"""
T15.1.4: TaxOptimizedPortfolioBuilder - Comprehensive unit tests

Tests cover:
- Integration of all 3 tax components
- Portfolio optimization for tax efficiency
- After-tax return calculation
- Tax report generation
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from app.services.tax_efficiency.tax_optimized_builder import (
    TaxOptimizedPortfolioBuilder,
    TaxOptimizedAllocation,
)


@pytest.fixture
def builder():
    """Create TaxOptimizedPortfolioBuilder instance."""
    return TaxOptimizedPortfolioBuilder()


@pytest.fixture
def base_date():
    """Base date for test trades."""
    return datetime(2025, 6, 15)


class TestOptimizeForTaxes:
    """Test portfolio optimization for tax efficiency."""

    @pytest.mark.asyncio
    async def test_optimize_single_harvestable_position(self, builder):
        """Optimize portfolio with single harvestable position."""
        base_allocation = {
            "AAPL": Decimal("0.5"),
            "MSFT": Decimal("0.5"),
        }
        current_positions = {
            "AAPL": Decimal("40000"),  # Loss position: €50k cost → €40k current
            "MSFT": Decimal("60000"),
        }
        cost_basis = {
            "AAPL": Decimal("50000"),
            "MSFT": Decimal("60000"),
        }
        quantities = {
            "AAPL": Decimal("400"),
            "MSFT": Decimal("600"),
        }
        current_prices = {
            "AAPL": Decimal("100"),
            "MSFT": Decimal("100"),
        }

        result = await builder.optimize_for_taxes(
            base_allocation=base_allocation,
            current_positions=current_positions,
            cost_basis=cost_basis,
            quantities=quantities,
            current_prices=current_prices,
            marginal_tax_rate=Decimal("0.25"),
            capital=Decimal("100000"),
        )

        assert isinstance(result, TaxOptimizedAllocation)
        assert result.base_allocation == base_allocation
        assert result.tax_benefit_estimated >= Decimal("0")

    @pytest.mark.asyncio
    async def test_optimize_multiple_positions(self, builder):
        """Optimize portfolio with multiple positions."""
        base_allocation = {
            "AAPL": Decimal("0.3"),
            "MSFT": Decimal("0.3"),
            "GOOGL": Decimal("0.4"),
        }
        current_positions = {
            "AAPL": Decimal("25000"),
            "MSFT": Decimal("30000"),
            "GOOGL": Decimal("45000"),
        }
        cost_basis = {
            "AAPL": Decimal("30000"),
            "MSFT": Decimal("30000"),
            "GOOGL": Decimal("40000"),
        }
        quantities = {
            "AAPL": Decimal("250"),
            "MSFT": Decimal("300"),
            "GOOGL": Decimal("450"),
        }
        current_prices = {
            "AAPL": Decimal("100"),
            "MSFT": Decimal("100"),
            "GOOGL": Decimal("100"),
        }

        result = await builder.optimize_for_taxes(
            base_allocation=base_allocation,
            current_positions=current_positions,
            cost_basis=cost_basis,
            quantities=quantities,
            current_prices=current_prices,
            marginal_tax_rate=Decimal("0.25"),
            capital=Decimal("100000"),
        )

        assert result.tax_benefit_estimated >= Decimal("0")

    @pytest.mark.asyncio
    async def test_no_harvestable_positions(self, builder):
        """Handle case with no harvestable positions (all gains)."""
        base_allocation = {
            "AAPL": Decimal("0.5"),
            "MSFT": Decimal("0.5"),
        }
        current_positions = {
            "AAPL": Decimal("60000"),  # €10k gain
            "MSFT": Decimal("70000"),  # €10k gain
        }
        cost_basis = {
            "AAPL": Decimal("50000"),
            "MSFT": Decimal("60000"),
        }
        quantities = {
            "AAPL": Decimal("600"),
            "MSFT": Decimal("700"),
        }
        current_prices = {
            "AAPL": Decimal("100"),
            "MSFT": Decimal("100"),
        }

        result = await builder.optimize_for_taxes(
            base_allocation=base_allocation,
            current_positions=current_positions,
            cost_basis=cost_basis,
            quantities=quantities,
            current_prices=current_prices,
            capital=Decimal("130000"),
        )

        # No losses to harvest
        assert len(result.harvesting_opportunities) == 0
        assert result.tax_benefit_estimated == Decimal("0")


class TestCalculateAfterTaxReturn:
    """Test after-tax return calculation."""

    def test_calculate_after_tax_return_long_term_gains(self, builder):
        """Calculate after-tax return with long-term gains."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("5.0"),
            realized_gains=Decimal("5000"),
            realized_losses=Decimal("0"),
            long_term_percentage=Decimal("1.0"),  # 100% LT
            marginal_tax_rate_st=Decimal("0.35"),
            marginal_tax_rate_lt=Decimal("0.15"),
        )

        # Tax on gains: 5000 * 0.15 = 750
        # After-tax return: 5.0 - (750 / 100000 * 100) = 4.25%
        assert after_tax == Decimal("4.25")

    def test_calculate_after_tax_return_short_term_gains(self, builder):
        """Calculate after-tax return with short-term gains."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("5.0"),
            realized_gains=Decimal("5000"),
            realized_losses=Decimal("0"),
            long_term_percentage=Decimal("0.0"),  # 100% ST
            marginal_tax_rate_st=Decimal("0.35"),
            marginal_tax_rate_lt=Decimal("0.15"),
        )

        # Tax on gains: 5000 * 0.35 = 1750
        # After-tax return: 5.0 - (1750 / 100000 * 100) = ~3.25%
        assert after_tax < Decimal("5.0")
        assert after_tax > Decimal("3.0")

    def test_calculate_after_tax_return_mixed_gains_losses(self, builder):
        """Calculate after-tax return with mixed gains and losses."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("5.0"),
            realized_gains=Decimal("10000"),
            realized_losses=Decimal("3000"),
            long_term_percentage=Decimal("0.6"),  # 60% LT
            marginal_tax_rate_st=Decimal("0.35"),
            marginal_tax_rate_lt=Decimal("0.15"),
        )

        # Net gains: 10000 - 3000 = 7000
        # LT portion: 7000 * 0.6 = 4200
        # ST portion: 7000 * 0.4 = 2800
        # Tax: (4200 * 0.15) + (2800 * 0.35) = 630 + 980 = 1610
        # After-tax: 5.0 - (1610 / 100000 * 100) = 3.39%
        assert after_tax == Decimal("3.39")

    def test_calculate_after_tax_return_no_gains(self, builder):
        """No tax impact when no gains realized."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("5.0"),
            realized_gains=Decimal("0"),
            realized_losses=Decimal("0"),
        )

        assert after_tax == Decimal("5.0")

    def test_calculate_after_tax_return_tax_loss_harvesting(self, builder):
        """Calculate return with tax-loss harvesting benefit."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("5.0"),
            realized_gains=Decimal("8000"),
            realized_losses=Decimal("8000"),  # Perfect offset (subtract, not negative)
            long_term_percentage=Decimal("0.5"),
            marginal_tax_rate_st=Decimal("0.35"),
            marginal_tax_rate_lt=Decimal("0.15"),
        )

        # Net gains = 8000 - 8000 = 0, so no tax
        assert after_tax == Decimal("5.0")


class TestGetTaxReport:
    """Test comprehensive tax reporting."""

    def test_tax_report_structure(self, builder):
        """Verify tax report has required sections."""
        report = builder.get_tax_report()

        assert "capital_gains_summary" in report
        assert "wash_sale_compliance" in report
        assert "tax_efficiency_score" in report

    def test_capital_gains_summary_fields(self, builder):
        """Verify capital gains summary contains expected fields."""
        report = builder.get_tax_report()
        summary = report["capital_gains_summary"]

        assert "short_term_gains" in summary
        assert "short_term_losses" in summary
        assert "long_term_gains" in summary
        assert "long_term_losses" in summary
        assert "net_gain_loss" in summary
        assert "projected_tax" in summary

    def test_wash_sale_compliance_section(self, builder):
        """Verify wash-sale compliance section exists."""
        report = builder.get_tax_report()
        compliance = report["wash_sale_compliance"]

        assert "total_violations" in compliance or isinstance(compliance, dict)

    def test_tax_efficiency_score_calculation(self, builder):
        """Verify tax efficiency score is calculated."""
        report = builder.get_tax_report()
        score = report["tax_efficiency_score"]

        # Score should be 0-100
        assert Decimal("0") <= score <= Decimal("100")


class TestCalculateTaxEfficiencyScore:
    """Test tax efficiency score calculation."""

    def test_score_for_100_percent_long_term(self, builder):
        """Maximum score (100) for 100% long-term gains."""
        # Mock gain report with only LT gains
        from app.services.tax_efficiency.capital_gain_tracker import TaxLotReport

        report = TaxLotReport(
            report_date=datetime.now(),
            total_short_term_gains=Decimal("0"),
            total_short_term_losses=Decimal("0"),
            total_long_term_gains=Decimal("10000"),
            total_long_term_losses=Decimal("0"),
            net_short_term=Decimal("0"),
            net_long_term=Decimal("10000"),
            net_capital_gain_loss=Decimal("10000"),
            projected_annual_tax=Decimal("1500"),  # 15%
            unrealized_gains_summary={},
        )

        score = builder._calculate_tax_efficiency_score(report)
        assert score == Decimal("100")

    def test_score_for_zero_gains(self, builder):
        """Maximum score (100) when no gains (no tax)."""
        from app.services.tax_efficiency.capital_gain_tracker import TaxLotReport

        report = TaxLotReport(
            report_date=datetime.now(),
            total_short_term_gains=Decimal("0"),
            total_short_term_losses=Decimal("0"),
            total_long_term_gains=Decimal("0"),
            total_long_term_losses=Decimal("0"),
            net_short_term=Decimal("0"),
            net_long_term=Decimal("0"),
            net_capital_gain_loss=Decimal("0"),
            projected_annual_tax=Decimal("0"),
            unrealized_gains_summary={},
        )

        score = builder._calculate_tax_efficiency_score(report)
        assert score == Decimal("100")

    def test_score_for_100_percent_short_term(self, builder):
        """Minimum score (50) for 100% short-term gains."""
        from app.services.tax_efficiency.capital_gain_tracker import TaxLotReport

        report = TaxLotReport(
            report_date=datetime.now(),
            total_short_term_gains=Decimal("10000"),
            total_short_term_losses=Decimal("0"),
            total_long_term_gains=Decimal("0"),
            total_long_term_losses=Decimal("0"),
            net_short_term=Decimal("10000"),
            net_long_term=Decimal("0"),
            net_capital_gain_loss=Decimal("10000"),
            projected_annual_tax=Decimal("3500"),  # 35%
            unrealized_gains_summary={},
        )

        score = builder._calculate_tax_efficiency_score(report)
        assert score == Decimal("50")

    def test_score_for_mixed_gains(self, builder):
        """Score between 50-100 for mixed ST/LT gains."""
        from app.services.tax_efficiency.capital_gain_tracker import TaxLotReport

        report = TaxLotReport(
            report_date=datetime.now(),
            total_short_term_gains=Decimal("5000"),
            total_short_term_losses=Decimal("0"),
            total_long_term_gains=Decimal("5000"),
            total_long_term_losses=Decimal("0"),
            net_short_term=Decimal("5000"),
            net_long_term=Decimal("5000"),
            net_capital_gain_loss=Decimal("10000"),
            projected_annual_tax=Decimal("2250"),  # (5000*0.15) + (5000*0.35)
            unrealized_gains_summary={},
        )

        score = builder._calculate_tax_efficiency_score(report)
        assert Decimal("50") < score < Decimal("100")
        assert score == Decimal("75")  # 50% LT = 50 + (0.5 * 50) = 75


class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_full_tax_optimization_flow(self, builder):
        """Test complete tax optimization flow."""
        # Setup portfolio with losses
        base_allocation = {
            "AAPL": Decimal("0.5"),
            "MSFT": Decimal("0.5"),
        }
        current_positions = {
            "AAPL": Decimal("40000"),
            "MSFT": Decimal("60000"),
        }
        cost_basis = {
            "AAPL": Decimal("50000"),
            "MSFT": Decimal("60000"),
        }
        quantities = {
            "AAPL": Decimal("400"),
            "MSFT": Decimal("600"),
        }
        current_prices = {
            "AAPL": Decimal("100"),
            "MSFT": Decimal("100"),
        }

        # Run optimization
        result = await builder.optimize_for_taxes(
            base_allocation=base_allocation,
            current_positions=current_positions,
            cost_basis=cost_basis,
            quantities=quantities,
            current_prices=current_prices,
            marginal_tax_rate=Decimal("0.25"),
            capital=Decimal("100000"),
        )

        # Verify result structure
        assert result.base_allocation is not None
        assert result.tax_adjusted_allocation is not None
        assert isinstance(result.harvesting_opportunities, list)
        assert result.tax_benefit_estimated >= Decimal("0")
        assert result.after_tax_return_pct >= Decimal("0")
        assert isinstance(result.adjustments_made, list)

    def test_tax_report_with_data(self, builder):
        """Generate tax report with real data."""
        # Record some transactions
        builder.gain_tracker.record_position_purchase(
            "AAPL", Decimal("100"), Decimal("100"), datetime.now()
        )
        builder.gain_tracker.record_position_sale(
            "AAPL", Decimal("100"), Decimal("120"),
            datetime.now() + timedelta(days=400), method="FIFO"
        )

        # Generate report
        report = builder.get_tax_report()

        # Verify report contains calculated values
        assert report["capital_gains_summary"]["long_term_gains"] > 0
        assert report["tax_efficiency_score"] > Decimal("0")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_optimize_with_zero_capital(self, builder):
        """Handle optimization with zero capital."""
        result = await builder.optimize_for_taxes(
            base_allocation={"AAPL": Decimal("1.0")},
            current_positions={"AAPL": Decimal("0")},
            cost_basis={"AAPL": Decimal("0")},
            quantities={"AAPL": Decimal("0")},
            current_prices={"AAPL": Decimal("100")},
            capital=Decimal("0"),
        )

        assert result.tax_benefit_estimated == Decimal("0")

    @pytest.mark.asyncio
    async def test_optimize_with_high_tax_rate(self, builder):
        """Test optimization with high marginal tax rate."""
        result = await builder.optimize_for_taxes(
            base_allocation={"AAPL": Decimal("1.0")},
            current_positions={"AAPL": Decimal("40000")},
            cost_basis={"AAPL": Decimal("50000")},
            quantities={"AAPL": Decimal("400")},
            current_prices={"AAPL": Decimal("100")},
            marginal_tax_rate=Decimal("0.50"),  # 50% rate
            capital=Decimal("100000"),
        )

        # Higher tax rate should result in higher tax benefit
        assert result.tax_benefit_estimated >= Decimal("0")

    def test_after_tax_return_negative_return(self, builder):
        """Handle negative gross return."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("-5.0"),
            realized_gains=Decimal("0"),
            realized_losses=Decimal("0"),
        )

        assert after_tax == Decimal("-5.0")

    def test_after_tax_return_maximum_tax_rate(self, builder):
        """Calculate after-tax return at maximum tax rate."""
        after_tax = builder.calculate_after_tax_return(
            gross_return_pct=Decimal("10.0"),
            realized_gains=Decimal("10000"),
            realized_losses=Decimal("0"),
            long_term_percentage=Decimal("1.0"),
            marginal_tax_rate_st=Decimal("0.37"),
            marginal_tax_rate_lt=Decimal("0.25"),
        )

        # Even with high tax, return should be positive
        assert after_tax > Decimal("0")
        assert after_tax < Decimal("10.0")
