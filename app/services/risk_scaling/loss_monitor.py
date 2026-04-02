"""
PHASE 3: Loss Monitor - Consecutive Loss Detection & Reduction

Tracks consecutive losses and applies position reduction scaling.
Each additional loss reduces position size until 3+ wins reset the streak.

Logic:
- 0 consecutive losses → scale = 1.0x
- 1 loss → scale = 0.9x (10% reduction)
- 2 losses → scale = 0.8x (20% reduction)
- 3 losses → scale = 0.6x (40% reduction)
- 4+ losses → scale = 0.5x (50% reduction, max reduction)

Reset: When 3+ winning trades occur in a row

Uses centralized configuration for all thresholds and scaling factors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Result of a single trade."""

    trade_id: str
    timestamp: datetime
    pnl: Decimal  # Profit/loss (positive = win, negative = loss)
    symbol: str
    side: str  # buy/sell
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal

    def is_winning(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl > Decimal("0")

    def is_losing(self) -> bool:
        """Check if trade was a loss."""
        return self.pnl < Decimal("0")


class LossMonitor:
    """
    Tracks consecutive losses and applies reduction in position sizing.

    Usage:
        monitor = LossMonitor()
        consecutive_losses = monitor.detect_consecutive_losses(trade_results)
        scale = monitor.calculate_loss_scale(consecutive_losses)
        should_reset = monitor.should_reset_loss_counter(trade_results)
    """

    def __init__(self, reset_threshold: int | None = None):
        """
        Initialize loss monitor.

        Args:
            reset_threshold: Number of wins needed to reset loss counter (uses centralized config if None)
        """
        # Use centralized config for reset_threshold if not provided
        if reset_threshold is None:
            tt = get_config().trading_thresholds
            reset_threshold = tt.loss_monitor_reset_threshold
        self.reset_threshold = reset_threshold
        self.consecutive_loss_count = 0
        self.consecutive_win_count = 0
        self.trade_history: list[TradeResult] = []

    def detect_consecutive_losses(
        self,
        trade_results: list[TradeResult],
        window_days: int | None = None,
    ) -> int:
        """
        Count consecutive losing trades from most recent backwards.

        Stops counting when a winning trade is encountered.

        Args:
            trade_results: List of trade results (should be chronologically ordered)
            window_days: Optional lookback window in days

        Returns:
            Number of consecutive losses
        """
        if not trade_results:
            return 0

        # Filter by window if specified
        if window_days is not None:
            cutoff = datetime.now() - __import__("datetime").timedelta(days=window_days)
            filtered = [t for t in trade_results if t.timestamp >= cutoff]
        else:
            filtered = trade_results

        if not filtered:
            return 0

        # Count backwards from most recent
        consecutive_losses = 0
        for trade in reversed(filtered):
            if trade.is_losing():
                consecutive_losses += 1
            else:
                # First winning trade breaks the streak
                break

        self.consecutive_loss_count = consecutive_losses
        self.trade_history = filtered

        logger.debug(f"Detected {consecutive_losses} consecutive losses")

        return consecutive_losses

    def calculate_loss_scale(
        self,
        consecutive_losses: int,
    ) -> Decimal:
        """
        Return position sizing scale based on loss streak.

        Mapping (from centralized config):
        - 0 losses: 1.0x
        - 1 loss: scale_1_loss (default 0.9x = 10% reduction)
        - 2 losses: scale_2_losses (default 0.8x = 20% reduction)
        - 3 losses: scale_3_losses (default 0.6x = 40% reduction)
        - 4+ losses: scale_max_reduction (default 0.5x = 50% reduction, maximum)

        Args:
            consecutive_losses: Count of consecutive losing trades

        Returns:
            Scaling factor (0.5 to 1.0), quantized to 2 decimals
        """
        # Get scales from centralized config
        tt = get_config().trading_thresholds
        scale_1 = Decimal(str(tt.loss_monitor_scale_1_loss))
        scale_2 = Decimal(str(tt.loss_monitor_scale_2_losses))
        scale_3 = Decimal(str(tt.loss_monitor_scale_3_losses))
        scale_max = Decimal(str(tt.loss_monitor_scale_max_reduction))

        if consecutive_losses <= 0:
            scale = Decimal("1.0")
        elif consecutive_losses == 1:
            scale = scale_1
        elif consecutive_losses == 2:
            scale = scale_2
        elif consecutive_losses == 3:
            scale = scale_3
        else:
            # 4+ losses: max reduction
            scale = scale_max

        return scale.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def should_reset_loss_counter(
        self,
        trade_results: list[TradeResult],
        lookback_trades: int | None = None,
    ) -> bool:
        """
        Check if loss streak should reset.

        Resets when reset_threshold consecutive winning trades occur.

        Args:
            trade_results: List of trade results
            lookback_trades: How many recent trades to examine (uses centralized config if None)

        Returns:
            True if reset condition met
        """
        # Use centralized config for lookback_trades if not provided
        if lookback_trades is None:
            tt = get_config().trading_thresholds
            lookback_trades = tt.loss_monitor_lookback_trades
        if not trade_results:
            return False

        # Get recent trades
        recent = (
            trade_results[-lookback_trades:]
            if len(trade_results) >= lookback_trades
            else trade_results
        )

        # Count consecutive wins from the end
        consecutive_wins = 0
        for trade in reversed(recent):
            if trade.is_winning():
                consecutive_wins += 1
            else:
                break

        should_reset = consecutive_wins >= self.reset_threshold

        if should_reset:
            logger.info(
                "Loss counter reset condition met: "
                f"{consecutive_wins} consecutive wins >= {self.reset_threshold}"
            )
            self.consecutive_loss_count = 0
            self.consecutive_win_count = consecutive_wins

        return should_reset

    def get_loss_streak_info(self) -> dict:
        """
        Get detailed information about current loss streak.

        Returns:
            Dictionary with loss streak details
        """
        return {
            "consecutive_losses": self.consecutive_loss_count,
            "consecutive_wins": self.consecutive_win_count,
            "reset_threshold": self.reset_threshold,
            "scaling_factor": self.calculate_loss_scale(self.consecutive_loss_count),
            "will_reset_next": (
                self.consecutive_win_count >= self.reset_threshold
                if self.consecutive_win_count > 0
                else False
            ),
        }

    def calculate_win_rate(
        self,
        trade_results: list[TradeResult],
        window_trades: int | None = None,
    ) -> Decimal:
        """
        Calculate win rate from recent trades.

        Args:
            trade_results: List of trade results
            window_trades: Number of recent trades to consider (uses centralized config if None)

        Returns:
            Win rate as percentage (0-100)
        """
        # Use centralized config for window_trades if not provided
        if window_trades is None:
            tt = get_config().trading_thresholds
            window_trades = tt.loss_monitor_window_trades
        if not trade_results:
            return Decimal("0")

        recent = (
            trade_results[-window_trades:] if len(trade_results) >= window_trades else trade_results
        )
        wins = sum(1 for t in recent if t.is_winning())
        win_rate = (Decimal(wins) / Decimal(len(recent))) * Decimal("100")

        return win_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_average_win_loss_ratio(
        self,
        trade_results: list[TradeResult],
        window_trades: int | None = None,
    ) -> Decimal | None:
        """
        Calculate average win size vs average loss size.

        Ratio > 1.0 is favorable (average wins > average losses).

        Args:
            trade_results: List of trade results
            window_trades: Number of recent trades (uses centralized config if None)

        Returns:
            Win/Loss ratio or None if insufficient data
        """
        # Use centralized config for window_trades if not provided
        if window_trades is None:
            tt = get_config().trading_thresholds
            window_trades = tt.loss_monitor_window_trades
        if not trade_results:
            return None

        recent = (
            trade_results[-window_trades:] if len(trade_results) >= window_trades else trade_results
        )

        wins = [t.pnl for t in recent if t.is_winning()]
        losses = [abs(t.pnl) for t in recent if t.is_losing()]

        if not wins or not losses:
            return None

        avg_win = sum(wins) / Decimal(len(wins))
        avg_loss = sum(losses) / Decimal(len(losses))

        if avg_loss == Decimal("0"):
            return None

        ratio = avg_win / avg_loss
        return ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def suggest_position_adjustment(
        self,
        consecutive_losses: int,
        win_rate: Decimal,
    ) -> tuple[Decimal, str]:
        """
        Suggest position size adjustment based on loss streak and win rate.

        Args:
            consecutive_losses: Current loss streak
            win_rate: Recent win rate (0-100)

        Returns:
            Tuple of (suggested_scale, recommendation)
        """
        loss_scale = self.calculate_loss_scale(consecutive_losses)

        if consecutive_losses >= 4:
            recommendation = (
                f"CRITICAL: {consecutive_losses} consecutive losses detected. "
                f"Reduce positions to 50% ({loss_scale:.2f}x). Consider review of strategy."
            )
        elif consecutive_losses >= 3:
            recommendation = (
                f"WARNING: {consecutive_losses} consecutive losses. "
                f"Reduce positions to 60% ({loss_scale:.2f}x)."
            )
        elif consecutive_losses >= 2:
            recommendation = (
                f"CAUTION: {consecutive_losses} consecutive losses. "
                f"Reduce positions to 80% ({loss_scale:.2f}x)."
            )
        elif consecutive_losses == 1:
            recommendation = (
                f"Note: 1 loss detected. Slight reduction to 90% ({loss_scale:.2f}x). "
                f"Current win rate: {win_rate:.1f}%"
            )
        else:
            recommendation = (
                f"No loss streak. Maintain normal sizing (1.0x). Win rate: {win_rate:.1f}%"
            )

        return loss_scale, recommendation

    def detect_performance_transition(
        self,
        trade_results: list[TradeResult],
        early_window: int = 10,
        recent_window: int = 10,
    ) -> tuple[bool, str]:
        """
        Detect if performance has changed between two periods.

        Args:
            trade_results: List of trades
            early_window: Trades to examine for early period
            recent_window: Trades to examine for recent period

        Returns:
            Tuple of (transition_detected, description)
        """
        if len(trade_results) < early_window + recent_window:
            return False, "Insufficient trade history"

        # Get early and recent periods
        early = trade_results[-early_window - recent_window : -recent_window]
        recent = trade_results[-recent_window:]

        early_wins = sum(1 for t in early if t.is_winning())
        recent_wins = sum(1 for t in recent if t.is_winning())

        early_rate = Decimal(early_wins) / Decimal(len(early))
        recent_rate = Decimal(recent_wins) / Decimal(len(recent))

        # Significant change if >20% difference in win rates
        change = abs(recent_rate - early_rate)
        is_significant = change > Decimal("0.2")

        if is_significant:
            if recent_rate > early_rate:
                desc = f"Performance IMPROVING: {early_rate:.0%} → {recent_rate:.0%}"
            else:
                desc = f"Performance DETERIORATING: {early_rate:.0%} → {recent_rate:.0%}"
        else:
            desc = f"Performance stable: {recent_rate:.0%}"

        return is_significant, desc
