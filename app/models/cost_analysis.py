"""
Cost Analysis Models.

This module defines Pydantic models for cost analysis functionality
including cost breakdown, profitability validation, and Cost Impact Ratio (CIR) analysis.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from app.backtesting.models import TradeStatus
from app.models.order import OrderSide, OrderType


class CostType(str, Enum):
    """Types of trading costs."""

    COMMISSION = "commission"
    SLIPPAGE = "slippage"
    INFRASTRUCTURE = "infrastructure"
    MARKET_IMPACT = "market_impact"
    BORROWING_COST = "borrowing_cost"


class CostBreakdownModel(BaseModel):
    """Pydantic model for cost breakdown."""

    trade_id: str = Field(..., description="Unique trade identifier", env="TRADE_ID")
    symbol: str = Field(..., description="Trading symbol", env="SYMBOL")
    order_type: OrderType = Field(..., description="Order type", env="ORDER_TYPE")
    quantity: Decimal = Field(..., description="Trade quantity", env="QUANTITY")
    execution_price: Decimal = Field(..., description="Execution price", env="EXECUTION_PRICE")

    # Cost components
    commission: Decimal = Field(..., ge=0, description="Commission cost", env="COMMISSION")
    slippage: Decimal = Field(..., ge=0, description="Slippage cost", env="SLIPPAGE")
    market_impact: Decimal = Field(..., ge=0, description="Market impact cost", env="MARKET_IMPACT")
    infrastructure_cost: Decimal = Field(
        ..., ge=0, description="Infrastructure cost", env="INFRASTRUCTURE_COST"
    )
    borrowing_cost: Decimal = Field(..., ge=0, description="Borrowing cost", env="BORROWING_COST")

    # Calculated metrics
    total_cost: Decimal = Field(..., ge=0, description="Total cost", env="TOTAL_COST")
    cost_percentage: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Cost as percentage of trade value",
        env="COST_PERCENTAGE",
    )
    cost_impact_ratio: Decimal = Field(
        ..., ge=0, description="Cost Impact Ratio (CIR)", env="COST_IMPACT_RATIO"
    )

    timestamp: datetime = Field(..., description="Cost calculation timestamp", env="TIMESTAMP")

    @field_validator("total_cost")
    @classmethod
    def validate_total_cost(cls, v, info=None):
        """Validate that total cost equals sum of components."""
        if (
            info
            and hasattr(info, "data")
            and "commission" in info.data
            and "slippage" in info.data
            and "market_impact" in info.data
        ):
            expected_total = (
                info.data["commission"]
                if info and hasattr(info, "data") and "commission" in info.data
                else (
                    None + info.data["slippage"]
                    if info and hasattr(info, "data") and "slippage" in info.data
                    else (
                        None + info.data["market_impact"]
                        if info and hasattr(info, "data") and "market_impact" in info.data
                        else None
                        + info.data.get(
                            "infrastructure_cost",
                            Decimal("0") if info and hasattr(info, "data") else None,
                        )
                        + info.data.get(
                            "borrowing_cost",
                            Decimal("0") if info and hasattr(info, "data") else None,
                        )
                    )
                )
            )
            if abs(v - expected_total) > Decimal("0.01"):
                raise ValueError("Total cost does not match sum of components")
        return v

    @field_validator("cost_percentage")
    @classmethod
    def validate_cost_percentage(cls, v, info=None):
        """Validate cost percentage calculation."""
        if (
            info
            and hasattr(info, "data")
            and "total_cost" in info.data
            and "execution_price" in info.data
            and "quantity" in info.data
        ):
            trade_value = (
                info.data["execution_price"]
                if info and hasattr(info, "data") and "execution_price" in info.data
                else (
                    None * info.data["quantity"]
                    if info and hasattr(info, "data") and "quantity" in info.data
                    else None
                )
            )
            if trade_value > 0:
                expected_percentage = (
                    info.data["total_cost"]
                    if info and hasattr(info, "data") and "total_cost" in info.data
                    else None / trade_value
                ) * 100
                if abs(v - expected_percentage) > Decimal("0.01"):
                    raise ValueError("Cost percentage calculation is incorrect")
        return v


class CostAnalysisResultModel(BaseModel):
    """Pydantic model for cost analysis result."""

    strategy_name: str = Field(..., description="Strategy name", env="STRATEGY_NAME")
    analysis_period: Tuple[datetime, datetime] = Field(..., description="Analysis period")
    total_trades: int = Field(..., ge=0, description="Total number of trades", env="TOTAL_TRADES")

    # Cost metrics
    total_commission: Decimal = Field(
        ..., ge=0, description="Total commission costs", env="TOTAL_COMMISSION"
    )
    total_slippage: Decimal = Field(
        ..., ge=0, description="Total slippage costs", env="TOTAL_SLIPPAGE"
    )
    total_market_impact: Decimal = Field(
        ..., ge=0, description="Total market impact costs", env="TOTAL_MARKET_IMPACT"
    )
    total_infrastructure: Decimal = Field(
        ..., ge=0, description="Total infrastructure costs", env="TOTAL_INFRASTRUCTURE"
    )
    total_borrowing: Decimal = Field(
        ..., ge=0, description="Total borrowing costs", env="TOTAL_BORROWING"
    )
    total_costs: Decimal = Field(..., ge=0, description="Total costs", env="TOTAL_COSTS")

    # Profitability metrics
    gross_profit: Decimal = Field(..., description="Gross profit", env="GROSS_PROFIT")
    net_profit: Decimal = Field(..., description="Net profit after costs", env="NET_PROFIT")
    cost_impact_ratio: Decimal = Field(
        ..., ge=0, description="Cost Impact Ratio (CIR)", env="COST_IMPACT_RATIO"
    )
    profitability_threshold: Decimal = Field(
        ...,
        ge=0,
        description="Minimum profitability threshold",
        env="PROFITABILITY_THRESHOLD",
    )

    # Cost breakdown by trade
    cost_breakdowns: List[CostBreakdownModel] = Field(..., description="Cost breakdowns by trade")

    # Validation results
    is_profitable: bool = Field(
        ..., description="Whether strategy is profitable", env="IS_PROFITABLE"
    )
    exceeds_cost_threshold: bool = Field(
        ..., description="Whether costs exceed threshold", env="EXCEEDS_COST_THRESHOLD"
    )
    recommendations: List[str] = Field(..., description="Recommendations for improvement")

    @field_validator("total_costs")
    @classmethod
    def validate_total_costs(cls, v, info=None):
        """Validate that total costs equal sum of components."""
        if (
            info
            and hasattr(info, "data")
            and all(
                key in info.data
                for key in [
                    "total_commission",
                    "total_slippage",
                    "total_market_impact",
                    "total_infrastructure",
                    "total_borrowing",
                ]
            )
        ):
            expected_total = (
                info.data["total_commission"]
                if info and hasattr(info, "data") and "total_commission" in info.data
                else (
                    None + info.data["total_slippage"]
                    if info and hasattr(info, "data") and "total_slippage" in info.data
                    else (
                        None + info.data["total_market_impact"]
                        if info and hasattr(info, "data") and "total_market_impact" in info.data
                        else (
                            None + info.data["total_infrastructure"]
                            if info
                            and hasattr(info, "data")
                            and "total_infrastructure" in info.data
                            else (
                                None + info.data["total_borrowing"]
                                if info and hasattr(info, "data") and "total_borrowing" in info.data
                                else None
                            )
                        )
                    )
                )
            )
            if abs(v - expected_total) > Decimal("0.01"):
                raise ValueError("Total costs do not match sum of components")
        return v

    @field_validator("net_profit")
    @classmethod
    def validate_net_profit(cls, v, info=None):
        """Validate net profit calculation."""
        if (
            info
            and hasattr(info, "data")
            and "gross_profit" in info.data
            and "total_costs" in info.data
        ):
            expected_net = (
                info.data["gross_profit"]
                if info and hasattr(info, "data") and "gross_profit" in info.data
                else (
                    None - info.data["total_costs"]
                    if info and hasattr(info, "data") and "total_costs" in info.data
                    else None
                )
            )
            if abs(v - expected_net) > Decimal("0.01"):
                raise ValueError("Net profit calculation is incorrect")
        return v

    @field_validator("cost_impact_ratio")
    @classmethod
    def validate_cost_impact_ratio(cls, v, info=None):
        """Validate Cost Impact Ratio calculation."""
        if (
            info
            and hasattr(info, "data")
            and "total_costs" in info.data
            and "gross_profit" in info.data
        ):
            if (
                info.data["gross_profit"]
                if info and hasattr(info, "data") and "gross_profit" in info.data
                else None > 0
            ):
                expected_cir = (
                    info.data["total_costs"]
                    if info and hasattr(info, "data") and "total_costs" in info.data
                    else (
                        None / info.data["gross_profit"]
                        if info and hasattr(info, "data") and "gross_profit" in info.data
                        else None
                    )
                ) * 100
                if abs(v - expected_cir) > Decimal("0.01"):
                    raise ValueError("Cost Impact Ratio calculation is incorrect")
        return v


class TradeCostAnalysisRequest(BaseModel):
    """Request model for trade cost analysis."""

    id: str = Field(..., description="Trade identifier", env="ID")
    symbol: str = Field(..., description="Trading symbol", env="SYMBOL")
    side: OrderSide = Field(..., description="Order side", env="SIDE")
    order_type: OrderType = Field(..., description="Order type", env="ORDER_TYPE")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity", env="QUANTITY")
    entry_price: Decimal = Field(..., gt=0, description="Entry price", env="ENTRY_PRICE")
    exit_price: Optional[Decimal] = Field(None, description="Exit price")
    entry_time: datetime = Field(..., description="Entry time", env="ENTRY_TIME")
    exit_time: Optional[datetime] = Field(None, description="Exit time")
    pnl: Optional[Decimal] = Field(None, description="Profit/Loss")
    status: TradeStatus = Field(
        default=TradeStatus.CLOSED, description="Trade status", env="STATUS"
    )
    commission: Optional[Decimal] = Field(None, ge=0, description="Commission paid")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    market_data: Dict[str, Any] = Field(
        default_factory=dict, description="Market data for cost calculation"
    )


class StrategyCostAnalysisRequest(BaseModel):
    """Request model for strategy cost analysis."""

    strategy_name: str = Field(..., description="Strategy name", env="STRATEGY_NAME")
    trades: List[TradeCostAnalysisRequest] = Field(..., description="List of trades to analyze")
    market_data: Dict[str, Any] = Field(
        default_factory=dict, description="Market data for cost calculation"
    )


class ProfitabilityValidationRequest(BaseModel):
    """Request model for profitability validation."""

    strategy_name: str = Field(..., description="Strategy name", env="STRATEGY_NAME")
    analysis_period: Tuple[datetime, datetime] = Field(..., description="Analysis period")
    total_trades: int = Field(..., ge=0, description="Total number of trades", env="TOTAL_TRADES")
    total_costs: Decimal = Field(..., ge=0, description="Total costs", env="TOTAL_COSTS")
    gross_profit: Decimal = Field(..., description="Gross profit", env="GROSS_PROFIT")
    net_profit: Decimal = Field(..., description="Net profit", env="NET_PROFIT")
    cost_impact_ratio: Decimal = Field(
        ..., ge=0, description="Cost Impact Ratio", env="COST_IMPACT_RATIO"
    )
    is_profitable: bool = Field(
        ..., description="Whether strategy is profitable", env="IS_PROFITABLE"
    )
    exceeds_cost_threshold: bool = Field(
        ..., description="Whether costs exceed threshold", env="EXCEEDS_COST_THRESHOLD"
    )
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class CostParametersModel(BaseModel):
    """Model for cost parameters configuration."""

    commission_rates: Dict[str, Decimal] = Field(..., description="Commission rates by asset class")
    slippage_rates: Dict[str, Decimal] = Field(..., description="Slippage rates by asset class")
    infrastructure_cost_per_trade: Decimal = Field(
        ...,
        ge=0,
        description="Infrastructure cost per trade",
        env="INFRASTRUCTURE_COST_PER_TRADE",
    )
    borrowing_cost_rate: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="Annual borrowing cost rate",
        env="BORROWING_COST_RATE",
    )
    min_profitability_threshold: Decimal = Field(
        ...,
        ge=0,
        description="Minimum profitability threshold",
        env="MIN_PROFITABILITY_THRESHOLD",
    )
    max_cost_impact_ratio: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Maximum allowed Cost Impact Ratio",
        env="MAX_COST_IMPACT_RATIO",
    )

    @field_validator("commission_rates")
    @classmethod
    def validate_commission_rates(cls, v):
        """Validate commission rates."""
        from app.shared.config.centralized_config import get_config
        cfg = get_config()
        max_commission = Decimal(str(getattr(cfg.trading, 'cost_max_commission_rate', 0.1)))
        for asset_class, rate in v.items():
            if rate < 0 or rate > max_commission:
                raise ValueError(f"Invalid commission rate for {asset_class}: {rate}")
        return v

    @field_validator("slippage_rates")
    @classmethod
    def validate_slippage_rates(cls, v):
        """Validate slippage rates."""
        from app.shared.config.centralized_config import get_config
        cfg = get_config()
        max_slippage = Decimal(str(getattr(cfg.trading, 'cost_max_slippage_rate', 0.05)))
        for asset_class, rate in v.items():
            if rate < 0 or rate > max_slippage:
                raise ValueError(f"Invalid slippage rate for {asset_class}: {rate}")
        return v


class CostAnalysisResponse(BaseModel):
    """Response model for cost analysis."""

    success: bool = Field(..., description="Whether analysis was successful", env="SUCCESS")
    data: Optional[CostAnalysisResultModel] = Field(None, description="Analysis result data")
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
        env="TIMESTAMP",
    )


class ProfitabilityValidationResponse(BaseModel):
    """Response model for profitability validation."""

    strategy_name: str = Field(..., description="Strategy name", env="STRATEGY_NAME")
    is_profitable: bool = Field(
        ..., description="Whether strategy is profitable", env="IS_PROFITABLE"
    )
    exceeds_cost_threshold: bool = Field(
        ..., description="Whether costs exceed threshold", env="EXCEEDS_COST_THRESHOLD"
    )
    is_valid: bool = Field(..., description="Whether strategy passes validation", env="IS_VALID")
    cost_impact_ratio: Decimal = Field(
        ..., ge=0, description="Cost Impact Ratio", env="COST_IMPACT_RATIO"
    )
    max_allowed_cir: Decimal = Field(
        ..., ge=0, description="Maximum allowed CIR", env="MAX_ALLOWED_CIR"
    )
    recommendations: List[str] = Field(..., description="Recommendations for improvement")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
        env="TIMESTAMP",
    )
