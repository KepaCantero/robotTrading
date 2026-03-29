"""
Asset models for AlgoTrading system.

This module defines the data models for assets, liquidity metrics,
and asset universe management.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class AssetClass(str, Enum):
    """Asset class enumeration."""

    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    BOND = "bond"


class Exchange(str, Enum):
    """Exchange enumeration."""

    # Equity exchanges
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    LSE = "LSE"
    TSE = "TSE"

    # Crypto exchanges
    BINANCE = "BINANCE"
    COINBASE = "COINBASE"
    KRAKEN = "KRAKEN"

    # Forex
    OANDA = "OANDA"
    FXCM = "FXCM"

    # Others
    CME = "CME"
    ICE = "ICE"


class Asset(BaseModel):
    """Asset model representing a tradable financial instrument."""

    symbol: str = Field(..., description="Asset symbol (e.g., AAPL, BTCUSDT)")
    name: str = Field(..., description="Full asset name")
    asset_class: AssetClass = Field(..., description="Asset class category")
    exchange: Exchange = Field(..., description="Primary exchange")
    sector: Optional[str] = Field(
        default=None, description="Sector classification (e.g., technology, energy, healthcare)"
    )
    country: Optional[str] = Field(
        default=None, description="Country or region code where asset is listed/from"
    )
    primary_exchange: Optional[str] = Field(
        default=None, description="Primary exchange for this asset"
    )

    # Liquidity metrics
    liquidity_score: float = Field(
        default=0.0, ge=0, le=100, description="Overall liquidity score (0-100)"
    )
    avg_volume: Decimal = Field(..., description="Average daily volume")
    avg_spread: Decimal = Field(..., description="Average bid-ask spread")
    market_cap: Optional[Decimal] = Field(None, ge=0, description="Market capitalization")

    # Trading characteristics
    min_trade_size: Decimal = Field(default=Decimal("0.01"), ge=0, description="Minimum trade size")
    max_trade_size: Decimal = Field(
        default=Decimal("1000000"), ge=0, description="Maximum trade size"
    )
    tick_size: Decimal = Field(default=Decimal("0.01"), ge=0, description="Minimum price increment")

    # Status and metadata
    is_active: bool = Field(default=True, description="Whether asset is actively traded")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate asset symbol format."""
        if not v or len(v.strip()) == 0:
            logger.error(
                "Asset symbol validation failed: empty symbol",
                extra={"symbol_value": repr(v)},
            )
            raise ValueError("Symbol cannot be empty")
        validated = v.strip().upper()
        logger.debug(
            "Asset symbol validated",
            extra={"original": v, "validated": validated},
        )
        return validated

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate asset name."""
        if not v or len(v.strip()) == 0:
            logger.error(
                "Asset name validation failed: empty name",
                extra={"name_value": repr(v)},
            )
            raise ValueError("Name cannot be empty")
        return v.strip()

    @property
    def volume_score(self) -> float:
        """Calculate volume-based liquidity score."""
        if self.avg_volume == 0:
            return 0.0

        # Normalize volume score (higher volume = higher score)
        # Using logarithmic scaling for better distribution
        import math

        log_volume = math.log10(float(self.avg_volume))
        # Scale 100-10000 to 0-100
        score = min(100.0, max(0.0, (log_volume - 2) * 20))
        logger.debug(
            "Calculated volume score",
            extra={
                "symbol": self.symbol,
                "avg_volume": str(self.avg_volume),
                "volume_score": score,
            },
        )
        return score

    @property
    def spread_score(self) -> float:
        """Calculate spread-based liquidity score."""
        if self.avg_spread == 0:
            return 100.0

        # Lower spread = higher score
        # Normalize based on typical spreads
        spread_pct = float(self.avg_spread) * 100
        score = max(0.0, min(100.0, 100 - spread_pct * 10))
        logger.debug(
            "Calculated spread score",
            extra={
                "symbol": self.symbol,
                "avg_spread": str(self.avg_spread),
                "spread_score": score,
            },
        )
        return score

    @property
    def combined_liquidity_score(self) -> float:
        """Calculate combined liquidity score."""
        volume_weight = 0.6
        spread_weight = 0.4

        score = self.volume_score * volume_weight + self.spread_score * spread_weight
        logger.debug(
            "Calculated combined liquidity score",
            extra={
                "symbol": self.symbol,
                "volume_score": self.volume_score,
                "spread_score": self.spread_score,
                "combined_score": score,
            },
        )
        return score


class AssetUniverse(BaseModel):
    """Asset universe representing a collection of assets for trading."""

    asset_class: AssetClass = Field(..., description="Asset class for this universe")
    assets: list[Asset] = Field(default_factory=list, description="List of assets in universe")
    top_n: int = Field(default=20, ge=1, le=100, description="Number of top assets to maintain")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    # Universe statistics
    total_assets: int = Field(default=0, ge=0, description="Total number of assets")
    avg_liquidity_score: float = Field(
        default=0.0, ge=0, le=100, description="Average liquidity score"
    )
    total_market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Total market cap of universe"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._update_statistics()
        logger.info(
            "AssetUniverse initialized",
            extra={
                "asset_class": self.asset_class.value,
                "total_assets": self.total_assets,
                "avg_liquidity_score": self.avg_liquidity_score,
            },
        )

    def _update_statistics(self):
        """Update universe statistics."""
        self.total_assets = len(self.assets)

        if self.assets:
            self.avg_liquidity_score = np.mean([asset.liquidity_score for asset in self.assets])

            market_caps = [asset.market_cap for asset in self.assets if asset.market_cap]
            if market_caps:
                self.total_market_cap = sum(market_caps)
        else:
            self.avg_liquidity_score = 0.0
            self.total_market_cap = None

        logger.debug(
            "Updated universe statistics",
            extra={
                "total_assets": self.total_assets,
                "avg_liquidity_score": self.avg_liquidity_score,
                "total_market_cap": str(self.total_market_cap) if self.total_market_cap else None,
            },
        )

    def add_asset(self, asset: Asset) -> bool:
        """Add asset to universe."""
        logger.debug(
            "Attempting to add asset to universe",
            extra={
                "symbol": asset.symbol,
                "asset_class": asset.asset_class.value,
                "universe_class": self.asset_class.value,
            },
        )

        if asset.asset_class != self.asset_class:
            logger.warning(
                "Asset class mismatch, cannot add to universe",
                extra={
                    "asset_symbol": asset.symbol,
                    "asset_class": asset.asset_class.value,
                    "expected_class": self.asset_class.value,
                },
            )
            return False

        # Check if asset already exists
        existing_symbols = {a.symbol for a in self.assets}
        if asset.symbol in existing_symbols:
            logger.debug(
                "Asset already exists in universe",
                extra={"symbol": asset.symbol},
            )
            return False

        self.assets.append(asset)
        self._update_statistics()
        logger.info(
            "Asset added to universe",
            extra={
                "symbol": asset.symbol,
                "total_assets": self.total_assets,
            },
        )
        return True

    def remove_asset(self, symbol: str) -> bool:
        """Remove asset from universe."""
        logger.debug(
            "Attempting to remove asset from universe",
            extra={"symbol": symbol},
        )

        original_count = len(self.assets)
        self.assets = [a for a in self.assets if a.symbol != symbol]

        if len(self.assets) < original_count:
            self._update_statistics()
            logger.info(
                "Asset removed from universe",
                extra={
                    "symbol": symbol,
                    "total_assets": self.total_assets,
                },
            )
            return True

        logger.debug(
            "Asset not found in universe",
            extra={"symbol": symbol},
        )
        return False

    def get_top_liquid_assets(self, n: Optional[int] = None) -> list[Asset]:
        """Get top N most liquid assets."""
        if n is None:
            n = self.top_n

        # Sort by liquidity score (descending)
        sorted_assets = sorted(self.assets, key=lambda x: x.liquidity_score, reverse=True)
        result = sorted_assets[:n]

        logger.debug(
            "Retrieved top liquid assets",
            extra={
                "requested_n": n,
                "returned_count": len(result),
            },
        )
        return result

    def get_asset_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol."""
        for asset in self.assets:
            if asset.symbol == symbol:
                logger.debug(
                    "Found asset by symbol",
                    extra={"symbol": symbol},
                )
                return asset

        logger.debug(
            "Asset not found by symbol",
            extra={"symbol": symbol},
        )
        return None

    def update_asset_liquidity(
        self,
        symbol: str,
        liquidity_score: float,
        avg_volume: Decimal,
        avg_spread: Decimal,
    ) -> bool:
        """Update asset liquidity metrics."""
        logger.debug(
            "Updating asset liquidity metrics",
            extra={
                "symbol": symbol,
                "liquidity_score": liquidity_score,
                "avg_volume": str(avg_volume),
                "avg_spread": str(avg_spread),
            },
        )

        asset = self.get_asset_by_symbol(symbol)
        if not asset:
            logger.warning(
                "Cannot update liquidity: asset not found",
                extra={"symbol": symbol},
            )
            return False

        asset.liquidity_score = liquidity_score
        asset.avg_volume = avg_volume
        asset.avg_spread = avg_spread
        asset.last_updated = datetime.utcnow()

        self._update_statistics()
        logger.info(
            "Asset liquidity updated",
            extra={
                "symbol": symbol,
                "new_liquidity_score": liquidity_score,
            },
        )
        return True


class LiquidityMetrics(BaseModel):
    """Liquidity metrics for asset analysis."""

    symbol: str = Field(..., description="Asset symbol")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")

    # Volume metrics
    daily_volume: Decimal = Field(ge=0, description="Daily trading volume")
    avg_volume_30d: Decimal = Field(ge=0, description="30-day average volume")
    volume_volatility: float = Field(
        default=0.0, ge=0, le=100, description="Volume volatility (0-100)"
    )

    # Spread metrics
    current_spread: Decimal = Field(ge=0, description="Current bid-ask spread")
    avg_spread_30d: Decimal = Field(ge=0, description="30-day average spread")
    spread_volatility: float = Field(
        default=0.0, ge=0, le=100, description="Spread volatility (0-100)"
    )

    # Price metrics
    current_price: Decimal = Field(ge=0, description="Current market price")
    price_volatility: float = Field(
        default=0.0, ge=0, le=100, description="Price volatility (0-100)"
    )

    # Calculated scores
    volume_score: float = Field(ge=0, le=100, description="Volume-based liquidity score")
    spread_score: float = Field(ge=0, le=100, description="Spread-based liquidity score")
    overall_liquidity_score: float = Field(ge=0, le=100, description="Overall liquidity score")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        validated = v.strip().upper()
        logger.debug(
            "LiquidityMetrics symbol validated",
            extra={"original": v, "validated": validated},
        )
        return validated


class AssetRanking(BaseModel):
    """Asset ranking based on liquidity metrics."""

    asset_class: AssetClass = Field(..., description="Asset class")
    ranking_date: datetime = Field(default_factory=datetime.utcnow, description="Ranking date")
    rankings: list[dict[str, Any]] = Field(default_factory=list, description="Ranked assets")

    def add_ranking(
        self,
        symbol: str,
        liquidity_score: float,
        rank: int,
        volume_score: float,
        spread_score: float,
    ) -> None:
        """Add asset ranking."""
        logger.debug(
            "Adding asset ranking",
            extra={
                "symbol": symbol,
                "rank": rank,
                "liquidity_score": liquidity_score,
            },
        )

        ranking_entry = {
            "symbol": symbol,
            "liquidity_score": liquidity_score,
            "rank": rank,
            "volume_score": volume_score,
            "spread_score": spread_score,
            "timestamp": datetime.utcnow(),
        }
        self.rankings.append(ranking_entry)

    def get_top_ranked(self, n: int = 20) -> list[dict[str, Any]]:
        """Get top N ranked assets."""
        sorted_rankings = sorted(self.rankings, key=lambda x: x["rank"])
        result = sorted_rankings[:n]
        logger.debug(
            "Retrieved top ranked assets",
            extra={"requested_n": n, "returned_count": len(result)},
        )
        return result


class AssetFilter(BaseModel):
    """Asset filtering criteria."""

    asset_class: Optional[AssetClass] = Field(None, description="Filter by asset class")
    min_liquidity_score: float = Field(
        default=50.0, ge=0, le=100, description="Minimum liquidity score"
    )
    min_volume: Decimal = Field(default=Decimal("100000"), ge=0, description="Minimum daily volume")
    max_spread: Decimal = Field(default=Decimal("0.01"), ge=0, description="Maximum spread")
    exchanges: Optional[list[Exchange]] = Field(None, description="Allowed exchanges")
    active_only: bool = Field(default=True, description="Only active assets")

    def matches(self, asset: Asset) -> bool:
        """Check if asset matches filter criteria."""
        if self.asset_class and asset.asset_class != self.asset_class:
            logger.debug(
                "Asset filter mismatch: asset_class",
                extra={
                    "symbol": asset.symbol,
                    "expected": self.asset_class.value,
                    "actual": asset.asset_class.value,
                },
            )
            return False

        if asset.liquidity_score < self.min_liquidity_score:
            logger.debug(
                "Asset filter mismatch: liquidity_score",
                extra={
                    "symbol": asset.symbol,
                    "min_required": self.min_liquidity_score,
                    "actual": asset.liquidity_score,
                },
            )
            return False

        if asset.avg_volume < self.min_volume:
            logger.debug(
                "Asset filter mismatch: volume",
                extra={
                    "symbol": asset.symbol,
                    "min_required": str(self.min_volume),
                    "actual": str(asset.avg_volume),
                },
            )
            return False

        if asset.avg_spread > self.max_spread:
            logger.debug(
                "Asset filter mismatch: spread",
                extra={
                    "symbol": asset.symbol,
                    "max_allowed": str(self.max_spread),
                    "actual": str(asset.avg_spread),
                },
            )
            return False

        if self.exchanges and asset.exchange not in self.exchanges:
            logger.debug(
                "Asset filter mismatch: exchange",
                extra={
                    "symbol": asset.symbol,
                    "allowed_exchanges": [e.value for e in self.exchanges],
                    "actual": asset.exchange.value,
                },
            )
            return False

        if self.active_only and not asset.is_active:
            logger.debug(
                "Asset filter mismatch: inactive",
                extra={"symbol": asset.symbol},
            )
            return False

        logger.debug(
            "Asset matches filter criteria",
            extra={"symbol": asset.symbol},
        )
        return True
