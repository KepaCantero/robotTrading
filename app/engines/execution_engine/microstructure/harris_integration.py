"""
Harris Trading Integration Module

Integrates all 10 Harris "Trading and Exchanges" rules into:
- Backtesting
- Live Trading
- Paper Trading

This module provides a unified interface for microstructure-aware trading.

Rules Implemented:
6.1  Order Book Depth Analysis
6.2  Bid-Ask Bounce Removal
6.3  Timing Cost Monitoring
6.4  Almgren-Chriss Market Impact
6.5  Quote Stuffing Detection
6.6  Limit Order Optimization
6.7  Dark Pool Routing
6.8  Liquidity Validation
6.9  Tick Size Adjustment
6.10 PFOF Evaluation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.centralized_config import get_config
from .almgren_chriss_model import MarketImpactEstimate, get_almgren_chriss_model
from .bid_ask_bounce_removal import get_bid_ask_bounce_remover
from .dark_pool_router import DarkPoolDecision, get_dark_pool_router
from .microstructure_engine import get_market_microstructure_engine
from .order_book_analyzer import OrderBookSnapshot, get_order_book_analyzer
from .tick_size_constraints import get_tick_size_constraints

logger = logging.getLogger(__name__)


@dataclass
class PreTradeCheckResult:
    """Result of pre-trade microstructure checks."""

    can_execute: bool
    confidence: float
    reasons: List[str]

    # Harris rule specific results
    order_book_depth_ok: bool
    liquidity_sufficient: bool
    quote_stuffing_detected: bool
    timing_cost_acceptable: bool
    market_impact_acceptable: bool

    # Execution recommendations
    recommended_venue: str
    recommended_order_type: str
    recommended_limit_price: Optional[Decimal]
    estimated_cost_bps: float

    # Risk factors
    risk_factors: Dict[str, float]


@dataclass
class PostTradeAnalysis:
    """Post-trade execution analysis."""

    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal

    # Cost breakdown
    implementation_shortfall_bps: float
    effective_spread_bps: float
    timing_cost_bps: float
    market_impact_bps: float

    # Quality metrics
    execution_quality_score: float
    price_improvement_bps: float
    vs_nbbo_bps: float

    # Timestamps
    signal_time: Optional[datetime]
    decision_time: Optional[datetime]
    submission_time: datetime
    execution_time: datetime


class HarrisMicrostructureIntegrator:
    """
    Unified Harris microstructure integration for all trading systems.

    Provides pre-trade checks, execution planning, and post-trade analysis
    following all 10 Harris rules.
    """

    def __init__(
        self,
        asset_class: str = "equity",
        enable_all_rules: bool = True,
        min_quality_score: float = 50.0,
    ):
        """
        Initialize Harris integrator.

        Args:
            asset_class: Asset class (equity, etf, forex, crypto, futures)
            enable_all_rules: Enable all 10 Harris rules
            min_quality_score: Minimum market quality score for trading
        """
        self.asset_class = asset_class
        self.enable_all_rules = enable_all_rules

        # Initialize all microstructure components
        self.microstructure_engine = get_market_microstructure_engine(
            asset_class=asset_class,
            default_min_quality_score=min_quality_score,
        )

        self.order_book_analyzer = get_order_book_analyzer()
        self.bounce_remover = get_bid_ask_bounce_remover()
        self.impact_model = get_almgren_chriss_model(asset_class=asset_class)
        self.tick_constraints = get_tick_size_constraints()
        self.dark_router = get_dark_pool_router()

        # Rule 6.5: Quote stuffing detection state
        self._quote_counts: Dict[str, List[datetime]] = {}

        # Rule 6.3: Timing cost tracking
        self._signal_times: Dict[str, datetime] = {}

        logger.info(
            f"HarrisMicrostructureIntegrator initialized for {asset_class} "
            f"(all_rules={enable_all_rules})"
        )

    # ==================== Harris Rule 6.1: Order Book Depth ====================

    def analyze_order_book_depth(
        self,
        order_book: OrderBookSnapshot,
        order_size: Decimal,
        max_participation: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Harris Rule 6.1: Analyze order book depth before execution.

        Shallow book = high market impact.
        """
        analysis = self.order_book_analyzer.analyze_order_book(order_book)

        # Check if order can be executed immediately
        can_execute = analysis.can_execute_immediately

        # Calculate effective spread for this order size
        # Note: analysis.side doesn't exist in BookAnalysisResult
        # We need to pass side separately or determine from context
        effective_spread = self._calculate_effective_spread_for_side(order_book, order_size)

        # Liquidity score
        liquidity_score = analysis.liquidity_score

        # Depth imbalance
        imbalance = analysis.imbalance

        return {
            "spread_bps": analysis.spread_bps,
            "imbalance": imbalance,
            "liquidity_score": liquidity_score,
            "can_execute_immediately": can_execute,
            "effective_spread_bps": effective_spread,
            "depth_ok": liquidity_score >= 50.0,
        }

    def _calculate_effective_spread_for_side(
        self,
        order_book: OrderBookSnapshot,
        order_size: Decimal,
    ) -> float:
        """
        Calculate effective spread estimate for order book.

        Returns average of bid and ask effective spreads as an estimate.
        For accurate side-specific calculation, use the full method with side parameter.
        """
        # Estimate based on spread and order size impact
        if order_book.spread_bps:
            base_spread = float(order_book.spread_bps)
            # Add impact factor for larger orders
            size_factor = min(2.0, float(order_size) / 1000.0)
            return base_spread * (1 + size_factor * 0.5)
        return 5.0  # Default 5 bps if no spread data

    # ==================== Harris Rule 6.2: Bid-Ask Bounce ====================

    def remove_bid_ask_bounce(
        self,
        df: pd.DataFrame,
        bid_col: str = "bid",
        ask_col: str = "ask",
        last_col: str = "close",
    ) -> pd.Series:
        """
        Harris Rule 6.2: Remove bid-ask bounce noise from price data.

        Bid-ask bounce creates artificial volatility.
        """
        return self.bounce_remover.remove_bid_ask_bounce(
            df=df,
            bid_col=bid_col,
            ask_col=ask_col,
            last_col=last_col,
        )

    # ==================== Harris Rule 6.3: Timing Cost ====================

    def record_signal_time(self, order_id: str, signal_time: datetime) -> None:
        """
        Harris Rule 6.3: Record signal time for timing cost calculation.

        Timing cost = opportunity cost of delayed execution.
        """
        self._signal_times[order_id] = signal_time

    def calculate_timing_cost(
        self,
        order_id: str,
        execution_price: Decimal,
        signal_price: Decimal,
        execution_time: datetime,
    ) -> float:
        """
        Harris Rule 6.3: Calculate timing cost.

        Returns timing cost in bps.
        """
        signal_time = self._signal_times.get(order_id)
        if not signal_time:
            return 0.0

        delay_seconds = (execution_time - signal_time).total_seconds()

        # Calculate price slippage due to delay
        price_move_bps = abs(float(execution_price - signal_price)) / float(signal_price) * 10000

        # Warn on significant delays
        if delay_seconds > 300:  # > 5 minutes
            logger.warning(
                f"Harris 6.3: Execution delay {delay_seconds}s for {order_id}, "
                f"timing_cost={price_move_bps:.2f}bps"
            )

        return price_move_bps

    # ==================== Harris Rule 6.4: Almgren-Chriss Impact ====================

    def estimate_market_impact(
        self,
        symbol: str,
        order_size: Decimal,
        adv: Decimal,
        volatility: float,
        price: Decimal,
        execution_time_seconds: int = 3600,
    ) -> MarketImpactEstimate:
        """
        Harris Rule 6.4: Estimate market impact using Almgren-Chriss.

        Permanent impact + Temporary impact.
        """
        return self.impact_model.estimate_impact(
            symbol=symbol,
            order_size=order_size,
            adv=adv,
            volatility=volatility,
            execution_time_seconds=execution_time_seconds,
            price=price,
        )

    # ==================== Harris Rule 6.5: Quote Stuffing ====================

    def detect_quote_stuffing(
        self,
        symbol: str,
        current_time: datetime,
        window_seconds: int = 10,
        threshold_quotes_per_second: float = 100.0,
    ) -> bool:
        """
        Harris Rule 6.5: Detect quote stuffing manipulation.

        >100 quotes/second = potential manipulation.
        """
        if symbol not in self._quote_counts:
            self._quote_counts[symbol] = []

        # Add current quote
        self._quote_counts[symbol].append(current_time)

        # Clean old quotes outside window
        cutoff = current_time - timedelta(seconds=window_seconds)
        self._quote_counts[symbol] = [t for t in self._quote_counts[symbol] if t > cutoff]

        # Calculate rate
        quote_rate = len(self._quote_counts[symbol]) / window_seconds

        if quote_rate > threshold_quotes_per_second:
            logger.warning(
                f"Harris 6.5: Quote stuffing detected for {symbol}: " f"{quote_rate:.0f} quotes/sec"
            )
            return True

        return False

    # ==================== Harris Rule 6.6: Limit Order Optimization ====================

    def calculate_optimal_limit_price(
        self,
        side: str,
        current_bid: Decimal,
        current_ask: Decimal,
        urgency: float = 0.5,  # 0 = patient, 1 = urgent
    ) -> Decimal:
        """
        Harris Rule 6.6: Calculate optimal limit price.

        Balance fill probability vs price improvement.
        """
        spread = current_ask - current_bid

        if side == "BUY":
            # Urgency 0 -> bid (0% of spread paid)
            # Urgency 1 -> ask (100% of spread paid)
            limit_price = current_bid + spread * Decimal(str(urgency))
        else:  # SELL
            # SELL: inverse
            limit_price = current_ask - spread * Decimal(str(urgency))

        # Apply tick size constraints (Rule 6.9)
        return self.tick_constraints.adjust_limit_price(
            side=side,
            reference_price=limit_price,
            current_bid=current_bid,
            current_ask=current_ask,
            aggressiveness=urgency,
        )

    # ==================== Harris Rule 6.7: Dark Pool Routing ====================

    def should_use_dark_pool(
        self,
        order_size: Decimal,
        adv: Decimal,
        order_value_usd: Decimal,
        information_leakage_risk: str = "MEDIUM",
        current_spread_bps: float = 5.0,
    ) -> DarkPoolDecision:
        """
        Harris Rule 6.7: Determine if dark pool should be used.

        Dark pools for large orders (>10% ADV) to hide flow.
        """
        return self.dark_router.should_use_dark_pool(
            order_size=order_size,
            adv=adv,
            order_value_usd=order_value_usd,
            information_leakage_risk=information_leakage_risk,
            current_spread_bps=current_spread_bps,
        )

    # ==================== Harris Rule 6.8: Liquidity Validation ====================

    def validate_liquidity_assumption(
        self,
        order_size: Decimal,
        adv: Decimal,
        max_participation: float = 0.20,
        volatility: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Harris Rule 6.8: Validate liquidity assumption.

        NEVER assume infinite liquidity.
        """
        participation = float(order_size / adv) if adv > 0 else 0

        valid = participation <= max_participation

        warnings = []
        if participation > max_participation:
            warnings.append(
                f"Order too large: {participation:.1%} of ADV " f"(max: {max_participation:.0%})"
            )

        if volatility and volatility > 0.05:  # >5% daily vol
            warnings.append(f"High volatility ({volatility:.1%}) - reduce participation rate")

        return {
            "valid": valid,
            "participation_rate": participation,
            "warnings": warnings,
            "max_safe_size": adv * Decimal(str(max_participation)),
        }

    # ==================== Harris Rule 6.9: Tick Size (integrated above) ====================

    # ==================== Harris Rule 6.10: PFOF Evaluation ====================

    def evaluate_execution_quality(
        self,
        executions: List[Any],
        nbbo_snapshot: Dict[str, Tuple[Decimal, Decimal]],
    ) -> Dict[str, float]:
        """
        Harris Rule 6.10: Evaluate execution quality vs NBBO.

        PFOF brokers may NOT give best price.
        """
        improvements = []

        for exec in executions:
            symbol = exec.symbol
            nbbo = nbbo_snapshot.get(symbol)

            if not nbbo:
                continue

            nbbo_bid, nbbo_ask = nbbo

            if exec.side == "BUY":
                benchmark_price = nbbo_ask
                improvement = float(benchmark_price - exec.price) / float(benchmark_price)
            else:  # SELL
                benchmark_price = nbbo_bid
                improvement = float(exec.price - benchmark_price) / float(benchmark_price)

            improvements.append(improvement)

        if not improvements:
            return {"avg_improvement_bps": 0.0, "pct_improved": 0.0}

        avg_improvement = np.mean(improvements)
        pct_improved = np.mean([1 for i in improvements if i > 0])

        if avg_improvement < 0:
            logger.warning(f"Harris 6.10: Average price worse than NBBO: {avg_improvement:.4%}")

        return {
            "avg_improvement_bps": avg_improvement * 10000,
            "pct_improved": pct_improved,
        }

    # ==================== Unified Pre-Trade Check ====================

    def pre_trade_check(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        order_book: Optional[OrderBookSnapshot] = None,
        price_history: Optional[pd.DataFrame] = None,
        adv: Optional[Decimal] = None,
        urgency: float = 0.5,
        signal_time: Optional[datetime] = None,
    ) -> PreTradeCheckResult:
        """
        Comprehensive pre-trade check using all Harris rules.

        Returns:
            PreTradeCheckResult with execution decision and recommendations
        """
        reasons = []
        can_execute = True
        confidence = 1.0

        # Default values
        if adv is None:
            adv = Decimal("1000000")

        # Rule 6.5: Quote stuffing detection
        quote_stuffing = self.detect_quote_stuffing(
            symbol=symbol,
            current_time=datetime.now(),
        )
        if quote_stuffing:
            can_execute = False
            confidence = 0.0
            reasons.append("Quote stuffing detected - DO NOT TRADE")

        # Rule 6.8: Liquidity validation
        liquidity_validation = self.validate_liquidity_assumption(
            order_size=quantity,
            adv=adv,
        )
        if not liquidity_validation["valid"]:
            can_execute = False
            confidence = 0.0
            reasons.append(
                f"Order exceeds liquidity capacity: {liquidity_validation['participation_rate']:.1%} of ADV"
            )

        # Rule 6.1: Order book depth
        order_book_ok = True
        if order_book:
            depth_analysis = self.analyze_order_book_depth(
                order_book=order_book,
                order_size=quantity,
            )
            order_book_ok = depth_analysis["depth_ok"]
            if not order_book_ok:
                confidence -= 0.2
                reasons.append("Shallow order book - reduced confidence")

        # Rule 6.4: Market impact estimation
        config = get_config()
        # Default volatility from config or use default value
        try:
            volatility = getattr(config.trading, 'max_risk_per_trade', 0.02)
        except AttributeError:
            volatility = 0.02  # Default 2% daily volatility

        if price_history is not None and len(price_history) > 1:
            calculated_vol = price_history["close"].pct_change().std() * np.sqrt(252)
            # Use calculated volatility only if it's a valid number
            import math
            if not pd.isna(calculated_vol) and not math.isnan(calculated_vol) and not math.isinf(calculated_vol):
                volatility = calculated_vol

        impact_estimate = self.estimate_market_impact(
            symbol=symbol,
            order_size=quantity,
            adv=adv,
            volatility=volatility,
            price=current_price,
        )

        market_impact_ok = impact_estimate.total_impact_bps <= Decimal("50")  # 50 bps threshold

        if not market_impact_ok:
            confidence -= 0.2
            reasons.append(f"High market impact: {impact_estimate.total_impact_bps:.1f} bps")

        # Rule 6.7: Dark pool decision
        order_value = quantity * current_price
        dark_decision = self.should_use_dark_pool(
            order_size=quantity,
            adv=adv,
            order_value_usd=order_value,
            current_spread_bps=float(impact_estimate.total_impact_bps),
        )

        # Rule 6.6: Optimal limit price
        if order_book:
            optimal_limit = self.calculate_optimal_limit_price(
                side=side,
                current_bid=order_book.best_bid or current_price,
                current_ask=order_book.best_ask or current_price,
                urgency=urgency,
            )
        else:
            optimal_limit = None

        # Rule 6.3: Record signal time for timing cost calculation
        if signal_time:
            self.record_signal_time(f"{symbol}_{side}_{datetime.now().isoformat()}", signal_time)

        # Overall decision
        confidence = max(0.0, confidence)

        # Risk factors
        risk_factors = {
            "participation_rate": float(quantity / adv),
            "market_impact_bps": float(impact_estimate.total_impact_bps),
            "volatility": volatility,
        }

        # Recommended venue and order type
        if dark_decision.use_dark_pool:
            recommended_venue = "dark_pool"
            recommended_order_type = dark_decision.order_type
        else:
            recommended_venue = "lit_exchange"
            recommended_order_type = "LIMIT" if urgency < 0.7 else "MARKET"

        return PreTradeCheckResult(
            can_execute=can_execute,
            confidence=confidence,
            reasons=reasons,
            order_book_depth_ok=order_book_ok,
            liquidity_sufficient=liquidity_validation["valid"],
            quote_stuffing_detected=quote_stuffing,
            timing_cost_acceptable=True,  # Will be calculated post-trade
            market_impact_acceptable=market_impact_ok,
            recommended_venue=recommended_venue,
            recommended_order_type=recommended_order_type,
            recommended_limit_price=optimal_limit,
            estimated_cost_bps=float(impact_estimate.total_impact_bps),
            risk_factors=risk_factors,
        )

    # ==================== Post-Trade Analysis ====================

    def analyze_execution(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        signal_price: Optional[Decimal],
        signal_time: Optional[datetime],
        submission_time: datetime,
        execution_time: datetime,
        arrival_price: Optional[Decimal] = None,
        decision_price: Optional[Decimal] = None,
        nbbo_at_execution: Optional[Tuple[Decimal, Decimal]] = None,
    ) -> PostTradeAnalysis:
        """
        Post-trade execution analysis using Harris concepts.

        Calculates:
        - Implementation shortfall
        - Effective spread
        - Timing cost
        - Market impact
        - Execution quality score
        """
        # Rule 6.3: Timing cost
        timing_cost_bps = 0.0
        if signal_price and signal_time:
            timing_cost_bps = self.calculate_timing_cost(
                order_id=order_id,
                execution_price=execution_price,
                signal_price=signal_price,
                execution_time=execution_time,
            )

        # Implementation shortfall (Perold - 1988)
        # IS = (Decision Price - Execution Price) / Decision Price
        implementation_shortfall_bps = 0.0
        if decision_price and decision_price > 0:
            shortfall = (float(decision_price) - float(execution_price)) / float(decision_price)
            implementation_shortfall_bps = shortfall * 10000

        # Effective spread
        effective_spread_bps = 0.0
        if nbbo_at_execution:
            bid, ask = nbbo_at_execution
            mid = (float(bid) + float(ask)) / 2
            if side == "BUY":
                effective_spread_bps = (float(execution_price) - mid) / mid * 10000
            else:
                effective_spread_bps = (mid - float(execution_price)) / mid * 10000

        # Market impact (approximation)
        market_impact_bps = 0.0
        if arrival_price:
            impact = (float(execution_price) - float(arrival_price)) / float(arrival_price)
            market_impact_bps = impact * 10000

        # Rule 6.10: Price improvement vs NBBO
        price_improvement_bps = 0.0
        vs_nbbo_bps = 0.0
        if nbbo_at_execution:
            bid, ask = nbbo_at_execution
            if side == "BUY":
                vs_nbbo_bps = (float(ask) - float(execution_price)) / float(ask) * 10000
                price_improvement_bps = max(0, vs_nbbo_bps)
            else:
                vs_nbbo_bps = (float(execution_price) - float(bid)) / float(bid) * 10000
                price_improvement_bps = max(0, vs_nbbo_bps)

        # Execution quality score (0-100)
        # Higher = better execution
        quality_score = 50.0  # Base score
        quality_score -= min(50, abs(implementation_shortfall_bps) / 2)  # Penalize shortfall
        quality_score += min(20, price_improvement_bps / 2)  # Reward improvement
        quality_score -= min(30, timing_cost_bps / 3)  # Penalize timing cost
        quality_score = max(0, min(100, quality_score))

        return PostTradeAnalysis(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
            implementation_shortfall_bps=implementation_shortfall_bps,
            effective_spread_bps=effective_spread_bps,
            timing_cost_bps=timing_cost_bps,
            market_impact_bps=market_impact_bps,
            execution_quality_score=quality_score,
            price_improvement_bps=price_improvement_bps,
            vs_nbbo_bps=vs_nbbo_bps,
            signal_time=signal_time,
            decision_time=signal_time,  # Using signal time as decision time
            submission_time=submission_time,
            execution_time=execution_time,
        )


# Global singleton
_harris_integrator: HarrisMicrostructureIntegrator = None


def get_harris_integrator(
    asset_class: str = "equity",
    enable_all_rules: bool = True,
    min_quality_score: float = 50.0,
) -> HarrisMicrostructureIntegrator:
    """Get or create global HarrisMicrostructureIntegrator instance."""
    global _harris_integrator
    if _harris_integrator is None:
        _harris_integrator = HarrisMicrostructureIntegrator(
            asset_class=asset_class,
            enable_all_rules=enable_all_rules,
            min_quality_score=min_quality_score,
        )

    return _harris_integrator
