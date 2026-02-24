"""
Post-Trade Compliance Checker
==============================

Coordinates all post-trade compliance analysis across multiple services.

Responsibilities:
- Collect post-trade analysis from all available services
- Aggregate execution quality metrics
- Calculate implementation shortfall
- Track SLO compliance

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.compliance.results import PostTradeCheckResult
from app.core.compliance.service_registry import get_service_registry

logger = logging.getLogger(__name__)


# =============================================================================
# POST-TRADE COMPLIANCE CHECKER
# =============================================================================


class PostTradeComplianceChecker:
    """
    Coordinates post-trade compliance analysis from all services.

    This class has a Single Responsibility:
        - Aggregate post-trade analysis from multiple services
        - Provide unified execution quality assessment

    It delegates to:
        - HarrisIntegrator: Execution quality analysis
        - SRE monitors: SLO tracking
        - Cost models: Transaction cost analysis
    """

    def __init__(self) -> None:
        """Initialize the post-trade checker with service registry."""
        self._registry = get_service_registry()
        self._cache: Dict[str, Any] = {}

    # =========================================================================
    # MAIN CHECK METHOD
    # =========================================================================

    def check_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        signal_price: Optional[Decimal] = None,
        signal_time: Optional[datetime] = None,
        submission_time: Optional[datetime] = None,
        execution_time: Optional[datetime] = None,
        nbbo_at_execution: Optional[Tuple[Decimal, Decimal]] = None,
        **kwargs: Any,  # Extension point for additional params
    ) -> PostTradeCheckResult:
        """
        Perform comprehensive post-trade analysis using all available services.

        Args:
            order_id: Unique order identifier
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Executed quantity
            execution_price: Actual execution price
            signal_price: Original signal price
            signal_time: Original signal timestamp
            submission_time: Order submission timestamp
            execution_time: Order execution timestamp
            nbbo_at_execution: NBBO (bid, ask) at execution time
            **kwargs: Additional parameters

        Returns:
            PostTradeCheckResult with aggregated analysis
        """
        result = PostTradeCheckResult(
            passed=True,
            confidence=1.0,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
        )

        # -------------------------------------------------------------------------
        # 1. Harris: Execution Quality Analysis
        # -------------------------------------------------------------------------
        self._analyze_harris_execution(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
            signal_price=signal_price,
            signal_time=signal_time,
            submission_time=submission_time,
            execution_time=execution_time,
            nbbo_at_execution=nbbo_at_execution,
            result=result,
        )

        # -------------------------------------------------------------------------
        # 2. SLO Tracking
        # -------------------------------------------------------------------------
        if submission_time and execution_time:
            latency_ms = (execution_time - submission_time).total_seconds() * 1000
            result.latency_ms = latency_ms

        # -------------------------------------------------------------------------
        # FINAL ASSESSMENT
        # -------------------------------------------------------------------------
        result.passed = result.execution_quality_score >= 50.0

        return result

    # =========================================================================
    # INDIVIDUAL ANALYSIS METHODS
    # =========================================================================

    def _analyze_harris_execution(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        signal_price: Optional[Decimal],
        signal_time: Optional[datetime],
        submission_time: Optional[datetime],
        execution_time: Optional[datetime],
        nbbo_at_execution: Optional[Tuple[Decimal, Decimal]],
        result: PostTradeCheckResult,
    ) -> None:
        """Analyze Harris execution quality."""
        harris = self._registry.get_service("harris_integrator")
        if harris is None:
            logger.warning("Harris integrator not available for post-trade analysis")
            return

        try:
            harris_analysis = harris.analyze_execution(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                execution_price=execution_price,
                signal_price=signal_price,
                signal_time=signal_time,
                submission_time=submission_time,
                execution_time=execution_time,
                nbbo_at_execution=nbbo_at_execution,
            )

            # Copy results
            result.implementation_shortfall_bps = harris_analysis.implementation_shortfall_bps
            result.market_impact_bps = harris_analysis.market_impact_bps
            result.timing_cost_bps = harris_analysis.timing_cost_bps
            result.effective_spread_bps = harris_analysis.effective_spread_bps
            result.execution_quality_score = harris_analysis.execution_quality_score
            result.price_improvement_bps = harris_analysis.price_improvement_bps

        except Exception as e:
            logger.warning("Harris post-trade analysis error:", error=e)

    def track_slo_compliance(
        self,
        order_id: str,
        latency_ms: float,
        fill_rate: float = 100.0,
        error_occurred: bool = False,
    ) -> Dict[str, Any]:
        """
        Track SLO compliance using Google SRE methods.

        Args:
            order_id: Order identifier
            latency_ms: Execution latency in milliseconds
            fill_rate: Fill rate percentage
            error_occurred: Whether an error occurred

        Returns:
            Dict with SLO status
        """
        golden_signals = self._registry.get_service("golden_signals")
        trading_metrics = self._registry.get_service("trading_metrics")

        if golden_signals is None and trading_metrics is None:
            return {"tracked": False, "reason": "SRE services not available"}

        try:
            # Update golden signals
            latency_ok = latency_ms < 100  # 100ms threshold
            fill_ok = fill_rate >= 0.95

            slo_status = "OK" if (latency_ok and fill_ok and not error_occurred) else "VIOLATED"

            if trading_metrics:
                trading_metrics.record_execution_latency(latency_ms)
                trading_metrics.record_fill_rate(fill_rate)

            if golden_signals:
                golden_signals.record_latency(latency_ms)
                if error_occurred:
                    golden_signals.record_error()

            return {
                "tracked": True,
                "slo_status": slo_status,
                "latency_ms": latency_ms,
                "latency_ok": latency_ok,
                "fill_rate": fill_rate,
                "fill_ok": fill_ok,
                "error_occurred": error_occurred,
            }

        except Exception as e:
            logger.warning("SLO tracking error:", error=e)
            return {"tracked": False, "error": str(e)}

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_available_analyses(self) -> List[str]:
        """Get list of available post-trade analyses."""
        analyses = []

        if self._registry.is_available("harris_integrator"):
            analyses.append("harris_execution_quality")

        if self._registry.is_available("golden_signals"):
            analyses.append("sre_golden_signals")

        if self._registry.is_available("trading_metrics"):
            analyses.append("sre_trading_metrics")

        return analyses

    def calculate_implementation_shortfall(
        self,
        signal_price: Decimal,
        execution_price: Decimal,
        side: str,
    ) -> float:
        """
        Calculate implementation shortfall in basis points.

        Args:
            signal_price: Original signal price
            execution_price: Actual execution price
            side: BUY or SELL

        Returns:
            Implementation shortfall in basis points
        """
        if side == "BUY":
            shortfall_bps = float((execution_price - signal_price) / signal_price * 10000)
        else:  # SELL
            shortfall_bps = float((signal_price - execution_price) / signal_price * 10000)

        return shortfall_bps

    def calculate_effective_spread(
        self,
        execution_price: Decimal,
        nbbo: Tuple[Decimal, Decimal],
    ) -> float:
        """
        Calculate effective spread in basis points.

        Args:
            execution_price: Execution price
            nbbo: (bid, ask) tuple

        Returns:
            Effective spread in basis points
        """
        bid, ask = nbbo
        midpoint = (bid + ask) / 2

        if execution_price > midpoint:
            # Bought at ask or higher
            effective_spread_bps = float((execution_price - midpoint) / midpoint * 10000) * 2
        else:
            # Sold at bid or lower
            effective_spread_bps = float((midpoint - execution_price) / midpoint * 10000) * 2

        return effective_spread_bps
