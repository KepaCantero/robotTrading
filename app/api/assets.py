"""
FastAPI endpoints for asset management and identification.

This module provides REST API endpoints for managing assets,
identifying liquid assets, and retrieving asset rankings.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.models.assets import AssetClass, AssetFilter, Exchange
from app.services.asset_identification import (
    AssetIdentificationService,
    get_asset_identification_service,
)

router = APIRouter(prefix="/assets", tags=["assets"])

_DEFAULT_BACKGROUND_TASKS = BackgroundTasks()


@router.get("/", response_model=Dict[str, Any])
async def get_assets_overview(
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get overview of all asset universes."""
    try:
        overview = {}

        for asset_class in AssetClass:
            summary = await service.get_universe_summary(asset_class)
            overview[asset_class.value] = summary

        return {"success": True, "overview": overview, "timestamp": datetime.utcnow()}

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting assets overview: {str(e)}")


@router.get("/liquid/{asset_class}", response_model=Dict[str, Any])
async def get_liquid_assets(
    asset_class: AssetClass,
    limit: int = Query(20, ge=1, le=100, description="Number of assets to return"),
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get top liquid assets for a specific asset class."""
    try:
        assets = await service.get_top_liquid_assets(asset_class, limit)

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

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting liquid assets: {str(e)}")


@router.get("/rankings/{asset_class}", response_model=Dict[str, Any])
async def get_asset_rankings_by_class(
    asset_class: AssetClass,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset rankings for a specific asset class."""
    try:
        ranking = await service.get_asset_rankings(asset_class)

        return {
            "success": True,
            "asset_class": asset_class.value,
            "ranking_date": ranking.ranking_date,
            "rankings": ranking.rankings,
            "count": len(ranking.rankings),
            "timestamp": datetime.utcnow(),
        }

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset rankings: {str(e)}")


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_asset_details(
    symbol: str,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get detailed asset information by symbol."""
    try:
        asset = await service.get_asset_details(symbol.upper())

        if not asset:
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

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset details: {str(e)}")


@router.get("/{symbol}/liquidity", response_model=Dict[str, Any])
async def get_liquidity_metrics(
    symbol: str,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get liquidity metrics for a specific asset."""
    try:
        metrics = await service.get_liquidity_metrics(symbol.upper())

        if not metrics:
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

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting liquidity metrics: {str(e)}")


@router.get("/rankings", response_model=Dict[str, Any])
async def get_asset_rankings(
    asset_class: Optional[AssetClass] = Query(None, description="Filter by asset class"),
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset rankings."""
    try:
        if asset_class:
            rankings = await service.get_asset_rankings(asset_class)
        else:
            # Get rankings for all asset classes
            rankings = {}
            for ac in AssetClass:
                rankings[ac.value] = await service.get_asset_rankings(ac)

        return {"success": True, "rankings": rankings, "timestamp": datetime.utcnow()}

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset rankings: {str(e)}")


@router.post("/filter", response_model=Dict[str, Any])
async def filter_assets(
    filter_criteria: AssetFilter,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Filter assets based on criteria."""
    try:
        filtered_assets = await service.filter_assets(None, filter_criteria)

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

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error filtering assets: {str(e)}")


@router.post("/refresh-liquidity", response_model=Dict[str, Any])
async def refresh_liquidity_data(
    background_tasks: BackgroundTasks = _DEFAULT_BACKGROUND_TASKS,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Refresh liquidity data for all assets."""
    try:
        # Start background task to refresh liquidity data
        background_tasks.add_task(service.refresh_liquidity_data)

        return {
            "success": True,
            "message": "Liquidity data refresh started",
            "timestamp": datetime.utcnow(),
        }

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing liquidity data: {str(e)}")


@router.get("/universe", response_model=Dict[str, Any])
async def get_asset_universe(
    asset_class: Optional[AssetClass] = Query(None, description="Filter by asset class"),
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset universe."""
    try:
        if asset_class:
            universe = await service.get_asset_universe(asset_class)
        else:
            # Get universe for all asset classes
            universe = {}
            for ac in AssetClass:
                universe[ac.value] = await service.get_asset_universe(ac)

        return {"success": True, "universe": universe, "timestamp": datetime.utcnow()}

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset universe: {str(e)}")


@router.post("/identify/{asset_class}", response_model=Dict[str, Any])
async def identify_liquid_assets(
    asset_class: AssetClass,
    limit: int = Query(20, ge=1, le=100, description="Number of assets to identify"),
    background_tasks: BackgroundTasks = _DEFAULT_BACKGROUND_TASKS,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Identify and rank liquid assets for a specific asset class."""
    try:
        # Identify liquid assets
        assets = await service.identify_liquid_assets(asset_class, limit)

        # Update universe in background
        background_tasks.add_task(service.update_asset_universe, asset_class, assets)

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

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        raise HTTPException(status_code=500, detail=f"Error identifying liquid assets: {str(e)}")


@router.post("/filter/{asset_class}", response_model=Dict[str, Any])
async def filter_assets_by_class(
    asset_class: AssetClass,
    filter_criteria: AssetFilter,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Filter assets based on criteria for a specific asset class."""
    try:
        filtered_assets = await service.filter_assets(asset_class, filter_criteria)

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

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error filtering assets: {str(e)}")


@router.get("/universe/{asset_class}", response_model=Dict[str, Any])
async def get_universe_summary(
    asset_class: AssetClass,
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get universe summary for a specific asset class."""
    try:
        summary = await service.get_universe_summary(asset_class)

        return {
            "success": True,
            "universe_summary": summary,
            "timestamp": datetime.utcnow(),
        }

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting universe summary: {str(e)}")


@router.get("/classes", response_model=Dict[str, Any])
async def get_asset_classes():
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

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset classes: {str(e)}")


@router.get("/exchanges", response_model=Dict[str, Any])
async def get_exchanges():
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

    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error getting exchanges: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for assets service."""
    try:
        return {
            "success": True,
            "status": "healthy",
            "service": "asset_identification",
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_asset_stats(
    service: AssetIdentificationService = Depends(get_asset_identification_service),
):
    """Get asset statistics across all universes."""
    try:
        stats = {
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
            summary = await service.get_universe_summary(asset_class)
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

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset stats: {str(e)}")
