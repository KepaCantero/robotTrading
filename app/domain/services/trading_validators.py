"""
Trading validators to prevent financial disasters.

This module provides validation functions to ensure trading operations
are safe and comply with risk management rules.

Uses centralized configuration for all thresholds and parameters.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class TradingValidator:
    """
    Validates trading operations to prevent catastrophic losses.

    This validator enforces critical safety rules:
    - Position size limits relative to capital
    - Mandatory stop-loss requirements
    - Maximum exposure limits
    """

    @staticmethod
    def validate_position_size(
        capital: Decimal,
        position_size: Decimal,
        max_position_percent: Decimal | None = None,
    ) -> bool:
        """
        Validate that position size doesn't exceed available capital.

        This is a CRITICAL safety check to prevent:
        - Over-leveraging beyond available capital
        - Single-position exposure that could wipe out the account
        - Accidentally trading with more money than available

        Args:
            capital: Available capital (must be positive)
            position_size: Requested position size (must be positive)
            max_position_percent: Maximum position as % of capital (default 25%)

        Returns:
            True if valid

        Raises:
            ValueError: If position size is invalid or exceeds safety limits
        """
        # Validate inputs
        if capital <= 0:
            raise ValueError(
                f"Capital must be positive for trading, got {capital}. "
                "Trading with zero or negative capital is not allowed."
            )

        if position_size <= 0:
            raise ValueError(
                f"Position size must be positive, got {position_size}. "
                "Position size cannot be zero or negative."
            )

        # Get thresholds from centralized config
        tt = get_config().trading_thresholds
        default_max_position_pct = Decimal(str(tt.validator_default_max_position_pct))
        min_position_pct = Decimal(str(tt.validator_min_position_pct))
        max_position_limit_pct = Decimal(str(tt.validator_max_position_pct))

        # Default: max position % from centralized config
        if max_position_percent is None:
            max_position_percent = default_max_position_pct

        # Validate max_position_percent is reasonable
        if not (min_position_pct <= max_position_percent <= max_position_limit_pct):
            raise ValueError(
                f"max_position_percent must be between {min_position_pct * 100:.1f}% and {max_position_limit_pct * 100:.1f}%, got {max_position_percent * 100:.1f}%"
            )

        max_position = capital * max_position_percent

        # CRITICAL: Check if position size exceeds maximum allowed
        if position_size > max_position:
            raise ValueError(
                f"Position size ${position_size:.2f} exceeds maximum "
                f"allowed ${max_position:.2f} ({max_position_percent * 100:.1f}% of capital). "
                f"This risk limit is in place to prevent catastrophic losses. "
                f"Available capital: ${capital:.2f}"
            )

        # CRITICAL: Check if position size exceeds available capital
        if position_size > capital:
            raise ValueError(
                f"Position size ${position_size:.2f} exceeds "
                f"available capital ${capital:.2f}. "
                "Cannot trade with more capital than available."
            )

        logger.debug(
            f"Position size validation passed: ${position_size:.2f} / ${capital:.2f} "
            f"({position_size / capital * 100:.1f}% of capital, max {max_position_percent * 100:.1f}%)"
        )

        return True

    @staticmethod
    def validate_stop_loss(
        entry_price: Decimal,
        stop_loss: Decimal | None,
        side: str = "long",
    ) -> bool:
        """
        Validate that stop-loss is properly defined and positioned.

        STOP-LOSS IS MANDATORY for all trades to prevent unlimited losses.
        Trading without stop-loss is prohibited for safety reasons.

        Args:
            entry_price: Entry price (must be positive)
            stop_loss: Stop loss price (must be defined)
            side: "long" or "short"

        Returns:
            True if valid

        Raises:
            ValueError: If stop-loss is missing or improperly positioned
        """
        # Validate entry price
        if entry_price <= 0:
            raise ValueError(
                f"Entry price must be positive, got {entry_price}. "
                "Cannot enter a position with zero or negative price."
            )

        # CRITICAL: Stop-loss is REQUIRED
        if stop_loss is None:
            raise ValueError(
                "Stop-loss is REQUIRED for all trades. "
                "Trading without stop-loss is prohibited. "
                "Set a stop-loss price to limit potential losses."
            )

        # Validate stop-loss price
        if stop_loss <= 0:
            raise ValueError(
                f"Stop-loss price must be positive, got {stop_loss}. "
                "Stop-loss cannot be zero or negative."
            )

        # Validate stop-loss positioning based on trade side
        side_lower = side.lower()

        if side_lower == "long":
            # For long positions, stop-loss must be BELOW entry price
            if stop_loss >= entry_price:
                raise ValueError(
                    f"Long position stop-loss (${stop_loss:.2f}) "
                    f"must be BELOW entry price (${entry_price:.2f}). "
                    f"Current stop-loss is ${abs(stop_loss - entry_price):.2f} above entry. "
                    "For long positions, stop-loss limits downside risk."
                )

            # Check if stop-loss is too far (more than configured threshold)
            tt = get_config().trading_thresholds
            stop_loss_warning_pct = Decimal(str(tt.validator_stop_loss_warning_pct))
            loss_percent = (entry_price - stop_loss) / entry_price
            if loss_percent > stop_loss_warning_pct:
                logger.warning(
                    f"Stop-loss for long position is {loss_percent * 100:.1f}% away from entry. "
                    f"Entry: ${entry_price:.2f}, Stop: ${stop_loss:.2f}. "
                    "This is a very wide stop-loss. Consider a tighter risk limit."
                )

        elif side_lower == "short":
            # For short positions, stop-loss must be ABOVE entry price
            if stop_loss <= entry_price:
                raise ValueError(
                    f"Short position stop-loss (${stop_loss:.2f}) "
                    f"must be ABOVE entry price (${entry_price:.2f}). "
                    f"Current stop-loss is ${abs(entry_price - stop_loss):.2f} below entry. "
                    "For short positions, stop-loss limits upside risk."
                )

            # Check if stop-loss is too far (more than configured threshold)
            tt = get_config().trading_thresholds
            stop_loss_warning_pct = Decimal(str(tt.validator_stop_loss_warning_pct))
            loss_percent = (stop_loss - entry_price) / entry_price
            if loss_percent > stop_loss_warning_pct:
                logger.warning(
                    f"Stop-loss for short position is {loss_percent * 100:.1f}% away from entry. "
                    f"Entry: ${entry_price:.2f}, Stop: ${stop_loss:.2f}. "
                    "This is a very wide stop-loss. Consider a tighter risk limit."
                )

        else:
            raise ValueError(f"Invalid trade side: '{side}'. Must be 'long' or 'short'.")

        logger.debug(
            f"Stop-loss validation passed: {side} position @ ${entry_price:.2f}, "
            f"stop-loss @ ${stop_loss:.2f}"
        )

        return True

    @staticmethod
    def validate_trade_risk_reward(
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal | None = None,
        min_reward_risk_ratio: Decimal | None = None,
    ) -> bool:
        """
        Validate that the trade has a favorable risk-reward ratio.

        This ensures that potential profits justify the risk taken.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional)
            min_reward_risk_ratio: Minimum acceptable reward/risk ratio (uses centralized config if None)

        Returns:
            True if valid

        Raises:
            ValueError: If risk-reward ratio is unfavorable
        """
        # Get default from centralized config if not provided
        if min_reward_risk_ratio is None:
            tt = get_config().trading_thresholds
            min_reward_risk_ratio = Decimal(str(tt.validator_min_reward_risk_ratio))

        if stop_loss is None:
            raise ValueError("Stop-loss is required for risk-reward calculation")

        if entry_price <= 0 or stop_loss <= 0:
            raise ValueError("Entry price and stop-loss must be positive")

        # Calculate risk (distance to stop-loss)
        risk = abs(entry_price - stop_loss)

        if take_profit is not None:
            if take_profit <= 0:
                raise ValueError("Take-profit price must be positive")

            # Calculate reward (distance to take-profit)
            reward = abs(take_profit - entry_price)

            # Calculate reward/risk ratio
            if risk > 0:
                reward_risk_ratio = reward / risk

                if reward_risk_ratio < min_reward_risk_ratio:
                    raise ValueError(
                        f"Reward/risk ratio ({reward_risk_ratio:.2f}) is below minimum "
                        f"({min_reward_risk_ratio:.2f}). Risk: ${risk:.2f}, Reward: ${reward:.2f}. "
                        "Only take trades where potential profit justifies the risk."
                    )

                logger.debug(
                    f"Risk-reward validation passed: ratio {reward_risk_ratio:.2f}, "
                    f"risk ${risk:.2f}, reward ${reward:.2f}"
                )
        else:
            # No take-profit set, skip validation
            logger.debug("No take-profit set, skipping reward/risk validation")

        return True

    @staticmethod
    def validate_trading_hours(
        current_time,
        allowed_hours: set | None = None,
    ) -> bool:
        """
        Validate that trading is allowed at the current time.

        This prevents trading during high-risk periods (e.g., overnight,
        during major news announcements, etc.)

        Args:
            current_time: Current datetime
            allowed_hours: Set of allowed hours (default: 9-16 for market hours)

        Returns:
            True if trading is allowed

        Raises:
            ValueError: If trading is not allowed at this time
        """
        if allowed_hours is None:
            # Default: Regular market hours (9 AM - 4 PM)
            allowed_hours = set(range(9, 17))  # 9:00 to 16:59

        current_hour = current_time.hour

        if current_hour not in allowed_hours:
            raise ValueError(
                f"Trading is not allowed at {current_hour}:00. "
                f"Allowed hours: {sorted(allowed_hours)}. "
                "Trading outside regular market hours carries additional risk."
            )

        logger.debug(f"Trading hours validation passed: {current_hour}:00 is allowed")

        return True
