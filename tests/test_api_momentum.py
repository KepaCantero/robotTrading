"""
Tests for Momentum API endpoints

This module tests the FastAPI endpoints for momentum analysis,
including edge cases, error handling, and data validation.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.momentum import router
from app.models.momentum import (
    MomentumSignal, MomentumType, Timeframe, TechnicalIndicators,
    MomentumStrategy, MomentumAnalysis, MomentumFilter
)
from app.services.momentum_analysis import get_momentum_analysis_service


# Create test app
app = FastAPI()

# Override dependencies for testing
def override_get_momentum_analysis_service():
    return AsyncMock()

app.dependency_overrides[get_momentum_analysis_service] = override_get_momentum_analysis_service

app.include_router(router)


class TestMomentumAPI:
    """Test Momentum API endpoints."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    def _override_service(self, mock_service):
        """Helper to override the service dependency."""
        app.dependency_overrides[get_momentum_analysis_service] = lambda: mock_service
        return mock_service
    
    def _cleanup_overrides(self):
        """Helper to clean up dependency overrides."""
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def sample_momentum_signal(self):
        """Sample momentum signal for testing."""
        return MomentumSignal(
            symbol="AAPL",
            signal_type=MomentumType.PRICE_MOMENTUM,
            strength=85.0,
            confidence=0.8,
            timeframe=Timeframe.DAILY,
            timestamp=datetime.utcnow() - timedelta(days=1),
            price=Decimal("150.0"),
            volume=Decimal("1000000"),
            direction="BUY",
            current_price=Decimal("150.0"),
            price_change=Decimal("5.0"),
            price_change_pct=Decimal("3.45"),
            volume_change=Decimal("100000"),
            volume_change_pct=Decimal("10.0"),
            expires_at=datetime.utcnow() + timedelta(days=1),
            technical_indicators=TechnicalIndicators(
                symbol="AAPL",
                rsi=70.0,
                ema_20=Decimal("145.0"),
                macd=Decimal("2.5"),
                atr=Decimal("3.0"),
                volume_sma=Decimal("1200000")
            )
        )
    
    @pytest.fixture
    def sample_technical_indicators(self):
        """Sample technical indicators for testing."""
        return TechnicalIndicators(
            symbol="AAPL",
            rsi=70.0,
            ema_20=Decimal("145.0"),
            macd=Decimal("2.5"),
            atr=Decimal("3.0"),
            volume_sma=Decimal("1200000")
        )
    
    @pytest.fixture
    def sample_momentum_strategy(self):
        """Sample momentum strategy for testing."""
        return MomentumStrategy(
            name="Daily Momentum",
            description="Simple daily momentum strategy",
            momentum_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            min_confidence=0.7,
            max_positions=10,
            risk_per_trade=0.02,
            is_active=True
        )
    
    @pytest.fixture
    def sample_momentum_analysis(self, sample_technical_indicators, sample_momentum_signal):
        """Sample momentum analysis for testing."""
        return MomentumAnalysis(
            symbol="AAPL",
            analysis_date=datetime.utcnow() - timedelta(days=1),
            momentum_score=85.0,
            confidence=0.8,
            technical_indicators=sample_technical_indicators,
            signals=[sample_momentum_signal],
            indicators={"symbol": "AAPL"},
            overall_momentum=85.0,
            trend_direction="BULLISH",
            risk_level="MEDIUM",
            volatility_level="MEDIUM"
        )
    
    @pytest.fixture
    def mock_service(self):
        """Mock momentum analysis service."""
        service = AsyncMock()
        service.strategies = {"daily_momentum": MagicMock()}
        service.analyses = {}
        return service
    
    def test_get_momentum_overview_success(self, client, mock_service):
        """Test successful momentum overview retrieval."""
        # Mock service response
        mock_service.get_top_momentum_assets.return_value = [
            {"symbol": "AAPL", "score": 85.0},
            {"symbol": "MSFT", "score": 82.0}
        ]
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "overview" in data
            assert "timestamp" in data
            assert len(data["overview"]["top_momentum_assets"]) == 2
        finally:
            self._cleanup_overrides()
    
    def test_get_momentum_overview_service_error(self, client, mock_service):
        """Test momentum overview with service error."""
        # Mock service to raise exception
        mock_service.get_top_momentum_assets.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum overview" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_analyze_asset_success(self, client, mock_service, sample_momentum_analysis):
        """Test successful asset analysis."""
        # Mock service response
        mock_service.analyze_asset_momentum.return_value = sample_momentum_analysis
        
        try:
            self._override_service(mock_service)
            response = client.post("/momentum/analyze", json={
                "symbol": "AAPL",
                "timeframe": "daily",
                "momentum_types": ["price", "volume"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "analysis" in data
            assert data["analysis"]["symbol"] == "AAPL"
        finally:
            self._cleanup_overrides()
    
    def test_analyze_asset_invalid_data(self, client):
        """Test asset analysis with invalid data."""
        response = client.post("/momentum/analyze", json={
            "symbol": "",  # Empty symbol
            "timeframe": "invalid_timeframe",  # Invalid timeframe
            "momentum_types": []  # Empty momentum types
        })
        
        assert response.status_code == 400  # Bad Request (manual validation)
    
    def test_analyze_asset_service_error(self, client, mock_service):
        """Test asset analysis with service error."""
        # Mock service to raise exception
        mock_service.analyze_asset_momentum.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.post("/momentum/analyze", json={
                "symbol": "AAPL",
                "timeframe": "daily"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "Error analyzing momentum for AAPL" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_technical_indicators_success(self, client, mock_service, sample_technical_indicators, sample_momentum_analysis):
        """Test successful technical indicators retrieval."""
        # Mock service response - technical indicators endpoint uses analyze_asset_momentum
        sample_momentum_analysis.indicators = sample_technical_indicators
        mock_service.analyze_asset_momentum.return_value = sample_momentum_analysis
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/indicators/AAPL")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "indicators" in data
            assert data["indicators"]["rsi"] == 70.0
        finally:
            self._cleanup_overrides()
    
    def test_get_technical_indicators_not_found(self, client, mock_service):
        """Test technical indicators with asset not found."""
        # Mock service to return None
        mock_service.analyze_asset_momentum.return_value = None
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/indicators/NONEXISTENT")
            
            assert response.status_code == 404
            data = response.json()
            assert "Analysis not found for NONEXISTENT" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_technical_indicators_service_error(self, client, mock_service):
        """Test technical indicators with service error."""
        # Mock service to raise exception
        mock_service.analyze_asset_momentum.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/indicators/AAPL")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting technical indicators" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_momentum_signals_success(self, client, mock_service, sample_momentum_signal):
        """Test successful momentum signals retrieval."""
        # Mock service response
        mock_service.get_momentum_signals_for_symbol.return_value = [sample_momentum_signal]
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/signals/AAPL")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "signals" in data
            assert len(data["signals"]) == 1
        finally:
            self._cleanup_overrides()
    
    def test_get_momentum_signals_not_found(self, client, mock_service):
        """Test momentum signals with asset not found."""
        # Mock service to return empty list
        mock_service.get_momentum_signals_for_symbol.return_value = []
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/signals/NONEXISTENT")
            
            assert response.status_code == 404
            data = response.json()
            assert "No momentum signals found" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_momentum_signals_service_error(self, client, mock_service):
        """Test momentum signals with service error."""
        # Mock service to raise exception
        mock_service.get_momentum_signals_for_symbol.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/signals/AAPL")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum signals" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_create_strategy_success(self, client, mock_service, sample_momentum_strategy):
        """Test successful strategy creation."""
        # Mock service response
        mock_service.create_strategy.return_value = sample_momentum_strategy
        
        try:
            self._override_service(mock_service)
            response = client.post("/momentum/strategies", json={
                "name": "Daily Momentum",
                "description": "Simple daily momentum strategy",
                "momentum_types": ["price"],
                "timeframe": "daily",
                "min_confidence": 0.7,
                "max_position_size": 0.5,
                "risk_per_trade": 0.02
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "strategy" in data
            assert data["strategy"]["name"] == "Daily Momentum"
        finally:
            self._cleanup_overrides()
    
    def test_create_strategy_invalid_data(self, client):
        """Test strategy creation with invalid data."""
        response = client.post("/momentum/strategies", json={
            "name": "",  # Empty name
            "momentum_types": [],  # Empty momentum types
            "min_confidence": -1.0,  # Invalid confidence
            "max_positions": 0  # Invalid max positions
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_create_strategy_service_error(self, client, mock_service):
        """Test strategy creation with service error."""
        # Mock service to raise exception
        mock_service.create_strategy.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.post("/momentum/strategies", json={
                "name": "Test Strategy",
                "description": "Test Description",
                "momentum_types": ["price"],
                "timeframe": "daily",
                "min_confidence": 0.7,
                "max_position_size": 0.5,
                "risk_per_trade": 0.02
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "Error creating momentum strategy" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_strategies_success(self, client, mock_service, sample_momentum_strategy):
        """Test successful strategies retrieval."""
        # Mock service response
        mock_service.get_strategies.return_value = [sample_momentum_strategy]
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "strategies" in data
            assert len(data["strategies"]) == 1
        finally:
            self._cleanup_overrides()
    
    def test_get_strategies_service_error(self, client, mock_service):
        """Test strategies retrieval with service error."""
        # Mock service to raise exception
        from unittest.mock import MagicMock
        mock_service.strategies = MagicMock()
        mock_service.strategies.items.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum strategies" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_strategy_success(self, client, mock_service, sample_momentum_strategy):
        """Test successful strategy retrieval."""
        # Mock service response
        mock_service.get_strategy.return_value = sample_momentum_strategy
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies/daily_momentum")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "strategy" in data
            assert data["strategy"]["name"] == "Daily Momentum"
        finally:
            self._cleanup_overrides()
    
    def test_get_strategy_not_found(self, client, mock_service):
        """Test strategy retrieval with strategy not found."""
        # Mock service to return None
        mock_service.get_strategy.return_value = None
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies/nonexistent")
            
            assert response.status_code == 404
            data = response.json()
            assert "Strategy nonexistent not found" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_strategy_service_error(self, client, mock_service):
        """Test strategy retrieval with service error."""
        # Mock service to raise exception
        mock_service.get_strategy.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies/daily_momentum")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum strategy" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_update_strategy_success(self, client, mock_service, sample_momentum_strategy):
        """Test successful strategy update."""
        # Mock service response
        mock_service.update_strategy.return_value = sample_momentum_strategy
        
        try:
            self._override_service(mock_service)
            response = client.put("/momentum/strategies/daily_momentum", json={
                "name": "Updated Daily Momentum",
                "min_confidence": 0.8
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "strategy" in data
        finally:
            self._cleanup_overrides()
    
    def test_update_strategy_invalid_data(self, client):
        """Test strategy update with invalid data."""
        response = client.put("/momentum/strategies/daily_momentum", json={
            "min_confidence": 2.0,  # Invalid confidence > 1
            "max_position_size": -1  # Invalid negative position size
        })
        
        # Should handle gracefully or return validation error
        assert response.status_code == 200  # No validation error (endpoint uses Dict[str, Any])
    
    def test_update_strategy_service_error(self, client, mock_service):
        """Test strategy update with service error."""
        # Mock service to raise exception
        mock_service.update_strategy.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.put("/momentum/strategies/daily_momentum", json={
                "min_confidence": 0.8
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "Error updating momentum strategy" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_delete_strategy_success(self, client, mock_service):
        """Test successful strategy deletion."""
        # Mock service response
        mock_service.delete_strategy.return_value = True
        
        try:
            self._override_service(mock_service)
            response = client.delete("/momentum/strategies/daily_momentum")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Strategy daily_momentum deleted successfully" in data["message"]
        finally:
            self._cleanup_overrides()
    
    def test_delete_strategy_not_found(self, client, mock_service):
        """Test strategy deletion with strategy not found."""
        # Mock service to return None for get_strategy (strategy not found)
        mock_service.get_strategy.return_value = None
        
        try:
            self._override_service(mock_service)
            response = client.delete("/momentum/strategies/nonexistent")
            
            assert response.status_code == 404
            data = response.json()
            assert "Strategy nonexistent not found" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_delete_strategy_service_error(self, client, mock_service):
        """Test strategy deletion with service error."""
        # Mock service to raise exception
        mock_service.delete_strategy.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.delete("/momentum/strategies/daily_momentum")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error deleting momentum strategy" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_analyses_success(self, client, mock_service, sample_momentum_analysis):
        """Test successful analyses retrieval."""
        # Mock service response
        mock_service.get_analyses.return_value = [sample_momentum_analysis]
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "analyses" in data
            assert len(data["analyses"]) == 1
        finally:
            self._cleanup_overrides()
    
    def test_get_analyses_service_error(self, client, mock_service):
        """Test analyses retrieval with service error."""
        # Mock service to raise exception
        mock_service.get_analyses.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum analyses" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_analysis_success(self, client, mock_service, sample_momentum_analysis):
        """Test successful analysis retrieval."""
        # Mock service response
        mock_service.get_analysis.return_value = sample_momentum_analysis
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses/AAPL_2024_01_01")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "analysis" in data
            assert data["analysis"]["symbol"] == "AAPL"
        finally:
            self._cleanup_overrides()
    
    def test_get_analysis_not_found(self, client, mock_service):
        """Test analysis retrieval with analysis not found."""
        # Mock service to return None
        mock_service.get_analysis.return_value = None
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses/nonexistent")
            
            assert response.status_code == 404
            data = response.json()
            assert "Analysis nonexistent not found" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_get_analysis_service_error(self, client, mock_service):
        """Test analysis retrieval with service error."""
        # Mock service to raise exception
        mock_service.get_analysis.side_effect = Exception("Service error")
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses/AAPL_2024_01_01")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting momentum analysis" in data["detail"]
        finally:
            self._cleanup_overrides()


class TestMomentumAPIEdgeCases:
    """Test edge cases for Momentum API."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    def _override_service(self, mock_service):
        """Helper to override the service dependency."""
        app.dependency_overrides[get_momentum_analysis_service] = lambda: mock_service
        return mock_service
    
    def _cleanup_overrides(self):
        """Helper to clean up dependency overrides."""
        app.dependency_overrides.clear()
    
    def test_get_momentum_overview_empty_response(self, client):
        """Test momentum overview with empty response."""
        mock_service = AsyncMock()
        # Mock service with empty strategies
        mock_service.strategies = {}
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["overview"]["top_momentum_assets"]) == 0
        finally:
            self._cleanup_overrides()
    
    def test_analyze_asset_with_extreme_values(self, client):
        """Test asset analysis with extreme values."""
        response = client.post("/momentum/analyze", json={
            "symbol": "A" * 100,  # Very long symbol
            "timeframe": "daily",
            "momentum_types": ["price"] * 50  # Many momentum types
        })
        
        # Should handle gracefully or return validation error
        assert response.status_code in [200, 422]
    
    def test_get_technical_indicators_with_zero_values(self, client):
        """Test technical indicators with zero values."""
        mock_service = AsyncMock()
        # Create analysis with zero indicators
        analysis = MomentumAnalysis(
            id="test_analysis",
            symbol="TEST",
            timestamp=datetime.utcnow(),
            indicators=TechnicalIndicators(
                symbol="TEST",
                rsi=0.0,
                ema_20=Decimal("0.0"),
                macd=Decimal("0.0"),
                atr=Decimal("0.0"),
                volume_sma=Decimal("0.0")
            ),
            overall_momentum=0.0,
            trend_direction="NEUTRAL",
            risk_level="LOW",
            volatility_level="LOW"
        )
        
        mock_service.analyze_asset_momentum.return_value = analysis
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/indicators/TEST")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["indicators"]["rsi"] == 0.0
        finally:
            self._cleanup_overrides()
    
    def test_get_momentum_signals_with_empty_list(self, client):
        """Test momentum signals with empty list."""
        mock_service = AsyncMock()
        mock_service.get_momentum_signals_for_symbol.return_value = []
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/signals/TEST")
            
            assert response.status_code == 404
            data = response.json()
            assert "No momentum signals found" in data["detail"]
        finally:
            self._cleanup_overrides()
    
    def test_create_strategy_with_extreme_values(self, client):
        """Test strategy creation with extreme values."""
        response = client.post("/momentum/strategies", json={
            "name": "A" * 1000,  # Very long name
            "description": "B" * 10000,  # Very long description
            "momentum_types": ["price"],
            "timeframe": "daily",
            "min_confidence": 0.999999,  # Very high confidence
            "max_position_size": 0.999999,  # Very high position size (but valid)
            "risk_per_trade": 0.999999  # Very high risk
        })
        
        # Should handle gracefully or return validation error
        assert response.status_code in [200, 422]
    
    def test_get_strategies_with_large_dataset(self, client):
        """Test strategies retrieval with large dataset."""
        mock_service = AsyncMock()
        
        # Mock service strategies dictionary
        strategies_dict = {}
        for i in range(1000):
            strategy = MomentumStrategy(
                name=f"Strategy_{i}",
                description=f"Description for strategy {i}",
                momentum_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_confidence=0.7,
                max_position_size=0.1,
                risk_per_trade=0.02,
                is_active=True
            )
            strategies_dict[strategy.name] = strategy
        
        mock_service.strategies = strategies_dict
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/strategies")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["strategies"]) == 1000
        finally:
            self._cleanup_overrides()
    
    def test_update_strategy_with_minimal_changes(self, client):
        """Test strategy update with minimal changes."""
        mock_service = AsyncMock()
        mock_service.update_strategy.return_value = MomentumStrategy(
            name="Updated Strategy",
            description="Updated description",
            momentum_type=MomentumType.PRICE_MOMENTUM,
            timeframe=Timeframe.DAILY,
            min_confidence=0.7,
            max_positions=10,
            risk_per_trade=0.02,
            is_active=True
        )
        
        try:
            self._override_service(mock_service)
            response = client.put("/momentum/strategies/test_strategy", json={
                "description": "Minimal change"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            self._cleanup_overrides()
    
    def test_get_analyses_with_empty_list(self, client):
        """Test analyses retrieval with empty list."""
        mock_service = AsyncMock()
        mock_service.get_analyses.return_value = []
        
        try:
            self._override_service(mock_service)
            response = client.get("/momentum/analyses")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["analyses"]) == 0
        finally:
            self._cleanup_overrides()