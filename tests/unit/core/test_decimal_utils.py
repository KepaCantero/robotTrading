"""
Unit Tests for Decimal Utilities

Tests for the decimal utility functions that ensure precision in financial calculations.
"""

import pytest
from decimal import Decimal, InvalidOperation
from app.core.decimal_utils import (
    to_decimal,
    to_decimal_required,
    safe_decimal_divide,
    validate_price,
    validate_quantity,
    round_decimal,
    format_currency,
    calculate_percentage,
    round_to_currency_precision,
)


class TestToDecimal:
    """Tests for to_decimal function."""

    def test_int_to_decimal(self):
        """Test converting int to Decimal."""
        assert to_decimal(100) == Decimal("100")
        assert to_decimal(0) == Decimal("0")
        assert to_decimal(-50) == Decimal("-50")

    def test_float_to_decimal(self):
        """Test converting float to Decimal (avoids precision issues)."""
        # Note: str(float) is used to avoid floating point representation issues
        result = to_decimal(100.50)
        assert result == Decimal("100.5")

        # Test problematic float
        result = to_decimal(0.1)
        assert str(result) == "0.1"

    def test_string_to_decimal(self):
        """Test converting string to Decimal."""
        assert to_decimal("100") == Decimal("100")
        assert to_decimal("100.50") == Decimal("100.50")
        assert to_decimal("-25.75") == Decimal("-25.75")

    def test_string_with_currency_symbols(self):
        """Test converting strings with currency symbols."""
        assert to_decimal("$100.50") == Decimal("100.50")
        assert to_decimal("€1,234.56") == Decimal("1234.56")
        assert to_decimal("£500") == Decimal("500")

    def test_decimal_to_decimal(self):
        """Test passing Decimal returns same Decimal."""
        original = Decimal("123.45")
        result = to_decimal(original)
        assert result == original
        assert result is original  # Same object reference

    def test_none_to_decimal(self):
        """Test None returns None."""
        assert to_decimal(None) is None

    def test_invalid_string_raises_error(self):
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert string"):
            to_decimal("not_a_number")

    def test_unsupported_type_raises_error(self):
        """Test unsupported type raises ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            to_decimal([1, 2, 3])


class TestToDecimalRequired:
    """Tests for to_decimal_required function."""

    def test_valid_conversion(self):
        """Test valid conversion works."""
        assert to_decimal_required(100) == Decimal("100")
        assert to_decimal_required("123.45") == Decimal("123.45")

    def test_none_raises_error(self):
        """Test None raises ValueError."""
        with pytest.raises(ValueError, match="Value cannot be None"):
            to_decimal_required(None)


class TestSafeDecimalDivide:
    """Tests for safe_decimal_divide function."""

    def test_normal_division(self):
        """Test normal division."""
        result = safe_decimal_divide("100", "4")
        assert result == Decimal("25")

    def test_division_by_zero_returns_none(self):
        """Test division by zero returns None."""
        result = safe_decimal_divide("100", "0")
        assert result is None

    def test_division_by_zero_returns_default(self):
        """Test division by zero returns default value."""
        default = Decimal("0")
        result = safe_decimal_divide("100", "0", default=default)
        assert result == Decimal("0")

    def test_invalid_values_return_none(self):
        """Test invalid values return None."""
        result = safe_decimal_divide("invalid", "4")
        assert result is None


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_price(self):
        """Test valid price passes validation."""
        result = validate_price("100.50")
        assert result == Decimal("100.50")

    def test_price_too_low(self):
        """Test price below minimum raises error."""
        with pytest.raises(ValueError, match="Price must be at least"):
            validate_price("0")

    def test_price_too_high(self):
        """Test price above maximum raises error."""
        with pytest.raises(ValueError, match="Price cannot exceed"):
            validate_price("2000000")

    def test_custom_bounds(self):
        """Test custom min/max bounds."""
        result = validate_price("50", min_value=Decimal("10"), max_value=Decimal("100"))
        assert result == Decimal("50")

    def test_invalid_price_type(self):
        """Test invalid price type raises error."""
        with pytest.raises(ValueError):
            validate_price("invalid")


class TestValidateQuantity:
    """Tests for validate_quantity function."""

    def test_valid_quantity(self):
        """Test valid quantity passes validation."""
        result = validate_quantity("1000")
        assert result == Decimal("1000")

    def test_quantity_too_low(self):
        """Test quantity below minimum raises error."""
        with pytest.raises(ValueError, match="Quantity must be at least"):
            validate_quantity("0")

    def test_negative_quantity(self):
        """Test negative quantity raises error."""
        with pytest.raises(ValueError):
            validate_quantity("-10")

    def test_quantity_too_high(self):
        """Test quantity above maximum raises error."""
        with pytest.raises(ValueError, match="Quantity cannot exceed"):
            validate_quantity("2000000000")

    def test_custom_bounds(self):
        """Test custom min/max bounds."""
        result = validate_quantity("500", min_value=Decimal("100"), max_value=Decimal("1000"))
        assert result == Decimal("500")


class TestRoundDecimal:
    """Tests for round_decimal function."""

    def test_round_half_up(self):
        """Test rounding with ROUND_HALF_UP (default)."""
        result = round_decimal("100.456", 2)
        assert result == Decimal("100.46")

        result = round_decimal("100.454", 2)
        assert result == Decimal("100.45")

    def test_round_down(self):
        """Test rounding with ROUND_DOWN."""
        from decimal import ROUND_DOWN

        result = round_decimal("100.459", 2, rounding=ROUND_DOWN)
        assert result == Decimal("100.45")

    def test_round_up(self):
        """Test rounding with ROUND_UP."""
        from decimal import ROUND_UP

        result = round_decimal("100.451", 2, rounding=ROUND_UP)
        assert result == Decimal("100.46")

    def test_round_to_zero_precision(self):
        """Test rounding to zero precision (integer)."""
        result = round_decimal("100.7", 0)
        assert result == Decimal("101")

    def test_round_negative_value(self):
        """Test rounding negative value."""
        result = round_decimal("-100.456", 2)
        assert result == Decimal("-100.46")


class TestFormatCurrency:
    """Tests for format_currency function."""

    def test_format_default_symbol(self):
        """Test formatting with default $ symbol."""
        result = format_currency("1234.56")
        assert result == "$1,234.56"

    def test_format_euro_symbol(self):
        """Test formatting with € symbol."""
        result = format_currency("1234.56", "€")
        assert result == "€1,234.56"

    def test_format_large_number(self):
        """Test formatting large number with commas."""
        result = format_currency("1234567.89")
        assert result == "$1,234,567.89"

    def test_format_zero(self):
        """Test formatting zero."""
        result = format_currency("0")
        assert result == "$0.00"

    def test_format_negative(self):
        """Test formatting negative value."""
        result = format_currency("-1234.56")
        assert result == "$-1,234.56"


class TestCalculatePercentage:
    """Tests for calculate_percentage function."""

    def test_calculate_percentage_normal(self):
        """Test calculating percentage."""
        result = calculate_percentage("50", "100")
        assert result == Decimal("50.00")

    def test_calculate_percentage_fractional(self):
        """Test calculating fractional percentage."""
        result = calculate_percentage("33.33", "100")
        assert result == Decimal("33.33")

    def test_calculate_percentage_division_by_zero(self):
        """Test division by zero returns None."""
        result = calculate_percentage("50", "0")
        assert result is None

    def test_calculate_percentage_custom_precision(self):
        """Test custom precision."""
        result = calculate_percentage("33.333", "100", precision=3)
        assert result == Decimal("33.333")


class TestRoundToCurrencyPrecision:
    """Tests for round_to_currency_precision function."""

    def test_round_usd(self):
        """Test rounding to USD precision (2 decimals)."""
        result = round_to_currency_precision("100.456", "USD")
        assert result == Decimal("100.46")

    def test_round_jpy(self):
        """Test rounding to JPY precision (0 decimals)."""
        result = round_to_currency_precision("100.7", "JPY")
        assert result == Decimal("101")

    def test_round_btc(self):
        """Test rounding to BTC precision (8 decimals)."""
        result = round_to_currency_precision("0.123456789", "BTC")
        assert result == Decimal("0.12345679")

    def test_round_eth(self):
        """Test rounding to ETH precision (18 decimals)."""
        result = round_to_currency_precision("1.1234567890123456789", "ETH")
        assert result == Decimal("1.123456789012345679")

    def test_unknown_currency_defaults_to_2(self):
        """Test unknown currency defaults to 2 decimals."""
        result = round_to_currency_precision("100.456", "XXX")
        assert result == Decimal("100.46")


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_very_small_number(self):
        """Test handling of very small numbers."""
        result = to_decimal("0.00000001")
        assert result == Decimal("0.00000001")

    def test_very_large_number(self):
        """Test handling of very large numbers."""
        result = to_decimal("999999999999")
        assert result == Decimal("999999999999")

    def test_scientific_notation_string(self):
        """Test parsing scientific notation strings."""
        result = to_decimal("1.23E+2")
        assert result == Decimal("123")

    def test_whitespace_in_string(self):
        """Test handling of whitespace in strings."""
        result = to_decimal("  100.50  ")
        assert result == Decimal("100.50")

    def test_mixed_currency_symbol_whitespace(self):
        """Test handling currency symbols with whitespace."""
        result = to_decimal(" $ 1,234.56 ")
        assert result == Decimal("1234.56")

    def test_zero_division_in_percentage(self):
        """Test percentage with zero denominator."""
        result = calculate_percentage("100", "0")
        assert result is None

    def test_negative_price_validation(self):
        """Test negative price validation."""
        with pytest.raises(ValueError):
            validate_price("-10")

    def test_negative_quantity_validation(self):
        """Test negative quantity validation."""
        with pytest.raises(ValueError):
            validate_quantity("-10")

    def test_rounding_extremely_small_value(self):
        """Test rounding extremely small value."""
        result = round_decimal("0.000000001", 8)
        assert result == Decimal("0.00000000")
