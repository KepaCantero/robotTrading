"""
T8.1.2: LimitAdjuster - Adjust trading limits dynamically

Manages stop losses, margin requirements, position limits, and daily loss limits
based on market conditions and portfolio state.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Tuple

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


def _get_config_limit(attr_name: str, default_value: float) -> Decimal:
    """
    Get limit value from config with fallback default.

    Args:
        attr_name: Config attribute name
        default_value: Default value if config attribute not found

    Returns:
        Decimal value from config or default
    """
    try:
        config = get_config()
        value = float(getattr(config.trading, attr_name, default_value))
        return Decimal(str(value))
    except (AttributeError, ValueError, TypeError) as e:
        logger.warning(f"Error getting config limit '{attr_name}': {e}, using default {default_value}")
        return Decimal(str(default_value))


@dataclass
class TradingLimits:
    """Trading limits for a position/portfolio."""

    stop_loss_pct: Decimal  # Stop loss as % (e.g., 0.02 = 2%)
    daily_loss_limit: Decimal  # Daily max loss in € or %
    max_position_size: Decimal  # Max size for single position (€)
    max_portfolio_leverage: Decimal  # Max leverage for portfolio
    min_margin_requirement: Decimal  # Minimum margin (e.g., 0.25 = 25%)
    max_drawdown_limit: Decimal  # Portfolio max drawdown before halt


class LimitAdjuster:
    """
    Adjusts trading limits based on:
    - Current market volatility
    - Portfolio drawdown status
    - Risk scaling state
    - Account tier and capital availability

    Core Principles:
    - Tighter limits when market/portfolio stress high
    - Looser limits when conditions favorable
    - Hard stops to prevent catastrophic loss

    All configurable values are loaded from the centralized config system.
    """

    def __init__(self):
        """Initialize limit adjuster."""
        logger.info("✅ LimitAdjuster initialized")

    def _get_tier_limits(self, tier: str) -> Dict[str, Decimal]:
        """
        Get default limits for a capital tier from config.

        Args:
            tier: Capital tier (micro/small/medium/large)

        Returns:
            Dict with limit values for the tier
        """
        tier = tier.lower()
        if tier == "micro":
            return {
                "stop_loss_pct": _get_config_limit("limit_micro_stop_loss_pct", 0.02),
                "daily_loss_limit_pct": _get_config_limit("limit_micro_daily_loss_limit_pct", 0.05),
                "max_position_pct": _get_config_limit("limit_micro_max_position_pct", 0.10),
                "leverage": _get_config_limit("limit_micro_leverage", 1.0),
                "margin_requirement": _get_config_limit("limit_micro_margin_requirement", 0.50),
                "max_drawdown_pct": _get_config_limit("limit_micro_max_drawdown_pct", 0.10),
            }
        elif tier == "small":
            return {
                "stop_loss_pct": _get_config_limit("limit_small_stop_loss_pct", 0.025),
                "daily_loss_limit_pct": _get_config_limit("limit_small_daily_loss_limit_pct", 0.08),
                "max_position_pct": _get_config_limit("limit_small_max_position_pct", 0.15),
                "leverage": _get_config_limit("limit_small_leverage", 1.0),
                "margin_requirement": _get_config_limit("limit_small_margin_requirement", 0.33),
                "max_drawdown_pct": _get_config_limit("limit_small_max_drawdown_pct", 0.15),
            }
        elif tier == "medium":
            return {
                "stop_loss_pct": _get_config_limit("limit_medium_stop_loss_pct", 0.03),
                "daily_loss_limit_pct": _get_config_limit("limit_medium_daily_loss_limit_pct", 0.10),
                "max_position_pct": _get_config_limit("limit_medium_max_position_pct", 0.20),
                "leverage": _get_config_limit("limit_medium_leverage", 1.5),
                "margin_requirement": _get_config_limit("limit_medium_margin_requirement", 0.25),
                "max_drawdown_pct": _get_config_limit("limit_medium_max_drawdown_pct", 0.20),
            }
        elif tier == "large":
            return {
                "stop_loss_pct": _get_config_limit("limit_large_stop_loss_pct", 0.035),
                "daily_loss_limit_pct": _get_config_limit("limit_large_daily_loss_limit_pct", 0.15),
                "max_position_pct": _get_config_limit("limit_large_max_position_pct", 0.25),
                "leverage": _get_config_limit("limit_large_leverage", 2.0),
                "margin_requirement": _get_config_limit("limit_large_margin_requirement", 0.20),
                "max_drawdown_pct": _get_config_limit("limit_large_max_drawdown_pct", 0.25),
            }
        else:
            # Default to medium tier for unknown tiers
            return self._get_tier_limits("medium")

    def _get_volatility_multipliers(self) -> Dict[str, Decimal]:
        """
        Get volatility multipliers from config.

        Returns:
            Dict with multiplier values for each volatility state
        """
        return {
            "very_low": _get_config_limit("limit_vol_multiplier_very_low", 1.2),
            "low": _get_config_limit("limit_vol_multiplier_low", 1.1),
            "normal": _get_config_limit("limit_vol_multiplier_normal", 1.0),
            "high": _get_config_limit("limit_vol_multiplier_high", 0.8),
            "extreme": _get_config_limit("limit_vol_multiplier_extreme", 0.5),
        }

    def _get_drawdown_multipliers(self) -> Dict[str, Decimal]:
        """
        Get drawdown multipliers from config.

        Returns:
            Dict with multiplier values for each drawdown state
        """
        return {
            "healthy": _get_config_limit("limit_dd_multiplier_healthy", 1.0),
            "caution": _get_config_limit("limit_dd_multiplier_caution", 0.8),
            "warning": _get_config_limit("limit_dd_multiplier_warning", 0.6),
            "critical": _get_config_limit("limit_dd_multiplier_critical", 0.3),
            "halt": _get_config_limit("limit_dd_multiplier_halt", 0.0),
        }

    def get_base_limits(self, capital_tier: str) -> TradingLimits:
        """
        Get default limits for capital tier from config.

        Args:
            capital_tier: Capital tier (micro/small/medium/large)

        Returns:
            TradingLimits with configured values for the tier
        """
        defaults = self._get_tier_limits(capital_tier)

        return TradingLimits(
            stop_loss_pct=defaults["stop_loss_pct"],
            daily_loss_limit=defaults["daily_loss_limit_pct"],
            max_position_size=defaults["max_position_pct"],
            max_portfolio_leverage=defaults["leverage"],
            min_margin_requirement=defaults["margin_requirement"],
            max_drawdown_limit=defaults["max_drawdown_pct"],
        )

    def adjust_limits_for_volatility(
        self,
        base_limits: TradingLimits,
        current_volatility: Decimal,
        average_volatility: Decimal,
    ) -> Tuple[TradingLimits, str]:
        """
        Adjust limits based on current vs. average volatility.

        Args:
            base_limits: Starting limits
            current_volatility: Current market vol (e.g., ATR)
            average_volatility: Historical average vol

        Returns:
            (adjusted_limits, reason_string)
        """
        if average_volatility <= Decimal("0"):
            return base_limits, "Cannot calculate vol adjustment (avg_vol = 0)"

        vol_ratio = current_volatility / average_volatility

        # Get thresholds from config
        very_low_threshold = _get_config_limit("limit_vol_ratio_very_low_threshold", 0.7)
        low_threshold = _get_config_limit("limit_vol_ratio_low_threshold", 0.9)
        normal_upper = _get_config_limit("limit_vol_ratio_normal_upper", 1.1)
        high_upper = _get_config_limit("limit_vol_ratio_high_upper", 1.5)

        # Determine vol state
        if vol_ratio < very_low_threshold:
            vol_state = "very_low"
        elif vol_ratio < low_threshold:
            vol_state = "low"
        elif vol_ratio < normal_upper:
            vol_state = "normal"
        elif vol_ratio < high_upper:
            vol_state = "high"
        else:
            vol_state = "extreme"

        multipliers = self._get_volatility_multipliers()
        multiplier = multipliers[vol_state]

        adjusted = TradingLimits(
            stop_loss_pct=base_limits.stop_loss_pct * multiplier,
            daily_loss_limit=base_limits.daily_loss_limit * multiplier,
            max_position_size=base_limits.max_position_size * multiplier,
            max_portfolio_leverage=base_limits.max_portfolio_leverage * multiplier,
            min_margin_requirement=base_limits.min_margin_requirement / multiplier if multiplier > Decimal("0") else base_limits.min_margin_requirement,
            max_drawdown_limit=base_limits.max_drawdown_limit * multiplier,
        )

        reason = f"Volatility {float(vol_ratio):.2f}x ({vol_state}) → multiplier {float(multiplier):.2f}x"
        logger.info(f"Limit adjustment for volatility: {reason}")

        return adjusted, reason

    def adjust_limits_for_drawdown(
        self,
        base_limits: TradingLimits,
        current_drawdown_pct: Decimal,
    ) -> Tuple[TradingLimits, str]:
        """
        Tighten limits as portfolio drawdown increases.

        Args:
            base_limits: Starting limits
            current_drawdown_pct: Current portfolio drawdown (e.g., 0.10 = 10%)

        Returns:
            (adjusted_limits, reason_string)
        """
        current_drawdown_pct = Decimal(str(current_drawdown_pct))

        # Get thresholds from config
        healthy_threshold = _get_config_limit("limit_dd_healthy_threshold", 0.05)
        caution_threshold = _get_config_limit("limit_dd_caution_threshold", 0.10)
        warning_threshold = _get_config_limit("limit_dd_warning_threshold", 0.15)
        critical_threshold = _get_config_limit("limit_dd_critical_threshold", 0.20)

        # Determine drawdown state
        if current_drawdown_pct < healthy_threshold:
            dd_state = "healthy"
        elif current_drawdown_pct < caution_threshold:
            dd_state = "caution"
        elif current_drawdown_pct < warning_threshold:
            dd_state = "warning"
        elif current_drawdown_pct < critical_threshold:
            dd_state = "critical"
        else:
            dd_state = "halt"

        multipliers = self._get_drawdown_multipliers()
        multiplier = multipliers[dd_state]

        adjusted = TradingLimits(
            stop_loss_pct=base_limits.stop_loss_pct * multiplier,
            daily_loss_limit=base_limits.daily_loss_limit * multiplier,
            max_position_size=base_limits.max_position_size * multiplier,
            max_portfolio_leverage=base_limits.max_portfolio_leverage * multiplier,
            min_margin_requirement=(
                base_limits.min_margin_requirement / multiplier
                if multiplier > Decimal("0")
                else base_limits.min_margin_requirement
            ),
            max_drawdown_limit=base_limits.max_drawdown_limit * multiplier,
        )

        reason = (
            f"Drawdown {float(current_drawdown_pct):.1%} ({dd_state}) → "
            f"multiplier {float(multiplier):.2f}x"
        )
        logger.info(f"Limit adjustment for drawdown: {reason}")

        return adjusted, reason

    def calculate_dynamic_stop_loss(
        self,
        position_entry_price: Decimal,
        position_size: Decimal,
        capital: Decimal,
        risk_per_trade_pct: Decimal,
        volatility_adjustment: Decimal = Decimal("1.0"),
    ) -> Decimal:
        """
        Calculate stop loss price based on capital risk allocation.

        Args:
            position_entry_price: Entry price (€)
            position_size: Position size (€)
            capital: Total capital (€)
            risk_per_trade_pct: Risk allowed per trade (e.g., 0.02 = 2%)
            volatility_adjustment: Vol adjustment multiplier

        Returns:
            Stop loss price
        """
        position_entry_price = Decimal(str(position_entry_price))
        position_size = Decimal(str(position_size))
        capital = Decimal(str(capital))
        risk_per_trade_pct = Decimal(str(risk_per_trade_pct))

        if position_entry_price <= Decimal("0"):
            return position_entry_price

        # Maximum loss allowed for this trade
        max_loss = capital * risk_per_trade_pct * volatility_adjustment

        # How far can price move before hitting max_loss
        # max_loss = position_size × (entry - stop)
        # stop = entry - max_loss / position_size

        price_distance = max_loss / position_size if position_size > Decimal("0") else Decimal("0")

        stop_loss_price = position_entry_price - price_distance

        logger.info(
            f"Dynamic stop loss: entry={position_entry_price:.2f}, "
            f"risk={risk_per_trade_pct:.1%}, "
            f"stop={stop_loss_price:.2f}"
        )

        return stop_loss_price

    def is_within_daily_limit(
        self,
        current_daily_loss: Decimal,
        daily_loss_limit: Decimal,
        capital: Decimal,
    ) -> bool:
        """
        Check if current daily loss within limit.

        Args:
            current_daily_loss: Current day's loss (€, negative value)
            daily_loss_limit: Daily limit as % of capital
            capital: Total capital (€)

        Returns:
            True if within limit
        """
        current_daily_loss = Decimal(str(current_daily_loss))
        daily_loss_limit = Decimal(str(daily_loss_limit))
        capital = Decimal(str(capital))

        max_loss_allowed = capital * daily_loss_limit

        # current_daily_loss is negative, so check absolute value
        within_limit = abs(current_daily_loss) <= max_loss_allowed

        if not within_limit:
            logger.warning(
                f"Daily loss €{abs(current_daily_loss):,.0f} exceeds limit "
                f"€{max_loss_allowed:,.0f} ({daily_loss_limit:.1%} of capital)"
            )

        return within_limit

    def is_within_leverage_limit(
        self,
        total_capital_deployed: Decimal,
        capital: Decimal,
        leverage_limit: Decimal,
    ) -> bool:
        """
        Check if leverage within limit.

        Args:
            total_capital_deployed: Sum of all position sizes (€)
            capital: Total capital (€)
            leverage_limit: Max leverage multiplier

        Returns:
            True if within limit
        """
        total_capital_deployed = Decimal(str(total_capital_deployed))
        capital = Decimal(str(capital))
        leverage_limit = Decimal(str(leverage_limit))

        if capital <= Decimal("0"):
            return True

        current_leverage = total_capital_deployed / capital

        within_limit = current_leverage <= leverage_limit

        if not within_limit:
            logger.warning(f"Leverage {current_leverage:.2f}x exceeds limit {leverage_limit:.2f}x")

        return within_limit

    def is_within_position_size_limit(
        self,
        position_size: Decimal,
        max_position_size_pct: Decimal,
        capital: Decimal,
    ) -> bool:
        """
        Check if single position within size limit.

        Args:
            position_size: Position size (€)
            max_position_size_pct: Max % of capital per position
            capital: Total capital (€)

        Returns:
            True if within limit
        """
        position_size = Decimal(str(position_size))
        max_position_size_pct = Decimal(str(max_position_size_pct))
        capital = Decimal(str(capital))

        max_allowed = capital * max_position_size_pct

        within_limit = position_size <= max_allowed

        if not within_limit:
            logger.warning(
                f"Position size €{position_size:,.0f} exceeds limit "
                f"€{max_allowed:,.0f} ({max_position_size_pct:.0%} of capital)"
            )

        return within_limit

    def get_comprehensive_limits(
        self,
        capital_tier: str,
        capital: Decimal,
        current_volatility: Decimal,
        average_volatility: Decimal,
        current_drawdown_pct: Decimal,
    ) -> Dict[str, any]:
        """
        Get all trading limits with all adjustments applied.

        Args:
            capital_tier: micro/small/medium/large
            capital: Total capital (€)
            current_volatility: Current vol (ATR)
            average_volatility: Historical avg vol
            current_drawdown_pct: Portfolio drawdown (0-1)

        Returns:
            Dict with all adjusted limits
        """
        # Start with base limits
        base = self.get_base_limits(capital_tier)

        # Apply volatility adjustment
        vol_adjusted, vol_reason = self.adjust_limits_for_volatility(
            base, current_volatility, average_volatility
        )

        # Apply drawdown adjustment
        final, dd_reason = self.adjust_limits_for_drawdown(vol_adjusted, current_drawdown_pct)

        return {
            "stop_loss_pct": final.stop_loss_pct,
            "daily_loss_limit_pct": final.daily_loss_limit,
            "max_position_pct": final.max_position_size,
            "max_leverage": final.max_portfolio_leverage,
            "margin_requirement": final.min_margin_requirement,
            "max_drawdown_pct": final.max_drawdown_limit,
            "daily_loss_limit_eur": capital * final.daily_loss_limit,
            "max_position_eur": capital * final.max_position_size,
            "volatility_adjustment": vol_reason,
            "drawdown_adjustment": dd_reason,
        }


# Singleton
_adjuster: Optional[LimitAdjuster] = None


def get_limit_adjuster() -> LimitAdjuster:
    """Get or create singleton LimitAdjuster."""
    global _adjuster
    if _adjuster is None:
        _adjuster = LimitAdjuster()

    return _adjuster
