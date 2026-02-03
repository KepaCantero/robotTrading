"""
Tests for assets API endpoints.

Tests the assets.py module which provides REST API endpoints for
managing assets, identifying liquid assets, and retrieving asset rankings.

GAP Coverage:
- API-006: Test coverage for assets endpoints
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.api.assets import (
    get_assets_overview,
    get_liquid_assets,
    get_asset_rankings_by_class,
    get_asset_details,
    get_liquidity_metrics,
    filter_assets,
    refresh_liquidity_data,
    get_asset_universe,
    identify_liquid_assets,
    filter_assets_by_class,
    get_universe_summary,
    get_asset_stats,
)
from app.models.assets import AssetClass, AssetFilter, Exchange


class TestAssetsEndpoints:
    """Test suite for assets API endpoints."""

    # Fixtures
    @pytest.fixture
    def mock_service(self):
        """Create a mock asset identification service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_asset(self):
        """Create a mock asset."""
        asset = Mock()
        asset.symbol = "AAPL"
        asset.name = "Apple Inc."
        asset.asset_class = AssetClass.EQUITY
        asset.exchange = Exchange.NASDAQ
        asset.liquidity_score = 95.5
        asset.avg_volume = Decimal("50000000")
        asset.avg_spread = Decimal("0.01")
        asset.market_cap = Decimal("2500000000000")
        asset.min_trade_size = Decimal("1")
        asset.max_trade_size = Decimal("10000")
        asset.tick_size = Decimal("0.01")
        asset.is_active = True
        asset.last_updated = datetime.utcnow()
        asset.metadata = {"sector": "Technology"}
        return asset

    @pytest.fixture
    def mock_liquidity_metrics(self):
        """Create a mock liquidity metrics."""
        metrics = Mock()
        metrics.symbol = "AAPL"
        metrics.overall_liquidity_score = 95.5
        metrics.volume_score = 90.0
        metrics.spread_score = 95.0
        metrics.avg_volume_30d = Decimal("50000000")
        metrics.avg_spread_30d = Decimal("0.01")
        metrics.current_spread = Decimal("0.01")
        metrics.volume_volatility = 0.15
        metrics.price_volatility = 0.20
        metrics.timestamp = datetime.utcnow()
        return metrics

    @pytest.fixture
    def mock_ranking(self):
        """Create a mock asset ranking."""
        ranking = Mock()
        ranking.ranking_date = datetime.utcnow()
        ranking.rankings = [
            {"symbol": "AAPL", "rank": 1, "score": 95.5},
            {"symbol": "MSFT", "rank": 2, "score": 94.0},
        ]
        return ranking

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/assets/"
        request.url.path = "/assets/"
        return request

    # Tests for get_assets_overview
    @pytest.mark.asyncio
    async def test_get_assets_overview_success(self, mock_service, mock_request):
        """Test get_assets_overview returns all asset class summaries."""
        # Setup mock
        mock_service.get_universe_summary = AsyncMock(
            return_value={
                "total_assets": 100,
                "avg_liquidity_score": 75.0,
                "top_assets": [],
            }
        )

        response = await get_assets_overview(
            http_request=mock_request,
            service=mock_service,
        )

        # Verify response
        assert response["success"] is True
        assert "overview" in response
        assert "timestamp" in response
        assert len(response["overview"]) == len(AssetClass)

    @pytest.mark.asyncio
    async def test_get_assets_overview_timeout(self, mock_service, mock_request):
        """Test get_assets_overview handles timeout with 504 status."""
        # Setup mock to timeout
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return {}

        mock_service.get_universe_summary = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_assets_overview(
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504
        assert "Timeout" in str(exc_info.value.detail)

    # Tests for get_liquid_assets
    @pytest.mark.asyncio
    async def test_get_liquid_assets_valid_limit(self, mock_service, mock_asset, mock_request):
        """Test get_liquid_assets with valid limit."""
        # Setup mock
        mock_service.get_top_liquid_assets = AsyncMock(return_value=[mock_asset])

        response = await get_liquid_assets(
            asset_class=AssetClass.EQUITY,
            limit=20,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert response["asset_class"] == AssetClass.EQUITY.value
        assert response["limit"] == 20
        assert response["count"] == 1
        assert len(response["assets"]) == 1
        assert response["assets"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_liquid_assets_timeout(self, mock_service, mock_request):
        """Test get_liquid_assets handles timeout."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return []

        mock_service.get_top_liquid_assets = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_liquid_assets(
                asset_class=AssetClass.EQUITY,
                limit=20,
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    # Tests for get_asset_details
    @pytest.mark.asyncio
    async def test_get_asset_details_found(self, mock_service, mock_asset, mock_request):
        """Test get_asset_details returns asset for valid symbol."""
        mock_service.get_asset_details = AsyncMock(return_value=mock_asset)

        response = await get_asset_details(
            symbol="aapl",
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert response["asset"]["symbol"] == "AAPL"  # Uppercase
        assert response["asset"]["name"] == "Apple Inc."

    @pytest.mark.asyncio
    async def test_get_asset_details_not_found(self, mock_service, mock_request):
        """Test get_asset_details returns 404 for non-existent symbol."""
        mock_service.get_asset_details = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_details(
                symbol="NONEXISTENT",
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404
        assert "NONEXISTENT not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_asset_details_symbol_uppercase(self, mock_service, mock_asset, mock_request):
        """Test get_asset_details converts symbol to uppercase."""
        mock_service.get_asset_details = AsyncMock(return_value=mock_asset)

        await get_asset_details(
            symbol="aapl",
            http_request=mock_request,
            service=mock_service,
        )

        # Verify service was called with uppercase
        mock_service.get_asset_details.assert_called_once_with("AAPL")

    # Tests for get_liquidity_metrics
    @pytest.mark.asyncio
    async def test_get_liquidity_metrics_found(self, mock_service, mock_liquidity_metrics, mock_request):
        """Test get_liquidity_metrics returns metrics for valid symbol."""
        mock_service.get_liquidity_metrics = AsyncMock(return_value=mock_liquidity_metrics)

        response = await get_liquidity_metrics(
            symbol="aapl",
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "metrics" in response
        assert response["metrics"]["symbol"] == "AAPL"
        assert response["metrics"]["liquidity_score"] == 95.5

    @pytest.mark.asyncio
    async def test_get_liquidity_metrics_not_found(self, mock_service, mock_request):
        """Test get_liquidity_metrics returns 404 for non-existent symbol."""
        mock_service.get_liquidity_metrics = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_liquidity_metrics(
                symbol="NONEXISTENT",
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 404

    # Tests for get_asset_rankings_by_class
    @pytest.mark.asyncio
    async def test_get_asset_rankings_by_class_success(self, mock_service, mock_ranking, mock_request):
        """Test get_asset_rankings_by_class returns rankings."""
        mock_service.get_asset_rankings = AsyncMock(return_value=mock_ranking)

        response = await get_asset_rankings_by_class(
            asset_class=AssetClass.EQUITY,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert response["asset_class"] == AssetClass.EQUITY.value
        assert "ranking_date" in response
        assert "rankings" in response
        assert response["count"] == 2

    # Tests for filter_assets
    @pytest.mark.asyncio
    async def test_filter_assets_with_criteria(self, mock_service, mock_asset, mock_request):
        """Test filter_assets with various filter criteria."""
        filter_criteria = AssetFilter(
            min_liquidity_score=Decimal("70.0"),
            min_volume=Decimal("1000000"),
            max_spread=Decimal("0.05"),
            active_only=True,
        )

        mock_service.filter_assets = AsyncMock(return_value=[mock_asset])

        response = await filter_assets(
            filter_criteria=filter_criteria,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "filter_criteria" in response
        assert response["filter_criteria"]["min_liquidity_score"] == 70.0
        assert response["filter_criteria"]["active_only"] is True
        assert response["count"] == 1

    # Tests for identify_liquid_assets
    @pytest.mark.asyncio
    async def test_identify_liquid_assets_success(self, mock_service, mock_asset, mock_request):
        """Test identify_liquid_assets returns identified assets."""
        mock_service.identify_liquid_assets = AsyncMock(return_value=[mock_asset])
        mock_service.update_asset_universe = Mock()

        response = await identify_liquid_assets(
            asset_class=AssetClass.EQUITY,
            limit=20,
            http_request=mock_request,
            background_tasks=Mock(),
            service=mock_service,
        )

        assert response["success"] is True
        assert response["asset_class"] == AssetClass.EQUITY.value
        assert response["count"] == 1

    @pytest.mark.asyncio
    async def test_identify_liquid_assets_longer_timeout(self, mock_service, mock_request):
        """Test identify_liquid_assets has longer timeout for expensive operations."""
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(31)  # Less than 60 second timeout but more than 30
            return []

        mock_service.identify_liquid_assets = slow_operation

        # Should not timeout with 60 second limit
        response = await identify_liquid_assets(
            asset_class=AssetClass.EQUITY,
            limit=20,
            http_request=mock_request,
            background_tasks=Mock(),
            service=mock_service,
        )

        assert response["success"] is True

    # Tests for refresh_liquidity_data
    @pytest.mark.asyncio
    async def test_refresh_liquidity_data_starts_background_task(self, mock_service, mock_request):
        """Test refresh_liquidity_data schedules background task."""
        mock_service.refresh_liquidity_data = Mock()
        background_tasks = Mock()

        response = await refresh_liquidity_data(
            http_request=mock_request,
            background_tasks=background_tasks,
            service=mock_service,
        )

        assert response["success"] is True
        assert "refresh started" in response["message"].lower()
        background_tasks.add_task.assert_called_once_with(mock_service.refresh_liquidity_data)

    # Tests for get_asset_universe
    @pytest.mark.asyncio
    async def test_get_asset_universe_by_class(self, mock_service, mock_request):
        """Test get_asset_universe for specific asset class."""
        mock_service.get_asset_universe = AsyncMock(return_value={"AAPL": {}})

        response = await get_asset_universe(
            asset_class=AssetClass.EQUITY,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "universe" in response

    @pytest.mark.asyncio
    async def test_get_asset_universe_all_classes(self, mock_service, mock_request):
        """Test get_asset_universe for all asset classes."""
        mock_service.get_asset_universe = AsyncMock(return_value={"AAPL": {}})

        response = await get_asset_universe(
            asset_class=None,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "universe" in response
        # Should have called get_asset_universe for each asset class
        assert mock_service.get_asset_universe.call_count == len(AssetClass)

    # Tests for filter_assets_by_class
    @pytest.mark.asyncio
    async def test_filter_assets_by_class(self, mock_service, mock_asset, mock_request):
        """Test filter_assets_by_class filters correctly."""
        filter_criteria = AssetFilter(
            min_liquidity_score=Decimal("70.0"),
            min_volume=Decimal("1000000"),
            max_spread=Decimal("0.05"),
            active_only=True,
        )

        mock_service.filter_assets = AsyncMock(return_value=[mock_asset])

        response = await filter_assets_by_class(
            asset_class=AssetClass.EQUITY,
            filter_criteria=filter_criteria,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert response["asset_class"] == AssetClass.EQUITY.value
        assert response["count"] == 1

    # Tests for get_universe_summary
    @pytest.mark.asyncio
    async def test_get_universe_summary(self, mock_service, mock_request):
        """Test get_universe_summary returns summary."""
        mock_service.get_universe_summary = AsyncMock(
            return_value={
                "total_assets": 100,
                "avg_liquidity_score": 75.0,
                "top_assets": [],
            }
        )

        response = await get_universe_summary(
            asset_class=AssetClass.EQUITY,
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "universe_summary" in response

    # Tests for get_asset_stats
    @pytest.mark.asyncio
    async def test_get_asset_stats(self, mock_service, mock_request):
        """Test get_asset_stats returns statistics."""
        mock_service.get_universe_summary = AsyncMock(
            return_value={
                "total_assets": 100,
                "avg_liquidity_score": 75.0,
                "top_assets": [],
            }
        )

        response = await get_asset_stats(
            http_request=mock_request,
            service=mock_service,
        )

        assert response["success"] is True
        assert "stats" in response
        assert "overall_stats" in response["stats"]
        assert response["stats"]["total_asset_classes"] == len(AssetClass)

    # Tests for timeout handling on various endpoints
    @pytest.mark.asyncio
    async def test_timeout_on_get_asset_rankings_by_class(self, mock_service, mock_request):
        """Test timeout handling on get_asset_rankings_by_class."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return Mock()

        mock_service.get_asset_rankings = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_rankings_by_class(
                asset_class=AssetClass.EQUITY,
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_on_filter_assets(self, mock_service, mock_request):
        """Test timeout handling on filter_assets."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return []

        mock_service.filter_assets = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await filter_assets(
                filter_criteria=AssetFilter(
                    min_liquidity_score=Decimal("70.0"),
                    min_volume=Decimal("1000000"),
                    max_spread=Decimal("0.05"),
                    active_only=True,
                ),
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_on_get_asset_universe(self, mock_service, mock_request):
        """Test timeout handling on get_asset_universe."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return {}

        mock_service.get_asset_universe = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_universe(
                asset_class=AssetClass.EQUITY,
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_on_filter_assets_by_class(self, mock_service, mock_request):
        """Test timeout handling on filter_assets_by_class."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return []

        mock_service.filter_assets = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await filter_assets_by_class(
                asset_class=AssetClass.EQUITY,
                filter_criteria=AssetFilter(
                    min_liquidity_score=Decimal("70.0"),
                    min_volume=Decimal("1000000"),
                    max_spread=Decimal("0.05"),
                    active_only=True,
                ),
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_on_get_universe_summary(self, mock_service, mock_request):
        """Test timeout handling on get_universe_summary."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return {}

        mock_service.get_universe_summary = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_universe_summary(
                asset_class=AssetClass.EQUITY,
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_on_get_asset_stats(self, mock_service, mock_request):
        """Test timeout handling on get_asset_stats."""
        async def timeout_mock(*args, **kwargs):
            await asyncio.sleep(31)
            return {}

        mock_service.get_universe_summary = timeout_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_asset_stats(
                http_request=mock_request,
                service=mock_service,
            )

        assert exc_info.value.status_code == 504


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
