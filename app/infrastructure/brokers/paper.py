"""
Paper Trading Service

Provides paper trading simulation without real money.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PaperTradingService:
    """Service for paper trading simulation."""

    def __init__(self, initial_capital: Optional[Decimal] = None):
        if initial_capital is None:
            initial_capital = Decimal("100000")
        self._capital = initial_capital
        self._positions: dict[str, Any] = {}
        self._orders: list[dict[str, Any]] = []
        self._pnl = Decimal("0")

    async def get_portfolio(self) -> dict[str, Any]:
        """Get current portfolio state."""
        return {
            "capital": self._capital,
            "positions": self._positions,
            "total_pnl": self._pnl,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
    ) -> dict[str, Any]:
        """Place a paper trading order."""
        order = {
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

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get all positions."""
        return list(self._positions.values())

    async def get_position(self, symbol: str) -> Optional[dict[str, Any]]:
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

    async def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return {}

    async def reset_circuit_breaker(self, breaker_name: str) -> None:
        """Reset a circuit breaker."""
        pass


# Singleton instance
_paper_trading_service: Optional[PaperTradingService] = None


def get_paper_trading_service() -> PaperTradingService:
    """Get the singleton PaperTradingService instance."""
    global _paper_trading_service
    if _paper_trading_service is None:
        _paper_trading_service = PaperTradingService()
    return _paper_trading_service
