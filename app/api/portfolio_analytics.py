"""
Portfolio Analytics API Endpoints

This module provides FastAPI endpoints for portfolio analytics including
performance metrics, risk analysis, and portfolio management features.

GAP Fixes:
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from . import audit_logger, get_correlation_id
from .security import rate_limit, require_auth, audit_log

from app.models.portfolio_analytics import (
    ExtendedPortfolio,
    PerformanceMetrics,
    PerformancePeriod,
    PortfolioAllocation,
    PortfolioAnalytics,
    PortfolioComparison,
    PortfolioRebalance,
    RiskMetrics,
)
from app.services.portfolio_analytics_service import (
    PortfolioAnalyticsService,
    get_portfolio_analytics_service,
)

router = APIRouter(prefix="/portfolio-analytics", tags=["Portfolio Analytics"])
logger = logging.getLogger(__name__)


# Request/Response Models
class PerformanceMetricsRequest(BaseModel):
    """Request model for performance metrics calculation."""

    portfolio_id: UUID = Field(..., description="Portfolio ID")
    period: PerformancePeriod = Field(
        default=PerformancePeriod.MONTHLY, description="Performance period"
    )
    start_date: Optional[datetime] = Field(None, description="Start date for calculation")
    end_date: Optional[datetime] = Field(None, description="End date for calculation")


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""

    success: bool = Field(..., description="Success status")
    data: Optional[PerformanceMetrics] = Field(None, description="Performance metrics data")
    error: Optional[str] = Field(None, description="Error message if any")


class RiskMetricsResponse(BaseModel):
    """Response model for risk metrics."""

    success: bool = Field(..., description="Success status")
    data: Optional[RiskMetrics] = Field(None, description="Risk metrics data")
    error: Optional[str] = Field(None, description="Error message if any")


class PortfolioAnalyticsResponse(BaseModel):
    """Response model for portfolio analytics."""

    success: bool = Field(..., description="Success status")
    data: Optional[PortfolioAnalytics] = Field(None, description="Portfolio analytics data")
    error: Optional[str] = Field(None, description="Error message if any")


class PortfolioAllocationResponse(BaseModel):
    """Response model for portfolio allocation."""

    success: bool = Field(..., description="Success status")
    data: Optional[PortfolioAllocation] = Field(None, description="Portfolio allocation data")
    error: Optional[str] = Field(None, description="Error message if any")


class RebalanceRequest(BaseModel):
    """Request model for rebalancing recommendations."""

    portfolio_id: UUID = Field(..., description="Portfolio ID")
    target_equity_allocation: Optional[Decimal] = Field(
        None, description="Target equity allocation percentage"
    )
    target_cash_allocation: Optional[Decimal] = Field(
        None, description="Target cash allocation percentage"
    )
    rebalance_threshold: Optional[Decimal] = Field(
        None, description="Rebalancing threshold percentage"
    )


class RebalanceResponse(BaseModel):
    """Response model for rebalancing recommendations."""

    success: bool = Field(..., description="Success status")
    data: Optional[PortfolioRebalance] = Field(None, description="Rebalancing recommendations")
    error: Optional[str] = Field(None, description="Error message if any")


class PortfolioComparisonRequest(BaseModel):
    """Request model for portfolio comparison."""

    portfolio_ids: List[UUID] = Field(..., description="Portfolio IDs to compare")


class PortfolioComparisonResponse(BaseModel):
    """Response model for portfolio comparison."""

    success: bool = Field(..., description="Success status")
    data: Optional[PortfolioComparison] = Field(None, description="Portfolio comparison data")
    error: Optional[str] = Field(None, description="Error message if any")


class AnalyticsSummaryResponse(BaseModel):
    """Response model for analytics summary."""

    success: bool = Field(..., description="Success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Analytics summary data")
    error: Optional[str] = Field(None, description="Error message if any")


# Mock portfolio data for demonstration
def _get_mock_portfolio(portfolio_id: UUID) -> ExtendedPortfolio:
    """Get mock portfolio data for demonstration."""
    from app.models.portfolio import AssetClass, Position

    # Create mock positions
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            realized_pnl=Decimal("0.00"),
            currency="USD",
            broker="mock",
        ),
        Position(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("300.00"),
            market_price=Decimal("310.00"),
            unrealized_pnl=Decimal("500.00"),
            realized_pnl=Decimal("0.00"),
            currency="USD",
            broker="mock",
        ),
        Position(
            symbol="GOOGL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("25"),
            avg_price=Decimal("2500.00"),
            market_price=Decimal("2550.00"),
            unrealized_pnl=Decimal("1250.00"),
            realized_pnl=Decimal("0.00"),
            currency="USD",
            broker="mock",
        ),
    ]

    # Calculate total value from positions and cash
    cash_amount = Decimal("10000.00")
    equity_value = Decimal("94750.00")  # Sum of position market values
    total_value = cash_amount + equity_value

    return ExtendedPortfolio(
        id=portfolio_id,
        name="Demo Portfolio",
        description="Demo portfolio for testing",
        cash=cash_amount,
        positions=positions,
        broker="mock",
        currency="USD",
        total_value=total_value,
        cash_balance=cash_amount,
    )


# API Endpoints


@router.post("/performance-metrics", response_model=PerformanceMetricsResponse)
@rate_limit(max_requests=50, window_seconds=60)
@require_auth()
@audit_log("performance_metrics_calculated", log_args=True)
async def calculate_performance_metrics(
    request: PerformanceMetricsRequest,
    http_request: Request,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Calculate performance metrics for a portfolio."""
    correlation_id = get_correlation_id()
    logger.info(
        "Calculating performance metrics",
        extra={
            "correlation_id": correlation_id,
            "portfolio_id": str(request.portfolio_id),
            "period": request.period.value,
        },
    )
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(request.portfolio_id)

        # Calculate performance metrics with timeout
        metrics = await asyncio.wait_for(
            analytics_service.calculate_performance_metrics(
                portfolio=portfolio,
                period=request.period,
                start_date=request.start_date,
                end_date=request.end_date,
            ),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        audit_logger.log_action(
            action="calculated_performance_metrics",
            method=http_request.method,
            path=http_request.url.path,
            details={"portfolio_id": str(request.portfolio_id), "period": request.period.value},
        )

        return PerformanceMetricsResponse(success=True, data=metrics)

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout calculating performance metrics",
            extra={
                "correlation_id": correlation_id,
                "portfolio_id": str(request.portfolio_id),
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type="TimeoutError",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        return PerformanceMetricsResponse(
            success=False, error=f"Timeout calculating performance metrics: {str(e)}"
        )
    except (ConnectionError, OSError) as e:
        logger.error(
            "Connection error calculating performance metrics",
            extra={
                "correlation_id": correlation_id,
                "portfolio_id": str(request.portfolio_id),
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        return PerformanceMetricsResponse(
            success=False, error=f"Failed to calculate performance metrics: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Unexpected error calculating performance metrics",
            extra={
                "correlation_id": correlation_id,
                "portfolio_id": str(request.portfolio_id),
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        return PerformanceMetricsResponse(
            success=False, error=f"Unexpected error: {str(e)}"
        )


@router.get("/performance-metrics/{portfolio_id}", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    portfolio_id: UUID,
    period: PerformancePeriod = Query(default=PerformancePeriod.MONTHLY),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get performance metrics for a portfolio."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(portfolio_id)

        # Calculate performance metrics
        metrics = await analytics_service.calculate_performance_metrics(
            portfolio=portfolio, period=period, start_date=start_date, end_date=end_date
        )

        return PerformanceMetricsResponse(success=True, data=metrics)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return PerformanceMetricsResponse(
            success=False, error=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/risk-metrics/{portfolio_id}", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    portfolio_id: UUID,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get risk metrics for a portfolio."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(portfolio_id)

        # Calculate risk metrics
        metrics = await analytics_service.calculate_risk_metrics(portfolio)

        return RiskMetricsResponse(success=True, data=metrics)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return RiskMetricsResponse(success=False, error=f"Failed to get risk metrics: {str(e)}")


@router.get("/analytics/{portfolio_id}", response_model=PortfolioAnalyticsResponse)
async def get_portfolio_analytics(
    portfolio_id: UUID,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get comprehensive portfolio analytics."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(portfolio_id)

        # Generate analytics
        analytics = await analytics_service.generate_portfolio_analytics(portfolio)

        return PortfolioAnalyticsResponse(success=True, data=analytics)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return PortfolioAnalyticsResponse(
            success=False, error=f"Failed to get portfolio analytics: {str(e)}"
        )


@router.get("/allocation/{portfolio_id}", response_model=PortfolioAllocationResponse)
async def get_portfolio_allocation(
    portfolio_id: UUID,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get portfolio allocation analysis."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(portfolio_id)

        # Analyze allocation
        allocation = await analytics_service.analyze_portfolio_allocation(portfolio)

        return PortfolioAllocationResponse(success=True, data=allocation)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return PortfolioAllocationResponse(
            success=False, error=f"Failed to get portfolio allocation: {str(e)}"
        )


@router.post("/rebalance", response_model=RebalanceResponse)
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "trader"])
@audit_log("rebalance_recommendation_generated", log_args=True)
async def get_rebalance_recommendation(
    request: RebalanceRequest,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get portfolio rebalancing recommendations."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(request.portfolio_id)

        # Create target allocation if provided
        target_allocation = None
        if (
            request.target_equity_allocation is not None
            or request.target_cash_allocation is not None
        ):
            from app.models.portfolio_analytics import PortfolioAllocation

            equity_allocation = request.target_equity_allocation or Decimal("60")
            cash_allocation = request.target_cash_allocation or Decimal("40")

            target_allocation = PortfolioAllocation(
                portfolio_id=request.portfolio_id,
                equity_allocation=equity_allocation,
                fixed_income_allocation=Decimal("0"),
                cash_allocation=cash_allocation,
                alternative_allocation=Decimal("0"),
                domestic_allocation=Decimal("100"),
                international_allocation=Decimal("0"),
            )

        # Generate rebalance recommendation
        rebalance = await analytics_service.generate_rebalance_recommendation(
            portfolio=portfolio, target_allocation=target_allocation
        )

        return RebalanceResponse(success=True, data=rebalance)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return RebalanceResponse(
            success=False, error=f"Failed to get rebalance recommendation: {str(e)}"
        )


@router.post("/compare", response_model=PortfolioComparisonResponse)
async def compare_portfolios(
    request: PortfolioComparisonRequest,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Compare multiple portfolios."""
    try:
        # Generate comparison
        comparison = await analytics_service.compare_portfolios(request.portfolio_ids)

        return PortfolioComparisonResponse(success=True, data=comparison)

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        return PortfolioComparisonResponse(
            success=False, error=f"Failed to compare portfolios: {str(e)}"
        )


@router.get("/summary/{portfolio_id}", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    portfolio_id: UUID,
    analytics_service: PortfolioAnalyticsService = Depends(get_portfolio_analytics_service),
):
    """Get portfolio analytics summary."""
    try:
        # Get portfolio data (mock for now)
        portfolio = _get_mock_portfolio(portfolio_id)

        # Generate analytics
        analytics = await analytics_service.generate_portfolio_analytics(portfolio)

        # Create summary
        summary = {
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio.name,
            "total_value": float(analytics.performance_metrics.total_value),
            "total_return": float(analytics.performance_metrics.total_return),
            "annualized_return": float(analytics.performance_metrics.annualized_return),
            "volatility": float(analytics.performance_metrics.volatility),
            "sharpe_ratio": float(analytics.performance_metrics.sharpe_ratio),
            "max_drawdown": float(analytics.performance_metrics.max_drawdown),
            "risk_level": analytics.risk_level.value,
            "risk_score": float(analytics.risk_score),
            "health_score": float(analytics.health_score),
            "diversification_score": float(analytics.diversification_score),
            "liquidity_score": float(analytics.liquidity_score),
            "position_count": analytics.performance_metrics.position_count,
            "recommendations_count": len(analytics.recommendations),
            "warnings_count": len(analytics.warnings),
            "analysis_date": analytics.analysis_date.isoformat(),
        }

        return AnalyticsSummaryResponse(success=True, data=summary)

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        return AnalyticsSummaryResponse(
            success=False, error=f"Failed to get analytics summary: {str(e)}"
        )


@router.get("/health-check")
async def health_check():
    """Health check endpoint for portfolio analytics service."""
    return {
        "status": "healthy",
        "service": "portfolio-analytics",
        "timestamp": datetime.utcnow().isoformat(),
    }
