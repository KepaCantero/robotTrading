"""
Circuit Breaker Manager V2 - Detects market halts and stops trading.

Protects against:
- Market-wide circuit breakers (Level 1: 7%, Level 2: 13%, Level 3: 20%)
- Single-stock trading halts
- Extreme volatility events
- Technical issues

This is a CRITICAL component for production trading.
Uses centralized configuration for all thresholds.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.shared.config.centralized_config import get_config
from app.shared.utils.decimal_utils import to_decimal
from app.core.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class CircuitBreakerLevel(Enum):
    """Market-wide circuit breaker levels."""

    LEVEL_1 = "level_1"  # 7% drop - 15 min halt
    LEVEL_2 = "level_2"  # 13% drop - 15 min halt
    LEVEL_3 = "level_3"  # 20% drop - Rest of day


class TradingStatus(Enum):
    """Trading status of market or symbol."""

    TRADING = "trading"
    HALTED = "halted"
    LIMIT_UP = "limit_up"  # Price reached upper limit
    LIMIT_DOWN = "limit_down"  # Price reached lower limit
    UNKNOWN = "unknown"


@dataclass
class MarketState:
    """Current state of a market or symbol."""

    symbol: str
    status: TradingStatus
    current_price: Decimal
    change_pct: Decimal
    volume: Optional[Decimal] = None
    vix: Optional[Decimal] = None
    last_update: datetime = field(default_factory=utc_now)
    halt_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "status": self.status.value,
            "current_price": str(self.current_price),
            "change_pct": str(self.change_pct),
            "volume": str(self.volume) if self.volume else None,
            "vix": str(self.vix) if self.vix else None,
            "last_update": self.last_update.isoformat(),
            "halt_reason": self.halt_reason,
        }


@dataclass
class CircuitBreakerEvent:
    """Record of a circuit breaker event."""

    timestamp: datetime
    symbol: str
    level: Optional[CircuitBreakerLevel]
    reason: str
    change_pct: Decimal

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "level": self.level.value if self.level else None,
            "reason": self.reason,
            "change_pct": str(self.change_pct),
        }


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior - uses centralized config."""

    def __init__(self, custom_config: Optional[Dict] = None):
        """Initialize config with centralized values."""
        tt = get_config().trading_thresholds

        # Market-wide thresholds (percentage drops) - from centralized config
        self.LEVEL_1_THRESHOLD = Decimal(str(tt.circuit_breaker_level_1))
        self.LEVEL_2_THRESHOLD = Decimal(str(tt.circuit_breaker_level_2))
        self.LEVEL_3_THRESHOLD = Decimal(str(tt.circuit_breaker_level_3))

        # Single stock halt thresholds - from centralized config
        self.STOCK_VOLATILITY_THRESHOLD = Decimal(str(tt.circuit_breaker_stock_volatility))
        self.STOCK_VOLUME_THRESHOLD = Decimal("0")

        # VIX thresholds - from centralized config
        self.VIX_HIGH = Decimal(str(tt.circuit_breaker_vix_high))
        self.VIX_EXTREME = Decimal(str(tt.circuit_breaker_vix_extreme))

        # Monitoring settings - from centralized config
        self.check_interval_seconds = float(getattr(
            tt, 'circuit_breaker_check_interval_seconds', 30.0
        ))
        self.market_index_symbol: str = "SPY"

        # Auto-resume settings - from centralized config
        self.auto_resume_on_halt_lift: bool = True
        self.halt_check_interval_seconds = float(getattr(
            tt, 'circuit_breaker_halt_check_interval_seconds', 60.0
        ))

        # Apply any custom overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(self, key):
                    setattr(self, key, value)


class CircuitBreakerManager:
    """
    Detects market halts and stops trading.

    Monitors:
    - Market-wide circuit breakers (S&P 500 drops)
    - Single-stock trading halts
    - Extreme volatility (VIX)
    - Technical issues

    When triggered, will:
    - Pause all trading
    - Log the event
    - Send alerts
    - Auto-resume when halt lifted
    """

    def __init__(
        self,
        broker,
        data_service,
        config: Optional[CircuitBreakerConfig] = None,
        on_halt: Optional[Callable[[CircuitBreakerEvent], None]] = None,
        on_resume: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize circuit breaker manager.

        Args:
            broker: Broker connector for executing trades
            data_service: Market data service for fetching prices
            config: Circuit breaker configuration
            on_halt: Callback when trading is halted
            on_resume: Callback when trading resumes
        """
        self.broker = broker
        self.data_service = data_service
        self.config = config or CircuitBreakerConfig()
        self.on_halt = on_halt
        self.on_resume = on_resume

        # State
        self._is_monitoring = False
        self._is_trading_paused = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._halt_check_task: Optional[asyncio.Task] = None

        # Track market states
        self._market_states: Dict[str, MarketState] = {}
        self._halted_symbols: Set[str] = set()

        # Event history
        self._events: List[CircuitBreakerEvent] = []

        logger.info("CircuitBreakerManager initialized")

    async def start(self) -> bool:
        """
        Start monitoring market status.

        Returns:
            True if started successfully
        """
        if self._is_monitoring:
            logger.warning("CircuitBreakerManager already monitoring")
            return False

        self._is_monitoring = True

        # Start monitoring loop
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("CircuitBreakerManager started monitoring")
        return True

    async def stop(self) -> bool:
        """
        Stop monitoring market status.

        Returns:
            True if stopped successfully
        """
        if not self._is_monitoring:
            logger.warning("CircuitBreakerManager not monitoring")
            return False

        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        if self._halt_check_task:
            self._halt_check_task.cancel()
            self._halt_check_task = None

        logger.info("CircuitBreakerManager stopped")
        return True

    async def pause_all_trading(self, reason: str) -> None:
        """
        Pause all trading activity.

        Args:
            reason: Reason for pausing
        """
        if self._is_trading_paused:
            logger.warning("Trading already paused")
            return

        self._is_trading_paused = True

        logger.critical(f"TRADING PAUSED: {reason}")

        # Cancel any pending orders
        try:
            open_orders = await self.broker.get_open_orders()
            for order in open_orders:
                await self.broker.cancel_order(order.order_id)
                logger.info(f"Cancelled order {order.order_id} due to trading pause")
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Error cancelling orders: {e}")

    async def resume_all_trading(self, reason: str = "Halt lifted") -> None:
        """
        Resume all trading activity.

        Args:
            reason: Reason for resuming
        """
        if not self._is_trading_paused:
            logger.warning("Trading not paused")
            return

        self._is_trading_paused = False

        logger.info(f"TRADING RESUMED: {reason}")

    async def is_market_halted(self) -> bool:
        """
        Check if market is in circuit breaker.

        Returns:
            True if market is halted
        """
        # Check if trading is paused
        if self._is_trading_paused:
            return True

        # Check if market index is halted
        market_state = self._market_states.get(self.config.market_index_symbol)
        if market_state and market_state.status != TradingStatus.TRADING:
            return True

        return False

    async def _monitor_loop(self) -> None:
        """Check for halts every 30 seconds."""
        while self._is_monitoring:
            try:
                # Check market-wide halts
                await self._check_market_wide_halt()

                # Check individual symbol halts
                await self._check_symbol_halts()

                # Check VIX level
                await self._check_vix_level()

                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)

    async def _check_market_wide_halt(self) -> None:
        """Check for market-wide circuit breakers."""
        try:
            # Get market index data (use SPY as proxy)
            index_data = await self.data_service.get_quote(self.config.market_index_symbol)

            if not index_data:
                logger.warning(f"Could not fetch data for {self.config.market_index_symbol}")
                return

            current_price = to_decimal(getattr(index_data, 'last_price', 0))
            change_pct = to_decimal(getattr(index_data, 'change_percent', 0))

            # Update market state
            self._market_states[self.config.market_index_symbol] = MarketState(
                symbol=self.config.market_index_symbol,
                status=TradingStatus.TRADING,
                current_price=current_price,
                change_pct=change_pct,
                last_update=utc_now(),
            )

            # Check circuit breaker levels
            if change_pct <= self.config.LEVEL_3_THRESHOLD:
                await self._on_circuit_breaker_triggered(
                    CircuitBreakerLevel.LEVEL_3,
                    self.config.market_index_symbol,
                    change_pct,
                )
            elif change_pct <= self.config.LEVEL_2_THRESHOLD:
                await self._on_circuit_breaker_triggered(
                    CircuitBreakerLevel.LEVEL_2,
                    self.config.market_index_symbol,
                    change_pct,
                )
            elif change_pct <= self.config.LEVEL_1_THRESHOLD:
                await self._on_circuit_breaker_triggered(
                    CircuitBreakerLevel.LEVEL_1,
                    self.config.market_index_symbol,
                    change_pct,
                )

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error checking market-wide halt: {e}")

    async def _check_symbol_halts(self) -> None:
        """Check for individual symbol trading halts."""
        # Get currently held symbols
        try:
            positions = await self.broker.get_positions()
            symbols = [p.symbol for p in positions] if positions else []

            for symbol in symbols:
                try:
                    quote = await self.data_service.get_quote(symbol)

                    if not quote:
                        continue

                    # Check for halt indicators
                    is_halted = getattr(quote, 'is_halted', False)
                    change_pct = to_decimal(getattr(quote, 'change_percent', 0))

                    if is_halted:
                        await self._on_symbol_halted(symbol, "Trading halt detected")

                    # Update state
                    self._market_states[symbol] = MarketState(
                        symbol=symbol,
                        status=TradingStatus.HALTED if is_halted else TradingStatus.TRADING,
                        current_price=to_decimal(getattr(quote, 'last_price', 0)),
                        change_pct=change_pct,
                        last_update=utc_now(),
                    )

                except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                    logger.error(f"Error checking halt for {symbol}: {e}")

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting positions for halt check: {e}")

    async def _check_vix_level(self) -> None:
        """Check VIX level for extreme volatility."""
        try:
            # Try to get VIX data (symbol: VIX or ^VIX)
            vix_data = await self.data_service.get_quote("VIX")

            if not vix_data:
                return

            vix = to_decimal(getattr(vix_data, 'last_price', 0))

            if vix >= self.config.VIX_EXTREME:
                await self.pause_all_trading(f"VIX at panic level: {vix}")
                logger.critical(f"VIX EXTREME: {vix}")
            elif vix >= self.config.VIX_HIGH:
                logger.warning(f"VIX HIGH: {vix}")

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Could not check VIX level: {e}")

    async def _on_circuit_breaker_triggered(
        self,
        level: CircuitBreakerLevel,
        symbol: str,
        change_pct: Decimal,
    ) -> None:
        """Handle circuit breaker trigger."""
        logger.critical(
            f"CIRCUIT BREAKER {level.value} TRIGGERED: " f"{symbol} down {abs(change_pct):.1%}"
        )

        # Pause all trading
        await self.pause_all_trading(
            f"Circuit breaker {level.value} - {symbol} down {abs(change_pct):.1%}"
        )

        # Record event
        event = CircuitBreakerEvent(
            timestamp=utc_now(),
            symbol=symbol,
            level=level,
            reason=f"Market dropped {abs(change_pct):.1%}",
            change_pct=change_pct,
        )
        self._events.append(event)

        # Call callback
        if self.on_halt:
            try:
                self.on_halt(event)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in halt callback: {e}")

        # Start halt check loop
        if self.config.auto_resume_on_halt_lift:
            self._halt_check_task = asyncio.create_task(self._halt_check_loop(symbol))

    async def _on_symbol_halted(self, symbol: str, reason: str) -> None:
        """Handle single symbol halt."""
        logger.warning(f"SYMBOL HALTED: {symbol} - {reason}")

        self._halted_symbols.add(symbol)

        # Record event
        event = CircuitBreakerEvent(
            timestamp=utc_now(),
            symbol=symbol,
            level=None,
            reason=reason,
            change_pct=Decimal("0"),
        )
        self._events.append(event)

        # Call callback
        if self.on_halt:
            try:
                self.on_halt(event)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in halt callback: {e}")

    async def _halt_check_loop(self, symbol: str) -> None:
        """Check if halt has been lifted."""
        while self._is_monitoring and self._is_trading_paused:
            try:
                await asyncio.sleep(self.config.halt_check_interval_seconds)

                # Check if market is still halted
                quote = await self.data_service.get_quote(symbol)

                if quote and not getattr(quote, 'is_halted', True):
                    # Halt lifted
                    await self.resume_all_trading(f"Halt lifted for {symbol}")

                    if self.on_resume:
                        try:
                            self.on_resume(symbol)
                        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                            logger.error(f"Error in resume callback: {e}")

                    break

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"Error in halt check loop: {e}")

    def get_market_state(self, symbol: str) -> Optional[MarketState]:
        """Get current state of a market or symbol."""
        return self._market_states.get(symbol)

    def get_halted_symbols(self) -> Set[str]:
        """Get set of currently halted symbols."""
        return self._halted_symbols.copy()

    def get_events(self, limit: int = 100) -> List[CircuitBreakerEvent]:
        """Get circuit breaker events."""
        return self._events[-limit:]

    def is_trading_paused(self) -> bool:
        """Check if trading is currently paused."""
        return self._is_trading_paused
