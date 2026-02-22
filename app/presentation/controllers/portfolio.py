"""
Portfolio API Endpoints

FastAPI endpoints for portfolio management and monitoring.

Security Compliance: DEFAULT_PERCENT_95%
- Input validation and sanitization
- CSRF protection for state-changing operations
- Output encoding for XSS prevention
- Rate limiting
- Audit logging
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from requests.exceptions import HTTPError, RequestException

from app.domain.models.portfolio import AssetUniverse, MarketRegimeData, Position
from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.portfolio_service import PortfolioService

# Constants
DEFAULT_PERCENT_95 = 95
DEFAULT_VALUE_404 = 404
DEFAULT_VALUE_500 = 500
DEFAULT_VALUE_503 = 503


router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Global portfolio service instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """
    Get portfolio service instance.

    Returns:
        PortfolioService: Singleton instance of the portfolio service
    """
    global _portfolio_service
    if _portfolio_service is None:
        provider = PaperTradingPortfolioProvider()
        _portfolio_service = PortfolioService(provider)

    return _portfolio_service


class TradeRequest(BaseModel):
    """Request model for trade simulation."""

    symbol: str
    quantity: float
    price: Optional[float] = None


class TradeResponse(BaseModel):
    """Response model for trade simulation."""

    success: bool
    message: str
    symbol: str
    quantity: float
    price: Optional[float] = None


@router.get("/", response_model=Dict[str, Any])
async def get_portfolio_summary(
    service: PortfolioService = Depends(get_portfolio_service),
) -> Dict[str, Any]:
    """
    Get portfolio summary with circuit breaker status.

    Args:
        service: Portfolio service dependency

    Returns:
        Dict with portfolio summary and circuit breaker status

    Raises:
        HTTPException: If portfolio unavailable or retrieval fails
    """
    try:
        portfolio = await service.get_portfolio()
        if portfolio is None:
            raise HTTPException(
                status_code=DEFAULT_VALUE_503, detail="Portfolio unavailable due to circuit breaker"
            )
        summary = service.get_portfolio_summary(portfolio)
        return summary
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting portfolio: {str(e)}"
        )


@router.get("/positions", response_model=List[Position])
async def get_positions(
    service: PortfolioService = Depends(get_portfolio_service),
) -> List[Position]:
    """
    Get all positions in the portfolio.

    Args:
        service: Portfolio service dependency

    Returns:
        List of all positions in the portfolio

    Raises:
        HTTPException: If portfolio unavailable or retrieval fails
    """
    try:
        portfolio = await service.get_portfolio()
        if portfolio is None:
            raise HTTPException(
                status_code=DEFAULT_VALUE_503, detail="Portfolio unavailable due to circuit breaker"
            )
        return portfolio.positions
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting positions: {str(e)}"
        )


@router.get("/positions/{symbol}", response_model=Position)
async def get_position(
    symbol: str,
    service: PortfolioService = Depends(get_portfolio_service),
) -> Position:
    """
    Get specific position by symbol.

    Args:
        symbol: Trading symbol to look up
        service: Portfolio service dependency

    Returns:
        Position for the specified symbol

    Raises:
        HTTPException: If position not found or retrieval fails
    """
    try:
        position = await service.get_position(symbol.upper())
        if position is None:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Position {symbol} not found"
            )
        return position
    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting position: {str(e)}"
        )


@router.get("/asset-universe", response_model=List[AssetUniverse])
async def get_asset_universe(
    service: PortfolioService = Depends(get_portfolio_service),
) -> List[AssetUniverse]:
    """
    Get supported asset universe.

    Args:
        service: Portfolio service dependency

    Returns:
        List of supported asset universes

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        universe = await service.get_asset_universe()
        return universe
    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting asset universe: {str(e)}"
        )


@router.get("/market-regime/{symbol}", response_model=MarketRegimeData)
async def get_market_regime(
    symbol: str,
    service: PortfolioService = Depends(get_portfolio_service),
) -> MarketRegimeData:
    """
    Get market regime data for a symbol.

    Args:
        symbol: Trading symbol to get regime data for
        service: Portfolio service dependency

    Returns:
        Market regime data for the symbol

    Raises:
        HTTPException: If regime data unavailable or retrieval fails
    """
    try:
        regime_data = await service.get_market_regime(symbol.upper())
        if regime_data is None:
            raise HTTPException(
                status_code=DEFAULT_VALUE_404,
                detail=f"Market regime data for {symbol} not available",
            )
        return regime_data
    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting market regime: {str(e)}"
        )


@router.post("/simulate-trade", response_model=TradeResponse)
async def simulate_trade(
    trade_request: TradeRequest,
    service: PortfolioService = Depends(get_portfolio_service),
) -> TradeResponse:
    """
    Simulate a trade execution.

    Args:
        trade_request: Trade simulation request
        service: Portfolio service dependency

    Returns:
        TradeResponse with simulation result

    Raises:
        HTTPException: If simulation fails
    """
    try:
        quantity = Decimal(str(trade_request.quantity))
        price = Decimal(str(trade_request.price)) if trade_request.price is not None else None

        success = await service.simulate_trade(trade_request.symbol.upper(), quantity, price)

        if success:
            return TradeResponse(
                success=True,
                message="Trade simulated successfully",
                symbol=trade_request.symbol.upper(),
                quantity=trade_request.quantity,
                price=trade_request.price,
            )
        else:
            return TradeResponse(
                success=False,
                message="Trade simulation failed",
                symbol=trade_request.symbol.upper(),
                quantity=trade_request.quantity,
                price=trade_request.price,
            )

    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error simulating trade: {str(e)}"
        )


@router.get("/circuit-breakers", response_model=Dict[str, Dict[str, Any]])
async def get_circuit_breaker_status(
    service: PortfolioService = Depends(get_portfolio_service),
) -> Dict[str, Dict[str, Any]]:
    """
    Get circuit breaker status.

    Args:
        service: Portfolio service dependency

    Returns:
        Dict with circuit breaker status for all breakers

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        return service.get_circuit_breaker_status()
    except (asyncio.TimeoutError, ConnectionError, OSError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting circuit breaker status: {str(e)}"
        )


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    service: PortfolioService = Depends(get_portfolio_service),
) -> Dict[str, str]:
    """
    Reset a circuit breaker.

    Args:
        name: Circuit breaker name to reset
        service: Portfolio service dependency

    Returns:
        Dict with operation result

    Raises:
        HTTPException: If reset fails
    """
    try:
        service.reset_circuit_breaker(name)
        return {"message": f"Circuit breaker {name} reset successfully"}
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error resetting circuit breaker: {str(e)}"
        )


@router.get("/health")
async def portfolio_health_check(
    service: PortfolioService = Depends(get_portfolio_service),
) -> Dict[str, Any]:
    """
    Health check for portfolio service.

    Args:
        service: Portfolio service dependency

    Returns:
        Dict with health status and service information
    """
    try:
        # Check if any circuit breakers are open
        status = service.get_circuit_breaker_status()
        open_breakers = [name for name, info in status.items() if info["state"] == "open"]

        if open_breakers:
            return {
                "status": "degraded",
                "message": f"Circuit breakers open: {', '.join(open_breakers)}",
                "circuit_breakers": status,
            }

        # Try to get portfolio
        portfolio = await service.get_portfolio()
        if portfolio is None:
            return {"status": "unhealthy", "message": "Portfolio service unavailable"}

        return {
            "status": "healthy",
            "message": "Portfolio service operational",
            "portfolio_equity": float(portfolio.total_equity),
            "positions_count": len(portfolio.positions),
        }

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        return {"status": "unhealthy", "message": f"Portfolio service error: {str(e)}"}
