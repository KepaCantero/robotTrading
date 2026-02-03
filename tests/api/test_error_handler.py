"""
Tests for API Error Handlers (API-008 Fix)

Tests the comprehensive error logging handlers that provide:
- Correlation IDs for request tracking
- Stack traces for debugging
- Request context (method, path, params)
- Proper error responses to clients
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_handler import (
    http_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
    pydantic_validation_exception_handler,
    generic_exception_handler,
    value_error_handler,
    key_error_handler,
    type_error_handler,
    attribute_error_handler,
    index_error_handler,
    log_exception_context,
)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/test/endpoint"
    request.url.query = {}
    request.path_params = {}
    request.query_params = {}
    request.client = Mock(host="127.0.0.1")
    request.headers = {"user-agent": "test-agent"}
    return request


class TestLogExceptionContext:
    """Tests for log_exception_context function."""

    @patch("app.api.error_handler.logger")
    def test_log_exception_context_basic(self, mock_logger, mock_request):
        """Test basic exception context logging."""
        exc = ValueError("Test error")

        log_exception_context(
            error_type="ValueError",
            error_message="Test error",
            request=mock_request,
            status_code=400,
            exc=exc,
        )

        # Verify logger was called with correct parameters
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "API exception: ValueError" in call_args[0][0]
        assert call_args[1]["exc_info"] == exc
        assert "correlation_id" in call_args[1]["extra"]
        assert call_args[1]["extra"]["error_type"] == "ValueError"
        assert call_args[1]["extra"]["method"] == "GET"
        assert call_args[1]["extra"]["path"] == "/test/endpoint"

    @patch("app.api.error_handler.logger")
    def test_log_exception_context_with_additional_context(self, mock_logger, mock_request):
        """Test exception logging with additional context."""
        log_exception_context(
            error_type="CustomError",
            error_message="Custom error message",
            request=mock_request,
            additional_context={"custom_field": "custom_value"},
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["extra"]["custom_field"] == "custom_value"


class TestHTTPExceptionHandler:
    """Tests for http_exception_handler."""

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_http_exception_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test HTTP exception handler logs and returns correct response."""
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(mock_request, exc)

        # Verify logging was called
        mock_log.assert_called_once()

        # Verify response
        assert response.status_code == 404
        body = response.body.decode()
        assert "Not found" in body
        assert "test-correlation-id" in body


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_validation_exception_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test validation error handler logs field-level errors."""
        errors = [
            {
                "loc": ("body", "field1"),
                "type": "value_error.missing",
                "msg": "Field required",
                "input": None,
            }
        ]
        exc = RequestValidationError(errors)

        response = await validation_exception_handler(mock_request, exc)

        # Verify logging was called with validation errors
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert "validation_errors" in call_kwargs["additional_context"]

        # Verify response
        assert response.status_code == 422
        assert "test-correlation-id" in response.body.decode()


class TestGenericExceptionHandler:
    """Tests for generic_exception_handler."""

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_generic_exception_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test generic exception handler returns safe error message."""
        exc = Exception("Internal error details that should not be exposed")

        response = await generic_exception_handler(mock_request, exc)

        # Verify logging was called
        mock_log.assert_called_once()

        # Verify response doesn't expose sensitive data
        assert response.status_code == 500
        body = response.body.decode()
        assert "Internal error details" not in body
        assert "internal server error occurred" in body.lower()
        assert "test-correlation-id" in body


class TestSpecificExceptionHandlers:
    """Tests for specific Python exception handlers."""

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_value_error_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test ValueError handler returns 400."""
        exc = ValueError("Invalid value")

        response = await value_error_handler(mock_request, exc)

        assert response.status_code == 400
        assert "test-correlation-id" in response.body.decode()

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_key_error_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test KeyError handler returns 400 with missing key."""
        exc = KeyError("missing_key")

        response = await key_error_handler(mock_request, exc)

        assert response.status_code == 400
        body = response.body.decode()
        assert "missing_key" in body or "field" in body.lower()
        assert "test-correlation-id" in body

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_type_error_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test TypeError handler returns 400."""
        exc = TypeError("Invalid type")

        response = await type_error_handler(mock_request, exc)

        assert response.status_code == 400
        assert "test-correlation-id" in response.body.decode()

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_attribute_error_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test AttributeError handler returns 500."""
        exc = AttributeError("Missing attribute")

        response = await attribute_error_handler(mock_request, exc)

        assert response.status_code == 500
        assert "test-correlation-id" in response.body.decode()

    @pytest.mark.asyncio
    @patch("app.api.error_handler.log_exception_context")
    @patch("app.api.error_handler.get_correlation_id", return_value="test-correlation-id")
    async def test_index_error_handler(self, mock_correlation_id, mock_log, mock_request):
        """Test IndexError handler returns 400."""
        exc = IndexError("Index out of range")

        response = await index_error_handler(mock_request, exc)

        assert response.status_code == 400
        assert "test-correlation-id" in response.body.decode()


@pytest.mark.integration
class TestErrorHandlerIntegration:
    """Integration tests for error handlers."""

    @pytest.mark.skip(reason="Requires TestClient fixture from conftest")
    async def test_error_handler_with_real_request(self, client):
        """Test error handlers work with real FastAPI requests."""
        # Test 404 error
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        # Test validation error
        response = client.post("/signals/evaluate", json={})
        assert response.status_code in [400, 422, 500]  # Depends on validation

        # Verify correlation ID in response
        assert "x-correlation-id" in response.headers
