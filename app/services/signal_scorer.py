"""
Signal Scorer Service

This module implements the signal scoring service with integration to portfolio service
for position sizing and real-time signal evaluation.
"""

import heapq
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple

from app.models.signal import (
    Signal, SignalType, SignalStrength, SignalSource, 
    MarketData, SignalScorer, SignalPriorityQueue
)
from app.services.portfolio_service import PortfolioService
from app.models.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)


class SignalScorerService:
    """Signal scorer service with portfolio integration."""
    
    def __init__(self, portfolio_service: PortfolioService):
        """Initialize signal scorer service."""
        self.portfolio_service = portfolio_service
        self.scorer = SignalScorer()
        self.priority_queue = SignalPriorityQueue(max_size=1000)
        self.signal_history: List[Signal] = []
        self.max_history_size = 10000
        
        # Signal processing configuration
        self.min_confidence_threshold = 60.0
        self.min_liquidity_threshold = 50.0
        self.max_position_size_percent = 10.0  # Max 10% of portfolio per position
        
        # Performance tracking
        self.signals_processed = 0
        self.signals_executed = 0
        self.total_pnl = Decimal("0")
    
    async def evaluate_signal(
        self, 
        symbol: str, 
        signal_type: SignalType, 
        market_data: MarketData,
        metadata: Dict[str, Any]
    ) -> Optional[Signal]:
        """Evaluate and score a trading signal."""
        try:
            # Calculate confidence score
            confidence = self.scorer.calculate_confidence_score(market_data, metadata)
            
            # Calculate liquidity score
            liquidity_score = self.scorer.calculate_liquidity_score(market_data, metadata)
            
            # Determine signal strength based on confidence
            strength = self._determine_signal_strength(confidence)
            
            # Determine signal source
            source = self._determine_signal_source(metadata)
            
            # Create initial signal
            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                liquidity_score=liquidity_score,
                priority_score=0.0,  # Will be calculated after portfolio integration
                source=source,
                price=market_data.price,
                volume=market_data.volume,
                metadata=metadata
            )
            
            # Calculate priority score with portfolio context
            priority_score = await self._calculate_priority_with_portfolio_context(signal, market_data)
            signal.priority_score = priority_score
            
            # Check if signal meets minimum thresholds
            if not self._meets_minimum_thresholds(signal):
                logger.info(f"Signal for {symbol} does not meet minimum thresholds")
                return None
            
            # Add to priority queue
            self.priority_queue.add_signal(signal)
            
            # Track signal
            self._track_signal(signal)
            self.signals_processed += 1
            
            logger.info(f"Signal evaluated for {symbol}: confidence={confidence:.1f}%, "
                       f"liquidity={liquidity_score:.1f}%, priority={priority_score:.1f}%")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error evaluating signal for {symbol}: {e}")
            return None
    
    async def get_next_actionable_signal(self) -> Optional[Signal]:
        """Get next actionable signal from priority queue."""
        try:
            while True:
                signal = self.priority_queue.get_next_signal()
                if signal is None:
                    return None
                
                # Check if signal is still actionable
                if self._is_signal_still_actionable(signal):
                    return signal
                else:
                    logger.info(f"Signal for {signal.symbol} is no longer actionable")
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting next actionable signal: {e}")
            return None
    
    async def calculate_position_size(self, signal: Signal) -> Decimal:
        """Calculate appropriate position size based on signal and portfolio."""
        try:
            # Get current portfolio
            portfolio = await self.portfolio_service.get_portfolio()
            if portfolio is None:
                return Decimal("0")
            
            # Calculate base position size based on signal confidence and liquidity
            base_size_percent = (signal.confidence + signal.liquidity_score) / 200.0  # 0-1 range
            
            # Apply maximum position size limit
            max_size_percent = Decimal(str(self.max_position_size_percent / 100.0))
            size_percent = min(Decimal(str(base_size_percent)), max_size_percent)
            
            # Calculate position size in dollars
            total_equity = portfolio.total_equity
            position_size = total_equity * size_percent
            
            # Round to reasonable precision
            position_size = position_size.quantize(Decimal("0.01"))
            
            logger.info(f"Calculated position size for {signal.symbol}: ${position_size:,.2f} "
                       f"({size_percent*100:.1f}% of portfolio)")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size for {signal.symbol}: {e}")
            return Decimal("0")
    
    async def execute_signal(self, signal: Signal) -> bool:
        """Execute a trading signal."""
        try:
            # Calculate position size
            position_size = await self.calculate_position_size(signal)
            if position_size <= 0:
                logger.warning(f"Cannot execute signal for {signal.symbol}: invalid position size")
                return False
            
            # Calculate quantity based on position size and price
            quantity = position_size / signal.price
            
            # Execute trade through portfolio service
            success = await self.portfolio_service.simulate_trade(
                signal.symbol, 
                quantity, 
                signal.price
            )
            
            if success:
                self.signals_executed += 1
                logger.info(f"Signal executed for {signal.symbol}: {quantity:.4f} shares at ${signal.price}")
                
                # Track execution
                self._track_execution(signal, quantity, success)
                
                return True
            else:
                logger.warning(f"Failed to execute signal for {signal.symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False
    
    async def get_signal_statistics(self) -> Dict[str, Any]:
        """Get signal processing statistics."""
        try:
            portfolio = await self.portfolio_service.get_portfolio()
            portfolio_pnl = portfolio.total_pnl if portfolio else Decimal("0")
            
            # Calculate success rate
            success_rate = 0.0
            if self.signals_processed > 0:
                success_rate = (self.signals_executed / self.signals_processed) * 100
            
            # Get queue summary
            queue_summary = self.priority_queue.get_queue_summary()
            
            return {
                "signals_processed": self.signals_processed,
                "signals_executed": self.signals_executed,
                "success_rate": success_rate,
                "total_pnl": float(portfolio_pnl),
                "queue_size": self.priority_queue.get_queue_size(),
                "queue_summary": queue_summary,
                "min_confidence_threshold": self.min_confidence_threshold,
                "min_liquidity_threshold": self.min_liquidity_threshold,
                "max_position_size_percent": self.max_position_size_percent
            }
            
        except Exception as e:
            logger.error(f"Error getting signal statistics: {e}")
            return {}
    
    async def get_signals_by_symbol(self, symbol: str) -> List[Signal]:
        """Get all signals for a specific symbol."""
        return self.priority_queue.get_signals_by_symbol(symbol)
    
    async def clear_expired_signals(self, max_age_minutes: int = 60):
        """Clear signals older than specified age."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
            temp_queue = []
            removed_count = 0
            
            # Filter out expired signals
            while self.priority_queue.queue:
                priority, count, signal = self.priority_queue.queue.pop()
                if signal.timestamp > cutoff_time:
                    temp_queue.append((priority, count, signal))
                else:
                    removed_count += 1
            
            # Restore valid signals
            for item in temp_queue:
                heapq.heappush(self.priority_queue.queue, item)
            
            logger.info(f"Cleared {removed_count} expired signals")
            
        except Exception as e:
            logger.error(f"Error clearing expired signals: {e}")
    
    def _determine_signal_strength(self, confidence: float) -> SignalStrength:
        """Determine signal strength based on confidence score."""
        if confidence >= 85:
            return SignalStrength.VERY_STRONG
        elif confidence >= 70:
            return SignalStrength.STRONG
        elif confidence >= 55:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _determine_signal_source(self, metadata: Dict[str, Any]) -> SignalSource:
        """Determine signal source based on metadata."""
        if 'rsi' in metadata or 'ema_trend' in metadata:
            return SignalSource.MOMENTUM
        elif 'volume' in metadata or 'avg_volume' in metadata:
            return SignalSource.VOLUME
        elif 'volatility' in metadata:
            return SignalSource.VOLATILITY
        elif 'macd_signal' in metadata or 'bollinger_position' in metadata:
            return SignalSource.TECHNICAL
        else:
            return SignalSource.LIQUIDITY
    
    async def _calculate_priority_with_portfolio_context(self, signal: Signal, market_data: MarketData) -> float:
        """Calculate priority score with portfolio context."""
        try:
            # Get base priority score
            base_priority = self.scorer.calculate_priority_score(signal, market_data)
            
            # Get portfolio context
            portfolio = await self.portfolio_service.get_portfolio()
            if portfolio is None:
                return base_priority
            
            # Adjust priority based on portfolio context
            portfolio_adjustment = 0.0
            
            # Check if we already have a position in this symbol
            existing_position = await self.portfolio_service.get_position(signal.symbol)
            if existing_position:
                # Reduce priority for symbols we already have positions in
                portfolio_adjustment -= 10.0
                
                # Further reduce if position is already large
                position_percent = (existing_position.market_value / portfolio.total_equity) * 100
                if position_percent > 5.0:  # More than 5% of portfolio
                    portfolio_adjustment -= 15.0
            
            # Increase priority for high-confidence signals on new symbols
            if not existing_position and signal.confidence > 80:
                portfolio_adjustment += 5.0
            
            # Adjust priority based on portfolio diversification
            diversification_score = self._calculate_diversification_score(portfolio, signal.symbol)
            portfolio_adjustment += diversification_score
            
            final_priority = base_priority + portfolio_adjustment
            return min(100.0, max(0.0, final_priority))
            
        except Exception as e:
            logger.error(f"Error calculating priority with portfolio context: {e}")
            # Return a reasonable default priority when portfolio service fails
            return 70.0
    
    def _calculate_diversification_score(self, portfolio: Portfolio, symbol: str) -> float:
        """Calculate diversification score for portfolio optimization."""
        try:
            # Count current positions by asset class
            positions_by_class = {}
            for pos in portfolio.positions:
                if pos.asset_class.value not in positions_by_class:
                    positions_by_class[pos.asset_class.value] = []
                positions_by_class[pos.asset_class.value].append(pos)
            
            # Determine asset class for the symbol (simplified)
            asset_class = "equity" if not symbol.endswith("USDT") else "crypto"
            
            # Calculate diversification score
            if asset_class not in positions_by_class:
                return 10.0  # Encourage diversification
            elif len(positions_by_class[asset_class]) < 3:
                return 5.0   # Moderate encouragement
            else:
                return -5.0  # Discourage over-concentration
                
        except Exception as e:
            logger.error(f"Error calculating diversification score: {e}")
            return 0.0
    
    def _meets_minimum_thresholds(self, signal: Signal) -> bool:
        """Check if signal meets minimum thresholds."""
        return (signal.confidence >= self.min_confidence_threshold and
                signal.liquidity_score >= self.min_liquidity_threshold)
    
    def _is_signal_still_actionable(self, signal: Signal) -> bool:
        """Check if signal is still actionable."""
        # Check age (signals older than 30 minutes are not actionable)
        age_minutes = (datetime.utcnow() - signal.timestamp).total_seconds() / 60
        if age_minutes > 30:
            return False
        
        # Check if still meets thresholds
        return self._meets_minimum_thresholds(signal)
    
    def _track_signal(self, signal: Signal):
        """Track signal in history."""
        self.signal_history.append(signal)
        
        # Maintain history size limit
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
    
    def _track_execution(self, signal: Signal, quantity: Decimal, success: bool):
        """Track signal execution."""
        execution_data = {
            "signal": signal,
            "quantity": quantity,
            "success": success,
            "timestamp": datetime.utcnow()
        }
        
        # This could be extended to store execution history in database
        logger.info(f"Signal execution tracked: {signal.symbol} - Success: {success}")
    
    def update_thresholds(self, confidence_threshold: float, liquidity_threshold: float):
        """Update minimum thresholds."""
        self.min_confidence_threshold = confidence_threshold
        self.min_liquidity_threshold = liquidity_threshold
        logger.info(f"Updated thresholds: confidence={confidence_threshold}%, "
                   f"liquidity={liquidity_threshold}%")
    
    def update_position_size_limit(self, max_percent: float):
        """Update maximum position size limit."""
        self.max_position_size_percent = max_percent
        logger.info(f"Updated max position size: {max_percent}%")
