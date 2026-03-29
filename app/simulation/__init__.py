"""
Simulation Module - Market Microstructure and Exchange Simulation

This module implements Larry Harris's "Trading and Exchanges" market microstructure theories,
including order book simulation, market mechanics, trading costs, and exchange behavior.

Components:
- Order Book Simulation: Limit order book dynamics, price formation, queue simulation
- Market Mechanics: Auction mechanics, continuous trading, opening/closing auctions
- Exchange Simulation: Order matching engine, trade execution
- Trading Costs: Bid-ask spread impact, market impact modeling, timing risk
- Market Microstructure: Order flow analysis, market depth, liquidity provision

Reference:
    Harris, L. (2003). Trading and Exchanges: Market Microstructure for Practitioners.
"""

from .exchange import (
    Exchange,
    ExecutionQuality,
    MarketMakerStrategy,
    OrderMatchingEngine,
    SpreadStrategy,
    TradeExecution,
)
from .market_mechanics import (
    AuctionMechanism,
    AuctionResult,
    AuctionType,
    ContinuousTrading,
    MarketPhase,
    TradingSession,
)
from .microstructure import (
    LiquidityProvider,
    MarketDepthAnalyzer,
    MarketMicrostructureMetrics,
    OrderFlowAnalyzer,
    OrderImbalance,
    PriceImpactFunction,
)
from .order_book import (
    LimitOrderBook,
    Order,
    OrderBookSnapshot,
    OrderSide,
    OrderType,
    PriceLevel,
    Trade,
)
from .trading_costs import (
    BidAskSpreadAnalyzer,
    CostBreakdown,
    ExecutionQualityMetrics,
    MarketImpactModel,
    TimingRiskCalculator,
    TradingCostAnalyzer,
)

__all__ = [
    # Market Mechanics
    "AuctionMechanism",
    "AuctionResult",
    "AuctionType",
    "BidAskSpreadAnalyzer",
    "ContinuousTrading",
    "CostBreakdown",
    # Exchange
    "Exchange",
    "ExecutionQuality",
    "ExecutionQualityMetrics",
    # Order Book
    "LimitOrderBook",
    "LiquidityProvider",
    "MarketDepthAnalyzer",
    "MarketImpactModel",
    "MarketMakerStrategy",
    "MarketMicrostructureMetrics",
    "MarketPhase",
    "Order",
    "OrderBookSnapshot",
    # Microstructure
    "OrderFlowAnalyzer",
    "OrderImbalance",
    "OrderMatchingEngine",
    "OrderSide",
    "OrderType",
    "PriceImpactFunction",
    "PriceLevel",
    "SpreadStrategy",
    "TimingRiskCalculator",
    "Trade",
    "TradeExecution",
    # Trading Costs
    "TradingCostAnalyzer",
    "TradingSession",
]
