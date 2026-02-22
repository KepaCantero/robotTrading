"""
FastAPI endpoints for momentum analysis and strategy management.

This module provides REST API endpoints for momentum analysis,
technical indicators, and momentum strategy management.
"""
# mypy: ignore-errors

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from requests.exceptions import ConnectionError, HTTPError, RequestException

from app.domain.models.momentum import MomentumFilter, MomentumStrategy, MomentumType, Timeframe
from app.domain.services.analysis.momentum import MomentumAnalysisService, get_momentum_analysis_service

# Constants
DEFAULT_VALUE_20 = 20
DEFAULT_VALUE_21 = 21
DEFAULT_VALUE_24 = 24
DEFAULT_VALUE_30 = 30
DEFAULT_VALUE_400 = 400
DEFAULT_VALUE_404 = 404
DEFAULT_VALUE_422 = 422
DEFAULT_VALUE_500 = 500
DEFAULT_VALUE_70 = 70
DEFAULT_VALUE_9 = 9
MAX_20 = 20
MAX_200 = 200
MAX_24 = 24
MAX_400 = 400
MAX_50 = 50


router = APIRouter(prefix="/momentum", tags=["momentum"])


@router.get("/", response_model=Dict[str, Any])
async def get_momentum_overview(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get overview of momentum analysis system."""
    try:
        # Get top momentum assets
        top_assets = await service.get_top_momentum_assets(10)

        # Get available strategies
        strategies = list(service.strategies.keys())

        # Get analysis count
        analysis_count = len(service.analyses)

        return {
            "success": True,
            "overview": {
                "total_analyses": analysis_count,
                "available_strategies": strategies,
                "top_momentum_assets": top_assets,
                "momentum_types": [mt.value for mt in MomentumType],
                "timeframes": [tf.value for tf in Timeframe],
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum overview: {str(e)}"
        )


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_asset_momentum_post(
    request_data: Dict[str, Any],
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Analyze momentum for a specific asset via POST request."""
    try:
        symbol = request_data.get("symbol", "").upper()
        timeframe_str = request_data.get("timeframe", "daily")
        request_data.get("momentum_types", [])

        if not symbol:
            raise HTTPException(status_code=DEFAULT_VALUE_400, detail="Symbol is required")

        # Convert timeframe string to enum
        timeframe_mapping = {
            "daily": Timeframe.DAILY,
            "1d": Timeframe.DAILY,
            "hourly": Timeframe.HOURLY,
            "1h": Timeframe.HOURLY,
            "4h": Timeframe.FOUR_HOUR,
            "weekly": Timeframe.WEEKLY,
            "1w": Timeframe.WEEKLY,
        }

        timeframe = timeframe_mapping.get(timeframe_str.lower())
        if not timeframe:
            raise HTTPException(
                status_code=DEFAULT_VALUE_400, detail=f"Invalid timeframe: {timeframe_str}"
            )

        # Analyze asset momentum
        analysis = await service.analyze_asset_momentum(symbol, timeframe)

        if not analysis:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"No analysis found for {symbol}"
            )

        return {
            "success": True,
            "analysis": {
                "symbol": analysis.symbol,
                "timeframe": analysis.timeframe.value,
                "analysis_date": analysis.analysis_date,
                "overall_momentum": analysis.overall_momentum,
                "trend_direction": analysis.trend_direction,
                "signal_count": analysis.signal_count,
                "risk_level": analysis.risk_level,
                "volatility_level": analysis.volatility_level,
                "indicators": {
                    "rsi": analysis.indicators.rsi,
                    "ema_9": analysis.indicators.ema_9,
                    "ema_21": analysis.indicators.ema_21,
                    "ema_50": analysis.indicators.ema_50,
                    "ema_200": analysis.indicators.ema_200,
                    "macd": analysis.indicators.macd,
                    "macd_signal": analysis.indicators.macd_signal,
                    "macd_histogram": analysis.indicators.macd_histogram,
                    "atr": analysis.indicators.atr,
                    "volatility": analysis.indicators.volatility,
                    "volume_ratio": analysis.indicators.volume_ratio,
                    "ema_trend": analysis.indicators.ema_trend,
                    "rsi_signal": analysis.indicators.rsi_signal,
                },
                "signals": [
                    {
                        "signal_type": signal.signal_type.value,
                        "strength": signal.strength,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "momentum_score": signal.momentum_score,
                        "current_price": float(signal.current_price),
                        "price_change_pct": signal.price_change_pct,
                        "volume_change_pct": signal.volume_change_pct,
                        "timestamp": signal.timestamp,
                        "expires_at": signal.expires_at,
                        "is_expired": signal.is_expired,
                    }
                    for signal in analysis.signals
                ],
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error analyzing momentum for {symbol}: {str(e)}"
        )


@router.get("/analyze/{symbol}", response_model=Dict[str, Any])
async def analyze_asset_momentum(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Analysis timeframe"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Analyze momentum for a specific asset."""
    try:
        analysis = await service.analyze_asset_momentum(symbol.upper(), timeframe)

        return {
            "success": True,
            "symbol": analysis.symbol,
            "timeframe": analysis.timeframe.value,
            "analysis_date": analysis.analysis_date,
            "overall_momentum": analysis.overall_momentum,
            "trend_direction": analysis.trend_direction,
            "signal_count": analysis.signal_count,
            "risk_level": analysis.risk_level,
            "volatility_level": analysis.volatility_level,
            "indicators": {
                "rsi": analysis.indicators.rsi,
                "ema_9": analysis.indicators.ema_9,
                "ema_21": analysis.indicators.ema_21,
                "ema_50": analysis.indicators.ema_50,
                "ema_200": analysis.indicators.ema_200,
                "macd": analysis.indicators.macd,
                "macd_signal": analysis.indicators.macd_signal,
                "macd_histogram": analysis.indicators.macd_histogram,
                "atr": analysis.indicators.atr,
                "volatility": analysis.indicators.volatility,
                "volume_ratio": analysis.indicators.volume_ratio,
                "ema_trend": analysis.indicators.ema_trend,
                "rsi_signal": analysis.indicators.rsi_signal,
            },
            "signals": [
                {
                    "signal_type": signal.signal_type.value,
                    "strength": signal.strength,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "momentum_score": signal.momentum_score,
                    "current_price": float(signal.current_price),
                    "price_change_pct": signal.price_change_pct,
                    "volume_change_pct": signal.volume_change_pct,
                    "rsi": signal.rsi,
                    "ema_short": signal.ema_short,
                    "ema_long": signal.ema_long,
                    "macd": signal.macd,
                    "macd_signal": signal.macd_signal,
                    "macd_histogram": signal.macd_histogram,
                    "timestamp": signal.timestamp,
                    "expires_at": signal.expires_at,
                    "is_expired": signal.is_expired,
                }
                for signal in analysis.signals
            ],
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error analyzing momentum for {symbol}: {str(e)}"
        )


@router.get("/signals/{symbol}", response_model=Dict[str, Any])
async def get_momentum_signals_for_symbol(
    symbol: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get momentum signals for a specific asset."""
    try:
        signals = await service.get_momentum_signals_for_symbol(symbol.upper())
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500,
            detail=f"Error getting momentum signals for {symbol}: {str(e)}",
        )

    if not signals:
        raise HTTPException(
            status_code=DEFAULT_VALUE_404, detail=f"No momentum signals found for {symbol.upper()}"
        )

    return {
        "success": True,
        "symbol": symbol.upper(),
        "signals": [
            {
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "timeframe": signal.timeframe.value,
                "strength": signal.strength,
                "direction": signal.direction,
                "confidence": signal.confidence,
                "momentum_score": signal.momentum_score,
                "current_price": float(signal.current_price),
                "price_change_pct": signal.price_change_pct,
                "volume_change_pct": signal.volume_change_pct,
                "timestamp": signal.timestamp,
                "expires_at": signal.expires_at,
                "is_expired": signal.is_expired,
            }
            for signal in signals
        ],
        "count": len(signals),
        "timestamp": datetime.utcnow(),
    }


@router.get("/signals", response_model=Dict[str, Any])
async def get_momentum_signals(
    momentum_types: Optional[List[MomentumType]] = Query(
        None, description="Filter by momentum types"
    ),
    timeframes: Optional[List[Timeframe]] = Query(None, description="Filter by timeframes"),
    min_strength: float = Query(50.0, ge=0, le=100, description="Minimum signal strength"),
    min_confidence: float = Query(60.0, ge=0, le=100, description="Minimum signal confidence"),
    active_only: bool = Query(True, description="Only active signals"),
    max_age_hours: int = Query(MAX_24, ge=1, description="Maximum signal age in hours"),
    limit: int = Query(50, ge=1, le=MAX_200, description="Maximum number of signals to return"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get momentum signals with filtering options."""
    try:
        # Create filter criteria
        filter_criteria = MomentumFilter(
            momentum_types=momentum_types,
            timeframes=timeframes,
            min_strength=min_strength,
            min_confidence=min_confidence,
            active_only=active_only,
            max_age_hours=max_age_hours,
        )

        # Get filtered signals
        signals = await service.get_momentum_signals(filter_criteria)

        # Apply limit
        signals = signals[:limit]

        return {
            "success": True,
            "filter_criteria": {
                "momentum_types": ([mt.value for mt in momentum_types] if momentum_types else None),
                "timeframes": [tf.value for tf in timeframes] if timeframes else None,
                "min_strength": min_strength,
                "min_confidence": min_confidence,
                "active_only": active_only,
                "max_age_hours": max_age_hours,
                "limit": limit,
            },
            "signals": [
                {
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "timeframe": signal.timeframe.value,
                    "strength": signal.strength,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "momentum_score": signal.momentum_score,
                    "current_price": float(signal.current_price),
                    "price_change_pct": signal.price_change_pct,
                    "volume_change_pct": signal.volume_change_pct,
                    "rsi": signal.rsi,
                    "ema_short": signal.ema_short,
                    "ema_long": signal.ema_long,
                    "macd": signal.macd,
                    "macd_signal": signal.macd_signal,
                    "macd_histogram": signal.macd_histogram,
                    "timestamp": signal.timestamp,
                    "expires_at": signal.expires_at,
                    "is_expired": signal.is_expired,
                    "time_to_expiry": (
                        signal.time_to_expiry.total_seconds() / 3600 if not signal.is_expired else 0
                    ),
                }
                for signal in signals
            ],
            "count": len(signals),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum signals: {str(e)}"
        )


@router.get("/signals/top", response_model=Dict[str, Any])
async def get_top_momentum_signals(
    limit: int = Query(10, ge=1, le=MAX_50, description="Number of top signals to return"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get top momentum signals by momentum score."""
    try:
        top_assets = await service.get_top_momentum_assets(limit)

        return {
            "success": True,
            "limit": limit,
            "top_signals": top_assets,
            "count": len(top_assets),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting top momentum signals: {str(e)}"
        )


@router.post("/strategies", response_model=Dict[str, Any])
async def create_momentum_strategy(
    strategy_data: Dict[str, Any],
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Create a new momentum strategy."""
    try:
        # Validate required fields
        required_fields = ["name", "description", "timeframe"]

        # Check for momentum_type or momentum_types
        if "momentum_type" not in strategy_data and "momentum_types" not in strategy_data:
            raise HTTPException(
                status_code=DEFAULT_VALUE_422,
                detail="Missing required field: momentum_type or momentum_types",
            )

        for field in required_fields:
            if field not in strategy_data:
                raise HTTPException(
                    status_code=DEFAULT_VALUE_422, detail=f"Missing required field: {field}"
                )

        # Convert momentum_type string to enum
        momentum_type_str = strategy_data.get("momentum_type", "price_momentum")

        # Handle both "momentum_type" and "momentum_types" formats
        if "momentum_types" in strategy_data and "momentum_type" not in strategy_data:
            momentum_types_list = strategy_data["momentum_types"]
            if isinstance(momentum_types_list, list) and len(momentum_types_list) > 0:
                momentum_type_str = momentum_types_list[0]

        momentum_type_mapping = {
            "price": MomentumType.PRICE_MOMENTUM,
            "price_momentum": MomentumType.PRICE_MOMENTUM,
            "volume": MomentumType.VOLUME_MOMENTUM,
            "volume_momentum": MomentumType.VOLUME_MOMENTUM,
            "volatility": MomentumType.VOLATILITY_MOMENTUM,
            "volatility_momentum": MomentumType.VOLATILITY_MOMENTUM,
        }
        momentum_type = momentum_type_mapping.get(momentum_type_str.lower())
        if not momentum_type:
            raise HTTPException(
                status_code=DEFAULT_VALUE_422, detail=f"Invalid momentum_type: {momentum_type_str}"
            )

        # Convert timeframe string to enum
        timeframe_str = strategy_data.get("timeframe", "daily")
        timeframe_mapping = {
            "daily": Timeframe.DAILY,
            "1d": Timeframe.DAILY,
            "hourly": Timeframe.HOURLY,
            "1h": Timeframe.HOURLY,
            "4h": Timeframe.FOUR_HOUR,
            "weekly": Timeframe.WEEKLY,
            "1w": Timeframe.WEEKLY,
        }
        timeframe = timeframe_mapping.get(timeframe_str.lower())
        if not timeframe:
            raise HTTPException(
                status_code=DEFAULT_VALUE_422, detail=f"Invalid timeframe: {timeframe_str}"
            )

        # Create strategy object
        strategy = MomentumStrategy(
            name=strategy_data["name"],
            description=strategy_data["description"],
            momentum_type=momentum_type,
            timeframe=timeframe,
            min_strength=strategy_data.get("min_strength", 0.5),
            min_confidence=strategy_data.get("min_confidence", 0.7),
            signal_duration=strategy_data.get("signal_duration", DEFAULT_VALUE_24),
            rsi_oversold=strategy_data.get("rsi_oversold", DEFAULT_VALUE_30),
            rsi_overbought=strategy_data.get("rsi_overbought", DEFAULT_VALUE_70),
            ema_short_period=strategy_data.get("ema_short_period", DEFAULT_VALUE_9),
            ema_long_period=strategy_data.get("ema_long_period", DEFAULT_VALUE_21),
            min_volume_ratio=strategy_data.get("min_volume_ratio", 1.2),
            volume_spike_threshold=strategy_data.get("volume_spike_threshold", 2.0),
            max_position_size=strategy_data.get("max_position_size", 10),
            stop_loss_pct=strategy_data.get("stop_loss_pct", 0.05),
            take_profit_pct=strategy_data.get("take_profit_pct", 0.10),
            is_active=strategy_data.get("is_active", True),
        )

        # Create strategy via service
        created_strategy = await service.create_strategy(strategy)

        return {
            "success": True,
            "strategy": {
                "name": created_strategy.name,
                "description": created_strategy.description,
                "momentum_type": created_strategy.momentum_type.value,
                "timeframe": created_strategy.timeframe.value,
                "min_strength": created_strategy.min_strength,
                "min_confidence": created_strategy.min_confidence,
                "signal_duration": created_strategy.signal_duration,
                "rsi_oversold": created_strategy.rsi_oversold,
                "rsi_overbought": created_strategy.rsi_overbought,
                "ema_short_period": created_strategy.ema_short_period,
                "ema_long_period": created_strategy.ema_long_period,
                "min_volume_ratio": created_strategy.min_volume_ratio,
                "volume_spike_threshold": created_strategy.volume_spike_threshold,
                "max_position_size": created_strategy.max_position_size,
                "stop_loss_pct": created_strategy.stop_loss_pct,
                "take_profit_pct": created_strategy.take_profit_pct,
                "is_active": created_strategy.is_active,
                "created_at": created_strategy.created_at,
                "updated_at": created_strategy.updated_at,
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error creating momentum strategy: {str(e)}"
        )


@router.get("/strategies/{strategy_name}", response_model=Dict[str, Any])
async def get_momentum_strategy(
    strategy_name: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get a specific momentum strategy."""
    try:
        strategy = await service.get_strategy(strategy_name)

        if not strategy:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Strategy {strategy_name} not found"
            )

        return {
            "success": True,
            "strategy": {
                "name": strategy.name,
                "description": strategy.description,
                "momentum_type": strategy.momentum_type.value,
                "timeframe": strategy.timeframe.value,
                "min_strength": strategy.min_strength,
                "min_confidence": strategy.min_confidence,
                "signal_duration": strategy.signal_duration,
                "rsi_oversold": strategy.rsi_oversold,
                "rsi_overbought": strategy.rsi_overbought,
                "ema_short_period": strategy.ema_short_period,
                "ema_long_period": strategy.ema_long_period,
                "min_volume_ratio": strategy.min_volume_ratio,
                "volume_spike_threshold": strategy.volume_spike_threshold,
                "max_position_size": strategy.max_position_size,
                "stop_loss_pct": strategy.stop_loss_pct,
                "take_profit_pct": strategy.take_profit_pct,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at,
                "updated_at": strategy.updated_at,
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum strategy: {str(e)}"
        )


@router.put("/strategies/{strategy_name}", response_model=Dict[str, Any])
async def update_momentum_strategy(
    strategy_name: str,
    strategy_data: Dict[str, Any],
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Update a momentum strategy."""
    try:
        # Get existing strategy
        existing_strategy = await service.get_strategy(strategy_name)
        if not existing_strategy:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Strategy {strategy_name} not found"
            )

        # Update fields if provided
        updated_fields = {}
        for field in [
            "description",
            "min_strength",
            "min_confidence",
            "signal_duration",
            "rsi_oversold",
            "rsi_overbought",
            "ema_short_period",
            "ema_long_period",
            "min_volume_ratio",
            "volume_spike_threshold",
            "max_position_size",
            "stop_loss_pct",
            "take_profit_pct",
            "is_active",
        ]:
            if field in strategy_data:
                updated_fields[field] = strategy_data[field]

        # Update strategy via service
        updated_strategy = await service.update_strategy(strategy_name, updated_fields)

        return {
            "success": True,
            "strategy": {
                "name": updated_strategy.name,
                "description": updated_strategy.description,
                "momentum_type": updated_strategy.momentum_type.value,
                "timeframe": updated_strategy.timeframe.value,
                "min_strength": updated_strategy.min_strength,
                "min_confidence": updated_strategy.min_confidence,
                "signal_duration": updated_strategy.signal_duration,
                "rsi_oversold": updated_strategy.rsi_oversold,
                "rsi_overbought": updated_strategy.rsi_overbought,
                "ema_short_period": updated_strategy.ema_short_period,
                "ema_long_period": updated_strategy.ema_long_period,
                "min_volume_ratio": updated_strategy.min_volume_ratio,
                "volume_spike_threshold": updated_strategy.volume_spike_threshold,
                "max_position_size": updated_strategy.max_position_size,
                "stop_loss_pct": updated_strategy.stop_loss_pct,
                "take_profit_pct": updated_strategy.take_profit_pct,
                "is_active": updated_strategy.is_active,
                "created_at": updated_strategy.created_at,
                "updated_at": updated_strategy.updated_at,
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error updating momentum strategy: {str(e)}"
        )


@router.delete("/strategies/{strategy_name}", response_model=Dict[str, Any])
async def delete_momentum_strategy(
    strategy_name: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Delete a momentum strategy."""
    try:
        # Check if strategy exists
        existing_strategy = await service.get_strategy(strategy_name)
        if not existing_strategy:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Strategy {strategy_name} not found"
            )

        # Delete strategy via service
        success = await service.delete_strategy(strategy_name)

        if not success:
            raise HTTPException(
                status_code=DEFAULT_VALUE_500, detail=f"Failed to delete strategy {strategy_name}"
            )

        return {
            "success": True,
            "message": f"Strategy {strategy_name} deleted successfully",
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error deleting momentum strategy: {str(e)}"
        )


@router.get("/strategies", response_model=Dict[str, Any])
async def get_momentum_strategies(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get available momentum strategies."""
    try:
        strategies = []

        for name, strategy in service.strategies.items():
            strategies.append(
                {
                    "name": strategy.name,
                    "description": strategy.description,
                    "momentum_type": strategy.momentum_type.value,
                    "timeframe": strategy.timeframe.value,
                    "min_strength": strategy.min_strength,
                    "min_confidence": strategy.min_confidence,
                    "signal_duration": strategy.signal_duration,
                    "rsi_oversold": strategy.rsi_oversold,
                    "rsi_overbought": strategy.rsi_overbought,
                    "ema_short_period": strategy.ema_short_period,
                    "ema_long_period": strategy.ema_long_period,
                    "min_volume_ratio": strategy.min_volume_ratio,
                    "volume_spike_threshold": strategy.volume_spike_threshold,
                    "max_position_size": strategy.max_position_size,
                    "stop_loss_pct": strategy.stop_loss_pct,
                    "take_profit_pct": strategy.take_profit_pct,
                    "is_active": strategy.is_active,
                    "created_at": strategy.created_at,
                    "updated_at": strategy.updated_at,
                }
            )

        return {
            "success": True,
            "strategies": strategies,
            "count": len(strategies),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum strategies: {str(e)}"
        )


@router.get("/strategies/{strategy_name}/signals", response_model=Dict[str, Any])
async def get_strategy_signals(
    strategy_name: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get signals for a specific strategy."""
    try:
        signals = await service.get_strategy_signals(strategy_name)

        if not signals:
            return {
                "success": True,
                "strategy_name": strategy_name,
                "signals": [],
                "count": 0,
                "message": f"No signals found for strategy {strategy_name}",
                "timestamp": datetime.utcnow(),
            }

        return {
            "success": True,
            "strategy_name": strategy_name,
            "signals": [
                {
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "timeframe": signal.timeframe.value,
                    "strength": signal.strength,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "momentum_score": signal.momentum_score,
                    "current_price": float(signal.current_price),
                    "price_change_pct": signal.price_change_pct,
                    "volume_change_pct": signal.volume_change_pct,
                    "timestamp": signal.timestamp,
                    "expires_at": signal.expires_at,
                    "is_expired": signal.is_expired,
                }
                for signal in signals
            ],
            "count": len(signals),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500,
            detail=f"Error getting signals for strategy {strategy_name}: {str(e)}",
        )


@router.post("/analyze/batch", response_model=Dict[str, Any])
async def analyze_multiple_assets(
    symbols: List[str],
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Analysis timeframe"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Analyze momentum for multiple assets."""
    try:
        if len(symbols) > DEFAULT_VALUE_20:
            raise HTTPException(status_code=400, detail="Maximum MAX_20 symbols allowed per batch")

        analyses = []
        errors = []

        for symbol in symbols:
            try:
                analysis = await service.analyze_asset_momentum(symbol.upper(), timeframe)
                analyses.append(
                    {
                        "symbol": analysis.symbol,
                        "overall_momentum": analysis.overall_momentum,
                        "trend_direction": analysis.trend_direction,
                        "signal_count": analysis.signal_count,
                        "risk_level": analysis.risk_level,
                        "volatility_level": analysis.volatility_level,
                    }
                )
            except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
                errors.append({"symbol": symbol, "error": str(e)})

        return {
            "success": True,
            "timeframe": timeframe.value,
            "requested_symbols": symbols,
            "analyses": analyses,
            "errors": errors,
            "successful_count": len(analyses),
            "error_count": len(errors),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error analyzing multiple assets: {str(e)}"
        )


@router.get("/indicators/{symbol}", response_model=Dict[str, Any])
async def get_technical_indicators(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Indicator timeframe"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get technical indicators for a specific asset."""
    try:
        analysis = await service.analyze_asset_momentum(symbol.upper(), timeframe)
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500,
            detail=f"Error getting technical indicators for {symbol}: {str(e)}",
        )

    if not analysis:
        raise HTTPException(
            status_code=DEFAULT_VALUE_404, detail=f"Analysis not found for {symbol.upper()}"
        )

    indicators = analysis.indicators

    return {
        "success": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "indicators": {
            "rsi": indicators.rsi,
            "ema_9": indicators.ema_9,
            "ema_21": indicators.ema_21,
            "ema_50": indicators.ema_50,
            "ema_200": indicators.ema_200,
            "macd": indicators.macd,
            "macd_signal": indicators.macd_signal,
            "macd_histogram": indicators.macd_histogram,
            "atr": indicators.atr,
            "volatility": indicators.volatility,
            "volume_sma_20": (
                float(indicators.volume_sma_20) if indicators.volume_sma_20 else None
            ),
            "volume_ratio": indicators.volume_ratio,
            "ema_trend": indicators.ema_trend,
            "rsi_signal": indicators.rsi_signal,
        },
        "timestamp": datetime.utcnow(),
    }


@router.get("/health", response_model=Dict[str, Any])
async def momentum_health_check():
    """Health check endpoint for momentum service."""
    try:
        return {
            "success": True,
            "status": "healthy",
            "service": "momentum_analysis",
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Momentum health check failed: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_momentum_stats(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get momentum analysis statistics."""
    try:
        # Get all signals
        all_signals = await service.get_momentum_signals()

        # Calculate statistics
        total_signals = len(all_signals)
        active_signals = len([s for s in all_signals if not s.is_expired])
        expired_signals = total_signals - active_signals

        # Signal type distribution
        signal_types = {}
        for signal in all_signals:
            signal_type = signal.signal_type.value
            signal_types[signal_type] = signal_types.get(signal_type, 0) + 1

        # Direction distribution
        buy_signals = len([s for s in all_signals if s.direction == "BUY"])
        sell_signals = len([s for s in all_signals if s.direction == "SELL"])

        # Average scores
        avg_strength = (
            sum(s.strength for s in all_signals) / total_signals if total_signals > 0 else 0
        )
        avg_confidence = (
            sum(s.confidence for s in all_signals) / total_signals if total_signals > 0 else 0
        )
        avg_momentum_score = (
            sum(s.momentum_score for s in all_signals) / total_signals if total_signals > 0 else 0
        )

        return {
            "success": True,
            "stats": {
                "total_signals": total_signals,
                "active_signals": active_signals,
                "expired_signals": expired_signals,
                "signal_types": signal_types,
                "direction_distribution": {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                },
                "average_scores": {
                    "strength": round(avg_strength, 2),
                    "confidence": round(avg_confidence, 2),
                    "momentum_score": round(avg_momentum_score, 2),
                },
                "total_analyses": len(service.analyses),
                "available_strategies": len(service.strategies),
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum stats: {str(e)}"
        )


@router.get("/analyses", response_model=Dict[str, Any])
async def get_momentum_analyses(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get all momentum analyses."""
    try:
        analyses = await service.get_analyses()

        analyses_data = []
        for analysis in analyses:
            analyses_data.append(
                {
                    "symbol": analysis.symbol,
                    "timeframe": analysis.timeframe.value,
                    "analysis_date": analysis.analysis_date,
                    "overall_momentum": analysis.overall_momentum,
                    "trend_direction": analysis.trend_direction,
                    "signal_count": analysis.signal_count,
                    "risk_level": analysis.risk_level,
                    "volatility_level": analysis.volatility_level,
                    "indicators": {
                        "rsi": analysis.indicators.rsi,
                        "ema_9": analysis.indicators.ema_9,
                        "ema_21": analysis.indicators.ema_21,
                        "ema_50": analysis.indicators.ema_50,
                        "ema_200": analysis.indicators.ema_200,
                        "macd": analysis.indicators.macd,
                        "macd_signal": analysis.indicators.macd_signal,
                        "macd_histogram": analysis.indicators.macd_histogram,
                        "atr": analysis.indicators.atr,
                        "volatility": analysis.indicators.volatility,
                        "volume_ratio": analysis.indicators.volume_ratio,
                        "ema_trend": analysis.indicators.ema_trend,
                        "rsi_signal": analysis.indicators.rsi_signal,
                    },
                    "signals": [
                        {
                            "signal_type": signal.signal_type.value,
                            "strength": signal.strength,
                            "direction": signal.direction,
                            "confidence": signal.confidence,
                            "momentum_score": signal.momentum_score,
                            "current_price": float(signal.current_price),
                            "price_change_pct": signal.price_change_pct,
                            "volume_change_pct": signal.volume_change_pct,
                            "timestamp": signal.timestamp,
                            "expires_at": signal.expires_at,
                            "is_expired": signal.is_expired,
                        }
                        for signal in analysis.signals
                    ],
                }
            )

        return {
            "success": True,
            "analyses": analyses_data,
            "count": len(analyses_data),
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum analyses: {str(e)}"
        )


@router.get("/analyses/{analysis_id}", response_model=Dict[str, Any])
async def get_momentum_analysis(
    analysis_id: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Get a specific momentum analysis."""
    try:
        analysis = await service.get_analysis(analysis_id)

        if not analysis:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Analysis {analysis_id} not found"
            )

        return {
            "success": True,
            "analysis": {
                "symbol": analysis.symbol,
                "timeframe": analysis.timeframe.value,
                "analysis_date": analysis.analysis_date,
                "overall_momentum": analysis.overall_momentum,
                "trend_direction": analysis.trend_direction,
                "signal_count": analysis.signal_count,
                "risk_level": analysis.risk_level,
                "volatility_level": analysis.volatility_level,
                "indicators": {
                    "rsi": analysis.indicators.rsi,
                    "ema_9": analysis.indicators.ema_9,
                    "ema_21": analysis.indicators.ema_21,
                    "ema_50": analysis.indicators.ema_50,
                    "ema_200": analysis.indicators.ema_200,
                    "macd": analysis.indicators.macd,
                    "macd_signal": analysis.indicators.macd_signal,
                    "macd_histogram": analysis.indicators.macd_histogram,
                    "atr": analysis.indicators.atr,
                    "volatility": analysis.indicators.volatility,
                    "volume_ratio": analysis.indicators.volume_ratio,
                    "ema_trend": analysis.indicators.ema_trend,
                    "rsi_signal": analysis.indicators.rsi_signal,
                },
                "signals": [
                    {
                        "signal_type": signal.signal_type.value,
                        "strength": signal.strength,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "momentum_score": signal.momentum_score,
                        "current_price": float(signal.current_price),
                        "price_change_pct": signal.price_change_pct,
                        "volume_change_pct": signal.volume_change_pct,
                        "timestamp": signal.timestamp,
                        "expires_at": signal.expires_at,
                        "is_expired": signal.is_expired,
                    }
                    for signal in analysis.signals
                ],
            },
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting momentum analysis: {str(e)}"
        )


@router.delete("/analyses/{analysis_id}", response_model=Dict[str, Any])
async def delete_momentum_analysis(
    analysis_id: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service),
):
    """Delete a momentum analysis."""
    try:
        # Check if analysis exists
        existing_analysis = await service.get_analysis(analysis_id)
        if not existing_analysis:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Analysis {analysis_id} not found"
            )

        # Delete analysis via service
        success = await service.delete_analysis(analysis_id)

        if not success:
            raise HTTPException(
                status_code=DEFAULT_VALUE_500, detail=f"Failed to delete analysis {analysis_id}"
            )

        return {
            "success": True,
            "message": f"Analysis {analysis_id} deleted successfully",
            "timestamp": datetime.utcnow(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error deleting momentum analysis: {str(e)}"
        )
