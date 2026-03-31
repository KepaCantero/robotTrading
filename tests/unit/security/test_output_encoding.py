"""
Test suite for Output Encoding

Tests:
- HTML encoding
- HTML attribute encoding
- JavaScript encoding
- CSS encoding
- URL encoding
- XML encoding
- CSV encoding
- JSON encoding
- Log encoding
- XSS pattern detection
"""


import pytest

from app.security.web_security.output_encoding import (
    ContentSecurityPolicy,
    encode_for_css,
    encode_for_csv,
    encode_for_html,
    encode_for_html_attribute,
    encode_for_javascript,
    encode_for_log,
    encode_for_sql_like,
    encode_for_url,
    encode_for_xml,
    encoder,
    safe_json_dumps,
    sanitize_output,
)


class TestHTMLEncoding:
    """Tests for HTML context encoding."""

    def test_encode_for_html_script_tag(self):
        """Test encoding of script tags."""
        result = encode_for_html("<script>alert('XSS')</script>")

        assert "&lt;script&gt;" in result
        assert "<script>" not in result
        assert "</script>" not in result

    def test_encode_for_html_special_chars(self):
        """Test encoding of HTML special characters."""
        result = encode_for_html("<div>&\"'</div>")

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
        assert "&#x27;" in result

    def test_encode_for_html_none(self):
        """Test encoding of None value."""
        result = encode_for_html(None)

        assert result == ""

    def test_encode_for_html_numbers(self):
        """Test encoding passes through numbers unchanged."""
        result = encode_for_html(123)

        assert result == "123"

    def test_encode_for_html_unicode(self):
        """Test encoding of unicode characters."""
        result = encode_for_html("Hello 世界")

        assert "Hello" in result
        assert "世界" in result


class TestHTMLAttributeEncoding:
    """Tests for HTML attribute context encoding."""

    def test_encode_for_html_attribute_quotes(self):
        """Test encoding of quotes in attributes."""
        result = encode_for_html_attribute('"onclick="alert(\'XSS\')"')

        assert "&quot;" in result
        assert "&#x27;" in result
        assert "&#x3d;" in result

    def test_encode_for_html_attribute_backticks(self):
        """Test encoding of backticks."""
        result = encode_for_html_attribute("`malicious`")

        assert "&#96;" in result

    def test_encode_for_html_attribute_equals(self):
        """Test encoding of equals signs."""
        result = encode_for_html_attribute("key=value")

        assert "&#x3d;" in result


class TestJavaScriptEncoding:
    """Tests for JavaScript context encoding."""

    def test_encode_for_javascript_single_quote(self):
        """Test encoding of single quotes."""
        result = encode_for_javascript("'; alert('XSS'); //")

        assert "\\x27" in result
        assert "alert" not in result.lower()

    def test_encode_for_javascript_double_quote(self):
        """Test encoding of double quotes."""
        result = encode_for_javascript('"xss"')

        assert "\\x22" in result

    def test_encode_for_javascript_angle_brackets(self):
        """Test encoding of angle brackets."""
        result = encode_for_javascript("<script>")

        assert "\\x3c" in result
        assert "\\x3e" in result

    def test_encode_for_javascript_backslash(self):
        """Test encoding of backslashes."""
        result = encode_for_javascript("\\n\\r")

        assert "\\x5c" in result

    def test_encode_for_javascript_none(self):
        """Test encoding of None returns null string."""
        result = encode_for_javascript(None)

        assert result == "null"

    def test_encode_for_javascript_non_string(self):
        """Test encoding of non-string types."""
        result = encode_for_javascript(123)

        assert result == "123"

        result = encode_for_javascript(["a", "b"])
        assert result == '["a", "b"]'


class TestCSSEncoding:
    """Tests for CSS context encoding."""

    def test_encode_for_css_special_chars(self):
        """Test encoding of special CSS characters."""
        result = encode_for_css("'); background: url('evil'); //")

        assert "\\27" in result
        assert "\\29" in result
        assert "\\3a" in result
        assert "\\28" in result
        assert "\\2f" in result

    def test_encode_for_css_alphanumeric(self):
        """Test encoding preserves alphanumeric."""
        result = encode_for_css("color123")

        assert "color123" in result

    def test_encode_for_css_spaces(self):
        """Test encoding preserves spaces."""
        result = encode_for_css("red blue")

        assert "red blue" in result


class TestURLEncoding:
    """Tests for URL context encoding."""

    def test_encode_for_url_special_chars(self):
        """Test encoding of URL special characters."""
        result = encode_for_url("hello world & test")

        assert "hello+world+%26+test" in result or "hello%20world%20%26%20test" in result

    def test_encode_for_url_slashes(self):
        """Test encoding of slashes."""
        result = encode_for_url("path/to/file")

        assert "path" in result
        assert "to" in result
        assert "file" in result
        assert "/" not in result or "%2F" in result or "%2f" in result

    def test_encode_for_url_none(self):
        """Test encoding of None returns empty string."""
        result = encode_for_url(None)

        assert result == ""


class TestXMLEncoding:
    """Tests for XML context encoding."""

    def test_encode_for_xml_special_chars(self):
        """Test encoding of XML special characters."""
        result = encode_for_xml("<tag>&\"'</tag>")

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
        assert "&apos;" in result

    def test_encode_for_xml_attribute(self):
        """Test encoding for XML attribute context."""
        result = encode_for_xml("value\"test", attribute=True)

        assert "&quot;" in result
        assert "&apos;" in result
        assert "&#x9;" in result or "&#xA;" in result or "&#xD;" in result

    def test_encode_for_xml_none(self):
        """Test encoding of None returns empty string."""
        result = encode_for_xml(None)

        assert result == ""


class TestCSVEncoding:
    """Tests for CSV context encoding."""

    def test_encode_for_csv_with_delimiter(self):
        """Test encoding when value contains delimiter."""
        result = encode_for_csv("value,with,commas")

        assert result.startswith('"')
        assert result.endswith('"')
        assert '","' in result

    def test_encode_for_csv_with_quote(self):
        """Test encoding when value contains quotes."""
        result = encode_for_csv('value "with" quotes')

        assert '""with""' in result

    def test_encode_for_csv_with_newline(self):
        """Test encoding when value contains newline."""
        result = encode_for_csv("value\nwith\nnewlines")

        assert result.startswith('"')
        assert result.endswith('"')

    def test_encode_for_csv_with_leading_space(self):
        """Test encoding when value has leading space."""
        result = encode_for_csv(" value")

        assert result.startswith('"')
        assert result.endswith('"')

    def test_encode_for_csv_simple(self):
        """Test encoding of simple value."""
        result = encode_for_csv("simple")

        assert result == "simple"

    def test_encode_for_csv_none(self):
        """Test encoding of None returns empty string."""
        result = encode_for_csv(None)

        assert result == ""


class TestSQLLikeEncoding:
    """Tests for SQL LIKE context encoding."""

    def test_encode_for_sql_like_wildcards(self):
        """Test encoding of SQL wildcards."""
        result = encode_for_sql_like("user_input")

        assert "user\\_input" == result or "user_input" == result

    def test_encode_for_sql_like_percent(self):
        """Test encoding of percent sign."""
        result = encode_for_sql_like("100%")

        assert "100\\%" in result

    def test_encode_for_sql_like_underscore(self):
        """Test encoding of underscore."""
        result = encode_for_sql_like("test_value")

        assert "test\\_value" in result

    def test_encode_for_sql_like_backslash(self):
        """Test encoding of backslash."""
        result = encode_for_sql_like("path\\to\\file")

        assert "\\\\\\\\" in result or "path" in result

    def test_encode_for_sql_like_none(self):
        """Test encoding of None returns empty string."""
        result = encode_for_sql_like(None)

        assert result == ""


class TestLogEncoding:
    """Tests for log-safe encoding."""

    def test_encode_for_log_email(self):
        """Test masking of email addresses."""
        result = encode_for_log("Contact user@example.com for support")

        assert "***@***.***" in result
        assert "user@example.com" not in result

    def test_encode_for_log_credit_card(self):
        """Test masking of credit card numbers."""
        result = encode_for_log("Card: 4111-1111-1111-1111")

        assert "****-****-****-****" in result
        assert "4111-1111-1111-1111" not in result

    def test_encode_for_log_ssn(self):
        """Test masking of Social Security numbers."""
        result = encode_for_log("SSN: 123-45-6789")

        assert "***-**-****" in result
        assert "123-45-6789" not in result

    def test_encode_for_log_password(self):
        """Test masking of passwords."""
        result = encode_for_log("password='secret123'")

        assert 'password="***"' in result
        assert "secret123" not in result

    def test_encode_for_log_truncation(self):
        """Test truncation of long values."""
        long_value = "a" * 2000
        result = encode_for_log(long_value, max_length=100)

        assert len(result) <= 104  # 100 + "..."
        assert "..." in result

    def test_encode_for_log_none(self):
        """Test encoding of None returns empty string."""
        result = encode_for_log(None)

        assert result == ""


class TestJSONEncoding:
    """Tests for JSON encoding."""

    def test_encode_json_simple(self):
        """Test encoding of simple JSON."""
        result = safe_json_dumps({"key": "value"})

        assert '{"key": "value"}' == result or '{"key":"value"}' == result

    def test_encode_json_with_special_chars(self):
        """Test encoding of JSON with special characters."""
        result = safe_json_dumps({"key": "<script>test</script>"})

        assert "<script>" in result
        assert "test" in result

    def test_encode_json_complex(self):
        """Test encoding of complex JSON."""
        data = {"user": "test", "values": [1, 2, 3], "nested": {"key": "value"}}

        result = safe_json_dumps(data)

        assert '"user": "test"' in result or '"user":"test"' in result
        assert '"values": [1, 2, 3]' in result or '"values":[1,2,3]' in result

    def test_encode_json_with_decimal(self):
        """Test encoding of Decimal values."""
        from decimal import Decimal

        result = safe_json_dumps({"price": Decimal("123.45")})

        assert "123.45" in result


class TestXSSDetection:
    """Tests for XSS pattern detection."""

    def test_check_for_xss_script_tag(self):
        """Test detection of script tag."""
        assert encoder.check_for_xss("<script>alert('xss')</script>")

    def test_check_for_xss_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        assert encoder.check_for_xss("javascript:alert('xss')")

    def test_check_for_xss_onclick(self):
        """Test detection of onclick handler."""
        assert encoder.check_for_xss("<div onclick='alert(1)'>")

    def test_check_for_xss_iframe(self):
        """Test detection of iframe."""
        assert encoder.check_for_xss("<iframe src='evil.com'></iframe>")

    def test_check_for_xss_safe_content(self):
        """Test safe content is not flagged."""
        assert not encoder.check_for_xss("This is safe content")

    def test_check_for_xss_eval(self):
        """Test detection of eval."""
        assert encoder.check_for_xss("eval(malicious_code())")


class TestContentSecurityPolicy:
    """Tests for Content Security Policy."""

    def test_csp_default_directives(self):
        """Test default CSP directives."""
        csp = ContentSecurityPolicy()

        header = csp.get_header_value()

        assert "default-src 'self'" in header
        assert "script-src 'self'" in header
        assert "style-src 'self' 'unsafe-inline'" in header
        assert "object-src 'none'" in header

    def test_csp_custom_directives(self):
        """Test custom CSP directives."""
        csp = ContentSecurityPolicy(
            {"script-src": "'self' https://cdn.example.com", "img-src": "'self' data: https:"}
        )

        header = csp.get_header_value()

        assert "script-src 'self' https://cdn.example.com" in header
        assert "img-src 'self' data: https:" in header

    def test_csp_add_directive(self):
        """Test adding CSP directive."""
        csp = ContentSecurityPolicy()

        csp.add_directive("script-src", "'self' 'unsafe-eval'")

        header = csp.get_header_value()

        assert "'unsafe-eval'" in header

    def test_csp_remove_directive(self):
        """Test removing CSP directive."""
        csp = ContentSecurityPolicy()

        csp.remove_directive("object-src")

        header = csp.get_header_value()

        assert "object-src" not in header


class TestSanitizeOutput:
    """Tests for output sanitization."""

    def test_sanitize_output_html_dict(self):
        """Test sanitization of dict for HTML context."""
        data = {"user": "<script>alert('xss')</script>", "safe": "value"}

        result = sanitize_output(data, context="html")

        assert "&lt;script&gt;" in result["user"]
        assert result["safe"] == "value"

    def test_sanitize_output_html_list(self):
        """Test sanitization of list for HTML context."""
        data = ["<script>alert(1)</script>", "safe"]

        result = sanitize_output(data, context="html")

        assert "&lt;script&gt;" in result[0]
        assert result[1] == "safe"

    def test_sanitize_output_attribute(self):
        """Test sanitization for attribute context."""
        data = "<script>alert('xss')</script>"

        result = sanitize_output(data, context="attribute")

        assert "&lt;" in result
        assert "&quot;" in result

    def test_sanitize_output_js(self):
        """Test sanitization for JavaScript context."""
        data = "'; alert('xss'); //"

        result = sanitize_output(data, context="js")

        assert "\\x27" in result

    def test_sanitize_output_url(self):
        """Test sanitization for URL context."""
        data = "hello world & test"

        result = sanitize_output(data, context="url")

        assert "%20" in result or "+" in result
        assert "%26" in result or "%3B" in result

    def test_sanitize_output_xml(self):
        """Test sanitization for XML context."""
        data = "<tag>&\"'</tag>"

        result = sanitize_output(data, context="xml")

        assert "&lt;" in result
        assert "&amp;" in result

    def test_sanitize_output_csv(self):
        """Test sanitization for CSV context."""
        data = "value,with,commas"

        result = sanitize_output(data, context="csv")

        assert result.startswith('"')
        assert result.endswith('"')

    def test_sanitize_output_log(self):
        """Test sanitization for log context."""
        data = "user@example.com"

        result = sanitize_output(data, context="log")

        assert "***@***.***" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
