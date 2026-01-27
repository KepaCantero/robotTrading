import logging

logger = logging.getLogger(__name__)
"""
Position Sizing Engine with ATR-Based Dynamic Stop Loss.

TASK-IND-2: Implements dynamic stop loss based on ATR (Average True Range).
Uses ATR * 2 as default multiplier for adaptive stop loss that adjusts to volatility.

Configuration:
This module now uses centralized configuration from config/risk_management.yaml:
- ATR multipliers (1.0, 2.0, 3.0) are loaded from config
- Position sizing percentages are loaded from config
- Risk per trade percentages are loaded from config
"""

from decimal import Decimal  # noqa: E402
from typing import Optional  # noqa: E402

# Import centralized configuration
try:
    from app.core.config.strategy_config_loader import get_strategy_config
    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


class PositionSizingEngine:
    """
    TASK-IND-2, IND-4: Calculates dynamic stop loss and position sizing based on ATR.

    Stop Loss Formula: stop_loss_distance = ATR * multiplier
    Default multiplier: 2.0 (2x ATR) - loaded from config
    Position Sizing: risk_per_trade = 2% capital / (ATR * 2)
    """

    def __init__(self, atr_multiplier: Optional[float] = None):
        """
        Initialize calculator.

        Args:
            atr_multiplier: Multiplier for ATR (default loaded from config, typically 2.0)
        """
        if atr_multiplier is None and HAS_CONFIG_LOADER:
            strategy_config = get_strategy_config()
            atr_multiplier = strategy_config.get_atr_multiplier('default_stop')
        elif atr_multiplier is None:
            atr_multiplier = 2.0

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
        risk_per_trade_pct: Optional[float] = None,
        entry_price: Decimal = None,
        atr: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        TASK-IND-4: Calculate position size based on ATR.

        Formula: risk_per_trade = 2% capital / (ATR * 2)
        This ensures consistent risk across different volatility levels.

        Args:
            capital: Total capital available
            risk_per_trade_pct: Risk per trade as percentage (loaded from config if None)
            entry_price: Entry price for the position
            atr: Average True Range

        Returns:
            Position size in shares or None
        """
        if not capital or capital <= 0 or not entry_price or entry_price <= 0:
            return None

        # Load default risk per trade from config if not provided
        if risk_per_trade_pct is None:
            if HAS_CONFIG_LOADER:
                strategy_config = get_strategy_config()
                risk_config = strategy_config.get_risk_config()
                risk_per_trade_pct = float(risk_config.get('risk_per_trade', {}).get('default', 0.02))
            else:
                risk_per_trade_pct = 0.02  # Default 2% risk per trade

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
