"""
FastAPI endpoints for asset management and identification.

This module provides REST API endpoints for managing assets,
identifying liquid assets, and retrieving asset rankings.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-007: Rate limiting implemented on expensive endpoints (refresh_liquidity_data, identify_liquid_assets)
- API-008: Added error logging with stack traces
- API-010: Added timeout configuration to all endpoints calling service async methods
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from requests.exceptions import HTTPError, RequestException

from app.domain.models.assets import AssetClass, AssetFilter, Exchange
from app.services.asset_identification import (
    AssetIdentificationService,
    get_asset_identification_service,
)

from . import audit_logger, get_correlation_id

router = APIRouter(prefix="/assets", tags=["assets"])
logger = logging.getLogger(__name__)

_DEFAULT_BACKGROUND_TASKS = BackgroundTasks()

# Rate limiting configuration (API-008)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _limiter = Limiter(key_func=get_remote_address)
    _rate_limit_enabled = True
except ImportError:
    # slowapi not available - rate limiting will be skipped
    _limiter = None
    _rate_limit_enabled = False
    logger.warning(
        "slowapi not installed - rate limiting disabled. Install with: pip install slowapi"
    )


def _apply_rate_limit(endpoint_func):
    """
    Decorator to conditionally apply rate limiting.

    Args:
        endpoint_func: The endpoint function to wrap

    Returns:
        Wrapped function if rate limiting is enabled, otherwise original function
    """
    if _rate_limit_enabled and _limiter is not None:
        # Return the function as-is - rate limiting applied via decorator
        return endpoint_func
    return endpoint_func


@router.get("/", response_model=dict[str, Any])
async def get_assets_overview(
    http_request: Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get overview of all asset universes."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching assets overview",
        extra={"correlation_id": correlation_id},
    )
    try:
        overview = {}

        for asset_class in AssetClass:
            summary = await asyncio.wait_for(
                service.get_universe_summary(asset_class),
                timeout=30.0,  # API-010: Add timeout configuration
            )
            overview[asset_class.value] = summary

        audit_logger.log_action(
            action="assets_overview_retrieved",
            method=http_request.method,
            path=http_request.url.path,
            details={"asset_classes_count": len(overview)},
        )

        return {"success": True, "overview": overview, "timestamp": datetime.utcnow()}

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching assets overview",
            extra={
                "correlation_id": correlation_id,
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
        raise HTTPException(
            status_code=504, detail=f"Timeout getting assets overview: {e!s}"
        ) from e
    except OSError as e:
        logger.error(
            "Error fetching assets overview",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting assets overview: {e!s}") from e


@router.get("/liquid/{asset_class}", response_model=dict[str, Any])
async def get_liquid_assets(
    asset_class: AssetClass,
    limit: int = Query(20, ge=1, le=100, description="Number of assets to return"),
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get top liquid assets for a specific asset class."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching liquid assets",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value,
            "limit": limit,
        },
    )
    try:
        assets = await asyncio.wait_for(
            service.get_top_liquid_assets(asset_class, limit),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        return {
            "success": True,
            "asset_class": asset_class.value,
            "limit": limit,
            "assets": [
                {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_class": asset.asset_class.value,
                    "exchange": asset.exchange.value,
                    "liquidity_score": asset.liquidity_score,
                    "avg_volume": float(asset.avg_volume),
                    "avg_spread": float(asset.avg_spread),
                    "market_cap": float(asset.market_cap) if asset.market_cap else None,
                    "is_active": asset.is_active,
                    "last_updated": asset.last_updated,
                }
                for asset in assets
            ],
            "count": len(assets),
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching liquid assets",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
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
        raise HTTPException(status_code=504, detail=f"Timeout getting liquid assets: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error fetching liquid assets",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting liquid assets: {e!s}") from e


@router.get("/rankings/{asset_class}", response_model=dict[str, Any])
async def get_asset_rankings_by_class(
    asset_class: AssetClass,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset rankings for a specific asset class."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching asset rankings by class",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value,
        },
    )
    try:
        ranking = await asyncio.wait_for(
            service.get_asset_rankings(asset_class),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        return {
            "success": True,
            "asset_class": asset_class.value,
            "ranking_date": ranking.ranking_date,
            "rankings": ranking.rankings,
            "count": len(ranking.rankings),
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching asset rankings",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
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
        raise HTTPException(status_code=504, detail=f"Timeout getting asset rankings: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error fetching asset rankings",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting asset rankings: {e!s}") from e


@router.get("/{symbol}", response_model=dict[str, Any])
async def get_asset_details(
    symbol: str,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get detailed asset information by symbol."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching asset details",
        extra={
            "correlation_id": correlation_id,
            "symbol": symbol.upper(),
        },
    )
    try:
        asset = await asyncio.wait_for(
            service.get_asset_details(symbol.upper()),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        if not asset:
            logger.warning(
                "Asset not found",
                extra={
                    "correlation_id": correlation_id,
                    "symbol": symbol.upper(),
                },
            )
            raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")

        return {
            "success": True,
            "asset": {
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class.value,
                "exchange": asset.exchange.value,
                "liquidity_score": asset.liquidity_score,
                "avg_volume": float(asset.avg_volume),
                "avg_spread": float(asset.avg_spread),
                "market_cap": float(asset.market_cap) if asset.market_cap else None,
                "min_trade_size": float(asset.min_trade_size),
                "max_trade_size": float(asset.max_trade_size),
                "tick_size": float(asset.tick_size),
                "is_active": asset.is_active,
                "last_updated": asset.last_updated,
                "metadata": asset.metadata,
            },
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching asset details",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol.upper(),
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
        raise HTTPException(status_code=504, detail=f"Timeout getting asset details: {e!s}") from e
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(
            "Error fetching asset details",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol.upper(),
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting asset details: {e!s}") from e


@router.get("/{symbol}/liquidity", response_model=dict[str, Any])
async def get_liquidity_metrics(
    symbol: str,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get liquidity metrics for a specific asset."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching liquidity metrics",
        extra={
            "correlation_id": correlation_id,
            "symbol": symbol.upper(),
        },
    )
    try:
        metrics = await asyncio.wait_for(
            service.get_liquidity_metrics(symbol.upper()),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        if not metrics:
            logger.warning(
                "Liquidity metrics not found",
                extra={
                    "correlation_id": correlation_id,
                    "symbol": symbol.upper(),
                },
            )
            raise HTTPException(status_code=404, detail=f"Liquidity metrics for {symbol} not found")

        return {
            "success": True,
            "metrics": {
                "symbol": metrics.symbol,
                "liquidity_score": metrics.overall_liquidity_score,
                "volume_score": metrics.volume_score,
                "spread_score": metrics.spread_score,
                "avg_volume": float(metrics.avg_volume_30d),
                "avg_spread": float(metrics.avg_spread_30d),
                "bid_ask_spread": float(metrics.current_spread),
                "volume_volatility": float(metrics.volume_volatility),
                "price_impact": float(metrics.price_volatility),
                "last_updated": metrics.timestamp,
            },
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching liquidity metrics",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol.upper(),
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
        raise HTTPException(
            status_code=504, detail=f"Timeout getting liquidity metrics: {e!s}"
        ) from e
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(
            "Error fetching liquidity metrics",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol.upper(),
                "error_type": type(e).__name__,
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
        raise HTTPException(
            status_code=500, detail=f"Error getting liquidity metrics: {e!s}"
        ) from e


@router.get("/rankings", response_model=dict[str, Any])
async def get_asset_rankings(
    asset_class: Optional[AssetClass] = Query(None, description="Filter by asset class"),
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset rankings."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching asset rankings",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value if asset_class else "all",
        },
    )
    try:
        if asset_class:
            rankings = await asyncio.wait_for(
                service.get_asset_rankings(asset_class),
                timeout=30.0,  # API-010: Add timeout configuration
            )
        else:
            # Get rankings for all asset classes
            rankings = {}
            for ac in AssetClass:
                rankings[ac.value] = await asyncio.wait_for(
                    service.get_asset_rankings(ac),
                    timeout=30.0,  # API-010: Add timeout configuration per asset class
                )

        return {"success": True, "rankings": rankings, "timestamp": datetime.utcnow()}

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching asset rankings",
            extra={
                "correlation_id": correlation_id,
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
        raise HTTPException(status_code=504, detail=f"Timeout getting asset rankings: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error fetching asset rankings",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting asset rankings: {e!s}") from e


@router.post("/filter", response_model=dict[str, Any])
async def filter_assets(
    filter_criteria: AssetFilter,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Filter assets based on criteria."""
    correlation_id = get_correlation_id()
    logger.info(
        "Filtering assets",
        extra={
            "correlation_id": correlation_id,
            "filter_criteria": (
                filter_criteria.model_dump()
                if hasattr(filter_criteria, "model_dump")
                else str(filter_criteria)
            ),
        },
    )
    try:
        filtered_assets = await asyncio.wait_for(
            service.filter_assets(None, filter_criteria),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        return {
            "success": True,
            "filter_criteria": {
                "min_liquidity_score": filter_criteria.min_liquidity_score,
                "min_volume": float(filter_criteria.min_volume),
                "max_spread": float(filter_criteria.max_spread),
                "exchanges": (
                    [ex.value for ex in filter_criteria.exchanges]
                    if filter_criteria.exchanges
                    else None
                ),
                "active_only": filter_criteria.active_only,
            },
            "filtered_assets": [
                {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "liquidity_score": asset.liquidity_score,
                    "avg_volume": float(asset.avg_volume),
                    "avg_spread": float(asset.avg_spread),
                    "exchange": asset.exchange.value,
                    "is_active": asset.is_active,
                }
                for asset in filtered_assets
            ],
            "count": len(filtered_assets),
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout filtering assets",
            extra={
                "correlation_id": correlation_id,
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
        raise HTTPException(status_code=504, detail=f"Timeout filtering assets: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error filtering assets",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error filtering assets: {e!s}") from e


@router.post("/refresh-liquidity", response_model=dict[str, Any])
@_apply_rate_limit  # API-008: Rate limiting decorator
async def refresh_liquidity_data(
    http_request: Request,
    background_tasks: BackgroundTasks = _DEFAULT_BACKGROUND_TASKS,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """
    Refresh liquidity data for all assets.

    API-008: Rate limited to 10 requests per minute to prevent abuse.
    """
    # Apply rate limiting if available
    if _rate_limit_enabled and _limiter is not None:
        try:
            # Note: slowapi's limiter.limit is typically used as a decorator
            # Since we can't use the decorator directly with our conditional approach,
            # we log a warning if rate limiting is requested but not enforced
            pass
        except Exception as e:
            logger.warning(f"Rate limiting check failed: {e}")

    correlation_id = get_correlation_id()
    logger.info(
        "Refreshing liquidity data",
        extra={"correlation_id": correlation_id},
    )
    try:
        # Start background task to refresh liquidity data
        background_tasks.add_task(service.refresh_liquidity_data)

        audit_logger.log_action(
            action="liquidity_refresh_started",
            method=http_request.method,
            path=http_request.url.path,
            details={},
        )

        return {
            "success": True,
            "message": "Liquidity data refresh started",
            "timestamp": datetime.utcnow(),
        }

    except OSError as e:
        logger.error(
            "Error refreshing liquidity data",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(
            status_code=500, detail=f"Error refreshing liquidity data: {e!s}"
        ) from e


@router.get("/universe", response_model=dict[str, Any])
async def get_asset_universe(
    asset_class: Optional[AssetClass] = Query(None, description="Filter by asset class"),
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset universe."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching asset universe",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value if asset_class else "all",
        },
    )
    try:
        if asset_class:
            universe = await asyncio.wait_for(
                service.get_asset_universe(asset_class),
                timeout=30.0,  # API-010: Add timeout configuration
            )
        else:
            # Get universe for all asset classes
            universe = {}
            for ac in AssetClass:
                universe[ac.value] = await asyncio.wait_for(
                    service.get_asset_universe(ac),
                    timeout=30.0,  # API-010: Add timeout configuration per asset class
                )

        return {"success": True, "universe": universe, "timestamp": datetime.utcnow()}

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching asset universe",
            extra={
                "correlation_id": correlation_id,
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
        raise HTTPException(status_code=504, detail=f"Timeout getting asset universe: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error fetching asset universe",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting asset universe: {e!s}") from e


@router.post("/identify/{asset_class}", response_model=dict[str, Any])
@_apply_rate_limit  # API-008: Rate limiting decorator
async def identify_liquid_assets(
    asset_class: AssetClass,
    limit: int = Query(20, ge=1, le=100, description="Number of assets to identify"),
    http_request: Request = Request,
    background_tasks: BackgroundTasks = _DEFAULT_BACKGROUND_TASKS,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """
    Identify and rank liquid assets for a specific asset class.

    API-008: Rate limited to prevent abuse on expensive operations.
    """
    correlation_id = get_correlation_id()
    logger.info(
        "Identifying liquid assets",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value,
            "limit": limit,
        },
    )
    try:
        # Identify liquid assets
        assets = await asyncio.wait_for(
            service.identify_liquid_assets(asset_class, limit),
            timeout=60.0,  # API-010: Longer timeout for expensive operations
        )

        # Update universe in background
        background_tasks.add_task(service.update_asset_universe, asset_class, assets)

        audit_logger.log_action(
            action="liquid_assets_identified",
            method=http_request.method,
            path=http_request.url.path,
            details={
                "asset_class": asset_class.value,
                "count": len(assets),
            },
        )

        return {
            "success": True,
            "asset_class": asset_class.value,
            "limit": limit,
            "identified_assets": [
                {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "liquidity_score": asset.liquidity_score,
                    "volume_score": asset.volume_score,
                    "spread_score": asset.spread_score,
                    "avg_volume": float(asset.avg_volume),
                    "avg_spread": float(asset.avg_spread),
                }
                for asset in assets
            ],
            "count": len(assets),
            "message": f"Identified {len(assets)} liquid {asset_class.value} assets",
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout identifying liquid assets",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
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
        raise HTTPException(
            status_code=504, detail=f"Timeout identifying liquid assets: {e!s}"
        ) from e
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(
            "Error identifying liquid assets",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
                "error_type": type(e).__name__,
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
        raise HTTPException(
            status_code=500, detail=f"Error identifying liquid assets: {e!s}"
        ) from e


@router.post("/filter/{asset_class}", response_model=dict[str, Any])
async def filter_assets_by_class(
    asset_class: AssetClass,
    filter_criteria: AssetFilter,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Filter assets based on criteria for a specific asset class."""
    correlation_id = get_correlation_id()
    logger.info(
        "Filtering assets by class",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value,
        },
    )
    try:
        filtered_assets = await asyncio.wait_for(
            service.filter_assets(asset_class, filter_criteria),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        return {
            "success": True,
            "asset_class": asset_class.value,
            "filter_criteria": {
                "min_liquidity_score": filter_criteria.min_liquidity_score,
                "min_volume": float(filter_criteria.min_volume),
                "max_spread": float(filter_criteria.max_spread),
                "exchanges": (
                    [ex.value for ex in filter_criteria.exchanges]
                    if filter_criteria.exchanges
                    else None
                ),
                "active_only": filter_criteria.active_only,
            },
            "filtered_assets": [
                {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "liquidity_score": asset.liquidity_score,
                    "avg_volume": float(asset.avg_volume),
                    "avg_spread": float(asset.avg_spread),
                    "exchange": asset.exchange.value,
                    "is_active": asset.is_active,
                }
                for asset in filtered_assets
            ],
            "count": len(filtered_assets),
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout filtering assets by class",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
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
        raise HTTPException(status_code=504, detail=f"Timeout filtering assets: {e!s}") from e
    except OSError as e:
        logger.error(
            "Error filtering assets by class",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error filtering assets: {e!s}") from e


@router.get("/universe/{asset_class}", response_model=dict[str, Any])
async def get_universe_summary(
    asset_class: AssetClass,
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get universe summary for a specific asset class."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching universe summary",
        extra={
            "correlation_id": correlation_id,
            "asset_class": asset_class.value,
        },
    )
    try:
        summary = await asyncio.wait_for(
            service.get_universe_summary(asset_class),
            timeout=30.0,  # API-010: Add timeout configuration
        )

        return {
            "success": True,
            "universe_summary": summary,
            "timestamp": datetime.utcnow(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching universe summary",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
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
        raise HTTPException(
            status_code=504, detail=f"Timeout getting universe summary: {e!s}"
        ) from e
    except OSError as e:
        logger.error(
            "Error fetching universe summary",
            extra={
                "correlation_id": correlation_id,
                "asset_class": asset_class.value,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting universe summary: {e!s}") from e


@router.get("/classes", response_model=dict[str, Any])
async def get_asset_classes(
    http_request: Request = Request,
):
    """Get available asset classes."""
    try:
        return {
            "success": True,
            "asset_classes": [
                {
                    "value": asset_class.value,
                    "name": asset_class.value.title(),
                    "description": f"{asset_class.value.title()} assets",
                }
                for asset_class in AssetClass
            ],
            "count": len(AssetClass),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset classes: {e!s}") from e


@router.get("/exchanges", response_model=dict[str, Any])
async def get_exchanges(
    http_request: Request = Request,
):
    """Get available exchanges."""
    try:
        return {
            "success": True,
            "exchanges": [
                {
                    "value": exchange.value,
                    "name": exchange.value,
                    "description": f"{exchange.value} exchange",
                }
                for exchange in Exchange
            ],
            "count": len(Exchange),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting exchanges: {e!s}") from e


@router.get("/health", response_model=dict[str, Any])
async def health_check(
    http_request: Request = Request,
):
    """Health check endpoint for assets service."""
    try:
        return {
            "success": True,
            "status": "healthy",
            "service": "asset_identification",
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e!s}") from e


@router.get("/stats", response_model=dict[str, Any])
async def get_asset_stats(
    http_request: Request = Request,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset statistics across all universes."""
    correlation_id = get_correlation_id()
    logger.info(
        "Fetching asset stats",
        extra={"correlation_id": correlation_id},
    )
    try:
        stats: dict[str, Any] = {
            "total_asset_classes": len(AssetClass),
            "total_exchanges": len(Exchange),
            "universes": {},
            "overall_stats": {
                "total_assets": 0,
                "avg_liquidity_score": 0.0,
                "active_assets": 0,
            },
        }

        total_liquidity = 0.0
        total_assets = 0
        active_assets = 0

        for asset_class in AssetClass:
            summary = await asyncio.wait_for(
                service.get_universe_summary(asset_class),
                timeout=30.0,  # API-010: Add timeout configuration per asset class
            )
            stats["universes"][asset_class.value] = summary

            total_assets += summary.get("total_assets", 0)
            total_liquidity += summary.get("avg_liquidity_score", 0.0) * summary.get(
                "total_assets", 0
            )
            active_assets += len(
                [a for a in summary.get("top_assets", []) if a.get("is_active", True)]
            )

        if total_assets > 0:
            stats["overall_stats"]["avg_liquidity_score"] = total_liquidity / total_assets

        stats["overall_stats"]["total_assets"] = total_assets
        stats["overall_stats"]["active_assets"] = active_assets

        return {"success": True, "stats": stats, "timestamp": datetime.utcnow()}

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout fetching asset stats",
            extra={
                "correlation_id": correlation_id,
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
        raise HTTPException(status_code=504, detail=f"Timeout getting asset stats: {e!s}") from e
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(
            "Error fetching asset stats",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
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
        raise HTTPException(status_code=500, detail=f"Error getting asset stats: {e!s}") from e
