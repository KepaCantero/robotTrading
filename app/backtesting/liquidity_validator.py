"""
Liquidity Validation for Realistic Order Execution

Validates that orders can be filled based on actual market volume and
implements realistic partial fill scenarios.

This module addresses HIGH PRIORITY #1 from the audit report:
- Volume-based rejection (>10% of daily volume)
- Warning for large orders (>5% of daily volume)
- Partial fills for orders that exceed available liquidity
- Market impact calculation

SINGLE SOURCE OF TRUTH: All values from CentralizedConfig.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple

# SINGLE SOURCE OF TRUTH: Use CentralizedConfig for all values
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


def _get_backtesting_config():
    """Helper to get backtesting config from CentralizedConfig."""
    return get_config().backtesting


@dataclass
class FillResult:
    """Result of an order fill attempt."""

    requested_quantity: Decimal
    filled_quantity: Decimal
    fill_price: Decimal
    fill_status: str  # "FILLED", "PARTIAL", "REJECTED"
    rejection_reason: Optional[str] = None
    avg_fill_price: Optional[Decimal] = None
    market_impact: Optional[Decimal] = None

    def __post_init__(self):
        """Set avg_fill_price to fill_price if not provided."""
        if self.avg_fill_price is None:
            self.avg_fill_price = self.fill_price


class LiquidityValidator:
    """
    Validates order liquidity and implements realistic fill scenarios.

    Features:
    - Volume-based rejection (>10% of daily volume)
    - Warning for large orders (>5% of daily volume)
    - Partial fills for orders that exceed available liquidity
    - Market impact calculation based on order size

    SINGLE SOURCE OF TRUTH: All thresholds from CentralizedConfig.

    Thresholds (from CentralizedConfig):
    - MAX_ORDER_PCT_OF_VOLUME: max order size % of volume
    - WARNING_ORDER_PCT_OF_VOLUME: warning threshold % of volume
    - PARTIAL_FILL_PCT: maximum fill % for partial fills
    """

    def __init__(
        self,
        enable_partial_fills: bool = True,
        max_order_pct_of_volume: Optional[Decimal] = None,
        warning_order_pct_of_volume: Optional[Decimal] = None,
        partial_fill_pct: Optional[Decimal] = None,
    ):
        """
        Initialize liquidity validator.

        SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.

        Args:
            enable_partial_fills: If True, allow partial fills for large orders
            max_order_pct_of_volume: Override default max order size
            warning_order_pct_of_volume: Override default warning threshold
            partial_fill_pct: Override default partial fill percentage
        """
        config = _get_backtesting_config()

        self.enable_partial_fills = enable_partial_fills

        # Get thresholds from CentralizedConfig or use overrides
        self.max_order_pct_of_volume = (
            max_order_pct_of_volume if max_order_pct_of_volume is not None else config.adv_limit_pct
        )
        self.warning_order_pct_of_volume = (
            warning_order_pct_of_volume
            if warning_order_pct_of_volume is not None
            else config.adv_limit_pct / 2
        )
        self.partial_fill_pct = (
            partial_fill_pct if partial_fill_pct is not None else config.adv_limit_pct / 2
        )

        # Market impact parameters from CentralizedConfig
        self.base_slippage_pct = config.base_slippage_bps / Decimal(
            "10000"
        )  # Convert bps to decimal
        self.max_additional_slippage = Decimal("0.01")  # 1% max additional

        logger.info(
            f"LiquidityValidator initialized: "
            f"max_order={self.max_order_pct_of_volume:.1%}, "
            f"warning={self.warning_order_pct_of_volume:.1%}, "
            f"partial_fill={self.partial_fill_pct:.1%}, "
            f"enable_partial={self.enable_partial_fills}"
        )

    def validate_order(
        self, order_quantity: Decimal, symbol: str, current_bar, order_side: str = "buy"
    ) -> Tuple[bool, str]:
        """
        Validate if order can be filled based on available liquidity.

        Args:
            order_quantity: Requested order quantity
            symbol: Trading symbol
            current_bar: Current market data bar with volume
            order_side: "buy" or "sell"

        Returns:
            Tuple of (is_valid, reason)
                - is_valid: True if order can be filled, False otherwise
                - reason: Human-readable explanation of validation result
        """
        # Check for volume data
        if not hasattr(current_bar, 'volume') or current_bar.volume is None:
            return False, "No volume data available"

        daily_volume = Decimal(str(current_bar.volume))

        if daily_volume <= 0:
            return False, f"Invalid daily volume: {daily_volume}"

        # Calculate order as percentage of daily volume
        order_pct = order_quantity / daily_volume

        # Reject if order exceeds maximum threshold
        if order_pct > self.max_order_pct_of_volume:
            return False, (
                f"Order {order_quantity:.0f} shares ({order_pct:.1%} of daily volume) "
                f"exceeds maximum {self.max_order_pct_of_volume:.1%} threshold. "
                f"Daily volume: {daily_volume:.0f} shares."
            )

        # Warn if order exceeds warning threshold but is still acceptable
        if order_pct > self.warning_order_pct_of_volume:
            logger.warning(
                f"⚠️ Large order for {symbol}: {order_quantity:.0f} shares "
                f"({order_pct:.1%} of daily volume {daily_volume:.0f}) - "
                f"may experience significant slippage and market impact"
            )

        return True, "OK"

    def simulate_fill(
        self, order_quantity: Decimal, current_bar, order_side: str = "buy", symbol: str = "UNKNOWN"
    ) -> FillResult:
        """
        Simulate realistic order fill with partial fills if necessary.

        This method:
        1. Validates the order against available liquidity
        2. Determines if full fill, partial fill, or rejection is appropriate
        3. Calculates realistic execution price with market impact

        Args:
            order_quantity: Requested order quantity
            current_bar: Current market data bar
            order_side: "buy" or "sell"
            symbol: Trading symbol (for logging)

        Returns:
            FillResult with fill details including execution price and status
        """
        # First validate the order
        is_valid, reason = self.validate_order(order_quantity, symbol, current_bar, order_side)

        if not is_valid:
            # Order rejected - no fill
            return FillResult(
                requested_quantity=order_quantity,
                filled_quantity=Decimal("0"),
                fill_price=Decimal("0"),
                fill_status="REJECTED",
                rejection_reason=reason,
                market_impact=Decimal("0"),
            )

        daily_volume = Decimal(str(current_bar.volume))
        order_pct = order_quantity / daily_volume

        # Check if we need to do a partial fill
        max_fillable = daily_volume * self.partial_fill_pct

        if order_quantity <= max_fillable:
            # Full fill possible - execute entire order
            if order_side == "buy":
                fill_price = self._calculate_buy_fill_price(current_bar, order_quantity)
            else:
                fill_price = self._calculate_sell_fill_price(current_bar, order_quantity)

            market_impact = self.calculate_market_impact(order_quantity, current_bar, order_side)

            return FillResult(
                requested_quantity=order_quantity,
                filled_quantity=order_quantity,
                fill_price=fill_price,
                fill_status="FILLED",
                avg_fill_price=fill_price,
                market_impact=market_impact,
            )
        else:
            # Partial fill scenario - order too large for immediate execution
            if self.enable_partial_fills:
                filled_quantity = max_fillable

                if order_side == "buy":
                    fill_price = self._calculate_buy_fill_price(current_bar, filled_quantity)
                else:
                    fill_price = self._calculate_sell_fill_price(current_bar, filled_quantity)

                market_impact = self.calculate_market_impact(
                    filled_quantity, current_bar, order_side
                )

                fill_pct = filled_quantity / order_quantity

                logger.warning(
                    f"⚠️ PARTIAL FILL for {symbol}: {filled_quantity:.0f}/{order_quantity:.0f} shares "
                    f"({fill_pct:.1%} filled) at ${fill_price:.2f}. "
                    f"Remaining {order_quantity - filled_quantity:.0f} shares unfilled."
                )

                return FillResult(
                    requested_quantity=order_quantity,
                    filled_quantity=filled_quantity,
                    fill_price=fill_price,
                    fill_status="PARTIAL",
                    avg_fill_price=fill_price,
                    market_impact=market_impact,
                )
            else:
                # Partial fills disabled - reject the order
                return FillResult(
                    requested_quantity=order_quantity,
                    filled_quantity=Decimal("0"),
                    fill_price=Decimal("0"),
                    fill_status="REJECTED",
                    rejection_reason=(
                        f"Order too large ({order_quantity:.0f} shares = {order_pct:.1%} of daily volume) "
                        f"and partial fills are disabled. "
                        f"Maximum fillable: {max_fillable:.0f} shares ({self.partial_fill_pct:.1%})."
                    ),
                    market_impact=Decimal("0"),
                )

    def _calculate_buy_fill_price(self, current_bar, quantity: Optional[Decimal] = None) -> Decimal:
        """
        Calculate realistic buy fill price with slippage and market impact.

        Buy orders pay more (worst case execution) due to:
        1. Base slippage (0.1%)
        2. Market impact based on order size (squared relationship)

        Args:
            current_bar: Current market data bar
            quantity: Order quantity (for market impact calculation)

        Returns:
            Execution price including all costs
        """
        # Get base price (prefer close, then last, then ask)
        if hasattr(current_bar, 'close'):
            base_price = Decimal(str(current_bar.close))
        elif hasattr(current_bar, 'last'):
            base_price = Decimal(str(current_bar.last))
        elif hasattr(current_bar, 'ask'):
            base_price = Decimal(str(current_bar.ask))
        else:
            base_price = Decimal("100")

        # Start with base slippage
        total_slippage = self.base_slippage_pct

        # Add market impact if quantity provided
        if quantity is not None and hasattr(current_bar, 'volume'):
            daily_volume = Decimal(str(current_bar.volume))

            if daily_volume > 0:
                # Market impact increases with square of order size
                # Small orders have minimal impact, large orders have significant impact
                volume_ratio = quantity / daily_volume
                impact_factor = volume_ratio**2
                additional_slippage = impact_factor * Decimal("0.1")  # Scale factor

                # Cap additional slippage
                additional_slippage = min(additional_slippage, self.max_additional_slippage)
                total_slippage += additional_slippage

        # Buy orders pay more (unfavorable execution)
        execution_price = base_price * (Decimal("1") + total_slippage)

        return execution_price

    def _calculate_sell_fill_price(
        self, current_bar, quantity: Optional[Decimal] = None
    ) -> Decimal:
        """
        Calculate realistic sell fill price with slippage and market impact.

        Sell orders receive less (worst case execution) due to:
        1. Base slippage (0.1%)
        2. Market impact based on order size (squared relationship)

        Args:
            current_bar: Current market data bar
            quantity: Order quantity (for market impact calculation)

        Returns:
            Execution price including all costs
        """
        # Get base price (prefer close, then last, then bid)
        if hasattr(current_bar, 'close'):
            base_price = Decimal(str(current_bar.close))
        elif hasattr(current_bar, 'last'):
            base_price = Decimal(str(current_bar.last))
        elif hasattr(current_bar, 'bid'):
            base_price = Decimal(str(current_bar.bid))
        else:
            base_price = Decimal("100")

        # Start with base slippage
        total_slippage = self.base_slippage_pct

        # Add market impact if quantity provided
        if quantity is not None and hasattr(current_bar, 'volume'):
            daily_volume = Decimal(str(current_bar.volume))

            if daily_volume > 0:
                # Market impact increases with square of order size
                volume_ratio = quantity / daily_volume
                impact_factor = volume_ratio**2
                additional_slippage = impact_factor * Decimal("0.1")

                # Cap additional slippage
                additional_slippage = min(additional_slippage, self.max_additional_slippage)
                total_slippage += additional_slippage

        # Sell orders receive less (unfavorable execution)
        execution_price = base_price * (Decimal("1") - total_slippage)

        return execution_price

    def calculate_market_impact(
        self, order_quantity: Decimal, current_bar, order_side: str = "buy"
    ) -> Decimal:
        """
        Calculate estimated market impact of an order.

        Uses square-root market impact model:
        Impact increases with sqrt(order_size / daily_volume)

        This provides a realistic estimate of how much the order itself
        will move the market price.

        Args:
            order_quantity: Order quantity
            current_bar: Current market data
            order_side: "buy" or "sell"

        Returns:
            Estimated price impact in decimal (0.01 = 1%)
        """
        if not hasattr(current_bar, 'volume') or current_bar.volume is None:
            return Decimal("0.01")  # 1% default if no volume data

        daily_volume = Decimal(str(current_bar.volume))

        if daily_volume <= 0:
            return Decimal("0.1")  # 10% impact if invalid volume

        order_pct = order_quantity / daily_volume

        # Square-root market impact model
        # Impact = base_factor * sqrt(order_pct)
        # Capped at 5% maximum impact
        base_impact = (order_pct ** Decimal("0.5")) * Decimal("0.1")

        # Cap at reasonable maximum
        max_impact = Decimal("0.05")  # 5%
        market_impact = min(base_impact, max_impact)

        return market_impact

    def get_liquidity_metrics(self, current_bar, order_quantity: Optional[Decimal] = None) -> dict:
        """
        Get liquidity metrics for current market conditions.

        Useful for logging and diagnostics.

        Args:
            current_bar: Current market data bar
            order_quantity: Optional order quantity to analyze

        Returns:
            Dictionary with liquidity metrics
        """
        daily_volume = Decimal(str(getattr(current_bar, 'volume', 0)))

        metrics = {
            "daily_volume": float(daily_volume),
            "max_order_size": float(daily_volume * self.max_order_pct_of_volume),
            "warning_threshold": float(daily_volume * self.warning_order_pct_of_volume),
            "partial_fill_size": float(daily_volume * self.partial_fill_pct),
        }

        if order_quantity is not None:
            order_pct = order_quantity / daily_volume if daily_volume > 0 else Decimal("0")
            metrics["order_quantity"] = float(order_quantity)
            metrics["order_pct_of_volume"] = float(order_pct)
            metrics["would_reject"] = order_pct > self.max_order_pct_of_volume
            metrics["would_warn"] = order_pct > self.warning_order_pct_of_volume

        return metrics
