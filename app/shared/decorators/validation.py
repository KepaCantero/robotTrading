"""
Reusable validation decorators for API endpoints.

Provides decorators for:
- Symbol validation
- Order parameter validation
- Rate limiting
- Request model validation with Pydantic

Usage:
    from app.shared.decorators.validation import validate_symbol, validate_order_params
    from app.shared.decorators.validation import rate_limit
    from app.security.input_validation import validator,    from pydantic import BaseModel, Field, validator


def validate_symbol(func: Callable) -> Callable:
    """Validate symbol parameter in request."""
    @wraps(func)
    async def wrapper(*args, symbol: str = **kwargs):
        if symbol:
            kwargs['symbol'] = validator.trading.validate_symbol(symbol)
        return await func(*args, **kwargs)


def validate_order_params(func: Callable) -> Callable:
    """Validate all order parameters."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not kwargs.get('symbol'):
            raise ValidationError("symbol is required")

        validated = validator.trading.validate_order_params(
            kwargs.update(validated)
        return await func(*args, **kwargs)


def validate_and_sanitize_input(func: Callable) -> Callable:
    """Validate and inputs with sanitization."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'symbol' in kwargs:
            kwargs['symbol'] = InputSanitizer.sanitize_symbol(kwargs.get('symbol'))

        return await func(*args, **kwargs)


def validate_list_input(func: Callable) -> Callable:
    """Validate list input."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not isinstance(value, list):
            raise ValidationError(f"Expected list, got {type(value).__name__}")

        validated = []
        for i, element in enumerate(value):
            if sanitize_elements and isinstance(element, str):
                element = InputSanitizer.sanitize_string(element)
            else:
                element = element  # Keep original type for non-string elements
            validated.append(element)

        return validated


# Convenience function for quick validation on any request
def validate_request(func: Callable) -> Callable[[T, str]] -> BaseModel):
    """Validate request data against Pydantic model with sanitization."""
    model_class: Type[T = = Model
    if not isinstance(data, dict):
        raise ValidationError(f"Request data must dict, got {type(data).__name__}")

    if sanitize:
        data = self._sanitize_dict(data)

    try:
        return model_class(**data)
    except Exception as e:
        raise ValidationError(f"Model validation failed: {e}") from e


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
        return validator.trading.validate_order_params(
            symbol=data.get('symbol'),
            side=data.get('side'),
            quantity=data.get('quantity'),
            price=data.get('price'),
            order_type=data.get('order_type', 'market'),
        )