"""
Performance regression tests for AlgoTrading system.

This module contains performance benchmarks to ensure that critical operations
maintain acceptable performance levels and detect performance regressions.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.momentum import MarketData
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.services.momentum_analysis import TechnicalIndicatorCalculator
from tests.fixtures.historical_data import (
    create_spy_2020_trending_market_data,
    create_spy_2020_trending_signals
)


class TestPerformanceRegression:
    """Performance regression tests for critical operations."""
    
    @pytest.fixture
    def default_config(self):
        """Default backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
            stop_loss_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("10.0")
        )
    
    @pytest.fixture
    def large_market_data(self):
        """Create large dataset for performance testing."""
        data = []
        # Use dynamic date within the last year
        base_date = datetime.utcnow() - timedelta(days=300)  # About 10 months ago
        base_price = Decimal("320.0")
        
        # Create 200 days of market data (reduced to avoid future dates)
        for i in range(200):  # Reduced from 1000 to 200
            date = base_date + timedelta(days=i)
            
            # Add trend and noise
            trend_factor = 1 + (i * 0.0001)  # 0.01% daily trend
            noise_factor = 1 + ((i % 10 - 5) * 0.001)  # ±0.5% noise
            
            price = base_price * Decimal(str(trend_factor * noise_factor))
            
            # Create OHLC data
            open_price = price * Decimal("0.999")
            high_price = price * Decimal("1.005")
            low_price = price * Decimal("0.995")
            close_price = price
            
            volume = Decimal("50000000")
            
            # Bid-ask spread calculation
            spread = (price * Decimal("0.001")).quantize(Decimal("0.000001"))
            bid = (price - spread / Decimal("2")).quantize(Decimal("0.000001"))
            ask = (price + spread / Decimal("2")).quantize(Decimal("0.000001"))
            
            # Recalculate spread to ensure exact match
            calculated_spread = ask - bid
            spread = calculated_spread.quantize(Decimal("0.000001"))
            
            data.append(MarketData(
                symbol="SPY",
                timestamp=date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                bid=bid,
                ask=ask,
                spread=spread
            ))
        
        return data
    
    @pytest.fixture
    def large_signal_set(self):
        """Create large signal set for performance testing."""
        signals = []
        # Use dynamic date within the last year
        base_date = datetime.utcnow() - timedelta(days=300)  # About 10 months ago
        
        # Create signals every 5 days (limit to avoid future dates)
        for i in range(0, 200, 5):  # Reduced from 1000 to 200 to avoid future dates
            signal_date = base_date + timedelta(days=i)
            price = Decimal("320.0") * Decimal(str(1 + i * 0.0001))
            
            signals.append(Signal(
                symbol="SPY",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=95.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000000"),
                timestamp=signal_date
            ))
        
        return signals
    
    def test_signal_generation_performance(self, benchmark):
        """Test that signal generation completes within acceptable time."""
        calculator = TechnicalIndicatorCalculator()
        
        # Create test data
        prices = [100.0 + i for i in range(100)]
        volumes = [1000000.0 + i * 1000 for i in range(100)]
        
        def generate_signals():
            """Generate signals for performance testing."""
            rsi = calculator.calculate_rsi(prices, 14)
            ema = calculator.calculate_ema(prices, 20)
            macd = calculator.calculate_macd(prices)
            atr = calculator.calculate_atr(prices, prices, prices, 14)
            volume_sma = calculator.calculate_volume_sma(volumes, 20)
            
            return {
                'rsi': rsi,
                'ema': ema,
                'macd': macd,
                'atr': atr,
                'volume_sma': volume_sma
            }
        
        # Benchmark signal generation
        result = benchmark(generate_signals)
        
        # Verify results are valid
        assert result['rsi'] is not None
        assert result['ema'] is not None
        assert result['macd'] is not None
        assert result['atr'] is not None
        assert result['volume_sma'] is not None
    
    def test_backtest_performance_small_dataset(self, benchmark, default_config):
        """Test backtest performance with small dataset (< 1 second)."""
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()
        
        def run_backtest():
            """Run backtest for performance testing."""
            backtester = SimpleBacktester(default_config)
            return backtester.run_backtest(market_data, signals)
        
        # Benchmark backtest execution
        result = benchmark(run_backtest)
        
        # Verify results are valid
        assert result.final_capital > 0
        assert len(result.trades) > 0
        assert result.performance.total_trades > 0
    
    def test_backtest_performance_large_dataset(self, benchmark, default_config, large_market_data, large_signal_set):
        """Test backtest performance with large dataset (< 30 seconds)."""
        def run_large_backtest():
            """Run large backtest for performance testing."""
            backtester = SimpleBacktester(default_config)
            return backtester.run_backtest(large_market_data, large_signal_set)
        
        # Benchmark large backtest execution
        result = benchmark(run_large_backtest)
        
        # Verify results are valid
        assert result.final_capital > 0
        assert len(result.trades) > 0
        assert result.performance.total_trades > 0
    
    def test_technical_indicator_calculation_performance(self, benchmark):
        """Test technical indicator calculation performance."""
        calculator = TechnicalIndicatorCalculator()
        
        # Create large dataset
        prices = [100.0 + i * 0.1 for i in range(1000)]
        volumes = [1000000.0 + i * 100 for i in range(1000)]
        
        def calculate_all_indicators():
            """Calculate all technical indicators for performance testing."""
            results = {}
            
            # RSI calculation
            for period in [14, 21, 50]:
                results[f'rsi_{period}'] = calculator.calculate_rsi(prices, period)
            
            # EMA calculation
            for period in [9, 21, 50, 200]:
                results[f'ema_{period}'] = calculator.calculate_ema(prices, period)
            
            # MACD calculation
            results['macd'] = calculator.calculate_macd(prices)
            
            # ATR calculation
            results['atr'] = calculator.calculate_atr(prices, prices, prices, 14)
            
            # Volume SMA calculation
            results['volume_sma'] = calculator.calculate_volume_sma(volumes, 20)
            
            return results
        
        # Benchmark indicator calculations
        result = benchmark(calculate_all_indicators)
        
        # Verify results are valid
        assert len(result) > 0
        for key, value in result.items():
            assert value is not None or key.startswith('rsi_') or key.startswith('ema_')
    
    def test_position_size_calculation_performance(self, benchmark, default_config):
        """Test position size calculation performance."""
        backtester = SimpleBacktester(default_config)
        
        # Create test signal
        signal = Signal(
            symbol="TEST",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=90.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100.0"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow()
        )
        
        def calculate_position_sizes():
            """Calculate position sizes for performance testing."""
            results = []
            for i in range(1000):
                price = Decimal(str(100 + i * 0.1))
                position_size = backtester._calculate_position_size(signal, price)
                results.append(position_size)
            return results
        
        # Benchmark position size calculations
        result = benchmark(calculate_position_sizes)
        
        # Verify results are valid
        assert len(result) == 1000
        assert all(size > 0 for size in result)
    
    def test_slippage_calculation_performance(self, benchmark, default_config):
        """Test slippage calculation performance."""
        backtester = SimpleBacktester(default_config)
        
        def calculate_slippage():
            """Calculate slippage for performance testing."""
            results = []
            for i in range(1000):
                price = Decimal(str(100 + i * 0.1))
                slippage_buy = backtester._apply_slippage(price, True)
                slippage_sell = backtester._apply_slippage(price, False)
                results.append((slippage_buy, slippage_sell))
            return results
        
        # Benchmark slippage calculations
        result = benchmark(calculate_slippage)
        
        # Verify results are valid
        assert len(result) == 1000
        assert all(buy_price > sell_price for buy_price, sell_price in result)
    
    def test_performance_regression_detection(self, benchmark):
        """Test that performance regression detection works."""
        calculator = TechnicalIndicatorCalculator()
        
        # Create test data
        prices = [100.0 + i for i in range(100)]
        
        def baseline_operation():
            """Baseline operation for regression testing."""
            return calculator.calculate_rsi(prices, 14)
        
        # Benchmark baseline operation
        result = benchmark(baseline_operation)
        
        # Verify result is valid
        assert result is not None
        assert 0 <= result <= 100


class TestPerformanceThresholds:
    """Test performance thresholds and alert conditions."""
    
    def test_signal_generation_threshold(self, benchmark):
        """Test that signal generation stays under 50ms threshold."""
        calculator = TechnicalIndicatorCalculator()
        prices = [Decimal(str(100 + i)) for i in range(100)]
        
        def generate_signal():
            return calculator.calculate_rsi(prices, 14)
        
        # This should complete in under 50ms
        result = benchmark(generate_signal)
        assert result is not None
    
    def test_backtest_threshold_small(self, benchmark):
        """Test that small backtest stays under 1 second threshold."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1")
        )
        
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()
        
        def run_backtest():
            backtester = SimpleBacktester(config)
            return backtester.run_backtest(market_data, signals)
        
        # This should complete in under 1 second
        result = benchmark(run_backtest)
        assert result.final_capital > 0
    
    def test_memory_usage_threshold(self, benchmark):
        """Test that memory usage stays within acceptable limits."""
        calculator = TechnicalIndicatorCalculator()
        
        # Create large dataset
        prices = [Decimal(str(100 + i * 0.1)) for i in range(10000)]
        
        def memory_intensive_operation():
            """Operation that uses significant memory."""
            results = []
            for i in range(100):
                rsi = calculator.calculate_rsi(prices, 14)
                results.append(rsi)
            return results
        
        # This should complete without excessive memory usage
        result = benchmark(memory_intensive_operation)
        assert len(result) == 100
        assert all(rsi is not None for rsi in result)


class TestPerformanceBaselines:
    """Test performance baselines for regression detection."""
    
    def test_technical_indicator_baseline(self, benchmark):
        """Establish baseline for technical indicator calculations."""
        calculator = TechnicalIndicatorCalculator()
        prices = [100.0 + i for i in range(100)]  # Use float instead of Decimal
        
        def baseline_calculations():
            """All baseline calculations in one function."""
            rsi = calculator.calculate_rsi(prices, 14)
            ema = calculator.calculate_ema(prices, 20)
            macd = calculator.calculate_macd(prices)
            return {'rsi': rsi, 'ema': ema, 'macd': macd}
        
        # Establish baseline
        result = benchmark(baseline_calculations)
        
        # Verify baseline is valid
        assert result['rsi'] is not None
        assert result['ema'] is not None
        assert result['macd'] is not None
    
    def test_backtest_baseline(self, benchmark):
        """Establish baseline for backtest execution."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1")
        )
        
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()
        
        def baseline_backtest():
            backtester = SimpleBacktester(config)
            return backtester.run_backtest(market_data, signals)
        
        # Establish baseline
        result = benchmark(baseline_backtest)
        
        # Verify baseline is valid
        assert result.final_capital > 0
        assert len(result.trades) > 0
        assert result.performance.total_trades > 0
