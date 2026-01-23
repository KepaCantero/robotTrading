import logging

logger = logging.getLogger(__name__)
"""
Position Sizing Engine with ATR-Based Dynamic Stop Loss.

TASK-IND-2: Implements dynamic stop loss based on ATR (Average True Range).
Uses ATR * 2 as default multiplier for adaptive stop loss that adjusts to volatility.
"""

from decimal import Decimal  # noqa: E402
from typing import Optional  # noqa: E402


class PositionSizingEngine:
    """
    TASK-IND-2, IND-4: Calculates dynamic stop loss and position sizing based on ATR.

    Stop Loss Formula: stop_loss_distance = ATR * multiplier
    Default multiplier: 2.0 (2x ATR)
    Position Sizing: risk_per_trade = 2% capital / (ATR * 2)
    """

    def __init__(self, atr_multiplier: float = 2.0):
        """
        Initialize calculator.

        Args:
            atr_multiplier: Multiplier for ATR (default 2.0 = 2x ATR)
        """
        self.atr_multiplier = Decimal(str(atr_multiplier))

    def calculate_stop_loss_price(
        self,
        entry_price: Decimal,
        direction: str,
        atr: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        TASK-IND-2: Calculate dynamic stop loss price.

        Priority:
        1. If ATR available: use ATR * multiplier (adaptive to volatility)
        2. If stop_loss_pct provided: use percentage-based stop
        3. Return None if neither available

        Args:
            entry_price: Entry price of the trade
            direction: 'buy' or 'sell'
            atr: Average True Range value
            stop_loss_pct: Stop loss percentage (fallback)

        Returns:
            Stop loss price or None
        """
        if not entry_price or entry_price <= 0:
            return None

        # TASK-IND-2: Use ATR-based dynamic stop if available
        if atr is not None:
            atr_value = Decimal(str(atr))
            stop_distance = atr_value * self.atr_multiplier

            if direction == "buy":
                return entry_price - stop_distance
            elif direction == "sell":
                return entry_price + stop_distance

        # Fallback: Use percentage-based stop loss
        if stop_loss_pct is not None:
            stop_pct = Decimal(str(stop_loss_pct))

            if direction == "buy":
                return entry_price * (Decimal("1") - stop_pct)
            elif direction == "sell":
                return entry_price * (Decimal("1") + stop_pct)

        return None

    def calculate_position_size_from_atr(
        self,
        capital: Decimal,
        risk_per_trade_pct: float,
        entry_price: Decimal,
        atr: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        TASK-IND-4: Calculate position size based on ATR.

        Formula: risk_per_trade = 2% capital / (ATR * 2)
        This ensures consistent risk across different volatility levels.

        Args:
            capital: Total capital available
            risk_per_trade_pct: Risk per trade as percentage (default 2%)
            entry_price: Entry price for the position
            atr: Average True Range

        Returns:
            Position size in shares or None
        """
        if not capital or capital <= 0 or not entry_price or entry_price <= 0:
            return None

        # Calculate risk amount in dollars
        risk_amount = capital * Decimal(str(risk_per_trade_pct)) / Decimal("100")

        # TASK-IND-4: Use ATR-based stop distance if available
        if atr is not None and atr > 0:
            stop_distance = Decimal(str(atr)) * self.atr_multiplier

            # CRITICAL VALIDATION: Ensure stop distance is reasonable vs entry price
            # Stop distance should not exceed 20% of entry price (sanity check)
            max_stop_pct = Decimal("0.20")
            max_stop_distance = entry_price * max_stop_pct

            if stop_distance > max_stop_distance:
                logger.warning(
                    f"ATR stop distance {stop_distance} exceeds 20% of price {entry_price}, "
                    f"capping at {max_stop_distance}"
                )
                stop_distance = max_stop_distance

            if stop_distance > 0:
                # Calculate shares: risk_amount / stop_distance_per_share
                # This gives us how many shares we can buy where losing stop_distance per share
                # equals our total risk amount
                shares = risk_amount / stop_distance

                # Verify result makes sense
                position_value = shares * entry_price
                if position_value > capital:
                    # Cap at available capital
                    shares = capital / entry_price
                    logger.debug(f"Position size capped at available capital: {shares} shares")

                return shares

        # Fallback: Use fixed percentage stop (e.g., 5%)
        default_stop_pct = Decimal("0.05")
        stop_distance = entry_price * default_stop_pct

        if stop_distance > 0:
            shares = risk_amount / stop_distance
            return shares

        return None
