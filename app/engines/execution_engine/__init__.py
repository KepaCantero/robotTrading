"""
Execution Engine Module

This module provides market microstructure analysis and execution capabilities.
The main implementation is in the microstructure subdirectory.

Components:
- MarketMicrostructureEngine: Main orchestrator for microstructure analysis
- Order book analysis and depth metrics
- Bid-ask bounce detection and removal
- Almgren-Chriss market impact modeling
- Adverse selection detection (VPIN, order flow toxicity)
- Market quality metrics
- Tick size constraints
- Dark pool routing logic

Compliance:
- Larry Harris "Trading and Exchanges" (Rule 6)
- Maureen O'Hara "Market Microstructure Theory" (Rule 7)

Example:
    from app.engines.execution_engine.microstructure import get_market_microstructure_engine

    engine = get_market_microstructure_engine()
    result = engine.analyze_market_microstructure(
        symbol="AAPL",
        order_book=order_book_snapshot,
        trade_data=trades_df,
    )
"""

# Re-export main components from microstructure for convenience
from .microstructure import (
    ExecutionPlan,
    MarketMicrostructureEngine,
    MicrostructureAnalysisResult,
    get_market_microstructure_engine,
)

__all__ = [
    "MarketMicrostructureEngine",
    "MicrostructureAnalysisResult",
    "ExecutionPlan",
    "get_market_microstructure_engine",
]
