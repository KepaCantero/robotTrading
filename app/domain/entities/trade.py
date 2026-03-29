"""
Trade Entity - Represents a completed trade

A Trade represents a completed transaction with entry and exit information,
profit/loss, and trade metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.domain.entities.position import PositionSide
from app.domain.value_objects.money import Money

logger = logging.getLogger(__name__)


class TradeStatus(str, Enum):
    """Trade status enumeration."""

    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PENDING = "pending"


class TradeType(str, Enum):
    """Trade type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class ExitReason(str, Enum):
    """Reason for trade exit."""

    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    SIGNAL_REVERSAL = "signal_reversal"
    RISK_LIMIT = "risk_limit"
    TIME_EXIT = "time_exit"
    LIQUIDATION = "liquidation"


@dataclass
class Trade:
    """
    Trade entity representing a completed trade.

    A Trade is different from Position:
    - Position: Current holding (open)
    - Trade: Historical record (closed)

    Trade captures the full lifecycle from entry to exit.
    """

    # Identity
    trade_id: str
    symbol: str

    # Trade details
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    currency: str = "USD"

    # Timestamps
    entry_date: datetime = field(default_factory=datetime.utcnow)
    exit_date: datetime | None = None

    # Execution details
    trade_type: TradeType = TradeType.MARKET
    status: TradeStatus = TradeStatus.FILLED
    exit_reason: ExitReason | None = None

    # Costs
    commission_paid: Decimal = Decimal("0")
    slippage_cost: Decimal = Decimal("0")

    # Risk management
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

    # Metadata
    strategy_name: str | None = None
    notes: str | None = None
    tags: list[str] = field(default_factory=lambda: [])

    def __post_init__(self):
        """Validate trade invariants."""
        logger.debug("Validating trade", extra={"trade_id": self.trade_id, "symbol": self.symbol})
        if not self.trade_id:
            logger.error("Trade validation failed: empty trade ID")
            raise ValueError("Trade ID cannot be empty")
        if not self.symbol:
            logger.error("Trade validation failed: empty symbol", extra={"trade_id": self.trade_id})
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            logger.error(
                "Trade validation failed: invalid quantity",
                extra={"trade_id": self.trade_id, "quantity": str(self.quantity)},
            )
            raise ValueError("Quantity must be positive")
        if self.entry_price < 0:
            logger.error(
                "Trade validation failed: negative entry price",
                extra={"trade_id": self.trade_id, "entry_price": str(self.entry_price)},
            )
            raise ValueError("Entry price cannot be negative")
        if self.exit_price < 0:
            logger.error(
                "Trade validation failed: negative exit price",
                extra={"trade_id": self.trade_id, "exit_price": str(self.exit_price)},
            )
            raise ValueError("Exit price cannot be negative")
        logger.debug(
            "Trade validation passed", extra={"trade_id": self.trade_id, "symbol": self.symbol}
        )

    # ==========================================================================
    # P&L Calculations
    # ==========================================================================

    def get_gross_pnl(self) -> Money:
        """
        Calculate gross profit/loss (before costs).

        Returns:
            Gross P&L
        """
        if self.exit_price == Decimal("0"):
            return Money(amount=Decimal("0"), currency=self.currency)

        price_diff = self.exit_price - self.entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff

        return Money(amount=price_diff * self.quantity, currency=self.currency)

    def get_net_pnl(self) -> Money:
        """
        Calculate net profit/loss (after costs).

        Returns:
            Net P&L
        """
        gross = self.get_gross_pnl().amount
        total_costs = self.commission_paid + self.slippage_cost
        return Money(amount=gross - total_costs, currency=self.currency)

    def get_pnl_percent(self) -> Decimal:
        """
        Calculate P&L as percentage of entry value.

        Returns:
            P&L percentage
        """
        entry_value = self.quantity * self.entry_price
        if entry_value == 0:
            return Decimal("0")

        net_pnl = self.get_net_pnl().amount
        return (net_pnl / entry_value) * Decimal("100")

    def get_total_cost(self) -> Money:
        """
        Calculate total cost of the trade.

        Returns:
            Total cost (commission + slippage)
        """
        return Money(
            amount=self.commission_paid + self.slippage_cost,
            currency=self.currency,
        )

    # ==========================================================================
    # Trade Metrics
    # ==========================================================================

    def get_holding_period_days(self) -> int:
        """Get holding period in days."""
        if self.exit_date is None:
            return (datetime.now(timezone.utc) - self.entry_date).days
        return (self.exit_date - self.entry_date).days

    def get_holding_period_hours(self) -> float:
        """Get holding period in hours."""
        if self.exit_date is None:
            delta = datetime.now(timezone.utc) - self.entry_date
        else:
            delta = self.exit_date - self.entry_date
        return delta.total_seconds() / 3600

    def get_risk_reward_ratio(self) -> Decimal | None:
        """
        Calculate risk/reward ratio based on stop loss and take profit.

        Returns:
            R/R ratio, or None if stop loss or take profit not set
        """
        if self.stop_loss is None or self.take_profit is None:
            return None

        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)

        if risk == 0:
            return None

        return reward / risk

    def get_actual_r_reward(self) -> Decimal | None:
        """
        Calculate actual risk/reward ratio based on actual P&L.

        Returns:
            Actual R/R ratio
        """
        if self.stop_loss is None:
            return None

        risk_amount = abs(self.entry_price - self.stop_loss) * self.quantity
        reward_amount = self.get_net_pnl().amount

        if risk_amount == 0:
            return None

        return reward_amount / risk_amount

    def is_profitable(self) -> bool:
        """Check if trade was profitable."""
        return self.get_net_pnl().amount > 0

    def is_winner(self) -> bool:
        """Check if trade was a winner (synonym for is_profitable)."""
        return self.is_profitable()

    def is_loser(self) -> bool:
        """Check if trade was a loser."""
        return self.get_net_pnl().amount < 0

    def is_break_even(self) -> bool:
        """Check if trade broke even (within small tolerance)."""
        return abs(self.get_net_pnl().amount) < Decimal("0.01")

    # ==========================================================================
    # Trade Status
    # ==========================================================================

    def is_open(self) -> bool:
        """Check if trade is still open (no exit)."""
        return self.exit_date is None or self.exit_price == Decimal("0")

    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return not self.is_open()

    def is_long(self) -> bool:
        """Check if this is a long trade."""
        return self.side == PositionSide.LONG

    def is_short(self) -> bool:
        """Check if this is a short trade."""
        return self.side == PositionSide.SHORT

    # ==========================================================================
    # Factory Methods
    # ==========================================================================

    @classmethod
    def from_position(
        cls,
        trade_id: str,
        position_quantity: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
        symbol: str,
        side: PositionSide,
        entry_date: datetime,
        exit_date: datetime,
        exit_reason: ExitReason | None = None,
        commission: Decimal | None = None,
        strategy_name: str | None = None,
    ) -> Trade:
        """
        Create a Trade from a closed position.

        Args:
            trade_id: Unique trade identifier
            position_quantity: Quantity traded
            entry_price: Entry price
            exit_price: Exit price
            symbol: Trading symbol
            side: Long or short
            entry_date: Entry date
            exit_date: Exit date
            exit_reason: Reason for exit
            commission: Commission paid
            strategy_name: Strategy that generated the trade

        Returns:
            Trade instance
        """
        if commission is None:
            commission = Decimal("0")
        logger.info(
            "Creating trade from position",
            extra={
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side.value,
                "quantity": str(position_quantity),
                "entry_price": str(entry_price),
                "exit_price": str(exit_price),
            },
        )
        return cls(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=position_quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=entry_date,
            exit_date=exit_date,
            exit_reason=exit_reason,
            commission_paid=commission,
            status=TradeStatus.FILLED,
            strategy_name=strategy_name,
        )

    @classmethod
    def create_long(
        cls,
        trade_id: str,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
        entry_date: datetime | None = None,
        exit_date: datetime | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        commission: Decimal | None = None,
        strategy_name: str | None = None,
    ) -> Trade:
        """Create a long trade."""
        if commission is None:
            commission = Decimal("0")
        logger.info(
            "Creating long trade",
            extra={
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "LONG",
                "quantity": str(quantity),
                "entry_price": str(entry_price),
                "exit_price": str(exit_price),
            },
        )
        return cls(
            trade_id=trade_id,
            symbol=symbol,
            side=PositionSide.LONG,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=entry_date or datetime.now(timezone.utc),
            exit_date=exit_date,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission_paid=commission,
            status=TradeStatus.FILLED,
            strategy_name=strategy_name,
        )

    @classmethod
    def create_short(
        cls,
        trade_id: str,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
        entry_date: datetime | None = None,
        exit_date: datetime | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        commission: Decimal | None = None,
        strategy_name: str | None = None,
    ) -> Trade:
        """Create a short trade."""
        if commission is None:
            commission = Decimal("0")
        logger.info(
            "Creating short trade",
            extra={
                "trade_id": trade_id,
                "symbol": symbol,
                "side": "SHORT",
                "quantity": str(quantity),
                "entry_price": str(entry_price),
                "exit_price": str(exit_price),
            },
        )
        return cls(
            trade_id=trade_id,
            symbol=symbol,
            side=PositionSide.SHORT,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=entry_date or datetime.now(timezone.utc),
            exit_date=exit_date,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission_paid=commission,
            status=TradeStatus.FILLED,
            strategy_name=strategy_name,
        )

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "entry_price": str(self.entry_price),
            "exit_price": str(self.exit_price),
            "currency": self.currency,
            "entry_date": self.entry_date.isoformat(),
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "status": self.status.value,
            "trade_type": self.trade_type.value,
            "gross_pnl": str(self.get_gross_pnl().amount),
            "net_pnl": str(self.get_net_pnl().amount),
            "pnl_percent": str(self.get_pnl_percent()),
            "total_cost": str(self.get_total_cost().amount),
            "commission_paid": str(self.commission_paid),
            "slippage_cost": str(self.slippage_cost),
            "holding_period_days": self.get_holding_period_days(),
            "stop_loss": str(self.stop_loss) if self.stop_loss else None,
            "take_profit": str(self.take_profit) if self.take_profit else None,
            "strategy_name": self.strategy_name,
            "is_profitable": self.is_profitable(),
        }

    def __str__(self) -> str:
        """String representation."""
        side_str = "LONG" if self.side == PositionSide.LONG else "SHORT"
        pnl_str = (
            f"+${self.get_net_pnl().amount:.2f}"
            if self.is_profitable()
            else f"-${abs(self.get_net_pnl().amount):.2f}"
        )
        return (
            f"{side_str} {self.symbol} {self.quantity} @ ${self.entry_price} "
            f"→ ${self.exit_price} | {pnl_str} ({self.get_pnl_percent():.2f}%)"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Trade(trade_id='{self.trade_id}', "
            f"symbol='{self.symbol}', "
            f"side={self.side}, "
            f"pnl=${self.get_net_pnl().amount:.2f})"
        )
