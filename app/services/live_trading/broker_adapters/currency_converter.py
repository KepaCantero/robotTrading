"""
Currency Converter for EUR/USD conversions.

Provides live exchange rate conversion between EUR and USD for
multi-currency trading accounts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from ib_insync import IB, util

util.patchAsyncio()

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """
    Currency converter with live exchange rates from IB.

    Supports EUR/USD conversions with caching to reduce API calls.
    """

    # Exchange rate validity period (5 minutes)
    RATE_VALIDITY = timedelta(minutes=5)

    # Default fallback rates (used only when IB is unavailable)
    FALLBACK_RATES = {
        ("EUR", "USD"): Decimal("1.08"),
        ("USD", "EUR"): Decimal("0.93"),
    }

    def __init__(self, ib_connection: Optional[IB] = None):
        """
        Initialize currency converter.

        Args:
            ib_connection: Optional IB connection for live rates
        """
        self.ib = ib_connection
        self._rates_cache: Dict[tuple, tuple] = {}  # (base, quote) -> (rate, timestamp)
        self._last_update: Optional[datetime] = None

    def _is_rate_valid(self, timestamp: datetime) -> bool:
        """Check if cached rate is still valid."""
        return datetime.now() - timestamp < self.RATE_VALIDITY

    async def get_exchange_rate(self, base: str, quote: str) -> Decimal:
        """
        Get live exchange rate from base to quote currency.

        Args:
            base: Base currency (e.g., "EUR")
            quote: Quote currency (e.g., "USD")

        Returns:
            Exchange rate as Decimal

        Raises:
            ValueError: If rate cannot be obtained
        """
        pair = (base.upper(), quote.upper())

        # Check cache first
        if pair in self._rates_cache:
            rate, timestamp = self._rates_cache[pair]
            if self._is_rate_valid(timestamp):
                return rate

        # Try to get live rate from IB
        rate = await self._fetch_live_rate(base, quote)
        if rate is not None:
            self._rates_cache[pair] = (rate, datetime.now())
            self._last_update = datetime.now()
            return rate

        # Fallback to cached rate if available (even if expired)
        if pair in self._rates_cache:
            logger.warning(f"Using expired rate for {base}/{quote}")
            return self._rates_cache[pair][0]

        # Use fallback rate as last resort
        if pair in self.FALLBACK_RATES:
            logger.warning(f"Using fallback rate for {base}/{quote}")
            return self.FALLBACK_RATES[pair]

        raise ValueError(f"Cannot get exchange rate for {base}/{quote}")

    async def _fetch_live_rate(self, base: str, quote: str) -> Optional[Decimal]:
        """
        Fetch live exchange rate from IB.

        Args:
            base: Base currency
            quote: Quote currency

        Returns:
            Exchange rate as Decimal, or None if unavailable
        """
        if not self.ib or not self.ib.isConnected():
            return None

        try:
            # Create forex contract
            from ib_insync.contract import Forex

            contract = Forex(
                baseCurrency=base.upper(),
                quoteCurrency=quote.upper()
            )

            # Request market data
            self.ib.reqMktData(contract, "", False, False)
            await asyncio.sleep(1)

            # Get ticker
            ticker = self.ib.ticker(contract)
            if ticker and ticker.marketPrice():
                return Decimal(str(ticker.marketPrice()))

            logger.warning(f"No market data for {base}/{quote}")
            return None

        except Exception as e:
            logger.error(f"Error fetching rate for {base}/{quote}: {e}")
            return None

    async def convert_eur_to_usd(self, amount: Decimal) -> Decimal:
        """
        Convert EUR to USD.

        Args:
            amount: Amount in EUR

        Returns:
            Amount in USD
        """
        rate = await self.get_exchange_rate("EUR", "USD")
        return amount * rate

    async def convert_usd_to_eur(self, amount: Decimal) -> Decimal:
        """
        Convert USD to EUR.

        Args:
            amount: Amount in USD

        Returns:
            Amount in EUR
        """
        rate = await self.get_exchange_rate("USD", "EUR")
        return amount * rate

    async def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """
        Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            Converted amount
        """
        if from_currency.upper() == to_currency.upper():
            return amount

        rate = await self.get_exchange_rate(from_currency, to_currency)
        return amount * rate

    async def update_rates(self) -> None:
        """
        Force update of all cached exchange rates.

        Useful to call periodically to keep rates fresh.
        """
        pairs_to_update = [("EUR", "USD"), ("USD", "EUR")]

        for base, quote in pairs_to_update:
            try:
                rate = await self._fetch_live_rate(base, quote)
                if rate:
                    self._rates_cache[(base, quote)] = (rate, datetime.now())
            except Exception as e:
                logger.error(f"Error updating {base}/{quote}: {e}")

        self._last_update = datetime.now()

    def get_last_update_time(self) -> Optional[datetime]:
        """Get timestamp of last successful rate update."""
        return self._last_update

    def set_ib_connection(self, ib: IB) -> None:
        """
        Set or update IB connection.

        Args:
            ib: IB connection object
        """
        self.ib = ib

    def clear_cache(self) -> None:
        """Clear all cached exchange rates."""
        self._rates_cache.clear()
        self._last_update = None


# Singleton instance
_converter_instance: Optional[CurrencyConverter] = None


def get_currency_converter(ib_connection: Optional[IB] = None) -> CurrencyConverter:
    """
    Get the singleton currency converter instance.

    Args:
        ib_connection: Optional IB connection to set

    Returns:
        CurrencyConverter instance
    """
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = CurrencyConverter(ib_connection)
    elif ib_connection is not None:
        _converter_instance.set_ib_connection(ib_connection)
    return _converter_instance
