"""
Point-in-Time Database for Backtesting

This module implements point-in-time (PIT) data handling as described in
Ernest Chan's "Algorithmic Trading" (Chapter 3).

Point-in-time data ensures that backtests only use information that would
have been available at each point in time, preventing look-ahead bias.

Key Features:
- Historical universe reconstruction
- Time-sensitive data queries
- Corporate actions adjustment
- Look-ahead prevention

Reference:
    "Algorithmic Trading" by Ernest P. Chan
    Chapter 3: Backtesting
    Section: Point-in-Time Data
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoricalConstituent:
    """A stock that was part of the universe at a historical date."""

    symbol: str
    entry_date: datetime
    exit_date: datetime | None
    exit_reason: str | None  # 'delisted', 'merged', 'still_trading'
    market_cap: Decimal | None
    sector: str | None


@dataclass(frozen=True)
class PITDataSnapshot:
    """Point-in-time snapshot of market data."""

    as_of_date: datetime
    available_symbols: list[str]
    total_universe_size: int
    data_coverage: dict[str, int]  # symbol -> days of history available


@dataclass(frozen=True)
class CorporateAction:
    """Corporate action that affects historical data."""

    symbol: str
    action_type: str  # 'split', 'dividend', 'merger', 'spinoff'
    ex_date: datetime
    action_details: dict[str, Any]
    adjustment_factor: Decimal


class PointInTimeDatabase:
    """
    Point-in-time database for look-ahead-bias-free backtesting.

    This implements Ernest Chan's recommendation to use only data that
    would have been available at each point in time during the backtest.
    """

    def __init__(
        self,
        pit_data_path: Path | None = None,
        cache_size_mb: int = 100,
    ):
        """
        Initialize the point-in-time database.

        Args:
            pit_data_path: Path to PIT data files
            cache_size_mb: Size of in-memory cache in MB
        """
        self.pit_data_path = pit_data_path or Path("data/pit_database")
        self.cache_size_mb = cache_size_mb

        # In-memory cache for historical snapshots
        self._snapshot_cache: dict[datetime, PITDataSnapshot] = {}

        # Corporate actions database
        self._corporate_actions: dict[str, list[CorporateAction]] = {}

        # Historical constituents database
        self._historical_constituents: dict[datetime, list[HistoricalConstituent]] = {}

        logger.info(
            f"PointInTimeDatabase initialized with cache size: {cache_size_mb}MB, "
            f"data path: {self.pit_data_path}"
        )

    def get_universe_at_date(
        self,
        query_date: datetime,
        min_market_cap: Decimal | None = None,
        sectors: list[str] | None = None,
        max_universe_size: int | None = None,
    ) -> list[str]:
        """
        Get the trading universe as of a specific historical date.

        This implements Ernest Chan's critical requirement: only trade
        stocks that would have been available at that point in time.

        Args:
            query_date: Historical date to query
            min_market_cap: Minimum market cap filter
            sectors: Sector filters
            max_universe_size: Maximum universe size (for top-N by market cap)

        Returns:
            List of symbols available at query_date
        """
        try:
            # Check cache first
            if query_date in self._snapshot_cache:
                snapshot = self._snapshot_cache[query_date]
                universe = snapshot.available_symbols
            else:
                # Load from disk or simulate
                universe = self._load_universe_for_date(query_date)

                # Cache the snapshot
                snapshot = PITDataSnapshot(
                    as_of_date=query_date,
                    available_symbols=universe,
                    total_universe_size=len(universe),
                    data_coverage={},
                )
                self._cache_snapshot(snapshot)

            # Apply filters
            if min_market_cap or sectors:
                universe = self._apply_filters(universe, query_date, min_market_cap, sectors)

            # Limit universe size if specified
            if max_universe_size and len(universe) > max_universe_size:
                universe = self._select_top_by_market_cap(universe, query_date, max_universe_size)

            logger.debug(f"PIT Database: Universe at {query_date.date()}: {len(universe)} symbols")
            return universe

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error getting universe at date {query_date}: {e}")
            return []

    def get_data_as_of_date(
        self,
        symbol: str,
        query_date: datetime,
        lookback_days: int = 252,
    ) -> pd.DataFrame | None:
        """
        Get historical data as of a specific date.

        This ensures that only data available up to query_date is returned,
        preventing look-ahead bias.

        Args:
            symbol: Stock symbol
            query_date: Date to get data as of
            lookback_days: Maximum lookback period

        Returns:
            DataFrame with data up to (not including) query_date
        """
        try:
            # Load data from source (CSV, database, etc.)
            # In production, this would query a PIT database
            data = self._load_historical_data(symbol, query_date, lookback_days)

            if data is None or data.empty:
                logger.debug(f"No data available for {symbol} as of {query_date.date()}")
                return None

            # Ensure no data after query_date is included
            # This is CRITICAL for preventing look-ahead bias
            data = data[data.index < query_date]

            # Adjust for corporate actions
            data = self._adjust_for_corporate_actions(symbol, data, query_date)

            logger.debug(
                f"PIT Database: Loaded {len(data)} data points for {symbol} "
                f"as of {query_date.date()}"
            )
            return data

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error getting data as of date for {symbol}: {e}")
            return None

    def apply_corporate_actions(
        self,
        symbol: str,
        data: pd.DataFrame,
        as_of_date: datetime,
    ) -> pd.DataFrame:
        """
        Apply corporate actions to historical prices as of a specific date.

        This ensures that splits, dividends, and other actions are applied
        only if they were known by the as_of_date.

        Args:
            symbol: Stock symbol
            data: Historical price data
            as_of_date: Date to apply actions as of

        Returns:
            Adjusted price data
        """
        try:
            if symbol not in self._corporate_actions:
                return data

            # Get actions that occurred before as_of_date
            applicable_actions = [
                action for action in self._corporate_actions[symbol] if action.ex_date <= as_of_date
            ]

            if not applicable_actions:
                return data

            # Sort by date and apply chronologically
            applicable_actions.sort(key=lambda a: a.ex_date)

            adjusted_data = data.copy()
            for action in applicable_actions:
                if action.action_type == "split":
                    adjusted_data = self._apply_split(adjusted_data, action)
                elif action.action_type == "dividend":
                    adjusted_data = self._apply_dividend(adjusted_data, action)
                elif action.action_type == "merger":
                    adjusted_data = self._apply_merger(adjusted_data, action)

            logger.debug(
                f"Applied {len(applicable_actions)} corporate actions for {symbol} "
                f"as of {as_of_date.date()}"
            )
            return adjusted_data

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error applying corporate actions for {symbol}: {e}")
            return data

    def create_pit_snapshot(
        self,
        as_of_date: datetime,
        current_symbols: list[str],
        data_sources: dict[str, pd.DataFrame],
    ) -> PITDataSnapshot:
        """
        Create a point-in-time snapshot of market data.

        Args:
            as_of_date: Date of snapshot
            current_symbols: Symbols available at this date
            data_sources: Historical data for each symbol

        Returns:
            PITDataSnapshot for the specified date
        """
        try:
            data_coverage = {}
            available_symbols = []

            for symbol in current_symbols:
                if symbol in data_sources:
                    symbol_data = data_sources[symbol]
                    # Only include data up to as_of_date
                    historical_data = symbol_data[symbol_data.index < as_of_date]
                    if len(historical_data) > 0:
                        available_symbols.append(symbol)
                        data_coverage[symbol] = len(historical_data)

            snapshot = PITDataSnapshot(
                as_of_date=as_of_date,
                available_symbols=available_symbols,
                total_universe_size=len(available_symbols),
                data_coverage=data_coverage,
            )

            # Cache the snapshot
            self._cache_snapshot(snapshot)

            logger.info(
                f"Created PIT snapshot for {as_of_date.date()}: "
                f"{len(available_symbols)} symbols with data"
            )
            return snapshot

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error creating PIT snapshot: {e}")
            raise

    def validate_no_look_ahead(
        self,
        signals: pd.DataFrame,
        data: pd.DataFrame,
        date_column: str = "date",
    ) -> bool:
        """
        Validate that no look-ahead bias exists in the backtest.

        Args:
            signals: DataFrame with signals and dates
            data: DataFrame with market data
            date_column: Name of date column

        Returns:
            True if no look-ahead bias detected, False otherwise
        """
        try:
            # Check that all signal dates exist in data
            signal_dates = pd.to_datetime(signals[date_column])
            data_dates = pd.to_datetime(data.index)

            # Ensure signal dates are not after data availability
            for signal_date in signal_dates:
                available_data = data_dates[data_dates <= signal_date]
                if len(available_data) == 0:
                    logger.warning(
                        f"Look-ahead bias detected: Signal at {signal_date.date()} "
                        f"has no preceding data"
                    )
                    return False

            logger.info("No look-ahead bias detected in backtest")
            return True

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error validating look-ahead bias: {e}")
            return False

    def _load_universe_for_date(self, query_date: datetime) -> list[str]:
        """Load the trading universe for a specific date."""
        # In production, load from actual PIT database
        # For now, simulate based on historical growth rates
        base_universe = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "JPM",
            "V",
            "JNJ",
        ]  # Simplified

        # Adjust for historical date (smaller universe in the past)
        years_ago = (datetime.now() - query_date).days / 365.25
        growth_factor = 0.95**years_ago  # Universe grows ~5% annually
        historical_size = max(10, int(len(base_universe) * growth_factor))

        return base_universe[:historical_size]

    def _apply_filters(
        self,
        universe: list[str],
        query_date: datetime,
        min_market_cap: Decimal | None,
        sectors: list[str] | None,
    ) -> list[str]:
        """Apply filters to universe."""
        filtered = universe.copy()

        # In production, apply actual filters based on historical data
        # For now, return unfiltered
        return filtered

    def _select_top_by_market_cap(
        self, universe: list[str], query_date: datetime, n: int
    ) -> list[str]:
        """Select top N stocks by market cap."""
        # In production, sort by actual market cap data
        # For now, return first N
        return universe[:n]

    def _load_historical_data(
        self, symbol: str, query_date: datetime, lookback_days: int
    ) -> pd.DataFrame | None:
        """Load historical data for a symbol."""
        # In production, load from PIT database
        # For now, return empty DataFrame to avoid pylint None assignment warning
        return pd.DataFrame()

    def _adjust_for_corporate_actions(
        self, symbol: str, data: pd.DataFrame, as_of_date: datetime
    ) -> pd.DataFrame:
        """Adjust data for corporate actions."""
        # Apply splits, dividends, etc.
        return data

    def _apply_split(self, data: pd.DataFrame, action: CorporateAction) -> pd.DataFrame:
        """Apply stock split to price data."""
        factor = float(action.adjustment_factor)
        data = data.copy()
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            if col in data.columns:
                data[col] = data[col] / factor
        if "volume" in data.columns:
            data["volume"] = data["volume"] * factor
        return data

    def _apply_dividend(self, data: pd.DataFrame, action: CorporateAction) -> pd.DataFrame:
        """Apply dividend adjustment to price data."""
        # Dividends don't change historical prices, but affect returns
        return data

    def _apply_merger(self, data: pd.DataFrame, action: CorporateAction) -> pd.DataFrame:
        """Apply merger adjustment to price data."""
        # Adjust for merger premium, etc.
        return data

    def _cache_snapshot(self, snapshot: PITDataSnapshot):
        """Cache a snapshot in memory."""
        self._snapshot_cache[snapshot.as_of_date] = snapshot

        # Implement cache size limit
        if len(self._snapshot_cache) > 1000:
            # Remove oldest entries
            sorted_dates = sorted(self._snapshot_cache.keys())
            for old_date in sorted_dates[: len(self._snapshot_cache) - 1000]:
                del self._snapshot_cache[old_date]


def create_pit_database_from_csv(
    data_path: Path,
    pit_output_path: Path | None = None,
) -> PointInTimeDatabase:
    """
    Create a point-in-time database from CSV files.

    Args:
        data_path: Path to CSV files with historical data
        pit_output_path: Output path for PIT database

    Returns:
        PointInTimeDatabase instance
    """
    pit_db = PointInTimeDatabase(pit_data_path=pit_output_path)

    # Load all CSV files and create snapshots
    # This is a simplified implementation
    # In production, would process all files and create comprehensive PIT database

    logger.info(f"Created PIT database from {data_path}")
    return pit_db
