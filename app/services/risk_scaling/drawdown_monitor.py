"""
PHASE 3: Drawdown Monitor - Capital Preservation via Circuit Breakers

Monitors maximum drawdown and applies circuit breaker logic.
Protects capital by halting trading if drawdown exceeds limits.

Logic:
- 0-5% drawdown → scale = 1.0x (normal)
- 5-10% drawdown → scale = 0.8x (caution)
- 10-15% drawdown → scale = 0.5x (warning)
- > 15% drawdown → scale = 0.0x (halt trading - circuit breaker)

Reset: When equity reaches new all-time high
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EquityPoint:
    """Single point in equity curve."""

    timestamp: datetime
    equity: Decimal  # Total account equity


class DrawdownMonitor:
    """
    Monitors maximum drawdown and applies circuit breaker protection.

    Usage:
        monitor = DrawdownMonitor()
        current_dd, max_dd = monitor.calculate_drawdown(equity_curve)
        scale = monitor.calculate_drawdown_scale(current_dd)
        should_halt = monitor.should_halt_trading(current_dd)
    """

    def __init__(self, max_drawdown_limit: Decimal = Decimal("0.15")):
        """
        Initialize drawdown monitor.

        Args:
            max_drawdown_limit: Maximum allowed drawdown before halting (default 15% = 0.15)
        """
        self.max_drawdown_limit = max_drawdown_limit
        self.peak_equity = Decimal("0")
        self.current_drawdown = Decimal("0")
        self.max_drawdown_recorded = Decimal("0")
        self.halt_triggered_at: Optional[datetime] = None

    def calculate_drawdown(
        self,
        equity_curve: List[Decimal],
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate current drawdown and maximum drawdown.

        Drawdown = (peak - current) / peak

        Args:
            equity_curve: List of equity values in chronological order

        Returns:
            Tuple of (current_drawdown, max_drawdown) as decimals (0-1)
        """
        if not equity_curve:
            return Decimal("0"), Decimal("0")

        # Find peak equity (running maximum)
        peak = equity_curve[0]
        max_dd = Decimal("0")
        current_peak = peak
        current_equity = equity_curve[-1]

        for equity in equity_curve:
            if equity > peak:
                peak = equity
                current_peak = peak
            else:
                # Calculate drawdown from this peak
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd

        # Current drawdown from peak
        if current_peak > Decimal("0"):
            current_dd = (current_peak - current_equity) / current_peak
        else:
            current_dd = Decimal("0")

        # Ensure non-negative
        current_dd = max(Decimal("0"), current_dd)
        max_dd = max(Decimal("0"), max_dd)

        # Store for later use
        self.current_drawdown = current_dd
        self.max_drawdown_recorded = max_dd
        self.peak_equity = current_peak

        return (
            current_dd.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            max_dd.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        )

    def calculate_drawdown_scale(
        self,
        current_drawdown: Decimal,
        max_drawdown_limit: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Return position sizing scale based on drawdown.

        Mapping:
        - 0-5% drawdown: 1.0x (normal)
        - 5-10% drawdown: 0.8x (caution)
        - 10-15% drawdown: 0.5x (warning)
        - >15% drawdown: 0.0x (halt)

        Args:
            current_drawdown: Current drawdown as decimal (0-1)
            max_drawdown_limit: Override limit for halt trigger

        Returns:
            Scaling factor (0.0 to 1.0), quantized to 2 decimals
        """
        if max_drawdown_limit is None:
            max_drawdown_limit = self.max_drawdown_limit

        if current_drawdown >= max_drawdown_limit:
            # Circuit breaker: halt trading
            return Decimal("0.0")
        elif current_drawdown >= Decimal("0.10"):
            # Warning: 10-15% drawdown
            return Decimal("0.5")
        elif current_drawdown >= Decimal("0.05"):
            # Caution: 5-10% drawdown
            return Decimal("0.8")
        else:
            # Normal: < 5% drawdown
            return Decimal("1.0")

    def should_halt_trading(
        self,
        current_drawdown: Decimal,
        halt_threshold: Optional[Decimal] = None,
    ) -> bool:
        """
        Check if should halt trading (circuit breaker activated).

        Args:
            current_drawdown: Current drawdown (0-1)
            halt_threshold: Drawdown threshold to trigger halt (default 15%)

        Returns:
            True if should halt trading
        """
        if halt_threshold is None:
            halt_threshold = self.max_drawdown_limit

        should_halt = current_drawdown >= halt_threshold

        if should_halt and self.halt_triggered_at is None:
            self.halt_triggered_at = datetime.now()
            logger.critical(
                f"CIRCUIT BREAKER ACTIVATED! Drawdown {current_drawdown:.1%} >= "
                f"halt threshold {halt_threshold:.1%}. Trading halted."
            )

        return should_halt

    def has_recovered(
        self,
        equity_curve: List[Decimal],
    ) -> bool:
        """
        Check if equity has recovered to new all-time high.

        Args:
            equity_curve: Current equity curve

        Returns:
            True if new ATH reached (drawdown reset)
        """
        if not equity_curve:
            return False

        current_dd, _ = self.calculate_drawdown(equity_curve)
        has_recovered = current_dd == Decimal("0")

        if has_recovered and self.halt_triggered_at is not None:
            recovery_time = datetime.now() - self.halt_triggered_at
            logger.info(
                "Recovery to all-time high achieved! "
                f"Recovery time: {recovery_time.total_seconds() / 3600:.1f} hours"
            )
            self.halt_triggered_at = None

        return has_recovered

    def get_drawdown_level(self, current_drawdown: Decimal) -> str:
        """
        Classify drawdown severity level.

        Args:
            current_drawdown: Current drawdown (0-1)

        Returns:
            Severity level string
        """
        if current_drawdown >= self.max_drawdown_limit:
            return "HALT"
        elif current_drawdown >= Decimal("0.10"):
            return "WARNING"
        elif current_drawdown >= Decimal("0.05"):
            return "CAUTION"
        else:
            return "NORMAL"

    def get_drawdown_timeline(
        self,
        equity_curve: List[EquityPoint],
    ) -> dict:
        """
        Get detailed drawdown timeline information.

        Args:
            equity_curve: List of EquityPoint with timestamps

        Returns:
            Dictionary with drawdown timeline details
        """
        if not equity_curve:
            return {}

        # Extract just equity values for calculation
        equities = [ep.equity for ep in equity_curve]
        current_dd, max_dd = self.calculate_drawdown(equities)

        # Find when max drawdown occurred
        peak = equities[0]
        max_dd_value = Decimal("0")
        max_dd_index = 0

        for i, equity in enumerate(equities):
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd_value:
                max_dd_value = dd
                max_dd_index = i

        return {
            "current_drawdown": float(current_dd),
            "current_drawdown_pct": f"{float(current_dd):.1%}",
            "max_drawdown": float(max_dd),
            "max_drawdown_pct": f"{float(max_dd):.1%}",
            "peak_equity": float(self.peak_equity),
            "current_equity": float(equities[-1]),
            "max_dd_occurred_at": (
                equity_curve[max_dd_index].timestamp.isoformat()
                if max_dd_index < len(equity_curve)
                else None
            ),
            "time_to_recover": None,  # Would be calculated if recovery data available
            "halt_threshold": f"{float(self.max_drawdown_limit):.1%}",
            "is_halted": self.should_halt_trading(current_dd),
        }

    def calculate_underwater_duration(
        self,
        equity_curve: List[EquityPoint],
    ) -> dict:
        """
        Calculate how long equity has been underwater (below previous peak).

        Args:
            equity_curve: List of EquityPoint objects

        Returns:
            Dictionary with underwater duration stats
        """
        if len(equity_curve) < 2:
            return {"current_underwater_days": 0, "max_underwater_days": 0}

        underwater_periods = []
        peak = equity_curve[0].equity
        underwater_start = None

        for ep in equity_curve:
            if ep.equity > peak:
                if underwater_start is not None:
                    underwater_duration = (ep.timestamp - underwater_start).days
                    underwater_periods.append(underwater_duration)
                peak = ep.equity
                underwater_start = None
            else:
                if underwater_start is None:
                    underwater_start = ep.timestamp

        # Current underwater duration
        if underwater_start is not None:
            current_underwater = (equity_curve[-1].timestamp - underwater_start).days
        else:
            current_underwater = 0

        return {
            "current_underwater_days": current_underwater,
            "avg_underwater_days": (
                sum(underwater_periods) / len(underwater_periods) if underwater_periods else 0
            ),
            "max_underwater_days": max(underwater_periods) if underwater_periods else 0,
            "num_underwater_periods": len(underwater_periods),
        }

    def suggest_drawdown_action(
        self,
        current_drawdown: Decimal,
    ) -> Tuple[str, str]:
        """
        Suggest action based on current drawdown.

        Args:
            current_drawdown: Current drawdown (0-1)

        Returns:
            Tuple of (action_level, description)
        """
        level = self.get_drawdown_level(current_drawdown)

        if level == "HALT":
            action = "STOP"
            desc = (
                f"Current drawdown {current_drawdown:.1%} >= halt threshold "
                f"{self.max_drawdown_limit:.1%}. HALT ALL TRADING immediately."
            )
        elif level == "WARNING":
            action = "REDUCE_50"
            desc = (
                f"Drawdown at {current_drawdown:.1%}. Reduce positions to 50% "
                "of normal sizing. Monitor closely."
            )
        elif level == "CAUTION":
            action = "REDUCE_20"
            desc = (
                f"Drawdown at {current_drawdown:.1%}. Reduce positions to 80% " f"of normal sizing."
            )
        else:
            action = "NORMAL"
            desc = f"Drawdown at {current_drawdown:.1%}. Normal trading mode."

        return action, desc
