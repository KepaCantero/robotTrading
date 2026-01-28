"""
Robust Backtesting Engine (FASE 5.1)

This module provides a production-grade backtesting engine capable of handling
25+ years of historical data with proper bias corrections and corporate actions handling.

Key Features:
- Efficient handling of large datasets (25+ years)
- Survivorship bias correction
- Corporate actions handling (splits, M&A, spin-offs)
- Dividend reinvestment (DRIP)
- Checkpoint/resume functionality
- Progress tracking for long backtests
- Comprehensive performance metrics

Based on AUDIT_PLAN_COMPLETO requirements for professional backtesting.

Example:
    ```python
    from app.backtesting.robust_engine import RobustBacktester, RobustBacktestConfig

    config = RobustBacktestConfig(
        initial_capital=Decimal("100000"),
        start_date=date(1999, 1, 1),
        end_date=date(2024, 12, 31),
        enable_dividend_reinvestment=True,
        enable_survivorship_correction=True,
    )

    backtester = RobustBacktester(config)
    result = await backtester.run_backtest(strategy, years=25)
    ```
"""

from .corporate_actions import (
    CorporateActionHandler,
    CorporateActionType,
)
from .dividend_handler import (
    DividendAction,
    DividendHandler,
    DividendTracker,
    DripConfig,
)
from .look_ahead_validator import (
    LookAheadValidator,
    ValidationResult,
)
from .models import (
    BacktestCheckpoint,
    CorporateAction,
    DelistedReturnData,
    DividendPayment,
    Merger,
    ProgressUpdate,
    SpinOff,
    StockSplit,
)
from .performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
    RegimeAnalysis,
    RollingMetrics,
    YearlyBreakdown,
)
from .pit_database import PITDatabaseClient
from .robust_backtester import (
    CheckpointData,
    RobustBacktestConfig,
    RobustBacktester,
    RobustBacktestResult,
)
from .survivorship_adjuster import (
    DelistedStock,
    DelistingReason,
    SurvivorshipAdjuster,
    SurvivorshipFreeResult,
)

__all__ = [
    # Main engine
    "RobustBacktester",
    "RobustBacktestConfig",
    "RobustBacktestResult",
    "CheckpointData",
    # Point-in-Time database
    "PITDatabaseClient",
    # Look-ahead bias validation
    "LookAheadValidator",
    "ValidationResult",
    # Corporate actions
    "CorporateActionHandler",
    "CorporateActionType",
    "StockSplit",
    "Merger",
    "SpinOff",
    "DividendPayment",
    "CorporateAction",
    # Dividend handling
    "DividendHandler",
    "DividendAction",
    "DividendTracker",
    "DripConfig",
    # Survivorship bias
    "SurvivorshipAdjuster",
    "DelistedStock",
    "DelistingReason",
    "SurvivorshipFreeResult",
    "DelistedReturnData",
    # Performance tracking
    "PerformanceTracker",
    "PerformanceMetrics",
    "YearlyBreakdown",
    "RollingMetrics",
    "RegimeAnalysis",
    # Checkpointing
    "BacktestCheckpoint",
    "ProgressUpdate",
]
