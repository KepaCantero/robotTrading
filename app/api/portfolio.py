"""
Portfolio API Endpoints

FastAPI endpoints for portfolio management and monitoring.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.portfolio import AssetUniverse, MarketRegimeData, Position
from app.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Global portfolio service instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get portfolio service instance."""
    global _portfolio_service
    if _portfolio_service is None:
        PaperTradingPortfolioProvider()

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
):
    """Get portfolio summary with circuit breaker status."""
    try:
        portfolio = await service.get_portfolio()
        if portfolio is None:
            raise HTTPException(
                status_code=503, detail="Portfolio unavailable due to circuit breaker"
            )
        summary = service.get_portfolio_summary(portfolio)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting portfolio: {str(e)}")


@router.get("/positions", response_model=List[Position])
async def get_positions(service: PortfolioService = Depends(get_portfolio_service)):
    """Get all positions in the portfolio."""
    try:
        portfolio = await service.get_portfolio()
        if portfolio is None:
            raise HTTPException(
                status_code=503, detail="Portfolio unavailable due to circuit breaker"
            )
        return portfolio.positions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting positions: {str(e)}")


@router.get("/positions/{symbol}", response_model=Position)
async def get_position(symbol: str, service: PortfolioService = Depends(get_portfolio_service)):
    """Get specific position by symbol."""
    try:
        position = await service.get_position(symbol.upper())
        if position is None:
            raise HTTPException(status_code=404, detail=f"Position {symbol} not found")
        return position
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting position: {str(e)}")


@router.get("/asset-universe", response_model=List[AssetUniverse])
async def get_asset_universe(
    service: PortfolioService = Depends(get_portfolio_service),
):
    """Get supported asset universe."""
    try:
        universe = await service.get_asset_universe()
        return universe
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting asset universe: {str(e)}")


@router.get("/market-regime/{symbol}", response_model=MarketRegimeData)
async def get_market_regime(
    symbol: str, service: PortfolioService = Depends(get_portfolio_service)
):
    """Get market regime data for a symbol."""
    try:
        regime_data = await service.get_market_regime(symbol.upper())
        if regime_data is None:
            raise HTTPException(
                status_code=404, detail=f"Market regime data for {symbol} not available"
            )
        return regime_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting market regime: {str(e)}")


@router.post("/simulate-trade", response_model=TradeResponse)
async def simulate_trade(
    trade_request: TradeRequest,
    service: PortfolioService = Depends(get_portfolio_service),
):
    """Simulate a trade execution."""
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating trade: {str(e)}")


@router.get("/circuit-breakers", response_model=Dict[str, Dict[str, Any]])
async def get_circuit_breaker_status(
    service: PortfolioService = Depends(get_portfolio_service),
):
    """Get circuit breaker status."""
    try:
        return service.get_circuit_breaker_status()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting circuit breaker status: {str(e)}"
        )


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str, service: PortfolioService = Depends(get_portfolio_service)
):
    """Reset a circuit breaker."""
    try:
        service.reset_circuit_breaker(name)
        return {"message": f"Circuit breaker {name} reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting circuit breaker: {str(e)}")


@router.get("/health")
async def portfolio_health_check(
    service: PortfolioService = Depends(get_portfolio_service),
):
    """Health check for portfolio service."""
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

    except Exception as e:
        return {"status": "unhealthy", "message": f"Portfolio service error: {str(e)}"}
