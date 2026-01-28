"""
Post-Trade Analysis Entity - Domain Layer

This entity represents a complete post-trade analysis from all systems.
It's a pure domain entity with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict


@dataclass
class PostTradeAnalysis:
    """
    Complete post-trade analysis from ALL systems.

    This is a domain entity that contains the results of comprehensive
    post-trade analysis across all trading systems without any infrastructure
    dependencies.
    """

    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal

    # Cost breakdown
    implementation_shortfall_bps: float = 0.0
    market_impact_bps: float = 0.0
    timing_cost_bps: float = 0.0
    effective_spread_bps: float = 0.0

    # Quality metrics
    execution_quality_score: float = 50.0
    price_improvement_bps: float = 0.0

    # SLO tracking (Google SRE)
    latency_ms: float = 0.0
    fill_rate: float = 100.0
    slo_met: bool = True

    def get_cost_summary(self) -> Dict[str, float]:
        """Get a summary of all execution costs."""
        return {
            "implementation_shortfall_bps": self.implementation_shortfall_bps,
            "market_impact_bps": self.market_impact_bps,
            "timing_cost_bps": self.timing_cost_bps,
            "effective_spread_bps": self.effective_spread_bps,
            "total_cost_bps": self.implementation_shortfall_bps,
        }

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get a summary of execution quality."""
        return {
            "execution_quality_score": self.execution_quality_score,
            "price_improvement_bps": self.price_improvement_bps,
            "fill_rate": self.fill_rate,
            "slo_met": self.slo_met,
        }

    def get_slo_summary(self) -> str:
        """Get a human-readable SLO summary."""
        status = "✅ MET" if self.slo_met else "❌ VIOLATED"
        return (
            f"SLO {status}: {self.latency_ms:.0f}ms "
            f"(threshold: 100ms, fill rate: {self.fill_rate:.1f}%)"
        )

    def is_high_quality_execution(self) -> bool:
        """Determine if this was a high-quality execution."""
        return self.slo_met and self.execution_quality_score >= 70.0 and self.fill_rate >= 95.0
