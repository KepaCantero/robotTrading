"""
Market Quality Metrics

Implements O'Hara Rule 7.9: Calculate market quality metrics.

Market quality metrics help decide whether to trade in a given market
by measuring liquidity, volatility, depth, and efficiency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MarketQualityMetrics:
    """Comprehensive market quality metrics (O'Hara Rule 7.9)."""

    symbol: str
    timestamp: pd.Timestamp

    # Core metrics
    avg_spread_bps: float
    avg_depth: float  # Average total depth
    realized_volatility: float  # Annualized
    avg_daily_volume: float

    # Composite score
    quality_score: float  # 0-100, higher = better quality

    # Regime classification
    liquidity_regime: str  # HIGH, NORMAL, LOW, STRESS
    volatility_regime: str  # LOW, NORMAL, HIGH, EXTREME

    # Trading recommendation
    can_trade: bool
    max_position_size: float | None
    recommended_order_type: str  # MARKET, LIMIT, ICEBERG, etc.


class MarketQualityCalculator:
    """
    Market Quality Metrics Calculator (O'Hara Rule 7.9).

    Calculates comprehensive market quality metrics to inform
    trading decisions and execution strategy.
    """

    # Quality score weights
    SPREAD_WEIGHT = 0.25
    DEPTH_WEIGHT = 0.25
    VOLATILITY_WEIGHT = 0.20
    VOLUME_WEIGHT = 0.15
    IMPACT_WEIGHT = 0.15

    # Thresholds for regime classification
    SPREAD_THRESHOLDS: ClassVar[dict] = {
        "EXCELLENT": 2.0,  # < 2 bps
        "GOOD": 5.0,  # < 5 bps
        "FAIR": 15.0,  # < 15 bps
        "POOR": 50.0,  # < 50 bps
    }

    VOLATILITY_THRESHOLDS: ClassVar[dict] = {
        "LOW": 0.10,  # < 10% annualized
        "NORMAL": 0.25,  # < 25%
        "HIGH": 0.50,  # < 50%
        "EXTREME": 1.0,  # >= 50%
    }

    def __init__(
        self,
        lookback_days: int = 20,
        min_quality_score: float = 50.0,
    ):
        """
        Initialize calculator.

        Args:
            lookback_days: Days to look back for metrics
            min_quality_score: Minimum quality score to allow trading
        """
        self.lookback_days = lookback_days
        self.min_quality_score = min_quality_score

        logger.info(
            f"MarketQualityCalculator initialized: lookback={lookback_days}d, "
            f"min_quality={min_quality_score}"
        )

    def calculate_market_quality(
        self,
        symbol: str,
        price_history: pd.DataFrame,
        volume_history: pd.DataFrame | None = None,
        order_books: list[dict] | None = None,
        price_col: str = "close",
        volume_col: str = "volume",
        bid_col: str | None = "bid",
        ask_col: str | None = "ask",
    ) -> MarketQualityMetrics:
        """
        Calculate comprehensive market quality metrics.

        Args:
            symbol: Trading symbol
            price_history: Price history DataFrame
            volume_history: Optional volume history
            order_books: Optional order book snapshots
            price_col: Price column name
            volume_col: Volume column name
            bid_col: Bid price column name
            ask_col: Ask price column name

        Returns:
            MarketQualityMetrics with all metrics
        """
        # Get recent data
        recent = price_history.tail(min(self.lookback_days, len(price_history)))

        # 1. Calculate spread metrics
        spread_bps = self._calculate_spread_bps(recent, bid_col, ask_col, price_col)

        # 2. Calculate depth metrics
        avg_depth = self._calculate_average_depth(order_books)

        # 3. Calculate volatility
        realized_vol = self._calculate_realized_volatility(recent, price_col)

        # 4. Calculate volume
        avg_daily_vol = self._calculate_average_daily_volume(
            price_history if volume_history is None else volume_history,
            volume_col,
        )

        # 5. Estimate market impact function
        impact_params = self._estimate_impact_function(price_history, volume_col, price_col)

        # 6. Calculate composite quality score
        quality_score = self._calculate_quality_score(
            spread_bps=spread_bps,
            avg_depth=avg_depth,
            volatility=realized_vol,
            volume=avg_daily_vol,
            impact_slope=impact_params.get("slope", 0.001),
        )

        # 7. Classify regimes
        liquidity_regime = self._classify_liquidity_regime(spread_bps, avg_depth)
        volatility_regime = self._classify_volatility_regime(realized_vol)

        # 8. Make trading recommendation
        can_trade = quality_score >= self.min_quality_score
        max_size = self._calculate_max_position_size(avg_daily_vol, quality_score, realized_vol)
        order_type = self._recommend_order_type(liquidity_regime, volatility_regime, spread_bps)

        return MarketQualityMetrics(
            symbol=symbol,
            timestamp=pd.Timestamp.now(),
            avg_spread_bps=spread_bps,
            avg_depth=avg_depth,
            realized_volatility=realized_vol,
            avg_daily_volume=avg_daily_vol,
            quality_score=quality_score,
            liquidity_regime=liquidity_regime,
            volatility_regime=volatility_regime,
            can_trade=can_trade,
            max_position_size=max_size,
            recommended_order_type=order_type,
        )

    def _calculate_spread_bps(
        self,
        df: pd.DataFrame,
        bid_col: str | None,
        ask_col: str | None,
        price_col: str,
    ) -> float:
        """Calculate average spread in basis points."""
        if bid_col and ask_col and bid_col in df.columns and ask_col in df.columns:
            # Use actual bid-ask
            df["spread"] = df[ask_col] - df[bid_col]
            df["mid"] = (df[bid_col] + df[ask_col]) / 2
            df["spread_bps"] = (df["spread"] / df["mid"]) * 10000
            return df["spread_bps"].mean()
        else:
            # Estimate spread from price movements
            # UseRolling estimator: spread ≈ 2 * std(returns)
            returns = df[price_col].pct_change().dropna()
            # Approximate spread as 2x the daily volatility (in bps)
            daily_vol = returns.std()
            spread_estimate = 2 * daily_vol * 10000
            return spread_estimate

    def _calculate_average_depth(
        self,
        order_books: list[dict] | None,
    ) -> float:
        """Calculate average order book depth."""
        if not order_books:
            return 0.0

        depths = []
        for book in order_books:
            bid_depth = sum(level.get("size", 0) for level in book.get("bids", []))
            ask_depth = sum(level.get("size", 0) for level in book.get("asks", []))
            depths.append(bid_depth + ask_depth)

        return np.mean(depths) if depths else 0.0

    def _calculate_realized_volatility(
        self,
        df: pd.DataFrame,
        price_col: str,
    ) -> float:
        """Calculate annualized realized volatility."""
        returns = df[price_col].pct_change().dropna()

        if len(returns) == 0:
            return 0.0

        daily_vol = returns.std()

        # Annualize (assuming 252 trading days)
        annualized_vol = daily_vol * np.sqrt(252)

        return annualized_vol

    def _calculate_average_daily_volume(
        self,
        df: pd.DataFrame,
        volume_col: str,
    ) -> float:
        """Calculate average daily volume."""
        if volume_col not in df.columns:
            return 0.0

        # Group by date and sum
        df_copy = df.copy()
        df_copy["date"] = pd.to_datetime(df_copy.index).date
        daily_volumes = df_copy.groupby("date")[volume_col].sum()

        return daily_volumes.mean() if len(daily_volumes) > 0 else 0.0

    def _estimate_impact_function(
        self,
        df: pd.DataFrame,
        volume_col: str,
        price_col: str,
    ) -> dict[str, float]:
        """
        Estimate market impact function: impact ~ a * (size / ADV)^b

        Returns coefficients a and b.
        """
        if volume_col not in df.columns:
            return {"slope": 0.001, "intercept": 0.0}

        # Use price-volume relationship as proxy
        df = df.copy()
        df["returns"] = df[price_col].pct_change()
        df["volume_zscore"] = (df[volume_col] - df[volume_col].mean()) / df[volume_col].std()

        # Correlation between volume and price moves (proxy for impact)
        correlation = df[["returns", "volume_zscore"]].corr().iloc[0, 1]

        # Impact slope (higher correlation = more impact)
        slope = abs(correlation) * 0.001 if not np.isnan(correlation) else 0.001

        return {"slope": slope, "intercept": 0.0}

    def _calculate_quality_score(
        self,
        spread_bps: float,
        avg_depth: float,
        volatility: float,
        volume: float,
        impact_slope: float,
    ) -> float:
        """
        Calculate composite market quality score (0-100).

        Higher score = better quality.
        """
        # 1. Spread score (tighter = better, max 25 points)
        if spread_bps <= self.SPREAD_THRESHOLDS["EXCELLENT"]:
            spread_score = 25.0
        elif spread_bps <= self.SPREAD_THRESHOLDS["GOOD"]:
            spread_score = 20.0
        elif spread_bps <= self.SPREAD_THRESHOLDS["FAIR"]:
            spread_score = 15.0
        elif spread_bps <= self.SPREAD_THRESHOLDS["POOR"]:
            spread_score = 10.0
        else:
            spread_score = 5.0

        # 2. Depth score (deeper = better, max 25 points)
        depth_score = min(25.0, avg_depth / 100000)  # 1M shares = 25 points

        # 3. Volatility score (lower = better for many strategies, max 20 points)
        if volatility <= self.VOLATILITY_THRESHOLDS["LOW"]:
            vol_score = 20.0
        elif volatility <= self.VOLATILITY_THRESHOLDS["NORMAL"]:
            vol_score = 15.0
        elif volatility <= self.VOLATILITY_THRESHOLDS["HIGH"]:
            vol_score = 10.0
        else:
            vol_score = 5.0

        # 4. Volume score (higher = better, max 15 points)
        volume_score = min(15.0, volume / 1000000)  # 10M shares = 15 points

        # 5. Impact score (lower impact = better, max 15 points)
        # Lower slope = less impact per unit volume
        impact_score = max(0, 15.0 - (impact_slope * 10000))

        # Total score
        total_score = (
            spread_score * self.SPREAD_WEIGHT * 4  # Normalize to 100
            + depth_score * self.DEPTH_WEIGHT * 4
            + vol_score * self.VOLATILITY_WEIGHT * 5
            + volume_score * self.VOLUME_WEIGHT * 5
            + impact_score * self.IMPACT_WEIGHT * 5
        )

        return min(100.0, max(0.0, total_score))

    def _classify_liquidity_regime(
        self,
        spread_bps: float,
        avg_depth: float,
    ) -> str:
        """Classify liquidity regime."""
        if spread_bps <= self.SPREAD_THRESHOLDS["EXCELLENT"] and avg_depth > 500000:
            return "EXCELLENT"
        elif spread_bps <= self.SPREAD_THRESHOLDS["GOOD"] and avg_depth > 200000:
            return "GOOD"
        elif spread_bps <= self.SPREAD_THRESHOLDS["FAIR"] and avg_depth > 50000:
            return "FAIR"
        else:
            return "POOR"

    def _classify_volatility_regime(
        self,
        volatility: float,
    ) -> str:
        """Classify volatility regime."""
        if volatility <= self.VOLATILITY_THRESHOLDS["LOW"]:
            return "LOW"
        elif volatility <= self.VOLATILITY_THRESHOLDS["NORMAL"]:
            return "NORMAL"
        elif volatility <= self.VOLATILITY_THRESHOLDS["HIGH"]:
            return "HIGH"
        else:
            return "EXTREME"

    def _calculate_max_position_size(
        self,
        avg_daily_volume: float,
        quality_score: float,
        volatility: float,
    ) -> float | None:
        """
        Calculate maximum recommended position size.

        Based on:
        - Daily volume (don't exceed X% of volume)
        - Market quality (lower quality = smaller position)
        - Volatility (higher vol = smaller position)
        """
        if avg_daily_volume == 0:
            return None

        # Base: 10% of daily volume
        base_size = avg_daily_volume * 0.10

        # Quality multiplier (0-1)
        quality_mult = quality_score / 100.0

        # Volatility penalty
        vol_penalty = min(1.0, 0.25 / volatility) if volatility > 0 else 1.0

        max_size = base_size * quality_mult * vol_penalty

        return max_size

    def _recommend_order_type(
        self,
        liquidity_regime: str,
        volatility_regime: str,
        spread_bps: float,
    ) -> str:
        """Recommend order type based on market conditions."""
        # Wide spread + low liquidity = use limit orders
        if spread_bps > 10 or liquidity_regime in ["POOR", "FAIR"]:
            return "LIMIT"

        # High volatility = use limit or stop-limit
        if volatility_regime in ["HIGH", "EXTREME"]:
            return "STOP_LIMIT"

        # Normal conditions = market orders acceptable
        if liquidity_regime in ["EXCELLENT", "GOOD"] and volatility_regime == "LOW":
            return "MARKET"

        # Default
        return "LIMIT"

    def compare_market_quality(
        self,
        symbols: list[str],
        price_data: dict[str, pd.DataFrame],
        volume_data: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """
        Compare market quality across multiple symbols.

        Returns DataFrame ranked by quality score.
        """
        results = []

        for symbol in symbols:
            df = price_data.get(symbol)
            if df is None:
                continue

            vol_df = volume_data.get(symbol) if volume_data else None

            metrics = self.calculate_market_quality(
                symbol=symbol,
                price_history=df,
                volume_history=vol_df,
            )

            results.append(
                {
                    "symbol": symbol,
                    "quality_score": metrics.quality_score,
                    "spread_bps": metrics.avg_spread_bps,
                    "depth": metrics.avg_depth,
                    "volatility": metrics.realized_volatility,
                    "volume": metrics.avg_daily_volume,
                    "liquidity_regime": metrics.liquidity_regime,
                    "can_trade": metrics.can_trade,
                }
            )

        result_df = pd.DataFrame(results)

        if len(result_df) > 0:
            result_df = result_df.sort_values("quality_score", ascending=False)

        return result_df


# Global singleton
_market_quality_calculator: MarketQualityCalculator = None


def get_market_quality_metrics(
    lookback_days: int = 20,
    min_quality_score: float = 50.0,
) -> MarketQualityCalculator:
    """Get or create global MarketQualityCalculator instance."""
    global _market_quality_calculator
    if _market_quality_calculator is None:
        _market_quality_calculator = MarketQualityCalculator(
            lookback_days=lookback_days,
            min_quality_score=min_quality_score,
        )

    return _market_quality_calculator
