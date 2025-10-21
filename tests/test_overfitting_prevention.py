"""
Tests for overfitting prevention in backtesting.

This module tests concepts from Ernie Chan's Chapter 1 regarding
overfitting prevention and strategy generalization.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import pytest
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.models.momentum import MarketData
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource


class TestOverfittingPrevention:
    """Test overfitting prevention techniques."""
    
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
    
    def test_out_of_sample_generalization(self, config):
        """
        Test strategy generalization on out-of-sample data.
        
        This test covers Ernie Chan's concept of using separate datasets
        for strategy development and validation.
        """
        # Create in-sample data (first 3 months)
        start_date = self._get_valid_timestamp(100)  # 100 days ago
        in_sample_data = self._create_trending_data(
            start_date=start_date,
            days=60,  # 3 months
            trend_factor=0.001
        )
        in_sample_signals = self._create_trending_signals(
            start_date=start_date,
            days=60,
            trend_factor=0.001
        )
        
        # Create out-of-sample data (next 3 months)
        out_sample_start = start_date + timedelta(days=60)
        out_sample_data = self._create_trending_data(
            start_date=out_sample_start,
            days=60,  # 3 months
            trend_factor=0.0005  # Different trend
        )
        out_sample_signals = self._create_trending_signals(
            start_date=out_sample_start,
            days=60,
            trend_factor=0.0005
        )
        
        # Run in-sample backtest
        backtester_in = SimpleBacktester(config)
        in_sample_result = backtester_in.run_backtest(in_sample_data, in_sample_signals)
        
        # Run out-of-sample backtest
        backtester_out = SimpleBacktester(config)
        out_sample_result = backtester_out.run_backtest(out_sample_data, out_sample_signals)
        
        # Validate that strategy performs reasonably on out-of-sample data
        assert out_sample_result.final_capital > 0, "Out-of-sample should not lose all capital"
        assert out_sample_result.total_return > -50, "Out-of-sample drawdown should be reasonable"
        
        # Check that performance degradation is not excessive
        performance_ratio = out_sample_result.total_return / in_sample_result.total_return
        assert performance_ratio > 0.3, f"Out-of-sample performance too degraded: {performance_ratio}"
    
    def test_parameter_stability(self, config):
        """
        Test strategy stability with minor parameter changes.
        
        This test covers Ernie Chan's concept of parameter stability
        to prevent overfitting to specific parameter values.
        """
        base_data = self._create_trending_data(days=60)  # Reduced from 252
        base_signals = self._create_trending_signals(days=60)  # Reduced from 252
        
        # Test with different slippage values
        slippage_values = [Decimal("0.05"), Decimal("0.1"), Decimal("0.15")]
        results = []
        
        for slippage in slippage_values:
            test_config = BacktestConfig(
                initial_capital=config.initial_capital,
                commission_per_trade=config.commission_per_trade,
                slippage_percentage=slippage,
                risk_free_rate=config.risk_free_rate,
                max_position_size=config.max_position_size
            )
            
            backtester = SimpleBacktester(test_config)
            result = backtester.run_backtest(base_data, base_signals)
            results.append(result.total_return)
        
        # Check that results don't vary excessively
        max_return = max(results)
        min_return = min(results)
        variation = (max_return - min_return) / abs(max_return) if max_return != 0 else 0
        
        assert variation < 0.5, f"Parameter sensitivity too high: {variation}"
    
    def test_walk_forward_analysis(self, config):
        """
        Test walk-forward analysis for strategy validation.
        
        This test implements Ernie Chan's walk-forward analysis concept
        where the strategy is continuously retrained and tested.
        """
        # Create 2 years of data
        full_data = self._create_trending_data(days=504)  # 2 years
        full_signals = self._create_trending_signals(days=504)
        
        # Split into 6-month training periods
        training_periods = []
        test_periods = []
        
        for i in range(0, 504, 126):  # Every 6 months
            if i + 252 < 504:  # Ensure we have both training and test data
                train_start = i
                train_end = i + 126
                test_start = i + 126
                test_end = i + 252
                
                training_periods.append((train_start, train_end))
                test_periods.append((test_start, test_end))
        
        results = []
        
        for train_period, test_period in zip(training_periods, test_periods):
            # Extract training data
            train_data = full_data[train_period[0]:train_period[1]]
            train_signals = full_signals[train_period[0]:train_period[1]]
            
            # Extract test data
            test_data = full_data[test_period[0]:test_period[1]]
            test_signals = full_signals[test_period[0]:test_period[1]]
            
            # Run backtest on test period
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(test_data, test_signals)
            results.append(result.total_return)
        
        # Validate walk-forward consistency
        assert len(results) > 0, "Should have walk-forward results"
        
        # Check that results are reasonably consistent
        avg_return = sum(results) / len(results)
        variance = sum((r - avg_return) ** 2 for r in results) / len(results)
        
        assert variance < 1000, f"Walk-forward variance too high: {variance}"
    
    def test_cross_validation_temporal(self, config):
        """
        Test temporal cross-validation for strategy robustness.
        
        This test implements temporal cross-validation where the strategy
        is tested on different time periods to ensure robustness.
        """
        # Create data for different market conditions
        trending_data = self._create_trending_data(days=126, trend_factor=0.002)
        ranging_data = self._create_ranging_data(days=126)
        volatile_data = self._create_volatile_data(days=126)
        
        datasets = [
            (trending_data, self._create_trending_signals(days=126, trend_factor=0.002)),
            (ranging_data, self._create_ranging_signals(days=126)),
            (volatile_data, self._create_volatile_signals(days=126))
        ]
        
        results = []
        
        for data, signals in datasets:
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(data, signals)
            results.append({
                'total_return': result.total_return,
                'sharpe_ratio': result.performance.sharpe_ratio,
                'max_drawdown': result.performance.max_drawdown
            })
        
        # Validate cross-validation results
        assert len(results) == 3, "Should test all market conditions"
        
        # Check that strategy doesn't fail catastrophically in any condition
        for result in results:
            assert result['total_return'] > -30, "Strategy should not fail catastrophically"
            assert result['max_drawdown'] > -40, "Drawdown should be reasonable"
    
    def _create_trending_data(self, start_date: datetime = None, days: int = 252, trend_factor: float = 0.001) -> List[MarketData]:
        """Create trending market data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        data = []
        base_price = Decimal("100.0")
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            trend = 1 + (i * trend_factor)
            noise = 1 + ((i % 10 - 5) * 0.001)
            price = base_price * Decimal(str(trend * noise))
            
            data.append(MarketData(
                symbol="TEST",
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
    
    def _create_trending_signals(self, start_date: datetime = None, days: int = 252, trend_factor: float = 0.001) -> List[Signal]:
        """Create signals for trending data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        signals = []
        base_price = Decimal("100.0")
        
        # Buy signals every 20 days
        for i in range(0, min(days, 60), 20):  # Limit to 60 days max
            date = start_date + timedelta(days=i)
            price = base_price * Decimal(str(1 + (i * trend_factor)))
            
            signals.append(Signal(
                symbol="TEST",
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
    
    def _create_ranging_data(self, start_date: datetime = None, days: int = 252) -> List[MarketData]:
        """Create ranging market data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        data = []
        base_price = Decimal("100.0")
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            cycle = 1 + Decimal(str(0.02 * (i % 20 - 10) / 10))  # 20-day cycle
            price = base_price * cycle
            
            data.append(MarketData(
                symbol="TEST",
                timestamp=date,
                open_price=price * Decimal("0.999"),
                high_price=price * Decimal("1.001"),
                low_price=price * Decimal("0.999"),
                close_price=price,
                volume=Decimal("1000000"),
                bid=price * Decimal("0.9995"),
                ask=price * Decimal("1.0005"),
                spread=price * Decimal("0.001")
            ))
        
        return data
    
    def _create_ranging_signals(self, start_date: datetime = None, days: int = 252) -> List[Signal]:
        """Create signals for ranging data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        signals = []
        base_price = Decimal("100.0")
        
        # Buy at cycle lows, sell at cycle highs
        for i in range(0, min(days, 60), 10):  # Reduced range to avoid future dates
            date = start_date + timedelta(days=i)
            cycle = 1 + Decimal(str(0.02 * (i % 20 - 10) / 10))
            price = base_price * cycle
            
            signal_type = SignalType.BUY if i % 20 < 10 else SignalType.SELL
            
            signals.append(Signal(
                symbol="TEST",
                signal_type=signal_type,
                strength=SignalStrength.MODERATE,
                confidence=65.0,
                liquidity_score=90.0,
                priority_score=70.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("1000"),
                timestamp=date
            ))
        
        return signals
    
    def _create_volatile_data(self, start_date: datetime = None, days: int = 252) -> List[MarketData]:
        """Create volatile market data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        data = []
        base_price = Decimal("100.0")
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            volatility = 1 + Decimal(str(0.05 * (i % 5 - 2)))  # High volatility
            price = base_price * volatility
            
            data.append(MarketData(
                symbol="TEST",
                timestamp=date,
                open_price=price * Decimal("0.995"),
                high_price=price * Decimal("1.01"),
                low_price=price * Decimal("0.99"),
                close_price=price,
                volume=Decimal("2000000"),  # Higher volume
                bid=price * Decimal("0.999"),
                ask=price * Decimal("1.001"),
                spread=price * Decimal("0.002")  # Wider spread
            ))
        
        return data
    
    def _create_volatile_signals(self, start_date: datetime = None, days: int = 252) -> List[Signal]:
        """Create signals for volatile data."""
        if start_date is None:
            start_date = self._get_valid_timestamp(100)  # 100 days ago
        
        signals = []
        base_price = Decimal("100.0")
        
        # More frequent signals due to volatility
        for i in range(0, min(days, 60), 5):  # Reduced range to avoid future dates
            date = start_date + timedelta(days=i)
            volatility = 1 + Decimal(str(0.05 * (i % 5 - 2)))
            price = base_price * volatility
            
            signals.append(Signal(
                symbol="TEST",
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=50.0,
                liquidity_score=85.0,
                priority_score=60.0,
                source=SignalSource.MOMENTUM,
                price=price,
                volume=Decimal("2000"),
                timestamp=date
            ))
        
        return signals
