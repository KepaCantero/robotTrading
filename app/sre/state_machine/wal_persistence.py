# mypy: ignore-errors
"""
Write-Ahead Logging (WAL) for Order State Machine

This module implements WAL persistence to prevent "orphaned positions" -
a critical SRE issue where the broker has a position open but the system
doesn't know about it due to crashes between broker ACK and database save.

CRITICAL: Order state MUST be saved to database BEFORE sending to broker.
This ensures that on restart, we can reconcile any orphaned positions.

Example:
    # BAD: Order lost if crash occurs here
    result = await broker.submit(order)
    await db.save_order(result)  # Never executes if crash

    # GOOD: Order saved before broker call
    await wal.write(OrderLog(state="SUBMITTING", order_id=order.id))
    result = await broker.submit(order)
    await wal.write(OrderLog(state="ACK_RECEIVED", ...))
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiofiles
import aiosqlite

logger = logging.getLogger(__name__)


class OrderState(str, Enum):
    """Order states with WAL persistence guarantees."""

    PENDING = "PENDING"  # Initial state
    SUBMITTING = "SUBMITTING"  # CRITICAL: Saved BEFORE broker call
    SUBMITTED = "SUBMITTED"  # Sent to broker
    ACK_RECEIVED = "ACK_RECEIVED"  # Broker acknowledged
    OPEN = "OPEN"  # Active in market
    PARTIAL_FILLED = "PARTIAL_FILLED"  # Partial execution
    FILLED = "FILLED"  # Fully executed
    CANCELLED = "CANCELLED"  # Cancelled by user
    REJECTED = "REJECTED"  # Broker rejected
    FAILED = "FAILED"  # System failure


@dataclass
class OrderLog:
    """WAL entry for order state transitions."""

    order_id: str
    state: OrderState
    timestamp: datetime
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: Decimal
    price: Optional[Decimal] = None
    error: Optional[str] = None
    broker_order_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["state"] = self.state.value
        data["quantity"] = str(self.quantity)
        if self.price:
            data["price"] = str(self.price)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrderLog":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["state"] = OrderState(data["state"])
        data["quantity"] = Decimal(data["quantity"])
        if data.get("price"):
            data["price"] = Decimal(data["price"])
        return cls(**data)


class OrderStateMachine:
    """
    Order state machine with WAL persistence.

    CRITICAL: This pattern prevents orphaned positions by ensuring
    state transitions are persisted BEFORE external operations.

    States:
        PENDING -> SUBMITTING -> SUBMITTED -> ACK_RECEIVED -> OPEN -> FILLED
                                  |              |
                                  v              v
                                REJECTED      CANCELLED
    """

    def __init__(self, db_path: str, wal_path: str):
        """
        Initialize state machine.

        Args:
            db_path: Path to SQLite database
            wal_path: Path to WAL file
        """
        self.db_path = db_path
        self.wal_path = Path(wal_path)
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Create database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS order_wal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT,
                    error TEXT,
                    broker_order_id TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_order_id
                ON order_wal(order_id)
            """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_state
                ON order_wal(state)
            """
            )
            await db.commit()

    async def write_state(self, log: OrderLog) -> bool:
        """
        Write order state to WAL (database and file).

        CRITICAL: This must complete BEFORE calling broker API.

        Args:
            log: Order log entry

        Returns:
            True if write successful
        """
        async with self._lock:
            try:
                # Write to database (primary WAL)
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        INSERT INTO order_wal
                        (order_id, state, timestamp, symbol, side, quantity,
                         price, error, broker_order_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            log.order_id,
                            log.state.value,
                            log.timestamp.isoformat(),
                            log.symbol,
                            log.side,
                            str(log.quantity),
                            str(log.price) if log.price else None,
                            log.error,
                            log.broker_order_id,
                            json.dumps(log.metadata) if log.metadata else None,
                        ),
                    )
                    await db.commit()

                # Write to file WAL (redundancy)
                await self._write_to_file(log)

                logger.info(f"WAL: Order {log.order_id} state -> {log.state.value}")
                return True

            except (asyncio.TimeoutError, OSError) as e:
                logger.critical(f"WAL write failed for order {log.order_id}: {e}")
                raise

    async def _write_to_file(self, log: OrderLog):
        """Append to file WAL for redundancy."""
        log_line = json.dumps(log.to_dict()) + "\n"
        async with aiofiles.open(self.wal_path, mode="a") as f:
            await f.write(log_line)

    async def get_order_history(self, order_id: str) -> list[OrderLog]:
        """Get all state transitions for an order."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT order_id, state, timestamp, symbol, side, quantity,
                       price, error, broker_order_id, metadata
                FROM order_wal
                WHERE order_id = ?
                ORDER BY timestamp ASC
            """,
                (order_id,),
            )
            rows = await cursor.fetchall()

            return [
                OrderLog(
                    order_id=row[0],
                    state=OrderState(row[1]),
                    timestamp=datetime.fromisoformat(row[2]),
                    symbol=row[3],
                    side=row[4],
                    quantity=Decimal(row[5]),
                    price=Decimal(row[6]) if row[6] else None,
                    error=row[7],
                    broker_order_id=row[8],
                    metadata=json.loads(row[9]) if row[9] else None,
                )
                for row in rows
            ]

    async def get_orders_in_state(self, state: OrderState) -> list[OrderLog]:
        """Get all orders currently in a specific state."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT order_id, state, timestamp, symbol, side, quantity,
                       price, error, broker_order_id, metadata
                FROM order_wal
                WHERE state = ?
                ORDER BY timestamp DESC
            """,
                (state.value,),
            )
            rows = await cursor.fetchall()

            return [
                OrderLog(
                    order_id=row[0],
                    state=OrderState(row[1]),
                    timestamp=datetime.fromisoformat(row[2]),
                    symbol=row[3],
                    side=row[4],
                    quantity=Decimal(row[5]),
                    price=Decimal(row[6]) if row[6] else None,
                    error=row[7],
                    broker_order_id=row[8],
                    metadata=json.loads(row[9]) if row[9] else None,
                )
                for row in rows
            ]

    async def get_pending_orders(self) -> list[OrderLog]:
        """Get orders in SUBMITTING or SUBMITTED state (may be orphaned)."""
        pending_states = [OrderState.SUBMITTING, OrderState.SUBMITTED, OrderState.ACK_RECEIVED]
        results = []
        for state in pending_states:
            results.extend(await self.get_orders_in_state(state))
        return results


class WALOrderManager:
    """
    High-level order manager with WAL guarantees.

    Usage:
        manager = WALOrderManager(db_path="...", wal_path="...")
        await manager.initialize()

        # Submit order with WAL protection
        result = await manager.submit_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00")
        )
    """

    def __init__(self, db_path: str, wal_path: str, broker_client: object):
        """
        Initialize order manager.

        Args:
            db_path: Path to SQLite database
            wal_path: Path to WAL file
            broker_client: Broker API client
        """
        self.state_machine = OrderStateMachine(db_path, wal_path)
        self.broker = broker_client

    async def initialize(self):
        """Initialize state machine."""
        await self.state_machine.initialize()

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "MARKET",
    ) -> dict[str, Any]:
        """
        Submit order with WAL protection.

        CRITICAL PATTERN:
        1. Save state as SUBMITTING (BEFORE broker call)
        2. Call broker API
        3. Save state as ACK_RECEIVED (AFTER broker ACK)
        4. Save state as OPEN/FILLED/REJECTED

        This ensures crash recovery can detect orphaned positions.

        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            order_type: Order type ('MARKET' or 'LIMIT')

        Returns:
            Order result with broker order ID
        """
        import uuid

        order_id = str(uuid.uuid4())

        # STEP 1: CRITICAL - Save BEFORE broker call
        log = OrderLog(
            order_id=order_id,
            state=OrderState.SUBMITTING,
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )
        await self.state_machine.write_state(log)

        try:
            # STEP 2: Call broker API
            logger.info(f"Submitting order {order_id} to broker")
            result = await self.broker.submit_order(
                symbol=symbol,
                side=side,
                quantity=float(quantity),
                price=float(price) if price else None,
                order_type=order_type,
            )

            # STEP 3: Save ACK state
            log.state = OrderState.ACK_RECEIVED
            log.broker_order_id = result.get("order_id")
            log.timestamp = datetime.now(timezone.utc)
            await self.state_machine.write_state(log)

            # STEP 4: Save final state
            if result.get("status") == "FILLED":
                log.state = OrderState.FILLED
            elif result.get("status") == "OPEN":
                log.state = OrderState.OPEN
            elif result.get("status") == "REJECTED":
                log.state = OrderState.REJECTED
                log.error = result.get("error")

            log.timestamp = datetime.now(timezone.utc)
            await self.state_machine.write_state(log)

            logger.info(f"Order {order_id} completed with state {log.state.value}")
            return {
                "order_id": order_id,
                "broker_order_id": log.broker_order_id,
                "state": log.state.value,
                "result": result,
            }

        except (OSError, ValueError) as e:
            # CRITICAL: Log failure state
            log.state = OrderState.FAILED
            log.error = str(e)
            log.timestamp = datetime.now(timezone.utc)
            await self.state_machine.write_state(log)

            logger.error(f"Order {order_id} failed: {e}")
            raise

    async def recover_orphaned_orders(self) -> list[dict[str, Any]]:
        """
        Detect and report orphaned orders for recovery.

        Called on system startup to find orders that were SUBMITTING
        or SUBMITTED when a crash occurred.

        Returns:
            List of orphaned orders that need reconciliation
        """
        pending = await self.state_machine.get_pending_orders()
        orphaned = []

        for log in pending:
            # Check with broker if order actually exists
            try:
                broker_status = await self.broker.get_order_status(log.broker_order_id)

                if broker_status and broker_status["status"] in ["OPEN", "PARTIAL_FILLED"]:
                    # Orphaned position! Broker has it, we don't
                    orphaned.append(
                        {
                            "order_id": log.order_id,
                            "broker_order_id": log.broker_order_id,
                            "symbol": log.symbol,
                            "side": log.side,
                            "quantity": log.quantity,
                            "state": broker_status["status"],
                            "recovery_action": "SET_STOP_LOSS",  # Critical!
                        }
                    )

                    logger.critical(
                        f"ORPHANED POSITION DETECTED: {log.symbol} {log.side} {log.quantity}"
                    )

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Failed to check order {log.order_id}: {e}")

        return orphaned
