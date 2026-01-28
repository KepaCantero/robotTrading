"""
Low Volatility Anomaly Strategy Domain Service

Implements the low volatility anomaly strategy which exploits
the empirical finding that low-volatility stocks tend to deliver
higher risk-adjusted returns than high-volatility stocks.

Reference: Rule 11-gray-vogel-quantitative-momentum.md (low vol concepts)
Paper: Baker, M., et al. (2011). "Betas vs. Fama-French Factors"
Paper: Blitz, D., & van Vliet, P. (2007). "The Volatility Effect"
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class VolatilityCategory(str, Enum):
    """Volatility category for stocks."""

    LOW_VOLATILITY = "low_volatility"  # Bottom 30% by volatility
    MEDIUM_VOLATILITY = "medium_volatility"  # Middle 40%
    HIGH_VOLATILITY = "high_volatility"  # Top 30%


@dataclass
class VolatilityMetrics:
    """Volatility metrics for a stock."""

    symbol: str
    daily_volatility: float  # Standard deviation of daily returns
    annualized_volatility: float  # Annualized volatility
    beta: float  # Market beta
    idiosyncratic_volatility: float  # Stock-specific volatility
    downside_deviation: float  # Downside risk only
    max_drawdown: float  # Maximum historical drawdown
    sharpe_ratio: float  # Risk-adjusted return
    sortino_ratio: float  # Downside-adjusted return
    percentile_rank: float  # Volatility rank (0-1)

    @property
    def volatility_category(self) -> VolatilityCategory:
        """Get volatility category."""
        if self.percentile_rank <= 0.3:
            return VolatilityCategory.LOW_VOLATILITY
        elif self.percentile_rank >= 0.7:
            return VolatilityCategory.HIGH_VOLATILITY
        else:
            return VolatilityCategory.MEDIUM_VOLATILITY

    @property
    def is_low_volatility(self) -> bool:
        """Check if stock is low volatility."""
        return self.percentile_rank <= 0.3

    @property
    def risk_adjusted_score(self) -> float:
        """
        Calculate risk-adjusted score.

        Higher score = better risk-adjusted performance.
        """
        # Combine Sharpe ratio (70%) with inverse volatility (30%)
        sharpe_component = np.tanh(self.sharpe_ratio)  # Normalize to -1 to 1
        inv_vol_component = 1.0 / (1.0 + self.annualized_volatility)

        score = 0.7 * (sharpe_component + 1) / 2 + 0.3 * inv_vol_component

        return max(0.0, min(1.0, score))


@dataclass
class LowVolatilityPortfolio:
    """Portfolio constructed using low volatility strategy."""

    positions: Dict[str, float]  # Symbol -> weight
    portfolio_volatility: float  # Weighted average volatility
    portfolio_beta: float  # Weighted average beta
    portfolio_sharpe: float  # Expected portfolio Sharpe ratio
    volatility_exposure: float  # Exposure to volatility factor

    @property
    def is_low_vol_portfolio(self) -> bool:
        """Check if portfolio is low volatility."""
        return self.portfolio_volatility < 0.15  # Less than 15% annual vol

    def get_volatility_breakdown(self) -> Dict[str, float]:
        """Get breakdown of volatility by category."""
        # This would require additional metadata
        # Simplified version returns portfolio-level metrics
        return {
            "total_volatility": self.portfolio_volatility,
            "market_beta": self.portfolio_beta,
            "sharpe_ratio": self.portfolio_sharpe,
        }


class LowVolatilityAnomaly:
    """
    Low volatility anomaly strategy.

    Exploits the empirical finding that low-volatility stocks
    tend to deliver higher risk-adjusted returns.

    Strategy:
    1. Rank stocks by volatility (lowest first)
    2. Select low-volatility stocks
    3. Weight by inverse volatility (risk parity)

    This is a pure domain service that can be used with any data source.

    Reference: Baker, M., et al. (2011), Blitz, D., & van Vliet, P. (2007)
    """

    def __init__(
        self,
        low_vol_threshold: float = 0.3,  # Bottom 30% by volatility
        max_beta: float = 0.8,  # Maximum acceptable beta
        max_volatility: float = 0.25,  # Maximum annualized volatility
        min_sharpe: float = 0.5,  # Minimum Sharpe ratio
        rebalance_frequency: str = "monthly",  # Rebalancing frequency
        weighting_method: str = "inverse_variance",  # inverse_variance, equal_weight, min_variance
    ):
        """
        Initialize low volatility strategy.

        Args:
            low_vol_threshold: Percentile threshold for low vol (0-1)
            max_beta: Maximum acceptable beta
            max_volatility: Maximum acceptable volatility
            min_sharpe: Minimum Sharpe ratio
            rebalance_frequency: How often to rebalance
            weighting_method: How to weight positions
        """
        self._vol_threshold = low_vol_threshold
        self._max_beta = max_beta
        self._max_vol = max_volatility
        self._min_sharpe = min_sharpe
        self._rebalance_freq = rebalance_frequency
        self._weighting = weighting_method

    def calculate_volatility_metrics(
        self,
        returns: np.ndarray,  # Daily returns
        market_returns: np.ndarray,  # Market returns (for beta)
        risk_free_rate: float = 0.02,
    ) -> VolatilityMetrics:
        """
        Calculate comprehensive volatility metrics.

        Args:
            returns: Asset return history
            market_returns: Market return history
            risk_free_rate: Annual risk-free rate

        Returns:
            VolatilityMetrics with calculated values
        """
        # Daily volatility
        daily_vol = float(np.std(returns))

        # Annualized volatility (assuming 252 trading days)
        annual_vol = daily_vol * np.sqrt(252)

        # Beta calculation
        if len(returns) == len(market_returns) and len(returns) > 1:
            covariance = np.cov(returns, market_returns)[0, 1]
            market_variance = np.var(market_returns)
            beta = float(covariance / market_variance) if market_variance > 0 else 1.0
        else:
            beta = 1.0

        # Idiosyncratic volatility
        idiosyncratic_vol = float(np.std(returns - beta * market_returns)) if len(returns) > 0 else annual_vol

        # Downside deviation (only negative returns)
        negative_returns = returns[returns < 0]
        downside_dev = float(np.std(negative_returns)) if len(negative_returns) > 0 else 0.0

        # Max drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = float(np.min(drawdown)) if len(drawdown) > 0 else 0.0

        # Sharpe ratio
        excess_returns = np.mean(returns) * 252 - risk_free_rate
        sharpe = float(excess_returns / annual_vol) if annual_vol > 0 else 0.0

        # Sortino ratio
        sortino = float(excess_returns / (downside_dev * np.sqrt(252))) if downside_dev > 0 else 0.0

        return VolatilityMetrics(
            symbol="",  # Will be set by caller
            daily_volatility=daily_vol,
            annualized_volatility=annual_vol,
            beta=beta,
            idiosyncratic_volatility=idiosyncratic_vol,
            downside_deviation=downside_dev,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            percentile_rank=0.0,  # Will be calculated across universe
        )

    def screen_low_volatility_stocks(
        self,
        volatility_metrics: Dict[str, VolatilityMetrics],
    ) -> List[str]:
        """
        Screen low volatility stocks based on criteria.

        Args:
            volatility_metrics: Dictionary of symbol -> VolatilityMetrics

        Returns:
            List of symbols that pass screening
        """
        # Calculate percentile ranks
        volatilities = [m.annualized_volatility for m in volatility_metrics.values()]
        vol_array = np.array(volatilities)

        for metrics in volatility_metrics.values():
            rank = np.sum(vol_array <= metrics.annualized_volatility) / len(vol_array)
            metrics.percentile_rank = float(rank)

        # Screen stocks
        qualified = []

        for symbol, metrics in volatility_metrics.items():
            if self._passes_screen(metrics):
                qualified.append(symbol)

        return qualified

    def _passes_screen(self, metrics: VolatilityMetrics) -> bool:
        """Check if stock passes low volatility screen."""
        # Volatility threshold
        if metrics.percentile_rank > self._vol_threshold:
            return False

        # Absolute volatility cap
        if metrics.annualized_volatility > self._max_vol:
            return False

        # Beta cap
        if metrics.beta > self._max_beta:
            return False

        # Minimum Sharpe ratio
        if metrics.sharpe_ratio < self._min_sharpe:
            return False

        return True

    def rank_low_volatility_stocks(
        self,
        volatility_metrics: Dict[str, VolatilityMetrics],
    ) -> List[Tuple[str, float]]:
        """
        Rank low volatility stocks by risk-adjusted score.

        Args:
            volatility_metrics: Dictionary of symbol -> VolatilityMetrics

        Returns:
            List of (symbol, score) tuples sorted by score (highest first)
        """
        scores = []

        for symbol, metrics in volatility_metrics.items():
            if not self._passes_screen(metrics):
                continue

            score = metrics.risk_adjusted_score
            scores.append((symbol, score))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores

    def construct_portfolio(
        self,
        volatility_metrics: Dict[str, VolatilityMetrics],
        capital: float,
        max_positions: int = 30,
        min_weight: float = 0.01,
        max_weight: float = 0.05,
    ) -> LowVolatilityPortfolio:
        """
        Construct low volatility portfolio.

        Args:
            volatility_metrics: Dictionary of symbol -> VolatilityMetrics
            capital: Total capital to invest
            max_positions: Maximum number of positions
            min_weight: Minimum weight per position
            max_weight: Maximum weight per position

        Returns:
            LowVolatilityPortfolio with optimal allocation
        """
        # Rank and select stocks
        ranked = self.rank_low_volatility_stocks(volatility_metrics)

        n_stocks = min(len(ranked), max_positions)
        selected = ranked[:n_stocks]

        if not selected:
            return LowVolatilityPortfolio(
                positions={},
                portfolio_volatility=0.0,
                portfolio_beta=0.0,
                portfolio_sharpe=0.0,
                volatility_exposure=0.0,
            )

        # Calculate weights based on method
        if self._weighting == "inverse_variance":
            weights = self._inverse_variance_weights(
                selected, volatility_metrics
            )
        elif self._weighting == "min_variance":
            weights = self._minimum_variance_weights(
                selected, volatility_metrics
            )
        else:  # equal_weight
            weights = {s: 1.0 / n_stocks for s, _ in selected}

        # Apply weight constraints
        weights = self._apply_weight_constraints(weights, min_weight, max_weight)

        # Renormalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {s: w / total_weight for s, w in weights.items()}

        # Calculate portfolio metrics
        portfolio_vol = sum(
            volatility_metrics[s].annualized_volatility * w
            for s, w in weights.items()
        )
        portfolio_beta = sum(
            volatility_metrics[s].beta * w
            for s, w in weights.items()
        )
        portfolio_sharpe = sum(
            volatility_metrics[s].sharpe_ratio * w
            for s, w in weights.items()
        )

        return LowVolatilityPortfolio(
            positions=weights,
            portfolio_volatility=portfolio_vol,
            portfolio_beta=portfolio_beta,
            portfolio_sharpe=portfolio_sharpe,
            volatility_exposure=-0.5,  # Negative exposure to vol factor
        )

    def _inverse_variance_weights(
        self,
        selected: List[Tuple[str, float]],
        volatility_metrics: Dict[str, VolatilityMetrics],
    ) -> Dict[str, float]:
        """Calculate inverse variance weights."""
        weights = {}

        for symbol, _ in selected:
            metrics = volatility_metrics[symbol]
            # Weight = 1 / variance
            variance = metrics.annualized_volatility ** 2
            weights[symbol] = 1.0 / variance if variance > 0 else 1.0

        return weights

    def _minimum_variance_weights(
        self,
        selected: List[Tuple[str, float]],
        volatility_metrics: Dict[str, VolatilityMetrics],
    ) -> Dict[str, float]:
        """
        Calculate minimum variance weights.

        Simplified version using diagonal covariance assumption.
        """
        weights = {}

        # Inverse volatility weighting (approximation of min variance)
        for symbol, _ in selected:
            metrics = volatility_metrics[symbol]
            inv_vol = 1.0 / metrics.annualized_volatility if metrics.annualized_volatility > 0 else 1.0
            weights[symbol] = inv_vol

        return weights

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

    def calculate_volatility_premium(
        self,
        volatility_metrics: Dict[str, VolatilityMetrics],
        returns: Dict[str, float],
    ) -> Tuple[float, float, float]:
        """
        Calculate low volatility premium.

        Compares returns of low-vol vs high-vol stocks.

        Args:
            volatility_metrics: Dictionary of symbol -> VolatilityMetrics
            returns: Dictionary of symbol -> return

        Returns:
            Tuple of (low_vol_return, medium_vol_return, high_vol_return)
        """
        low_vol_returns = []
        medium_vol_returns = []
        high_vol_returns = []

        for symbol, metrics in volatility_metrics.items():
            if symbol not in returns:
                continue

            if metrics.is_low_volatility:
                low_vol_returns.append(returns[symbol])
            elif metrics.volatility_category == VolatilityCategory.HIGH_VOLATILITY:
                high_vol_returns.append(returns[symbol])
            else:
                medium_vol_returns.append(returns[symbol])

        low_return = np.mean(low_vol_returns) if low_vol_returns else 0.0
        medium_return = np.mean(medium_vol_returns) if medium_vol_returns else 0.0
        high_return = np.mean(high_vol_returns) if high_vol_returns else 0.0

        return float(low_return), float(medium_return), float(high_return)
