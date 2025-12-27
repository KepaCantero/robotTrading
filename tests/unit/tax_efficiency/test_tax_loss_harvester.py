"""
T15.1.1: TaxLossHarvester - Comprehensive unit tests

Tests cover:
- Position identification with various loss thresholds
- Tax benefit calculation across different tax rates
- Replacement position suggestions
- Annual tax benefit estimation with loss carryforward
"""

from decimal import Decimal

import pytest

from app.services.tax_efficiency.tax_loss_harvester import HarvestablePosition, TaxLossHarvester


@pytest.fixture
def harvester():
    """Create TaxLossHarvester instance."""
    return TaxLossHarvester()


class TestIdentifyHarvestablePositions:
    """Test position identification with various loss scenarios."""

    def test_identify_single_losing_position(self, harvester):
        """Identify a single position with unrealized loss."""
        positions = {"AAPL": Decimal("9000")}  # Current value
        cost_basis = {"AAPL": Decimal("10000")}  # Cost basis
        quantities = {"AAPL": Decimal("100")}
        current_prices = {"AAPL": Decimal("90")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("100")
        )

        assert len(harvestable) == 1
        assert harvestable[0].symbol == "AAPL"
        assert harvestable[0].unrealized_loss == Decimal("-1000")
        assert harvestable[0].quantity == Decimal("100")

    def test_identify_multiple_losing_positions(self, harvester):
        """Identify multiple positions with losses."""
        positions = {"AAPL": Decimal("9000"), "MSFT": Decimal("4000"), "GOOGL": Decimal("19500")}
        cost_basis = {"AAPL": Decimal("10000"), "MSFT": Decimal("5000"), "GOOGL": Decimal("20000")}
        quantities = {"AAPL": Decimal("100"), "MSFT": Decimal("50"), "GOOGL": Decimal("100")}
        current_prices = {"AAPL": Decimal("90"), "MSFT": Decimal("80"), "GOOGL": Decimal("195")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("100")
        )

        assert len(harvestable) == 3
        symbols = [p.symbol for p in harvestable]
        assert set(symbols) == {"AAPL", "MSFT", "GOOGL"}

    def test_exclude_profitable_positions(self, harvester):
        """Exclude positions with gains."""
        positions = {"AAPL": Decimal("11000"), "MSFT": Decimal("4000")}
        cost_basis = {"AAPL": Decimal("10000"), "MSFT": Decimal("5000")}
        quantities = {"AAPL": Decimal("100"), "MSFT": Decimal("50")}
        current_prices = {"AAPL": Decimal("110"), "MSFT": Decimal("80")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("100")
        )

        assert len(harvestable) == 1
        assert harvestable[0].symbol == "MSFT"

    def test_respect_minimum_loss_threshold(self, harvester):
        """Exclude positions with losses below threshold."""
        positions = {"AAPL": Decimal("9950"), "MSFT": Decimal("4000")}
        cost_basis = {"AAPL": Decimal("10000"), "MSFT": Decimal("5000")}
        quantities = {"AAPL": Decimal("100"), "MSFT": Decimal("50")}
        current_prices = {"AAPL": Decimal("99.50"), "MSFT": Decimal("80")}

        # Threshold of €500 should exclude AAPL (only €50 loss)
        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("500")
        )

        assert len(harvestable) == 1
        assert harvestable[0].symbol == "MSFT"

    def test_sort_by_loss_magnitude(self, harvester):
        """Sort results by loss amount (largest first)."""
        positions = {"A": Decimal("8000"), "B": Decimal("9000"), "C": Decimal("9500")}
        cost_basis = {"A": Decimal("10000"), "B": Decimal("10000"), "C": Decimal("10000")}
        quantities = {"A": Decimal("100"), "B": Decimal("100"), "C": Decimal("100")}
        current_prices = {"A": Decimal("80"), "B": Decimal("90"), "C": Decimal("95")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("100")
        )

        # Should be sorted: A (-€2000), B (-€1000), C (-€500)
        assert harvestable[0].unrealized_loss == Decimal("-2000")
        assert harvestable[1].unrealized_loss == Decimal("-1000")
        assert harvestable[2].unrealized_loss == Decimal("-500")

    def test_exclude_zero_quantity_positions(self, harvester):
        """Exclude positions with zero quantity."""
        positions = {"AAPL": Decimal("0"), "MSFT": Decimal("4000")}
        cost_basis = {"AAPL": Decimal("10000"), "MSFT": Decimal("5000")}
        quantities = {"AAPL": Decimal("0"), "MSFT": Decimal("50")}
        current_prices = {"AAPL": Decimal("100"), "MSFT": Decimal("80")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices
        )

        assert len(harvestable) == 1
        assert harvestable[0].symbol == "MSFT"


class TestCalculateTaxBenefit:
    """Test tax benefit calculation."""

    def test_calculate_tax_benefit_15_percent(self, harvester):
        """Calculate benefit with 15% tax rate."""
        loss = Decimal("-1000")
        rate = Decimal("0.15")
        benefit = harvester.calculate_tax_benefit(loss, rate)
        assert benefit == Decimal("150")

    def test_calculate_tax_benefit_25_percent(self, harvester):
        """Calculate benefit with 25% tax rate."""
        loss = Decimal("-1000")
        rate = Decimal("0.25")
        benefit = harvester.calculate_tax_benefit(loss, rate)
        assert benefit == Decimal("250")

    def test_calculate_tax_benefit_35_percent(self, harvester):
        """Calculate benefit with 35% tax rate."""
        loss = Decimal("-1000")
        rate = Decimal("0.35")
        benefit = harvester.calculate_tax_benefit(loss, rate)
        assert benefit == Decimal("350")

    def test_calculate_tax_benefit_45_percent(self, harvester):
        """Calculate benefit with 45% tax rate (high earner)."""
        loss = Decimal("-5000")
        rate = Decimal("0.45")
        benefit = harvester.calculate_tax_benefit(loss, rate)
        assert benefit == Decimal("2250")

    def test_no_benefit_for_gains(self, harvester):
        """Return zero benefit for gains."""
        gain = Decimal("1000")
        rate = Decimal("0.25")
        benefit = harvester.calculate_tax_benefit(gain, rate)
        assert benefit == Decimal("0")

    def test_no_benefit_for_zero_gain_loss(self, harvester):
        """Return zero benefit for break-even positions."""
        zero = Decimal("0")
        rate = Decimal("0.25")
        benefit = harvester.calculate_tax_benefit(zero, rate)
        assert benefit == Decimal("0")

    def test_benefit_scales_with_loss_magnitude(self, harvester):
        """Benefit increases proportionally with loss."""
        rate = Decimal("0.25")
        benefit_1k = harvester.calculate_tax_benefit(Decimal("-1000"), rate)
        benefit_5k = harvester.calculate_tax_benefit(Decimal("-5000"), rate)
        benefit_10k = harvester.calculate_tax_benefit(Decimal("-10000"), rate)

        assert benefit_5k == benefit_1k * 5
        assert benefit_10k == benefit_1k * 10


class TestSuggestReplacementPosition:
    """Test replacement position suggestions."""

    def test_aapl_replacement(self, harvester):
        """AAPL should suggest MSFT as replacement."""
        replacement = harvester.suggest_replacement_position(
            "AAPL", Decimal("100"), Decimal("150"), asset_class="equity"
        )

        assert replacement.symbol == "MSFT"
        assert replacement.quantity == Decimal("100")
        assert replacement.correlation_with_original >= Decimal("0.7")

    def test_voo_replacement(self, harvester):
        """VOO (index fund) should suggest SPY."""
        replacement = harvester.suggest_replacement_position(
            "VOO", Decimal("50"), Decimal("400"), asset_class="equity"
        )

        assert replacement.symbol == "SPY"
        assert replacement.correlation_with_original > Decimal("0.95")

    def test_bnd_replacement(self, harvester):
        """BND (bonds) should suggest AGG."""
        replacement = harvester.suggest_replacement_position(
            "BND", Decimal("200"), Decimal("75"), asset_class="fixed_income"
        )

        assert replacement.symbol == "AGG"
        assert replacement.correlation_with_original > Decimal("0.80")

    def test_replacement_maintains_quantity(self, harvester):
        """Replacement should maintain original quantity."""
        original_qty = Decimal("150")
        replacement = harvester.suggest_replacement_position(
            "GOOGL", original_qty, Decimal("100"), asset_class="equity"
        )

        assert replacement.quantity == original_qty

    def test_default_replacement_for_unknown_symbol(self, harvester):
        """Unknown symbol should default to SPY (equity) or AGG (fixed_income)."""
        replacement_equity = harvester.suggest_replacement_position(
            "UNKNOWN_TICKER", Decimal("100"), Decimal("100"), asset_class="equity"
        )

        replacement_bonds = harvester.suggest_replacement_position(
            "UNKNOWN_TICKER", Decimal("100"), Decimal("100"), asset_class="fixed_income"
        )

        assert replacement_equity.symbol == "SPY"
        assert replacement_bonds.symbol == "AGG"

    def test_replacement_correlation_within_bounds(self, harvester):
        """Correlation should always be between 0 and 1."""
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "VOO", "BND", "TLT"]
        for symbol in symbols:
            replacement = harvester.suggest_replacement_position(
                symbol, Decimal("100"), Decimal("100"), asset_class="equity"
            )
            assert Decimal("0") <= replacement.correlation_with_original <= Decimal("1")


class TestEstimateAnnualTaxBenefit:
    """Test annual tax benefit estimation."""

    def test_single_position_benefit(self, harvester):
        """Calculate benefit for single position."""
        pos = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("100"),
            current_price=Decimal("90"),
            unrealized_loss=Decimal("-1000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        benefit_dict = harvester.estimate_annual_tax_benefit(
            [pos], marginal_tax_rate=Decimal("0.25")
        )

        assert benefit_dict["total_harvestable_loss"] == Decimal("1000")
        assert benefit_dict["usable_this_year"] == Decimal("1000")
        assert benefit_dict["tax_benefit_this_year"] == Decimal("250")
        assert benefit_dict["carryforward_to_next_year"] == Decimal("0")

    def test_exceed_annual_deduction_limit(self, harvester):
        """Losses exceeding €3k should carryforward."""
        pos = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("100"),
            current_price=Decimal("50"),
            unrealized_loss=Decimal("-5000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        benefit_dict = harvester.estimate_annual_tax_benefit(
            [pos], marginal_tax_rate=Decimal("0.25")
        )

        assert benefit_dict["total_harvestable_loss"] == Decimal("5000")
        assert benefit_dict["usable_this_year"] == Decimal("3000")
        assert benefit_dict["carryforward_to_next_year"] == Decimal("2000")
        assert benefit_dict["tax_benefit_this_year"] == Decimal("750")

    def test_multiple_positions_combined(self, harvester):
        """Combine losses from multiple positions."""
        positions = [
            HarvestablePosition(
                symbol="AAPL",
                quantity=Decimal("100"),
                purchase_price=Decimal("100"),
                current_price=Decimal("80"),
                unrealized_loss=Decimal("-2000"),
                tax_benefit=Decimal("0"),
                hold_period_days=180,
            ),
            HarvestablePosition(
                symbol="MSFT",
                quantity=Decimal("50"),
                purchase_price=Decimal("200"),
                current_price=Decimal("150"),
                unrealized_loss=Decimal("-2500"),
                tax_benefit=Decimal("0"),
                hold_period_days=200,
            ),
        ]

        benefit_dict = harvester.estimate_annual_tax_benefit(
            positions, marginal_tax_rate=Decimal("0.25")
        )

        assert benefit_dict["total_harvestable_loss"] == Decimal("4500")
        assert benefit_dict["usable_this_year"] == Decimal("3000")
        assert benefit_dict["carryforward_to_next_year"] == Decimal("1500")

    def test_with_carryforward_losses(self, harvester):
        """Account for losses carried forward from prior year."""
        pos = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("100"),
            current_price=Decimal("80"),
            unrealized_loss=Decimal("-2000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        benefit_dict = harvester.estimate_annual_tax_benefit(
            [pos], marginal_tax_rate=Decimal("0.25"), capital_losses_carryforward=Decimal("1500")
        )

        # Total available: €2000 + €1500 carryforward = €3500
        # Usable this year: €3000 (max deduction)
        # New carryforward: €500
        assert benefit_dict["carryforward_to_next_year"] == Decimal("500")

    def test_zero_losses(self, harvester):
        """Handle case with no losses."""
        benefit_dict = harvester.estimate_annual_tax_benefit([], marginal_tax_rate=Decimal("0.25"))

        assert benefit_dict["total_harvestable_loss"] == Decimal("0")
        assert benefit_dict["usable_this_year"] == Decimal("0")
        assert benefit_dict["tax_benefit_this_year"] == Decimal("0")


class TestCreateHarvestingOpportunity:
    """Test complete harvesting opportunity creation."""

    def test_create_opportunity_with_replacement(self, harvester):
        """Create opportunity with replacement suggestion."""
        position = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("100"),
            current_price=Decimal("80"),
            unrealized_loss=Decimal("-2000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        opportunity = harvester.create_harvesting_opportunity(
            position, marginal_tax_rate=Decimal("0.25"), suggest_replacement=True
        )

        assert opportunity.position == position
        assert opportunity.replacement is not None
        assert opportunity.total_tax_benefit == Decimal("500")
        assert "Harvest" in opportunity.recommendation
        assert "AAPL" in opportunity.recommendation
        assert "Replace" in opportunity.recommendation

    def test_create_opportunity_without_replacement(self, harvester):
        """Create opportunity without replacement suggestion."""
        position = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            purchase_price=Decimal("100"),
            current_price=Decimal("80"),
            unrealized_loss=Decimal("-2000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        opportunity = harvester.create_harvesting_opportunity(
            position, marginal_tax_rate=Decimal("0.25"), suggest_replacement=False
        )

        assert opportunity.position == position
        assert opportunity.replacement is None
        assert opportunity.total_tax_benefit == Decimal("500")

    def test_opportunity_recommendation_format(self, harvester):
        """Recommendation should include position details."""
        position = HarvestablePosition(
            symbol="GOOGL",
            quantity=Decimal("50"),
            purchase_price=Decimal("150"),
            current_price=Decimal("100"),
            unrealized_loss=Decimal("-2500"),
            tax_benefit=Decimal("0"),
            hold_period_days=200,
        )

        opportunity = harvester.create_harvesting_opportunity(
            position, marginal_tax_rate=Decimal("0.35"), suggest_replacement=True
        )

        recommendation = opportunity.recommendation
        assert "50" in recommendation  # quantity
        assert "GOOGL" in recommendation  # symbol
        assert "2500" in recommendation or "2,500" in recommendation  # loss amount
        assert "875" in recommendation or "875.00" in recommendation  # tax benefit

    def test_opportunity_tax_benefit_calculation(self, harvester):
        """Tax benefit should be accurate for various rates."""
        position = HarvestablePosition(
            symbol="MSFT",
            quantity=Decimal("100"),
            purchase_price=Decimal("250"),
            current_price=Decimal("200"),
            unrealized_loss=Decimal("-5000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        # Test multiple tax rates
        for rate, expected in [
            (Decimal("0.15"), Decimal("750")),
            (Decimal("0.25"), Decimal("1250")),
            (Decimal("0.35"), Decimal("1750")),
        ]:
            opportunity = harvester.create_harvesting_opportunity(position, marginal_tax_rate=rate)
            assert opportunity.total_tax_benefit == expected


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_loss(self, harvester):
        """Handle very small loss amounts."""
        positions = {"AAPL": Decimal("9999.99")}
        cost_basis = {"AAPL": Decimal("10000")}
        quantities = {"AAPL": Decimal("1")}
        current_prices = {"AAPL": Decimal("9999.99")}

        harvestable = harvester.identify_harvestable_positions(
            positions, cost_basis, quantities, current_prices, min_loss_threshold=Decimal("0.01")
        )

        assert len(harvestable) == 1
        assert abs(harvestable[0].unrealized_loss) < Decimal("1")

    def test_large_loss_amount(self, harvester):
        """Handle very large loss amounts."""
        position = HarvestablePosition(
            symbol="AAPL",
            quantity=Decimal("100000"),
            purchase_price=Decimal("100"),
            current_price=Decimal("50"),
            unrealized_loss=Decimal("-5000000"),
            tax_benefit=Decimal("0"),
            hold_period_days=180,
        )

        benefit_dict = harvester.estimate_annual_tax_benefit(
            [position], marginal_tax_rate=Decimal("0.45")
        )

        # Only €3000 usable per year
        assert benefit_dict["usable_this_year"] == Decimal("3000")
        assert benefit_dict["carryforward_to_next_year"] == Decimal("4997000")

    def test_empty_positions_dict(self, harvester):
        """Handle empty positions dictionary."""
        harvestable = harvester.identify_harvestable_positions({}, {}, {}, {})

        assert len(harvestable) == 0

    def test_decimal_precision(self, harvester):
        """Maintain decimal precision through calculations."""
        loss = Decimal("-1234.56")
        rate = Decimal("0.2375")  # 23.75%
        benefit = harvester.calculate_tax_benefit(loss, rate)

        # Should be exactly €293.21
        expected = Decimal("1234.56") * Decimal("0.2375")
        assert benefit == expected
