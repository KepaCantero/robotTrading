"""
T4.1: BacktestOrchestrator Models

Dataclasses for backtesting orchestration, execution, and result handling.
Uses centralized configuration for default values.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Import config for default values (avoid circular import)
def _get_default_commission() -> Decimal:
    from app.core.centralized_config import get_config
    return Decimal("0.001")  # 0.1% default commission

def _get_default_slippage() -> Decimal:
    from app.core.centralized_config import get_config
    tt = get_config().trading_thresholds
    return tt.base_slippage / Decimal("100")  # Convert % to decimal

def _get_default_stop_loss() -> Decimal:
    from app.core.centralized_config import get_config
    tt = get_config().trading_thresholds
    return Decimal(str(tt.stop_loss_pct))

def _get_default_take_profit() -> Decimal:
    from app.core.centralized_config import get_config
    tt = get_config().trading_thresholds
    return Decimal(str(tt.take_profit_pct))

def _get_default_max_loss() -> Decimal:
    from app.core.centralized_config import get_config
    tt = get_config().trading_thresholds
    return Decimal(str(tt.circuit_breaker_daily_loss))

def _get_default_position_size() -> Decimal:
    from app.core.centralized_config import get_config
    tt = get_config().trading_thresholds
    return Decimal(str(tt.max_position_size))


class BacktestStatus(str, Enum):
    """Status of a backtest execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BacktestConfig:
    """Configuration for a single backtest execution - uses centralized config for defaults."""

    # Test metadata
    test_id: str
    profile_id: str
    input_id: str
    module_parameter_set_id: str

    # Backtesting parameters
    initial_capital: Decimal
    start_date: date
    end_date: date
    commission_pct: Decimal = field(default_factory=_get_default_commission)  # Uses config
    slippage_pct: Decimal = field(default_factory=_get_default_slippage)  # Uses config

    # Strategy parameters
    strategy_name: str = "momentum_modular"
    symbols: List[str] = field(default_factory=list)
    max_positions: int = 10
    max_position_size_pct: Decimal = field(default_factory=_get_default_position_size)  # Uses config

    # Risk parameters - use centralized config
    max_loss_pct: Decimal = field(default_factory=_get_default_max_loss)  # Uses config (circuit_breaker_daily_loss)
    stop_loss_pct: Decimal = field(default_factory=_get_default_stop_loss)  # Uses config
    take_profit_pct: Decimal = field(default_factory=_get_default_take_profit)  # Uses config

    # Validation/gating
    run_risk_envelope: bool = True
    enable_diagnostics: bool = False


@dataclass
class BacktestMetrics:
    """Performance metrics from a backtest."""

    # Returns
    total_return_pct: Decimal
    annual_return_pct: Decimal
    monthly_return_pct: Decimal

    # Risk metrics
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    max_drawdown_pct: Decimal
    volatility_pct: Decimal
    var_95_pct: Decimal  # Value at Risk

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: Decimal
    avg_win_pct: Decimal
    avg_loss_pct: Decimal
    profit_factor: Decimal
    expectancy_pct: Decimal

    # Other metrics
    recovery_factor: Decimal  # Net profit / max drawdown
    ulcer_index: Decimal
    consecutive_wins: int
    consecutive_losses: int


@dataclass
class BacktestResult:
    """Result of a single backtest execution."""

    # Execution metadata
    test_id: str
    profile_id: str
    input_id: str
    status: BacktestStatus = BacktestStatus.PENDING
    success: bool = False
    error_message: str = ""

    # Configuration reference
    config: Optional[BacktestConfig] = None

    # Performance metrics
    metrics: Optional[BacktestMetrics] = None

    # Feasibility calculation
    required_annual_return_pct: Decimal = field(default=Decimal("0.0"))
    achieved_annual_return_pct: Decimal = field(default=Decimal("0.0"))
    feasibility_ratio: Decimal = field(default=Decimal("0.0"))  # achieved / required

    # Capital evolution
    starting_capital: Decimal = field(default=Decimal("0.0"))
    ending_capital: Decimal = field(default=Decimal("0.0"))
    peak_capital: Decimal = field(default=Decimal("0.0"))

    # Validation results
    validation_passed: bool = True
    validation_warnings: List[str] = field(default_factory=list)
    validation_failures: List[str] = field(default_factory=list)

    # Execution timing
    execution_timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "test_id": self.test_id,
            "profile_id": self.profile_id,
            "input_id": self.input_id,
            "status": self.status.value,
            "success": self.success,
            "error_message": self.error_message,
            "required_annual_return_pct": str(self.required_annual_return_pct),
            "achieved_annual_return_pct": str(self.achieved_annual_return_pct),
            "feasibility_ratio": str(self.feasibility_ratio),
            "starting_capital": str(self.starting_capital),
            "ending_capital": str(self.ending_capital),
            "peak_capital": str(self.peak_capital),
            "validation_passed": self.validation_passed,
            "execution_duration_seconds": self.execution_duration_seconds,
            "metrics": (
                {
                    "total_return_pct": str(self.metrics.total_return_pct),
                    "annual_return_pct": str(self.metrics.annual_return_pct),
                    "sharpe_ratio": str(self.metrics.sharpe_ratio),
                    "max_drawdown_pct": str(self.metrics.max_drawdown_pct),
                    "win_rate_pct": str(self.metrics.win_rate_pct),
                }
                if self.metrics
                else None
            ),
        }


@dataclass
class BacktestOrchestrationRequest:
    """Request to orchestrate backtesting for a profile."""

    profile_id: str
    input_id: str
    module_parameter_set_id: str
    initial_capital: Decimal
    target_monthly_return_eur: Decimal
    objective: str  # Investment objective
    risk_profile: str  # Risk profile
    start_date: date
    end_date: date
    strategy_name: str = "momentum_modular"
    symbols: List[str] = field(default_factory=list)


@dataclass
class BacktestOrchestrationResult:
    """Result of backtest orchestration."""

    success: bool
    backtest_result: Optional[BacktestResult] = None
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    feasibility_ratio: Decimal = field(default=Decimal("0.0"))
    feasibility_status: str = "unknown"  # APPROVED, CONDITIONAL, REJECTED
    orchestration_time_ms: float = 0.0
