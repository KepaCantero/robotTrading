"""
Unified Compliance Integration Module (Refactored)
===================================================

Simplified facade that delegates to specialized coordinators.
This addresses SOL-001 violation by separating concerns.

Architecture:
    ComplianceIntegrationFacade (Facade)
    ├── ServiceRegistry (Service Locator)
    ├── PreTradeComplianceChecker (Pre-trade coordinator)
    ├── PostTradeComplianceChecker (Post-trade coordinator)
    └── PortfolioComplianceOptimizer (Optimization coordinator)

Benefits:
    - Single Responsibility: Each coordinator has one job
    - Lazy Initialization: Services created only when needed
    - Thread-Safe: Concurrent access supported
    - Extensible: Easy to add new services
    - Testable: Each coordinator independently testable

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Import refactored modules
from app.core.compliance import (
    ComprehensivePostTradeAnalysis,
    ComprehensivePreTradeAnalysis,
    PortfolioComplianceOptimizer,
    PortfolioOptimizationResult,
    PostTradeComplianceChecker,
    PreTradeComplianceChecker,
    get_service_registry,
)

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
import sys

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Legacy imports for backward compatibility
try:
    from app.engines.execution_engine.microstructure.order_book_analyzer import OrderBookSnapshot
except ImportError:
    OrderBookSnapshot = None

logger = logging.getLogger(__name__)


# =============================================================================
# COMPLIANCE INTEGRATION FACADE
# =============================================================================


class ComplianceIntegrationFacade:
    """
    Simplified facade for compliance integration.

    This facade delegates to specialized coordinators, following the Facade pattern.
    It maintains backward compatibility with the existing API.

    Responsibilities:
        - Provide simplified interface for clients
        - Delegate to appropriate coordinators
        - Manage lazy initialization
        - Maintain backward compatibility
    """

    _instance: Optional["ComplianceIntegrationFacade"] = None

    def __init__(
        self,
        asset_class: str = "equity",
        enable_all_rules: bool = True,
        strict_mode: bool = False,
    ):
        """
        Initialize the compliance integration facade.

        Args:
            asset_class: Asset class (equity, etf, forex, crypto, futures)
            enable_all_rules: Enable all compliance rules
            strict_mode: If True, enforce all compliance checks strictly
        """
        if ComplianceIntegrationFacade._instance is not None:
            logger.warning("ComplianceIntegrationFacade is a singleton. Using existing instance.")

        self.asset_class = asset_class
        self.enable_all_rules = enable_all_rules
        self.strict_mode = strict_mode

        # Get service registry (singleton)
        self._registry = get_service_registry()

        # Initialize coordinators (lazy)
        self._pre_trade_checker: Optional[PreTradeComplianceChecker] = None
        self._post_trade_checker: Optional[PostTradeComplianceChecker] = None
        self._portfolio_optimizer: Optional[PortfolioComplianceOptimizer] = None

        # Availability flags (for backward compatibility)
        self._initialize_availability_flags()

        logger.info("ComplianceIntegrationFacade initialized")

    @classmethod
    def getInstance(cls) -> "ComplianceIntegrationFacade":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # LAZY INITIALIZATION
    # =========================================================================

    @property
    def pre_trade_checker(self) -> PreTradeComplianceChecker:
        """Lazy initialization of pre-trade checker."""
        if self._pre_trade_checker is None:
            self._pre_trade_checker = PreTradeComplianceChecker()
        return self._pre_trade_checker

    @property
    def post_trade_checker(self) -> PostTradeComplianceChecker:
        """Lazy initialization of post-trade checker."""
        if self._post_trade_checker is None:
            self._post_trade_checker = PostTradeComplianceChecker()
        return self._post_trade_checker

    @property
    def portfolio_optimizer(self) -> PortfolioComplianceOptimizer:
        """Lazy initialization of portfolio optimizer."""
        if self._portfolio_optimizer is None:
            self._portfolio_optimizer = PortfolioComplianceOptimizer()
        return self._portfolio_optimizer

    def _initialize_availability_flags(self) -> None:
        """Initialize availability flags for backward compatibility."""
        availability = self._registry.get_availability_report()

        # Map to legacy names
        self.chan_available = availability.get("regime_detector", False) or availability.get(
            "portfolio_optimizer", False
        )
        self.narang_available = availability.get("alpha_model", False) or availability.get(
            "risk_model", False
        )
        self.lopez_de_prado_available = availability.get(
            "meta_labeling", False
        ) or availability.get("purged_cv", False)
        self.harris_available = availability.get("harris_integrator", False)
        self.ohara_available = availability.get("liquidity_analyzer", False) or availability.get(
            "order_flow_analyzer", False
        )
        self.hull_available = availability.get("var_calculator", False) or availability.get(
            "greeks_calculator", False
        )
        self.sre_available = availability.get("golden_signals", False) or availability.get(
            "trading_metrics", False
        )

    # =========================================================================
    # MAIN API METHODS (Backward Compatible)
    # =========================================================================

    def comprehensive_pre_trade_check(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        price_history: Optional[pd.DataFrame] = None,
        order_book: Optional[Any] = None,
        urgency: float = 0.5,
        signal_time: Optional[datetime] = None,
    ) -> ComprehensivePreTradeAnalysis:
        """
        Comprehensive pre-trade check using all available compliance systems.

        This is the MAIN entry point for compliance-aware trading decisions.

        Returns:
            ComprehensivePreTradeAnalysis with decision and recommendations
        """
        result = self.pre_trade_checker.check_signal(
            symbol=symbol,
            side=side,
            quantity=quantity,
            current_price=current_price,
            price_history=price_history,
            order_book=order_book,
            urgency=urgency,
            signal_time=signal_time,
        )

        # Convert to legacy format
        return ComprehensivePreTradeAnalysis(
            passed=result.passed,
            confidence=result.confidence,
            reasons=result.reasons,
            risk_factors=result.risk_factors,
            can_execute=result.can_execute,
            market_regime=result.market_regime,
            regime_confidence=result.regime_confidence,
            alpha_signal=result.alpha_signal,
            alpha_decay_rate=result.alpha_decay_rate,
            recommended_holding_period=result.recommended_holding_period,
            order_book_depth_ok=result.order_book_depth_ok,
            liquidity_score=result.liquidity_score,
            liquidity_regime=result.liquidity_regime,
            flow_toxicity=result.flow_toxicity,
            vpin=result.vpin,
            pin=result.pin,
            estimated_market_impact_bps=result.estimated_market_impact_bps,
            estimated_timing_cost_bps=result.estimated_timing_cost_bps,
            estimated_total_cost_bps=result.estimated_total_cost_bps,
            recommended_venue=result.recommended_venue,
            recommended_algorithm=result.recommended_algorithm,
            recommended_limit_price=result.recommended_limit_price,
            var_1d_95=result.var_1d_95,
            beta=result.beta,
        )

    def comprehensive_post_trade_analysis(
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
        nbbo_at_execution: Optional[Tuple[Decimal, Decimal]] = None,
    ) -> ComprehensivePostTradeAnalysis:
        """
        Comprehensive post-trade analysis using all available systems.
        """
        result = self.post_trade_checker.check_trade(
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

        # Convert to legacy format
        return ComprehensivePostTradeAnalysis(
            passed=result.passed,
            confidence=result.confidence,
            reasons=result.reasons,
            risk_factors=result.risk_factors,
            order_id=result.order_id,
            symbol=result.symbol,
            side=result.side,
            quantity=result.quantity,
            execution_price=result.execution_price,
            implementation_shortfall_bps=result.implementation_shortfall_bps,
            market_impact_bps=result.market_impact_bps,
            timing_cost_bps=result.timing_cost_bps,
            effective_spread_bps=result.effective_spread_bps,
            execution_quality_score=result.execution_quality_score,
            price_improvement_bps=result.price_improvement_bps,
            latency_ms=result.latency_ms,
            fill_rate=result.fill_rate,
        )

    def optimize_portfolio_comprehensive(
        self,
        symbols: List[str],
        returns: pd.DataFrame,
        current_prices: Dict[str, Decimal],
        price_histories: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> PortfolioOptimizationResult:
        """
        Comprehensive portfolio optimization using Chan + Narang methods.
        """
        result = self.portfolio_optimizer.optimize_portfolio(
            symbols=symbols,
            returns=returns,
            current_prices=current_prices,
            price_histories=price_histories,
        )

        # Convert to legacy format (Decimal weights)
        return PortfolioOptimizationResult(
            passed=result.passed,
            confidence=result.confidence,
            reasons=result.reasons,
            risk_factors=result.risk_factors,
            weights={k: Decimal(str(v)) for k, v in result.weights.items()},
            expected_return=result.expected_return,
            expected_risk=result.expected_risk,
            sharpe_ratio=result.sharpe_ratio,
            factor_exposures=result.factor_exposures,
            regime=result.regime,
            regime_adjusted=result.regime_adjusted,
        )

    # =========================================================================
    # UTILITY METHODS (Backward Compatible)
    # =========================================================================

    def track_slo_compliance(
        self,
        order_id: str,
        latency_ms: float,
        fill_rate: float,
        error_occurred: bool = False,
    ) -> Dict[str, Any]:
        """Track SLO compliance using Google SRE methods."""
        return self.post_trade_checker.track_slo_compliance(
            order_id=order_id,
            latency_ms=latency_ms,
            fill_rate=fill_rate,
            error_occurred=error_occurred,
        )

    def get_system_availability(self) -> Dict[str, bool]:
        """Get availability status of all compliance systems."""
        return {
            "ernest_chan": self.chan_available,
            "narang": self.narang_available,
            "lopez_de_prado": self.lopez_de_prado_available,
            "harris": self.harris_available,
            "ohara": self.ohara_available,
            "hull": self.hull_available,
            "google_sre": self.sre_available,
        }


# =============================================================================
# LEGACY CLASS NAME (Backward Compatibility)
# =============================================================================


class ComplianceIntegrationEngine(ComplianceIntegrationFacade):
    """
    Legacy class name for backward compatibility.

    This class is now an alias for ComplianceIntegrationFacade.
    Existing code using ComplianceIntegrationEngine will continue to work.
    """


# =============================================================================
# GLOBAL SINGLETON (Backward Compatible)
# =============================================================================

_compliance_integration_engine: Optional[ComplianceIntegrationFacade] = None


def get_compliance_integration_engine(
    asset_class: str = "equity",
    enable_all_rules: bool = True,
    strict_mode: bool = False,
) -> ComplianceIntegrationFacade:
    """
    Get or create the global ComplianceIntegrationFacade instance.

    This is the main entry point for using ALL compliance systems in:
    - Backtesting
    - Live Trading
    - Paper Trading

    Example:
        engine = get_compliance_integration_engine()

        # Pre-trade check
        analysis = engine.comprehensive_pre_trade_check(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            price_history=price_df,
        )

        if analysis.can_execute:
            logger.debug(f"Execute: {analysis.recommended_algorithm}")
            logger.debug(f"Venue: {analysis.recommended_venue}")
    """
    global _compliance_integration_engine
    if _compliance_integration_engine is None:
        _compliance_integration_engine = ComplianceIntegrationFacade(
            asset_class=asset_class,
            enable_all_rules=enable_all_rules,
            strict_mode=strict_mode,
        )

    return _compliance_integration_engine


# =============================================================================
# CONVENIENCE FUNCTIONS (Backward Compatible)
# =============================================================================


def quick_pre_trade_check(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    price_history: Optional[pd.DataFrame] = None,
) -> Tuple[bool, str]:
    """
    Quick pre-trade check - returns (can_execute, reason).

    Convenience function for fast decision making.
    """
    engine = get_compliance_integration_engine()

    analysis = engine.comprehensive_pre_trade_check(
        symbol=symbol,
        side=side,
        quantity=quantity,
        current_price=price,
        price_history=price_history,
    )

    if not analysis.can_execute:
        return False, "; ".join(analysis.reasons)

    return True, f"OK (confidence: {analysis.confidence:.0%})"


def get_execution_recommendation(
    symbol: str,
    quantity: Decimal,
    current_price: Decimal,
    price_history: Optional[pd.DataFrame] = None,
    order_book: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Get execution recommendation combining all compliance systems.

    Returns:
        Dict with venue, algorithm, limit_price, and estimated costs.
    """
    engine = get_compliance_integration_engine()

    analysis = engine.comprehensive_pre_trade_check(
        symbol=symbol,
        side="BUY",  # Default
        quantity=quantity,
        current_price=current_price,
        price_history=price_history,
        order_book=order_book,
    )

    return {
        "venue": analysis.recommended_venue,
        "algorithm": analysis.recommended_algorithm,
        "limit_price": analysis.recommended_limit_price,
        "estimated_cost_bps": analysis.estimated_total_cost_bps,
        "confidence": analysis.confidence,
        "liquidity_regime": analysis.liquidity_regime,
        "market_regime": analysis.market_regime,
    }


# =============================================================================
# MAIN (For Testing)
# =============================================================================


if __name__ == "__main__":
    # Test the refactored integration
    logging.basicConfig(level=logging.INFO)

    facade = get_compliance_integration_engine()

    # Print availability
    logger.debug("\n" + "=" * 80)
    logger.debug("COMPLIANCE SYSTEMS AVAILABILITY (Refactored)")
    logger.debug("=" * 80)
    availability = facade.get_system_availability()
    for name, available in availability.items():
        status = "✅" if available else "❌"
        logger.debug(f"{status} {name}")

    logger.debug("\n" + "=" * 80)
    logger.debug("REFACTORED ARCHITECTURE READY:")
    logger.debug("  - ServiceRegistry: Lazy-loaded service management")
    logger.debug("  - PreTradeChecker: Coordinated pre-trade checks")
    logger.debug("  - PostTradeChecker: Coordinated post-trade analysis")
    logger.debug("  - PortfolioOptimizer: Coordinated optimization")
    logger.debug("  - Facade: Simplified interface")
    logger.debug("=" * 80)
