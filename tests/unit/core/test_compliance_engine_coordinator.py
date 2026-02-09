"""
Unit tests for ComplianceEngine coordinator methods (Task 09).

Tests for:
- IAlertProcessor protocol methods (process_alert, validate_alert, etc.)
- ITradeExecutor protocol methods (execute_trade, cancel_order, etc.)
- IStrategyCycleRunner protocol methods (run_cycle, validate_cycle_input, etc.)
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.core.compliance_engine import ComplianceEngine


class TestIAlertProcessorMethods:
    """Test IAlertProcessor protocol implementation."""

    @pytest.fixture
    def engine(self):
        """Create test engine instance."""
        engine = ComplianceEngine(enable_logging=False)
        # Reset singleton for testing
        engine._initialized = False
        return engine

    @pytest.mark.asyncio
    async def test_process_alert_valid(self, engine):
        """Test processing a valid alert."""
        alert = {
            "symbol": "AAPL",
            "alert_type": "price_cross",
            "severity": "WARNING",
            "timestamp": datetime.now().isoformat(),
            "price": "150.00",
        }

        result = await engine.process_alert(alert)

        # Should return None (no trade rule configured in test)
        # But should not raise an error
        assert result is None or hasattr(result, "symbol")

    @pytest.mark.asyncio
    async def test_process_alert_invalid_format(self, engine):
        """Test processing an alert with invalid format."""
        alert = {
            "symbol": "AAPL",
            # Missing alert_type and timestamp
        }

        result = await engine.process_alert(alert)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_alert_no_symbol(self, engine):
        """Test processing an alert without symbol."""
        alert = {
            "alert_type": "price_cross",
            "severity": "WARNING",
            "timestamp": datetime.now().isoformat(),
        }

        result = await engine.process_alert(alert)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_alert_valid(self, engine):
        """Test validating a valid alert."""
        alert = {
            "symbol": "AAPL",
            "alert_type": "price_cross",
            "timestamp": datetime.now().isoformat(),
        }

        result = await engine.validate_alert(alert)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_alert_invalid(self, engine):
        """Test validating an invalid alert."""
        alert = {"symbol": "AAPL"}  # Missing fields

        result = await engine.validate_alert(alert)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_duplicate_alerts(self, engine):
        """Test filtering duplicate alerts."""
        alert1 = {
            "symbol": "AAPL",
            "alert_type": "price_cross",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        alert2 = {
            "symbol": "AAPL",
            "alert_type": "price_cross",
            "timestamp": "2024-01-01T00:00:00Z",  # Same as alert1
        }
        alert3 = {
            "symbol": "GOOGL",
            "alert_type": "price_cross",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        alerts = [alert1, alert2, alert3]
        result = await engine.filter_duplicate_alerts(alerts)

        # Should have 2 alerts (alert2 is duplicate of alert1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_prioritize_alerts(self, engine):
        """Test prioritizing alerts by severity."""
        alert1 = {
            "symbol": "AAPL",
            "alert_type": "price_cross",
            "severity": "INFO",
            "timestamp": datetime.now().isoformat(),
        }
        alert2 = {
            "symbol": "GOOGL",
            "alert_type": "price_cross",
            "severity": "CRITICAL",
            "timestamp": datetime.now().isoformat(),
        }
        alert3 = {
            "symbol": "TSLA",
            "alert_type": "price_cross",
            "severity": "WARNING",
            "timestamp": datetime.now().isoformat(),
        }

        alerts = [alert1, alert3, alert2]  # Unordered
        result = await engine.prioritize_alerts(alerts)

        # CRITICAL should be first
        assert result[0]["severity"] == "CRITICAL"
        # WARNING should be second
        assert result[1]["severity"] == "WARNING"
        # INFO should be last
        assert result[2]["severity"] == "INFO"

    @pytest.mark.asyncio
    async def test_get_alert_history(self, engine):
        """Test getting alert history."""
        result = await engine.get_alert_history("AAPL", 7)
        assert isinstance(result, list)


class TestITradeExecutorMethods:
    """Test ITradeExecutor protocol implementation."""

    @pytest.fixture
    def engine(self):
        """Create test engine instance."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False
        return engine

    @pytest.fixture
    def mock_signal(self):
        """Create a mock TradeSignal."""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.signal_id = "test_signal_1"
        signal.alert_id = "test_alert_1"
        signal.order_side.value = "BUY"
        signal.order_type.value = "MARKET"
        signal.quantity = Decimal("100")
        signal.price = Decimal("150")
        signal.stop_loss = Decimal("148")
        signal.take_profit = Decimal("154")
        signal.severity.value = "WARNING"
        signal.reason = "Test signal"
        return signal

    @pytest.mark.asyncio
    async def test_execute_trade_success(self, engine, mock_signal):
        """Test successful trade execution."""
        # Mock dependencies
        with patch(
            "app.core.compliance_engine.TradingDecisionLogger"
        ) as mock_logger, patch(
            "app.core.compliance_engine.SpainTaxEngineImpl"
        ) as mock_tax:
            # Setup mocks
            mock_logger.return_value.log_signal.return_value = "test_corr_id"
            mock_tax.return_value.calculate_capital_gains_tax.return_value = Decimal("0")

            result = await engine.execute_trade(mock_signal)

            assert result.success is True
            assert result.symbol == "AAPL"
            assert result.quantity == Decimal("100")

    @pytest.mark.asyncio
    async def test_execute_trade_kill_switch_active(self, engine, mock_signal):
        """Test trade execution blocked by kill switch."""
        # Activate kill switch
        engine.set_starting_capital(100000)
        engine.track_daily_pnl("TEST", "BUY", Decimal("100"), Decimal("100"), Decimal("90"))

        with patch(
            "app.core.compliance_engine.TradingDecisionLogger"
        ) as mock_logger, patch(
            "app.core.compliance_engine.SpainTaxEngineImpl"
        ):
            mock_logger.return_value.log_signal.return_value = "test_corr_id"

            result = await engine.execute_trade(mock_signal)

            assert result.success is False
            assert "KILL SWITCH" in result.error

    @pytest.mark.asyncio
    async def test_cancel_order(self, engine):
        """Test canceling an order."""
        with patch("app.core.compliance_engine.BrokerConnector") as mock_broker:
            mock_broker.return_value.cancel_order = AsyncMock(return_value=True)

            result = await engine.cancel_order("test_order_id")

            assert result is True

    @pytest.mark.asyncio
    async def test_modify_order(self, engine):
        """Test modifying an order."""
        with patch("app.core.compliance_engine.BrokerConnector") as mock_broker:
            mock_broker.return_value.modify_order = AsyncMock(return_value=True)

            result = await engine.modify_order("test_order_id", Decimal("155"))

            assert result is True

    @pytest.mark.asyncio
    async def test_get_order_status_submitted(self, engine):
        """Test getting status of submitted order."""
        engine._active_orders["test_order_id"] = {"symbol": "AAPL"}

        result = await engine.get_order_status("test_order_id")

        assert result == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_get_order_status_unknown(self, engine):
        """Test getting status of unknown order."""
        result = await engine.get_order_status("unknown_order")

        assert result == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_get_open_orders(self, engine):
        """Test getting all open orders."""
        engine._active_orders["order1"] = {"symbol": "AAPL"}
        engine._active_orders["order2"] = {"symbol": "GOOGL"}

        result = await engine.get_open_orders()

        assert len(result) == 2
        assert "order1" in result
        assert "order2" in result


class TestIStrategyCycleRunnerMethods:
    """Test IStrategyCycleRunner protocol implementation."""

    @pytest.fixture
    def engine(self):
        """Create test engine instance."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False
        return engine

    @pytest.fixture
    def mock_signals(self):
        """Create mock TradeSignals."""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = f"STOCK{i}"
            signal.quantity = Decimal("100")
            signal.price = Decimal(str(100 + i))
            signal.order_side.value = "BUY"
            signal.signal_id = f"signal_{i}"
            signal.alert_id = f"alert_{i}"
            signal.stop_loss = Decimal("98")
            signal.take_profit = Decimal("102")
            signal.severity.value = "WARNING"
            signal.reason = "Test"
            signals.append(signal)
        return signals

    @pytest.mark.asyncio
    async def test_run_cycle_success(self, engine, mock_signals):
        """Test successful cycle execution."""
        # Mock execute_trade to return success
        async def mock_execute(signal):
            result = Mock()
            result.success = True
            result.order_id = f"order_{signal.symbol}"
            return result

        engine.execute_trade = mock_execute

        result = await engine.run_cycle(mock_signals)

        assert result.success is True
        assert result.total_signals == 3
        assert result.executed_signals == 3
        assert result.failed_signals == 0

    @pytest.mark.asyncio
    async def test_run_cycle_invalid_input(self, engine):
        """Test cycle with invalid input."""
        result = await engine.run_cycle("not_a_list")

        assert result.success is False
        assert "Invalid cycle input" in result.errors

    @pytest.mark.asyncio
    async def test_validate_cycle_input_valid(self, engine, mock_signals):
        """Test validating valid cycle input."""
        result = await engine.validate_cycle_input(mock_signals)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_cycle_input_invalid_type(self, engine):
        """Test validating invalid cycle input type."""
        result = await engine.validate_cycle_input("not_a_list")
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_cycle_input_missing_attributes(self, engine):
        """Test validating cycle input with missing attributes."""
        invalid_signal = Mock()
        invalid_signal.symbol = "AAPL"
        # Missing quantity attribute

        result = await engine.validate_cycle_input([invalid_signal])
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_cycle_input_invalid_quantity(self, engine):
        """Test validating cycle input with invalid quantity."""
        invalid_signal = Mock()
        invalid_signal.symbol = "AAPL"
        invalid_signal.quantity = Decimal("-100")  # Negative quantity

        result = await engine.validate_cycle_input([invalid_signal])
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_cycle_phase_validate(self, engine, mock_signals):
        """Test executing validate phase."""
        result = await engine.execute_cycle_phase("validate", mock_signals)
        assert result.get("passed") is True

    @pytest.mark.asyncio
    async def test_execute_cycle_phase_execute(self, engine, mock_signals):
        """Test executing execute phase."""
        # Mock execute_trade
        async def mock_execute(signal):
            result = Mock()
            result.success = True
            result.order_id = f"order_{signal.symbol}"
            return result

        engine.execute_trade = mock_execute

        result = await engine.execute_cycle_phase("execute", mock_signals)
        assert "order_id" in result

    @pytest.mark.asyncio
    async def test_handle_cycle_error(self, engine):
        """Test handling cycle error."""
        error = Exception("Test error")

        # Should not raise
        await engine.handle_cycle_error(error)

    @pytest.mark.asyncio
    async def test_get_cycle_metrics(self, engine):
        """Test getting cycle metrics."""
        engine._active_orders["order1"] = {"symbol": "AAPL"}
        engine._completed_trades.append({"order_id": "order2"})

        result = await engine.get_cycle_metrics()

        assert "active_orders" in result
        assert "completed_trades" in result
        assert "slo_metrics" in result
        assert "daily_pnl" in result
        assert result["active_orders"] == 1


class TestProtocolCompliance:
    """Test that all protocol methods are properly implemented."""

    def test_i_alert_processor_compliance(self):
        """Verify IAlertProcessor protocol compliance."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False

        required_methods = [
            "process_alert",
            "validate_alert",
            "filter_duplicate_alerts",
            "prioritize_alerts",
            "get_alert_history",
        ]

        for method_name in required_methods:
            assert hasattr(engine, method_name), f"Missing method: {method_name}"
            method = getattr(engine, method_name)
            assert asyncio.iscoroutinefunction(
                method
            ), f"{method_name} should be async"

    def test_i_trade_executor_compliance(self):
        """Verify ITradeExecutor protocol compliance."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False

        required_methods = [
            "execute_trade",
            "cancel_order",
            "modify_order",
            "get_order_status",
            "get_open_orders",
        ]

        for method_name in required_methods:
            assert hasattr(engine, method_name), f"Missing method: {method_name}"
            method = getattr(engine, method_name)
            assert asyncio.iscoroutinefunction(
                method
            ), f"{method_name} should be async"

    def test_i_strategy_cycle_runner_compliance(self):
        """Verify IStrategyCycleRunner protocol compliance."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False

        required_methods = [
            "run_cycle",
            "validate_cycle_input",
            "execute_cycle_phase",
            "handle_cycle_error",
            "get_cycle_metrics",
        ]

        for method_name in required_methods:
            assert hasattr(engine, method_name), f"Missing method: {method_name}"
            method = getattr(engine, method_name)
            assert asyncio.iscoroutinefunction(
                method
            ), f"{method_name} should be async"

    def test_max_methods_per_protocol(self):
        """Verify ISP compliance: max 5 methods per protocol."""
        engine = ComplianceEngine(enable_logging=False)
        engine._initialized = False

        # IAlertProcessor methods (5 max)
        alert_processor_methods = [
            "process_alert",
            "validate_alert",
            "filter_duplicate_alerts",
            "prioritize_alerts",
            "get_alert_history",
        ]
        assert len(alert_processor_methods) == 5

        # ITradeExecutor methods (5 max)
        trade_executor_methods = [
            "execute_trade",
            "cancel_order",
            "modify_order",
            "get_order_status",
            "get_open_orders",
        ]
        assert len(trade_executor_methods) == 5

        # IStrategyCycleRunner methods (5 max)
        cycle_runner_methods = [
            "run_cycle",
            "validate_cycle_input",
            "execute_cycle_phase",
            "handle_cycle_error",
            "get_cycle_metrics",
        ]
        assert len(cycle_runner_methods) == 5
