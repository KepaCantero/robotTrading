"""
Market Microstructure Analysis Module

This module implements advanced market microstructure analysis following:
- Larry Harris "Trading and Exchanges" (Rule 6)
- Maureen O'Hara "Market Microstructure Theory" (Rule 7)

Components:
- Order book depth analysis
- Bid-ask bounce removal
- Almgren-Chriss market impact model
- Adverse selection detection (VPIN, order flow toxicity)
- Market quality metrics
- Tick size constraints
- Dark pool logic
"""

from .adverse_selection_detector import (
    AdverseSelectionDetector,
    AdverseSelectionResult,
    OrderFlowToxicity,
    OrderToxicityResult,
    VPINCalculator,
    VPINResult,
    get_adverse_selection_detector,
    get_order_flow_toxicity,
    get_vpin_calculator,
)
from .almgren_chriss_model import (
    AlmgrenChrissModel,
    MarketImpactEstimate,
    OptimalExecutionSchedule,
    get_almgren_chriss_model,
)
from .bid_ask_bounce_removal import (
    BidAskBounceRemover,
    BounceAnalysisResult,
    get_bid_ask_bounce_remover,
)
from .dark_pool_router import (
    DarkPoolDecision,
    DarkPoolRouter,
    get_dark_pool_router,
)
from .market_quality_metrics import (
    MarketQualityCalculator,
    MarketQualityMetrics,
    get_market_quality_metrics,
)
from .microstructure_engine import (
    ExecutionPlan,
    MarketMicrostructureEngine,
    MicrostructureAnalysisResult,
    get_market_microstructure_engine,
)
from .order_book_analyzer import (
    BookAnalysisResult,
    OrderBookAnalyzer,
    OrderBookLevel,
    OrderBookSnapshot,
    get_order_book_analyzer,
)
from .tick_size_constraints import (
    TickSizeAnalysis,
    TickSizeConstraints,
    get_tick_size_constraints,
)

__all__ = [
    "OrderBookAnalyzer",
    "OrderBookSnapshot",
    "OrderBookLevel",
    "BookAnalysisResult",
    "get_order_book_analyzer",
    "BidAskBounceRemover",
    "BounceAnalysisResult",
    "get_bid_ask_bounce_remover",
    "AlmgrenChrissModel",
    "MarketImpactEstimate",
    "OptimalExecutionSchedule",
    "get_almgren_chriss_model",
    "AdverseSelectionDetector",
    "VPINCalculator",
    "OrderFlowToxicity",
    "AdverseSelectionResult",
    "VPINResult",
    "OrderToxicityResult",
    "get_adverse_selection_detector",
    "get_vpin_calculator",
    "get_order_flow_toxicity",
    "MarketQualityCalculator",
    "MarketQualityMetrics",
    "get_market_quality_metrics",
    "TickSizeConstraints",
    "TickSizeAnalysis",
    "get_tick_size_constraints",
    "DarkPoolRouter",
    "DarkPoolDecision",
    "get_dark_pool_router",
    "MarketMicrostructureEngine",
    "MicrostructureAnalysisResult",
    "ExecutionPlan",
    "get_market_microstructure_engine",
]
