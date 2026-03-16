"""
Portfolio Performance Calculations

This module provides performance calculation functions for portfolio analytics
including returns, volatility, and various performance ratios.
"""

import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List


class PerformanceCalculations:
    """Performance calculation utilities for portfolio analytics."""

    def __init__(self, risk_free_rate: Decimal, benchmark_return: Decimal):
        """
        Initialize performance calculations with configuration.

        Args:
            risk_free_rate: Annual risk-free rate (e.g., 0.02 for 2%)
            benchmark_return: Annual benchmark return (e.g., 0.08 for 8%)
        """
        self._risk_free_rate = risk_free_rate
        self._benchmark_return = benchmark_return

    def get_period_start_date(self, end_date: datetime, period_value: str) -> datetime:
        """
        Get start date based on performance period.

        Args:
            end_date: End date for the period
            period_value: Period string (DAILY, WEEKLY, MONTHLY, etc.)

        Returns:
            Calculated start date for the period
        """
        period_map = {
            "DAILY": timedelta(days=1),
            "WEEKLY": timedelta(weeks=1),
            "MONTHLY": timedelta(days=30),
            "QUARTERLY": timedelta(days=90),
            "YEARLY": timedelta(days=365),
            "ALL_TIME": timedelta(days=365 * 5),
        }
        delta = period_map.get(period_value, timedelta(days=30))
        return end_date - delta

    def calculate_returns(self, values: List[Decimal]) -> List[Decimal]:
        """
        Calculate period-over-period returns from portfolio values.

        Args:
            values: List of portfolio values in chronological order

        Returns:
            List of decimal returns (as fractions, not percentages)
        """
        if len(values) < 2:
            return []

        returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                return_val = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(return_val)

        return returns

    def calculate_total_return(self, values: List[Decimal]) -> Decimal:
        """
        Calculate total return over the entire period.

        Args:
            values: List of portfolio values in chronological order

        Returns:
            Total return as percentage
        """
        if len(values) < 2:
            return Decimal("0")

        return (values[-1] - values[0]) / values[0] * 100

    def calculate_annualized_return(self, returns: List[Decimal], period_value: str) -> Decimal:
        """
        Calculate annualized return from period returns.

        Args:
            returns: List of period returns
            period_value: Period string for annualization factor

        Returns:
            Annualized return as percentage
        """
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)

        annualization_factors = {
            "DAILY": 252,
            "WEEKLY": 52,
            "MONTHLY": 12,
            "QUARTERLY": 4,
            "YEARLY": 1,
        }
        factor = annualization_factors.get(period_value, 365)

        return avg_return * factor * 100

    def calculate_cumulative_return(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate cumulative return from period returns.

        Args:
            returns: List of period returns

        Returns:
            Cumulative return as percentage
        """
        if not returns:
            return Decimal("0")

        cumulative = Decimal("1")
        for ret in returns:
            cumulative *= 1 + ret

        return (cumulative - 1) * 100

    def calculate_volatility(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate volatility (standard deviation of returns).

        Args:
            returns: List of period returns

        Returns:
            Volatility as percentage
        """
        if len(returns) < 2:
            return Decimal("0")

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)

        return (variance ** Decimal("0.5")) * 100

    def calculate_sharpe_ratio(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate Sharpe ratio (risk-adjusted return).

        Args:
            returns: List of period returns

        Returns:
            Sharpe ratio (capped to [-10, 10] range)
        """
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        volatility = self.calculate_volatility(returns) / 100

        if volatility == 0:
            return Decimal("0")

        risk_free_daily = self._risk_free_rate / 252
        excess_return = avg_return - risk_free_daily

        sharpe = excess_return / volatility
        return max(min(sharpe, Decimal("10")), Decimal("-10"))

    def calculate_sortino_ratio(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate Sortino ratio (downside risk-adjusted return).

        Args:
            returns: List of period returns

        Returns:
            Sortino ratio
        """
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return Decimal("0")

        downside_deviation = Decimal(str(statistics.stdev([float(r) for r in downside_returns])))

        if downside_deviation == 0:
            return Decimal("0")

        return (avg_return - self._risk_free_rate / 252) / downside_deviation

    def calculate_max_drawdown(self, values: List[Decimal]) -> Decimal:
        """
        Calculate maximum drawdown from peak.

        Args:
            values: List of portfolio values in chronological order

        Returns:
            Maximum drawdown as percentage (positive value)
        """
        if len(values) < 2:
            return Decimal("0")

        peak = values[0]
        max_dd = Decimal("0")

        for value in values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown

        return max_dd * 100

    def calculate_var(self, returns: List[Decimal], confidence: float) -> Decimal:
        """
        Calculate Value at Risk at given confidence level.

        Args:
            returns: List of period returns
            confidence: Confidence level (e.g., 0.95 for 95%)

        Returns:
            VaR as percentage (negative value representing loss)
        """
        if not returns:
            return Decimal("0")

        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))

        if index >= len(sorted_returns):
            return Decimal("0")

        return sorted_returns[index] * 100

    def calculate_calmar_ratio(self, annualized_return: Decimal, max_drawdown: Decimal) -> Decimal:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            annualized_return: Annualized return as percentage
            max_drawdown: Maximum drawdown as percentage

        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return Decimal("0")

        return annualized_return / abs(max_drawdown)

    def calculate_information_ratio(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate Information ratio vs benchmark.

        Args:
            returns: List of period returns

        Returns:
            Information ratio (capped to [-10, 10] range)
        """
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        benchmark_return = self._benchmark_return / 252

        excess_return = avg_return - benchmark_return
        tracking_error = self.calculate_tracking_error(returns)

        if tracking_error == 0:
            return Decimal("0")

        info_ratio = excess_return / tracking_error
        return max(min(info_ratio, Decimal("10")), Decimal("-10"))

    def calculate_treynor_ratio(self, returns: List[Decimal], beta: Decimal) -> Decimal:
        """
        Calculate Treynor ratio (excess return / beta).

        Args:
            returns: List of period returns
            beta: Portfolio beta

        Returns:
            Treynor ratio (capped to [-10, 10] range)
        """
        if not returns or beta == 0:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)

        treynor = (avg_return - self._risk_free_rate / 252) / beta
        return max(min(treynor, Decimal("10")), Decimal("-10"))

    def calculate_jensen_alpha(self, returns: List[Decimal], beta: Decimal) -> Decimal:
        """
        Calculate Jensen's alpha.

        Args:
            returns: List of period returns
            beta: Portfolio beta

        Returns:
            Jensen's alpha (capped to [-1, 1] range)
        """
        if not returns:
            return Decimal("0")

        avg_return = sum(returns) / len(returns)
        benchmark_return = self._benchmark_return / 252

        alpha = (avg_return - self._risk_free_rate / 252) - beta * (
            benchmark_return - self._risk_free_rate / 252
        )
        return max(min(alpha, Decimal("1")), Decimal("-1"))

    def calculate_tracking_error(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate tracking error vs benchmark.

        Args:
            returns: List of period returns

        Returns:
            Tracking error as decimal
        """
        if not returns:
            return Decimal("0")

        benchmark_return = self._benchmark_return / 252
        excess_returns = [r - benchmark_return for r in returns]

        return self.calculate_volatility(excess_returns) / 100

    def calculate_realized_volatility(self, returns: List[Decimal]) -> Decimal:
        """
        Calculate realized volatility.

        Args:
            returns: List of period returns

        Returns:
            Realized volatility as percentage
        """
        return self.calculate_volatility(returns)
