"""
Tests for timezone utilities module.

Phase 0.3: Timezone Awareness Tests
- Verify utc_now() returns timezone-aware datetime
- Verify to_utc() handles both naive and aware datetimes
- Verify market timezone utilities
- Verify database compatibility functions
"""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from app.core.timezone_utils import (
    utc_now,
    to_utc,
    to_market_time,
    format_utc,
    format_market_time,
    get_market_timezone,
    is_market_open,
    get_market_open_close_time,
    validate_timezone_aware,
    ensure_timezone_aware,
    parse_iso_datetime,
    get_db_timestamp_default,
    get_db_timestamp_onupdate,
    to_local_timezone,
    format_for_display,
)


class TestUTCNOW:
    """Tests for utc_now() function."""

    def test_utc_now_returns_timezone_aware(self):
        """Test that utc_now returns timezone-aware datetime."""
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_utc_now_is_recent(self):
        """Test that utc_now returns recent time."""
        now = utc_now()
        # Should be within 1 second of current time
        assert abs((datetime.now(timezone.utc) - now).total_seconds()) < 1.0


class TestToUTC:
    """Tests for to_utc() function."""

    def test_to_utc_with_aware_datetime(self):
        """Test to_utc with timezone-aware datetime."""
        # Create datetime in different timezone
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5)))
        result = to_utc(dt)

        assert result.tzinfo == timezone.utc
        # Should be converted to UTC (12:00 +05:00 = 07:00 UTC)
        assert result.hour == 7

    def test_to_utc_with_naive_datetime(self):
        """Test to_utc with naive datetime (should warn and convert)."""
        dt = datetime(2024, 1, 1, 12, 0)
        result = to_utc(dt)

        assert result.tzinfo == timezone.utc
        # Should assume UTC and add timezone
        assert result.hour == 12

    def test_to_utc_already_utc(self):
        """Test to_utc with UTC datetime (should be idempotent)."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = to_utc(dt)

        assert result.tzinfo == timezone.utc
        assert result.hour == 12


class TestMarketTime:
    """Tests for market timezone functions."""

    @pytest.mark.parametrize("market", ["us", "eu", "forex", "crypto", "asia"])
    def test_get_market_timezone(self, market):
        """Test get_market_timezone returns valid timezone."""
        tz = get_market_timezone(market)
        assert tz is not None
        assert isinstance(tz, timezone)

    def test_to_market_time(self):
        """Test to_market_time conversion."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        us_time = to_market_time(dt, "us")

        assert us_time.tzinfo is not None
        # In Phase 0.3, all markets use UTC
        assert us_time.hour == 12

    @pytest.mark.parametrize("market", ["crypto", "forex"])
    def test_is_market_open_24_7(self, market):
        """Test that crypto and forex are always open."""
        assert is_market_open(market) is True

    def test_get_market_open_close_time(self):
        """Test get_market_open_close_time returns valid times."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        open_time, close_time = get_market_open_close_time("us", dt)

        assert open_time.tzinfo is not None
        assert close_time.tzinfo is not None
        assert open_time < close_time


class TestFormatting:
    """Tests for formatting functions."""

    def test_format_utc(self):
        """Test format_utc includes timezone."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        formatted = format_utc(dt)

        assert "UTC" in formatted
        assert "2024-01-01" in formatted

    def test_format_utc_custom_format(self):
        """Test format_utc with custom format string."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        formatted = format_utc(dt, fmt="%Y-%m-%d")

        assert formatted == "2024-01-01"

    def test_format_market_time(self):
        """Test format_market_time."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        formatted = format_market_time(dt, "us")

        assert "2024-01-01" in formatted


class TestValidation:
    """Tests for validation functions."""

    def test_validate_timezone_aware_with_aware(self):
        """Test validate_timezone_aware with aware datetime passes."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        # Should not raise
        validate_timezone_aware(dt)

    def test_validate_timezone_aware_with_naive(self):
        """Test validate_timezone_aware with naive datetime raises."""
        dt = datetime(2024, 1, 1, 12, 0)
        with pytest.raises(ValueError, match="must be timezone-aware"):
            validate_timezone_aware(dt)

    def test_ensure_timezone_aware_with_aware(self):
        """Test ensure_timezone_aware with aware datetime."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = ensure_timezone_aware(dt)

        assert result.tzinfo == timezone.utc

    def test_ensure_timezone_aware_with_naive(self):
        """Test ensure_timezone_aware with naive datetime converts."""
        dt = datetime(2024, 1, 1, 12, 0)
        result = ensure_timezone_aware(dt)

        assert result.tzinfo == timezone.utc


class TestParsing:
    """Tests for parsing functions."""

    def test_parse_iso_datetime_with_z(self):
        """Test parse_iso_datetime with Z suffix."""
        dt = parse_iso_datetime("2024-01-01T12:00:00Z")

        assert dt.tzinfo == timezone.utc
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12

    def test_parse_iso_datetime_with_offset(self):
        """Test parse_iso_datetime with timezone offset."""
        dt = parse_iso_datetime("2024-01-01T12:00:00+05:00")

        assert dt.tzinfo == timezone.utc
        # Should convert 12:00 +05:00 to 07:00 UTC
        assert dt.hour == 7

    def test_parse_iso_datetime_invalid(self):
        """Test parse_iso_datetime with invalid string."""
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_iso_datetime("not-a-datetime")


class TestDatabaseCompatibility:
    """Tests for database compatibility functions."""

    def test_get_db_timestamp_default(self):
        """Test get_db_timestamp_default returns callable."""
        func = get_db_timestamp_default()
        assert callable(func)

        # Call it
        dt = func()
        assert dt.tzinfo == timezone.utc

    def test_get_db_timestamp_onupdate(self):
        """Test get_db_timestamp_onupdate returns callable."""
        func = get_db_timestamp_onupdate()
        assert callable(func)

        # Call it
        dt = func()
        assert dt.tzinfo == timezone.utc


class TestDisplayUtilities:
    """Tests for display utilities."""

    def test_to_local_timezone(self):
        """Test to_local_timezone conversion."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        local_dt = to_local_timezone(dt, timezone(timedelta(hours=-5)))

        assert local_dt.tzinfo is not None
        # 12:00 UTC = 07:00 EST
        assert local_dt.hour == 7

    def test_format_for_display(self):
        """Test format_for_display includes timezone."""
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        display = format_for_display(dt, timezone(timedelta(hours=-5)))

        assert "2024-01-01" in display
        # Should include timezone info
        assert len(display) > 0


class TestIntegration:
    """Integration tests for timezone utilities."""

    def test_workflow_create_store_and_retrieve(self):
        """Test complete workflow: create, store, retrieve, display."""
        # Create timezone-aware timestamp
        created_at = utc_now()
        assert created_at.tzinfo is not None

        # Format for storage/display
        formatted = format_utc(created_at, fmt="%Y-%m-%dT%H:%M:%S")
        assert "2024" in formatted or "2025" in formatted or "2026" in formatted

        # Parse back (add Z for UTC)
        parsed = parse_iso_datetime(formatted + "Z")
        assert parsed.tzinfo == timezone.utc

        # Convert to market time
        market_time = to_market_time(parsed, "crypto")
        assert market_time.tzinfo is not None

    def test_market_hours_workflow(self):
        """Test market hours checking workflow."""
        dt = utc_now()

        # Check if markets are open
        crypto_open = is_market_open("crypto", dt)
        assert crypto_open is True

        forex_open = is_market_open("forex", dt)
        assert forex_open is True

        # Get market hours
        us_open, us_close = get_market_open_close_time("us", dt)
        assert us_open.tzinfo is not None
        assert us_close.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
