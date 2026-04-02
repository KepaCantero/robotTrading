"""
Wash Sale Tracker for USA Accounts.

USA Wash Sale Rule (IRC Section 1091):
- Sell security at loss
- Buy substantially identical security within 30 days before or after
- Loss is disallowed for tax purposes
- Disallowed loss added to new position's basis

IMPORTANT: Spain does NOT have wash sale rules.
Losses are fully deductible in the year realized.

Reference:
    https://www.irs.gov/publications/p550
    Publication 550 - Investment Income and Expenses
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import ClassVar

from app.services.compliance.pdt_tracker import Country

logger = logging.getLogger(__name__)


@dataclass
class WashSale:
    """Record of a wash sale."""

    symbol: str
    sale_date: date
    sale_price: Decimal
    loss_amount: Decimal
    disallowed_loss: Decimal
    replacement_buy_date: date | None = None
    replacement_price: Decimal | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "sale_date": self.sale_date.isoformat(),
            "sale_price": str(self.sale_price),
            "loss_amount": str(self.loss_amount),
            "disallowed_loss": str(self.disallowed_loss),
            "replacement_buy_date": (
                self.replacement_buy_date.isoformat() if self.replacement_buy_date else None
            ),
            "replacement_price": (str(self.replacement_price) if self.replacement_price else None),
        }


@dataclass
class PositionRecord:
    """Record of a position for wash sale tracking."""

    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    price: Decimal
    trade_date: date
    is_wash_sale: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "trade_date": self.trade_date.isoformat(),
            "is_wash_sale": self.is_wash_sale,
        }


class WashSaleTracker:
    """
    Track wash sales (USA only).

    USA Wash Sale Rule:
    - Sell at loss, buy same/substantially identical within 30 days
    - Loss disallowed for tax purposes
    - Must add disallowed loss to new position's basis

    Spain: No wash sale rule - all losses are deductible

    Usage:
        tracker = WashSaleTracker(country=Country.US)

        # Check if sale would be a wash sale
        is_wash = tracker.is_wash_sale(
            symbol="AAPL",
            sale_date=date.today(),
            sale_price=Decimal("145"),
        )

        # Record a sale
        tracker.record_sale(
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("100"),
            price=Decimal("145"),
            trade_date=date.today(),
        )
    """

    WASH_SALE_WINDOW_DAYS = 30
    SUBSTANTIALLY_IDENTICAL: ClassVar[dict] = {
        # Same symbol
        # Different classes (e.g., BRK.A vs BRK.B)
        # ETFs tracking same index
    }

    def __init__(self, country: Country = Country.ES):
        """
        Initialize wash sale tracker.

        Args:
            country: Country for compliance rules
        """
        self.country = country

        # Trade history
        self._positions: deque[PositionRecord] = deque(maxlen=10000)
        self._wash_sales: list[WashSale] = []

        # Index by symbol for fast lookup
        self._positions_by_symbol: dict[str, deque[PositionRecord]] = {}

        logger.info(f"WashSaleTracker initialized for {country.value}")

    def is_wash_sale(
        self,
        symbol: str,
        sale_date: date,
        sale_price: Decimal,
    ) -> bool:
        """
        Check if sale would be a wash sale.

        Args:
            symbol: Symbol being sold
            sale_date: Date of sale
            sale_price: Sale price

        Returns:
            True if wash sale (USA only)

        Examples:
            >>> tracker = WashSaleTracker(country=Country.US)
            >>> # Buy AAPL on Jan 1
            >>> tracker.record_sale(
            ...     symbol="AAPL",
            ...     side="BUY",
            ...     quantity=Decimal("100"),
            ...     price=Decimal("150"),
            ...     trade_date=date(2024, 1, 1),
            ... )
            >>> # Sell on Jan 15 at loss
            >>> is_wash = tracker.is_wash_sale(
            ...     symbol="AAPL",
            ...     sale_date=date(2024, 1, 15),
            ...     sale_price=Decimal("140"),
            ... )
            >>> is_wash
            True  # Would be wash sale if bought within +/- 30 days
        """
        # Spain: No wash sale rule
        if self.country != Country.US:
            return False

        # Look for purchases in 30-day window before sale
        window_start = sale_date - timedelta(days=self.WASH_SALE_WINDOW_DAYS)
        window_end = sale_date + timedelta(days=self.WASH_SALE_WINDOW_DAYS)

        # Check this symbol's positions
        for position in self._positions_by_symbol.get(symbol, []):
            position_date = position.trade_date

            # Check if in window
            if window_start <= position_date <= window_end:
                # Found a purchase in window - would be wash sale
                return True

        return False

    def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        trade_date: date,
    ) -> None:
        """
        Record a trade for wash sale tracking.

        Args:
            symbol: Symbol traded
            side: BUY or SELL
            quantity: Quantity traded
            price: Price per share
            trade_date: Date of trade
        """
        position = PositionRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
        )

        self._positions.append(position)

        # Update symbol index
        if symbol not in self._positions_by_symbol:
            self._positions_by_symbol[symbol] = deque(maxlen=1000)
        self._positions_by_symbol[symbol].append(position)

        # Check if this is a wash sale
        if (
            side == "SELL"
            and self.country == Country.US
            and self._check_and_record_wash_sale(position)
        ):
            logger.warning(f"Wash sale detected: {symbol} sold on {trade_date}")

    def check_wash_sale_impact(
        self,
        symbol: str,
        sale_date: date,
        sale_price: Decimal,
        cost_basis: Decimal,
    ) -> tuple[bool, Decimal, Decimal]:
        """
        Calculate wash sale impact on a potential sale.

        Args:
            symbol: Symbol being sold
            sale_date: Date of sale
            sale_price: Sale price
            cost_basis: Original cost basis

        Returns:
            Tuple of (is_wash_sale, disallowed_loss, adjusted_basis)
        """
        if not self.is_wash_sale(symbol, sale_date, sale_price):
            # Not a wash sale - full loss deductible
            loss = max(Decimal("0"), cost_basis - sale_price)
            return False, Decimal("0"), loss

        # Calculate wash sale impact
        total_loss = cost_basis - sale_price

        if total_loss <= 0:
            # No loss - not a wash sale concern
            return False, Decimal("0"), Decimal("0")

        # Loss is disallowed - must be added to new position basis
        # This is simplified - actual calculation more complex
        disallowed_loss = total_loss
        deductible_loss = Decimal("0")

        # Record wash sale
        wash_sale = WashSale(
            symbol=symbol,
            sale_date=sale_date,
            sale_price=sale_price,
            loss_amount=total_loss,
            disallowed_loss=disallowed_loss,
        )

        self._wash_sales.append(wash_sale)

        return True, disallowed_loss, deductible_loss

    def get_wash_sales(self, start_date: date | None = None) -> list[WashSale]:
        """
        Get list of wash sales.

        Args:
            start_date: Optional start date filter

        Returns:
            List of wash sale records
        """
        if start_date is None:
            return self._wash_sales.copy()

        return [ws for ws in self._wash_sales if ws.sale_date >= start_date]

    def get_wash_sale_summary(self) -> dict:
        """
        Get summary of wash sales.

        Returns:
            Dictionary with wash sale statistics
        """
        if not self._wash_sales:
            return {
                "total_wash_sales": 0,
                "total_disallowed_loss": "0",
                "by_symbol": {},
            }

        total_disallowed = sum(ws.disallowed_loss for ws in self._wash_sales)

        by_symbol = {}
        for ws in self._wash_sales:
            if ws.symbol not in by_symbol:
                by_symbol[ws.symbol] = {
                    "count": 0,
                    "disallowed_loss": Decimal("0"),
                }
            by_symbol[ws.symbol]["count"] += 1
            by_symbol[ws.symbol]["disallowed_loss"] += ws.disallowed_loss

        return {
            "total_wash_sales": len(self._wash_sales),
            "total_disallowed_loss": str(total_disallowed),
            "by_symbol": {
                symbol: {
                    "count": data["count"],
                    "disallowed_loss": str(data["disallowed_loss"]),
                }
                for symbol, data in by_symbol.items()
            },
        }

    def _check_and_record_wash_sale(self, position: PositionRecord) -> bool:
        """
        Check if position is a wash sale and record it.

        Args:
            position: Position to check

        Returns:
            True if wash sale recorded
        """
        # Look for purchases in window before this sale
        window_start = position.trade_date - timedelta(days=self.WASH_SALE_WINDOW_DAYS)

        for prev_position in self._positions_by_symbol.get(position.symbol, []):
            if (
                prev_position.side == "BUY"
                and prev_position != position
                and window_start <= prev_position.trade_date <= position.trade_date
            ):
                # This is a wash sale
                loss = (prev_position.price - position.price) * position.quantity

                if loss > 0:
                    wash_sale = WashSale(
                        symbol=position.symbol,
                        sale_date=position.trade_date,
                        sale_price=position.price,
                        loss_amount=loss,
                        disallowed_loss=loss,
                        replacement_buy_date=prev_position.trade_date,
                        replacement_price=prev_position.price,
                    )

                    self._wash_sales.append(wash_sale)
                    position.is_wash_sale = True

                    return True

        return False

    def reset(self) -> None:
        """Reset all tracking (for testing)."""
        self._positions.clear()
        self._wash_sales.clear()
        self._positions_by_symbol.clear()

        logger.info("WashSaleTracker reset")
