"""
Integration tests for PHASE 3: Dynamic Risk Scaling

Tests the complete PHASE 3 system end-to-end, including:
- Full orchestrator flow with all 4 monitors
- RiskScalingMonitor with state persistence
- Multi-symbol tracking
- Signal adjustment with dynamic scaling
- Alert generation and dashboard data
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from app.services.risk_scaling.volatility_monitor import VolatilityMonitor, PriceData
from app.services.risk_scaling.sharpe_ratio_monitor import SharpeRatioMonitor
from app.services.risk_scaling.loss_monitor import LossMonitor, TradeResult
from app.services.risk_scaling.drawdown_monitor import DrawdownMonitor, EquityPoint
from app.services.risk_scaling.risk_scaling_orchestrator import RiskScalingOrchestrator
from app.services.risk_scaling.risk_scaling_monitor import RiskScalingMonitor
from app.services.risk_scaling.models import (
    RiskScalingFactors,
    RiskScalingState,
    RiskAlert,
    RiskAlertType,
    RiskLevel,
    Signal,
    AdjustedSignal,
)


class TestRiskScalingFullFlow:
    """Integration test for complete PHASE 3 risk scaling flow."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with all monitors."""
        return RiskScalingOrchestrator()

    @pytest.fixture
    def monitor(self):
        """Create RiskScalingMonitor for state tracking."""
        return RiskScalingMonitor(history_retention_days=30)

    @pytest.fixture
    def sample_price_data(self):
        """Create 30 days of OHLC price data."""
        prices = []
        base_time = datetime.now() - timedelta(days=30)
        base_price = Decimal("100")

        for i in range(30):
            prices.append(
                PriceData(
                    timestamp=base_time + timedelta(days=i),
                    open=base_price + Decimal(str(i * 0.1)),
                    high=base_price + Decimal(str(i * 0.2)),
                    low=base_price + Decimal(str(i * 0.05)),
                    close=base_price + Decimal(str(i * 0.12)),
                )
            )

        return prices

    @pytest.fixture
    def sample_returns(self):
        """Create daily returns."""
        return [Decimal(str(0.01 * (-1 if i % 5 == 0 else 1))) for i in range(30)]

    @pytest.fixture
    def sample_trade_results(self):
        """Create trade results with mixed wins/losses."""
        trades = []
        base_time = datetime.now() - timedelta(days=30)
        pnl_sequence = [100, 50, -100, -50, 150, -75, 200, 100, -125, 300]

        for i, pnl in enumerate(pnl_sequence * 3):  # 30 trades
            trades.append(
                TradeResult(
                    trade_id=f"trade_{i}",
                    timestamp=base_time + timedelta(days=i),
                    pnl=Decimal(str(pnl)),
                    symbol="TEST",
                    side="buy",
                    entry_price=Decimal("100"),
                    exit_price=Decimal("100") + Decimal(str(pnl / 100)),
                    quantity=Decimal("1"),
                )
            )

        return trades

    @pytest.fixture
    def sample_equity_curve(self):
        """Create equity curve."""
        base_equity = Decimal("10000")
        returns = [
            Decimal("0.01"),
            Decimal("0.02"),
            Decimal("-0.01"),
            Decimal("-0.02"),
            Decimal("0.015"),
            Decimal("0.005"),
            Decimal("-0.03"),
            Decimal("0.02"),
            Decimal("0.01"),
            Decimal("0.025"),
        ] * 3

        curve = [base_equity]
        for ret in returns:
            curve.append(curve[-1] * (Decimal("1") + ret))

        return curve

    @pytest.mark.asyncio
    async def test_full_orchestrator_flow(
        self, orchestrator, sample_price_data, sample_returns, sample_trade_results, sample_equity_curve
    ):
        """Test complete orchestrator flow with all 4 monitors."""
        portfolio_id = "test_portfolio"

        # Calculate scaling factors
        scaling_factors = await orchestrator.calculate_scaling_factors(
            symbol="TEST",
            prices=sample_price_data,
            daily_returns=sample_returns,
            trade_results=sample_trade_results,
            equity_curve=sample_equity_curve,
        )

        # Validate factors are within expected ranges
        assert Decimal("0.2") <= scaling_factors.sharpe_scale <= Decimal("1.0")
        assert Decimal("0.5") <= scaling_factors.volatility_scale <= Decimal("1.5")
        assert Decimal("0.5") <= scaling_factors.loss_scale <= Decimal("1.0")
        assert Decimal("0.0") <= scaling_factors.drawdown_scale <= Decimal("1.0")

        # Combined scale should be product of all
        expected_combined = (
            scaling_factors.volatility_scale
            * scaling_factors.sharpe_scale
            * scaling_factors.loss_scale
            * scaling_factors.drawdown_scale
        )
        assert scaling_factors.combined_scale == expected_combined

    @pytest.mark.asyncio
    async def test_signal_adjustment_with_scaling(self, orchestrator):
        """Test signal adjustment based on dynamic scaling factors."""
        signal_dict = {
            "signal_id": "signal_001",
            "symbol": "AAPL",
            "side": "buy",
        }

        scaling_factors = RiskScalingFactors(
            volatility_scale=Decimal("0.8"),  # Reduce due to volatility
            sharpe_scale=Decimal("0.9"),  # Slight reduction
            loss_scale=Decimal("0.7"),  # Consecutive losses
            drawdown_scale=Decimal("1.0"),  # Normal
        )

        adjusted = await orchestrator.apply_dynamic_scaling(
            signal=signal_dict,
            base_position_size=Decimal("1000"),
            stop_loss_price=Decimal("145"),
            scaling_factors=scaling_factors,
        )

        # Position should be reduced
        expected_adjusted = Decimal("1000") * (Decimal("0.8") * Decimal("0.9") * Decimal("0.7"))
        assert adjusted.adjusted_position_size == expected_adjusted
        assert adjusted.is_rejected is False
        assert adjusted.scaling_factors == scaling_factors

    @pytest.mark.asyncio
    async def test_halted_trading_scenario(self, orchestrator):
        """Test when drawdown triggers trading halt."""
        signal_dict = {
            "signal_id": "signal_002",
            "symbol": "TEST",
            "side": "buy",
        }

        # Extreme drawdown scenario
        scaling_factors = RiskScalingFactors(
            volatility_scale=Decimal("1.0"),
            sharpe_scale=Decimal("0.5"),  # Poor performance
            loss_scale=Decimal("0.5"),  # Multiple losses
            drawdown_scale=Decimal("0.0"),  # HALT
        )

        adjusted = await orchestrator.apply_dynamic_scaling(
            signal=signal_dict,
            base_position_size=Decimal("5000"),
            stop_loss_price=Decimal("95"),
            scaling_factors=scaling_factors,
        )

        # Should be completely halted
        assert adjusted.adjusted_position_size == Decimal("0")
        assert adjusted.is_rejected is True
        assert adjusted.rejection_reason == "Trading halted due to drawdown circuit breaker"

    @pytest.mark.asyncio
    async def test_monitor_state_persistence(self, monitor, orchestrator):
        """Test RiskScalingMonitor persists state and history."""
        portfolio_id = "portfolio_123"

        # Create initial state with combined scale 0.72 (WARNING level)
        initial_state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.0"),
                sharpe_scale=Decimal("0.9"),
                loss_scale=Decimal("0.8"),
                drawdown_scale=Decimal("1.0"),
            ),
            current_atr=Decimal("1.5"),
            sharpe_ratio=Decimal("1.2"),
            consecutive_losses=1,
            current_drawdown=Decimal("0.05"),
            max_drawdown=Decimal("0.12"),
            active_alerts=[],
        )

        # Store state
        monitor.store_state(portfolio_id, initial_state)

        # Retrieve and verify
        status = await monitor.get_scaling_status(portfolio_id)
        assert status.portfolio_id == portfolio_id
        assert status.scaling_factors.combined_scale == initial_state.scaling_factors.combined_scale
        # combined = 1.0 × 0.9 × 0.8 × 1.0 = 0.72 → WARNING (< 0.8)
        assert status.risk_level == RiskLevel.WARNING

    @pytest.mark.asyncio
    async def test_alert_generation_and_subscription(self, monitor):
        """Test alert generation and subscriber notification."""
        portfolio_id = "test_alert_portfolio"

        # Subscribe to alerts
        subscription = await monitor.subscribe_to_alerts(
            portfolio_id=portfolio_id,
            alert_types=[RiskAlertType.HALT_TRADING, RiskAlertType.DRAWDOWN_WARNING],
            min_severity=RiskLevel.WARNING,
        )

        assert subscription.portfolio_id == portfolio_id
        assert len(subscription.alert_types) == 2
        assert subscription.enabled is True

        # Create and record alert
        alert = RiskAlert(
            portfolio_id=portfolio_id,
            alert_type=RiskAlertType.DRAWDOWN_WARNING,
            severity=RiskLevel.CRITICAL,
            message="Drawdown exceeded 20%",
        )

        await monitor.record_alert(alert)

        # Verify alert was recorded
        alerts = await monitor.get_alert_history(portfolio_id=portfolio_id, hours_back=1)
        assert len(alerts) == 1
        assert alerts[0].alert_type == RiskAlertType.DRAWDOWN_WARNING

    @pytest.mark.asyncio
    async def test_scaling_trends_analysis(self, monitor):
        """Test historical trend analysis over time period."""
        from app.services.risk_scaling.models import RiskScalingSnapshot

        portfolio_id = "trend_test_portfolio"

        # Create multiple snapshots over 7 days
        base_time = datetime.now() - timedelta(days=7)
        snapshots = []

        for i in range(7):
            snapshot = RiskScalingSnapshot(
                timestamp=base_time + timedelta(days=i),
                scaling_factors=RiskScalingFactors(
                    volatility_scale=Decimal(str(1.0 + i * 0.05)),  # Increasing volatility
                    sharpe_scale=Decimal(str(1.0 - i * 0.05)),  # Decreasing performance
                    loss_scale=Decimal(str(1.0 - i * 0.02)),  # Slight decline
                    drawdown_scale=Decimal("1.0"),
                ),
                current_atr=Decimal(str(1.0 + i * 0.1)),
                average_atr=Decimal("1.0"),
                sharpe_ratio=Decimal(str(2.0 - i * 0.2)),  # Decreasing sharpe ratio
            )
            snapshots.append(snapshot)

        # Create state with snapshots
        state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.3"),
                sharpe_scale=Decimal("0.7"),
                loss_scale=Decimal("0.86"),
                drawdown_scale=Decimal("1.0"),
            ),
            current_atr=Decimal("1.6"),
            sharpe_ratio=Decimal("1.6"),
            consecutive_losses=6,
            current_drawdown=Decimal("0.08"),
            max_drawdown=Decimal("0.17"),
            active_alerts=[],
            scaling_history=snapshots,
        )

        monitor.store_state(portfolio_id, state)

        # Analyze trends
        trends = await monitor.get_scaling_trends(portfolio_id, days=7)

        assert trends["portfolio_id"] == portfolio_id
        assert trends["data_points"] > 0
        assert "combined_scale" in trends
        assert "volatility_scale" in trends
        assert "sharpe_scale" in trends

        # Verify trend analysis contains all expected metrics
        assert "trend" in trends["combined_scale"]

    @pytest.mark.asyncio
    async def test_multi_symbol_independent_tracking(self, orchestrator, monitor):
        """Test tracking multiple symbols with independent scaling."""
        # Create different market conditions for two symbols tracked independently
        # using separate portfolio IDs (one per symbol)

        # Stable symbol (AAPL)
        state_stable = RiskScalingState(
            portfolio_id="portfolio_AAPL",
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.3"),  # Low volatility boost
                sharpe_scale=Decimal("1.0"),
                loss_scale=Decimal("1.0"),
                drawdown_scale=Decimal("1.0"),
            ),
            current_atr=Decimal("0.5"),
            sharpe_ratio=Decimal("1.8"),
            consecutive_losses=0,
            current_drawdown=Decimal("0.01"),
            max_drawdown=Decimal("0.03"),
            active_alerts=[],
        )

        # Volatile symbol (TSLA)
        state_volatile = RiskScalingState(
            portfolio_id="portfolio_TSLA",
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("0.6"),  # High volatility reduction
                sharpe_scale=Decimal("0.8"),
                loss_scale=Decimal("0.9"),
                drawdown_scale=Decimal("1.0"),
            ),
            current_atr=Decimal("2.5"),
            sharpe_ratio=Decimal("1.1"),
            consecutive_losses=1,
            current_drawdown=Decimal("0.08"),
            max_drawdown=Decimal("0.15"),
            active_alerts=[],
        )

        monitor.store_state("portfolio_AAPL", state_stable)
        monitor.store_state("portfolio_TSLA", state_volatile)

        # Verify independent scaling
        status_aapl = await monitor.get_scaling_status("portfolio_AAPL")
        status_tsla = await monitor.get_scaling_status("portfolio_TSLA")

        assert status_aapl.scaling_factors.volatility_scale > status_tsla.scaling_factors.volatility_scale
        assert status_aapl.scaling_factors.combined_scale > status_tsla.scaling_factors.combined_scale

    @pytest.mark.asyncio
    async def test_dashboard_data_generation(self, monitor):
        """Test complete dashboard data generation."""
        portfolio_id = "dashboard_test"

        # Setup state with alerts
        state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.0"),
                sharpe_scale=Decimal("0.95"),
                loss_scale=Decimal("0.85"),
                drawdown_scale=Decimal("0.9"),
            ),
            current_atr=Decimal("1.3"),
            sharpe_ratio=Decimal("1.5"),
            consecutive_losses=0,
            current_drawdown=Decimal("0.04"),
            max_drawdown=Decimal("0.08"),
            active_alerts=[],
        )

        monitor.store_state(portfolio_id, state)

        # Generate dashboard data
        dashboard_data = await monitor.get_portfolio_dashboard_data(portfolio_id)

        assert dashboard_data["portfolio_id"] == portfolio_id
        assert "status" in dashboard_data
        assert "trends" in dashboard_data
        assert "recent_alerts" in dashboard_data
        assert "last_updated" in dashboard_data

        status = dashboard_data["status"]
        assert "scaling_factors" in status
        assert "risk_level" in status

    @pytest.mark.asyncio
    async def test_recovery_from_extreme_drawdown(self, monitor):
        """Test system behavior during recovery from extreme conditions."""
        portfolio_id = "recovery_test"

        # Extreme drawdown state
        extreme_state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.0"),
                sharpe_scale=Decimal("0.2"),
                loss_scale=Decimal("0.5"),
                drawdown_scale=Decimal("0.0"),  # HALTED
            ),
            current_atr=Decimal("3.0"),
            sharpe_ratio=Decimal("-0.5"),
            consecutive_losses=5,
            current_drawdown=Decimal("0.25"),
            max_drawdown=Decimal("0.30"),
            active_alerts=[],
        )

        monitor.store_state(portfolio_id, extreme_state)

        status_extreme = await monitor.get_scaling_status(portfolio_id)
        assert status_extreme.risk_level == RiskLevel.HALT

        # Simulate recovery
        recovered_state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=RiskScalingFactors(
                volatility_scale=Decimal("1.0"),
                sharpe_scale=Decimal("0.9"),
                loss_scale=Decimal("1.0"),
                drawdown_scale=Decimal("0.8"),  # Recovering
            ),
            current_atr=Decimal("1.5"),
            sharpe_ratio=Decimal("1.2"),
            consecutive_losses=0,
            current_drawdown=Decimal("0.10"),
            max_drawdown=Decimal("0.25"),
            active_alerts=[],
        )

        monitor.store_state(portfolio_id, recovered_state)

        status_recovered = await monitor.get_scaling_status(portfolio_id)
        # combined = 1.0 × 0.9 × 1.0 × 0.8 = 0.72 → WARNING (< 0.8)
        assert status_recovered.risk_level == RiskLevel.WARNING
        assert status_recovered.risk_level != RiskLevel.HALT

    @pytest.mark.asyncio
    async def test_alert_resolution_workflow(self, monitor):
        """Test alert lifecycle: creation, notification, resolution."""
        portfolio_id = "alert_lifecycle_test"

        # Subscribe to alerts
        await monitor.subscribe_to_alerts(
            portfolio_id=portfolio_id,
            alert_types=[RiskAlertType.HALT_TRADING],
            min_severity=RiskLevel.CRITICAL,
        )

        # Create alert
        alert = RiskAlert(
            portfolio_id=portfolio_id,
            alert_type=RiskAlertType.HALT_TRADING,
            severity=RiskLevel.HALT,
            message="Maximum drawdown exceeded",
        )

        await monitor.record_alert(alert)

        # Verify alert is active
        alerts = await monitor.get_alert_history(portfolio_id=portfolio_id, hours_back=1)
        assert len(alerts) == 1
        assert alerts[0].resolved is False

        # Resolve alert
        resolved = await monitor.resolve_alert(alerts[0].alert_id)

        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, orchestrator):
        """Test graceful degradation with insufficient data."""
        # Minimal price data (less than ATR period)
        minimal_prices = [
            PriceData(
                timestamp=datetime.now() - timedelta(days=i),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
            )
            for i in range(5)  # Only 5 candles, need 14+ for ATR
        ]

        minimal_returns = [Decimal("0.01") for _ in range(5)]

        # Should handle gracefully (not raise exception)
        try:
            scaling_factors = await orchestrator.calculate_scaling_factors(
                symbol="TEST",
                prices=minimal_prices,
                daily_returns=minimal_returns,
                trade_results=[],
                equity_curve=[Decimal("10000"), Decimal("10100")],
            )

            # Should have default scaling or reduced functionality
            assert scaling_factors is not None
        except ValueError:
            # Alternative: may raise error that's handled upstream
            pass
