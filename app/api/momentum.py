"""
FastAPI endpoints for momentum analysis and strategy management.

This module provides REST API endpoints for momentum analysis,
technical indicators, and momentum strategy management.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.momentum import (
    MomentumSignal, MomentumType, Timeframe, TechnicalIndicators,
    MomentumStrategy, MomentumAnalysis, MomentumFilter
)
from app.services.momentum_analysis import (
    MomentumAnalysisService, get_momentum_analysis_service
)

router = APIRouter(prefix="/momentum", tags=["momentum"])


@router.get("/", response_model=Dict[str, Any])
async def get_momentum_overview(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
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
                "timeframes": [tf.value for tf in Timeframe]
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting momentum overview: {str(e)}")


@router.get("/analyze/{symbol}", response_model=Dict[str, Any])
async def analyze_asset_momentum(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Analysis timeframe"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
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
                "macd_signal": analysis.indicators.macd_signal
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
                    "is_expired": signal.is_expired
                }
                for signal in analysis.signals
            ],
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing momentum for {symbol}: {str(e)}")


@router.get("/signals", response_model=Dict[str, Any])
async def get_momentum_signals(
    momentum_types: Optional[List[MomentumType]] = Query(None, description="Filter by momentum types"),
    timeframes: Optional[List[Timeframe]] = Query(None, description="Filter by timeframes"),
    min_strength: float = Query(50.0, ge=0, le=100, description="Minimum signal strength"),
    min_confidence: float = Query(60.0, ge=0, le=100, description="Minimum signal confidence"),
    active_only: bool = Query(True, description="Only active signals"),
    max_age_hours: int = Query(24, ge=1, description="Maximum signal age in hours"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of signals to return"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
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
            max_age_hours=max_age_hours
        )
        
        # Get filtered signals
        signals = await service.get_momentum_signals(filter_criteria)
        
        # Apply limit
        signals = signals[:limit]
        
        return {
            "success": True,
            "filter_criteria": {
                "momentum_types": [mt.value for mt in momentum_types] if momentum_types else None,
                "timeframes": [tf.value for tf in timeframes] if timeframes else None,
                "min_strength": min_strength,
                "min_confidence": min_confidence,
                "active_only": active_only,
                "max_age_hours": max_age_hours,
                "limit": limit
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
                    "time_to_expiry": signal.time_to_expiry.total_seconds() / 3600 if not signal.is_expired else 0
                }
                for signal in signals
            ],
            "count": len(signals),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting momentum signals: {str(e)}")


@router.get("/signals/top", response_model=Dict[str, Any])
async def get_top_momentum_signals(
    limit: int = Query(10, ge=1, le=50, description="Number of top signals to return"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
):
    """Get top momentum signals by momentum score."""
    try:
        top_assets = await service.get_top_momentum_assets(limit)
        
        return {
            "success": True,
            "limit": limit,
            "top_signals": top_assets,
            "count": len(top_assets),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting top momentum signals: {str(e)}")


@router.get("/strategies", response_model=Dict[str, Any])
async def get_momentum_strategies(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
):
    """Get available momentum strategies."""
    try:
        strategies = []
        
        for name, strategy in service.strategies.items():
            strategies.append({
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
                "updated_at": strategy.updated_at
            })
        
        return {
            "success": True,
            "strategies": strategies,
            "count": len(strategies),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting momentum strategies: {str(e)}")


@router.get("/strategies/{strategy_name}/signals", response_model=Dict[str, Any])
async def get_strategy_signals(
    strategy_name: str,
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
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
                "timestamp": datetime.utcnow()
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
                    "is_expired": signal.is_expired
                }
                for signal in signals
            ],
            "count": len(signals),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting signals for strategy {strategy_name}: {str(e)}")


@router.post("/analyze/batch", response_model=Dict[str, Any])
async def analyze_multiple_assets(
    symbols: List[str],
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Analysis timeframe"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
):
    """Analyze momentum for multiple assets."""
    try:
        if len(symbols) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 symbols allowed per batch")
        
        analyses = []
        errors = []
        
        for symbol in symbols:
            try:
                analysis = await service.analyze_asset_momentum(symbol.upper(), timeframe)
                analyses.append({
                    "symbol": analysis.symbol,
                    "overall_momentum": analysis.overall_momentum,
                    "trend_direction": analysis.trend_direction,
                    "signal_count": analysis.signal_count,
                    "risk_level": analysis.risk_level,
                    "volatility_level": analysis.volatility_level
                })
            except Exception as e:
                errors.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "timeframe": timeframe.value,
            "requested_symbols": symbols,
            "analyses": analyses,
            "errors": errors,
            "successful_count": len(analyses),
            "error_count": len(errors),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing multiple assets: {str(e)}")


@router.get("/indicators/{symbol}", response_model=Dict[str, Any])
async def get_technical_indicators(
    symbol: str,
    timeframe: Timeframe = Query(Timeframe.DAILY, description="Indicator timeframe"),
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
):
    """Get technical indicators for a specific asset."""
    try:
        analysis = await service.analyze_asset_momentum(symbol.upper(), timeframe)
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
                "volume_sma_20": float(indicators.volume_sma_20) if indicators.volume_sma_20 else None,
                "volume_ratio": indicators.volume_ratio,
                "ema_trend": indicators.ema_trend,
                "rsi_signal": indicators.rsi_signal,
                "macd_signal": indicators.macd_signal
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting technical indicators for {symbol}: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def momentum_health_check():
    """Health check endpoint for momentum service."""
    try:
        return {
            "success": True,
            "status": "healthy",
            "service": "momentum_analysis",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Momentum health check failed: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_momentum_stats(
    service: MomentumAnalysisService = Depends(get_momentum_analysis_service)
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
        avg_strength = sum(s.strength for s in all_signals) / total_signals if total_signals > 0 else 0
        avg_confidence = sum(s.confidence for s in all_signals) / total_signals if total_signals > 0 else 0
        avg_momentum_score = sum(s.momentum_score for s in all_signals) / total_signals if total_signals > 0 else 0
        
        return {
            "success": True,
            "stats": {
                "total_signals": total_signals,
                "active_signals": active_signals,
                "expired_signals": expired_signals,
                "signal_types": signal_types,
                "direction_distribution": {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals
                },
                "average_scores": {
                    "strength": round(avg_strength, 2),
                    "confidence": round(avg_confidence, 2),
                    "momentum_score": round(avg_momentum_score, 2)
                },
                "total_analyses": len(service.analyses),
                "available_strategies": len(service.strategies)
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting momentum stats: {str(e)}")
