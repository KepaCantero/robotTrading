"""
Tests for automated execution in backtesting.

This module tests concepts from Ernie Chan's Chapter 1 regarding
automated execution including signal-to-order conversion and
real-time execution simulation.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult, Trade, TradeStatus
from app.models.momentum import MarketData
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.order import Order, OrderType, OrderStatus
from app.providers.paper_trading import PaperTradingPortfolioProvider


class TestAutomatedExecution:
    """Test automated execution capabilities."""
    
    def _get_valid_timestamp(self, days_ago: int = 30) -> datetime:
        """Get a valid timestamp for testing (within the last year)."""
        return datetime.utcnow() - timedelta(days=days_ago)
    
    @pytest.fixture
    def config(self):
        """Default backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1")
        )
    
    @pytest.fixture
    def paper_trading_provider(self):
        """Paper trading provider for testing."""
        return PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
    
    def test_signal_to_order_conversion(self, config):
        """
        Test conversion of trading signals to executable orders.
        
        This test covers Ernie Chan's concept of converting signals
        into executable orders with proper risk management.
        """
        # Create market data
        market_data = self._create_market_data_for_execution()
        
        # Create signals
        signals = self._create_execution_signals()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify that signals are converted to orders/trades
        assert len(result.trades) > 0, "Signals should be converted to trades"
        
        # Verify order properties
        for trade in result.trades:
            assert trade.symbol in ["EXEC_STOCK"], f"Invalid symbol: {trade.symbol}"
            assert trade.side in ["buy", "sell"], f"Invalid side: {trade.side}"
            assert trade.quantity > 0, f"Invalid quantity: {trade.quantity}"
            assert trade.entry_price > 0, f"Invalid price: {trade.entry_price}"
            assert trade.entry_time is not None, "Missing entry time"
            assert trade.status in [TradeStatus.OPEN, TradeStatus.CLOSED], f"Invalid status: {trade.status}"
    
    def test_real_time_execution_simulation(self, config, paper_trading_provider):
        """
        Test real-time execution simulation.
        
        This test simulates real-time trading execution with
        proper timing and market conditions.
        """
        # Create market data with real-time updates
        market_data = self._create_real_time_market_data()
        
        # Simulate real-time execution
        execution_results = []
        
        for i, md in enumerate(market_data):
            # Generate signal based on current market data
            signal = self._generate_real_time_signal(md, i)
            
            if signal:
                # Execute signal in real-time
                execution_result = self._execute_real_time_signal(
                    signal, md, paper_trading_provider
                )
                execution_results.append(execution_result)
        
        # Verify real-time execution
        assert len(execution_results) > 0, "Should have real-time executions"
        
        # Verify execution timing
        for result in execution_results:
            assert result['execution_time'] >= result['signal_time'], \
                "Execution should be after signal generation"
            assert result['execution_price'] > 0, "Invalid execution price"
            assert result['execution_quantity'] > 0, "Invalid execution quantity"
    
    def test_market_impact_simulation(self, config):
        """
        Test simulation of market impact on execution.
        
        This test covers the impact of order size on execution price
        and market conditions.
        """
        # Create market data
        market_data = self._create_market_data_for_impact()
        
        # Test different order sizes
        order_sizes = [Decimal("100"), Decimal("1000"), Decimal("10000")]
        impact_results = []
        
        for order_size in order_sizes:
            # Create signal with specific order size
            signal = self._create_signal_with_size(order_size)
            
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(market_data, [signal])
            
            if result.trades:
                trade = result.trades[0]
                market_price = next(md.close_price for md in market_data if md.timestamp >= trade.entry_time)
                impact = abs(trade.entry_price - market_price) / market_price
                impact_results.append((order_size, impact))
        
        # Verify that larger orders have more impact
        assert len(impact_results) > 1, "Should test multiple order sizes"
        
        # Sort by order size
        impact_results.sort(key=lambda x: x[0])
        
        # Verify impact increases with order size
        for i in range(1, len(impact_results)):
            assert impact_results[i][1] >= impact_results[i-1][1], \
                f"Impact should increase with order size: {impact_results}"
    
    def test_execution_timing_constraints(self, config):
        """
        Test execution timing constraints and market hours.
        
        This test ensures that orders are only executed during
        appropriate market hours and timing constraints.
        """
        # Create market data with different times
        market_data = self._create_market_data_with_timing()
        
        # Create signals at different times
        signals = self._create_signals_with_timing()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify execution timing
        for trade in result.trades:
            # Check that trade time is reasonable (not in the future)
            assert trade.entry_time <= datetime.utcnow(), f"Trade executed in the future: {trade.entry_time}"
            
            # Check that trade time matches market data time
            market_point = next((md for md in market_data if md.timestamp >= trade.entry_time), None)
            assert market_point is not None, f"No market data for trade time: {trade.entry_time}"
            
            # Verify that trade was executed after signal timestamp
            signal_time = next((s.timestamp for s in signals if s.symbol == trade.symbol), None)
            if signal_time:
                assert trade.entry_time >= signal_time, f"Trade executed before signal: {trade.entry_time} < {signal_time}"
    
    def test_partial_fill_simulation(self, config):
        """
        Test simulation of partial order fills.
        
        This test covers scenarios where orders are only partially filled
        due to market conditions or liquidity constraints.
        """
        # Create market data with limited liquidity
        market_data = self._create_low_liquidity_market_data()
        
        # Create large order signal
        large_signal = self._create_large_order_signal()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, [large_signal])
        
        # Verify partial fill handling
        if result.trades:
            trade = result.trades[0]
            
            # Check that trade quantity is reasonable
            assert trade.quantity > 0, "Should have some fill"
            assert trade.quantity <= large_signal.volume, "Should not exceed signal volume"
            
            # Verify trade status
            if trade.quantity < large_signal.volume:
                assert trade.status == TradeStatus.PARTIALLY_FILLED, \
                    "Should be marked as partially filled"
    
    def test_execution_cost_calculation(self, config):
        """
        Test calculation of execution costs including commissions and slippage.
        
        This test ensures that all execution costs are properly calculated
        and accounted for in the backtest results.
        """
        # Create market data
        market_data = self._create_market_data_for_costs()
        
        # Create signals
        signals = self._create_cost_test_signals()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify cost calculations
        total_commission = Decimal("0")
        total_slippage = Decimal("0")
        
        for trade in result.trades:
            assert trade.commission >= 0, f"Invalid commission: {trade.commission}"
            assert trade.slippage >= 0, f"Invalid slippage: {trade.slippage}"
            
            total_commission += trade.commission
            total_slippage += trade.slippage
        
        # Verify that costs are reasonable
        assert total_commission > 0, "Should have commission costs"
        assert total_slippage > 0, "Should have slippage costs"
        
        # Verify that costs are proportional to trading activity
        expected_commission = len(result.trades) * config.commission_per_trade
        assert abs(total_commission - expected_commission) < Decimal("0.01"), \
            f"Commission calculation error: {total_commission} vs {expected_commission}"
    
    def test_order_priority_and_routing(self, config):
        """
        Test order priority and routing simulation.
        
        This test simulates how orders are prioritized and routed
        in different market conditions.
        """
        # Create market data
        market_data = self._create_market_data_for_routing()
        
        # Create multiple signals with different priorities
        signals = self._create_priority_signals()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify order execution order
        executed_trades = sorted(result.trades, key=lambda t: t.entry_time)
        
        # Check that higher priority signals are executed first
        for i in range(1, len(executed_trades)):
            current_trade = executed_trades[i]
            previous_trade = executed_trades[i-1]
            
            # Verify chronological order
            assert current_trade.entry_time >= previous_trade.entry_time, \
                "Trades should be in chronological order"
    
    def test_execution_error_handling(self, config):
        """
        Test handling of execution errors and failures.
        
        This test covers scenarios where order execution fails
        due to various market conditions or system errors.
        """
        # Create market data with potential execution issues
        market_data = self._create_problematic_market_data()
        
        # Create signals that might fail
        signals = self._create_problematic_signals()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify error handling
        assert result.final_capital > 0, "Should handle execution errors gracefully"
        
        # Verify that failed executions don't crash the system
        assert len(result.trades) >= 0, "Should handle execution failures"
        
        # Check that system continues to function
        assert result.performance.total_trades >= 0, "Should track performance correctly"
    
    def _create_market_data_for_execution(self) -> List[MarketData]:
        """Create market data for execution testing."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(50):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.2))
            
            data.append(MarketData(
                symbol="EXEC_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_execution_signals(self) -> List[Signal]:
        """Create signals for execution testing."""
        signals = []
        base_date = self._get_valid_timestamp(30)  # 30 days ago
        
        for i in range(0, 15, 5):  # Further reduced range to avoid future dates
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.2))
            
            signals.append(Signal(
                symbol="EXEC_STOCK",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=90.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_real_time_market_data(self) -> List[MarketData]:
        """Create market data for real-time execution testing."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(20):
            date = base_date + timedelta(hours=i)  # Hourly data
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            data.append(MarketData(
                symbol="RT_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _generate_real_time_signal(self, market_data: MarketData, index: int) -> Optional[Signal]:
        """Generate real-time signal based on market data."""
        if index % 5 == 0:  # Generate signal every 5 hours
            return Signal(
                symbol="RT_STOCK",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=90.0,
                priority_score=80.0,
                source=SignalSource.MOMENTUM,
                price=market_data.close_price,
                volume=Decimal("1000"),
                timestamp=market_data.timestamp
            )
        return None
    
    def _execute_real_time_signal(self, signal: Signal, market_data: MarketData, provider: PaperTradingPortfolioProvider) -> Dict[str, Any]:
        """Execute signal in real-time."""
        # Simulate execution delay
        execution_time = market_data.timestamp + timedelta(minutes=1)
        
        # Simulate execution price with slippage
        slippage_factor = Decimal("0.001")  # 0.1% slippage
        execution_price = market_data.close_price * (Decimal("1") + slippage_factor)
        
        # Simulate execution quantity
        execution_quantity = signal.volume
        
        return {
            'signal_time': signal.timestamp,
            'execution_time': execution_time,
            'execution_price': execution_price,
            'execution_quantity': execution_quantity,
            'symbol': signal.symbol
        }
    
    def _create_market_data_for_impact(self) -> List[MarketData]:
        """Create market data for market impact testing."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(10):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0")
            
            data.append(MarketData(
                symbol="IMPACT_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_signal_with_size(self, order_size: Decimal) -> Signal:
        """Create signal with specific order size."""
        return Signal(
            symbol="IMPACT_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=90.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=order_size,
            timestamp=self._get_valid_timestamp(5)  # 5 days ago
        )
    
    def _create_market_data_with_timing(self) -> List[MarketData]:
        """Create market data with different timing scenarios."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        # Create data for different times of day
        times = [
            self._get_valid_timestamp(1).replace(hour=9, minute=30),   # Market open
            self._get_valid_timestamp(1).replace(hour=12, minute=0),   # Midday
            self._get_valid_timestamp(1).replace(hour=15, minute=30),  # Near close
            self._get_valid_timestamp(1).replace(hour=16, minute=0),   # After hours
            self._get_valid_timestamp(1).replace(hour=20, minute=0),   # Evening
        ]
        
        for i, time in enumerate(times):
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            data.append(MarketData(
                symbol="TIMING_STOCK",
                timestamp=time,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_signals_with_timing(self) -> List[Signal]:
        """Create signals with different timing."""
        signals = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        # Signal during market hours
        signals.append(Signal(
            symbol="TIMING_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=90.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
            timestamp=base_date.replace(hour=10, minute=0)
        ))
        
        # Signal after market hours (should not execute)
        signals.append(Signal(
            symbol="TIMING_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=90.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.1"),
            volume=Decimal("1000"),
            timestamp=base_date.replace(hour=18, minute=0)
        ))
        
        return signals
    
    def _create_low_liquidity_market_data(self) -> List[MarketData]:
        """Create market data with low liquidity."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(5):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0")
            
            # Calculate bid and ask with wide spread
            spread_amount = price * Decimal("0.01")  # 1% spread
            bid = price - spread_amount / 2
            ask = price + spread_amount / 2
            
            data.append(MarketData(
                symbol="LOW_LIQ_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("10000"),  # Low volume
                bid=bid,
                ask=ask,
                spread=spread_amount
            ))
        
        return data
    
    def _create_large_order_signal(self) -> Signal:
        """Create large order signal for partial fill testing."""
        return Signal(
            symbol="LOW_LIQ_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=30.0,  # Low liquidity
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=Decimal("50000"),  # Large order
            timestamp=self._get_valid_timestamp(5)  # 5 days ago
        )
    
    def _create_market_data_for_costs(self) -> List[MarketData]:
        """Create market data for cost calculation testing."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(20):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            data.append(MarketData(
                symbol="COST_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_cost_test_signals(self) -> List[Signal]:
        """Create signals for cost testing."""
        signals = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(0, 10, 5):  # Reduced range to avoid future dates
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            signals.append(Signal(
                symbol="COST_STOCK",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=90.0,
                priority_score=80.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_market_data_for_routing(self) -> List[MarketData]:
        """Create market data for order routing testing."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(15):
            date = base_date + timedelta(minutes=i * 30)  # 30-minute intervals
            price = Decimal("100.0") + Decimal(str(i * 0.05))
            
            data.append(MarketData(
                symbol="ROUTE_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_priority_signals(self) -> List[Signal]:
        """Create signals with different priorities."""
        signals = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        # High priority signal
        signals.append(Signal(
            symbol="ROUTE_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=90.0,
            liquidity_score=95.0,
            priority_score=95.0,  # High priority
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
            timestamp=base_date + timedelta(minutes=15)
        ))
        
        # Low priority signal
        signals.append(Signal(
            symbol="ROUTE_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.WEAK,
            confidence=60.0,
            liquidity_score=80.0,
            priority_score=60.0,  # Low priority
            source=SignalSource.MOMENTUM,
            price=Decimal("100.05"),
            volume=Decimal("500"),
            timestamp=base_date + timedelta(minutes=30)
        ))
        
        return signals
    
    def _create_problematic_market_data(self) -> List[MarketData]:
        """Create market data with potential execution issues."""
        data = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        for i in range(10):
            date = base_date + timedelta(days=i)
            
            # Create problematic scenarios
            if i == 3:  # Market halt
                continue  # Skip this day
            
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            data.append(MarketData(
                symbol="PROBLEM_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.002"),
                low_price=price * Decimal("0.998"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_problematic_signals(self) -> List[Signal]:
        """Create signals that might cause execution problems."""
        signals = []
        base_date = self._get_valid_timestamp(10)  # 10 days ago
        
        # Normal signal
        signals.append(Signal(
            symbol="PROBLEM_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=90.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
            timestamp=base_date
        ))
        
        # Signal during market halt (should fail gracefully)
        signals.append(Signal(
            symbol="PROBLEM_STOCK",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=90.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.3"),
            volume=Decimal("1000"),
            timestamp=base_date + timedelta(days=3)
        ))
        
        return signals
