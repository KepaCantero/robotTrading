"""
Position Entity - Represents a holding in a portfolio

A Position represents a single asset holding with entry/exit information,
profit/loss calculations, and risk metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.domain.value_objects.money import Money

logger = logging.getLogger(__name__)


class PositionSide(str, Enum):
    """Position side (long or short)."""

    LONG = "long"
    SHORT = "short"


class PositionStatus(str, Enum):
    """Position status."""

    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


# Maximum position size to prevent unlimited position growth
MAX_POSITION_SIZE = Decimal("1000000")


@dataclass
class Position:
    """
    Position entity representing a holding in a portfolio.

    A position tracks entry/exit prices, quantities, and P&L.
    It is an entity with identity (symbol + entry_date).

    Supports both avg_entry_price and avg_price as aliases.
    """

    # Identity
    symbol: str
    entry_date: datetime = field(default_factory=datetime.utcnow)

    # Position details
    side: PositionSide = PositionSide.LONG
    quantity: Decimal = Decimal("0")
    avg_entry_price: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    currency: str = "USD"

    # Tracking
    status: PositionStatus = PositionStatus.OPEN
    exit_date: Optional[datetime] = None
    avg_exit_price: Decimal = Decimal("0")

    # Risk metrics
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    max_price: Decimal = Decimal("0")  # Highest price since entry
    min_price: Decimal = Decimal("0")  # Lowest price since entry

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __init__(
        self,
        symbol: str,
        entry_date: Optional[datetime] = None,
        side: PositionSide = PositionSide.LONG,
        quantity: Decimal = Decimal("0"),
        avg_entry_price: Decimal = Decimal("0"),
        avg_price: Optional[Decimal] = None,  # Alias for avg_entry_price
        current_price: Decimal = Decimal("0"),
        currency: str = "USD",
        status: PositionStatus = PositionStatus.OPEN,
        exit_date: Optional[datetime] = None,
        avg_exit_price: Decimal = Decimal("0"),
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        max_price: Decimal = Decimal("0"),
        min_price: Decimal = Decimal("0"),
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        """
        Initialize Position.

        Args:
            symbol: Trading symbol
            entry_date: Position entry date
            side: Position side (long/short)
            quantity: Number of shares
            avg_entry_price: Average entry price
            avg_price: Alias for avg_entry_price (for backward compatibility)
            current_price: Current market price
            currency: Position currency
            status: Position status
            exit_date: Position exit date
            avg_exit_price: Average exit price
            stop_loss: Stop loss price
            take_profit: Take profit price
            max_price: Highest price since entry
            min_price: Lowest price since entry
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        # Handle avg_price alias
        if avg_price is not None:
            avg_entry_price = avg_price

        now = datetime.now(timezone.utc)
        if created_at is None:
            created_at = now
        if updated_at is None:
            updated_at = now
        if entry_date is None:
            entry_date = now

        # Set all attributes directly to bypass dataclass __init__
        self.__dict__['symbol'] = symbol
        self.__dict__['entry_date'] = entry_date
        self.__dict__['side'] = side
        self.__dict__['quantity'] = quantity
        self.__dict__['avg_entry_price'] = avg_entry_price
        self.__dict__['current_price'] = current_price
        self.__dict__['currency'] = currency
        self.__dict__['status'] = status
        self.__dict__['exit_date'] = exit_date
        self.__dict__['avg_exit_price'] = avg_exit_price
        self.__dict__['stop_loss'] = stop_loss
        self.__dict__['take_profit'] = take_profit
        self.__dict__['max_price'] = max_price if max_price != Decimal("0") else current_price
        self.__dict__['min_price'] = min_price if min_price != Decimal("0") else current_price
        self.__dict__['created_at'] = created_at
        self.__dict__['updated_at'] = updated_at

        # Validate
        self._validate()

    def _validate(self) -> None:
        """Validate position invariants."""
        logger.debug(
            "Validating position",
            extra={"symbol": self.symbol, "quantity": str(self.quantity)}
        )
        if not self.symbol:
            logger.error("Position validation failed: empty symbol")
            raise ValueError("Symbol cannot be empty")
        if self.quantity < 0:
            logger.error(
                "Position validation failed: negative quantity",
                extra={"symbol": self.symbol, "quantity": str(self.quantity)}
            )
            raise ValueError("Quantity cannot be negative")
        if self.avg_entry_price < 0:
            logger.error(
                "Position validation failed: negative entry price",
                extra={"symbol": self.symbol, "avg_entry_price": str(self.avg_entry_price)}
            )
            raise ValueError("Entry price cannot be negative")
        if self.current_price < 0:
            logger.error(
                "Position validation failed: negative current price",
                extra={"symbol": self.symbol, "current_price": str(self.current_price)}
            )
            raise ValueError("Current price cannot be negative")
        if self.current_price == 0:
            logger.error(
                "Position validation failed: zero price",
                extra={"symbol": self.symbol}
            )
            raise ValueError("Price cannot be zero")
        if self.stop_loss is not None and self.stop_loss <= 0:
            logger.error(
                "Position validation failed: invalid stop loss",
                extra={"symbol": self.symbol, "stop_loss": str(self.stop_loss)}
            )
            raise ValueError("Stop loss must be positive when set")
        if self.take_profit is not None and self.take_profit <= 0:
            logger.error(
                "Position validation failed: invalid take profit",
                extra={"symbol": self.symbol, "take_profit": str(self.take_profit)}
            )
            raise ValueError("Take profit must be positive when set")
        logger.debug(
            "Position validation passed",
            extra={"symbol": self.symbol}
        )

    @property
    def avg_price(self) -> Decimal:
        """Alias for avg_entry_price for backward compatibility."""
        return self.avg_entry_price

    # Additional backward compatibility methods
    def get_pnl(self) -> Decimal:
        """Get P&L as Decimal - for backward compatibility."""
        return self.get_unrealized_pnl_amount()

    def get_quantity(self) -> Decimal:
        """Get position quantity."""
        return self.quantity

    def get_current_price(self) -> Decimal:
        """Get current price."""
        return self.current_price

    # Domain behaviors - position value
    def get_value(self) -> Money:
        """Calculate current position value."""
        return Money(amount=self.quantity * self.current_price, currency=self.currency)

    def get_cost_basis(self) -> Money:
        """Calculate total cost basis."""
        return Money(amount=self.quantity * self.avg_entry_price, currency=self.currency)

    # Domain behaviors - P&L calculations
    def get_unrealized_pnl_amount(self) -> Decimal:
        """
        Calculate unrealized profit/loss as Decimal (can be negative for losses).

        Returns:
            P&L amount (positive for profit, negative for loss)
        """
        if self.status == PositionStatus.CLOSED:
            return Decimal("0")

        price_diff = self.current_price - self.avg_entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff

        return price_diff * self.quantity

    def get_unrealized_pnl(self) -> Money:
        """
        Calculate unrealized profit/loss as Money.

        Note: For losses, returns Money with absolute value.
        Use get_unrealized_pnl_amount() to get signed value.
        """
        pnl_amount = self.get_unrealized_pnl_amount()
        # Money can't be negative, so use absolute value
        return Money(amount=abs(pnl_amount), currency=self.currency)

    def get_realized_pnl_amount(self) -> Decimal:
        """
        Calculate realized profit/loss as Decimal (can be negative for losses).

        Returns:
            P&L amount (positive for profit, negative for loss)
        """
        if self.status != PositionStatus.CLOSED or self.avg_exit_price == Decimal("0"):
            return Decimal("0")

        price_diff = self.avg_exit_price - self.avg_entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff

        return price_diff * self.quantity

    def get_realized_pnl(self) -> Money:
        """
        Calculate realized profit/loss as Money.

        Note: For losses, returns Money with absolute value.
        Use get_realized_pnl_amount() to get signed value.
        """
        pnl_amount = self.get_realized_pnl_amount()
        # Money can't be negative, so use absolute value
        return Money(amount=abs(pnl_amount), currency=self.currency)

    def get_pnl_percent(self) -> Decimal:
        """Calculate P&L as percentage of cost basis."""
        cost = self.get_cost_basis().amount
        if cost == 0:
            return Decimal("0")

        if self.status == PositionStatus.CLOSED:
            pnl = self.get_realized_pnl_amount()
        else:
            pnl = self.get_unrealized_pnl_amount()

        return (pnl / cost) * Decimal("100")

    # Domain behaviors - price updates
    def update_price(self, new_price: Decimal) -> None:
        """
        Update current price and track max/min.

        Args:
            new_price: New current price

        Raises:
            ValueError: If price is negative or zero
        """
        logger.debug(
            "Updating position price",
            extra={"symbol": self.symbol, "old_price": str(self.current_price), "new_price": str(new_price)}
        )
        if new_price <= 0:
            logger.error(
                "Price update failed: invalid price",
                extra={"symbol": self.symbol, "new_price": str(new_price)}
            )
            raise ValueError("Price must be positive")

        self.current_price = new_price
        self.updated_at = datetime.now(timezone.utc)

        # Update max/min
        if new_price > self.max_price:
            logger.debug(
                "New max price recorded",
                extra={"symbol": self.symbol, "max_price": str(new_price)}
            )
            self.max_price = new_price
        if new_price < self.min_price:
            logger.debug(
                "New min price recorded",
                extra={"symbol": self.symbol, "min_price": str(new_price)}
            )
            self.min_price = new_price

    def add_shares(self, quantity: Decimal, price: Decimal) -> None:
        """
        Add shares to existing position (average up/down).

        Args:
            quantity: Number of shares to add
            price: Price per share

        Raises:
            ValueError: If quantity or price is negative, or position size exceeds limit
        """
        logger.info(
            "Adding shares to position",
            extra={
                "symbol": self.symbol,
                "current_quantity": str(self.quantity),
                "adding_quantity": str(quantity),
                "price": str(price)
            }
        )
        if quantity < 0:
            logger.error(
                "Add shares failed: negative quantity",
                extra={"symbol": self.symbol, "quantity": str(quantity)}
            )
            raise ValueError("Quantity cannot be negative")
        if price < 0:
            logger.error(
                "Add shares failed: negative price",
                extra={"symbol": self.symbol, "price": str(price)}
            )
            raise ValueError("Price cannot be negative")

        # Calculate new total quantity
        total_quantity = self.quantity + quantity
        if total_quantity > MAX_POSITION_SIZE:
            logger.error(
                "Add shares failed: position size limit exceeded",
                extra={
                    "symbol": self.symbol,
                    "current_quantity": str(self.quantity),
                    "adding_quantity": str(quantity),
                    "total_quantity": str(total_quantity),
                    "max_size": str(MAX_POSITION_SIZE)
                }
            )
            raise ValueError(
                f"Position size cannot exceed {MAX_POSITION_SIZE}. "
                f"Current: {self.quantity}, Adding: {quantity}, Total would be: {total_quantity}"
            )

        # Calculate new average price
        total_cost = (self.quantity * self.avg_entry_price) + (quantity * price)

        self.quantity = total_quantity
        self.avg_entry_price = total_cost / total_quantity if total_quantity > 0 else Decimal("0")
        self.updated_at = datetime.now(timezone.utc)
        logger.info(
            "Shares added successfully",
            extra={
                "symbol": self.symbol,
                "new_quantity": str(self.quantity),
                "new_avg_price": str(self.avg_entry_price)
            }
        )

    def remove_shares(self, quantity: Decimal, price: Decimal) -> None:
        """
        Remove shares from position (partial exit).

        Args:
            quantity: Number of shares to remove
            price: Exit price per share

        Raises:
            ValueError: If quantity exceeds current position
        """
        logger.info(
            "Removing shares from position",
            extra={
                "symbol": self.symbol,
                "current_quantity": str(self.quantity),
                "removing_quantity": str(quantity),
                "exit_price": str(price)
            }
        )
        if quantity < 0:
            logger.error(
                "Remove shares failed: negative quantity",
                extra={"symbol": self.symbol, "quantity": str(quantity)}
            )
            raise ValueError("Quantity cannot be negative")
        if quantity > self.quantity:
            logger.error(
                "Remove shares failed: quantity exceeds position",
                extra={
                    "symbol": self.symbol,
                    "current_quantity": str(self.quantity),
                    "removing_quantity": str(quantity)
                }
            )
            raise ValueError("Cannot remove more shares than held")

        self.quantity -= quantity
        self.avg_exit_price = price

        if self.quantity == 0:
            logger.info(
                "Position closed",
                extra={
                    "symbol": self.symbol,
                    "exit_price": str(price),
                    "status": "closed"
                }
            )
            self.status = PositionStatus.CLOSED
            self.exit_date = datetime.now(timezone.utc)

        self.updated_at = datetime.now(timezone.utc)

    # Domain behaviors - risk checks
    def is_stop_loss_hit(self) -> bool:
        """Check if stop-loss level has been triggered."""
        if self.stop_loss is None:
            return False

        if self.side == PositionSide.LONG:
            return self.current_price <= self.stop_loss
        else:  # SHORT
            return self.current_price >= self.stop_loss

    def is_take_profit_hit(self) -> bool:
        """Check if take-profit level has been triggered."""
        if self.take_profit is None:
            return False

        if self.side == PositionSide.LONG:
            return self.current_price >= self.take_profit
        else:  # SHORT
            return self.current_price <= self.take_profit

    def get_risk_reward_ratio(self) -> Optional[Decimal]:
        """
        Calculate risk/reward ratio.

        Returns:
            Risk/reward ratio, or None if stop loss or take profit not set
        """
        if self.stop_loss is None or self.take_profit is None:
            return None

        risk = abs(self.avg_entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.avg_entry_price)

        if risk == 0:
            return None

        return reward / risk

    # Domain behaviors - position info
    def get_age_days(self) -> int:
        """Get position age in days."""
        end_date = (
            self.exit_date if self.status == PositionStatus.CLOSED else datetime.now(timezone.utc)
        )
        return (end_date - self.entry_date).days

    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN

    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.status == PositionStatus.CLOSED

    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        if self.status == PositionStatus.CLOSED:
            return self.get_realized_pnl_amount() > 0
        return self.get_unrealized_pnl_amount() > 0

    # Factory methods
    @classmethod
    def create_long(
        cls,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        currency: str = "USD",
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Position:
        """Create a new long position."""
        logger.info(
            "Creating long position",
            extra={
                "symbol": symbol,
                "quantity": str(quantity),
                "entry_price": str(entry_price),
                "side": "LONG"
            }
        )
        return cls(
            symbol=symbol,
            entry_date=datetime.now(timezone.utc),
            side=PositionSide.LONG,
            quantity=quantity,
            avg_entry_price=entry_price,
            current_price=entry_price,
            currency=currency,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=PositionStatus.OPEN,
        )

    @classmethod
    def create_short(
        cls,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        currency: str = "USD",
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Position:
        """Create a new short position."""
        logger.info(
            "Creating short position",
            extra={
                "symbol": symbol,
                "quantity": str(quantity),
                "entry_price": str(entry_price),
                "side": "SHORT"
            }
        )
        return cls(
            symbol=symbol,
            entry_date=datetime.now(timezone.utc),
            side=PositionSide.SHORT,
            quantity=quantity,
            avg_entry_price=entry_price,
            current_price=entry_price,
            currency=currency,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=PositionStatus.OPEN,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "avg_entry_price": str(self.avg_entry_price),
            "current_price": str(self.current_price),
            "currency": self.currency,
            "status": self.status.value,
            "unrealized_pnl": str(self.get_unrealized_pnl().amount),
            "realized_pnl": str(self.get_realized_pnl().amount),
            "pnl_percent": str(self.get_pnl_percent()),
            "value": str(self.get_value().amount),
            "cost_basis": str(self.get_cost_basis().amount),
            "stop_loss": str(self.stop_loss) if self.stop_loss else None,
            "take_profit": str(self.take_profit) if self.take_profit else None,
            "entry_date": self.entry_date.isoformat(),
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
        }

    def __str__(self) -> str:
        """String representation."""
        side_str = "LONG" if self.side == PositionSide.LONG else "SHORT"
        return (
            f"{side_str} {self.symbol}: "
            f"{self.quantity} @ ${self.avg_entry_price} "
            f"(P&L: {self.get_pnl_percent():.2f}%)"
        )
