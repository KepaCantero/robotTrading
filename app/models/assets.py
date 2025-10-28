"""
Asset models for AlgoTrading system.

This module defines the data models for assets, liquidity metrics,
and asset universe management.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate asset symbol format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate asset name."""
        if not v or len(v.strip()) == 0:
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
        return min(100.0, max(0.0, (log_volume - 2) * 20))

    @property
    def spread_score(self) -> float:
        """Calculate spread-based liquidity score."""
        if self.avg_spread == 0:
            return 100.0

        # Lower spread = higher score
        # Normalize based on typical spreads
        spread_pct = float(self.avg_spread) * 100
        return max(0.0, min(100.0, 100 - spread_pct * 10))

    @property
    def combined_liquidity_score(self) -> float:
        """Calculate combined liquidity score."""
        volume_weight = 0.6
        spread_weight = 0.4

        return self.volume_score * volume_weight + self.spread_score * spread_weight


class AssetUniverse(BaseModel):
    """Asset universe representing a collection of assets for trading."""

    asset_class: AssetClass = Field(..., description="Asset class for this universe")
    assets: List[Asset] = Field(default_factory=list, description="List of assets in universe")
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

    def _update_statistics(self):
        """Update universe statistics."""
        self.total_assets = len(self.assets)

        if self.assets:
            self.avg_liquidity_score = sum(asset.liquidity_score for asset in self.assets) / len(
                self.assets
            )

            market_caps = [asset.market_cap for asset in self.assets if asset.market_cap]
            if market_caps:
                self.total_market_cap = sum(market_caps)
        else:
            self.avg_liquidity_score = 0.0
            self.total_market_cap = None

    def add_asset(self, asset: Asset) -> bool:
        """Add asset to universe."""
        if asset.asset_class != self.asset_class:
            return False

        # Check if asset already exists
        existing_symbols = {a.symbol for a in self.assets}
        if asset.symbol in existing_symbols:
            return False

        self.assets.append(asset)
        self._update_statistics()
        return True

    def remove_asset(self, symbol: str) -> bool:
        """Remove asset from universe."""
        original_count = len(self.assets)
        self.assets = [a for a in self.assets if a.symbol != symbol]

        if len(self.assets) < original_count:
            self._update_statistics()
            return True
        return False

    def get_top_liquid_assets(self, n: Optional[int] = None) -> List[Asset]:
        """Get top N most liquid assets."""
        if n is None:
            n = self.top_n

        # Sort by liquidity score (descending)
        sorted_assets = sorted(self.assets, key=lambda x: x.liquidity_score, reverse=True)
        return sorted_assets[:n]

    def get_asset_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol."""
        for asset in self.assets:
            if asset.symbol == symbol:
                return asset
        return None

    def update_asset_liquidity(
        self,
        symbol: str,
        liquidity_score: float,
        avg_volume: Decimal,
        avg_spread: Decimal,
    ) -> bool:
        """Update asset liquidity metrics."""
        asset = self.get_asset_by_symbol(symbol)
        if not asset:
            return False

        asset.liquidity_score = liquidity_score
        asset.avg_volume = avg_volume
        asset.avg_spread = avg_spread
        asset.last_updated = datetime.utcnow()

        self._update_statistics()
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
        return v.strip().upper()


class AssetRanking(BaseModel):
    """Asset ranking based on liquidity metrics."""

    asset_class: AssetClass = Field(..., description="Asset class")
    ranking_date: datetime = Field(default_factory=datetime.utcnow, description="Ranking date")
    rankings: List[Dict[str, Any]] = Field(default_factory=list, description="Ranked assets")

    def add_ranking(
        self,
        symbol: str,
        liquidity_score: float,
        rank: int,
        volume_score: float,
        spread_score: float,
    ) -> None:
        """Add asset ranking."""
        ranking_entry = {
            "symbol": symbol,
            "liquidity_score": liquidity_score,
            "rank": rank,
            "volume_score": volume_score,
            "spread_score": spread_score,
            "timestamp": datetime.utcnow(),
        }
        self.rankings.append(ranking_entry)

    def get_top_ranked(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get top N ranked assets."""
        sorted_rankings = sorted(self.rankings, key=lambda x: x["rank"])
        return sorted_rankings[:n]


class AssetFilter(BaseModel):
    """Asset filtering criteria."""

    asset_class: Optional[AssetClass] = Field(None, description="Filter by asset class")
    min_liquidity_score: float = Field(
        default=50.0, ge=0, le=100, description="Minimum liquidity score"
    )
    min_volume: Decimal = Field(default=Decimal("100000"), ge=0, description="Minimum daily volume")
    max_spread: Decimal = Field(default=Decimal("0.01"), ge=0, description="Maximum spread")
    exchanges: Optional[List[Exchange]] = Field(None, description="Allowed exchanges")
    active_only: bool = Field(default=True, description="Only active assets")

    def matches(self, asset: Asset) -> bool:
        """Check if asset matches filter criteria."""
        if self.asset_class and asset.asset_class != self.asset_class:
            return False

        if asset.liquidity_score < self.min_liquidity_score:
            return False

        if asset.avg_volume < self.min_volume:
            return False

        if asset.avg_spread > self.max_spread:
            return False

        if self.exchanges and asset.exchange not in self.exchanges:
            return False

        if self.active_only and not asset.is_active:
            return False

        return True
