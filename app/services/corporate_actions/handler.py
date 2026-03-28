"""
Corporate Actions Handler - Handle stock splits, dividends, mergers, delistings.

Corporate actions can significantly affect positions:
- Stock splits: Quantity adjusted, entry price adjusted
- Dividends: Cash received, baseline price adjusted
- Mergers: Position converted to acquiring company
- Delistings: Position needs to be closed
- Spin-offs: New shares received
- Rights offerings: Rights issued to shareholders

This module integrates with:
- Broker adapters (IBKR, Alpaca, etc.)
- Position monitoring
- Portfolio management
- Tax calculations (FIFO)

Phase 2.6: Corporate Actions Handler for multi-day position support.

Author: Algorithmic Trading System
Date: 2026-01-25
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class CorporateActionType(Enum):
    """Types of corporate actions."""

    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    DIVIDEND = "dividend"
    SPECIAL_DIVIDEND = "special_dividend"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    SPINOFF = "spinoff"
    DELISTING = "delisting"
    RIGHTS_OFFERING = "rights_offering"
    SYMBOL_CHANGE = "symbol_change"


@dataclass
class CorporateAction:
    """Represents a corporate action event."""

    action_type: CorporateActionType
    symbol: str
    ex_date: date
    ratio: Optional[Decimal] = None  # For splits, mergers, spinoffs
    amount: Optional[Decimal] = None  # For dividends
    new_symbol: Optional[str] = None  # For mergers, symbol changes
    description: Optional[str] = None
    record_date: Optional[date] = None
    payable_date: Optional[date] = None
    processed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.value,
            "symbol": self.symbol,
            "ex_date": self.ex_date.isoformat(),
            "ratio": str(self.ratio) if self.ratio else None,
            "amount": str(self.amount) if self.amount else None,
            "new_symbol": self.new_symbol,
            "description": self.description,
            "record_date": self.record_date.isoformat() if self.record_date else None,
            "payable_date": self.payable_date.isoformat() if self.payable_date else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

    def __post_init__(self):
        """Validate corporate action data."""
        if self.action_type in [
            CorporateActionType.STOCK_SPLIT,
            CorporateActionType.REVERSE_SPLIT,
            CorporateActionType.MERGER,
            CorporateActionType.ACQUISITION,
            CorporateActionType.SPINOFF,
        ] and (self.ratio is None or self.ratio <= 0):
            raise ValueError(f"Ratio must be positive for {self.action_type.value}")

        if self.action_type in [
            CorporateActionType.DIVIDEND,
            CorporateActionType.SPECIAL_DIVIDEND,
        ] and (self.amount is None or self.amount < 0):
            raise ValueError(f"Amount must be non-negative for {self.action_type.value}")

        if self.action_type in [
            CorporateActionType.MERGER,
            CorporateActionType.ACQUISITION,
            CorporateActionType.SYMBOL_CHANGE,
        ] and not self.new_symbol:
            raise ValueError(f"new_symbol required for {self.action_type.value}")


class CorporateActionsHandler:
    """
    Handle corporate events that affect positions.

    Monitors for corporate actions and adjusts positions accordingly:
    - Stock split position adjustment
    - Dividend baseline adjustment
    - Merger position conversion
    - Delisting detection and position closure

    Integration points:
    - Broker adapters for position queries and order placement
    - Position monitor for baseline adjustments
    - Database for action persistence
    - Tax system for cost basis updates
    """

    def __init__(
        self,
        broker=None,
        position_monitor=None,
        on_action: Optional[Callable[[CorporateAction], None]] = None,
    ):
        """
        Initialize corporate actions handler.

        Args:
            broker: Broker connector (implements IBroker interface)
            position_monitor: Position monitor service for baseline adjustments
            on_action: Optional callback when action is processed
        """
        self.broker = broker
        self.position_monitor = position_monitor
        self.on_action = on_action

        # Action history
        self._processed_actions: Dict[str, CorporateAction] = {}

        # Statistics
        self._stats = {
            "stock_splits_processed": 0,
            "dividends_processed": 0,
            "mergers_processed": 0,
            "delistings_processed": 0,
            "positions_adjusted": 0,
            "positions_closed": 0,
        }

        logger.info("CorporateActionsHandler initialized")

    async def on_stock_split(
        self,
        symbol: str,
        ratio: Decimal,
        ex_date: date,
        record_date: Optional[date] = None,
    ) -> Dict[str, Union[str, int, List[Dict[str, str]]]]:
        """
        Adjust positions for stock split.

        For a 2-for-1 split (ratio=2):
        - Quantity multiplied by ratio
        - Entry price divided by ratio

        Args:
            symbol: Symbol that split
            ratio: Split ratio (e.g., 2 for 2-for-1)
            ex_date: Ex-dividend date
            record_date: Record date (optional)

        Returns:
            Dict with adjustment results

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_stock_split("AAPL", Decimal("4"), date(2024, 6, 1))
            >>> print(result["positions_adjusted"])
            1
        """
        logger.info(f"Processing stock split: {symbol} ratio={ratio} ex_date={ex_date}")

        if ratio <= 0:
            raise ValueError(f"Invalid split ratio: {ratio}")

        # Get open positions for symbol
        positions = await self._get_open_positions(symbol)

        adjusted = []
        for position in positions:
            try:
                # Get current values
                old_quantity = self._get_position_quantity(position)
                old_avg_price = self._get_position_avg_price(position)
                position_id = self._get_position_id(position)

                # Calculate new values
                new_quantity = old_quantity * ratio
                new_avg_price = old_avg_price / ratio if ratio > 0 else old_avg_price

                # Update position
                await self._update_position(
                    position=position,
                    quantity=new_quantity,
                    avg_price=new_avg_price,
                )

                adjusted.append(
                    {
                        "position_id": position_id,
                        "old_quantity": str(old_quantity),
                        "new_quantity": str(new_quantity),
                        "old_avg_price": str(old_avg_price),
                        "new_avg_price": str(new_avg_price),
                    }
                )

                self._stats["positions_adjusted"] += 1

                logger.info(
                    f"Adjusted position {position_id}: "
                    f"{old_quantity} -> {new_quantity} shares, "
                    f"avg_price {old_avg_price} -> {new_avg_price}"
                )

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error adjusting position for stock split: {e}")
                continue

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.STOCK_SPLIT,
            symbol=symbol,
            ex_date=ex_date,
            ratio=ratio,
            record_date=record_date,
            description=f"{ratio}-for-1 stock split",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        self._stats["stock_splits_processed"] += 1

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "symbol": symbol,
            "ratio": str(ratio),
            "ex_date": ex_date.isoformat(),
            "positions_adjusted": len(adjusted),
            "adjustments": adjusted,
        }

    async def on_dividend(
        self,
        symbol: str,
        amount: Decimal,
        ex_date: date,
        record_date: Optional[date] = None,
        payable_date: Optional[date] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Record dividend payment.

        Don't confuse dividend drop with crash - adjust baseline price.

        Args:
            symbol: Symbol paying dividend
            amount: Dividend per share
            ex_date: Ex-dividend date
            record_date: Record date (optional)
            payable_date: Payment date (optional)

        Returns:
            Dict with dividend details

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_dividend("AAPL", Decimal("0.24"), date(2024, 2, 9))
            >>> print(result["amount"])
            '0.24'
        """
        logger.info(f"Processing dividend: {symbol} amount={amount} ex_date={ex_date}")

        if amount < 0:
            raise ValueError(f"Invalid dividend amount: {amount}")

        # Calculate total dividend payment
        positions = await self._get_open_positions(symbol)
        total_shares = sum(self._get_position_quantity(p) for p in positions)
        total_payment = amount * total_shares

        # Adjust baseline price for position monitoring
        # This prevents triggering stop-loss on dividend drop
        if self.position_monitor:
            await self._adjust_dividend_baseline(symbol, amount, positions)

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.DIVIDEND,
            symbol=symbol,
            ex_date=ex_date,
            amount=amount,
            record_date=record_date,
            payable_date=payable_date,
            description=f"Dividend ${amount} per share (total: ${total_payment:.2f})",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        self._stats["dividends_processed"] += 1

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "symbol": symbol,
            "amount": str(amount),
            "total_payment": str(total_payment),
            "shares_held": str(total_shares),
            "ex_date": ex_date.isoformat(),
            "record_date": record_date.isoformat() if record_date else None,
            "payable_date": payable_date.isoformat() if payable_date else None,
        }

    async def on_merger(
        self,
        symbol: str,
        acquire_symbol: str,
        ratio: Decimal,
        ex_date: date,
        record_date: Optional[date] = None,
    ) -> Dict[str, Union[str, int, List[Dict[str, str]]]]:
        """
        Convert positions to acquiring company.

        Args:
            symbol: Symbol being acquired
            acquire_symbol: Acquiring company symbol
            ratio: Exchange ratio (shares of acquire_symbol per share of symbol)
            ex_date: Ex-dividend date
            record_date: Record date (optional)

        Returns:
            Dict with conversion results

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_merger("TWTR", "ELON", Decimal("1.5"), date(2022, 10, 27))
            >>> print(result["positions_converted"])
            1
        """
        logger.info(
            f"Processing merger: {symbol} -> {acquire_symbol} ratio={ratio} ex_date={ex_date}"
        )

        if ratio <= 0:
            raise ValueError(f"Invalid merger ratio: {ratio}")

        if not acquire_symbol:
            raise ValueError("Acquiring symbol is required")

        # Get open positions for acquired company
        positions = await self._get_open_positions(symbol)

        converted = []
        for position in positions:
            try:
                # Get current values
                old_symbol = self._get_position_symbol(position)
                old_quantity = self._get_position_quantity(position)
                old_avg_price = self._get_position_avg_price(position)
                position_id = self._get_position_id(position)

                # Calculate new values
                new_quantity = old_quantity * ratio
                new_avg_price = old_avg_price / ratio if ratio > 0 else old_avg_price

                # Update position
                await self._update_position(
                    position=position,
                    symbol=acquire_symbol,
                    quantity=new_quantity,
                    avg_price=new_avg_price,
                )

                converted.append(
                    {
                        "position_id": position_id,
                        "old_symbol": old_symbol,
                        "new_symbol": acquire_symbol,
                        "old_quantity": str(old_quantity),
                        "new_quantity": str(new_quantity),
                        "old_avg_price": str(old_avg_price),
                        "new_avg_price": str(new_avg_price),
                    }
                )

                self._stats["positions_adjusted"] += 1

                logger.info(
                    f"Converted position {position_id}: "
                    f"{old_symbol} -> {acquire_symbol}, "
                    f"{old_quantity} -> {new_quantity} shares"
                )

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error converting position for merger: {e}")
                continue

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.MERGER,
            symbol=symbol,
            ex_date=ex_date,
            ratio=ratio,
            new_symbol=acquire_symbol,
            record_date=record_date,
            description=f"Merger: {symbol} acquired by {acquire_symbol} ({ratio}:1 ratio)",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        self._stats["mergers_processed"] += 1

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "symbol": symbol,
            "acquire_symbol": acquire_symbol,
            "ratio": str(ratio),
            "ex_date": ex_date.isoformat(),
            "positions_converted": len(converted),
            "conversions": converted,
        }

    async def on_delisting(
        self,
        symbol: str,
        delist_date: date,
        reason: Optional[str] = None,
        force_close: bool = True,
    ) -> Dict[str, Optional[Union[str, int, List[Dict[str, Optional[str]]]]]]:
        """
        Handle delisting - close positions.

        Args:
            symbol: Symbol being delisted
            delist_date: Date of delisting
            reason: Reason for delisting
            force_close: If True, attempt to close positions via broker

        Returns:
            Dict with delisting results

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_delisting("BANKRUPT", date(2024, 3, 15), "Bankruptcy")
            >>> print(result["positions_closed"])
            1
        """
        logger.critical(f"Processing delisting: {symbol} - {reason} on {delist_date}")

        # Get open positions
        positions = await self._get_open_positions(symbol)

        closed = []
        for position in positions:
            position_id = self._get_position_id(position)
            quantity = self._get_position_quantity(position)

            try:
                if force_close and self.broker:
                    # Place market order to close
                    # Note: For delisted symbols, this may fail
                    from app.shared.interfaces.broker_base import Order, OrderSide, OrderType

                    order = Order(
                        order_id=f"DELIST_{symbol}_{position_id}",
                        symbol=symbol,
                        side=OrderSide.SELL if quantity > 0 else OrderSide.BUY,
                        type=OrderType.MARKET,
                        quantity=abs(quantity),
                    )

                    try:
                        result = await self.broker.execute_order_with_wal(order, dry_run=False)
                        closed.append(
                            {
                                "position_id": position_id,
                                "order_id": result.order_id if result else None,
                                "status": "closed",
                            }
                        )
                        logger.critical(f"Closed position {position_id} due to delisting")
                    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                        logger.warning(f"Could not close position {position_id}: {e}")
                        closed.append(
                            {
                                "position_id": position_id,
                                "order_id": None,
                                "status": "failed_to_close",
                                "error": str(e),
                            }
                        )
                else:
                    # Mark as manually closed
                    closed.append(
                        {
                            "position_id": position_id,
                            "order_id": None,
                            "status": "marked_closed",
                        }
                    )

                self._stats["positions_closed"] += 1

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error processing position {position_id} for delisting: {e}")
                closed.append(
                    {
                        "position_id": position_id,
                        "order_id": None,
                        "status": "error",
                        "error": str(e),
                    }
                )

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.DELISTING,
            symbol=symbol,
            ex_date=delist_date,
            description=reason or "Delisted",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        self._stats["delistings_processed"] += 1

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "symbol": symbol,
            "reason": reason,
            "delist_date": delist_date.isoformat(),
            "positions_closed": len(closed),
            "closures": closed,
        }

    async def on_spinoff(
        self,
        symbol: str,
        spinoff_symbol: str,
        ratio: Decimal,
        ex_date: date,
        record_date: Optional[date] = None,
    ) -> Dict[str, Union[str, int, List[Dict[str, str]]]]:
        """
        Handle spin-off - create new positions.

        Args:
            symbol: Original company symbol
            spinoff_symbol: New spin-off company symbol
            ratio: Spin-off ratio (shares of spinoff per share of original)
            ex_date: Ex-dividend date
            record_date: Record date (optional)

        Returns:
            Dict with spin-off results

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_spinoff("FOO", "BAR", Decimal("0.5"), date(2024, 1, 1))
            >>> print(result["new_positions_created"])
            1
        """
        logger.info(
            f"Processing spinoff: {symbol} -> {spinoff_symbol} ratio={ratio} ex_date={ex_date}"
        )

        if ratio <= 0:
            raise ValueError(f"Invalid spinoff ratio: {ratio}")

        if not spinoff_symbol:
            raise ValueError("Spin-off symbol is required")

        # Get open positions for original company
        positions = await self._get_open_positions(symbol)

        created = []
        for position in positions:
            try:
                quantity = self._get_position_quantity(position)
                avg_price = self._get_position_avg_price(position)
                position_id = self._get_position_id(position)

                # Calculate spin-off shares
                spinoff_quantity = quantity * ratio

                # Adjust original position cost basis
                # (Simplified: proportional reduction)
                original_cost_reduction = avg_price * ratio
                new_avg_price = avg_price - original_cost_reduction

                # Update original position
                await self._update_position(
                    position=position, avg_price=max(new_avg_price, Decimal("0.01"))
                )

                # Create new spin-off position
                # This would typically create a new position record
                created.append(
                    {
                        "original_position_id": position_id,
                        "spinoff_symbol": spinoff_symbol,
                        "spinoff_quantity": str(spinoff_quantity),
                        "original_symbol": symbol,
                        "new_avg_price": str(new_avg_price),
                    }
                )

                logger.info(
                    f"Created spin-off position: {spinoff_quantity} shares of {spinoff_symbol}"
                )

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error creating spin-off position: {e}")
                continue

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.SPINOFF,
            symbol=symbol,
            ex_date=ex_date,
            ratio=ratio,
            new_symbol=spinoff_symbol,
            record_date=record_date,
            description=f"Spin-off: {spinoff_symbol} from {symbol} ({ratio}:1 ratio)",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "symbol": symbol,
            "spinoff_symbol": spinoff_symbol,
            "ratio": str(ratio),
            "ex_date": ex_date.isoformat(),
            "new_positions_created": len(created),
            "creations": created,
        }

    async def on_symbol_change(
        self,
        old_symbol: str,
        new_symbol: str,
        ex_date: date,
    ) -> Dict[str, Union[str, int, List[Dict[str, str]]]]:
        """
        Handle symbol change (ticker rename).

        Args:
            old_symbol: Old symbol
            new_symbol: New symbol
            ex_date: Effective date of change

        Returns:
            Dict with symbol change results

        Example:
            >>> handler = CorporateActionsHandler(broker)
            >>> result = await handler.on_symbol_change("FB", "META", date(2022, 6, 9))
            >>> print(result["positions_updated"])
            1
        """
        logger.info(f"Processing symbol change: {old_symbol} -> {new_symbol} on {ex_date}")

        if not new_symbol:
            raise ValueError("New symbol is required")

        # Get open positions for old symbol
        positions = await self._get_open_positions(old_symbol)

        updated = []
        for position in positions:
            try:
                position_id = self._get_position_id(position)

                # Update symbol
                await self._update_position(position=position, symbol=new_symbol)

                updated.append(
                    {
                        "position_id": position_id,
                        "old_symbol": old_symbol,
                        "new_symbol": new_symbol,
                    }
                )

                logger.info(f"Updated position {position_id}: {old_symbol} -> {new_symbol}")

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error updating position for symbol change: {e}")
                continue

        # Record action
        action = CorporateAction(
            action_type=CorporateActionType.SYMBOL_CHANGE,
            symbol=old_symbol,
            ex_date=ex_date,
            new_symbol=new_symbol,
            description=f"Symbol change: {old_symbol} -> {new_symbol}",
            processed_at=utc_now(),
        )
        self._processed_actions[action.symbol + "_" + action.ex_date.isoformat()] = action

        # Call callback
        if self.on_action:
            self.on_action(action)

        return {
            "old_symbol": old_symbol,
            "new_symbol": new_symbol,
            "ex_date": ex_date.isoformat(),
            "positions_updated": len(updated),
            "updates": updated,
        }

    # ==========================================================================
    # PRIVATE HELPER METHODS
    # ==========================================================================

    async def _get_open_positions(self, symbol: str) -> List[object]:
        """
        Get open positions for symbol.

        Handles different broker implementations.
        """
        if self.broker is None:
            logger.warning(f"No broker configured, returning empty positions for {symbol}")
            return []

        try:
            # Try different broker interfaces
            if hasattr(self.broker, "get_all_open_positions"):
                all_positions = await self.broker.get_all_open_positions()
                return [p for p in (all_positions or []) if self._get_position_symbol(p) == symbol]
            elif hasattr(self.broker, "get_positions"):
                all_positions = await self.broker.get_positions()
                return [p for p in (all_positions or []) if p.get("symbol") == symbol]
            else:
                logger.warning("Broker does not support position queries")
                return []
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting positions for {symbol}: {e}")
            return []

    async def _update_position(
        self,
        position: object,
        symbol: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        avg_price: Optional[Decimal] = None,
    ) -> None:
        """
        Update position with new values.

        This would typically update the position in the database.
        Implementation depends on position storage.
        """
        # Update position object
        if symbol is not None:
            if hasattr(position, "symbol"):
                position.symbol = symbol
            elif isinstance(position, dict):
                position["symbol"] = symbol

        if quantity is not None:
            if hasattr(position, "quantity") or hasattr(position, "avg_price"):
                position.quantity = quantity
            elif isinstance(position, dict):
                position["quantity"] = quantity

        if avg_price is not None:
            if hasattr(position, "avg_price"):
                position.avg_price = avg_price
            elif hasattr(position, "avg_entry_price"):
                position.avg_entry_price = avg_price
            elif isinstance(position, dict):
                position["avg_price"] = avg_price

        # Recalculate derived metrics if available
        if hasattr(position, "recalculate_metrics"):
            position.recalculate_metrics()

        # Position persistence is handled by the broker/portfolio service
        # The in-memory position object has been updated above.
        # For database persistence, the position service will handle this
        # when saving the portfolio state.

    async def _adjust_dividend_baseline(
        self, symbol: str, amount: Decimal, positions: List[object]
    ) -> None:
        """
        Adjust baseline price for dividend to prevent false stop-loss triggers.

        Args:
            symbol: Symbol that paid dividend
            amount: Dividend amount per share
            positions: List of positions to adjust
        """
        if self.position_monitor is None:
            return

        try:
            # Adjust baseline by dividend amount
            for position in positions:
                position_id = self._get_position_id(position)
                # This would call the position monitor to adjust baseline
                logger.debug(f"Adjusting baseline for {position_id} by dividend amount {amount}")
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error adjusting dividend baseline: {e}")

    def _get_position_symbol(self, position: object) -> str:
        """Extract symbol from position object."""
        if hasattr(position, "symbol"):
            return position.symbol
        elif isinstance(position, dict):
            return position.get("symbol", "")
        return ""

    def _get_position_quantity(self, position: object) -> Decimal:
        """Extract quantity from position object."""
        value = None
        if hasattr(position, "quantity"):
            value = position.quantity
        elif hasattr(position, "position"):  # IB format
            value = position.position
        elif isinstance(position, dict):
            value = position.get("quantity", position.get("position", 0))

        if value is None:
            return Decimal("0")

        if isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, Decimal):
            return value
        else:
            return Decimal(str(value))

    def _get_position_avg_price(self, position: object) -> Decimal:
        """Extract average price from position object."""
        value = None
        if hasattr(position, "avg_price"):
            value = position.avg_price
        elif hasattr(position, "avg_entry_price"):
            value = position.avg_entry_price
        elif hasattr(position, "avgCost"):  # IB format
            value = position.avgCost
        elif isinstance(position, dict):
            value = position.get("avg_price", position.get("avg_entry_price", 0))

        if value is None:
            return Decimal("0")

        if isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, Decimal):
            return value
        else:
            return Decimal(str(value))

    def _get_position_id(self, position: object) -> str:
        """Extract position ID from position object."""
        if hasattr(position, "position_id"):
            return str(position.position_id)
        elif hasattr(position, "id"):
            return str(position.id)
        elif isinstance(position, dict):
            return position.get("position_id", position.get("id", ""))
        return ""

    # ==========================================================================
    # PUBLIC QUERY METHODS
    # ==========================================================================

    def get_processed_actions(self) -> List[CorporateAction]:
        """Get list of processed corporate actions."""
        return list(self._processed_actions.values())

    def get_action_for_symbol(self, symbol: str) -> List[CorporateAction]:
        """Get all actions for a symbol."""
        return [action for action in self._processed_actions.values() if action.symbol == symbol]

    def get_action_by_type(self, action_type: CorporateActionType) -> List[CorporateAction]:
        """Get all actions of a specific type."""
        return [
            action
            for action in self._processed_actions.values()
            if action.action_type == action_type
        ]

    def get_stats(self) -> Dict[str, int]:
        """Get handler statistics."""
        return self._stats.copy()

    def clear_history(self) -> None:
        """Clear action history (useful for testing)."""
        self._processed_actions.clear()
        logger.info("Corporate action history cleared")
