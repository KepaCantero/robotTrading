"""
Tests for app.core.exceptions

Test suite for core exception classes and helper functions.
"""

import pytest

from app.core.exceptions import (
    # Exception classes
    AlgoTradingError,
    ConfigurationError,
    ValidationError,
    BusinessLogicError,
    MarketDataError,
    TradingError,
    PortfolioError,
    SignalError,
    BacktestError,
    AlgoTradingDatabaseError,
    APIError,
    AuthenticationError,
    # Helper functions
    raise_configuration_error,
    raise_validation_error,
    raise_business_logic_error,
    raise_market_data_error,
    raise_trading_error,
    raise_database_error,
    raise_authentication_error,
)


class TestAlgoTradingError:
    """Test suite for the base AlgoTradingError class."""

    def test_instantiation_with_message_only(self) -> None:
        """Test that AlgoTradingError can be instantiated with just a message."""
        # Arrange
        message = "Test error message"

        # Act
        error = AlgoTradingError(message)

        # Assert
        assert error.message == message
        assert str(error) == message
        assert error.error_code is None
        assert error.details == {}

    def test_instantiation_with_error_code(self) -> None:
        """Test that AlgoTradingError can be instantiated with error code."""
        # Arrange
        message = "Test error message"
        error_code = "TEST_001"

        # Act
        error = AlgoTradingError(message, error_code=error_code)

        # Assert
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == {}

    def test_instantiation_with_details(self) -> None:
        """Test that AlgoTradingError can be instantiated with details."""
        # Arrange
        message = "Test error message"
        details = {"key": "value", "number": 42}

        # Act
        error = AlgoTradingError(message, details=details)

        # Assert
        assert error.message == message
        assert error.error_code is None
        assert error.details == details

    def test_instantiation_with_all_parameters(self) -> None:
        """Test that AlgoTradingError can be instantiated with all parameters."""
        # Arrange
        message = "Test error message"
        error_code = "TEST_001"
        details = {"key": "value"}

        # Act
        error = AlgoTradingError(message, error_code=error_code, details=details)

        # Assert
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == details

    def test_empty_details_defaults_to_empty_dict(self) -> None:
        """Test that None details defaults to empty dict."""
        # Arrange
        message = "Test error message"

        # Act
        error = AlgoTradingError(message, details=None)

        # Assert
        assert error.details == {}
        assert isinstance(error.details, dict)


class TestConcreteExceptionClasses:
    """Test suite for concrete exception classes."""

    def test_configuration_error_exists(self) -> None:
        """Test that ConfigurationError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = ConfigurationError("Config error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, ConfigurationError)
        assert error.message == "Config error"

    def test_validation_error_exists(self) -> None:
        """Test that ValidationError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = ValidationError("Validation error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, ValidationError)
        assert error.message == "Validation error"

    def test_business_logic_error_exists(self) -> None:
        """Test that BusinessLogicError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = BusinessLogicError("Business logic error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, BusinessLogicError)
        assert error.message == "Business logic error"

    def test_market_data_error_exists(self) -> None:
        """Test that MarketDataError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = MarketDataError("Market data error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, MarketDataError)
        assert error.message == "Market data error"

    def test_trading_error_exists(self) -> None:
        """Test that TradingError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = TradingError("Trading error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, TradingError)
        assert error.message == "Trading error"

    def test_portfolio_error_exists(self) -> None:
        """Test that PortfolioError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = PortfolioError("Portfolio error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, PortfolioError)
        assert error.message == "Portfolio error"

    def test_signal_error_exists(self) -> None:
        """Test that SignalError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = SignalError("Signal error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, SignalError)
        assert error.message == "Signal error"

    def test_backtest_error_exists(self) -> None:
        """Test that BacktestError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = BacktestError("Backtest error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, BacktestError)
        assert error.message == "Backtest error"

    def test_algo_trading_database_error_exists(self) -> None:
        """Test that AlgoTradingDatabaseError exists (not DatabaseError)."""
        # Arrange & Act
        error = AlgoTradingDatabaseError("Database error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, AlgoTradingDatabaseError)
        assert error.message == "Database error"
        # Verify it's NOT named DatabaseError (P0 fix)
        assert type(error).__name__ == "AlgoTradingDatabaseError"

    def test_database_error_has_correct_class_name(self) -> None:
        """Test that DatabaseError was renamed to AlgoTradingDatabaseError."""
        # This is a P0 fix test to ensure no name shadowing
        # Arrange & Act
        error = AlgoTradingDatabaseError("DB connection failed")

        # Assert
        assert error.__class__.__name__ == "AlgoTradingDatabaseError"
        # Ensure we can catch it specifically
        assert isinstance(error, AlgoTradingDatabaseError)

    def test_api_error_exists(self) -> None:
        """Test that APIError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = APIError("API error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, APIError)
        assert error.message == "API error"

    def test_authentication_error_exists(self) -> None:
        """Test that AuthenticationError class exists and inherits from AlgoTradingError."""
        # Arrange & Act
        error = AuthenticationError("Authentication error")

        # Assert
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, AuthenticationError)
        assert error.message == "Authentication error"

    def test_all_exceptions_support_error_codes(self) -> None:
        """Test that all exception classes support error codes."""
        # Arrange
        error_code = "ERR_001"

        # Act & Assert
        exceptions = [
            ConfigurationError("msg", error_code=error_code),
            ValidationError("msg", error_code=error_code),
            BusinessLogicError("msg", error_code=error_code),
            MarketDataError("msg", error_code=error_code),
            TradingError("msg", error_code=error_code),
            PortfolioError("msg", error_code=error_code),
            SignalError("msg", error_code=error_code),
            BacktestError("msg", error_code=error_code),
            AlgoTradingDatabaseError("msg", error_code=error_code),
            APIError("msg", error_code=error_code),
            AuthenticationError("msg", error_code=error_code),
        ]

        for error in exceptions:
            assert error.error_code == error_code

    def test_all_exceptions_support_details(self) -> None:
        """Test that all exception classes support details."""
        # Arrange
        details = {"field": "value", "status": 42}

        # Act & Assert
        exceptions = [
            ConfigurationError("msg", details=details),
            ValidationError("msg", details=details),
            BusinessLogicError("msg", details=details),
            MarketDataError("msg", details=details),
            TradingError("msg", details=details),
            PortfolioError("msg", details=details),
            SignalError("msg", details=details),
            BacktestError("msg", details=details),
            AlgoTradingDatabaseError("msg", details=details),
            APIError("msg", details=details),
            AuthenticationError("msg", details=details),
        ]

        for error in exceptions:
            assert error.details == details


class TestRaiseConfigurationError:
    """Test suite for raise_configuration_error helper function."""

    def test_raises_configuration_error_with_valid_message(self) -> None:
        """Test that raise_configuration_error raises ConfigurationError."""
        # Arrange
        message = "Configuration file not found"

        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            raise_configuration_error(message)

        assert exc_info.value.message == message
        assert exc_info.value.error_code is None
        assert exc_info.value.details == {}

    def test_raises_configuration_error_with_error_code(self) -> None:
        """Test that raise_configuration_error includes error code."""
        # Arrange
        message = "Invalid configuration"
        error_code = "CONFIG_001"

        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            raise_configuration_error(message, error_code=error_code)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code

    def test_raises_configuration_error_with_details(self) -> None:
        """Test that raise_configuration_error includes details."""
        # Arrange
        message = "Configuration validation failed"
        details = {"missing_key": "api_key", "path": "/config.yaml"}

        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            raise_configuration_error(message, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_configuration_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_configuration_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_configuration_error validates whitespace-only input."""
        # Arrange
        message = "   "

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_configuration_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_none_message(self) -> None:
        """Test that raise_configuration_error validates None input."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_configuration_error(None)  # type: ignore

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseValidationError:
    """Test suite for raise_validation_error helper function."""

    def test_raises_validation_error_with_valid_message(self) -> None:
        """Test that raise_validation_error raises ValidationError."""
        # Arrange
        message = "Invalid input data"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error(message)

        assert exc_info.value.message == message

    def test_raises_validation_error_with_error_code(self) -> None:
        """Test that raise_validation_error includes error code."""
        # Arrange
        message = "Validation failed"
        error_code = "VAL_001"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error(message, error_code=error_code)

        assert exc_info.value.error_code == error_code

    def test_raises_validation_error_with_details(self) -> None:
        """Test that raise_validation_error includes details."""
        # Arrange
        message = "Schema validation failed"
        details = {"field": "email", "reason": "invalid format"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error(message, details=details)

        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_validation_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_validation_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_validation_error validates whitespace-only input."""
        # Arrange
        message = "\t\n"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_validation_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseBusinessLogicError:
    """Test suite for raise_business_logic_error helper function."""

    def test_raises_business_logic_error_with_valid_message(self) -> None:
        """Test that raise_business_logic_error raises BusinessLogicError."""
        # Arrange
        message = "Insufficient capital"

        # Act & Assert
        with pytest.raises(BusinessLogicError) as exc_info:
            raise_business_logic_error(message)

        assert exc_info.value.message == message

    def test_raises_business_logic_error_with_all_parameters(self) -> None:
        """Test that raise_business_logic_error supports all parameters."""
        # Arrange
        message = "Position size exceeds limit"
        error_code = "BUS_001"
        details = {"max_size": 1000, "requested": 1500}

        # Act & Assert
        with pytest.raises(BusinessLogicError) as exc_info:
            raise_business_logic_error(message, error_code=error_code, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_business_logic_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_business_logic_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_business_logic_error validates whitespace-only input."""
        # Arrange
        message = "   "

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_business_logic_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseMarketDataError:
    """Test suite for raise_market_data_error helper function."""

    def test_raises_market_data_error_with_valid_message(self) -> None:
        """Test that raise_market_data_error raises MarketDataError."""
        # Arrange
        message = "No data available for symbol"

        # Act & Assert
        with pytest.raises(MarketDataError) as exc_info:
            raise_market_data_error(message)

        assert exc_info.value.message == message

    def test_raises_market_data_error_with_all_parameters(self) -> None:
        """Test that raise_market_data_error supports all parameters."""
        # Arrange
        message = "Data feed disconnected"
        error_code = "MD_001"
        details = {"provider": "yahoo", "retry_after": 60}

        # Act & Assert
        with pytest.raises(MarketDataError) as exc_info:
            raise_market_data_error(message, error_code=error_code, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_market_data_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_market_data_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_market_data_error validates whitespace-only input."""
        # Arrange
        message = "\t  \n"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_market_data_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseTradingError:
    """Test suite for raise_trading_error helper function."""

    def test_raises_trading_error_with_valid_message(self) -> None:
        """Test that raise_trading_error raises TradingError."""
        # Arrange
        message = "Order execution failed"

        # Act & Assert
        with pytest.raises(TradingError) as exc_info:
            raise_trading_error(message)

        assert exc_info.value.message == message

    def test_raises_trading_error_with_all_parameters(self) -> None:
        """Test that raise_trading_error supports all parameters."""
        # Arrange
        message = "Order rejected by exchange"
        error_code = "TRD_001"
        details = {"order_id": "12345", "reason": "insufficient margin"}

        # Act & Assert
        with pytest.raises(TradingError) as exc_info:
            raise_trading_error(message, error_code=error_code, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_trading_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_trading_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_trading_error validates whitespace-only input."""
        # Arrange
        message = "   "

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_trading_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseDatabaseError:
    """Test suite for raise_database_error helper function."""

    def test_raises_database_error_with_valid_message(self) -> None:
        """Test that raise_database_error raises AlgoTradingDatabaseError."""
        # Arrange
        message = "Connection to database failed"

        # Act & Assert
        with pytest.raises(AlgoTradingDatabaseError) as exc_info:
            raise_database_error(message)

        assert exc_info.value.message == message

    def test_raises_algo_trading_database_error_not_generic_database_error(
        self,
    ) -> None:
        """Test that raise_database_error raises AlgoTradingDatabaseError (P0 fix)."""
        # This ensures the renamed exception is used
        # Arrange
        message = "Database connection failed"

        # Act & Assert
        with pytest.raises(AlgoTradingDatabaseError) as exc_info:
            raise_database_error(message)

        # Verify it's specifically AlgoTradingDatabaseError
        assert type(exc_info.value).__name__ == "AlgoTradingDatabaseError"

    def test_raises_database_error_with_all_parameters(self) -> None:
        """Test that raise_database_error supports all parameters."""
        # Arrange
        message = "Query execution failed"
        error_code = "DB_001"
        details = {"query": "SELECT * FROM table", "sql_code": "42P01"}

        # Act & Assert
        with pytest.raises(AlgoTradingDatabaseError) as exc_info:
            raise_database_error(message, error_code=error_code, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_database_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_database_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_database_error validates whitespace-only input."""
        # Arrange
        message = "   "

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_database_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestRaiseAuthenticationError:
    """Test suite for raise_authentication_error helper function."""

    def test_raises_authentication_error_with_valid_message(self) -> None:
        """Test that raise_authentication_error raises AuthenticationError."""
        # Arrange
        message = "Invalid credentials"

        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            raise_authentication_error(message)

        assert exc_info.value.message == message

    def test_raises_authentication_error_with_all_parameters(self) -> None:
        """Test that raise_authentication_error supports all parameters."""
        # Arrange
        message = "Token expired"
        error_code = "AUTH_001"
        details = {"token": "***", "expired_at": "2024-01-01T00:00:00Z"}

        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            raise_authentication_error(message, error_code=error_code, details=details)

        assert exc_info.value.message == message
        assert exc_info.value.error_code == error_code
        assert exc_info.value.details == details

    def test_raises_value_error_for_empty_message(self) -> None:
        """Test that raise_authentication_error validates input (P0 fix)."""
        # Arrange
        message = ""

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_authentication_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)

    def test_raises_value_error_for_whitespace_only_message(self) -> None:
        """Test that raise_authentication_error validates whitespace-only input."""
        # Arrange
        message = "\t\n  "

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            raise_authentication_error(message)

        assert "message must be a non-empty string" in str(exc_info.value)


class TestExceptionCatching:
    """Test suite for exception catching behavior."""

    def test_catch_all_via_base_exception(self) -> None:
        """Test that all specific exceptions can be caught via AlgoTradingError."""
        # Arrange
        exceptions = [
            ConfigurationError("msg"),
            ValidationError("msg"),
            BusinessLogicError("msg"),
            MarketDataError("msg"),
            TradingError("msg"),
            PortfolioError("msg"),
            SignalError("msg"),
            BacktestError("msg"),
            AlgoTradingDatabaseError("msg"),
            APIError("msg"),
            AuthenticationError("msg"),
        ]

        # Act & Assert
        for exc in exceptions:
            assert isinstance(exc, AlgoTradingError)

    def test_catch_specific_exception_type(self) -> None:
        """Test that specific exceptions maintain their type for catching."""
        # Arrange & Act
        error = AlgoTradingDatabaseError("Specific database error")

        # Assert - should be catchable by specific type
        caught = False
        try:
            raise error
        except AlgoTradingDatabaseError:
            caught = True

        assert caught

    def test_exception_inheritance_chain(self) -> None:
        """Test the full exception inheritance chain."""
        # Arrange & Act
        error = AlgoTradingDatabaseError("Test")

        # Assert
        assert isinstance(error, AlgoTradingDatabaseError)
        assert isinstance(error, AlgoTradingError)
        assert isinstance(error, Exception)  # Python base exception


class TestExceptionAttributes:
    """Test suite for exception attribute access."""

    def test_exception_attributes_are_accessible(self) -> None:
        """Test that all exception attributes are accessible."""
        # Arrange
        message = "Test message"
        error_code = "TEST_001"
        details = {"key": "value"}

        # Act
        error = AlgoTradingDatabaseError(message, error_code=error_code, details=details)

        # Assert
        assert hasattr(error, "message")
        assert hasattr(error, "error_code")
        assert hasattr(error, "details")
        assert error.message == message
        assert error.error_code == error_code
        assert error.details == details

    def test_exception_str_representation(self) -> None:
        """Test string representation of exceptions."""
        # Arrange
        message = "Error message"

        # Act
        error = TradingError(message)

        # Assert
        assert str(error) == message
        assert repr(error) == f"TradingError('{message}')"

    def test_exception_with_nested_details(self) -> None:
        """Test exceptions with nested dictionary details."""
        # Arrange
        message = "Complex error"
        details = {
            "level1": {"level2": {"level3": "deep value"}},
            "list": [1, 2, 3],
            "mixed": [{"key": "value"}, "string"],
        }

        # Act
        error = ValidationError(message, details=details)

        # Assert
        assert error.details == details
        assert error.details["level1"]["level2"]["level3"] == "deep value"
        assert error.details["list"] == [1, 2, 3]


class TestInputValidationEdgeCases:
    """Test suite for input validation edge cases (P0 fixes)."""

    @pytest.mark.parametrize(
        "message",
        [
            "",  # Empty string
            " ",  # Single space
            "\t",  # Tab
            "\n",  # Newline
            "\r",  # Carriage return
            "   \t\n   ",  # Mixed whitespace
            "\u200B",  # Zero-width space
            "\uFEFF",  # Zero-width non-breaking space
        ],
    )
    def test_all_helper_functions_reject_invalid_messages(self, message: str) -> None:
        """Test that all helper functions reject various invalid message formats."""
        # Arrange
        helper_functions = [
            raise_configuration_error,
            raise_validation_error,
            raise_business_logic_error,
            raise_market_data_error,
            raise_trading_error,
            raise_database_error,
            raise_authentication_error,
        ]

        # Act & Assert
        for helper_func in helper_functions:
            with pytest.raises(ValueError, match="message must be a non-empty string"):
                helper_func(message)  # type: ignore

    def test_valid_messages_with_special_characters(self) -> None:
        """Test that valid messages with special characters are accepted."""
        # Arrange
        valid_messages = [
            "Error: Test @#$%",
            "Multi\nLine\nMessage",
            "Message with emoji: 🚀",
            "Message with quotes: 'single' and \"double\"",
            "Message with unicode: Café",
        ]

        # Act & Assert
        for message in valid_messages:
            # Should not raise ValueError
            try:
                raise_configuration_error(message)
            except ConfigurationError:
                pass  # Expected
            except ValueError as e:
                pytest.fail(f"Valid message was rejected: {message} - {e}")
