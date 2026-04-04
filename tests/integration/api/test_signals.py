"""
Signal Management API Endpoints Test Suite

Tests for signal management API endpoints with DI container pattern.

Reference: Rule DP-004 - Use dependency injection instead of direct instantiation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.presentation.api.signals import get_signal_scorer_service, router
from app.services.signal_scorer import SignalScorerService


class TestSignalsAPIEndpoints:
    """Test signal management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_signal(self):
        """Create mock signal using actual Signal model."""
        return Signal(
            signal_id="test_signal_123",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=75.0,
            liquidity_score=60.0,
            priority_score=80.0,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            source=SignalSource.TECHNICAL,
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_evaluate_signal_success_buy(self, client, mock_signal):
        """Test evaluate_signal with valid buy signal."""
        with patch.object(
            SignalScorerService, "evaluate_signal", new=AsyncMock(return_value=mock_signal)
        ):
            response = client.post(
                "/signals/evaluate",
                json={
                    "symbol": "AAPL",
                    "signal_type": "buy",
                    "market_data": {
                        "symbol": "AAPL",
                        "price": 150.0,
                        "volume": 1000000.0,
                        "bid": 149.5,
                        "ask": 150.5,
                        "spread": 1.0,
                    },
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_evaluate_signal_invalid_signal_type(self, client):
        """Test evaluate_signal rejects invalid signal_type."""
        response = client.post(
            "/signals/evaluate",
            json={
                "symbol": "AAPL",
                "signal_type": "invalid_type",
                "market_data": {
                    "symbol": "AAPL",
                    "price": 150.0,
                    "volume": 1000000.0,
                    "bid": 149.5,
                    "ask": 150.5,
                    "spread": 1.0,
                },
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_evaluate_signal_below_thresholds(self, client):
        """Test evaluate_signal returns rejection when below thresholds."""
        with patch.object(SignalScorerService, "evaluate_signal", new=AsyncMock(return_value=None)):
            response = client.post(
                "/signals/evaluate",
                json={
                    "symbol": "AAPL",
                    "signal_type": "buy",
                    "market_data": {
                        "symbol": "AAPL",
                        "price": 150.0,
                        "volume": 1000000.0,
                        "bid": 149.5,
                        "ask": 150.5,
                        "spread": 1.0,
                    },
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "does not meet minimum thresholds" in data["message"]

    @pytest.mark.asyncio
    async def test_get_next_actionable_signal_has_signal(self, client, mock_signal):
        """Test get_next_actionable_signal returns signal when available."""
        with patch.object(
            SignalScorerService,
            "get_next_actionable_signal",
            new=AsyncMock(return_value=mock_signal),
        ):
            response = client.get("/signals/next")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_next_actionable_signal_empty_queue(self, client):
        """Test get_next_actionable_signal returns empty response when queue empty."""
        with patch.object(
            SignalScorerService, "get_next_actionable_signal", new=AsyncMock(return_value=None)
        ):
            response = client.get("/signals/next")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "No actionable signals available" in data["message"]

    @pytest.mark.asyncio
    async def test_execute_signal_success(self, client, mock_signal):
        """Test execute_signal executes trade successfully."""
        with (
            patch.object(
                SignalScorerService,
                "get_signals_by_symbol",
                new=AsyncMock(return_value=[mock_signal]),
            ),
            patch.object(SignalScorerService, "execute_signal", new=AsyncMock(return_value=True)),
        ):
            response = client.post("/signals/execute/AAPL")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_execute_signal_no_signals_found(self, client):
        """Test execute_signal returns error for unknown symbol."""
        with patch.object(
            SignalScorerService, "get_signals_by_symbol", new=AsyncMock(return_value=[])
        ):
            response = client.post("/signals/execute/NONEXISTENT")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "No signals found" in data["message"]

    @pytest.mark.asyncio
    async def test_get_signal_statistics(self, client):
        """Test get_signal_statistics returns correct stats."""
        with patch.object(
            SignalScorerService,
            "get_signal_statistics",
            new=AsyncMock(
                return_value={
                    "signals_processed": 100,
                    "signals_executed": 50,
                    "success_rate": 50.0,
                    "total_pnl": 5000.0,
                    "queue_size": 10,
                    "queue_summary": {},
                    "min_confidence_threshold": 60.0,
                    "min_liquidity_threshold": 50.0,
                    "max_position_size_percent": 10.0,
                }
            ),
        ):
            response = client.get("/signals/statistics")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["signals_processed"] == 100
            assert data["signals_executed"] == 50

    @pytest.mark.asyncio
    async def test_get_signals_by_symbol(self, client, mock_signal):
        """Test get_signals_by_symbol returns signals for symbol."""
        with patch.object(
            SignalScorerService, "get_signals_by_symbol", new=AsyncMock(return_value=[mock_signal])
        ):
            response = client.get("/signals/symbol/AAPL")
            assert response.status_code == status.HTTP_200_OK
            signals = response.json()
            assert len(signals) == 1

    @pytest.mark.asyncio
    async def test_clear_expired_signals(self, client):
        """Test clear_expired_signals removes old signals."""
        with patch.object(SignalScorerService, "clear_expired_signals", new=AsyncMock()):
            response = client.post("/signals/clear-expired?max_age_minutes=60")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_thresholds_valid(self, client):
        """Test update_thresholds with valid values."""
        with patch.object(SignalScorerService, "update_thresholds"):
            response = client.post(
                "/signals/thresholds?confidence_threshold=70&liquidity_threshold=60"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_thresholds_invalid_confidence(self, client):
        """Test update_thresholds validates range (0-100) for confidence."""
        response = client.post(
            "/signals/thresholds?confidence_threshold=150&liquidity_threshold=60"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_thresholds_invalid_liquidity(self, client):
        """Test update_thresholds validates range (0-100) for liquidity."""
        response = client.post(
            "/signals/thresholds?confidence_threshold=70&liquidity_threshold=150"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_position_size_limit_valid(self, client):
        """Test update_position_size_limit with valid value."""
        with patch.object(SignalScorerService, "update_position_size_limit"):
            response = client.post("/signals/position-size-limit?max_percent=15")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_position_size_limit_invalid(self, client):
        """Test update_position_size_limit validates range (0-100)."""
        response = client.post("/signals/position-size-limit?max_percent=150")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_signal_health_check_healthy(self, client):
        """Test signal_health_check returns healthy status."""
        with patch.object(
            SignalScorerService,
            "get_signal_statistics",
            new=AsyncMock(return_value={"signals_processed": 100}),
        ):
            response = client.get("/signals/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] in ["healthy", "unhealthy"]


class TestDIContainerPattern:
    """Test DI container pattern for signal scorer service."""

    def test_get_signal_scorer_service_returns_singleton(self):
        """Test that get_signal_scorer_service returns the same instance."""
        service1 = get_signal_scorer_service()
        service2 = get_signal_scorer_service()
        # Both should be SignalScorerService instances
        assert isinstance(service1, SignalScorerService)
        assert isinstance(service2, SignalScorerService)

    def test_get_signal_scorer_service_from_di_container(self):
        """Test that get_signal_scorer_service uses DI container."""
        from app.core.di_container import get_signal_scorer_service as di_get_signal_scorer_service

        # Get service from DI container module
        service_from_di = di_get_signal_scorer_service()
        service_from_api = get_signal_scorer_service()

        # Both should be SignalScorerService instances and the same singleton
        assert isinstance(service_from_di, SignalScorerService)
        assert isinstance(service_from_api, SignalScorerService)
        assert service_from_di is service_from_api  # Same singleton instance

    def test_di_container_initialization(self):
        """Test that DI container is properly initialized with signal services."""
        from app.core.di_container import get_signal_scorer_service as di_get_signal_scorer_service

        # Get service from DI container module
        service = di_get_signal_scorer_service()
        assert service is not None
        assert isinstance(service, SignalScorerService)

    def test_signal_service_depends_on_portfolio_service(self):
        """Test that SignalScorerService properly depends on PortfolioService."""
        from app.core.di_container import (
            get_portfolio_service,
            get_signal_scorer_service as di_get_signal_scorer_service,
        )

        # Get signal scorer service from DI container
        signal_service = di_get_signal_scorer_service()
        portfolio_service = get_portfolio_service()

        # Should have portfolio_service as dependency
        assert signal_service.portfolio_service is not None
        assert isinstance(signal_service.portfolio_service, type(portfolio_service))
        # Should be the same singleton instance
        assert signal_service.portfolio_service is portfolio_service


class TestSymbolUppercaseConversion:
    """Test symbol parameter uppercase conversion."""

    @pytest.mark.asyncio
    async def test_execute_signal_converts_symbol_to_uppercase(self, client):
        """Test execute_signal converts symbol to uppercase."""
        mock_signal = Signal(
            signal_id="test_signal_123",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=75.0,
            liquidity_score=60.0,
            priority_score=80.0,
            price=Decimal("150.00"),
            volume=Decimal("1000000"),
            source=SignalSource.TECHNICAL,
            metadata={},
        )

        with (
            patch.object(
                SignalScorerService,
                "get_signals_by_symbol",
                new=AsyncMock(return_value=[mock_signal]),
            ) as mock_get,
            patch.object(SignalScorerService, "execute_signal", new=AsyncMock(return_value=True)),
        ):
            client.post("/signals/execute/aapl")
            # Should call with uppercase symbol
            mock_get.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_signals_by_symbol_converts_to_uppercase(self, client):
        """Test get_signals_by_symbol converts symbol to uppercase."""
        with patch.object(
            SignalScorerService, "get_signals_by_symbol", new=AsyncMock(return_value=[])
        ) as mock_get:
            client.get("/signals/symbol/aapl")
            # Should call with uppercase symbol
            mock_get.assert_called_once_with("AAPL")


class TestErrorHandling:
    """Test error handling in signals API."""

    @pytest.mark.asyncio
    async def test_evaluate_signal_error_handling(self, client):
        """Test evaluate_signal handles errors correctly."""
        with patch.object(
            SignalScorerService,
            "evaluate_signal",
            new=AsyncMock(side_effect=ValueError("Test error")),
        ):
            response = client.post(
                "/signals/evaluate",
                json={
                    "symbol": "AAPL",
                    "signal_type": "buy",
                    "market_data": {
                        "symbol": "AAPL",
                        "price": 150.0,
                        "volume": 1000000.0,
                        "bid": 149.5,
                        "ask": 150.5,
                        "spread": 1.0,
                    },
                },
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_get_next_actionable_signal_error_handling(self, client):
        """Test get_next_actionable_signal handles errors correctly."""
        with patch.object(
            SignalScorerService,
            "get_next_actionable_signal",
            new=AsyncMock(side_effect=ValueError("Test error")),
        ):
            response = client.get("/signals/next")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_get_signal_statistics_error_handling(self, client):
        """Test get_signal_statistics handles connection errors correctly."""
        import asyncio

        with patch.object(
            SignalScorerService,
            "get_signal_statistics",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            response = client.get("/signals/statistics")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
