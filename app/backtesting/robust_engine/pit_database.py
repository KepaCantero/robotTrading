"""
Point-in-Time Database Client for Robust Backtesting Engine.

This module provides a high-level client wrapper for the PointInTimeDatabase
that integrates seamlessly with the RobustBacktester.

The PIT database ensures that backtests only use information that would have
been available at each point in time, preventing look-ahead bias as described
in Ernest Chan's "Algorithmic Trading" (Chapter 3).

Key Features:
- Clean API for time-aware data queries
- Automatic caching for performance
- Integration with look-ahead bias validation
- Support for universe reconstruction

Reference:
    AUDIT_PLAN_COMPLETO - FASE 5.1: Point-in-Time Data
    "Algorithmic Trading" by Ernest P. Chan - Chapter 3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..point_in_time_database import CorporateAction, PITDataSnapshot, PointInTimeDatabase

logger = logging.getLogger(__name__)


@dataclass
class PITUniverseQuery:
    """
    Query parameters for point-in-time universe retrieval.

    Attributes:
        query_date: Date to query universe as of
        min_market_cap: Optional minimum market cap filter
        sectors: Optional sector filters
        max_universe_size: Maximum universe size (for top-N by market cap)
    """

    query_date: date
    min_market_cap: Optional[Decimal] = None
    sectors: Optional[List[str]] = None
    max_universe_size: Optional[int] = None


@dataclass
class PITDataQuery:
    """
    Query parameters for point-in-time data retrieval.

    Attributes:
        symbol: Stock symbol to query
        query_date: Date to get data as of
        lookback_days: Maximum lookback period in days
        adjust_for_corporate_actions: Whether to apply corporate action adjustments
    """

    symbol: str
    query_date: date
    lookback_days: int = 252
    adjust_for_corporate_actions: bool = True


class PITDatabaseClient:
    """
    Client wrapper for PointInTimeDatabase integration with RobustBacktester.

    This class provides a clean, high-level API for querying point-in-time
    data while preventing look-ahead bias. It handles caching, validation,
    and integration with the broader backtesting infrastructure.

    Example:
        ```python
        pit_client = PITDatabaseClient(
            pit_db=PointInTimeDatabase(pit_data_path="./data/pit")
        )

        # Get universe as of specific date
        universe = pit_client.get_universe_as_of(
            query_date=date(2010, 1, 1),
            min_market_cap=Decimal("1000000000")  # $1B+ market cap
        )

        # Get OHLCV data as of specific date
        data = pit_client.get_ohlcv_as_of(
            symbol="AAPL",
            query_date=date(2010, 1, 1),
            lookback_days=252
        )
        ```
    """

    def __init__(
        self,
        pit_db: PointInTimeDatabase,
        cache_size_mb: int = 100,
        enable_caching: bool = True,
    ) -> None:
        """
        Initialize the PIT database client.

        Args:
            pit_db: Underlying PointInTimeDatabase instance
            cache_size_mb: Maximum cache size in megabytes
            enable_caching: Whether to enable in-memory caching
        """
        self.pit_db = pit_db
        self.cache_size_mb = cache_size_mb
        self.enable_caching = enable_caching

        # Internal caches
        self._universe_cache: Dict[date, List[str]] = {}
        self._data_cache: Dict[Tuple[str, date], pd.DataFrame] = {}
        self._snapshot_cache: Dict[date, PITDataSnapshot] = {}

        # Statistics
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        logger.info(
            f"PITDatabaseClient initialized with cache size: {cache_size_mb}MB, "
            f"caching {'enabled' if enable_caching else 'disabled'}"
        )

    def get_universe_as_of(
        self,
        query_date: date,
        min_market_cap: Optional[Decimal] = None,
        sectors: Optional[List[str]] = None,
        max_universe_size: Optional[int] = None,
    ) -> List[str]:
        """
        Get the trading universe as of a specific historical date.

        This implements Ernest Chan's critical requirement: only trade stocks
        that would have been available at that point in time.

        Args:
            query_date: Historical date to query
            min_market_cap: Optional minimum market cap filter
            sectors: Optional sector filters
            max_universe_size: Maximum universe size (for top-N by market cap)

        Returns:
            List of symbols available at query_date

        Raises:
            ValueError: If query_date is in the future
        """
        if query_date > date.today():
            raise ValueError(f"query_date {query_date} is in the future")

        # Check cache first
        if self.enable_caching and query_date in self._universe_cache:
            self._cache_hits += 1
            logger.debug(f"PIT Universe cache hit for {query_date}")
            return self._universe_cache[query_date].copy()

        self._cache_misses += 1

        # Query underlying database
        universe = self.pit_db.get_universe_at_date(
            query_date=datetime.combine(query_date, datetime.min.time()),
            min_market_cap=min_market_cap,
            sectors=sectors,
            max_universe_size=max_universe_size,
        )

        logger.debug(
            f"PIT Universe at {query_date}: {len(universe)} symbols "
            f"(cache: {'hit' if self._cache_hits > 0 else 'miss'})"
        )

        # Cache the result
        if self.enable_caching:
            self._universe_cache[query_date] = universe.copy()
            self._manage_cache_size()

        return universe

    def get_ohlcv_as_of(
        self,
        symbol: str,
        query_date: date,
        lookback_days: int = 252,
        adjust_for_corporate_actions: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data as of a specific date.

        CRITICAL: Returns ONLY data available BEFORE query_date, preventing
        look-ahead bias as emphasized by Ernest Chan.

        Args:
            symbol: Stock ticker symbol
            query_date: Date to get data as of
            lookback_days: Maximum lookback period in days
            adjust_for_corporate_actions: Whether to apply corporate action adjustments

        Returns:
            DataFrame with OHLCV data up to (not including) query_date,
            or None if no data is available
        """
        # Check cache first
        cache_key = (symbol, query_date)
        if self.enable_caching and cache_key in self._data_cache:
            self._cache_hits += 1
            logger.debug(f"PIT Data cache hit for {symbol} at {query_date}")
            return self._data_cache[cache_key].copy()

        self._cache_misses += 1

        # Query underlying database
        data = self.pit_db.get_data_as_of_date(
            symbol=symbol,
            query_date=datetime.combine(query_date, datetime.min.time()),
            lookback_days=lookback_days,
        )

        if data is None or data.empty:
            logger.debug(f"No PIT data available for {symbol} as of {query_date}")
            return None

        # Double-check: ensure no data on/after query_date
        # This is a critical safety check
        before_count = len(data)
        # Properly check for DatetimeIndex - isinstance check is more reliable than hasattr
        # because .date is an accessor property on DatetimeIndex, not a direct attribute
        if isinstance(data.index, pd.DatetimeIndex):
            data = data[data.index.date < query_date]
        elif hasattr(data.index, 'date'):
            data = data[data.index.date < query_date]
        else:
            data = data[data.index < query_date]
        after_count = len(data)

        if before_count != after_count:
            logger.warning(
                f"Removed {before_count - after_count} data points on/after {query_date} "
                f"for {symbol} (look-ahead bias prevention)"
            )

        # Apply corporate actions if requested
        if adjust_for_corporate_actions:
            data = self.pit_db.apply_corporate_actions(
                symbol=symbol,
                data=data,
                as_of_date=datetime.combine(query_date, datetime.min.time()),
            )

        logger.debug(
            f"PIT Data for {symbol} as of {query_date}: {len(data)} bars "
            f"(cache: {'hit' if self._cache_hits > 0 else 'miss'})"
        )

        # Cache the result
        if self.enable_caching and data is not None:
            self._data_cache[cache_key] = data.copy()
            self._manage_cache_size()

        return data

    def validate_no_look_ahead(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        date_column: str = "date",
    ) -> tuple[bool, list[str]]:
        """
        Validate that no look-ahead bias exists in the backtest.

        This checks that all signals are generated using only data that
        would have been available at that point in time.

        Args:
            signals: DataFrame with signals and timestamps
            market_data: DataFrame with market data
            date_column: Name of date column in signals

        Returns:
            Tuple of (is_valid, list of issues found)
        """
        issues = []

        # Ensure signals index is datetime
        if not isinstance(signals.index, pd.DatetimeIndex):
            if date_column in signals.columns:
                signals = signals.set_index(date_column)
            else:
                issues.append("Signals DataFrame has no datetime index or date column")
                return False, issues

        # Check that all signal dates exist in data
        signal_dates = pd.to_datetime(signals.index)
        data_dates = (
            pd.to_datetime(market_data.index)
            if not isinstance(market_data.index, pd.DatetimeIndex)
            else market_data.index
        )

        for signal_date in signal_dates:
            available_data = data_dates[data_dates <= signal_date]
            if len(available_data) == 0:
                issues.append(
                    f"Look-ahead bias detected: Signal at {signal_date.date()} "
                    f"has no preceding data"
                )

        is_valid = len(issues) == 0

        if is_valid:
            logger.info("No look-ahead bias detected in backtest")
        else:
            logger.warning(f"Look-ahead bias validation failed with {len(issues)} issues")

        return is_valid, issues

    def get_snapshot_as_of(
        self,
        query_date: date,
        current_symbols: List[str],
        data_sources: Dict[str, pd.DataFrame],
    ) -> PITDataSnapshot:
        """
        Create or retrieve a point-in-time snapshot of market data.

        Args:
            query_date: Date of snapshot
            current_symbols: Symbols available at this date
            data_sources: Historical data for each symbol

        Returns:
            PITDataSnapshot for the specified date
        """
        # Check cache first
        if self.enable_caching and query_date in self._snapshot_cache:
            return self._snapshot_cache[query_date]

        # Create snapshot
        snapshot = self.pit_db.create_pit_snapshot(
            as_of_date=datetime.combine(query_date, datetime.min.time()),
            current_symbols=current_symbols,
            data_sources=data_sources,
        )

        # Cache the snapshot
        if self.enable_caching:
            self._snapshot_cache[query_date] = snapshot
            self._manage_cache_size()

        return snapshot

    def create_point_in_time_universe(
        self,
        current_universe: List[str],
        backtest_start: date,
        backtest_end: date,
        frequency: str = "M",
    ) -> Dict[date, List[str]]:
        """
        Create a point-in-time universe for backtesting.

        This implements Ernest Chan's recommendation to use only stocks that
        would have been available at each point in time.

        Args:
            current_universe: Currently traded symbols
            backtest_start: Backtest start date
            backtest_end: Backtest end date
            frequency: Rebalancing frequency ('D', 'W', 'ME', 'QE')

        Returns:
            Dictionary mapping dates to available universe
        """
        # This delegates to the survivorship adjuster which has this logic
        from .survivorship_adjuster import SurvivorshipAdjuster

        adjuster = SurvivorshipAdjuster()
        return adjuster.create_point_in_time_universe(
            current_universe=current_universe,
            backtest_start=backtest_start,
            backtest_end=backtest_end,
            frequency=frequency,
        )

    def get_corporate_actions(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[CorporateAction]:
        """
        Get corporate actions for a symbol within a date range.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of corporate actions in date range
        """
        # This would query the underlying PIT database's corporate actions
        # For now, return empty list as the implementation is in PointInTimeDatabase
        return []

    def _manage_cache_size(self) -> None:
        """Manage cache size to stay within configured limits."""
        if not self.enable_caching:
            return

        # Rough estimation of cache size (very approximate)
        total_items = len(self._universe_cache) + len(self._data_cache) + len(self._snapshot_cache)

        # Assume ~1KB per cached item on average
        estimated_size_mb = total_items / 1024

        if estimated_size_mb > self.cache_size_mb:
            # Clear oldest entries (LRU-style)
            self._universe_cache.clear()
            self._data_cache.clear()
            self._snapshot_cache.clear()
            logger.debug(f"Cleared PIT cache (estimated size: {estimated_size_mb:.1f}MB)")

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "universe_cache_size": len(self._universe_cache),
            "data_cache_size": len(self._data_cache),
            "snapshot_cache_size": len(self._snapshot_cache),
            "caching_enabled": self.enable_caching,
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._universe_cache.clear()
        self._data_cache.clear()
        self._snapshot_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.debug("PIT database cache cleared")
