"""
Paper Trading Service

Provides paper trading simulation without real money.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

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

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


class PaperTradingService:
    """Service for paper trading simulation."""

    def __init__(self, initial_capital: Decimal | None = None) -> None:
        if initial_capital is None:
            initial_capital = Decimal("100000")
        self._capital = initial_capital
        self._positions: dict[str, PaperPosition] = {}
        self._orders: list[dict[str, object]] = []
        self._pnl = Decimal("0")

        # Storage for API-facing domain objects
        self.portfolios: dict[UUID, PaperPortfolio] = {}
        self.sessions: dict[UUID, PaperTradingSession] = {}
        self.trades: dict[UUID, PaperTrade] = {}
        self.configs: dict[UUID, PaperTradingConfig] = {}

    async def create_portfolio(
        self,
        name: str,
        config_id: UUID | None = None,
        initial_cash: Decimal | None = None,
    ) -> PaperPortfolio:
        """Create a new paper trading portfolio."""
        cash = initial_cash if initial_cash is not None else self._capital
        portfolio = PaperPortfolio(
            id=uuid4(),
            name=name,
            cash_balance=cash,
            initial_cash=cash,
            total_equity=cash,
            config_id=config_id,
        )
        self.portfolios[portfolio.id] = portfolio
        return portfolio

    async def get_portfolio(self, portfolio_id: UUID) -> PaperPortfolio | None:
        """Get portfolio by ID."""
        return self.portfolios.get(portfolio_id)

    async def create_session(
        self,
        portfolio_id: UUID,
        name: str,
        description: str | None = None,
        config_id: UUID | None = None,
    ) -> PaperTradingSession:
        """Create a new trading session."""
        if config_id is None:
            config_id = uuid4()
        session = PaperTradingSession(
            id=uuid4(),
            portfolio_id=portfolio_id,
            config_id=config_id,
            name=name,
            description=description,
        )
        self.sessions[session.id] = session
        return session

    async def get_session(self, session_id: UUID) -> PaperTradingSession | None:
        """Get session by ID."""
        return self.sessions.get(session_id)

    async def close_session(self, session_id: UUID) -> PaperTradingSession:
        """Close a trading session."""
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session.is_active = False
        session.ended_at = datetime.utcnow()
        session.status = "closed"
        return session

    async def execute_trade(
        self,
        portfolio_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal | None = None,
        session_id: UUID | None = None,
        strategy_id: str | None = None,
        signal_id: UUID | None = None,
    ) -> PaperTrade:
        """Execute a paper trade."""
        execution_price = price if price is not None else Decimal("0")
        if execution_price <= 0:
            logger.warning("No valid price provided for %s paper trade; skipping fill", symbol)
            raise ValueError(f"Cannot execute paper trade for {symbol}: no price provided")
        trade = PaperTrade(
            id=uuid4(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=execution_price,
            filled_quantity=quantity,
            filled_price=execution_price,
            status=TradeStatus.FILLED,
            strategy_id=strategy_id,
            signal_id=signal_id,
        )
        self.trades[trade.id] = trade
        return trade

    async def get_trades(
        self,
        portfolio_id: UUID,
        session_id: UUID | None = None,
        symbol: str | None = None,
        status: TradeStatus | None = None,
    ) -> list[PaperTrade]:
        """Get trades for a portfolio with optional filters."""
        result = list(self.trades.values())
        if symbol is not None:
            result = [t for t in result if t.symbol == symbol]
        if status is not None:
            result = [t for t in result if t.status == status]
        return result

    async def get_positions(self, portfolio_id: UUID) -> list[PaperPosition]:
        """Get all positions for a portfolio."""
        return list(self._positions.values())

    async def update_market_prices(self, quotes: dict[str, Quote]) -> None:
        """Update market prices for all symbols."""
        for symbol, quote in quotes.items():
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.current_price = quote.last
                pos.recalculate_metrics()

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal | None = None,
    ) -> dict[str, object]:
        """Place a paper trading order."""
        order: dict[str, object] = {
            "order_id": f"order_{len(self._orders)}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price or Decimal("100.00"),
            "status": "filled",
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._orders.append(order)
        return order

    async def get_position(self, symbol: str) -> PaperPosition | None:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)

    async def simulate_trade(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> bool:
        """Simulate a trade without executing."""
        return True

    async def get_circuit_breaker_status(self) -> dict[str, object]:
        """Get circuit breaker status."""
        return {}

    async def reset_circuit_breaker(self, breaker_name: str) -> None:
        """Reset a circuit breaker."""
        pass


# Singleton instance
_paper_trading_service: PaperTradingService | None = None


def get_paper_trading_service() -> PaperTradingService:
    """Get the singleton PaperTradingService instance."""
    global _paper_trading_service
    if _paper_trading_service is None:
        _paper_trading_service = PaperTradingService()
    return _paper_trading_service
