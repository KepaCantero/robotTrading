"""
Portfolio Allocation Calculations

This module provides portfolio-level calculation functions for analytics
including concentration metrics, diversification scores, and allocation analysis.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio
    from app.domain.models.portfolio_analytics import PortfolioAllocation


class PortfolioCalculations:
    """Portfolio-level calculation utilities for analytics."""

    def calculate_herfindahl_index(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate Herfindahl concentration index.

        Sum of squared position weights. Higher values indicate more concentration.
        Range: 1/N (perfectly diversified) to 1 (single position).

        Args:
            portfolio: Portfolio object with positions

        Returns:
            Herfindahl index (0-1 range)
        """
        if not portfolio.positions:
            return Decimal("0")

        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        weights = [pos.market_value / total_value for pos in portfolio.positions]
        herfindahl = Decimal(str(sum(w**2 for w in weights)))

        return herfindahl

    def calculate_effective_positions(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate effective number of positions.

        Inverse of Herfindahl index. Represents the number of equal-weighted
        positions that would provide the same level of diversification.

        Args:
            portfolio: Portfolio object with positions

        Returns:
            Effective number of positions
        """
        herfindahl = self.calculate_herfindahl_index(portfolio)

        if herfindahl == 0:
            return Decimal("0")

        return Decimal("1") / herfindahl

    def calculate_largest_position_weight(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate weight of largest position as percentage.

        Args:
            portfolio: Portfolio object with positions

        Returns:
            Largest position weight as percentage
        """
        if not portfolio.positions:
            return Decimal("0")

        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        largest_position = max(portfolio.positions, key=lambda p: p.market_value)
        return Decimal(str(largest_position.market_value / total_value * 100))

    def calculate_diversification_ratio(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate diversification ratio.

        Ratio of effective positions to actual positions.
        Higher values indicate better diversification.

        Args:
            portfolio: Portfolio object with positions

        Returns:
            Diversification ratio (0-1 range)
        """
        effective_positions = self.calculate_effective_positions(portfolio)
        actual_positions = len(portfolio.positions)

        if actual_positions == 0:
            return Decimal("0")

        return effective_positions / actual_positions

    def calculate_equity_allocation(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate equity allocation as percentage.

        Args:
            portfolio: Portfolio object with positions

        Returns:
            Equity allocation as percentage
        """
        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        equity_value = sum(pos.market_value for pos in portfolio.positions)
        return Decimal(str(equity_value / total_value * 100))

    def calculate_cash_allocation(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate cash allocation as percentage.

        Args:
            portfolio: Portfolio object with positions and cash_balance

        Returns:
            Cash allocation as percentage
        """
        total_value = portfolio.total_value
        if total_value == 0:
            return Decimal("0")

        return Decimal(str(portfolio.cash_balance / total_value * 100))

    def get_top_holdings(self, portfolio: Portfolio, limit: int = 10) -> list[dict]:
        """
        Get top holdings by market value.

        Args:
            portfolio: Portfolio object with positions
            limit: Maximum number of holdings to return

        Returns:
            List of dicts with symbol, weight, market_value, quantity
        """
        total_value = portfolio.total_value
        top_holdings = []

        sorted_positions = sorted(portfolio.positions, key=lambda p: p.market_value, reverse=True)[
            :limit
        ]

        for position in sorted_positions:
            weight = (
                (position.market_value / total_value * 100) if total_value > 0 else Decimal("0")
            )
            top_holdings.append(
                {
                    "symbol": position.symbol,
                    "weight": weight,
                    "market_value": position.market_value,
                    "quantity": position.quantity,
                }
            )

        return top_holdings

    def estimate_rebalance_risk_impact(
        self,
        current: PortfolioAllocation,
        target: PortfolioAllocation,
        risk_impact_factor: Decimal,
    ) -> Decimal:
        """
        Estimate risk impact of rebalancing.

        Args:
            current: Current portfolio allocation
            target: Target portfolio allocation
            risk_impact_factor: Factor to scale impact

        Returns:
            Estimated risk impact
        """
        equity_change = abs(current.equity_allocation - target.equity_allocation)
        return Decimal(str(equity_change * risk_impact_factor))

    def estimate_rebalance_return_impact(
        self,
        current: PortfolioAllocation,
        target: PortfolioAllocation,
        return_impact_factor: Decimal,
    ) -> Decimal:
        """
        Estimate return impact of rebalancing.

        Args:
            current: Current portfolio allocation
            target: Target portfolio allocation
            return_impact_factor: Factor to scale impact

        Returns:
            Estimated return impact
        """
        equity_change = target.equity_allocation - current.equity_allocation
        return Decimal(str(equity_change * return_impact_factor))

    def calculate_liquidity_score(self, portfolio: Portfolio) -> Decimal:
        """
        Calculate liquidity score based on cash ratio.

        Args:
            portfolio: Portfolio object with cash_balance and total_value

        Returns:
            Liquidity score (0-100)
        """
        cash_ratio = (
            portfolio.cash_balance / portfolio.total_value
            if portfolio.total_value > 0
            else Decimal("0")
        )

        return min(cash_ratio * 100, Decimal("100"))

    def calculate_diversification_score(
        self, portfolio: Portfolio, well_diversified_threshold: Decimal | None = None
    ) -> Decimal:
        """
        Calculate diversification score (0-100).

        Based on effective number of positions relative to a threshold.
        A higher score indicates better diversification.

        Args:
            portfolio: Portfolio object with positions
            well_diversified_threshold: Number of positions considered well-diversified
                (default: 10 positions)

        Returns:
            Diversification score (0-100)
        """
        if not portfolio.positions:
            return Decimal("0")

        if well_diversified_threshold is None:
            well_diversified_threshold = Decimal("10")

        effective_positions = self.calculate_effective_positions(portfolio)

        return min(effective_positions / well_diversified_threshold, Decimal("1")) * 100
