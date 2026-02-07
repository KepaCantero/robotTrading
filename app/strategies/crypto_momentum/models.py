"""
Data Models for Crypto Momentum Strategy

This module defines Pydantic models for cryptocurrency momentum investing including:
- Strategy configuration
- Crypto asset profiles
- Momentum scoring
- On-chain metrics
- Portfolio models
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CryptoAssetType(str, Enum):
    """Type of cryptocurrency asset."""

    BITCOIN = "bitcoin"  # BTC and BTC forks
    ETHEREUM = "ethereum"  # ETH and ERC-20 tokens
    STABLECOIN = "stablecoin"  # USD-pegged tokens
    DEFI = "defi"  # DeFi protocol tokens
    L1_BLOCKCHAIN = "l1_blockchain"  # Layer 1 blockchain tokens
    L2_SCALING = "l2_scaling"  # Layer 2 scaling tokens
    MEME = "meme"  # Meme/community tokens
    UTILITY = "utility"  # Utility tokens
    EXCHANGE = "exchange"  # Exchange tokens
    NFT_PLATFORM = "nft_platform"  # NFT platform tokens
    PRIVACY = "privacy"  # Privacy-focused coins
    OTHER = "other"


class CryptoExchange(str, Enum):
    """Major cryptocurrency exchanges."""

    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BITSTAMP = "bitstamp"
    GEMINI = "gemini"
    BITFINEX = "bitfinex"
    OKEX = "okex"
    HUOBI = "huobi"
    KUCOIN = "kucoin"
    GATE_IO = "gate_io"


class OnChainMetrics(BaseModel):
    """
    On-chain metrics for cryptocurrency analysis.

    These metrics provide insights into network activity and token utility
    that are not available in traditional markets.

    Attributes:
        active_addresses: Number of active addresses (24h)
        transaction_count: Number of transactions (24h)
        transaction_volume: Total transaction volume (24h) in USD
        market_cap: Current market capitalization in USD
        nvt_ratio: Network Value to Transactions ratio
        realized_cap: Realized capitalization
        mayer_multiple: Mayer Multiple (for Bitcoin)
        hashrate: Hash rate (for PoW coins)
        staking_ratio: Percentage of supply staked (for PoS coins)
        token_velocity: Token velocity (annualized)
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    active_addresses: Optional[int] = Field(
        None, ge=0, description="Number of active addresses (24h)"
    )
    transaction_count: Optional[int] = Field(None, ge=0, description="Number of transactions (24h)")
    transaction_volume: Optional[Decimal] = Field(
        None, ge=0, description="Total transaction volume (24h) in USD"
    )
    market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Current market capitalization in USD"
    )
    nvt_ratio: Optional[Decimal] = Field(
        None, ge=0, description="Network Value to Transactions ratio"
    )
    realized_cap: Optional[Decimal] = Field(None, ge=0, description="Realized capitalization")
    mayer_multiple: Optional[Decimal] = Field(
        None, ge=0, description="Mayer Multiple (for Bitcoin)"
    )
    hashrate: Optional[Decimal] = Field(None, ge=0, description="Hash rate (for PoW coins)")
    staking_ratio: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Percentage of supply staked"
    )
    token_velocity: Optional[Decimal] = Field(None, ge=0, description="Token velocity (annualized)")

    @property
    def network_health_score(self) -> Optional[Decimal]:
        """
        Calculate network health score (0-100).

        Higher values indicate healthier network activity.
        """
        if not all([self.active_addresses, self.transaction_count, self.transaction_volume]):
            return None

        # Normalize metrics (simplified scoring)
        # More active addresses = better
        address_score = min(100, self.active_addresses / 10000)

        # More transactions = better
        tx_score = min(100, self.transaction_count / 100000)

        # Higher volume = better (up to a point)
        volume_score = min(100, float(self.transaction_volume) / 1_000_000)

        return Decimal(str((address_score + tx_score + volume_score) / 3)).quantize(Decimal("0.01"))


@dataclass
class CryptoAsset:
    """
    Cryptocurrency asset for momentum analysis.

    This dataclass represents a crypto asset with all relevant metrics
    for screening and momentum scoring.

    Attributes:
        symbol: Trading symbol (e.g., "BTC", "ETH")
        name: Full name of the cryptocurrency
        asset_type: Type of cryptocurrency
        market_cap: Market capitalization in USD
        liquidity_score: Liquidity score (0-100)
        volatility_90d: 90-day volatility (annualized %)
        avg_daily_volume: Average daily trading volume (24h)
        exchanges: List of major exchanges where listed
        btc_correlation: Correlation with Bitcoin (-1 to 1)
        btc_beta: Beta to Bitcoin
        current_price: Current price in USD
        on_chain_metrics: Optional on-chain metrics
        is_eligible: Whether asset meets screening criteria
    """

    symbol: str
    name: str
    asset_type: CryptoAssetType
    market_cap: Decimal
    liquidity_score: Decimal
    volatility_90d: Decimal
    avg_daily_volume: Decimal
    exchanges: List[CryptoExchange]
    btc_correlation: Optional[float] = None
    btc_beta: Optional[float] = None
    current_price: Decimal = Decimal("0")
    on_chain_metrics: Optional[OnChainMetrics] = None
    is_eligible: bool = True

    def is_eligible_for_trading(
        self,
        min_market_cap: Decimal,
        min_daily_volume: Decimal,
        min_liquidity_score: Decimal,
        required_exchanges: Optional[List[CryptoExchange]] = None,
    ) -> bool:
        """
        Check if asset meets minimum trading criteria.

        Args:
            min_market_cap: Minimum market capitalization
            min_daily_volume: Minimum average daily volume
            min_liquidity_score: Minimum liquidity score (0-100)
            required_exchanges: Required exchanges (if None, any major exchange)

        Returns:
            True if asset meets all criteria
        """
        # Market cap check
        if self.market_cap < min_market_cap:
            return False

        # Volume check
        if self.avg_daily_volume < min_daily_volume:
            return False

        # Liquidity score check
        if self.liquidity_score < min_liquidity_score:
            return False

        # Exchange listing check
        if required_exchanges:
            if not any(exchange in self.exchanges for exchange in required_exchanges):
                return False

        return True


class CryptoMomentumScore(BaseModel):
    """
    Momentum score for a cryptocurrency asset.

    Attributes:
        symbol: Trading symbol
        raw_momentum: Raw momentum score (0-100)
        volatility_adjusted_momentum: Volatility-adjusted momentum
        btc_adjusted_momentum: BTC correlation-adjusted momentum
        final_score: Final momentum score (0-100)
        rank: Rank among screened assets
        percentile: Percentile rank (0-100)
        confidence: Confidence in the score (0-100)
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Trading symbol")
    raw_momentum: Decimal = Field(..., ge=0, le=100, description="Raw momentum score (0-100)")
    volatility_adjusted_momentum: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Volatility-adjusted momentum"
    )
    btc_adjusted_momentum: Optional[Decimal] = Field(
        None, ge=0, le=100, description="BTC correlation-adjusted momentum"
    )
    final_score: Decimal = Field(..., ge=0, le=100, description="Final momentum score (0-100)")
    rank: Optional[int] = Field(None, ge=1, description="Rank among screened assets")
    percentile: Optional[Decimal] = Field(None, ge=0, le=100, description="Percentile rank (0-100)")
    confidence: Decimal = Field(..., ge=0, le=100, description="Confidence in the score (0-100)")

    @property
    def is_high_momentum(self) -> bool:
        """Check if this is a high momentum asset (score > 70)."""
        return self.final_score > Decimal("70")

    @property
    def is_low_momentum(self) -> bool:
        """Check if this is a low momentum asset (score < 40)."""
        return self.final_score < Decimal("40")


class CryptoPosition(BaseModel):
    """
    Position in a cryptocurrency asset.

    Attributes:
        symbol: Trading symbol
        quantity: Quantity held
        entry_price: Average entry price
        current_price: Current market price
        value: Current position value
        weight: Portfolio weight (0-1)
        unrealized_pnl: Unrealized P&L
        unrealized_pnl_pct: Unrealized P&L percentage
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., gt=0, description="Quantity held")
    entry_price: Decimal = Field(..., gt=0, description="Average entry price")
    current_price: Decimal = Field(..., gt=0, description="Current market price")
    value: Optional[Decimal] = Field(default=None, ge=0, description="Current position value")
    weight: Decimal = Field(..., ge=0, le=1, description="Portfolio weight (0-1)")
    unrealized_pnl: Optional[Decimal] = Field(default=None, description="Unrealized P&L")
    unrealized_pnl_pct: Optional[Decimal] = Field(default=None, description="Unrealized P&L %")

    @model_validator(mode="after")
    def calculate_position_metrics(self) -> "CryptoPosition":
        """Calculate position value and P&L from price and quantity."""
        # Only calculate if not already set to avoid recursion
        if self.value is None:
            object.__setattr__(self, 'value', self.quantity * self.current_price)
        else:
            object.__setattr__(self, 'value', self.value)

        price_change = self.current_price - self.entry_price

        if self.unrealized_pnl is None:
            object.__setattr__(self, 'unrealized_pnl', price_change * self.quantity)
        else:
            object.__setattr__(self, 'unrealized_pnl', self.unrealized_pnl)

        if self.unrealized_pnl_pct is None and self.entry_price > 0:
            object.__setattr__(self, 'unrealized_pnl_pct', (price_change / self.entry_price) * 100)
        elif self.unrealized_pnl_pct is None:
            object.__setattr__(self, 'unrealized_pnl_pct', Decimal("0"))

        return self


class CryptoPortfolio(BaseModel):
    """
    Cryptocurrency momentum portfolio.

    Attributes:
        positions: List of positions
        total_value: Total portfolio value
        cash: Cash amount
        btc_weight: Bitcoin weight
        altcoin_weight: Altcoin weight
        expected_volatility: Expected annual volatility
        last_rebalance: Last rebalance date
        rebalance_threshold: Rebalance threshold
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    positions: List[CryptoPosition] = Field(default_factory=list, description="List of positions")
    total_value: Decimal = Field(..., ge=0, description="Total portfolio value")
    cash: Decimal = Field(default=Decimal("0"), ge=0, description="Cash amount")
    btc_weight: Decimal = Field(default=Decimal("0"), ge=0, le=1, description="Bitcoin weight")
    altcoin_weight: Decimal = Field(default=Decimal("0"), ge=0, le=1, description="Altcoin weight")
    expected_volatility: Optional[Decimal] = Field(
        None, ge=0, description="Expected annual volatility"
    )
    last_rebalance: Optional[date] = Field(None, description="Last rebalance date")
    rebalance_threshold: Decimal = Field(
        default=Decimal("0.05"), ge=0, le=1, description="Rebalance threshold"
    )

    @property
    def invested_value(self) -> Decimal:
        """Calculate total invested value."""
        return sum(pos.value for pos in self.positions)

    @property
    def btc_position(self) -> Optional[CryptoPosition]:
        """Get Bitcoin position if exists."""
        for pos in self.positions:
            if pos.symbol == "BTC":
                return pos
        return None

    def needs_rebalance(self) -> bool:
        """Check if portfolio needs rebalancing."""
        if not self.positions:
            return False

        # Check if any position has drifted beyond threshold
        for pos in self.positions:
            if abs(pos.weight - Decimal("0.1")) > self.rebalance_threshold:  # Assuming 10% target
                return True

        return False


class CryptoMomentumConfig(BaseModel):
    """
    Configuration for the crypto momentum strategy.

    Attributes:
        lookback_days: Lookback period for momentum calculation
        volatility_adjustment: Whether to adjust for volatility
        btc_adjustment: Whether to adjust for BTC correlation
        max_position_size: Maximum position size (0-1)
        btc_weight: Target Bitcoin weight in portfolio
        portfolio_size: Target number of positions
        rebalance_threshold: Rebalance threshold (0-1)
        min_market_cap: Minimum market cap for screening
        min_daily_volume: Minimum daily volume for screening
        min_liquidity_score: Minimum liquidity score (0-100)
        max_volatility: Maximum allowed volatility
        target_volatility: Target portfolio volatility
        required_exchanges: Required exchanges for listing
        use_on_chain_metrics: Whether to use on-chain metrics
        social_sentiment_weight: Weight for social sentiment (0-1)
    """

    model_config = ConfigDict(
        strict=False,
        validate_assignment=True,
        extra="ignore",
    )

    # Momentum parameters
    lookback_days: int = Field(
        90, ge=30, le=365, description="Lookback period for momentum calculation (days)"
    )
    volatility_adjustment: bool = Field(True, description="Whether to adjust for volatility")
    btc_adjustment: bool = Field(True, description="Whether to adjust for BTC correlation")

    # Portfolio parameters
    max_position_size: Decimal = Field(
        Decimal("0.10"), ge=0.01, le=0.5, description="Maximum position size (0-1)"
    )
    btc_weight: Decimal = Field(
        Decimal("0.50"), ge=0, le=1, description="Target Bitcoin weight in portfolio"
    )
    portfolio_size: int = Field(10, ge=5, le=30, description="Target number of positions")
    rebalance_threshold: Decimal = Field(
        Decimal("0.05"), ge=0.01, le=0.20, description="Rebalance threshold (0-1)"
    )

    # Screening parameters
    min_market_cap: Decimal = Field(
        Decimal("1000000000"), ge=0, description="Minimum market cap for screening (USD)"
    )
    min_daily_volume: Decimal = Field(
        Decimal("10000000"), ge=0, description="Minimum daily volume for screening (USD)"
    )
    min_liquidity_score: Decimal = Field(
        Decimal("50"), ge=0, le=100, description="Minimum liquidity score (0-100)"
    )
    max_volatility: Optional[Decimal] = Field(
        None, ge=0, le=200, description="Maximum allowed volatility (%)"
    )
    target_volatility: Optional[Decimal] = Field(
        None, ge=10, le=100, description="Target portfolio volatility (%)"
    )

    # Exchange requirements
    required_exchanges: List[str] = Field(
        default_factory=lambda: ["binance", "coinbase"],
        description="Required exchanges for listing",
    )

    # Advanced features
    use_on_chain_metrics: bool = Field(False, description="Whether to use on-chain metrics")
    social_sentiment_weight: Decimal = Field(
        Decimal("0.0"), ge=0, le=1, description="Weight for social sentiment (0-1)"
    )

    @model_validator(mode="after")
    def validate_weights(self) -> "CryptoMomentumConfig":
        """Validate that weights are within bounds."""
        if self.max_position_size > Decimal("0.5"):
            raise ValueError("max_position_size cannot exceed 50%")

        if self.btc_weight > Decimal("1.0"):
            raise ValueError("btc_weight cannot exceed 100%")

        if self.social_sentiment_weight > Decimal("1.0"):
            raise ValueError("social_sentiment_weight cannot exceed 100%")

        return self

    def get_screening_description(self) -> str:
        """Get human-readable description of screening criteria."""
        btc_weight_pct = float(self.btc_weight) * 100
        return (
            f"Crypto Momentum Screening Criteria:\n"
            f"  - Lookback period: {self.lookback_days} days\n"
            f"  - Min market cap: ${self.min_market_cap:,.0f}\n"
            f"  - Min daily volume: ${self.min_daily_volume:,.0f}\n"
            f"  - Min liquidity score: {self.min_liquidity_score}\n"
            f"  - Max position size: {float(self.max_position_size):.1%}\n"
            f"  - BTC weight: {btc_weight_pct:.0f}%\n"
            f"  - Portfolio size: {self.portfolio_size} positions\n"
            f"  - Required exchanges: {', '.join(self.required_exchanges)}\n"
        )


@dataclass
class CryptoScreeningResult:
    """
    Result of crypto asset screening.

    Attributes:
        passed_assets: List of assets that passed screening
        failed_assets: Dict with assets that failed and reasons
        total_evaluated: Total number of assets evaluated
        screening_time_ms: Time taken for screening (milliseconds)
        min_market_cap: Minimum market cap used
        min_daily_volume: Minimum daily volume used
        min_liquidity_score: Minimum liquidity score used
    """

    passed_assets: List[CryptoAsset]
    failed_assets: Dict[str, List[str]]
    total_evaluated: int
    screening_time_ms: float
    min_market_cap: Decimal
    min_daily_volume: Decimal
    min_liquidity_score: Decimal

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.passed_assets) / self.total_evaluated) * 100
