"""
Decimal Utilities for Financial Calculations

This module provides utility functions for handling Decimal arithmetic
in financial calculations to ensure precision and avoid floating-point errors.

Key principles:
- All prices and quantities must use Decimal type
- No float arithmetic for financial calculations
- Safe conversion from external data sources
"""

import logging
import math
import numbers
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, getcontext
from typing import List, Optional, Sequence, Union

# Set high precision for financial calculations
getcontext().prec = 28  # Sufficient for most financial calculations
getcontext().rounding = ROUND_HALF_UP  # Standard banking rounding

logger = logging.getLogger(__name__)


def to_decimal(value: Union[int, float, str, Decimal, None]) -> Optional[Decimal]:
    """
    Safely convert value to Decimal for financial calculations.

    This function handles conversion from various types to Decimal while
    avoiding floating-point precision issues. It's the primary entry point
    for all external data entering the financial calculation system.

    Args:
        value: int, float, str, Decimal, or None to convert

    Returns:
        Decimal representation or None if input is None

    Raises:
        ValueError: If value cannot be converted to Decimal
        InvalidOperation: If the string representation is invalid

    Examples:
        >>> to_decimal(100)
        Decimal('100')
        >>> to_decimal(100.50)
        Decimal('100.5')
        >>> to_decimal("123.45")
        Decimal('123.45')
        >>> to_decimal(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            # Remove common currency symbols and formatting
            cleaned = (
                value.strip().replace('$', '').replace(',', '').replace('€', '').replace('£', '')
            )
            return Decimal(cleaned)
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Cannot convert string '{value}' to Decimal: {e}") from e
    if isinstance(value, float):
        # Convert via string to avoid floating point precision issues
        # This is critical: Decimal(0.1) != Decimal('0.1')
        # The float 0.1 is actually 0.1000000000000000055511151231257827021181583404541015625
        return Decimal(str(value))

    raise ValueError(f"Cannot convert {type(value).__name__} to Decimal")


def to_decimal_required(value: Union[int, float, str, Decimal]) -> Decimal:
    """
    Convert value to Decimal, raising an error if value is None.

    Use this for required financial fields where None is not acceptable.

    Args:
        value: int, float, str, or Decimal to convert

    Returns:
        Decimal representation

    Raises:
        ValueError: If value is None or cannot be converted to Decimal
        InvalidOperation: If the string representation is invalid

    Examples:
        >>> to_decimal_required(100)
        Decimal('100')
        >>> to_decimal_required(None)
        ValueError: Value cannot be None
    """
    if value is None:
        raise ValueError("Value cannot be None for required Decimal field")
    return to_decimal(value)


def safe_decimal_divide(
    numerator: Union[int, float, str, Decimal],
    denominator: Union[int, float, str, Decimal],
    default: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """
    Safely divide two Decimal values, handling division by zero.

    Args:
        numerator: The numerator value
        denominator: The denominator value
        default: Value to return if division by zero (default: None)

    Returns:
        Result of division as Decimal, or default if division by zero

    Examples:
        >>> safe_decimal_divide("100", "4")
        Decimal('25')
        >>> safe_decimal_divide("100", "0")
        None
        >>> safe_decimal_divide("100", "0", Decimal("0"))
        Decimal('0')
    """
    try:
        num = to_decimal_required(numerator)
        denom = to_decimal_required(denominator)

        if denom == 0:
            return default

        return num / denom
    except (ValueError, InvalidOperation) as e:
        logger.warning(f"Error in decimal division: {e}")
        return default


def validate_price(
    value: Union[int, float, str, Decimal],
    min_value: Decimal = Decimal("0.01"),
    max_value: Decimal = Decimal("1000000"),
) -> Decimal:
    """
    Validate that a value is a valid price within acceptable bounds.

    Args:
        value: The price value to validate
        min_value: Minimum acceptable price (default: $0.01)
        max_value: Maximum acceptable price (default: $1,000,000)

    Returns:
        Validated Decimal price

    Raises:
        ValueError: If price is outside valid bounds or cannot be converted

    Examples:
        >>> validate_price("100.50")
        Decimal('100.50')
        >>> validate_price("0")
        ValueError: Price must be at least 0.01
    """
    price = to_decimal_required(value)

    if price < min_value:
        raise ValueError(f"Price must be at least {min_value}, got {price}")
    if price > max_value:
        raise ValueError(f"Price cannot exceed {max_value}, got {price}")

    return price


def validate_quantity(
    value: Union[int, float, str, Decimal],
    min_value: Decimal = Decimal("0.001"),
    max_value: Decimal = Decimal("1000000000"),
) -> Decimal:
    """
    Validate that a value is a valid quantity within acceptable bounds.

    Args:
        value: The quantity value to validate
        min_value: Minimum acceptable quantity (default: 0.001)
        max_value: Maximum acceptable quantity (default: 1B)

    Returns:
        Validated Decimal quantity

    Raises:
        ValueError: If quantity is outside valid bounds or cannot be converted

    Examples:
        >>> validate_quantity("1000")
        Decimal('1000')
        >>> validate_quantity("-10")
        ValueError: Quantity must be non-negative
    """
    quantity = to_decimal_required(value)

    if quantity < min_value:
        raise ValueError(f"Quantity must be at least {min_value}, got {quantity}")
    if quantity > max_value:
        raise ValueError(f"Quantity cannot exceed {max_value}, got {quantity}")

    return quantity


def round_decimal(
    value: Union[int, float, str, Decimal], precision: int, rounding: str = ROUND_HALF_UP
) -> Decimal:
    """
    Round a Decimal value to specified precision.

    Args:
        value: The value to round
        precision: Number of decimal places
        rounding: Rounding mode (default: ROUND_HALF_UP)

    Returns:
        Rounded Decimal value

    Examples:
        >>> round_decimal("100.456", 2)
        Decimal('100.46')
        >>> round_decimal("100.454", 2)
        Decimal('100.45')
    """
    decimal_value = to_decimal_required(value)
    quantizer = Decimal("1").scaleb(-precision)
    return decimal_value.quantize(quantizer, rounding=rounding)


def format_currency(value: Union[int, float, str, Decimal], symbol: str = "$") -> str:
    """
    Format a Decimal value as a currency string.

    Args:
        value: The value to format
        symbol: Currency symbol (default: "$")

    Returns:
        Formatted currency string

    Examples:
        >>> format_currency("1234.56")
        '$1,234.56'
        >>> format_currency("1234.56", "€")
        '€1,234.56'
    """
    decimal_value = to_decimal_required(value)
    formatted = f"{decimal_value:,.2f}"
    return f"{symbol}{formatted}"


def calculate_percentage(
    numerator: Union[int, float, str, Decimal],
    denominator: Union[int, float, str, Decimal],
    precision: int = 2,
) -> Optional[Decimal]:
    """
    Calculate percentage safely, handling division by zero.

    Args:
        numerator: The numerator value
        denominator: The denominator value
        precision: Decimal precision for result (default: 2)

    Returns:
        Percentage as Decimal, or None if division by zero

    Examples:
        >>> calculate_percentage("50", "100")
        Decimal('50.00')
        >>> calculate_percentage("50", "0")
        None
    """
    result = safe_decimal_divide(numerator, denominator)
    if result is None:
        return None

    percentage = result * Decimal("100")
    return round_decimal(percentage, precision)


# Convenience dictionaries for common currency precisions
CURRENCY_PRECISIONS = {
    "USD": 2,  # US Dollar
    "EUR": 2,  # Euro
    "GBP": 2,  # British Pound
    "JPY": 0,  # Japanese Yen (no decimal for JPY)
    "BTC": 8,  # Bitcoin (Satoshi precision)
    "ETH": 18,  # Ethereum (Wei precision)
}

# Asset class specific price precisions
ASSET_CLASS_PRECISIONS = {
    "equity": 2,  # Stocks: 2 decimal places (e.g., $150.25)
    "forex": 5,  # Forex pairs: up to 5 decimal places (e.g., EUR/USD 1.08452)
    "crypto": 8,  # Crypto pairs: up to 8 decimal places (e.g., BTC/USD or SAT/BTC)
    "commodity": 2,  # Commodities: 2 decimal places (e.g., Gold $1950.50)
    "bond": 4,  # Bonds: 4 decimal places (e.g., 99.8750)
    "index": 2,  # Indices: 2 decimal places (e.g., SPX 4785.50)
}

# Common forex pair specific precisions (some pairs use 4, others 5)
FOREX_PAIR_PRECISIONS = {
    # Japanese Yen pairs: 2 decimal places (e.g., USD/JPY 149.50)
    "USD/JPY": 2,
    "EUR/JPY": 2,
    "GBP/JPY": 2,
    "AUD/JPY": 2,
    "CAD/JPY": 2,
    "CHF/JPY": 2,
    # All other major pairs: 4-5 decimal places
    "EUR/USD": 5,
    "GBP/USD": 5,
    "USD/CHF": 5,
    "AUD/USD": 5,
    "USD/CAD": 5,
    "NZD/USD": 5,
}

# Crypto pair specific precisions (more granular for high-value/low-value pairs)
CRYPTO_PAIR_PRECISIONS = {
    # BTC pairs: 8 decimal places for high precision
    "BTC/USD": 8,
    "BTC/EUR": 8,
    "BTC/GBP": 8,
    # ETH pairs: 8 decimal places
    "ETH/USD": 8,
    "ETH/BTC": 8,
    # Stablecoin pairs: higher precision for small value assets
    "USDC/USD": 6,
    "USDT/USD": 6,
    "DAI/USD": 6,
    # SAT/BTC: 8 decimal places (1 BTC = 100,000,000 SAT)
    "SAT/BTC": 8,
    # Micro pairs: maximum precision
    "SHIB/USD": 8,
    "PEPE/USD": 8,
    "DOGE/USD": 8,
}


def round_to_currency_precision(
    value: Union[int, float, str, Decimal], currency: str = "USD"
) -> Decimal:
    """
    Round a value to the standard precision for a given currency.

    Args:
        value: The value to round
        currency: Currency code (default: "USD")

    Returns:
        Rounded Decimal value

    Examples:
        >>> round_to_currency_precision("100.456", "USD")
        Decimal('100.46')
        >>> round_to_currency_precision("100.456", "JPY")
        Decimal('100')
    """
    precision = CURRENCY_PRECISIONS.get(currency.upper(), 2)
    return round_decimal(value, precision)


def get_price_precision(asset_class: str = "equity", symbol: Optional[str] = None) -> int:
    """
    Get the appropriate price precision for an asset class or specific trading pair.

    This is CRITICAL for proper financial data handling. Using incorrect precision
    will cause data loss and incorrect trading decisions.

    Args:
        asset_class: Asset class (equity, forex, crypto, commodity, bond, index)
        symbol: Optional trading symbol for precision lookup (e.g., "EUR/USD", "SAT/BTC")

    Returns:
        Number of decimal places for price precision

    Raises:
        ValueError: If asset_class is unknown

    Examples:
        >>> get_price_precision("equity")
        2
        >>> get_price_precision("forex", "EUR/USD")
        5
        >>> get_price_precision("forex", "USD/JPY")
        2
        >>> get_price_precision("crypto", "SAT/BTC")
        8
        >>> get_price_precision("crypto", "BTC/USD")
        8
    """
    asset_class_lower = asset_class.lower()

    # If symbol is provided, check for specific pair precision
    if symbol:
        symbol_upper = symbol.upper()

        # Check crypto pairs first
        if asset_class_lower == "crypto" and symbol_upper in CRYPTO_PAIR_PRECISIONS:
            return CRYPTO_PAIR_PRECISIONS[symbol_upper]

        # Check forex pairs
        if asset_class_lower == "forex" and symbol_upper in FOREX_PAIR_PRECISIONS:
            return FOREX_PAIR_PRECISIONS[symbol_upper]

    # Fall back to asset class default
    if asset_class_lower not in ASSET_CLASS_PRECISIONS:
        raise ValueError(
            f"Unknown asset class: {asset_class}. "
            f"Valid options: {list(ASSET_CLASS_PRECISIONS.keys())}"
        )

    return ASSET_CLASS_PRECISIONS[asset_class_lower]


def round_price(
    value: Union[int, float, str, Decimal],
    asset_class: str = "equity",
    symbol: Optional[str] = None,
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    """
    Round a price value to the appropriate precision for its asset class.

    This is the PRIMARY function for price rounding in the system.
    NEVER use round(price, 2) directly - it breaks Forex and Crypto precision.

    Args:
        value: The price value to round
        asset_class: Asset class (equity, forex, crypto, commodity, bond, index)
        symbol: Optional trading symbol for precision lookup
        rounding: Rounding mode (default: ROUND_HALF_UP)

    Returns:
        Rounded Decimal price with proper precision

    Raises:
        ValueError: If asset_class is unknown

    Examples:
        >>> round_price("100.456789", "equity")
        Decimal('100.46')
        >>> round_price("1.084527", "forex", "EUR/USD")
        Decimal('1.08453')
        >>> round_price("149.123", "forex", "USD/JPY")
        Decimal('149.12')
        >>> round_price("0.0000123456789", "crypto", "SAT/BTC")
        Decimal('0.00001235')
    """
    precision = get_price_precision(asset_class, symbol)
    decimal_value = to_decimal_required(value)
    quantizer = Decimal("1").scaleb(-precision)
    return decimal_value.quantize(quantizer, rounding=rounding)


def validate_price_for_asset_class(
    value: Union[int, float, str, Decimal],
    asset_class: str = "equity",
    symbol: Optional[str] = None,
) -> Decimal:
    """
    Validate and round a price for a specific asset class.

    This ensures prices are properly formatted for trading and avoids
    precision loss that could cause execution issues.

    Args:
        value: The price value to validate
        asset_class: Asset class (equity, forex, crypto, commodity, bond, index)
        symbol: Optional trading symbol

    Returns:
        Validated and rounded Decimal price

    Raises:
        ValueError: If price is invalid or asset_class is unknown

    Examples:
        >>> validate_price_for_asset_class("100.456789", "equity")
        Decimal('100.46')
        >>> validate_price_for_asset_class("1.084527", "forex", "EUR/USD")
        Decimal('1.08453')
    """
    decimal_value = to_decimal_required(value)

    # Validate minimum price based on asset class
    min_prices = {
        "equity": Decimal("0.01"),
        "forex": Decimal("0.00001"),
        "crypto": Decimal("0.00000001"),
        "commodity": Decimal("0.01"),
        "bond": Decimal("0.0001"),
        "index": Decimal("0.01"),
    }

    asset_class_lower = asset_class.lower()
    min_price = min_prices.get(asset_class_lower, Decimal("0.01"))

    if decimal_value < min_price:
        raise ValueError(
            f"Price for {asset_class} must be at least {min_price}, got {decimal_value}"
        )

    # Round to appropriate precision
    return round_price(decimal_value, asset_class, symbol)


# ============================================================================
# STATISTICAL CALCULATION UTILITIES
# These functions provide centralized, optimized statistical calculations
# ============================================================================


def safe_mean(
    values: Sequence[Union[int, float, str, Decimal]],
    default: Optional[Decimal] = None
) -> Optional[Decimal]:
    """
    Calculate mean (average) of a sequence of values using specialized libraries.

    Replaces manual sum(values) / len(values) calculations.

    Args:
        values: Sequence of numeric values
        default: Value to return if sequence is empty (default: None)

    Returns:
        Mean as Decimal, or default if sequence is empty

    Examples:
        >>> safe_mean([1, 2, 3, 4, 5])
        Decimal('3')
        >>> safe_mean([])
        None
        >>> safe_mean([], Decimal("0"))
        Decimal('0')
    """
    if not values:
        return default

    # Convert all values to Decimal
    decimal_values = [to_decimal(v) for v in values if v is not None]
    if not decimal_values:
        return default

    # Use built-in sum which is optimized in Python
    return sum(decimal_values) / len(decimal_values)


def safe_variance(
    values: Sequence[Union[int, float, str, Decimal]],
    default: Optional[Decimal] = None,
    sample: bool = False
) -> Optional[Decimal]:
    """
    Calculate variance of a sequence of values.

    Replaces manual sum((x - mean)**2) / n calculations.

    Args:
        values: Sequence of numeric values
        default: Value to return if sequence is empty (default: None)
        sample: If True, calculate sample variance (n-1 denominator)

    Returns:
        Variance as Decimal, or default if sequence is empty/has 1 element

    Examples:
        >>> safe_variance([1, 2, 3, 4, 5])
        Decimal('2')
        >>> safe_variance([1, 2, 3, 4, 5], sample=True)
        Decimal('2.5')
    """
    mean_val = safe_mean(values)
    if mean_val is None:
        return default

    decimal_values = [to_decimal(v) for v in values if v is not None]
    n = len(decimal_values)

    if n < 2:
        return default

    # Calculate variance
    squared_diffs = [(v - mean_val) ** 2 for v in decimal_values]
    denominator = n - 1 if sample else n
    return sum(squared_diffs) / denominator


def safe_std(
    values: Sequence[Union[int, float, str, Decimal]],
    default: Optional[Decimal] = None,
    sample: bool = False
) -> Optional[Decimal]:
    """
    Calculate standard deviation of a sequence of values.

    Replaces manual variance**0.5 or math.sqrt(variance) calculations.

    Args:
        values: Sequence of numeric values
        default: Value to return if sequence is empty (default: None)
        sample: If True, calculate sample std (n-1 denominator)

    Returns:
        Standard deviation as Decimal, or default if sequence is empty/has 1 element

    Examples:
        >>> safe_std([1, 2, 3, 4, 5])
        Decimal('1.414213562373095048801689')
    """
    variance_val = safe_variance(values, default, sample=sample)
    if variance_val is None or variance_val < 0:
        return default

    # Use Decimal sqrt() for precision
    try:
        return variance_val.sqrt()
    except (InvalidOperation, AttributeError):
        # Fallback to math.sqrt for very old Python versions
        return Decimal(str(math.sqrt(float(variance_val))))


def safe_decimal_sqrt(
    value: Union[int, float, str, Decimal],
    default: Optional[Decimal] = None
) -> Optional[Decimal]:
    """
    Calculate square root of a Decimal value.

    Replaces manual value**0.5 or math.sqrt(value) for Decimals.

    Args:
        value: The value to calculate square root of
        default: Value to return if value is negative (default: None)

    Returns:
        Square root as Decimal, or default if value is negative

    Examples:
        >>> safe_decimal_sqrt(25)
        Decimal('5')
        >>> safe_decimal_sqrt(-1)
        None
    """
    decimal_value = to_decimal(value)
    if decimal_value is None:
        return default

    if decimal_value < 0:
        return default

    try:
        return decimal_value.sqrt()
    except (InvalidOperation, AttributeError):
        return Decimal(str(math.sqrt(float(decimal_value))))


# ============================================================================
# FINANCIAL CALCULATION UTILITIES
# ============================================================================

# Basis point constant: 1 BPS = 0.01% = 0.0001 = 1/10000
_BPS_CONVERSION_FACTOR = Decimal("10000")
_BPS_DECIMAL_FACTOR = Decimal("0.0001")  # 1/10000


def to_bps(
    value: Union[int, float, str, Decimal],
    precision: int = 2
) -> Decimal:
    """
    Convert a decimal value to basis points (BPS).

    1 BPS = 0.01% = 0.0001 = 1/10000

    Replaces manual value * 10000 calculations.

    Args:
        value: The decimal value to convert (e.g., 0.01 for 1%)
        precision: Decimal precision for result (default: 2)

    Returns:
        Value in basis points as Decimal

    Examples:
        >>> to_bps(0.01)  # 1%
        Decimal('100.00')
        >>> to_bps(0.025)  # 2.5%
        Decimal('250.00')
        >>> to_bps("0.005")  # 0.5%
        Decimal('50.00')
    """
    decimal_value = to_decimal_required(value)
    result = decimal_value * _BPS_CONVERSION_FACTOR
    return round_decimal(result, precision)


def from_bps(
    bps_value: Union[int, float, str, Decimal],
    precision: int = 6
) -> Decimal:
    """
    Convert basis points (BPS) to decimal value.

    1 BPS = 0.01% = 0.0001 = 1/10000

    Replaces manual value / 10000 calculations.

    Args:
        bps_value: The basis points value to convert
        precision: Decimal precision for result (default: 6)

    Returns:
        Decimal value (e.g., 0.01 for 100 BPS)

    Examples:
        >>> from_bps(100)  # 100 BPS = 1%
        Decimal('0.010000')
        >>> from_bps(250)  # 250 BPS = 2.5%
        Decimal('0.025000')
        >>> from_bps("50")  # 50 BPS = 0.5%
        Decimal('0.005000')
    """
    decimal_value = to_decimal_required(bps_value)
    result = decimal_value * _BPS_DECIMAL_FACTOR
    return round_decimal(result, precision)


def to_bps_float(value: float) -> float:
    """
    Convert a float to basis points (BPS) as float.

    Faster version for float calculations without Decimal overhead.

    Args:
        value: The float value to convert

    Returns:
        Value in basis points as float

    Examples:
        >>> to_bps_float(0.01)  # 1%
        100.0
        >>> to_bps_float(0.025)  # 2.5%
        250.0
    """
    return value * 10000.0


def from_bps_float(bps_value: float) -> float:
    """
    Convert basis points (BPS) to decimal value as float.

    Faster version for float calculations without Decimal overhead.

    Args:
        bps_value: The basis points value to convert

    Returns:
        Decimal value as float

    Examples:
        >>> from_bps_float(100)  # 100 BPS = 1%
        0.01
        >>> from_bps_float(250)  # 250 BPS = 2.5%
        0.025
    """
    return bps_value / 10000.0


def spread_to_bps(
    bid: Union[int, float, str, Decimal],
    ask: Union[int, float, str, Decimal],
    precision: int = 2
) -> Decimal:
    """
    Convert bid-ask spread to basis points.

    Spread BPS = (ask - bid) / midpoint * 10000

    Args:
        bid: Bid price
        ask: Ask price
        precision: Decimal precision for result (default: 2)

    Returns:
        Spread in basis points as Decimal

    Examples:
        >>> spread_to_bps(100, 101)
        Decimal('99.50')  # Approximately 1% spread
    """
    decimal_bid = to_decimal_required(bid)
    decimal_ask = to_decimal_required(ask)

    midpoint = (decimal_bid + decimal_ask) / 2
    if midpoint == 0:
        return Decimal("0")

    spread_decimal = (decimal_ask - decimal_bid) / midpoint
    return to_bps(spread_decimal, precision)


def annualize_volatility(
    daily_volatility: Union[int, float, str, Decimal],
    trading_days: int = 252
) -> Decimal:
    """
    Annualize daily volatility using proper sqrt calculation.

    Annual Volatility = Daily Volatility * sqrt(trading_days)

    Replaces manual volatility * (252**0.5) calculations.

    Args:
        daily_volatility: Daily volatility value
        trading_days: Number of trading days per year (default: 252)

    Returns:
        Annualized volatility as Decimal

    Examples:
        >>> annualize_volatility(0.01)
        Decimal('0.158707...')  # ~15.87% annualized
    """
    decimal_vol = to_decimal_required(daily_volatility)
    sqrt_days = safe_decimal_sqrt(trading_days) or Decimal(str(math.sqrt(trading_days)))
    return decimal_vol * sqrt_days


def annualize_returns(
    daily_return: Union[int, float, str, Decimal],
    trading_days: int = 252
) -> Decimal:
    """
    Annualize daily returns.

    Annual Return = Daily Return * trading_days

    Args:
        daily_return: Daily return value
        trading_days: Number of trading days per year (default: 252)

    Returns:
        Annualized return as Decimal

    Examples:
        >>> annualize_returns(0.001)
        Decimal('0.252')  # 25.2% annualized
    """
    decimal_return = to_decimal_required(daily_return)
    return decimal_return * Decimal(trading_days)
