"""
T8.1.2: LimitAdjuster - Adjust trading limits dynamically

Manages stop losses, margin requirements, position limits, and daily loss limits
based on market conditions and portfolio state.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


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
    """

    # Default limits by capital tier (as % of capital)
    DEFAULT_LIMITS_BY_TIER = {
        "micro": {
            "stop_loss_pct": Decimal("0.02"),  # 2% stops
            "daily_loss_limit_pct": Decimal("0.05"),  # 5% daily max loss
            "max_position_pct": Decimal("0.10"),  # 10% max per position
            "leverage": Decimal("1.0"),  # No leverage
            "margin_requirement": Decimal("0.50"),  # 50% margin
            "max_drawdown_pct": Decimal("0.10"),  # 10% max drawdown
        },
        "small": {
            "stop_loss_pct": Decimal("0.025"),
            "daily_loss_limit_pct": Decimal("0.08"),
            "max_position_pct": Decimal("0.15"),
            "leverage": Decimal("1.0"),
            "margin_requirement": Decimal("0.33"),
            "max_drawdown_pct": Decimal("0.15"),
        },
        "medium": {
            "stop_loss_pct": Decimal("0.03"),
            "daily_loss_limit_pct": Decimal("0.10"),
            "max_position_pct": Decimal("0.20"),
            "leverage": Decimal("1.5"),
            "margin_requirement": Decimal("0.25"),
            "max_drawdown_pct": Decimal("0.20"),
        },
        "large": {
            "stop_loss_pct": Decimal("0.035"),
            "daily_loss_limit_pct": Decimal("0.15"),
            "max_position_pct": Decimal("0.25"),
            "leverage": Decimal("2.0"),
            "margin_requirement": Decimal("0.20"),
            "max_drawdown_pct": Decimal("0.25"),
        },
    }

    # Volatility multipliers (expand/contract limits)
    VOLATILITY_MULTIPLIERS = {
        "very_low": Decimal("1.2"),  # Expand limits in calm markets
        "low": Decimal("1.1"),
        "normal": Decimal("1.0"),  # Baseline
        "high": Decimal("0.8"),  # Contract limits
        "extreme": Decimal("0.5"),  # Severe contraction
    }

    # Drawdown multipliers (tighten as portfolio loses)
    DRAWDOWN_MULTIPLIERS = {
        "healthy": Decimal("1.0"),  # < 5% drawdown
        "caution": Decimal("0.8"),  # 5-10% drawdown
        "warning": Decimal("0.6"),  # 10-15% drawdown
        "critical": Decimal("0.3"),  # 15-20% drawdown
        "halt": Decimal("0.0"),  # > 20% or hard stop hit
    }

    def __init__(self):
        """Initialize limit adjuster."""
        logger.info("✅ LimitAdjuster initialized")

    def get_base_limits(self, capital_tier: str) -> TradingLimits:
        """Get default limits for capital tier."""
        defaults = self.DEFAULT_LIMITS_BY_TIER.get(
            capital_tier.lower(), self.DEFAULT_LIMITS_BY_TIER["medium"]
        )

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

        # Determine vol state
        if vol_ratio < Decimal("0.7"):
            vol_state = "very_low"
        elif vol_ratio < Decimal("0.9"):
            vol_state = "low"
        elif vol_ratio < Decimal("1.1"):
            vol_state = "normal"
        elif vol_ratio < Decimal("1.5"):
            vol_state = "high"
        else:
            vol_state = "extreme"

        multiplier = self.VOLATILITY_MULTIPLIERS[vol_state]

        adjusted = TradingLimits(
            stop_loss_pct=base_limits.stop_loss_pct * multiplier,
            daily_loss_limit=base_limits.daily_loss_limit * multiplier,
            max_position_size=base_limits.max_position_size * multiplier,
            max_portfolio_leverage=base_limits.max_portfolio_leverage * multiplier,
            min_margin_requirement=base_limits.min_margin_requirement / multiplier,
            max_drawdown_limit=base_limits.max_drawdown_limit * multiplier,
        )

        reason = f"Volatility {vol_ratio:.2f}x ({vol_state}) → multiplier {multiplier:.2f}x"
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

        # Determine drawdown state
        if current_drawdown_pct < Decimal("0.05"):
            dd_state = "healthy"
        elif current_drawdown_pct < Decimal("0.10"):
            dd_state = "caution"
        elif current_drawdown_pct < Decimal("0.15"):
            dd_state = "warning"
        elif current_drawdown_pct < Decimal("0.20"):
            dd_state = "critical"
        else:
            dd_state = "halt"

        multiplier = self.DRAWDOWN_MULTIPLIERS[dd_state]

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
            f"Drawdown {current_drawdown_pct:.1%} ({dd_state}) → " f"multiplier {multiplier:.2f}x"
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
        pass

    return _adjuster
