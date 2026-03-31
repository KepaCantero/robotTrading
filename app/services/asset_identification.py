"""
Asset identification and ranking service for AlgoTrading system.

This service handles the identification, ranking, and management of liquid assets
for momentum trading strategies.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any, Optional

from app.domain.models.assets import (
    Asset,
    AssetClass,
    AssetFilter,
    AssetRanking,
    AssetUniverse,
    Exchange,
    LiquidityMetrics,
)
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# Get spread defaults from centralized config
_config = get_config()
DEFAULT_STOCK_SPREAD = _config.trading.default_stock_spread
DEFAULT_CRYPTO_SPREAD = _config.trading.default_crypto_spread
DEFAULT_FOREX_SPREAD = _config.trading.default_forex_spread


class AssetIdentificationService:
    """Service for identifying and ranking liquid assets."""

    def __init__(self):
        self.asset_universes: dict[AssetClass, AssetUniverse] = {}
        self.liquidity_metrics: dict[str, LiquidityMetrics] = {}
        self.rankings: dict[AssetClass, AssetRanking] = {}

        # Initialize default universes
        self._initialize_default_universes()

    def _initialize_default_universes(self):
        """Initialize default asset universes."""
        for asset_class in AssetClass:
            self.asset_universes[asset_class] = AssetUniverse(asset_class=asset_class, top_n=20)
            self.rankings[asset_class] = AssetRanking(asset_class=asset_class)

    async def identify_liquid_assets(self, asset_class: AssetClass, limit: int = 20) -> list[Asset]:
        """Identify the most liquid assets for a given asset class."""
        try:
            # Get predefined liquid assets for each class
            liquid_assets = await self._get_predefined_liquid_assets(asset_class)

            # Calculate liquidity scores
            for asset in liquid_assets:
                await self._calculate_liquidity_score(asset)

            # Sort by liquidity score and return top N
            sorted_assets = sorted(liquid_assets, key=lambda x: x.liquidity_score, reverse=True)
            return sorted_assets[:limit]

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error identifying liquid assets for {asset_class}: {e}")
            return []

    async def _get_predefined_liquid_assets(self, asset_class: AssetClass) -> list[Asset]:
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

    async def _get_liquid_equities(self) -> list[Asset]:
        """Get liquid equity assets from MarketUniverseLoader (S&P 500)."""
        try:
            # Import here to avoid circular dependency
            from app.services.market_universe_loader import get_market_universe_loader

            loader = get_market_universe_loader()

            # Fetch S&P 500 universe
            tickers = await loader.get_sp500_universe()

            # Download recent data for metrics
            data = await loader.download_universe_data(tickers[:50], period="3mo", interval="1d")

            # Convert to Asset objects
            equities = []
            for ticker, df in data.items():
                if df is None or len(df) < 20:
                    continue

                try:
                    avg_volume = Decimal(str(int(df["volume"].mean())))
                    avg_price = Decimal(str(df["close"].mean()))

                    asset = Asset(
                        symbol=ticker,
                        name=ticker,  # yfinance would need separate call for name
                        asset_class=AssetClass.EQUITY,
                        exchange=Exchange.NASDAQ,  # Simplified
                        avg_volume=avg_volume,
                        avg_spread=DEFAULT_STOCK_SPREAD,
                        market_cap=Decimal(str(avg_price * 1000000000)),  # Approximation
                    )
                    equities.append(asset)

                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.debug(f"Error creating asset for {ticker}: {e}")
                    continue

            # If we got assets from API, return them
            if equities:
                logger.info(f"✅ Loaded {len(equities)} equities from MarketUniverseLoader")
                return equities

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"MarketUniverseLoader failed, using fallback: {e}")

        # Fallback to hardcoded list if API fails
        return await self._get_fallback_equities()

    async def _get_liquid_cryptos(self) -> list[Asset]:
        """Get liquid cryptocurrency assets from MarketUniverseLoader."""
        try:
            # Import here to avoid circular dependency
            from app.services.market_universe_loader import get_market_universe_loader

            loader = get_market_universe_loader()

            # Fetch crypto universe
            tickers = await loader.get_crypto_universe(top_n=20)

            # Convert yfinance format (BTC-USD) to binance format (BTCUSDT)
            binance_tickers = [t.replace("-USD", "USDT") for t in tickers]

            # Download recent data
            data = await loader.download_universe_data(tickers[:10], period="3mo", interval="1d")

            # Convert to Asset objects
            cryptos = []
            for i, (ticker, df) in enumerate(data.items()):
                if df is None or len(df) < 20:
                    continue

                try:
                    avg_volume = Decimal(str(int(df["volume"].mean())))

                    asset = Asset(
                        symbol=(
                            binance_tickers[i]
                            if i < len(binance_tickers)
                            else ticker.replace("-USD", "USDT")
                        ),
                        name=ticker.replace("-USD", ""),  # Simplified
                        asset_class=AssetClass.CRYPTO,
                        exchange=Exchange.BINANCE,
                        avg_volume=avg_volume,
                        avg_spread=DEFAULT_CRYPTO_SPREAD,
                        market_cap=None,
                    )
                    cryptos.append(asset)

                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.debug(f"Error creating crypto asset for {ticker}: {e}")
                    continue

            if cryptos:
                logger.info(f"✅ Loaded {len(cryptos)} cryptos from MarketUniverseLoader")
                return cryptos

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.warning(f"MarketUniverseLoader crypto failed, using fallback: {e}")

        return await self._get_fallback_cryptos()

    async def _get_liquid_forex(self) -> list[Asset]:
        """Get liquid forex pairs."""
        forex_pairs = [
            Asset(
                symbol="EURUSD",
                name="Euro/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("1000000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="GBPUSD",
                name="British Pound/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("300000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="USDJPY",
                name="US Dollar/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("400000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="USDCHF",
                name="US Dollar/Swiss Franc",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("100000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="AUDUSD",
                name="Australian Dollar/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("150000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="USDCAD",
                name="US Dollar/Canadian Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("120000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="NZDUSD",
                name="New Zealand Dollar/US Dollar",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("50000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="EURGBP",
                name="Euro/British Pound",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("80000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="EURJPY",
                name="Euro/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("200000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="GBPJPY",
                name="British Pound/Japanese Yen",
                asset_class=AssetClass.FOREX,
                exchange=Exchange.OANDA,
                avg_volume=Decimal("100000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=None,
            ),
        ]
        return forex_pairs

    async def _get_liquid_commodities(self) -> list[Asset]:
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
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=None,
            ),
            Asset(
                symbol="OIL",
                name="Crude Oil",
                asset_class=AssetClass.COMMODITY,
                exchange=Exchange.CME,
                avg_volume=Decimal("200000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
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
                avg_spread=DEFAULT_STOCK_SPREAD,
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

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error calculating liquidity score for {asset.symbol}: {e}")
            asset.liquidity_score = 0.0

    async def update_asset_universe(self, asset_class: AssetClass, assets: list[Asset]) -> bool:
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

        except (asyncio.TimeoutError, OSError) as e:
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

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error updating rankings for {asset_class}: {e}")

    async def get_top_liquid_assets(self, asset_class: AssetClass, limit: int = 20) -> list[Asset]:
        """Get top liquid assets for a given class."""
        try:
            universe = self.asset_universes[asset_class]
            return universe.get_top_liquid_assets(limit)

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error getting top liquid assets for {asset_class}: {e}")
            return []

    async def get_asset_rankings(self, asset_class: AssetClass) -> AssetRanking:
        """Get asset rankings for a given class."""
        try:
            return self.rankings[asset_class]

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error getting rankings for {asset_class}: {e}")
            return AssetRanking(asset_class=asset_class)

    async def filter_assets(
        self, asset_class: AssetClass, filter_criteria: AssetFilter
    ) -> list[Asset]:
        """Filter assets based on criteria."""
        try:
            universe = self.asset_universes[asset_class]
            filtered_assets = []

            for asset in universe.assets:
                if filter_criteria.matches(asset):
                    filtered_assets.append(asset)

            return filtered_assets

        except (asyncio.TimeoutError, OSError) as e:
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

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting asset {symbol}: {e}")
            return None

    async def get_universe_summary(self, asset_class: AssetClass) -> dict[str, Any]:
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
                    float(universe.total_market_cap) if universe.total_market_cap else None
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

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error getting universe summary for {asset_class}: {e}")
            return {}

    # ============ FALLBACK METHODS (if MarketUniverseLoader fails) ============

    async def _get_fallback_equities(self) -> list[Asset]:
        """Fallback hardcoded equities (used if MarketUniverseLoader fails)."""
        return [
            Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("50000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("3000000000000"),
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("30000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("2800000000000"),
            ),
            Asset(
                symbol="GOOGL",
                name="Alphabet",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("25000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("1800000000000"),
            ),
            Asset(
                symbol="AMZN",
                name="Amazon",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("20000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("1500000000000"),
            ),
            Asset(
                symbol="TSLA",
                name="Tesla",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("40000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("800000000000"),
            ),
            Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("35000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("1200000000000"),
            ),
            Asset(
                symbol="META",
                name="Meta",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("20000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("700000000000"),
            ),
            Asset(
                symbol="BRK.B",
                name="Berkshire",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("15000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("800000000000"),
            ),
            Asset(
                symbol="JPM",
                name="JPMorgan",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("12000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("450000000000"),
            ),
            Asset(
                symbol="JNJ",
                name="J&J",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NYSE,
                avg_volume=Decimal("8000000"),
                avg_spread=DEFAULT_STOCK_SPREAD,
                market_cap=Decimal("400000000000"),
            ),
        ]

    async def _get_fallback_cryptos(self) -> list[Asset]:
        """Fallback hardcoded cryptos (used if MarketUniverseLoader fails)."""
        return [
            Asset(
                symbol="BTCUSDT",
                name="Bitcoin",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("50000000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=Decimal("1000000000000"),
            ),
            Asset(
                symbol="ETHUSDT",
                name="Ethereum",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("20000000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=Decimal("300000000000"),
            ),
            Asset(
                symbol="BNBUSDT",
                name="BNB",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("1000000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=Decimal("50000000000"),
            ),
            Asset(
                symbol="SOLUSDT",
                name="Solana",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("1500000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=Decimal("15000000000"),
            ),
            Asset(
                symbol="XRPUSDT",
                name="XRP",
                asset_class=AssetClass.CRYPTO,
                exchange=Exchange.BINANCE,
                avg_volume=Decimal("3000000000"),
                avg_spread=DEFAULT_CRYPTO_SPREAD,
                market_cap=Decimal("25000000000"),
            ),
        ]


# Global service instance
_asset_service: Optional[AssetIdentificationService] = None


def get_asset_identification_service() -> AssetIdentificationService:
    """Get global asset identification service instance."""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetIdentificationService()

    return _asset_service
