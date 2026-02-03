"""
Compliance Check Results Data Classes
======================================

Defines the data structures for compliance check results.
These are shared across all coordinators and services.

Author: Compliance Integration System
Date: 2026-02-03
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


# =============================================================================
# PRE-TRADE RESULTS
# =============================================================================


@dataclass(frozen=True)
class CheckResult:
    """
    Base result for all compliance checks.

    Attributes:
        passed: Whether the check passed
        confidence: Confidence score (0-1)
        reasons: List of reasons for the decision
        risk_factors: Dictionary of risk factors
    """

    passed: bool
    confidence: float
    reasons: List[str] = field(default_factory=list)
    risk_factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "risk_factors": self.risk_factors,
        }


@dataclass(frozen=True)
class PreTradeCheckResult(CheckResult):
    """
    Result from pre-trade compliance check.

    Aggregates results from multiple pre-trade services.
    """

    # Decision
    can_execute: bool = True

    # Ernest Chan - Regime
    market_regime: Optional[str] = None
    regime_confidence: float = 0.0

    # Narang - Alpha
    alpha_signal: Optional[float] = None
    alpha_decay_rate: Optional[float] = None
    recommended_holding_period: Optional[int] = None

    # Harris & O'Hara - Microstructure
    order_book_depth_ok: bool = True
    liquidity_score: float = 0.0
    liquidity_regime: str = "UNKNOWN"
    flow_toxicity: float = 0.0
    vpin: float = 0.0
    pin: float = 0.0

    # Cost estimates
    estimated_market_impact_bps: float = 0.0
    estimated_timing_cost_bps: float = 0.0
    estimated_total_cost_bps: float = 0.0

    # Execution recommendations
    recommended_venue: str = "lit_exchange"
    recommended_algorithm: str = "LIMIT"
    recommended_limit_price: Optional[Decimal] = None

    # Hull - Risk metrics
    var_1d_95: Optional[float] = None
    beta: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "can_execute": self.can_execute,
                "market_regime": self.market_regime,
                "regime_confidence": self.regime_confidence,
                "alpha_signal": self.alpha_signal,
                "alpha_decay_rate": self.alpha_decay_rate,
                "recommended_holding_period": self.recommended_holding_period,
                "order_book_depth_ok": self.order_book_depth_ok,
                "liquidity_score": self.liquidity_score,
                "liquidity_regime": self.liquidity_regime,
                "flow_toxicity": self.flow_toxicity,
                "vpin": self.vpin,
                "pin": self.pin,
                "estimated_market_impact_bps": self.estimated_market_impact_bps,
                "estimated_timing_cost_bps": self.estimated_timing_cost_bps,
                "estimated_total_cost_bps": self.estimated_total_cost_bps,
                "recommended_venue": self.recommended_venue,
                "recommended_algorithm": self.recommended_algorithm,
                "recommended_limit_price": (
                    str(self.recommended_limit_price) if self.recommended_limit_price else None
                ),
                "var_1d_95": self.var_1d_95,
                "beta": self.beta,
            }
        )
        return base_dict


# =============================================================================
# POST-TRADE RESULTS
# =============================================================================


@dataclass(frozen=True)
class PostTradeCheckResult(CheckResult):
    """
    Result from post-trade compliance analysis.

    Aggregates results from multiple post-trade services.
    """

    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: Decimal = Decimal("0")
    execution_price: Decimal = Decimal("0")

    # Cost breakdown
    implementation_shortfall_bps: float = 0.0
    market_impact_bps: float = 0.0
    timing_cost_bps: float = 0.0
    effective_spread_bps: float = 0.0

    # Execution quality
    execution_quality_score: float = 0.0
    price_improvement_bps: float = 0.0

    # SLO tracking
    latency_ms: float = 0.0
    fill_rate: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "order_id": self.order_id,
                "symbol": self.symbol,
                "side": self.side,
                "quantity": str(self.quantity),
                "execution_price": str(self.execution_price),
                "implementation_shortfall_bps": self.implementation_shortfall_bps,
                "market_impact_bps": self.market_impact_bps,
                "timing_cost_bps": self.timing_cost_bps,
                "effective_spread_bps": self.effective_spread_bps,
                "execution_quality_score": self.execution_quality_score,
                "price_improvement_bps": self.price_improvement_bps,
                "latency_ms": self.latency_ms,
                "fill_rate": self.fill_rate,
            }
        )
        return base_dict


# =============================================================================
# OPTIMIZATION RESULTS
# =============================================================================


@dataclass(frozen=True)
class OptimizeResult(CheckResult):
    """
    Result from portfolio optimization.

    Aggregates results from optimization services.
    """

    weights: Dict[str, float] = field(default_factory=dict)
    expected_return: float = 0.0
    expected_risk: float = 0.0
    sharpe_ratio: float = 0.0

    # Factor exposures (Narang)
    factor_exposures: Dict[str, float] = field(default_factory=dict)

    # Regime awareness (Chan)
    regime: str = "UNKNOWN"
    regime_adjusted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "weights": {k: float(v) for k, v in self.weights.items()},
                "expected_return": self.expected_return,
                "expected_risk": self.expected_risk,
                "sharpe_ratio": self.sharpe_ratio,
                "factor_exposures": self.factor_exposures,
                "regime": self.regime,
                "regime_adjusted": self.regime_adjusted,
            }
        )
        return base_dict


# =============================================================================
# LEGACY COMPATIBILITY (Backward Compatibility)
# =============================================================================


@dataclass(frozen=True)
class ComprehensivePreTradeAnalysis(PreTradeCheckResult):
    """
    Legacy compatibility wrapper for existing code.

    Maintains backward compatibility with ComprehensivePreTradeAnalysis.
    """

    pass


@dataclass(frozen=True)
class ComprehensivePostTradeAnalysis(PostTradeCheckResult):
    """
    Legacy compatibility wrapper for existing code.

    Maintains backward compatibility with ComprehensivePostTradeAnalysis.
    """

    pass


@dataclass(frozen=True)
class PortfolioOptimizationResult(OptimizeResult):
    """
    Legacy compatibility wrapper for existing code.

    Maintains backward compatibility with PortfolioOptimizationResult.
    """

    weights: Dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with Decimal weights."""
        base_dict = super().to_dict()
        base_dict["weights"] = {k: str(v) for k, v in self.weights.items()}
        return base_dict
