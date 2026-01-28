"""
Symbol Value Object - Trading symbol representation

Symbol is a value object representing a trading symbol with validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    """Asset class enumeration."""

    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    FUTURES = "futures"
    OPTION = "option"
    FOREX = "forex"
    CRYPTO = "crypto"
    BOND = "bond"
    COMMODITY = "commodity"


class Exchange(str, Enum):
    """Major exchanges."""

    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    LSE = "LSE"
    TSE = "TSE"
    SSE = "SSE"
    HKE = "HKE"
    ASX = "ASX"
    TSX = "TSX"
    EUREX = "EUREX"
    CME = "CME"
    CBOE = "CBOE"
    ICE = "ICE"
    LME = "LME"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"


@dataclass(frozen=True)
class Symbol:
    """
    Symbol value object representing a trading instrument.

    Immutable and defined by its ticker and exchange.
    """

    ticker: str
    exchange: Exchange = Exchange.NASDAQ
    asset_class: AssetClass = AssetClass.EQUITY

    def __post_init__(self):
        """Validate symbol invariants."""
        if not self.ticker:
            raise ValueError("Ticker cannot be empty")

        # Normalize ticker to uppercase
        object.__setattr__(self, "ticker", self.ticker.upper().strip())

    @property
    def is_us_equity(self) -> bool:
        """Check if this is a US equity."""
        return (
            self.asset_class == AssetClass.EQUITY
            and self.exchange in (Exchange.NYSE, Exchange.NASDAQ, Exchange.AMEX)
        )

    @property
    def is_etf(self) -> bool:
        """Check if this is an ETF."""
        return self.asset_class == AssetClass.ETF

    @property
    def is_index(self) -> bool:
        """Check if this is an index."""
        return self.asset_class == AssetClass.INDEX

    @property
    def is_futures(self) -> bool:
        """Check if this is a futures contract."""
        return self.asset_class == AssetClass.FUTURES

    @property
    def is_option(self) -> bool:
        """Check if this is an option."""
        return self.asset_class == AssetClass.OPTION

    @property
    def is_forex(self) -> bool:
        """Check if this is a forex pair."""
        return self.asset_class == AssetClass.FOREX

    @property
    def is_crypto(self) -> bool:
        """Check if this is a cryptocurrency."""
        return self.asset_class == AssetClass.CRYPTO

    # Factory methods for common symbols
    @classmethod
    def stock(cls, ticker: str, exchange: Exchange = Exchange.NASDAQ) -> Symbol:
        """Create an equity symbol."""
        return cls(ticker=ticker, exchange=exchange, asset_class=AssetClass.EQUITY)

    @classmethod
    def etf(cls, ticker: str, exchange: Exchange = Exchange.NYSE) -> Symbol:
        """Create an ETF symbol."""
        return cls(ticker=ticker, exchange=exchange, asset_class=AssetClass.ETF)

    @classmethod
    def index(cls, ticker: str) -> Symbol:
        """Create an index symbol."""
        return cls(ticker=ticker, exchange=Exchange.NYSE, asset_class=AssetClass.INDEX)

    @classmethod
    def futures(cls, ticker: str, exchange: Exchange = Exchange.CME) -> Symbol:
        """Create a futures symbol."""
        return cls(ticker=ticker, exchange=exchange, asset_class=AssetClass.FUTURES)

    @classmethod
    def forex(cls, pair: str) -> Symbol:
        """Create a forex pair symbol."""
        return cls(ticker=pair.upper(), exchange=Exchange.FOREX, asset_class=AssetClass.FOREX)

    @classmethod
    def crypto(cls, ticker: str) -> Symbol:
        """Create a crypto symbol."""
        return cls(ticker=ticker.upper(), exchange=Exchange.CRYPTO, asset_class=AssetClass.CRYPTO)

    @classmethod
    def option(
        cls,
        underlying: str,
        expiry: str,
        strike: float,
        is_call: bool,
        exchange: Exchange = Exchange.CBOE,
    ) -> Symbol:
        """
        Create an option symbol.

        Args:
            underlying: Underlying ticker
            expiry: Expiry date (YYYYMMDD)
            strike: Strike price
            is_call: True for call, False for put
            exchange: Options exchange

        Returns:
            Option symbol (simplified OCC format)
        """
        # Simplified OCC format: UNDERLYINGYYYYMMDD Strike C/P
        type_char = "C" if is_call else "P"
        strike_str = f"{int(strike * 1000):08d}"  # Strike in cents, padded
        ticker = f"{underlying}{expiry}{strike_str}{type_char}"
        return cls(ticker=ticker, exchange=exchange, asset_class=AssetClass.OPTION)

    # Comparison
    def __eq__(self, other) -> bool:
        """Compare symbols."""
        if not isinstance(other, Symbol):
            return False
        return self.ticker == other.ticker and self.exchange == other.exchange

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.ticker, self.exchange))

    def __str__(self) -> str:
        """String representation."""
        return f"{self.ticker}.{self.exchange.value}"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Symbol(ticker='{self.ticker}', "
            f"exchange={self.exchange}, "
            f"asset_class={self.asset_class})"
        )
