"""
PHASE 3: Sharpe Ratio Monitor - Performance-Based Capital Allocation

Monitors rolling Sharpe ratio to allocate capital based on performance.
Strong performance (Sharpe > 1.5) → maintain full allocation (1.0x)
Weak performance (Sharpe < 0.5) → reduce allocation (0.5x)
Negative returns → minimal allocation (0.2x)

Formula:
- Sharpe = (mean_return - risk_free_rate) / std_return
- Annualized = Sharpe * sqrt(252)
- Scaling based on performance brackets

Uses centralized configuration for trading calendar constants.
"""

import logging
import math
import statistics
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional, Tuple

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class SharpeRatioMonitor:
    """
    Monitors rolling Sharpe ratio for performance-based capital allocation.

    Logic:
    - Sharpe > 1.5 → scale = 1.0x (strong, maintain allocation)
    - Sharpe 0.5-1.5 → scale = 0.7-0.9x (decent, slight reduction)
    - Sharpe 0-0.5 → scale = 0.2-0.5x (weak, significant reduction)
    - Sharpe < 0 → scale = 0.2x (negative, minimal allocation)

    Usage:
        monitor = SharpeRatioMonitor()
        sharpe = await monitor.calculate_rolling_sharpe(daily_returns, window=30)
        scale = monitor.calculate_sharpe_scale(sharpe)
    """

    def __init__(self, risk_free_rate: Decimal = None):
        """
        Initialize Sharpe ratio monitor.

        Args:
            risk_free_rate: Annual risk-free rate (uses centralized config if None)
        """
        # Get trading calendar constants from centralized config
        tt = get_config().trading_thresholds
        annual_trading_days = tt.annual_trading_days_const

        # Use default from centralized config if not provided
        if risk_free_rate is None:
            risk_free_rate = Decimal(str(tt.opportunity_risk_free_rate))

        self.risk_free_rate = risk_free_rate
        self.daily_risk_free_rate = risk_free_rate / Decimal(str(annual_trading_days))
        self.sharpe_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}

    async def calculate_rolling_sharpe(
        self,
        daily_returns: List[Decimal],
        window_days: int = 30,
        risk_free_rate: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate rolling Sharpe ratio over window_days.

        Formula:
        - Daily Sharpe = (mean_daily_return - daily_rf_rate) / std_daily_return
        - Annualized Sharpe = Daily Sharpe * sqrt(252)

        Args:
            daily_returns: List of daily returns as decimals (e.g., 0.01 = 1%)
            window_days: Window size for rolling calculation (default 30)
            risk_free_rate: Override default risk-free rate

        Returns:
            Annualized Sharpe ratio as Decimal
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        # Get trading calendar constants from centralized config
        tt = get_config().trading_thresholds
        annual_trading_days = Decimal(str(tt.annual_trading_days_const))
        daily_rf = risk_free_rate / annual_trading_days

        if len(daily_returns) < window_days:
            logger.warning(
                f"Insufficient returns data: {len(daily_returns)} < window {window_days}"
            )
            return Decimal("0")

        # Use last window_days returns
        window_returns = daily_returns[-window_days:]

        # Calculate mean return
        mean_return = sum(window_returns) / Decimal(len(window_returns))

        # Calculate standard deviation
        if len(window_returns) < 2:
            logger.warning("Cannot calculate std dev with <2 data points")
            return Decimal("0")

        # Convert to float for statistics calculation
        float_returns = [float(r) for r in window_returns]
        std_return = Decimal(str(statistics.stdev(float_returns)))

        if std_return == Decimal("0"):
            logger.warning("Standard deviation is 0, cannot calculate Sharpe")
            return Decimal("0")

        # Calculate daily Sharpe
        daily_sharpe = (mean_return - daily_rf) / std_return

        # Annualize: multiply by sqrt(annual_trading_days)
        tt = get_config().trading_thresholds
        annual_trading_days = tt.annual_trading_days_const
        annualized_sharpe = daily_sharpe * Decimal(str(math.sqrt(annual_trading_days)))

        return annualized_sharpe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_sharpe_scale(
        self,
        sharpe_ratio: Decimal,
    ) -> Decimal:
        """
        Return capital allocation scaling based on Sharpe ratio.

        Mapping:
        - Sharpe > 1.5: 1.0x (strong performance)
        - Sharpe 1.0-1.5: 0.9x
        - Sharpe 0.5-1.0: 0.7-0.8x (moderate)
        - Sharpe 0-0.5: 0.5x (weak)
        - Sharpe < 0: 0.2x (negative)

        Args:
            sharpe_ratio: Sharpe ratio value

        Returns:
            Scaling factor (0.2 to 1.0), quantized to 3 decimals
        """
        if sharpe_ratio >= Decimal("1.5"):
            # Strong performance - maintain allocation
            scale = Decimal("1.0")
        elif sharpe_ratio >= Decimal("1.0"):
            # Good performance - slight reduction (0.9x)
            scale = Decimal("0.9")
        elif sharpe_ratio >= Decimal("0.5"):
            # Decent performance - moderate reduction (0.7x to 0.8x)
            # Linear interpolation between 0.5 and 1.0
            # At 0.5: 0.7x, at 1.0: 0.9x
            t = (sharpe_ratio - Decimal("0.5")) / Decimal("0.5")
            scale = Decimal("0.7") + (t * Decimal("0.2"))
        elif sharpe_ratio >= Decimal("0"):
            # Weak performance - significant reduction (0.2x to 0.5x)
            # Linear interpolation: at 0: 0.2x, at 0.5: 0.7x
            t = sharpe_ratio / Decimal("0.5")
            scale = Decimal("0.2") + (t * Decimal("0.3"))
        else:
            # Negative returns - minimal allocation
            scale = Decimal("0.2")

        return scale.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def is_sharpe_declining(
        self,
        current_sharpe: Decimal,
        previous_sharpe: Optional[Decimal] = None,
        history: Optional[List[Decimal]] = None,
        window: int = 5,
    ) -> Tuple[bool, str]:
        """
        Check if Sharpe ratio is trending down.

        Can check either against single previous value or recent history.

        Args:
            current_sharpe: Current Sharpe ratio
            previous_sharpe: Previous period Sharpe (optional)
            history: List of recent Sharpe values (optional, used if no previous_sharpe)
            window: Window size for trend detection in history (default 5)

        Returns:
            Tuple of (is_declining, reason)
        """
        if previous_sharpe is not None:
            # Check against single previous value
            is_declining = current_sharpe < previous_sharpe
            reason = f"Current {current_sharpe:.2f} < Previous {previous_sharpe:.2f}"
            return is_declining, reason

        if history and len(history) >= window:
            # Check if recent values are trending down
            recent = history[-window:]
            # Calculate slope: is the trend downward?
            differences = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
            avg_change = sum(differences) / Decimal(len(differences))
            is_declining = avg_change < Decimal("0")
            reason = f"Trend slope: {avg_change:.3f} (window={window})"
            return is_declining, reason

        return False, "Insufficient data for trend detection"

    def get_sharpe_interpretation(self, sharpe_ratio: Decimal) -> str:
        """
        Get human-readable interpretation of Sharpe ratio.

        Args:
            sharpe_ratio: Sharpe ratio value

        Returns:
            Interpretation string
        """
        if sharpe_ratio >= Decimal("2.0"):
            return "Outstanding"
        elif sharpe_ratio >= Decimal("1.5"):
            return "Very Good"
        elif sharpe_ratio >= Decimal("1.0"):
            return "Good"
        elif sharpe_ratio >= Decimal("0.5"):
            return "Acceptable"
        elif sharpe_ratio >= Decimal("0"):
            return "Weak"
        else:
            return "Poor (Negative)"

    def calculate_information_ratio(
        self,
        portfolio_returns: List[Decimal],
        benchmark_returns: List[Decimal],
        risk_free_rate: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate Information Ratio (excess return / tracking error).

        Information Ratio = (mean(portfolio - benchmark)) / std(portfolio - benchmark)

        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns (same length as portfolio)
            risk_free_rate: Risk-free rate (not used for IR, kept for compatibility)

        Returns:
            Information Ratio as Decimal
        """
        if len(portfolio_returns) != len(benchmark_returns):
            raise ValueError("Portfolio and benchmark returns must have same length")

        if len(portfolio_returns) < 2:
            return Decimal("0")

        # Calculate excess returns
        excess_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]

        # Mean excess return
        mean_excess = sum(excess_returns) / Decimal(len(excess_returns))

        # Tracking error (std of excess returns)
        float_excess = [float(r) for r in excess_returns]
        tracking_error = Decimal(str(statistics.stdev(float_excess)))

        if tracking_error == Decimal("0"):
            return Decimal("0")

        ir = mean_excess / tracking_error
        return ir.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def detect_performance_regime_shift(
        self,
        history: List[Decimal],
        window: int = 10,
    ) -> Tuple[bool, str]:
        """
        Detect significant changes in performance regime.

        Args:
            history: Historical Sharpe ratios
            window: Window size for comparison (default 10)

        Returns:
            Tuple of (regime_shift_detected, description)
        """
        if len(history) < window * 2:
            return False, "Insufficient history"

        # Split into two halves
        mid = len(history) - window
        recent_window = history[mid:]
        prior_window = history[mid - window : mid]

        mean_recent = sum(recent_window) / Decimal(len(recent_window))
        mean_prior = sum(prior_window) / Decimal(len(prior_window))

        # Calculate if change is significant (>30%)
        if mean_prior != Decimal("0"):
            percent_change = ((mean_recent - mean_prior) / mean_prior).abs()
            is_significant = percent_change > Decimal("0.3")

            direction = "improvement" if mean_recent > mean_prior else "deterioration"
            desc = f"Sharpe {direction} {percent_change:.0%}: {mean_prior:.2f} → {mean_recent:.2f}"

            return is_significant, desc

        return False, "Prior Sharpe was zero"

    def suggest_capital_adjustment(
        self,
        current_sharpe: Decimal,
        previous_sharpe: Optional[Decimal] = None,
        current_allocation: Optional[Decimal] = None,
    ) -> Tuple[Decimal, str]:
        """
        Suggest capital adjustment based on Sharpe trend.

        Args:
            current_sharpe: Current Sharpe ratio
            previous_sharpe: Previous Sharpe ratio
            current_allocation: Current capital allocation factor

        Returns:
            Tuple of (suggested_allocation, reason)
        """
        if current_allocation is None:
            current_allocation = Decimal("1.0")
        suggested_scale = self.calculate_sharpe_scale(current_sharpe)
        current_interpretation = self.get_sharpe_interpretation(current_sharpe)

        if previous_sharpe is not None:
            previous_scale = self.calculate_sharpe_scale(previous_sharpe)
            previous_interpretation = self.get_sharpe_interpretation(previous_sharpe)

            if suggested_scale > previous_scale:
                reason = (
                    f"Performance improving: {previous_interpretation} → {current_interpretation}, "
                    f"scale {previous_scale:.2f}x → {suggested_scale:.2f}x"
                )
            elif suggested_scale < previous_scale:
                reason = (
                    f"Performance deteriorating: {previous_interpretation} → {current_interpretation}, "
                    f"scale {previous_scale:.2f}x → {suggested_scale:.2f}x"
                )
            else:
                reason = (
                    f"Performance stable: {current_interpretation}, "
                    f"maintain scale {suggested_scale:.2f}x"
                )
        else:
            reason = f"Current performance: {current_interpretation}, scale {suggested_scale:.2f}x"

        return suggested_scale, reason
