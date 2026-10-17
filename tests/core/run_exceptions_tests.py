#!/usr/bin/env python3
"""
Simple test runner for test_exceptions.py when pytest is not available.
This script runs the tests manually to verify coverage.
"""

import importlib.util
import os
import sys
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Direct import of exceptions module bypassing app/__init__.py
spec = importlib.util.spec_from_file_location(
    "app.core.exceptions", "/Users/kepa.cantero/Projects/algoTrading/app/core/exceptions.py"
)
exceptions_module = importlib.util.module_from_spec(spec)
sys.modules['app.core.exceptions'] = exceptions_module
spec.loader.exec_module(exceptions_module)

# Import test classes from the loaded module
AlgoTradingError = exceptions_module.AlgoTradingError
ConfigurationError = exceptions_module.ConfigurationError
ValidationError = exceptions_module.ValidationError
BusinessLogicError = exceptions_module.BusinessLogicError
MarketDataError = exceptions_module.MarketDataError
TradingError = exceptions_module.TradingError
PortfolioError = exceptions_module.PortfolioError
SignalError = exceptions_module.SignalError
BacktestError = exceptions_module.BacktestError
AlgoTradingDatabaseError = exceptions_module.AlgoTradingDatabaseError
APIError = exceptions_module.APIError
AuthenticationError = exceptions_module.AuthenticationError
raise_configuration_error = exceptions_module.raise_configuration_error
raise_validation_error = exceptions_module.raise_validation_error
raise_business_logic_error = exceptions_module.raise_business_logic_error
raise_market_data_error = exceptions_module.raise_market_data_error
raise_trading_error = exceptions_module.raise_trading_error
raise_database_error = exceptions_module.raise_database_error
raise_authentication_error = exceptions_module.raise_authentication_error


class TestRunner:
    """Simple test runner."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_test(self, test_name: str, test_func):
        """Run a single test function."""
        try:
            test_func()
            self.passed += 1
            print(f"✓ {test_name}")
            return True
        except AssertionError as e:
            self.failed += 1
            self.errors.append((test_name, str(e)))
            print(f"✗ {test_name}: {e}")
            return False
        except Exception as e:
            self.failed += 1
            self.errors.append((test_name, traceback.format_exc()))
            print(f"✗ {test_name}: {type(e).__name__}: {e}")
            return False

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}")
                print(f"    {error[:200]}...")
        print("=" * 60)
        return self.failed == 0


# Test functions
def test_algo_trading_database_error_exists():
    """Test that AlgoTradingDatabaseError exists (P0 fix)."""
    assert hasattr(exceptions_module, 'AlgoTradingDatabaseError')
    error = AlgoTradingDatabaseError("test")
    assert error.__class__.__name__ == "AlgoTradingDatabaseError"


def test_configuration_error_validation_empty():
    """Test that raise_configuration_error validates empty input (P0 fix)."""
    try:
        raise_configuration_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_configuration_error_validation_whitespace():
    """Test that raise_configuration_error validates whitespace input."""
    try:
        raise_configuration_error("   ")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_validation_error_validation_empty():
    """Test that raise_validation_error validates empty input (P0 fix)."""
    try:
        raise_validation_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_business_logic_error_validation_empty():
    """Test that raise_business_logic_error validates empty input (P0 fix)."""
    try:
        raise_business_logic_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_market_data_error_validation_empty():
    """Test that raise_market_data_error validates empty input (P0 fix)."""
    try:
        raise_market_data_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_trading_error_validation_empty():
    """Test that raise_trading_error validates empty input (P0 fix)."""
    try:
        raise_trading_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_database_error_validation_empty():
    """Test that raise_database_error validates empty input (P0 fix)."""
    try:
        raise_database_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_database_error_raises_algo_trading_database_error():
    """Test that raise_database_error raises AlgoTradingDatabaseError (P0 fix)."""
    try:
        raise_database_error("Database error")
        assert False, "Should have raised AlgoTradingDatabaseError"
    except AlgoTradingDatabaseError as e:
        assert e.message == "Database error"
        assert e.__class__.__name__ == "AlgoTradingDatabaseError"


def test_authentication_error_validation_empty():
    """Test that raise_authentication_error validates empty input (P0 fix)."""
    try:
        raise_authentication_error("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "message must be a non-empty string" in str(e)


def test_all_helper_functions_validate_input():
    """Test that all helper functions validate input (P0 fix)."""
    # Use the module's functions directly
    helper_functions = [
        ('raise_configuration_error', exceptions_module.raise_configuration_error),
        ('raise_validation_error', exceptions_module.raise_validation_error),
        ('raise_business_logic_error', exceptions_module.raise_business_logic_error),
        ('raise_market_data_error', exceptions_module.raise_market_data_error),
        ('raise_trading_error', exceptions_module.raise_trading_error),
        ('raise_database_error', exceptions_module.raise_database_error),
        ('raise_authentication_error', exceptions_module.raise_authentication_error),
    ]

    for name, func in helper_functions:
        try:
            func("   ")  # whitespace only
            assert False, f"{name} should validate input"
        except ValueError:
            pass  # Expected


def test_all_exception_classes_exist():
    """Test that all exception classes exist."""
    expected_classes = [
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
    ]

    for cls in expected_classes:
        assert cls is not None
        assert issubclass(cls, AlgoTradingError) or cls is AlgoTradingError


def test_exceptions_support_error_codes():
    """Test that all exceptions support error codes."""
    error_code = "TEST_001"

    exceptions_list = [
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

    for error in exceptions_list:
        assert error.error_code == error_code


def test_exceptions_support_details():
    """Test that all exceptions support details."""
    details = {"key": "value"}

    exceptions_list = [
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

    for error in exceptions_list:
        assert error.details == details


def test_exceptions_can_be_caught_by_base_type():
    """Test that all exceptions can be caught by AlgoTradingError."""
    exceptions_list = [
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

    for error in exceptions_list:
        assert isinstance(error, AlgoTradingError)


def test_exception_inheritance():
    """Test exception inheritance chain."""
    error = AlgoTradingDatabaseError("test")
    assert isinstance(error, AlgoTradingDatabaseError)
    assert isinstance(error, AlgoTradingError)
    assert isinstance(error, Exception)


def test_exception_attributes():
    """Test that exception attributes are accessible."""
    message = "Test message"
    error_code = "TEST_001"
    details = {"key": "value"}

    error = AlgoTradingDatabaseError(message, error_code=error_code, details=details)

    assert error.message == message
    assert error.error_code == error_code
    assert error.details == details


def test_exception_str_representation():
    """Test string representation of exceptions."""
    message = "Error message"
    error = TradingError(message)
    assert str(error) == message


def test_raise_configuration_error_with_all_params():
    """Test raise_configuration_error with all parameters."""
    try:
        raise_configuration_error("msg", error_code="C001", details={"key": "value"})
    except ConfigurationError as e:
        assert e.message == "msg"
        assert e.error_code == "C001"
        assert e.details == {"key": "value"}


def test_raise_validation_error_with_all_params():
    """Test raise_validation_error with all parameters."""
    try:
        raise_validation_error("msg", error_code="V001", details={"field": "email"})
    except ValidationError as e:
        assert e.message == "msg"
        assert e.error_code == "V001"
        assert e.details == {"field": "email"}


def test_raise_business_logic_error_with_all_params():
    """Test raise_business_logic_error with all parameters."""
    try:
        raise_business_logic_error("msg", error_code="B001", details={"capital": 1000})
    except BusinessLogicError as e:
        assert e.message == "msg"
        assert e.error_code == "B001"
        assert e.details == {"capital": 1000}


def test_raise_market_data_error_with_all_params():
    """Test raise_market_data_error with all parameters."""
    try:
        raise_market_data_error("msg", error_code="M001", details={"symbol": "AAPL"})
    except MarketDataError as e:
        assert e.message == "msg"
        assert e.error_code == "M001"
        assert e.details == {"symbol": "AAPL"}


def test_raise_trading_error_with_all_params():
    """Test raise_trading_error with all parameters."""
    try:
        raise_trading_error("msg", error_code="T001", details={"order_id": "123"})
    except TradingError as e:
        assert e.message == "msg"
        assert e.error_code == "T001"
        assert e.details == {"order_id": "123"}


def test_raise_database_error_with_all_params():
    """Test raise_database_error with all parameters."""
    try:
        raise_database_error("msg", error_code="D001", details={"query": "SELECT"})
    except AlgoTradingDatabaseError as e:
        assert e.message == "msg"
        assert e.error_code == "D001"
        assert e.details == {"query": "SELECT"}


def test_raise_authentication_error_with_all_params():
    """Test raise_authentication_error with all parameters."""
    try:
        raise_authentication_error("msg", error_code="A001", details={"user": "test"})
    except AuthenticationError as e:
        assert e.message == "msg"
        assert e.error_code == "A001"
        assert e.details == {"user": "test"}


def test_empty_details_defaults_to_empty_dict():
    """Test that None details defaults to empty dict."""
    error = ConfigurationError("msg", details=None)
    assert error.details == {}
    assert isinstance(error.details, dict)


# Run all tests
def main():
    """Run all tests."""
    runner = TestRunner()

    tests = [
        # P0 Critical Tests
        ("AlgoTradingDatabaseError exists (P0)", test_algo_trading_database_error_exists),
        (
            "ConfigurationError validates empty input (P0)",
            test_configuration_error_validation_empty,
        ),
        (
            "ConfigurationError validates whitespace (P0)",
            test_configuration_error_validation_whitespace,
        ),
        ("ValidationError validates empty input (P0)", test_validation_error_validation_empty),
        (
            "BusinessLogicError validates empty input (P0)",
            test_business_logic_error_validation_empty,
        ),
        ("MarketDataError validates empty input (P0)", test_market_data_error_validation_empty),
        ("TradingError validates empty input (P0)", test_trading_error_validation_empty),
        ("DatabaseError validates empty input (P0)", test_database_error_validation_empty),
        (
            "DatabaseError raises AlgoTradingDatabaseError (P0)",
            test_database_error_raises_algo_trading_database_error,
        ),
        (
            "AuthenticationError validates empty input (P0)",
            test_authentication_error_validation_empty,
        ),
        ("All helper functions validate input (P0)", test_all_helper_functions_validate_input),
        # Core Tests
        ("All exception classes exist", test_all_exception_classes_exist),
        ("Exceptions support error codes", test_exceptions_support_error_codes),
        ("Exceptions support details", test_exceptions_support_details),
        ("Exceptions can be caught by base type", test_exceptions_can_be_caught_by_base_type),
        ("Exception inheritance", test_exception_inheritance),
        ("Exception attributes", test_exception_attributes),
        ("Exception string representation", test_exception_str_representation),
        # Helper Function Tests
        (
            "raise_configuration_error with all params",
            test_raise_configuration_error_with_all_params,
        ),
        ("raise_validation_error with all params", test_raise_validation_error_with_all_params),
        (
            "raise_business_logic_error with all params",
            test_raise_business_logic_error_with_all_params,
        ),
        ("raise_market_data_error with all params", test_raise_market_data_error_with_all_params),
        ("raise_trading_error with all params", test_raise_trading_error_with_all_params),
        ("raise_database_error with all params", test_raise_database_error_with_all_params),
        (
            "raise_authentication_error with all params",
            test_raise_authentication_error_with_all_params,
        ),
        # Edge Cases
        ("Empty details defaults to empty dict", test_empty_details_defaults_to_empty_dict),
    ]

    print("Running tests for app.core.exceptions...\n")

    for test_name, test_func in tests:
        runner.run_test(test_name, test_func)

    success = runner.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
