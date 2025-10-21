"""
Cost Analysis Models.

This module defines Pydantic models for cost analysis functionality
including cost breakdown, profitability validation, and Cost Impact Ratio (CIR) analysis.
"""

from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from app.models.order import OrderType, OrderSide
from app.backtesting.models import TradeStatus


class CostType(str, Enum):
    """Types of trading costs."""
    COMMISSION = "commission"
    SLIPPAGE = "slippage"
    INFRASTRUCTURE = "infrastructure"
    MARKET_IMPACT = "market_impact"
    BORROWING_COST = "borrowing_cost"


class CostBreakdownModel(BaseModel):
    """Pydantic model for cost breakdown."""
    
    trade_id: str = Field(..., description="Unique trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., description="Trade quantity")
    execution_price: Decimal = Field(..., description="Execution price")
    
    # Cost components
    commission: Decimal = Field(..., ge=0, description="Commission cost")
    slippage: Decimal = Field(..., ge=0, description="Slippage cost")
    market_impact: Decimal = Field(..., ge=0, description="Market impact cost")
    infrastructure_cost: Decimal = Field(..., ge=0, description="Infrastructure cost")
    borrowing_cost: Decimal = Field(..., ge=0, description="Borrowing cost")
    
    # Calculated metrics
    total_cost: Decimal = Field(..., ge=0, description="Total cost")
    cost_percentage: Decimal = Field(..., ge=0, le=100, description="Cost as percentage of trade value")
    cost_impact_ratio: Decimal = Field(..., ge=0, description="Cost Impact Ratio (CIR)")
    
    timestamp: datetime = Field(..., description="Cost calculation timestamp")
    
    @validator('total_cost')
    def validate_total_cost(cls, v, values):
        """Validate that total cost equals sum of components."""
        if 'commission' in values and 'slippage' in values and 'market_impact' in values:
            expected_total = (
                values['commission'] + 
                values['slippage'] + 
                values['market_impact'] + 
                values.get('infrastructure_cost', Decimal('0')) + 
                values.get('borrowing_cost', Decimal('0'))
            )
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError("Total cost does not match sum of components")
        return v
    
    @validator('cost_percentage')
    def validate_cost_percentage(cls, v, values):
        """Validate cost percentage calculation."""
        if 'total_cost' in values and 'execution_price' in values and 'quantity' in values:
            trade_value = values['execution_price'] * values['quantity']
            if trade_value > 0:
                expected_percentage = (values['total_cost'] / trade_value) * 100
                if abs(v - expected_percentage) > Decimal('0.01'):
                    raise ValueError("Cost percentage calculation is incorrect")
        return v


class CostAnalysisResultModel(BaseModel):
    """Pydantic model for cost analysis result."""
    
    strategy_name: str = Field(..., description="Strategy name")
    analysis_period: Tuple[datetime, datetime] = Field(..., description="Analysis period")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    
    # Cost metrics
    total_commission: Decimal = Field(..., ge=0, description="Total commission costs")
    total_slippage: Decimal = Field(..., ge=0, description="Total slippage costs")
    total_market_impact: Decimal = Field(..., ge=0, description="Total market impact costs")
    total_infrastructure: Decimal = Field(..., ge=0, description="Total infrastructure costs")
    total_borrowing: Decimal = Field(..., ge=0, description="Total borrowing costs")
    total_costs: Decimal = Field(..., ge=0, description="Total costs")
    
    # Profitability metrics
    gross_profit: Decimal = Field(..., description="Gross profit")
    net_profit: Decimal = Field(..., description="Net profit after costs")
    cost_impact_ratio: Decimal = Field(..., ge=0, description="Cost Impact Ratio (CIR)")
    profitability_threshold: Decimal = Field(..., ge=0, description="Minimum profitability threshold")
    
    # Cost breakdown by trade
    cost_breakdowns: List[CostBreakdownModel] = Field(..., description="Cost breakdowns by trade")
    
    # Validation results
    is_profitable: bool = Field(..., description="Whether strategy is profitable")
    exceeds_cost_threshold: bool = Field(..., description="Whether costs exceed threshold")
    recommendations: List[str] = Field(..., description="Recommendations for improvement")
    
    @validator('total_costs')
    def validate_total_costs(cls, v, values):
        """Validate that total costs equal sum of components."""
        if all(key in values for key in ['total_commission', 'total_slippage', 'total_market_impact', 'total_infrastructure', 'total_borrowing']):
            expected_total = (
                values['total_commission'] + 
                values['total_slippage'] + 
                values['total_market_impact'] + 
                values['total_infrastructure'] + 
                values['total_borrowing']
            )
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError("Total costs do not match sum of components")
        return v
    
    @validator('net_profit')
    def validate_net_profit(cls, v, values):
        """Validate net profit calculation."""
        if 'gross_profit' in values and 'total_costs' in values:
            expected_net = values['gross_profit'] - values['total_costs']
            if abs(v - expected_net) > Decimal('0.01'):
                raise ValueError("Net profit calculation is incorrect")
        return v
    
    @validator('cost_impact_ratio')
    def validate_cost_impact_ratio(cls, v, values):
        """Validate Cost Impact Ratio calculation."""
        if 'total_costs' in values and 'gross_profit' in values:
            if values['gross_profit'] > 0:
                expected_cir = (values['total_costs'] / values['gross_profit']) * 100
                if abs(v - expected_cir) > Decimal('0.01'):
                    raise ValueError("Cost Impact Ratio calculation is incorrect")
        return v


class TradeCostAnalysisRequest(BaseModel):
    """Request model for trade cost analysis."""
    
    id: str = Field(..., description="Trade identifier")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    exit_price: Optional[Decimal] = Field(None, description="Exit price")
    entry_time: datetime = Field(..., description="Entry time")
    exit_time: Optional[datetime] = Field(None, description="Exit time")
    pnl: Optional[Decimal] = Field(None, description="Profit/Loss")
    status: TradeStatus = Field(default=TradeStatus.CLOSED, description="Trade status")
    commission: Optional[Decimal] = Field(None, ge=0, description="Commission paid")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    market_data: Dict[str, Any] = Field(default_factory=dict, description="Market data for cost calculation")


class StrategyCostAnalysisRequest(BaseModel):
    """Request model for strategy cost analysis."""
    
    strategy_name: str = Field(..., description="Strategy name")
    trades: List[TradeCostAnalysisRequest] = Field(..., description="List of trades to analyze")
    market_data: Dict[str, Any] = Field(default_factory=dict, description="Market data for cost calculation")


class ProfitabilityValidationRequest(BaseModel):
    """Request model for profitability validation."""
    
    strategy_name: str = Field(..., description="Strategy name")
    analysis_period: Tuple[datetime, datetime] = Field(..., description="Analysis period")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    total_costs: Decimal = Field(..., ge=0, description="Total costs")
    gross_profit: Decimal = Field(..., description="Gross profit")
    net_profit: Decimal = Field(..., description="Net profit")
    cost_impact_ratio: Decimal = Field(..., ge=0, description="Cost Impact Ratio")
    is_profitable: bool = Field(..., description="Whether strategy is profitable")
    exceeds_cost_threshold: bool = Field(..., description="Whether costs exceed threshold")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class CostParametersModel(BaseModel):
    """Model for cost parameters configuration."""
    
    commission_rates: Dict[str, Decimal] = Field(..., description="Commission rates by asset class")
    slippage_rates: Dict[str, Decimal] = Field(..., description="Slippage rates by asset class")
    infrastructure_cost_per_trade: Decimal = Field(..., ge=0, description="Infrastructure cost per trade")
    borrowing_cost_rate: Decimal = Field(..., ge=0, le=1, description="Annual borrowing cost rate")
    min_profitability_threshold: Decimal = Field(..., ge=0, description="Minimum profitability threshold")
    max_cost_impact_ratio: Decimal = Field(..., ge=0, le=100, description="Maximum allowed Cost Impact Ratio")
    
    @validator('commission_rates')
    def validate_commission_rates(cls, v):
        """Validate commission rates."""
        for asset_class, rate in v.items():
            if rate < 0 or rate > Decimal('0.1'):  # Max 10% commission
                raise ValueError(f"Invalid commission rate for {asset_class}: {rate}")
        return v
    
    @validator('slippage_rates')
    def validate_slippage_rates(cls, v):
        """Validate slippage rates."""
        for asset_class, rate in v.items():
            if rate < 0 or rate > Decimal('0.05'):  # Max 5% slippage
                raise ValueError(f"Invalid slippage rate for {asset_class}: {rate}")
        return v


class CostAnalysisResponse(BaseModel):
    """Response model for cost analysis."""
    
    success: bool = Field(..., description="Whether analysis was successful")
    data: Optional[CostAnalysisResultModel] = Field(None, description="Analysis result data")
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ProfitabilityValidationResponse(BaseModel):
    """Response model for profitability validation."""
    
    strategy_name: str = Field(..., description="Strategy name")
    is_profitable: bool = Field(..., description="Whether strategy is profitable")
    exceeds_cost_threshold: bool = Field(..., description="Whether costs exceed threshold")
    is_valid: bool = Field(..., description="Whether strategy passes validation")
    cost_impact_ratio: Decimal = Field(..., ge=0, description="Cost Impact Ratio")
    max_allowed_cir: Decimal = Field(..., ge=0, description="Maximum allowed CIR")
    recommendations: List[str] = Field(..., description="Recommendations for improvement")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
