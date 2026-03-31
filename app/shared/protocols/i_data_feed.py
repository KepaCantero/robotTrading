"""
Data feed protocol for dependency inversion.

Allows domain layer to depend on abstractions rather than
concrete infrastructure implementations like YahooFinanceFeed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.domain.models.market_data import DataFrequency

if TYPE_CHECKING:
    from datetime import datetime

    from app.domain.models.market_data import HistoricalData, Quote


class IDataFeed(Protocol):
    """Protocol for market data feed providers."""

    async def connect(self) -> bool:
        """Connect to the data feed."""
        ...

    async def disconnect(self) -> bool:
        """Disconnect from the data feed."""
        ...

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get current quote for a symbol."""
        ...

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> list[HistoricalData]:
        """Get historical market data for a symbol."""
        ...

    async def subscribe_to_symbols(self, symbols: list[str]) -> bool:
        """Subscribe to real-time data for given symbols."""
        ...
