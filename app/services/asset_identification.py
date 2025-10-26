"""
Asset identification and ranking service for AlgoTrading system.

This service handles the identification, ranking, and management of liquid assets
for momentum trading strategies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.models.assets import (
    Asset,
    AssetClass,
    AssetFilter,
    AssetRanking,
    AssetUniverse,
    Exchange,
    LiquidityMetrics,
)

logger = logging.getLogger(__name__)


class AssetIdentificationService:
    """Service for identifying and ranking liquid assets."""

    def __init__(self):
        self.asset_universes: Dict[AssetClass, AssetUniverse] = {}
        self.liquidity_metrics: Dict[str, LiquidityMetrics] = {}
        self.rankings: Dict[AssetClass, AssetRanking] = {}

        # Initialize default universes
        self._initialize_default_universes()

    def _initialize_default_universes(self):
        """Initialize default asset universes."""
        for asset_class in AssetClass:
            self.asset_universes[asset_class] = AssetUniverse(
                asset_class=asset_class, top_n=20
            )
            self.rankings[asset_class] = AssetRanking(asset_class=asset_class)

    async def identify_liquid_assets(
        self, asset_class: AssetClass, limit: int = 20
    ) -> List[Asset]:
        """Identify the most liquid assets for a given asset class."""
        try:
            # Get predefined liquid assets for each class
            liquid_assets = await self._get_predefined_liquid_assets(asset_class)

            # Calculate liquidity scores
            for asset in liquid_assets:
                await self._calculate_liquidity_score(asset)

            # Sort by liquidity score and return top N
            sorted_assets = sorted(
                liquid_assets, key=lambda x: x.liquidity_score, reverse=True
            )
            return sorted_assets[:limit]

        except Exception as e:
            logger.error(f"Error identifying liquid assets for {asset_class}: {e}")
            return []

    async def _get_predefined_liquid_assets(
        self, asset_class: AssetClass
    ) -> List[Asset]:
        """Get predefined liquid assets for each asset class."""
        if asset_class == AssetClass.EQUITY:
            return await self._get_liquid_equities()
        elif asset_class == AssetClass.CRYPTO:
            return await self._get_liquid_cryptos()
        elif asset_class == AssetClass.FOREX:
            return await self._get_liquid_forex()
        elif asset_class == AssetClass.COMMODITY:
            return await self._get_liquid_commodities()
        else:
            return []

    async def _get_liquid_equities(self) -> List[Asset]:
        """Get liquid equity assets."""
        equities = [
            Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("3000000000000"),
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft Corporation",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("30000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("2800000000000"),
            ),
            Asset(
                symbol="GOOGL",
                name="Alphabet Inc. Class A",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("25000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("1800000000000"),
            ),
            Asset(
                symbol="AMZN",
                name="Amazon.com Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("20000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("1500000000000"),
            ),
            Asset(
                symbol="TSLA",
                name="Tesla Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("40000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("800000000000"),
            ),
            Asset(
                symbol="NVDA",
                name="NVIDIA Corporation",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("35000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("1200000000000"),
            ),
            Asset(
                symbol="META",
                name="Meta Platforms Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("20000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("700000000000"),
            ),
            Asset(
                symbol="BRK.B",
                name="Berkshire Hathaway Inc. Class B",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("15000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("800000000000"),
            ),
            Asset(
                symbol="JPM",
                name="JPMorgan Chase & Co.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("12000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("450000000000"),
            ),
            Asset(
                symbol="JNJ",
                name="Johnson & Johnson",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("8000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("400000000000"),
            ),
            Asset(
                symbol="V",
                name="Visa Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("6000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("500000000000"),
            ),
            Asset(
                symbol="PG",
                name="Procter & Gamble Co.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("5000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("350000000000"),
            ),
            Asset(
                symbol="UNH",
                name="UnitedHealth Group Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("4000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("500000000000"),
            ),
            Asset(
                symbol="HD",
                name="Home Depot Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("3000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("350000000000"),
            ),
            Asset(
                symbol="MA",
                name="Mastercard Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("2500000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("350000000000"),
            ),
            Asset(
                symbol="DIS",
                name="Walt Disney Co.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("8000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("200000000000"),
            ),
            Asset(
                symbol="ADBE",
                name="Adobe Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("2000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("250000000000"),
            ),
            Asset(
                symbol="CRM",
                name="Salesforce Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("3000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("200000000000"),
            ),
            Asset(
                symbol="NFLX",
                name="Netflix Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("2000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("150000000000"),
            ),
            Asset(
                symbol="PYPL",
                name="PayPal Holdings Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("5000000"),
                avg_spread=Decimal("0.01"),
                market_cap=Decimal("100000000000"),
            ),
        ]
        return equities

    async def _get_liquid_cryptos(self) -> List[Asset]:
        """Get liquid cryptocurrency assets."""
        cryptos = [
            Asset(
                symbol="BTCUSDT",
                name="Bitcoin",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("50000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("1000000000000"),
            ),
            Asset(
                symbol="ETHUSDT",
                name="Ethereum",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("20000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("300000000000"),
            ),
            Asset(
                symbol="BNBUSDT",
                name="BNB",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("1000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("50000000000"),
            ),
            Asset(
                symbol="ADAUSDT",
                name="Cardano",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("2000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("20000000000"),
            ),
            Asset(
                symbol="SOLUSDT",
                name="Solana",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("1500000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("15000000000"),
            ),
            Asset(
                symbol="XRPUSDT",
                name="XRP",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("3000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("25000000000"),
            ),
            Asset(
                symbol="DOTUSDT",
                name="Polkadot",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("500000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("10000000000"),
            ),
            Asset(
                symbol="AVAXUSDT",
                name="Avalanche",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("800000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("8000000000"),
            ),
            Asset(
                symbol="MATICUSDT",
                name="Polygon",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("600000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("5000000000"),
            ),
            Asset(
                symbol="LINKUSDT",
                name="Chainlink",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("400000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=Decimal("4000000000"),
            ),
        ]
        return cryptos

    async def _get_liquid_forex(self) -> List[Asset]:
        """Get liquid forex pairs."""
        forex_pairs = [
            Asset(
                symbol="EURUSD",
                name="Euro/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("1000000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="GBPUSD",
                name="British Pound/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("300000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="USDJPY",
                name="US Dollar/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("400000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="USDCHF",
                name="US Dollar/Swiss Franc",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("100000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="AUDUSD",
                name="Australian Dollar/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("150000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="USDCAD",
                name="US Dollar/Canadian Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("120000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="NZDUSD",
                name="New Zealand Dollar/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("50000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="EURGBP",
                name="Euro/British Pound",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("80000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="EURJPY",
                name="Euro/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("200000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
            Asset(
                symbol="GBPJPY",
                name="British Pound/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("100000000"),
                avg_spread=Decimal("0.0001"),
                market_cap=None,
            ),
        ]
        return forex_pairs

    async def _get_liquid_commodities(self) -> List[Asset]:
        """Get liquid commodity assets."""
        commodities = [
            Asset(
                symbol="GOLD",
                name="Gold",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("100000"),
                avg_spread=Decimal("0.1"),
                market_cap=None,
            ),
            Asset(
                symbol="SILVER",
                name="Silver",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("50000"),
                avg_spread=Decimal("0.01"),
                market_cap=None,
            ),
            Asset(
                symbol="OIL",
                name="Crude Oil",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("200000"),
                avg_spread=Decimal("0.01"),
                market_cap=None,
            ),
            Asset(
                symbol="NATURAL_GAS",
                name="Natural Gas",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("100000"),
                avg_spread=Decimal("0.001"),
                market_cap=None,
            ),
            Asset(
                symbol="COPPER",
                name="Copper",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("30000"),
                avg_spread=Decimal("0.01"),
                market_cap=None,
            ),
        ]
        return commodities

    async def _calculate_liquidity_score(self, asset: Asset) -> None:
        """Calculate liquidity score for an asset."""
        try:
            # Calculate volume score
            volume_score = asset.volume_score

            # Calculate spread score
            spread_score = asset.spread_score

            # Calculate combined score
            combined_score = asset.combined_liquidity_score

            # Update asset with calculated score
            asset.liquidity_score = combined_score

            # Store metrics
            metrics = LiquidityMetrics(
                symbol=asset.symbol,
                daily_volume=asset.avg_volume,
                avg_volume_30d=asset.avg_volume,
                current_spread=asset.avg_spread,
                avg_spread_30d=asset.avg_spread,
                current_price=Decimal("100.0"),  # Placeholder
                volume_score=volume_score,
                spread_score=spread_score,
                overall_liquidity_score=combined_score,
            )

            self.liquidity_metrics[asset.symbol] = metrics

        except Exception as e:
            logger.error(f"Error calculating liquidity score for {asset.symbol}: {e}")
            asset.liquidity_score = 0.0

    async def update_asset_universe(
        self, asset_class: AssetClass, assets: List[Asset]
    ) -> bool:
        """Update asset universe with new assets."""
        try:
            universe = self.asset_universes[asset_class]

            # Clear existing assets
            universe.assets.clear()

            # Add new assets
            for asset in assets:
                universe.add_asset(asset)

            # Update rankings
            await self._update_rankings(asset_class)

            return True

        except Exception as e:
            logger.error(f"Error updating universe for {asset_class}: {e}")
            return False

    async def _update_rankings(self, asset_class: AssetClass) -> None:
        """Update asset rankings."""
        try:
            universe = self.asset_universes[asset_class]
            ranking = self.rankings[asset_class]

            # Clear existing rankings
            ranking.rankings.clear()

            # Get top assets
            top_assets = universe.get_top_liquid_assets()

            # Add rankings
            for i, asset in enumerate(top_assets, 1):
                ranking.add_ranking(
                    symbol=asset.symbol,
                    liquidity_score=asset.liquidity_score,
                    rank=i,
                    volume_score=asset.volume_score,
                    spread_score=asset.spread_score,
                )

        except Exception as e:
            logger.error(f"Error updating rankings for {asset_class}: {e}")

    async def get_top_liquid_assets(
        self, asset_class: AssetClass, limit: int = 20
    ) -> List[Asset]:
        """Get top liquid assets for a given class."""
        try:
            universe = self.asset_universes[asset_class]
            return universe.get_top_liquid_assets(limit)

        except Exception as e:
            logger.error(f"Error getting top liquid assets for {asset_class}: {e}")
            return []

    async def get_asset_rankings(self, asset_class: AssetClass) -> AssetRanking:
        """Get asset rankings for a given class."""
        try:
            return self.rankings[asset_class]

        except Exception as e:
            logger.error(f"Error getting rankings for {asset_class}: {e}")
            return AssetRanking(asset_class=asset_class)

    async def filter_assets(
        self, asset_class: AssetClass, filter_criteria: AssetFilter
    ) -> List[Asset]:
        """Filter assets based on criteria."""
        try:
            universe = self.asset_universes[asset_class]
            filtered_assets = []

            for asset in universe.assets:
                if filter_criteria.matches(asset):
                    filtered_assets.append(asset)

            return filtered_assets

        except Exception as e:
            logger.error(f"Error filtering assets for {asset_class}: {e}")
            return []

    async def get_asset_by_symbol(
        self, symbol: str, asset_class: Optional[AssetClass] = None
    ) -> Optional[Asset]:
        """Get asset by symbol."""
        try:
            if asset_class:
                universe = self.asset_universes[asset_class]
                return universe.get_asset_by_symbol(symbol)
            else:
                # Search all universes
                for universe in self.asset_universes.values():
                    asset = universe.get_asset_by_symbol(symbol)
                    if asset:
                        return asset
                return None

        except Exception as e:
            logger.error(f"Error getting asset {symbol}: {e}")
            return None

    async def get_universe_summary(self, asset_class: AssetClass) -> Dict[str, Any]:
        """Get universe summary."""
        try:
            universe = self.asset_universes[asset_class]
            ranking = self.rankings[asset_class]

            return {
                "asset_class": asset_class.value,
                "total_assets": universe.total_assets,
                "top_n": universe.top_n,
                "avg_liquidity_score": universe.avg_liquidity_score,
                "total_market_cap": (
                    float(universe.total_market_cap)
                    if universe.total_market_cap
                    else None
                ),
                "last_updated": universe.last_updated,
                "top_assets": [
                    {
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "liquidity_score": asset.liquidity_score,
                        "avg_volume": float(asset.avg_volume),
                        "avg_spread": float(asset.avg_spread),
                    }
                    for asset in universe.get_top_liquid_assets(10)
                ],
                "ranking_count": len(ranking.rankings),
            }

        except Exception as e:
            logger.error(f"Error getting universe summary for {asset_class}: {e}")
            return {}


# Global service instance
_asset_service: Optional[AssetIdentificationService] = None


def get_asset_identification_service() -> AssetIdentificationService:
    """Get global asset identification service instance."""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetIdentificationService()
    return _asset_service
