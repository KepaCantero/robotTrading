"""
Comprehensive tests for Advanced Risk Manager (TASK-RM-1 to RM-5).
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.advanced_risk_manager import (
    AdvancedRiskManager,
    CircuitBreaker,
    DrawdownMonitor,
    RiskRewardValidator,
    TradeRiskLimiter,
)


@pytest.fixture
def sample_signal():
    """Create a sample trading signal."""
    return Signal(
        symbol="AAPL",
        signal_type=SignalType.BUY,
        strength=SignalStrength.STRONG,
        confidence=85.0,
        liquidity_score=90.0,
        priority_score=85.0,
        source=SignalSource.MOMENTUM,
        price=Decimal("150.00"),
        volume=Decimal("1000"),
    )


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio."""
    positions = []

    return Portfolio(
        cash=Decimal("90000"),
        positions=positions,
        timestamp=datetime.utcnow(),
        broker="paper",
        currency="USD",
    )


class TestTradeRiskLimiter:
    """Tests for TASK-RM-1: Trade Risk Limiter."""

    def test_initialization(self):
        """Test limiter initialization."""
        limiter = TradeRiskLimiter(max_risk_per_trade=Decimal("0.02"))

        assert limiter.max_risk_per_trade == Decimal("0.02")

    def test_calculate_max_position_size(self, sample_signal, sample_portfolio):
        """Test calculating maximum position size."""
        limiter = TradeRiskLimiter()

        max_size = limiter.calculate_max_position_size(
            sample_signal, sample_portfolio, Decimal("0.05")  # 5% stop loss
        )

        assert max_size > Decimal("0")

    def test_validate_trade_risk_valid(self, sample_signal, sample_portfolio):
        """Test validating trade risk within limits."""
        limiter = TradeRiskLimiter()

        position_size = Decimal("100")
        stop_loss_pct = Decimal("0.05")

        is_valid = limiter.validate_trade_risk(
            sample_signal, sample_portfolio, position_size, stop_loss_pct
        )

        assert is_valid is True

    def test_validate_trade_risk_exceeds_limit(self, sample_signal, sample_portfolio):
        """Test validating trade risk exceeding limits."""
        limiter = TradeRiskLimiter(max_risk_per_trade=Decimal("0.01"))  # 1% limit

        position_size = Decimal("10000")
        stop_loss_pct = Decimal("0.10")

        is_valid = limiter.validate_trade_risk(
            sample_signal, sample_portfolio, position_size, stop_loss_pct
        )

        assert is_valid is False


class TestRiskRewardValidator:
    """Tests for TASK-RM-2: Risk/Reward Ratio Validator."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = RiskRewardValidator(min_reward_ratio=Decimal("3.0"))

        assert validator.min_reward_ratio == Decimal("3.0")

    def test_validate_risk_reward_valid(self):
        """Test validating valid risk/reward ratio."""
        validator = RiskRewardValidator()

        # Entry: 100, Stop: 95 (risk=5), Target: 115 (reward=15) = 3:1
        is_valid = validator.validate_risk_reward(
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("115"),
        )

        assert is_valid is True

    def test_validate_risk_reward_invalid(self):
        """Test validating invalid risk/reward ratio."""
        validator = RiskRewardValidator()

        # Entry: 100, Stop: 95 (risk=5), Target: 105 (reward=5) = 1:1
        is_valid = validator.validate_risk_reward(
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("105"),
        )

        assert is_valid is False

    def test_calculate_min_take_profit(self):
        """Test calculating minimum take profit."""
        validator = RiskRewardValidator()

        min_tp = validator.calculate_min_take_profit(
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
        )

        # Risk = 5, min reward = 15, so min TP = 100 + 15 = 115
        assert min_tp >= Decimal("115")


class TestDrawdownMonitor:
    """Tests for TASK-RM-4: Drawdown Monitor."""

    def test_initialization(self):
        """Test monitor initialization."""
        monitor = DrawdownMonitor()

        assert monitor.max_drawdown == Decimal("0.15")
        assert monitor.peak_equity == Decimal("0")
        assert monitor.is_stopped is False

    def test_check_drawdown_within_limits(self):
        """Test drawdown within limits."""
        monitor = DrawdownMonitor()
        monitor.update_equity(Decimal("100000"))

        exceeded, drawdown = monitor.check_drawdown(Decimal("98000"))

        assert exceeded is False
        assert drawdown < monitor.max_drawdown

    def test_check_drawdown_exceeded(self):
        """Test drawdown exceeding limits."""
        monitor = DrawdownMonitor()
        monitor.update_equity(Decimal("100000"))

        exceeded, drawdown = monitor.check_drawdown(Decimal("80000"))

        assert exceeded is True
        assert drawdown > monitor.max_drawdown

    def test_reset(self):
        """Test resetting monitor."""
        monitor = DrawdownMonitor()
        monitor.is_stopped = True

        monitor.reset()

        assert monitor.is_stopped is False


class TestCircuitBreaker:
    """Tests for TASK-RM-5: Circuit Breaker."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(max_consecutive_stops=5)

        assert breaker.max_consecutive_stops == 5

    def test_record_stop_loss(self):
        """Test recording stop losses."""
        breaker = CircuitBreaker(max_consecutive_stops=3)

        breaker.record_stop_loss("momentum")
        assert breaker.get_consecutive_stops("momentum") == 1

        breaker.record_stop_loss("momentum")
        assert breaker.get_consecutive_stops("momentum") == 2

    def test_circuit_breaker_triggers(self):
        """Test circuit breaker triggering pause."""
        breaker = CircuitBreaker(max_consecutive_stops=3)

        breaker.record_stop_loss("momentum")
        breaker.record_stop_loss("momentum")
        breaker.record_stop_loss("momentum")

        assert breaker.is_strategy_paused("momentum") is True

    def test_reset_stops(self):
        """Test resetting stop counter."""
        breaker = CircuitBreaker()

        breaker.record_stop_loss("momentum")
        breaker.record_stop_loss("momentum")
        assert breaker.get_consecutive_stops("momentum") == 2

        breaker.reset_stops("momentum")
        assert breaker.get_consecutive_stops("momentum") == 0
        assert breaker.is_strategy_paused("momentum") is False


class TestAdvancedRiskManager:
    """Tests for complete Advanced Risk Manager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = AdvancedRiskManager()

        assert manager.trade_risk_limiter is not None
        assert manager.risk_reward_validator is not None
        assert manager.exposure_limiter is not None
        assert manager.drawdown_monitor is not None
        assert manager.circuit_breaker is not None

    def test_validate_trade_all_pass(self, sample_signal, sample_portfolio):
        """Test validating trade with all checks passing."""
        manager = AdvancedRiskManager()

        is_valid, reason = manager.validate_trade(
            signal=sample_signal,
            portfolio=sample_portfolio,
            position_size=Decimal("100"),
            stop_loss_pct=Decimal("0.05"),
            take_profit_pct=Decimal("0.15"),
            strategy_name="momentum",
        )

        assert is_valid is True

    def test_validate_trade_circuit_breaker(self, sample_signal, sample_portfolio):
        """Test validating trade with circuit breaker active."""
        manager = AdvancedRiskManager(max_consecutive_stops=2)

        # Trigger circuit breaker
        manager.circuit_breaker.record_stop_loss("momentum")
        manager.circuit_breaker.record_stop_loss("momentum")

        is_valid, reason = manager.validate_trade(
            signal=sample_signal,
            portfolio=sample_portfolio,
            position_size=Decimal("100"),
            stop_loss_pct=Decimal("0.05"),
            take_profit_pct=Decimal("0.15"),
            strategy_name="momentum",
        )

        assert is_valid is False
        assert "paused" in reason.lower()

    def test_calculate_safe_position_size(self, sample_signal, sample_portfolio):
        """Test calculating safe position size."""
        manager = AdvancedRiskManager()

        safe_size = manager.calculate_safe_position_size(
            signal=sample_signal,
            portfolio=sample_portfolio,
            stop_loss_pct=Decimal("0.05"),
        )

        assert safe_size >= Decimal("0")

    def test_record_trade_result_stop_loss(self):
        """Test recording trade result with stop loss."""
        manager = AdvancedRiskManager()

        manager.record_trade_result(
            strategy_name="momentum",
            was_stop_loss=True,
            current_equity=Decimal("100000"),
        )

        assert manager.circuit_breaker.get_consecutive_stops("momentum") == 1

    def test_record_trade_result_no_stop(self):
        """Test recording trade result without stop loss."""
        manager = AdvancedRiskManager()

        # First record a stop
        manager.record_trade_result(
            strategy_name="momentum",
            was_stop_loss=True,
            current_equity=Decimal("100000"),
        )

        # Then record a win
        manager.record_trade_result(
            strategy_name="momentum",
            was_stop_loss=False,
            current_equity=Decimal("101000"),
        )

        assert manager.circuit_breaker.get_consecutive_stops("momentum") == 0

    def test_get_risk_status(self):
        """Test getting risk status."""
        manager = AdvancedRiskManager()

        status = manager.get_risk_status()

        assert "drawdown_exceeded" in status
        assert "peak_equity" in status
        assert "strategy_stops" in status
        assert "paused_strategies" in status
