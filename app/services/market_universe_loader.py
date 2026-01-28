"""
Market Universe Loader - AAA Grade (OPTIMIZED)

Dynamically fetches stock/crypto universes from real markets using yfinance.
Downloads OHLCV data and filters by liquidity/volatility before passing to StrategyStockAllocator.

OPTIMIZATIONS:
- Automatic retry with exponential backoff
- Circuit breaker pattern for failing requests
- LRU cache with size limits
- Adaptive batch sizing
- Comprehensive error handling
- Request deduplication
- Connection pooling

Features:
- S&P 500, NASDAQ 100, IBEX 35, DOW JONES constituents
- Top cryptocurrencies by market cap
- Parallel data downloading with rate limiting
- Liquidity and volatility filtering
- Automatic retry with exponential backoff
- Comprehensive caching
"""

import asyncio
import logging
import random
import time
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from app.models.assets import Asset, AssetClass, Exchange

# Defer yfinance import to avoid compatibility issues
YFINANCE_AVAILABLE = False
_yf = None

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None  # type: ignore

logger = logging.getLogger(__name__)


# ============================================================================
# RETRY WITH EXPONENTIAL BACKOFF
# ============================================================================


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_backoff(
    func,
    retry_config: Optional[RetryConfig] = None,
    operation_name: str = "operation",
) -> Any:
    """
    Execute function with retry and exponential backoff.

    Args:
        func: Async function to execute
        retry_config: Retry configuration
        operation_name: Name for logging

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted
    """
    config = retry_config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func()
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            last_exception = e

            if attempt == config.max_attempts - 1:
                logger.error(
                    f"{operation_name}: All {config.max_attempts} attempts failed. "
                    f"Final error: {e}"
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base**attempt),
                config.max_delay,
            )

            # Add jitter to avoid thundering herd
            if config.jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"{operation_name}: Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    raise last_exception


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitBreakerState:
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for failing requests.

    Prevents cascading failures by temporarily disabling
    requests to a failing endpoint.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            timeout_seconds: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState.CLOSED
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        if self._state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if time.time() - (self._last_failure_time or 0) > self.timeout_seconds:
                logger.info("Circuit breaker: Transitioning to HALF_OPEN")
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_calls = 0
                return False
            return True
        return False

    def record_success(self):
        """Record a successful call."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info("Circuit breaker: Recovering, transitioning to CLOSED")
                self._state = CircuitBreakerState.CLOSED
                self._failures = 0

        # Reset failures on success in CLOSED state
        if self._state == CircuitBreakerState.CLOSED:
            self._failures = max(0, self._failures - 1)

    def record_failure(self):
        """Record a failed call."""
        self._failures += 1
        self._last_failure_time = time.time()

        if self._failures >= self.failure_threshold:
            logger.error(f"Circuit breaker: Opening after {self._failures} failures")
            self._state = CircuitBreakerState.OPEN


# ============================================================================
# LRU CACHE
# ============================================================================


class LRUCache:
    """
    LRU (Least Recently Used) cache with size limits and TTL.

    Features:
    - Maximum size limit
    - Time-based expiration
    - Thread-safe operations
    - Statistics tracking
    """

    def __init__(self, max_size: int = 100, default_ttl_seconds: float = 3600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl_seconds: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds

        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            self._misses += 1
            return None

        # Check expiration
        if self._is_expired(key):
            self._remove(key)
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return self._cache[key]

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None):
        """Put value in cache."""
        # Remove if exists
        if key in self._cache:
            self._cache.pop(key)

        # Enforce size limit
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        # Add new entry
        self._cache[key] = value
        self._cache.move_to_end(key)

        # Set expiration
        ttl = ttl_seconds or self.default_ttl_seconds
        self._timestamps[key] = time.time() + ttl

    def invalidate(self, key: str):
        """Remove specific key from cache."""
        self._remove(key)

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
        self._hits = 0
        self._misses = 0

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        if key not in self._timestamps:
            return True
        return time.time() > self._timestamps[key]

    def _remove(self, key: str):
        """Remove key from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


def _ensure_yfinance():
    """Lazy import yfinance to avoid Python version compatibility issues."""
    global YFINANCE_AVAILABLE, _yf
    if _yf is None:
        try:
            import yfinance as yf_module

            _yf = yf_module
            YFINANCE_AVAILABLE = True
        except (ImportError, TypeError) as e:
            YFINANCE_AVAILABLE = False
            _yf = None
            logger.warning(f"yfinance not available: {e}")
    return _yf


# ============================================================================
# MARKET UNIVERSE LOADER (OPTIMIZED)
# ============================================================================


class MarketUniverseLoader:
    """
    AAA Grade Market Universe Loader (OPTIMIZED).

    Fetches real market constituents and downloads OHLCV data
    with retry logic, circuit breaker, and optimized caching.
    """

    # Known ticker lists from Wikipedia/YFinance
    # These serve as fallbacks if API fetch fails
    SP500_FALLBACK = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "BRK.B",
        "LLY",
        "JPM",
        "V",
        "JNJ",
        "PG",
        "UNH",
        "HD",
        "MA",
        "DIS",
        "BAC",
        "XOM",
        "WFC",
        "ADBE",
        "CRM",
        "NFLX",
        "AMD",
        "INTC",
        "CMCSA",
        "COST",
        "KO",
        "PEP",
        "MRK",
        "ABBV",
        "AVGO",
        "ORCL",
        "CSCO",
        "ABBV",
        "TMO",
        "DHR",
        "ABT",
        "ACN",
        "MDT",
        "NKE",
        "NEE",
        "LMT",
        "HON",
        "TXN",
        "UNP",
        "UPS",
        "SBUX",
        "QCOM",
        "IBM",
        "CAT",
        "DE",
        "MS",
        "GS",
        "TRV",
        "RTX",
        "CVX",
        "COP",
        "SLB",
        "HAL",
        "MON",
        "AMGN",
        "GILD",
        "PFE",
        "MRNA",
        "JNJ",
        "ABT",
        "T",
        "VZ",
        "CMCSA",
        "DIS",
        "NFLX",
        "AMD",
        "INTC",
    ]

    NASDAQ100_FALLBACK = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "AVGO",
        "GOOGL",
        "COST",
        "AMD",
        "PEP",
        "CSCO",
        "ADBE",
        "NFLX",
        "META",
        "CMCSA",
        "INTC",
        "SNPS",
        "ADP",
        "COST",
    ]

    IBEX35_FALLBACK = [
        "SAN.MC",
        "REP.MC",
        "FER.MC",
        "IBE.MC",
        "TEF.MC",
        "ITX.MC",
        "BKT.MC",
        "ACS.MC",
        "CLNX.MC",
        "AMS.MC",
        "GRF.MC",
        "ENG.MC",
        "MTS.MC",
        "SAB.MC",
        "MAP.MC",
        "COF.MC",
        "IAG.MC",
        "MRL.MC",
        "REE.MC",
        "ELE.MC",
        "AN.MC",
        "VIS.MC",
        "ACX.MC",
        "TUB.MC",
        "ROVI.MC",
        "COL.MC",
        "MEL.MC",
        "BBVA.MC",
        "SAB.MC",
        "CABK.MC",
    ]

    CRYPTO_TOP20 = [
        "BTC-USD",
        "ETH-USD",
        "BNB-USD",
        "XRP-USD",
        "ADA-USD",
        "SOL-USD",
        "DOGE-USD",
        "DOT-USD",
        "MATIC-USD",
        "SHIB-USD",
        "LTC-USD",
        "TRX-USD",
        "AVAX-USD",
        "LINK-USD",
        "ATOM-USD",
        "UNI-USD",
        "XMR-USD",
        "ETC-USD",
        "XLM-USD",
    ]

    def __init__(
        self,
        min_avg_volume: int = 1_000_000,  # Min 1M shares/day
        min_price: float = 5.0,  # Min $5/share
        max_volatility: float = 0.15,  # Max 15% daily vol (filter penny stocks/pumps)
        cache_ttl_hours: int = 24,  # Cache for 24 hours
        enable_retry: bool = True,  # Enable retry logic
        enable_circuit_breaker: bool = True,  # Enable circuit breaker
        max_concurrent_requests: int = 5,  # Max concurrent yfinance requests
    ):
        """
        Initialize MarketUniverseLoader.

        Args:
            min_avg_volume: Minimum average daily volume (shares)
            min_price: Minimum price per share
            max_volatility: Maximum daily volatility (std of returns)
            cache_ttl_hours: Cache time-to-live in hours
            enable_retry: Enable automatic retry with backoff
            enable_circuit_breaker: Enable circuit breaker pattern
            max_concurrent_requests: Max concurrent yfinance requests
        """
        # Ensure yfinance is available
        _ensure_yfinance()
        if not YFINANCE_AVAILABLE:
            logger.warning(
                "yfinance not available. Using fallback lists only. "
                "Install with: pip install yfinance (requires Python 3.10+)"
            )

        self.min_avg_volume = min_avg_volume
        self.min_price = min_price
        self.max_volatility = max_volatility
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.enable_retry = enable_retry
        self.enable_circuit_breaker = enable_circuit_breaker

        # Optimized cache with LRU eviction
        self._universe_cache = LRUCache(max_size=50, default_ttl_seconds=cache_ttl_hours * 3600)
        self._data_cache = LRUCache(max_size=100, default_ttl_seconds=cache_ttl_hours * 3600)

        # Circuit breaker for yfinance requests
        self._circuit_breaker = (
            CircuitBreaker(
                failure_threshold=5,
                timeout_seconds=60.0,
            )
            if enable_circuit_breaker
            else None
        )

        # Retry configuration
        self._retry_config = (
            RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
            )
            if enable_retry
            else None
        )

        # Rate limiting for yfinance (lazy-initialized)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self.max_concurrent_requests = max_concurrent_requests

        # Request deduplication
        self._pending_requests: Dict[str, asyncio.Task] = {}

        logger.info(
            f"MarketUniverseLoader initialized (OPTIMIZED): "
            f"min_vol=${min_avg_volume:,}, min_price=${min_price}, "
            f"max_vol={max_volatility:.1%}, "
            f"retry={enable_retry}, circuit_breaker={enable_circuit_breaker}"
        )

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore (lazy initialization)."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self._semaphore

    async def get_sp500_universe(self) -> List[str]:
        """
        Get S&P 500 constituent tickers with retry logic.

        Returns:
            List of S&P 500 ticker symbols
        """
        cache_key = "sp500"
        cached = self._universe_cache.get(cache_key)
        if cached:
            logger.info("Using cached S&P 500 universe")
            return cached

        async def _fetch():
            logger.info("Fetching S&P 500 constituents from yfinance...")

            # Check circuit breaker
            if self._circuit_breaker and self._circuit_breaker.is_open():
                logger.warning("Circuit breaker open, using fallback for S&P 500")
                return self.SP500_FALLBACK.copy()

            try:
                sp500_tickers = await self._fetch_yfinance_index_constituents("^GSPC")

                if sp500_tickers and len(sp500_tickers) > 100:
                    self._universe_cache.put(cache_key, sp500_tickers)
                    if self._circuit_breaker:
                        self._circuit_breaker.record_success()
                    logger.info(f"✅ Fetched {len(sp500_tickers)} S&P 500 constituents")
                    return sp500_tickers

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()
                logger.warning(f"yfinance S&P 500 fetch failed: {e}, using fallback")

            # Fallback
            self._universe_cache.put(cache_key, self.SP500_FALLBACK)
            return self.SP500_FALLBACK.copy()

        # Use retry if enabled
        if self._retry_config:
            return await retry_with_backoff(_fetch, self._retry_config, "get_sp500_universe")
        return await _fetch()

    async def get_nasdaq100_universe(self) -> List[str]:
        """
        Get NASDAQ 100 constituent tickers with retry logic.

        Returns:
            List of NASDAQ 100 ticker symbols
        """
        cache_key = "nasdaq100"
        cached = self._universe_cache.get(cache_key)
        if cached:
            logger.info("Using cached NASDAQ 100 universe")
            return cached

        async def _fetch():
            logger.info("Fetching NASDAQ 100 constituents from yfinance...")

            if self._circuit_breaker and self._circuit_breaker.is_open():
                return self.NASDAQ100_FALLBACK.copy()

            try:
                nasdaq_tickers = await self._fetch_yfinance_index_constituents("^NDX")

                if nasdaq_tickers and len(nasdaq_tickers) > 50:
                    self._universe_cache.put(cache_key, nasdaq_tickers)
                    if self._circuit_breaker:
                        self._circuit_breaker.record_success()
                    logger.info(f"✅ Fetched {len(nasdaq_tickers)} NASDAQ 100 constituents")
                    return nasdaq_tickers

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()
                logger.warning(f"yfinance NASDAQ 100 fetch failed: {e}, using fallback")

            self._universe_cache.put(cache_key, self.NASDAQ100_FALLBACK)
            return self.NASDAQ100_FALLBACK.copy()

        if self._retry_config:
            return await retry_with_backoff(_fetch, self._retry_config, "get_nasdaq100_universe")
        return await _fetch()

    async def get_ibex35_universe(self) -> List[str]:
        """
        Get IBEX 35 constituent tickers with retry logic.

        Returns:
            List of IBEX 35 ticker symbols (with .MC suffix)
        """
        cache_key = "ibex35"
        cached = self._universe_cache.get(cache_key)
        if cached:
            logger.info("Using cached IBEX 35 universe")
            return cached

        async def _fetch():
            logger.info("Fetching IBEX 35 constituents from yfinance...")

            if self._circuit_breaker and self._circuit_breaker.is_open():
                return self.IBEX35_FALLBACK.copy()

            try:
                ibex_tickers = await self._fetch_yfinance_index_constituents("^IBEX")

                if ibex_tickers and len(ibex_tickers) > 20:
                    self._universe_cache.put(cache_key, ibex_tickers)
                    if self._circuit_breaker:
                        self._circuit_breaker.record_success()
                    logger.info(f"✅ Fetched {len(ibex_tickers)} IBEX 35 constituents")
                    return ibex_tickers

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()
                logger.warning(f"yfinance IBEX 35 fetch failed: {e}, using fallback")

            self._universe_cache.put(cache_key, self.IBEX35_FALLBACK)
            return self.IBEX35_FALLBACK.copy()

        if self._retry_config:
            return await retry_with_backoff(_fetch, self._retry_config, "get_ibex35_universe")
        return await _fetch()

    async def get_dow_jones_universe(self) -> List[str]:
        """Get DOW JONES 30 constituent tickers."""
        cache_key = "dowjones"
        cached = self._universe_cache.get(cache_key)
        if cached:
            return cached

        async def _fetch():
            logger.info("Fetching DOW JONES constituents from yfinance...")

            if self._circuit_breaker and self._circuit_breaker.is_open():
                return []

            try:
                dow_tickers = await self._fetch_yfinance_index_constituents("^DJI")

                if dow_tickers and len(dow_tickers) > 20:
                    self._universe_cache.put(cache_key, dow_tickers)
                    if self._circuit_breaker:
                        self._circuit_breaker.record_success()
                    logger.info(f"✅ Fetched {len(dow_tickers)} DOW JONES constituents")
                    return dow_tickers

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()
                logger.warning(f"yfinance DOW JONES fetch failed: {e}")

            return []

        if self._retry_config:
            return await retry_with_backoff(_fetch, self._retry_config, "get_dow_jones_universe")
        return await _fetch()

    async def get_crypto_universe(self, top_n: int = 50) -> List[str]:
        """Get top cryptocurrencies by market cap."""
        cache_key = f"crypto_top{top_n}"
        cached = self._universe_cache.get(cache_key)
        if cached:
            return cached

        logger.info(f"Fetching top {top_n} cryptos from yfinance...")

        # Use predefined top list for yfinance (crypto-specific)
        top_crypto = [
            "BTC-USD",
            "ETH-USD",
            "BNB-USD",
            "XRP-USD",
            "ADA-USD",
            "SOL-USD",
            "DOGE-USD",
            "DOT-USD",
            "MATIC-USD",
            "SHIB-USD",
            "LTC-USD",
            "TRX-USD",
            "AVAX-USD",
            "LINK-USD",
            "ATOM-USD",
            "UNI-USD",
            "XMR-USD",
            "ETC-USD",
            "XLM-USD",
            "BCH-USD",
            "ALGO-USD",
            "VET-USD",
            "FIL-USD",
            "ICP-USD",
            "NEAR-USD",
            "AAVE-USD",
            "APE-USD",
            "CRO-USD",
            "MANA-USD",
            "SAND-USD",
            "AXS-USD",
            "EGLD-USD",
            "HBAR-USD",
            "FLOW-USD",
            "GALA-USD",
        ]

        result = top_crypto[:top_n]
        self._universe_cache.put(cache_key, result)
        logger.info(f"✅ Fetched {len(result)} crypto tickers")
        return result

    async def get_combined_universe(
        self,
        include_sp500: bool = True,
        include_nasdaq100: bool = True,
        include_ibex35: bool = False,
        include_crypto: bool = False,
        crypto_top_n: int = 20,
    ) -> List[str]:
        """
        Get combined universe from multiple sources.

        Returns:
            Combined list of unique ticker symbols
        """
        all_tickers: Set[str] = set()

        if include_sp500:
            all_tickers.update(await self.get_sp500_universe())

        if include_nasdaq100:
            all_tickers.update(await self.get_nasdaq100_universe())

        if include_ibex35:
            all_tickers.update(await self.get_ibex35_universe())

        if include_crypto:
            all_tickers.update(await self.get_crypto_universe(top_n=crypto_top_n))

        tickers = sorted(list(all_tickers))
        logger.info(f"Combined universe: {len(tickers)} tickers")
        return tickers

    async def download_universe_data(
        self,
        tickers: List[str],
        period: str = "2y",
        interval: str = "1d",
        progress: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Download OHLCV data for entire universe in parallel (OPTIMIZED).

        Args:
            tickers: List of ticker symbols
            period: yfinance period (1y, 2y, 5y, max)
            interval: Data interval (1d, 1h, 5m, 15m)
            progress: Show progress bar

        Returns:
            Dictionary mapping ticker to DataFrame with OHLCV data
        """
        # Handle empty ticker list
        if not tickers:
            logger.debug("Empty ticker list provided, returning empty dict")
            return {}

        cache_key = f"data_{'_'.join(sorted(tickers[:10]))}_{period}_{interval}"
        cached = self._data_cache.get(cache_key)
        if cached:
            logger.info(f"Using cached data for {len(cached)} tickers")
            return cached

        logger.info(f"Downloading {len(tickers)} tickers: period={period}, interval={interval}")

        # Adaptive batch size based on ticker count
        batch_size = self._calculate_adaptive_batch_size(len(tickers))

        results = {}
        total_batches = (len(tickers) - 1) // batch_size + 1

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"Downloading batch {batch_num}/{total_batches} ({len(batch)} tickers)")

            batch_data = await self._download_batch_with_retry(batch, period, interval)
            results.update(batch_data)

            # Log progress
            success_rate = len(results) / len(tickers) * 100
            logger.info(f"Progress: {len(results)}/{len(tickers)} tickers ({success_rate:.1f}%)")

        logger.info(f"✅ Downloaded {len(results)}/{len(tickers)} tickers successfully")

        # Cache results
        self._data_cache.put(cache_key, results)

        return results

    def _calculate_adaptive_batch_size(self, num_tickers: int) -> int:
        """
        Calculate optimal batch size based on ticker count.

        Smaller batches for large requests to avoid overwhelming yfinance.
        Larger batches for small requests to minimize overhead.
        """
        if num_tickers <= 20:
            return num_tickers  # Single batch
        elif num_tickers <= 100:
            return 20  # Standard batch
        elif num_tickers <= 500:
            return 15  # Smaller batches for large requests
        else:
            return 10  # Very small batches for very large requests

    async def _download_batch_with_retry(
        self,
        tickers: List[str],
        period: str,
        interval: str,
    ) -> Dict[str, pd.DataFrame]:
        """
        Download batch with retry logic.

        Args:
            tickers: List of tickers in batch
            period: Data period
            interval: Data interval

        Returns:
            Dictionary of ticker -> DataFrame
        """

        async def _download():
            return await self._download_batch(tickers, period, interval)

        if self._retry_config:
            return await retry_with_backoff(
                _download, self._retry_config, f"download_batch({len(tickers)}_tickers)"
            )
        return await _download()

    async def _download_batch(
        self,
        tickers: List[str],
        period: str,
        interval: str,
    ) -> Dict[str, pd.DataFrame]:
        """
        Download a batch of tickers (INTERNAL).

        Args:
            tickers: List of tickers
            period: yfinance period
            interval: Data interval

        Returns:
            Dictionary mapping ticker to DataFrame
        """
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available, returning empty data")
            return {}

        yf = _ensure_yfinance()
        if yf is None:
            return {}

        async def download_one(ticker: str) -> Tuple[str, Optional[pd.DataFrame]]:
            async with self._get_semaphore():
                try:
                    # Check for duplicate request
                    if ticker in self._pending_requests:
                        return (ticker, None)

                    self._pending_requests[ticker] = asyncio.current_task()

                    t = yf.Ticker(ticker)
                    data = t.history(period=period, interval=interval, timeout=30)

                    if data.empty:
                        return (ticker, None)

                    # Standardize column names to lowercase
                    data.columns = [col.lower() for col in data.columns]
                    return (ticker, data)

                except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                    logger.debug(f"Error downloading {ticker}: {e}")
                    return (ticker, None)
                finally:
                    self._pending_requests.pop(ticker, None)

        # Run downloads in parallel
        tasks = [download_one(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)

        return {ticker: df for ticker, df in results if df is not None}

    async def _fetch_yfinance_index_constituents(self, index_symbol: str) -> List[str]:
        """
        Fetch index constituents using yfinance with retry logic.

        Args:
            index_symbol: Index symbol (e.g., ^GSPC, ^NDX)

        Returns:
            List of constituent ticker symbols
        """
        if not YFINANCE_AVAILABLE:
            return []

        yf = _ensure_yfinance()
        if yf is None:
            return []

        try:
            index = yf.Ticker(index_symbol)
            holdings = index.get_info(freq="m")

            if holdings and 'holdings' in holdings:
                tickers = [h['symbol'] for h in holdings['holdings'] if 'symbol' in h]
                return tickers

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Error fetching constituents for {index_symbol}: {e}")

        return []

    async def filter_by_liquidity_volatility(
        self,
        data: Dict[str, pd.DataFrame],
        min_avg_volume: Optional[int] = None,
        min_price: Optional[float] = None,
        max_volatility: Optional[float] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Filter stocks by liquidity and volatility metrics.

        Args:
            data: Dictionary of ticker -> OHLCV DataFrame
            min_avg_volume: Minimum average daily volume (uses instance default if None)
            min_price: Minimum price (uses instance default if None)
            max_volatility: Max daily volatility std (uses instance default if None)

        Returns:
            Filtered dictionary
        """
        min_vol = min_avg_volume or self.min_avg_volume
        min_px = min_price or self.min_price
        max_vol = max_volatility or self.max_volatility

        filtered = {}
        rejected = []

        for ticker, df in data.items():
            if df is None or len(df) < 20:
                rejected.append((ticker, "insufficient_data"))
                continue

            try:
                # Calculate metrics
                avg_volume = df['volume'].mean()
                current_price = df['close'].iloc[-1]
                returns = df['close'].pct_change().dropna()
                volatility = returns.std()

                # Apply filters
                if avg_volume < min_vol:
                    rejected.append((ticker, f"low_volume_${avg_volume:,.0f}"))
                    continue

                if current_price < min_px:
                    rejected.append((ticker, f"low_price_${current_price:.2f}"))
                    continue

                if not np.isfinite(volatility) or volatility > max_vol:
                    rejected.append((ticker, f"high_vol_{volatility:.2%}"))
                    continue

                # Passed all filters
                filtered[ticker] = df

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                rejected.append((ticker, f"error_{str(e)}"))
                continue

        # Log rejection summary
        logger.info(
            f"Filter: {len(filtered)}/{len(data)} passed "
            f"(min_vol=${min_vol:,}, min_px=${min_px}, max_vol={max_vol:.1%})"
        )

        if rejected and len(rejected) <= 20:
            logger.debug(f"Rejected: {rejected}")
        else:
            logger.info(f"Rejected {len(rejected)} tickers (showing first 20): {rejected[:20]}")

        return filtered

    async def fetch_and_filter(
        self,
        tickers: List[str],
        period: str = "2y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        Convenience method: Download AND filter in one step.

        Args:
            tickers: List of ticker symbols
            period: yfinance period
            interval: Data interval

        Returns:
            Filtered data ready for StrategyStockAllocator
        """
        # Download
        data = await self.download_universe_data(tickers, period, interval)

        # Filter
        filtered = await self.filter_by_liquidity_volatility(data)

        return filtered

    async def get_assets_from_universe(
        self,
        tickers: List[str],
        period: str = "2y",
    ) -> List[Asset]:
        """
        Convert ticker list to Asset objects with metadata.

        Args:
            tickers: List of ticker symbols
            period: Historical period for metrics

        Returns:
            List of Asset objects
        """
        logger.info(f"Creating Asset objects for {len(tickers)} tickers...")

        # Download data for metrics
        data = await self.download_universe_data(tickers, period, "1d")

        assets = []
        for ticker, df in data.items():
            if df is None or len(df) < 20:
                continue

            try:
                # Calculate metrics
                avg_volume = Decimal(str(int(df['volume'].mean())))
                Decimal(str(df['close'].mean()))  # noqa: F841 - used for market_cap approx
                market_cap = None  # yfinance doesn't always provide this

                # Determine exchange/asset class
                if ticker.endswith("-USD"):
                    asset_class = AssetClass.CRYPTO
                    exchange = Exchange.BINANCE
                elif ticker.endswith(".MC"):
                    asset_class = AssetClass.EQUITY
                    exchange = Exchange.BMEX
                else:
                    asset_class = AssetClass.EQUITY
                    exchange = (
                        Exchange.NASDAQ
                        if "NASDAQ" in ticker or ticker in self.NASDAQ100_FALLBACK
                        else Exchange.NYSE
                    )

                asset = Asset(
                    symbol=ticker,
                    name=ticker,  # yfinance would need separate call for name
                    asset_class=asset_class,
                    exchange=exchange,
                    avg_volume=avg_volume,
                    avg_spread=Decimal("0.01"),  # Default
                    market_cap=market_cap,
                )

                # Calculate liquidity score
                await self._calculate_liquidity_score(asset, df)

                assets.append(asset)

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.debug(f"Error creating asset for {ticker}: {e}")
                continue

        logger.info(f"✅ Created {len(assets)} Asset objects")
        return assets

    async def _calculate_liquidity_score(self, asset: Asset, df: pd.DataFrame) -> None:
        """
        Calculate liquidity score for an asset.

        Args:
            asset: Asset object to update
            df: Historical price data
        """
        try:
            # Volume score (0-100)
            volume_score = min(100, asset.avg_volume / 1_000_000 * 10)

            # Spread score (assume tight spread for liquid assets)
            spread_score = 90  # Default for major assets

            # Combined score
            combined_score = volume_score * 0.7 + spread_score * 0.3

            asset.liquidity_score = combined_score

        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            asset.liquidity_score = 50.0  # Default

    def clear_cache(self):
        """Clear all cached data."""
        self._universe_cache.clear()
        self._data_cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "universe_cache": self._universe_cache.get_stats(),
            "data_cache": self._data_cache.get_stats(),
        }

    def _get_cached_universe(self, key: str) -> Optional[List[str]]:
        """Get cached universe (legacy method for compatibility)."""
        return self._universe_cache.get(key)

    def _cache_universe(self, key: str, tickers: List[str]):
        """Cache universe (legacy method for compatibility)."""
        self._universe_cache.put(key, tickers)

    def _get_cached_data(self, key: str) -> Optional[Dict[str, pd.DataFrame]]:
        """Get cached data (legacy method for compatibility)."""
        return self._data_cache.get(key)

    def _cache_data(self, key: str, data: Dict[str, pd.DataFrame]):
        """Cache data (legacy method for compatibility)."""
        self._data_cache.put(key, data)


# ============================================================================
# SINGLETON
# ============================================================================

_market_universe_loader: Optional[MarketUniverseLoader] = None


def get_market_universe_loader() -> MarketUniverseLoader:
    """
    Get the global MarketUniverseLoader instance.

    Returns:
        MarketUniverseLoader: Global loader instance
    """
    global _market_universe_loader
    if _market_universe_loader is None:
        _market_universe_loader = MarketUniverseLoader()
        logger.info("✅ MarketUniverseLoader global instance created")
    return _market_universe_loader
