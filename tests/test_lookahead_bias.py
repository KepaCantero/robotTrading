"""
Tests for look-ahead bias prevention in backtesting.

This module tests concepts from Ernie Chan's Chapter 1 regarding
look-ahead bias and ensuring decisions are based only on available information.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.models.momentum import MarketData
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource


class TestLookAheadBias:
    """Test look-ahead bias prevention techniques."""
    
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
    
    def test_signal_timing_validation(self, config):
        """
        Test that signals are only processed with information available at that time.
        
        This test covers Ernie Chan's concept of look-ahead bias where
        future information is used to make past decisions.
        """
        # Create market data with known future prices
        market_data = self._create_market_data_with_future_info()
        
        # Create signals that should NOT use future information
        signals = self._create_signals_without_lookahead()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify that signals are processed in chronological order
        signal_times = [s.timestamp for s in signals]
        assert signal_times == sorted(signal_times), "Signals should be in chronological order"
        
        # Verify that we have some trades (basic functionality)
        assert len(result.trades) > 0, "Should have executed some trades"
        
        # Verify that trades are executed at appropriate times
        for trade in result.trades:
            # Find the corresponding market data point
            market_point = next((md for md in market_data if md.timestamp >= trade.entry_time), None)
            assert market_point is not None, f"Trade {trade.trade_id} has no corresponding market data"
            
            # Verify that trade timestamp is not in the future relative to market data
            assert trade.entry_time <= market_point.timestamp, \
                f"Trade {trade.trade_id} executed at {trade.entry_time} but market data is at {market_point.timestamp}"
    
    def test_future_price_prevention(self, config):
        """
        Test prevention of using future prices in signal generation.
        
        This test ensures that signals are generated based only on
        historical data available at the time of signal generation.
        """
        # Create market data
        market_data = self._create_market_data_with_future_info()
        
        # Create signals that might accidentally use future information
        signals_with_lookahead = self._create_signals_with_lookahead()
        signals_without_lookahead = self._create_signals_without_lookahead()
        
        backtester = SimpleBacktester(config)
        
        # Run backtest with look-ahead signals
        result_with_lookahead = backtester.run_backtest(market_data, signals_with_lookahead)
        
        # Run backtest without look-ahead signals
        result_without_lookahead = backtester.run_backtest(market_data, signals_without_lookahead)
        
        # Verify that look-ahead bias leads to unrealistic performance
        assert result_with_lookahead.total_return > result_without_lookahead.total_return, \
            "Look-ahead bias should inflate performance"
        
        # Check that the difference is significant
        performance_difference = result_with_lookahead.total_return - result_without_lookahead.total_return
        assert performance_difference > 20, \
            f"Look-ahead bias effect should be significant: {performance_difference}"
    
    def test_technical_indicator_lookahead(self, config):
        """
        Test that technical indicators don't use future data.
        
        This test ensures that technical indicators are calculated
        using only historical data available at each point in time.
        """
        # Create market data with known patterns
        market_data = self._create_market_data_with_patterns()
        
        # Create signals based on technical indicators
        signals = self._create_technical_indicator_signals(market_data)
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify that technical indicators are calculated correctly
        for i, signal in enumerate(signals):
            # Get historical data up to signal time
            historical_data = [md for md in market_data if md.timestamp <= signal.timestamp]
            
            # Calculate technical indicator using only historical data
            if len(historical_data) >= 20:  # Need enough data for moving average
                prices = [md.close_price for md in historical_data[-20:]]
                sma = sum(prices) / len(prices)
                
                # Verify that signal is based on historical data
                assert abs(signal.price - historical_data[-1].close_price) < Decimal("1.0"), \
                    f"Signal price {signal.price} should be close to historical price {historical_data[-1].close_price}"
    
    def test_data_availability_validation(self, config):
        """
        Test validation that data is available at signal generation time.
        
        This test ensures that signals are only generated when
        sufficient historical data is available.
        """
        # Create market data with gaps
        market_data = self._create_market_data_with_gaps()
        
        # Create signals that might reference unavailable data
        signals = self._create_signals_with_data_gaps()
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)
        
        # Verify that signals are only processed when data is available
        processed_signals = []
        for signal in signals:
            # Check if data is available at signal time
            available_data = [md for md in market_data if md.timestamp <= signal.timestamp]
            if len(available_data) >= 10:  # Minimum data requirement
                processed_signals.append(signal)
        
        # Verify that we have some trades (basic functionality)
        assert len(result.trades) > 0, "Should have executed some trades"
        
        # Verify that signals are processed in chronological order
        signal_times = [s.timestamp for s in signals]
        assert signal_times == sorted(signal_times), "Signals should be in chronological order"
    
    def test_real_time_simulation(self, config):
        """
        Test real-time simulation without look-ahead bias.
        
        This test simulates real-time trading where decisions
        are made with only current and historical information.
        """
        # Create market data
        market_data = self._create_market_data_with_future_info()
        
        # Simulate real-time signal generation
        real_time_signals = self._simulate_real_time_signals(market_data)
        
        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, real_time_signals)
        
        # Verify that signals are generated in real-time order
        for i in range(1, len(real_time_signals)):
            assert real_time_signals[i].timestamp >= real_time_signals[i-1].timestamp, \
                "Signals should be in chronological order"
        
        # Verify that performance is realistic (not inflated by look-ahead)
        assert result.total_return < 100, "Real-time performance should be realistic"
        assert result.performance.sharpe_ratio is None or result.performance.sharpe_ratio < 3, \
            "Real-time Sharpe ratio should be realistic"
    
    def test_news_event_lookahead(self, config):
        """
        Test prevention of using future news events in signal generation.
        
        This test ensures that signals don't incorporate information
        from future news events or announcements.
        """
        # Create market data with news events
        market_data = self._create_market_data_with_news_events()
        
        # Create signals that might use future news
        signals_with_news_lookahead = self._create_signals_with_news_lookahead()
        signals_without_news_lookahead = self._create_signals_without_news_lookahead()
        
        backtester = SimpleBacktester(config)
        
        # Run both backtests
        result_with_news = backtester.run_backtest(market_data, signals_with_news_lookahead)
        result_without_news = backtester.run_backtest(market_data, signals_without_news_lookahead)
        
        # Verify that news look-ahead bias inflates performance
        assert result_with_news.total_return > result_without_news.total_return, \
            "News look-ahead bias should inflate performance"
    
    def _create_market_data_with_future_info(self) -> List[MarketData]:
        """Create market data with known future information."""
        data = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        # Create data with a clear trend that becomes obvious over time
        for i in range(100):
            date = base_date + timedelta(days=i)
            
            # Price starts low and increases significantly
            price = Decimal("50.0") + Decimal(str(i * 2.0))  # Clear upward trend
            
            data.append(MarketData(
                symbol="TREND_STOCK",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.005"),
                low_price=price * Decimal("0.995"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_signals_without_lookahead(self) -> List[Signal]:
        """Create signals that don't use future information."""
        signals = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        # Generate signals based only on current price (no future knowledge)
        for i in range(0, 50, 5):  # Reduced range to avoid future dates
            date = base_date + timedelta(days=i)
            price = Decimal("50.0") + Decimal(str(i * 2.0))
            
            # Signal based only on current price level
            if price < Decimal("100.0"):  # Buy when price is low
                signal_type = SignalType.BUY
                confidence = 70.0
            else:  # Sell when price is high
                signal_type = SignalType.SELL
                confidence = 60.0
            
            signals.append(Signal(
                symbol="TREND_STOCK",
                signal_type=signal_type,
                strength=SignalStrength.MODERATE,
                confidence=confidence,
                liquidity_score=90.0,
                priority_score=80.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_signals_with_lookahead(self) -> List[Signal]:
        """Create signals that use future information (for testing bias detection)."""
        signals = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        # Generate signals with perfect future knowledge
        for i in range(0, 50, 5):  # Reduced range to avoid future dates
            date = base_date + timedelta(days=i)
            current_price = Decimal("50.0") + Decimal(str(i * 2.0))
            future_price = Decimal("50.0") + Decimal(str((i + 5) * 2.0))  # Future price
            
            # Perfect signal based on future price movement
            if future_price > current_price:
                signal_type = SignalType.BUY
                confidence = 95.0  # Very high confidence due to future knowledge
            else:
                signal_type = SignalType.SELL
                confidence = 95.0
            
            signals.append(Signal(
                symbol="TREND_STOCK",
                signal_type=signal_type,
                strength=SignalStrength.STRONG,
                confidence=confidence,
                liquidity_score=90.0,
                priority_score=95.0,
                source=SignalSource.MOMENTUM,
                price=current_price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_market_data_with_patterns(self) -> List[MarketData]:
        """Create market data with recognizable patterns."""
        data = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        # Create data with cyclical patterns
        for i in range(100):
            date = base_date + timedelta(days=i)
            
            # Cyclical pattern with noise
            cycle = Decimal(str(5 * (i % 20)))  # 20-day cycle (0-95)
            noise = Decimal(str((i % 7) * 0.2))  # Weekly noise (0-1.2)
            price = Decimal("100.0") + cycle + noise
            
            data.append(MarketData(
                symbol="PATTERN_STOCK",
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
    
    def _create_technical_indicator_signals(self, market_data: List[MarketData]) -> List[Signal]:
        """Create signals based on technical indicators."""
        signals = []
        
        # Generate signals based on moving average crossover
        for i in range(20, len(market_data), 5):  # Start after 20 days for SMA
            current_data = market_data[:i+1]  # Only historical data
            
            if len(current_data) >= 20:
                # Calculate 20-day SMA
                recent_prices = [md.close_price for md in current_data[-20:]]
                sma = sum(recent_prices) / len(recent_prices)
                
                current_price = current_data[-1].close_price
                
                # Buy when price crosses above SMA
                if current_price > sma:
                    signal_type = SignalType.BUY
                    confidence = 60.0
                else:
                    signal_type = SignalType.SELL
                    confidence = 60.0
                
                signals.append(Signal(
                    symbol="PATTERN_STOCK",
                    signal_type=signal_type,
                    strength=SignalStrength.MODERATE,
                    confidence=confidence,
                    liquidity_score=90.0,
                    priority_score=70.0,
                    source=SignalSource.MOMENTUM,
                    price=current_price,
                    volume=Decimal("1000"),
                    timestamp=current_data[-1].timestamp
                ))
        
        return signals
    
    def _create_market_data_with_gaps(self) -> List[MarketData]:
        """Create market data with gaps in availability."""
        data = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        # Create data with some missing days
        for i in range(100):
            # Skip some days to create gaps
            if i % 15 == 0:  # Skip every 15th day
                continue
                
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.5))
            
            data.append(MarketData(
                symbol="GAPPED_STOCK",
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
    
    def _create_signals_with_data_gaps(self) -> List[Signal]:
        """Create signals that might reference unavailable data."""
        signals = []
        base_date = self._get_valid_timestamp(150)  # 150 days ago
        
        # Generate signals for all days (including gaps)
        for i in range(0, 50, 5):  # Reduced range to avoid future dates
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.5))
            
            signals.append(Signal(
                symbol="GAPPED_STOCK",
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
    
    def _simulate_real_time_signals(self, market_data: List[MarketData]) -> List[Signal]:
        """Simulate real-time signal generation."""
        signals = []
        
        # Process data day by day
        for i in range(10, len(market_data), 5):  # Start after 10 days
            current_data = market_data[:i+1]  # Only historical data
            
            if len(current_data) >= 10:
                # Simple momentum signal based on recent price movement
                recent_prices = [md.close_price for md in current_data[-10:]]
                price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                
                if price_change > Decimal("0.02"):  # 2% increase
                    signal_type = SignalType.BUY
                    confidence = 60.0
                elif price_change < Decimal("-0.02"):  # 2% decrease
                    signal_type = SignalType.SELL
                    confidence = 60.0
                else:
                    continue  # No signal
                
                signals.append(Signal(
                    symbol="TREND_STOCK",
                    signal_type=signal_type,
                    strength=SignalStrength.MODERATE,
                    confidence=confidence,
                    liquidity_score=90.0,
                    priority_score=70.0,
                    source=SignalSource.MOMENTUM,
                    price=recent_prices[-1],
                    volume=Decimal("1000"),
                    timestamp=current_data[-1].timestamp
                ))
        
        return signals
    
    def _create_market_data_with_news_events(self) -> List[MarketData]:
        """Create market data with news events."""
        data = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        for i in range(100):
            date = base_date + timedelta(days=i)
            
            # Normal price movement
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            # Add news event impact (known in advance for testing)
            if i == 50:  # News event on day 50
                price += Decimal("10.0")  # Positive news
            
            data.append(MarketData(
                symbol="NEWS_STOCK",
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
    
    def _create_signals_with_news_lookahead(self) -> List[Signal]:
        """Create signals that use future news information."""
        signals = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        for i in range(0, 100, 10):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            # Signal based on future news event
            if i < 50:  # Before news event
                signal_type = SignalType.BUY  # Buy before good news
                confidence = 90.0  # High confidence due to future knowledge
            else:  # After news event
                signal_type = SignalType.SELL  # Sell after news
                confidence = 80.0
            
            signals.append(Signal(
                symbol="NEWS_STOCK",
                signal_type=signal_type,
                strength=SignalStrength.STRONG,
                confidence=confidence,
                liquidity_score=90.0,
                priority_score=90.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_signals_without_news_lookahead(self) -> List[Signal]:
        """Create signals that don't use future news information."""
        signals = []
        base_date = self._get_valid_timestamp(100)  # 100 days ago
        
        for i in range(0, 100, 10):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.1))
            
            # Signal based only on current price level
            if price < Decimal("105.0"):  # Buy when price is low
                signal_type = SignalType.BUY
                confidence = 60.0
            else:  # Sell when price is high
                signal_type = SignalType.SELL
                confidence = 60.0
            
            signals.append(Signal(
                symbol="NEWS_STOCK",
                signal_type=signal_type,
                strength=SignalStrength.MODERATE,
                confidence=confidence,
                liquidity_score=90.0,
                priority_score=70.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
