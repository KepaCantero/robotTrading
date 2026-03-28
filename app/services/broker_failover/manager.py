"""
Broker Failover Manager - Manage multiple broker connections with failover.

Provides:
- Automatic failover to secondary broker
- Health checks every minute
- Position sync across brokers
- Configurable failover triggers
- Alert on failover
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class BrokerHealth(Enum):
    """Health status of a broker."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class BrokerConfig:
    """Configuration for a broker."""

    name: str
    broker: object  # Broker adapter instance
    priority: int  # 1 = highest priority
    enabled: bool = True
    health_check_interval: float = 60.0  # seconds
    failover_timeout: float = 30.0  # seconds


@dataclass
class BrokerState:
    """Current state of a broker."""

    name: str
    health: BrokerHealth
    is_primary: bool
    is_active: bool
    last_health_check: datetime
    consecutive_failures: int = 0
    total_failures: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Union[str, int, float, bool, datetime, None]]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "health": self.health.value,
            "is_primary": self.is_primary,
            "is_active": self.is_active,
            "last_health_check": self.last_health_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "total_failures": self.total_failures,
            "last_error": self.last_error,
        }


class BrokerFailoverManager:
    """
    Manage multiple broker connections with failover.

    Features:
    - Automatic failover to secondary broker
    - Health checks every minute
    - Position sync across brokers
    - Configurable failover triggers
    - Alert on failover
    """

    def __init__(
        self,
        brokers: List[BrokerConfig],
        on_failover: Optional[Callable[[str, str], None]] = None,
        health_check_interval: float = 60.0,
    ):
        """
        Initialize broker failover manager.

        Args:
            brokers: List of broker configurations
            on_failover: Callback when failover occurs (from_broker, to_broker)
            health_check_interval: How often to check broker health
        """
        # Sort brokers by priority
        self.brokers = sorted(brokers, key=lambda b: b.priority)
        self.on_failover = on_failover
        self.health_check_interval = health_check_interval

        # State
        self._active_broker: Optional[BrokerConfig] = None
        self._broker_states: Dict[str, BrokerState] = {}
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Initialize states
        for broker in self.brokers:
            self._broker_states[broker.name] = BrokerState(
                name=broker.name,
                health=BrokerHealth.UNKNOWN,
                is_primary=(broker == self.brokers[0]),
                is_active=False,
                last_health_check=utc_now(),
            )

        logger.info(
            f"BrokerFailoverManager initialized with {len(brokers)} brokers: "
            f"{[b.name for b in brokers]}"
        )

    async def start(self) -> bool:
        """Start health monitoring."""
        if self._is_monitoring:
            logger.warning("BrokerFailoverManager already running")
            return False

        self._is_monitoring = True

        # Try to connect to primary broker
        await self._connect_to_primary()

        # Start health check loop
        self._monitor_task = asyncio.create_task(self._health_check_loop())

        logger.info("BrokerFailoverManager started")
        return True

    async def stop(self) -> bool:
        """Stop health monitoring."""
        if not self._is_monitoring:
            logger.warning("BrokerFailoverManager not running")
            return False

        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        logger.info("BrokerFailoverManager stopped")
        return True

    async def execute_order_with_failover(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = "MARKET",
        price: Optional[Decimal] = None,
    ) -> Optional[object]:
        """
        Try primary broker, failover to secondary if needed.

        Args:
            symbol: Symbol to trade
            side: BUY or SELL
            quantity: Quantity
            order_type: Order type
            price: Limit price (for LIMIT orders)

        Returns:
            Order object if successful
        """
        brokers = [b for b in self.brokers if b.enabled]

        for broker_config in brokers:
            try:
                logger.debug(f"Trying broker {broker_config.name} for order")

                # Import OrderSide and OrderType for broker adapters
                from app.services.live_trading.broker_connector import OrderSide, OrderType

                # Convert string parameters to enums if needed
                order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

                # Map order type string to enum
                order_type_map = {
                    "MARKET": OrderType.MARKET,
                    "MKT": OrderType.MARKET,
                    "LIMIT": OrderType.LIMIT,
                    "LMT": OrderType.LIMIT,
                    "STOP": OrderType.STOP,
                    "STP": OrderType.STOP,
                    "STOP_LIMIT": OrderType.STOP_LIMIT,
                }
                order_type_enum = order_type_map.get(order_type.upper(), OrderType.MARKET)

                execution = await asyncio.wait_for(
                    broker_config.broker.place_order(
                        symbol=symbol,
                        side=order_side,
                        quantity=quantity,
                        order_type=order_type_enum,
                        price=price,
                    ),
                    timeout=self.brokers[0].failover_timeout,
                )

                if execution:
                    logger.info(f"Order executed via {broker_config.name}")
                    return execution

            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(f"Broker {broker_config.name} failed: {e}")
                await self._mark_broker_unhealthy(broker_config.name, str(e))
                continue

        logger.error("All brokers failed")
        return None

    async def sync_positions(self) -> Dict[str, Dict[str, object]]:
        """
        Sync positions across all brokers.

        Returns:
            Dictionary with broker name as key and positions as value
        """
        positions_by_broker = {}

        for broker_config in self.brokers:
            if not broker_config.enabled:
                continue

            try:
                from app.services.live_trading.broker_connector import BrokerPosition

                positions: List[BrokerPosition] = await broker_config.broker.get_positions()
                positions_by_broker[broker_config.name] = {pos.symbol: pos for pos in positions}

                logger.debug(f"Synced {len(positions)} positions from {broker_config.name}")
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Failed to sync positions from {broker_config.name}: {e}")
                positions_by_broker[broker_config.name] = {}

        return positions_by_broker

    async def get_account_info(self) -> Optional[Dict[str, Union[str, int, float, bool, Decimal]]]:
        """
        Get account info from active broker with failover.

        Returns:
            Account information dict or None
        """
        # Try active broker first
        if self._active_broker:
            try:
                account = await self._active_broker.broker.get_account_info()
                if account:
                    return account
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(f"Failed to get account info from {self._active_broker.name}: {e}")

        # Try other brokers
        for broker_config in self.brokers:
            if broker_config.name == self._active_broker.name:
                continue
            if not broker_config.enabled:
                continue

            try:
                account = await broker_config.broker.get_account_info()
                if account:
                    logger.info(f"Got account info from backup broker {broker_config.name}")
                    return account
            except (OSError, ValueError):
                continue

        return None

    async def _connect_to_primary(self) -> None:
        """Try to connect to primary broker."""
        if not self.brokers:
            logger.error("No brokers configured")
            return

        for broker in self.brokers:
            if not broker.enabled:
                continue

            if await self._check_broker_health(broker):
                self._active_broker = broker
                state = self._broker_states[broker.name]
                state.is_active = True
                state.health = BrokerHealth.HEALTHY
                logger.info(f"Connected to primary broker: {broker.name}")
                return

        logger.error("Could not connect to any broker")

    async def _health_check_loop(self) -> None:
        """Check broker health every minute."""
        while self._is_monitoring:
            try:
                for broker in self.brokers:
                    if not broker.enabled:
                        continue

                    is_healthy = await self._check_broker_health(broker)
                    state = self._broker_states[broker.name]

                    if is_healthy:
                        if state.health != BrokerHealth.HEALTHY:
                            state.health = BrokerHealth.HEALTHY
                            state.consecutive_failures = 0
                            logger.info(f"Broker {broker.name} recovered")
                    else:
                        state.consecutive_failures += 1
                        state.total_failures += 1

                        if state.consecutive_failures >= 3:
                            await self._mark_broker_unhealthy(
                                broker.name, f"{state.consecutive_failures} consecutive failures"
                            )

                # Check if we need to failover
                if self._active_broker:
                    active_state = self._broker_states[self._active_broker.name]
                    if active_state.health == BrokerHealth.UNHEALTHY:
                        await self._trigger_failover()

                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _check_broker_health(self, broker: BrokerConfig) -> bool:
        """Check if broker is healthy."""
        try:
            # Try to get account info
            account = await asyncio.wait_for(
                broker.broker.get_account_info(),
                timeout=10.0,
            )

            return account is not None

        except (asyncio.TimeoutError, OSError) as e:
            logger.debug(f"Health check failed for {broker.name}: {e}")
            return False

    async def _mark_broker_unhealthy(self, name: str, reason: str) -> None:
        """Mark broker as unhealthy."""
        state = self._broker_states[name]
        state.health = BrokerHealth.UNHEALTHY
        state.last_error = reason

        logger.warning(f"Broker {name} marked unhealthy: {reason}")

    async def _trigger_failover(self) -> None:
        """Trigger failover to next healthy broker."""
        if not self._active_broker:
            return

        old_broker = self._active_broker

        # Find next healthy broker
        for broker in self.brokers:
            if broker.name == old_broker.name:
                continue

            state = self._broker_states[broker.name]
            if state.health == BrokerHealth.HEALTHY and broker.enabled:
                # Switch active broker
                self._active_broker = broker

                # Update states
                old_state = self._broker_states[old_broker.name]
                old_state.is_active = False
                state.is_active = True

                logger.critical(f"FAILOVER: {old_broker.name} -> {broker.name}")

                # Call callback
                if self.on_failover:
                    try:
                        self.on_failover(old_broker.name, broker.name)
                    except (OSError, ValueError) as e:
                        logger.error(f"Error in failover callback: {e}")

                return

        logger.error("No healthy broker available for failover")

    def get_active_broker(self) -> Optional[object]:
        """Get currently active broker."""
        return self._active_broker.broker if self._active_broker else None

    def get_active_broker_name(self) -> Optional[str]:
        """Get name of currently active broker."""
        return self._active_broker.name if self._active_broker else None

    def get_broker_states(self) -> Dict[str, BrokerState]:
        """Get state of all brokers."""
        return self._broker_states.copy()

    def get_statistics(self) -> Dict[str, Union[str, int, bool, None]]:
        """Get failover statistics."""
        return {
            "active_broker": self._active_broker.name if self._active_broker else None,
            "total_brokers": len(self.brokers),
            "healthy_brokers": sum(
                1 for s in self._broker_states.values() if s.health == BrokerHealth.HEALTHY
            ),
            "unhealthy_brokers": sum(
                1 for s in self._broker_states.values() if s.health == BrokerHealth.UNHEALTHY
            ),
            "is_monitoring": self._is_monitoring,
        }

    def get_health_report(self) -> Dict[str, Union[str, int, bool, None, Dict, List]]:
        """
        Generate a comprehensive health report.

        Returns:
            Dictionary with health status of all brokers
        """
        report = {
            "timestamp": utc_now().isoformat(),
            "active_broker": self._active_broker.name if self._active_broker else None,
            "monitoring_active": self._is_monitoring,
            "brokers": {},
        }

        for broker_name, state in self._broker_states.items():
            report["brokers"][broker_name] = state.to_dict()

        return report

    async def force_failover(self, target_broker_name: str) -> bool:
        """
        Manually trigger failover to a specific broker.

        Args:
            target_broker_name: Name of broker to failover to

        Returns:
            True if failover successful
        """
        # Find target broker
        target_broker = None
        for broker in self.brokers:
            if broker.name == target_broker_name:
                target_broker = broker
                break

        if not target_broker:
            logger.error(f"Target broker {target_broker_name} not found")
            return False

        if not target_broker.enabled:
            logger.error(f"Target broker {target_broker_name} is not enabled")
            return False

        old_broker = self._active_broker

        # Switch active broker
        self._active_broker = target_broker

        # Update states
        if old_broker:
            old_state = self._broker_states[old_broker.name]
            old_state.is_active = False

        target_state = self._broker_states[target_broker.name]
        target_state.is_active = True
        target_state.health = BrokerHealth.HEALTHY

        logger.info(
            f"Manual failover: {old_broker.name if old_broker else 'None'} -> {target_broker.name}"
        )

        # Call callback
        if self.on_failover and old_broker:
            try:
                self.on_failover(old_broker.name, target_broker.name)
            except (OSError, ValueError) as e:
                logger.error(f"Error in failover callback: {e}")

        return True

    def enable_broker(self, broker_name: str) -> bool:
        """Enable a broker."""
        for broker in self.brokers:
            if broker.name == broker_name:
                broker.enabled = True
                logger.info(f"Broker {broker_name} enabled")
                return True
        return False

    def disable_broker(self, broker_name: str) -> bool:
        """Disable a broker."""
        for broker in self.brokers:
            if broker.name == broker_name:
                broker.enabled = False
                logger.info(f"Broker {broker_name} disabled")
                return True
        return False
