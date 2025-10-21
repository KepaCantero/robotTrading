"""
Portfolio Service with Circuit Breakers

This module implements the portfolio service with circuit breakers for
operational resilience and risk management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from app.models.portfolio import (
    Portfolio, Position, AssetUniverse, MarketRegimeData,
    CircuitBreaker, CircuitBreakerState, PortfolioProvider
)
from app.providers.paper_trading import PaperTradingPortfolioProvider

logger = logging.getLogger(__name__)


class PortfolioService:
    """Portfolio service with circuit breakers and risk management."""
    
    def __init__(self, provider: PortfolioProvider):
        """Initialize portfolio service with a provider."""
        self.provider = provider
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            "api_errors": CircuitBreaker(
                name="api_errors",
                max_errors=3,
                cooldown_seconds=300
            ),
            "slippage": CircuitBreaker(
                name="slippage",
                max_errors=5,
                cooldown_seconds=600
            ),
            "performance": CircuitBreaker(
                name="performance",
                max_errors=3,
                cooldown_seconds=1800
            )
        }
        self.slippage_history: List[float] = []
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None
    
    async def get_portfolio(self) -> Optional[Portfolio]:
        """Get portfolio with circuit breaker protection."""
        try:
            # Check if API error circuit breaker is open
            if self.circuit_breakers["api_errors"].state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset("api_errors"):
                    self.circuit_breakers["api_errors"].state = CircuitBreakerState.HALF_OPEN
                else:
                    logger.warning("API circuit breaker is OPEN, skipping portfolio request")
                    return None
            
            # Attempt to get portfolio
            portfolio = await self.provider.get_portfolio()
            
            # Reset error count on success
            self.circuit_breakers["api_errors"].error_count = 0
            self.error_count = 0
            
            # Check performance circuit breaker
            await self._check_performance_circuit_breaker(portfolio)
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            await self._handle_error("api_errors")
            return None
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position with circuit breaker protection."""
        try:
            if self.circuit_breakers["api_errors"].state == CircuitBreakerState.OPEN:
                return None
            
            position = await self.provider.get_position(symbol)
            self.circuit_breakers["api_errors"].error_count = 0
            return position
            
        except Exception as e:
            logger.error(f"Error getting position {symbol}: {e}")
            await self._handle_error("api_errors")
            return None
    
    async def add_position(self, position: Position) -> bool:
        """Add a position to the portfolio."""
        try:
            # Get current portfolio
            portfolio = await self.get_portfolio()
            if portfolio is None:
                return False
            
            # Create new portfolio with added position
            new_positions = portfolio.positions.copy()
            new_positions.append(position)
            
            # Create new portfolio instance
            new_portfolio = Portfolio(
                cash=portfolio.cash,
                positions=new_positions,
                timestamp=datetime.utcnow(),
                broker=portfolio.broker,
                currency=portfolio.currency
            )
            
            # Update the provider with new portfolio
            await self.provider.update_portfolio(new_portfolio)
            
            logger.info(f"Added position for {position.symbol}: {position.quantity} shares")
            return True
            
        except Exception as e:
            logger.error(f"Error adding position for {position.symbol}: {e}")
            await self._handle_error("api_errors")
            return False
    
    async def update_position(self, position: Position) -> bool:
        """Update an existing position in the portfolio."""
        try:
            # Get current portfolio
            portfolio = await self.get_portfolio()
            if portfolio is None:
                return False
            
            # Find and update the position
            new_positions = []
            position_updated = False
            
            for pos in portfolio.positions:
                if pos.symbol == position.symbol:
                    new_positions.append(position)
                    position_updated = True
                else:
                    new_positions.append(pos)
            
            # If position wasn't found, add it
            if not position_updated:
                new_positions.append(position)
            
            # Create new portfolio instance
            new_portfolio = Portfolio(
                cash=portfolio.cash,
                positions=new_positions,
                timestamp=datetime.utcnow(),
                broker=portfolio.broker,
                currency=portfolio.currency
            )
            
            # Update the provider with new portfolio
            await self.provider.update_portfolio(new_portfolio)
            
            logger.info(f"Updated position for {position.symbol}: {position.quantity} shares")
            return True
            
        except Exception as e:
            logger.error(f"Error updating position for {position.symbol}: {e}")
            await self._handle_error("api_errors")
            return False
    
    async def get_asset_universe(self) -> List[AssetUniverse]:
        """Get asset universe."""
        try:
            return await self.provider.get_asset_universe()
        except Exception as e:
            logger.error(f"Error getting asset universe: {e}")
            await self._handle_error("api_errors")
            return []
    
    async def get_market_regime(self, symbol: str) -> Optional[MarketRegimeData]:
        """Get market regime data."""
        try:
            return await self.provider.get_market_regime(symbol)
        except Exception as e:
            logger.error(f"Error getting market regime for {symbol}: {e}")
            await self._handle_error("api_errors")
            return None
    
    async def simulate_trade(self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None) -> bool:
        """Simulate trade with slippage monitoring."""
        try:
            # Check slippage circuit breaker
            if self.circuit_breakers["slippage"].state == CircuitBreakerState.OPEN:
                logger.warning("Slippage circuit breaker is OPEN, reducing trade size")
                quantity = quantity * Decimal("0.5")  # Reduce position size
            
            # Execute trade
            success = False
            if hasattr(self.provider, 'simulate_trade'):
                success = await self.provider.simulate_trade(symbol, quantity, price)
            
            # Monitor slippage if we have price data
            if success and price is not None:
                await self._monitor_slippage(symbol, price)
            
            return success
            
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            await self._handle_error("api_errors")
            return False
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with circuit breaker status."""
        portfolio = await self.get_portfolio()
        if portfolio is None:
            return {
                "error": "Portfolio unavailable due to circuit breaker",
                "circuit_breakers": {
                    name: cb.state.value for name, cb in self.circuit_breakers.items()
                }
            }
        
        summary = {
            "broker": portfolio.broker,
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
            "circuit_breakers": {
                name: {
                    "state": cb.state.value,
                    "error_count": cb.error_count,
                    "last_error_time": cb.last_error_time.isoformat() if cb.last_error_time else None
                }
                for name, cb in self.circuit_breakers.items()
            }
        }
        
        return summary
    
    async def _handle_error(self, circuit_breaker_name: str):
        """Handle error and update circuit breaker."""
        cb = self.circuit_breakers[circuit_breaker_name]
        cb.error_count += 1
        cb.last_error_time = datetime.utcnow()
        
        if cb.should_trigger():
            cb.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {circuit_breaker_name} triggered after {cb.error_count} errors")
    
    def _should_attempt_reset(self, circuit_breaker_name: str) -> bool:
        """Check if circuit breaker should attempt reset."""
        cb = self.circuit_breakers[circuit_breaker_name]
        if cb.last_error_time is None:
            return False  # No error time means we shouldn't attempt reset
        
        time_since_error = datetime.utcnow() - cb.last_error_time
        return time_since_error.total_seconds() >= cb.cooldown_seconds
    
    async def _check_performance_circuit_breaker(self, portfolio: Portfolio):
        """Check performance circuit breaker based on portfolio metrics."""
        try:
            # Check if portfolio has excessive drawdown
            pnl_percentage = float(portfolio.total_pnl_percentage)
            
            # Trigger if drawdown exceeds -10%
            if pnl_percentage < -10.0:
                await self._handle_error("performance")
                logger.warning(f"Performance circuit breaker triggered: {pnl_percentage}% P&L")
            
        except Exception as e:
            logger.error(f"Error checking performance circuit breaker: {e}")
    
    async def _monitor_slippage(self, symbol: str, expected_price: Decimal):
        """Monitor slippage for trades."""
        try:
            # Get current market price
            position = await self.get_position(symbol)
            if position is None:
                return
            
            actual_price = position.market_price
            slippage = abs(float(actual_price - expected_price)) / float(expected_price)
            
            # Add to slippage history
            self.slippage_history.append(slippage)
            
            # Keep only last 10 trades
            if len(self.slippage_history) > 10:
                self.slippage_history = self.slippage_history[-10:]
            
            # Check average slippage
            if len(self.slippage_history) >= 5:
                avg_slippage = sum(self.slippage_history) / len(self.slippage_history)
                
                # Trigger circuit breaker if average slippage > 0.5%
                if avg_slippage > 0.005:
                    await self._handle_error("slippage")
                    logger.warning(f"Slippage circuit breaker triggered: {avg_slippage:.4f} average slippage")
            
        except Exception as e:
            logger.error(f"Error monitoring slippage: {e}")
    
    def reset_circuit_breaker(self, name: str):
        """Manually reset a circuit breaker."""
        if name in self.circuit_breakers:
            self.circuit_breakers[name].reset()
            logger.info(f"Circuit breaker {name} manually reset")
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": cb.state.value,
                "error_count": cb.error_count,
                "max_errors": cb.max_errors,
                "last_error_time": cb.last_error_time.isoformat() if cb.last_error_time else None,
                "cooldown_seconds": cb.cooldown_seconds
            }
            for name, cb in self.circuit_breakers.items()
        }
