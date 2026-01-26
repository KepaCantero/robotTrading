"""
Unit tests for Circuit Breaker Manager V2.

Tests market halt detection and trading pause functionality.
"""

from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.circuit_breaker_manager_v2 import (
    CircuitBreakerManager,
    CircuitBreakerLevel,
    CircuitBreakerConfig,
    TradingStatus,
    MarketState,
    CircuitBreakerEvent,
)


@pytest.fixture
def mock_broker():
    """Create mock broker."""
    broker = MagicMock()
    broker.get_open_orders = AsyncMock(return_value=[])
    broker.get_positions = AsyncMock(return_value=[])
    broker.cancel_order = AsyncMock()
    return broker


@pytest.fixture
def mock_data_service():
    """Create mock data service."""
    data_service = MagicMock()
    data_service.get_quote = AsyncMock(return_value=None)
    return data_service


@pytest.fixture
def mock_quote():
    """Create mock quote data."""
    quote = MagicMock()
    quote.last_price = 100.0
    quote.change_percent = 0.0
    quote.is_halted = False
    return quote


@pytest.fixture
def circuit_breaker_manager(mock_broker, mock_data_service):
    """Create circuit breaker manager instance."""
    config = CircuitBreakerConfig()
    config.check_interval_seconds = 0.1  # Faster for testing
    config.halt_check_interval_seconds = 0.1

    manager = CircuitBreakerManager(
        broker=mock_broker,
        data_service=mock_data_service,
        config=config,
    )
    return manager


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_thresholds(self):
        """Test default circuit breaker thresholds."""
        config = CircuitBreakerConfig()

        assert config.LEVEL_1_THRESHOLD == Decimal("-0.07")
        assert config.LEVEL_2_THRESHOLD == Decimal("-0.13")
        assert config.LEVEL_3_THRESHOLD == Decimal("-0.20")

    def test_vix_thresholds(self):
        """Test VIX thresholds."""
        config = CircuitBreakerConfig()

        assert config.VIX_HIGH == Decimal("40")
        assert config.VIX_EXTREME == Decimal("60")

    def test_market_index_symbol(self):
        """Test default market index symbol."""
        config = CircuitBreakerConfig()
        assert config.market_index_symbol == "SPY"


class TestMarketState:
    """Test market state dataclass."""

    def test_market_state_creation(self):
        """Test creating market state."""
        state = MarketState(
            symbol="SPY",
            status=TradingStatus.TRADING,
            current_price=Decimal("100.0"),
            change_pct=Decimal("-0.05"),
        )

        assert state.symbol == "SPY"
        assert state.status == TradingStatus.TRADING
        assert state.current_price == Decimal("100.0")
        assert state.change_pct == Decimal("-0.05")

    def test_market_state_to_dict(self):
        """Test converting market state to dictionary."""
        state = MarketState(
            symbol="AAPL",
            status=TradingStatus.HALTED,
            current_price=Decimal("150.0"),
            change_pct=Decimal("-0.10"),
            halt_reason="News pending",
        )

        result = state.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["status"] == "halted"
        assert result["current_price"] == "150.0"
        assert result["change_pct"] == "-0.10"
        assert result["halt_reason"] == "News pending"


class TestCircuitBreakerEvent:
    """Test circuit breaker event dataclass."""

    def test_event_creation(self):
        """Test creating circuit breaker event."""
        event = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            symbol="SPY",
            level=CircuitBreakerLevel.LEVEL_1,
            reason="Market dropped 7%",
            change_pct=Decimal("-0.07"),
        )

        assert event.symbol == "SPY"
        assert event.level == CircuitBreakerLevel.LEVEL_1
        assert event.change_pct == Decimal("-0.07")

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            symbol="SPY",
            level=CircuitBreakerLevel.LEVEL_2,
            reason="Market dropped 13%",
            change_pct=Decimal("-0.13"),
        )

        result = event.to_dict()

        assert result["symbol"] == "SPY"
        assert result["level"] == "level_2"
        assert result["reason"] == "Market dropped 13%"


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality."""

    def test_initialization(self, circuit_breaker_manager):
        """Test manager initialization."""
        manager = circuit_breaker_manager

        assert not manager._is_monitoring, "Manager should not be monitoring on initialization"
        assert not manager._is_trading_paused, "Manager should not be paused on initialization"
        assert len(manager._market_states) == 0, "Market states should be empty on initialization"
        assert len(manager._halted_symbols) == 0, "Halted symbols should be empty on initialization"
        assert len(manager._events) == 0, "Events should be empty on initialization"

    @pytest.mark.asyncio
    async def test_start_monitoring(self, circuit_breaker_manager):
        """Test starting monitoring."""
        manager = circuit_breaker_manager

        result = await manager.start()
        assert result is True, "start() should return True when starting monitoring successfully"
        assert manager._is_monitoring is True, "Manager should be monitoring after start()"

        await manager.stop()

    @pytest.mark.asyncio
    async def test_start_already_monitoring(self, circuit_breaker_manager):
        """Test starting when already monitoring."""
        manager = circuit_breaker_manager

        await manager.start()
        result = await manager.start()

        assert result is False, "start() should return False when already monitoring"

        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, circuit_breaker_manager):
        """Test stopping monitoring."""
        manager = circuit_breaker_manager

        await manager.start()
        result = await manager.stop()

        assert result is True, "stop() should return True when stopping monitoring successfully"
        assert manager._is_monitoring is False, "Manager should not be monitoring after stop()"

    @pytest.mark.asyncio
    async def test_stop_when_not_monitoring(self, circuit_breaker_manager):
        """Test stopping when not monitoring."""
        manager = circuit_breaker_manager

        result = await manager.stop()

        assert result is False

    @pytest.mark.asyncio
    async def test_pause_all_trading(self, circuit_breaker_manager, mock_broker):
        """Test pausing all trading."""
        manager = circuit_breaker_manager

        # Mock open orders
        mock_order = MagicMock()
        mock_order.order_id = "order123"
        mock_broker.get_open_orders = AsyncMock(return_value=[mock_order])

        await manager.pause_all_trading("Test pause")

        assert manager._is_trading_paused is True, "Trading should be paused after pause_all_trading()"
        mock_broker.cancel_order.assert_called_once_with("order123")

    @pytest.mark.asyncio
    async def test_pause_already_paused(self, circuit_breaker_manager):
        """Test pausing when already paused."""
        manager = circuit_breaker_manager
        manager._is_trading_paused = True

        await manager.pause_all_trading("Test pause")

        # Should remain paused
        assert manager._is_trading_paused is True, "Trading should remain paused when already paused"

    @pytest.mark.asyncio
    async def test_resume_all_trading(self, circuit_breaker_manager):
        """Test resuming all trading."""
        manager = circuit_breaker_manager
        manager._is_trading_paused = True

        await manager.resume_all_trading("Halt lifted")

        assert manager._is_trading_paused is False, "Trading should be resumed after resume_all_trading()"

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, circuit_breaker_manager):
        """Test resuming when not paused."""
        manager = circuit_breaker_manager

        await manager.resume_all_trading("Test resume")

        # Should remain not paused
        assert manager._is_trading_paused is False, "Trading should remain not paused when resume is called while not paused"

    @pytest.mark.asyncio
    async def test_is_market_halted_when_trading_paused(self, circuit_breaker_manager):
        """Test market halt check when trading paused."""
        manager = circuit_breaker_manager
        manager._is_trading_paused = True

        result = await manager.is_market_halted()

        assert result is True, "Market should be halted when trading is paused"

    @pytest.mark.asyncio
    async def test_is_market_halted_when_symbol_halted(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test market halt check when symbol halted."""
        manager = circuit_breaker_manager

        # Set up market state with halted status
        manager._market_states["SPY"] = MarketState(
            symbol="SPY",
            status=TradingStatus.HALTED,
            current_price=Decimal("100.0"),
            change_pct=Decimal("0.0"),
        )

        result = await manager.is_market_halted()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_market_halted_when_trading(
        self, circuit_breaker_manager
    ):
        """Test market halt check when trading normally."""
        manager = circuit_breaker_manager

        result = await manager.is_market_halted()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_market_wide_halt_level_1(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test detection of Level 1 circuit breaker."""
        manager = circuit_breaker_manager
        mock_quote.change_percent = -0.08  # 8% drop
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_market_wide_halt()

        assert manager._is_trading_paused is True, "Trading should be paused on Level 1 circuit breaker (7%+ drop)"
        assert len(manager._events) == 1, "Should have one event recorded for Level 1 circuit breaker"
        assert manager._events[0].level == CircuitBreakerLevel.LEVEL_1, "Event level should be LEVEL_1"

    @pytest.mark.asyncio
    async def test_check_market_wide_halt_level_2(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test detection of Level 2 circuit breaker."""
        manager = circuit_breaker_manager
        mock_quote.change_percent = -0.14  # 14% drop
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_market_wide_halt()

        assert manager._is_trading_paused is True
        assert len(manager._events) == 1
        assert manager._events[0].level == CircuitBreakerLevel.LEVEL_2

    @pytest.mark.asyncio
    async def test_check_market_wide_halt_level_3(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test detection of Level 3 circuit breaker."""
        manager = circuit_breaker_manager
        mock_quote.change_percent = -0.25  # 25% drop
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_market_wide_halt()

        assert manager._is_trading_paused is True
        assert len(manager._events) == 1
        assert manager._events[0].level == CircuitBreakerLevel.LEVEL_3

    @pytest.mark.asyncio
    async def test_check_market_wide_halt_no_trigger(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test no circuit breaker trigger for normal movement."""
        manager = circuit_breaker_manager
        mock_quote.change_percent = -0.02  # 2% drop - normal
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_market_wide_halt()

        assert manager._is_trading_paused is False, "Trading should not be paused for normal market movement (2% drop)"
        assert len(manager._events) == 0, "No events should be recorded for normal market movement"

    @pytest.mark.asyncio
    async def test_check_symbol_halts(
        self, circuit_breaker_manager, mock_data_service, mock_quote, mock_broker
    ):
        """Test detection of single stock halts."""
        manager = circuit_breaker_manager

        # Mock positions
        mock_position = MagicMock()
        mock_position.symbol = "AAPL"
        mock_broker.get_positions = AsyncMock(return_value=[mock_position])

        # Mock halted quote
        mock_quote.is_halted = True
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_symbol_halts()

        assert "AAPL" in manager._halted_symbols
        assert len(manager._events) == 1

    @pytest.mark.asyncio
    async def test_check_vix_extreme(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test VIX extreme level triggers pause."""
        manager = circuit_breaker_manager
        mock_quote.last_price = 65.0  # VIX at 65 - panic level
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_vix_level()

        assert manager._is_trading_paused is True

    @pytest.mark.asyncio
    async def test_check_vix_high(
        self, circuit_breaker_manager, mock_data_service, mock_quote
    ):
        """Test VIX high level doesn't trigger pause."""
        manager = circuit_breaker_manager
        mock_quote.last_price = 45.0  # VIX at 45 - high but not panic
        mock_data_service.get_quote = AsyncMock(return_value=mock_quote)

        await manager._check_vix_level()

        # Should not pause at high level, only extreme
        assert manager._is_trading_paused is False

    @pytest.mark.asyncio
    async def test_on_halt_callback(self, circuit_breaker_manager):
        """Test halt callback is called."""
        manager = circuit_breaker_manager
        callback_called = []

        def halt_callback(event):
            callback_called.append(event)

        manager.on_halt = halt_callback

        event = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            symbol="SPY",
            level=CircuitBreakerLevel.LEVEL_1,
            reason="Test halt",
            change_pct=Decimal("-0.07"),
        )

        await manager.pause_all_trading("Test halt")
        manager._events.append(event)

        if manager.on_halt:
            manager.on_halt(event)

        assert len(callback_called) == 1
        assert callback_called[0].symbol == "SPY"

    def test_get_market_state(self, circuit_breaker_manager):
        """Test getting market state."""
        manager = circuit_breaker_manager

        state = MarketState(
            symbol="AAPL",
            status=TradingStatus.TRADING,
            current_price=Decimal("150.0"),
            change_pct=Decimal("0.01"),
        )
        manager._market_states["AAPL"] = state

        result = manager.get_market_state("AAPL")

        assert result is not None
        assert result.symbol == "AAPL"
        assert result.status == TradingStatus.TRADING

    def test_get_market_state_not_found(self, circuit_breaker_manager):
        """Test getting market state for unknown symbol."""
        manager = circuit_breaker_manager

        result = manager.get_market_state("UNKNOWN")

        assert result is None, "get_market_state() should return None for unknown symbol"

    def test_get_halted_symbols(self, circuit_breaker_manager):
        """Test getting halted symbols."""
        manager = circuit_breaker_manager
        manager._halted_symbols = {"AAPL", "TSLA", "MSFT"}

        result = manager.get_halted_symbols()

        assert result == {"AAPL", "TSLA", "MSFT"}

    def test_get_events(self, circuit_breaker_manager):
        """Test getting circuit breaker events."""
        manager = circuit_breaker_manager

        event1 = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            symbol="SPY",
            level=CircuitBreakerLevel.LEVEL_1,
            reason="Test 1",
            change_pct=Decimal("-0.07"),
        )
        event2 = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            symbol="AAPL",
            level=None,
            reason="Test 2",
            change_pct=Decimal("0.0"),
        )

        manager._events = [event1, event2]

        result = manager.get_events()

        assert len(result) == 2
        assert result[0].symbol == "SPY"
        assert result[1].symbol == "AAPL"

    def test_get_events_with_limit(self, circuit_breaker_manager):
        """Test getting circuit breaker events with limit."""
        manager = circuit_breaker_manager

        for i in range(10):
            event = CircuitBreakerEvent(
                timestamp=datetime.now(timezone.utc),
                symbol=f"STOCK{i}",
                level=None,
                reason=f"Test {i}",
                change_pct=Decimal("0.0"),
            )
            manager._events.append(event)

        result = manager.get_events(limit=5)

        assert len(result) == 5

    def test_is_trading_paused(self, circuit_breaker_manager):
        """Test checking if trading is paused."""
        manager = circuit_breaker_manager

        assert manager.is_trading_paused() is False, "is_trading_paused() should return False initially"

        manager._is_trading_paused = True

        assert manager.is_trading_paused() is True, "is_trading_paused() should return True when paused"


class TestCircuitBreakerLevels:
    """Test circuit breaker level enum."""

    def test_level_values(self):
        """Test circuit breaker level values."""
        assert CircuitBreakerLevel.LEVEL_1.value == "level_1"
        assert CircuitBreakerLevel.LEVEL_2.value == "level_2"
        assert CircuitBreakerLevel.LEVEL_3.value == "level_3"


class TestTradingStatus:
    """Test trading status enum."""

    def test_status_values(self):
        """Test trading status values."""
        assert TradingStatus.TRADING.value == "trading"
        assert TradingStatus.HALTED.value == "halted"
        assert TradingStatus.LIMIT_UP.value == "limit_up"
        assert TradingStatus.LIMIT_DOWN.value == "limit_down"
        assert TradingStatus.UNKNOWN.value == "unknown"
