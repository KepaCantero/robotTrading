"""
Market Data API Endpoints Test Suite

Tests for market data API endpoints.

Reference: API-004 - Test coverage for API endpoints.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.presentation.api.market_data import router
from app.domain.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    Quote,
)


class TestMarketDataAPIEndpoints:
    """Test market data API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_quote(self):
        """Create mock quote."""
        return Quote(
            symbol="AAPL",
            price=Decimal("150.25"),
            bid=Decimal("150.20"),
            ask=Decimal("150.30"),
            volume=1000000,
            timestamp=datetime.utcnow(),
        )

    @pytest.fixture
    def mock_feed_config(self):
        """Create mock feed configuration."""
        return DataFeedConfig(
            id=uuid4(),
            name="Test Feed",
            feed_type=DataFeedType.REST_API,
            api_key="test_key",
            base_url="https://api.example.com",
            rate_limit=60,
            supported_symbols=["AAPL", "MSFT", "GOOGL"],
            supported_frequencies=[DataFrequency.DAILY, DataFrequency.REAL_TIME],
            max_history_days=365,
            timeout_seconds=30,
            retry_attempts=3,
            retry_delay=1.0,
            is_active=True,
        )

    @pytest.fixture
    def mock_historical_data(self):
        """Create mock historical data."""
        base_date = datetime.utcnow() - timedelta(days=10)
        return [
            HistoricalData(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=Decimal("148.0"),
                high=Decimal("152.0"),
                low=Decimal("147.0"),
                close=Decimal("150.0"),
                volume=1000000,
            )
            for i in range(10)
        ]

    @pytest.mark.asyncio
    async def test_get_quote_success(self, client, mock_quote):
        """Test get_quote returns valid quote data."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_quote.return_value = mock_quote
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/quotes/AAPL")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["symbol"] == "AAPL"
            assert data["data"]["price"] == 150.25

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, client):
        """Test get_quote returns error when quote not available."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_quote.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/quotes/NONEXISTENT")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "not available" in data["error"]

    @pytest.mark.asyncio
    async def test_get_multiple_quotes_success(self, client, mock_quote):
        """Test get_multiple_quotes returns quotes for multiple symbols."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_quote.return_value = mock_quote
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/quotes?symbols=AAPL&symbols=MSFT")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_top_liquid_quotes_success(self, client, mock_quote):
        """Test get_top_liquid_quotes returns liquid assets."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_top_liquid_assets_quotes.return_value = [mock_quote]
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/quotes/top-liquid?limit=10")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_top_liquid_quotes_invalid_limit(self, client):
        """Test get_top_liquid_quotes validates limit parameter."""
        response = client.get("/market-data/quotes/top-liquid?limit=150")
        # Should return validation error (422) for limit > 100
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_historical_data_success(self, client, mock_historical_data):
        """Test get_historical_data returns historical data."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=10)

        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_historical_data.return_value = mock_historical_data
            mock_get_service.return_value = mock_service

            response = client.get(
                f"/market-data/historical/AAPL?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 10

    @pytest.mark.asyncio
    async def test_get_historical_data_invalid_date_range(self, client):
        """Test get_historical_data validates date range (start >= end)."""
        end_date = datetime.utcnow()
        start_date = end_date + timedelta(days=1)  # Start after end

        response = client.get(
            f"/market-data/historical/AAPL?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "before end date" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_historical_data_exceeds_max_days(self, client):
        """Test get_historical_data rejects ranges > 365 days."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=400)  # More than 365 days

        response = client.get(
            f"/market-data/historical/AAPL?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_feed_config_success(self, client, mock_feed_config):
        """Test create_feed_config creates configuration."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.add_feed_config.return_value = mock_feed_config.id
            mock_get_service.return_value = mock_service

            response = client.post(
                "/market-data/feeds",
                json={
                    "name": "Test Feed",
                    "feed_type": "REST_API",
                    "base_url": "https://api.example.com",
                    "rate_limit": 60,
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "Test Feed"

    @pytest.mark.asyncio
    async def test_create_feed_config_invalid_rate_limit(self, client):
        """Test create_feed_config validates rate_limit range (1-3600)."""
        response = client.post(
            "/market-data/feeds",
            json={
                "name": "Test Feed",
                "feed_type": "REST_API",
                "base_url": "https://api.example.com",
                "rate_limit": 5000,  # Exceeds max of 3600
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_feed_config_invalid_timeout(self, client):
        """Test create_feed_config validates timeout_seconds range (1-300)."""
        response = client.post(
            "/market-data/feeds",
            json={
                "name": "Test Feed",
                "feed_type": "REST_API",
                "base_url": "https://api.example.com",
                "timeout_seconds": 500,  # Exceeds max of 300
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_feed_configs_success(self, client, mock_feed_config):
        """Test list_feed_configs returns all configurations."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_feed_configs.return_value = [mock_feed_config]
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/feeds")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_get_feed_config_success(self, client, mock_feed_config):
        """Test get_feed_config returns configuration."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_feed_config.return_value = mock_feed_config
            mock_get_service.return_value = mock_service

            response = client.get(f"/market-data/feeds/{mock_feed_config.id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "Test Feed"

    @pytest.mark.asyncio
    async def test_get_feed_config_not_found(self, client):
        """Test get_feed_config returns 404 for non-existent config."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_feed_config.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get(f"/market-data/feeds/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_connect_feed_success(self, client, mock_feed_config):
        """Test connect_feed connects to feed."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.connect_feed.return_value = True
            mock_get_service.return_value = mock_service

            response = client.post(f"/market-data/feeds/{mock_feed_config.id}/connect")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_disconnect_feed_success(self, client, mock_feed_config):
        """Test disconnect_feed disconnects from feed."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.disconnect_feed.return_value = True
            mock_get_service.return_value = mock_service

            response = client.post(f"/market-data/feeds/{mock_feed_config.id}/disconnect")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_subscribe_to_symbols_success(self, client):
        """Test subscribe_to_symbols subscribes to symbols."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.subscribe_to_symbols.return_value = True
            mock_get_service.return_value = mock_service

            response = client.post(
                "/market-data/subscribe",
                json={"symbols": ["AAPL", "MSFT"], "frequency": "REAL_TIME"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_service_status_success(self, client):
        """Test get_service_status returns service status."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_service_status.return_value = {
                "status": "operational",
                "feeds_active": 3,
            }
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/status")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "operational"

    @pytest.mark.asyncio
    async def test_clear_cache_success(self, client):
        """Test clear_cache clears cached data."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.clear_cache.return_value = None
            mock_get_service.return_value = mock_service

            response = client.post("/market-data/cache/clear")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_cache_stats_success(self, client):
        """Test get_cache_stats returns cache metrics."""
        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_cache_stats.return_value = {"cached_quotes": 100, "cache_size_mb": 1.5}
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/cache/stats")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "data" in data


class TestErrorHandling:
    """Test error handling in market data API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_quote_timeout(self, client):
        """Test get_quote handles timeout errors."""
        import asyncio

        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_quote.side_effect = asyncio.TimeoutError()
            mock_get_service.return_value = mock_service

            response = client.get("/market-data/quotes/AAPL")
            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    @pytest.mark.asyncio
    async def test_get_historical_data_connection_error(self, client):
        """Test get_historical_data handles connection errors."""
        from requests.exceptions import ConnectionError

        with patch("app.presentation.api.market_data.get_market_data_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_historical_data.side_effect = ConnectionError("Connection failed")
            mock_get_service.return_value = mock_service

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=10)

            response = client.get(
                f"/market-data/historical/AAPL?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
