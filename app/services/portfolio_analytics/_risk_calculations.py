"""
Portfolio Risk Calculations

This module provides risk calculation functions for portfolio analytics
including downside risk, tail risk, and volatility metrics.
"""

from __future__ import annotations

from decimal import Decimal


class RiskCalculations:
    """Risk calculation utilities for portfolio analytics."""

    def calculate_downside_deviation(self, returns: list[Decimal], volatility_func) -> Decimal:
        """
        Calculate downside deviation (volatility of negative returns only).

        Args:
            returns: List of period returns
            volatility_func: Function to calculate volatility

        Returns:
            Downside deviation as percentage
        """
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return Decimal("0")

        return Decimal(str(volatility_func(negative_returns)))

    def calculate_semi_variance(self, returns: list[Decimal]) -> Decimal:
        """
        Calculate semi-variance (variance of returns below mean).

        Args:
            returns: List of period returns

        Returns:
            Semi-variance
        """
        mean_return = (
            sum(returns, Decimal("0")) / Decimal(len(returns)) if returns else Decimal("0")
        )
        negative_deviations = [(r - mean_return) ** 2 for r in returns if r < mean_return]

        if not negative_deviations:
            return Decimal("0")

        return sum(negative_deviations, Decimal("0")) / Decimal(len(negative_deviations))

    def calculate_lower_partial_moment(
        self, returns: list[Decimal], target_return: Decimal | None = None
    ) -> Decimal:
        """
        Calculate lower partial moment (squared deviations below target).

        Args:
            returns: List of period returns
            target_return: Target return threshold (default: 0)

        Returns:
            Lower partial moment
        """
        if target_return is None:
            target_return = Decimal("0")

        negative_deviations = [(target_return - r) ** 2 for r in returns if r < target_return]

        if not negative_deviations:
            return Decimal("0")

        return sum(negative_deviations, Decimal("0")) / Decimal(len(negative_deviations))

    def calculate_skewness(self, returns: list[Decimal], volatility_func) -> Decimal:
        """
        Calculate skewness of return distribution.

        Args:
            returns: List of period returns
            volatility_func: Function to calculate volatility

        Returns:
            Skewness (negative = left-skewed, positive = right-skewed)
        """
        if len(returns) < 3:
            return Decimal("0")

        mean_return = sum(returns, Decimal("0")) / Decimal(len(returns))
        std_dev = Decimal(str(volatility_func(returns))) / Decimal("100")

        if std_dev == 0:
            return Decimal("0")

        skewness = sum(((r - mean_return) / std_dev) ** 3 for r in returns) / len(returns)
        return Decimal(str(skewness))

    def calculate_kurtosis(self, returns: list[Decimal], volatility_func) -> Decimal:
        """
        Calculate kurtosis of return distribution.

        Args:
            returns: List of period returns
            volatility_func: Function to calculate volatility

        Returns:
            Kurtosis (3 = normal distribution)
        """
        if len(returns) < 4:
            return Decimal("0")

        mean_return = sum(returns, Decimal("0")) / Decimal(len(returns))
        std_dev = Decimal(str(volatility_func(returns))) / Decimal("100")

        if std_dev == 0:
            return Decimal("0")

        kurtosis = sum(((r - mean_return) / std_dev) ** 4 for r in returns) / len(returns)
        return Decimal(str(kurtosis))

    def calculate_tail_ratio(self, returns: list[Decimal]) -> Decimal:
        """
        Calculate tail ratio (upper tail / lower tail).

        Args:
            returns: List of period returns

        Returns:
            Tail ratio (>1 = fatter upper tail, <1 = fatter lower tail)
        """
        if len(returns) < 20:
            return Decimal("0")

        sorted_returns = sorted(returns)
        tail_size = len(returns) // 10

        if tail_size == 0:
            return Decimal("0")

        upper_tail = sorted_returns[-tail_size:]
        lower_tail = sorted_returns[:tail_size]

        upper_avg = sum(upper_tail, Decimal("0")) / Decimal(len(upper_tail))
        lower_avg = sum(lower_tail, Decimal("0")) / Decimal(len(lower_tail))

        if lower_avg == 0:
            return Decimal("0")

        return abs(upper_avg / lower_avg)
