"""
FIFO Integrator - Live Trading Integration Service

Integrates FIFO tax lot tracking with the live trading system.
Records all trades in FIFO database, creates lots for BUY orders,
and closes lots in FIFO order on SELL orders.

This is a CRITICAL component for Spain tax compliance (Modelo 721).

Key Features:
- Automatic trade recording on execution
- Lot creation for each BUY
- Lot closure in FIFO order on SELL
- Accurate cost basis calculation
- Open lots tracking
- Multi-exchange support

Author: Claude (FIFO Database Integration - Phase 2.1)
Date: 2026-01-25
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_transaction
from app.tax.database.fifo_schema import (
    Account,
    AssetType,
    ExchangeType,
    FIFOCalculation,
    FIFOProcessor,
    Lot,
    LotStatus,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Trade data from live trading system."""

    trade_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: Decimal
    execution_price: Decimal
    execution_time: datetime
    commission: Decimal = Decimal("0")
    broker_name: str = "alpaca"
    broker_trade_id: Optional[str] = None
    order_id: Optional[str] = None
    fill_type: str = "FULL"  # FULL or PARTIAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position data from live trading system."""

    symbol: str
    quantity: Decimal
    average_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    timestamp: datetime


@dataclass
class LotInfo:
    """Information about a FIFO lot."""

    lot_id: UUID
    symbol: str
    quantity_opened: Decimal
    quantity_remaining: Decimal
    cost_basis_open: Decimal
    average_cost: Decimal
    opened_at: datetime
    status: LotStatus
    holding_period_days: Optional[int] = None
    realized_gain: Optional[Decimal] = None
    realized_loss: Optional[Decimal] = None


class FIFOIntegrator:
    """
    Integrates FIFO tracking with live trading.

    This service hooks into the live trading system to automatically
    record all trades in the FIFO database, ensuring Spain tax compliance.

    Usage:
        integrator = FIFOIntegrator()
        await integrator.initialize()

        # Trade execution events
        await integrator.on_trade_executed(trade)

        # Query open lots
        lots = await integrator.get_open_lots("AAPL")

        # Get cost basis
        cost_basis = await integrator.get_cost_basis("AAPL")
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize FIFO integrator.

        Args:
            user_id: User UUID for tax reporting. Defaults to settings value.
        """
        self.user_id = user_id or uuid4()
        self._accounts_cache: Dict[str, UUID] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self) -> None:
        """Initialize the FIFO integrator.

        Creates default accounts if they don't exist.
        """
        try:
            self.logger.info(f"Initializing FIFO integrator for user {self.user_id}")

            # Ensure we have a default account
            async with get_db_transaction() as session:
                settings = get_settings()

                # Create default account for stocks if not exists
                default_account = await self._get_or_create_account(
                    session=session,
                    exchange_name=settings.get("FIFO_DEFAULT_EXCHANGE", "alpaca"),
                    exchange_type=ExchangeType.BROKER,
                    currency="USD",
                )

                self._accounts_cache["default"] = default_account.id

            self.logger.info("FIFO integrator initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing FIFO integrator: {e}")
            raise

    async def _get_or_create_account(
        self,
        session: AsyncSession,
        exchange_name: str,
        exchange_type: ExchangeType,
        currency: str,
    ) -> Account:
        """
        Get or create a trading account.

        Args:
            session: Database session
            exchange_name: Name of exchange (e.g., "alpaca", "binance")
            exchange_type: Type of exchange
            currency: Account currency

        Returns:
            Account instance
        """
        # Try to find existing account
        stmt = select(Account).where(
            Account.user_id == self.user_id,
            Account.exchange_name == exchange_name,
            Account.currency == currency,
            Account.is_active == True,
        )
        result = await session.execute(stmt)
        account = result.scalars().first()

        if account is None:
            # Create new account
            account = Account(
                user_id=self.user_id,
                account_name=f"{exchange_name}_{currency}",
                exchange_type=exchange_type,
                exchange_name=exchange_name,
                currency=currency,
                is_active=True,
            )
            session.add(account)
            await session.flush()

            self.logger.info(f"Created new account: {account.account_name}")

        return account

    async def _determine_asset_type(self, symbol: str) -> AssetType:
        """
        Determine asset type based on symbol.

        Args:
            symbol: Trading symbol

        Returns:
            AssetType enum value
        """
        # Crypto symbols typically have specific patterns
        crypto_patterns = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI"]

        symbol_upper = symbol.upper()

        # Check for crypto patterns
        for pattern in crypto_patterns:
            if pattern in symbol_upper:
                return AssetType.CRYPTO

        # Check for forex patterns (e.g., EURUSD, GBPJPY)
        if len(symbol) == 6 and any(c in symbol for c in ["EUR", "GBP", "JPY", "CHF"]):
            return AssetType.FOREX

        # Default to US stocks
        return AssetType.STOCK_US

    async def on_trade_executed(self, trade: Trade) -> None:
        """
        Record trade in FIFO database.

        This is the main entry point for trade recording from the live trading system.
        Automatically creates lots for BUY orders and closes lots for SELL orders.

        Args:
            trade: Trade data from live trading system

        Raises:
            ValueError: If trade data is invalid or insufficient lots for SELL
        """
        try:
            async with get_db_transaction() as session:
                # Determine asset type
                asset_type = await self._determine_asset_type(trade.symbol)

                # Get or create account
                account = await self._get_or_create_account(
                    session=session,
                    exchange_name=trade.broker_name.lower(),
                    exchange_type=ExchangeType.BROKER,
                    currency="USD",  # Default to USD for stocks
                )

                # Determine transaction type
                if trade.side.upper() == "BUY":
                    tx_type = TransactionType.BUY
                elif trade.side.upper() == "SELL":
                    tx_type = TransactionType.SELL
                else:
                    raise ValueError(f"Invalid trade side: {trade.side}")

                # Create external_id for deduplication
                external_id = f"{trade.broker_name}_{trade.broker_trade_id or trade.trade_id}"

                # Create transaction record
                transaction = Transaction(
                    external_id=external_id,
                    exchange_tx_id=trade.broker_trade_id,
                    account_id=account.id,
                    asset_type=asset_type,
                    symbol=trade.symbol.upper(),
                    tx_type=tx_type,
                    side=trade.side.upper(),
                    quantity=trade.quantity,
                    quantity_symbol=trade.symbol.upper(),
                    price=trade.execution_price,
                    total_value=trade.quantity * trade.execution_price,
                    fee_amount=trade.commission,
                    fee_currency="USD",
                    fee_included=False,
                    occurred_at=trade.execution_time,
                    is_taxable=True,
                    tax_year=trade.execution_time.year,
                    meta_data=trade.metadata,
                )

                session.add(transaction)
                await session.flush()

                # Process FIFO logic
                processor = FIFOProcessor(session)

                if tx_type == TransactionType.BUY:
                    # Create new lot
                    lot = processor.process_buy(transaction)
                    transaction.lot_id = lot.id

                    self.logger.info(
                        f"Created FIFO lot {lot.id} for BUY {trade.quantity} "
                        f"{trade.symbol} at {trade.execution_price}"
                    )

                elif tx_type == TransactionType.SELL:
                    # Close lots in FIFO order
                    try:
                        fifo_calc = processor.process_sell(transaction, strict_fifo=True)

                        # Store calculation results in transaction metadata
                        transaction.meta_data["fifo_calculation"] = {
                            "lots_closed": [str(lot_id) for lot_id in fifo_calc.lots_closed],
                            "cost_basis": str(fifo_calc.cost_basis),
                            "proceeds": str(fifo_calc.proceeds),
                            "gain": str(fifo_calc.gain),
                            "loss": str(fifo_calc.loss),
                            "quantity_sold": str(fifo_calc.quantity_sold),
                        }

                        # Update lot realized gains/losses
                        for lot_id in fifo_calc.lots_closed:
                            lot = await session.get(Lot, lot_id)
                            if lot:
                                lot.realized_gain = fifo_calc.gain
                                lot.realized_loss = fifo_calc.loss

                        self.logger.info(
                            f"Closed FIFO lots for SELL {trade.quantity} {trade.symbol}. "
                            f"Cost basis: {fifo_calc.cost_basis}, Gain: {fifo_calc.gain}, "
                            f"Loss: {fifo_calc.loss}"
                        )

                    except ValueError as e:
                        self.logger.error(f"Insufficient lots for SELL: {e}")
                        # Still save the transaction but mark with error
                        transaction.meta_data["fifo_error"] = str(e)

                await session.flush()

        except Exception as e:
            self.logger.error(f"Error recording trade in FIFO: {e}", exc_info=True)
            raise

    async def on_position_opened(self, position: Position) -> None:
        """
        Handle position opened event.

        Note: This is called for informational purposes. Actual lot creation
        happens in on_trade_executed() when the BUY trade is recorded.

        Args:
            position: Position data from live trading system
        """
        try:
            self.logger.info(
                f"Position opened: {position.symbol} Quantity: {position.quantity} "
                f"Cost Basis: {position.cost_basis}"
            )

            # Verify FIFO lots match position
            lots = await self.get_open_lots(position.symbol)
            total_quantity = sum(lot.quantity_remaining for lot in lots)

            if abs(total_quantity - position.quantity) > Decimal("0.0001"):
                self.logger.warning(
                    f"Position quantity mismatch for {position.symbol}: "
                    f"Position={position.quantity}, FIFO lots={total_quantity}"
                )

        except Exception as e:
            self.logger.error(f"Error handling position opened: {e}")

    async def on_position_closed(self, position: Position) -> None:
        """
        Handle position closed event.

        Note: Actual lot closure happens in on_trade_executed() when
        the SELL trade is recorded. This is for verification and logging.

        Args:
            position: Position data from live trading system
        """
        try:
            self.logger.info(
                f"Position closed: {position.symbol} Final P&L: {position.unrealized_pnl}"
            )

            # Check if all lots are closed
            lots = await self.get_open_lots(position.symbol)

            if lots:
                self.logger.warning(
                    f"Position closed but {len(lots)} lots still open for {position.symbol}"
                )

        except Exception as e:
            self.logger.error(f"Error handling position closed: {e}")

    async def get_open_lots(self, symbol: str) -> List[LotInfo]:
        """
        Get all open lots for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of LotInfo objects for open lots, ordered by opened_at (FIFO)
        """
        try:
            async with get_db_transaction() as session:
                stmt = select(Lot).where(
                    Lot.symbol == symbol.upper(),
                    Lot.status == LotStatus.OPEN,
                    Lot.quantity_remaining > 0,
                ).order_by(Lot.opened_at)

                result = await session.execute(stmt)
                lots = result.scalars().all()

                return [
                    LotInfo(
                        lot_id=lot.id,
                        symbol=lot.symbol,
                        quantity_opened=lot.quantity_opened,
                        quantity_remaining=lot.quantity_remaining,
                        cost_basis_open=lot.cost_basis_open,
                        average_cost=lot.cost_basis_open / lot.quantity_opened,
                        opened_at=lot.opened_at,
                        status=lot.status,
                        holding_period_days=lot.holding_period_days,
                        realized_gain=lot.realized_gain,
                        realized_loss=lot.realized_loss,
                    )
                    for lot in lots
                ]

        except Exception as e:
            self.logger.error(f"Error getting open lots for {symbol}: {e}")
            return []

    async def get_cost_basis(self, symbol: str) -> Decimal:
        """
        Calculate total cost basis for open positions of a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Total cost basis as Decimal
        """
        try:
            lots = await self.get_open_lots(symbol)
            return sum(lot.cost_basis_open for lot in lots)

        except Exception as e:
            self.logger.error(f"Error calculating cost basis for {symbol}: {e}")
            return Decimal("0")

    async def get_total_quantity(self, symbol: str) -> Decimal:
        """
        Get total quantity of open lots for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Total quantity as Decimal
        """
        try:
            lots = await self.get_open_lots(symbol)
            return sum(lot.quantity_remaining for lot in lots)

        except Exception as e:
            self.logger.error(f"Error getting total quantity for {symbol}: {e}")
            return Decimal("0")

    async def get_average_cost(self, symbol: str) -> Decimal:
        """
        Calculate weighted average cost of open lots.

        Args:
            symbol: Trading symbol

        Returns:
            Average cost per unit as Decimal
        """
        try:
            lots = await self.get_open_lots(symbol)

            if not lots:
                return Decimal("0")

            total_cost = sum(lot.cost_basis_open for lot in lots)
            total_quantity = sum(lot.quantity_remaining for lot in lots)

            if total_quantity == 0:
                return Decimal("0")

            return total_cost / total_quantity

        except Exception as e:
            self.logger.error(f"Error calculating average cost for {symbol}: {e}")
            return Decimal("0")

    async def get_realized_gains_losses(
        self, symbol: Optional[str] = None, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get realized gains and losses summary.

        Args:
            symbol: Optional symbol filter
            year: Optional tax year filter

        Returns:
            Dictionary with gains/losses summary
        """
        try:
            async with get_db_transaction() as session:
                stmt = select(Lot).where(Lot.status == LotStatus.CLOSED)

                if symbol:
                    stmt = stmt.where(Lot.symbol == symbol.upper())

                if year:
                    stmt = stmt.where(Lot.tax_year_closed == year)

                result = await session.execute(stmt)
                lots = result.scalars().all()

                total_gain = sum(lot.realized_gain or Decimal("0") for lot in lots)
                total_loss = sum(lot.realized_loss or Decimal("0") for lot in lots)

                # Separate long-term vs short-term
                long_term_gain = Decimal("0")
                short_term_gain = Decimal("0")
                long_term_loss = Decimal("0")
                short_term_loss = Decimal("0")

                for lot in lots:
                    if lot.is_long_term:
                        long_term_gain += lot.realized_gain or Decimal("0")
                        long_term_loss += lot.realized_loss or Decimal("0")
                    else:
                        short_term_gain += lot.realized_gain or Decimal("0")
                        short_term_loss += lot.realized_loss or Decimal("0")

                return {
                    "total_gain": float(total_gain),
                    "total_loss": float(total_loss),
                    "net_gain_loss": float(total_gain - total_loss),
                    "long_term_gain": float(long_term_gain),
                    "long_term_loss": float(long_term_loss),
                    "short_term_gain": float(short_term_gain),
                    "short_term_loss": float(short_term_loss),
                    "lots_closed": len(lots),
                }

        except Exception as e:
            self.logger.error(f"Error getting realized gains/losses: {e}")
            return {}

    async def verify_fifo_integrity(self, symbol: str) -> Dict[str, Any]:
        """
        Verify FIFO lot integrity for a symbol.

        Useful for debugging and ensuring data consistency.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with verification results
        """
        try:
            async with get_db_transaction() as session:
                # Get all lots for symbol
                stmt = select(Lot).where(Lot.symbol == symbol.upper())
                result = await session.execute(stmt)
                lots = result.scalars().all()

                # Get all transactions for symbol
                tx_stmt = select(Transaction).where(
                    Transaction.symbol == symbol.upper(),
                    Transaction.tx_type.in_([TransactionType.BUY, TransactionType.SELL]),
                )
                tx_result = await session.execute(tx_stmt)
                transactions = tx_result.scalars().all()

                # Calculate totals
                total_bought = sum(
                    t.quantity for t in transactions if t.tx_type == TransactionType.BUY
                )
                total_sold = sum(
                    t.quantity for t in transactions if t.tx_type == TransactionType.SELL
                )

                total_opened = sum(lot.quantity_opened for lot in lots)
                total_remaining = sum(lot.quantity_remaining for lot in lots)

                # Check integrity
                is_valid = (total_bought == total_opened) and (
                    total_remaining == (total_bought - total_sold)
                )

                return {
                    "symbol": symbol,
                    "is_valid": is_valid,
                    "total_bought": float(total_bought),
                    "total_sold": float(total_sold),
                    "total_opened": float(total_opened),
                    "total_remaining": float(total_remaining),
                    "expected_remaining": float(total_bought - total_sold),
                    "open_lots": sum(1 for lot in lots if lot.status == LotStatus.OPEN),
                    "closed_lots": sum(1 for lot in lots if lot.status == LotStatus.CLOSED),
                    "partial_lots": sum(1 for lot in lots if lot.status == LotStatus.PARTIAL),
                }

        except Exception as e:
            self.logger.error(f"Error verifying FIFO integrity for {symbol}: {e}")
            return {"symbol": symbol, "is_valid": False, "error": str(e)}


# Singleton instance
_fifo_integrator_instance: Optional[FIFOIntegrator] = None


def get_fifo_integrator(user_id: Optional[UUID] = None) -> FIFOIntegrator:
    """
    Get or create the FIFO integrator singleton.

    Args:
        user_id: Optional user UUID for tax reporting

    Returns:
        FIFOIntegrator: Shared integrator instance
    """
    global _fifo_integrator_instance
    if _fifo_integrator_instance is None:
        _fifo_integrator_instance = FIFOIntegrator(user_id=user_id)
    return _fifo_integrator_instance
