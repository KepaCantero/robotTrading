"""
Bid-Ask Bounce Removal

Implements Harris Rule 6.2: Remove bid-ask bounce noise from price data.

Bid-ask bounce creates artificial volatility when trades alternate between
bid and ask prices. This module provides methods to filter this noise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BounceAnalysisResult:
    """Result of bid-ask bounce analysis."""

    original_volatility: float
    mid_price_volatility: float
    bounce_ratio: float  # Higher = more bounce noise
    is_bounce_dominant: bool
    recommended_method: str


class BidAskBounceRemover:
    """
    Bid-Ask Bounce Removal (Harris Rule 6.2).

    Filters out artificial volatility created by bid-ask bounce.
    """

    def __init__(
        self,
        min_bounce_threshold: float = 0.3,
        default_method: str = "mid_price",
    ):
        """
        Initialize remover.

        Args:
            min_bounce_threshold: Minimum bounce ratio to consider bounce dominant
            default_method: Default removal method (mid_price, vwap, ewma)
        """
        self.min_bounce_threshold = min_bounce_threshold
        self.default_method = default_method

        logger.info(
            f"BidAskBounceRemover initialized with method={default_method}, "
            f"threshold={min_bounce_threshold}"
        )

    def remove_bid_ask_bounce(
        self,
        df: pd.DataFrame,
        bid_col: str = "bid",
        ask_col: str = "ask",
        last_col: str = "close",
        method: str | None = None,
        span: int = 20,
    ) -> pd.Series:
        """
        Remove bid-ask bounce from price data.

        Args:
            df: DataFrame with bid/ask/last prices
            bid_col: Column name for bid prices
            ask_col: Column name for ask prices
            last_col: Column name for last trade prices
            method: Removal method (mid_price, vwap, ewma, last_with_threshold)
            span: Span for EWMA smoothing

        Returns:
            Series with bounce-adjusted prices
        """
        method = method or self.default_method

        if method == "mid_price":
            return self._mid_price_method(df, bid_col, ask_col)
        elif method == "vwap":
            return self._vwap_method(df, bid_col, ask_col, last_col)
        elif method == "ewma":
            return self._ewma_method(df, bid_col, ask_col, span)
        elif method == "last_with_threshold":
            return self._threshold_method(df, last_col, bid_col, ask_col)
        else:
            logger.warning(f"Unknown method {method}, using mid_price")
            return self._mid_price_method(df, bid_col, ask_col)

    def _mid_price_method(
        self,
        df: pd.DataFrame,
        bid_col: str,
        ask_col: str,
    ) -> pd.Series:
        """
        Mid-price method: Use (bid + ask) / 2.

        This is the standard method to remove bid-ask bounce.
        """
        if bid_col not in df.columns or ask_col not in df.columns:
            logger.error(f"Columns {bid_col} and/or {ask_col} not found")
            raise ValueError("Bid and ask columns required")

        # Handle missing values
        bids = df[bid_col].ffill()
        asks = df[ask_col].ffill()

        mid_prices = (bids + asks) / 2

        logger.debug(f"Applied mid-price method to {len(mid_prices)} data points")
        return mid_prices

    def _vwap_method(
        self,
        df: pd.DataFrame,
        bid_col: str,
        ask_col: str,
        last_col: str,
    ) -> pd.Series:
        """
        VWAP method: Volume-weighted average of bid and ask.

        Requires volume data.
        """
        bid_vol_col = f"{bid_col}_volume"
        ask_vol_col = f"{ask_col}_volume"

        if bid_vol_col not in df.columns or ask_vol_col not in df.columns:
            logger.warning("Volume data not available, falling back to mid-price")
            return self._mid_price_method(df, bid_col, ask_col)

        # Calculate VWAP
        total_notional = df[bid_col] * df[bid_vol_col] + df[ask_col] * df[ask_vol_col]
        total_volume = df[bid_vol_col] + df[ask_vol_col]

        vwap = total_notional / total_volume

        logger.debug("Applied VWAP method")
        return vwap

    def _ewma_method(
        self,
        df: pd.DataFrame,
        bid_col: str,
        ask_col: str,
        span: int = 20,
    ) -> pd.Series:
        """
        EWMA method: Exponentially weighted moving average of mid prices.

        Provides additional smoothing beyond mid-price.
        """
        mid_prices = self._mid_price_method(df, bid_col, ask_col)
        ewma_prices = mid_prices.ewm(span=span, adjust=False).mean()

        logger.debug(f"Applied EWMA method with span={span}")
        return ewma_prices

    def _threshold_method(
        self,
        df: pd.DataFrame,
        last_col: str,
        bid_col: str,
        ask_col: str,
        threshold_bps: float = 5.0,
    ) -> pd.Series:
        """
        Threshold method: Only update last price if move exceeds threshold.

        This filters out small bid-ask bounces while preserving real moves.
        """
        last_prices = df[last_col].copy()
        mid_prices = self._mid_price_method(df, bid_col, ask_col)

        # Calculate deviation from mid
        deviation_bps = (last_prices - mid_prices).abs() / mid_prices * 10000

        # Only use last price if deviation > threshold
        adjusted_prices = np.where(
            deviation_bps > threshold_bps,
            last_prices,
            mid_prices,
        )

        return pd.Series(adjusted_prices, index=df.index)

    def analyze_bounce(
        self,
        df: pd.DataFrame,
        bid_col: str = "bid",
        ask_col: str = "ask",
        last_col: str = "close",
    ) -> BounceAnalysisResult:
        """
        Analyze extent of bid-ask bounce in data.

        Compares volatility of last prices vs mid prices.
        Higher ratio = more bounce noise.
        """
        if last_col not in df.columns:
            logger.error(f"Column {last_col} not found")
            raise ValueError("Last price column required")

        # Calculate returns
        last_returns = df[last_col].pct_change().dropna()
        mid_prices = self._mid_price_method(df, bid_col, ask_col)
        mid_returns = mid_prices.pct_change().dropna()

        # Calculate volatilities
        original_vol = last_returns.std() * np.sqrt(252)  # Annualized
        mid_vol = mid_returns.std() * np.sqrt(252)

        # Bounce ratio
        bounce_ratio = original_vol / mid_vol if mid_vol > 0 else 1.0

        is_dominant = bounce_ratio > self.min_bounce_threshold

        # Recommend method
        if bounce_ratio > 2.0:
            recommended = "ewma"  # Heavy smoothing needed
        elif bounce_ratio > 1.5:
            recommended = "mid_price"  # Standard approach
        else:
            recommended = "last_with_threshold"  # Minimal filtering

        return BounceAnalysisResult(
            original_volatility=original_vol,
            mid_price_volatility=mid_vol,
            bounce_ratio=bounce_ratio,
            is_bounce_dominant=is_dominant,
            recommended_method=recommended,
        )

    def detect_crossing_pattern(
        self,
        df: pd.DataFrame,
        last_col: str = "close",
        bid_col: str = "bid",
        ask_col: str = "ask",
        window: int = 10,
    ) -> dict[str, any]:
        """
        Detect bid-ask crossing pattern.

        A crossing pattern occurs when trades alternate between bid and ask,
        creating a zigzag pattern.
        """
        if last_col not in df.columns or bid_col not in df.columns or ask_col not in df.columns:
            return {"detected": False, "reason": "Missing required columns"}

        # Classify each trade as buy (at ask) or sell (at bid)
        last_prices = df[last_col]
        bids = df[bid_col]
        asks = df[ask_col]

        # Determine side
        buy_mask = last_prices >= asks  # At or above ask = buy
        sell_mask = last_prices <= bids  # At or below bid = sell

        # Count crossings
        crossings = 0
        for i in range(1, len(df)):
            if (buy_mask.iloc[i] and sell_mask.iloc[i - 1]) or (
                sell_mask.iloc[i] and buy_mask.iloc[i - 1]
            ):
                crossings += 1

        # Calculate crossing rate
        if len(df) > window:
            crossing_rate = crossings / len(df)
            expected_rate = 0.5  # Random would be 50%
            excess_crossing = crossing_rate - expected_rate
        else:
            crossing_rate = 0
            excess_crossing = 0

        return {
            "detected": excess_crossing > 0.1,
            "crossing_rate": crossing_rate,
            "excess_crossing": excess_crossing,
            "total_crossings": crossings,
            "sample_size": len(df),
        }

    def get_optimal_sampling_frequency(
        self,
        df: pd.DataFrame,
        bid_col: str = "bid",
        ask_col: str = "ask",
        min_frequency_seconds: int = 60,
    ) -> int:
        """
        Determine optimal sampling frequency to minimize bounce.

        Lower frequency can reduce bid-ask bounce effects.
        """
        # Calculate spread as percentage
        mid = (df[bid_col] + df[ask_col]) / 2
        spread_pct = ((df[ask_col] - df[bid_col]) / mid * 100).mean()

        # Rule of thumb: sample at interval where spread < 0.5% of price movement
        # For highly liquid stocks (spread ~0.01%), 1-second sampling is fine
        # For illiquid stocks (spread ~0.5%), need 60-second or more

        if spread_pct < 0.02:
            return 1  # 1 second
        elif spread_pct < 0.05:
            return 5  # 5 seconds
        elif spread_pct < 0.1:
            return 15  # 15 seconds
        elif spread_pct < 0.2:
            return 30  # 30 seconds
        else:
            return max(min_frequency_seconds, 60)  # 1 minute or more


# Global singleton
_bid_ask_bounce_remover: BidAskBounceRemover = None


def get_bid_ask_bounce_remover(
    min_bounce_threshold: float = 0.3,
    default_method: str = "mid_price",
) -> BidAskBounceRemover:
    """Get or create global BidAskBounceRemover instance."""
    global _bid_ask_bounce_remover
    if _bid_ask_bounce_remover is None:
        _bid_ask_bounce_remover = BidAskBounceRemover(
            min_bounce_threshold=min_bounce_threshold,
            default_method=default_method,
        )

    return _bid_ask_bounce_remover
