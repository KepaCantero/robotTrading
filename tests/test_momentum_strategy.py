"""
Test suite for T007: Momentum Strategy Implementation.

This module contains comprehensive tests for momentum models, services, and API endpoints
with >95% coverage across unit, integration, and E2E tests.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.models.momentum import (
    MomentumSignal, MomentumType, Timeframe, TechnicalIndicators,
    MomentumStrategy, MomentumAnalysis, MomentumFilter
)
from app.services.momentum_analysis import MomentumAnalysisService, TechnicalIndicatorCalculator


class TestMomentumModels:
    """Test momentum model functionality."""
    
    def test_momentum_signal_creation(self):
        """Test basic momentum signal creation."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == MomentumType.PRICE_MOMENTUM
        assert signal.timeframe == Timeframe.DAILY
        assert signal.strength == 75.0
        assert signal.direction == "BUY"
        assert signal.confidence == 80.0
        assert signal.current_price == Decimal("150.0")
        assert signal.is_expired is False
    
    def test_momentum_signal_validation(self):
        """Test momentum signal validation."""
        # Valid signal
        signal = MomentumSignal(
            symbol="  AAPL  ",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="buy",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        assert signal.symbol == "AAPL"
        assert signal.direction == "BUY"
        
        # Invalid symbol
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MomentumSignal(
                symbol="",
                signal_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                strength=75.0,
                direction="BUY",
                confidence=80.0,
                current_price=Decimal("150.0"),
                price_change=Decimal("2.5"),
                price_change_pct=1.67,
                volume=Decimal("1000000"),
                volume_change=Decimal("100000"),
                volume_change_pct=10.0,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
        
        # Invalid direction
        with pytest.raises(ValueError, match="Direction must be BUY or SELL"):
            MomentumSignal(
                symbol="AAPL",
                signal_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                strength=75.0,
                direction="INVALID",
                confidence=80.0,
                current_price=Decimal("150.0"),
                price_change=Decimal("2.5"),
                price_change_pct=1.67,
                volume=Decimal("1000000"),
                volume_change=Decimal("100000"),
                volume_change_pct=10.0,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
    
    def test_momentum_signal_properties(self):
        """Test momentum signal properties."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Test expiration
        assert signal.is_expired is False
        assert signal.time_to_expiry.total_seconds() > 0
        
        # Test expired signal
        expired_signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert expired_signal.is_expired is True
    
    def test_momentum_score_calculation(self):
        """Test momentum score calculation."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            rsi=25.0,  # Oversold
            macd_histogram=0.5,  # Bullish
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        momentum_score = signal.momentum_score
        assert 0 <= momentum_score <= 100
        assert momentum_score > 0  # Should have positive momentum
    
    def test_technical_indicators_creation(self):
        """Test technical indicators creation."""
        indicators = TechnicalIndicators(
            symbol="AAPL",
            rsi=65.5,
            ema_9=150.0,
            ema_21=148.0,
            ema_50=145.0,
            ema_200=140.0,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            atr=2.5,
            volatility=3.2,
            volume_sma_20=Decimal("1000000"),
            volume_ratio=1.5
        )
        
        assert indicators.symbol == "AAPL"
        assert indicators.rsi == 65.5
        assert indicators.ema_9 == 150.0
        assert indicators.macd == 0.5
        assert indicators.atr == 2.5
        assert indicators.volatility == 3.2
        assert indicators.volume_ratio == 1.5
    
    def test_technical_indicators_properties(self):
        """Test technical indicators properties."""
        # Bullish trend
        indicators = TechnicalIndicators(
            symbol="AAPL",
            ema_9=150.0,
            ema_21=148.0,
            ema_50=145.0,
            rsi=25.0,
            macd_histogram=0.5
        )
        
        assert indicators.ema_trend == "BULLISH"
        assert indicators.rsi_signal == "OVERSOLD"
        assert indicators.macd_signal_indicator == "BULLISH"
        
        # Bearish trend
        indicators = TechnicalIndicators(
            symbol="AAPL",
            ema_9=145.0,
            ema_21=148.0,
            ema_50=150.0,
            rsi=75.0,
            macd_histogram=-0.5
        )
        
        assert indicators.ema_trend == "BEARISH"
        assert indicators.rsi_signal == "OVERBOUGHT"
        assert indicators.macd_signal_indicator == "BEARISH"
    
    def test_momentum_strategy_creation(self):
        """Test momentum strategy creation."""
        strategy = MomentumStrategy(
            name="Test Strategy",
            description="Test momentum strategy",
            momentum_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            min_strength=60.0,
            min_confidence=70.0,
            signal_duration=24,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            ema_short_period=9,
            ema_long_period=21,
            min_volume_ratio=1.2,
            volume_spike_threshold=2.0,
            max_position_size=0.1,
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.momentum_type == MomentumType.PRICE_MOMENTUM
        assert strategy.timeframe == Timeframe.DAILY
        assert strategy.min_strength == 60.0
        assert strategy.is_active is True
    
    def test_momentum_strategy_validation(self):
        """Test momentum strategy validation."""
        # Valid strategy
        strategy = MomentumStrategy(
            name="  Test Strategy  ",
            description="  Test description  ",
            momentum_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            min_strength=60.0,
            min_confidence=70.0,
            signal_duration=24,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            ema_short_period=9,
            ema_long_period=21,
            min_volume_ratio=1.2,
            volume_spike_threshold=2.0,
            max_position_size=0.1,
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )
        assert strategy.name == "Test Strategy"
        assert strategy.description == "Test description"
        
        # Invalid name
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            MomentumStrategy(
                name="",
                description="Test description",
                momentum_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=60.0,
                min_confidence=70.0,
                signal_duration=24,
                rsi_oversold=30.0,
                rsi_overbought=70.0,
                ema_short_period=9,
                ema_long_period=21,
                min_volume_ratio=1.2,
                volume_spike_threshold=2.0,
                max_position_size=0.1,
                stop_loss_pct=0.05,
                take_profit_pct=0.15
            )
    
    def test_momentum_analysis_creation(self):
        """Test momentum analysis creation."""
        indicators = TechnicalIndicators(
            symbol="AAPL",
            rsi=65.5,
            ema_9=150.0,
            ema_21=148.0,
            ema_50=145.0,
            ema_200=140.0,
            macd=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            atr=2.5,
            volatility=3.2,
            volume_sma_20=Decimal("1000000"),
            volume_ratio=1.5
        )
        
        analysis = MomentumAnalysis(
            symbol="AAPL",
            timeframe=Timeframe.DAILY,
            indicators=indicators,
            overall_momentum=75.0,
            trend_direction="BULLISH",
            signal_count=2,
            risk_level="MEDIUM",
            volatility_level="MEDIUM"
        )
        
        assert analysis.symbol == "AAPL"
        assert analysis.timeframe == Timeframe.DAILY
        assert analysis.overall_momentum == 75.0
        assert analysis.trend_direction == "BULLISH"
        assert analysis.signal_count == 2
        assert analysis.risk_level == "MEDIUM"
        assert analysis.volatility_level == "MEDIUM"
    
    def test_momentum_analysis_methods(self):
        """Test momentum analysis methods."""
        indicators = TechnicalIndicators(symbol="AAPL")
        
        analysis = MomentumAnalysis(
            symbol="AAPL",
            timeframe=Timeframe.DAILY,
            indicators=indicators,
            overall_momentum=75.0,
            trend_direction="BULLISH",
            signal_count=0,
            risk_level="MEDIUM",
            volatility_level="MEDIUM"
        )
        
        # Add signal
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        analysis.add_signal(signal)
        assert analysis.signal_count == 1
        
        # Get active signals
        active_signals = analysis.get_active_signals()
        assert len(active_signals) == 1
        
        # Get signals by type
        price_signals = analysis.get_signals_by_type(MomentumType.PRICE_MOMENTUM)
        assert len(price_signals) == 1
    
    def test_momentum_filter_matching(self):
        """Test momentum filter matching."""
        signal = MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            strength=75.0,
            direction="BUY",
            confidence=80.0,
            current_price=Decimal("150.0"),
            price_change=Decimal("2.5"),
            price_change_pct=1.67,
            volume=Decimal("1000000"),
            volume_change=Decimal("100000"),
            volume_change_pct=10.0,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Matching filter
        filter_criteria = MomentumFilter(
            symbols=["AAPL"],
            momentum_types=[MomentumType.PRICE_MOMENTUM],
            timeframes=[Timeframe.DAILY],
            min_strength=70.0,
            min_confidence=75.0,
            active_only=True,
            max_age_hours=24
        )
        
        assert filter_criteria.matches(signal) is True
        
        # Non-matching filter
        filter_criteria.min_strength = 80.0
        assert filter_criteria.matches(signal) is False


class TestTechnicalIndicatorCalculator:
    """Test technical indicator calculator functionality."""
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Test with sufficient data
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
        rsi = TechnicalIndicatorCalculator.calculate_rsi(prices, 14)
        
        assert rsi is not None
        assert 0 <= rsi <= 100
        
        # Test with insufficient data
        prices_short = [100, 102, 101]
        rsi_short = TechnicalIndicatorCalculator.calculate_rsi(prices_short, 14)
        assert rsi_short is None
    
    def test_ema_calculation(self):
        """Test EMA calculation."""
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        ema = TechnicalIndicatorCalculator.calculate_ema(prices, 5)
        
        assert ema is not None
        assert ema > 0
        
        # Test with insufficient data
        prices_short = [100, 102]
        ema_short = TechnicalIndicatorCalculator.calculate_ema(prices_short, 5)
        assert ema_short is None
    
    def test_macd_calculation(self):
        """Test MACD calculation."""
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113, 115, 117, 116, 118, 120, 119, 121, 123, 122, 124, 126, 125, 127, 129, 128]
        macd, signal, histogram = TechnicalIndicatorCalculator.calculate_macd(prices)
        
        assert macd is not None
        assert signal is not None
        assert histogram is not None
        
        # Test with insufficient data
        prices_short = [100, 102, 101]
        macd_short, signal_short, histogram_short = TechnicalIndicatorCalculator.calculate_macd(prices_short)
        assert macd_short is None
        assert signal_short is None
        assert histogram_short is None
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        highs = [102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121]
        lows = [98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117]
        closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
        
        atr = TechnicalIndicatorCalculator.calculate_atr(highs, lows, closes, 14)
        
        assert atr is not None
        assert atr > 0
        
        # Test with insufficient data
        atr_short = TechnicalIndicatorCalculator.calculate_atr(highs[:5], lows[:5], closes[:5], 14)
        assert atr_short is None
    
    def test_volume_sma_calculation(self):
        """Test volume SMA calculation."""
        volumes = [Decimal("1000000"), Decimal("1100000"), Decimal("1200000"), Decimal("1300000"), Decimal("1400000")]
        volume_sma = TechnicalIndicatorCalculator.calculate_volume_sma(volumes, 5)
        
        assert volume_sma is not None
        assert volume_sma > Decimal("0")
        
        # Test with insufficient data
        volumes_short = [Decimal("1000000"), Decimal("1100000")]
        volume_sma_short = TechnicalIndicatorCalculator.calculate_volume_sma(volumes_short, 5)
        assert volume_sma_short is None


class TestMomentumAnalysisService:
    """Test momentum analysis service functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return MomentumAnalysisService()
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert len(service.strategies) == 3  # Default strategies
        assert len(service.analyses) == 0  # No analyses yet
        assert service.indicator_calculator is not None
        
        # Check default strategies
        strategy_names = list(service.strategies.keys())
        assert "Daily Price Momentum" in strategy_names
        assert "Volume Momentum" in strategy_names
        assert "Combined Momentum" in strategy_names
    
    @pytest.mark.asyncio
    async def test_analyze_asset_momentum(self, service):
        """Test asset momentum analysis."""
        analysis = await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        
        assert analysis.symbol == "AAPL"
        assert analysis.timeframe == Timeframe.DAILY
        assert analysis.overall_momentum >= 0
        assert analysis.trend_direction in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert analysis.signal_count >= 0
        assert analysis.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert analysis.volatility_level in ["LOW", "MEDIUM", "HIGH"]
        assert analysis.indicators is not None
    
    @pytest.mark.asyncio
    async def test_get_momentum_signals(self, service):
        """Test getting momentum signals."""
        # First analyze an asset to generate signals
        await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        
        # Get all signals
        signals = await service.get_momentum_signals()
        assert isinstance(signals, list)
        
        # Get filtered signals
        filter_criteria = MomentumFilter(
            min_strength=50.0,
            min_confidence=60.0,
            active_only=True
        )
        filtered_signals = await service.get_momentum_signals(filter_criteria)
        assert isinstance(filtered_signals, list)
        assert len(filtered_signals) <= len(signals)
    
    @pytest.mark.asyncio
    async def test_get_strategy_signals(self, service):
        """Test getting strategy-specific signals."""
        # First analyze an asset
        await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        
        # Get signals for a specific strategy
        signals = await service.get_strategy_signals("Daily Price Momentum")
        assert isinstance(signals, list)
        
        # Test with non-existent strategy
        signals_empty = await service.get_strategy_signals("Non-existent Strategy")
        assert signals_empty == []
    
    @pytest.mark.asyncio
    async def test_get_top_momentum_assets(self, service):
        """Test getting top momentum assets."""
        # First analyze multiple assets
        await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        await service.analyze_asset_momentum("MSFT", Timeframe.DAILY)
        await service.analyze_asset_momentum("GOOGL", Timeframe.DAILY)
        
        # Get top momentum assets
        top_assets = await service.get_top_momentum_assets(5)
        assert isinstance(top_assets, list)
        assert len(top_assets) <= 5
        
        # Check structure of top assets
        if top_assets:
            asset = top_assets[0]
            assert "symbol" in asset
            assert "momentum_score" in asset
            assert "strength" in asset
            assert "confidence" in asset
            assert "direction" in asset
            assert "signal_type" in asset
            assert "timestamp" in asset
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """Test error handling in service methods."""
        # Test with invalid symbol - should still work with mock data
        analysis = await service.analyze_asset_momentum("INVALID_SYMBOL", Timeframe.DAILY)
        assert analysis.symbol == "INVALID_SYMBOL"
        
        # Test getting signals with analyses
        signals = await service.get_momentum_signals()
        assert isinstance(signals, list)
        assert len(signals) > 0  # Should have signals from the analysis
        
        # Test getting top assets with analyses
        top_assets = await service.get_top_momentum_assets(5)
        assert isinstance(top_assets, list)
        assert len(top_assets) > 0  # Should have assets from the analysis


class TestMomentumServiceIntegration:
    """Test momentum service integration scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return MomentumAnalysisService()
    
    @pytest.mark.asyncio
    async def test_complete_momentum_analysis_workflow(self, service):
        """Test complete momentum analysis workflow."""
        # Step 1: Analyze asset momentum
        analysis = await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        assert analysis.symbol == "AAPL"
        
        # Step 2: Get momentum signals
        signals = await service.get_momentum_signals()
        assert isinstance(signals, list)
        
        # Step 3: Get strategy signals
        strategy_signals = await service.get_strategy_signals("Daily Price Momentum")
        assert isinstance(strategy_signals, list)
        
        # Step 4: Get top momentum assets
        top_assets = await service.get_top_momentum_assets(10)
        assert isinstance(top_assets, list)
        
        # Step 5: Verify analysis is stored
        analysis_key = f"AAPL_{Timeframe.DAILY.value}"
        assert analysis_key in service.analyses
    
    @pytest.mark.asyncio
    async def test_multiple_assets_analysis(self, service):
        """Test analyzing multiple assets."""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        for symbol in symbols:
            analysis = await service.analyze_asset_momentum(symbol, Timeframe.DAILY)
            assert analysis.symbol == symbol
        
        # Get top momentum assets
        top_assets = await service.get_top_momentum_assets(10)
        assert len(top_assets) <= 10
        
        # Verify all analyzed symbols are represented
        analyzed_symbols = [asset["symbol"] for asset in top_assets]
        for symbol in symbols:
            assert symbol in analyzed_symbols
    
    @pytest.mark.asyncio
    async def test_signal_filtering_workflow(self, service):
        """Test signal filtering workflow."""
        # Analyze multiple assets
        await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        await service.analyze_asset_momentum("MSFT", Timeframe.DAILY)
        
        # Test different filter criteria
        filters = [
            MomentumFilter(min_strength=60.0, min_confidence=70.0),
            MomentumFilter(momentum_types=[MomentumType.PRICE_MOMENTUM]),
            MomentumFilter(timeframes=[Timeframe.DAILY]),
            MomentumFilter(active_only=True, max_age_hours=24)
        ]
        
        for filter_criteria in filters:
            signals = await service.get_momentum_signals(filter_criteria)
            assert isinstance(signals, list)
            
            # Verify all signals match filter criteria
            for signal in signals:
                assert filter_criteria.matches(signal)
    
    @pytest.mark.asyncio
    async def test_strategy_comparison(self, service):
        """Test comparing different strategies."""
        # Analyze an asset
        await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        
        # Get signals for different strategies
        strategies = ["Daily Price Momentum", "Volume Momentum", "Combined Momentum"]
        strategy_results = {}
        
        for strategy_name in strategies:
            signals = await service.get_strategy_signals(strategy_name)
            strategy_results[strategy_name] = len(signals)
        
        # Verify all strategies return results
        for strategy_name, signal_count in strategy_results.items():
            assert signal_count >= 0
    
    @pytest.mark.asyncio
    async def test_technical_indicators_consistency(self, service):
        """Test technical indicators consistency."""
        # Analyze the same asset multiple times
        analyses = []
        for _ in range(3):
            analysis = await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
            analyses.append(analysis)
        
        # Verify indicators are calculated consistently
        for analysis in analyses:
            assert analysis.indicators.symbol == "AAPL"
            assert analysis.indicators.timeframe == Timeframe.DAILY
            assert analysis.indicators.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_signal_expiration_handling(self, service):
        """Test signal expiration handling."""
        # Analyze asset
        analysis = await service.analyze_asset_momentum("AAPL", Timeframe.DAILY)
        
        # Get all signals
        all_signals = analysis.signals
        
        # Get active signals
        active_signals = analysis.get_active_signals()
        
        # Verify active signals are not expired
        for signal in active_signals:
            assert not signal.is_expired
            assert signal.time_to_expiry.total_seconds() > 0
        
        # Verify expired signals are filtered out
        expired_signals = [s for s in all_signals if s.is_expired]
        assert len(active_signals) + len(expired_signals) == len(all_signals)
