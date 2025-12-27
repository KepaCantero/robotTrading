"""
Tests for AlertToTradeMapper - Alert to trade signal mapping

Tests cover:
- Rule registration and management
- Signal generation from alerts
- Severity-based quantity scaling
- Cooldown period enforcement
- Risk-aware quantity calculation
"""

from datetime import datetime, timedelta
from decimal import Decimal


from app.services.alerting_system import AlertSeverity
from app.services.live_trading.alert_to_trade_mapper import (
    AlertToTradeMapper,
    AlertToTradeRule,
    TradeSignalType,
)
from app.services.live_trading.broker_connector import OrderSide, OrderType


class TestAlertToTradeRuleManagement:
    """Test rule registration and management."""

    def test_register_single_rule(self):
        """Test registering a single trade rule."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            signal_type=TradeSignalType.LONG,
        )

        mapper.register_rule(rule)
        assert "rule_001" in mapper.rules
        assert mapper.rules["rule_001"] == rule

    def test_register_multiple_rules(self):
        """Test registering multiple rules."""
        mapper = AlertToTradeMapper()

        for i in range(5):
            rule = AlertToTradeRule(
                rule_id=f"rule_{i:03d}",
                alert_rule_id=f"alert_{i:03d}",
                signal_type=TradeSignalType.LONG if i % 2 == 0 else TradeSignalType.SHORT,
            )
            mapper.register_rule(rule)

        assert len(mapper.rules) == 5

    def test_unregister_rule(self):
        """Test unregistering a rule."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
        )

        mapper.register_rule(rule)
        assert len(mapper.rules) == 1

        result = mapper.unregister_rule("rule_001")
        assert result is True
        assert len(mapper.rules) == 0

    def test_unregister_nonexistent_rule(self):
        """Test unregistering non-existent rule."""
        mapper = AlertToTradeMapper()
        result = mapper.unregister_rule("nonexistent")
        assert result is False


class TestSignalGeneration:
    """Test trade signal generation from alerts."""

    def test_long_signal_generation(self):
        """Test generating LONG signal from alert."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            signal_type=TradeSignalType.LONG,
            base_quantity=Decimal("100"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        assert signal.signal_type == TradeSignalType.LONG
        assert signal.order_side == OrderSide.BUY
        assert signal.symbol == "AAPL"

    def test_short_signal_generation(self):
        """Test generating SHORT signal from alert."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            signal_type=TradeSignalType.SHORT,
            base_quantity=Decimal("100"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="TSLA",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("250"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        assert signal.signal_type == TradeSignalType.SHORT
        assert signal.order_side == OrderSide.SELL

    def test_no_rule_for_alert(self):
        """Test signal generation when no matching rule exists."""
        mapper = AlertToTradeMapper()

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="nonexistent_rule",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is None


class TestSeverityBasedScaling:
    """Test severity-based quantity scaling."""

    def test_info_severity_scaling(self):
        """Test quantity scaling for INFO severity."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            base_quantity=Decimal("100"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.INFO,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        # INFO severity multiplier is 0.5, so 100 * 0.5 = 50
        assert signal.quantity == Decimal("50")

    def test_warning_severity_scaling(self):
        """Test quantity scaling for WARNING severity."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            base_quantity=Decimal("100"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        # WARNING severity multiplier is 1.0, so 100 * 1.0 = 100
        assert signal.quantity == Decimal("100")

    def test_critical_severity_scaling(self):
        """Test quantity scaling for CRITICAL severity."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            base_quantity=Decimal("100"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.CRITICAL,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        # CRITICAL severity multiplier is 2.0, so 100 * 2.0 = 200
        assert signal.quantity == Decimal("200")


class TestCooldownPeriod:
    """Test cooldown period enforcement."""

    def test_cooldown_period_enforced(self):
        """Test that cooldown period prevents immediate re-triggering."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            quiet_period_minutes=5,
        )
        mapper.register_rule(rule)

        # First signal should succeed
        signal1 = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )
        assert signal1 is not None

        # Immediate second signal should be blocked
        signal2 = mapper.map_alert_to_signal(
            alert_id="evt_002",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )
        assert signal2 is None

    def test_cooldown_period_expired(self):
        """Test signal generation after cooldown expires."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            quiet_period_minutes=1,
        )
        mapper.register_rule(rule)

        # First signal
        signal1 = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )
        assert signal1 is not None

        # Simulate time passing
        rule.last_triggered_at = datetime.utcnow() - timedelta(minutes=2)

        # Signal after cooldown should succeed
        signal2 = mapper.map_alert_to_signal(
            alert_id="evt_002",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )
        assert signal2 is not None


class TestPositionSizeLimit:
    """Test position size limit enforcement."""

    def test_position_size_respected(self):
        """Test that position size respects max limit."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            base_quantity=Decimal("1000"),
            max_position_size=Decimal("10000"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        position_value = signal.quantity * Decimal("150")
        assert position_value <= Decimal("10000")

    def test_large_quantity_scaled_down(self):
        """Test that large quantities are scaled to position limit."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            base_quantity=Decimal("5000"),
            severity_multipliers={
                AlertSeverity.INFO: Decimal("1"),
                AlertSeverity.WARNING: Decimal("2"),
                AlertSeverity.CRITICAL: Decimal("3"),
            },
            max_position_size=Decimal("10000"),
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.CRITICAL,  # Multiplier 3, so 5000*3 = 15000
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        # Should be scaled down to max position size / price
        max_quantity = Decimal("10000") / Decimal("150")
        assert signal.quantity <= max_quantity


class TestLimitOrderGeneration:
    """Test limit order generation."""

    def test_limit_order_price_calculation(self):
        """Test limit order price calculation."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            use_limit_orders=True,
            limit_price_offset=Decimal("1"),  # 1% offset
            signal_type=TradeSignalType.LONG,
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("100"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        assert signal.order_type == OrderType.LIMIT
        # For LONG: price - 1% offset = 100 - 1 = 99
        assert signal.price == Decimal("99")

    def test_short_limit_order_price(self):
        """Test short limit order price calculation."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
            use_limit_orders=True,
            limit_price_offset=Decimal("1"),  # 1% offset
            signal_type=TradeSignalType.SHORT,
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("100"),
            portfolio_value=Decimal("100000"),
        )

        assert signal is not None
        # For SHORT: price + 1% offset = 100 + 1 = 101
        assert signal.price == Decimal("101")


class TestSignalRetrieval:
    """Test signal retrieval and statistics."""

    def test_get_signal(self):
        """Test retrieving signal by ID."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        retrieved = mapper.get_signal(signal.signal_id)
        assert retrieved is not None
        assert retrieved.signal_id == signal.signal_id

    def test_get_pending_signals(self):
        """Test retrieving pending signals."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
        )
        mapper.register_rule(rule)

        # Generate multiple signals
        for i in range(3):
            mapper.map_alert_to_signal(
                alert_id=f"evt_{i:03d}",
                alert_rule_id="alert_001",
                symbol="AAPL",
                severity=AlertSeverity.WARNING,
                current_price=Decimal("150"),
                portfolio_value=Decimal("100000"),
            )

        pending = mapper.get_pending_signals()
        assert len(pending) == 3

    def test_signal_statistics(self):
        """Test signal generation statistics."""
        mapper = AlertToTradeMapper()

        # Register rules for different signal types
        for signal_type in TradeSignalType:
            rule = AlertToTradeRule(
                rule_id=f"rule_{signal_type.value}",
                alert_rule_id=f"alert_{signal_type.value}",
                signal_type=signal_type,
            )
            mapper.register_rule(rule)

        # Generate signals
        mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_long",
            symbol="AAPL",
            severity=AlertSeverity.CRITICAL,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        stats = mapper.get_signal_statistics()
        assert stats["total_signals"] == 1
        assert stats["active_rules"] == 5
        assert stats["by_severity"]["critical"] == 1

    def test_signal_to_dict(self):
        """Test signal serialization."""
        mapper = AlertToTradeMapper()
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="alert_001",
        )
        mapper.register_rule(rule)

        signal = mapper.map_alert_to_signal(
            alert_id="evt_001",
            alert_rule_id="alert_001",
            symbol="AAPL",
            severity=AlertSeverity.WARNING,
            current_price=Decimal("150"),
            portfolio_value=Decimal("100000"),
        )

        signal_dict = signal.to_dict()
        assert signal_dict["signal_id"] == signal.signal_id
        assert signal_dict["symbol"] == "AAPL"
        assert signal_dict["severity"] == "warning"
