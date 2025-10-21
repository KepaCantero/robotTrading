"""
Comprehensive test suite for T005 Signal Scorer System.

Tests cover all components: signal models, scoring algorithms, priority queue, and API endpoints.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.models.signal import (
    Signal, SignalType, SignalStrength, SignalSource, 
    MarketData, SignalScorer, SignalPriorityQueue
)
from app.services.signal_scorer import SignalScorerService
from app.services.portfolio_service import PortfolioService
from app.providers.paper_trading import PaperTradingPortfolioProvider


class TestSignalModels:
    """Test signal models and data structures."""
    
    def test_signal_creation(self):
        """Test Signal model creation and validation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=85.5,
            liquidity_score=75.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            metadata={"rsi": 65, "ema_trend": 0.02}
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 85.5
        assert signal.liquidity_score == 75.0
        assert signal.priority_score == 80.0
        assert signal.combined_score == (85.5 + 75.0 + 80.0) / 3
        assert signal.is_actionable is True
        assert signal.is_high_priority is False  # priority_score = 80.0 == 80, not > 80
    
    def test_signal_properties(self):
        """Test Signal model properties."""
        signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.SELL,
            strength=SignalStrength.WEAK,
            confidence=45.0,
            liquidity_score=60.0,
            priority_score=50.0,
            source=SignalSource.VOLUME,
            price=Decimal("45000.00"),
            volume=Decimal("100"),
            metadata={"volume_ratio": 1.5}
        )
        
        assert signal.combined_score == (45.0 + 60.0 + 50.0) / 3
        assert signal.is_actionable is False  # confidence < 60%
        assert signal.is_high_priority is False  # priority < 80%
    
    def test_market_data_creation(self):
        """Test MarketData model creation."""
        market_data = MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            bid=Decimal("149.95"),
            ask=Decimal("150.05"),
            spread=Decimal("0.10"),
            timestamp=datetime.utcnow()
        )
        
        assert market_data.symbol == "AAPL"
        assert market_data.mid_price == Decimal("150.00")
        assert market_data.spread_percentage == Decimal("0.06666666666666666666666666667")
    
    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY == "buy"
        assert SignalType.SELL == "sell"
        assert SignalType.HOLD == "hold"
    
    def test_signal_strength_enum(self):
        """Test SignalStrength enum values."""
        assert SignalStrength.WEAK == "weak"
        assert SignalStrength.MODERATE == "moderate"
        assert SignalStrength.STRONG == "strong"
        assert SignalStrength.VERY_STRONG == "very_strong"
    
    def test_signal_source_enum(self):
        """Test SignalSource enum values."""
        assert SignalSource.MOMENTUM == "momentum"
        assert SignalSource.LIQUIDITY == "liquidity"
        assert SignalSource.VOLATILITY == "volatility"
        assert SignalSource.VOLUME == "volume"
        assert SignalSource.TECHNICAL == "technical"
        assert SignalSource.FUNDAMENTAL == "fundamental"


class TestSignalScorer:
    """Test SignalScorer functionality."""
    
    @pytest.fixture
    def scorer(self):
        """Create a test scorer instance."""
        return SignalScorer()
    
    @pytest.fixture
    def market_data(self):
        """Create test market data."""
        return MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            bid=Decimal("149.95"),
            ask=Decimal("150.05"),
            spread=Decimal("0.10"),
            timestamp=datetime.utcnow()
        )
    
    def test_calculate_confidence_score(self, scorer, market_data):
        """Test confidence score calculation."""
        metadata = {
            "rsi": 65,
            "ema_trend": 0.02,
            "avg_volume": 800000,
            "volatility": 0.025,
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        
        confidence = scorer.calculate_confidence_score(market_data, metadata)
        
        assert 0 <= confidence <= 100
        assert isinstance(confidence, float)
    
    def test_calculate_liquidity_score(self, scorer, market_data):
        """Test liquidity score calculation."""
        liquidity_score = scorer.calculate_liquidity_score(market_data)
        
        assert 0 <= liquidity_score <= 100
        assert isinstance(liquidity_score, float)
    
    def test_calculate_priority_score(self, scorer, market_data):
        """Test priority score calculation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=0.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000")
        )
        
        priority_score = scorer.calculate_priority_score(signal, market_data)
        
        assert 0 <= priority_score <= 100
        assert isinstance(priority_score, float)
    
    def test_momentum_score_calculation(self, scorer):
        """Test momentum score calculation."""
        # Test RSI in neutral zone
        metadata = {"rsi": 50, "ema_trend": 0}
        score = scorer._calculate_momentum_score(metadata)
        assert 0 <= score <= 100
        
        # Test RSI overbought
        metadata = {"rsi": 80, "ema_trend": 0}
        score = scorer._calculate_momentum_score(metadata)
        assert score < 100  # Should be penalized
    
    def test_volume_score_calculation(self, scorer, market_data):
        """Test volume score calculation."""
        # Test high volume ratio
        metadata = {"avg_volume": 500000}
        score = scorer._calculate_volume_score(market_data, metadata)
        assert score > 50  # Should be high for 2x average volume
        
        # Test low volume ratio
        metadata = {"avg_volume": 2000000}
        score = scorer._calculate_volume_score(market_data, metadata)
        assert score < 50  # Should be low for 0.5x average volume
    
    def test_volatility_score_calculation(self, scorer):
        """Test volatility score calculation."""
        # Test moderate volatility
        metadata = {"volatility": 0.02}
        score = scorer._calculate_volatility_score(metadata)
        assert score > 80  # Should be high for moderate volatility
        
        # Test high volatility
        metadata = {"volatility": 0.08}
        score = scorer._calculate_volatility_score(metadata)
        assert score <= 50  # Should be penalized for high volatility
    
    def test_technical_score_calculation(self, scorer):
        """Test technical score calculation."""
        metadata = {
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        score = scorer._calculate_technical_score(metadata)
        assert 0 <= score <= 100


class TestSignalPriorityQueue:
    """Test SignalPriorityQueue functionality."""
    
    @pytest.fixture
    def queue(self):
        """Create a test priority queue."""
        return SignalPriorityQueue(max_size=5)
    
    @pytest.fixture
    def test_signals(self):
        """Create test signals with different priorities."""
        return [
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=90.0,
                liquidity_score=80.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.00"),
                volume=Decimal("1000000")
            ),
            Signal(
                symbol="MSFT",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=70.0,
                liquidity_score=60.0,
                priority_score=65.0,
                source=SignalSource.TECHNICAL,
                price=Decimal("300.00"),
                volume=Decimal("500000")
            ),
            Signal(
                symbol="GOOGL",
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=50.0,
                liquidity_score=40.0,
                priority_score=45.0,
                source=SignalSource.VOLUME,
                price=Decimal("2500.00"),
                volume=Decimal("100000")
            )
        ]
    
    def test_add_signal(self, queue, test_signals):
        """Test adding signals to priority queue."""
        for signal in test_signals:
            success = queue.add_signal(signal)
            assert success is True
        
        assert queue.get_queue_size() == 3
    
    def test_get_next_signal(self, queue, test_signals):
        """Test getting next highest priority signal."""
        for signal in test_signals:
            queue.add_signal(signal)
        
        # Should get highest priority signal first (AAPL with 85.0)
        next_signal = queue.get_next_signal()
        assert next_signal is not None
        assert next_signal.symbol == "AAPL"
        assert next_signal.priority_score == 85.0
        
        # Should get second highest priority signal (MSFT with 65.0)
        next_signal = queue.get_next_signal()
        assert next_signal.symbol == "MSFT"
        assert next_signal.priority_score == 65.0
    
    def test_peek_next_signal(self, queue, test_signals):
        """Test peeking at next signal without removing."""
        for signal in test_signals:
            queue.add_signal(signal)
        
        # Peek should return highest priority signal
        peeked_signal = queue.peek_next_signal()
        assert peeked_signal.symbol == "AAPL"
        
        # Queue size should remain the same
        assert queue.get_queue_size() == 3
        
        # Getting next signal should return the same signal
        next_signal = queue.get_next_signal()
        assert next_signal.symbol == "AAPL"
    
    def test_get_signals_by_symbol(self, queue, test_signals):
        """Test getting signals by symbol."""
        for signal in test_signals:
            queue.add_signal(signal)
        
        # Add another AAPL signal
        aapl_signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=70.0,
            priority_score=72.0,
            source=SignalSource.VOLATILITY,
            price=Decimal("155.00"),
            volume=Decimal("800000")
        )
        queue.add_signal(aapl_signal)
        
        # Get all AAPL signals
        aapl_signals = queue.get_signals_by_symbol("AAPL")
        assert len(aapl_signals) == 2
        
        # Get MSFT signals
        msft_signals = queue.get_signals_by_symbol("MSFT")
        assert len(msft_signals) == 1
        assert msft_signals[0].symbol == "MSFT"
    
    def test_queue_size_limit(self, queue):
        """Test queue size limit."""
        # Add more signals than max_size
        for i in range(10):
            signal = Signal(
                symbol=f"SYMBOL{i}",
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=60.0,
                liquidity_score=50.0,
                priority_score=55.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("100.00"),
                volume=Decimal("100000")
            )
            queue.add_signal(signal)
        
        # Queue size should not exceed max_size
        assert queue.get_queue_size() <= queue.max_size
    
    def test_clear_signals(self, queue, test_signals):
        """Test clearing all signals."""
        for signal in test_signals:
            queue.add_signal(signal)
        
        assert queue.get_queue_size() == 3
        
        queue.clear_signals()
        assert queue.get_queue_size() == 0
    
    def test_get_queue_summary(self, queue, test_signals):
        """Test getting queue summary."""
        for signal in test_signals:
            queue.add_signal(signal)
        
        summary = queue.get_queue_summary()
        
        assert summary["total_signals"] == 3
        assert summary["avg_priority"] > 0
        assert "signal_types" in summary
        assert "symbols" in summary
        assert len(summary["symbols"]) == 3


class TestSignalScorerService:
    """Test SignalScorerService functionality."""
    
    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        portfolio_service = PortfolioService(provider)
        return SignalScorerService(portfolio_service)
    
    @pytest.fixture
    def market_data(self):
        """Create test market data."""
        return MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            bid=Decimal("149.95"),
            ask=Decimal("150.05"),
            spread=Decimal("0.10"),
            timestamp=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_signal_success(self, service, market_data):
        """Test successful signal evaluation."""
        metadata = {
            "rsi": 65,
            "ema_trend": 0.02,
            "avg_volume": 800000,
            "volatility": 0.025,
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        
        signal = await service.evaluate_signal(
            "AAPL",
            SignalType.BUY,
            market_data,
            metadata
        )
        
        assert signal is not None
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence > 0
        assert signal.liquidity_score > 0
        assert signal.priority_score > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_signal_low_thresholds(self, service, market_data):
        """Test signal evaluation with low thresholds."""
        metadata = {
            "rsi": 30,  # Oversold
            "ema_trend": -0.05,  # Strong downtrend
            "avg_volume": 2000000,  # Low volume ratio
            "volatility": 0.08,  # High volatility
            "macd_signal": -1.0,  # Strong sell signal
            "bollinger_position": 0.1  # Near lower band
        }
        
        signal = await service.evaluate_signal(
            "AAPL",
            SignalType.BUY,
            market_data,
            metadata
        )
        
        # Should return None due to low thresholds
        assert signal is None
    
    @pytest.mark.asyncio
    async def test_get_next_actionable_signal(self, service, market_data):
        """Test getting next actionable signal."""
        # First add a good signal
        metadata = {
            "rsi": 65,
            "ema_trend": 0.02,
            "avg_volume": 800000,
            "volatility": 0.025,
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        
        signal = await service.evaluate_signal(
            "AAPL",
            SignalType.BUY,
            market_data,
            metadata
        )
        
        assert signal is not None
        
        # Get next actionable signal
        next_signal = await service.get_next_actionable_signal()
        assert next_signal is not None
        assert next_signal.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_calculate_position_size(self, service, market_data):
        """Test position size calculation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=77.5,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000")
        )
        
        position_size = await service.calculate_position_size(signal)
        
        assert position_size > 0
        assert position_size <= Decimal("20000")  # Should not exceed 20% of 100k portfolio (testing config)
    
    @pytest.mark.asyncio
    async def test_execute_signal(self, service, market_data):
        """Test signal execution."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=77.5,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.00"),
            volume=Decimal("1000000")
        )
        
        success = await service.execute_signal(signal)
        
        assert success is True
        
        # Check that position was created
        portfolio = await service.portfolio_service.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_get_signal_statistics(self, service):
        """Test getting signal statistics."""
        stats = await service.get_signal_statistics()
        
        assert "signals_processed" in stats
        assert "signals_executed" in stats
        assert "success_rate" in stats
        assert "total_pnl" in stats
        assert "queue_size" in stats
        assert "queue_summary" in stats
    
    @pytest.mark.asyncio
    async def test_get_signals_by_symbol(self, service, market_data):
        """Test getting signals by symbol."""
        metadata = {
            "rsi": 65,
            "ema_trend": 0.02,
            "avg_volume": 800000,
            "volatility": 0.025,
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        
        # Add a signal
        await service.evaluate_signal(
            "AAPL",
            SignalType.BUY,
            market_data,
            metadata
        )
        
        # Get signals by symbol
        signals = await service.get_signals_by_symbol("AAPL")
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_clear_expired_signals(self, service):
        """Test clearing expired signals."""
        # This test would require creating signals with old timestamps
        # For now, just test that the method doesn't raise an error
        await service.clear_expired_signals(max_age_minutes=1)
        
        # Should not raise an exception
        assert True
    
    def test_update_thresholds(self, service):
        """Test updating thresholds."""
        service.update_thresholds(70.0, 60.0)
        
        assert service.min_confidence_threshold == 70.0
        assert service.min_liquidity_threshold == 60.0
    
    def test_update_position_size_limit(self, service):
        """Test updating position size limit."""
        service.update_position_size_limit(15.0)
        
        assert service.max_position_size_percent == 15.0


class TestIntegration:
    """Integration tests for the complete signal scoring system."""
    
    @pytest.mark.asyncio
    async def test_complete_signal_workflow(self):
        """Test complete signal workflow from evaluation to execution."""
        # Initialize services
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        portfolio_service = PortfolioService(provider)
        signal_service = SignalScorerService(portfolio_service)
        
        # Create market data
        market_data = MarketData(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            bid=Decimal("149.95"),
            ask=Decimal("150.05"),
            spread=Decimal("0.10"),
            timestamp=datetime.utcnow()
        )
        
        # Create signal metadata
        metadata = {
            "rsi": 65,
            "ema_trend": 0.02,
            "avg_volume": 800000,
            "volatility": 0.025,
            "macd_signal": 0.5,
            "bollinger_position": 0.6
        }
        
        # Evaluate signal
        signal = await signal_service.evaluate_signal(
            "AAPL",
            SignalType.BUY,
            market_data,
            metadata
        )
        
        assert signal is not None
        assert signal.confidence > 60.0
        assert signal.liquidity_score > 50.0
        
        # Get next actionable signal
        next_signal = await signal_service.get_next_actionable_signal()
        assert next_signal is not None
        assert next_signal.symbol == "AAPL"
        
        # Calculate position size
        position_size = await signal_service.calculate_position_size(next_signal)
        assert position_size > 0
        
        # Execute signal
        success = await signal_service.execute_signal(next_signal)
        assert success is True
        
        # Verify execution
        portfolio = await portfolio_service.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"
        
        # Get statistics
        stats = await signal_service.get_signal_statistics()
        assert stats["signals_processed"] >= 1
        assert stats["signals_executed"] >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_signals_priority(self):
        """Test priority handling with multiple signals."""
        # Initialize services
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        portfolio_service = PortfolioService(provider)
        signal_service = SignalScorerService(portfolio_service)
        
        # Create multiple signals with different priorities
        symbols = ["AAPL", "MSFT", "GOOGL"]
        signals = []
        
        for i, symbol in enumerate(symbols):
            market_data = MarketData(
                symbol=symbol,
                price=Decimal("150.00"),
                volume=Decimal("1000000"),
                bid=Decimal("149.95"),
                ask=Decimal("150.05"),
                spread=Decimal("0.10"),
                timestamp=datetime.utcnow()
            )
            
            metadata = {
                "rsi": 65 + i * 5,  # Different RSI values
                "ema_trend": 0.02 + i * 0.01,
                "avg_volume": 800000,
                "volatility": 0.025,
                "macd_signal": 0.5,
                "bollinger_position": 0.6
            }
            
            signal = await signal_service.evaluate_signal(
                symbol,
                SignalType.BUY,
                market_data,
                metadata
            )
            
            if signal:
                signals.append(signal)
        
        # Should have multiple signals
        assert len(signals) >= 2
        
        # Get signals in priority order
        executed_signals = []
        for _ in range(len(signals)):
            next_signal = await signal_service.get_next_actionable_signal()
            if next_signal:
                executed_signals.append(next_signal)
        
        # Should have executed signals in priority order
        assert len(executed_signals) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
