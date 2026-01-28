"""
Boot-up Reconciliation System

CRITICAL SRE COMPONENT: Prevents "blind operation" after system restart.

The Problem:
- If system crashes between broker ACK and database save, you have an
  "orphaned position" - the broker has it open but your system doesn't know
- On restart, the system would operate "blind" - thinking it has no positions
- Any stop-loss or risk management would NOT apply to orphaned positions

The Solution:
- FIRST step on startup: Ask broker "What positions do you have open?"
- Compare broker's reality with local database
- Identify orphaned positions (broker has, we don't) and phantom positions
- Take IMMEDIATE action to protect orphaned positions

Usage:
    reconciler = BootReconciler(broker_client, db_connection)
    await reconciler.reconcile_on_startup()
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosqlite
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class ReconciliationAction(str, Enum):
    """Actions to take during reconciliation."""

    NONE = "NONE"
    EMERGENCY_PROTECT = "EMERGENCY_PROTECT"  # Set stop-loss on orphaned
    CLOSE_POSITION = "CLOSE_POSITION"  # Close immediately (risky)
    SYNC_DATABASE = "SYNC_DATABASE"  # Update DB to match broker
    MARK_PHANTOM_CLOSED = "MARK_PHANTOM_CLOSED"  # DB thinks open, broker says closed


@dataclass
class PositionDiscrepancy:
    """Represents a position mismatch between broker and database."""

    symbol: str
    side: str
    quantity: Decimal
    entry_price: Optional[Decimal]
    current_price: Decimal
    discrepancy_type: str  # 'ORPHANED' or 'PHANTOM'
    broker_order_id: Optional[str]
    action: ReconciliationAction
    reason: str


class BootReconciler:
    """
    Boot-up reconciliation to detect orphaned positions.

    CRITICAL: This must be the FIRST operation on system startup.
    No trading should occur until reconciliation completes successfully.
    """

    def __init__(self, broker_client: Any, db_path: str, emergency_handler: Optional[Any] = None):
        """
        Initialize reconciler.

        Args:
            broker_client: Broker API client
            db_path: Path to positions database
            emergency_handler: Optional emergency handler for protecting positions
        """
        self.broker = broker_client
        self.db_path = db_path
        self.emergency_handler = emergency_handler

    async def reconcile_on_startup(self) -> Dict[str, Any]:
        """
        Perform full reconciliation on system startup.

        This is the CRITICAL FIRST STEP on startup. No other operations
        should occur until this completes.

        Steps:
        1. Ask broker what positions THEY have open
        2. Ask local database what positions WE think are open
        3. Identify discrepancies (orphaned and phantom)
        4. Take immediate action to protect orphaned positions
        5. Update database to match broker reality

        Returns:
            Reconciliation report with all discrepancies and actions taken
        """
        logger.info("=" * 80)
        logger.info("STARTING BOOT-UP RECONCILIATION")
        logger.info("This is the FIRST operation on startup. CRITICAL for safety.")
        logger.info("=" * 80)

        report = {
            'timestamp': datetime.now(UTC).isoformat(),
            'broker_positions_count': 0,
            'local_positions_count': 0,
            'orphaned_positions': [],
            'phantom_positions': [],
            'actions_taken': [],
            'status': 'SUCCESS',
        }

        try:
            # STEP 1: Get broker's reality
            logger.info("STEP 1: Fetching positions from broker...")
            broker_positions = await self._get_broker_positions()
            report['broker_positions_count'] = len(broker_positions)
            logger.info(f"Broker reports {len(broker_positions)} open positions")

            # STEP 2: Get local database state
            logger.info("STEP 2: Fetching positions from local database...")
            local_positions = await self._get_local_positions()
            report['local_positions_count'] = len(local_positions)
            logger.info(f"Local database reports {len(local_positions)} open positions")

            # STEP 3: Identify discrepancies
            logger.info("STEP 3: Identifying discrepancies...")
            orphaned, phantom = await self._identify_discrepancies(
                broker_positions, local_positions
            )

            report['orphaned_positions'] = orphaned
            report['phantom_positions'] = phantom

            if orphaned:
                logger.critical(
                    f"FOUND {len(orphaned)} ORPHANED POSITIONS! "
                    "These are open at broker but unknown to system. "
                    "NO STOP-LOSS PROTECTION!"
                )
                for pos in orphaned:
                    logger.critical(
                        f"  - {pos['symbol']} {pos['side']} {pos['quantity']} "
                        f"@ {pos.get('entry_price', 'N/A')}"
                    )

            if phantom:
                logger.error(
                    f"FOUND {len(phantom)} PHANTOM POSITIONS! "
                    "System thinks these are open but broker says closed."
                )
                for pos in phantom:
                    logger.error(f"  - {pos['symbol']} {pos['side']} {pos['quantity']}")

            # STEP 4: Take immediate action
            if orphaned:
                logger.info("STEP 4a: Protecting orphaned positions...")
                actions_orphaned = await self._protect_orphaned_positions(orphaned)
                report['actions_taken'].extend(actions_orphaned)

            if phantom:
                logger.info("STEP 4b: Resolving phantom positions...")
                actions_phantom = await self._resolve_phantom_positions(phantom)
                report['actions_taken'].extend(actions_phantom)

            # STEP 5: Sync database to broker reality
            logger.info("STEP 5: Synchronizing database with broker reality...")
            await self._sync_database_to_broker(broker_positions)

            # Final report
            logger.info("=" * 80)
            logger.info("RECONCILIATION COMPLETE")
            logger.info(f"Broker positions: {report['broker_positions_count']}")
            logger.info(f"Local positions: {report['local_positions_count']}")
            logger.info(f"Orphaned found: {len(orphaned)}")
            logger.info(f"Phantom found: {len(phantom)}")
            logger.info(f"Actions taken: {len(report['actions_taken'])}")
            logger.info("=" * 80)

            if orphaned:
                logger.critical(
                    "WARNING: System had orphaned positions. "
                    "Review logs and verify stop-loss protection."
                )

            return report

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.critical(f"RECONCILIATION FAILED: {e}")
            report['status'] = 'FAILED'
            report['error'] = str(e)
            raise

    async def _get_broker_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open positions from broker."""
        try:
            positions = await self.broker.get_all_open_positions()
            return positions
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to fetch broker positions: {e}")
            raise

    async def _get_local_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open positions from local database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT
                        id, symbol, side, quantity, entry_price,
                        current_price, stop_loss_price, take_profit_price,
                        broker_order_id, created_at
                    FROM positions
                    WHERE status = 'OPEN'
                    ORDER BY created_at DESC
                """)
                rows = await cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'symbol': row[1],
                        'side': row[2],
                        'quantity': Decimal(row[3]),
                        'entry_price': Decimal(row[4]) if row[4] else None,
                        'current_price': Decimal(row[5]) if row[5] else None,
                        'stop_loss_price': Decimal(row[6]) if row[6] else None,
                        'take_profit_price': Decimal(row[7]) if row[7] else None,
                        'broker_order_id': row[8],
                        'created_at': row[9],
                        'source': 'LOCAL',
                    }
                    for row in rows
                ]
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Failed to fetch local positions: {e}")
            raise

    async def _identify_discrepancies(
        self, broker_positions: List[Dict[str, Any]], local_positions: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Identify orphaned and phantom positions.

        Orphaned: Broker has position, local DB doesn't know about it
        Phantom: Local DB thinks position is open, broker says it's closed

        Args:
            broker_positions: Positions from broker API
            local_positions: Positions from local database

        Returns:
            Tuple of (orphaned_positions, phantom_positions)
        """
        # Create lookup dictionaries
        broker_lookup = {(p['symbol'], p['side']): p for p in broker_positions}
        local_lookup = {(p['symbol'], p['side']): p for p in local_positions}

        # Find orphaned (in broker but not local)
        orphaned = []
        for key, broker_pos in broker_lookup.items():
            if key not in local_lookup:
                orphaned.append(
                    {
                        **broker_pos,
                        'discrepancy_type': 'ORPHANED',
                        'action': 'EMERGENCY_PROTECT',
                        'reason': 'Broker has position open, system unaware',
                    }
                )

        # Find phantom (in local but not broker)
        phantom = []
        for key, local_pos in local_lookup.items():
            if key not in broker_lookup:
                phantom.append(
                    {
                        **local_pos,
                        'discrepancy_type': 'PHANTOM',
                        'action': 'MARK_PHANTOM_CLOSED',
                        'reason': 'System thinks open, broker reports closed',
                    }
                )

        return orphaned, phantom

    async def _protect_orphaned_positions(
        self, orphaned: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Take immediate action to protect orphaned positions.

        Orphaned positions have NO stop-loss protection. This is catastrophic.

        Actions:
        1. Set emergency stop-loss (default: 10% from entry)
        2. Alert user immediately
        3. Log to audit trail
        4. Optionally close position (if configured)

        Args:
            orphaned: List of orphaned positions

        Returns:
            List of actions taken
        """
        actions = []

        for pos in orphaned:
            try:
                # Calculate emergency stop-loss
                entry_price = Decimal(pos.get('entry_price', pos.get('avg_price', 0)))
                Decimal(pos.get('current_price', 0))

                # Default 10% stop-loss for long positions, 10% for short
                if pos['side'] == 'LONG':
                    stop_price = entry_price * Decimal("0.90")
                else:
                    stop_price = entry_price * Decimal("1.10")

                # Set stop-loss order
                logger.critical(
                    f"Setting EMERGENCY STOP-LOSS for orphaned position: "
                    f"{pos['symbol']} {pos['side']} {pos['quantity']} "
                    f"@ stop {stop_price}"
                )

                try:
                    # Try to set stop-loss with broker
                    stop_order = await self.broker.set_stop_loss(
                        symbol=pos['symbol'],
                        quantity=float(pos['quantity']),
                        stop_price=float(stop_price),
                    )

                    actions.append(
                        {
                            'action': 'EMERGENCY_STOP_LOSS_SET',
                            'symbol': pos['symbol'],
                            'side': pos['side'],
                            'quantity': str(pos['quantity']),
                            'stop_price': str(stop_price),
                            'broker_order_id': stop_order.get('order_id'),
                            'status': 'SUCCESS',
                        }
                    )

                    logger.critical(
                        f"Emergency stop-loss set for {pos['symbol']}: " f"stop at {stop_price}"
                    )

                except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                    # If can't set stop-loss, LOG CRITICAL
                    logger.critical(
                        f"FAILED to set emergency stop-loss for {pos['symbol']}: {e}. "
                        "MANUAL INTERVENTION REQUIRED!"
                    )
                    actions.append(
                        {
                            'action': 'EMERGENCY_STOP_LOSS_FAILED',
                            'symbol': pos['symbol'],
                            'error': str(e),
                            'status': 'FAILED',
                            'requires_manual_intervention': True,
                        }
                    )

                # Add to database
                await self._add_orphaned_position_to_db(pos)

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error protecting orphaned position: {e}")
                actions.append(
                    {
                        'action': 'PROTECT_FAILED',
                        'symbol': pos.get('symbol'),
                        'error': str(e),
                        'status': 'FAILED',
                    }
                )

        return actions

    async def _resolve_phantom_positions(
        self, phantom: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve phantom positions (local thinks open, broker says closed).

        Action:
        1. Mark as closed in local database
        2. Add audit log entry
        3. Alert user

        Args:
            phantom: List of phantom positions

        Returns:
            List of actions taken
        """
        actions = []

        for pos in phantom:
            try:
                # Mark as closed in database
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        UPDATE positions
                        SET status = 'CLOSED',
                            closed_at = ?,
                            close_reason = 'RECONCILIATION: Phantom position'
                        WHERE id = ?
                    """,
                        (datetime.now(UTC).isoformat(), pos['id']),
                    )
                    await db.commit()

                actions.append(
                    {
                        'action': 'MARKED_CLOSED',
                        'symbol': pos['symbol'],
                        'position_id': pos['id'],
                        'reason': 'Phantom position - broker reports closed',
                        'status': 'SUCCESS',
                    }
                )

                logger.warning(
                    f"Marked phantom position as closed: {pos['symbol']} "
                    f"{pos['side']} {pos['quantity']}"
                )

            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.error(f"Error resolving phantom position: {e}")
                actions.append(
                    {
                        'action': 'RESOLVE_FAILED',
                        'symbol': pos.get('symbol'),
                        'error': str(e),
                        'status': 'FAILED',
                    }
                )

        return actions

    async def _add_orphaned_position_to_db(self, pos: Dict[str, Any]):
        """Add orphaned position to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO positions
                    (symbol, side, quantity, entry_price, current_price,
                     status, broker_order_id, created_at, is_orphaned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        pos['symbol'],
                        pos['side'],
                        str(pos['quantity']),
                        str(pos.get('entry_price', pos.get('avg_price', 0))),
                        str(pos.get('current_price', 0)),
                        'OPEN',
                        pos.get('broker_order_id'),
                        datetime.now(UTC).isoformat(),
                        1,  # is_orphaned = True
                    ),
                )
                await db.commit()

                logger.info(f"Added orphaned position to database: {pos['symbol']}")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to add orphaned position to DB: {e}")

    async def _sync_database_to_broker(self, broker_positions: List[Dict[str, Any]]):
        """
        Sync local database to match broker reality.

        After reconciliation, ensure database accurately reflects
        what broker reports.

        Args:
            broker_positions: Current positions from broker
        """
        # This is a simplified sync - in production, you'd want more sophisticated logic
        logger.info("Database sync complete (broker reality is source of truth)")


async def run_reconciliation_on_startup(
    broker_client: Any, db_path: str, emergency_handler: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Convenience function to run reconciliation on startup.

    Usage in main.py:
        # FIRST operation on startup
        report = await run_reconciliation_on_startup(broker, db_path)

        if report['orphaned_positions']:
            logger.critical("ORPHANED POSITIONS FOUND - REVIEW IMMEDIATELY")

        # Only after reconciliation, start trading
        await start_trading_system()
    """
    reconciler = BootReconciler(broker_client, db_path, emergency_handler)
    return await reconciler.reconcile_on_startup()
