"""
Tests for Code Contracts Implementation

This module tests the Design by Contract system using Pydantic
for data validation in the algorithmic trading system.

Author: AlgoTrading MVP Team
Version: 1.0.0
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.contracts import (ContractViolationError, InvariantError,
                                MarketDataContract, PositionContract,
                                PostconditionError, PreconditionError,
                                SignalContract, TechnicalIndicatorContract,
                                contract, risk_calculation, signal_analysis,
                                trading_operation, validate_batch_trading_data,
                                validate_non_zero_quantity,
                                validate_position_size,
                                validate_positive_amount, validate_profit_loss,
                                validate_reasonable_price,
                                validate_signal_confidence,
                                validate_trading_data)


class TestContractViolations:
    """Test contract violation exceptions."""

    def test_contract_violation_error(self):
        """Test ContractViolationError creation."""
        error = ContractViolationError("Test message", "TEST", "test_function")
        assert error.message == "Test message"
        assert error.contract_type == "TEST"
        assert error.function_name == "test_function"
        assert str(error) == "[TEST] test_function: Test message"

    def test_precondition_error(self):
        """Test PreconditionError creation."""
        error = PreconditionError("Precondition failed", "test_function")
        assert error.contract_type == "PRECONDITION"
        assert error.function_name == "test_function"

    def test_postcondition_error(self):
        """Test PostconditionError creation."""
        error = PostconditionError("Postcondition failed", "test_function")
        assert error.contract_type == "POSTCONDITION"
        assert error.function_name == "test_function"

    def test_invariant_error(self):
        """Test InvariantError creation."""
        error = InvariantError("Invariant failed", "test_function")
        assert error.contract_type == "INVARIANT"
        assert error.function_name == "test_function"


class TestMarketDataContract:
    """Test MarketDataContract validation."""

    def test_valid_market_data(self):
        """Test valid market data passes validation."""
        data = {
            "symbol": "AAPL",
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        contract = MarketDataContract(**data)
        assert contract.validate_trading_data() is True

    def test_invalid_symbol_lowercase(self):
        """Test lowercase symbol fails validation."""
        data = {
            "symbol": "aapl",  # lowercase
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(ValueError, match="Symbol must be uppercase"):
            MarketDataContract(**data)

    def test_invalid_symbol_characters(self):
        """Test symbol with invalid characters fails validation."""
        data = {
            "symbol": "AAPL@",  # invalid character
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(ValueError, match="Symbol contains invalid characters"):
            MarketDataContract(**data)

    def test_negative_price(self):
        """Test negative price fails validation."""
        data = {
            "symbol": "AAPL",
            "price": Decimal("-150.0"),  # negative
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(Exception, match="Input should be greater than 0"):
            MarketDataContract(**data)

    def test_excessive_price(self):
        """Test excessive price fails validation."""
        data = {
            "symbol": "AAPL",
            "price": Decimal("2000000.0"),  # > $1M
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(ValueError, match="Price exceeds maximum limit"):
            MarketDataContract(**data)

    def test_excessive_total_value(self):
        """Test excessive total value fails invariant validation."""
        data = {
            "symbol": "AAPL",
            "price": Decimal("1000.0"),
            "volume": Decimal("2000000"),  # $2B total value
            "timestamp": datetime.utcnow(),
        }
        contract = MarketDataContract(**data)
        with pytest.raises(InvariantError, match="Total value.*exceeds limit"):
            contract.validate_trading_data()


class TestSignalContract:
    """Test SignalContract validation."""

    def test_valid_signal(self):
        """Test valid signal passes validation."""
        data = {
            "signal_type": "BUY",
            "confidence": 0.8,
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        contract = SignalContract(**data)
        assert contract.validate_trading_data() is True

    def test_invalid_signal_type(self):
        """Test invalid signal type fails validation."""
        data = {
            "signal_type": "INVALID",
            "confidence": 0.8,
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        with pytest.raises(ValueError, match="String should match pattern"):
            SignalContract(**data)

    def test_invalid_confidence_range(self):
        """Test confidence outside range fails validation."""
        data = {
            "signal_type": "BUY",
            "confidence": 1.5,  # > 1.0
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        with pytest.raises(ValueError, match="Input should be less than or equal to 1"):
            SignalContract(**data)

    def test_strong_signal_low_confidence(self):
        """Test strong signal with low confidence fails invariant."""
        data = {
            "signal_type": "BUY",
            "confidence": 0.5,  # Low confidence
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        contract = SignalContract(**data)
        with pytest.raises(InvariantError, match="Strong signal with low confidence"):
            contract.validate_trading_data()

    def test_weak_signal_high_confidence(self):
        """Test weak signal with high confidence fails invariant."""
        data = {
            "signal_type": "BUY",
            "confidence": 0.9,  # High confidence
            "strength": "WEAK",
            "symbol": "AAPL",
        }
        contract = SignalContract(**data)
        with pytest.raises(InvariantError, match="Weak signal with high confidence"):
            contract.validate_trading_data()


class TestTechnicalIndicatorContract:
    """Test TechnicalIndicatorContract validation."""

    def test_valid_rsi(self):
        """Test valid RSI passes validation."""
        data = {
            "indicator_type": "RSI",
            "value": 50.0,
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
        }
        contract = TechnicalIndicatorContract(**data)
        assert contract.validate_trading_data() is True

    def test_invalid_rsi_range(self):
        """Test RSI outside valid range fails validation."""
        data = {
            "indicator_type": "RSI",
            "value": 150.0,  # > 100
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
        }
        contract = TechnicalIndicatorContract(**data)
        with pytest.raises(InvariantError, match="RSI value.*outside valid range"):
            contract.validate_trading_data()

    def test_negative_ema(self):
        """Test negative EMA fails validation."""
        data = {
            "indicator_type": "EMA",
            "value": -10.0,  # negative
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
        }
        contract = TechnicalIndicatorContract(**data)
        with pytest.raises(InvariantError, match="EMA value.*must be positive"):
            contract.validate_trading_data()

    def test_negative_atr(self):
        """Test negative ATR fails validation."""
        data = {
            "indicator_type": "ATR",
            "value": -5.0,  # negative
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
        }
        contract = TechnicalIndicatorContract(**data)
        with pytest.raises(InvariantError, match="ATR value.*must be non-negative"):
            contract.validate_trading_data()


class TestPositionContract:
    """Test PositionContract validation."""

    def test_valid_position(self):
        """Test valid position passes validation."""
        data = {
            "symbol": "AAPL",
            "quantity": Decimal("100"),
            "avg_price": Decimal("150.0"),
            "current_price": Decimal("155.0"),
        }
        contract = PositionContract(**data)
        assert contract.validate_trading_data() is True

    def test_excessive_position_value(self):
        """Test excessive position value fails validation."""
        data = {
            "symbol": "AAPL",
            "quantity": Decimal("100000"),  # $15M position
            "avg_price": Decimal("150.0"),
            "current_price": Decimal("155.0"),
        }
        contract = PositionContract(**data)
        with pytest.raises(InvariantError, match="Position value.*exceeds limit"):
            contract.validate_trading_data()

    def test_excessive_quantity(self):
        """Test excessive quantity fails validation."""
        data = {
            "symbol": "AAPL",
            "quantity": Decimal("2000000"),  # 2M shares
            "avg_price": Decimal("150.0"),
            "current_price": Decimal("155.0"),
        }
        contract = PositionContract(**data)
        with pytest.raises(InvariantError, match="Position value.*exceeds limit"):
            contract.validate_trading_data()


class TestContractDecorator:
    """Test contract decorator functionality."""

    def test_precondition_validation(self):
        """Test precondition validation."""

        @contract(preconditions=[validate_positive_amount])
        def test_function(amount: Decimal) -> Decimal:
            return amount * 2

        # Valid call
        result = test_function(Decimal("100"))
        assert result == Decimal("200")

        # Invalid call
        with pytest.raises(PreconditionError, match="Precondition failed"):
            test_function(Decimal("-100"))

    def test_postcondition_validation(self):
        """Test postcondition validation."""

        @contract(postconditions=[validate_position_size])
        def test_function(amount: Decimal) -> Decimal:
            return amount * 1000

        # Valid call
        result = test_function(Decimal("1000"))
        assert result == Decimal("1000000")

        # Invalid call (result too large)
        with pytest.raises(PostconditionError, match="Postcondition failed"):
            test_function(Decimal("20000"))  # Results in $20M

    def test_data_contract_validation(self):
        """Test data contract validation."""

        @contract(data_contract=MarketDataContract)
        def test_function(data: dict) -> dict:
            return {"processed": True, **data}

        # Valid data
        valid_data = {
            "symbol": "AAPL",
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        result = test_function(valid_data)
        assert result["processed"] is True

        # Invalid data
        invalid_data = {
            "symbol": "aapl",  # lowercase
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(ContractViolationError, match="Data validation error"):
            test_function(invalid_data)

    def test_multiple_preconditions(self):
        """Test multiple preconditions."""

        @contract(preconditions=[validate_positive_amount, validate_reasonable_price])
        def test_function(amount: Decimal, price: Decimal) -> Decimal:
            return amount * price

        # Valid call
        result = test_function(Decimal("100"), Decimal("150"))
        assert result == Decimal("15000")

        # Invalid amount
        with pytest.raises(PreconditionError):
            test_function(Decimal("-100"), Decimal("150"))

        # Invalid price
        with pytest.raises(PreconditionError):
            test_function(Decimal("100"), Decimal("2000000"))


class TestPredefinedDecorators:
    """Test predefined contract decorators."""

    def test_trading_operation_decorator(self):
        """Test trading_operation decorator."""

        @trading_operation(MarketDataContract)
        def process_trade(data: dict, amount: Decimal) -> dict:
            return {"trade_processed": True, "amount": amount}

        # Valid call
        valid_data = {
            "symbol": "AAPL",
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        result = process_trade(valid_data, Decimal("1000"))
        assert result["trade_processed"] is True

        # Invalid amount
        with pytest.raises(PreconditionError):
            process_trade(valid_data, Decimal("-1000"))

    def test_signal_analysis_decorator(self):
        """Test signal_analysis decorator."""

        @signal_analysis(SignalContract)
        def analyze_signal(signal_data: dict) -> dict:
            return {"analysis_complete": True}

        # Valid call
        valid_signal = {
            "signal_type": "BUY",
            "confidence": 0.8,
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        result = analyze_signal(valid_signal)
        assert result["analysis_complete"] is True

        # Invalid confidence
        invalid_signal = {
            "signal_type": "BUY",
            "confidence": 1.5,  # Invalid
            "strength": "STRONG",
            "symbol": "AAPL",
        }
        with pytest.raises(ContractViolationError):
            analyze_signal(invalid_signal)

    def test_risk_calculation_decorator(self):
        """Test risk_calculation decorator."""

        @risk_calculation()
        def calculate_risk(quantity: Decimal) -> Decimal:
            return quantity * Decimal("100")  # Risk calculation

        # Valid call
        result = calculate_risk(Decimal("1000"))
        assert result == Decimal("100000")

        # Invalid quantity (zero)
        with pytest.raises(PreconditionError):
            calculate_risk(Decimal("0"))


class TestValidationUtilities:
    """Test validation utility functions."""

    def test_validate_trading_data(self):
        """Test validate_trading_data utility."""
        valid_data = {
            "symbol": "AAPL",
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }

        # Valid data
        assert validate_trading_data(valid_data, MarketDataContract) is True

        # Invalid data
        invalid_data = {
            "symbol": "aapl",  # lowercase
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.utcnow(),
        }
        with pytest.raises(ContractViolationError):
            validate_trading_data(invalid_data, MarketDataContract)

    def test_validate_batch_trading_data(self):
        """Test validate_batch_trading_data utility."""
        valid_batch = [
            {
                "symbol": "AAPL",
                "price": Decimal("150.0"),
                "volume": Decimal("1000000"),
                "timestamp": datetime.utcnow(),
            },
            {
                "symbol": "MSFT",
                "price": Decimal("200.0"),
                "volume": Decimal("500000"),
                "timestamp": datetime.utcnow(),
            },
        ]

        # Valid batch
        assert validate_batch_trading_data(valid_batch, MarketDataContract) is True

        # Invalid batch
        invalid_batch = [
            {
                "symbol": "AAPL",
                "price": Decimal("150.0"),
                "volume": Decimal("1000000"),
                "timestamp": datetime.utcnow(),
            },
            {
                "symbol": "aapl",  # lowercase - invalid
                "price": Decimal("200.0"),
                "volume": Decimal("500000"),
                "timestamp": datetime.utcnow(),
            },
        ]
        with pytest.raises(ContractViolationError, match="Batch validation failed at index 1"):
            validate_batch_trading_data(invalid_batch, MarketDataContract)


class TestContractIntegration:
    """Test contract integration with existing code."""

    def test_contract_with_existing_models(self):
        """Test contracts work with existing Pydantic models."""
        # This would test integration with existing models like Position, Signal, etc.
        # For now, we'll test that contracts can be applied to simple functions

        @contract(data_contract=SignalContract)
        def process_signal(signal_data: dict) -> str:
            return f"Processed {signal_data['signal_type']} signal for {signal_data['symbol']}"

        valid_signal = {
            "signal_type": "BUY",
            "confidence": 0.8,
            "strength": "STRONG",
            "symbol": "AAPL",
        }

        result = process_signal(valid_signal)
        assert "Processed BUY signal for AAPL" in result

    def test_contract_performance(self):
        """Test that contracts don't significantly impact performance."""
        import time

        @contract(preconditions=[validate_positive_amount])
        def fast_function(amount: Decimal) -> Decimal:
            return amount * 2

        # Measure execution time
        start_time = time.time()
        for _ in range(1000):
            fast_function(Decimal("100"))
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second for 1000
        # calls)
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Contract validation too slow: {execution_time}s"
