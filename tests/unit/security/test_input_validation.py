"""
Test suite for Input Validation

Tests:
- SQL injection prevention
- XSS prevention
- Command injection prevention
- Path traversal prevention
- Trading input validation
- Rate limiting
"""

import pytest
from decimal import Decimal, InvalidOperation

from app.security.input_validation import (
    InputSanitizer,
    NumericValidator,
    TradingValidator,
    RateLimiter,
    ListValidator,
    DictValidator,
    ValidationError,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
    COMMAND_INJECTION_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
    validate_and_sanitize_input,
    rate_limiter,
)


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""

    def test_detect_union_select(self):
        """Test detection of UNION SELECT injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("1' UNION SELECT * FROM users--")

    def test_detect_or_injection(self):
        """Test detection of OR-based injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("' OR '1'='1")

    def test_detect_drop_table(self):
        """Test detection of DROP TABLE injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("'; DROP TABLE users; --")

    def test_detect_comment_injection(self):
        """Test detection of SQL comment injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("admin'--")

    def test_detect_insert_statement(self):
        """Test detection of INSERT statement injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("'; INSERT INTO users VALUES ('hacker', 'password')--")

    def test_allow_safe_sql_keywords(self):
        """Test that SQL keywords in safe contexts are allowed."""
        sanitizer = InputSanitizer()

        # Should not trigger when keywords are part of normal text
        safe_text = "I selected the best option for this project"
        result = sanitizer.sanitize_string(safe_text)
        assert "selected" in result


class TestXSSPrevention:
    """Tests for XSS prevention."""

    def test_detect_script_tag(self):
        """Test detection of script tag injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("<script>alert('XSS')</script>")

    def test_detect_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("javascript:alert('XSS')")

    def test_detect_onclick_handler(self):
        """Test detection of onclick event handler."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("<img src=x onerror=alert('XSS')>")

    def test_detect_iframe_injection(self):
        """Test detection of iframe injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("<iframe src='evil.com'></iframe>")

    def test_detect_encoded_injection(self):
        """Test detection of URL-encoded injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("%3Cscript%3Ealert('XSS')%3C/script%3E")

    def test_html_escaping(self):
        """Test HTML escaping of output."""
        sanitizer = InputSanitizer()

        result = sanitizer.sanitize_string("<b>bold</b>")
        assert "&lt;b&gt;" in result


class TestCommandInjectionPrevention:
    """Tests for command injection prevention."""

    def test_detect_shell_metacharacters(self):
        """Test detection of shell metacharacters."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("file.txt; rm -rf /")

    def test_detect_pipe_injection(self):
        """Test detection of pipe injection."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("input | cat /etc/passwd")

    def test_detect_backtick_injection(self):
        """Test detection of backtick execution."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("`whoami`")

    def test_detect_dollar_sign_injection(self):
        """Test detection of variable substitution."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("$HOME")

    def test_detect_ampsersand_injection(self):
        """Test detection of command chaining."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("input && malicious_command")


class TestPathTraversalPrevention:
    """Tests for path traversal prevention."""

    def test_detect_double_dot_slash(self):
        """Test detection of ../ pattern."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("../../../etc/passwd")

    def test_detect_double_dot_backslash(self):
        """Test detection of ..\\ pattern."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("..\\..\\..\\windows\\system32")

    def test_detect_url_encoded_traversal(self):
        """Test detection of URL-encoded path traversal."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("%2e%2e%2f")

    def test_detect_mixed_encoding(self):
        """Test detection of mixed encoding traversal."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_string("..%2f..%2f..%2fetc")


class TestTradingInputValidation:
    """Tests for trading-specific input validation."""

    def test_validate_price_valid(self):
        """Test validation of valid price."""
        validator = TradingValidator()

        price = validator.validate_price("100.50")
        assert price == Decimal("100.50")

    def test_validate_price_too_low(self):
        """Test validation rejects price below minimum."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_price("0.00001")

    def test_validate_price_too_high(self):
        """Test validation rejects price above maximum."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_price("10000001")

    def test_validate_price_too_many_decimals(self):
        """Test validation rejects price with too many decimals."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_price("100.123456789")

    def test_validate_price_negative(self):
        """Test validation rejects negative price."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_price("-10")

    def test_validate_price_zero(self):
        """Test validation rejects zero price."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_price("0")

    def test_validate_quantity_valid(self):
        """Test validation of valid quantity."""
        validator = TradingValidator()

        quantity = validator.validate_quantity("100")
        assert quantity == Decimal("100")

    def test_validate_quantity_fractional(self):
        """Test validation of fractional quantity."""
        validator = TradingValidator()

        quantity = validator.validate_quantity("0.5")
        assert quantity == Decimal("0.5")

    def test_validate_quantity_too_low(self):
        """Test validation rejects quantity below minimum."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_quantity("0.00001")

    def test_validate_quantity_too_high(self):
        """Test validation rejects quantity above maximum."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_quantity("1000000001")

    def test_validate_quantity_negative(self):
        """Test validation rejects negative quantity."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_quantity("-10")

    def test_validate_symbol_valid(self):
        """Test validation of valid symbol."""
        validator = TradingValidator()

        symbol = validator.validate_symbol("AAPL")
        assert symbol == "AAPL"

    def test_validate_symbol_uppercase(self):
        """Test validation uppercases symbols."""
        validator = TradingValidator()

        symbol = validator.validate_symbol("aapl")
        assert symbol == "AAPL"

    def test_validate_symbol_with_hyphen(self):
        """Test validation of symbol with hyphen."""
        validator = TradingValidator()

        symbol = validator.validate_symbol("BTC-USD")
        assert symbol == "BTC-USD"

    def test_validate_symbol_too_long(self):
        """Test validation rejects overly long symbols."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_symbol("A" * 21)

    def test_validate_symbol_with_null_byte(self):
        """Test validation rejects symbols with null bytes."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_symbol("AAPL\x00")

    def test_validate_order_params_valid(self):
        """Test validation of valid order parameters."""
        validator = TradingValidator()

        params = validator.validate_order_params(
            symbol="AAPL", side="buy", quantity=100, price=150.25, order_type="limit"
        )

        assert params["symbol"] == "AAPL"
        assert params["side"] == "buy"
        assert params["quantity"] == Decimal("100")
        assert params["price"] == Decimal("150.25")
        assert params["order_type"] == "limit"

    def test_validate_order_params_invalid_side(self):
        """Test validation rejects invalid order side."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_order_params(symbol="AAPL", side="invalid", quantity=100)

    def test_validate_order_params_invalid_type(self):
        """Test validation rejects invalid order type."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_order_params(
                symbol="AAPL", side="buy", quantity=100, order_type="invalid_type"
            )

    def test_validate_portfolio_allocation_valid(self):
        """Test validation of valid portfolio allocation."""
        validator = TradingValidator()

        allocations = validator.validate_portfolio_allocation({"AAPL": 50, "MSFT": 30, "GOOGL": 20})

        assert allocations["AAPL"] == Decimal("50")
        assert allocations["MSFT"] == Decimal("30")
        assert allocations["GOOGL"] == Decimal("20")

    def test_validate_portfolio_allocation_total_not_100(self):
        """Test validation rejects allocation not totaling 100%."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_portfolio_allocation(
                {"AAPL": 50, "MSFT": 30, "GOOGL": 10}  # Total = 90
            )

    def test_validate_portfolio_allocation_negative(self):
        """Test validation rejects negative allocation."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_portfolio_allocation({"AAPL": 50, "MSFT": -10, "GOOGL": 60})

    def test_validate_portfolio_allocation_over_100(self):
        """Test validation rejects allocation over 100%."""
        validator = TradingValidator()

        with pytest.raises(ValidationError):
            validator.validate_portfolio_allocation({"AAPL": 50, "MSFT": 60})  # > 100


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_within_limit(self):
        """Test request within rate limit is allowed."""
        limiter = RateLimiter()

        allowed, info = limiter.check_rate_limit(identifier="test_user", limit=10, window=60)

        assert allowed is True
        assert info["remaining"] == 9

    def test_rate_limit_exceeded(self):
        """Test request exceeding rate limit is blocked."""
        limiter = RateLimiter()

        # Make requests up to limit
        for i in range(10):
            limiter.check_rate_limit(identifier="test_user_exceed", limit=10, window=60)

        # Next request should be blocked
        with pytest.raises(ValidationError):
            limiter.check_rate_limit(identifier="test_user_exceed", limit=10, window=60)

    def test_rate_limit_sliding_window(self):
        """Test rate limit sliding window behavior."""
        limiter = RateLimiter()

        # Make requests
        for i in range(5):
            limiter.check_rate_limit(
                identifier="test_window", limit=10, window=1  # 1 second window
            )

        # Check stats
        stats = limiter.get_usage_stats("test_window")
        assert stats["current"] == 5
        assert stats["remaining"] == 5

    def test_rate_limit_reset(self):
        """Test rate limit reset functionality."""
        limiter = RateLimiter()

        # Use up limit
        for i in range(5):
            limiter.check_rate_limit(identifier="test_reset", limit=5, window=60)

        # Reset
        limiter.reset_limit("test_reset")

        # Should be able to make requests again
        allowed, info = limiter.check_rate_limit(identifier="test_reset", limit=5, window=60)

        assert allowed is True

    def test_rate_limit_category_auth(self):
        """Test auth category rate limiting."""
        limiter = RateLimiter()

        # Auth has strict limits (5 per minute)
        for i in range(5):
            limiter.check_rate_limit(identifier="test_auth", category="auth")

        # Should be blocked
        with pytest.raises(ValidationError):
            limiter.check_rate_limit(identifier="test_auth", category="auth")

    def test_rate_limit_category_trade(self):
        """Test trade category rate limiting."""
        limiter = RateLimiter()

        # Trade has higher limits (100 per minute)
        for i in range(100):
            limiter.check_rate_limit(identifier="test_trade", category="trade")

        # Should be blocked
        with pytest.raises(ValidationError):
            limiter.check_rate_limit(identifier="test_trade", category="trade")


class TestNumericValidation:
    """Tests for numeric input validation."""

    def test_validate_decimal_valid(self):
        """Test validation of valid decimal."""
        validator = NumericValidator()

        result = validator.validate_decimal("123.456")
        assert result == Decimal("123.456")

    def test_validate_decimal_with_range(self):
        """Test validation with range constraints."""
        validator = NumericValidator()

        result = validator.validate_decimal("50", min_value=Decimal("0"), max_value=Decimal("100"))

        assert result == Decimal("50")

    def test_validate_decimal_below_minimum(self):
        """Test validation rejects value below minimum."""
        validator = NumericValidator()

        with pytest.raises(ValidationError):
            validator.validate_decimal("-10", min_value=Decimal("0"))

    def test_validate_decimal_above_maximum(self):
        """Test validation rejects value above maximum."""
        validator = NumericValidator()

        with pytest.raises(ValidationError):
            validator.validate_decimal("150", max_value=Decimal("100"))

    def test_validate_decimal_too_many_decimals(self):
        """Test validation rejects too many decimal places."""
        validator = NumericValidator()

        with pytest.raises(ValidationError):
            validator.validate_decimal("1.23456789", max_precision=4)

    def test_validate_integer_valid(self):
        """Test validation of valid integer."""
        validator = NumericValidator()

        result = validator.validate_integer("42")
        assert result == 42

    def test_validate_integer_with_range(self):
        """Test validation with range constraints."""
        validator = NumericValidator()

        result = validator.validate_integer("50", min_value=0, max_value=100)

        assert result == 50

    def test_validate_percentage_0_to_1(self):
        """Test validation of percentage in 0-1 range."""
        validator = NumericValidator()

        result = validator.validate_percentage("0.5")
        assert result == Decimal("50")

    def test_validate_percentage_0_to_100(self):
        """Test validation of percentage in 0-100 range."""
        validator = NumericValidator()

        result = validator.validate_percentage("75")
        assert result == Decimal("75")

    def test_validate_percentage_invalid(self):
        """Test validation rejects invalid percentage."""
        validator = NumericValidator()

        with pytest.raises(ValidationError):
            validator.validate_percentage("150")


class TestListValidation:
    """Tests for list input validation."""

    def test_validate_list_valid(self):
        """Test validation of valid list."""
        validator = ListValidator()

        result = validator.validate_list([1, 2, 3, 4, 5])
        assert result == [1, 2, 3, 4, 5]

    def test_validate_list_too_long(self):
        """Test validation rejects overly long list."""
        validator = ListValidator()

        with pytest.raises(ValidationError):
            validator.validate_list(list(range(1000)), max_length=100)

    def test_validate_list_with_element_type(self):
        """Test validation with element type constraint."""
        validator = ListValidator()

        result = validator.validate_list(["a", "b", "c"], element_type=str)

        assert result == ["a", "b", "c"]

    def test_validate_list_wrong_element_type(self):
        """Test validation rejects wrong element type."""
        validator = ListValidator()

        with pytest.raises(ValidationError):
            validator.validate_list([1, 2, "string"], element_type=int)

    def test_validate_symbol_list(self):
        """Test validation of symbol list."""
        validator = ListValidator()

        result = validator.validate_symbol_list(["AAPL", "MSFT", "GOOGL"])
        assert result == ["AAPL", "MSFT", "GOOGL"]


class TestDictValidation:
    """Tests for dictionary input validation."""

    def test_validate_dict_valid(self):
        """Test validation of valid dict."""
        validator = DictValidator()

        result = validator.validate_dict({"key": "value"})
        assert result == {"key": "value"}

    def test_validate_dict_too_many_keys(self):
        """Test validation rejects dict with too many keys."""
        validator = DictValidator()

        with pytest.raises(ValidationError):
            validator.validate_dict({str(i): i for i in range(200)}, max_keys=100)

    def test_validate_dict_with_types(self):
        """Test validation with key/value type constraints."""
        validator = DictValidator()

        result = validator.validate_dict({"a": 1, "b": 2}, key_type=str, value_type=int)

        assert result == {"a": 1, "b": 2}


class TestEmailValidation:
    """Tests for email validation."""

    def test_validate_email_valid(self):
        """Test validation of valid email."""
        sanitizer = InputSanitizer()

        result = sanitizer.sanitize_email("user@example.com")
        assert result == "user@example.com"

    def test_validate_email_uppercase(self):
        """Test validation lowercases email."""
        sanitizer = InputSanitizer()

        result = sanitizer.sanitize_email("USER@EXAMPLE.COM")
        assert result == "user@example.com"

    def test_validate_email_invalid_format(self):
        """Test validation rejects invalid email format."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_email("not-an-email")

    def test_validate_email_too_long(self):
        """Test validation rejects overly long email."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_email("a" * 250 + "@example.com")


class TestURLValidation:
    """Tests for URL validation."""

    def test_validate_url_valid_http(self):
        """Test validation of valid HTTP URL."""
        sanitizer = InputSanitizer()

        result = sanitizer.sanitize_url("http://example.com")
        assert result == "http://example.com"

    def test_validate_url_valid_https(self):
        """Test validation of valid HTTPS URL."""
        sanitizer = InputSanitizer()

        result = sanitizer.sanitize_url("https://example.com/path?query=value")
        assert "https://example.com" in result

    def test_validate_url_javascript_protocol(self):
        """Test validation rejects javascript: protocol."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_url("javascript:alert('XSS')")

    def test_validate_url_data_protocol(self):
        """Test validation rejects data: protocol."""
        sanitizer = InputSanitizer()

        with pytest.raises(ValidationError):
            sanitizer.sanitize_url("data:text/html,<script>alert('XSS')</script>")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
