"""
Tests for app/security/security_headers.py
"""

from unittest.mock import Mock

import pytest

from app.security.web_security.security_headers import (
    ContentSecurityPolicy,
    HSTSHeader,
    PermissionsPolicy,
    ReferrerPolicy,
    SecurityHeadersMiddleware,
    XFrameOptions,
    add_security_headers,
    get_security_headers,
)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    def test_initialization(self):
        """Test middleware initialization."""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        assert middleware.enable_hsts is True
        assert middleware.enable_csp is True
        assert middleware.enable_frame_options is True

    def test_add_security_headers(self):
        """Test adding security headers to response."""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)

        request = Mock()
        request.url.scheme = "https"

        response = Mock()
        response.headers = {}

        middleware._add_security_headers(request, response)

        # Check headers were added
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_hsts_https_only(self):
        """Test HSTS only added for HTTPS."""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_hsts=True)

        # HTTP request - no HSTS
        request_http = Mock()
        request_http.url.scheme = "http"
        response_http = Mock()
        response_http.headers = {}
        middleware._add_security_headers(request_http, response_http)
        assert "Strict-Transport-Security" not in response_http.headers

        # HTTPS request - HSTS added
        request_https = Mock()
        request_https.url.scheme = "https"
        response_https = Mock()
        response_https.headers = {}
        middleware._add_security_headers(request_https, response_https)
        assert "Strict-Transport-Security" in response_https.headers

    def test_disable_csp(self):
        """Test disabling CSP."""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_csp=False)

        request = Mock()
        request.url.scheme = "https"
        response = Mock()
        response.headers = {}

        middleware._add_security_headers(request, response)
        assert "Content-Security-Policy" not in response.headers


class TestContentSecurityPolicy:
    """Test CSP header generation."""

    def test_default_csp(self):
        """Test default CSP directives."""
        csp = ContentSecurityPolicy()
        header = csp.get_header_value()
        assert "default-src 'self'" in header
        assert "script-src 'self'" in header
        assert "object-src 'none'" in header

    def test_custom_csp(self):
        """Test custom CSP directives."""
        custom = {
            "script-src": ["'self'", "https://cdn.example.com"],
            "img-src": ["'self'", "data:", "https:"],
        }
        csp = ContentSecurityPolicy(directives=custom)
        header = csp.get_header_value()
        assert "https://cdn.example.com" in header

    def test_add_directive(self):
        """Test adding CSP directive."""
        csp = ContentSecurityPolicy()
        csp.add_directive("script-src", "https://cdn.example.com", "https://api.example.com")
        header = csp.get_header_value()
        assert "https://cdn.example.com" in header

    def test_remove_directive(self):
        """Test removing CSP directive."""
        csp = ContentSecurityPolicy()
        csp.remove_directive("script-src")
        header = csp.get_header_value()
        assert "script-src" not in header

    def test_set_report_only(self):
        """Test setting report-only mode."""
        csp = ContentSecurityPolicy()
        csp.set_report_only("https://example.com/csp-report")
        header = csp.get_header_value()
        assert "report-uri" in header or "report-to" in header

    def test_allow_source(self):
        """Test allowing specific source."""
        csp = ContentSecurityPolicy()
        csp.allow_source("script-src", "https://cdn.example.com")
        header = csp.get_header_value()
        assert "https://cdn.example.com" in header

    def test_enable_strict_mode(self):
        """Test enabling strict CSP mode."""
        csp = ContentSecurityPolicy()
        csp.enable_strict_mode()
        header = csp.get_header_value()
        assert "script-src 'self'" in header
        assert "style-src 'self'" in header


class TestHSTSHeader:
    """Test HSTS header generation."""

    def test_default_hsts(self):
        """Test default HSTS configuration."""
        hsts = HSTSHeader()
        header = hsts.get_header_value()
        assert "max-age=31536000" in header
        assert "includeSubDomains" in header
        assert "preload" in header

    def test_custom_max_age(self):
        """Test custom max age."""
        hsts = HSTSHeader(max_age=86400)  # 1 day
        header = hsts.get_header_value()
        assert "max-age=86400" in header

    def test_no_subdomains(self):
        """Test without subdomains."""
        hsts = HSTSHeader(include_subdomains=False)
        header = hsts.get_header_value()
        assert "includeSubDomains" not in header

    def test_no_preload(self):
        """Test without preload."""
        hsts = HSTSHeader(preload=False)
        header = hsts.get_header_value()
        assert "preload" not in header


class TestXFrameOptions:
    """Test X-Frame-Options header."""

    def test_default_deny(self):
        """Test default DENY value."""
        xfo = XFrameOptions()
        header = xfo.get_header_value()
        assert header == "DENY"

    def test_sameorigin(self):
        """Test SAMEORIGIN value."""
        xfo = XFrameOptions(value="SAMEORIGIN")
        header = xfo.get_header_value()
        assert header == "SAMEORIGIN"

    def test_invalid_value(self):
        """Test invalid value raises error."""
        with pytest.raises(ValueError):
            XFrameOptions(value="INVALID")


class TestReferrerPolicy:
    """Test Referrer-Policy header."""

    def test_default_policy(self):
        """Test default policy."""
        policy = ReferrerPolicy()
        header = policy.get_header_value()
        assert "strict-origin-when-cross-origin" in header

    def test_no_referrer(self):
        """Test no-referrer policy."""
        policy = ReferrerPolicy(policy="no-referrer")
        header = policy.get_header_value()
        assert header == "no-referrer"

    def test_invalid_policy(self):
        """Test invalid policy raises error."""
        with pytest.raises(ValueError):
            ReferrerPolicy(policy="invalid-policy")


class TestPermissionsPolicy:
    """Test Permissions-Policy header."""

    def test_default_permissions(self):
        """Test default permissions."""
        pp = PermissionsPolicy()
        header = pp.get_header_value()
        assert "geolocation=()" in header
        assert "microphone=()" in header

    def test_custom_permissions(self):
        """Test custom permissions."""
        custom = {
            "geolocation": ["https://example.com"],
            "camera": [],
        }
        pp = PermissionsPolicy(permissions=custom)
        header = pp.get_header_value()
        assert "https://example.com" in header

    def test_allow_feature(self):
        """Test allowing a feature."""
        pp = PermissionsPolicy()
        pp.allow("geolocation", "https://example.com")
        header = pp.get_header_value()
        assert "https://example.com" in header

    def test_deny_feature(self):
        """Test denying a feature."""
        pp = PermissionsPolicy()
        pp.deny("geolocation")
        header = pp.get_header_value()
        assert "geolocation=()" in header


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_security_headers(self):
        """Test getting default security headers."""
        headers = get_security_headers()
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

    def test_add_security_headers_to_response(self):
        """Test adding security headers to response."""
        response = Mock()
        response.headers = {}
        response.request = Mock()
        response.request.url.scheme = "https"

        add_security_headers(response)

        # Check headers were added
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
