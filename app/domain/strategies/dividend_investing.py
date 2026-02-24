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

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


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

        # Validate inputs and handle NaN/inf
        payout_ratio = (
            self.payout_ratio if np.isfinite(self.payout_ratio) and self.payout_ratio >= 0 else 1.0
        )
        fcf_payout = (
            self.free_cash_payout_ratio
            if np.isfinite(self.free_cash_payout_ratio) and self.free_cash_payout_ratio >= 0
            else 1.0
        )
        growth_years = (
            self.dividend_growth_years
            if np.isfinite(self.dividend_growth_years) and self.dividend_growth_years >= 0
            else 0
        )
        roe = self.return_on_equity if np.isfinite(self.return_on_equity) else 0.0
        debt_to_equity = (
            self.debt_to_equity
            if np.isfinite(self.debt_to_equity) and self.debt_to_equity >= 0
            else 2.0
        )

        # Payout ratio (ideal: 40-60%)
        if 0.4 <= payout_ratio <= 0.6:
            score += 0.3
        elif 0.3 <= payout_ratio <= 0.7:
            score += 0.2
        elif payout_ratio < 0.8:
            score += 0.1

        # FCF payout ratio (ideal: < 70%)
        if fcf_payout < 0.5:
            score += 0.3
        elif fcf_payout < 0.7:
            score += 0.2
        elif fcf_payout < 0.85:
            score += 0.1

        # Dividend growth consistency
        if growth_years >= 25:
            score += 0.2
        elif growth_years >= 10:
            score += 0.15
        elif growth_years >= 5:
            score += 0.1

        # Earnings quality (ROE)
        if roe > 0.15:
            score += 0.1
        elif roe > 0.10:
            score += 0.05

        # Financial health (D/E)
        if debt_to_equity < 0.5:
            score += 0.1
        elif debt_to_equity < 1.0:
            score += 0.05

        return min(1.0, max(0.0, score))

    @property
    def dividend_attractiveness_score(self) -> float:
        """
        Calculate dividend attractiveness score (0-1).

        Combines yield, growth, and sustainability.
        """
        score = 0.0

        # Validate inputs and handle NaN/inf
        dividend_yield = (
            self.dividend_yield
            if np.isfinite(self.dividend_yield) and self.dividend_yield >= 0
            else 0.0
        )
        growth_rate = self.dividend_growth_rate if np.isfinite(self.dividend_growth_rate) else 0.0

        # Dividend yield (2-6% ideal)
        if 0.03 <= dividend_yield <= 0.06:
            score += 0.4
        elif 0.02 <= dividend_yield <= 0.08:
            score += 0.3
        elif dividend_yield > 0.01:
            score += 0.2

        # Dividend growth
        if growth_rate > 0.10:
            score += 0.3
        elif growth_rate > 0.05:
            score += 0.2
        elif growth_rate > 0.02:
            score += 0.1

        # Sustainability
        score += self.dividend_sustainability_score * 0.3

        return min(1.0, max(0.0, score))


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
        min_yield: float | None = None,  # Minimum 2% yield
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
        # Get min_yield from config or use default
        if min_yield is None:
            try:
                config = get_config()
                min_yield = float(getattr(config.trading, 'dividend_min_yield', 0.02))
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Error getting dividend_min_yield config: {e}, using default 0.02")
                min_yield = 0.02

        self._min_yield = min_yield
        self._max_yield = max_yield
        self._min_growth = min_growth_rate
        self._max_payout = max_payout_ratio
        self._min_years = min_dividend_years
        self._min_sustainability = min_sustainability_score
        self._target_yield = target_portfolio_yield

        # Load trading thresholds from config
        trading_config = get_config()
        self._tt = trading_config.trading_thresholds

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
        # Validate metrics first
        if not all(
            [
                np.isfinite(metrics.dividend_yield) and metrics.dividend_yield >= 0,
                np.isfinite(metrics.payout_ratio) and metrics.payout_ratio >= 0,
                np.isfinite(metrics.dividend_years) and metrics.dividend_years >= 0,
                np.isfinite(metrics.dividend_sustainability_score)
                and 0 <= metrics.dividend_sustainability_score <= 1,
                np.isfinite(metrics.dividend_growth_rate),
            ]
        ):
            logger.warning(f"Invalid dividend metrics for {metrics.symbol}")
            return False

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
        min_weight: float | None = None,
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
        # Get min_weight from config or use default
        if min_weight is None:
            try:
                config = get_config()
                min_weight = float(getattr(config.trading, 'dividend_min_weight', 0.02))
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Error getting dividend_min_weight config: {e}, using default 0.02")
                min_weight = 0.02

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
        # Input validation
        if not np.isfinite(current_price) or current_price <= 0:
            logger.warning(f"Invalid current_price: {current_price}")
            return DividendSignal.AVOID

        if fair_value < 0 or not np.isfinite(fair_value):
            fair_value = 0.0

        # Check if passes screen
        if not self._passes_screen(metrics):
            return DividendSignal.AVOID

        # Calculate attractiveness score
        score = metrics.dividend_attractiveness_score

        # Validate score
        if not np.isfinite(score):
            score = 0.0

        # Valuation check
        if fair_value > 0:
            valuation_ratio = (
                current_price / fair_value if np.isfinite(current_price / fair_value) else 1.0
            )
        else:
            valuation_ratio = 1.0

        # Validate valuation ratio
        if not np.isfinite(valuation_ratio):
            valuation_ratio = 1.0

        # Validate payout ratio
        payout_ratio = metrics.payout_ratio if np.isfinite(metrics.payout_ratio) else 1.0

        # Generate signal
        if score > self._tt.dividend_score_excellent and valuation_ratio < self._tt.valuation_ratio_cheap:
            return DividendSignal.BUY
        elif score > self._tt.dividend_score_good and valuation_ratio < self._tt.valuation_ratio_fair:
            return DividendSignal.BUY
        elif score < 0.3 or payout_ratio > 0.9:
            # Risk of dividend cut (0.3 and 0.9 are business logic, not config)
            return DividendSignal.SELL
        elif valuation_ratio > 1.2:
            # Overvalued (1.2 is business logic, not config)
            return DividendSignal.SELL
        else:
            return DividendSignal.HOLD
