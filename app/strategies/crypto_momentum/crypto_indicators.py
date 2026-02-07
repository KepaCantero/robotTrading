"""
Crypto-Specific Technical Indicators

This module provides technical indicators optimized for cryptocurrency markets,
including on-chain metrics, network health indicators, and sentiment measures.

Crypto-specific indicators differ from traditional markets:
- Network Value to Transactions (NVT) ratio
- Mayer Multiple (for Bitcoin)
- Active addresses and transaction counts
- Hash rate (for PoW coins)
- Staking ratios (for PoS coins)
- Token velocity
- Fear & Greed index components
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .models import OnChainMetrics

logger = logging.getLogger(__name__)


class CryptoIndicators:
    """
    Technical indicators optimized for crypto assets.

    This class provides crypto-specific technical indicators that go beyond
    traditional price-based metrics to include on-chain and network metrics.

    Key differences from traditional markets:
    - On-chain transaction data
    - Network activity metrics
    - Social sentiment impact
    - Bitcoin correlation effects
    - 24/7 trading patterns
    """

    def __init__(self):
        """Initialize crypto indicators calculator."""
        self.indicator_cache: Dict[str, Dict] = {}

    def calculate_nvt_ratio(
        self,
        market_cap: pd.Series,
        transaction_volume: pd.Series,
        ma_days: int = 30,
    ) -> pd.Series:
        """
        Calculate Network Value to Transactions ratio.

        NVT = market_cap / transaction_volume

        High NVT indicates network value is high relative to on-chain activity
        (potentially overvalued). Low NVT indicates undervaluation.

        Args:
            market_cap: Series of market cap values
            transaction_volume: Series of transaction volumes
            ma_days: Moving average days for smoothing

        Returns:
            Series of NVT ratio values
        """
        # Smooth transaction volume with moving average
        tx_ma = transaction_volume.rolling(window=ma_days).mean()

        # Calculate NVT ratio
        nvt = market_cap / tx_ma

        logger.debug(f"Calculated NVT ratio: mean={nvt.mean():.2f}, std={nvt.std():.2f}")

        return nvt

    def calculate_mayer_multiple(
        self, current_price: float, realized_cap: pd.Series, ma_days: int = 200
    ) -> float:
        """
        Calculate Mayer Multiple (for Bitcoin).

        Mayer Multiple = price / (200-day MA of realized cap)

        Interpretation:
        - > 2.4: Overvalued (historical top zone)
        - 1.0 - 2.4: Normal range
        - < 1.0: Undervalued (historical bottom zone)

        Args:
            current_price: Current BTC price
            realized_cap: Series of realized cap values
            ma_days: Moving average days

        Returns:
            Mayer Multiple value
        """
        realized_ma = realized_cap.rolling(window=ma_days).mean()
        mayer_multiple = current_price / realized_ma.iloc[-1]

        logger.debug(f"Calculated Mayer Multiple: {mayer_multiple:.2f}")

        return mayer_multiple

    def calculate_fear_greed_index(self, metrics: Dict[str, float]) -> float:
        """
        Calculate Fear & Greed index for crypto markets.

        Combines multiple factors:
        - Volatility (25%)
        - Market momentum (25%)
        - Social media (15%)
        - Surveys (15%)
        - Taker buy/sell ratio (10%)
        - Bitcoin dominance (10%)

        Returns value from 0 (Extreme Fear) to 100 (Extreme Greed).

        Args:
            metrics: Dictionary with metric values

        Returns:
            Fear & Greed index (0-100)
        """
        weights = {
            "volatility": 0.25,
            "momentum": 0.25,
            "social_media": 0.15,
            "surveys": 0.15,
            "taker_buy_sell": 0.10,
            "btc_dominance": 0.10,
        }

        score = 0.0

        # Volatility component (inverse: higher vol = more fear)
        if "volatility" in metrics:
            vol = metrics["volatility"]
            # Assume normal vol is around 50%, scale 0-100
            vol_score = max(0, min(100, 100 - (vol - 20) * 2))
            score += vol_score * weights["volatility"]

        # Momentum component
        if "momentum" in metrics:
            mom = metrics["momentum"]
            # Positive momentum = greed, negative = fear
            momentum_score = 50 + mom * 10
            momentum_score = max(0, min(100, momentum_score))
            score += momentum_score * weights["momentum"]

        # Social media sentiment
        if "social_media" in metrics:
            social = metrics["social_media"]
            score += social * weights["social_media"]

        # Surveys
        if "surveys" in metrics:
            survey = metrics["surveys"]
            score += survey * weights["surveys"]

        # Taker buy/sell ratio
        if "taker_buy_sell" in metrics:
            taker = metrics["taker_buy_sell"]
            # Ratio > 1 = more buying (greed), < 1 = more selling (fear)
            taker_score = 50 + (taker - 1) * 50
            taker_score = max(0, min(100, taker_score))
            score += taker_score * weights["taker_buy_sell"]

        # BTC dominance (inverse: higher BTC dominance = altcoin fear)
        if "btc_dominance" in metrics:
            btc_dom = metrics["btc_dominance"]
            # Higher dominance = more fear in altcoins
            dom_score = max(0, min(100, 100 - btc_dom))
            score += dom_score * weights["btc_dominance"]

        logger.debug(f"Calculated Fear & Greed index: {score:.1f}")

        return score

    def calculate_relative_strength(
        self, asset_prices: pd.Series, btc_prices: pd.Series
    ) -> pd.Series:
        """
        Calculate relative strength vs Bitcoin.

        RS = asset_return / btc_return

        Values > 1 indicate asset outperforming BTC.
        Values < 1 indicate asset underperforming BTC.

        Args:
            asset_prices: Series of asset prices
            btc_prices: Series of BTC prices

        Returns:
            Series of relative strength values
        """
        # Calculate returns
        asset_returns = asset_prices.pct_change()
        btc_returns = btc_prices.pct_change()

        # Calculate relative strength
        rs = asset_returns / btc_returns

        logger.debug(f"Calculated relative strength: mean={rs.mean():.2f}")

        return rs

    def calculate_momentum_score(
        self,
        prices: pd.Series,
        benchmark_prices: Optional[pd.Series] = None,
        lookback_days: int = 90,
    ) -> float:
        """
        Calculate volatility-adjusted momentum score.

        Score = (return / volatility) × beta_adjustment

        Where:
        - return: n-day return
        - volatility: annualized vol
        - beta_adjustment: reduce if high BTC correlation

        Args:
            prices: Price series
            benchmark_prices: Benchmark (BTC) price series for beta
            lookback_days: Lookback period

        Returns:
            Momentum score (0-100)
        """
        if len(prices) < lookback_days:
            logger.warning(f"Insufficient data: {len(prices)} < {lookback_days}")
            return 50.0

        # Use last lookback_days
        recent_prices = prices.tail(lookback_days)

        # Calculate total return
        total_return = (recent_prices.iloc[-1] / recent_prices.iloc[0]) - 1

        # Calculate annualized volatility
        returns = recent_prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(365)  # 365 days for crypto

        # Risk-adjusted return (Sharpe-like ratio without risk-free rate)
        if volatility > 0:
            risk_adj_return = total_return / volatility
        else:
            risk_adj_return = 0

        # Normalize to 0-100 scale
        # Assume reasonable range is -2 to +2 risk-adjusted returns
        raw_score = 50 + risk_adj_return * 25
        raw_score = max(0, min(100, raw_score))

        # Adjust for BTC correlation if benchmark provided
        if benchmark_prices is not None and len(benchmark_prices) >= lookback_days:
            btc_adj = self._calculate_btc_adjustment(
                recent_prices, benchmark_prices.tail(lookback_days)
            )
            raw_score *= btc_adj

        final_score = max(0, min(100, raw_score))

        logger.debug(
            f"Momentum score: {final_score:.1f} "
            f"(return={total_return:.2%}, vol={volatility:.2%})"
        )

        return final_score

    def calculate_crypto_beta(self, asset_returns: pd.Series, btc_returns: pd.Series) -> float:
        """
        Calculate beta to Bitcoin.

        Crypto assets with high BTC beta may not provide
        diversification benefits.

        Beta = Cov(asset, btc) / Var(btc)

        Args:
            asset_returns: Asset return series
            btc_returns: BTC return series

        Returns:
            Beta value
        """
        # Align series
        aligned_data = pd.DataFrame({"asset": asset_returns, "btc": btc_returns}).dropna()

        if len(aligned_data) < 2:
            logger.warning("Insufficient data for beta calculation")
            return 1.0

        covariance = aligned_data["asset"].cov(aligned_data["btc"])
        btc_variance = aligned_data["btc"].var()

        if btc_variance == 0:
            logger.warning("Zero BTC variance")
            return 1.0

        beta = covariance / btc_variance

        logger.debug(f"Calculated BTC beta: {beta:.2f}")

        return beta

    def calculate_network_health_score(self, on_chain_metrics: OnChainMetrics) -> Optional[Decimal]:
        """
        Calculate network health score from on-chain metrics.

        Combines:
        - Active addresses growth
        - Transaction count growth
        - Transaction volume growth
        - NVT ratio (inverse)

        Args:
            on_chain_metrics: On-chain metrics

        Returns:
            Network health score (0-100)
        """
        if on_chain_metrics.network_health_score is not None:
            return on_chain_metrics.network_health_score

        # Calculate individual components
        score_parts = []

        # Active addresses score (more is better, up to a point)
        if on_chain_metrics.active_addresses:
            addr_score = min(100, on_chain_metrics.active_addresses / 10000)
            score_parts.append(addr_score)

        # Transaction count score
        if on_chain_metrics.transaction_count:
            tx_score = min(100, on_chain_metrics.transaction_count / 100000)
            score_parts.append(tx_score)

        # Transaction volume score
        if on_chain_metrics.transaction_volume:
            vol_score = min(100, float(on_chain_metrics.transaction_volume) / 1_000_000)
            score_parts.append(float(vol_score))

        # NVT ratio (inverse: lower is better)
        if on_chain_metrics.nvt_ratio:
            nvt = float(on_chain_metrics.nvt_ratio)
            # NVT of 100 = 0 points, NVT of 10 = 100 points
            nvt_score = max(0, min(100, 120 - nvt))
            score_parts.append(nvt_score)

        if not score_parts:
            return None

        avg_score = sum(score_parts) / len(score_parts)

        logger.debug(f"Network health score: {avg_score:.1f}")

        return Decimal(str(avg_score)).quantize(Decimal("0.01"))

    def calculate_token_velocity(self, transaction_volume: Decimal, market_cap: Decimal) -> Decimal:
        """
        Calculate token velocity.

        Velocity = transaction_volume / market_cap

        Higher velocity indicates more active usage of the token.

        Args:
            transaction_volume: Annual transaction volume
            market_cap: Current market cap

        Returns:
            Token velocity (annualized)
        """
        if market_cap == 0:
            return Decimal("0")

        velocity = transaction_volume / market_cap

        logger.debug(f"Token velocity: {velocity:.2f}")

        return velocity.quantize(Decimal("0.01"))

    def calculate_staking_apr(self, staking_rewards: Decimal, staked_amount: Decimal) -> Decimal:
        """
        Calculate annual percentage rate for staking.

        Args:
            staking_rewards: Annual staking rewards
            staked_amount: Amount staked

        Returns:
            APR as percentage
        """
        if staked_amount == 0:
            return Decimal("0")

        apr = (staking_rewards / staked_amount) * 100

        logger.debug(f"Staking APR: {apr:.2f}%")

        return apr.quantize(Decimal("0.01"))

    def _calculate_btc_adjustment(self, asset_prices: pd.Series, btc_prices: pd.Series) -> float:
        """
        Calculate BTC correlation adjustment factor.

        Reduces score for assets highly correlated with BTC
        since they don't provide diversification benefits.

        Args:
            asset_prices: Asset price series
            btc_prices: BTC price series

        Returns:
            Adjustment factor (0.5 to 1.0)
        """
        asset_returns = asset_prices.pct_change().dropna()
        btc_returns = btc_prices.pct_change().dropna()

        # Calculate correlation
        aligned_data = pd.DataFrame({"asset": asset_returns, "btc": btc_returns}).dropna()

        if len(aligned_data) < 2:
            return 1.0

        correlation = aligned_data["asset"].corr(aligned_data["btc"])

        # Adjustment: high correlation = lower score
        # Correlation 0-0.3 = 1.0 (no penalty)
        # Correlation 0.3-0.7 = 0.8 (slight penalty)
        # Correlation 0.7-1.0 = 0.5 (significant penalty)
        abs_corr = abs(correlation)

        if abs_corr < 0.3:
            return 1.0
        elif abs_corr < 0.7:
            return 0.8
        else:
            return 0.5

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index for crypto prices.

        Args:
            prices: Price series
            period: RSI period

        Returns:
            RSI series
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: Price series
            period: EMA period

        Returns:
            EMA series
        """
        return prices.ewm(span=period, adjust=False).mean()

    def calculate_macd(
        self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD indicator.

        Args:
            prices: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram
