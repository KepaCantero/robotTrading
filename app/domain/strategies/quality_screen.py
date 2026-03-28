"""
Quality Investing Strategy Domain Service

Implements quality-based stock selection based on fundamental metrics
that identify high-quality, profitable companies.

Reference: Berkin & Swedroe concepts on quality investing
Paper: Novy-Marx, R. (2013). "The Other Side of Value: Gross Profitability Premium"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class QualitySignal(str, Enum):
    """Signal for quality investing."""

    HIGH_QUALITY = "high_quality"  # Top quality stocks
    GOOD_QUALITY = "good_quality"  # Above average quality
    AVERAGE_QUALITY = "average_quality"  # Average quality
    LOW_QUALITY = "low_quality"  # Below average quality
    POOR_QUALITY = "poor_quality"  # Poor quality (avoid)


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for a company."""

    symbol: str
    # Profitability metrics
    gross_profit_margin: float  # Gross profit / revenue
    operating_profit_margin: float  # Operating income / revenue
    net_profit_margin: float  # Net income / revenue
    return_on_equity: float  # ROE
    return_on_assets: float  # ROA
    return_on_invested_capital: float  # ROIC
    free_cash_flow_margin: float  # FCF / revenue

    # Financial health
    current_ratio: float  # Current assets / current liabilities
    quick_ratio: float  # (Current assets - inventory) / current liabilities
    debt_to_equity: float  # D/E ratio
    interest_coverage: float  # EBIT / interest expense
    altman_z_score: float  # Bankruptcy risk score

    # Earnings quality
    accruals: float  # Net income - cash flow from operations
    earnings_smoothness: float  # Std dev of earnings (lower is better)
    earnings_consistency: float  # Years of positive earnings

    # Growth metrics
    revenue_growth: float  # Revenue CAGR
    earnings_growth: float  # Earnings CAGR
    fcf_growth: float  # Free cash flow CAGR

    # Valuation (for quality-adjusted value)
    price_to_book: float  # P/B ratio
    price_to_earnings: float  # P/E ratio
    enterprise_value_to_ebitda: float  # EV/EBITDA

    @property
    def profitability_score(self) -> float:
        """Calculate profitability score (0-1)."""
        score = 0.0

        # Gross margin (>40% excellent)
        if self.gross_profit_margin > 0.4:
            score += 0.2
        elif self.gross_profit_margin > 0.3:
            score += 0.15
        elif self.gross_profit_margin > 0.2:
            score += 0.1

        # Operating margin (>15% excellent)
        if self.operating_profit_margin > 0.15:
            score += 0.2
        elif self.operating_profit_margin > 0.1:
            score += 0.15
        elif self.operating_profit_margin > 0.05:
            score += 0.1

        # ROE (>15% excellent)
        if self.return_on_equity > 0.15:
            score += 0.2
        elif self.return_on_equity > 0.1:
            score += 0.15
        elif self.return_on_equity > 0.05:
            score += 0.1

        # ROIC (>12% excellent)
        if self.return_on_invested_capital > 0.12:
            score += 0.2
        elif self.return_on_invested_capital > 0.08:
            score += 0.15
        elif self.return_on_invested_capital > 0.04:
            score += 0.1

        # FCF margin (>10% excellent)
        if self.free_cash_flow_margin > 0.1:
            score += 0.2
        elif self.free_cash_flow_margin > 0.05:
            score += 0.15
        elif self.free_cash_flow_margin > 0.0:
            score += 0.1

        return min(1.0, score)

    @property
    def financial_health_score(self) -> float:
        """Calculate financial health score (0-1)."""
        score = 0.0

        # Current ratio (>2 excellent)
        if self.current_ratio > 2.0:
            score += 0.2
        elif self.current_ratio > 1.5:
            score += 0.15
        elif self.current_ratio > 1.0:
            score += 0.1

        # Quick ratio (>1 excellent)
        if self.quick_ratio > 1.0:
            score += 0.2
        elif self.quick_ratio > 0.8:
            score += 0.15
        elif self.quick_ratio > 0.5:
            score += 0.1

        # Debt-to-equity (<0.5 excellent)
        if self.debt_to_equity < 0.3:
            score += 0.3
        elif self.debt_to_equity < 0.5:
            score += 0.2
        elif self.debt_to_equity < 1.0:
            score += 0.1

        # Interest coverage (>5 excellent)
        if self.interest_coverage > 10:
            score += 0.3
        elif self.interest_coverage > 5:
            score += 0.2
        elif self.interest_coverage > 2:
            score += 0.1

        return min(1.0, score)

    @property
    def overall_quality_score(self) -> float:
        """
        Calculate overall quality score (0-1).

        Weights:
        - Profitability: 50%
        - Financial health: 30%
        - Earnings quality: 20%
        """
        profit_score = self.profitability_score
        health_score = self.financial_health_score

        # Earnings quality (lower accruals and smoother earnings better)
        earnings_score = 0.0
        if abs(self.accruals) < 0.05:
            earnings_score += 0.5
        elif abs(self.accruals) < 0.1:
            earnings_score += 0.3
        elif abs(self.accruals) < 0.15:
            earnings_score += 0.1

        if self.earnings_consistency >= 5:
            earnings_score += 0.5
        elif self.earnings_consistency >= 3:
            earnings_score += 0.3
        elif self.earnings_consistency >= 1:
            earnings_score += 0.1

        # Weighted score
        overall = 0.5 * profit_score + 0.3 * health_score + 0.2 * earnings_score

        return min(1.0, overall)

    @property
    def quality_category(self) -> QualitySignal:
        """Get quality category."""
        score = self.overall_quality_score

        if score >= 0.8:
            return QualitySignal.HIGH_QUALITY
        elif score >= 0.6:
            return QualitySignal.GOOD_QUALITY
        elif score >= 0.4:
            return QualitySignal.AVERAGE_QUALITY
        elif score >= 0.2:
            return QualitySignal.LOW_QUALITY
        else:
            return QualitySignal.POOR_QUALITY

    def is_quality_stock(self, threshold: float = 0.6) -> bool:
        """Check if stock meets quality threshold."""
        return self.overall_quality_score >= threshold


@dataclass
class QualityPortfolio:
    """Portfolio constructed using quality strategy."""

    positions: Dict[str, float]  # Symbol -> weight
    portfolio_quality_score: float  # Weighted average quality score
    portfolio_profitability: float  # Weighted average profitability
    portfolio_financial_health: float  # Weighted average financial health

    @property
    def quality_grade(self) -> QualitySignal:
        """Get portfolio quality grade."""
        score = self.portfolio_quality_score

        if score >= 0.8:
            return QualitySignal.HIGH_QUALITY
        elif score >= 0.6:
            return QualitySignal.GOOD_QUALITY
        elif score >= 0.4:
            return QualitySignal.AVERAGE_QUALITY
        else:
            return QualitySignal.LOW_QUALITY


class QualityInvesting:
    """
    Quality investing strategy.

    Selects stocks based on quality metrics including profitability,
    financial health, and earnings quality.

    Focuses on high-quality companies with sustainable competitive advantages.

    This is a pure domain service that can be used with any data source.

    Reference: Novy-Marx, R. (2013), Berkin & Swedroe quality concepts
    """

    def __init__(
        self,
        min_quality_score: float = 0.6,  # Minimum quality score
        min_roe: float = 0.10,  # Minimum ROE
        min_profit_margin: float = 0.05,  # Minimum profit margin
        max_debt_to_equity: float = 1.0,  # Maximum D/E ratio
        min_interest_coverage: float = 2.0,  # Minimum interest coverage
        quality_weight: float = 0.7,  # Weight for quality in ranking
        value_weight: float = 0.3,  # Weight for value in ranking
    ):
        """
        Initialize quality investing strategy.

        Args:
            min_quality_score: Minimum overall quality score
            min_roe: Minimum return on equity
            min_profit_margin: Minimum profit margin
            max_debt_to_equity: Maximum debt-to-equity ratio
            min_interest_coverage: Minimum interest coverage ratio
            quality_weight: Weight for quality in composite score
            value_weight: Weight for value (cheapness) in composite score
        """
        self._min_quality = min_quality_score
        self._min_roe = min_roe
        self._min_margin = min_profit_margin
        self._max_de = max_debt_to_equity
        self._min_coverage = min_interest_coverage
        self._quality_weight = quality_weight
        self._value_weight = value_weight
        logger.debug(
            "QualityInvesting strategy initialized",
            extra={
                "min_quality_score": min_quality_score,
                "min_roe": min_roe,
                "min_profit_margin": min_profit_margin,
                "max_debt_to_equity": max_debt_to_equity,
                "min_interest_coverage": min_interest_coverage,
                "quality_weight": quality_weight,
                "value_weight": value_weight,
            },
        )

    def screen_quality_stocks(
        self,
        quality_metrics: Dict[str, QualityMetrics],
    ) -> List[str]:
        """
        Screen quality stocks based on criteria.

        Args:
            quality_metrics: Dictionary of symbol -> QualityMetrics

        Returns:
            List of symbols that pass screening
        """
        logger.debug(
            "Starting quality stock screening", extra={"total_stocks": len(quality_metrics)}
        )
        qualified = []

        for symbol, metrics in quality_metrics.items():
            if self._passes_screen(metrics):
                qualified.append(symbol)

        logger.info(
            "Quality stock screening completed",
            extra={
                "total_stocks": len(quality_metrics),
                "qualified_stocks": len(qualified),
                "pass_rate": len(qualified) / len(quality_metrics) if quality_metrics else 0,
            },
        )
        return qualified

    def _passes_screen(self, metrics: QualityMetrics) -> bool:
        """Check if stock passes quality screen."""
        # Quality score
        if metrics.overall_quality_score < self._min_quality:
            return False

        # Profitability
        if metrics.return_on_equity < self._min_roe:
            return False

        if metrics.net_profit_margin < self._min_margin:
            return False

        # Financial health
        if metrics.debt_to_equity > self._max_de:
            return False

        if metrics.interest_coverage < self._min_coverage:
            return False

        # Bankruptcy risk
        if metrics.altman_z_score < 1.8:  # Distress zone
            return False

        return True

    def rank_quality_stocks(
        self,
        quality_metrics: Dict[str, QualityMetrics],
    ) -> List[Tuple[str, float]]:
        """
        Rank quality stocks by quality-value composite.

        Args:
            quality_metrics: Dictionary of symbol -> QualityMetrics

        Returns:
            List of (symbol, score) tuples sorted by score (highest first)
        """
        logger.debug("Starting quality stock ranking", extra={"total_stocks": len(quality_metrics)})
        scores = []

        for symbol, metrics in quality_metrics.items():
            if not self._passes_screen(metrics):
                continue

            score = self._calculate_quality_value_score(metrics)
            scores.append((symbol, score))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "Quality stock ranking completed",
            extra={
                "total_stocks": len(quality_metrics),
                "ranked_stocks": len(scores),
                "top_score": scores[0][1] if scores else None,
                "bottom_score": scores[-1][1] if scores else None,
            },
        )

        return scores

    def _calculate_quality_value_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate quality-value composite score.

        Combines quality with cheapness (value factor).
        """
        # Quality score (0-1)
        quality = metrics.overall_quality_score

        # Value score (0-1) - lower is better, so invert
        # Using multiple value metrics
        pb_score = 1.0 / (1.0 + metrics.price_to_book)  # Cheaper = higher score
        pe_score = 1.0 / (1.0 + metrics.price_to_earnings) if metrics.price_to_earnings > 0 else 0
        ev_score = (
            1.0 / (1.0 + metrics.enterprise_value_to_ebitda)
            if metrics.enterprise_value_to_ebitda > 0
            else 0
        )

        value = (pb_score + pe_score + ev_score) / 3.0

        # Weighted composite
        composite = self._quality_weight * quality + self._value_weight * value

        return composite

    def construct_portfolio(
        self,
        quality_metrics: Dict[str, QualityMetrics],
        capital: float,
        max_positions: int = 25,
        min_weight: float | None = None,
        max_weight: float = 0.06,
    ) -> QualityPortfolio:
        """
        Construct quality portfolio.

        Args:
            quality_metrics: Dictionary of symbol -> QualityMetrics
            capital: Total capital to invest
            max_positions: Maximum number of positions
            min_weight: Minimum weight per position
            max_weight: Maximum weight per position

        Returns:
            QualityPortfolio with optimal allocation
        """
        logger.info(
            "Constructing quality portfolio",
            extra={
                "capital": capital,
                "max_positions": max_positions,
                "min_weight": min_weight,
                "max_weight": max_weight,
                "available_stocks": len(quality_metrics),
            },
        )
        # Get min_weight from config if not provided
        if min_weight is None:
            try:
                config = get_config()
                min_weight = float(getattr(config.trading, 'min_allocation_weight', 0.02))
            except Exception:
                min_weight = 0.02

        # Rank stocks
        ranked = self.rank_quality_stocks(quality_metrics)

        # Select top stocks
        n_stocks = min(len(ranked), max_positions)
        selected = ranked[:n_stocks]

        if not selected:
            logger.warning(
                "No quality stocks selected for portfolio",
                extra={"capital": capital, "max_positions": max_positions},
            )
            return QualityPortfolio(
                positions={},
                portfolio_quality_score=0.0,
                portfolio_profitability=0.0,
                portfolio_financial_health=0.0,
            )

        # Equal-weight with quality adjustments
        weights = {}
        for symbol, _score in selected:
            # Base equal weight
            base_weight = 1.0 / n_stocks

            # Adjust by quality (higher quality = slightly higher weight)
            metrics = quality_metrics[symbol]
            quality_adjustment = 1.0 + 0.5 * (metrics.overall_quality_score - 0.5)

            weights[symbol] = base_weight * quality_adjustment

        # Normalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {s: w / total_weight for s, w in weights.items()}

        # Apply weight constraints
        weights = self._apply_weight_constraints(weights, min_weight, max_weight)

        # Renormalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {s: w / total_weight for s, w in weights.items()}

        # Calculate portfolio metrics
        portfolio_quality = sum(
            quality_metrics[s].overall_quality_score * w for s, w in weights.items()
        )
        portfolio_profitability = sum(
            quality_metrics[s].profitability_score * w for s, w in weights.items()
        )
        portfolio_health = sum(
            quality_metrics[s].financial_health_score * w for s, w in weights.items()
        )

        logger.info(
            "Quality portfolio constructed successfully",
            extra={
                "positions_count": len(weights),
                "portfolio_quality_score": portfolio_quality,
                "portfolio_profitability": portfolio_profitability,
                "portfolio_financial_health": portfolio_health,
                "capital": capital,
            },
        )

        return QualityPortfolio(
            positions=weights,
            portfolio_quality_score=portfolio_quality,
            portfolio_profitability=portfolio_profitability,
            portfolio_financial_health=portfolio_health,
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

    def generate_signal(
        self,
        metrics: QualityMetrics,
        current_price: float,
        fair_value: float = 0.0,
    ) -> QualitySignal:
        """
        Generate trading signal for quality stock.

        Args:
            metrics: Quality metrics
            current_price: Current price
            fair_value: Estimated fair value (optional)

        Returns:
            QualitySignal with action
        """
        logger.debug(
            "Generating quality signal",
            extra={
                "symbol": metrics.symbol,
                "current_price": current_price,
                "fair_value": fair_value,
                "quality_score": metrics.overall_quality_score,
            },
        )
        # Get quality category
        category = metrics.quality_category

        # Valuation check
        if fair_value > 0:
            valuation_ratio = current_price / fair_value
        else:
            valuation_ratio = 1.0

        # High quality stocks
        if category == QualitySignal.HIGH_QUALITY:
            if valuation_ratio < 0.8:
                return QualitySignal.HIGH_QUALITY  # Buy high quality at discount
            elif valuation_ratio > 1.2:
                return QualitySignal.GOOD_QUALITY  # Overvalued, downgrade
            else:
                return category

        # Good quality stocks
        elif category == QualitySignal.GOOD_QUALITY:
            if valuation_ratio < 0.75:
                return QualitySignal.GOOD_QUALITY  # Buy at discount
            else:
                return category

        # Avoid poor quality
        elif category in (QualitySignal.LOW_QUALITY, QualitySignal.POOR_QUALITY):
            logger.debug(
                "Poor quality stock signal generated",
                extra={
                    "symbol": metrics.symbol,
                    "category": category.value,
                    "quality_score": metrics.overall_quality_score,
                },
            )
            return QualitySignal.POOR_QUALITY  # Avoid

        else:
            logger.debug(
                "Quality signal generated",
                extra={
                    "symbol": metrics.symbol,
                    "category": category.value,
                    "valuation_ratio": valuation_ratio,
                },
            )
            return category

    def calculate_gross_profitability_premium(
        self,
        quality_metrics: Dict[str, QualityMetrics],
        returns: Dict[str, float],
    ) -> Tuple[float, float]:
        """
        Calculate gross profitability premium.

        Compares returns of high-gross-margin stocks vs low-gross-margin stocks.

        Args:
            quality_metrics: Dictionary of symbol -> QualityMetrics
            returns: Dictionary of symbol -> return

        Returns:
            Tuple of (high_gp_return, low_gp_return)
        """
        logger.debug(
            "Calculating gross profitability premium",
            extra={"stocks_count": len(quality_metrics), "returns_count": len(returns)},
        )
        # Split by gross profit margin
        high_gp = []
        low_gp = []

        for symbol, metrics in quality_metrics.items():
            if symbol not in returns:
                continue

            if metrics.gross_profit_margin > 0.4:
                high_gp.append(returns[symbol])
            elif metrics.gross_profit_margin < 0.2:
                low_gp.append(returns[symbol])

        high_gp_return = np.mean(high_gp) if high_gp else 0.0
        low_gp_return = np.mean(low_gp) if low_gp else 0.0

        logger.info(
            "Gross profitability premium calculated",
            extra={
                "high_gp_stocks": len(high_gp),
                "low_gp_stocks": len(low_gp),
                "high_gp_return": float(high_gp_return),
                "low_gp_return": float(low_gp_return),
                "premium": float(high_gp_return - low_gp_return),
            },
        )

        return float(high_gp_return), float(low_gp_return)
