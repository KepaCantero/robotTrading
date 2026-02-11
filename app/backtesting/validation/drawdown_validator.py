"""
Drawdown Validator for backtesting results.

Validates drawdown calculations to ensure accuracy
and detect potential issues in risk metrics.
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.backtesting.models import Trade, TradeStatus

logger = logging.getLogger(__name__)


class DrawdownValidationError(Exception):
    """Exception raised when drawdown validation fails."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}


class DrawdownValidator:
    """
    Validate drawdown calculations in backtesting results.

    Checks:
    - Max drawdown is correctly calculated
    - Drawdown is always negative (or zero)
    - Drawdown recovery is correctly tracked
    - No unrealistic drawdown values
    """

    # Validation thresholds
    MAX_DRAWDOWN_PCT = Decimal("100")  # Max 100% drawdown
    MIN_DRAWDOWN_PCT = Decimal("0")    # Min 0% drawdown

    def __init__(
        self,
        max_drawdown_pct: Optional[Decimal] = None,
        min_drawdown_pct: Optional[Decimal] = None,
    ):
        """
        Initialize Drawdown Validator.

        Args:
            max_drawdown_pct: Maximum allowed drawdown percentage
            min_drawdown_pct: Minimum allowed drawdown percentage
        """
        self.max_drawdown_pct = max_drawdown_pct or self.MAX_DRAWDOWN_PCT
        self.min_drawdown_pct = min_drawdown_pct or self.MIN_DRAWDOWN_PCT

    def calculate_equity_curve(
        self,
        trades: List[Trade],
        initial_capital: Decimal,
    ) -> List[Tuple[str, Decimal]]:
        """
        Calculate equity curve from trades.

        Args:
            trades: List of closed trades
            initial_capital: Starting capital

        Returns:
            List of (timestamp, equity_value) tuples
        """
        equity_curve = [("start", initial_capital)]
        current_capital = initial_capital

        # Sort trades by exit time
        closed_trades = [
            t for t in trades
            if t.status == TradeStatus.CLOSED and t.exit_time is not None
        ]
        closed_trades.sort(key=lambda t: t.exit_time)

        for trade in closed_trades:
            if trade.pnl is not None:
                current_capital += trade.pnl
                equity_curve.append((trade.exit_time.isoformat(), current_capital))

        return equity_curve

    def calculate_drawdown(
        self,
        equity_curve: List[Tuple[str, Decimal]],
    ) -> Tuple[List[Tuple[str, Decimal]], Decimal]:
        """
        Calculate drawdown series and max drawdown.

        Args:
            equity_curve: List of (timestamp, equity_value) tuples

        Returns:
            Tuple of (drawdown_series, max_drawdown)
        """
        if not equity_curve:
            return [], Decimal("0")

        drawdowns = []
        peak = equity_curve[0][1]
        max_dd = Decimal("0")

        for timestamp, equity in equity_curve:
            if equity > peak:
                peak = equity

            drawdown = (equity - peak) / peak * 100 if peak > 0 else Decimal("0")
            drawdowns.append((timestamp, drawdown))

            if drawdown < max_dd:
                max_dd = drawdown

        return drawdowns, max_dd

    def validate_max_drawdown(
        self,
        reported_max_dd: Decimal,
        equity_curve: Optional[List[Tuple[str, Decimal]]] = None,
        trades: Optional[List[Trade]] = None,
        initial_capital: Optional[Decimal] = None,
    ) -> bool:
        """
        Validate reported max drawdown.

        Args:
            reported_max_dd: Reported maximum drawdown (as percentage, e.g., -15.5)
            equity_curve: Optional pre-calculated equity curve
            trades: Optional trades to calculate equity curve
            initial_capital: Required if trades provided

        Returns:
            True if max drawdown is valid

        Raises:
            DrawdownValidationError: If validation fails
        """
        # Calculate equity curve if not provided
        if equity_curve is None:
            if trades is None or initial_capital is None:
                raise DrawdownValidationError(
                    "Must provide either equity_curve or trades + initial_capital"
                )
            equity_curve = self.calculate_equity_curve(trades, initial_capital)

        # Calculate actual max drawdown
        _, actual_max_dd = self.calculate_drawdown(equity_curve)

        # Compare (allow small rounding difference)
        difference = abs(reported_max_dd - actual_max_dd)

        if difference > Decimal("0.1"):  # Max 0.1% tolerance
            raise DrawdownValidationError(
                f"Max drawdown mismatch: reported {reported_max_dd}%, "
                f"calculated {actual_max_dd}% (diff: {difference}%)",
                details={
                    "reported_max_dd": float(reported_max_dd),
                    "actual_max_dd": float(actual_max_dd),
                    "difference": float(difference),
                },
            )

        return True

    def validate_drawdown_range(
        self,
        drawdown_pct: Decimal,
    ) -> bool:
        """
        Validate drawdown is within acceptable range.

        Args:
            drawdown_pct: Drawdown percentage (should be negative or zero)

        Returns:
            True if within range

        Raises:
            DrawdownValidationError: If outside range
        """
        if drawdown_pct > self.min_drawdown_pct:
            raise DrawdownValidationError(
                f"Drawdown is positive: {drawdown_pct}% (should be <= 0%)",
                details={"drawdown_pct": float(drawdown_pct)},
            )

        if drawdown_pct < -self.max_drawdown_pct:
            raise DrawdownValidationError(
                f"Drawdown exceeds maximum: {drawdown_pct}% "
                f"(max: {-self.max_drawdown_pct}%)",
                details={
                    "drawdown_pct": float(drawdown_pct),
                    "max_allowed": float(-self.max_drawdown_pct),
                },
            )

        return True

    def validate_drawdown_recovery(
        self,
        equity_curve: List[Tuple[str, Decimal]],
    ) -> bool:
        """
        Validate drawdown recovery is tracked correctly.

        Checks that after each drawdown, the equity eventually
        recovers to a new peak or ends appropriately.

        Args:
            equity_curve: List of (timestamp, equity_value) tuples

        Returns:
            True if recovery is valid

        Raises:
            DrawdownValidationError: If recovery tracking is wrong
        """
        if len(equity_curve) < 2:
            return True

        peaks = []
        peak = equity_curve[0][1]

        # Find all peaks
        for timestamp, equity in equity_curve:
            if equity > peak:
                peak = equity
                peaks.append((timestamp, peak))

        # Check that we have reasonable peak progression
        if len(peaks) > 1:
            # Each peak should be higher than the last (or there was a drawdown)
            for i in range(1, len(peaks)):
                if peaks[i][1] < peaks[i-1][1]:
                    raise DrawdownValidationError(
                        f"Peak decreased without tracking: "
                        f"{peaks[i-1][1]} -> {peaks[i][1]}",
                        details={
                            "previous_peak": float(peaks[i-1][1]),
                            "current_peak": float(peaks[i][1]),
                        },
                    )

        return True

    def get_drawdown_statistics(
        self,
        trades: List[Trade],
        initial_capital: Decimal,
    ) -> Dict[str, any]:
        """
        Get comprehensive drawdown statistics.

        Args:
            trades: List of trades
            initial_capital: Starting capital

        Returns:
            Dictionary with drawdown statistics
        """
        equity_curve = self.calculate_equity_curve(trades, initial_capital)
        drawdowns, max_dd = self.calculate_drawdown(equity_curve)

        # Calculate average drawdown
        negative_drawdowns = [dd for _, dd in drawdowns if dd < 0]
        avg_dd = np.mean(negative_drawdowns) if negative_drawdowns else Decimal("0")

        # Count drawdown periods
        in_drawdown = False
        drawdown_periods = 0
        for _, dd in drawdowns:
            if dd < -1:  # More than 1% drawdown
                if not in_drawdown:
                    drawdown_periods += 1
                    in_drawdown = True
            else:
                in_drawdown = False

        return {
            "max_drawdown_pct": float(max_dd),
            "avg_drawdown_pct": float(avg_dd),
            "drawdown_periods": drawdown_periods,
            "current_drawdown": float(drawdowns[-1][1]) if drawdowns else 0.0,
            "equity_low": float(min(eq for _, eq in equity_curve)),
            "equity_high": float(max(eq for _, eq in equity_curve)),
        }
