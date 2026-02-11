"""
Market Microstructure Analysis Engine

Main orchestrator for market microstructure analysis following:
- Larry Harris "Trading and Exchanges" (Rule 6)
- Maureen O'Hara "Market Microstructure Theory" (Rule 7)

This engine integrates all microstructure components:
- Order book analysis
- Bid-ask bounce removal
- Market impact modeling (Almgren-Chriss)
- Adverse selection detection
- Market quality metrics
- Tick size constraints
- Dark pool routing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .adverse_selection_detector import (
    AdverseSelectionResult,
    get_adverse_selection_detector,
    get_order_flow_toxicity,
    get_vpin_calculator,
)
from .almgren_chriss_model import MarketImpactEstimate, get_almgren_chriss_model
from .bid_ask_bounce_removal import BounceAnalysisResult, get_bid_ask_bounce_remover
from .dark_pool_router import DarkPoolDecision, get_dark_pool_router
from .market_quality_metrics import MarketQualityMetrics, get_market_quality_metrics
from .order_book_analyzer import BookAnalysisResult, OrderBookSnapshot, get_order_book_analyzer
from .tick_size_constraints import TickSizeAnalysis, get_tick_size_constraints

logger = logging.getLogger(__name__)


@dataclass
class MicrostructureAnalysisResult:
    """Complete microstructure analysis result."""

    symbol: str
    timestamp: pd.Timestamp

    # Order book analysis
    book_analysis: Optional[BookAnalysisResult]

    # Bid-ask bounce
    bounce_analysis: Optional[BounceAnalysisResult]

    # Market impact
    impact_estimate: Optional[MarketImpactEstimate]

    # Adverse selection
    adverse_selection: Optional[AdverseSelectionResult]
    vpin: Optional[float]
    toxicity: Optional[float]

    # Market quality
    market_quality: Optional[MarketQualityMetrics]

    # Tick constraints
    tick_analysis: Optional[TickSizeAnalysis]

    # Dark pool decision
    dark_pool_decision: Optional[DarkPoolDecision]

    # Overall recommendation
    should_trade: bool
    confidence: float
    execution_strategy: str


@dataclass
class ExecutionPlan:
    """Optimal execution plan based on microstructure analysis."""

    symbol: str
    order_size: Decimal
    order_side: str  # BUY or SELL

    # Venue allocation
    venues: Dict[str, Decimal]  # venue -> size

    # Timing
    execution_schedule: List[Tuple[int, Decimal]]  # (time_seconds, size)

    # Order types
    order_type: str  # MARKET, LIMIT, ICEBERG, VWAP, etc.

    # Price limits
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]

    # Expected costs
    expected_cost_bps: Decimal
    expected_cost_usd: Decimal

    # Risk factors
    risk_factors: Dict[str, float]


class MarketMicrostructureEngine:
    """
    Market Microstructure Analysis Engine.

    Orchestrates all microstructure analysis components to provide
    comprehensive market assessment and execution recommendations.
    """

    def __init__(
        self,
        asset_class: str = "equity",
        default_min_quality_score: float = 50.0,
    ):
        """
        Initialize microstructure engine.

        Args:
            asset_class: Asset class for parameter defaults
            default_min_quality_score: Minimum quality score for trading
        """
        self.asset_class = asset_class

        # Initialize components
        self.order_book_analyzer = get_order_book_analyzer()
        self.bounce_remover = get_bid_ask_bounce_remover()
        self.impact_model = get_almgren_chriss_model(asset_class=asset_class)
        self.adverse_detector = get_adverse_selection_detector()
        self.vpin_calc = get_vpin_calculator()
        self.toxicity_calc = get_order_flow_toxicity()
        self.quality_calc = get_market_quality_metrics(min_quality_score=default_min_quality_score)
        self.tick_constraints = get_tick_size_constraints()
        self.dark_router = get_dark_pool_router()

        logger.info(f"MarketMicrostructureEngine initialized for {asset_class}")

    def analyze_market_microstructure(
        self,
        symbol: str,
        price_history: pd.DataFrame,
        order_book: Optional[OrderBookSnapshot] = None,
        executions: Optional[pd.DataFrame] = None,
        order_size: Optional[Decimal] = None,
        order_side: Optional[str] = None,
    ) -> MicrostructureAnalysisResult:
        """
        Perform comprehensive microstructure analysis.

        Args:
            symbol: Trading symbol
            price_history: Price history DataFrame
            order_book: Optional order book snapshot
            executions: Optional historical executions
            order_size: Optional planned order size
            order_side: Optional order side (BUY/SELL)

        Returns:
            MicrostructureAnalysisResult with all analysis components
        """
        timestamp = pd.Timestamp.now()

        # 1. Order book analysis
        book_analysis = None
        if order_book:
            book_analysis = self.order_book_analyzer.analyze_order_book(order_book)

        # 2. Bid-ask bounce analysis
        bounce_analysis = None
        if "bid" in price_history.columns and "ask" in price_history.columns:
            bounce_analysis = self.bounce_remover.analyze_bounce(
                price_history, bid_col="bid", ask_col="ask", last_col="close"
            )

        # 3. Market impact estimation
        impact_estimate = None
        if order_size and order_side:
            # Estimate ADV from volume
            adv = (
                Decimal(str(price_history["volume"].mean()))
                if "volume" in price_history.columns
                else Decimal("1000000")
            )
            volatility = (
                price_history["close"].pct_change().std() * np.sqrt(252)
                if len(price_history) > 1
                else 0.02
            )

            impact_estimate = self.impact_model.estimate_impact(
                symbol=symbol,
                order_size=order_size,
                adv=adv,
                volatility=volatility,
                price=(
                    Decimal(str(price_history["close"].iloc[-1]))
                    if len(price_history) > 0
                    else None
                ),
            )

        # 4. Adverse selection detection
        adverse_selection = None
        vpin = None
        toxicity = None

        if executions is not None and len(executions) > 10:
            adverse_selection = self.adverse_detector.detect_adverse_selection(
                executions=executions,
                price_history=price_history,
            )
            vpin = adverse_selection.vpin
            toxicity = adverse_selection.toxicity
        else:
            # Calculate VPIN from price history
            try:
                vpin_result = self.vpin_calc.calculate_vpin(
                    price_history,
                    price_col="close",
                    volume_col="volume" if "volume" in price_history.columns else None,
                )
                vpin = vpin_result.vpin
            except Exception as e:
                logger.warning(f"VPIN calculation failed: {e}")

            # Calculate toxicity
            try:
                toxicity_result = self.toxicity_calc.calculate_toxicity(
                    price_history,
                    price_col="close",
                    volume_col="volume" if "volume" in price_history.columns else None,
                )
                toxicity = toxicity_result.toxicity_score
            except Exception as e:
                logger.warning(f"Toxicity calculation failed: {e}")

        # 5. Market quality metrics
        market_quality = self.quality_calc.calculate_market_quality(
            symbol=symbol,
            price_history=price_history,
        )

        # 6. Tick size analysis
        tick_analysis = None
        if order_book and order_book.mid_price:
            tick_analysis = self.tick_constraints.analyze_tick_regime(
                symbol=symbol,
                price=order_book.mid_price,
                bid=order_book.best_bid or Decimal("0"),
                ask=order_book.best_ask or Decimal("0"),
            )

        # 7. Dark pool decision
        dark_pool_decision = None
        if order_size and order_side:
            adv = (
                Decimal(str(price_history["volume"].mean()))
                if "volume" in price_history.columns
                else Decimal("1000000")
            )
            order_value = (
                order_size * Decimal(str(price_history["close"].iloc[-1]))
                if len(price_history) > 0
                else Decimal("0")
            )

            dark_pool_decision = self.dark_router.should_use_dark_pool(
                order_size=order_size,
                adv=adv,
                order_value_usd=order_value,
                information_leakage_risk="MEDIUM",
                current_spread_bps=float(book_analysis.spread_bps) if book_analysis else 5.0,
            )

        # 8. Overall recommendation
        should_trade = market_quality.can_trade if market_quality else True

        confidence = 0.5
        if market_quality:
            confidence = market_quality.quality_score / 100.0

        if adverse_selection and adverse_selection.detected:
            should_trade = False
            confidence = max(0.0, confidence - 0.3)

        if vpin and vpin > 0.5:  # High VPIN
            confidence = max(0.0, confidence - 0.2)

        # Execution strategy
        execution_strategy = self._determine_execution_strategy(
            market_quality,
            adverse_selection,
            dark_pool_decision,
            impact_estimate,
        )

        return MicrostructureAnalysisResult(
            symbol=symbol,
            timestamp=timestamp,
            book_analysis=book_analysis,
            bounce_analysis=bounce_analysis,
            impact_estimate=impact_estimate,
            adverse_selection=adverse_selection,
            vpin=vpin,
            toxicity=toxicity,
            market_quality=market_quality,
            tick_analysis=tick_analysis,
            dark_pool_decision=dark_pool_decision,
            should_trade=should_trade,
            confidence=confidence,
            execution_strategy=execution_strategy,
        )

    def _determine_execution_strategy(
        self,
        market_quality: Optional[MarketQualityMetrics],
        adverse_selection: Optional[AdverseSelectionResult],
        dark_pool_decision: Optional[DarkPoolDecision],
        impact_estimate: Optional[MarketImpactEstimate],
    ) -> str:
        """Determine optimal execution strategy."""
        if adverse_selection and adverse_selection.detected:
            return "REDUCE_FREQUENCY_USE_LIMITS"

        if dark_pool_decision and dark_pool_decision.use_dark_pool:
            return f"DARK_POOL_{dark_pool_decision.order_type}"

        if impact_estimate:
            participation = impact_estimate.participation_rate
            if participation > 0.20:  # Large order
                return "TWAP_OR_VWAP"
            elif participation > 0.10:
                return "SPLIT_ORDER_LIMIT"

        if market_quality and market_quality.liquidity_regime == "POOR":
            return "LIMIT_ORDERS_ONLY"

        return "STANDARD_LIMIT"

    def create_execution_plan(
        self,
        analysis: MicrostructureAnalysisResult,
        order_size: Decimal,
        order_side: str,
        current_price: Decimal,
        urgency: float = 0.5,  # 0 = patient, 1 = urgent
    ) -> ExecutionPlan:
        """
        Create optimal execution plan from microstructure analysis.

        Args:
            analysis: Microstructure analysis result
            order_size: Order quantity
            order_side: Order side (BUY/SELL)
            current_price: Current market price
            urgency: Execution urgency (0-1)

        Returns:
            ExecutionPlan with detailed execution instructions
        """
        # Determine venues
        if analysis.dark_pool_decision:
            venues = analysis.dark_pool_decision.venue_allocation
        else:
            venues = {"lit_exchange": Decimal("1")}

        # Determine schedule based on impact estimate
        if analysis.impact_estimate:
            rec_time = analysis.impact_estimate.recommended_execution_time
            rec_tranche = analysis.impact_estimate.recommended_tranche_size

            n_tranches = max(1, int(float(order_size / rec_tranche)))
            interval = rec_time // n_tranches if n_tranches > 0 else rec_time

            schedule = []
            for i in range(n_tranches):
                time = i * interval
                size = (
                    rec_tranche
                    if i < n_tranches - 1
                    else order_size - rec_tranche * (n_tranches - 1)
                )
                schedule.append((time, size))
        else:
            schedule = [(0, order_size)]

        # Order type
        order_type = analysis.execution_strategy

        # Limit price
        limit_price = None
        if analysis.book_analysis and urgency < 1.0:
            limit_price = self.tick_constraints.adjust_limit_price(
                side=order_side,
                reference_price=current_price,
                current_bid=(
                    analysis.book_analysis.mid_price - analysis.book_analysis.spread / 2
                    if analysis.book_analysis.mid_price
                    else current_price
                ),
                current_ask=(
                    analysis.book_analysis.mid_price + analysis.book_analysis.spread / 2
                    if analysis.book_analysis.mid_price
                    else current_price
                ),
                aggressiveness=urgency,
            )

        # Expected costs
        if analysis.impact_estimate:
            expected_cost_bps = analysis.impact_estimate.total_impact_bps
            expected_cost_usd = analysis.impact_estimate.total_cost_usd
        else:
            expected_cost_bps = Decimal("5")  # Default estimate
            expected_cost_usd = order_size * current_price * expected_cost_bps / Decimal("10000")

        # Risk factors
        risk_factors = {}
        if analysis.vpin:
            risk_factors["informed_trading_risk"] = analysis.vpin
        if analysis.toxicity:
            risk_factors["order_flow_toxicity"] = analysis.toxicity
        if analysis.market_quality:
            risk_factors["liquidity_risk"] = 1.0 - (analysis.market_quality.quality_score / 100.0)

        return ExecutionPlan(
            symbol=analysis.symbol,
            order_size=order_size,
            order_side=order_side,
            venues=venues,
            execution_schedule=schedule,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=None,
            expected_cost_bps=expected_cost_bps,
            expected_cost_usd=expected_cost_usd,
            risk_factors=risk_factors,
        )

    def get_market_microstructure_report(
        self,
        analysis: MicrostructureAnalysisResult,
    ) -> Dict[str, Any]:
        """
        Generate human-readable microstructure report.

        Returns dictionary with formatted analysis results.
        """
        report = {
            "symbol": analysis.symbol,
            "timestamp": analysis.timestamp.isoformat(),
            "summary": {
                "should_trade": analysis.should_trade,
                "confidence": f"{analysis.confidence:.1%}",
                "strategy": analysis.execution_strategy,
            },
        }

        # Market quality
        if analysis.market_quality:
            report["market_quality"] = {
                "score": f"{analysis.market_quality.quality_score:.1f}/100",
                "liquidity_regime": analysis.market_quality.liquidity_regime,
                "volatility_regime": analysis.market_quality.volatility_regime,
                "spread_bps": f"{analysis.market_quality.avg_spread_bps:.2f}",
                "can_trade": analysis.market_quality.can_trade,
            }

        # Order book
        if analysis.book_analysis:
            report["order_book"] = {
                "spread_bps": f"{analysis.book_analysis.spread_bps:.2f}",
                "imbalance": f"{analysis.book_analysis.imbalance:.2f}",
                "liquidity_score": f"{analysis.book_analysis.liquidity_score:.1f}",
                "can_execute_immediately": analysis.book_analysis.can_execute_immediately,
            }

        # Market impact
        if analysis.impact_estimate:
            report["market_impact"] = {
                "total_bps": f"{analysis.impact_estimate.total_impact_bps:.2f}",
                "permanent_bps": f"{analysis.impact_estimate.permanent_impact_bps:.2f}",
                "temporary_bps": f"{analysis.impact_estimate.temporary_impact_bps:.2f}",
                "cost_usd": f"${float(analysis.impact_estimate.total_cost_usd):,.2f}",
            }

        # Adverse selection
        if analysis.adverse_selection:
            report["adverse_selection"] = {
                "detected": analysis.adverse_selection.detected,
                "confidence": f"{analysis.adverse_selection.confidence:.1%}",
                "adverse_move_rate": f"{analysis.adverse_selection.adverse_move_rate:.1%}",
                "action": analysis.adverse_selection.recommended_action,
            }

        # VPIN and toxicity
        if analysis.vpin is not None:
            report["vpin"] = {
                "value": f"{analysis.vpin:.3f}",
                "interpretation": (
                    "HIGH" if analysis.vpin > 0.4 else "NORMAL" if analysis.vpin > 0.2 else "LOW"
                ),
            }

        if analysis.toxicity is not None:
            report["toxicity"] = {
                "value": f"{analysis.toxicity:.4f}",
                "interpretation": "TOXIC" if analysis.toxicity > 0.5 else "NORMAL",
            }

        # Dark pool
        if analysis.dark_pool_decision:
            report["dark_pool"] = {
                "use": analysis.dark_pool_decision.use_dark_pool,
                "confidence": f"{analysis.dark_pool_decision.confidence:.1%}",
                "reason": analysis.dark_pool_decision.reason,
                "venues": analysis.dark_pool_decision.venue_allocation,
            }

        return report


# Global singleton
_microstructure_engine: MarketMicrostructureEngine = None


def get_market_microstructure_engine(
    asset_class: str = "equity",
    default_min_quality_score: float = 50.0,
) -> MarketMicrostructureEngine:
    """Get or create global MarketMicrostructureEngine instance."""
    global _microstructure_engine
    if _microstructure_engine is None:
        _microstructure_engine = MarketMicrostructureEngine(
            asset_class=asset_class,
            default_min_quality_score=default_min_quality_score,
        )

    return _microstructure_engine
