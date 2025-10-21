"""
Backtesting models for AlgoTrading system.

This module defines the data models for backtesting operations,
including trade records, performance metrics, and backtest configuration.
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


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
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate trade side."""
        if v.lower() not in ['buy', 'sell']:
            raise ValueError("Trade side must be 'buy' or 'sell'")
        return v.lower()
    
    @model_validator(mode='after')
    def validate_trade_logic(self) -> 'Trade':
        """Validate trade logic."""
        if self.status == TradeStatus.CLOSED:
            if self.exit_price is None:
                raise ValueError("Closed trade must have exit price")
            if self.exit_time is None:
                raise ValueError("Closed trade must have exit time")
            if self.pnl is None:
                raise ValueError("Closed trade must have P&L calculated")
        
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
    
    # Trade statistics
    avg_win: Decimal = Field(..., description="Average winning trade")
    avg_loss: Decimal = Field(..., le=0, description="Average losing trade")
    largest_win: Decimal = Field(..., ge=0, description="Largest winning trade")
    largest_loss: Decimal = Field(..., le=0, description="Largest losing trade")
    
    # Time metrics
    total_days: int = Field(..., ge=0, description="Total trading days")
    avg_trade_duration: Decimal = Field(..., ge=0, description="Average trade duration in days")
    
    @model_validator(mode='after')
    def validate_metrics_consistency(self) -> 'PerformanceMetrics':
        """Validate metrics consistency."""
        if self.total_trades != self.winning_trades + self.losing_trades:
            raise ValueError("Total trades must equal winning + losing trades")
        
        if self.total_trades > 0:
            expected_win_rate = Decimal(str((self.winning_trades / self.total_trades) * 100))
            if abs(self.win_rate - expected_win_rate) > Decimal('0.01'):
                raise ValueError(f"Win rate calculation mismatch: {self.win_rate} vs {expected_win_rate}")
        
        if self.gross_profit + self.gross_loss != self.net_profit:
            raise ValueError("Gross profit + gross loss must equal net profit")
        
        return self


class BacktestConfig(BaseModel):
    """Configuration for backtesting runs."""
    
    initial_capital: Decimal = Field(default=Decimal("100000"), gt=0, description="Initial capital")
    commission_per_trade: Decimal = Field(default=Decimal("1.0"), ge=0, description="Commission per trade")
    slippage_percentage: Decimal = Field(default=Decimal("0.1"), ge=0, le=10, description="Slippage percentage")
    risk_free_rate: Decimal = Field(default=Decimal("0.02"), ge=0, le=1, description="Risk-free rate (annual)")
    max_position_size: Decimal = Field(default=Decimal("0.1"), gt=0, le=1, description="Maximum position size as % of capital")
    stop_loss_percentage: Optional[Decimal] = Field(None, ge=0, le=50, description="Stop loss percentage")
    take_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="Take profit percentage")
    
    @field_validator('slippage_percentage')
    @classmethod
    def validate_slippage(cls, v: Decimal) -> Decimal:
        """Validate slippage percentage."""
        if v > Decimal('5.0'):  # 5% max slippage
            raise ValueError(f"Slippage percentage too high: {v}%. Maximum allowed: 5%")
        return v
    
    @model_validator(mode='after')
    def validate_config_logic(self) -> 'BacktestConfig':
        """Validate configuration logic."""
        if self.stop_loss_percentage is not None and self.take_profit_percentage is not None:
            if self.stop_loss_percentage >= self.take_profit_percentage:
                raise ValueError("Stop loss percentage must be less than take profit percentage")
        
        return self


class BacktestResult(BaseModel):
    """Complete backtest result."""
    
    config: BacktestConfig = Field(..., description="Backtest configuration")
    trades: List[Trade] = Field(..., description="List of executed trades")
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    final_capital: Decimal = Field(..., gt=0, description="Final capital")
    total_return: Decimal = Field(..., description="Total return percentage")
    annualized_return: Decimal = Field(..., description="Annualized return percentage")
    
    @model_validator(mode='after')
    def validate_result_consistency(self) -> 'BacktestResult':
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
