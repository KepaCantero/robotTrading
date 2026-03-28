"""
Timezone utilities for multi-market trading system.

Ensures consistent timezone handling across stocks (US/EU), forex (24/7),
and crypto (24/7) markets.

Phase 0.3: Timezone Awareness Implementation
- All timestamps use timezone-aware datetime
- Consistent UTC handling across all services
- Market-specific timezone support
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# Market-specific timezone configurations
# Note: Using UTC for simplicity in Phase 0.3
# Phase 3 will implement proper exchange timezones
MARKET_TIMEZONES = {
    "us": timezone.utc,  # Will be US/Eastern in Phase 3
    "eu": timezone.utc,  # Will be Europe/Madrid in Phase 3
    "forex": timezone.utc,
    "crypto": timezone.utc,
    "asia": timezone.utc,  # Will be Asia/Tokyo in Phase 3
}


def utc_now() -> datetime:
    """
    Get current UTC time with timezone info.

    This is the RECOMMENDED way to get current time throughout the system.
    Replaces datetime.utcnow() which returns naive datetime.

    Returns:
        datetime with UTC timezone set

    Example:
        >>> from app.shared.utils.timezone_utils import utc_now
        >>> now = utc_now()
        >>> now.tzinfo is not None
        True
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Handles both naive and aware datetimes:
    - Naive: Assumes UTC and adds timezone info (with warning)
    - Aware: Converts to UTC

    Args:
        dt: datetime to convert (naive or aware)

    Returns:
        datetime with UTC timezone

    Example:
        >>> from datetime import datetime
        >>> from app.shared.utils.timezone_utils import to_utc
        >>> naive = datetime(2024, 1, 1, 12, 0)
        >>> aware = to_utc(naive)
        >>> aware.tzinfo is not None
        True
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        logger.warning(
            "Converting naive datetime to UTC - assuming input was UTC. "
            "Use utc_now() or timezone-aware datetime to avoid this warning."
        )
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def to_market_time(dt: datetime, market: str) -> datetime:
    """
    Convert datetime to market-specific timezone.

    Args:
        dt: datetime to convert (will be converted to UTC first if needed)
        market: Market identifier (us, eu, forex, crypto, asia)

    Returns:
        datetime in market timezone

    Example:
        >>> from app.shared.utils.timezone_utils import to_market_time, utc_now
        >>> now = utc_now()
        >>> us_time = to_market_time(now, "us")
        >>> us_time.tzinfo is not None
        True
    """
    tz = MARKET_TIMEZONES.get(market.lower(), timezone.utc)
    dt_utc = to_utc(dt)
    return dt_utc.astimezone(tz)


def format_utc(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format datetime as UTC string.

    Args:
        dt: datetime to format
        fmt: format string (default: "YYYY-MM-DD HH:MM:SS TZ")

    Returns:
        formatted string with timezone info

    Example:
        >>> from app.shared.utils.timezone_utils import utc_now, format_utc
        >>> now = utc_now()
        >>> formatted = format_utc(now)
        >>> 'UTC' in formatted
        True
    """
    return to_utc(dt).strftime(fmt)


def format_market_time(dt: datetime, market: str, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format datetime in market-specific timezone.

    Args:
        dt: datetime to format
        market: Market identifier
        fmt: format string

    Returns:
        formatted string in market timezone

    Example:
        >>> from app.shared.utils.timezone_utils import utc_now, format_market_time
        >>> now = utc_now()
        >>> formatted = format_market_time(now, "us")
    """
    dt_market = to_market_time(dt, market)
    return dt_market.strftime(fmt)


def get_market_timezone(market: str) -> timezone:
    """
    Get timezone for a specific market.

    Args:
        market: Market identifier (us, eu, forex, crypto, asia)

    Returns:
        timezone for the market

    Example:
        >>> from app.shared.utils.timezone_utils import get_market_timezone
        >>> tz = get_market_timezone("us")
        >>> tz is not None
        True
    """
    return MARKET_TIMEZONES.get(market.lower(), timezone.utc)


def is_market_open(market: str, dt: Optional[datetime] = None) -> bool:
    """
    Check if market is open at given time.

    Phase 0.3: Simplified logic
    - Crypto and forex are 24/7
    - Stocks: Will implement proper hours in Phase 3

    Args:
        market: Market identifier
        dt: datetime to check (defaults to now)

    Returns:
        True if market is open

    Example:
        >>> from app.shared.utils.timezone_utils import is_market_open
        >>> is_market_open("crypto")
        True
    """
    if dt is None:
        dt = utc_now()

    dt = to_utc(dt)

    # Crypto and forex are 24/7
    if market.lower() in ("crypto", "forex"):
        return True

    # US market: 9:30 AM - 4:00 PM ET (simplified to UTC for Phase 0.3)
    # EU market: 9:00 AM - 5:30 PM CET (simplified to UTC for Phase 0.3)
    # For Phase 0.3, return True for all - full implementation in Phase 3
    return True


def get_market_open_close_time(
    market: str, dt: Optional[datetime] = None
) -> tuple[datetime, datetime]:
    """
    Get market open and close times for a given date.

    Phase 0.3: Returns placeholder times
    Phase 3: Will implement proper exchange hours

    Args:
        market: Market identifier
        dt: Reference date (defaults to today)

    Returns:
        Tuple of (open_time, close_time) in UTC

    Example:
        >>> from app.shared.utils.timezone_utils import get_market_open_close_time
        >>> open_time, close_time = get_market_open_close_time("us")
    """
    if dt is None:
        dt = utc_now()

    dt = to_utc(dt)

    # Placeholder times - will implement properly in Phase 3
    if market.lower() == "us":
        # 9:30 AM - 4:00 PM ET (placeholder: use UTC times)
        open_time = dt.replace(hour=14, minute=30, second=0, microsecond=0)
        close_time = dt.replace(hour=21, minute=0, second=0, microsecond=0)
    elif market.lower() == "eu":
        # 9:00 AM - 5:30 PM CET (placeholder: use UTC times)
        open_time = dt.replace(hour=8, minute=0, second=0, microsecond=0)
        close_time = dt.replace(hour=16, minute=30, second=0, microsecond=0)
    else:
        # 24/7 markets (crypto, forex)
        open_time = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        close_time = dt.replace(hour=23, minute=59, second=59, microsecond=0)

    return open_time, close_time


def validate_timezone_aware(dt: datetime, param_name: str = "datetime") -> None:
    """
    Validate that a datetime is timezone-aware.

    Raises ValueError if datetime is naive.

    Args:
        dt: datetime to validate
        param_name: Name of parameter for error message

    Raises:
        ValueError: If datetime is naive

    Example:
        >>> from datetime import datetime
        >>> from app.shared.utils.timezone_utils import validate_timezone_aware
        >>> naive = datetime(2024, 1, 1)
        >>> validate_timezone_aware(naive)
        Traceback (most recent call last):
        ...
        ValueError: datetime must be timezone-aware
    """
    if dt.tzinfo is None:
        raise ValueError(
            f"{param_name} must be timezone-aware. "
            f"Use utc_now() or to_utc() to ensure timezone awareness."
        )


def ensure_timezone_aware(dt: datetime, param_name: str = "datetime") -> datetime:
    """
    Ensure datetime is timezone-aware, converting if necessary.

    Unlike to_utc(), this logs a warning when converting naive datetime.

    Args:
        dt: datetime to check/convert
        param_name: Name of parameter for warning message

    Returns:
        timezone-aware datetime

    Example:
        >>> from datetime import datetime
        >>> from app.shared.utils.timezone_utils import ensure_timezone_aware
        >>> naive = datetime(2024, 1, 1, 12, 0)
        >>> aware = ensure_timezone_aware(naive)
        >>> aware.tzinfo is not None
        True
    """
    if dt.tzinfo is None:
        logger.warning(
            f"{param_name} is naive datetime. Converting to UTC. "
            f"Please use utc_now() or timezone-aware datetime in the future."
        )
        return to_utc(dt)
    return dt


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware datetime.

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        timezone-aware datetime

    Raises:
        ValueError: If string cannot be parsed

    Example:
        >>> from app.shared.utils.timezone_utils import parse_iso_datetime
        >>> dt = parse_iso_datetime("2024-01-01T12:00:00Z")
        >>> dt.tzinfo is not None
        True
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return to_utc(dt)
    except ValueError as e:
        raise ValueError(f"Cannot parse ISO datetime '{iso_string}': {e}")


# ============================================================================
# DATABASE COMPATIBILITY
# ============================================================================


def get_db_timestamp_default():
    """
    Get default timestamp for database columns.

    Use this as the 'default' value for TIMESTAMP columns.

    Returns:
        Callable that returns current UTC datetime

    Example:
        >>> from sqlalchemy import Column, TIMESTAMP
        >>> from app.shared.utils.timezone_utils import get_db_timestamp_default
        >>> created_at = Column(TIMESTAMP(timezone=True), default=get_db_timestamp_default())
    """
    return utc_now


def get_db_timestamp_onupdate():
    """
    Get onupdate timestamp for database columns.

    Use this as the 'onupdate' value for TIMESTAMP columns.

    Returns:
        Callable that returns current UTC datetime

    Example:
        >>> from sqlalchemy import Column, TIMESTAMP
        >>> from app.shared.utils.timezone_utils import get_db_timestamp_onupdate
        >>> updated_at = Column(TIMESTAMP(timezone=True), onupdate=get_db_timestamp_onupdate())
    """
    return utc_now


# ============================================================================
# DISPLAY UTILITIES
# ============================================================================


def to_local_timezone(dt: datetime, local_tz: Optional[timezone] = None) -> datetime:
    """
    Convert datetime to local timezone for display.

    Args:
        dt: datetime to convert
        local_tz: Local timezone (defaults to system local timezone)

    Returns:
        datetime in local timezone

    Example:
        >>> from app.shared.utils.timezone_utils import utc_now, to_local_timezone
        >>> now = utc_now()
        >>> local = to_local_timezone(now)
    """
    dt_utc = to_utc(dt)
    if local_tz is None:
        # Use system local timezone
        try:
            import tzlocal

            local_tz = tzlocal.get_localzone()
        except ImportError:
            logger.warning("tzlocal not installed, falling back to UTC")
            local_tz = timezone.utc
    return dt_utc.astimezone(local_tz)


def format_for_display(dt: datetime, local_tz: Optional[timezone] = None) -> str:
    """
    Format datetime for user display in local timezone.

    Args:
        dt: datetime to format
        local_tz: Local timezone (defaults to system local timezone)

    Returns:
        formatted string in local timezone

    Example:
        >>> from app.shared.utils.timezone_utils import utc_now, format_for_display
        >>> now = utc_now()
        >>> display_str = format_for_display(now)
    """
    local_dt = to_local_timezone(dt, local_tz)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
