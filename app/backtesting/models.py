"""
Backtesting models for AlgoTrading system.

This module defines the data models for backtesting operations,
including trade records, performance metrics, and backtest configuration.

REQUIREMENT: pydantic>=2.0 is a hard dependency for this module.
The fallback pattern has been removed to ensure consistent validation behavior.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator



class TradeSide(str, Enum):
    """Trade side (buy/sell)."""

    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, Enum):
    """Trade execution status."""

    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


class Trade(BaseModel):
    """
    Canonical Trade model for the AlgoTrading system.

    This is the single source of truth for all trade-related data across
    backtesting, portfolio management, and execution layers.

    Consolidated from:
    - app/backtesting/models.py (original canonical)
    - app/domain/portfolio/multi_asset/models.py (merged)
    - app/domain/services/backtesting/backtest_engine.py (merged)

    Note: The SQLAlchemy Trade model in app/infrastructure/persistence/database/models.py
    remains separate for database persistence. Use to_pydantic() and from_pydantic()
    methods for conversion.
    """

    # Core identification
    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")

    # Trade side and quantity
    side: str = Field(..., description="Trade side (buy/sell)")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")

    # Price information
    entry_price: Decimal = Field(..., gt=0, description="Entry/execution price")
    exit_price: Optional[Decimal] = Field(None, gt=0, description="Exit price (for closed trades)")

    # Timestamps
    entry_time: datetime = Field(..., description="Entry/execution timestamp")
    exit_time: Optional[datetime] = Field(None, description="Exit timestamp (for closed trades)")

    # Status and P&L
    status: TradeStatus = Field(TradeStatus.OPEN, description="Trade status")
    pnl: Optional[Decimal] = Field(None, description="Profit/Loss")
    pnl_percentage: Optional[Decimal] = Field(None, description="P&L percentage")

    # Transaction costs
    commission: Decimal = Field(default=Decimal("0"), ge=0, description="Commission paid")
    slippage: Decimal = Field(default=Decimal("0"), ge=0, description="Slippage cost")
    market_impact: Decimal = Field(default=Decimal("0"), ge=0, description="Market impact cost")

    # Additional context (from multi_asset Trade)
    asset_class: Optional[str] = Field(None, description="Asset class (equity, bond, crypto, etc.)")
    value: Optional[Decimal] = Field(None, ge=0, description="Total trade value (quantity * price)")
    currency: str = Field(default="USD", description="Trade currency")
    priority: int = Field(default=0, ge=0, le=100, description="Execution priority (0-100)")
    estimated_cost: Decimal = Field(
        default=Decimal("0"), ge=0, description="Estimated trading cost"
    )
    reason: Optional[str] = Field(None, description="Reason or signal that triggered the trade")

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate trade side."""
        if v.lower() not in ["buy", "sell"]:
            raise ValueError("Trade side must be 'buy' or 'sell'")
        return v.lower()

    @model_validator(mode="after")
    def validate_trade_logic(self) -> "Trade":
        """Validate trade logic."""
        if self.status == TradeStatus.CLOSED:
            if self.exit_price is None:
                raise ValueError("Closed trade must have exit price")
            if self.exit_time is None:
                raise ValueError("Closed trade must have exit time")
            # Pnl can be None for now - will be calculated properly

        if self.exit_time is not None and self.exit_time < self.entry_time:
            raise ValueError("Exit time cannot be before entry time")

        return self

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side.lower() == "buy"

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side.lower() == "sell"

    @property
    def notional_value(self) -> Decimal:
        """Total notional value of the trade."""
        return self.quantity * self.entry_price

    @property
    def total_cost(self) -> Decimal:
        """Total cost including commission, slippage, and market impact."""
        return self.commission + self.slippage + self.market_impact + self.estimated_cost


class PerformanceMetrics(BaseModel):
    """
    Canonical Performance Metrics for backtesting results.

    This is the SINGLE SOURCE OF TRUTH for all performance metrics across the system.
    All other PerformanceMetrics implementations should import from this module.

    Consolidates metrics from:
    - app/backtesting/robust_engine/performance_tracker.py
    - app/domain/services/backtesting/backtest_engine.py
    - app/domain/models/portfolio_analytics.py
    - app/presentation/dashboard/dashboard_data.py
    """

    # =========================================================================
    # RETURN METRICS
    # =========================================================================
    total_return: Optional[Decimal] = Field(
        None, description="Total return over entire period (decimal form)"
    )
    annualized_return: Optional[Decimal] = Field(None, description="Annualized return percentage")
    cagr: Optional[Decimal] = Field(None, description="Compound Annual Growth Rate (decimal form)")
    cumulative_return: Optional[Decimal] = Field(None, description="Cumulative return over period")

    # =========================================================================
    # BASIC TRADE METRICS
    # =========================================================================
    total_trades: int = Field(default=0, ge=0, description="Total number of trades")
    winning_trades: int = Field(default=0, ge=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, ge=0, description="Number of losing trades")
    win_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="Win rate percentage")

    # =========================================================================
    # P&L METRICS
    # =========================================================================
    total_pnl: Decimal = Field(default=Decimal("0"), description="Total profit/loss")
    total_pnl_percentage: Decimal = Field(default=Decimal("0"), description="Total P&L percentage")
    gross_profit: Decimal = Field(default=Decimal("0"), ge=0, description="Gross profit")
    gross_loss: Decimal = Field(default=Decimal("0"), le=0, description="Gross loss")
    net_profit: Decimal = Field(default=Decimal("0"), description="Net profit")
    daily_pnl: Optional[Decimal] = Field(None, description="Daily profit/loss")
    daily_return_pct: Optional[float] = Field(None, description="Daily return percentage")

    # =========================================================================
    # RISK METRICS
    # =========================================================================
    max_drawdown: Decimal = Field(
        default=Decimal("0"), le=0, description="Maximum drawdown (decimal form)"
    )
    max_drawdown_percentage: Decimal = Field(
        default=Decimal("0"), le=0, description="Maximum drawdown percentage"
    )
    max_drawdown_duration: Optional[int] = Field(
        None, ge=0, description="Maximum drawdown duration in days"
    )
    current_drawdown: Optional[float] = Field(None, description="Current drawdown")
    volatility: Optional[Decimal] = Field(None, description="Volatility (decimal form)")
    volatility_annualized: Optional[Decimal] = Field(
        None, description="Annualized Volatility: std(returns) * sqrt(252)"
    )
    annualized_volatility: Optional[Decimal] = Field(
        None, description="Annualized volatility (alternative name)"
    )

    # =========================================================================
    # RISK-ADJUSTED RETURN METRICS
    # =========================================================================
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio (annualized)")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio (downside risk)")
    calmar_ratio: Optional[Decimal] = Field(
        None, description="Calmar Ratio: CAGR / |Max Drawdown| (>1.0 good, >3.0 excellent)"
    )
    omega_ratio: Optional[Decimal] = Field(
        None, description="Omega Ratio: Probability-weighted gains/losses ratio (>1.0 profitable)"
    )
    treynor_ratio: Optional[Decimal] = Field(
        None, description="Treynor ratio: (Return - RiskFree) / Beta"
    )
    information_ratio: Optional[Decimal] = Field(None, description="Information ratio vs benchmark")
    risk_reward_ratio: Optional[Decimal] = Field(
        None, description="Average risk/reward ratio per trade (target >=1:3)"
    )

    # =========================================================================
    # ADVANCED RISK METRICS
    # =========================================================================
    ulcer_index: Optional[Decimal] = Field(
        None, description="Ulcer Index: Duration-weighted drawdown penalty (lower is better)"
    )
    recovery_factor: Optional[Decimal] = Field(
        None, description="Recovery Factor: Net Profit / |Max Drawdown|"
    )
    profit_factor: Optional[Decimal] = Field(
        None, description="Profit Factor: Gross Profit / |Gross Loss| (>1.5 good, >2.0 excellent)"
    )
    tail_ratio: Optional[Decimal] = Field(
        None, description="Ratio of extreme gains to extreme losses"
    )

    # =========================================================================
    # RETURN DISTRIBUTION METRICS
    # =========================================================================
    skewness: Optional[Decimal] = Field(
        None, description="Skewness: Return distribution asymmetry (negative is worse)"
    )
    kurtosis: Optional[Decimal] = Field(
        None, description="Excess Kurtosis: Tail risk measure (negative is better)"
    )

    # =========================================================================
    # VALUE AT RISK METRICS
    # =========================================================================
    var_95: Optional[Decimal] = Field(
        None, description="Value at Risk 95%: Worst 5% scenario (negative value = potential loss)"
    )
    var_99: Optional[Decimal] = Field(None, description="Value at Risk 99%: Worst 1% scenario")
    cvar_95: Optional[Decimal] = Field(
        None, description="Conditional VaR 95%: Expected loss beyond VaR threshold"
    )

    # =========================================================================
    # TRADE STATISTICS
    # =========================================================================
    avg_win: Decimal = Field(default=Decimal("0"), description="Average winning trade")
    avg_loss: Decimal = Field(default=Decimal("0"), le=0, description="Average losing trade")
    avg_trade_return: Optional[Decimal] = Field(None, description="Average trade return")
    largest_win: Decimal = Field(default=Decimal("0"), ge=0, description="Largest winning trade")
    largest_loss: Decimal = Field(default=Decimal("0"), le=0, description="Largest losing trade")
    best_trade: Optional[Decimal] = Field(None, description="Best single trade return")
    worst_trade: Optional[Decimal] = Field(None, description="Worst single trade return")
    expectancy: Optional[Decimal] = Field(
        None,
        description="Expectancy: Expected value per trade (positive=profitable, negative=unprofitable)",
    )

    # =========================================================================
    # STREAK METRICS
    # =========================================================================
    winning_streak: Optional[int] = Field(None, ge=0, description="Longest winning streak")
    losing_streak: Optional[int] = Field(None, ge=0, description="Longest losing streak")

    # =========================================================================
    # YEARLY PERFORMANCE METRICS
    # =========================================================================
    best_year: Optional[Decimal] = Field(None, description="Best calendar year return")
    worst_year: Optional[Decimal] = Field(None, description="Worst calendar year return")
    avg_yearly_return: Optional[Decimal] = Field(None, description="Average yearly return")

    # =========================================================================
    # BENCHMARK COMPARISON METRICS
    # =========================================================================
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error vs benchmark")
    beta: Optional[Decimal] = Field(None, description="Portfolio beta")
    alpha: Optional[Decimal] = Field(None, description="Jensen's alpha")
    jensen_alpha: Optional[Decimal] = Field(None, description="Jensen's alpha (alternative name)")

    # =========================================================================
    # TIME METRICS
    # =========================================================================
    total_days: int = Field(default=0, ge=0, description="Total trading days")
    avg_trade_duration: Decimal = Field(
        default=Decimal("0"), ge=0, description="Average trade duration in days"
    )

    # =========================================================================
    # PORTFOLIO VALUE METRICS (for dashboard)
    # =========================================================================
    portfolio_value: Optional[Decimal] = Field(None, description="Current portfolio value")
    starting_capital: Optional[Decimal] = Field(None, description="Starting capital")

    @model_validator(mode="after")
    def validate_metrics_consistency(self) -> "PerformanceMetrics":
        """Validate metrics consistency - only validate if fields are set."""
        # Only validate trade counts if they are non-zero (indicates they were explicitly set)
        if self.total_trades > 0 or self.winning_trades > 0 or self.losing_trades > 0:
            if self.total_trades != self.winning_trades + self.losing_trades:
                raise ValueError("Total trades must equal winning + losing trades")

        # Only validate win rate if total_trades > 0
        if self.total_trades > 0 and self.win_rate != Decimal("0"):
            expected_win_rate = Decimal(str((self.winning_trades / self.total_trades) * 100))
            if abs(self.win_rate - expected_win_rate) > Decimal("0.01"):
                raise ValueError(
                    f"Win rate calculation mismatch: {self.win_rate} vs {expected_win_rate}"
                )

        # Only validate P&L consistency if values are set
        if self.gross_profit != Decimal("0") or self.gross_loss != Decimal("0"):
            if self.gross_profit + self.gross_loss != self.net_profit:
                raise ValueError("Gross profit + gross loss must equal net profit")

        return self

    class Config:
        """Pydantic config for PerformanceMetrics."""

        # Allow extra fields for forward compatibility
        extra = "ignore"
        # Use enum values
        use_enum_values = True


class BacktestConfig(BaseModel):
    """Configuration for backtesting runs."""

    strategy_name: str = Field(default="default_strategy", description="Strategy name")
    initial_capital: Decimal = Field(default=Decimal("100000"), gt=0, description="Initial capital")
    commission_per_trade: Decimal = Field(
        default=Decimal("1.0"), ge=0, description="Commission per trade"
    )
    slippage_percentage: Decimal = Field(
        default=Decimal("0.1"), ge=0, le=10, description="Slippage percentage"
    )
    risk_free_rate: Decimal = Field(
        default=Decimal("0.02"), ge=0, le=1, description="Risk-free rate (annual)"
    )
    max_position_size: Decimal = Field(
        default=Decimal("0.1"),
        gt=0,
        le=1,
        description="Maximum position size as % of capital",
    )
    stop_loss_percentage: Optional[Decimal] = Field(
        None, ge=0, le=50, description="Stop loss percentage"
    )
    take_profit_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Take profit percentage"
    )

    @field_validator("slippage_percentage")
    @classmethod
    def validate_slippage(cls, v: Decimal) -> Decimal:
        """Validate slippage percentage."""
        if v > Decimal("5.0"):  # 5% max slippage
            raise ValueError(f"Slippage percentage too high: {v}%. Maximum allowed: 5%")
        return v

    @model_validator(mode="after")
    def validate_config_logic(self) -> "BacktestConfig":
        """Validate configuration logic."""
        if self.stop_loss_percentage is not None and self.take_profit_percentage is not None:
            if self.stop_loss_percentage >= self.take_profit_percentage:
                raise ValueError("Stop loss percentage must be less than take profit percentage")

        return self


class BacktestResult(BaseModel):
    """Complete backtest result."""

    strategy_name: str = Field(default="default_strategy", description="Strategy name")
    config: Optional[BacktestConfig] = Field(default=None, description="Backtest configuration")
    trades: List[Trade] = Field(default_factory=list, description="List of executed trades")
    performance: Optional[PerformanceMetrics] = Field(
        default=None, description="Performance metrics"
    )
    equity_curve: List[Tuple[datetime, Decimal]] = Field(
        default_factory=list, description="Portfolio equity over time"
    )
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    final_capital: Decimal = Field(..., gt=0, description="Final capital")
    total_return: Decimal = Field(..., description="Total return percentage")
    annualized_return: Optional[Decimal] = Field(
        default=None, description="Annualized return percentage"
    )

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "BacktestResult":
        """Validate result consistency."""
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")

        if self.final_capital <= 0:
            raise ValueError("Final capital must be positive")

        # Validate that all trades are within the backtest period
        for trade in self.trades:
            if trade.entry_time < self.start_date or trade.entry_time > self.end_date:
                raise ValueError(f"Trade {trade.trade_id} entry time outside backtest period")

            if trade.exit_time is not None and trade.exit_time > self.end_date:
                raise ValueError(f"Trade {trade.trade_id} exit time after backtest end")

        return self
