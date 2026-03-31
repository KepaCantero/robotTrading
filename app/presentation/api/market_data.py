"""
Market Data API Endpoints

This module provides FastAPI endpoints for market data management,
including quotes, historical data, and feed configuration.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
- API-009: Added audit logging
- API-010: Added timeout configuration
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    HTTPError,
    RequestException,
)

from app.domain.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    Quote,
)
from app.infrastructure.feeds.market_data import MarketDataService, get_market_data_service

from . import audit_logger, get_correlation_id
from .security import audit_log, rate_limit, require_auth

if TYPE_CHECKING:
    from uuid import UUID

router = APIRouter(prefix="/market-data", tags=["market-data"])
logger = logging.getLogger(__name__)


# Request/Response Models
class QuoteResponse(BaseModel):
    """Quote response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Quote | None = Field(None, description="Quote data")
    error: str | None = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HistoricalDataResponse(BaseModel):
    """Historical data response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: list[HistoricalData] = Field(default_factory=list, description="Historical data")
    count: int = Field(default=0, description="Number of data points")
    error: str | None = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class FeedConfigResponse(BaseModel):
    """Feed configuration response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: DataFeedConfig | None = Field(None, description="Feed configuration")
    error: str | None = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class FeedConfigsResponse(BaseModel):
    """Multiple feed configurations response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: list[DataFeedConfig] = Field(default_factory=list, description="Feed configurations")
    count: int = Field(default=0, description="Number of configurations")
    error: str | None = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ServiceStatusResponse(BaseModel):
    """Service status response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: dict[str, Any] = Field(default_factory=dict, description="Service status data")
    error: str | None = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class CreateFeedConfigRequest(BaseModel):
    """Request model for creating feed configuration."""

    name: str = Field(..., description="Feed configuration name")
    feed_type: DataFeedType = Field(..., description="Type of data feed")
    api_key: str | None = Field(None, description="API key for the feed")
    base_url: str = Field(..., description="Base URL for the API")
    rate_limit: int = Field(default=60, ge=1, le=3600, description="Rate limit per minute")
    supported_symbols: list[str] = Field(
        default_factory=list, description="Supported trading symbols"
    )
    supported_frequencies: list[DataFrequency] = Field(
        default_factory=list, description="Supported data frequencies"
    )
    max_history_days: int = Field(
        default=365, ge=1, le=3650, description="Maximum historical data days"
    )
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    retry_delay: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Delay between retries in seconds"
    )
    is_active: bool = Field(default=True, description="Whether the feed is active")


class SubscribeRequest(BaseModel):
    """Request model for subscribing to symbols."""

    symbols: list[str] = Field(..., description="Symbols to subscribe to")
    feed_id: UUID | None = Field(None, description="Specific feed ID to use")
    frequency: DataFrequency = Field(
        default=DataFrequency.REAL_TIME, description="Data update frequency"
    )


# Endpoints
@router.get("/quotes/{symbol}", response_model=QuoteResponse)
@rate_limit(max_requests=200, window_seconds=60)
async def get_quote(
    http_request: Request,
    symbol: str = Path(..., description="Trading symbol"),
    feed_id: UUID | None = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get real-time quote for a symbol."""
    correlation_id = get_correlation_id(http_request) if http_request else ""
    logger.info(
        "Fetching quote for symbol",
        extra={
            "correlation_id": correlation_id,
            "symbol": symbol,
            "feed_id": str(feed_id) if feed_id else None,
        },
    )
    try:
        quote_data = await asyncio.wait_for(
            service.get_quote(symbol),
            timeout=15.0,  # API-010: Add timeout configuration
        )

        if quote_data:
            audit_logger.log_action(
                action="quote_retrieved",
                method="GET",
                path="/quotes/{symbol}",
                details={"symbol": symbol, "feed_id": str(feed_id) if feed_id else None},
            )
            return QuoteResponse(
                success=True,
                data=Quote(
                    symbol=quote_data.get("symbol", symbol),
                    bid=quote_data.get("bid"),
                    ask=quote_data.get("ask"),
                    last=quote_data.get("price"),
                    open=quote_data.get("open"),
                    high=quote_data.get("high"),
                    low=quote_data.get("low"),
                    close=quote_data.get("close"),
                    volume=quote_data.get("volume"),
                ),
                error=None,
                timestamp=datetime.utcnow(),
            )
        else:
            return QuoteResponse(
                success=False,
                data=None,
                error=f"No quote data available for {symbol}",
                timestamp=datetime.utcnow(),
            )
    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching quote",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method="GET",
            path="/quotes/{symbol}",
            error_type="TimeoutError",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=504, detail=f"Timeout getting quote for {symbol}: {e!s}"
        ) from e
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(
            "Error fetching quote",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol,
                "error_type": type(e).__name__,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method="GET",
            path="/quotes/{symbol}",
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting quote for {symbol}: {e!s}"
        ) from e


@router.get("/quotes", response_model=list[QuoteResponse])
async def get_multiple_quotes(
    symbols: list[str] = Query(..., description="Trading symbols"),
    feed_id: UUID | None = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get real-time quotes for multiple symbols."""
    try:
        quotes: list[QuoteResponse] = []
        for sym in symbols:
            quote_data = await service.get_quote(sym)
            if quote_data:
                quotes.append(
                    QuoteResponse(
                        success=True,
                        data=Quote(
                            symbol=quote_data.get("symbol", sym),
                            bid=quote_data.get("bid"),
                            ask=quote_data.get("ask"),
                            last=quote_data.get("price"),
                            open=quote_data.get("open"),
                            high=quote_data.get("high"),
                            low=quote_data.get("low"),
                            close=quote_data.get("close"),
                            volume=quote_data.get("volume"),
                        ),
                        error=None,
                        timestamp=datetime.utcnow(),
                    )
                )
            else:
                quotes.append(
                    QuoteResponse(
                        success=False,
                        data=None,
                        error=f"No quote data for {sym}",
                        timestamp=datetime.utcnow(),
                    )
                )

        return quotes
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting quotes: {e!s}") from e


@router.get("/quotes/top-liquid", response_model=list[QuoteResponse])
async def get_top_liquid_quotes(
    limit: int = Query(default=20, ge=1, le=100, description="Number of quotes to return"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get quotes for top liquid assets."""
    try:
        quotes_data = await service.get_top_liquid_quotes(limit)

        return [
            QuoteResponse(
                success=True,
                data=Quote(
                    symbol=q.get("symbol", ""),
                    bid=q.get("bid"),
                    ask=q.get("ask"),
                    last=q.get("price"),
                    open=q.get("open"),
                    high=q.get("high"),
                    low=q.get("low"),
                    close=q.get("close"),
                    volume=q.get("volume"),
                ),
                error=None,
                timestamp=datetime.utcnow(),
            )
            for q in quotes_data
        ]
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting top liquid quotes: {e!s}"
        ) from e


@router.get("/historical/{symbol}", response_model=HistoricalDataResponse)
async def get_historical_data(
    symbol: str = Path(..., description="Trading symbol"),
    start_date: datetime = Query(..., description="Start date for historical data"),
    end_date: datetime = Query(..., description="End date for historical data"),
    frequency: DataFrequency = Query(default=DataFrequency.DAILY, description="Data frequency"),
    feed_id: UUID | None = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get historical data for a symbol."""
    try:
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

        await service.get_historical_data(symbol, start_date, end_date)

        historical_models: list[HistoricalData] = []

        return HistoricalDataResponse(
            success=True,
            data=historical_models,
            count=len(historical_models),
            error=None,
            timestamp=datetime.utcnow(),
        )

    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting historical data for {symbol}: {e!s}",
        ) from e


@router.post("/feeds", response_model=FeedConfigResponse)
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("feed_config_created", log_args=True, sensitive_params=["api_key"])
async def create_feed_config(
    request: CreateFeedConfigRequest,
    service: MarketDataService = Depends(get_market_data_service),
):
    """Create a new data feed configuration."""
    try:
        config = DataFeedConfig(
            name=request.name,
            feed_type=request.feed_type,
            api_key=request.api_key,
            base_url=request.base_url,
            rate_limit=request.rate_limit,
            supported_symbols=request.supported_symbols,
            supported_frequencies=request.supported_frequencies,
            max_history_days=request.max_history_days,
            timeout_seconds=request.timeout_seconds,
            retry_attempts=request.retry_attempts,
            retry_delay=request.retry_delay,
            is_active=request.is_active,
            last_updated=datetime.utcnow(),
        )

        config_id = await service.add_feed_config(config)
        config.id = config_id

        return FeedConfigResponse(
            success=True, data=config, error=None, timestamp=datetime.utcnow()
        )
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating feed configuration: {e!s}"
        ) from e


@router.get("/feeds", response_model=FeedConfigsResponse)
async def list_feed_configs(
    service: MarketDataService = Depends(get_market_data_service),
):
    """List all data feed configurations."""
    try:
        configs = await service.list_feed_configs()

        return FeedConfigsResponse(
            success=True, data=configs, count=len(configs), error=None, timestamp=datetime.utcnow()
        )
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing feed configurations: {e!s}"
        ) from e


@router.get("/feeds/{config_id}", response_model=FeedConfigResponse)
async def get_feed_config(
    config_id: UUID = Path(..., description="Feed configuration ID"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get a specific data feed configuration."""
    try:
        config = await service.get_feed_config(config_id)

        if config:
            return FeedConfigResponse(
                success=True, data=config, error=None, timestamp=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Feed configuration not found: {config_id}"
            )

    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting feed configuration: {e!s}"
        ) from e


@router.post("/feeds/{config_id}/connect")
async def connect_feed(
    config_id: UUID = Path(..., description="Feed configuration ID"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Connect to a data feed."""
    try:
        success = await service.connect_feed(config_id)

        if success:
            return {"success": True, "message": f"Connected to feed {config_id}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to connect to feed {config_id}")

    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to feed: {e!s}") from e


@router.post("/feeds/{config_id}/disconnect")
async def disconnect_feed(
    config_id: UUID = Path(..., description="Feed configuration ID"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Disconnect from a data feed."""
    try:
        success = await service.disconnect_feed(config_id)

        if success:
            return {"success": True, "message": f"Disconnected from feed {config_id}"}
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to disconnect from feed {config_id}"
            )

    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting from feed: {e!s}") from e


@router.post("/subscribe")
async def subscribe_to_symbols(
    request: SubscribeRequest,
    service: MarketDataService = Depends(get_market_data_service),
):
    """Subscribe to real-time updates for symbols."""
    try:
        success = await service.subscribe_to_symbols(request.symbols, request.feed_id)

        if success:
            return {
                "success": True,
                "message": f"Subscribed to symbols: {request.symbols}",
                "symbols": request.symbols,
                "frequency": request.frequency,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to subscribe to symbols: {request.symbols}",
            )

    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error subscribing to symbols: {e!s}") from e


@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status(
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get market data service status."""
    try:
        status_data = await service.get_service_status()

        return ServiceStatusResponse(
            success=True, data=status_data, error=None, timestamp=datetime.utcnow()
        )
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting service status: {e!s}") from e


@router.post("/cache/clear")
async def clear_cache(service: MarketDataService = Depends(get_market_data_service)):
    """Clear all cached market data."""
    try:
        service.clear_cache()
        return {"success": True, "message": "Cache cleared successfully"}
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {e!s}") from e


@router.get("/cache/stats")
async def get_cache_stats(
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get cache statistics."""
    try:
        stats = service.get_cache_stats()
        return {"success": True, "data": stats}
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {e!s}") from e
