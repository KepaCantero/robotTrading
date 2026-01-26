"""
Unit Tests for Shadow Mode Component

Tests cover:
1. Shadow mode execution
2. Order validation
3. Fill simulation
4. WAL integration
5. Shadow vs real comparison
6. Shadow to production transition
7. Statistics and tracking
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiosqlite

from app.core.shadow_mode import (
    ShadowModeAwareBroker,
    ShadowModeConfig,
    ShadowModeExecutor,
    ShadowExecutionResult,
    ShadowRealComparison,
    ShadowModeType,
    detect_shadow_mode_from_env,
)
from app.core.interfaces.broker_base import Order, OrderSide, OrderStatus, OrderType, Ticker
from app.sre.state_machine.wal_persistence import OrderLog, OrderState

# Python 3.9 compatibility
UTC = timezone.utc


@pytest.fixture
async def temp_db_path(tmp_path: Path) -> str:
    """Create temporary database for testing."""
    return str(tmp_path / "test_shadow_wal.db")


@pytest.fixture
async def temp_wal_path(tmp_path: Path) -> str:
    """Create temporary WAL path for testing."""
    return str(tmp_path / "test_shadow_wal.log")


@pytest.fixture
async def wal_manager(temp_db_path: str, temp_wal_path: str):
    """Create WAL manager for testing."""
    from app.sre.state_machine.wal_persistence import OrderStateMachine

    wal = OrderStateMachine(temp_db_path, temp_wal_path)
    await wal.initialize()
    return wal


@pytest.fixture
def mock_broker():
    """Create mock broker client."""
    broker = MagicMock()

    # Mock get_live_ticker
    broker.get_live_ticker = AsyncMock(
        return_value=Ticker(
            symbol="AAPL",
            bid=Decimal("149.50"),
            ask=Decimal("150.50"),
            last=Decimal("150.00"),
            timestamp=datetime.now(UTC),
        )
    )

    # Mock execute_order_with_wal
    broker.execute_order_with_wal = AsyncMock(
        return_value={
            "order_id": "real_order_123",
            "status": "FILLED",
            "filled_quantity": 100.0,
            "execution_price": 150.25,
        }
    )

    return broker


@pytest.fixture
def shadow_config():
    """Create shadow mode configuration."""
    return ShadowModeConfig(
        enabled=True,
        shadow_type=ShadowModeType.SHADOW,
        fill_simulation_model="realistic",
        slippage_bps=5,
        fill_delay_ms=100,
        partial_fill_probability=0.1,
        rejection_probability=0.01,
    )


@pytest.fixture
def shadow_executor(mock_broker, wal_manager, shadow_config):
    """Create shadow mode executor for testing."""
    return ShadowModeExecutor(
        broker_client=mock_broker,
        wal_manager=wal_manager,
        config=shadow_config,
    )


class TestShadowModeConfig:
    """Test ShadowModeConfig validation."""

    def test_valid_config(self, shadow_config):
        """Test valid configuration."""
        assert shadow_config.enabled is True
        assert shadow_config.shadow_type == ShadowModeType.SHADOW
        assert shadow_config.slippage_bps == 5
        assert shadow_config.fill_delay_ms == 100

    def test_invalid_slippage(self):
        """Test invalid slippage configuration."""
        with pytest.raises(ValueError, match="slippage_bps must be non-negative"):
            ShadowModeConfig(slippage_bps=-1)

    def test_invalid_fill_delay(self):
        """Test invalid fill delay configuration."""
        with pytest.raises(ValueError, match="fill_delay_ms must be non-negative"):
            ShadowModeConfig(fill_delay_ms=-1)

    def test_invalid_partial_fill_probability(self):
        """Test invalid partial fill probability."""
        with pytest.raises(ValueError, match="partial_fill_probability must be between 0 and 1"):
            ShadowModeConfig(partial_fill_probability=1.5)

    def test_invalid_rejection_probability(self):
        """Test invalid rejection probability."""
        with pytest.raises(ValueError, match="rejection_probability must be between 0 and 1"):
            ShadowModeConfig(rejection_probability=-0.1)


class TestShadowModeExecutor:
    """Test ShadowModeExecutor functionality."""

    @pytest.mark.asyncio
    async def test_is_shadow_mode_enabled(self, shadow_executor):
        """Test checking if shadow mode is enabled."""
        assert await shadow_executor.is_shadow_mode_enabled() is True

        shadow_executor.config.enabled = False
        assert await shadow_executor.is_shadow_mode_enabled() is False

    @pytest.mark.asyncio
    async def test_execute_order_shadow_basic(
        self, shadow_executor, mock_broker
    ):
        """Test basic shadow order execution."""
        result = await shadow_executor.execute_order_shadow(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="MARKET",
        )

        assert result.symbol == "AAPL"
        assert result.side == "BUY"
        assert result.quantity == Decimal("100")
        assert result.requested_price == Decimal("150.00")
        assert result.simulated_fill_price is not None
        assert result.simulated_fill_quantity > 0
        assert result.status in ["FILLED", "PARTIAL_FILLED", "REJECTED"]
        assert result.wal_recorded is True
        assert result.shadow_order_id.startswith("SHADOW_")

    @pytest.mark.asyncio
    async def test_execute_order_shadow_disabled(self, shadow_executor):
        """Test that execution fails when shadow mode is disabled."""
        shadow_executor.config.enabled = False

        with pytest.raises(RuntimeError, match="Shadow mode is not enabled"):
            await shadow_executor.execute_order_shadow(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
            )

    @pytest.mark.asyncio
    async def test_execute_order_shadow_writes_to_wal(
        self, shadow_executor, wal_manager
    ):
        """Test that shadow orders are written to WAL."""
        result = await shadow_executor.execute_order_shadow(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )

        # Check WAL was written
        history = await wal_manager.get_order_history(result.shadow_order_id)
        assert len(history) >= 2  # SUBMITTING and ACK_RECEIVED at minimum

        # Check states
        states = [log.state for log in history]
        assert OrderState.SUBMITTING in states
        assert OrderState.ACK_RECEIVED in states

        # Check shadow_mode metadata
        submitting_log = next(log for log in history if log.state == OrderState.SUBMITTING)
        assert submitting_log.metadata.get("shadow_mode") is True
        assert submitting_log.metadata.get("shadow_order_id") == result.shadow_order_id

    @pytest.mark.asyncio
    async def test_validate_order_for_shadow_valid(self, shadow_executor):
        """Test order validation with valid order."""
        # Should not raise
        await shadow_executor.validate_order_for_shadow(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="LIMIT",
        )

    @pytest.mark.asyncio
    async def test_validate_order_for_shadow_invalid_symbol(self, shadow_executor):
        """Test order validation with invalid symbol."""
        with pytest.raises(ValueError, match="Invalid symbol format"):
            await shadow_executor.validate_order_for_shadow(
                symbol="INVALID_SYMBOL_123!@#",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                order_type="MARKET",
            )

    @pytest.mark.asyncio
    async def test_validate_order_for_shadow_invalid_side(self, shadow_executor):
        """Test order validation with invalid side."""
        with pytest.raises(ValueError, match="Invalid side"):
            await shadow_executor.validate_order_for_shadow(
                symbol="AAPL",
                side="INVALID",
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                order_type="MARKET",
            )

    @pytest.mark.asyncio
    async def test_validate_order_for_shadow_negative_quantity(self, shadow_executor):
        """Test order validation with negative quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await shadow_executor.validate_order_for_shadow(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("-100"),
                price=Decimal("150.00"),
                order_type="MARKET",
            )

    @pytest.mark.asyncio
    async def test_validate_order_for_shadow_limit_without_price(self, shadow_executor):
        """Test order validation for LIMIT order without price."""
        with pytest.raises(ValueError, match="LIMIT orders require a price"):
            await shadow_executor.validate_order_for_shadow(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                price=None,
                order_type="LIMIT",
            )

    @pytest.mark.asyncio
    async def test_simulate_fill_market_order(self, shadow_executor, mock_broker):
        """Test fill simulation for market order."""
        result = await shadow_executor.simulate_fill(
            shadow_order_id="test_shadow_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=None,
            order_type="MARKET",
        )

        assert result.symbol == "AAPL"
        assert result.simulated_fill_price is not None
        assert result.simulated_fill_quantity > 0
        assert result.status in ["FILLED", "PARTIAL_FILLED", "REJECTED"]

    @pytest.mark.asyncio
    async def test_simulate_fill_limit_order(self, shadow_executor):
        """Test fill simulation for limit order."""
        result = await shadow_executor.simulate_fill(
            shadow_order_id="test_shadow_123",
            symbol="AAPL",
            side="SELL",
            quantity=Decimal("50"),
            price=Decimal("150.00"),
            order_type="LIMIT",
        )

        assert result.simulated_fill_price is not None
        # For sell orders, fill price should be at or below limit
        assert result.simulated_fill_price <= Decimal("150.00")

    @pytest.mark.asyncio
    async def test_simulate_fill_applies_slippage(self, shadow_executor):
        """Test that fill simulation applies slippage."""
        shadow_executor.config.slippage_bps = 10  # 0.1%

        result = await shadow_executor.simulate_fill(
            shadow_order_id="test_shadow_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="LIMIT",
        )

        # For buy orders, fill price should be higher due to slippage
        assert result.simulated_fill_price > Decimal("150.00")
        # Check slippage is approximately 10bps
        expected_price = Decimal("150.00") * Decimal("1.001")
        assert abs(result.simulated_fill_price - expected_price) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_simulate_fill_partial_fill(self, shadow_executor):
        """Test partial fill simulation."""
        shadow_executor.config.partial_fill_probability = 1.0  # Always partial

        result = await shadow_executor.simulate_fill(
            shadow_order_id="test_shadow_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="MARKET",
        )

        assert result.was_partial_fill is True
        assert result.status == "PARTIAL_FILLED"
        assert result.simulated_fill_quantity < result.quantity

    @pytest.mark.asyncio
    async def test_simulate_fill_rejection(self, shadow_executor):
        """Test order rejection simulation."""
        shadow_executor.config.rejection_probability = 1.0  # Always reject

        result = await shadow_executor.simulate_fill(
            shadow_order_id="test_shadow_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="MARKET",
        )

        assert result.was_rejected is True
        assert result.status == "REJECTED"
        assert result.simulated_fill_quantity == Decimal("0")

    @pytest.mark.asyncio
    async def test_shadow_to_production_transition_no_data(self, shadow_executor):
        """Test transition validation with no shadow data."""
        report = await shadow_executor.shadow_to_production_transition()

        assert report["can_transition"] is False
        assert len(report["errors"]) > 0
        assert "No shadow results found" in report["errors"][0]

    @pytest.mark.asyncio
    async def test_shadow_to_production_transition_with_success(
        self, shadow_executor
    ):
        """Test successful transition validation."""
        # Create some successful shadow results
        for i in range(10):
            result = ShadowExecutionResult(
                order_id=f"order_{i}",
                shadow_order_id=f"SHADOW_order_{i}",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                requested_price=Decimal("150.00"),
                simulated_fill_price=Decimal("150.01"),
                simulated_fill_quantity=Decimal("100"),
                status="FILLED",
                execution_time_ms=100,
                slippage_bps=1,
                was_rejected=False,
                wal_recorded=True,
            )
            shadow_executor.shadow_results.append(result)

        report = await shadow_executor.shadow_to_production_transition()

        # Should have high success rate
        assert report["can_transition"] is True
        assert len(report["errors"]) == 0

    @pytest.mark.asyncio
    async def test_compare_shadow_vs_real(self, shadow_executor):
        """Test shadow vs real comparison."""
        # Add some shadow results
        result = ShadowExecutionResult(
            order_id="order_1",
            shadow_order_id="SHADOW_order_1",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            requested_price=Decimal("150.00"),
            simulated_fill_price=Decimal("150.01"),
            simulated_fill_quantity=Decimal("100"),
            status="FILLED",
            execution_time_ms=100,
            slippage_bps=1,
            was_rejected=False,
            wal_recorded=True,
        )
        shadow_executor.shadow_results.append(result)

        comparisons = await shadow_executor.compare_shadow_vs_real()

        assert len(comparisons) == 1
        assert comparisons[0].shadow_order_id == "SHADOW_order_1"
        assert comparisons[0].shadow_price == Decimal("150.01")

    @pytest.mark.asyncio
    async def test_get_shadow_statistics(self, shadow_executor):
        """Test shadow mode statistics."""
        # Add some shadow results
        now = datetime.now(UTC)
        for i in range(10):
            result = ShadowExecutionResult(
                order_id=f"order_{i}",
                shadow_order_id=f"SHADOW_order_{i}",
                symbol="AAPL" if i % 2 == 0 else "TSLA",
                side="BUY",
                quantity=Decimal("100"),
                requested_price=Decimal("150.00"),
                simulated_fill_price=Decimal("150.01"),
                simulated_fill_quantity=Decimal("100"),
                status="FILLED",
                execution_time_ms=100 + i * 10,
                slippage_bps=5,
                was_rejected=False,
                wal_recorded=True,
                timestamp=now - timedelta(minutes=i),
            )
            shadow_executor.shadow_results.append(result)

        stats = await shadow_executor.get_shadow_statistics(minutes=60)

        assert stats["total_orders"] == 10
        assert stats["filled"] == 10
        assert stats["fill_rate"] == 1.0
        assert stats["avg_slippage_bps"] == 5.0
        assert "AAPL" in stats["by_symbol"]
        assert "TSLA" in stats["by_symbol"]

    @pytest.mark.asyncio
    async def test_get_shadow_statistics_no_data(self, shadow_executor):
        """Test statistics with no data."""
        stats = await shadow_executor.get_shadow_statistics()

        assert stats["total_orders"] == 0
        assert "message" in stats

    @pytest.mark.asyncio
    async def test_reset_daily_counters(self, shadow_executor):
        """Test resetting daily counters."""
        shadow_executor.daily_order_count["2025-01-25"] = 100
        shadow_executor.daily_order_count["2025-01-26"] = 200

        await shadow_executor.reset_daily_counters()

        assert len(shadow_executor.daily_order_count) == 0

    @pytest.mark.asyncio
    async def test_daily_order_limit(self, shadow_executor):
        """Test daily order limit enforcement."""
        shadow_executor.config.max_shadow_orders_per_day = 2

        # First two orders should succeed
        await shadow_executor.execute_order_shadow(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
        )

        await shadow_executor.execute_order_shadow(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
        )

        # Third order should fail
        with pytest.raises(RuntimeError, match="Daily shadow order limit exceeded"):
            await shadow_executor.execute_order_shadow(
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
            )


class TestShadowModeAwareBroker:
    """Test ShadowModeAwareBroker wrapper."""

    @pytest.mark.asyncio
    async def test_intercepts_shadow_execution(self, mock_broker, wal_manager):
        """Test that broker intercepts execution when shadow mode enabled."""
        config = ShadowModeConfig(enabled=True)
        shadow_executor = ShadowModeExecutor(
            broker_client=mock_broker,
            wal_manager=wal_manager,
            config=config,
        )
        shadow_broker = ShadowModeAwareBroker(mock_broker, shadow_executor)

        order = Order(
            order_id="test_order",
            symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("100"),
        )

        result = await shadow_broker.execute_order_with_wal(order)

        # Should return shadow result
        assert result.get("shadow_mode") is True
        assert result["order_id"].startswith("SHADOW_")
        assert mock_broker.execute_order_with_wal.call_count == 0

    @pytest.mark.asyncio
    async def test_delegates_real_execution(self, mock_broker, wal_manager):
        """Test that broker delegates to real broker when shadow mode disabled."""
        config = ShadowModeConfig(enabled=False)
        shadow_executor = ShadowModeExecutor(
            broker_client=mock_broker,
            wal_manager=wal_manager,
            config=config,
        )
        shadow_broker = ShadowModeAwareBroker(mock_broker, shadow_executor)

        order = Order(
            order_id="test_order",
            symbol="AAPL",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("100"),
        )

        result = await shadow_broker.execute_order_with_wal(order)

        # Should return real result
        assert result.get("shadow_mode") is None
        assert mock_broker.execute_order_with_wal.call_count == 1

    @pytest.mark.asyncio
    async def test_delegates_other_methods(self, mock_broker, wal_manager):
        """Test that broker delegates other methods to real broker."""
        config = ShadowModeConfig(enabled=True)
        shadow_executor = ShadowModeExecutor(
            broker_client=mock_broker,
            wal_manager=wal_manager,
            config=config,
        )
        shadow_broker = ShadowModeAwareBroker(mock_broker, shadow_executor)

        # Call some other method
        mock_broker.get_broker_name = MagicMock(return_value="test_broker")
        name = shadow_broker.get_broker_name()

        assert name == "test_broker"


class TestShadowExecutionResult:
    """Test ShadowExecutionResult."""

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ShadowExecutionResult(
            order_id="order_123",
            shadow_order_id="SHADOW_order_123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            requested_price=Decimal("150.00"),
            simulated_fill_price=Decimal("150.01"),
            simulated_fill_quantity=Decimal("100"),
            status="FILLED",
            execution_time_ms=100,
            slippage_bps=1,
        )

        data = result.to_dict()

        assert data["order_id"] == "order_123"
        assert data["symbol"] == "AAPL"
        assert data["quantity"] == "100"
        assert data["requested_price"] == "150.00"
        assert isinstance(data, dict)


class TestDetectShadowModeFromEnv:
    """Test environment-based configuration detection."""

    @pytest.mark.asyncio
    async def test_detect_shadow_mode_enabled(self, monkeypatch):
        """Test detecting shadow mode from environment."""
        monkeypatch.setenv("SHADOW_MODE_ENABLED", "true")
        monkeypatch.setenv("SHADOW_MODE_TYPE", "shadow")
        monkeypatch.setenv("SHADOW_SLIPPAGE_BPS", "10")
        monkeypatch.setenv("SHADOW_FILL_DELAY_MS", "200")

        config = detect_shadow_mode_from_env()

        assert config.enabled is True
        assert config.shadow_type == ShadowModeType.SHADOW
        assert config.slippage_bps == 10
        assert config.fill_delay_ms == 200

    @pytest.mark.asyncio
    async def test_detect_shadow_mode_disabled(self, monkeypatch):
        """Test default configuration when shadow mode not enabled."""
        monkeypatch.delenv("SHADOW_MODE_ENABLED", raising=False)

        config = detect_shadow_mode_from_env()

        assert config.enabled is False

    @pytest.mark.asyncio
    async def test_detect_shadow_mode_defaults(self, monkeypatch):
        """Test default values for shadow mode configuration."""
        monkeypatch.setenv("SHADOW_MODE_ENABLED", "true")

        config = detect_shadow_mode_from_env()

        assert config.shadow_type == ShadowModeType.SHADOW
        assert config.slippage_bps == 5
        assert config.fill_delay_ms == 100
