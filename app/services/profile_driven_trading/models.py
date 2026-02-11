"""
Data models for Profile-Driven Trading Orchestrator.

Defines configuration, results, and intermediate data structures used
throughout the trading lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np


class StageType(Enum):
    """Types of stages in the trading lifecycle."""

    PROFILE_GENERATION = "profile_generation"
    UNIVERSE_SELECTION = "universe_selection"
    CAPITAL_ALLOCATION = "capital_allocation"
    SIGNAL_GENERATION = "signal_generation"
    TAX_OPTIMIZATION = "tax_optimization"
    RISK_VALIDATION = "risk_validation"
    BACKTEST_VALIDATION = "backtest_validation"
    TRADE_EXECUTION = "trade_execution"


@dataclass
class OrchestratorConfig:
    """
    Configuration for the Profile-Driven Trading Orchestrator.

    Controls which features are enabled and how the orchestrator behaves.
    """

    # Feature flags
    enable_rl_signals: bool = True
    enable_tax_optimization: bool = True
    enable_backtest_validation: bool = True
    enable_risk_gates: bool = True
    auto_execute_trades: bool = False  # Default to dry-run for safety
    use_ibkr: bool = False  # Use Interactive Brokers or mock (default: disabled/mock)

    # Universe selection parameters
    include_sp500: bool = True
    include_nasdaq100: bool = False
    include_ibex35: bool = False
    include_crypto: bool = False
    top_n_per_universe: int = 100
    download_period: str = "6mo"
    download_interval: str = "1d"
    min_avg_volume: int = 1_000_000
    min_price: float = 5.0
    max_volatility: float = 0.15

    # Strategy allocation (default distribution)
    strategy_allocations: Dict[str, float] = field(
        default_factory=lambda: {
            "momentum": 0.50,
            "mean_reversion": 0.35,
            "pairs_trading": 0.15,
        }
    )

    # Risk limits
    max_position_size_pct: float = 0.10  # 10% max per position
    max_daily_loss_pct: float = 0.05  # 5% daily loss limit
    max_drawdown_pct: float = 0.15  # 15% max drawdown

    # Tax optimization parameters
    marginal_tax_rate: float = 0.25  # 25% tax rate
    enable_tax_loss_harvesting: bool = True

    # Backtest validation parameters
    backtest_start_date: Optional[str] = None  # Auto-detected if None
    backtest_end_date: Optional[str] = None  # Auto-detected if None
    min_feasibility_ratio: float = 0.80  # 80% of target return

    # Logging and monitoring
    log_level: str = "INFO"
    enable_detailed_logging: bool = True
    save_execution_history: bool = True

    # Performance tuning
    max_concurrent_stages: int = 4  # Parallel stage execution
    timeout_seconds: int = 300  # 5 minutes per stage


@dataclass
class StageResult:
    """
    Result of executing a single stage in the pipeline.

    Captures success/failure, data produced, and performance metrics.
    """

    stage_type: StageType
    success: bool
    data: Optional[Any] = None
    message: str = ""
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage_type": self.stage_type.value,
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "has_data": self.data is not None,
        }


@dataclass
class SignalSet:
    """
    Set of trading signals from multiple sources.

    Combines signals from RL, momentum, mean reversion, and other strategies.
    """

    signals: Dict[str, str] = field(default_factory=dict)  # symbol -> "BUY"/"SELL"/"HOLD"
    buy_count: int = 0
    sell_count: int = 0
    hold_count: int = 0
    rl_signals: Dict[str, str] = field(default_factory=dict)
    momentum_signals: Dict[str, str] = field(default_factory=dict)
    mean_reversion_signals: Dict[str, str] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)  # symbol -> confidence
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def add_signal(
        self, symbol: str, action: str, source: str = "default", confidence: float = 0.5
    ):
        """Add a signal for a symbol."""
        self.signals[symbol] = action
        self.confidence_scores[symbol] = confidence

        if action == "BUY":
            self.buy_count += 1
        elif action == "SELL":
            self.sell_count += 1
        else:
            self.hold_count += 1

        # Track by source
        if source == "rl":
            self.rl_signals[symbol] = action
        elif source == "momentum":
            self.momentum_signals[symbol] = action
        elif source == "mean_reversion":
            self.mean_reversion_signals[symbol] = action

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the signal set."""
        total = len(self.signals)
        return {
            "total_signals": total,
            "buy_signals": self.buy_count,
            "sell_signals": self.sell_count,
            "hold_signals": self.hold_count,
            "buy_pct": self.buy_count / total if total > 0 else 0,
            "sell_pct": self.sell_count / total if total > 0 else 0,
            "hold_pct": self.hold_count / total if total > 0 else 0,
            "rl_signals_count": len(self.rl_signals),
            "momentum_signals_count": len(self.momentum_signals),
            "mean_reversion_signals_count": len(self.mean_reversion_signals),
            "avg_confidence": (
                np.mean(list(self.confidence_scores.values()))
                if self.confidence_scores
                else 0
            ),
        }


@dataclass
class RiskValidationResult:
    """
    Result of risk validation checks.

    Indicates whether the portfolio passes risk limits and what violations exist.
    """

    passed: bool
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of risk validation."""
        return {
            "passed": self.passed,
            "risk_level": self.risk_level,
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
            "key_metrics": {
                k: v
                for k, v in self.metrics.items()
                if k in ["daily_loss_pct", "drawdown_pct", "leverage", "concentration"]
            },
        }


@dataclass
class ExecutionResult:
    """
    Result of trade execution.

    Details what trades were executed and their status.
    """

    executed: bool
    dry_run: bool = True
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_failed: int = 0
    total_value_eur: float = 0.0
    execution_time_ms: float = 0.0
    order_details: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of execution result."""
        return {
            "executed": self.executed,
            "dry_run": self.dry_run,
            "orders_submitted": self.orders_submitted,
            "orders_filled": self.orders_filled,
            "orders_failed": self.orders_failed,
            "fill_rate": (
                self.orders_filled / self.orders_submitted if self.orders_submitted > 0 else 0
            ),
            "total_value_eur": self.total_value_eur,
        }


@dataclass
class TradingResult:
    """
    Complete result of the trading lifecycle execution.

    Contains all stage results, final allocation, signals, and execution outcome.
    """

    success: bool
    profile_id: str = ""
    allocation: Optional[Dict[str, Any]] = None
    signals: Optional[SignalSet] = None
    execution_result: Optional[ExecutionResult] = None
    stage_results: List[StageResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Optional intermediate results
    investment_profile: Optional[Any] = None
    universe_data: Optional[Dict[str, Any]] = None
    tax_optimized_allocation: Optional[Any] = None
    risk_validation: Optional[RiskValidationResult] = None
    backtest_result: Optional[Any] = None

    def get_stage_result(self, stage_type: StageType) -> Optional[StageResult]:
        """Get result for a specific stage."""
        for result in self.stage_results:
            if result.stage_type == stage_type:
                return result
        return None

    def get_successful_stages(self) -> List[StageResult]:
        """Get all successfully completed stages."""
        return [r for r in self.stage_results if r.success]

    def get_failed_stages(self) -> List[StageResult]:
        """Get all failed stages."""
        return [r for r in self.stage_results if not r.success]

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the trading result."""
        successful_stages = self.get_successful_stages()
        failed_stages = self.get_failed_stages()

        return {
            "success": self.success,
            "profile_id": self.profile_id,
            "execution_time_seconds": self.execution_time_ms / 1000,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stages": {
                "total": len(self.stage_results),
                "successful": len(successful_stages),
                "failed": len(failed_stages),
                "failed_stages": [s.stage_type.value for s in failed_stages],
            },
            "allocation": {
                "has_allocation": self.allocation is not None,
                "num_positions": len(self.allocation) if self.allocation else 0,
            },
            "signals": self.signals.get_summary() if self.signals else None,
            "execution": self.execution_result.get_summary() if self.execution_result else None,
            "risk": (self.risk_validation.get_summary() if self.risk_validation else None),
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "profile_id": self.profile_id,
            "execution_time_ms": self.execution_time_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stage_results": [r.to_dict() for r in self.stage_results],
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.get_summary(),
        }
