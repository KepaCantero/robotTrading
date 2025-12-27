"""
Signal Management API Endpoints

FastAPI endpoints for signal scoring, evaluation, and management.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.models.signal import MarketData, Signal, SignalType
from app.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.portfolio_service import PortfolioService
from app.services.signal_scorer import SignalScorerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])

# Global signal scorer service instance
_signal_scorer_service: Optional[SignalScorerService] = None


def get_signal_scorer_service() -> SignalScorerService:
    """Get signal scorer service instance."""
    global _signal_scorer_service
    if _signal_scorer_service is None:
        portfolio_provider = PaperTradingPortfolioProvider()
        portfolio_service = PortfolioService(portfolio_provider)

    return _signal_scorer_service


class MarketDataRequest(BaseModel):
    """Request model for market data."""

    symbol: str
    price: float
    volume: float
    bid: float
    ask: float
    spread: float


class SignalEvaluationRequest(BaseModel):
    """Request model for signal evaluation."""

    symbol: str
    signal_type: str
    market_data: MarketDataRequest
    metadata: Dict[str, Any] = {}


class SignalResponse(BaseModel):
    """Response model for signal evaluation."""

    success: bool
    signal: Optional[Signal] = None
    message: str


class SignalStatisticsResponse(BaseModel):
    """Response model for signal statistics."""

    signals_processed: int
    signals_executed: int
    success_rate: float
    total_pnl: float
    queue_size: int
    queue_summary: Dict[str, Any]
    thresholds: Dict[str, float]


@router.post("/evaluate", response_model=SignalResponse)
async def evaluate_signal(
    request: SignalEvaluationRequest,
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Evaluate and score a trading signal."""
    try:
        # Convert request to MarketData
        market_data = MarketData(
            symbol=request.market_data.symbol,
            price=Decimal(str(request.market_data.price)),
            volume=Decimal(str(request.market_data.volume)),
            bid=Decimal(str(request.market_data.bid)),
            ask=Decimal(str(request.market_data.ask)),
            spread=Decimal(str(request.market_data.spread)),
            timestamp=datetime.utcnow(),
        )

        # Convert signal type
        try:
            signal_type = SignalType(request.signal_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid signal type: {request.signal_type}"
            )

        # Evaluate signal
        signal = await service.evaluate_signal(
            request.symbol, signal_type, market_data, request.metadata
        )

        if signal:
            return SignalResponse(
                success=True,
                signal=signal,
                message=f"Signal evaluated successfully for {request.symbol}",
            )
        else:
            return SignalResponse(
                success=False,
                signal=None,
                message=f"Signal for {request.symbol} does not meet minimum thresholds",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating signal: {str(e)}")


@router.get("/next", response_model=SignalResponse)
async def get_next_actionable_signal(
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Get next actionable signal from priority queue."""
    try:
        signal = await service.get_next_actionable_signal()

        if signal:
            return SignalResponse(
                success=True,
                signal=signal,
                message=f"Next actionable signal: {signal.symbol}",
            )
        else:
            return SignalResponse(
                success=False, signal=None, message="No actionable signals available"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting next signal: {str(e)}")


@router.post("/execute/{signal_id}")
async def execute_signal(
    signal_id: str,
    background_tasks: BackgroundTasks,
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Execute a trading signal."""
    try:
        # Get signals by symbol (using signal_id as symbol)
        signals = await service.get_signals_by_symbol(signal_id.upper())

        if not signals:
            return {
                "success": False,
                "message": f"No signals found for {signal_id}",
                "signal": None,
            }

        # Execute the first signal found
        signal = signals[0]
        success = await service.execute_signal(signal)

        if success:
            return {
                "success": True,
                "message": f"Signal executed successfully for {signal.symbol}",
                "signal": signal,
            }
        else:
            return {
                "success": False,
                "message": f"Failed to execute signal for {signal.symbol}",
                "signal": signal,
            }

    except Exception as e:
        logger.error(f"Error executing signal for {signal_id}: {e}")
        return {
            "success": False,
            "message": f"Error executing signal: {str(e)}",
            "signal": None,
        }


@router.get("/statistics", response_model=SignalStatisticsResponse)
async def get_signal_statistics(
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Get signal processing statistics."""
    try:
        stats = await service.get_signal_statistics()

        return SignalStatisticsResponse(
            signals_processed=stats.get("signals_processed", 0),
            signals_executed=stats.get("signals_executed", 0),
            success_rate=stats.get("success_rate", 0.0),
            total_pnl=stats.get("total_pnl", 0.0),
            queue_size=stats.get("queue_size", 0),
            queue_summary=stats.get("queue_summary", {}),
            thresholds={
                "confidence": stats.get("min_confidence_threshold", 60.0),
                "liquidity": stats.get("min_liquidity_threshold", 50.0),
                "max_position_size": stats.get("max_position_size_percent", 10.0),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.get("/symbol/{symbol}", response_model=List[Signal])
async def get_signals_by_symbol(
    symbol: str, service: SignalScorerService = Depends(get_signal_scorer_service)
):
    """Get all signals for a specific symbol."""
    try:
        signals = await service.get_signals_by_symbol(symbol.upper())
        return signals

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting signals for {symbol}: {str(e)}")


@router.post("/clear-expired")
async def clear_expired_signals(
    max_age_minutes: int = 60,
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Clear signals older than specified age."""
    try:
        await service.clear_expired_signals(max_age_minutes)
        return {
            "success": True,
            "message": f"Cleared signals older than {max_age_minutes} minutes",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing expired signals: {str(e)}")


@router.post("/thresholds")
async def update_thresholds(
    confidence_threshold: float,
    liquidity_threshold: float,
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Update minimum thresholds for signal evaluation."""
    try:
        if not (0 <= confidence_threshold <= 100):
            raise HTTPException(
                status_code=400, detail="Confidence threshold must be between 0 and 100"
            )

        if not (0 <= liquidity_threshold <= 100):
            raise HTTPException(
                status_code=400, detail="Liquidity threshold must be between 0 and 100"
            )

        service.update_thresholds(confidence_threshold, liquidity_threshold)

        return {
            "success": True,
            "message": f"Updated thresholds: confidence={confidence_threshold}%, liquidity={liquidity_threshold}%",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating thresholds: {str(e)}")


@router.post("/position-size-limit")
async def update_position_size_limit(
    max_percent: float,
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Update maximum position size limit."""
    try:
        if not (0 < max_percent <= 100):
            raise HTTPException(
                status_code=400, detail="Max position size must be between 0 and 100%"
            )

        service.update_position_size_limit(max_percent)

        return {
            "success": True,
            "message": f"Updated max position size: {max_percent}%",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating position size limit: {str(e)}")


@router.get("/health")
async def signal_health_check(
    service: SignalScorerService = Depends(get_signal_scorer_service),
):
    """Health check for signal scorer service."""
    try:
        stats = await service.get_signal_statistics()

        # Check if service is healthy
        if stats.get("signals_processed", 0) >= 0:  # Basic health check
            return {
                "status": "healthy",
                "message": "Signal scorer service operational",
                "statistics": {
                    "signals_processed": stats.get("signals_processed", 0),
                    "signals_executed": stats.get("signals_executed", 0),
                    "queue_size": stats.get("queue_size", 0),
                },
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Signal scorer service not responding properly",
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Signal scorer service error: {str(e)}",
        }
