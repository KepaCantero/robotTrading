"""
Paper Trading Service for Analytic Mode

This module implements the paper trading service that simulates realistic trading
conditions including fees, slippage, and market impact for the algorithmic trading system.
"""

import asyncio
import logging
import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from app.domain.models.market_data import Quote
from app.domain.models.order import Order
from app.domain.models.paper_trading import (
    OrderSide,
    OrderType,
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    PaperTradingConfig,
    PaperTradingMode,
    PaperTradingSession,
    TradeStatus,
)
from app.domain.models.slippage_analysis import SlippageCalculationParams
from app.services.slippage_analysis_service import DynamicSlippageService
from app.shared.config.centralized_config import get_config


class PaperTradingService:
    """
    Paper trading service for realistic trading simulation.

    Provides comprehensive paper trading functionality including:
    - Realistic trade execution with fees and slippage
    - Portfolio management and P&L tracking
    - Risk management and position sizing
    - Performance metrics calculation
    """

    def __init__(self):
        logger.debug("Initializing PaperTradingService")
        self.portfolios: Dict[UUID, PaperPortfolio] = {}
        self.sessions: Dict[UUID, PaperTradingSession] = {}
        self.configs: Dict[UUID, PaperTradingConfig] = {}
        self.trades: Dict[UUID, PaperTrade] = {}
        # symbol -> portfolio_id -> position
        self.positions: Dict[str, Dict[UUID, PaperPosition]] = {}

        # Servicio de análisis de slippage dinámico
        slippage_params = SlippageCalculationParams()
        self.slippage_service = DynamicSlippageService(slippage_params)

        # Market data cache for realistic pricing
        self.market_data_cache: Dict[str, Quote] = {}

        # Default configuration
        self._create_default_config()
        logger.info("PaperTradingService initialized")

    def _create_default_config(self) -> None:
        """Create default paper trading configuration using centralized config."""
        # Get risk management thresholds from centralized config
        risk_config = get_config().trading

        default_config = PaperTradingConfig(
            name="Default Paper Trading",
            simulation_mode=PaperTradingMode.REALISTIC,
            initial_cash=Decimal("100000"),
            commission_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.0005"),
            market_impact_rate=Decimal("0.0001"),
            max_position_size=Decimal("0.5"),  # 50% max position
            # Use centralized config
            max_daily_loss=Decimal(str(risk_config.daily_loss_limit)),
            # Use centralized config
            max_drawdown=Decimal(str(risk_config.max_drawdown_limit)),
            execution_delay_ms=100,
            partial_fill_probability=Decimal("0.0"),  # No partial fills by default
        )
        self.configs[default_config.id] = default_config

    async def create_portfolio(
        self,
        name: str,
        config_id: Optional[UUID] = None,
        initial_cash: Optional[Decimal] = None,
    ) -> PaperPortfolio:
        """Create a new paper trading portfolio."""
        logger.debug(
            "create_portfolio called",
            extra={"name": name, "config_id": str(config_id), "initial_cash": str(initial_cash)},
        )
        if config_id is None:
            config_id = list(self.configs.keys())[0]  # Use default config

        config = self.configs[config_id]

        portfolio = PaperPortfolio(
            name=name,
            cash_balance=initial_cash or config.initial_cash,
            initial_cash=initial_cash or config.initial_cash,
            total_equity=initial_cash or config.initial_cash,
            simulation_mode=config.simulation_mode,
            config_id=config_id,
            commission_rate=config.commission_rate,
            slippage_rate=config.slippage_rate,
        )

        self.portfolios[portfolio.id] = portfolio
        logger.info(
            "Portfolio created",
            extra={
                "portfolio_id": str(portfolio.id),
                "name": name,
                "initial_cash": str(portfolio.initial_cash),
            },
        )
        return portfolio

    async def create_session(
        self,
        portfolio_id: UUID,
        name: str,
        description: Optional[str] = None,
        config_id: Optional[UUID] = None,
    ) -> PaperTradingSession:
        """Create a new paper trading session."""
        logger.debug(
            "create_session called", extra={"portfolio_id": str(portfolio_id), "name": name}
        )
        if portfolio_id not in self.portfolios:
            logger.error("Portfolio not found", extra={"portfolio_id": str(portfolio_id)})
            raise ValueError(f"Portfolio {portfolio_id} not found")

        if config_id is None:
            config_id = list(self.configs.keys())[0]  # Use default config

        session = PaperTradingSession(
            portfolio_id=portfolio_id,
            config_id=config_id,
            name=name,
            description=description,
        )

        self.sessions[session.id] = session
        logger.info(
            "Session created",
            extra={"session_id": str(session.id), "portfolio_id": str(portfolio_id), "name": name},
        )
        return session

    async def execute_trade(
        self,
        portfolio_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        session_id: Optional[UUID] = None,
        strategy_id: Optional[str] = None,
        signal_id: Optional[UUID] = None,
    ) -> PaperTrade:
        """Execute a paper trade with realistic simulation."""
        logger.debug(
            "execute_trade called",
            extra={
                "portfolio_id": str(portfolio_id),
                "symbol": symbol,
                "side": str(side),
                "quantity": str(quantity),
            },
        )
        if portfolio_id not in self.portfolios:
            logger.error("Portfolio not found for trade", extra={"portfolio_id": str(portfolio_id)})
            raise ValueError(f"Portfolio {portfolio_id} not found")

        portfolio = self.portfolios[portfolio_id]

        # Get configuration - use default config if none specified
        config_id = getattr(portfolio, "config_id", None)
        if config_id is None:
            config_id = list(self.configs.keys())[0]  # Use default config

        config = self.configs[config_id]

        # Get current market price
        current_price = await self._get_current_price(symbol)
        if current_price is None:
            logger.error("No market data available for symbol", extra={"symbol": symbol})
            raise ValueError(f"No market data available for {symbol}")

        # Determine execution price
        execution_price = price if order_type == OrderType.LIMIT else current_price

        # Create trade
        trade = PaperTrade(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=execution_price,
            strategy_id=strategy_id,
            signal_id=signal_id,
        )

        # Simulate execution delay
        if config.execution_delay_ms > 0:
            await asyncio.sleep(config.execution_delay_ms / 1000.0)

        # Check if trade can be executed
        if not await self._can_execute_trade(portfolio, trade, config, current_price):
            logger.warning(
                "Trade rejected due to risk limits",
                extra={
                    "trade_id": str(trade.id),
                    "portfolio_id": str(portfolio_id),
                    "symbol": symbol,
                },
            )
            trade.status = TradeStatus.REJECTED
            self.trades[trade.id] = trade
            return trade

        # Calculate realistic execution costs
        await self._calculate_execution_costs(trade, config, current_price)

        # Execute the trade
        await self._execute_trade(portfolio, trade, config)

        # Update session statistics
        if session_id and session_id in self.sessions:
            await self._update_session_stats(session_id, trade)

        self.trades[trade.id] = trade
        logger.info(
            "Trade executed",
            extra={
                "trade_id": str(trade.id),
                "portfolio_id": str(portfolio_id),
                "symbol": symbol,
                "side": str(side),
                "quantity": str(quantity),
                "status": str(trade.status),
            },
        )
        return trade

    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current market price for symbol."""
        if symbol in self.market_data_cache:
            quote = self.market_data_cache[symbol]
            return quote.last

        # Fallback to mock price generation
        return await self._generate_mock_price(symbol)

    async def _generate_mock_price(self, symbol: str) -> Decimal:
        """Generate mock price for testing."""
        # Simple mock price generation based on symbol
        base_prices = {
            "AAPL": Decimal("150.00"),
            "MSFT": Decimal("300.00"),
            "GOOGL": Decimal("2500.00"),
            "TSLA": Decimal("200.00"),
            "AMZN": Decimal("3000.00"),
            "BTCUSDT": Decimal("50000.00"),
            "ETHUSDT": Decimal("3000.00"),
            "ADAUSDT": Decimal("0.50"),
            "DOTUSDT": Decimal("20.00"),
            "LINKUSDT": Decimal("15.00"),
        }

        base_price = base_prices.get(symbol, Decimal("100.00"))

        # Add some random variation
        variation = Decimal("0.02")  # ±2% variation
        return base_price * (Decimal("1") + variation)

    async def _can_execute_trade(
        self,
        portfolio: PaperPortfolio,
        trade: PaperTrade,
        config: PaperTradingConfig,
        current_price: Decimal,
    ) -> bool:
        """Check if trade can be executed based on risk limits."""
        # Use current price for calculations
        trade_price = trade.price if trade.order_type == OrderType.LIMIT else current_price

        # Check cash availability for buy orders
        if trade.side == OrderSide.BUY:
            required_cash = trade.quantity * trade_price
            if required_cash > portfolio.cash_balance:
                return False

        # Check position size limits
        position_value = trade.quantity * trade_price
        max_position_value = portfolio.total_equity * config.max_position_size

        if position_value > max_position_value:
            return False

        # Check daily loss limits
        if portfolio.daily_pnl < -portfolio.total_equity * config.max_daily_loss:
            return False

        # Check drawdown limits
        if portfolio.max_drawdown > config.max_drawdown:
            return False

        return True

    async def _calculate_execution_costs(
        self, trade: PaperTrade, config: PaperTradingConfig, market_price: Decimal
    ) -> None:
        """Calculate realistic execution costs."""
        if config.simulation_mode == PaperTradingMode.SIMPLE:
            # Simple mode: no costs
            trade.slippage = Decimal("0")
            trade.commission = Decimal("0")
            trade.market_impact = Decimal("0")
        else:
            # Realistic mode: calculate costs

            # Calculate dynamic slippage
            # Create a mock quote for slippage calculation
            quote = Quote(
                symbol=trade.symbol,
                last=market_price,
                bid=market_price * Decimal("0.999"),
                ask=market_price * Decimal("1.001"),
                volume=Decimal("1000000"),
                timestamp=datetime.now(),
            )

            slippage_amount = self._calculate_dynamic_slippage(trade, market_price, quote, config)
            trade.slippage = slippage_amount

            # Calculate commission
            trade.commission = trade.quantity * trade.price * config.commission_rate

            # Calculate market impact
            trade.market_impact = trade.quantity * market_price * config.market_impact_rate

            # Adjust execution price based on slippage
            if trade.order_type == OrderType.LIMIT:
                # For limit orders, use the specified price
                trade.filled_price = trade.price
            elif trade.side == OrderSide.BUY:
                trade.filled_price = trade.price + (slippage_amount / trade.quantity)
            else:
                trade.filled_price = trade.price - (slippage_amount / trade.quantity)

    async def _execute_trade(
        self, portfolio: PaperPortfolio, trade: PaperTrade, config: PaperTradingConfig
    ) -> None:
        """Execute the trade and update portfolio."""
        # Determine if trade should be partially filled
        if config.partial_fill_probability > 0 and random.random() < float(
            config.partial_fill_probability
        ):
            # Partial fill
            fill_ratio = Decimal(str(random.uniform(0.5, 0.9)))
            trade.filled_quantity = trade.quantity * fill_ratio
            trade.status = TradeStatus.PARTIALLY_FILLED
        else:
            # Full fill
            trade.filled_quantity = trade.quantity
            trade.status = TradeStatus.FILLED

        trade.filled_at = datetime.utcnow()

        # Update portfolio cash
        trade_cost = trade.filled_quantity * trade.filled_price + trade.commission
        if trade.side == OrderSide.BUY:
            portfolio.cash_balance -= trade_cost
        else:
            portfolio.cash_balance += trade_cost

        # Update or create position
        await self._update_position(portfolio, trade)

        # Update portfolio metrics
        await self._update_portfolio_metrics(portfolio)

    async def _update_position(self, portfolio: PaperPortfolio, trade: PaperTrade) -> None:
        """Update portfolio position after trade execution."""
        symbol = trade.symbol

        # Initialize positions dict for symbol if needed
        if symbol not in self.positions:
            self.positions[symbol] = {}

        portfolio_id = portfolio.id

        if portfolio_id in self.positions[symbol]:
            # Update existing position
            position = self.positions[symbol][portfolio_id]

            if trade.side == OrderSide.BUY:
                # Add to position
                new_quantity = position.quantity + trade.filled_quantity
                new_cost_basis = (
                    position.quantity * position.avg_price
                    + trade.filled_quantity * trade.filled_price
                )
                position.avg_price = new_cost_basis / new_quantity
                position.quantity = new_quantity
            else:
                # Reduce position
                position.quantity -= trade.filled_quantity

                # Calculate realized P&L
                realized_pnl = trade.filled_quantity * (trade.filled_price - position.avg_price)
                position.realized_pnl += realized_pnl
        else:
            # Create new position
            position = PaperPosition(
                symbol=symbol,
                quantity=(
                    trade.filled_quantity if trade.side == OrderSide.BUY else -trade.filled_quantity
                ),
                avg_price=trade.filled_price,
                current_price=trade.filled_price,
                market_value=trade.filled_quantity * trade.filled_price,
                cost_basis=trade.filled_quantity * trade.filled_price,
            )

            self.positions[symbol][portfolio_id] = position

        # Update position in portfolio
        await self._sync_positions_to_portfolio(portfolio)

    async def _sync_positions_to_portfolio(self, portfolio: PaperPortfolio) -> None:
        """Sync positions from internal storage to portfolio."""
        portfolio_positions = []

        for symbol_positions in self.positions.values():
            if portfolio.id in symbol_positions:
                position = symbol_positions[portfolio.id]
                if position.quantity != 0:  # Only include non-zero positions
                    portfolio_positions.append(position)

        portfolio.positions = portfolio_positions

    async def _update_portfolio_metrics(self, portfolio: PaperPortfolio) -> None:
        """Update portfolio performance metrics."""
        # Calculate total equity
        positions_value = sum(pos.market_value for pos in portfolio.positions)
        portfolio.total_equity = portfolio.cash_balance + positions_value

        # Calculate total P&L
        positions_pnl = sum(pos.total_pnl for pos in portfolio.positions)
        cash_pnl = portfolio.cash_balance - portfolio.initial_cash
        portfolio.total_pnl = positions_pnl + cash_pnl

        # Calculate total return
        if portfolio.initial_cash > 0:
            portfolio.total_return = (portfolio.total_pnl / portfolio.initial_cash) * Decimal("100")

        # Update last updated timestamp
        portfolio.last_updated = datetime.utcnow()

    async def _update_session_stats(self, session_id: UUID, trade: PaperTrade) -> None:
        """Update session statistics."""
        session = self.sessions[session_id]
        session.total_trades += 1

        if trade.status == TradeStatus.FILLED:
            session.successful_trades += 1
        else:
            session.failed_trades += 1

        session.last_activity = datetime.utcnow()

    async def update_market_prices(self, quotes: Dict[str, Quote]) -> None:
        """Update market prices for all symbols."""
        self.market_data_cache.update(quotes)

        # Update all positions with new prices
        for portfolio in self.portfolios.values():
            for position in portfolio.positions:
                if position.symbol in quotes:
                    quote = quotes[position.symbol]
                    position.current_price = quote.last
                    position.last_updated = datetime.utcnow()
                    # Recalculate position metrics
                    position.recalculate_metrics()

            # Recalculate portfolio metrics
            await self._update_portfolio_metrics(portfolio)

    async def get_portfolio(self, portfolio_id: UUID) -> Optional[PaperPortfolio]:
        """Get portfolio by ID."""
        return self.portfolios.get(portfolio_id)

    async def get_session(self, session_id: UUID) -> Optional[PaperTradingSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    async def get_trades(
        self,
        portfolio_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        status: Optional[TradeStatus] = None,
    ) -> List[PaperTrade]:
        """Get trades with optional filters."""
        trades = list(self.trades.values())

        if portfolio_id:
            trades = [t for t in trades if t.id in self.trades]

        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        if status:
            trades = [t for t in trades if t.status == status]

        return sorted(trades, key=lambda t: t.created_at, reverse=True)

    async def get_positions(self, portfolio_id: UUID) -> List[PaperPosition]:
        """Get all positions for a portfolio."""
        positions = []
        for symbol_positions in self.positions.values():
            if portfolio_id in symbol_positions:
                position = symbol_positions[portfolio_id]
                if position.quantity != 0:
                    positions.append(position)

        return positions

    async def close_session(self, session_id: UUID) -> PaperTradingSession:
        """Close a trading session."""
        logger.debug("close_session called", extra={"session_id": str(session_id)})
        if session_id not in self.sessions:
            logger.error("Session not found", extra={"session_id": str(session_id)})
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        session.is_active = False
        session.status = "closed"
        session.ended_at = datetime.utcnow()

        logger.info(
            "Session closed",
            extra={
                "session_id": str(session_id),
                "total_trades": session.total_trades,
                "successful_trades": session.successful_trades,
            },
        )
        return session

    def _calculate_dynamic_slippage(
        self,
        trade: PaperTrade,
        market_price: Decimal,
        quote: Quote,
        config: PaperTradingConfig,
    ) -> Decimal:
        """Calcular slippage dinámico basado en volatilidad y liquidez."""
        logger.debug(
            "Calculating dynamic slippage",
            extra={"symbol": trade.symbol, "quantity": str(trade.quantity)},
        )
        try:
            # Obtener datos necesarios para el análisis
            asset_symbol = trade.symbol
            order_side = (
                trade.order_type.value
                if hasattr(trade.order_type, "value")
                else str(trade.order_type)
            )
            order_size = trade.quantity * market_price

            # Simular datos históricos de precios (en producción vendrían del
            # market data service)
            price_history = self._get_price_history(asset_symbol, days=30)

            # Simular métricas de mercado (en producción vendrían de APIs
            # reales)
            volume_24h = Decimal("1000000")  # Simulado
            order_book_depth = Decimal("500000")  # Simulado
            market_cap = Decimal("10000000000")  # Simulado

            # Calcular slippage dinámico
            slippage_analysis = self.slippage_service.calculate_dynamic_slippage(
                asset_symbol=asset_symbol,
                base_price=market_price,
                order_side=order_side,
                order_size=order_size,
                quote=quote,
                price_history=price_history,
                volume_24h=volume_24h,
                order_book_depth=order_book_depth,
                market_cap=market_cap,
            )

            # Convertir slippage porcentual a cantidad absoluta
            slippage_amount = order_size * slippage_analysis.total_slippage / Decimal("100")

            logger.debug(
                "Dynamic slippage calculated",
                extra={
                    "symbol": trade.symbol,
                    "slippage_amount": str(slippage_amount),
                    "total_slippage_pct": str(slippage_analysis.total_slippage),
                },
            )
            return slippage_amount

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # Fallback al slippage fijo si hay error
            logger.warning(
                "Dynamic slippage calculation failed, using fallback",
                extra={"symbol": trade.symbol, "error": str(e)},
            )
            return trade.quantity * market_price * config.slippage_rate

    def _get_price_history(self, symbol: str, days: int = 30) -> List[Decimal]:
        """Obtener historial de precios para cálculo de volatilidad."""
        # En producción, esto vendría del market data service
        # Por ahora, simulamos datos históricos
        base_price = Decimal("100.0")
        prices = []

        for _i in range(days):
            # Simular variación de precios con tendencia aleatoria
            variation = Decimal(str(random.uniform(-0.05, 0.05)))  # ±5% variación
            price = base_price * (1 + variation)
            prices.append(price)
            base_price = price  # Usar precio anterior como base

        return prices

    async def execute_order(self, order: Order) -> Dict[str, Any]:
        """
        Execute an Order object using the paper trading service.

        Args:
            order: Order object to execute

        Returns:
            Dictionary with execution result
        """
        logger.debug(
            "execute_order called",
            extra={
                "symbol": order.symbol,
                "side": str(order.side),
                "quantity": str(order.quantity),
            },
        )
        try:
            # Create a default portfolio if none exists
            portfolio_id = list(self.portfolios.keys())[0] if self.portfolios else None
            if portfolio_id is None:
                # Create a default portfolio for testing
                # create_portfolio takes name, not portfolio_id/initial_capital/currency
                portfolio = await self.create_portfolio(
                    name="Default Portfolio",
                    initial_cash=Decimal("100000"),
                )
                portfolio_id = portfolio.id
                logger.info(
                    "Created default portfolio for order execution",
                    extra={"portfolio_id": str(portfolio_id)},
                )

            # Execute the trade using the existing execute_trade method
            trade = await self.execute_trade(
                portfolio_id=portfolio_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
            )

            result = {
                "success": trade.status == TradeStatus.FILLED,
                "trade_id": str(trade.id),
                "executed_price": trade.price,
                "executed_quantity": trade.quantity,
                "status": trade.status.value,
            }
            logger.info(
                "Order executed",
                extra={
                    "trade_id": str(trade.id),
                    "symbol": order.symbol,
                    "success": result["success"],
                    "status": result["status"],
                },
            )
            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(
                "Order execution failed",
                extra={"symbol": order.symbol, "error": str(e), "error_type": type(e).__name__},
            )
            return {"success": False, "error": str(e), "status": "failed"}


# Global service instance
_paper_trading_service: Optional[PaperTradingService] = None


def get_paper_trading_service() -> PaperTradingService:
    """Get the global paper trading service instance."""
    global _paper_trading_service
    if _paper_trading_service is None:
        _paper_trading_service = PaperTradingService()

    return _paper_trading_service
