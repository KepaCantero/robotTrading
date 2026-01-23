"""
Tests for Asset API endpoints

This module tests the FastAPI endpoints for asset management,
including edge cases, error handling, and data validation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.assets import router
from app.models.assets import (
    Asset,
    AssetClass,
    AssetRanking,
    AssetUniverse,
    Exchange,
    LiquidityMetrics,
)
from app.services.asset_identification import get_asset_identification_service

# Create test app
app = FastAPI()

# Override dependencies for testing


def override_get_asset_identification_service():
    return AsyncMock()


app.dependency_overrides[get_asset_identification_service] = (
    override_get_asset_identification_service
)

app.include_router(router)


class TestAssetAPI:
    """Test Asset API endpoints."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    def _override_service(self, mock_service):
        """Helper to override the service dependency."""
        app.dependency_overrides[get_asset_identification_service] = lambda: mock_service
        return mock_service

    def _cleanup_overrides(self):
        """Helper to clean up dependency overrides."""
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_asset(self):
        """Sample asset for testing."""
        return Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("50000000"),
            avg_spread=Decimal("0.01"),
            market_cap=Decimal("3000000000000"),
            liquidity_score=85.0,
        )

    @pytest.fixture
    def sample_liquidity_metrics(self):
        """Sample liquidity metrics for testing."""
        return LiquidityMetrics(
            symbol="AAPL",
            daily_volume=Decimal("50000000"),
            avg_volume_30d=Decimal("45000000"),
            volume_volatility=0.15,
            current_spread=Decimal("0.01"),
            avg_spread_30d=Decimal("0.012"),
            spread_volatility=0.02,
            current_price=Decimal("150.0"),
            price_volatility=0.12,
            volume_score=85.0,
            spread_score=80.0,
            overall_liquidity_score=82.5,
        )

    @pytest.fixture
    def sample_asset_universe(self, sample_asset):
        """Sample asset universe for testing."""
        universe = AssetUniverse(asset_class=AssetClass.EQUITY, assets=[sample_asset], top_n=20)
        return universe

    @pytest.fixture
    def mock_service(self):
        """Mock asset identification service."""
        service = AsyncMock()
        return service

    def test_get_assets_overview_success(self, client, mock_service):
        """Test successful assets overview retrieval."""
        # Mock service response
        mock_service.get_universe_summary.return_value = {
            "total_assets": 100,
            "liquid_assets": 20,
            "avg_liquidity_score": 75.5,
        }

        try:
            self._override_service(mock_service)
            response = client.get("/assets/")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "overview" in data
            assert "timestamp" in data
        finally:
            self._cleanup_overrides()

    def test_get_assets_overview_service_error(self, client, mock_service):
        """Test assets overview with service error."""
        # Mock service to raise exception
        mock_service.get_universe_summary.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting assets overview" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_liquid_assets_success(self, client, mock_service, sample_asset_universe):
        """Test successful liquid assets retrieval."""
        # Mock service response - the API calls get_top_liquid_assets, not
        # get_liquid_assets
        mock_service.get_top_liquid_assets.return_value = sample_asset_universe.assets

        try:
            self._override_service(mock_service)
            response = client.get("/assets/liquid/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "assets" in data
            assert data["asset_class"] == "equity"
            assert data["count"] == len(sample_asset_universe.assets)
        finally:
            self._cleanup_overrides()

    def test_get_liquid_assets_invalid_class(self, client):
        """Test liquid assets with invalid asset class."""
        response = client.get("/assets/liquid/invalid_class")

        assert response.status_code == 422  # Validation error

    def test_get_liquid_assets_service_error(self, client, mock_service):
        """Test liquid assets with service error."""
        # Mock service to raise exception
        mock_service.get_top_liquid_assets.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/liquid/equity")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting liquid assets" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_asset_details_success(self, client, mock_service, sample_asset):
        """Test successful asset details retrieval."""
        # Mock service response
        mock_service.get_asset_details.return_value = sample_asset

        try:
            self._override_service(mock_service)
            response = client.get("/assets/AAPL")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "asset" in data
            assert data["asset"]["symbol"] == "AAPL"
        finally:
            self._cleanup_overrides()

    def test_get_asset_details_not_found(self, client, mock_service):
        """Test asset details with asset not found."""
        # Mock service to return None
        mock_service.get_asset_details.return_value = None

        try:
            self._override_service(mock_service)
            response = client.get("/assets/NONEXISTENT")

            assert response.status_code == 404
            data = response.json()
            assert "Asset NONEXISTENT not found" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_asset_details_service_error(self, client, mock_service):
        """Test asset details with service error."""
        # Mock service to raise exception
        mock_service.get_asset_details.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/AAPL")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting asset details" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_liquidity_metrics_success(self, client, mock_service, sample_liquidity_metrics):
        """Test successful liquidity metrics retrieval."""
        # Mock service response
        mock_service.get_liquidity_metrics.return_value = sample_liquidity_metrics

        try:
            self._override_service(mock_service)
            response = client.get("/assets/AAPL/liquidity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "metrics" in data
            assert data["metrics"]["symbol"] == "AAPL"
        finally:
            self._cleanup_overrides()

    def test_get_liquidity_metrics_not_found(self, client, mock_service):
        """Test liquidity metrics with asset not found."""
        # Mock service to return None
        mock_service.get_liquidity_metrics.return_value = None

        try:
            self._override_service(mock_service)
            response = client.get("/assets/NONEXISTENT/liquidity")

            assert response.status_code == 404
            data = response.json()
            assert "Liquidity metrics for NONEXISTENT not found" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_liquidity_metrics_service_error(self, client, mock_service):
        """Test liquidity metrics with service error."""
        # Mock service to raise exception
        mock_service.get_liquidity_metrics.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/AAPL/liquidity")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting liquidity metrics" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_get_asset_rankings_success(self, client, mock_service):
        """Test successful asset rankings retrieval."""
        # Create mock asset ranking data
        from datetime import datetime

        from app.models.assets import AssetRanking

        mock_ranking = AssetRanking(
            asset_class=AssetClass.EQUITY,
            ranking_date=datetime.utcnow(),
            rankings=[
                {"symbol": "AAPL", "rank": 1, "liquidity_score": 95.0},
                {"symbol": "MSFT", "rank": 2, "liquidity_score": 90.0},
                {"symbol": "GOOGL", "rank": 3, "liquidity_score": 85.0},
            ],
        )
        # Mock service response
        mock_service.get_asset_rankings.return_value = mock_ranking

        try:
            self._override_service(mock_service)
            response = client.get("/assets/rankings/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "rankings" in data
            assert len(data["rankings"]) == 3
        finally:
            self._cleanup_overrides()

    def test_get_asset_rankings_invalid_class(self, client):
        """Test asset rankings with invalid asset class."""
        response = client.get("/assets/rankings/invalid_class")

        assert response.status_code == 422  # Validation error

    def test_get_asset_rankings_service_error(self, client, mock_service):
        """Test asset rankings with service error."""
        # Mock service to raise exception
        mock_service.get_asset_rankings.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/rankings/equity")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting asset rankings" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_filter_assets_success(self, client, mock_service, sample_asset):
        """Test successful asset filtering."""
        # Mock service response
        mock_service.filter_assets.return_value = [sample_asset]

        try:
            self._override_service(mock_service)
            response = client.post(
                "/assets/filter",
                json={
                    "asset_class": "equity",
                    "min_liquidity_score": 80.0,
                    "max_spread": 0.02,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "filtered_assets" in data
            assert len(data["filtered_assets"]) == 1
        finally:
            self._cleanup_overrides()

    def test_filter_assets_invalid_filter(self, client):
        """Test asset filtering with invalid filter data."""
        response = client.post(
            "/assets/filter",
            json={
                "asset_class": "invalid_class",
                "min_liquidity_score": -10.0,  # Invalid negative score
                "max_spread": -0.01,  # Invalid negative spread
            },
        )

        assert response.status_code == 422  # Validation error

    def test_filter_assets_service_error(self, client, mock_service):
        """Test asset filtering with service error."""
        # Mock service to raise exception
        mock_service.filter_assets.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.post(
                "/assets/filter",
                json={"asset_class": "equity", "min_liquidity_score": 80.0},
            )

            assert response.status_code == 500
            data = response.json()
            assert "Error filtering assets" in data["detail"]
        finally:
            self._cleanup_overrides()

    def test_refresh_liquidity_data_success(self, client, mock_service):
        """Test successful liquidity data refresh."""
        # Mock service response
        mock_service.refresh_liquidity_data.return_value = {"refreshed": 100}

        try:
            self._override_service(mock_service)
            response = client.post("/assets/refresh-liquidity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
            assert "refresh" in data["message"]
        finally:
            self._cleanup_overrides()

    def test_refresh_liquidity_data_service_error(self, client, mock_service):
        """Test liquidity data refresh with service error."""
        # Mock service to raise exception
        mock_service.refresh_liquidity_data.side_effect = Exception("Service error")

        with patch("app.api.assets.get_asset_identification_service", return_value=mock_service):
            response = client.post("/assets/refresh-liquidity")

            assert response.status_code == 500
            data = response.json()
            assert "Error refreshing liquidity data" in data["detail"]

    def test_get_asset_universe_success(self, client, mock_service, sample_asset_universe):
        """Test successful asset universe retrieval."""
        # Mock service response
        mock_service.get_asset_universe.return_value = sample_asset_universe

        try:
            self._override_service(mock_service)
            response = client.get("/assets/universe/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "universe_summary" in data
            assert isinstance(data["universe_summary"], list)
        finally:
            self._cleanup_overrides()

    def test_get_asset_universe_invalid_class(self, client):
        """Test asset universe with invalid asset class."""
        response = client.get("/assets/universe/invalid_class")

        assert response.status_code == 422  # Validation error

    def test_get_asset_universe_service_error(self, client, mock_service):
        """Test asset universe with service error."""
        # Mock service to raise exception
        mock_service.get_universe_summary.side_effect = Exception("Service error")

        try:
            self._override_service(mock_service)
            response = client.get("/assets/universe/equity")

            assert response.status_code == 500
            data = response.json()
            assert "Error getting universe summary" in data["detail"]
        finally:
            self._cleanup_overrides()


class TestAssetAPIEdgeCases:
    """Test Asset API edge cases and error scenarios."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    def _override_service(self, mock_service):
        """Helper to override the service dependency."""
        app.dependency_overrides[get_asset_identification_service] = lambda: mock_service
        return mock_service

    def _cleanup_overrides(self):
        """Helper to clean up dependency overrides."""
        app.dependency_overrides.clear()

    def test_get_assets_overview_empty_response(self, client):
        """Test assets overview with empty service response."""
        mock_service = AsyncMock()
        mock_service.get_universe_summary.return_value = {}

        with patch("app.api.assets.get_asset_identification_service", return_value=mock_service):
            response = client.get("/assets/")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "overview" in data

    def test_get_liquid_assets_empty_universe(self, client):
        """Test liquid assets with empty universe."""
        mock_service = AsyncMock()
        AssetUniverse(asset_class=AssetClass.EQUITY, assets=[], top_n=20)
        mock_service.get_top_liquid_assets.return_value = []

        try:
            self._override_service(mock_service)
            response = client.get("/assets/liquid/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["assets"]) == 0
        finally:
            self._cleanup_overrides()

    def test_get_asset_details_case_sensitivity(self, client):
        """Test asset details with case sensitivity."""
        mock_service = AsyncMock()
        mock_service.get_asset_details.return_value = None

        try:
            self._override_service(mock_service)
            # Test lowercase symbol
            response = client.get("/assets/aapl")
            assert response.status_code == 404

            # Test mixed case symbol
            response = client.get("/assets/AaPl")
            assert response.status_code == 404
        finally:
            self._cleanup_overrides()

    def test_get_liquidity_metrics_with_zero_values(self, client):
        """Test liquidity metrics with zero values."""
        mock_service = AsyncMock()
        zero_metrics = LiquidityMetrics(
            symbol="TEST",
            daily_volume=Decimal("0"),
            avg_volume_30d=Decimal("0"),
            volume_volatility=0.0,
            current_spread=Decimal("0"),
            avg_spread_30d=Decimal("0"),
            spread_volatility=0.0,
            current_price=Decimal("0"),
            price_volatility=0.0,
            volume_score=0.0,
            spread_score=0.0,
            overall_liquidity_score=0.0,
        )
        mock_service.get_liquidity_metrics.return_value = zero_metrics

        try:
            self._override_service(mock_service)
            response = client.get("/assets/TEST/liquidity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["metrics"]["liquidity_score"] == 0.0
        finally:
            self._cleanup_overrides()

    def test_filter_assets_with_extreme_values(self, client):
        """Test asset filtering with extreme values."""
        mock_service = AsyncMock()
        mock_service.filter_assets.return_value = []

        with patch("app.api.assets.get_asset_identification_service", return_value=mock_service):
            response = client.post(
                "/assets/filter",
                json={
                    "asset_class": "equity",
                    "min_liquidity_score": 100.0,  # Maximum possible score
                    "max_spread": 0.0,  # Minimum possible spread
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_asset_rankings_with_single_asset(self, client):
        """Test asset rankings with single asset."""
        mock_service = AsyncMock()
        ranking = AssetRanking(asset_class=AssetClass.EQUITY)
        ranking.add_ranking("AAPL", 85.0, 1, 80.0, 90.0)
        mock_service.get_asset_rankings.return_value = ranking

        try:
            self._override_service(mock_service)
            response = client.get("/assets/rankings/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["rankings"]) == 1
        finally:
            self._cleanup_overrides()

    def test_refresh_liquidity_data_with_zero_refreshed(self, client):
        """Test liquidity data refresh with zero refreshed assets."""
        mock_service = AsyncMock()
        mock_service.refresh_liquidity_data.return_value = {"refreshed": 0}

        try:
            self._override_service(mock_service)
            response = client.post("/assets/refresh-liquidity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "refresh" in data["message"]
        finally:
            self._cleanup_overrides()

    def test_get_asset_universe_with_large_dataset(self, client):
        """Test asset universe with large dataset."""
        mock_service = AsyncMock()
        # Create a large universe with 1000 assets
        large_assets = []
        for i in range(1000):
            asset = Asset(
                symbol=f"ASSET{i:04d}",
                name=f"Asset {i}",
                asset_class=AssetClass.EQUITY,
                exchange=Exchange.NASDAQ,
                avg_volume=Decimal("1000000"),
                avg_spread=Decimal("0.01"),
                liquidity_score=float(i % 100),
            )
            large_assets.append(asset)

        AssetUniverse(
            asset_class=AssetClass.EQUITY,
            assets=large_assets,
            top_n=100,  # Changed from 1000 to comply with model validation
        )
        mock_service.get_universe_summary.return_value = large_assets

        try:
            self._override_service(mock_service)
            response = client.get("/assets/universe/equity")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["universe_summary"]) == 1000
        finally:
            self._cleanup_overrides()
