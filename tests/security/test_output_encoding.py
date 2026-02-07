"""
Tests for app/security/output_encoding.py
"""


from app.security.output_encoding import (
    ContentSecurityPolicy,
    OutputEncoder,
    encode_for_css,
    encode_for_html,
    encode_for_html_attribute,
    encode_for_javascript,
    encode_for_url,
    safe_json_dumps,
    sanitize_output,
)


class TestOutputEncoder:
    """Test output encoding for XSS prevention."""

    def test_encode_for_html_basic(self):
        """Test basic HTML encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_html("Hello World")
        assert result == "Hello World"

    def test_encode_for_html_script_tags(self):
        """Test HTML encoding of script tags."""
        encoder = OutputEncoder()
        result = encoder.encode_for_html("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_encode_for_html_quotes(self):
        """Test HTML encoding of quotes."""
        encoder = OutputEncoder()
        result = encoder.encode_for_html('Test "quoted" text')
        assert "&quot;" in result
        assert '"' not in result or result.count('"') < 2

    def test_encode_for_html_none(self):
        """Test encoding None value."""
        encoder = OutputEncoder()
        result = encoder.encode_for_html(None)
        assert result == ""

    def test_encode_for_html_attribute(self):
        """Test HTML attribute encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_html_attribute('" onclick="alert(\'xss\')')
        assert "&quot;" in result
        assert "&#x27;" in result

    def test_encode_for_javascript_basic(self):
        """Test basic JavaScript encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_javascript("test string")
        assert result.startswith("'")
        assert result.endswith("'")

    def test_encode_for_javascript_dangerous_chars(self):
        """Test JavaScript encoding of dangerous characters."""
        encoder = OutputEncoder()
        result = encoder.encode_for_javascript("'; alert('xss'); //")
        assert "\\x27" in result  # Single quote encoded

    def test_encode_for_javascript_none(self):
        """Test encoding None as JavaScript."""
        encoder = OutputEncoder()
        result = encoder.encode_for_javascript(None)
        assert result == "null"

    def test_encode_for_javascript_number(self):
        """Test encoding number as JavaScript."""
        encoder = OutputEncoder()
        result = encoder.encode_for_javascript(42)
        assert result == "42"

    def test_encode_for_css_basic(self):
        """Test basic CSS encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_css("test-value")
        assert "test-value" in result or result == "test-value"

    def test_encode_for_css_dangerous(self):
        """Test CSS encoding of dangerous strings."""
        encoder = OutputEncoder()
        result = encoder.encode_for_css("'); background: url('evil'); //")
        assert "\\27" in result or "\\29" in result

    def test_encode_for_css_none(self):
        """Test encoding None as CSS."""
        encoder = OutputEncoder()
        result = encoder.encode_for_css(None)
        assert result == ""

    def test_encode_for_url(self):
        """Test URL encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_url("test value/slash")
        assert "test" in result
        assert "value" in result

    def test_encode_json_valid(self):
        """Test JSON encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_json({"key": "value", "number": 42})
        assert '"key": "value"' in result or '"key":"value"' in result
        assert '"number": 42' in result or '"number":42' in result

    def test_encode_xml(self):
        """Test XML encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_xml("<test>&</test>")
        assert "&lt;test&gt;&amp;&lt;/test&gt;" == result

    def test_encode_csv(self):
        """Test CSV encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_csv('value with "quotes"')
        assert '"' in result  # Should be quoted

    def test_encode_for_log(self):
        """Test log encoding."""
        encoder = OutputEncoder()
        result = encoder.encode_for_log("test@example.com")
        assert "***@***.***" in result

    def test_check_for_xss(self):
        """Test XSS pattern detection."""
        encoder = OutputEncoder()

        # Should detect XSS
        assert encoder.check_for_xss("<script>alert(1)</script>") is True
        assert encoder.check_for_xss("javascript:alert(1)") is True
        assert encoder.check_for_xss("onclick=alert(1)") is True

        # Should not detect safe content
        assert encoder.check_for_xss("safe content") is False

    def test_encode_dict(self):
        """Test dictionary encoding."""
        encoder = OutputEncoder()
        data = {"key": "<script>", "nested": {"value": "test"}}
        result = encoder.encode_dict(data, context="html")
        assert "&lt;script&gt;" in result["key"]

    def test_encode_list(self):
        """Test list encoding."""
        encoder = OutputEncoder()
        data = ["<script>", "safe", "test"]
        result = encoder.encode_list(data, context="html")
        assert "&lt;script&gt;" in result[0]


class TestContentSecurityPolicy:
    """Test CSP header generation."""

    def test_default_csp(self):
        """Test default CSP directives."""
        csp = ContentSecurityPolicy()
        header = csp.get_header_value()
        assert "default-src 'self'" in header
        assert "script-src 'self'" in header

    def test_custom_csp(self):
        """Test custom CSP directives."""
        csp = ContentSecurityPolicy(
            directives={"script-src": ["'self'", "https://cdn.example.com"]}
        )
        header = csp.get_header_value()
        assert "https://cdn.example.com" in header

    def test_add_directive(self):
        """Test adding CSP directive."""
        csp = ContentSecurityPolicy()
        csp.add_directive("img-src", "https://example.com")
        header = csp.get_header_value()
        assert "https://example.com" in header

    def test_remove_directive(self):
        """Test removing CSP directive."""
        csp = ContentSecurityPolicy()
        csp.remove_directive("script-src")
        header = csp.get_header_value()
        assert "script-src" not in header


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_encode_for_html(self):
        """Test HTML encoding function."""
        result = encode_for_html("<script>")
        assert "&lt;script&gt;" == result

    def test_encode_for_html_attribute(self):
        """Test HTML attribute encoding function."""
        result = encode_for_html_attribute('"test"')
        assert "&quot;" in result

    def test_encode_for_css(self):
        """Test CSS encoding function."""
        result = encode_for_css("test")
        assert isinstance(result, str)

    def test_encode_for_javascript(self):
        """Test JavaScript encoding function."""
        result = encode_for_javascript("test")
        assert isinstance(result, str)

    def test_encode_for_url(self):
        """Test URL encoding function."""
        result = encode_for_url("test value")
        assert "test" in result

    def test_safe_json_dumps(self):
        """Test safe JSON serialization."""
        result = safe_json_dumps({"key": "value"})
        assert '"key": "value"' in result or '"key":"value"' in result

    def test_sanitize_output_dict(self):
        """Test sanitizing dictionary output."""
        result = sanitize_output({"key": "<script>"}, context="html")
        assert "&lt;script&gt;" in result["key"]

    def test_sanitize_output_list(self):
        """Test sanitizing list output."""
        result = sanitize_output(["<script>", "safe"], context="html")
        assert "&lt;script&gt;" in result[0]

    def test_sanitize_output_string(self):
        """Test sanitizing string output."""
        result = sanitize_output("<script>", context="html")
        assert "&lt;script&gt;" == result
