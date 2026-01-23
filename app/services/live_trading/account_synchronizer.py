"""
T16.1.4: AccountSynchronizer - Portfolio reconciliation and balance sync

Synchronizes local portfolio state with broker account:
- Balance reconciliation
- Position verification
- Cash tracking
- Margin utilization monitoring

MEMORY: Uses deque with maxlen to prevent unbounded memory growth.
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Deque, Dict, List, Optional, Tuple

from fastapi import Depends

from .broker_connector import BrokerAccount, BrokerConnector, BrokerPosition, get_broker_connector

logger = logging.getLogger(__name__)


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state."""

    timestamp: datetime
    total_value: Decimal
    cash: Decimal
    positions_value: Decimal
    margin_used: Decimal
    buying_power: Decimal
    num_positions: int


@dataclass
class Reconciliation:
    """Reconciliation result."""

    timestamp: datetime
    is_balanced: bool
    discrepancies: List[str] = None
    local_value: Decimal = Decimal("0")
    broker_value: Decimal = Decimal("0")
    difference: Decimal = Decimal("0")

    def __post_init__(self):
        if self.discrepancies is None:
            self.discrepancies = []


class AccountSynchronizer:
    """
    Synchronizes local portfolio with broker account.

    Features:
    - Balance reconciliation
    - Position verification
    - Portfolio snapshots
    - Historical tracking
    - Discrepancy detection
    """

    def __init__(self, broker: Optional[BrokerConnector] = None):
        """Initialize account synchronizer."""
        self.broker = broker or get_broker_connector()
        self.local_positions: Dict[str, BrokerPosition] = {}
        self.local_cash = Decimal("0")
        # MEMORY: Use deque with maxlen to prevent unbounded growth
        self.snapshots: Deque[PortfolioSnapshot] = deque(maxlen=1440)  # 24h at 1min intervals
        self.reconciliation_history: Deque[Reconciliation] = deque(maxlen=1000)
        self.last_sync: Optional[datetime] = None
        logger.info("✅ AccountSynchronizer initialized with bounded history")

    async def sync_account(self) -> bool:
        """
        Synchronize with broker account.

        Returns:
            True if sync successful
        """
        try:
            account = await self.broker.get_account_info()
            if not account:
                logger.error("❌ Failed to get account info")
                return False

            self.local_cash = account.cash_available
            self.last_sync = datetime.now()

            logger.info(f"✅ Account synced: ${self.local_cash:,.2f} cash available")
            return True

        except Exception as e:
            logger.error(f"❌ Sync error: {str(e)}")
            return False

    async def sync_positions(self) -> bool:
        """
        Synchronize positions with broker.

        Returns:
            True if sync successful
        """
        try:
            positions = await self.broker.get_positions()
            self.local_positions = positions
            self.last_sync = datetime.now()

            logger.info(f"✅ Synced {len(positions)} positions")
            return True

        except Exception as e:
            logger.error(f"❌ Position sync error: {str(e)}")
            return False

    async def full_sync(self) -> Tuple[bool, str]:
        """
        Perform complete synchronization.

        Returns:
            (success, message)
        """
        try:
            # Sync account and positions
            account_ok = await self.sync_account()
            positions_ok = await self.sync_positions()

            if account_ok and positions_ok:
                # Create snapshot
                await self.take_snapshot()
                return True, "Full sync completed successfully"
            else:
                return False, "Partial sync failure"

        except Exception as e:
            return False, f"Sync error: {str(e)}"

    async def reconcile_balance(self) -> Reconciliation:
        """
        Reconcile local and broker balances.

        Returns:
            Reconciliation result
        """
        discrepancies = []

        # Get broker account
        account = await self.broker.get_account_info()
        if not account:
            return Reconciliation(
                datetime.now(),
                False,
                ["Cannot access broker account"],
            )

        # Calculate local portfolio value
        local_value = self.local_cash
        for position in self.local_positions.values():
            local_value += position.market_value

        # Get broker portfolio value
        broker_value = account.cash_available
        positions = await self.broker.get_positions()
        for position in positions.values():
            broker_value += position.market_value

        # Check for discrepancies
        difference = abs(local_value - broker_value)
        tolerance = Decimal("100")  # €100 tolerance

        if difference > tolerance:
            discrepancies.append(
                f"Balance mismatch: local €{local_value:,.2f} vs broker €{broker_value:,.2f}"
            )

        is_balanced = len(discrepancies) == 0

        reconciliation = Reconciliation(
            datetime.now(),
            is_balanced,
            discrepancies,
            local_value,
            broker_value,
            difference,
        )

        self.reconciliation_history.append(reconciliation)
        logger.info(f"{'✅' if is_balanced else '⚠️'} Reconciliation: {difference:,.2f} difference")

        return reconciliation

    async def reconcile_positions(self) -> Reconciliation:
        """
        Reconcile positions between local and broker.

        Returns:
            Reconciliation result
        """
        discrepancies = []

        # Get broker positions
        broker_positions = await self.broker.get_positions()

        # Check for quantity mismatches
        all_symbols = set(self.local_positions.keys()) | set(broker_positions.keys())

        for symbol in all_symbols:
            local_pos = self.local_positions.get(symbol)
            broker_pos = broker_positions.get(symbol)

            local_qty = local_pos.quantity if local_pos else Decimal("0")
            broker_qty = broker_pos.quantity if broker_pos else Decimal("0")

            if local_qty != broker_qty:
                discrepancies.append(
                    f"{symbol}: local {local_qty} shares vs broker {broker_qty} shares"
                )

        is_balanced = len(discrepancies) == 0

        reconciliation = Reconciliation(
            datetime.now(),
            is_balanced,
            discrepancies,
        )

        self.reconciliation_history.append(reconciliation)
        logger.info(
            f"{'✅' if is_balanced else '⚠️'} Position reconciliation: {len(discrepancies)} discrepancies"
        )

        return reconciliation

    async def take_snapshot(self) -> PortfolioSnapshot:
        """
        Take snapshot of current portfolio state.

        Returns:
            PortfolioSnapshot
        """
        account = await self.broker.get_account_info()
        if not account:
            account = BrokerAccount("unknown", None)

        positions = await self.broker.get_positions()

        total_value = self.local_cash
        positions_value = Decimal("0")

        for position in self.local_positions.values():
            positions_value += position.market_value

        total_value += positions_value

        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=total_value,
            cash=self.local_cash,
            positions_value=positions_value,
            margin_used=account.margin_used if account else Decimal("0"),
            buying_power=account.buying_power if account else Decimal("0"),
            num_positions=len(positions),
        )

        self.snapshots.append(snapshot)
        logger.info(f"✅ Snapshot taken: €{total_value:,.2f} total value")

        return snapshot

    async def get_latest_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get latest portfolio snapshot."""
        return self.snapshots[-1] if self.snapshots else None

    async def get_portfolio_history(
        self,
        hours: int = 24,
    ) -> List[PortfolioSnapshot]:
        """
        Get portfolio history for time period.

        Args:
            hours: Number of hours to look back

        Returns:
            List of PortfolioSnapshot
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [s for s in self.snapshots if s.timestamp >= cutoff_time]

    async def calculate_daily_return(self) -> Optional[Decimal]:
        """
        Calculate return since start of day.

        Returns:
            Daily return percentage
        """
        if len(self.snapshots) < 2:
            return None

        # Find first snapshot of today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_snapshots = [s for s in self.snapshots if s.timestamp >= today_start]

        if not today_snapshots:
            return None

        opening_value = today_snapshots[0].total_value
        current_value = self.snapshots[-1].total_value

        if opening_value <= 0:
            return None

        return (current_value - opening_value) / opening_value * Decimal("100")

    async def get_margin_status(self) -> Dict:
        """
        Get margin utilization status.

        Returns:
            Dict with margin metrics
        """
        account = await self.broker.get_account_info()
        if not account:
            return {}

        margin_pct = (
            (account.margin_used / account.equity * Decimal("100"))
            if account.equity > 0
            else Decimal("0")
        )

        return {
            "margin_used": account.margin_used,
            "equity": account.equity,
            "margin_percentage": margin_pct,
            "buying_power": account.buying_power,
            "cash_available": account.cash_available,
        }

    def get_sync_status(self) -> Dict:
        """Get synchronization status."""
        return {
            "last_sync": self.last_sync,
            "is_synced": self.last_sync is not None,
            "num_snapshots": len(self.snapshots),
            "num_reconciliations": len(self.reconciliation_history),
            "last_reconciliation": (
                self.reconciliation_history[-1] if self.reconciliation_history else None
            ),
        }


# Singleton
_synchronizer: Optional[AccountSynchronizer] = None


def get_account_synchronizer(
    broker: BrokerConnector = Depends(get_broker_connector),
) -> AccountSynchronizer:
    """Get or create singleton AccountSynchronizer."""
    global _synchronizer
    if _synchronizer is None:
        _synchronizer = AccountSynchronizer(broker=broker)

    return _synchronizer
