"""
Cross-Sectional Momentum Strategy Domain Service

Implements cross-sectional momentum (relative strength) where
assets are ranked based on past performance and top performers
are selected.

Reference: Rule 11-gray-vogel-quantitative-momentum.md
Paper: Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners
       and Selling Losers: Implications for Stock Market Efficiency"
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class MomentumSignal(str, Enum):
    """Momentum signal type."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class MomentumAsset:
    """Asset with momentum metrics."""

    symbol: str
    momentum_score: float  # Momentum score (return over lookback)
    rank: int  # Cross-sectional rank
    percentile: float  # Percentile rank (0-1)
    signal: MomentumSignal  # Generated signal


@dataclass
class MomentumPortfolio:
    """Momentum-based portfolio allocation."""

    long_positions: Dict[str, float]  # Symbol -> weight
    short_positions: Dict[str, float]  # Symbol -> weight (if allowed)
    cash_weight: float  # Weight in cash
    rebalance_date: pd.Timestamp  # When portfolio was constructed

    @property
    def net_exposure(self) -> float:
        """Get net market exposure."""
        long_weight = sum(self.long_positions.values())
        short_weight = sum(self.short_positions.values())
        return long_weight - short_weight

    @property
    def gross_exposure(self) -> float:
        """Get gross market exposure."""
        return sum(self.long_positions.values()) + sum(self.short_positions.values())

    def get_weights_dict(self) -> Dict[str, float]:
        """Get all positions as dictionary."""
        weights = self.long_positions.copy()
        for symbol, weight in self.short_positions.items():
            weights[symbol] = weights.get(symbol, 0.0) - weight
        return weights


class CrossSectionalMomentum:
    """
    Cross-sectional momentum strategy.

    Ranks assets based on past returns over a lookback period
    and goes long top performers, short bottom performers.

    This is a pure domain service that can be used with any data source.

    Reference: Jegadeesh & Titman (1993) - 3-12 month momentum
    """

    def __init__(
        self,
        lookback_months: int = 12,  # 12 months momentum (classic)
        top_percentile: float = 0.3,  # Top 30% long
        bottom_percentile: float = 0.3,  # Bottom 30% short
        long_only: bool = True,  # Long-only or long-short
        min_assets: int = 10,  # Minimum assets to trade
        max_assets: int = 100,  # Maximum assets to trade
        rebalance_frequency: str = "monthly",  # monthly, quarterly
    ):
        """
        Initialize cross-sectional momentum.

        Args:
            lookback_months: Lookback period for momentum calculation
            top_percentile: Top percentile to go long
            bottom_percentile: Bottom percentile to short
            long_only: Whether to implement long-only strategy
            min_assets: Minimum number of assets to include
            max_assets: Maximum number of assets to include
            rebalance_frequency: Rebalancing frequency
        """
        self._lookback_months = lookback_months
        self._top_percentile = top_percentile
        self._bottom_percentile = bottom_percentile
        self._long_only = long_only
        self._min_assets = min_assets
        self._max_assets = max_assets
        self._rebalance_frequency = rebalance_frequency

    def calculate_momentum_scores(
        self,
        returns: pd.DataFrame,  # symbols x dates
    ) -> Dict[str, MomentumAsset]:
        """
        Calculate momentum scores for all assets.

        Args:
            returns: DataFrame of returns (symbols in rows, dates in columns)

        Returns:
            Dictionary of symbol -> MomentumAsset
        """
        # Calculate cumulative returns over lookback period
        lookback_periods = self._lookback_months * 21  # Approx trading days per month

        # Ensure we have enough data
        if returns.shape[1] < lookback_periods:
            lookback_periods = returns.shape[1] - 1

        # Calculate momentum (cumulative return over lookback)
        momentum = (1 + returns.iloc[:, -lookback_periods:]).prod(axis=1) - 1

        # Rank assets by momentum
        ranks = momentum.rank(ascending=False)
        percentiles = ranks / len(ranks)

        # Determine signals
        assets = {}
        for symbol in returns.index:
            mom_score = float(momentum[symbol])
            rank = int(ranks[symbol])
            percentile = float(percentiles[symbol])

            if percentile >= (1 - self._top_percentile):
                signal = MomentumSignal.LONG
            elif not self._long_only and percentile <= self._bottom_percentile:
                signal = MomentumSignal.SHORT
            else:
                signal = MomentumSignal.NEUTRAL

            assets[symbol] = MomentumAsset(
                symbol=symbol,
                momentum_score=mom_score,
                rank=rank,
                percentile=percentile,
                signal=signal,
            )

        return assets

    def construct_portfolio(
        self,
        momentum_assets: Dict[str, MomentumAsset],
        current_prices: Dict[str, float],
        total_capital: float,
    ) -> MomentumPortfolio:
        """
        Construct momentum portfolio.

        Args:
            momentum_assets: Assets with momentum metrics
            current_prices: Current prices for each asset
            total_capital: Total capital to allocate

        Returns:
            MomentumPortfolio with optimal allocation
        """
        # Filter assets with signals
        long_assets = [
            (s, a) for s, a in momentum_assets.items() if a.signal == MomentumSignal.LONG
        ]
        short_assets = [
            (s, a) for s, a in momentum_assets.items() if a.signal == MomentumSignal.SHORT
        ]

        # Apply minimum/maximum asset constraints
        n_long = min(len(long_assets), self._max_assets)
        n_long = max(n_long, self._min_assets) if len(long_assets) >= self._min_assets else 0

        n_short = 0 if self._long_only else min(len(short_assets), self._max_assets)

        # Sort by rank (best first)
        long_assets.sort(key=lambda x: x[1].rank)
        short_assets.sort(key=lambda x: x[1].rank) if not self._long_only else []

        # Equal weight long positions
        long_weights = {}
        if n_long > 0:
            long_weight = 1.0 / n_long
            for symbol, _ in long_assets[:n_long]:
                long_weights[symbol] = long_weight

        # Equal weight short positions
        short_weights = {}
        if n_short > 0:
            short_weight = 1.0 / n_short
            for symbol, _ in short_assets[:n_short]:
                short_weights[symbol] = short_weight

        # Calculate cash weight
        gross_long = sum(long_weights.values()) if long_weights else 0
        gross_short = sum(short_weights.values()) if short_weights else 0
        cash_weight = max(0, 1.0 - gross_long - gross_short)

        return MomentumPortfolio(
            long_positions=long_weights,
            short_positions=short_weights,
            cash_weight=cash_weight,
            rebalance_date=pd.Timestamp.now(),
        )

    def should_rebalance(
        self,
        last_rebalance: pd.Timestamp,
        current_date: pd.Timestamp,
    ) -> bool:
        """
        Check if portfolio should be rebalanced.

        Args:
            last_rebalance: Last rebalance date
            current_date: Current date

        Returns:
            True if rebalancing is needed
        """
        if self._rebalance_frequency == "monthly":
            return (
                current_date.year > last_rebalance.year or current_date.month > last_rebalance.month
            )
        elif self._rebalance_frequency == "quarterly":
            return (
                current_date.year > last_rebalance.year
                or (current_date.month - 1) // 3 > (last_rebalance.month - 1) // 3
            )
        else:  # annual
            return current_date.year > last_rebalance.year


@dataclass
class MomentumMetrics:
    """Performance metrics for momentum strategy."""

    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    hit_rate: float  # Percentage of profitable trades
    average_hold_period: float  # In days

    def __str__(self) -> str:
        return (
            f"Return: {self.total_return:.2%}, "
            f"Sharpe: {self.sharpe_ratio:.2f}, "
            f"Max DD: {self.max_drawdown:.2%}, "
            f"Hit Rate: {self.hit_rate:.1%}"
        )
