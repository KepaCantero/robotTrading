"""
Realistic Execution Model for Backtesting (FASE 5.2)

This module provides comprehensive execution modeling including:
- Realistic transaction costs (US equity fee structure)
- Advanced slippage modeling
- Market impact (Almgren-Chriss model)
- Order fill simulation with partial fills
- Time-of-day impact modeling

Components:
- TransactionCostCalculator: US equity fee structure (SEC, FINRA, exchange fees)
- SlippageModel: Size and volatility-based slippage
- MarketImpactModel: Almgren-Chriss permanent and temporary impact
- OrderFillSimulator: Realistic order fill simulation
- RealisticExecutionModel: Main execution model coordinating all components

Usage:
    from app.backtesting.execution import (
        RealisticExecutionModel,
        ExecutionConfig,
        TransactionCostCalculator,
        SlippageModel,
        MarketImpactModel,
    )

    # Configure execution model
    config = ExecutionConfig(
        cost_config=CostConfig(
            commission_per_share=Decimal("0.005"),
            sec_fee_rate=Decimal("0.0000078"),
            finra_taf_rate=Decimal("0.000145"),
        ),
        slippage_config=SlippageConfig(
            base_slippage_bps=Decimal("5"),
            vol_multiplier=Decimal("2"),
        ),
        impact_config=ImpactConfig(
            temporary_coef=Decimal("0.1"),
            permanent_coef=Decimal("0.05"),
        ),
    )

    execution_model = RealisticExecutionModel(config)
    result = await execution_model.execute_order(signal, market_data)
"""

from .execution_model import (
    CostConfig,
    ExecutionConfig,
    ImpactConfig,
    RealisticExecutionModel,
    SlippageConfig,
)
from .market_impact import AlmgrenChrissConfig, MarketImpact, MarketImpactModel
from .models import CostBreakdown, ExecutionResult, ExecutionSummary
from .order_fill_simulator import FillReason, FillResult, MarketSnapshot, Order, OrderFillSimulator
from .slippage_model import SlippageEstimate, SlippageModel, TimeOfDayImpact
from .transaction_cost import US_EQUITY_FEES, TransactionCost, TransactionCostCalculator

__all__ = [
    # Main execution model
    "RealisticExecutionModel",
    "ExecutionConfig",
    # Cost components
    "TransactionCostCalculator",
    "TransactionCost",
    "CostConfig",
    "US_EQUITY_FEES",
    # Slippage components
    "SlippageModel",
    "SlippageEstimate",
    "SlippageConfig",
    "TimeOfDayImpact",
    # Market impact components
    "MarketImpactModel",
    "MarketImpact",
    "AlmgrenChrissConfig",
    "ImpactConfig",
    # Order fill simulation
    "OrderFillSimulator",
    "FillResult",
    "FillReason",
    "MarketSnapshot",
    "Order",
    # Result models
    "ExecutionResult",
    "ExecutionSummary",
    "CostBreakdown",
]

# Version information
__version__ = "1.0.0"
__author__ = "AlgoTrading Team"
