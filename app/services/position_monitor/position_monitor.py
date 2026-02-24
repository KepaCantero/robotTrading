"""
Position Monitor - Continuously monitors open positions and executes stops.

This is the most critical component for production trading:
- Checks positions every second
- Executes stop-loss automatically when hit
- Executes take-profit automatically when hit
- Survives process restart (reads from DB)
- Handles broker disconnections gracefully

CRITICALITY: LIFE-THREATENING - System executes trades then forgets positions exist.
No stop-loss execution in production.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from requests.exceptions import HTTPError
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

from app.shared.config.centralized_config import get_config
from app.core.decimal_utils import to_decimal, validate_price

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """Status of a monitored position."""

    ACTIVE = "active"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class MonitoredPosition:
    """
    A position being monitored for stop-loss/take-profit.

    This represents a trading position that needs continuous monitoring
    for automatic stop-loss and take-profit execution.

    Attributes:
        position_id: Unique identifier for this position
        symbol: Trading symbol (e.g., "AAPL", "BTCUSD")
        side: Position side ("LONG" or "SHORT")
        entry_price: Price at which position was opened
        quantity: Position size (number of shares/contracts)
        current_price: Current market price
        stop_loss_price: Absolute stop-loss price (optional)
        stop_loss_pct: Stop-loss as percentage (optional)
        take_profit_price: Absolute take-profit price (optional)
        take_profit_pct: Take-profit as percentage (optional)
        status: Current position status
        opened_at: When position was opened
        last_checked: When position was last checked
        check_count: Number of times position has been checked
    """

    position_id: str
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_price: Decimal
    quantity: Decimal
    current_price: Decimal
    stop_loss_price: Optional[Decimal] = None
    stop_loss_pct: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    take_profit_pct: Optional[Decimal] = None
    status: PositionStatus = PositionStatus.ACTIVE
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_checked: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    check_count: int = 0

    def should_trigger_stop_loss(self) -> bool:
        """
        Check if current price triggers stop-loss.

        For LONG positions: stop-loss triggers when price <= stop_loss_price
        For SHORT positions: stop-loss triggers when price >= stop_loss_price

        Returns:
            True if stop-loss should be triggered
        """
        if self.stop_loss_price is None:
            return False

        if self.side == "LONG":
            return self.current_price <= self.stop_loss_price
        else:  # SHORT
            return self.current_price >= self.stop_loss_price

    def should_trigger_take_profit(self) -> bool:
        """
        Check if current price triggers take-profit.

        For LONG positions: take-profit triggers when price >= take_profit_price
        For SHORT positions: take-profit triggers when price <= take_profit_price

        Returns:
            True if take-profit should be triggered
        """
        if self.take_profit_price is None:
            return False

        if self.side == "LONG":
            return self.current_price >= self.take_profit_price
        else:  # SHORT
            return self.current_price <= self.take_profit_price

    def calculate_stop_loss_price(self) -> Optional[Decimal]:
        """
        Calculate stop-loss price from percentage if not set.

        For LONG: stop_loss = entry_price * (1 - stop_loss_pct)
        For SHORT: stop_loss = entry_price * (1 + stop_loss_pct)

        Returns:
            Calculated stop-loss price or None
        """
        if self.stop_loss_price:
            return self.stop_loss_price

        if self.stop_loss_pct:
            if self.side == "LONG":
                return self.entry_price * (Decimal("1") - self.stop_loss_pct)
            else:
                return self.entry_price * (Decimal("1") + self.stop_loss_pct)

        return None

    def calculate_take_profit_price(self) -> Optional[Decimal]:
        """
        Calculate take-profit price from percentage if not set.

        For LONG: take_profit = entry_price * (1 + take_profit_pct)
        For SHORT: take_profit = entry_price * (1 - take_profit_pct)

        Returns:
            Calculated take-profit price or None
        """
        if self.take_profit_price:
            return self.take_profit_price

        if self.take_profit_pct:
            if self.side == "LONG":
                return self.entry_price * (Decimal("1") + self.take_profit_pct)
            else:
                return self.entry_price * (Decimal("1") - self.take_profit_pct)

        return None

    def update_current_price(self, price: Decimal) -> None:
        """
        Update current price and last checked time.

        Args:
            price: New current price
        """
        self.current_price = validate_price(price)
        self.last_checked = datetime.now(timezone.utc)
        self.check_count += 1

    def calculate_pnl(self) -> Decimal:
        """
        Calculate unrealized P&L for this position.

        For LONG: pnl = (current_price - entry_price) * quantity
        For SHORT: pnl = (entry_price - current_price) * quantity

        Returns:
            Current unrealized P&L
        """
        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    def calculate_pnl_percentage(self) -> Optional[Decimal]:
        """
        Calculate P&L as percentage of entry price.

        Returns:
            P&L percentage or None if invalid
        """
        if self.entry_price == 0:
            return None

        pnl = self.calculate_pnl()
        total_value = self.entry_price * self.quantity

        if total_value == 0:
            return None

        return (pnl / total_value) * Decimal("100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": str(self.entry_price),
            "quantity": str(self.quantity),
            "current_price": str(self.current_price),
            "stop_loss_price": str(self.stop_loss_price) if self.stop_loss_price else None,
            "stop_loss_pct": str(self.stop_loss_pct) if self.stop_loss_pct else None,
            "take_profit_price": str(self.take_profit_price) if self.take_profit_price else None,
            "take_profit_pct": str(self.take_profit_pct) if self.take_profit_pct else None,
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "last_checked": self.last_checked.isoformat(),
            "check_count": self.check_count,
            "unrealized_pnl": str(self.calculate_pnl()),
            "unrealized_pnl_pct": (
                str(self.calculate_pnl_percentage()) if self.calculate_pnl_percentage() else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitoredPosition":
        """Create MonitoredPosition from dictionary."""
        return cls(
            position_id=data["position_id"],
            symbol=data["symbol"],
            side=data["side"],
            entry_price=to_decimal(data["entry_price"]),
            quantity=to_decimal(data["quantity"]),
            current_price=to_decimal(data["current_price"]),
            stop_loss_price=(
                to_decimal(data["stop_loss_price"]) if data.get("stop_loss_price") else None
            ),
            stop_loss_pct=to_decimal(data["stop_loss_pct"]) if data.get("stop_loss_pct") else None,
            take_profit_price=(
                to_decimal(data["take_profit_price"]) if data.get("take_profit_price") else None
            ),
            take_profit_pct=(
                to_decimal(data["take_profit_pct"]) if data.get("take_profit_pct") else None
            ),
            status=PositionStatus(data.get("status", "active")),
            opened_at=(
                datetime.fromisoformat(data["opened_at"])
                if data.get("opened_at")
                else datetime.now(timezone.utc)
            ),
            last_checked=(
                datetime.fromisoformat(data["last_checked"])
                if data.get("last_checked")
                else datetime.now(timezone.utc)
            ),
            check_count=data.get("check_count", 0),
        )


class PositionMonitorConfig:
    """
    Configuration for position monitor.

    Uses centralized configuration for all timeout and interval values.

    Attributes:
        check_interval_seconds: How often to check positions (uses centralized config)
        max_price_fetch_retries: Max retries for fetching prices (uses centralized config)
        price_fetch_timeout_seconds: Timeout for price fetching (uses centralized config)
        auto_restart: Automatically restart monitoring on errors
        log_all_checks: Log every position check (verbose)
        audit_log_enabled: Enable audit logging
        persist_state: Persist state to database
        state_sync_interval_seconds: How often to sync state to DB (uses centralized config)
        execute_stops_automatically: Automatically execute stops when triggered
        stop_execution_timeout_seconds: Timeout for stop order execution (uses centralized config)
    """

    def __init__(self, custom_config: Optional[Dict] = None):
        """
        Initialize PositionMonitorConfig with centralized config values.

        Args:
            custom_config: Optional dict with custom values (overrides centralized config)
        """
        # Get centralized config for default values
        tt = get_config().trading_thresholds

        # Use centralized config directly - no hasattr, no fallbacks
        self.check_interval_seconds = tt.position_monitor_check_interval
        self.max_price_fetch_retries = tt.position_monitor_max_retries
        self.price_fetch_timeout_seconds = tt.position_monitor_price_fetch_timeout
        self.auto_restart: bool = True
        self.log_all_checks: bool = False
        self.audit_log_enabled: bool = True

        # Database persistence
        self.persist_state: bool = True
        self.state_sync_interval_seconds = tt.position_monitor_state_sync_interval

        # Stop execution
        self.execute_stops_automatically: bool = True
        self.stop_execution_timeout_seconds = tt.position_monitor_stop_execution_timeout

        # Apply any custom overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(self, key):
                    setattr(self, key, value)


class PositionMonitor:
    """
    Continuously monitors open positions and executes stops automatically.

    This is a CRITICAL production component. It must:
    1. Check every position every second
    2. Execute stop-loss immediately when hit
    3. Execute take-profit immediately when hit
    4. Survive process restarts (load from DB)
    5. Handle broker disconnections gracefully

    Usage:
        monitor = PositionMonitor(broker)
        await monitor.start()

        # Add position to monitor
        position = MonitoredPosition(
            position_id="pos_1",
            symbol="AAPL",
            side="LONG",
            entry_price=Decimal("150.0"),
            quantity=Decimal("100"),
            current_price=Decimal("150.0"),
            stop_loss_pct=Decimal("0.05"),  # 5% stop-loss
        )
        await monitor.add_position(position)

        # Stop monitoring
        await monitor.stop()
    """

    def __init__(
        self,
        broker,
        config: Optional[PositionMonitorConfig] = None,
        on_stop_triggered: Optional[Callable[[MonitoredPosition], None]] = None,
    ):
        """
        Initialize position monitor.

        Args:
            broker: Broker connector for fetching prices and executing orders
            config: Monitor configuration
            on_stop_triggered: Optional callback when stop is triggered
        """
        self.broker = broker
        self.config = config or PositionMonitorConfig()
        self.on_stop_triggered = on_stop_triggered

        # Unique monitor ID for state persistence
        self.monitor_id = (
            f"monitor_{id(self)}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # State
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._state_sync_task: Optional[asyncio.Task] = None

        # Monitored positions (in-memory cache)
        self._positions: Dict[str, MonitoredPosition] = {}

        # Audit log
        self._audit_log: List[Dict[str, Any]] = []

        # Statistics
        self._stats = {
            "monitor_start_time": None,
            "total_checks": 0,
            "stop_loss_triggered": 0,
            "take_profit_triggered": 0,
            "execution_failures": 0,
        }

        logger.info("PositionMonitor initialized")

    async def start(self) -> bool:
        """
        Start monitoring positions.

        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("PositionMonitor already running")
            return False

        self.is_running = True
        self._stats["monitor_start_time"] = datetime.now(timezone.utc)

        # Load existing positions from broker
        await self._load_positions_from_broker()

        # Load persisted state if enabled
        if self.config.persist_state:
            await self._load_state_from_db()

        # Start monitoring loop
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        # Start state sync loop
        if self.config.persist_state:
            self._state_sync_task = asyncio.create_task(self._state_sync_loop())

        logger.info(
            f"PositionMonitor started - monitoring {len(self._positions)} positions "
            f"every {self.config.check_interval_seconds}s"
        )
        return True

    async def stop(self) -> bool:
        """
        Stop monitoring positions.

        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            logger.warning("PositionMonitor not running")
            return False

        self.is_running = False

        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        if self._state_sync_task:
            self._state_sync_task.cancel()
            self._state_sync_task = None

        # Final state sync
        if self.config.persist_state:
            await self._sync_state()

        # Log statistics
        uptime = (
            datetime.now(timezone.utc) - self._stats["monitor_start_time"]
            if self._stats["monitor_start_time"]
            else None
        )
        logger.info(
            f"PositionMonitor stopped - "
            f"uptime: {uptime}, "
            f"total_checks: {self._stats['total_checks']}, "
            f"stop_loss_triggered: {self._stats['stop_loss_triggered']}, "
            f"take_profit_triggered: {self._stats['take_profit_triggered']}, "
            f"execution_failures: {self._stats['execution_failures']}"
        )
        return True

    async def add_position(self, position: MonitoredPosition) -> bool:
        """
        Add a position to monitoring.

        Args:
            position: Position to monitor

        Returns:
            True if added successfully
        """
        # Calculate stop/take prices from percentages if needed
        if position.stop_loss_price is None and position.stop_loss_pct:
            position.stop_loss_price = position.calculate_stop_loss_price()

        if position.take_profit_price is None and position.take_profit_pct:
            position.take_profit_price = position.calculate_take_profit_price()

        self._positions[position.position_id] = position

        if self.config.audit_log_enabled:
            self._audit_log.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "position_added",
                    "position_id": position.position_id,
                    "symbol": position.symbol,
                    "side": position.side,
                    "entry_price": str(position.entry_price),
                    "quantity": str(position.quantity),
                    "stop_loss_price": (
                        str(position.stop_loss_price) if position.stop_loss_price else None
                    ),
                    "take_profit_price": (
                        str(position.take_profit_price) if position.take_profit_price else None
                    ),
                }
            )

        logger.info(
            f"Added position to monitor: {position.symbol} ({position.position_id}) "
            f"- SL: {position.stop_loss_price}, TP: {position.take_profit_price}"
        )
        return True

    async def remove_position(self, position_id: str) -> bool:
        """
        Remove a position from monitoring.

        Args:
            position_id: Position ID to remove

        Returns:
            True if removed successfully
        """
        if position_id not in self._positions:
            logger.warning(f"Position not found for removal: {position_id}")
            return False

        position = self._positions.pop(position_id)

        if self.config.audit_log_enabled:
            self._audit_log.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "position_removed",
                    "position_id": position_id,
                    "symbol": position.symbol,
                    "status": position.status.value,
                    "final_price": str(position.current_price),
                    "final_pnl": str(position.calculate_pnl()),
                }
            )

        logger.info(f"Removed position from monitor: {position.symbol} ({position_id})")
        return True

    async def _load_positions_from_broker(self) -> None:
        """Load open positions from broker."""
        try:
            # Check if broker has get_positions method
            if not hasattr(self.broker, "get_positions"):
                logger.warning("Broker does not support get_positions(), skipping load")
                return

            positions = await self.broker.get_positions()

            if not positions:
                logger.info("No open positions found at broker")
                return

            for pos in positions:
                # Convert broker position to MonitoredPosition
                # Handle different broker position formats
                position_id = (
                    getattr(pos, "position_id", None)
                    or getattr(pos, "id", None)
                    or f"pos_{pos.symbol}_{id(pos)}"
                )

                # Get position side
                quantity = getattr(pos, "position", getattr(pos, "quantity", 0))
                side = "LONG" if quantity > 0 else "SHORT"

                monitored = MonitoredPosition(
                    position_id=position_id,
                    symbol=getattr(pos, "symbol", "UNKNOWN"),
                    side=side,
                    entry_price=to_decimal(
                        getattr(pos, "avg_cost", getattr(pos, "avg_entry_price", 0))
                    ),
                    quantity=to_decimal(abs(quantity)),
                    current_price=to_decimal(getattr(pos, "current_price", 0)),
                )

                await self.add_position(monitored)

            logger.info(f"Loaded {len(positions)} positions from broker")

        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Error loading positions from broker: {e}")

    async def _load_state_from_db(self) -> None:
        """
        Load persisted state from database for recovery.

        CRITICAL: This enables position recovery after restart.
        """
        try:
            from app.database import get_sync_db

            with get_sync_db() as session:
                from app.database.models import PositionState

                # Query the position_state table
                state_record = (
                    session.query(PositionState)
                    .filter(PositionState.monitor_id == self.monitor_id, PositionState.is_active)
                    .first()
                )

                if state_record:
                    # Deserialize positions
                    state_data = json.loads(state_record.positions_json)

                    # Restore positions
                    for pos_data in state_data.get('positions', []):
                        position = MonitoredPosition.from_dict(pos_data)
                        self._positions[position.position_id] = position

                    logger.info(
                        f"Loaded {len(self._positions)} positions from database "
                        f"for monitor {self.monitor_id}"
                    )
                else:
                    logger.info(
                        f"No existing state found in database for monitor {self.monitor_id}"
                    )

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Failed to load state from database: {e}", exc_info=True)

    async def _monitor_loop(self) -> None:
        """Main monitoring loop - checks positions every second."""
        while self.is_running:
            try:
                await self._check_all_positions()
                self._stats["total_checks"] += 1
                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in monitor loop: {e}")
                if self.config.auto_restart:
                    logger.info("Auto-restarting monitor loop in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    raise

    async def _check_all_positions(self) -> None:
        """Check all monitored positions for stop/take triggers."""
        if not self._positions:
            return

        # Fetch current prices for all symbols
        symbols = {p.symbol for p in self._positions.values()}
        prices = await self._fetch_current_prices(symbols)

        # Check each position (use list() to avoid dictionary changed size error)
        for position in list(self._positions.values()):
            if position.status != PositionStatus.ACTIVE:
                continue

            # Update current price
            current_price = prices.get(position.symbol)
            if current_price is not None:
                position.update_current_price(current_price)
            else:
                logger.warning(f"Could not fetch price for {position.symbol}")
                continue

            # Check stop-loss
            if position.should_trigger_stop_loss():
                await self._on_stop_loss_triggered(position)
                continue

            # Check take-profit
            if position.should_trigger_take_profit():
                await self._on_take_profit_triggered(position)
                continue

            # Log check if enabled
            if self.config.log_all_checks:
                logger.debug(
                    f"Checked {position.symbol}: {position.current_price} "
                    f"(SL: {position.stop_loss_price}, TP: {position.take_profit_price}) "
                    f"P&L: {position.calculate_pnl()}"
                )

    async def _fetch_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Fetch current prices for multiple symbols.

        Args:
            symbols: List of symbols to fetch prices for

        Returns:
            Dictionary mapping symbol to price
        """
        prices = {}

        for symbol in symbols:
            try:
                # Check if broker has get_quote or get_market_data method
                if hasattr(self.broker, "get_quote"):
                    quote = await asyncio.wait_for(
                        self.broker.get_quote(symbol),
                        timeout=self.config.price_fetch_timeout_seconds,
                    )

                    if quote and hasattr(quote, "last_price"):
                        prices[symbol] = to_decimal(quote.last_price)

                elif hasattr(self.broker, "get_market_data"):
                    market_data = await asyncio.wait_for(
                        self.broker.get_market_data(symbol),
                        timeout=self.config.price_fetch_timeout_seconds,
                    )

                    if market_data and "last" in market_data:
                        prices[symbol] = to_decimal(market_data["last"])

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching price for {symbol}")
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error fetching price for {symbol}: {e}")

        return prices

    async def _on_stop_loss_triggered(self, position: MonitoredPosition) -> None:
        """
        Handle stop-loss trigger.

        Args:
            position: Position with triggered stop-loss
        """
        position.status = PositionStatus.STOP_LOSS_TRIGGERED
        self._stats["stop_loss_triggered"] += 1

        pnl = position.calculate_pnl()
        pnl_pct = position.calculate_pnl_percentage()

        if self.config.audit_log_enabled:
            self._audit_log.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "stop_loss_triggered",
                    "position_id": position.position_id,
                    "symbol": position.symbol,
                    "side": position.side,
                    "entry_price": str(position.entry_price),
                    "trigger_price": str(position.current_price),
                    "stop_price": str(position.stop_loss_price),
                    "pnl": str(pnl),
                    "pnl_pct": str(pnl_pct) if pnl_pct else None,
                }
            )

        logger.critical(
            f"STOP LOSS TRIGGERED: {position.symbol} @ {position.current_price} "
            f"(entry: {position.entry_price}, stop: {position.stop_loss_price}) "
            f"P&L: {pnl} ({pnl_pct}%)"  # type: ignore
        )

        # Execute stop if configured
        if self.config.execute_stops_automatically:
            from . import stop_executor  # noqa: F811

            executor = stop_executor.StopExecutor(  # type: ignore
                self.broker, order_timeout=self.config.stop_execution_timeout_seconds
            )
            result = await executor.execute_stop_loss(position)

            if result.success:
                position.status = PositionStatus.CLOSED
                await self.remove_position(position.position_id)
            else:
                self._stats["execution_failures"] += 1
                position.status = PositionStatus.ERROR
                logger.error(
                    f"Failed to execute stop-loss for {position.symbol}: {result.error_message}"
                )

        # Call callback if provided
        if self.on_stop_triggered:
            try:
                self.on_stop_triggered(position)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error in stop triggered callback: {e}")

    async def _on_take_profit_triggered(self, position: MonitoredPosition) -> None:
        """
        Handle take-profit trigger.

        Args:
            position: Position with triggered take-profit
        """
        position.status = PositionStatus.TAKE_PROFIT_TRIGGERED
        self._stats["take_profit_triggered"] += 1

        pnl = position.calculate_pnl()
        pnl_pct = position.calculate_pnl_percentage()

        if self.config.audit_log_enabled:
            self._audit_log.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "take_profit_triggered",
                    "position_id": position.position_id,
                    "symbol": position.symbol,
                    "side": position.side,
                    "entry_price": str(position.entry_price),
                    "trigger_price": str(position.current_price),
                    "take_profit_price": str(position.take_profit_price),
                    "pnl": str(pnl),
                    "pnl_pct": str(pnl_pct) if pnl_pct else None,
                }
            )

        logger.info(
            f"TAKE PROFIT TRIGGERED: {position.symbol} @ {position.current_price} "
            f"(entry: {position.entry_price}, target: {position.take_profit_price}) "
            f"P&L: {pnl} ({pnl_pct}%)"  # type: ignore
        )

        # Execute take profit if configured
        if self.config.execute_stops_automatically:
            from . import stop_executor  # noqa: F811

            executor = stop_executor.StopExecutor(  # type: ignore
                self.broker, order_timeout=self.config.stop_execution_timeout_seconds
            )
            result = await executor.execute_take_profit(position)

            if result.success:
                position.status = PositionStatus.CLOSED
                await self.remove_position(position.position_id)
            else:
                self._stats["execution_failures"] += 1
                position.status = PositionStatus.ERROR
                logger.error(
                    f"Failed to execute take-profit for {position.symbol}: {result.error_message}"
                )

        # Call callback if provided
        if self.on_stop_triggered:
            try:
                self.on_stop_triggered(position)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in take profit callback: {e}")

    async def _state_sync_loop(self) -> None:
        """Periodically sync state to database."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.state_sync_interval_seconds)
                await self._sync_state()
            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in state sync loop: {e}")

    async def _sync_state(self) -> None:
        """
        Sync current state to database for recovery.

        CRITICAL: This enables position recovery after restart.
        """
        try:
            from app.database import get_sync_db

            with get_sync_db() as session:
                from app.database.models import PositionState

                # Serialize current positions
                positions_list = [pos.to_dict() for pos in self._positions.values()]
                state_json = json.dumps(
                    {
                        'positions': positions_list,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    },
                    default=str,
                )

                # Check if state exists
                existing = (
                    session.query(PositionState)
                    .filter(PositionState.monitor_id == self.monitor_id)
                    .first()
                )

                if existing:
                    # Update existing
                    existing.positions_json = state_json
                    existing.last_sync = datetime.now(timezone.utc)
                    existing.version += 1
                else:
                    # Create new
                    new_state = PositionState(
                        monitor_id=self.monitor_id,
                        positions_json=state_json,
                        last_sync=datetime.now(timezone.utc),
                        is_active=True,
                    )
                    session.add(new_state)

                session.commit()
                logger.debug(f"State synced to database for monitor {self.monitor_id}")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to sync state to database: {e}", exc_info=True)

    def get_monitored_positions(self) -> List[MonitoredPosition]:
        """Get list of all monitored positions."""
        return list(self._positions.values())

    def get_active_positions(self) -> List[MonitoredPosition]:
        """Get list of active positions only."""
        return [p for p in self._positions.values() if p.status == PositionStatus.ACTIVE]

    def get_position(self, position_id: str) -> Optional[MonitoredPosition]:
        """Get a specific monitored position."""
        return self._positions.get(position_id)

    def get_positions_by_symbol(self, symbol: str) -> List[MonitoredPosition]:
        """Get all monitored positions for a symbol."""
        return [p for p in self._positions.values() if p.symbol == symbol]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        return self._audit_log[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        active = sum(1 for p in self._positions.values() if p.status == PositionStatus.ACTIVE)
        stopped = sum(
            1 for p in self._positions.values() if p.status == PositionStatus.STOP_LOSS_TRIGGERED
        )
        profited = sum(
            1 for p in self._positions.values() if p.status == PositionStatus.TAKE_PROFIT_TRIGGERED
        )
        errors = sum(1 for p in self._positions.values() if p.status == PositionStatus.ERROR)

        uptime = (
            datetime.now(timezone.utc) - self._stats["monitor_start_time"]
            if self._stats["monitor_start_time"]
            else None
        )

        return {
            "is_running": self.is_running,
            "uptime_seconds": uptime.total_seconds() if uptime else 0,
            "total_positions": len(self._positions),
            "active_positions": active,
            "stop_loss_triggered": stopped,
            "take_profit_triggered": profited,
            "error_positions": errors,
            "audit_log_entries": len(self._audit_log),
            "check_interval_seconds": self.config.check_interval_seconds,
            "total_checks": self._stats["total_checks"],
            "stop_loss_triggered_count": self._stats["stop_loss_triggered"],
            "take_profit_triggered_count": self._stats["take_profit_triggered"],
            "execution_failures": self._stats["execution_failures"],
        }

    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all monitored positions."""
        positions = self.get_monitored_positions()

        total_pnl = sum(p.calculate_pnl() for p in positions)
        total_value = sum(p.entry_price * p.quantity for p in positions)

        return {
            "total_positions": len(positions),
            "active_positions": len(self.get_active_positions()),
            "total_unrealized_pnl": str(total_pnl),
            "total_value": str(total_value),
            "positions_by_symbol": {
                symbol: len([p for p in positions if p.symbol == symbol])
                for symbol in {p.symbol for p in positions}
            },
            "positions_by_status": {
                "active": sum(1 for p in positions if p.status == PositionStatus.ACTIVE),
                "stopped": sum(
                    1 for p in positions if p.status == PositionStatus.STOP_LOSS_TRIGGERED
                ),
                "profited": sum(
                    1 for p in positions if p.status == PositionStatus.TAKE_PROFIT_TRIGGERED
                ),
                "closed": sum(1 for p in positions if p.status == PositionStatus.CLOSED),
                "error": sum(1 for p in positions if p.status == PositionStatus.ERROR),
            },
        }
