"""
Post-Trade Analysis Entity - Domain Layer

This entity represents a complete post-trade analysis from all systems.
It's a pure domain entity with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict


@dataclass(frozen=True)
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

    def __post_init__(self) -> None:
        """Validate all trading-critical fields."""
        # Validate order_id
        if not self.order_id or not isinstance(self.order_id, str):
            raise ValueError("order_id must be a non-empty string")

        # Validate symbol
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("symbol must be a non-empty string")

        # Validate side
        valid_sides = {"BUY", "SELL", "buy", "sell"}
        if self.side not in valid_sides:
            raise ValueError(f"side must be one of {valid_sides}, got: {self.side}")

        # Validate quantity
        if not isinstance(self.quantity, Decimal):
            raise ValueError("quantity must be a Decimal")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got: {self.quantity}")

        # Validate execution_price
        if not isinstance(self.execution_price, Decimal):
            raise ValueError("execution_price must be a Decimal")
        if self.execution_price <= 0:
            raise ValueError(f"execution_price must be positive, got: {self.execution_price}")

        # Validate scores are in valid ranges
        if not 0.0 <= self.execution_quality_score <= 100.0:
            raise ValueError(
                f"execution_quality_score must be between 0 and 100, got: {self.execution_quality_score}"
            )

        if not 0.0 <= self.fill_rate <= 100.0:
            raise ValueError(f"fill_rate must be between 0 and 100, got: {self.fill_rate}")

        if self.latency_ms < 0:
            raise ValueError(f"latency_ms must be non-negative, got: {self.latency_ms}")

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
