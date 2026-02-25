"""
Price data provider for momentum analysis.

SOLID Principles:
- SRP: Only provides price data
- OCP: Extensible through new data sources
- LSP: Implements PriceDataProvider protocol
- ISP: Focused on data retrieval
- DIP: High-level modules depend on this abstraction
"""

import logging
from decimal import Decimal
from typing import Dict, List

from app.domain.models.momentum import Timeframe

logger = logging.getLogger(__name__)


class MockPriceDataProvider:
    """
    Mock price data provider for testing and demonstration.

    Single Responsibility:
    - Generate mock price data
    - Provide price data for analysis

    Open/Closed:
    - Open for extension (can be replaced with real data provider)
    - Closed for modification (core generation logic stable)

    Liskov Substitution:
    - Implements PriceDataProvider protocol
    - Substitutable with any PriceDataProvider implementation
    """

    async def get_price_data(self, symbol: str, timeframe: Timeframe) -> Dict[str, List[float]]:
        """
        Get price data for a symbol.

        Args:
            symbol: Asset symbol
            timeframe: Analysis timeframe

        Returns:
            Dictionary with prices, highs, lows, and volumes
        """
        return await self.generate_mock_data(symbol, timeframe)

    async def generate_mock_data(self, symbol: str, timeframe: Timeframe) -> Dict[str, List[float]]:
        """
        Generate mock price data for demonstration.

        Args:
            symbol: Asset symbol
            timeframe: Analysis timeframe

        Returns:
            Dictionary with generated price data
        """
        import random

        base_price = 100.0
        prices = [base_price]
        highs = [base_price * 1.02]
        lows = [base_price * 0.98]
        volumes = [Decimal("1000000")]

        for _ in range(50):
            change = random.uniform(-0.05, 0.05)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
            highs.append(new_price * random.uniform(1.0, 1.03))
            lows.append(new_price * random.uniform(0.97, 1.0))
            volumes.append(Decimal(str(random.randint(500000, 2000000))))

        return {
            "prices": prices,
            "highs": highs,
            "lows": lows,
            "volumes": volumes,
        }
