"""
Backtesting models for AlgoTrading system.

This module defines the data models for backtesting operations,
including trade records, performance metrics, and backtest configuration.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Tuple

# Try to import pydantic with fallback to dataclasses
try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback to standard library dataclasses
    from dataclasses import dataclass

    # Create pydantic-like API using dataclasses
    class Field:
        """Fallback Field descriptor for dataclasses."""

        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
            self.kwargs = kwargs

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            if self.default_factory is not None:
                if self.default_factory == list:
                    return []
                elif self.default_factory == dict:
                    return {}
                return self.default_factory()
            return self.default

    def field_validator(*args):
        """Fallback field validator decorator (no-op in dataclasses)."""

        def decorator(func):
            return func

        return decorator

    def model_validator(*args, **kwargs):
        """Fallback model validator decorator (no-op in dataclasses)."""

        def decorator(func):
            return func

        return decorator

    # Create a base class that mimics pydantic's BaseModel
    class BaseModel:
        """Fallback base class using dataclasses."""

        def __init_subclass__(cls, **kwargs):
            # Add dataclass decorator automatically
            dataclass(cls)

        def model_dump(self):
            """Convert to dictionary (pydantic compatibility)."""
            result = {}
            for key in self.__dataclass_fields__:
                value = getattr(self, key)
                if isinstance(value, Decimal):
                    result[key] = float(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = [v.model_dump() if hasattr(v, 'model_dump') else v for v in value]
                else:
                    result[key] = value
            return result

        def dict(self):
            """Legacy method (pydantic compatibility)."""
            return self.model_dump()


class TradeStatus(str, Enum):
    """Trade execution status."""

    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


class Trade(BaseModel):
    """Individual trade record for backtesting."""

    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Trade side (buy/sell)")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    exit_price: Optional[Decimal] = Field(None, gt=0, description="Exit price")
    entry_time: datetime = Field(..., description="Entry timestamp")
    exit_time: Optional[datetime] = Field(None, description="Exit timestamp")
    status: TradeStatus = Field(TradeStatus.OPEN, description="Trade status")
    pnl: Optional[Decimal] = Field(None, description="Profit/Loss")
    pnl_percentage: Optional[Decimal] = Field(None, description="P&L percentage")
    commission: Decimal = Field(default=Decimal("0"), ge=0, description="Commission paid")
    slippage: Decimal = Field(default=Decimal("0"), ge=0, description="Slippage cost")
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


class PerformanceMetrics(BaseModel):
    """Performance metrics for backtesting results."""

    # Basic metrics
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(..., ge=0, description="Number of winning trades")
    losing_trades: int = Field(..., ge=0, description="Number of losing trades")
    win_rate: Decimal = Field(..., ge=0, le=100, description="Win rate percentage")

    # P&L metrics
    total_pnl: Decimal = Field(..., description="Total profit/loss")
    total_pnl_percentage: Decimal = Field(..., description="Total P&L percentage")
    gross_profit: Decimal = Field(..., ge=0, description="Gross profit")
    gross_loss: Decimal = Field(..., le=0, description="Gross loss")
    net_profit: Decimal = Field(..., description="Net profit")

    # Risk metrics
    max_drawdown: Decimal = Field(..., le=0, description="Maximum drawdown")
    max_drawdown_percentage: Decimal = Field(..., le=0, description="Maximum drawdown percentage")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio")
    risk_reward_ratio: Optional[Decimal] = Field(
        None, description="Average risk/reward ratio per trade (target ≥1:3)"
    )

    # Advanced financial metrics (PHASE 4 MODULE 7)
    calmar_ratio: Optional[Decimal] = Field(
        None, description="Calmar Ratio: CAGR / |Max Drawdown| (>1.0 good, >3.0 excellent)"
    )
    omega_ratio: Optional[Decimal] = Field(
        None, description="Omega Ratio: Probability-weighted gains/losses ratio (>1.0 profitable)"
    )
    ulcer_index: Optional[Decimal] = Field(
        None, description="Ulcer Index: Duration-weighted drawdown penalty (lower is better)"
    )
    volatility_annualized: Optional[Decimal] = Field(
        None, description="Annualized Volatility: std(returns) * sqrt(252)"
    )
    recovery_factor: Optional[Decimal] = Field(
        None, description="Recovery Factor: Net Profit / |Max Drawdown|"
    )
    profit_factor: Optional[Decimal] = Field(
        None, description="Profit Factor: Gross Profit / |Gross Loss| (>1.5 good, >2.0 excellent)"
    )
    skewness: Optional[Decimal] = Field(
        None, description="Skewness: Return distribution asymmetry (negative is worse)"
    )
    kurtosis: Optional[Decimal] = Field(
        None, description="Excess Kurtosis: Tail risk measure (negative is better)"
    )
    var_95: Optional[Decimal] = Field(
        None, description="Value at Risk 95%: Worst 5% scenario (negative value = potential loss)"
    )
    cvar_95: Optional[Decimal] = Field(
        None, description="Conditional VaR 95%: Expected loss beyond VaR threshold"
    )

    # Trade statistics
    avg_win: Decimal = Field(..., description="Average winning trade")
    avg_loss: Decimal = Field(..., le=0, description="Average losing trade")
    largest_win: Decimal = Field(..., ge=0, description="Largest winning trade")
    largest_loss: Decimal = Field(..., le=0, description="Largest losing trade")
    expectancy: Optional[Decimal] = Field(
        None,
        description="Expectancy: Expected value per trade (positive=profitable, negative=unprofitable)",
    )

    # Time metrics
    total_days: int = Field(..., ge=0, description="Total trading days")
    avg_trade_duration: Decimal = Field(..., ge=0, description="Average trade duration in days")

    @model_validator(mode="after")
    def validate_metrics_consistency(self) -> "PerformanceMetrics":
        """Validate metrics consistency."""
        if self.total_trades != self.winning_trades + self.losing_trades:
            raise ValueError("Total trades must equal winning + losing trades")

        if self.total_trades > 0:
            expected_win_rate = Decimal(str((self.winning_trades / self.total_trades) * 100))
            if abs(self.win_rate - expected_win_rate) > Decimal("0.01"):
                raise ValueError(
                    f"Win rate calculation mismatch: {self.win_rate} vs {expected_win_rate}"
                )

        if self.gross_profit + self.gross_loss != self.net_profit:
            raise ValueError("Gross profit + gross loss must equal net profit")

        return self


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
