"""
Tests for app/security/input_validation.py
"""

import pytest
from decimal import Decimal
from app.security.input_validation import (
    ValidationError,
    InputSanitizer,
    NumericValidator,
    ListValidator,
    TradingValidator,
    RateLimiter,
    validate_and_sanitize_input,
)


class TestInputSanitizer:
    """Test input sanitization."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = InputSanitizer.sanitize_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_string_html(self):
        """Test HTML escaping."""
        result = InputSanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_sanitize_string_sql_injection(self):
        """Test SQL injection detection."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string("'; DROP TABLE users; --")

    def test_sanitize_string_xss(self):
        """Test XSS detection."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string("<script>alert(1)</script>")

    def test_sanitize_string_command_injection(self):
        """Test command injection detection."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string("; rm -rf /")

    def test_sanitize_string_path_traversal(self):
        """Test path traversal detection."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string("../../../etc/passwd")

    def test_sanitize_string_max_length(self):
        """Test max length enforcement."""
        long_string = "a" * 200
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string(long_string, max_length=100)

    def test_sanitize_symbol(self):
        """Test symbol sanitization."""
        result = InputSanitizer.sanitize_symbol("  aapl  ")
        assert result == "AAPL"

    def test_sanitize_symbol_invalid(self):
        """Test invalid symbol format."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_symbol("AAPL@#$")

    def test_sanitize_email(self):
        """Test email sanitization."""
        result = InputSanitizer.sanitize_email("  Test@Example.COM  ")
        assert result == "test@example.com"

    def test_sanitize_email_invalid(self):
        """Test invalid email format."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_email("invalid-email")

    def test_sanitize_url(self):
        """Test URL sanitization."""
        result = InputSanitizer.sanitize_url("https://example.com")
        assert result == "https://example.com"

    def test_sanitize_url_dangerous(self):
        """Test dangerous URL protocol."""
        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_url("javascript:alert(1)")


class TestNumericValidator:
    """Test numeric validation."""

    def test_validate_decimal_valid(self):
        """Test valid decimal validation."""
        result = NumericValidator.validate_decimal("100.50")
        assert result == Decimal("100.50")

    def test_validate_decimal_min(self):
        """Test minimum value constraint."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_decimal("5", min_value=10)

    def test_validate_decimal_max(self):
        """Test maximum value constraint."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_decimal("150", max_value=100)

    def test_validate_decimal_precision(self):
        """Test precision constraint."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_decimal("100.123456789", max_precision=6)

    def test_validate_integer_valid(self):
        """Test valid integer validation."""
        result = NumericValidator.validate_integer("42")
        assert result == 42

    def test_validate_integer_range(self):
        """Test integer range validation."""
        with pytest.raises(ValidationError):
            NumericValidator.validate_integer("150", min_value=0, max_value=100)

    def test_validate_percentage(self):
        """Test percentage validation."""
        result = NumericValidator.validate_percentage("0.5")
        assert result == Decimal("50")

        result = NumericValidator.validate_percentage("75")
        assert result == Decimal("75")


class TestTradingValidator:
    """Test trading-specific validation."""

    def test_validate_price_valid(self):
        """Test valid price validation."""
        result = TradingValidator.validate_price("100.50")
        assert result == Decimal("100.50")

    def test_validate_price_too_low(self):
        """Test price below minimum."""
        with pytest.raises(ValidationError):
            TradingValidator.validate_price("0.00001")

    def test_validate_price_negative(self):
        """Test negative price."""
        with pytest.raises(ValidationError):
            TradingValidator.validate_price("-10.00")

    def test_validate_quantity_valid(self):
        """Test valid quantity validation."""
        result = TradingValidator.validate_quantity("100")
        assert result == Decimal("100")

    def test_validate_quantity_negative(self):
        """Test negative quantity."""
        with pytest.raises(ValidationError):
            TradingValidator.validate_quantity("-10")

    def test_validate_symbol_valid(self):
        """Test valid symbol validation."""
        result = TradingValidator.validate_symbol("AAPL")
        assert result == "AAPL"

    def test_validate_symbol_invalid_chars(self):
        """Test invalid symbol characters."""
        with pytest.raises(ValidationError):
            TradingValidator.validate_symbol("AAPL@#$")

    def test_validate_order_params(self):
        """Test order parameter validation."""
        result = TradingValidator.validate_order_params(
            symbol="AAPL",
            side="buy",
            quantity="100",
            price="150.00",
            order_type="limit"
        )
        assert result["symbol"] == "AAPL"
        assert result["side"] == "buy"
        assert result["quantity"] == Decimal("100")

    def test_validate_order_params_invalid_side(self):
        """Test invalid order side."""
        with pytest.raises(ValidationError):
            TradingValidator.validate_order_params(
                symbol="AAPL",
                side="invalid",
                quantity="100"
            )


class TestListValidator:
    """Test list validation."""

    def test_validate_list_valid(self):
        """Test valid list validation."""
        result = ListValidator.validate_list([1, 2, 3])
        assert result == [1, 2, 3]

    def test_validate_list_too_long(self):
        """Test list length limit."""
        with pytest.raises(ValidationError):
            ListValidator.validate_list(list(range(200)), max_length=100)

    def test_validate_symbol_list(self):
        """Test symbol list validation."""
        result = ListValidator.validate_symbol_list(["AAPL", "MSFT", "GOOGL"])
        assert result == ["AAPL", "MSFT", "GOOGL"]


class TestRateLimiter:
    """Test rate limiting."""

    def test_rate_limit_within_limit(self):
        """Test requests within rate limit."""
        limiter = RateLimiter()
        allowed, info = limiter.check_rate_limit("test_user", limit=5, window=60)
        assert allowed is True
        assert info["remaining"] == 4

    def test_rate_limit_exceed(self):
        """Test exceeding rate limit."""
        limiter = RateLimiter()
        # Make 5 requests (limit is 5)
        for _ in range(5):
            limiter.check_rate_limit("test_user2", limit=5, window=60)
        
        # 6th request should fail
        with pytest.raises(ValidationError):
            limiter.check_rate_limit("test_user2", limit=5, window=60)

    def test_rate_limit_reset(self):
        """Test rate limit reset."""
        limiter = RateLimiter()
        limiter.check_rate_limit("test_user3", limit=5, window=60)
        limiter.reset_limit("test_user3")
        
        # Should be able to make requests again
        allowed, _ = limiter.check_rate_limit("test_user3", limit=5, window=60)
        assert allowed is True


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_validate_and_sanitize_input_string(self):
        """Test string validation."""
        result = validate_and_sanitize_input("test string", input_type="str")
        assert result == "test string"

    def test_validate_and_sanitize_input_symbol(self):
        """Test symbol validation."""
        result = validate_and_sanitize_input("aapl", input_type="symbol")
        assert result == "AAPL"

    def test_validate_and_sanitize_input_price(self):
        """Test price validation."""
        result = validate_and_sanitize_input("100.50", input_type="price")
        assert result == Decimal("100.50")

    def test_validate_and_sanitize_input_list(self):
        """Test list validation."""
        result = validate_and_sanitize_input([1, 2, 3], input_type="list")
        assert result == [1, 2, 3]
