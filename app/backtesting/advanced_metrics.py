"""
Advanced Financial Metrics Calculator - PHASE 4 MODULE 7

Calculates sophisticated financial metrics including:
- Calmar Ratio: Risk-adjusted return relative to max drawdown
- Omega Ratio: Probability-weighted downside/upside
- Ulcer Index: Duration-weighted drawdown penalty
- Annualized Volatility: Return standard deviation
- Recovery Factor: Profit relative to drawdown
- Skewness & Kurtosis: Return distribution shape
- Value at Risk (VaR) & Conditional VaR (CVaR): Tail risk metrics
"""

import logging
from decimal import Decimal
from typing import List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class AdvancedMetricsCalculator:
    """Calculator for advanced financial metrics."""

    def __init__(self, risk_free_rate: Decimal = Decimal("0.02"), confidence_level: float = 0.95):
        """
        Initialize advanced metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
            confidence_level: Confidence level for VaR/CVaR (default: 95%)
        """
        self.risk_free_rate = float(risk_free_rate)
        self.confidence_level = confidence_level

    def calculate_calmar_ratio(self, cagr: Decimal, max_drawdown: Decimal) -> Optional[Decimal]:
        """
        Calculate Calmar Ratio.

        Formula: CAGR / |Max Drawdown|
        - Values > 1.0 are good
        - Values > 3.0 are excellent
        - Penalizes large drawdowns

        Args:
            cagr: Compound Annual Growth Rate (must not be None)
            max_drawdown: Maximum drawdown (negative value, must not be zero)

        Returns:
            Calmar Ratio or None if calculation not possible
        """
        try:
            if max_drawdown is None or cagr is None:
                return None

            abs_drawdown = abs(float(max_drawdown))
            if abs_drawdown == 0:
                return None

            calmar = float(cagr) / abs_drawdown
            return Decimal(str(round(calmar, 4)))

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return None

    def calculate_omega_ratio(
        self, returns: List[Decimal], threshold: float = 0.0
    ) -> Optional[Decimal]:
        """
        Calculate Omega Ratio.

        Formula: E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
        - Measures probability-weighted ratio of gains to losses
        - Values > 1.0 indicate more upside than downside
        - More sophisticated than Sharpe ratio

        Args:
            returns: List of returns
            threshold: Target return threshold (default: 0%)

        Returns:
            Omega Ratio or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            returns_array = np.array([float(r) for r in returns])

            # Calculate excess returns relative to threshold
            excess_above = np.maximum(returns_array - threshold, 0)
            excess_below = np.maximum(threshold - returns_array, 0)

            # Calculate averages
            avg_gain = np.mean(excess_above)
            avg_loss = np.mean(excess_below)

            # Avoid division by zero - no losses means infinite ratio
            if avg_loss == 0:
                if avg_gain > 0:
                    # Infinite ratio (all gains, no losses) - return large number
                    return Decimal("999999")
                # No gains, no losses - ratio is 1:1
                return Decimal("1")

            omega = avg_gain / avg_loss
            return Decimal(str(round(omega, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Omega ratio: {e}")
            return None

    def calculate_ulcer_index(
        self, equity_curve: List[Decimal], rolling_window: int = 14
    ) -> Optional[Decimal]:
        """
        Calculate Ulcer Index.

        Formula: sqrt(mean(max(0, (Peak - Price) / Peak)^2))
        - Penalizes the duration and magnitude of underwater periods
        - Only looks at drawdowns, not recovery
        - More sensitive to deep drawdowns than max drawdown alone

        Args:
            equity_curve: List of portfolio equity values
            rolling_window: Window size for peak calculation (default: 14)

        Returns:
            Ulcer Index or None if calculation not possible
        """
        try:
            if not equity_curve or len(equity_curve) < 2:
                return None

            equity_array = np.array([float(e) for e in equity_curve])

            # Calculate rolling maximum (peak)
            rolling_max = np.maximum.accumulate(equity_array)

            # Calculate drawdown percentage from peak
            drawdowns = (rolling_max - equity_array) / rolling_max

            # Ulcer = sqrt(mean(drawdown^2))
            ulcer = np.sqrt(np.mean(np.square(drawdowns)))

            return Decimal(str(round(ulcer, 6)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Ulcer index: {e}")
            return None

    def calculate_annualized_volatility(self, returns: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate Annualized Volatility.

        Formula: std(returns) * sqrt(252)
        - Standard deviation of returns annualized
        - Higher volatility = higher risk
        - 252 = number of trading days per year

        Args:
            returns: List of returns

        Returns:
            Annualized Volatility or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            returns_array = np.array([float(r) for r in returns])
            daily_volatility = np.std(returns_array)

            # Annualize
            annualized_vol = daily_volatility * np.sqrt(252)

            return Decimal(str(round(annualized_vol, 6)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating annualized volatility: {e}")
            return None

    def calculate_recovery_factor(
        self, total_pnl: Decimal, max_drawdown: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Recovery Factor.

        Formula: Net Profit / |Max Drawdown|
        - Measures how much profit was made relative to the largest loss
        - Higher values indicate better risk-reward
        - Similar to Calmar but uses absolute profit instead of CAGR

        Args:
            total_pnl: Total profit/loss
            max_drawdown: Maximum drawdown (negative value)

        Returns:
            Recovery Factor or None if calculation not possible
        """
        try:
            if max_drawdown == 0 or max_drawdown is None:
                return None

            abs_drawdown = abs(float(max_drawdown))
            if abs_drawdown == 0:
                return None

            recovery = float(total_pnl) / abs_drawdown
            return Decimal(str(round(recovery, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Recovery factor: {e}")
            return None

    def calculate_profit_factor(
        self, gross_profit: Decimal, gross_loss: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Profit Factor.

        Formula: Gross Profit / |Gross Loss|
        - Ratio of total wins to total losses
        - Values > 1.0 are profitable
        - Values > 1.5 are generally considered good
        - Values > 2.0 are excellent

        Args:
            gross_profit: Sum of all winning trades
            gross_loss: Sum of all losing trades (absolute value)

        Returns:
            Profit Factor or None if calculation not possible
        """
        try:
            if not gross_loss or gross_loss == 0:
                return Decimal("999") if gross_profit > 0 else Decimal("0")

            abs_loss = abs(float(gross_loss))
            if abs_loss == 0:
                return Decimal("999") if gross_profit > 0 else Decimal("0")

            profit_factor = float(gross_profit) / abs_loss
            return Decimal(str(round(profit_factor, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Profit factor: {e}")
            return None

    def calculate_skewness(self, returns: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate Skewness of Returns.

        Formula: (Mean - Median) / StdDev, or using scipy.stats
        - Positive skew: tail on right side (occasional large gains)
        - Negative skew: tail on left side (occasional large losses)
        - Negative skew is generally worse for traders

        Args:
            returns: List of returns

        Returns:
            Skewness value or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 3:
                return None

            returns_array = np.array([float(r) for r in returns])
            skewness = stats.skew(returns_array)

            return Decimal(str(round(skewness, 6)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Skewness: {e}")
            return None

    def calculate_kurtosis(self, returns: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate Kurtosis of Returns (Excess Kurtosis).

        Formula: 4th moment / (stddev^4) - 3
        - Excess kurtosis = 0 for normal distribution
        - Positive excess kurtosis: fatter tails (more extreme events)
        - Negative excess kurtosis: thinner tails (fewer extreme events)
        - Traders prefer negative kurtosis (fewer extreme losses)

        Args:
            returns: List of returns

        Returns:
            Excess Kurtosis value or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 4:
                return None

            returns_array = np.array([float(r) for r in returns])
            kurtosis = stats.kurtosis(returns_array)  # Returns excess kurtosis

            return Decimal(str(round(kurtosis, 6)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Kurtosis: {e}")
            return None

    def calculate_var(
        self, returns: List[Decimal], confidence: Optional[float] = None
    ) -> Optional[Decimal]:
        """
        Calculate Value at Risk (VaR).

        Historical method: Uses percentile of returns distribution
        - VaR(95%) = worst 5% of returns
        - Negative value: potential loss
        - Example: VaR = -0.05 means 5% chance of losing 5% in a day

        Args:
            returns: List of returns
            confidence: Confidence level (default: self.confidence_level)

        Returns:
            VaR value or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            if confidence is None:
                confidence = self.confidence_level

            returns_array = np.array([float(r) for r in returns])
            var = np.percentile(returns_array, (1 - confidence) * 100)

            return Decimal(str(round(var, 6)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating VaR: {e}")
            return None

    def calculate_cvar(
        self, returns: List[Decimal], confidence: Optional[float] = None
    ) -> Optional[Decimal]:
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.

        Formula: Average of returns worse than VaR threshold
        - More conservative than VaR
        - Considers tail behavior beyond VaR threshold
        - Better risk measure for extreme events

        Args:
            returns: List of returns
            confidence: Confidence level (default: self.confidence_level)

        Returns:
            CVaR value or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            if confidence is None:
                confidence = self.confidence_level

            returns_array = np.array([float(r) for r in returns])
            var = np.percentile(returns_array, (1 - confidence) * 100)

            # Get returns worse than VaR threshold
            tail_returns = returns_array[returns_array <= var]

            if len(tail_returns) == 0:
                # If no returns worse than VaR, return VaR itself
                return Decimal(str(round(var, 6)))

            # CVaR = average of tail returns
            cvar = np.mean(tail_returns)

            return Decimal(str(round(cvar, 6)))

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error(f"Error calculating CVaR: {e}")
            return None

    def calculate_sortino_modified(
        self, returns: List[Decimal], target_return: float = 0.0
    ) -> Optional[Decimal]:
        """
        Calculate Modified Sortino Ratio.

        Uses target return threshold instead of risk-free rate.
        Formula: (Mean Return - Target) / Downside Deviation

        Args:
            returns: List of returns
            target_return: Target return threshold (default: 0%)

        Returns:
            Modified Sortino Ratio or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            returns_array = np.array([float(r) for r in returns])
            mean_return = np.mean(returns_array)

            # Calculate downside deviation (only negative deviations from target)
            downside_returns = np.minimum(returns_array - target_return, 0)
            downside_deviation = np.std(downside_returns)

            if downside_deviation == 0:
                return Decimal("999") if mean_return > target_return else Decimal("0")

            # Annualize
            annual_return = mean_return * 252
            annual_downside = downside_deviation * np.sqrt(252)

            sortino = (annual_return - target_return) / annual_downside

            return Decimal(str(round(sortino, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Modified Sortino: {e}")
            return None

    def calculate_tail_ratio(self, returns: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate Tail Ratio (Req #6 - Advanced Metrics).

        Measures the ratio of extreme gains to extreme losses.
        Formula: Percentile_95(gains) / |Percentile_5(losses)|
        - Values > 1.0 indicate better upside than downside tail behavior
        - Higher values indicate asymmetric returns favoring gains

        Args:
            returns: List of returns

        Returns:
            Tail Ratio or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 20:
                return None

            returns_array = np.array([float(r) for r in returns])

            # Calculate 95th percentile (extreme gains)
            percentile_95 = np.percentile(returns_array, 95)

            # Calculate 5th percentile (extreme losses)
            percentile_5 = np.percentile(returns_array, 5)

            # Tail ratio: ratio of extreme gains to extreme losses
            if percentile_5 >= 0:
                # No extreme losses, all returns are positive
                return Decimal("999")
            if percentile_5 == 0:
                return None

            tail_ratio = percentile_95 / abs(percentile_5)

            return Decimal(str(round(tail_ratio, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Tail Ratio: {e}")
            return None

    def calculate_sqn(
        self, returns: List[Decimal], number_of_trades: Optional[int] = None
    ) -> Optional[Decimal]:
        """
        Calculate System Quality Number (SQN) (Req #6 - Advanced Metrics).

        Van Tharp's metric for system quality.
        Formula: (Mean / StdDev) * sqrt(N)
        where N is number of trades (or returns)
        - SQN > 2.0: Excellent system
        - SQN 1.5 - 2.0: Good system
        - SQN 1.0 - 1.5: Acceptable system
        - SQN < 1.0: Poor system

        Args:
            returns: List of returns
            number_of_trades: Optional override for number of trades

        Returns:
            System Quality Number or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return None

            returns_array = np.array([float(r) for r in returns])

            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)

            if std_return == 0:
                return None

            # Use provided trade count or number of returns
            n = number_of_trades if number_of_trades else len(returns)

            # SQN = (Mean / StdDev) * sqrt(N)
            sqn = (mean_return / std_return) * np.sqrt(n)

            return Decimal(str(round(sqn, 4)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating SQN: {e}")
            return None

    def calculate_all_advanced_metrics(
        self,
        returns: List[Decimal],
        equity_curve: List[Decimal],
        cagr: Decimal,
        max_drawdown: Decimal,
        total_pnl: Decimal,
        gross_profit: Decimal,
        gross_loss: Decimal,
    ) -> dict:
        """
        Calculate all advanced metrics at once.

        Args:
            returns: List of returns
            equity_curve: List of equity values over time
            cagr: Compound Annual Growth Rate
            max_drawdown: Maximum drawdown
            total_pnl: Total profit/loss
            gross_profit: Sum of winning trades
            gross_loss: Sum of losing trades

        Returns:
            Dictionary with all advanced metrics
        """
        return {
            "calmar_ratio": self.calculate_calmar_ratio(cagr, max_drawdown),
            "omega_ratio": self.calculate_omega_ratio(returns),
            "ulcer_index": self.calculate_ulcer_index(equity_curve),
            "volatility_annualized": self.calculate_annualized_volatility(returns),
            "recovery_factor": self.calculate_recovery_factor(total_pnl, max_drawdown),
            "profit_factor": self.calculate_profit_factor(gross_profit, gross_loss),
            "skewness": self.calculate_skewness(returns),
            "kurtosis": self.calculate_kurtosis(returns),
            "var_95": self.calculate_var(returns),
            "cvar_95": self.calculate_cvar(returns),
        }
