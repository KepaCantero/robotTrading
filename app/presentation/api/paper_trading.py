"""
Paper Trading API Endpoints

This module provides FastAPI endpoints for paper trading management,
portfolio simulation, and trade execution for the algorithmic trading system.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
- API-009: Added audit logging for trade operations
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

from app.domain.models.paper_trading import (
    OrderSide,
    OrderType,
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    PaperTradingConfig,
    PaperTradingSession,
    TradeStatus,
)
from app.infrastructure.brokers.paper import PaperTradingService, get_paper_trading_service

from . import audit_logger, get_correlation_id
from .security import audit_log, rate_limit, require_auth

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from app.domain.models.market_data import Quote

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])
logger = logging.getLogger(__name__)


# Request/Response Models
class CreatePortfolioRequest(BaseModel):
    """Request model for creating a portfolio."""

    name: str = Field(..., description="Portfolio name")
    config_id: UUID | None = Field(None, description="Configuration ID")
    initial_cash: Decimal | None = Field(None, description="Initial cash amount")


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    portfolio_id: UUID = Field(..., description="Portfolio ID")
    name: str = Field(..., description="Session name")
    description: str | None = Field(None, description="Session description")
    config_id: UUID | None = Field(None, description="Configuration ID")


class ExecuteTradeRequest(BaseModel):
    """Request model for executing a trade."""

    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    price: Decimal | None = Field(None, gt=0, description="Order price (for limit orders)")
    strategy_id: str | None = Field(None, description="Strategy ID")
    signal_id: UUID | None = Field(None, description="Signal ID")


class UpdateMarketPricesRequest(BaseModel):
    """Request model for updating market prices."""

    quotes: dict[str, Quote] = Field(..., description="Market quotes by symbol")


class PortfolioResponse(BaseModel):
    """Response model for portfolio data."""

    success: bool = Field(True, description="Success status")
    portfolio: PaperPortfolio = Field(..., description="Portfolio data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SessionResponse(BaseModel):
    """Response model for session data."""

    success: bool = Field(True, description="Success status")
    session: PaperTradingSession = Field(..., description="Session data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class TradeResponse(BaseModel):
    """Response model for trade data."""

    success: bool = Field(True, description="Success status")
    trade: PaperTrade = Field(..., description="Trade data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class TradesResponse(BaseModel):
    """Response model for multiple trades."""

    success: bool = Field(True, description="Success status")
    trades: list[PaperTrade] = Field(..., description="List of trades")
    count: int = Field(..., description="Number of trades")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PositionsResponse(BaseModel):
    """Response model for positions."""

    success: bool = Field(True, description="Success status")
    positions: list[PaperPosition] = Field(..., description="List of positions")
    count: int = Field(..., description="Number of positions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class MarketUpdateResponse(BaseModel):
    """Response model for market updates."""

    success: bool = Field(True, description="Success status")
    updated_symbols: list[str] = Field(..., description="Updated symbols")
    count: int = Field(..., description="Number of updated symbols")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Portfolio Management Endpoints
@router.post("/portfolios", response_model=PortfolioResponse)
@rate_limit(max_requests=20, window_seconds=60)
@require_auth()
@audit_log("portfolio_created", log_args=True)
async def create_portfolio(
    request: CreatePortfolioRequest,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> PortfolioResponse:
    """Create a new paper trading portfolio."""
    try:
        portfolio = await service.create_portfolio(
            name=request.name,
            config_id=request.config_id,
            initial_cash=request.initial_cash,
        )
        return PortfolioResponse(portfolio=portfolio)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: UUID,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> PortfolioResponse:
    """Get portfolio by ID."""
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return PortfolioResponse(portfolio=portfolio)


@router.get("/portfolios", response_model=list[PortfolioResponse])
async def list_portfolios(
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> list[PortfolioResponse]:
    """List all portfolios."""
    portfolios = list(service.portfolios.values())
    return [PortfolioResponse(portfolio=p) for p in portfolios]


# Session Management Endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> SessionResponse:
    """Create a new trading session."""
    try:
        session = await service.create_session(
            portfolio_id=request.portfolio_id,
            name=request.name,
            description=request.description,
            config_id=request.config_id,
        )
        return SessionResponse(session=session)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID, service: Annotated[PaperTradingService, Depends(get_paper_trading_service)]
) -> SessionResponse:
    """Get session by ID."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(session=session)


@router.post("/sessions/{session_id}/close", response_model=SessionResponse)
async def close_session(
    session_id: UUID, service: Annotated[PaperTradingService, Depends(get_paper_trading_service)]
) -> SessionResponse:
    """Close a trading session."""
    try:
        session = await service.close_session(session_id)
        return SessionResponse(session=session)
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    portfolio_id: Annotated[UUID | None, Query(None, description="Filter by portfolio ID")],
    is_active: Annotated[bool | None, Query(None, description="Filter by active status")],
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> list[SessionResponse]:
    """List sessions with optional filters."""
    sessions = list(service.sessions.values())

    if portfolio_id:
        sessions = [s for s in sessions if s.portfolio_id == portfolio_id]

    if is_active is not None:
        sessions = [s for s in sessions if s.is_active == is_active]

    return [SessionResponse(session=s) for s in sessions]


# Trade Execution Endpoints
@router.post("/portfolios/{portfolio_id}/trades", response_model=TradeResponse)
@rate_limit(max_requests=100, window_seconds=60)
@require_auth(roles=["admin", "trader"])
@audit_log("trade_executed", log_args=True, sensitive_params=["api_key"])
async def execute_trade(
    portfolio_id: UUID,
    request: ExecuteTradeRequest,
    session_id: Annotated[UUID | None, Query(None, description="Session ID")],
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
    http_request: Request = None,
) -> TradeResponse:
    """Execute a paper trade."""
    correlation_id = get_correlation_id()
    logger.info(
        "Executing paper trade",
        extra={
            "correlation_id": correlation_id,
            "portfolio_id": str(portfolio_id),
            "symbol": request.symbol,
            "side": request.side.value,
            "order_type": request.order_type.value,
            "quantity": float(request.quantity),
        },
    )
    try:
        trade = await asyncio.wait_for(
            service.execute_trade(
                portfolio_id=portfolio_id,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                session_id=session_id,
                strategy_id=request.strategy_id,
                signal_id=request.signal_id,
            ),
            timeout=15.0,  # API-010: Add timeout configuration
        )

        audit_logger.log_action(
            action="trade_executed",
            method="POST",
            path="/portfolios/{portfolio_id}/trades",
            details={
                "portfolio_id": str(portfolio_id),
                "symbol": request.symbol,
                "side": request.side.value,
                "quantity": float(request.quantity),
                "trade_id": str(trade.id) if trade else None,
            },
        )

        return TradeResponse(trade=trade)
    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout executing trade",
            extra={
                "correlation_id": correlation_id,
                "portfolio_id": str(portfolio_id),
                "symbol": request.symbol,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method="POST",
            path="/portfolios/{portfolio_id}/trades",
            error_type="TimeoutError",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(status_code=504, detail=f"Trade execution timeout: {e!s}") from e
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(
            "Error executing trade",
            extra={
                "correlation_id": correlation_id,
                "portfolio_id": str(portfolio_id),
                "symbol": request.symbol,
                "error_type": type(e).__name__,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method="POST",
            path="/portfolios/{portfolio_id}/trades",
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/portfolios/{portfolio_id}/trades", response_model=TradesResponse)
async def get_trades(
    portfolio_id: UUID,
    symbol: Annotated[str | None, Query(None, description="Filter by symbol")],
    status: Annotated[TradeStatus | None, Query(None, description="Filter by status")],
    session_id: Annotated[UUID | None, Query(None, description="Filter by session ID")],
    limit: Annotated[int, Query(100, ge=1, le=1000, description="Maximum number of trades")],
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> TradesResponse:
    """Get trades for a portfolio with optional filters."""
    trades = await service.get_trades(
        portfolio_id=portfolio_id, session_id=session_id, symbol=symbol, status=status
    )

    # Apply limit
    trades = trades[:limit]

    return TradesResponse(trades=trades, count=len(trades))


@router.get("/trades/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: UUID, service: Annotated[PaperTradingService, Depends(get_paper_trading_service)]
) -> TradeResponse:
    """Get trade by ID."""
    trade = service.trades.get(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return TradeResponse(trade=trade)


# Position Management Endpoints
@router.get("/portfolios/{portfolio_id}/positions", response_model=PositionsResponse)
async def get_positions(
    portfolio_id: UUID,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> PositionsResponse:
    """Get all positions for a portfolio."""
    positions = await service.get_positions(portfolio_id)
    return PositionsResponse(positions=positions, count=len(positions))


@router.get("/portfolios/{portfolio_id}/positions/{symbol}", response_model=PositionsResponse)
async def get_position(
    portfolio_id: UUID,
    symbol: str,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> PositionsResponse:
    """Get position for a specific symbol."""
    positions = await service.get_positions(portfolio_id)
    symbol_positions = [p for p in positions if p.symbol == symbol]

    return PositionsResponse(positions=symbol_positions, count=len(symbol_positions))


# Market Data Endpoints
@router.post("/market/update", response_model=MarketUpdateResponse)
async def update_market_prices(
    request: UpdateMarketPricesRequest,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> MarketUpdateResponse:
    """Update market prices for all symbols."""
    try:
        await service.update_market_prices(request.quotes)
        updated_symbols = list(request.quotes.keys())
        return MarketUpdateResponse(updated_symbols=updated_symbols, count=len(updated_symbols))
    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Configuration Endpoints
@router.get("/configs", response_model=list[PaperTradingConfig])
async def list_configs(
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> list[PaperTradingConfig]:
    """List all paper trading configurations."""
    return list(service.configs.values())


@router.get("/configs/{config_id}", response_model=PaperTradingConfig)
async def get_config(
    config_id: UUID, service: Annotated[PaperTradingService, Depends(get_paper_trading_service)]
) -> PaperTradingConfig:
    """Get configuration by ID."""
    config = service.configs.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return config


# Statistics Endpoints
@router.get("/portfolios/{portfolio_id}/stats")
async def get_portfolio_stats(
    portfolio_id: UUID,
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
) -> dict[str, Any]:
    """Get portfolio statistics."""
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trades = await service.get_trades(portfolio_id=portfolio_id)
    positions = await service.get_positions(portfolio_id)

    stats = {
        "portfolio": {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "total_equity": float(portfolio.total_equity),
            "cash_balance": float(portfolio.cash_balance),
            "total_pnl": float(portfolio.total_pnl),
            "total_return": float(portfolio.total_return),
            "daily_pnl": float(portfolio.daily_pnl),
            "daily_return": float(portfolio.daily_return),
        },
        "trades": {
            "total": len(trades),
            "filled": len([t for t in trades if t.status == TradeStatus.FILLED]),
            "pending": len([t for t in trades if t.status == TradeStatus.PENDING]),
            "rejected": len([t for t in trades if t.status == TradeStatus.REJECTED]),
        },
        "positions": {
            "total": len(positions),
            "long": len([p for p in positions if p.quantity > 0]),
            "short": len([p for p in positions if p.quantity < 0]),
        },
        "timestamp": datetime.utcnow(),
    }

    return stats


# Health Check Endpoint
@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for paper trading service."""
    return {
        "status": "healthy",
        "service": "paper-trading",
        "timestamp": datetime.utcnow().isoformat(),
    }
