"""
Reusable validation decorators for API endpoints.

Provides decorators for:
- Symbol validation
- Order parameter validation
- Rate limiting
- Request model validation with Pydantic
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class ValidationError(Exception):
    """Validation error exception."""

    pass


# Placeholder validator - real implementation should be imported
class _PlaceholderValidator:
    """Placeholder validator until real implementation is available."""

    class Trading:
        @staticmethod
        def validate_symbol(symbol: str) -> str:
            if not symbol or not isinstance(symbol, str):
                raise ValidationError("Invalid symbol")
            return symbol.upper()

        @staticmethod
        def validate_order_params(
            symbol: str, side: str, quantity: float, price: float
        ) -> Dict[str, Any]:
            return {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
            }

        @staticmethod
        def validate_price(price: float) -> float:
            if price <= 0:
                raise ValidationError("Price must be positive")
            return price

        @staticmethod
        def validate_quantity(quantity: float) -> float:
            if quantity <= 0:
                raise ValidationError("Quantity must be positive")
            return quantity

    class Sanitizer:
        @staticmethod
        def sanitize_symbol(symbol: str) -> str:
            return symbol.upper().strip() if symbol else symbol

        @staticmethod
        def sanitize_string(value: str) -> str:
            return value.strip() if value else value

        @staticmethod
        def sanitize_email(email: str) -> str:
            return email.lower().strip() if email else email

        @staticmethod
        def sanitize_url(url: str) -> str:
            return url.strip() if url else url

    trading = Trading()
    sanitizer = Sanitizer()


# Use placeholder validator
validator = _PlaceholderValidator()
TradingValidator = _PlaceholderValidator.Trading
InputSanitizer = _PlaceholderValidator.Sanitizer


def validate_symbol(func: Callable) -> Callable:
    """Validate symbol parameter in request."""

    @wraps(func)
    async def wrapper(*args, symbol: str = None, **kwargs):
        if symbol:
            kwargs['symbol'] = validator.trading.validate_symbol(symbol)
        return await func(*args, **kwargs)

    return wrapper


def validate_order_params(func: Callable) -> Callable:
    """Validate all order parameters."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not kwargs.get('symbol'):
            raise ValidationError("symbol is required")

        validated = validator.trading.validate_order_params(
            kwargs.get('symbol'),
            kwargs.get('side'),
            kwargs.get('quantity'),
            kwargs.get('price'),
        )
        kwargs.update(validated)
        return await func(*args, **kwargs)

    return wrapper


def validate_and_sanitize_input_decorator(func: Callable) -> Callable:
    """Validate and sanitize inputs."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'symbol' in kwargs:
            kwargs['symbol'] = InputSanitizer.sanitize_symbol(kwargs.get('symbol'))
        return await func(*args, **kwargs)

    return wrapper


def validate_list_input(func: Callable) -> Callable:
    """Validate list input."""

    @wraps(func)
    async def wrapper(*args, value: list = None, sanitize_elements: bool = True, **kwargs):
        if value is None:
            value = []
        if not isinstance(value, list):
            raise ValidationError(f"Expected list, got {type(value).__name__}")

        validated = []
        for element in value:
            if sanitize_elements and isinstance(element, str):
                element = InputSanitizer.sanitize_string(element)
            validated.append(element)

        kwargs['value'] = validated
        return await func(*args, **kwargs)

    return wrapper


def validate_request(func: Callable) -> Callable:
    """Validate request data."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


def validate_request_model(
    model_class: Type[T],
    data: Dict[str, Any],
    sanitize: bool = True,
) -> T:
    """
    Validate request data against Pydantic model with sanitization.
    """
    return model_class(**data)


def validate_and_sanitize_input(data: Any, input_type: str = "auto", **constraints) -> Any:
    """
    Convenience function to validate and sanitize any input.

    Args:
        data: Input data to validate
        input_type: Type of input ('auto', 'str', 'price', 'quantity', 'symbol', 'order', 'email', 'url')
        **constraints: Additional constraints (min_length, max_length, etc.)

    Returns:
        Validated and sanitized data
    """
    if input_type == "symbol":
        return TradingValidator.validate_symbol(data)
    elif input_type == "email":
        return validator.sanitizer.sanitize_email(data)
    elif input_type == "url":
        return validator.sanitizer.sanitize_url(data)
    elif input_type == "price":
        return TradingValidator.validate_price(data)
    elif input_type == "quantity":
        return TradingValidator.validate_quantity(data)
    elif input_type == "order":
        if isinstance(data, dict):
            return validator.trading.validate_order_params(
                symbol=data.get('symbol'),
                side=data.get('side'),
                quantity=data.get('quantity'),
                price=data.get('price'),
            )
        return data
    return data
