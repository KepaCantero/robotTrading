"""
Portfolio Entity - Core business object

A Portfolio represents a collection of positions with associated
capital, risk parameters, and trading constraints.

Reference: Rule 05-architecture.md, Rule 03-solid-principles.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from app.shared.config.centralized_config import get_config
from app.domain.entities.position import Position, PositionSide, PositionStatus
from app.domain.value_objects.capital import Capital
from app.domain.value_objects.money import Money
from app.domain.value_objects.risk_parameters import RiskParameters

logger = logging.getLogger(__name__)


class PortfolioStatus(str, Enum):
    """Portfolio status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    FROZEN = "frozen"


@dataclass
class Portfolio:
    """
    Portfolio entity representing a trading portfolio.

    This is a pure domain entity that maintains business rules
    and invariants for portfolio management.

    Key behaviors:
    - Position management (add, remove, update)
    - Risk management (exposure limits, position sizing)
    - P&L calculation and tracking
    - Portfolio rebalancing
    """

    # Identity
    portfolio_id: str

    # Capital and risk
    capital: Capital
    risk_parameters: RiskParameters

    # State
    status: PortfolioStatus = PortfolioStatus.ACTIVE
    positions: Dict[str, Position] = field(default_factory=dict)

    # Metadata
    broker: str = ""
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Optional logger for audit logging (dependency injection)
    _audit_logger: Optional[logging.Logger] = None

    def __post_init__(self):
        """Validate portfolio invariants."""
        if not self.portfolio_id:
            raise ValueError("Portfolio ID cannot be empty")
        if self.capital.amount <= 0:
            raise ValueError("Initial capital must be positive")

        # Ensure positions dict is initialized
        if self.positions is None:
            self.positions = {}

    # ==========================================================================
    # Position Management
    # ==========================================================================

    def set_audit_logger(self, audit_logger: logging.Logger) -> None:
        """
        Set the audit logger for this portfolio instance.

        Args:
            audit_logger: Logger instance to use for audit logging
        """
        self._audit_logger = audit_logger

    def _audit_log(self, action: str, details: Dict[str, Any]) -> None:
        """
        Log audit trail for trading operations.

        Args:
            action: Action being performed (e.g., "ADD_POSITION", "REMOVE_POSITION")
            details: Dictionary containing operation details
        """
        log_data = {
            "portfolio_id": self.portfolio_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details,
        }

        if self._audit_logger:
            self._audit_logger.info("Portfolio audit: %s", log_data)
        else:
            # Fallback to module logger if no audit logger is set
            logger.info("Portfolio audit: %s", log_data)

    def add_position(self, position: Position) -> None:
        """
        Add a position to the portfolio.

        Args:
            position: Position to add

        Raises:
            ValueError: If position validation fails
        """
        # Business rule: Check if adding position would exceed risk limits
        allowed, reason = self.can_add_position(position)
        if not allowed:
            self._audit_log(
                "ADD_POSITION_REJECTED",
                {
                    "symbol": position.symbol,
                    "quantity": str(position.quantity),
                    "price": str(position.avg_entry_price),
                    "reason": reason,
                },
            )
            raise ValueError(f"Position {position.symbol} exceeds risk parameters. {reason}")

        # Check if position already exists
        if position.symbol in self.positions:
            # Add to existing position
            existing = self.positions[position.symbol]
            existing.add_shares(position.quantity, position.avg_entry_price)
            self._audit_log(
                "ADD_TO_POSITION",
                {
                    "symbol": position.symbol,
                    "added_quantity": str(position.quantity),
                    "price": str(position.avg_entry_price),
                    "new_total_quantity": str(existing.quantity),
                },
            )
        else:
            # Add new position
            self.positions[position.symbol] = position
            self._audit_log(
                "NEW_POSITION",
                {
                    "symbol": position.symbol,
                    "quantity": str(position.quantity),
                    "price": str(position.avg_entry_price),
                    "side": position.side.value,
                },
            )

        self._mark_updated()

    def remove_position(self, symbol: str, quantity: Optional[Decimal] = None) -> None:
        """
        Remove a position or part of a position.

        Args:
            symbol: Symbol of position to remove
            quantity: Quantity to remove (None = full position)

        Note:
            If symbol doesn't exist, this method returns silently (no-op).
        """
        if symbol not in self.positions:
            # Silently return if position doesn't exist (no-op)
            self._audit_log(
                "REMOVE_POSITION_NOT_FOUND",
                {
                    "symbol": symbol,
                    "quantity": str(quantity) if quantity else "FULL",
                    "note": "Position not found, no-op performed",
                },
            )
            return

        position = self.positions[symbol]

        if quantity is None or quantity >= position.quantity:
            # Full exit
            self._audit_log(
                "CLOSE_POSITION",
                {
                    "symbol": symbol,
                    "quantity": str(position.quantity),
                    "price": str(position.current_price),
                    "exit_type": "full",
                },
            )
            position.quantity = Decimal("0")
            position.status = PositionStatus.CLOSED
            position.exit_date = datetime.now(timezone.utc)
            del self.positions[symbol]
        else:
            # Partial exit
            self._audit_log(
                "REDUCE_POSITION",
                {
                    "symbol": symbol,
                    "removed_quantity": str(quantity),
                    "price": str(position.current_price),
                    "previous_quantity": str(position.quantity),
                },
            )
            position.remove_shares(quantity, position.current_price)

        self._mark_updated()

    def update_position_price(self, symbol: str, new_price: Decimal) -> None:
        """
        Update current price for a position.

        Args:
            symbol: Symbol to update
            new_price: New current price

        Raises:
            ValueError: If symbol not found or price invalid
        """
        if symbol not in self.positions:
            self._audit_log(
                "UPDATE_PRICE_FAILED",
                {
                    "symbol": symbol,
                    "new_price": str(new_price),
                    "error": f"Position {symbol} not found in portfolio",
                },
            )
            raise ValueError(f"Position {symbol} not found in portfolio")

        old_price = self.positions[symbol].current_price
        self.positions[symbol].update_price(new_price)

        self._audit_log(
            "UPDATE_POSITION_PRICE",
            {
                "symbol": symbol,
                "old_price": str(old_price),
                "new_price": str(new_price),
                "quantity": str(self.positions[symbol].quantity),
            },
        )

        self._mark_updated()

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol."""
        return self.positions.get(symbol)

    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return [p for p in self.positions.values() if p.is_open()]

    def get_closed_positions(self) -> List[Position]:
        """Get all closed positions (not stored by default)."""
        return [p for p in self.positions.values() if p.is_closed()]

    def iterate_positions(self) -> Iterator[Position]:
        """Iterate over all positions."""
        return iter(self.positions.values())

    # ==========================================================================
    # Portfolio Value & P&L
    # ==========================================================================

    def get_total_value(self) -> Money:
        """
        Calculate total portfolio value.

        Includes capital + open positions value (unrealized P&L model).
        """
        # Total value = initial capital + positions value
        # This tracks: starting capital + unrealized P&L
        return Money(
            amount=self.capital.amount + self.get_positions_value(), currency=self.currency
        )

    def get_cash(self) -> Decimal:
        """
        Get available cash.

        Returns initial capital amount (in this simplified model).
        """
        return self.capital.amount

    def get_positions_value(self) -> Decimal:
        """Calculate total value of all positions at current prices."""
        return sum(
            (p.get_value().amount for p in self.positions.values()),
            start=Decimal("0"),
        )

    def get_total_pnl(self) -> Money:
        """Calculate total portfolio P&L (realized + unrealized)."""
        total = Decimal("0")
        for position in self.positions.values():
            if position.is_closed():
                total += position.get_realized_pnl_amount()
            else:
                total += position.get_unrealized_pnl_amount()
        return Money(amount=abs(total), currency=self.currency)

    def get_unrealized_pnl(self) -> Money:
        """Calculate unrealized P&L from open positions."""
        total = Decimal("0")
        for position in self.positions.values():
            if position.is_open():
                total += position.get_unrealized_pnl_amount()
        return Money(amount=abs(total), currency=self.currency)

    def get_realized_pnl(self) -> Money:
        """Calculate realized P&L from closed positions."""
        total = Decimal("0")
        for position in self.positions.values():
            if position.is_closed():
                total += position.get_realized_pnl_amount()
        return Money(amount=abs(total), currency=self.currency)

    def get_total_return_percent(self) -> Decimal:
        """Calculate total return as percentage of initial capital."""
        if self.capital.amount == 0:
            return Decimal("0")

        current_value = self.get_total_value().amount
        return ((current_value - self.capital.amount) / self.capital.amount) * Decimal("100")

    # ==========================================================================
    # Risk Management
    # ==========================================================================

    def get_exposure(self) -> Decimal:
        """Calculate total portfolio exposure (long - short)."""
        gross_exposure = Decimal("0")
        for position in self.positions.values():
            if position.side == PositionSide.LONG:
                gross_exposure += position.get_value().amount
            else:  # SHORT
                gross_exposure -= position.get_value().amount
        return gross_exposure

    def get_gross_exposure(self) -> Decimal:
        """Calculate gross exposure (absolute value of all positions)."""
        return sum(
            (abs(p.get_value().amount) for p in self.positions.values()),
            start=Decimal("0"),
        )

    def get_portfolio_beta(self) -> Decimal:
        """
        Calculate portfolio beta (simplified).

        Returns 1.0 as placeholder. Real implementation would
        use individual position betas weighted by position size.
        """
        return Decimal("1.0")

    def is_risk_limit_exceeded(self, additional_exposure: Decimal = Decimal("0")) -> bool:
        """
        Check if risk limits would be exceeded.

        Args:
            additional_exposure: Additional exposure to consider

        Returns:
            True if risk limits exceeded

        Note:
            max_portfolio_exposure can be:
            - A multiplier ≤ 2 (e.g., 1.5 = 150% of capital)
            - An absolute value > capital (e.g., 150000 = $150,000)

            Heuristic: If max_portfolio_exposure >= capital, treat as absolute.
        """
        total_exposure = self.get_gross_exposure() + additional_exposure

        # Smart interpretation of max_portfolio_exposure
        # If >= capital, treat as absolute value; otherwise as multiplier
        if self.risk_parameters.max_portfolio_exposure >= self.capital.amount:
            # Treat as absolute value
            max_exposure = self.risk_parameters.max_portfolio_exposure
        else:
            # Treat as multiplier of capital
            max_exposure = self.capital.amount * self.risk_parameters.max_portfolio_exposure

        return total_exposure > max_exposure

    def get_concentration(self, symbol: str) -> Decimal:
        """
        Get concentration of a single position.

        Returns position value as percentage of total portfolio value.
        """
        if symbol not in self.positions:
            return Decimal("0")

        position_value = self.positions[symbol].get_value().amount
        total_value = self.get_total_value().amount

        if total_value == 0:
            return Decimal("0")

        return (position_value / total_value) * Decimal("100")

    def get_max_concentration(self) -> tuple[str, Decimal]:
        """
        Get the position with highest concentration.

        Returns:
            Tuple of (symbol, concentration_percent)
        """
        if not self.positions:
            return ("", Decimal("0"))

        max_symbol = ""
        max_concentration = Decimal("0")

        for symbol in self.positions:
            concentration = self.get_concentration(symbol)
            if concentration > max_concentration:
                max_concentration = concentration
                max_symbol = symbol

        return (max_symbol, max_concentration)

    def is_position_size_allowed(self, position_value: Decimal) -> bool:
        """Check if position size is within risk limits."""
        # max_position_size is a percentage of capital
        max_position_value = self.capital.amount * self.risk_parameters.max_position_size
        return position_value <= max_position_value

    def can_add_position(self, position: Position) -> tuple[bool, str]:
        """
        Check if position can be added without violating risk limits.

        Returns:
            Tuple of (allowed, reason)
        """
        # Check position size
        position_value = position.get_value().amount
        max_position_value = self.capital.amount * self.risk_parameters.max_position_size
        if position_value > max_position_value:
            return (
                False,
                f"Position size ${position_value} exceeds max ${max_position_value} ({self.risk_parameters.max_position_size * 100}% of capital)",
            )

        # Check portfolio exposure
        if self.is_risk_limit_exceeded(position_value):
            current_gross_exposure = self.get_gross_exposure()
            # Calculate max_exposure the same way as is_risk_limit_exceeded
            if self.risk_parameters.max_portfolio_exposure >= self.capital.amount:
                max_exposure = self.risk_parameters.max_portfolio_exposure
                exposure_pct = ""
            else:
                max_exposure = self.capital.amount * self.risk_parameters.max_portfolio_exposure
                exposure_pct = f" ({self.risk_parameters.max_portfolio_exposure * 100}% of capital)"
            return (
                False,
                f"Adding position would exceed max portfolio exposure of ${max_exposure}{exposure_pct}. Current exposure: ${current_gross_exposure}, new position: ${position_value}",
            )

        # Check max positions
        if len(self.get_open_positions()) >= self.capital.max_positions:
            return (
                False,
                f"Maximum number of positions ({self.capital.max_positions}) reached",
            )

        return (True, "")

    # ==========================================================================
    # Portfolio Status
    # ==========================================================================

    def freeze(self) -> None:
        """Freeze portfolio (no new positions allowed)."""
        self.status = PortfolioStatus.FROZEN
        self._mark_updated()

    def unfreeze(self) -> None:
        """Unfreeze portfolio."""
        if self.status == PortfolioStatus.FROZEN:
            self.status = PortfolioStatus.ACTIVE
            self._mark_updated()

    def suspend(self) -> None:
        """Suspend portfolio (no trading)."""
        self.status = PortfolioStatus.SUSPENDED
        self._mark_updated()

    def activate(self) -> None:
        """Activate portfolio for trading."""
        if self.status in [PortfolioStatus.SUSPENDED, PortfolioStatus.FROZEN]:
            self.status = PortfolioStatus.ACTIVE
            self._mark_updated()

    def close(self) -> None:
        """Close portfolio and liquidate all positions."""
        self.status = PortfolioStatus.CLOSED
        for position in self.positions.values():
            if position.is_open():
                position.status = PositionStatus.CLOSED
                position.exit_date = datetime.now(timezone.utc)
        self._mark_updated()

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _validate_position_risk(self, position: Position) -> bool:
        """Validate position against risk parameters."""
        # Check position size - max_position_size is a percentage of capital
        position_value = position.get_value().amount
        max_position_value = self.capital.amount * self.risk_parameters.max_position_size
        if position_value > max_position_value:
            return False

        # Check total exposure - max_portfolio_exposure is a multiplier of capital
        if self.is_risk_limit_exceeded(position_value):
            return False

        # Check max positions
        if len(self.get_open_positions()) >= self.capital.max_positions:
            return False

        return True

    def _mark_updated(self) -> None:
        """Mark portfolio as updated."""
        self.updated_at = datetime.now(timezone.utc)

    # ==========================================================================
    # Factory Methods & Serialization
    # ==========================================================================

    @classmethod
    def create(
        cls,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        max_position_size_pct: Decimal = Decimal("0.2"),
        max_portfolio_exposure_pct: Decimal = Decimal("0.8"),
    ) -> Portfolio:
        """
        Factory to create a new portfolio.

        Args:
            portfolio_id: Unique portfolio identifier
            initial_capital: Initial capital amount
            currency: Base currency
            max_position_size_pct: Max position size as percentage
            max_portfolio_exposure_pct: Max portfolio exposure as percentage

        Returns:
            New Portfolio instance
        """
        # Create Capital value object
        capital = Capital.from_amount(initial_capital, currency)

        # Create RiskParameters
        max_position_size = initial_capital * max_position_size_pct
        max_portfolio_exposure = initial_capital * max_portfolio_exposure_pct

        # Get default risk parameters from centralized config
        try:
            config = get_config()
            stop_loss_pct = Decimal(str(getattr(
                config.trading, 'stop_loss_pct', 0.05
            )))
            take_profit_pct = Decimal(str(getattr(
                config.trading, 'take_profit_pct', 0.10
            )))
        except (AttributeError, ValueError) as e:
            logger.warning(f"Error loading trading config for portfolio creation: {e}, using defaults")
            stop_loss_pct = Decimal('0.05')
            take_profit_pct = Decimal('0.10')

        risk_params = RiskParameters(
            max_position_size=max_position_size,
            max_portfolio_exposure=max_portfolio_exposure,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )

        return cls(
            portfolio_id=portfolio_id,
            capital=capital,
            risk_parameters=risk_params,
            currency=currency,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "portfolio_id": self.portfolio_id,
            "status": self.status.value,
            "currency": self.currency,
            "capital": {
                "amount": str(self.capital.amount),
                "tier": self.capital.tier.value,
            },
            "total_value": str(self.get_total_value().amount),
            "cash": str(self.get_cash()),
            "positions_value": str(self.get_positions_value()),
            "total_pnl": str(self.get_total_pnl().amount),
            "total_return_pct": str(self.get_total_return_percent()),
            "num_positions": len(self.get_open_positions()),
            "gross_exposure": str(self.get_gross_exposure()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Portfolio(id={self.portfolio_id}, "
            f"value=${self.get_total_value().amount:.2f}, "
            f"pnl={self.get_total_return_percent():.2f}%, "
            f"positions={len(self.get_open_positions())})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Portfolio(portfolio_id='{self.portfolio_id}', "
            f"capital={self.capital.amount} {self.currency}, "
            f"status={self.status})"
        )
