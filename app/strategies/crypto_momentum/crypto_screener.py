"""
Crypto Asset Screener

This module provides screening functionality for cryptocurrency assets,
filtering by market cap, liquidity, exchange listing, and volatility.

Crypto markets differ significantly from traditional markets:
- 24/7 trading with continuous price discovery
- Higher volatility and lower liquidity in smaller cap tokens
- Bitcoin dominance affects most altcoins
- Exchange listings affect liquidity and accessibility
"""

import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional

from .models import CryptoAsset, CryptoAssetType, CryptoExchange, CryptoScreeningResult

logger = logging.getLogger(__name__)


class CryptoScreener:
    """
    Screen crypto assets for momentum strategy.

    This class implements screening logic for cryptocurrency assets,
    filtering based on market cap, liquidity, exchange listing, and volatility.

    Crypto-specific considerations:
    - Minimum market cap to avoid micro-cap scams
    - Minimum liquidity for entry/exit
    - Listing on major exchanges for accessibility
    - Volatility range for manageable risk
    - BTC correlation for diversification
    """

    # Major exchanges (most liquid, most reliable)
    MAJOR_EXCHANGES = [
        CryptoExchange.BINANCE,
        CryptoExchange.COINBASE,
        CryptoExchange.KRAKEN,
        CryptoExchange.BITSTAMP,
    ]

    # Tier 2 exchanges (still reliable, less liquidity)
    TIER_2_EXCHANGES = [
        CryptoExchange.GEMINI,
        CryptoExchange.BITFINEX,
        CryptoExchange.OKEX,
        CryptoExchange.HUOBI,
        CryptoExchange.KUCOIN,
    ]

    # Minimum market caps by asset type (USD)
    MIN_MARKET_CAP_BY_TYPE = {
        CryptoAssetType.BITCOIN: Decimal("10000000000"),  # $10B+
        CryptoAssetType.ETHEREUM: Decimal("5000000000"),  # $5B+
        CryptoAssetType.STABLECOIN: Decimal("1000000000"),  # $1B+
        CryptoAssetType.DEFI: Decimal("500000000"),  # $500M+
        CryptoAssetType.L1_BLOCKCHAIN: Decimal("1000000000"),  # $1B+
        CryptoAssetType.L2_SCALING: Decimal("500000000"),  # $500M+
        CryptoAssetType.UTILITY: Decimal("200000000"),  # $200M+
        CryptoAssetType.EXCHANGE: Decimal("500000000"),  # $500M+
        CryptoAssetType.NFT_PLATFORM: Decimal("100000000"),  # $100M+
        CryptoAssetType.MEME: Decimal("50000000"),  # $50M+
        CryptoAssetType.PRIVACY: Decimal("100000000"),  # $100M+
        CryptoAssetType.OTHER: Decimal("100000000"),  # $100M+
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize crypto screener.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.screening_history: List[CryptoScreeningResult] = []

    def screen(
        self,
        universe: List[CryptoAsset],
        min_market_cap: Optional[Decimal] = None,
        min_daily_volume: Optional[Decimal] = None,
        min_liquidity_score: Optional[Decimal] = None,
        max_volatility: Optional[Decimal] = None,
        required_exchanges: Optional[List[CryptoExchange]] = None,
        asset_types: Optional[List[CryptoAssetType]] = None,
    ) -> CryptoScreeningResult:
        """
        Screen crypto assets by criteria.

        Args:
            universe: List of crypto assets to screen
            min_market_cap: Minimum market cap (USD)
            min_daily_volume: Minimum daily volume (USD)
            min_liquidity_score: Minimum liquidity score (0-100)
            max_volatility: Maximum volatility (% annualized)
            required_exchanges: Required exchanges for listing
            asset_types: Asset types to include

        Returns:
            Screening result with passed and failed assets
        """
        start_time = time.time()

        # Set defaults from config
        min_market_cap = min_market_cap or Decimal(
            str(self.config.get("min_market_cap", "1000000000"))
        )
        min_daily_volume = min_daily_volume or Decimal(
            str(self.config.get("min_daily_volume", "10000000"))
        )
        min_liquidity_score = min_liquidity_score or Decimal(
            str(self.config.get("min_liquidity_score", "50"))
        )
        max_volatility = max_volatility or self.config.get("max_volatility")

        passed_assets: List[CryptoAsset] = []
        failed_assets: Dict[str, List[str]] = {}

        for asset in universe:
            failures = self._check_asset(
                asset=asset,
                min_market_cap=min_market_cap,
                min_daily_volume=min_daily_volume,
                min_liquidity_score=min_liquidity_score,
                max_volatility=max_volatility,
                required_exchanges=required_exchanges,
                asset_types=asset_types,
            )

            if failures:
                failed_assets[asset.symbol] = failures
            else:
                passed_assets.append(asset)

        elapsed_ms = (time.time() - start_time) * 1000

        result = CryptoScreeningResult(
            passed_assets=passed_assets,
            failed_assets=failed_assets,
            total_evaluated=len(universe),
            screening_time_ms=elapsed_ms,
            min_market_cap=min_market_cap,
            min_daily_volume=min_daily_volume,
            min_liquidity_score=min_liquidity_score,
        )

        self.screening_history.append(result)

        logger.info(
            f"Screening complete: {len(passed_assets)}/{len(universe)} passed "
            f"({result.pass_rate:.1f}%), {elapsed_ms:.1f}ms"
        )

        return result

    def _check_asset(
        self,
        asset: CryptoAsset,
        min_market_cap: Decimal,
        min_daily_volume: Decimal,
        min_liquidity_score: Decimal,
        max_volatility: Optional[Decimal],
        required_exchanges: Optional[List[CryptoExchange]],
        asset_types: Optional[List[CryptoAssetType]],
    ) -> List[str]:
        """
        Check if an asset meets all screening criteria.

        Args:
            asset: Crypto asset to check
            min_market_cap: Minimum market cap
            min_daily_volume: Minimum daily volume
            min_liquidity_score: Minimum liquidity score
            max_volatility: Maximum volatility
            required_exchanges: Required exchanges
            asset_types: Allowed asset types

        Returns:
            List of failure reasons (empty if passes)
        """
        failures: List[str] = []

        # Market cap check
        type_min_cap = self.MIN_MARKET_CAP_BY_TYPE.get(asset.asset_type, Decimal("100000000"))
        effective_min_cap = max(min_market_cap, type_min_cap)

        if asset.market_cap < effective_min_cap:
            failures.append(
                f"Market cap too low: ${asset.market_cap:,.0f} < ${effective_min_cap:,.0f}"
            )

        # Daily volume check
        if asset.avg_daily_volume < min_daily_volume:
            failures.append(
                f"Volume too low: ${asset.avg_daily_volume:,.0f} < ${min_daily_volume:,.0f}"
            )

        # Liquidity score check
        if asset.liquidity_score < min_liquidity_score:
            failures.append(
                f"Liquidity score too low: {asset.liquidity_score} < {min_liquidity_score}"
            )

        # Volatility check
        if max_volatility is not None:
            if asset.volatility_90d > max_volatility:
                failures.append(
                    f"Volatility too high: {asset.volatility_90d:.1f}% > {max_volatility:.1f}%"
                )

        # Exchange listing check
        if required_exchanges:
            if not any(exchange in asset.exchanges for exchange in required_exchanges):
                failures.append(
                    f"Not listed on required exchanges: "
                    f"has {[e.value for e in asset.exchanges]}, "
                    f"needs {[e.value for e in required_exchanges]}"
                )

        # Asset type filter
        if asset_types and asset.asset_type not in asset_types:
            failures.append(f"Asset type not allowed: {asset.asset_type.value}")

        return failures

    def calculate_liquidity_score(self, asset: CryptoAsset) -> Decimal:
        """
        Calculate liquidity score for a crypto asset.

        Score is based on:
        - Daily volume relative to market cap (volume/market_cap ratio)
        - Number of major exchange listings
        - Bid-ask spread (if available)

        Higher score = more liquid

        Args:
            asset: Crypto asset

        Returns:
            Liquidity score (0-100)
        """
        score = Decimal("0")

        # Volume/market cap ratio (higher is better)
        if asset.market_cap > 0:
            volume_ratio = asset.avg_daily_volume / asset.market_cap
            # 5% daily volume = 100 points, 0.1% = 0 points
            vol_score = min(100, volume_ratio * 2000)
            score += Decimal(str(vol_score)) * Decimal("0.6")

        # Exchange listing score
        major_count = sum(1 for e in asset.exchanges if e in self.MAJOR_EXCHANGES)
        tier2_count = sum(1 for e in asset.exchanges if e in self.TIER_2_EXCHANGES)

        # Major exchanges worth more
        exchange_score = major_count * 20 + tier2_count * 10
        score += Decimal(str(min(100, exchange_score))) * Decimal("0.4")

        return min(Decimal("100"), score).quantize(Decimal("0.01"))

    def verify_listing(self, symbol: str, major_exchanges: List[CryptoExchange]) -> bool:
        """
        Verify asset trades on major exchanges.

        In production, this would query exchange APIs.
        For now, returns True if any major exchange is in the list.

        Args:
            symbol: Trading symbol
            major_exchanges: List of major exchanges to check

        Returns:
            True if listed on any major exchange
        """
        # In production, implement actual exchange API calls
        # For now, just check if the list is non-empty
        return len(major_exchanges) > 0

    def calculate_btc_correlation_score(self, asset: CryptoAsset) -> Decimal:
        """
        Calculate BTC correlation score for diversification analysis.

        Lower correlation to BTC = better diversification potential.

        Args:
            asset: Crypto asset

        Returns:
            Correlation score (0-100, where 100 = uncorrelated)
        """
        if asset.btc_correlation is None:
            return Decimal("50")  # Neutral score

        # Invert correlation: low correlation = high score
        correlation = asset.btc_correlation

        # Correlation of 0 = 100 points, correlation of 1 = 0 points
        score = (1 - abs(correlation)) * 100

        return Decimal(str(score)).quantize(Decimal("0.01"))

    def get_screening_summary(self) -> Dict:
        """
        Get summary of screening history.

        Returns:
            Summary statistics
        """
        if not self.screening_history:
            return {"total_screenings": 0}

        total_evaluations = sum(r.total_evaluated for r in self.screening_history)
        total_passed = sum(len(r.passed_assets) for r in self.screening_history)
        avg_pass_rate = sum(r.pass_rate for r in self.screening_history) / len(
            self.screening_history
        )
        avg_time_ms = sum(r.screening_time_ms for r in self.screening_history) / len(
            self.screening_history
        )

        return {
            "total_screenings": len(self.screening_history),
            "total_evaluations": total_evaluations,
            "total_passed": total_passed,
            "avg_pass_rate": avg_pass_rate,
            "avg_screening_time_ms": avg_time_ms,
        }
