"""
Pre-Trade Analysis Entity - Domain Layer

This entity represents a complete pre-trade analysis from all systems.
It's a pure domain entity with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PreTradeAnalysis:
    """
    Complete pre-trade analysis from ALL 17 systems (8 main + 12 compliance).

    This is a domain entity that contains the results of comprehensive
    pre-trade analysis across all trading systems without any infrastructure
    dependencies.
    """

    # Basic decision
    can_execute: bool
    confidence: float
    reasons: List[str] = field(default_factory=list)

    # ========== 8 MAIN SYSTEMS ==========

    # 1. Backtesting Engine
    backtest_confidence: float = 0.0
    backtest_period: Optional[str] = None
    historical_sharpe: Optional[float] = None

    # 2. Risk Engine (main)
    portfolio_var: Optional[float] = None
    position_limit_ok: bool = True
    leverage_ratio: float = 0.0
    drawdown_limit_ok: bool = True

    # 3. Portfolio Engine (main)
    current_exposure: float = 0.0
    diversification_score: float = 0.0
    correlation_risk: float = 0.0

    # 4. Data Engine
    data_freshness_ms: float = 0.0
    data_quality_score: float = 100.0
    missing_data_detected: bool = False

    # 5. Context Engine (main)
    market_regime: Optional[str] = None
    volatility_regime: str = "NORMAL"
    correlation_regime: str = "NORMAL"
    regime_confidence: float = 0.0

    # 6. Execution Engine (main)
    execution_probability: float = 0.95
    estimated_slippage_bps: float = 0.0
    optimal_participation_rate: float = 0.0

    # 7. Strategies
    strategy_signal: float = 0.0
    strategy_health: float = 100.0

    # 8. Live/Paper Trading
    account_balance_ok: bool = True
    buying_power_ok: bool = True
    day_trading_count: int = 0
    pattern_day_trader_ok: bool = True

    # ========== 12 COMPLIANCE SYSTEMS ==========

    # 1. Ernest Chan (Rule 1)
    chan_regime: Optional[str] = None
    chan_factor_scores: Dict[str, float] = field(default_factory=dict)
    chan_optimization_method: str = "mean_variance"
    chan_execution_algo: Optional[str] = None

    # 2. Narang (Rule 2)
    narang_alpha_signal: Optional[float] = None
    narang_alpha_quality: str = "UNKNOWN"
    narang_recommended_holding_period: Optional[int] = None
    narang_transaction_cost_bps: float = 0.0

    # 3. Lopez de Prado (Rule 3)
    sample_weights_available: bool = False
    meta_labeling_signal: Optional[float] = None
    purged_cv_score: Optional[float] = None
    mcc_metric: Optional[float] = None

    # 4. Tomasini (Rule 4)
    tomasini_architecture_score: float = 100.0
    walk_forward_passed: bool = True
    overfitting_risk: str = "LOW"

    # 5. Hastie (Rule 5)
    statistical_model_health: float = 100.0
    cross_validation_score: Optional[float] = None
    regularization_strength: float = 0.0
    feature_importance_stable: bool = True

    # 6. Harris (Rule 6)
    harris_order_book_depth_ok: bool = True
    harris_liquidity_score: float = 50.0
    harris_vpin: float = 0.0
    harris_pin: float = 0.0
    bid_ask_bounce_risk: str = "LOW"

    # 7. O'Hara (Rule 7)
    ohara_liquidity_regime: str = "NORMAL"
    ohara_order_flow_toxicity: float = 0.0
    ohara_price_discovery_score: float = 50.0
    dark_pool_available: bool = False

    # 8. Percival (Rule 8)
    architecture_pattern_compliance: float = 100.0
    clean_architecture_score: float = 100.0
    dependency_health: float = 100.0

    # 9. Hull (Rule 13)
    hull_var_1d_95: Optional[float] = None
    hull_var_1d_99: Optional[float] = None
    hull_greeks_delta: Optional[float] = None
    hull_greeks_gamma: Optional[float] = None
    hull_stress_test_passed: bool = True

    # 10. Google SRE (Rule 20)
    slo_compliance: bool = True
    error_budget_remaining: float = 100.0
    latency_p95_ms: float = 0.0
    golden_signals_health: float = 100.0

    # 11. Beck TDD (Rule 21)
    test_coverage: float = 100.0
    tests_passing: bool = True
    tdd_compliance: float = 100.0

    # 12. Martin Clean Arch (Rule 18)
    martin_layer_separation: float = 100.0
    martin_dependency_rule: float = 100.0
    martin_interface_health: float = 100.0

    # ========== AGGREGATED METRICS ==========

    # Combined microstructure (Harris + O'Hara)
    liquidity_score: float = 50.0
    liquidity_regime: str = "NORMAL"

    # Combined cost estimates
    market_impact_bps: float = 0.0
    timing_cost_bps: float = 0.0
    total_cost_bps: float = 0.0

    # Execution recommendations
    venue: str = "lit_exchange"
    algorithm: str = "LIMIT"
    limit_price: Optional[Decimal] = None

    # System participation
    systems_contributed: int = 0
    systems_total: int = 17

    def get_execution_summary(self) -> str:
        """Get a human-readable execution summary."""
        if not self.can_execute:
            return f"Cannot execute: {'; '.join(self.reasons)}"

        return (
            f"Execute {self.algorithm} @ {self.limit_price or 'MARKET'} "
            f"on {self.venue} (confidence: {self.confidence:.0%}, "
            f"est. cost: {self.total_cost_bps:.1f} bps)"
        )

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get a summary of risk metrics."""
        return {
            "portfolio_var": self.portfolio_var,
            "position_limit_ok": self.position_limit_ok,
            "drawdown_limit_ok": self.drawdown_limit_ok,
            "hull_var_1d_95": self.hull_var_1d_95,
            "leverage_ratio": self.leverage_ratio,
            "liquidity_score": self.liquidity_score,
        }

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get a summary of compliance metrics."""
        return {
            "slo_compliance": self.slo_compliance,
            "test_coverage": self.test_coverage,
            "clean_architecture_score": self.clean_architecture_score,
            "architecture_pattern_compliance": self.architecture_pattern_compliance,
        }
