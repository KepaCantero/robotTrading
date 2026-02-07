"""
Market Data API Endpoints

This module provides FastAPI endpoints for market data management,
including quotes, historical data, and feed configuration.
"""
# mypy: ignore-errors

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from requests.exceptions import ConnectionError, HTTPError, RequestException

from app.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    Quote,
)
from app.services.market_data_service import MarketDataService, get_market_data_service

router = APIRouter(prefix="/market-data", tags=["market-data"])


# Request/Response Models
class QuoteResponse(BaseModel):
    """Quote response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Quote] = Field(None, description="Quote data")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HistoricalDataResponse(BaseModel):
    """Historical data response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: List[HistoricalData] = Field(default_factory=list, description="Historical data")
    count: int = Field(default=0, description="Number of data points")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class FeedConfigResponse(BaseModel):
    """Feed configuration response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[DataFeedConfig] = Field(None, description="Feed configuration")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class FeedConfigsResponse(BaseModel):
    """Multiple feed configurations response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: List[DataFeedConfig] = Field(default_factory=list, description="Feed configurations")
    count: int = Field(default=0, description="Number of configurations")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ServiceStatusResponse(BaseModel):
    """Service status response model."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Dict[str, Any] = Field(default_factory=dict, description="Service status data")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class CreateFeedConfigRequest(BaseModel):
    """Request model for creating feed configuration."""

    name: str = Field(..., description="Feed configuration name")
    feed_type: DataFeedType = Field(..., description="Type of data feed")
    api_key: Optional[str] = Field(None, description="API key for the feed")
    base_url: str = Field(..., description="Base URL for the API")
    rate_limit: int = Field(default=60, ge=1, le=3600, description="Rate limit per minute")
    supported_symbols: List[str] = Field(
        default_factory=list, description="Supported trading symbols"
    )
    supported_frequencies: List[DataFrequency] = Field(
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

    symbols: List[str] = Field(..., description="Symbols to subscribe to")
    feed_id: Optional[UUID] = Field(None, description="Specific feed ID to use")
    frequency: DataFrequency = Field(
        default=DataFrequency.REAL_TIME, description="Data update frequency"
    )


# Endpoints
@router.get("/quotes/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str = Path(..., description="Trading symbol"),
    feed_id: Optional[UUID] = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get real-time quote for a symbol."""
    try:
        quote = await service.get_quote(symbol, feed_id)

        if quote:
            return QuoteResponse(success=True, data=quote, timestamp=datetime.utcnow())
        else:
            return QuoteResponse(
                success=False,
                error=f"No quote data available for {symbol}",
                timestamp=datetime.utcnow(),
            )
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting quote for {symbol}: {str(e)}")


@router.get("/quotes", response_model=List[QuoteResponse])
async def get_multiple_quotes(
    symbols: List[str] = Query(..., description="Trading symbols"),
    feed_id: Optional[UUID] = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get real-time quotes for multiple symbols."""
    try:
        quotes = []
        for symbol in symbols:
            quote = await service.get_quote(symbol, feed_id)
            quotes.append(
                QuoteResponse(
                    success=quote is not None,
                    data=quote,
                    error=None if quote else f"No quote data for {symbol}",
                    timestamp=datetime.utcnow(),
                )
            )

        return quotes
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting quotes: {str(e)}")


@router.get("/quotes/top-liquid", response_model=List[QuoteResponse])
async def get_top_liquid_quotes(
    limit: int = Query(default=20, ge=1, le=100, description="Number of quotes to return"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get quotes for top liquid assets."""
    try:
        quotes = await service.get_top_liquid_assets_quotes(limit)

        return [
            QuoteResponse(success=True, data=quote, timestamp=datetime.utcnow()) for quote in quotes
        ]
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting top liquid quotes: {str(e)}")


@router.get("/historical/{symbol}", response_model=HistoricalDataResponse)
async def get_historical_data(
    symbol: str = Path(..., description="Trading symbol"),
    start_date: datetime = Query(..., description="Start date for historical data"),
    end_date: datetime = Query(..., description="End date for historical data"),
    frequency: DataFrequency = Query(default=DataFrequency.DAILY, description="Data frequency"),
    feed_id: Optional[UUID] = Query(None, description="Specific feed ID to use"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get historical data for a symbol."""
    try:
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

        historical_data = await service.get_historical_data(
            symbol, start_date, end_date, frequency, feed_id
        )

        return HistoricalDataResponse(
            success=True,
            data=historical_data,
            count=len(historical_data),
            timestamp=datetime.utcnow(),
        )
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting historical data for {symbol}: {str(e)}",
        )


@router.post("/feeds", response_model=FeedConfigResponse)
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
        )

        config_id = await service.add_feed_config(config)
        config.id = config_id

        return FeedConfigResponse(success=True, data=config, timestamp=datetime.utcnow())
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error creating feed configuration: {str(e)}")


@router.get("/feeds", response_model=FeedConfigsResponse)
async def list_feed_configs(
    service: MarketDataService = Depends(get_market_data_service),
):
    """List all data feed configurations."""
    try:
        configs = await service.list_feed_configs()

        return FeedConfigsResponse(
            success=True, data=configs, count=len(configs), timestamp=datetime.utcnow()
        )
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error listing feed configurations: {str(e)}")


@router.get("/feeds/{config_id}", response_model=FeedConfigResponse)
async def get_feed_config(
    config_id: UUID = Path(..., description="Feed configuration ID"),
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get a specific data feed configuration."""
    try:
        config = await service.get_feed_config(config_id)

        if config:
            return FeedConfigResponse(success=True, data=config, timestamp=datetime.utcnow())
        else:
            raise HTTPException(
                status_code=404, detail=f"Feed configuration not found: {config_id}"
            )
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting feed configuration: {str(e)}")


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to feed: {str(e)}")


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting from feed: {str(e)}")


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error subscribing to symbols: {str(e)}")


@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status(
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get market data service status."""
    try:
        status = await service.get_service_status()

        return ServiceStatusResponse(success=True, data=status, timestamp=datetime.utcnow())
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(service: MarketDataService = Depends(get_market_data_service)):
    """Clear all cached market data."""
    try:
        await service.clear_cache()
        return {"success": True, "message": "Cache cleared successfully"}
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats(
    service: MarketDataService = Depends(get_market_data_service),
):
    """Get cache statistics."""
    try:
        stats = await service.get_cache_stats()
        return {"success": True, "data": stats}
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")
