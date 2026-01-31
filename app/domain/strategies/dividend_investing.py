"""
Dividend Investing Strategy Domain Service

Implements dividend investing strategies based on:
- Dividend yield
- Dividend growth
- Payout ratio
- Dividend sustainability

Reference: Rule 41-arnott-campbell-dividends-earnings.md
Paper: Arnott, R.D., & Asness, C.S. (2003). "Surprise! Higher Dividends = Higher Earnings Growth"
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class DividendSignal(str, Enum):
    """Signal for dividend investing."""

    BUY = "buy"  # Attractive dividend profile
    HOLD = "hold"  # Maintain current position
    SELL = "sell"  # Dividend cut risk or overvalued
    AVOID = "avoid"  # Not suitable for dividend strategy


@dataclass
class DividendMetrics:
    """Comprehensive dividend metrics for a company."""

    symbol: str
    dividend_yield: float  # Annual dividend / price
    dividend_growth_rate: float  # Historical CAGR of dividends
    payout_ratio: float  # Dividends / earnings
    free_cash_payout_ratio: float  # Dividends / free cash flow
    dividend_years: int  # Consecutive years of dividend payments
    dividend_growth_years: int  # Consecutive years of dividend increases
    earnings_yield: float  # Earnings / price (inverse of P/E)
    return_on_equity: float  # ROE
    debt_to_equity: float  # D/E ratio

    @property
    def is_dividend_aristocrat(self) -> bool:
        """Check if stock is a dividend aristocrat (25+ years of increases)."""
        return self.dividend_growth_years >= 25

    @property
    def is_dividend_king(self) -> bool:
        """Check if stock is a dividend king (50+ years of increases)."""
        return self.dividend_growth_years >= 50

    @property
    def dividend_sustainability_score(self) -> float:
        """
        Calculate dividend sustainability score (0-1).

        Higher score indicates more sustainable dividend.
        """
        score = 0.0

        # Payout ratio (ideal: 40-60%)
        if 0.4 <= self.payout_ratio <= 0.6:
            score += 0.3
        elif 0.3 <= self.payout_ratio <= 0.7:
            score += 0.2
        elif self.payout_ratio < 0.8:
            score += 0.1

        # FCF payout ratio (ideal: < 70%)
        if self.free_cash_payout_ratio < 0.5:
            score += 0.3
        elif self.free_cash_payout_ratio < 0.7:
            score += 0.2
        elif self.free_cash_payout_ratio < 0.85:
            score += 0.1

        # Dividend growth consistency
        if self.dividend_growth_years >= 25:
            score += 0.2
        elif self.dividend_growth_years >= 10:
            score += 0.15
        elif self.dividend_growth_years >= 5:
            score += 0.1

        # Earnings quality (ROE)
        if self.return_on_equity > 0.15:
            score += 0.1
        elif self.return_on_equity > 0.10:
            score += 0.05

        # Financial health (D/E)
        if self.debt_to_equity < 0.5:
            score += 0.1
        elif self.debt_to_equity < 1.0:
            score += 0.05

        return min(1.0, score)

    @property
    def dividend_attractiveness_score(self) -> float:
        """
        Calculate dividend attractiveness score (0-1).

        Combines yield, growth, and sustainability.
        """
        score = 0.0

        # Dividend yield (2-6% ideal)
        if 0.03 <= self.dividend_yield <= 0.06:
            score += 0.4
        elif 0.02 <= self.dividend_yield <= 0.08:
            score += 0.3
        elif self.dividend_yield > 0.01:
            score += 0.2

        # Dividend growth
        if self.dividend_growth_rate > 0.10:
            score += 0.3
        elif self.dividend_growth_rate > 0.05:
            score += 0.2
        elif self.dividend_growth_rate > 0.02:
            score += 0.1

        # Sustainability
        score += self.dividend_sustainability_score * 0.3

        return min(1.0, score)


@dataclass
class DividendPortfolio:
    """Portfolio constructed using dividend strategy."""

    positions: Dict[str, float]  # Symbol -> weight
    portfolio_yield: float  # Weighted average dividend yield
    portfolio_growth_rate: float  # Weighted average dividend growth
    portfolio_payout_ratio: float  # Weighted average payout ratio
    yield_on_cost: float = 0.0  # Expected yield on original cost
    expected_annual_income: float = 0.0  # Expected annual dividend income

    @property
    def current_yield(self) -> float:
        """Get current portfolio yield."""
        return self.portfolio_yield

    def calculate_income(self, capital: float) -> float:
        """Calculate expected annual income from capital."""
        return capital * self.portfolio_yield


class DividendInvesting:
    """
    Dividend investing strategy.

    Selects stocks based on dividend yield, growth, and sustainability.
    Focuses on high-quality dividend payers with sustainable payouts.

    This is a pure domain service that can be used with any data source.

    Reference: Arnott, R.D., & Asness, C.S. (2003)
    """

    def __init__(
        self,
        min_yield: float = 0.02,  # Minimum 2% yield
        max_yield: float = 0.10,  # Maximum 10% yield (avoid yield traps)
        min_growth_rate: float = 0.0,  # Minimum dividend growth
        max_payout_ratio: float = 0.8,  # Maximum payout ratio
        min_dividend_years: int = 5,  # Minimum years of payments
        min_sustainability_score: float = 0.5,  # Minimum sustainability (0-1)
        target_portfolio_yield: float = 0.04,  # Target 4% portfolio yield
    ):
        """
        Initialize dividend investing strategy.

        Args:
            min_yield: Minimum dividend yield
            max_yield: Maximum dividend yield (avoid yield traps)
            min_growth_rate: Minimum dividend growth rate
            max_payout_ratio: Maximum payout ratio
            min_dividend_years: Minimum years of dividend payments
            min_sustainability_score: Minimum sustainability score
            target_portfolio_yield: Target portfolio yield
        """
        self._min_yield = min_yield
        self._max_yield = max_yield
        self._min_growth = min_growth_rate
        self._max_payout = max_payout_ratio
        self._min_years = min_dividend_years
        self._min_sustainability = min_sustainability_score
        self._target_yield = target_portfolio_yield

    def screen_dividend_stocks(
        self,
        dividend_metrics: Dict[str, DividendMetrics],
    ) -> List[str]:
        """
        Screen dividend stocks based on criteria.

        Args:
            dividend_metrics: Dictionary of symbol -> DividendMetrics

        Returns:
            List of symbols that pass screening
        """
        qualified = []

        for symbol, metrics in dividend_metrics.items():
            if self._passes_screen(metrics):
                qualified.append(symbol)

        return qualified

    def _passes_screen(self, metrics: DividendMetrics) -> bool:
        """Check if stock passes dividend screen."""
        # Yield requirements
        if metrics.dividend_yield < self._min_yield or metrics.dividend_yield > self._max_yield:
            return False

        # Payout ratio
        if metrics.payout_ratio > self._max_payout:
            return False

        # Dividend history
        if metrics.dividend_years < self._min_years:
            return False

        # Sustainability
        if metrics.dividend_sustainability_score < self._min_sustainability:
            return False

        # Growth rate (if specified)
        if self._min_growth > 0 and metrics.dividend_growth_rate < self._min_growth:
            return False

        return True

    def rank_dividend_stocks(
        self,
        dividend_metrics: Dict[str, DividendMetrics],
    ) -> List[Tuple[str, float]]:
        """
        Rank dividend stocks by attractiveness.

        Args:
            dividend_metrics: Dictionary of symbol -> DividendMetrics

        Returns:
            List of (symbol, score) tuples sorted by score (highest first)
        """
        scores = []

        for symbol, metrics in dividend_metrics.items():
            if not self._passes_screen(metrics):
                continue

            score = self._calculate_dividend_score(metrics)
            scores.append((symbol, score))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores

    def _calculate_dividend_score(self, metrics: DividendMetrics) -> float:
        """
        Calculate composite dividend score.

        Weights:
        - Attractiveness: 50%
        - Sustainability: 30%
        - Growth consistency: 20%
        """
        attractiveness = metrics.dividend_attractiveness_score
        sustainability = metrics.dividend_sustainability_score

        # Growth consistency (based on years of growth)
        if metrics.dividend_growth_years >= 25:
            growth_score = 1.0
        elif metrics.dividend_growth_years >= 10:
            growth_score = 0.75
        elif metrics.dividend_growth_years >= 5:
            growth_score = 0.5
        else:
            growth_score = 0.25

        # Weighted score
        score = 0.5 * attractiveness + 0.3 * sustainability + 0.2 * growth_score

        return score

    def construct_portfolio(
        self,
        dividend_metrics: Dict[str, DividendMetrics],
        capital: float,
        max_positions: int = 30,
        min_weight: float = 0.02,
        max_weight: float = 0.05,
    ) -> DividendPortfolio:
        """
        Construct dividend portfolio.

        Args:
            dividend_metrics: Dictionary of symbol -> DividendMetrics
            capital: Total capital to invest
            max_positions: Maximum number of positions
            min_weight: Minimum weight per position
            max_weight: Maximum weight per position

        Returns:
            DividendPortfolio with optimal allocation
        """
        # Rank stocks
        ranked = self.rank_dividend_stocks(dividend_metrics)

        # Select top stocks
        n_stocks = min(len(ranked), max_positions)
        selected = ranked[:n_stocks]

        if not selected:
            return DividendPortfolio(
                positions={},
                portfolio_yield=0.0,
                portfolio_growth_rate=0.0,
                portfolio_payout_ratio=0.0,
            )

        # Calculate weights (yield-weighted with caps)
        weights = {}
        total_yield_weight = 0.0

        # First pass: yield-weighted
        for symbol, score in selected:
            metrics = dividend_metrics[symbol]
            # Use yield as base weight, adjusted by score
            base_weight = metrics.dividend_yield * score
            weights[symbol] = base_weight
            total_yield_weight += base_weight

        # Normalize to 100%
        if total_yield_weight > 0:
            weights = {s: w / total_yield_weight for s, w in weights.items()}

        # Apply weight constraints
        weights = self._apply_weight_constraints(weights, min_weight, max_weight)

        # Renormalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {s: w / total_weight for s, w in weights.items()}

        # Calculate portfolio metrics
        portfolio_yield = sum(dividend_metrics[s].dividend_yield * w for s, w in weights.items())
        portfolio_growth = sum(
            dividend_metrics[s].dividend_growth_rate * w for s, w in weights.items()
        )
        portfolio_payout = sum(dividend_metrics[s].payout_ratio * w for s, w in weights.items())

        return DividendPortfolio(
            positions=weights,
            portfolio_yield=portfolio_yield,
            portfolio_growth_rate=portfolio_growth,
            portfolio_payout_ratio=portfolio_payout,
            expected_annual_income=capital * portfolio_yield,
        )

    def _apply_weight_constraints(
        self,
        weights: Dict[str, float],
        min_weight: float,
        max_weight: float,
    ) -> Dict[str, float]:
        """Apply min/max weight constraints."""
        # Cap at max_weight
        weights = {s: min(w, max_weight) for s, w in weights.items()}

        # Remove stocks below min_weight
        weights = {s: w for s, w in weights.items() if w >= min_weight}

        return weights

    def rebalance_portfolio(
        self,
        current_portfolio: DividendPortfolio,
        dividend_metrics: Dict[str, DividendMetrics],
        capital: float,
        rebalance_threshold: float = 0.05,  # 5% deviation
    ) -> DividendPortfolio:
        """
        Rebalance dividend portfolio.

        Args:
            current_portfolio: Current portfolio
            dividend_metrics: Updated dividend metrics
            capital: Current capital
            rebalance_threshold: Threshold for rebalancing

        Returns:
            New DividendPortfolio if rebalancing needed, otherwise current
        """
        # Calculate current weights
        current_weights = current_portfolio.positions

        # Calculate optimal weights
        optimal = self.construct_portfolio(
            dividend_metrics,
            capital,
        )

        # Check if rebalancing needed
        needs_rebalance = False

        for symbol in set(list(current_weights.keys()) + list(optimal.positions.keys())):
            current = current_weights.get(symbol, 0.0)
            target = optimal.positions.get(symbol, 0.0)

            if abs(current - target) > rebalance_threshold:
                needs_rebalance = True
                break

        if needs_rebalance:
            return optimal
        else:
            return current_portfolio

    def generate_signal(
        self,
        metrics: DividendMetrics,
        current_price: float,
        fair_value: float = 0.0,
    ) -> DividendSignal:
        """
        Generate trading signal for dividend stock.

        Args:
            metrics: Dividend metrics
            current_price: Current price
            fair_value: Estimated fair value (optional)

        Returns:
            DividendSignal with action
        """
        # Check if passes screen
        if not self._passes_screen(metrics):
            return DividendSignal.AVOID

        # Calculate attractiveness score
        score = metrics.dividend_attractiveness_score

        # Valuation check
        if fair_value > 0:
            valuation_ratio = current_price / fair_value
        else:
            valuation_ratio = 1.0

        # Generate signal
        if score > 0.7 and valuation_ratio < 0.9:
            return DividendSignal.BUY
        elif score > 0.5 and valuation_ratio < 1.0:
            return DividendSignal.BUY
        elif score < 0.3 or metrics.payout_ratio > 0.9:
            # Risk of dividend cut
            return DividendSignal.SELL
        elif valuation_ratio > 1.2:
            # Overvalued
            return DividendSignal.SELL
        else:
            return DividendSignal.HOLD
