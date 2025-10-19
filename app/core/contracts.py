"""
Code Contracts Implementation for AlgoTrading MVP

This module implements Design by Contract using Pydantic for data validation
before critical operations in the algorithmic trading system.

Author: AlgoTrading MVP Team
Version: 1.0.0
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError, field_validator
import logging

logger = logging.getLogger(__name__)


class ContractViolationError(Exception):
    """Raised when a code contract is violated."""
    
    def __init__(self, message: str, contract_type: str, function_name: str):
        self.message = message
        self.contract_type = contract_type
        self.function_name = function_name
        super().__init__(f"[{contract_type}] {function_name}: {message}")


class PreconditionError(ContractViolationError):
    """Raised when a precondition contract is violated."""
    
    def __init__(self, message: str, function_name: str):
        super().__init__(message, "PRECONDITION", function_name)


class PostconditionError(ContractViolationError):
    """Raised when a postcondition contract is violated."""
    
    def __init__(self, message: str, function_name: str):
        super().__init__(message, "POSTCONDITION", function_name)


class InvariantError(ContractViolationError):
    """Raised when an invariant contract is violated."""
    
    def __init__(self, message: str, function_name: str):
        super().__init__(message, "INVARIANT", function_name)


class TradingDataContract(BaseModel):
    """Base contract for trading data validation."""
    
    def validate_trading_data(self) -> bool:
        """Validate trading-specific invariants."""
        return True


class MarketDataContract(TradingDataContract):
    """Contract for market data validation."""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    price: Decimal = Field(..., gt=0)
    volume: Decimal = Field(..., ge=0)
    timestamp: datetime = Field(...)
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol format."""
        if not v.isupper():
            raise ValueError("Symbol must be uppercase")
        if not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Symbol contains invalid characters")
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price is reasonable."""
        if v <= 0:
            raise ValueError("Price must be positive")
        if v > Decimal('1000000'):  # $1M per share limit
            raise ValueError("Price exceeds maximum limit")
        return v
    
    def validate_trading_data(self) -> bool:
        """Validate market data invariants."""
        # Price should be reasonable relative to volume
        if self.price * self.volume > Decimal('1000000000'):  # $1B total value limit
            raise InvariantError(
                f"Total value {self.price * self.volume} exceeds limit",
                "MarketDataContract"
            )
        return True


class SignalContract(TradingDataContract):
    """Contract for trading signal validation."""
    
    signal_type: str = Field(..., pattern="^(BUY|SELL|HOLD)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    strength: str = Field(..., pattern="^(WEAK|MEDIUM|STRONG)$")
    symbol: str = Field(..., min_length=1, max_length=20)
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is reasonable."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def validate_trading_data(self) -> bool:
        """Validate signal invariants."""
        # Strong signals should have high confidence
        if self.strength == "STRONG" and self.confidence < 0.7:
            raise InvariantError(
                f"Strong signal with low confidence {self.confidence}",
                "SignalContract"
            )
        
        # Weak signals should have low confidence
        if self.strength == "WEAK" and self.confidence > 0.8:
            raise InvariantError(
                f"Weak signal with high confidence {self.confidence}",
                "SignalContract"
            )
        
        return True


class TechnicalIndicatorContract(TradingDataContract):
    """Contract for technical indicator validation."""
    
    indicator_type: str = Field(..., pattern="^(RSI|EMA|MACD|ATR|VOLUME_SMA)$")
    value: float = Field(...)
    symbol: str = Field(..., min_length=1, max_length=20)
    timestamp: datetime = Field(...)
    
    def validate_trading_data(self) -> bool:
        """Validate technical indicator invariants."""
        if self.indicator_type == "RSI":
            if not (0 <= self.value <= 100):
                raise InvariantError(
                    f"RSI value {self.value} outside valid range [0, 100]",
                    "TechnicalIndicatorContract"
                )
        
        elif self.indicator_type == "EMA":
            if self.value <= 0:
                raise InvariantError(
                    f"EMA value {self.value} must be positive",
                    "TechnicalIndicatorContract"
                )
        
        elif self.indicator_type == "ATR":
            if self.value < 0:
                raise InvariantError(
                    f"ATR value {self.value} must be non-negative",
                    "TechnicalIndicatorContract"
                )
        
        return True


class PositionContract(TradingDataContract):
    """Contract for position validation."""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: Decimal = Field(...)
    avg_price: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    
    def validate_trading_data(self) -> bool:
        """Validate position invariants."""
        # Position value should be reasonable
        position_value = abs(self.quantity * self.avg_price)
        if position_value > Decimal('10000000'):  # $10M position limit
            raise InvariantError(
                f"Position value {position_value} exceeds limit",
                "PositionContract"
            )
        
        # Quantity should be reasonable
        if abs(self.quantity) > Decimal('1000000'):  # 1M shares limit
            raise InvariantError(
                f"Position quantity {self.quantity} exceeds limit",
                "PositionContract"
            )
        
        return True


def contract(
    preconditions: Optional[List[Callable]] = None,
    postconditions: Optional[List[Callable]] = None,
    invariants: Optional[List[Callable]] = None,
    data_contract: Optional[Type[TradingDataContract]] = None
):
    """
    Decorator for implementing Design by Contract.
    
    Args:
        preconditions: List of functions to validate before execution
        postconditions: List of functions to validate after execution
        invariants: List of functions to validate object state
        data_contract: Pydantic model for data validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__name__}"
            
            # Validate preconditions
            if preconditions:
                for precondition in preconditions:
                    try:
                        if not precondition(*args, **kwargs):
                            raise PreconditionError(
                                f"Precondition failed: {precondition.__name__}",
                                function_name
                            )
                    except Exception as e:
                        raise PreconditionError(
                            f"Precondition error: {str(e)}",
                            function_name
                        )
            
            # Validate data contract if provided
            if data_contract:
                try:
                    # Extract data from args/kwargs for validation
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    # Find data parameters
                    for param_name, param_value in bound_args.arguments.items():
                        if isinstance(param_value, dict):
                            # Try to create contract instance
                            contract_instance = data_contract(**param_value)
                            if not contract_instance.validate_trading_data():
                                raise ContractViolationError(
                                    "Data contract validation failed",
                                    "DATA_CONTRACT",
                                    function_name
                                )
                        elif isinstance(param_value, (list, tuple)):
                            # Validate list of data
                            for item in param_value:
                                if isinstance(item, dict):
                                    contract_instance = data_contract(**item)
                                    if not contract_instance.validate_trading_data():
                                        raise ContractViolationError(
                                            "Data contract validation failed",
                                            "DATA_CONTRACT",
                                            function_name
                                        )
                
                except ValidationError as e:
                    raise ContractViolationError(
                        f"Data validation error: {str(e)}",
                        "DATA_CONTRACT",
                        function_name
                    )
            
            # Execute function
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Function {function_name} failed: {str(e)}")
                raise
            
            # Validate postconditions
            if postconditions:
                for postcondition in postconditions:
                    try:
                        if not postcondition(result, *args, **kwargs):
                            raise PostconditionError(
                                f"Postcondition failed: {postcondition.__name__}",
                                function_name
                            )
                    except Exception as e:
                        raise PostconditionError(
                            f"Postcondition error: {str(e)}",
                            function_name
                        )
            
            return result
        
        return wrapper
    return decorator


# Predefined contract validators for common trading operations

def validate_positive_amount(*args, **kwargs) -> bool:
    """Precondition: Amount must be positive."""
    # Look for Decimal arguments
    for arg in args:
        if isinstance(arg, Decimal):
            return arg > 0
    return True


def validate_non_zero_quantity(*args, **kwargs) -> bool:
    """Precondition: Quantity must be non-zero."""
    # Look for Decimal arguments
    for arg in args:
        if isinstance(arg, Decimal):
            return arg != 0
    return True


def validate_reasonable_price(*args, **kwargs) -> bool:
    """Precondition: Price must be reasonable."""
    # Look for Decimal arguments
    for arg in args:
        if isinstance(arg, Decimal):
            if not (Decimal('0.01') <= arg <= Decimal('1000000')):
                return False
    return True


def validate_signal_confidence(*args, **kwargs) -> bool:
    """Precondition: Signal confidence must be valid."""
    # Look for float arguments or dict with confidence
    for arg in args:
        if isinstance(arg, float):
            return 0.0 <= arg <= 1.0
        elif isinstance(arg, dict) and 'confidence' in arg:
            return 0.0 <= arg['confidence'] <= 1.0
    return True


def validate_position_size(result, *args, **kwargs) -> bool:
    """Postcondition: Position size must be reasonable."""
    if isinstance(result, Decimal):
        return result <= Decimal('10000000')  # $10M limit
    return True


def validate_profit_loss(result, *args, **kwargs) -> bool:
    """Postcondition: P&L should be reasonable."""
    if isinstance(result, Decimal):
        return abs(result) <= Decimal('100000000')  # $100M limit
    return True


# Example usage decorators for common patterns

def trading_operation(data_contract: Type[TradingDataContract]):
    """Decorator for trading operations with data validation."""
    return contract(
        preconditions=[validate_positive_amount],
        data_contract=data_contract,
        postconditions=[validate_position_size]
    )


def signal_analysis(data_contract: Type[TradingDataContract]):
    """Decorator for signal analysis operations."""
    return contract(
        preconditions=[validate_signal_confidence],
        data_contract=data_contract
    )


def risk_calculation():
    """Decorator for risk calculation operations."""
    return contract(
        preconditions=[validate_non_zero_quantity],
        postconditions=[validate_profit_loss]
    )


# Contract validation utilities

def validate_trading_data(data: Dict[str, Any], contract_type: Type[TradingDataContract]) -> bool:
    """
    Validate trading data against a contract.
    
    Args:
        data: Data dictionary to validate
        contract_type: Contract class to validate against
        
    Returns:
        True if validation passes
        
    Raises:
        ContractViolationError: If validation fails
    """
    try:
        contract_instance = contract_type(**data)
        return contract_instance.validate_trading_data()
    except ValidationError as e:
        raise ContractViolationError(
            f"Data validation failed: {str(e)}",
            "DATA_VALIDATION",
            "validate_trading_data"
        )


def validate_batch_trading_data(
    data_list: List[Dict[str, Any]], 
    contract_type: Type[TradingDataContract]
) -> bool:
    """
    Validate a batch of trading data against a contract.
    
    Args:
        data_list: List of data dictionaries to validate
        contract_type: Contract class to validate against
        
    Returns:
        True if all validations pass
        
    Raises:
        ContractViolationError: If any validation fails
    """
    for i, data in enumerate(data_list):
        try:
            validate_trading_data(data, contract_type)
        except ContractViolationError as e:
            raise ContractViolationError(
                f"Batch validation failed at index {i}: {str(e)}",
                "BATCH_VALIDATION",
                "validate_batch_trading_data"
            )
    return True
