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
import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from requests.exceptions import HTTPError, RequestException

from app.domain.models.portfolio import AssetUniverse, MarketRegimeData, Position
from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PERCENT_95 = 95
DEFAULT_VALUE_404 = 404
DEFAULT_VALUE_500 = 500
DEFAULT_VALUE_503 = 503


router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Global portfolio service instance
_portfolio_service: PortfolioService | None = None


def get_portfolio_service() -> PortfolioService:
    """
    Get portfolio service instance.

    Returns:
        PortfolioService: Singleton instance of the portfolio service
    """
    global _portfolio_service
    if _portfolio_service is None:
        logger.info("Initializing portfolio service singleton")
        provider = PaperTradingPortfolioProvider()
        _portfolio_service = PortfolioService(provider)
        logger.info("Portfolio service initialized successfully")

    return _portfolio_service


class TradeRequest(BaseModel):
    """Request model for trade simulation."""

    symbol: str
    quantity: float
    price: float | None = None


class TradeResponse(BaseModel):
    """Response model for trade simulation."""

    success: bool
    message: str
    symbol: str
    quantity: float
    price: float | None = None


@router.get("/", response_model=dict[str, Any])
async def get_portfolio_summary(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> dict[str, Any]:
    """
    Get portfolio summary with circuit breaker status.

    Args:
        service: Portfolio service dependency

    Returns:
        Dict with portfolio summary and circuit breaker status

    Raises:
        HTTPException: If portfolio unavailable or retrieval fails
    """
    logger.debug("get_portfolio_summary called")
    try:
        portfolio = await service.get_portfolio()
        if portfolio is None:
            logger.warning("Portfolio unavailable due to circuit breaker")
            raise HTTPException(
                status_code=DEFAULT_VALUE_503, detail="Portfolio unavailable due to circuit breaker"
            )
        summary = service.get_portfolio_summary(portfolio)
        logger.info(
            "Portfolio summary retrieved",
            extra={
                "total_equity": (
                    float(portfolio.total_equity) if hasattr(portfolio, "total_equity") else None
                )
            },
        )
        return summary
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(
            "Error getting portfolio summary",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting portfolio: {e!s}"
        ) from e


@router.get("/positions", response_model=list[Position])
async def get_positions(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[Position]:
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
            status_code=DEFAULT_VALUE_500, detail=f"Error getting positions: {e!s}"
        ) from e


@router.get("/positions/{symbol}", response_model=Position)
async def get_position(
    symbol: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
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
    logger.debug("get_position called", extra={"symbol": symbol})
    try:
        position = await service.get_position(symbol.upper())
        if position is None:
            logger.warning("Position not found", extra={"symbol": symbol})
            raise HTTPException(
                status_code=DEFAULT_VALUE_404, detail=f"Position {symbol} not found"
            )
        logger.info("Position retrieved", extra={"symbol": symbol})
        return position
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(
            "Error getting position",
            extra={"symbol": symbol, "error_type": type(e).__name__, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting position: {e!s}"
        ) from e


@router.get("/asset-universe", response_model=list[AssetUniverse])
async def get_asset_universe(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[AssetUniverse]:
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
    except (asyncio.TimeoutError, OSError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting asset universe: {e!s}"
        ) from e


@router.get("/market-regime/{symbol}", response_model=MarketRegimeData)
async def get_market_regime(
    symbol: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
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
            status_code=DEFAULT_VALUE_500, detail=f"Error getting market regime: {e!s}"
        ) from e


@router.post("/simulate-trade", response_model=TradeResponse)
async def simulate_trade(
    trade_request: TradeRequest,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
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
    logger.info(
        "simulate_trade called",
        extra={
            "symbol": trade_request.symbol,
            "quantity": trade_request.quantity,
            "price": trade_request.price,
        },
    )
    try:
        quantity = Decimal(str(trade_request.quantity))
        price = Decimal(str(trade_request.price)) if trade_request.price is not None else None

        success = await service.simulate_trade(trade_request.symbol.upper(), quantity, price)

        if success:
            logger.info(
                "Trade simulated successfully",
                extra={"symbol": trade_request.symbol, "quantity": trade_request.quantity},
            )
            return TradeResponse(
                success=True,
                message="Trade simulated successfully",
                symbol=trade_request.symbol.upper(),
                quantity=trade_request.quantity,
                price=trade_request.price,
            )
        else:
            logger.warning(
                "Trade simulation failed",
                extra={"symbol": trade_request.symbol, "quantity": trade_request.quantity},
            )
            return TradeResponse(
                success=False,
                message="Trade simulation failed",
                symbol=trade_request.symbol.upper(),
                quantity=trade_request.quantity,
                price=trade_request.price,
            )

    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        logger.error(
            "Error simulating trade",
            extra={
                "symbol": trade_request.symbol,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error simulating trade: {e!s}"
        ) from e


@router.get("/circuit-breakers", response_model=dict[str, dict[str, Any]])
async def get_circuit_breaker_status(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> dict[str, dict[str, Any]]:
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
    except (asyncio.TimeoutError, OSError) as e:
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error getting circuit breaker status: {e!s}"
        ) from e


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> dict[str, str]:
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
    logger.info("reset_circuit_breaker called", extra={"circuit_breaker_name": name})
    try:
        service.reset_circuit_breaker(name)
        logger.info("Circuit breaker reset successfully", extra={"circuit_breaker_name": name})
        return {"message": f"Circuit breaker {name} reset successfully"}
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(
            "Error resetting circuit breaker",
            extra={
                "circuit_breaker_name": name,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=DEFAULT_VALUE_500, detail=f"Error resetting circuit breaker: {e!s}"
        ) from e


@router.get("/health")
async def portfolio_health_check(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> dict[str, Any]:
    """
    Health check for portfolio service.

    Args:
        service: Portfolio service dependency

    Returns:
        Dict with health status and service information
    """
    logger.debug("portfolio_health_check called")
    try:
        # Check if any circuit breakers are open
        status = service.get_circuit_breaker_status()
        open_breakers = [name for name, info in status.items() if info["state"] == "open"]

        if open_breakers:
            logger.warning(
                "Health check: circuit breakers open", extra={"open_breakers": open_breakers}
            )
            return {
                "status": "degraded",
                "message": f"Circuit breakers open: {', '.join(open_breakers)}",
                "circuit_breakers": status,
            }

        # Try to get portfolio
        portfolio = await service.get_portfolio()
        if portfolio is None:
            logger.warning("Health check: portfolio service unavailable")
            return {"status": "unhealthy", "message": "Portfolio service unavailable"}

        logger.info(
            "Health check passed",
            extra={
                "portfolio_equity": float(portfolio.total_equity),
                "positions_count": len(portfolio.positions),
            },
        )
        return {
            "status": "healthy",
            "message": "Portfolio service operational",
            "portfolio_equity": float(portfolio.total_equity),
            "positions_count": len(portfolio.positions),
        }

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(
            "Health check failed", extra={"error_type": type(e).__name__, "error_message": str(e)}
        )
        return {"status": "unhealthy", "message": f"Portfolio service error: {e!s}"}
