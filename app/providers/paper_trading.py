"""
Paper Trading Portfolio Provider

This module implements a paper trading portfolio provider for testing
and simulation without real broker connections.
"""

import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.core.config.base import get_config
from app.models.portfolio import (
    AssetClass,
    AssetUniverse,
    MarketRegime,
    MarketRegimeData,
    Portfolio,
    Position,
)


class PaperTradingPortfolioProvider:
    """Paper trading portfolio provider for testing and simulation."""

    def __init__(self, initial_cash: Decimal = Decimal("100000")):
        """Initialize paper trading provider with initial cash."""
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.broker = "paper_trading"

        # Simulated market data
        self.market_prices: Dict[str, Decimal] = {
            "AAPL": Decimal("150.00"),
            "MSFT": Decimal("300.00"),
            "GOOGL": Decimal("2500.00"),
            "TSLA": Decimal("200.00"),
            "AMZN": Decimal("3000.00"),
            "NVDA": Decimal("400.00"),
            "META": Decimal("300.00"),
            "NFLX": Decimal("400.00"),
            "BTCUSDT": Decimal("45000.00"),
            "ETHUSDT": Decimal("3000.00"),
            "BNBUSDT": Decimal("300.00"),
            "ADAUSDT": Decimal("0.50"),
            "SOLUSDT": Decimal("100.00"),
            "DOTUSDT": Decimal("6.00"),
        }

        # Asset universes for different asset classes
        self.asset_universes = [
            AssetUniverse(
                broker=self.broker,
                asset_class=AssetClass.EQUITY,
                symbols=[
                    "AAPL",
                    "MSFT",
                    "GOOGL",
                    "TSLA",
                    "AMZN",
                    "NVDA",
                    "META",
                    "NFLX",
                ],
                min_volume=Decimal("1000000"),
                max_spread=Decimal("0.01"),
            ),
            AssetUniverse(
                broker=self.broker,
                asset_class=AssetClass.CRYPTO,
                symbols=[
                    "BTCUSDT",
                    "ETHUSDT",
                    "BNBUSDT",
                    "ADAUSDT",
                    "SOLUSDT",
                    "DOTUSDT",
                ],
                min_volume=Decimal("10000000"),
                max_spread=Decimal("0.001"),
            ),
        ]

    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio state."""
        # Update market prices with some random movement
        await self._update_market_prices()

        # Update position P&L
        for symbol, position in self.positions.items():
            if symbol in self.market_prices:
                position.market_price = self.market_prices[symbol]
                position.unrealized_pnl = (
                    position.market_price - position.avg_price
                ) * position.quantity

        return Portfolio(
            cash=self.cash,
            positions=list(self.positions.values()),
            timestamp=datetime.utcnow(),
            broker=self.broker,
            currency="USD",
        )

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get specific position by symbol."""
        return self.positions.get(symbol.upper())

    async def get_asset_universe(self) -> List[AssetUniverse]:
        """Get supported asset universe for this provider."""
        return self.asset_universes

    async def get_market_regime(self, symbol: str) -> Optional[MarketRegimeData]:
        """Get market regime data for a symbol."""
        # Simple market regime detection based on price movement
        if symbol not in self.market_prices:
            return None

        # Simulate different market regimes
        regimes = [
            MarketRegime.TRENDING_UP,
            MarketRegime.TRENDING_DOWN,
            MarketRegime.RANGING,
            MarketRegime.VOLATILE,
        ]
        regime = random.choice(regimes)

        # Calculate simple indicators
        self.market_prices[symbol]
        atr_ratio = random.uniform(0.01, 0.05)  # Simulated ATR ratio
        trend_strength = random.uniform(0.3, 0.9)
        volatility_level = random.uniform(0.1, 0.8)

        return MarketRegimeData(
            regime=regime,
            confidence=random.uniform(0.6, 0.95),
            atr_ratio=atr_ratio,
            trend_strength=trend_strength,
            volatility_level=volatility_level,
            timestamp=datetime.utcnow(),
        )

    async def simulate_trade(
        self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None
    ) -> bool:
        """Simulate a trade execution."""
        symbol = symbol.upper()

        if symbol not in self.market_prices:
            return False

        if price is None:
            price = self.market_prices[symbol]

        total_cost = abs(quantity) * price

        # Check if we have enough cash for buy orders
        if quantity > 0 and total_cost > self.cash:
            return False

        # Execute the trade
        if symbol in self.positions:
            # Update existing position
            existing_pos = self.positions[symbol]
            total_quantity = existing_pos.quantity + quantity
            total_cost_basis = (existing_pos.quantity * existing_pos.avg_price) + (quantity * price)

            if total_quantity == 0:
                # Close position
                self.cash += existing_pos.quantity * price
                del self.positions[symbol]
            else:
                # Update position
                unrealized_pnl = total_quantity * (price - (total_cost_basis / total_quantity))
                self.positions[symbol] = Position(
                    symbol=symbol,
                    asset_class=self._get_asset_class(symbol),
                    quantity=total_quantity,
                    avg_price=total_cost_basis / total_quantity,
                    market_price=price,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=existing_pos.realized_pnl,
                    currency="USD",
                    broker=self.broker,
                )
                self.cash -= quantity * price
        else:
            # Create new position
            if quantity > 0:  # Buy
                self.positions[symbol] = Position(
                    symbol=symbol,
                    asset_class=self._get_asset_class(symbol),
                    quantity=quantity,
                    avg_price=price,
                    market_price=price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker=self.broker,
                )
                self.cash -= total_cost
            else:  # Sell (short)
                self.positions[symbol] = Position(
                    symbol=symbol,
                    asset_class=self._get_asset_class(symbol),
                    quantity=quantity,
                    avg_price=price,
                    market_price=price,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker=self.broker,
                )
                self.cash += total_cost

        return True

    async def reset_portfolio(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_cash
        self.positions = {}

    def _get_asset_class(self, symbol: str) -> AssetClass:
        """Determine asset class based on symbol."""
        if symbol.endswith("USDT") or symbol.endswith("BTC") or symbol.endswith("ETH"):
            return AssetClass.CRYPTO
        else:
            return AssetClass.EQUITY

    async def _update_market_prices(self):
        """Update market prices with simulated movement."""
        cfg = get_config()
        for symbol in self.market_prices:
            # Simulate price movement (-2% to +2%)
            current_price = self.market_prices[symbol]
            # Use config value for max risk per trade (2% default)
            change_percent = getattr(cfg.trading, 'max_risk_per_trade', 0.02)
            new_price = current_price * (1 + Decimal(str(change_percent)))
            self.market_prices[symbol] = new_price

    def get_supported_symbols(self) -> List[str]:
        """Get list of all supported symbols."""
        symbols = []
        for universe in self.asset_universes:
            symbols.extend(universe.symbols)
        return symbols

    def is_symbol_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported."""
        return symbol.upper() in self.get_supported_symbols()

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary for API responses."""
        portfolio = await self.get_portfolio()

        return {
            "broker": self.broker,
            "total_equity": float(portfolio.total_equity),
            "cash": float(portfolio.cash),
            "total_pnl": float(portfolio.total_pnl),
            "total_pnl_percentage": float(portfolio.total_pnl_percentage),
            "positions_count": len(portfolio.positions),
            "positions_by_asset_class": {
                asset_class.value: len(positions)
                for asset_class, positions in portfolio.positions_by_asset_class.items()
            },
            "timestamp": portfolio.timestamp.isoformat(),
        }

    async def update_portfolio(self, portfolio: Portfolio) -> bool:
        """Update portfolio state."""
        try:
            # Update cash
            self.cash = portfolio.cash

            # Update positions
            self.positions = {pos.symbol: pos for pos in portfolio.positions}

            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return False
