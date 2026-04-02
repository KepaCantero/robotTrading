from __future__ import annotations

# mypy: ignore-errors
"""
Data Sanity Layer - Prevents "Flash Crash" Problem

CRITICAL SRE COMPONENT: Validates market data before executing orders.

The Problem:
- Data provider sends erroneous price (e.g., spike to zero due to API error)
- System reads "Price: $0.00", stop-loss triggers instantly
- Sells everything at the worst possible moment
- This is a catastrophic failure scenario

The Solution:
- Multi-layer sanity checks before executing any order
- Validate against recent prices (deviation filter)
- Cross-check with second data source for anomalies
- Detect stale/frozen data feeds
- Reject prices that don't make sense

This layer sits BETWEEN data providers and trading logic.
All price data must pass through this validation.

Usage:
    sanity_layer = DataSanityLayer(
        primary_source=alpaca_client,
        secondary_source=yahoo_client,
        cache=redis_client
    )

    # Validate price before using it
    if await sanity_layer.validate_price("AAPL", Decimal("150.00")):
        await execute_stop_loss(...)
    else:
        logger.error("Price sanity check failed - NOT executing")
"""

import asyncio
import logging
import statistics
import tempfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


class SanityCheckResult(str, Enum):
    """Results of sanity checks."""

    PASS = "PASS"
    FAIL = "FAIL"  # Price rejected, don't execute
    WARNING = "WARNING"  # Price suspicious but not rejected
    STALE = "STALE"  # Data is stale/frozen


@dataclass
class PriceValidation:
    """Result of price validation."""

    symbol: str
    price: Decimal
    result: SanityCheckResult
    deviation_pct: Decimal | None = None
    confirmed_by_secondary: bool | None = None
    reason: str | None = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DataSanityLayer:
    """
    Data integrity validation layer.

    Multi-layer checks:
    1. Deviation filter: Reject if price changed >50% from recent avg
    2. Secondary confirmation: Confirm with second source if >20% deviation
    3. Stale detection: Detect frozen data feeds
    4. Logical checks: Reject impossible prices (zero, negative, etc.)

    Configuration:
        max_deviation_pct: Maximum allowed deviation from recent avg (default: 50%)
        confirmation_threshold_pct: Threshold for secondary confirmation (default: 20%)
        staleness_seconds: Consider data stale if older than this (default: 60s)
        min_samples: Minimum samples for deviation calculation (default: 5)
    """

    def __init__(
        self,
        primary_source: object,
        secondary_source: object | None = None,
        db_path: str | None = None,
        max_deviation_pct: Decimal | None = None,
        confirmation_threshold_pct: Decimal | None = None,
        staleness_seconds: int = 60,
        min_samples: int = 5,
    ):
        """
        Initialize sanity layer.

        Args:
            primary_source: Primary data source (broker API)
            secondary_source: Secondary data source for confirmation (optional)
            db_path: Path to cache database for historical prices
            max_deviation_pct: Maximum deviation from recent average (default: 50%)
            confirmation_threshold_pct: Threshold for secondary confirmation (default: 20%)
            staleness_seconds: Seconds before data considered stale (default: 60)
            min_samples: Minimum samples for deviation calculation (default: 5)
        """
        if max_deviation_pct is None:
            max_deviation_pct = Decimal("50.0")
        if confirmation_threshold_pct is None:
            confirmation_threshold_pct = Decimal("20.0")
        self.primary_source = primary_source
        self.secondary_source = secondary_source
        self._temp_dir: str | None = None
        self.db_path = db_path
        self.max_deviation_pct = max_deviation_pct
        self.confirmation_threshold_pct = confirmation_threshold_pct
        self.staleness_seconds = staleness_seconds
        self.min_samples = min_samples

        # In-memory cache for recent prices (fast access)
        self.price_cache: dict[str, deque] = {}
        self.timestamp_cache: dict[str, datetime] = {}

    def _get_db_path(self) -> str:
        """Get database path, creating a secure temp directory if none was provided."""
        if self.db_path is None:
            if self._temp_dir is None:
                self._temp_dir = tempfile.mkdtemp(prefix="sanity_cache_")
            self.db_path = str(Path(self._temp_dir) / "sanity_cache.db")
        return self.db_path

    async def validate_price(
        self, symbol: str, price: Decimal, source: str = "primary"
    ) -> PriceValidation:
        """
        Validate price against multiple sanity checks.

        CRITICAL: This must pass BEFORE executing any stop-loss or order.

        Args:
            symbol: Trading symbol
            price: Price to validate
            source: Data source name

        Returns:
            PriceValidation with result and reasoning
        """
        now = datetime.now(timezone.utc)

        # Check 1: Logical sanity (zero, negative, etc.)
        if not self._logical_sanity_check(price):
            return PriceValidation(
                symbol=symbol,
                price=price,
                result=SanityCheckResult.FAIL,
                reason=f"Price failed logical sanity check: {price}",
            )

        # Check 2: Stale data detection
        if await self._is_stale_data(symbol, now):
            return PriceValidation(
                symbol=symbol,
                price=price,
                result=SanityCheckResult.STALE,
                reason=f"Data is stale (> {self.staleness_seconds}s old)",
            )

        # Check 3: Deviation from recent prices
        recent_prices = await self._get_recent_prices(symbol, minutes=5)

        if len(recent_prices) >= self.min_samples:
            avg_price = statistics.mean(recent_prices)
            deviation_pct = abs(price - avg_price) / avg_price * 100

            # CRITICAL: Reject if deviation > 50%
            if deviation_pct > self.max_deviation_pct:
                logger.error(
                    f"Price sanity check FAILED: {symbol} price={price} "
                    f"vs avg={avg_price:.2f} deviation={deviation_pct:.1f}%"
                )
                return PriceValidation(
                    symbol=symbol,
                    price=price,
                    result=SanityCheckResult.FAIL,
                    deviation_pct=Decimal(f"{deviation_pct:.1f}"),
                    reason=f"Price deviation {deviation_pct:.1f}% exceeds threshold {self.max_deviation_pct}%",
                )

            # Warning if deviation > 20% (but confirm with secondary source)
            if deviation_pct > self.confirmation_threshold_pct and self.secondary_source:
                confirmed = await self._confirm_with_secondary_source(symbol, price)

                if not confirmed:
                    logger.error(f"Price NOT confirmed by secondary source: {symbol} price={price}")
                    return PriceValidation(
                        symbol=symbol,
                        price=price,
                        result=SanityCheckResult.FAIL,
                        deviation_pct=Decimal(f"{deviation_pct:.1f}"),
                        confirmed_by_secondary=False,
                        reason="High deviation and not confirmed by secondary source",
                    )
                else:
                    logger.warning(
                        f"Price confirmed by secondary source despite high deviation: "
                        f"{symbol} price={price}"
                    )
                    return PriceValidation(
                        symbol=symbol,
                        price=price,
                        result=SanityCheckResult.WARNING,
                        deviation_pct=Decimal(f"{deviation_pct:.1f}"),
                        confirmed_by_secondary=True,
                        reason="High deviation but confirmed by secondary source",
                    )

        # All checks passed
        await self._update_price_cache(symbol, price, now)
        return PriceValidation(
            symbol=symbol,
            price=price,
            result=SanityCheckResult.PASS,
            reason="All sanity checks passed",
        )

    def _logical_sanity_check(self, price: Decimal) -> bool:
        """
        Basic logical sanity checks.

        Reject if:
        - Price is zero
        - Price is negative
        - Price is unreasonably high (> $1,000,000 for stocks)
        """
        if price <= 0:
            logger.error(f"Price sanity check: Price is zero or negative: {price}")
            return False

        if price > Decimal("1000000"):
            logger.error(f"Price sanity check: Price unreasonably high: {price}")
            return False

        return True

    async def _is_stale_data(self, symbol: str, now: datetime) -> bool:
        """
        Check if data is stale (frozen feed).

        If we haven't received an update in staleness_seconds,
        the feed might be frozen.
        """
        if symbol not in self.timestamp_cache:
            # First time seeing this symbol
            return False

        last_update = self.timestamp_cache[symbol]
        age = (now - last_update).total_seconds()

        if age > self.staleness_seconds:
            logger.warning(f"Stale data detected: {symbol} last update {age:.0f}s ago")
            return True

        return False

    async def _get_recent_prices(self, symbol: str, minutes: int = 5) -> list[float]:
        """
        Get recent prices from cache.

        Returns list of recent prices for deviation calculation.
        """
        # Try in-memory cache first
        if symbol in self.price_cache:
            prices = list(self.price_cache[symbol])
            if len(prices) >= self.min_samples:
                return [float(p) for p in prices]

        # Fall back to database cache
        try:
            async with aiosqlite.connect(self._get_db_path()) as db:
                # Create table if not exists
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS price_cache (
                        symbol TEXT,
                        price REAL,
                        timestamp TEXT,
                        PRIMARY KEY (symbol, timestamp)
                    )
                """
                )

                # Get recent prices
                cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
                cursor = await db.execute(
                    """
                    SELECT price
                    FROM price_cache
                    WHERE symbol = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (symbol, cutoff, self.min_samples * 2),
                )

                rows = await cursor.fetchall()
                prices = [row[0] for row in rows]

                # Update in-memory cache
                if prices:
                    if symbol not in self.price_cache:
                        self.price_cache[symbol] = deque(maxlen=self.min_samples * 2)
                    for price in prices:
                        self.price_cache[symbol].append(Decimal(str(price)))

                return prices

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting recent prices from cache: {e}")
            return []

    async def _confirm_with_secondary_source(self, symbol: str, price: Decimal) -> bool:
        """
        Confirm price with secondary data source.

        Used when price deviation is suspicious but not definitively bad.

        Args:
            symbol: Trading symbol
            price: Price to confirm

        Returns:
            True if secondary source confirms similar price
        """
        if not self.secondary_source:
            logger.warning("No secondary source available for price confirmation")
            return False  # Can't confirm without secondary source

        try:
            # Get price from secondary source
            secondary_price = await self.secondary_source.get_price(symbol)

            if secondary_price is None:
                logger.warning(f"Secondary source has no price for {symbol}")
                return False

            # Check if prices are within 5% of each other
            diff_pct = abs(price - secondary_price) / price * 100

            if diff_pct <= 5.0:
                logger.info(
                    f"Secondary source confirms price: {symbol} "
                    f"primary={price} secondary={secondary_price} diff={diff_pct:.1f}%"
                )
                return True
            else:
                logger.warning(
                    f"Secondary source DOES NOT confirm: {symbol} "
                    f"primary={price} secondary={secondary_price} diff={diff_pct:.1f}%"
                )
                return False

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error confirming with secondary source: {e}")
            return False

    async def _update_price_cache(self, symbol: str, price: Decimal, timestamp: datetime):
        """Update price cache (memory and database)."""
        # Update in-memory cache
        if symbol not in self.price_cache:
            self.price_cache[symbol] = deque(maxlen=self.min_samples * 2)
        self.price_cache[symbol].append(price)
        self.timestamp_cache[symbol] = timestamp

        # Update database cache (async, don't wait)
        self._cache_task = asyncio.create_task(self._write_to_db_cache(symbol, price, timestamp))

    async def _write_to_db_cache(self, symbol: str, price: Decimal, timestamp: datetime):
        """Write price to database cache."""
        try:
            async with aiosqlite.connect(self._get_db_path()) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO price_cache (symbol, price, timestamp)
                    VALUES (?, ?, ?)
                """,
                    (symbol, float(price), timestamp.isoformat()),
                )
                await db.commit()

                # Prune old data
                cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
                await db.execute(
                    """
                    DELETE FROM price_cache WHERE timestamp < ?
                """,
                    (cutoff,),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error writing to price cache: {e}")


class SafeStopLossExecutor:
    """
    Stop-loss executor with data sanity checks.

    This wraps the stop-loss execution with price validation.
    No stop-loss will execute if price sanity checks fail.

    Usage:
        executor = SafeStopLossExecutor(sanity_layer, broker_client)

        # Safe stop-loss execution
        await executor.execute_stop_loss(position)

    This prevents the "flash crash" problem where erroneous prices
    trigger stop-losses at the worst possible moment.
    """

    def __init__(self, sanity_layer: DataSanityLayer, broker_client: object):
        """
        Initialize safe stop-loss executor.

        Args:
            sanity_layer: Data sanity validation layer
            broker_client: Broker API client
        """
        self.sanity_layer = sanity_layer
        self.broker = broker_client

    async def execute_stop_loss(
        self, position: dict[str, str | int | float | Decimal | None], stop_price: Decimal
    ) -> bool:
        """
        Execute stop-loss with price validation.

        CRITICAL: Validates current price BEFORE executing stop-loss.

        Args:
            position: Position data
            stop_price: Stop-loss trigger price

        Returns:
            True if stop-loss executed, False if rejected
        """
        symbol = position["symbol"]

        # Get current price
        current_price = await self._get_current_price(symbol)

        # Validate price before executing
        validation = await self.sanity_layer.validate_price(symbol, current_price)

        if validation.result == SanityCheckResult.FAIL:
            logger.critical(
                f"STOP-LOSS EXECUTION BLOCKED: {symbol} "
                f"price={current_price} reason={validation.reason}"
            )
            return False

        if validation.result == SanityCheckResult.STALE:
            logger.error(
                f"STOP-LOSS EXECUTION BLOCKED: {symbol} data is stale: {validation.reason}"
            )
            return False

        if validation.result == SanityCheckResult.WARNING:
            logger.warning(
                f"Stop-loss executing with warning: {symbol} "
                f"price={current_price} reason={validation.reason}"
            )
            # Continue anyway, but log warning

        # Price validated - execute stop-loss
        logger.info(f"Executing stop-loss for {symbol}: current={current_price} stop={stop_price}")

        try:
            await self.broker.close_position(
                symbol=symbol, quantity=float(position["quantity"]), side=position["side"]
            )

            logger.info(f"Stop-loss executed successfully: {symbol}")
            return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Stop-loss execution failed: {e}")
            return False

    async def _get_current_price(self, symbol: str) -> Decimal:
        """Get current price from primary source."""
        try:
            price = await self.broker.get_current_price(symbol)
            return Decimal(str(price))
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            raise
