"""
Tests for Error Handling System
TASK-4: Sistema de manejo de errores unificado
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from app.exceptions.trading_exceptions import (
    AlgoTradingError,
    ValidationError,
    BusinessLogicError,
    ExternalAPIError,
    DatabaseError,
    NetworkError,
    ConfigurationError,
    SecurityError,
    PerformanceError,
    SystemError,
    ErrorSeverity,
    ErrorCategory,
    TradingError,
    SignalError,
    PortfolioError,
    RiskManagementError,
    MarketDataError,
    BrokerError
)
from app.exceptions.error_handler import (
    ErrorHandler,
    error_handler,
    create_error_response,
    raise_validation_error,
    raise_business_logic_error,
    raise_external_api_error,
    raise_database_error,
    raise_configuration_error
)
from app.exceptions import setup_error_handling, create_error_handling_app


class TestTradingExceptions:
    """Tests for trading exceptions."""

    def test_algotrading_error_creation(self):
        """Test AlgoTradingError creation."""
        error = AlgoTradingError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={"test": "data"}
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details == {"test": "data"}

    def test_algotrading_error_to_dict(self):
        """Test AlgoTradingError to_dict method."""
        error = AlgoTradingError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={"test": "data"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "business_logic"
        assert error_dict["severity"] == "medium"
        assert error_dict["details"] == {"test": "data"}

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(
            message="Invalid input",
            field="price",
            value="invalid",
            details={"expected": "number"}
        )
        
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.details["field"] == "price"
        assert error.details["value"] == "invalid"

    def test_business_logic_error(self):
        """Test BusinessLogicError."""
        error = BusinessLogicError(
            message="Insufficient funds",
            operation="buy_order",
            details={"required": 1000, "available": 500}
        )
        
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details["operation"] == "buy_order"

    def test_external_api_error(self):
        """Test ExternalAPIError."""
        error = ExternalAPIError(
            message="API request failed",
            api_name="market_data",
            status_code=500,
            details={"endpoint": "/quotes"}
        )
        
        assert error.category == ErrorCategory.EXTERNAL_API
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["api_name"] == "market_data"
        assert error.details["status_code"] == 500

    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError(
            message="Connection failed",
            operation="insert",
            table="trades",
            details={"connection_string": "postgresql://..."}
        )
        
        assert error.category == ErrorCategory.DATABASE
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["operation"] == "insert"
        assert error.details["table"] == "trades"

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError(
            message="Connection timeout",
            endpoint="https://api.example.com",
            timeout=30.0,
            details={"retry_count": 3}
        )
        
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["endpoint"] == "https://api.example.com"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError(
            message="Missing required config",
            config_key="API_KEY",
            details={"file": "config.yaml"}
        )
        
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.details["config_key"] == "API_KEY"

    def test_security_error(self):
        """Test SecurityError."""
        error = SecurityError(
            message="Unauthorized access",
            violation_type="invalid_token",
            details={"ip": "192.168.1.1"}
        )
        
        assert error.category == ErrorCategory.SECURITY
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.details["violation_type"] == "invalid_token"

    def test_performance_error(self):
        """Test PerformanceError."""
        error = PerformanceError(
            message="Operation too slow",
            operation="data_processing",
            duration=10.5,
            threshold=5.0,
            details={"records_processed": 10000}
        )
        
        assert error.category == ErrorCategory.PERFORMANCE
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details["operation"] == "data_processing"

    def test_system_error(self):
        """Test SystemError."""
        error = SystemError(
            message="System failure",
            component="memory_manager",
            details={"memory_usage": "95%"}
        )
        
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.details["component"] == "memory_manager"

    def test_trading_error(self):
        """Test TradingError."""
        error = TradingError(
            message="Order rejected",
            symbol="AAPL",
            operation="buy",
            details={"reason": "insufficient_funds"}
        )
        
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.details["symbol"] == "AAPL"
        assert error.details["operation"] == "buy"

    def test_signal_error(self):
        """Test SignalError."""
        error = SignalError(
            message="Signal generation failed",
            signal_type="BUY",
            strategy="momentum",
            details={"reason": "insufficient_data"}
        )
        
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.details["signal_type"] == "BUY"
        assert error.details["strategy"] == "momentum"

    def test_portfolio_error(self):
        """Test PortfolioError."""
        error = PortfolioError(
            message="Portfolio update failed",
            operation="rebalance",
            portfolio_id="portfolio_1",
            details={"reason": "invalid_allocation"}
        )
        
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.details["operation"] == "rebalance"
        assert error.details["portfolio_id"] == "portfolio_1"

    def test_risk_management_error(self):
        """Test RiskManagementError."""
        error = RiskManagementError(
            message="Risk limit exceeded",
            risk_type="position_size",
            limit=0.1,
            current_value=0.15,
            details={"symbol": "AAPL"}
        )
        
        assert error.category == ErrorCategory.BUSINESS_LOGIC
        assert error.details["risk_type"] == "position_size"
        assert error.details["limit"] == 0.1

    def test_market_data_error(self):
        """Test MarketDataError."""
        error = MarketDataError(
            message="Data unavailable",
            symbol="AAPL",
            data_type="quotes",
            details={"provider": "yahoo"}
        )
        
        assert error.category == ErrorCategory.EXTERNAL_API
        assert error.details["symbol"] == "AAPL"
        assert error.details["data_type"] == "quotes"

    def test_broker_error(self):
        """Test BrokerError."""
        error = BrokerError(
            message="Order execution failed",
            broker="interactive_brokers",
            operation="place_order",
            order_id="order_123",
            details={"reason": "market_closed"}
        )
        
        assert error.category == ErrorCategory.EXTERNAL_API
        assert error.details["broker"] == "interactive_brokers"
        assert error.details["operation"] == "place_order"


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()

    def test_handle_algotrading_error(self, handler):
        """Test handling AlgoTradingError."""
        error = AlgoTradingError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM
        )
        
        response = handler.handle_algotrading_error(error)
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "TEST_ERROR" in content
        assert "Test error" in content

    def test_handle_validation_error(self, handler):
        """Test handling validation error."""
        error = RequestValidationError([{"type": "missing", "loc": ["body", "price"]}])
        
        response = handler.handle_validation_error(error)
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "validation" in content.lower()

    def test_handle_http_exception(self, handler):
        """Test handling HTTP exception."""
        error = HTTPException(status_code=404, detail="Not found")
        
        response = handler.handle_http_exception(error)
        
        assert response.status_code == 404
        content = response.body.decode()
        assert "Not found" in content

    def test_handle_generic_exception(self, handler):
        """Test handling generic exception."""
        error = ValueError("Generic error")
        
        response = handler.handle_generic_exception(error)
        
        assert response.status_code == 500
        content = response.body.decode()
        assert "unexpected error" in content.lower()

    def test_get_http_status_code(self, handler):
        """Test HTTP status code mapping."""
        assert handler._get_http_status_code(ErrorSeverity.LOW) == 400
        assert handler._get_http_status_code(ErrorSeverity.MEDIUM) == 400
        assert handler._get_http_status_code(ErrorSeverity.HIGH) == 500
        assert handler._get_http_status_code(ErrorSeverity.CRITICAL) == 500

    def test_get_log_level(self, handler):
        """Test log level mapping."""
        from app.services.centralized_logging import LogLevel
        
        assert handler._get_log_level(ErrorSeverity.LOW) == LogLevel.INFO
        assert handler._get_log_level(ErrorSeverity.MEDIUM) == LogLevel.WARNING
        assert handler._get_log_level(ErrorSeverity.HIGH) == LogLevel.ERROR
        assert handler._get_log_level(ErrorSeverity.CRITICAL) == LogLevel.CRITICAL


class TestErrorResponseTemplates:
    """Tests for error response templates."""

    def test_create_error_response(self):
        """Test create_error_response function."""
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test error",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={"test": "data"},
            status_code=400
        )
        
        assert response.status_code == 400
        content = response.body.decode()
        assert "TEST_ERROR" in content
        assert "Test error" in content

    def test_raise_validation_error(self):
        """Test raise_validation_error function."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("Invalid input", "price", "invalid")
        
        assert exc_info.value.message == "Invalid input"
        assert exc_info.value.details["field"] == "price"

    def test_raise_business_logic_error(self):
        """Test raise_business_logic_error function."""
        with pytest.raises(BusinessLogicError) as exc_info:
            raise_business_logic_error("Business rule violated", "order_validation")
        
        assert exc_info.value.message == "Business rule violated"
        assert exc_info.value.details["operation"] == "order_validation"

    def test_raise_external_api_error(self):
        """Test raise_external_api_error function."""
        with pytest.raises(ExternalAPIError) as exc_info:
            raise_external_api_error("API failed", "market_data", 500)
        
        assert exc_info.value.message == "API failed"
        assert exc_info.value.details["api_name"] == "market_data"

    def test_raise_database_error(self):
        """Test raise_database_error function."""
        with pytest.raises(DatabaseError) as exc_info:
            raise_database_error("DB failed", "insert", "trades")
        
        assert exc_info.value.message == "DB failed"
        assert exc_info.value.details["operation"] == "insert"

    def test_raise_configuration_error(self):
        """Test raise_configuration_error function."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise_configuration_error("Config missing", "API_KEY")
        
        assert exc_info.value.message == "Config missing"
        assert exc_info.value.details["config_key"] == "API_KEY"


class TestFastAPIIntegration:
    """Tests for FastAPI integration."""

    def test_create_error_handling_app(self):
        """Test creating FastAPI app with error handling."""
        app = create_error_handling_app()
        
        assert app is not None
        assert len(app.exception_handlers) > 0

    def test_error_handling_in_fastapi(self):
        """Test error handling in FastAPI app."""
        app = FastAPI()
        setup_error_handling(app)
        
        @app.get("/test-error")
        def test_error():
            raise AlgoTradingError(
                message="Test error",
                error_code="TEST_ERROR",
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.MEDIUM
            )
        
        client = TestClient(app)
        response = client.get("/test-error")
        
        assert response.status_code == 400
        assert "TEST_ERROR" in response.json()["error"]["code"]

    def test_validation_error_in_fastapi(self):
        """Test validation error handling in FastAPI."""
        app = FastAPI()
        setup_error_handling(app)
        
        @app.post("/test-validation")
        def test_validation(data: dict):
            return data
        
        client = TestClient(app)
        response = client.post("/test-validation", json={"invalid": "data"})
        
        # Should not raise exception, FastAPI handles validation
        assert response.status_code in [200, 422]

    def test_http_exception_in_fastapi(self):
        """Test HTTP exception handling in FastAPI."""
        app = FastAPI()
        setup_error_handling(app)
        
        @app.get("/test-http-error")
        def test_http_error():
            raise HTTPException(status_code=404, detail="Not found")
        
        client = TestClient(app)
        response = client.get("/test-http-error")
        
        assert response.status_code == 404
        assert "Not found" in response.json()["error"]["message"]

    def test_generic_exception_in_fastapi(self):
        """Test generic exception handling in FastAPI."""
        app = FastAPI()
        setup_error_handling(app)
        
        @app.get("/test-generic-error")
        def test_generic_error():
            raise ValueError("Generic error")
        
        client = TestClient(app)
        response = client.get("/test-generic-error")
        
        assert response.status_code == 500
        assert "unexpected error" in response.json()["error"]["message"].lower()


class TestErrorSeverityEnum:
    """Tests for ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorCategoryEnum:
    """Tests for ErrorCategory enum."""

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.BUSINESS_LOGIC.value == "business_logic"
        assert ErrorCategory.EXTERNAL_API.value == "external_api"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.SECURITY.value == "security"
        assert ErrorCategory.PERFORMANCE.value == "performance"
        assert ErrorCategory.SYSTEM.value == "system"
