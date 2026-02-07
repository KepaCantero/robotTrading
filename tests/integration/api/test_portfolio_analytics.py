"""
Portfolio Analytics API Endpoints Test Suite

Tests for portfolio analytics API endpoints.

Reference: API-004 - Test coverage for API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.portfolio_analytics import router
from app.models.portfolio_analytics import (
    PerformanceMetrics,
    PerformancePeriod,
    PortfolioAllocation,
    PortfolioAnalytics,
    PortfolioComparison,
    PortfolioRebalance,
    RiskLevel,
    RiskMetrics,
)


class TestPortfolioAnalyticsAPIEndpoints:
    """Test portfolio analytics API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_portfolio_id(self):
        """Create mock portfolio ID."""
        return uuid4()

    @pytest.fixture
    def mock_performance_metrics(self, mock_portfolio_id):
        """Create mock performance metrics."""
        return PerformanceMetrics(
            portfolio_id=mock_portfolio_id,
            period=PerformancePeriod.MONTHLY,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            total_return=Decimal("10.5"),
            annualized_return=Decimal("12.3"),
            cumulative_return=Decimal("15.5"),
            total_value=Decimal("100000.00"),
            cash_value=Decimal("10000.00"),
            equity_value=Decimal("90000.00"),
            volatility=Decimal("15.2"),
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("2.1"),
            max_drawdown=Decimal("-8.5"),
            var_95=Decimal("-2.5"),
            var_99=Decimal("-4.0"),
            calmar_ratio=Decimal("1.4"),
            information_ratio=Decimal("0.8"),
            treynor_ratio=Decimal("1.2"),
            jensen_alpha=Decimal("0.5"),
            position_count=5,
        )

    @pytest.fixture
    def mock_risk_metrics(self, mock_portfolio_id):
        """Create mock risk metrics."""
        return RiskMetrics(
            portfolio_id=mock_portfolio_id,
            daily_volatility=Decimal("0.8"),
            annualized_volatility=Decimal("15.2"),
            realized_volatility=Decimal("14.5"),
            downside_deviation=Decimal("0.6"),
            semi_variance=Decimal("0.4"),
            lower_partial_moment=Decimal("0.5"),
            skewness=Decimal("-0.3"),
            kurtosis=Decimal("3.2"),
            tail_ratio=Decimal("0.9"),
            herfindahl_index=Decimal("0.15"),
            effective_number_of_positions=Decimal("6.5"),
            largest_position_weight=Decimal("25.0"),
            average_correlation=Decimal("0.4"),
            diversification_ratio=Decimal("1.2"),
        )

    @pytest.fixture
    def mock_portfolio_analytics(
        self, mock_portfolio_id, mock_performance_metrics, mock_risk_metrics
    ):
        """Create mock portfolio analytics."""
        return PortfolioAnalytics(
            portfolio_id=mock_portfolio_id,
            performance_metrics=mock_performance_metrics,
            risk_metrics=mock_risk_metrics,
            risk_level=RiskLevel.MODERATE,
            risk_score=Decimal("55.0"),
            health_score=Decimal("75.0"),
            diversification_score=Decimal("70.0"),
            liquidity_score=Decimal("80.0"),
            recommendations=["Increase diversification", "Reduce cash allocation"],
            warnings=["High volatility detected"],
        )

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics_success(
        self, client, mock_portfolio_id, mock_performance_metrics
    ):
        """Test calculate_performance_metrics returns valid metrics."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.calculate_performance_metrics.return_value = mock_performance_metrics
            mock_get_service.return_value = mock_service

            response = client.post(
                "/portfolio-analytics/performance-metrics",
                json={
                    "portfolio_id": str(mock_portfolio_id),
                    "period": "MONTHLY",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_value"] == 100000.00

    @pytest.mark.asyncio
    async def test_get_performance_metrics_success(
        self, client, mock_portfolio_id, mock_performance_metrics
    ):
        """Test get_performance_metrics returns valid metrics."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.calculate_performance_metrics.return_value = mock_performance_metrics
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/performance-metrics/{mock_portfolio_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["sharpe_ratio"] == 1.5

    @pytest.mark.asyncio
    async def test_get_risk_metrics_success(self, client, mock_portfolio_id, mock_risk_metrics):
        """Test get_risk_metrics returns valid risk metrics."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.calculate_risk_metrics.return_value = mock_risk_metrics
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/risk-metrics/{mock_portfolio_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["var_95"] == -2.5

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_success(
        self, client, mock_portfolio_id, mock_portfolio_analytics
    ):
        """Test get_portfolio_analytics returns comprehensive analytics."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_portfolio_analytics.return_value = mock_portfolio_analytics
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/analytics/{mock_portfolio_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["risk_level"] == "moderate"
            assert data["data"]["health_score"] == 75.0

    @pytest.mark.asyncio
    async def test_get_portfolio_allocation_success(self, client, mock_portfolio_id):
        """Test get_portfolio_allocation returns allocation breakdown."""
        mock_allocation = PortfolioAllocation(
            portfolio_id=mock_portfolio_id,
            equity_allocation=Decimal("60.0"),
            fixed_income_allocation=Decimal("20.0"),
            cash_allocation=Decimal("10.0"),
            alternative_allocation=Decimal("10.0"),
            domestic_allocation=Decimal("70.0"),
            international_allocation=Decimal("30.0"),
        )

        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.analyze_portfolio_allocation.return_value = mock_allocation
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/allocation/{mock_portfolio_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["equity_allocation"] == 60.0

    @pytest.mark.asyncio
    async def test_get_rebalance_recommendation_success(self, client, mock_portfolio_id):
        """Test get_rebalance_recommendation returns valid recommendations."""
        # Create current and target allocations
        current_allocation = PortfolioAllocation(
            portfolio_id=mock_portfolio_id,
            equity_allocation=Decimal("70.0"),
            fixed_income_allocation=Decimal("20.0"),
            cash_allocation=Decimal("10.0"),
            alternative_allocation=Decimal("0.0"),
            domestic_allocation=Decimal("100.0"),
            international_allocation=Decimal("0.0"),
        )
        target_allocation = PortfolioAllocation(
            portfolio_id=mock_portfolio_id,
            equity_allocation=Decimal("60.0"),
            fixed_income_allocation=Decimal("30.0"),
            cash_allocation=Decimal("10.0"),
            alternative_allocation=Decimal("0.0"),
            domestic_allocation=Decimal("100.0"),
            international_allocation=Decimal("0.0"),
        )

        mock_rebalance = PortfolioRebalance(
            portfolio_id=mock_portfolio_id,
            trigger_reason="Allocation drift",
            trigger_threshold=Decimal("5.0"),
            current_allocation=current_allocation,
            target_allocation=target_allocation,
            rebalance_actions=[],
            risk_impact=Decimal("0.5"),
            return_impact=Decimal("0.3"),
        )

        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_rebalance_recommendation.return_value = mock_rebalance
            mock_get_service.return_value = mock_service

            response = client.post(
                "/portfolio-analytics/rebalance",
                json={
                    "portfolio_id": str(mock_portfolio_id),
                    "target_equity_allocation": "60.0",
                    "target_cash_allocation": "10.0",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            # The PortfolioRebalance model doesn't have a rebalance_needed field
            assert "current_allocation" in data["data"]

    @pytest.mark.asyncio
    async def test_compare_portfolios_success(
        self, client, mock_performance_metrics, mock_risk_metrics
    ):
        """Test compare_portfolios returns comparison data."""
        portfolio_ids = [uuid4(), uuid4()]

        # Create performance and risk metrics for each portfolio
        perf1 = mock_performance_metrics.model_copy(update={"portfolio_id": portfolio_ids[0]})
        perf2 = mock_performance_metrics.model_copy(update={"portfolio_id": portfolio_ids[1]})
        risk1 = mock_risk_metrics.model_copy(update={"portfolio_id": portfolio_ids[0]})
        risk2 = mock_risk_metrics.model_copy(update={"portfolio_id": portfolio_ids[1]})

        mock_comparison = PortfolioComparison(
            portfolio_ids=portfolio_ids,
            performance_comparison={
                str(portfolio_ids[0]): perf1,
                str(portfolio_ids[1]): perf2,
            },
            risk_comparison={
                str(portfolio_ids[0]): risk1,
                str(portfolio_ids[1]): risk2,
            },
            performance_ranking=[
                (portfolio_ids[0], Decimal("10.5")),
                (portfolio_ids[1], Decimal("8.3")),
            ],
            risk_ranking=[
                (portfolio_ids[1], Decimal("5.0")),
                (portfolio_ids[0], Decimal("6.0")),
            ],
            sharpe_ranking=[
                (portfolio_ids[0], Decimal("1.5")),
                (portfolio_ids[1], Decimal("1.2")),
            ],
            best_performer=portfolio_ids[0],
            lowest_risk=portfolio_ids[1],
            best_risk_adjusted=portfolio_ids[0],
            comparison_summary="Portfolio 1 outperforms Portfolio 2",
        )

        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.compare_portfolios.return_value = mock_comparison
            mock_get_service.return_value = mock_service

            response = client.post(
                "/portfolio-analytics/compare",
                json={"portfolio_ids": [str(pid) for pid in portfolio_ids]},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_analytics_summary_success(
        self, client, mock_portfolio_id, mock_portfolio_analytics
    ):
        """Test get_analytics_summary returns summary data."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.generate_portfolio_analytics.return_value = mock_portfolio_analytics
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/summary/{mock_portfolio_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "total_value" in data["data"]
            assert "risk_score" in data["data"]

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health_check returns healthy status."""
        response = client.get("/portfolio-analytics/health-check")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "portfolio-analytics"


class TestErrorHandling:
    """Test error handling in portfolio analytics API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics_timeout(self, client):
        """Test calculate_performance_metrics handles timeout errors."""
        import asyncio

        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.calculate_performance_metrics.side_effect = asyncio.TimeoutError()
            mock_get_service.return_value = mock_service

            response = client.post(
                "/portfolio-analytics/performance-metrics",
                json={"portfolio_id": str(uuid4()), "period": "MONTHLY"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "Timeout" in data["error"]

    @pytest.mark.asyncio
    async def test_get_risk_metrics_connection_error(self, client):
        """Test get_risk_metrics handles connection errors."""
        with patch(
            "app.api.portfolio_analytics.get_portfolio_analytics_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.calculate_risk_metrics.side_effect = ConnectionError("Connection failed")
            mock_get_service.return_value = mock_service

            response = client.get(f"/portfolio-analytics/risk-metrics/{uuid4()}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
