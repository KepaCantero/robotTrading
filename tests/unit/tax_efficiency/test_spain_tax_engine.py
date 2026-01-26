"""
Unit tests for SpainTaxEngine.

Tests Spain-specific tax rules:
- Progressive capital gains tax (19/21/23%)
- No LT/ST distinction
- Dividend taxation same as capital gains
- No wash sale rule
- EU withholding tax handling
- Modelo 720 threshold tracking
"""

import pytest
from decimal import Decimal

from app.services.tax_efficiency.engines.spain_tax_engine import SpainTaxEngine
from app.services.tax_efficiency.engines.factory import get_tax_engine


class TestSpainTaxEngine:
    """Test suite for SpainTaxEngine."""

    @pytest.fixture
    def engine(self):
        """Create a SpainTaxEngine instance for testing."""
        return SpainTaxEngine()

    @pytest.fixture
    def engine_with_custom_config(self):
        """Create engine with custom tax rates."""
        config = {
            "rate_1": "0.20",
            "rate_2": "0.22",
            "rate_3": "0.25",
            "bracket_1_limit": "30000",
            "bracket_2_limit": "50000",
        }
        return SpainTaxEngine(config)

    # Test progressive capital gains tax
    def test_bracket_1_tax(self, engine):
        """Test first bracket: 19% on gains up to €33,007.99."""
        gain = Decimal("20000")
        tax = engine.calculate_capital_gains_tax(gain)
        expected = gain * engine.RATE_1
        assert tax == expected
        assert tax == Decimal("3800")

    def test_bracket_2_tax(self, engine):
        """Test second bracket: 21% on gains €33,008 - €53,407.99."""
        gain = Decimal("40000")
        tax = engine.calculate_capital_gains_tax(gain)
        expected = gain * engine.RATE_2
        assert tax == expected
        assert tax == Decimal("8400")

    def test_bracket_3_tax(self, engine):
        """Test third bracket: 23% on gains over €53,408."""
        gain = Decimal("100000")
        tax = engine.calculate_capital_gains_tax(gain)
        expected = gain * engine.RATE_3
        assert tax == expected
        assert tax == Decimal("23000")

    def test_bracket_boundary_1_to_2(self, engine):
        """Test boundary between bracket 1 and 2."""
        # Just below bracket 2
        gain_1 = Decimal("33000")
        tax_1 = engine.calculate_capital_gains_tax(gain_1)
        assert tax_1 == gain_1 * engine.RATE_1

        # In bracket 2
        gain_2 = Decimal("34000")
        tax_2 = engine.calculate_capital_gains_tax(gain_2)
        assert tax_2 == gain_2 * engine.RATE_2

    def test_bracket_boundary_2_to_3(self, engine):
        """Test boundary between bracket 2 and 3."""
        # Just below bracket 3
        gain_1 = Decimal("53000")
        tax_1 = engine.calculate_capital_gains_tax(gain_1)
        assert tax_1 == gain_1 * engine.RATE_2

        # In bracket 3
        gain_2 = Decimal("55000")
        tax_2 = engine.calculate_capital_gains_tax(gain_2)
        assert tax_2 == gain_2 * engine.RATE_3

    def test_no_tax_on_zero_gain(self, engine):
        """Test no tax on zero gain."""
        tax = engine.calculate_capital_gains_tax(Decimal("0"))
        assert tax == Decimal("0")

    def test_no_tax_on_loss(self, engine):
        """Test no tax on losses."""
        tax = engine.calculate_capital_gains_tax(Decimal("-5000"))
        assert tax == Decimal("0")

    # Test no LT/ST distinction
    def test_holding_period_ignored(self, engine):
        """Test that holding period doesn't affect tax calculation."""
        gain = Decimal("20000")

        # Short-term (30 days)
        tax_st = engine.calculate_capital_gains_tax(gain, holding_period_days=30)

        # Long-term (400 days)
        tax_lt = engine.calculate_capital_gains_tax(gain, holding_period_days=400)

        # Should be identical
        assert tax_st == tax_lt

    # Test dividend taxation
    def test_dividend_tax_same_as_capital_gains(self, engine):
        """Test dividends taxed at same progressive rates as capital gains."""
        dividend = Decimal("20000")
        tax = engine.calculate_dividend_tax(dividend)

        # Should use same progressive calculation
        capital_gain_tax = engine.calculate_capital_gains_tax(dividend)
        assert tax == capital_gain_tax

    def test_dividend_tax_bracket_3(self, engine):
        """Test dividend tax in highest bracket."""
        dividend = Decimal("100000")
        tax = engine.calculate_dividend_tax(dividend)
        expected = dividend * engine.RATE_3
        assert tax == expected

    # Test wash sale rule
    def test_no_wash_sale_rule(self, engine):
        """Test Spain does not have wash sale rule."""
        assert engine.applies_wash_sale() is False

    # Test withholding tax rates
    def test_eu_withholding_tax_zero(self, engine):
        """Test 0% withholding for EU countries."""
        eu_countries = ["FR", "DE", "IT", "PT", "NL", "ES"]

        for country in eu_countries:
            rate = engine.get_withholding_tax_rate(country)
            assert rate == Decimal("0"), f"Failed for {country}"

    def test_us_withholding_tax(self, engine):
        """Test 15% withholding for US (tax treaty)."""
        rate = engine.get_withholding_tax_rate("US")
        assert rate == Decimal("0.15")

    def test_uk_withholding_tax(self, engine):
        """Test 15% withholding for UK (tax treaty)."""
        rate = engine.get_withholding_tax_rate("UK")
        assert rate == Decimal("0.15")

    def test_ch_withholding_tax(self, engine):
        """Test 15% withholding for Switzerland (tax treaty)."""
        rate = engine.get_withholding_tax_rate("CH")
        assert rate == Decimal("0.15")

    def test_default_withholding_tax(self, engine):
        """Test 19% default withholding for non-EU/non-treaty countries."""
        rate = engine.get_withholding_tax_rate("JP")
        assert rate == Decimal("0.19")

    # Test deductions
    def test_tax_with_deductions(self, engine):
        """Test tax calculation with allowable deductions."""
        gain = Decimal("50000")
        deductions = Decimal("5000")

        taxable_gain = gain - deductions
        expected_tax = taxable_gain * engine.RATE_2  # Now in bracket 2

        tax = engine.calculate_tax_with_deductions(gain, deductions)
        assert tax == expected_tax

    def test_deductions_exceed_gain(self, engine):
        """Test deductions cannot create negative taxable income."""
        gain = Decimal("5000")
        deductions = Decimal("10000")

        tax = engine.calculate_tax_with_deductions(gain, deductions)
        assert tax == Decimal("0")  # No tax on negative taxable income

    # Test gain/loss compensation
    def test_gain_loss_compensation(self, engine):
        """Test losses offset gains."""
        gains = [Decimal("30000"), Decimal("10000")]
        losses = [Decimal("-5000"), Decimal("-3000")]

        tax = engine.calculate_compensated_tax(gains, losses)

        # Net gain: 40000 - 8000 = 32000
        # Tax: 32000 * 0.19 = 6080 (bracket 1: <= 33,007.99)
        expected_tax = Decimal("32000") * engine.RATE_1
        assert tax == expected_tax

    def test_losses_exceed_gains(self, engine):
        """Test no tax when losses exceed gains."""
        gains = [Decimal("10000")]
        losses = [Decimal("-15000")]

        tax = engine.calculate_compensated_tax(gains, losses)
        assert tax == Decimal("0")

    # Test total tax liability
    def test_total_tax_liability(self, engine):
        """Test combined tax on capital gains + dividends."""
        capital_gains = Decimal("20000")
        dividends = Decimal("10000")

        tax = engine.calculate_total_tax_liability(capital_gains, dividends)

        # Total: 30000, falls in bracket 1 (<= 33,007.99)
        expected = Decimal("30000") * engine.RATE_1
        assert tax == expected

    def test_total_tax_with_other_income(self, engine):
        """Test total tax calculation (other income not combined in Spain)."""
        capital_gains = Decimal("20000")
        dividends = Decimal("10000")
        other_income = Decimal("50000")

        tax = engine.calculate_total_tax_liability(
            capital_gains, dividends, other_income
        )

        # Other income is taxed separately under general IRPF
        # Only savings income (capital gains + dividends) combined
        expected = Decimal("30000") * engine.RATE_1
        assert tax == expected

    # Test Modelo 720 threshold
    def test_modelo_720_below_threshold(self, engine):
        """Test Modelo 720 not required below €50k threshold."""
        result = engine.check_modelo_720_threshold(Decimal("40000"))

        assert result["threshold"] == 50000.0
        assert result["value"] == 40000.0
        assert result["exceeds"] is False
        assert result["filing_required"] is False

    def test_modelo_720_at_threshold(self, engine):
        """Test Modelo 720 at exactly €50k threshold."""
        result = engine.check_modelo_720_threshold(Decimal("50000"))

        assert result["exceeds"] is False  # Not > threshold
        assert result["filing_required"] is False

    def test_modelo_720_above_threshold(self, engine):
        """Test Modelo 720 required above €50k threshold."""
        result = engine.check_modelo_720_threshold(Decimal("60000"))

        assert result["exceeds"] is True
        assert result["filing_required"] is True
        assert result["form"] == "Modelo 720"
        assert result["deadline"] == "March 31st (following year)"

    # Test tax rate by gain
    def test_get_tax_rate_by_gain_bracket_1(self, engine):
        """Test getting tax rate for bracket 1."""
        rate, limit = engine.get_tax_rate_by_gain(Decimal("20000"))
        assert rate == engine.RATE_1
        assert limit == engine.BRACKET_1_LIMIT

    def test_get_tax_rate_by_gain_bracket_2(self, engine):
        """Test getting tax rate for bracket 2."""
        rate, limit = engine.get_tax_rate_by_gain(Decimal("40000"))
        assert rate == engine.RATE_2
        assert limit == engine.BRACKET_2_LIMIT

    def test_get_tax_rate_by_gain_bracket_3(self, engine):
        """Test getting tax rate for bracket 3."""
        rate, limit = engine.get_tax_rate_by_gain(Decimal("100000"))
        assert rate == engine.RATE_3
        assert limit == Decimal("Infinity")

    # Test tax brackets display
    def test_get_tax_brackets(self, engine):
        """Test getting all tax brackets for display."""
        brackets = engine.get_tax_brackets()

        assert len(brackets) == 3

        assert brackets[0]["bracket"] == 1
        assert brackets[0]["rate"] == 0.19
        assert brackets[0]["limit"] == 33007.99

        assert brackets[1]["bracket"] == 2
        assert brackets[1]["rate"] == 0.21
        assert brackets[1]["limit"] == 53407.99

        assert brackets[2]["bracket"] == 3
        assert brackets[2]["rate"] == 0.23
        assert brackets[2]["limit"] == float("inf")

    # Test annual estimation
    def test_estimate_annual_tax(self, engine):
        """Test annual tax estimation."""
        unrealized_gains = Decimal("25000")
        estimated_dividends = Decimal("5000")

        estimate = engine.estimate_annual_tax(unrealized_gains, estimated_dividends)

        assert estimate["unrealized_gains"] == 25000.0
        assert estimate["estimated_dividends"] == 5000.0
        assert estimate["total_income"] == 30000.0
        assert estimate["currency"] == "EUR"

        # Tax should be 30000 * 0.19 = 5700 (bracket 1)
        assert estimate["estimated_tax"] == 5700.0

        # Effective rate: 5700 / 30000 = 0.19
        assert estimate["effective_rate"] == 0.19

    # Test custom config
    def test_custom_config_rates(self, engine_with_custom_config):
        """Test engine with custom tax rates."""
        engine = engine_with_custom_config

        assert engine.RATE_1 == Decimal("0.20")
        assert engine.RATE_2 == Decimal("0.22")
        assert engine.RATE_3 == Decimal("0.25")

    def test_custom_config_calculation(self, engine_with_custom_config):
        """Test tax calculation with custom rates."""
        engine = engine_with_custom_config
        gain = Decimal("25000")

        tax = engine.calculate_capital_gains_tax(gain)
        # Custom bracket 1 limit is 30000, so 25000 falls in bracket 1 (20%)
        expected = gain * Decimal("0.20")  # Custom rate 1

        assert tax == expected

    def test_custom_config_brackets(self, engine_with_custom_config):
        """Test custom bracket limits."""
        engine = engine_with_custom_config

        assert engine.BRACKET_1_LIMIT == Decimal("30000")
        assert engine.BRACKET_2_LIMIT == Decimal("50000")

    # Test factory
    def test_factory_spain_engine(self):
        """Test factory creates SpainTaxEngine."""
        engine = get_tax_engine("ES")

        assert isinstance(engine, SpainTaxEngine)
        assert engine.calculate_capital_gains_tax(Decimal("20000")) == Decimal("3800")

    def test_factory_default_to_spain(self):
        """Test factory defaults to Spain for unknown countries."""
        engine = get_tax_engine("XX")

        # Should return SpainTaxEngine as default
        assert isinstance(engine, SpainTaxEngine)

    def test_factory_case_insensitive(self):
        """Test factory is case-insensitive."""
        engine_upper = get_tax_engine("ES")
        engine_lower = get_tax_engine("es")
        engine_mixed = get_tax_engine("Es")

        assert all(isinstance(e, SpainTaxEngine) for e in [engine_upper, engine_lower, engine_mixed])

    # Test repr
    def test_repr(self, engine):
        """Test string representation."""
        repr_str = repr(engine)

        assert "SpainTaxEngine" in repr_str
        assert "0.19" in repr_str
        assert "0.21" in repr_str
        assert "0.23" in repr_str
