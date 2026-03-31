"""
Real-Time Correlation Analyzer - Phase 2.4

Calculate real correlation from historical prices.

This module replaces simulated correlation (0.3 if same sector) with actual
correlation calculated from historical price movements using pandas for
efficient calculation.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

from app.domain.models.market_data import DataFrequency

logger = logging.getLogger(__name__)


@dataclass
class CorrelationConfig:
    """Configuration for correlation analyzer."""

    lookback_days: int = 60
    update_interval_seconds: float = 3600.0  # 1 hour
    min_data_points: int = 20
    cache_enabled: bool = True
    use_fallback: bool = True  # Use simulated correlation if unavailable
    fallback_value: float = 0.3
    max_cache_age_seconds: float = 7200.0  # 2 hours


@dataclass
class CorrelationCache:
    """Cache entry for correlation matrix."""

    matrix: pd.DataFrame
    timestamp: datetime
    symbols: set[str]

    def is_valid(self, max_age_seconds: float) -> bool:
        """Check if cache is still valid."""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < max_age_seconds


class CorrelationAnalyzer:
    """
    Calculate real correlation from historical prices.

    Replaces simulated correlation (0.3 if same sector) with actual
    correlation calculated from historical price movements.

    Features:
    - Uses pandas for efficient correlation calculation
    - Implements caching for performance
    - Background task for periodic updates
    - Fallback to simulated correlation if data unavailable
    """

    def __init__(
        self,
        data_service,
        config: Optional[CorrelationConfig] = None,
    ):
        """
        Initialize correlation analyzer.

        Args:
            data_service: Market data service for fetching historical prices
            config: Configuration options (uses defaults if not provided)
        """
        self.data_service = data_service
        self.config = config or CorrelationConfig()

        # Cache storage
        self._cache: Optional[CorrelationCache] = None
        self._cache_lock = asyncio.Lock()

        # Background update task
        self._update_task: Optional[asyncio.Task] = None
        self._update_loop_running = False

        # Statistics
        self._calculations_performed = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._fallback_used = 0

        # Symbol metadata for fallback correlation
        self._symbol_sectors: dict[str, str] = {}
        self._symbol_markets: dict[str, str] = {}
        self._symbol_asset_classes: dict[str, str] = {}

        logger.info(
            f"CorrelationAnalyzer initialized with lookback={self.config.lookback_days} days, "
            f"update_interval={self.config.update_interval_seconds}s"
        )

    async def calculate_correlation_matrix(
        self,
        symbols: list[str],
        lookback_days: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix from historical returns.

        Uses pandas for efficient calculation of Pearson correlation
        coefficients between all symbol pairs.

        Args:
            symbols: List of symbols to analyze
            lookback_days: Days of history (default from config)

        Returns:
            DataFrame with correlation matrix (symbols as both index and columns)

        Raises:
            ValueError: If symbols list is empty
            RuntimeError: If insufficient data available
        """
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        lookback = lookback_days or self.config.lookback_days

        logger.debug(f"Calculating correlation matrix for {len(symbols)} symbols")

        # Fetch historical prices for all symbols
        prices_dict = await self._fetch_historical_prices(symbols, lookback)

        if not prices_dict:
            logger.warning("No historical prices fetched, using fallback")
            if self.config.use_fallback:
                return self._generate_fallback_matrix(symbols)
            raise RuntimeError("No historical data available")

        # Check if we have at least 2 symbols (minimum for correlation)
        if len(prices_dict) < 2:
            logger.warning(f"Insufficient symbols with data: {len(prices_dict)} < 2")
            if self.config.use_fallback:
                return self._generate_fallback_matrix(symbols)
            raise RuntimeError("Insufficient data for correlation calculation")

        # Create DataFrame from prices
        prices_df = pd.DataFrame(prices_dict)

        # Calculate returns
        returns_df = self._calculate_returns(prices_df)

        # Calculate correlation matrix
        correlation_matrix = self._calculate_correlation(returns_df)

        self._calculations_performed += 1

        logger.info(
            f"Calculated correlation matrix for {len(symbols)} symbols "
            f"({len(correlation_matrix)}x{len(correlation_matrix)})"
        )

        return correlation_matrix

    async def update_correlation_cache(self, symbols: list[str]) -> None:
        """
        Update correlation cache.

        Fetches new data and calculates updated correlation matrix.
        Should be called periodically (e.g., every hour).

        Args:
            symbols: List of symbols to analyze
        """
        try:
            logger.debug(f"Updating correlation cache for {len(symbols)} symbols")

            # Calculate new correlation matrix
            correlation_matrix = await self.calculate_correlation_matrix(symbols)

            # Update cache
            async with self._cache_lock:
                self._cache = CorrelationCache(
                    matrix=correlation_matrix,
                    timestamp=datetime.now(timezone.utc),
                    symbols=set(symbols),
                )

            logger.debug("Correlation cache updated successfully")

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to update correlation cache: {e}")

    async def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get correlation between two symbols.

        First checks cache, then calculates if needed.
        Uses fallback if data unavailable.

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Try to get from cache first
        cached_matrix = self.get_cached_matrix()
        if cached_matrix is not None:
            try:
                if symbol1 in cached_matrix.index and symbol2 in cached_matrix.columns:
                    correlation = float(cached_matrix.loc[symbol1, symbol2])
                    self._cache_hits += 1
                    return correlation
            except (KeyError, ValueError) as e:
                logger.debug(f"Cache lookup failed: {e}")

        self._cache_misses += 1

        # Calculate on-demand if not in cache
        try:
            correlation_matrix = await self.calculate_correlation_matrix([symbol1, symbol2])
            correlation = float(correlation_matrix.loc[symbol1, symbol2])

            # Update cache with new calculation
            if self.config.cache_enabled:
                async with self._cache_lock:
                    self._cache = CorrelationCache(
                        matrix=correlation_matrix,
                        timestamp=datetime.now(timezone.utc),
                        symbols={symbol1, symbol2},
                    )

            return correlation

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Failed to calculate correlation: {e}, using fallback")

            # Use fallback if calculation failed
            self._fallback_used += 1
            return self._get_fallback_correlation(symbol1, symbol2)

    def get_cached_matrix(self) -> Optional[pd.DataFrame]:
        """
        Get cached correlation matrix.

        Returns the cached matrix if it exists and is still valid.
        Returns None otherwise.

        Note: This method does NOT increment cache_hits counter to avoid
        double counting when called from get_correlation().

        Returns:
            Cached correlation matrix or None
        """
        if not self.config.cache_enabled:
            return None

        if self._cache is None:
            return None

        if self._cache.is_valid(self.config.max_cache_age_seconds):
            return self._cache.matrix.copy()

        return None

    async def start_background_updates(self, symbols: list[str]) -> None:
        """
        Start background task for periodic correlation updates.

        Args:
            symbols: List of symbols to track
        """
        if self._update_loop_running:
            logger.warning("Background update loop already running")
            return

        self._update_loop_running = True
        self._update_task = asyncio.create_task(self._update_loop(set(symbols)))

        logger.info(
            f"Started background correlation updates (interval: "
            f"{self.config.update_interval_seconds}s)"
        )

    async def stop_background_updates(self) -> None:
        """Stop background task for periodic correlation updates."""
        if not self._update_loop_running:
            return

        self._update_loop_running = False

        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
            self._update_task = None

        logger.info("Stopped background correlation updates")

    def set_symbol_metadata(
        self,
        symbol: str,
        sector: Optional[str] = None,
        market: Optional[str] = None,
        asset_class: Optional[str] = None,
    ) -> None:
        """
        Set metadata for a symbol for fallback correlation calculation.

        Args:
            symbol: Symbol to set metadata for
            sector: Sector classification (e.g., "Technology", "Healthcare")
            market: Market classification (e.g., "US", "EU", "Asia")
            asset_class: Asset class (e.g., "stock", "bond", "crypto", "forex")
        """
        if sector:
            self._symbol_sectors[symbol] = sector
        if market:
            self._symbol_markets[symbol] = market
        if asset_class:
            self._symbol_asset_classes[symbol] = asset_class

    async def _fetch_historical_prices(
        self,
        symbols: list[str],
        lookback_days: int,
    ) -> dict[str, pd.Series]:
        """
        Fetch historical prices for multiple symbols.

        Args:
            symbols: List of symbols to fetch
            lookback_days: Number of days of history to fetch

        Returns:
            Dictionary mapping symbol to price series (indexed by date)
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days)

        prices_dict = {}

        # Fetch data for each symbol
        for symbol in symbols:
            try:
                historical_data = await self.data_service.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=DataFrequency.DAILY,
                )

                if historical_data:
                    # Convert to pandas Series
                    dates = [pd.to_datetime(data.timestamp) for data in historical_data]
                    close_prices = [float(data.close) for data in historical_data]

                    if len(close_prices) >= self.config.min_data_points:
                        prices_dict[symbol] = pd.Series(close_prices, index=dates, name=symbol)
                        logger.debug(f"Fetched {len(close_prices)} data points for {symbol}")
                else:
                    logger.warning(f"No historical data for {symbol}")

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}")

        logger.info(f"Fetched historical prices for {len(prices_dict)}/{len(symbols)} symbols")

        return prices_dict

    def _calculate_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate percentage returns from prices.

        Uses pandas pct_change() for efficient calculation.

        Args:
            prices: DataFrame with price series (columns = symbols)

        Returns:
            DataFrame with percentage returns
        """
        # Calculate percentage change
        returns = prices.pct_change()

        # Drop first row (NaN from pct_change)
        returns = returns.dropna()

        return returns

    def _calculate_correlation(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Pearson correlation matrix.

        Uses pandas corr() method for efficient calculation.

        Args:
            returns: DataFrame with return series (columns = symbols)

        Returns:
            DataFrame with correlation matrix
        """
        # Calculate Pearson correlation
        correlation_matrix = returns.corr(method="pearson")

        # Fill NaN values with 0 (no correlation)
        correlation_matrix = correlation_matrix.fillna(0)

        return correlation_matrix

    def _generate_fallback_matrix(self, symbols: list[str]) -> pd.DataFrame:
        """
        Generate fallback correlation matrix using simulated values.

        Args:
            symbols: List of symbols

        Returns:
            DataFrame with fallback correlation matrix
        """
        n = len(symbols)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i, j] = 1.0  # Perfect correlation with self
                else:
                    matrix[i, j] = self._get_fallback_correlation(symbols[i], symbols[j])

        return pd.DataFrame(matrix, index=symbols, columns=symbols)

    def _get_fallback_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get simulated correlation if real data unavailable.

        Fallback logic:
        - Same sector: 0.5
        - Same market (US): 0.3
        - Same asset class (stocks): 0.2
        - Different: 0.1

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            Fallback correlation value
        """
        # Check same sector
        if (
            symbol1 in self._symbol_sectors
            and symbol2 in self._symbol_sectors
            and self._symbol_sectors[symbol1] == self._symbol_sectors[symbol2]
        ):
            return 0.5

        # Check same market
        if (
            symbol1 in self._symbol_markets
            and symbol2 in self._symbol_markets
            and self._symbol_markets[symbol1] == self._symbol_markets[symbol2]
        ):
            return 0.3

        # Check same asset class
        if (
            symbol1 in self._symbol_asset_classes
            and symbol2 in self._symbol_asset_classes
            and self._symbol_asset_classes[symbol1] == self._symbol_asset_classes[symbol2]
        ):
            return 0.2

        # Default fallback
        return self.config.fallback_value

    async def _update_loop(self, symbols: set[str]) -> None:
        """
        Background loop for periodic updates.

        Runs continuously, updating correlation cache at configured intervals.

        Args:
            symbols: Set of symbols to track
        """
        logger.info("Starting correlation update loop")

        while self._update_loop_running:
            try:
                # Update correlation cache
                await self.update_correlation_cache(list(symbols))

                # Wait for next update interval
                await asyncio.sleep(self.config.update_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Correlation update loop cancelled")
                break

            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error in correlation update loop: {e}")
                # Wait before retrying
                await asyncio.sleep(60)

    def get_statistics(self) -> dict[str, any]:
        """
        Get correlation analyzer statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "calculations_performed": self._calculations_performed,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "fallback_used": self._fallback_used,
            "cache_enabled": self.config.cache_enabled,
            "background_updates_running": self._update_loop_running,
            "cached_symbols": list(self._cache.symbols) if self._cache else [],
            "cache_age_seconds": (
                (datetime.now(timezone.utc) - self._cache.timestamp).total_seconds()
                if self._cache
                else None
            ),
        }

    def clear_cache(self) -> None:
        """Clear the correlation cache."""
        self._cache = None
        logger.info("Correlation cache cleared")
